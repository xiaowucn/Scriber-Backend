import logging

from remarkable.answer.common import is_empty_answer
from remarkable.answer.reader import AnswerReader
from remarkable.converter import AnswerWorkShop
from remarkable.db import pw_db
from remarkable.models.ecitic_dcm import DcmFileInfo
from remarkable.plugins.ecitic_dcm.service import DcmBondOrderService

logger = logging.getLogger(__name__)


class EciticDcmAnswerWorkShop(AnswerWorkShop):
    async def work(self):
        logger.info("EciticDcmAnswerWorkShop.work()")
        if is_empty_answer(self.answer, "userAnswer"):
            logger.info(f"{self.file.name}的答案为空")
            return

        investor_name = None
        answer_reader = AnswerReader(self.answer)
        if nodes := answer_reader.find_nodes(["机构名称"]):
            investor_name = list(nodes)[0].data.plain_text

        logger.info(f"{self.file.name}的机构名称为{investor_name}")
        if not investor_name:
            return

        async with pw_db.atomic():
            await pw_db.execute(
                DcmFileInfo.update(investor_name=investor_name).where(DcmFileInfo.file_id == self.file.id)
            )
            await DcmBondOrderService.update_relationship_by_investor_name(
                self.file.id, self.question.id, investor_name
            )
