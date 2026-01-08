# CYC: skip-file
import logging
import traceback
from collections import Counter, defaultdict
from functools import partial

from sqlalchemy import and_

from remarkable import config
from remarkable.checker.helpers import audit_file_rules, audit_file_rules_by_mold
from remarkable.common.constants import AuditStatusEnum, ComplianceStatus
from remarkable.common.enums import AuditAnswerType, ClientName
from remarkable.common.exceptions import NoFileError
from remarkable.config import get_config
from remarkable.db import peewee_transaction_wrapper, pw_db
from remarkable.models.new_file import NewFile
from remarkable.pw_models.audit_rule import NewAuditResult
from remarkable.pw_models.model import NewAuditStatus, NewFileMeta, NewMold, NewRuleResult
from remarkable.pw_models.question import NewQuestion
from remarkable.rule.common import autodoc
from remarkable.rule.inspector import AnswerInspectorFactory, LegacyInspector
from remarkable.schema.cgs.rules import AuditStatusType
from remarkable.service.new_file import NewFileMetaService
from remarkable.service.rpc import wrap_gen_rule_result

logger = logging.getLogger(__name__)


class RuleService:
    @staticmethod
    @autodoc
    async def inspect_rules(_file: NewFile) -> dict[str, list[NewRuleResult]] | None:
        if not _file or not _file.molds:
            return

        # 清空旧的审核结果
        await pw_db.execute(NewRuleResult.delete().where(NewRuleResult.fid == _file.id))

        meta = await NewFileMetaService.get_file_metas(_file.id)
        inspector = None
        questions = {}
        for mold_id in sorted(_file.molds):
            mold = await NewMold.find_by_id(mold_id)
            question = await NewQuestion.find_by_fid_mid(_file.id, mold_id)
            if not inspector:
                inspector = await AnswerInspectorFactory.create(
                    mold,
                    doc=_file,
                    question=question,
                    meta=meta,
                )
            questions[mold.name] = question
        if not inspector:
            return

        if get_config("prompter.mode") == "rpc":
            inspector.gen_rule_result = partial(wrap_gen_rule_result, inspector)

        if isinstance(inspector, LegacyInspector):
            rule_results = inspector.check()
            rows = [rule_result["misc"] for rule_result in rule_results]
            if rows:
                await NewRuleResult.bulk_insert(rows)
            inspector.question.preset_answer["rule_result"] = {"items": rule_results}
            params = {"preset_answer": inspector.question.preset_answer}
            await inspector.question.update_(**params)
        else:  # inspector is instance of Inspector
            inspector.questions = questions
            rule_results = inspector.check()
            await pw_db.execute(NewRuleResult.delete().where(NewRuleResult.fid == _file.id))
            rows = [i for lst in rule_results.values() for i in lst]
            if rows:
                await NewRuleResult.bulk_insert(rows)
            else:
                logger.warning(f"Got empty rows, please check your inspector: {inspector.__class__}")
            await _file.update_()
            await pw_db.execute(NewFileMeta.update().where(NewFileMeta.file_id == _file.id))
        return rule_results

    @staticmethod
    def is_compliance(ai_status, audit_status):
        """优先按人工审核统计, 人工未审核时, 取AI判定结果"""
        return (
            audit_status == AuditStatusEnum.UNAUDITED
            and ai_status in (ComplianceStatus.COMPLIANCE, ComplianceStatus.DIS_IN_TIME)
        ) or audit_status in (AuditStatusEnum.COMPLIANCE, AuditStatusEnum.DIS_IN_TIME)

    @classmethod
    async def calc_audit_summary(cls, file_id):
        compliance_count = non_compliance_count = total_count = 0
        for item in (
            await NewRuleResult.select(NewRuleResult.result, NewRuleResult.audit_status)
            .where(and_(NewRuleResult.fid == file_id, NewRuleResult.second_rule == "AI判定"))
            .order_by(NewRuleResult.id)
        ):
            total_count += 1
            if cls.is_compliance(item.ai_status, item.audit_status):
                compliance_count += 1
            else:
                non_compliance_count += 1
        return {
            "compliance_count": compliance_count,
            "non_compliance_count": non_compliance_count,
            "total_count": total_count,
        }

    @classmethod
    @peewee_transaction_wrapper
    async def gen_rule_summary(cls, report_year: int):
        """按年份统计合规/不合规公司"""

        total_count = pw_db.count(
            NewFileMeta.select(NewFileMeta.stock_code).where(NewFileMeta.report_year == report_year)
        )
        ret = []
        summary = defaultdict(Counter)
        rule_results = await pw_db.execute(
            NewRuleResult.select()
            .join(NewFileMeta, on=(NewFileMeta.file_id == NewRuleResult.fid))
            .where(and_(NewFileMeta.report_year == report_year, NewRuleResult.second_rule == "AI判定"))
        )
        for rule_result in rule_results:
            if cls.is_compliance(rule_result.result, rule_result.audit_status):
                summary[rule_result.rule].update(["compliance_count"])
            else:
                summary[rule_result.rule].update(["non_compliance_count"])

        for rule, counter in summary.items():
            ret.append(
                {
                    "rule_name": rule,
                    "compliance_count": counter["compliance_count"],
                    "non_compliance_count": counter["non_compliance_count"],
                    "total_count": total_count,
                }
            )
        return ret


async def do_inspect_rule_pipe(file_id, audit_preset_answer=False):
    if config.get_config("inspector.package_name"):  # 有新的审核模块,需要在事务之外执行的逻辑
        conditions = [NewAuditResult.fid == file_id, NewAuditResult.answer_type == AuditAnswerType.final_answer]
        await pw_db.execute(NewAuditResult.delete().where(*conditions))
        await pw_db.create(
            NewAuditStatus,
            fid=file_id,
            status=AuditStatusType.PROCESS.value,
            answer_type=AuditAnswerType.final_answer,
        )
    await inspect_rule_pipe(file_id, audit_preset_answer=audit_preset_answer)


@peewee_transaction_wrapper
async def inspect_rule_pipe(file_id, audit_preset_answer=False):
    # 新的审核模块,位于 remarkable.checker
    if inspector_package := config.get_config("inspector.package_name"):
        logger.info(f"{inspector_package=}, inspect file: {file_id}")
        if ClientName.cmfchina == get_config("client.name"):
            await audit_file_rules_by_mold(int(file_id), audit_preset_answer=audit_preset_answer)
        else:
            await audit_file_rules(int(file_id), audit_preset_answer=audit_preset_answer)

    if not (config.get_config("web.inspect_rules")):
        logger.warning("web.inspect_rules is False, skip inspect!")
        return

    _file = await NewFile.find_by_id(file_id)
    if not _file:
        raise NoFileError(f"File not found, id: {file_id}", logger=logger)

    logger.info(f"Start inspecting file: {file_id}")
    try:
        await RuleService.inspect_rules(_file)
    except Exception:
        traceback.print_exc()
        logger.error(f"error in inspect rule for file {file_id}")

    if config.get_config("web.answer_convert"):
        from remarkable.service.answer import set_convert_answer

        questions = await NewQuestion.find_by_fid(_file.id)
        for question in questions:
            await set_convert_answer(question.id)
