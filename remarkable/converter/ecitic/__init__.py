import logging

from remarkable.answer.common import is_empty_answer
from remarkable.common.constants import EciticTgTaskType, EciticTgTriggerType
from remarkable.config import get_config
from remarkable.converter import AnswerWorkShop
from remarkable.db import pw_db
from remarkable.models.ecitic import EciticFile, EciticFileInfo, EciticPush, EciticTemplate
from remarkable.models.new_user import ADMIN
from remarkable.plugins.ecitic.common import ecitic_tg_diff, ecitic_tg_push, get_push_data
from remarkable.pw_models.model import NewFileProject
from remarkable.pw_models.question import NewQuestion
from remarkable.service.answer import get_master_question_answer
from remarkable.service.new_question import NewQuestionService

logger = logging.getLogger(__name__)


class EciticTGAnswerWorkShop(AnswerWorkShop):
    async def work(self):
        logger.info("EciticTGAnswerWorkShop.work()")
        file_info = await EciticFileInfo.get_by_file_id(self.file.id)
        if not file_info or not file_info.version:
            logger.info(f"{self.file.name}版本号为空")
            return
        if is_empty_answer(self.question.preset_answer, "userAnswer"):
            if get_config("citics.email_url"):
                from remarkable.plugins.ecitic.tg_task import send_fail_email_to_ecitic_tg

                await send_fail_email_to_ecitic_tg(self.file, "模型提取答案为空")
                logger.info(f"{self.file.name}模型提取答案为空")
            return

        # 单文档自动推送
        if await self.is_auto_push(self.file):
            logger.info(f"{self.file.id}单文档自动推送")
            file, push_data_list = await get_push_data(self.question.id, only_auto_push=True)
            project = await NewFileProject.find_by_id(file.pid)
            try:
                await ecitic_tg_push(
                    project.name, file, file.uid, push_data_list, EciticTgTaskType.SINGLE, EciticTgTriggerType.AUTO
                )
            except Exception as exp:
                logger.exception(exp)

        # 自动比对推送
        await self.compare_and_push(file_info)

    async def compare_and_push(self, file_info):
        query = (
            EciticFile.select()
            .join(EciticFileInfo)
            .where(
                EciticFile.id != self.file.id,
                EciticFile.pid == self.file.pid,
                EciticFileInfo.version == file_info.version,
            )
        )
        files = await pw_db.execute(query)
        for file in files:
            logger.info(f"{self.file.id}自动比对({file.id})")
            # 一个pdf, 一个word
            if not (self.file.is_word and file.is_pdf or self.file.is_pdf and file.is_word):
                continue

            pdf_file = self.file if self.file.is_pdf else file
            if not await self.is_auto_push(pdf_file):
                logger.info(f"pdf_file{pdf_file.id}未配置自动推送")
                continue

            question = await pw_db.first(
                NewQuestion.select().where(NewQuestion.fid == file.id, NewQuestion.mold == self.question.mold)
            )
            if not question:
                logger.info(f"{file.id}未找到question")
                continue

            master_answer, _ = await get_master_question_answer(question)
            if is_empty_answer(master_answer, "userAnswer"):
                logger.info(f"Answer not ready yet, {file.id=}")
                continue

            compare_record, compare_result, _ = await ecitic_tg_diff(
                self.question.id, question.id, uid=ADMIN.id, trigger_type=EciticTgTriggerType.AUTO
            )
            # 完全一致
            if compare_result.is_diff:
                logger.info(f"{self.file.id}比对{file.id}的结果存在差异")
                continue

            logger.info(f"{self.file.id}自动比对({file.id})推送")

            _, push_data_list = await get_push_data(compare_record_id=compare_record.id, only_auto_push=True)
            project = await NewFileProject.find_by_id(pdf_file.pid)
            try:
                await ecitic_tg_push(
                    project.name,
                    pdf_file,
                    pdf_file.uid,
                    push_data_list,
                    EciticTgTaskType.COMPARE,
                    EciticTgTriggerType.AUTO,
                    compare_record.id,
                )
            except Exception as exp:
                logger.exception(exp)

    @staticmethod
    async def is_auto_push(file):
        """
        文档关联的模板是否配置了自动推送
        :param file:
        :return:
        """
        file_info = await EciticFileInfo.get_by_file_id(file.id)

        cond = EciticTemplate.id.in_(file_info.templates)
        cond &= EciticPush.enabled
        query = EciticPush.select().join(EciticTemplate, on=(EciticPush.template == EciticTemplate.id)).where(cond)
        return await pw_db.exists(query)


if __name__ == "__main__":
    import asyncio

    asyncio.run(NewQuestionService.post_pipe(11717, 2272, None))
