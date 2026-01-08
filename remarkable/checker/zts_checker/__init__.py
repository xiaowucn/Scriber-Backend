import logging

from remarkable.answer.common import is_empty_answer
from remarkable.answer.reader import AnswerReader
from remarkable.checker.answers import AnswerManager
from remarkable.checker.base_inspector import InspectContext
from remarkable.checker.default_checker import Inspector as DefaultInspector
from remarkable.checker.zts_checker.schema_checker import check_schema
from remarkable.common.constants import ZTS_DOC_TYPES_ANNUAL, ZTS_DOC_TYPES_SEMI, AIStatus, RuleType, ZTSProjectStatus
from remarkable.db import pw_db
from remarkable.plugins.zts.service import ZTSFileService, ZTSProjectService
from remarkable.pw_models.audit_rule import NewAuditResult
from remarkable.pw_models.model import NewFileProject
from remarkable.pw_models.question import NewQuestion
from remarkable.service.answer import get_master_question_answer

logger = logging.getLogger(__name__)


class Inspector(DefaultInspector):
    def __init__(self, file, mold, question):
        super().__init__(file, mold, question)
        self.managers = {}
        self.answer_readers = {}
        self.doc_types = set()

    @property
    def inspect_name(self):
        return "zts-checker"

    async def ready_to_check(self):
        files = await ZTSFileService.get_files_by_project_id(self.file.pid)
        file_ids = [file["id"] for file in files]
        questions = await pw_db.execute(NewQuestion.select().where(NewQuestion.fid.in_(file_ids)))
        for question in questions:
            answer, mold = await get_master_question_answer(question)
            if is_empty_answer(answer, "userAnswer"):
                logger.info(f"Answer not ready yet, {question.fid}")
                if question.ai_status == AIStatus.FINISH.value:
                    await NewFileProject.update_by_pk(self.file.pid, status=ZTSProjectStatus.FAILED.value)
                    await ZTSProjectService.push_inspect_result(
                        self.file.pid, {}, status=ZTSProjectStatus.FAILED.value, msg="部分文档的答案缺失"
                    )
                return False
        return True

    async def build_context(self):
        managers = {}
        files = await ZTSFileService.get_files_by_project_id(self.file.pid)
        for file in files:
            question = await pw_db.first(NewQuestion.select().where(NewQuestion.fid == file["id"]))
            answer, mold = await get_master_question_answer(question)
            manager = AnswerManager(question, None, mold, answer)
            managers[file["doc_type"]] = manager

        return InspectContext(managers=managers, using_preset_answer=False)

    async def prepare_data(self, context: InspectContext):
        self.context = context
        # 同项目下的file都有answer时才能开始审核
        file_ids = []
        files = await ZTSFileService.get_files_by_project_id(self.file.pid)
        for file in files:
            manager = context.managers[file["doc_type"]]
            answer = manager.answer
            if is_empty_answer(answer, "userAnswer"):
                logger.info(f"Answer not ready yet, {file['id']}")
                return

            file_ids.append(file["id"])
            answer_reader = AnswerReader(manager.answer)
            self.doc_types.add(file["doc_type"])
            self.managers[file["doc_type"]] = manager
            self.answer_readers[file["doc_type"]] = answer_reader

        await pw_db.execute(
            NewAuditResult.delete().where(
                NewAuditResult.fid.in_(file_ids), NewAuditResult.answer_type == self.answer_type
            )
        )

        if self.doc_types not in (ZTS_DOC_TYPES_ANNUAL, ZTS_DOC_TYPES_SEMI):
            raise Exception("invalid doc_type")

    async def run_check(self, **kwargs):
        labels = kwargs["labels"]
        inspect_fields = []

        results = []
        for result_item in check_schema(
            self.file,
            self.mold,
            self.managers,
            self.reader,
            labels,
            inspect_fields,
            self.doc_types,
            self.answer_readers,
        ):
            results.append(
                NewAuditResult(
                    name=result_item.name,
                    related_name=result_item.related_name,
                    is_compliance_ai=result_item.is_compliance_real,
                    is_compliance=result_item.is_compliance_real,
                    rule_id=None,
                    is_builtin=True,
                    qid=None,
                    rule_type=getattr(result_item, "rule_type", None) or RuleType.SCHEMA.value,
                    reasons=result_item.reasons,
                    tip_content=None,
                    fid=self.file.id,
                    is_compliance_tip=False,
                    is_noncompliance_tip=False,
                    schema_id=self.mold.id,
                    schema_results=result_item.schema_results,
                    order_key=None,
                    label=result_item.label,
                    contract_content=result_item.contract_content,
                    answer_type=self.answer_type,
                )
            )

        return results

    async def save_results(self, results, labels, is_preset_answer: bool = False):
        try:
            async with pw_db.atomic():
                await super()._save_results(results, labels, is_preset_answer=is_preset_answer)
                data = await ZTSProjectService.get_inspect_conclusion(results)
                await ZTSProjectService.update_inspect_info(self.file.pid, data)
                await NewFileProject.update_by_pk(self.file.pid, status=ZTSProjectStatus.DONE.value)

            await ZTSProjectService.push_inspect_result(self.file.pid, data, status=ZTSProjectStatus.DONE.value)
        except Exception as exp:
            await NewFileProject.update_by_pk(self.file.pid, status=ZTSProjectStatus.FAILED.value)
            await ZTSProjectService.push_inspect_result(
                self.file.pid, {}, status=ZTSProjectStatus.FAILED.value, msg="审核时发生异常"
            )
            raise exp
