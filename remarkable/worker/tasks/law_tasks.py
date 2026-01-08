import hashlib
import logging
import os
import shutil
import tempfile
from itertools import chain, groupby

import requests
from calliper_diff.diff_data import diff_data
from utensils.hash import md5sum
from utensils.syncer import sync

from remarkable.common.exceptions import CustomError, PdfinsightError, PushError
from remarkable.common.storage import localstorage
from remarkable.config import get_config
from remarkable.db import pw_db
from remarkable.plugins.cgs.scripts.cgs_demo import generate_timestamp
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
from remarkable.routers.schemas.law import DiffLawRuleSchema
from remarkable.security import authtoken
from remarkable.service.law import determine_rule_scenarios
from remarkable.service.law_chatdoc import download_chatdoc_interdoc, download_chatdoc_origin
from remarkable.service.law_prompt import (
    analysis_rule_focus_area,
    determine_rules_scenarios,
    fill_template_check_rule,
    split_rule_check_point,
)
from remarkable.service.new_file import html2pdf
from remarkable.service.word import text2pdf
from remarkable.utils.rule_para import calc_diff_ratio, format_diff_result, generate_rules_paras
from remarkable.utils.split_law import split_interdoc
from remarkable.utils.split_law_template import split_template_interdoc
from remarkable.worker.app import app, task_log

logger = logging.getLogger(__name__)


async def parse_law_by_insight(law):
    if law.status >= LawStatus.PARSED:
        logger.info("law file parsed: {law.id=} {law.status=}")
        return

    callback_url = (
        f"{get_config('web.scheme', 'http')}://{get_config('web.domain')}/api/v2/laws/files/"
        f"{law.id}/hash/{law.hash}/preprocess-callback"
    )
    pdfinsight_api = authtoken.encode_url(
        f"{get_config('app.auth.pdfinsight.url')}/api/v1/preprocess?law_id={law.id}",
        get_config("app.auth.pdfinsight.app_id"),
        get_config("app.auth.pdfinsight.secret_key"),
    )

    post_data = {
        "app": get_config("app.app_id"),
        "app_id": get_config("app.app_id"),
        "callback": callback_url,
        "key": f"law#{law.id}#{law.hash}",
        "priority": 0,
        "title_ai": (int(get_config("app.auth.pdfinsight.title_ai", True))),
        "column": (int((get_config("app.auth.pdfinsight.column") or 0))),
        "force_ocr": 0,
        "garbled_file_handle": 0,
        "newline_mode": (get_config("app.auth.pdfinsight.newline_mode") or 0),
        "report_colorful_exception": 1,  # 传1的话在涂色流程解析异常时会回传错误信息， scriber固定传1， 不需要修改
        "as_pdf": 1,
        "as_docx": 1,
    }

    logger.info(post_data)

    file_obj = localstorage.read_file(law.parse_path())
    files = {"file": (law.parse_name(), file_obj)}
    try:
        ret = requests.post(pdfinsight_api, data=post_data, files=files, timeout=10)
    except Exception as exp:
        raise PushError("parse law request error: {}".format(exp)) from exp
    if ret.status_code != 200:
        raise CustomError("parse law error: {} \n {}".format(ret.status_code, ret.text))
    if ret.json().get("status", "") == "error":
        raise PdfinsightError(f"parse law failed: \n{ret.text}")
    await pw_db.update(law, status=LawStatus.PARSING)


async def fetch_law_from_chatdoc(law: Law):
    try:
        if law.ext in (".txt", ".html"):
            origin = await download_chatdoc_origin(law.chatdoc_unique)
            origin_hash = hashlib.md5(origin).hexdigest()
            origin_path = localstorage.get_path(origin_hash, parent=LAW_FILE_PARENT)
            localstorage.write_file(origin_path, origin)
            if law.ext == ".txt":
                with tempfile.TemporaryDirectory() as tmp_dir:
                    tmp_path = os.path.join(tmp_dir, "tmp.pdf")

                    await text2pdf(origin_path, tmp_path)
                    pdf = md5sum(tmp_path)
                    pdf_path = localstorage.get_path(pdf, parent=LAW_FILE_PARENT)
                    localstorage.create_dir(os.path.dirname(pdf_path))
                    shutil.move(tmp_path, pdf_path)
            else:
                content = await html2pdf(origin.decode("utf-8"))
                pdf = hashlib.md5(content).hexdigest()
                pdf_path = localstorage.get_path(pdf, parent=LAW_FILE_PARENT)
                localstorage.write_file(pdf_path, content)
            await pw_db.update(law, hash=origin_hash, pdf=pdf)

            await parse_law_by_insight(law)
            return

        interdoc_content = await download_chatdoc_interdoc(law.chatdoc_unique)
        interdoc_hash = hashlib.md5(interdoc_content).hexdigest()
        localstorage.write_file(localstorage.get_path(interdoc_hash, parent=LAW_FILE_PARENT), interdoc_content)

        await pw_db.update(law, pdfinsight=interdoc_hash, status=LawStatus.PARSED)
        split_law_rules.delay(law.id)
    except Exception as e:
        logger.exception(e)
        await pw_db.update(law, status=LawStatus.FETCH_FAIL)
        if not law.is_current:
            await pw_db.execute(LawOrder.refresh_err(law.order_id, "fetch error"))


@app.task
@task_log()
@sync
async def parse_law_file(law_id: int):
    law = await Law.get_by_id(law_id)
    if not law:
        logger.info(f"miss {law_id} to parse")
        return

    if law.chatdoc_unique is None:
        try:
            await parse_law_by_insight(law)
        except Exception as e:
            await pw_db.update(law, status=LawStatus.PARSE_FAIL)
            if not law.is_current:
                await pw_db.execute(LawOrder.refresh_err(law.order_id, f"parse exception: {e}"))
            raise e
        return

    await fetch_law_from_chatdoc(law)


@app.task
@task_log()
@sync
async def split_law_rules(law_id):
    law = await Law.get_by_id(
        law_id, prefetch_queries=[LawOrder.select(), LawsScenarios.select(), LawScenario.select()]
    )
    if not law or not law.pdfinsight:
        logger.info(f"miss {law_id} interdoc to split")
        return

    await pw_db.update(law, status=LawStatus.SPLITTING)
    try:
        if law.is_template:
            rules_text = split_template_interdoc(law.pdfinsight_path())
        else:
            rules_text = split_interdoc(law.pdfinsight_path())
        rules = [
            {
                "law_id": law.id,
                "order_id": law.order_id,
                "content": content,
                "match_all": False,
            }
            for content in rules_text
        ]
        scenario_map = {m.scenario.name: m.scenario.id for m in law.order.law_scenarios}
        rules_scenarios = []
        if law.is_current:
            if len(scenario_map) > 1:
                rules_scenarios = await determine_rules_scenarios(rules_text, set(scenario_map))
            if not rules_scenarios:
                rules_scenarios = [list(scenario_map)] * len(rules_text)

        async with pw_db.atomic():
            await law.lock_for_update()
            law_rules = await pw_db.execute(LawRule.select().where(LawRule.law_id == law.id))
            for rule in law_rules:
                await rule.soft_delete()

            rule_ids = list(await LawRule.bulk_insert(rules, iter_ids=True))
            if rules_scenarios:
                await LawRulesScenarios.bulk_insert(
                    [
                        {
                            "rule_id": rule_id,
                            "scenario_id": scenario_map[scenario],
                            "order_id": law.order_id,
                            "law_id": law.id,
                        }
                        for rule_id, scenarios in zip(rule_ids, rules_scenarios)
                        for scenario in set(scenarios)
                    ]
                )
            await pw_db.update(law, status=LawStatus.SPLIT)
        if not law.is_current:
            diff_law_rules_task.delay(law.order_id)
    except Exception as e:
        logger.exception(e)
        await pw_db.update(law, status=LawStatus.SPLIT_FAIL)
        if not law.is_current:
            await pw_db.execute(LawOrder.refresh_err(law.order_id, f"split exception: {e}"))


async def diff_law_rules_process(law_order_id):
    async with pw_db.atomic():
        laws_status = await pw_db.scalars(
            Law.select(Law.status, for_update=True).where(Law.order_id == law_order_id, ~Law.is_current)
        )
        if any(0 <= status < LawStatus.SPLIT for status in laws_status):
            return

    law_order = await LawOrder.get_by_id(
        law_order_id, [Law.select().order_by(Law.is_current.desc()), LawRule.select().order_by(LawRule.id)]
    )
    rules = []
    for _, laws in groupby(law_order.laws, lambda x: x.is_current):
        rules.append([rule for law in laws for rule in law.law_rules])

    para1, para2 = map(generate_rules_paras, rules)
    try:
        diff_result, _ = diff_data(
            para1,
            para2,
            {
                "ignore_header_footer": False,
                "ignore_punctuations": True,
                "include_equal": True,
                "ignore_diff_on_toc_page": False,
                "similarity_diff_offset": 0,
            },
        )
    except Exception as e:
        logger.exception("diff law rules Error")
        await pw_db.execute(LawOrder.refresh_err(law_order_id, f"diff rule Error: {e}"))
        return
    ratio = calc_diff_ratio(diff_result)
    if ratio < 80:
        await pw_db.execute(LawOrder.refresh_err(law_order_id, "ratio < 80%"))
        return

    rule_map = {rule.id: rule for rule in chain(*rules)}
    diff = [diff for part in diff_result for diff in format_diff_result(part, rule_map)]
    equal_pairs = [(item["left"][0].id, item["right"][0].id) for item in diff if item["equal"]]
    result = DiffLawRuleSchema(ratio=ratio, diff=[i for i in diff if not i["equal"]], equal_pairs=equal_pairs)

    await pw_db.update(law_order, refresh_status=LawRefreshStatus.SUCCESS, meta=result.model_dump(mode="json"))


@app.task
@task_log()
@sync
async def diff_law_rules_task(law_order_id):
    await diff_law_rules_process(law_order_id)


@app.task
@task_log()
@sync
async def convert_rule_task(rule_id: int, abandoned_reason="重新转换审核规则"):
    up_rule = await pw_db.execute(
        LawRule.update({LawRule.status: LawRuleStatus.CONVERTING}).where(
            LawRule.id == rule_id, LawRule.status == LawRuleStatus.WAITING, LawRule.deleted_utc == 0
        )
    )
    if not up_rule:
        logger.info(f"skip convert {rule_id=}")

    rule = await LawRule.get_by_id(
        rule_id, [LawRulesScenarios.select(), LawScenario.select(), (LawOrder.select(), LawRule)]
    )
    if not rule.rule_scenarios:
        await determine_rule_scenarios(rule)
    try:
        check_points = []
        if rule.order.is_template:
            cp = rule.template_cp()
            cp.update(await fill_template_check_rule(rule))
            check_points.append(cp)
        else:
            area = await analysis_rule_focus_area(rule)
            if area:
                for focus_point in area.focus_area:
                    res = await split_rule_check_point(area, focus_point)
                    for cp in res:
                        if cp.check_type == "无":
                            logger.info(cp.model_dump_json())
                            continue
                        check_points.append(cp.row_data(rule))

        assert check_points
        assert abandoned_reason
        async with pw_db.atomic():
            await pw_db.execute(
                LawCheckPoint.update(
                    {
                        LawCheckPoint.updated_utc: generate_timestamp(),
                        LawCheckPoint.abandoned: True,
                        LawCheckPoint.abandoned_reason: abandoned_reason,
                    }
                ).where(LawCheckPoint.rule_id == rule.id, ~LawCheckPoint.abandoned)
            )
            cp_ids = await LawCheckPoint.bulk_insert(check_points, iter_ids=True)
            await LawCPsScenarios.bulk_insert(
                [
                    {"cp_id": cp_id, "scenario_id": rule_scenario.scenario_id}
                    for cp_id in cp_ids
                    for rule_scenario in rule.rule_scenarios
                ]
            )
            await pw_db.update(rule, status=LawRuleStatus.CONVERTED)
    except Exception as e:
        logger.exception(e)
        await pw_db.update(rule, status=LawRuleStatus.CONVERT_FAILED)
