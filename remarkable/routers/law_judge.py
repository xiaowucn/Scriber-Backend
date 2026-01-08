import logging
from collections import defaultdict
from http.client import HTTPException

from fastapi import APIRouter, Depends
from starlette.status import HTTP_400_BAD_REQUEST

from remarkable.db import pw_db
from remarkable.dependencies import check_user_permission
from remarkable.models.new_file import NewFile
from remarkable.models.new_user import NewAdminUser
from remarkable.plugins.cgs.scripts.cgs_demo import generate_timestamp
from remarkable.pw_models.law import LawCheckPoint, LawOrder, LawRule
from remarkable.pw_models.law_judge import JudgeStatusEnum, LawJudgeResult, LawJudgeResultRecord
from remarkable.routers import DEBUG_WEBIF, debug_route
from remarkable.routers.schemas import ContractRects
from remarkable.routers.schemas.law_judge import (
    LawJudgeResultDBSchema,
    LawJudgeResultRecordsDBSchema,
    LawJudgeResultWithNameDBSchema,
    SetLawJudgeResultsSchema,
)
from remarkable.service.law import (
    extract_contract_contents,
    get_file_reader,
    judge_check_point,
    judge_check_point_template,
)
from remarkable.worker.tasks import judge_file

judge_router = APIRouter(prefix="", tags=["judge"])
logger = logging.getLogger(__name__)


@judge_router.get("/files/{file_id:int}/judge-results", response_model=list[LawJudgeResultWithNameDBSchema])
async def get_judge_results(file_id: int, user: NewAdminUser = Depends(check_user_permission("inspect"))):
    results = await LawJudgeResult.get_judge_results(file_id)
    return results


@judge_router.put("/files/{file_id:int}/judge-results")
async def set_judge_results(
    file_id: int, schema: SetLawJudgeResultsSchema, user: NewAdminUser = Depends(check_user_permission("inspect"))
):
    if not schema.results:
        raise HTTPException(HTTP_400_BAD_REQUEST, "审核结果未做任何修改，已保存答案")

    await LawJudgeResult.batch_update_user_result(schema.results, user)
    return {}


@judge_router.post("/files/{file_id:int}/judge-results/{result_id:int}", response_model=LawJudgeResultDBSchema)
async def update_judge_results(
    file_id: int,
    result_id: int,
    schema: ContractRects | None = None,
    user: NewAdminUser = Depends(check_user_permission("inspect")),
):
    result = await LawJudgeResult.get_by_id(result_id)
    check_point = await LawCheckPoint.get_by_id(result.cp_id, LawOrder.select())
    async with pw_db.atomic():
        await pw_db.execute(LawJudgeResultRecord.delete().where(LawJudgeResultRecord.result_id == result.id))
        await pw_db.update(result, judge_status=JudgeStatusEnum.DOING)

    if check_point.check_method is not None:
        if schema is None:
            law_rule = await LawRule.get_by_id(result.rule_id)
            if check_point.id < 0:
                law_rule.content = check_point.rule_content
                law_rule.updated_utc = generate_timestamp()
            file = await NewFile.get_by_id(file_id)
            contents = await extract_contract_contents(file.chatdoc_unique, law_rule)
            if not contents:
                await pw_db.update(result, judge_status=JudgeStatusEnum.FAILED)
                return result
            contents, rects = map(list, zip(*contents.items()))
        else:
            _contents, _rects = map(list, zip(*schema))
            contents = ["\n".join(_contents)]
            merged_rects = defaultdict(list)
            for pages_boxes in _rects:
                for page_boxes in pages_boxes:
                    for page, boxes in page_boxes.items():
                        merged_rects[page].extend(boxes)
            rects = [[merged_rects]]

        data = await judge_check_point(check_point, check_point.order.name, contents, rects)
    else:
        reader = await get_file_reader(file_id)
        data = await judge_check_point_template(check_point, check_point.order.name, reader, schema)

    await pw_db.update(result, **data)
    return result


@judge_router.get("/judge-results/{result_id:int}/records", response_model=list[LawJudgeResultRecordsDBSchema])
async def get_judge_result_records(result_id: int, user: NewAdminUser = Depends(check_user_permission("inspect"))):
    records = await pw_db.prefetch(
        LawJudgeResultRecord.select()
        .filter(LawJudgeResultRecord.result_id == result_id)
        .order_by(LawJudgeResultRecord.id.desc()),
        NewAdminUser.select(NewAdminUser.id, NewAdminUser.name, include_deleted=True),
    )
    return records


if DEBUG_WEBIF:

    @debug_route.post(
        "/files/{file_id:int}/judge",
        dependencies=[Depends(check_user_permission("inspect"))],
        description="同步运行大模型审核,和文件相同场景的大模型规则越多越慢",
    )
    async def debug_judge(file_id: int):
        count = await judge_file(file_id)
        return {"count": count}
