import logging

import attr

from remarkable.checker.base_inspector import BaseInspector, InspectContext
from remarkable.checker.cgs_checker.answers import CGSAnswerManager
from remarkable.checker.cgs_checker.external_resource import AMACSource, CGSSource
from remarkable.checker.cgs_checker.rule_checker import (
    FundManagerInfoChecker,
    apply_fund_checker_result,
)
from remarkable.checker.cgs_checker.schema_checker import check_schema
from remarkable.checker.cgs_checker.template_checker import check_by_templates
from remarkable.checker.cgs_checker.util import is_skip_check
from remarkable.common.enums import AuditAnswerType
from remarkable.common.exceptions import CustomError
from remarkable.config import get_config
from remarkable.pw_models.audit_rule import NewAuditResult, NewAuditRule
from remarkable.service.answer import get_master_question_answer

logger = logging.getLogger(__name__)


class Inspector(BaseInspector):
    def __init__(self, file, mold, question):
        super().__init__(file, mold, question)
        self.manager = None
        self.context = None
        self.fund_manager_info = None
        self.company_info = None

    @property
    def inspect_name(self):
        return "cgs-checker"

    async def run_check(self, **kwargs):
        # 第一次的需求文件 https://docs.qq.com/sheet/DS0JXc1FDdG1rbG5N?tab=BB08J2
        labels = kwargs["labels"]
        inspect_fields = (kwargs.get("inspect_fields") or {}).get(self.mold.name) or []
        schema_names = kwargs.get("schema_names")

        if labels and inspect_fields:
            raise CustomError("Passing both labels and inspect_fields at the same time is invalid.")

        answer_type = (
            AuditAnswerType.preset_answer if self.context.using_preset_answer else AuditAnswerType.final_answer
        )

        results = []
        # 检查内部规则
        for result_item in check_by_templates(
            self.file,
            self.mold,
            self.manager,
            self.reader,
            labels,
            inspect_fields,
            self.fund_manager_info,
            schema_names,
        ):
            audit_result = NewAuditResult.from_inspect_result(self.manager.question.id, result_item)
            audit_result.answer_type = answer_type
            results.append(audit_result)

        for result_item in check_schema(
            self.file, self.mold, self.manager, self.reader, labels, inspect_fields, self.fund_manager_info
        ):
            audit_result = NewAuditResult.from_inspect_result(
                self.manager.question.id, result_item, is_template_rule=False
            )
            audit_result.answer_type = answer_type
            results.append(audit_result)

        # 检查配置的规则，检查依赖爬虫数据的规则
        rules = await NewAuditRule.list_reviewing_rules(
            self.mold.id, only_review_passed=get_config("feature.rule_need_review")
        )
        fund_manager_checker = FundManagerInfoChecker(self.fund_manager_info, self.company_info)
        for rule in rules:
            if is_skip_check(rule, inspect_fields, labels):
                continue

            matched, reasons, suggestion = apply_fund_checker_result(rule, self.manager, fund_manager_checker)
            schema_results = self.manager.build_schema_results(rule.schema_fields)
            audit_result = NewAuditResult(
                name=rule.name,
                is_builtin=False,
                is_compliance_ai=matched,
                is_compliance=matched,
                rule_id=rule.id,
                origin_contents=[rule.origin_content],
                suggestion=suggestion,
                suggestion_ai=suggestion,
                rule_type=rule.rule_type,
                reasons=[attr.asdict(item) for item in reasons],
                tip_content=rule.tip_content,
                fid=self.file.id,
                qid=self.manager.question.id,
                is_compliance_tip=rule.is_compliance_tip,
                is_noncompliance_tip=rule.is_noncompliance_tip,
                schema_id=self.mold.id,
                schema_results=schema_results,
                order_key=NewAuditResult.get_first_position(schema_results, None),
                label=rule.label,
                answer_type=answer_type,
            )
            results.append(audit_result)

        return results

    async def build_context(self):
        answer, mold = await get_master_question_answer(self.question)
        manager = CGSAnswerManager(self.question, self.reader, mold, answer)
        return InspectContext(managers={self.question.id: manager}, using_preset_answer=False)

    async def prepare_data(self, context: InspectContext):
        self.context = context
        manager = context.managers.get(self.question.id)
        self.manager = manager

        # 初始化爬虫返回的数据和 比对结果
        self.fund_manager_info = await AMACSource(self.manager).get()

        # 初始化客户接口返回的数据和 比对结果
        self.company_info = await CGSSource(self.manager).get()

        logging.info(f"manger results:{self.fund_manager_info}")
        logging.info(f"sda results:{self.company_info}")

    async def save_results(self, results, labels, is_preset_answer: bool = False):
        if not labels:
            await NewAuditResult.reset_results(self.file.id, self.mold.id, is_preset_answer=is_preset_answer)
            await NewAuditResult.bulk_insert([item.to_dict(exclude=[NewAuditResult.id]) for item in results])
        elif results:
            await NewAuditResult.update_results(labels, results)
