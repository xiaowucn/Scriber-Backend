import copy
import logging
from functools import cached_property

import attr

from remarkable.checker.base_inspector import InspectContext
from remarkable.checker.cmfchina_checker.answer import CmfChinaAnswerManager
from remarkable.checker.cmfchina_checker.server import CmfChinaInspectorServer
from remarkable.checker.default_checker import Inspector as DefaultInspector
from remarkable.checker.default_checker import get_inspect_result
from remarkable.common.storage import localstorage
from remarkable.config import get_config
from remarkable.converter import SimpleJSONConverter
from remarkable.db import pw_db
from remarkable.models.cmf_china import CmfABCompare
from remarkable.pdfinsight.reader import PdfinsightReader
from remarkable.plugins.cgs.common.utils import append_suggestion, format_suggestion
from remarkable.plugins.cgs.schemas.reasons import CustomRuleNoMatchItem, IgnoreConditionItem
from remarkable.pw_models.audit_rule import NewAuditResult, NewAuditRule
from remarkable.pw_models.model import NewAuditStatus
from remarkable.schema.cgs.rules import AuditStatusType
from remarkable.service.answer import (
    get_master_preset_answer,
    get_master_question_answer,
    get_preset_answer_by_mid_qid,
    get_question_answer_by_mid_qid,
)

logger = logging.getLogger(__name__)


class Inspector(DefaultInspector):
    @cached_property
    def reader(self):
        if self.file.is_excel:
            return None
        return PdfinsightReader(localstorage.mount(self.file.pdfinsight_path()))

    async def build_context(self):
        answer = await get_question_answer_by_mid_qid(self.mold, self.question)
        manager = CmfChinaAnswerManager(self.question, self.reader, self.mold, answer)
        return InspectContext(managers={self.question.id: manager}, using_preset_answer=False)

    async def build_context_for_preset_answer(self):
        answer = await get_preset_answer_by_mid_qid(self.mold, self.question)
        manager = CmfChinaAnswerManager(self.question, self.reader, self.mold, answer)
        return InspectContext(managers={self.question.id: manager}, using_preset_answer=True)

    async def run_check(self, **kwargs):
        labels = kwargs["labels"]

        # 外部审核
        if server_url := get_config("inspector.external_url"):
            await self.send_to_server(server_url)

        results = []
        answer_type = self.answer_type
        # 检查页面上配置的规则
        rules = await NewAuditRule.list_reviewing_rules(
            self.mold.id, only_review_passed=get_config("feature.rule_need_review")
        )

        for rule in rules:
            if labels and rule.label not in labels:
                continue
            if len(rule.schema_fields) > 1:
                # https://gitpd.paodingai.com/cheftin/docs_scriber/-/issues/7474#note_747351
                # 如果规格包含多个字段，则不审核.
                schema_results = self.manager.build_schema_results(rule.schema_fields)
                matched = None
                reasons = [IgnoreConditionItem(reason_text="规则建立不合理", matched=True)]
                suggestion = None
                results.append(
                    NewAuditResult(
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
                )
            else:
                for name in rule.schema_fields:
                    for answer in self.manager.get(name):
                        schema_results = []
                        if answer:
                            schema_results.append(
                                {"name": name, "matched": True if answer.value else False, **answer.first_result}
                            )
                        else:
                            schema_results.append({"name": name, "matched": False})

                        matched, reasons, suggestion = get_inspect_result(rule, {name: answer})
                        results.append(
                            NewAuditResult(
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
                        )

        return results

    async def send_to_server(self, server_url: str):
        data = self.gen_inspect_payload()

        # 增加ABCompare数据
        if ab_compare := await pw_db.first(
            CmfABCompare.select(CmfABCompare.url.alias("ab_url"), CmfABCompare.use_llm, CmfABCompare.prompt)
            .where(CmfABCompare.mold_id == self.mold.id)
            .dicts()
        ):
            data.update(ab_compare)

        audit_status_data = {
            "fid": self.file.id,
            "schema_id": self.mold.id,
            "status": AuditStatusType.WAITING_CALLBACK.value,
            "answer_type": self.answer_type.value,
        }
        inspector_server = CmfChinaInspectorServer(server_url)
        is_success = await inspector_server.send(data)
        if not is_success:
            audit_status_data["status"] = AuditStatusType.REMOTE_REQUEST_FAILED.value
        await pw_db.create(NewAuditStatus, **audit_status_data)
