# CYC: build-with-nuitka
import asyncio
import hashlib
import logging
import os
from typing import Annotated, Literal

import peewee
from fastapi import APIRouter, Body, Depends, File, Form, HTTPException, Path, Query, UploadFile
from httpx import HTTPStatusError
from peewee import JOIN, fn
from speedy.peewee_plus.engine import IntegrityErrors
from starlette.status import HTTP_400_BAD_REQUEST, HTTP_409_CONFLICT

from remarkable.common.constants import RuleReviewStatus
from remarkable.common.storage import localstorage
from remarkable.common.util import generate_timestamp
from remarkable.db import pw_db
from remarkable.dependencies import (
    check_any_permissions,
    check_user_permission,
    get_current_user,
    model_by_cond_with_perm,
    model_with_perm,
    pw_transaction,
)
from remarkable.models.new_file import NewFile
from remarkable.models.new_user import NewAdminUser
from remarkable.models.query_helper import AsyncPagination
from remarkable.pw_models.law import (
    LAW_FILE_PARENT,
    Law,
    LawCheckPoint,
    LawCPsScenarios,
    LawOrder,
    LawRefreshStatus,
    LawRule,
    LawRulesScenarios,
    LawRuleStatus,
    LawScenario,
    LawsScenarios,
    LawStatus,
)
from remarkable.pw_models.model import NewFileTree
from remarkable.routers import DEBUG_WEBIF, debug_route
from remarkable.routers.schemas import ContractRects, PaginateResWithScenarioIdsSchema
from remarkable.routers.schemas.law import (
    AnalysisLawCheckPointSchema,
    ApplyLawRulesSchema,
    ContractComplianceCheckPointWithRectsLLMS,
    ContractComplianceResultLLMS,
    CreatedLawsSchema,
    CreateLawSchema,
    DiffLawRuleSchema,
    EditLawCheckPointSchema,
    EditLawRule,
    EditLawSchema,
    ExtractRuleKeywordsSchema,
    LawCheckPointPaginateResSchema,
    LawCheckPointReviewSchema,
    LawCheckPointsAliasSchema,
    LawCheckPointSimpleDBSchema,
    LawFileDBSchema,
    LawOrderDBSchema,
    LawOrderNameDBSchema,
    LawRuleDBSchema,
    RefreshLawSchema,
    RuleCheckPointLLMS,
    RuleKeywordsSchema,
    SaveAllLawCheckPointSchema,
    ScenarioDBSchema,
    ScenarioSchema,
    SearchLawCheckPointSchema,
    SearchLawOrderSchema,
    SearchLawRuleSchema,
    TuningLawRuleResLLMS,
)
from remarkable.routers.schemas.law_judge import LawJudgeLLMResultSchema
from remarkable.service.law import extract_contract_contents, get_file_reader, judge_check_point_template
from remarkable.service.law_chatdoc import mark_created_laws, public_laws
from remarkable.service.law_prompt import (
    analysis_rule_focus_area,
    check_contract_compliance,
    extract_rule_keywords,
    split_rule_check_point,
)
from remarkable.utils.split_law import clean_rule
from remarkable.worker.tasks.law_tasks import convert_rule_task, parse_law_file, split_law_rules

law_router = APIRouter(prefix="/laws", tags=["law"])
logger = logging.getLogger(__name__)


async def reparse_law_file_with_status(law):
    await pw_db.update(law, status=LawStatus.PENDING)
    return parse_law_file.delay(law.id)


@law_router.get("/scenarios", response_model=list[ScenarioDBSchema])
async def get_scenarios(user: NewAdminUser = Depends(get_current_user)):
    scenarios = await pw_db.execute(LawScenario.select().order_by(LawScenario.id.asc()))

    return scenarios


@law_router.post("/scenarios", response_model=ScenarioDBSchema)
async def create_scenario(form: ScenarioSchema, user: NewAdminUser = Depends(check_user_permission("manage_law"))):
    try:
        scenario = await pw_db.create(LawScenario, name=form.name, user_id=user.id)
    except IntegrityErrors as e:
        raise HTTPException(status_code=HTTP_409_CONFLICT, detail="应用场景已存在") from e

    return scenario


@law_router.put("/scenarios/{scenario_id:int}", response_model=ScenarioDBSchema)
async def update_scenario(
    form: ScenarioSchema,
    scenario: Annotated[LawScenario, model_with_perm(LawScenario, alias="scenario_id", action="update")],
    user: NewAdminUser = Depends(get_current_user),
):
    try:
        await pw_db.update(scenario, name=form.name, updated_by_id=user.id)
    except IntegrityErrors as e:
        raise HTTPException(status_code=HTTP_409_CONFLICT, detail="应用场景名称已存在") from e

    return scenario


@law_router.delete("/scenarios/{scenario_id:int}", dependencies=[Depends(pw_transaction)])
async def delete_scenario(
    scenario: Annotated[
        LawScenario, model_with_perm(LawScenario, alias="scenario_id", for_update=True, action="update")
    ],
):
    if await pw_db.exists(LawsScenarios.select().where(LawsScenarios.scenario_id == scenario.id)):
        raise HTTPException(HTTP_400_BAD_REQUEST, "应用场景正在使用中，无法删除")
    if await pw_db.exists(LawRulesScenarios.select().where(LawRulesScenarios.scenario_id == scenario.id)):
        raise HTTPException(HTTP_400_BAD_REQUEST, "应用场景正在使用中，无法删除")
    if await pw_db.exists(LawCPsScenarios.select().where(LawCPsScenarios.scenario_id == scenario.id)):
        raise HTTPException(HTTP_400_BAD_REQUEST, "应用场景正在使用中，无法删除")
    if await pw_db.exists(NewFile.select().where(NewFile.scenario_id == scenario.id)):
        raise HTTPException(HTTP_400_BAD_REQUEST, "应用场景已被文件使用，无法删除")
    if await pw_db.exists(NewFileTree.select().where(NewFileTree.default_scenario_id == scenario.id)):
        raise HTTPException(HTTP_400_BAD_REQUEST, "应用场景已被文件树使用，无法删除")
    await pw_db.delete(scenario)
    return {}


@law_router.get("/public-list")
async def get_public_laws():
    try:
        tree, created_uniques = await asyncio.gather(
            public_laws(),
            pw_db.scalars(Law.select(Law.chatdoc_unique.distinct()).where(Law.chatdoc_unique.is_null(False))),
        )
        mark_created_laws(tree, set(created_uniques))
        return tree
    except HTTPStatusError:
        raise
    except Exception as e:
        logger.exception(e)
        raise HTTPException(HTTP_400_BAD_REQUEST, "获取公共法规失败") from e


@law_router.post("", response_model=CreatedLawsSchema)
async def create_laws(
    form: Annotated[CreateLawSchema, Form(...)],
    user: Annotated[NewAdminUser, Depends(get_current_user)],
    files: list[UploadFile] = File(default_factory=list),
):
    if not form.chatdocs and not files:
        raise HTTPException(HTTP_400_BAD_REQUEST, "请上传或选择法规文件")

    laws = []
    duplicates = []
    if form.chatdocs:
        async with pw_db.atomic():
            scenario_ids = await pw_db.scalars(
                LawScenario.select(LawScenario.id, for_update=True).where(LawScenario.id.in_(form.scenario_ids))
            )
            if not scenario_ids or len(scenario_ids) != len(set(form.scenario_ids)):
                raise HTTPException(HTTP_400_BAD_REQUEST, "选择的应用场景未找到")
            rank = await LawOrder.max_rank_with_lock() + 1
            for chatdoc in form.chatdocs:
                order_name = os.path.splitext(chatdoc.name)[0]
                law_order = await pw_db.create(
                    LawOrder, rank=rank, name=order_name, user_id=user.id, is_template=form.is_template
                )
                law_order.laws = []
                if chatdoc.is_empty:
                    children = chatdoc.children
                else:
                    children = [chatdoc, *chatdoc.children]
                for _chatdoc in children:
                    law = await pw_db.create(
                        Law,
                        order_id=law_order.id,
                        name=_chatdoc.name,
                        is_template=form.is_template,
                        chatdoc_unique=_chatdoc.chatdoc_unique,
                        is_current=True,
                    )
                    law_order.laws.append(law)
                for scenario_id in scenario_ids:
                    await pw_db.create(LawsScenarios, law_id=law_order.id, scenario_id=scenario_id, user=user.id)
                laws.append(law_order)
                rank += 1
        for law in laws:
            for file in law.laws:
                parse_law_file.delay(file.id)
        return {"laws": laws, "duplicates": duplicates}

    async with pw_db.atomic():
        scenario_ids = await pw_db.scalars(
            LawScenario.select(LawScenario.id, for_update=True).where(LawScenario.id.in_(form.scenario_ids))
        )
        if not scenario_ids or len(scenario_ids) != len(set(form.scenario_ids)):
            raise HTTPException(HTTP_400_BAD_REQUEST, "选择的应用场景未找到")
        rank = await LawOrder.max_rank_with_lock() + 1
        for file in files:
            file_name, file_ext = os.path.splitext(file.filename)
            file_ext = file_ext.lower()
            if file_ext not in Law.LAW_FILE_EXTENSIONS:
                continue
            is_pdf = file_ext == ".pdf"
            file_content = await file.read()
            file_hash = hashlib.md5(file_content).hexdigest()
            if await pw_db.exists(Law.select().where(Law.hash == file_hash, Law.is_current)):
                duplicates.append(file.filename)
                continue
            law_order = await pw_db.create(
                LawOrder, rank=rank, name=file_name, user_id=user.id, is_template=form.is_template
            )
            localstorage.write_file(localstorage.get_path(file_hash, parent=LAW_FILE_PARENT), file_content)
            law = await pw_db.create(
                Law,
                order_id=law_order.id,
                name=file.filename,
                is_template=form.is_template,
                hash=file_hash,
                size=file.size,
                docx=None if is_pdf else file_hash,
                pdf=file_hash if is_pdf else None,
                is_current=True,
            )
            law_order.laws = [law]
            for scenario_id in scenario_ids:
                await pw_db.create(LawsScenarios, law_id=law_order.id, scenario_id=scenario_id, user=user.id)
            laws.append(law_order)
            rank += 1
    for law in laws:
        for file in law.laws:
            parse_law_file.delay(file.id)
    return {"laws": laws, "duplicates": duplicates}


@law_router.get("", response_model=PaginateResWithScenarioIdsSchema[LawOrderDBSchema])
async def get_laws(
    form: Annotated[SearchLawOrderSchema, Query(...)],
    user: Annotated[NewAdminUser, Depends(check_user_permission("manage_law"))],
):
    query = LawOrder.select(
        LawOrder.id,
        LawOrder.rank,
        LawOrder.name,
        LawOrder.is_template,
        LawOrder.refresh_status,
        LawOrder.meta["error_msg"].alias("refresh_msg"),
    ).order_by(LawOrder.rank.desc())
    if form.rank:
        query = query.where(LawOrder.rank == form.rank)
    elif form.name:
        query = query.where(LawOrder.name.contains(form.name))

    if form.scenario_ids:
        query = query.where(
            LawOrder.id.in_(
                LawsScenarios.select(LawsScenarios.law_id.distinct()).where(
                    LawsScenarios.scenario_id.in_(form.scenario_ids)
                )
            )
        )
    if form.from_chatdoc is not None:
        order_ids = Law.select(Law.order_id.distinct()).where(
            Law.is_current, Law.chatdoc_unique.is_null(not form.from_chatdoc)
        )
        query = query.where(LawOrder.id.in_(order_ids))
    if form.status:
        cte = (
            Law.select(
                Law.order_id,
                Law.status,
                fn.ROW_NUMBER()
                .over(partition_by=[Law.order_id], order_by=[(Law.status >= 0), fn.ABS(Law.status)])
                .alias("row"),
            )
            .where(Law.is_current)
            .cte("cte")
        )
        query = (
            query.join(cte, on=(LawOrder.id == cte.c.order_id))
            .where(cte.c.row == 1, cte.c.status.in_(form.status))
            .with_cte(cte)
        )
    if form.is_template is not None:
        query = query.where(LawOrder.is_template == form.is_template)

    pagination = AsyncPagination(query, form.page, form.size)
    laws = await pagination.data(Law.select(), LawsScenarios.select(), LawScenario.select(), no_marshal=True)

    laws["scenario_ids"] = await pw_db.scalars(LawsScenarios.select(LawsScenarios.scenario_id.distinct()))
    return laws


@law_router.get("/converted", response_model=list[LawOrderNameDBSchema])
async def get_law_orders(
    user: Annotated[
        NewAdminUser, Depends(check_any_permissions("manage_law", "customer_rule_participate", "customer_rule_review"))
    ],
    name: str = "",
):
    query = (
        LawOrder.select(LawOrder.id, LawOrder.name, LawOrder.rank, LawOrder.is_template)
        .where(
            fn.EXISTS(LawCheckPoint.select(1).where(LawCheckPoint.order_id == LawOrder.id, ~LawCheckPoint.abandoned))
        )
        .order_by(LawOrder.rank.desc())
    )
    if name:
        query = query.where(LawOrder.name.contains(name))

    orders = await pw_db.execute(query)
    return orders


@law_router.get("/{rank:int}", response_model=LawOrderDBSchema)
async def get_law(
    law_order: Annotated[
        LawOrder,
        model_by_cond_with_perm(
            LawOrder,
            LawOrder.rank,
            Law.select(),
            LawsScenarios.select(),
            LawScenario.select(),
            alias="rank",
            action="update",
            exclude_fields=[LawOrder.meta],
        ),
    ],
):
    return law_order


@law_router.put("/{law_id:int}")
async def edit_law(
    form: EditLawSchema,
    law_order: Annotated[
        LawOrder,
        model_with_perm(LawOrder, Law.split_ids(), alias="law_id", action="update", exclude_fields=[LawOrder.meta]),
    ],
    user: Annotated[NewAdminUser, Depends(get_current_user)],
):
    async with pw_db.atomic():
        scenario_ids = await pw_db.scalars(
            LawScenario.select(LawScenario.id, for_update=True).where(LawScenario.id.in_(form.scenario_ids))
        )
        if not scenario_ids or len(scenario_ids) != len(set(form.scenario_ids)):
            raise HTTPException(HTTP_400_BAD_REQUEST, "选择的法规场景未找到")
        rule_scenario_ids = await pw_db.scalars(
            LawRulesScenarios.select(LawRulesScenarios.scenario_id.distinct()).where(
                LawRulesScenarios.rule_id.in_(
                    LawRule.select(LawRule.id).where(
                        LawRule.order_id == law_order.id,
                    )
                )
            )
        )
        cp_scenario_ids = await pw_db.scalars(
            LawCPsScenarios.select(LawCPsScenarios.scenario_id.distinct()).where(
                LawCPsScenarios.cp_id.in_(
                    LawCheckPoint.select(LawCheckPoint.id).where(
                        LawCheckPoint.order_id == law_order.id,
                    )
                )
            )
        )
        if missing_scenario_ids := (set(cp_scenario_ids) | set(rule_scenario_ids)) - set(scenario_ids):
            scenario_names = await pw_db.scalars(
                LawScenario.select(LawScenario.name).where(LawScenario.id.in_(missing_scenario_ids))
            )
            raise HTTPException(HTTP_400_BAD_REQUEST, f"{'、'.join(scenario_names)}法规场景正在被使用, 无法移除")
        exists = await pw_db.execute(LawsScenarios.select().where(LawsScenarios.law_id == law_order.id))
        for law_scenario in exists:
            if law_scenario.scenario_id in scenario_ids:
                scenario_ids.remove(law_scenario.scenario_id)
                continue
            await pw_db.update(law_scenario, deleted_utc=generate_timestamp(), updated_by_id=user.id)
        for scenario_id in scenario_ids:
            await pw_db.create(LawsScenarios, law_id=law_order.id, scenario_id=scenario_id, user=user.id)
        await pw_db.update(law_order, name=form.name, updated_by_id=user.id)
    return {}


@law_router.put("/{law_id:int}/trigger")
async def trigger_law(
    law_order: Annotated[
        LawOrder,
        model_with_perm(LawOrder, Law.select(), alias="law_id", action="update", exclude_fields=[LawOrder.meta]),
    ],
    user: Annotated[NewAdminUser, Depends(get_current_user)],
):
    for law in law_order.laws:
        if law.status >= LawStatus.SPLIT:
            await reparse_law_file_with_status(law)
            continue
        if law.status < 0:
            if law.status <= LawStatus.SPLIT_FAIL:
                split_law_rules.delay(law.id)
            else:
                await reparse_law_file_with_status(law)
        elif law.status < LawStatus.PARSED:
            await reparse_law_file_with_status(law)
        else:
            split_law_rules.delay(law.id)
    return {}


@law_router.delete("/{law_id:int}")
async def delete_law(
    law_order: Annotated[
        LawOrder, model_with_perm(LawOrder, alias="law_id", action="update", exclude_fields=[LawOrder.meta])
    ],
    user: Annotated[NewAdminUser, Depends(get_current_user)],
):
    async with pw_db.atomic():
        law_order.updated_by_id = user.id
        law_order.rank = None
        await law_order.soft_delete()
    return {}


@law_router.post("/{law_id:int}/refresh", response_model=list[LawFileDBSchema])
async def refresh_law(
    form: Annotated[RefreshLawSchema, Form(...)],
    law_order: Annotated[
        LawOrder,
        model_with_perm(LawOrder, Law.select(), alias="law_id", action="update", exclude_fields=[LawOrder.meta]),
    ],
    user: Annotated[NewAdminUser, Depends(get_current_user)],
    file: UploadFile | None = None,
):
    if not form.chatdoc and file is None:
        raise HTTPException(HTTP_400_BAD_REQUEST, "请上传或选择要更新的法规文件")
    if not any(law.is_current and law.status >= LawStatus.SPLIT for law in law_order.laws):
        raise HTTPException(HTTP_400_BAD_REQUEST, "法规文件处理中，不可更新")
    refreshing_laws = [law for law in law_order.laws if not law.is_current]
    if law_order.refresh_status >= LawRefreshStatus.REFRESHING and refreshing_laws:
        raise HTTPException(HTTP_400_BAD_REQUEST, "法规文件正在更新中")

    if form.chatdoc:
        laws = []
        async with pw_db.atomic():
            await law_order.refresh(user.id, refreshing_laws)
            if form.chatdoc.is_empty:
                children = form.chatdoc.children
            else:
                children = [form.chatdoc, *form.chatdoc.children]
            for chatdoc in children:
                law = await pw_db.create(
                    Law,
                    order_id=law_order.id,
                    name=chatdoc.name,
                    chatdoc_unique=chatdoc.chatdoc_unique,
                    is_current=False,
                )
                laws.append(law)
        for law in laws:
            parse_law_file.delay(law.id)
        return [law]

    laws = []
    exists_laws_hash = [law.hash for law in law_order.laws]
    try:
        async with pw_db.atomic():
            file_ext = os.path.splitext(file.filename)[-1].lower()
            if file_ext not in Law.LAW_FILE_EXTENSIONS:
                raise HTTPException(HTTP_400_BAD_REQUEST, "上传的法规文件类型不允许")
            is_pdf = file_ext == ".pdf"
            file_content = await file.read()
            file_hash = hashlib.md5(file_content).hexdigest()
            if file_hash in exists_laws_hash:
                raise HTTPException(HTTP_400_BAD_REQUEST, "上传的法规与原法规完全一致，无须更新")
            localstorage.write_file(localstorage.get_path(file_hash, parent=LAW_FILE_PARENT), file_content)
            law = await pw_db.create(
                Law,
                order_id=law_order.id,
                name=file.filename,
                hash=file_hash,
                size=file.size,
                docx=None if is_pdf else file_hash,
                pdf=file_hash if is_pdf else None,
                is_current=False,
            )
            laws.append(law)
            await law_order.refresh(user.id, refreshing_laws)
    except HTTPException as e:
        if law_order.refresh_status != LawRefreshStatus.INIT:
            draft_laws = [law for law in law_order.laws if not law.is_current]
            async with pw_db.atomic():
                for law in draft_laws:
                    law.updated_by_id = user.id
                    await law.soft_delete()
                await pw_db.update(law_order, refresh_status=LawRefreshStatus.INIT, meta={})
        raise e
    for law in laws:
        parse_law_file.delay(law.id)
    return laws


@law_router.post("/files/{file_id:int}/hash/{file_hash:str}/preprocess-callback", include_in_schema=False)
async def handler_pdfinsight_callback(
    file_id: int = Path(...),
    file_hash: str = Path(...),
    error_code: int | None = Form(None),
    file: UploadFile | None = File(None),
    pdf: UploadFile | None = File(None),
):
    law = await Law.get_by_id(file_id)
    if not law or law.hash != file_hash:
        logger.error(f"Invalid Law file preprocess callback，{error_code=}")
        raise HTTPException(HTTP_400_BAD_REQUEST)

    if not file or (not law.pdf and not pdf):
        await pw_db.update(law, status=LawStatus.PARSE_FAIL)
        logger.error(f"Invalid Law file preprocess callback，{error_code=}")
        return {}

    interdoc_content = await file.read()
    interdoc_hash = hashlib.md5(interdoc_content).hexdigest()
    localstorage.write_file(localstorage.get_path(interdoc_hash, parent=LAW_FILE_PARENT), interdoc_content)

    await pw_db.update(law, pdfinsight=interdoc_hash, status=LawStatus.PARSED)
    split_law_rules.delay(law.id)
    return {}


@law_router.get("/{rank:int}/rules", response_model=PaginateResWithScenarioIdsSchema[LawRuleDBSchema])
async def law_rules(
    form: Annotated[SearchLawRuleSchema, Query(...)],
    law_order: Annotated[
        LawOrder,
        model_by_cond_with_perm(LawOrder, LawOrder.rank, alias="rank", action="view", exclude_fields=[LawOrder.meta]),
    ],
):
    law_ids = Law.select(Law.id).where(Law.order_id == law_order.id, Law.is_current, Law.status == LawStatus.SPLIT)

    query = LawRule.select().where(LawRule.law_id.in_(law_ids))
    if keywords := clean_rule(form.keywords):
        query = query.where(LawRule.content.contains(keywords))
    if form.status is not None:
        query = query.where(LawRule.status.in_(form.status))
    if form.scenario_ids:
        query = query.where(
            fn.EXISTS(
                LawRulesScenarios.select(1).where(
                    LawRulesScenarios.scenario_id.in_(form.scenario_ids), LawRulesScenarios.rule_id == LawRule.id
                )
            )
        )
    if form.enable is not None:
        query = query.where(LawRule.enable == form.enable)
    if form.desc:
        query = query.order_by(LawRule.id.desc())
    else:
        query = query.order_by(LawRule.id.asc())
    pagination = AsyncPagination(query, form.page, form.size)
    rules = await pagination.data(LawRulesScenarios.select(), LawScenario.select(), no_marshal=True)

    rules["scenario_ids"] = await pw_db.scalars(
        LawsScenarios.select(LawsScenarios.scenario_id.distinct()).where(LawsScenarios.law_id == law_order.id)
    )
    return rules


@law_router.get("/rules/{rule_id:int}/content")
async def get_rule_content(
    rule: Annotated[
        LawRule,
        model_with_perm(LawRule, alias="rule_id", action="view", fields=(LawRule.id, LawRule.content)),
    ],
):
    return {"content": rule.content}


@law_router.put("/rules/{rule_id:int}/convert")
async def convert_rule(
    rule: Annotated[
        LawRule,
        model_with_perm(LawRule, alias="rule_id", action="view", fields=(LawRule.id, LawRule.status)),
    ],
):
    if rule.status in (LawRuleStatus.DISABLED, LawRuleStatus.CONVERTING):
        raise HTTPException(HTTP_400_BAD_REQUEST, "当前状态不允许转换规则")

    await pw_db.update(rule, status=LawRuleStatus.WAITING)
    convert_rule_task.delay(rule.id)
    return {}


@law_router.post(
    "/rule/keywords", response_model=RuleKeywordsSchema, dependencies=[Depends(check_user_permission("manage_law"))]
)
async def get_rule_keywords(rule: ExtractRuleKeywordsSchema):
    if rule.id:
        rule = await LawRule.get_by_id(rule.id)
    return await extract_rule_keywords(rule.content)


@law_router.post("/{law_id:int}/rules", response_model=LawRuleDBSchema)
async def create_rule(
    form: EditLawRule,
    user: Annotated[NewAdminUser, Depends(get_current_user)],
    law_order: Annotated[
        LawOrder,
        model_with_perm(
            LawOrder,
            Law.split_ids().order_by(Law.id.desc()).limit(1),
            LawsScenarios.select(),
            alias="law_id",
            action="update",
            exclude_fields=[LawOrder.meta],
        ),
    ],
):
    if not law_order.laws:
        raise HTTPException(HTTP_400_BAD_REQUEST, "法规文件处理中，无法新建法规明细")
    law_id = law_order.laws[0].id

    # 前置检查：规范化内容是否重复
    cleaned_content = clean_rule(form.content)
    if await LawRule.check_duplicate_content(cleaned_content, law_order.id):
        raise HTTPException(HTTP_400_BAD_REQUEST, "当前法规内容已存在，请勿重复添加")

    async with pw_db.atomic():
        scenario_ids = await pw_db.scalars(
            LawScenario.select(LawScenario.id, for_update=True).where(
                LawScenario.id.in_(set(form.scenario_ids) & {ls.scenario_id for ls in law_order.law_scenarios}),
            )
        )
        if not scenario_ids or len(scenario_ids) != len(set(form.scenario_ids)):
            raise HTTPException(HTTP_400_BAD_REQUEST, "选择的应用场景未找到")
        rule = await pw_db.create(
            LawRule,
            law_id=law_id,
            order_id=law_order.id,
            content=cleaned_content,
            prompt=form.prompt,
            keywords=form.keywords,
            match_all=form.match_all,
            updated_by_id=user.id,
        )
        for scenario_id in scenario_ids:
            await pw_db.create(
                LawRulesScenarios,
                rule_id=rule.id,
                scenario_id=scenario_id,
                updated_by_id=user.id,
                order_id=rule.order_id,
                law_id=rule.law_id,
            )
    return rule


@law_router.put("/{law_id:int}/rules/{rule_id:int}/switch", response_model=LawRuleDBSchema)
async def switch_rule(
    enable: bool,
    rule_id: int,
    user: Annotated[NewAdminUser, Depends(get_current_user)],
    law_order: Annotated[
        LawOrder,
        model_with_perm(LawOrder, Law.split_ids(), alias="law_id", action="update", exclude_fields=[LawOrder.meta]),
    ],
):
    rule = await LawRule.get_by_id(rule_id)
    if not rule or not any(law.id == rule.law_id for law in law_order.laws):
        raise HTTPException(HTTP_400_BAD_REQUEST, "未找到法规明细")
    async with pw_db.atomic():
        if enable and rule.status == LawRuleStatus.DISABLED:
            status = LawRuleStatus.INIT
        elif not enable and rule.status == LawRuleStatus.INIT:
            status = LawRuleStatus.DISABLED
        else:
            status = rule.status
        await pw_db.update(rule, updated_by_id=user.id, enable=enable, status=status)
        stmt = LawCheckPoint.update({LawCheckPoint.enable: enable, LawCheckPoint.enable_switcher_id: user.id}).where(
            LawCheckPoint.rule_id == rule_id,
            LawCheckPoint.parent_id.is_null(),
        )
        if enable:
            stmt = stmt.where(
                LawCheckPoint.review_status == RuleReviewStatus.PASS,
                ~LawCheckPoint.abandoned,
            )
        await pw_db.execute(stmt)
    return rule


@law_router.put("/{law_id:int}/rules/{rule_id:int}")
async def edit_rule(
    rule_id: int,
    form: EditLawRule,
    user: Annotated[NewAdminUser, Depends(get_current_user)],
    law_order: Annotated[
        LawOrder,
        model_with_perm(
            LawOrder,
            Law.split_ids(),
            LawsScenarios.select(),
            alias="law_id",
            action="update",
            exclude_fields=[LawOrder.meta],
        ),
    ],
):
    rule = await LawRule.get_by_id(rule_id)
    if not rule or not any(law.id == rule.law_id for law in law_order.laws):
        raise HTTPException(HTTP_400_BAD_REQUEST, "未找到法规明细")

    # 检查规范化内容是否重复
    cleaned_content = clean_rule(form.content)
    if await LawRule.check_duplicate_content(cleaned_content, rule.order_id, exclude_id=rule.id):
        raise HTTPException(HTTP_400_BAD_REQUEST, "当前法规内容已存在，请确认后重新修改")

    async with pw_db.atomic():
        scenario_ids = await pw_db.scalars(
            LawScenario.select(LawScenario.id, for_update=True).where(
                LawScenario.id.in_(set(form.scenario_ids) & {ls.scenario_id for ls in law_order.law_scenarios}),
            )
        )
        if not scenario_ids or len(scenario_ids) != len(set(form.scenario_ids)):
            raise HTTPException(HTTP_400_BAD_REQUEST, "选择的应用场景未找到")
        exists = await pw_db.execute(LawRulesScenarios.select().where(LawRulesScenarios.rule_id == rule.id))
        for rule_scenario in exists:
            if rule_scenario.scenario_id in scenario_ids:
                scenario_ids.remove(rule_scenario.scenario_id)
                continue
            await pw_db.update(rule_scenario, deleted_utc=generate_timestamp(), updated_by_id=user.id)
        for scenario_id in scenario_ids:
            await pw_db.create(
                LawRulesScenarios,
                rule_id=rule.id,
                scenario_id=scenario_id,
                updated_by_id=user.id,
                order_id=rule.order_id,
                law_id=rule.law_id,
            )
        extra = {"status": LawRuleStatus.WAITING} if form.update_check_points else {}
        await pw_db.update(
            rule,
            content=cleaned_content,
            prompt=form.prompt,
            keywords=form.keywords,
            match_all=form.match_all,
            **extra,
        )
    if form.update_check_points:
        convert_rule_task.delay(rule.id, abandoned_reason="原始法规被修改")
    return {}


@law_router.get("/rules/{rule_id:int}/contract")
async def get_rule_contract(
    chatdoc_unique: str,
    law_rule: Annotated[
        LawRule,
        model_with_perm(
            LawRule,
            (LawRulesScenarios.select(), LawRule),
            (LawScenario.select(), LawRulesScenarios),
            alias="rule_id",
            action="view",
        ),
    ],
):
    try:
        contents = await extract_contract_contents(chatdoc_unique, law_rule)
        return {"contents": "\n".join(contents)}
    except HTTPStatusError:
        raise
    except Exception as e:
        logger.exception(f"提取合同原文失败: {e}")
        raise HTTPException(HTTP_400_BAD_REQUEST, f"提取合同原文失败: {str(e)}") from e


@law_router.delete("/{law_id:int}/rules/{rule_id:int}")
async def delete_rule(
    rule_id: int,
    user: Annotated[NewAdminUser, Depends(get_current_user)],
    law_order: Annotated[
        LawOrder,
        model_with_perm(
            LawOrder,
            Law.split_ids(),
            LawsScenarios.select(),
            alias="law_id",
            action="update",
            exclude_fields=[LawOrder.meta],
        ),
    ],
):
    rule = await LawRule.get_by_id(rule_id)
    if not rule:
        return {}
    if not any(law.id == rule.law_id for law in law_order.laws):
        raise HTTPException(HTTP_400_BAD_REQUEST, "非法操作")

    async with pw_db.atomic():
        rule.updated_by_id = user.id
        await rule.soft_delete()
    return {}


@law_router.get("/{law_id:int}/diff-rules", response_model=DiffLawRuleSchema)
async def diff_law_rules(law_order: Annotated[LawOrder, model_with_perm(LawOrder, alias="law_id", action="view")]):
    if law_order.refresh_status != LawRefreshStatus.SUCCESS or not law_order.meta:
        raise HTTPException(HTTP_400_BAD_REQUEST, "法规明细数据异常，请刷新后重试")
    return law_order.meta


@law_router.put("/{law_id:int}/revert", response_model=LawOrderDBSchema)
async def revert_law(
    law_order: Annotated[
        LawOrder,
        model_with_perm(
            LawOrder,
            Law.select(),
            LawsScenarios.select(),
            LawScenario.select(),
            alias="law_id",
            action="update",
            exclude_fields=[LawOrder.meta],
        ),
    ],
    user: Annotated[NewAdminUser, Depends(get_current_user)],
):
    draft_laws = [law for law in law_order.laws if not law.is_current]
    async with pw_db.atomic():
        for law in draft_laws:
            law.updated_by_id = user.id
            await law.soft_delete()
        await pw_db.update(law_order, refresh_status=LawRefreshStatus.INIT, meta={})
    law_order.laws = [law for law in law_order.laws if law.is_current]
    return law_order


@law_router.post("/{law_id:int}/apply", response_model=LawOrderDBSchema)
async def apply_law(
    form: ApplyLawRulesSchema,
    law_order: Annotated[
        LawOrder,
        model_with_perm(
            LawOrder,
            Law.select(),
            LawsScenarios.select(),
            LawScenario.select(),
            alias="law_id",
            action="update",
        ),
    ],
    user: Annotated[NewAdminUser, Depends(get_current_user)],
):
    pairs = [*law_order.meta.get("equal_pairs", []), *form.pairs]
    rules = await pw_db.prefetch(
        LawRule.select().where(
            LawRule.law_id.in_([law.id for law in law_order.laws]),
            LawRule.id.in_([part for pair in pairs for part in pair]),
        ),
        LawRulesScenarios.select(),
        (LawCheckPoint.select().where(LawCheckPoint.parent_id.is_null(), ~LawCheckPoint.abandoned), LawRule),
        (LawCPsScenarios.select(), LawCheckPoint),
        *LawCheckPoint.children_with_scenario()[:-1],
    )
    rule_map = {rule.id: rule for rule in rules}
    async with pw_db.atomic():
        rules_scenarios = []
        check_points = []
        cp_idx = 0
        cp_scenario_map = {}
        cp_draft_map = {}
        cp_draft_scenarios = []
        for left, right in pairs:
            left = rule_map.get(left)
            right = rule_map.get(right)
            if not left or not right:
                raise HTTPException(HTTP_400_BAD_REQUEST, "法规明细有变更，无法更新")
            await pw_db.update(right, enable=left.enable, status=left.status, updated_by_id=user.id)
            for rule_scenario in left.rule_scenarios:
                rules_scenarios.append(
                    {
                        "rule_id": right.id,
                        "scenario_id": rule_scenario.scenario_id,
                        "order_id": right.order_id,
                        "law_id": right.law_id,
                    }
                )
            for cp in left.check_points:
                check_points.append(cp.cp_dict(new_rule=right))
                cp_scenario_map[cp_idx] = [cp_scenario.scenario_id for cp_scenario in cp.cp_scenarios]
                if cp.draft:
                    cp_draft_map[cp_idx] = cp.draft.cp_dict(new_rule=right)
                    cp_draft_scenarios.append([cp_scenario.scenario_id for cp_scenario in cp.draft.cp_scenarios])
                cp_idx += 1
        await LawRulesScenarios.bulk_insert(rules_scenarios)
        cp_ids = list(await LawCheckPoint.bulk_insert(check_points, iter_ids=True))
        cp_scenarios = [
            {"cp_id": cp_ids[_idx], "scenario_id": _id} for _idx, ids in cp_scenario_map.items() for _id in ids
        ]
        await LawCPsScenarios.bulk_insert(cp_scenarios)

        draft_check_points = [_data | {"parent_id": cp_ids[_idx]} for _idx, _data in cp_draft_map.items()]
        draft_ids = list(await LawCheckPoint.bulk_insert(draft_check_points, iter_ids=True))
        draft_scenarios = [
            {"cp_id": cp_id, "scenario_id": _id} for cp_id, ids in zip(draft_ids, cp_draft_scenarios) for _id in ids
        ]
        await LawCPsScenarios.bulk_insert(draft_scenarios)
        law_name = law_order.name
        for law in law_order.laws:
            if law.is_current:
                await law.soft_delete()
            else:
                law_name = law.filename
                await pw_db.update(law, is_current=True)
        if len(law_order.scenarios) == 1:
            scenario_id = law_order.scenarios[0].id
            rule_laws = await pw_db.execute(
                LawRule.select(LawRule.id, LawRule.law_id)
                .join(
                    LawRulesScenarios,
                    JOIN.LEFT_OUTER,
                    on=(LawRulesScenarios.rule_id == LawRule.id),
                    include_deleted=True,
                )
                .where(
                    LawRule.order_id == law_order.id,
                    LawRulesScenarios.id.is_null(),
                )
                .tuples()
            )
            if rule_laws:
                await LawRulesScenarios.bulk_insert(
                    [
                        {
                            "rule_id": rule_id,
                            "scenario_id": scenario_id,
                            "order_id": law_order.id,
                            "law_id": law_id,
                        }
                        for rule_id, law_id in rule_laws
                    ]
                )
        await pw_db.update(
            law_order, name=law_name, refresh_status=LawRefreshStatus.INIT, meta={}, updated_by_id=user.id
        )

    law_order.laws = [law for law in law_order.laws if law.deleted_utc == 0]
    return law_order


@law_router.put("/rules/{rule_id:int}/checkpoint")
async def analysis_rule_template_checkpoint(
    rule_id: int,
    form: ExtractRuleKeywordsSchema,
    user: Annotated[NewAdminUser, Depends(check_any_permissions("customer_rule_participate", "customer_rule_review"))],
):
    rule = await LawRule.get_by_id(
        rule_id, [LawRulesScenarios.select(), LawScenario.select(), (LawOrder.select(), LawRule)]
    )
    rule.content = form.content
    area = await analysis_rule_focus_area(rule, limit=True)
    if area:
        for focus_point in area.focus_area:
            res = await split_rule_check_point(area, focus_point)
            if res:
                res: RuleCheckPointLLMS = res[0]
                return res.row_data(rule)
    raise HTTPException(HTTP_400_BAD_REQUEST, "智能分析失败")


@law_router.post("/{law_id:int}/rules/convert")
async def convert_rules(
    status: Annotated[
        list[Literal[LawRuleStatus.INIT, LawRuleStatus.CONVERTED, LawRuleStatus.CONVERT_FAILED]],
        Body(embed=True, min_length=1, description="sub of LawRuleStatus Enum"),
    ],
    law_order: Annotated[
        LawOrder,
        model_with_perm(LawOrder, Law.split_ids(), alias="law_id", action="update", exclude_fields=[LawOrder.meta]),
    ],
):
    law_ids = [law.id for law in law_order.laws]
    rule_ids = await pw_db.scalars(
        LawRule.update({LawRule.status: LawRuleStatus.WAITING})
        .where(LawRule.law_id.in_(law_ids), LawRule.status.in_(status), LawRule.enable)
        .returning(LawRule.id)
    )
    for rule_id in rule_ids:
        convert_rule_task.delay(rule_id)
    return {"count": len(rule_ids)}


@law_router.get("/check-points", response_model=LawCheckPointPaginateResSchema)
async def law_check_points(
    form: Annotated[SearchLawCheckPointSchema, Query(...)],
    user: Annotated[NewAdminUser, Depends(check_any_permissions("customer_rule_participate", "customer_rule_review"))],
):
    Draft = LawCheckPoint.alias()  # noqa
    cond = LawCheckPoint.parent_id.is_null()
    if form.order_ids:
        cond &= LawCheckPoint.order_id.in_(form.order_ids)
    if form.law_name:
        order_ids = LawOrder.select(LawOrder.id).where(LawOrder.name.contains(form.law_name))
        cond &= LawCheckPoint.order_id.in_(order_ids)
    if form.abandoned is not None:
        cond &= LawCheckPoint.abandoned == form.abandoned
    if form.review_status:
        if form.review_status == RuleReviewStatus.NOT_REVIEWED:
            status = [RuleReviewStatus.NOT_REVIEWED, RuleReviewStatus.DEL_NOT_REVIEWED]
        elif form.review_status == RuleReviewStatus.NOT_PASS:
            status = [RuleReviewStatus.NOT_PASS, RuleReviewStatus.DEL_NOT_PASS]
        else:
            status = [RuleReviewStatus.PASS]  # 未使用

        cond &= (Draft.review_status.is_null() & LawCheckPoint.review_status.in_(status)) | Draft.review_status.in_(
            status
        )
    if form.parent_name:
        cond &= fn.COALESCE(LawCheckPoint.alias_name, LawCheckPoint.name).contains(form.parent_name)
    elif form.name:
        cond &= peewee.Case(
            None,
            ((Draft.displaying(Draft), fn.COALESCE(Draft.alias_name, Draft.name)),),
            fn.COALESCE(LawCheckPoint.alias_name, LawCheckPoint.name),
        ).contains(form.name)
    if form.is_consistency is not None:
        cond &= peewee.Case(None, ((Draft.displaying(Draft), Draft.check_method),), LawCheckPoint.check_method).is_null(
            form.is_consistency
        )
    if form.parent_rule_content:
        cond &= LawCheckPoint.rule_content.contains(form.parent_rule_content)
    elif form.rule_content:
        cond &= peewee.Case(
            None, ((Draft.displaying(Draft), Draft.rule_content),), LawCheckPoint.rule_content
        ).contains(form.rule_content)
    if form.scenario_ids:
        # 草稿没有场景 表示 草稿场景和父级一样, 审核通过时不用处理场景
        cond &= fn.EXISTS(
            LawCPsScenarios.select(1).where(
                LawCPsScenarios.scenario_id.in_(form.scenario_ids),
                LawCPsScenarios.cp_id
                == peewee.Case(
                    None,
                    (
                        (
                            Draft.displaying(Draft)
                            & fn.EXISTS(LawCPsScenarios.select(1).where(LawCPsScenarios.cp_id == Draft.id)),
                            Draft.id,
                        ),
                    ),
                    LawCheckPoint.id,
                ),
            )
        )

    query = (
        LawCheckPoint.select(LawCheckPoint)
        .join(
            Draft,
            JOIN.LEFT_OUTER,
            on=(Draft.parent_id == LawCheckPoint.id),
            include_deleted=True,
        )
        .where(cond)
        .objects()
        .order_by(LawCheckPoint.id.desc())
    )
    pagination = AsyncPagination(query, form.page, form.size)
    check_points = await pagination.data(
        LawCPsScenarios.select(),
        (LawScenario.select(), LawCPsScenarios),
        LawOrder.select(LawOrder.id, LawOrder.name, LawOrder.rank, LawOrder.is_template, include_deleted=True),
        (LawsScenarios.select(), LawOrder),
        (LawScenario.select(), LawsScenarios),
        *LawCheckPoint.children_with_scenario(),
        no_marshal=True,
    )
    all_scenario_ids = await pw_db.scalars(LawCPsScenarios.select(LawCPsScenarios.scenario_id.distinct()))
    check_points["all_scenario_ids"] = [_id for _id in all_scenario_ids if _id and _id > 0]
    check_points["user_map"] = {user.id: user.name}
    user_ids = {user_id for item in check_points["items"] for user_id in item.full_user_ids if user_id} - {user.id}
    if user_ids:
        check_points["user_map"].update(
            dict(
                await pw_db.execute(
                    NewAdminUser.select(NewAdminUser.id, NewAdminUser.name, include_deleted=True)
                    .where(NewAdminUser.id.in_(user_ids))
                    .tuples()
                )
            )
        )
    return check_points


@law_router.get("/check-points/{cp_id:int}", response_model=LawCheckPointSimpleDBSchema)
async def get_check_point(
    check_point: Annotated[
        LawCheckPoint,
        model_with_perm(LawCheckPoint, LawCheckPoint.select(), alias="cp_id", action="view"),
    ],
):
    return check_point


@law_router.get("/{law_id:int}/check-points/exists")
async def check_check_points_exists(
    law_id,
    user: Annotated[
        NewAdminUser, Depends(check_any_permissions("manage_law", "customer_rule_participate", "customer_rule_review"))
    ],
):
    query = LawCheckPoint.select(1).where(LawCheckPoint.order_id == law_id)
    exists = await pw_db.exists(query)
    return {"exists": exists}


@law_router.get("/rules/{rule_id:int}/check-points/exists-ids")
async def check_rule_check_points_exists_ids(
    rule_id,
    user: Annotated[
        NewAdminUser, Depends(check_any_permissions("manage_law", "customer_rule_participate", "customer_rule_review"))
    ],
):
    query = LawCheckPoint.select(LawCheckPoint.id).where(
        LawCheckPoint.rule_id == rule_id, LawCheckPoint.parent_id.is_null()
    )
    exists_ids = await pw_db.scalars(query)
    return {"exists_ids": exists_ids}


@law_router.get("/check-points/{cp_id:int}/switch")
async def switch_check_point(
    enable: bool,
    check_point: Annotated[
        LawCheckPoint,
        model_with_perm(LawCheckPoint, alias="cp_id", action="view"),
    ],
    user: Annotated[NewAdminUser, Depends(check_any_permissions("customer_rule_participate", "customer_rule_review"))],
):
    if enable and check_point.review_status != RuleReviewStatus.PASS:
        raise HTTPException(HTTP_400_BAD_REQUEST, "无法启用未审核通过的大模型规则")
    if enable and check_point.abandoned:
        raise HTTPException(HTTP_400_BAD_REQUEST, "无法启用废弃的大模型规则")
    await pw_db.update(check_point, enable=enable, enable_switcher_id=user.id)
    return check_point


@law_router.put(
    "/check-points/{cp_id:int}", dependencies=[Depends(pw_transaction)], response_model=LawCheckPointSimpleDBSchema
)
async def update_check_point(
    form: EditLawCheckPointSchema,
    check_point: Annotated[
        LawCheckPoint,
        model_with_perm(
            LawCheckPoint,
            (LawCPsScenarios.select(), LawCheckPoint),
            (LawScenario.select(), LawCPsScenarios),
            *LawCheckPoint.children_with_scenario(),
            alias="cp_id",
            action="update",
            for_update=True,
        ),
    ],
    user: Annotated[NewAdminUser, Depends(check_any_permissions("customer_rule_participate"))],
):
    if check_point.abandoned:
        raise HTTPException(HTTP_400_BAD_REQUEST, "无法编辑已经废弃的大模型规则")
    if (check_point.draft or check_point).review_status == RuleReviewStatus.DEL_NOT_REVIEWED:
        raise HTTPException(HTTP_400_BAD_REQUEST, "无法编辑删除审核中的大模型规则")
    if form.scenario_ids:
        full_ids = set(
            await pw_db.scalars(
                LawsScenarios.select(LawsScenarios.scenario_id).where(LawsScenarios.law_id == check_point.order_id)
            )
        )
        if not form.scenario_ids.issubset(full_ids):
            raise HTTPException(HTTP_400_BAD_REQUEST, "请选择对应的法规场景")
    if draft := check_point.draft:
        if draft.review_status == RuleReviewStatus.NOT_REVIEWED and draft.updated_by_id != user.id:
            raise HTTPException(HTTP_400_BAD_REQUEST, "无法编辑待审核的大模型规则")
        await draft.update_draft(form, user)
        return check_point

    await check_point.create_draft(form, user)
    return check_point


@law_router.put("/check-points/save-all")
async def update_check_points(
    form: SaveAllLawCheckPointSchema,
    user: Annotated[NewAdminUser, Depends(check_any_permissions("customer_rule_participate"))],
):
    conflict_ids = []
    async with pw_db.atomic():
        check_points = await pw_db.prefetch(
            LawCheckPoint.select(for_update=True).where(LawCheckPoint.id.in_([item.id for item in form.check_points])),
            LawOrder.select(),
            LawsScenarios.select(),
            *LawCheckPoint.children_with_scenario(),
        )
        check_points_map = {check_point.id: check_point for check_point in check_points}

        for item in form.check_points:
            check_point = check_points_map[item.id]
            if (
                check_point.abandoned
                or (check_point.draft or check_point).review_status == RuleReviewStatus.DEL_NOT_REVIEWED
            ):
                conflict_ids.append(item.id)
                continue
            if item.scenario_ids and not item.scenario_ids.issubset(
                {law_scenario.scenario_id for law_scenario in check_point.order.law_scenarios}
            ):
                conflict_ids.append(item.id)
                continue
            if draft := check_point.draft:
                if draft.updated_by_id == user.id:
                    await draft.update_draft(item, user)
                else:
                    conflict_ids.append(item.id)
                continue

            await check_point.create_draft(item, user)

    return {"conflict_ids": conflict_ids}


@law_router.put("/check-points/{cp_id:int}/del", dependencies=[Depends(pw_transaction)])
async def start_check_point_del(
    check_point: Annotated[
        LawCheckPoint,
        model_with_perm(LawCheckPoint, LawCheckPoint.select(), alias="cp_id", action="update", for_update=True),
    ],
    user: Annotated[NewAdminUser, Depends(check_any_permissions("customer_rule_participate", "customer_rule_review"))],
):
    if check_point.abandoned or (check_point.draft or check_point).review_status == RuleReviewStatus.DEL_NOT_REVIEWED:
        return {}
    if not check_point.draft and check_point.enable and check_point.review_status == RuleReviewStatus.PASS:
        form = EditLawCheckPointSchema.model_validate(check_point, from_attributes=True)
        draft = await check_point.create_draft(form, user, review_status=RuleReviewStatus.DEL_NOT_REVIEWED)
        return {"draft": draft}
    await pw_db.update(
        check_point.draft or check_point, review_status=RuleReviewStatus.DEL_NOT_REVIEWED, updated_by_id=user.id
    )
    return {}


@law_router.delete("/check-points/{cp_id:int}", dependencies=[Depends(pw_transaction)])
async def delete_check_point(
    check_point: Annotated[
        LawCheckPoint,
        model_with_perm(LawCheckPoint, alias="cp_id", action="view"),
    ],
    user: Annotated[NewAdminUser, Depends(check_any_permissions("customer_rule_participate", "customer_rule_review"))],
):
    if not check_point.abandoned:
        raise HTTPException(HTTP_400_BAD_REQUEST, "只允许删除已经废弃的大模型规则")
    async with pw_db.atomic():
        await check_point.soft_delete()

    return {}


@law_router.put(
    "/check-points/{cp_id:int}/review",
    dependencies=[Depends(pw_transaction)],
    response_model=LawCheckPointSimpleDBSchema,
)
async def review_check_point(
    form: LawCheckPointReviewSchema,
    check_point: Annotated[
        LawCheckPoint,
        model_with_perm(
            LawCheckPoint,
            (LawCPsScenarios.select(), LawCheckPoint),
            (LawScenario.select(), LawCPsScenarios),
            *LawCheckPoint.children_with_scenario(),
            alias="cp_id",
            action="view",
            for_update=True,
        ),
    ],
    user: Annotated[NewAdminUser, Depends(check_any_permissions("customer_rule_review"))],
):
    ins = check_point.draft or check_point
    if ins.review_status not in (RuleReviewStatus.NOT_REVIEWED, RuleReviewStatus.DEL_NOT_REVIEWED):
        raise HTTPException(HTTP_400_BAD_REQUEST, "规则已审核，请勿重复操作")
    if ins.updated_by_id == user.id:
        raise HTTPException(HTTP_400_BAD_REQUEST, "不允许审核自己更新的规则")
    if check_point.abandoned:
        raise HTTPException(HTTP_400_BAD_REQUEST, "不允许审核废弃的规则")

    ins.meta["review_reason"] = form.review_reason
    if form.review_status != RuleReviewStatus.PASS:
        if not form.review_reason:
            raise HTTPException(HTTP_400_BAD_REQUEST, "审核不通过时，请填写原因")
        await pw_db.update(ins, review_status=form.review_status, reviewer_id=user.id, meta=ins.meta)
        return check_point

    if approved := check_point.draft:
        # 草稿转正
        await pw_db.delete(check_point)
        if check_point.draft.cp_scenarios:
            await pw_db.execute(LawCPsScenarios.delete().where(LawCPsScenarios.cp_id == check_point.id))
            await pw_db.execute(
                LawCPsScenarios.update({LawCPsScenarios.cp_id: check_point.id}).where(
                    LawCPsScenarios.cp_id == check_point.draft.id
                )
            )
        # 不能用`pw_db.update`修改id, 因为where中的id也被改了
        await pw_db.execute(
            LawCheckPoint.update(
                {
                    LawCheckPoint.id: ins.parent_id,
                    LawCheckPoint.meta: ins.meta,
                    LawCheckPoint.enable: check_point.enable,
                    LawCheckPoint.review_status: form.review_status,
                    LawCheckPoint.reviewer_id: user.id,
                    LawCheckPoint.parent_id: None,
                }
            ).where(LawCheckPoint.id == ins.id)
        )
        ins.id = ins.parent_id
        ins.parent_id = None
        check_point = ins

    if ins.review_status == RuleReviewStatus.NOT_REVIEWED:
        if not approved:
            await pw_db.update(ins, review_status=form.review_status, reviewer_id=user.id, meta=ins.meta)
        if not ins.enable:
            await pw_db.update(ins, enable=True, enable_switcher_id=user.id)
        res = LawCheckPointSimpleDBSchema.model_validate(check_point)
        logger.info(f"{user.id=} approved {check_point.id=} data:\ncpl={res.model_dump_json()}")
        return res

    await pw_db.update(
        ins,
        review_status=form.review_status,
        reviewer_id=user.id,
        meta=ins.meta,
        abandoned=True,
        abandoned_reason="废弃请求同意",
    )
    return check_point


@law_router.put("/check-points/alias")
async def set_check_points_alias(
    form: LawCheckPointsAliasSchema,
    user: Annotated[NewAdminUser, Depends(check_any_permissions("customer_rule_participate", "customer_rule_review"))],
):
    if form.alias_name and form.cp_ids:
        await pw_db.execute(
            LawCheckPoint.update(
                {
                    LawCheckPoint.alias_name: form.alias_name,
                    LawCheckPoint.alias_by_id: user.id,
                    LawCheckPoint.updated_utc: generate_timestamp(),
                }
            ).where(LawCheckPoint.id.in_(form.cp_ids) | LawCheckPoint.parent_id.in_(form.cp_ids))
        )

    return {}


@law_router.post(
    "/check-points/{cp_id:int}/contract-analysis",
    response_model=ContractComplianceCheckPointWithRectsLLMS | LawJudgeLLMResultSchema,
)
async def analyze_contract_with_check_point(
    form: AnalysisLawCheckPointSchema,
    check_point: Annotated[
        LawCheckPoint,
        model_with_perm(
            LawCheckPoint,
            LawRule.select(),
            (LawOrder.select(), LawCheckPoint),
            alias="cp_id",
            action="view",
        ),
    ],
):
    law_rule = check_point.rule
    if check_point.abandoned or isinstance(law_rule, int):
        raise HTTPException(400, f"审核规则（审核ID{check_point.id}）已废弃，已自动跳过测试")

    try:
        form._id = check_point.id
        form.name = check_point.name

        if form.check_method is None:
            reader = await get_file_reader(None, form.chatdoc_unique)
            if form.snippet:
                contract_rects: ContractRects = [(form.snippet, [{0: [(111, 111, 222, 222)]}])]
            else:
                contract_rects = None
            result = await judge_check_point_template(form, check_point.order.name, reader, contract_rects)
            return result

        if form.snippet:
            contents = {form.snippet: [{0: [[-1, -1, -1, -1]]}]}
        else:
            contents = await extract_contract_contents(form.chatdoc_unique, law_rule)
        if not contents:
            raise HTTPException(HTTP_400_BAD_REQUEST, "提取片段内容不包含任何关键词，请调整关键词后再尝试")
        contents, rects = map(list, zip(*contents.items()))
        ret = await check_contract_compliance([form], contents, check_point.order.name)
        item = ret.check_points[0]

        contract_rects = [(contents[0], rects[0])]
        return ContractComplianceCheckPointWithRectsLLMS(
            **item.model_dump(exclude={"id"}), contract_rects=contract_rects
        )
    except (HTTPException, HTTPStatusError):
        raise
    except Exception as e:
        logger.exception(f"合同分析失败: {e}")
        raise HTTPException(HTTP_400_BAD_REQUEST, f"合同分析失败: {str(e)}") from e


@law_router.get("/rules/{rule_id:int}/contract-analysis", response_model=ContractComplianceResultLLMS)
async def analyze_contract_with_rule(
    chatdoc_unique: str,
    law_rule: Annotated[
        LawRule,
        model_with_perm(
            LawRule,
            (LawCheckPoint.select(), LawRule),
            (LawOrder.select(), LawRule),
            (LawRulesScenarios.select(), LawRule),
            (LawScenario.select(), LawRulesScenarios),
            alias="rule_id",
            action="view",
        ),
    ],
):
    try:
        contents = await extract_contract_contents(chatdoc_unique, law_rule)
        return await check_contract_compliance(law_rule.check_points, contents, law_rule.order.name)
    except HTTPStatusError:
        raise
    except Exception as e:
        logger.exception(f"法规条款合同分析失败: {e}")
        raise HTTPException(HTTP_400_BAD_REQUEST, f"法规条款合同分析失败: {str(e)}") from e


if DEBUG_WEBIF:
    import zipfile
    from io import BytesIO

    from speedy.pai_response import file_response

    from remarkable.routers.schemas.debug import DebugLawSchema

    @debug_route.get("/laws/{rank:int}/debug-data", dependencies=[Depends(check_user_permission("manage_law"))])
    async def debug_law_data(rank):
        laws = await pw_db.prefetch(
            LawOrder.select().where(LawOrder.rank == rank),
            LawsScenarios.select(),
            LawScenario.select(),
            Law.select().order_by(Law.id.asc()),
            LawRule.select().order_by(LawRule.id.asc()),
            LawRulesScenarios.select(),
            (LawScenario.select(), LawRulesScenarios),
            (LawCheckPoint.select().where(LawCheckPoint.parent_id.is_null()), LawRule),
            (LawCPsScenarios.select(), LawCheckPoint),
            (LawScenario.select(), LawCPsScenarios),
            *LawCheckPoint.children_with_scenario(),
        )

        law_order = laws[0]

        zip_buffer = BytesIO()
        with zipfile.ZipFile(zip_buffer, "w", compression=zipfile.ZIP_DEFLATED) as zip_file:
            zip_file.writestr("law.json", DebugLawSchema.model_validate(law_order).model_dump_json())
            for law in law_order.laws:
                if law.pdfinsight:
                    zip_file.write(law.pdfinsight_path(), law.pdfinsight)
                elif law.chatdoc_unique:
                    pass
                else:
                    zip_file.write(law.file_path(), law.hash)
        return file_response(
            content=zip_buffer,
            media_type="application/octet-stream",
            headers={"Content-Disposition": f'attachment; filename="law_{rank}.zip"'},
            allow_etag=False,
        )

    @debug_route.post("/laws/files/{file_id:int}/reparse", dependencies=[Depends(check_user_permission("manage_law"))])
    async def reparse_law_file(file_id):
        parse_law_file.delay(file_id)
        return {}

    @debug_route.post("/laws/files/{file_id:int}/split", dependencies=[Depends(check_user_permission("manage_law"))])
    async def resplit_law_file(file_id):
        async with pw_db.atomic():
            rules = await pw_db.prefetch(LawRule.select().where(LawRule.law_id == file_id), LawRulesScenarios.select())
            for rule in rules:
                await rule.soft_delete()
        split_law_rules.delay(file_id)
        return {}

    @debug_route.post(
        "/laws/rules/{rule_id:int}/tun",
        dependencies=[Depends(check_user_permission("manage_law"))],
        response_model=TuningLawRuleResLLMS,
    )
    async def tune_law_rule(rule_id):
        rule = await LawRule.get_by_id(rule_id, [LawRulesScenarios.select(), LawScenario.select(), LawOrder.select()])
        area = await analysis_rule_focus_area(rule)

        check_points = []
        if area:
            for focus_point in area.focus_area:
                res = await split_rule_check_point(area, focus_point)
                check_points.extend(res)
        # await LawCheckPoint.bulk_insert([cp.row_data(rule) for cp in check_points])

        return {"area": area, "check_points": check_points}
