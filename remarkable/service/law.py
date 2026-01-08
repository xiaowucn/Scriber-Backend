import asyncio
import logging
from collections import defaultdict

from httpx import HTTPStatusError

from remarkable.common.async_redis_cache import redis_acache_with_lock
from remarkable.common.constants import RuleType
from remarkable.common.storage import localstorage
from remarkable.db import pw_db
from remarkable.models.new_file import NewFile
from remarkable.pdfinsight.reader import PdfinsightReader
from remarkable.plugins.cgs.scripts.cgs_demo import generate_timestamp
from remarkable.pw_models.law import LawCheckPoint, LawOrder, LawRule, LawRulesScenarios, LawScenario, LawsScenarios
from remarkable.pw_models.law_judge import JudgeStatusEnum, LawJudgeResult
from remarkable.routers.schemas import ContractRects
from remarkable.routers.schemas.law import ContractComplianceCheckPointWithRectsLLMS
from remarkable.routers.schemas.law_template import LawTemplatesSchema
from remarkable.service.law_chatdoc import ask_chatdoc, get_answer_detail_trace
from remarkable.service.law_prompt import (
    build_contract_analysis_question,
    check_contract_compliance,
    determine_rules_scenarios,
)

logger = logging.getLogger(__name__)


async def determine_rule_scenarios(rule):
    scenario_map = dict(
        await pw_db.execute(
            LawScenario.select(LawScenario.name, LawScenario.id)
            .where(
                LawScenario.id.in_(
                    LawsScenarios.select(LawsScenarios.scenario_id).where(LawsScenarios.law_id == rule.order_id)
                )
            )
            .tuples()
        )
    )
    scenarios = scenario_map
    if len(scenario_map) > 1:
        try:
            scenarios = (await determine_rules_scenarios([rule.content], set(scenario_map)))[0]
        except Exception as e:
            logger.exception(e)

    await LawRulesScenarios.bulk_insert(
        [
            {
                "rule_id": rule.id,
                "scenario_id": scenario_map[scenario],
                "order_id": rule.order_id,
                "law_id": rule.law_id,
            }
            for scenario in scenarios
        ]
    )


@redis_acache_with_lock(expire_seconds=7200, lock_timeout=300)
async def extract_contract_contents(chatdoc_unique: str, law_rule: LawRule) -> dict[str, list[dict]]:
    question = build_contract_analysis_question(law_rule)
    data = await ask_chatdoc(chatdoc_unique, question)

    answers = law_rule.filter_by_keywords([{"text": data["answer"]}])
    if not answers:
        return {}

    answer = answers[0]["text"]
    rects = defaultdict(list)

    detail_data = await get_answer_detail_trace(data["id"], data["answer"], [1, len(data["answer"])])

    if detail_data["status"] == "traced":
        for ele in detail_data["data"]:
            for page, recs in ele["boxes"].items():
                rects[page].extend(recs)
    return {answer: [rects]}


async def get_file_reader(file_id, chatdoc_unique=None):
    if chatdoc_unique:
        file = await NewFile.get_by_cond(NewFile.chatdoc_unique == chatdoc_unique)
    elif file_id:
        file = await NewFile.get_by_id(file_id)
    else:
        file = None
    if not file:
        return None
    return await asyncio.to_thread(PdfinsightReader, localstorage.mount(file.pdfinsight_path()))


async def judge_file_law_templates(file_id, cp_ids):
    if not cp_ids:
        return

    reader = await get_file_reader(file_id)
    check_points = await pw_db.prefetch(
        LawCheckPoint.select(include_deleted=True).where(LawCheckPoint.id.in_(cp_ids)), LawOrder.select()
    )
    for cp in check_points:
        result = await LawJudgeResult.get_by_cond((LawJudgeResult.file_id == file_id) & (LawJudgeResult.cp_id == cp.id))
        if result:
            if cp.check_method is not None:
                await pw_db.update(result, judge_status=JudgeStatusEnum.FAILED)
                return

            await pw_db.update(result, judge_status=JudgeStatusEnum.DOING)
            data = await judge_check_point_template(cp, cp.order.name, reader)
            await pw_db.update(result, **data)


async def judge_file_law_rule(file_id, chatdoc_unique, rule_id, cp_ids):
    law_rule = await LawRule.get_by_id(rule_id, LawOrder.select())
    try:
        contents = await extract_contract_contents(chatdoc_unique, law_rule)
        contents, rects = map(list, zip(*contents.items()))
    except Exception as e:
        if isinstance(e, HTTPStatusError):
            logger.error(f"Call {e.request.url} {e.response.status_code} response: {e.response.text}")
        else:
            logger.exception(e)
        await pw_db.execute(
            LawJudgeResult.update(
                {
                    LawJudgeResult.judge_status: JudgeStatusEnum.FAILED,
                    LawJudgeResult.updated_utc: generate_timestamp(),
                    LawJudgeResult.is_compliance: False,
                    LawJudgeResult.is_compliance_ai: True,
                    LawJudgeResult.origin_contents: [law_rule.order.name, law_rule.content],
                }
            ).where(LawJudgeResult.file_id == file_id, LawJudgeResult.cp_id.in_(cp_ids))
        )
        return

    check_points = await pw_db.execute(LawCheckPoint.select(include_deleted=True).where(LawCheckPoint.id.in_(cp_ids)))
    for cp in check_points:
        result = await LawJudgeResult.get_by_cond((LawJudgeResult.file_id == file_id) & (LawJudgeResult.cp_id == cp.id))
        if result:
            await pw_db.update(result, judge_status=JudgeStatusEnum.DOING)

            data = await judge_check_point(cp, law_rule.order.name, contents, rects)
            await pw_db.update(result, **data)


async def judge_check_point_template(
    check_point, order_name, reader: PdfinsightReader, contract_rects: ContractRects = None
):
    name = check_point.alias_name or check_point.name
    try:
        assert check_point.check_method is None
        templates = LawTemplatesSchema.model_validate(check_point.templates)

        is_compliance, reasons, suggestion, schema_results = await templates.compare(reader, name, contract_rects)

        is_compliance_ai = is_compliance
        judge_status = JudgeStatusEnum.SUCCESS
    except Exception as e:
        if isinstance(e, HTTPStatusError):
            logger.error(f"Call {e.request.url} {e.response.status_code} response: {e.response.text}")
        else:
            logger.exception(e)
        is_compliance = bool()
        is_compliance_ai = not is_compliance
        reasons = []
        suggestion = ""
        schema_results = []
        judge_status = JudgeStatusEnum.FAILED

    return {
        "name": name,
        "is_compliance": is_compliance,
        "is_compliance_ai": is_compliance_ai,
        "is_compliance_user": None,
        "is_edited": False,
        "is_compliance_tip": False,
        "is_noncompliance_tip": False,
        "tip_content": None,
        "order_key": LawJudgeResult.get_first_position(schema_results, None),
        "origin_contents": [order_name, check_point.rule_content],
        "contract_content": None,
        "reasons": reasons,
        "related_name": None,
        "rule_type": RuleType.TEMPLATE.value if check_point.check_method is None else RuleType.SCHEMA.value,
        "schema_results": schema_results,
        "suggestion": suggestion,
        "suggestion_ai": suggestion,
        "suggestion_user": None,
        "user_reason": None,
        "judge_status": judge_status,
    }


async def judge_check_point(check_point, order_name, contents, rects):
    try:
        assert check_point.check_method is not None
        ret = await check_contract_compliance([check_point], contents, order_name)
        item = ret.check_points[0]

        contract_rects = [(contents[0], rects[0])]
        llm_result = ContractComplianceCheckPointWithRectsLLMS(
            **item.model_dump(exclude={"id"}), contract_rects=contract_rects
        )
        if llm_result.compliance_status == "合规":
            is_compliance = True
        elif llm_result.compliance_status == "不合规":
            is_compliance = False
        else:
            is_compliance = None
        is_compliance_ai = is_compliance
        judge_status = JudgeStatusEnum.SUCCESS
    except Exception as e:
        if isinstance(e, HTTPStatusError):
            logger.error(f"Call {e.request.url} {e.response.status_code} response: {e.response.text}")
        else:
            logger.exception(e)
        llm_result = ContractComplianceCheckPointWithRectsLLMS(
            check_type="", judgment_basis="", compliance_status="", suggestion="", contract_rects=[]
        )
        is_compliance = bool()
        is_compliance_ai = not is_compliance
        judge_status = JudgeStatusEnum.FAILED

    name = check_point.alias_name or check_point.name
    schema_results = []
    for text, _rects in llm_result.contract_rects:
        for _rect in _rects:
            if not _rect:
                continue
            page = min(int(p) for p in _rect)
            schema_results.append({"name": name, "page": str(page), "text": text, "outlines": _rect})
    return {
        "name": name,
        "is_compliance": is_compliance,
        "is_compliance_ai": is_compliance_ai,
        "is_compliance_user": None,
        "is_edited": False,
        "is_compliance_tip": False,
        "is_noncompliance_tip": False,
        "tip_content": None,
        "order_key": LawJudgeResult.get_first_position(schema_results, None),
        "origin_contents": [order_name, check_point.rule_content],
        "contract_content": None,
        "reasons": [{"reason_text": llm_result.judgment_basis}],
        "related_name": None,
        "rule_type": RuleType.TEMPLATE.value if check_point.check_method is None else RuleType.SCHEMA.value,
        "schema_results": schema_results,
        "suggestion": llm_result.suggestion,
        "suggestion_ai": llm_result.suggestion,
        "suggestion_user": None,
        "user_reason": None,
        "judge_status": judge_status,
    }
