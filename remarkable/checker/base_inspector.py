import logging
import time
from dataclasses import dataclass
from functools import cached_property

from remarkable.checker.answers import AnswerManager
from remarkable.common.storage import localstorage
from remarkable.config import get_config
from remarkable.pdfinsight.reader import PdfinsightReader
from remarkable.service.answer import get_master_preset_answer, get_master_question_answer

logger = logging.getLogger(__name__)


@dataclass(kw_only=True, frozen=True)
class InspectContext:
    managers: dict[int | str, AnswerManager]
    using_preset_answer: bool = False


class BaseInspector:
    """
    审核者(类似Prophet)
    控制审核的整体流程
    """

    def __init__(self, file, mold, question):
        self.file = file
        self.mold = mold
        self.question = question

    @cached_property
    def reader(self):
        return PdfinsightReader(localstorage.mount(self.file.pdfinsight_path()))

    @property
    def inspect_name(self):
        return self.__class__.__name__

    @property
    def is_auditable(self):
        audit_molds = get_config("inspector.audit_molds") or []
        if audit_molds and self.mold.name not in audit_molds:
            return False

        return True

    async def ready_to_check(self):
        return True

    async def start_check(self, context: InspectContext, **kwargs):
        if not self.is_auditable:
            logger.info(f"Mold not in audit_molds, skip run Inspector.check: {self.file.id=}, {self.mold.name=}")
            return []
        logger.info(f"Start run Inspector.check: {self.file.id=}, {self.mold.name=}")

        await self.prepare_data(context)

        start = time.time()
        result_items = await self.run_check(**kwargs)
        await self.save_results(result_items, kwargs.get("labels"), is_preset_answer=context.using_preset_answer)

        logging.info(f"run {len(result_items)} rule results.")
        logging.info(
            f"End run {self.inspect_name}: fid:{self.file.id} schema_id:{self.mold.id}. time: {time.time() - start}s"
        )
        return result_items

    async def prepare_data(self, context: InspectContext):
        raise NotImplementedError

    async def build_context(self):
        answer, mold = await get_master_question_answer(self.question)
        manager = AnswerManager(self.question, self.reader, mold, answer)
        return InspectContext(managers={self.question.id: manager}, using_preset_answer=False)

    async def build_context_for_preset_answer(self):
        answer, mold = await get_master_preset_answer(self.question)
        manager = AnswerManager(self.question, self.reader, mold, answer)
        return InspectContext(managers={self.question.id: manager}, using_preset_answer=True)

    async def run_check(self, **kwargs):
        raise NotImplementedError

    async def save_results(self, results, labels, is_preset_answer: bool = False):
        raise NotImplementedError
