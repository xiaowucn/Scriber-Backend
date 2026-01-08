import logging

from remarkable.common.constants import AIStatus
from remarkable.common.enums import NafmiiTaskType
from remarkable.db import pw_db
from remarkable.hooks.base import InsightFinishHook, PredictFinishHook
from remarkable.models.nafmii import NafmiiFileInfo, NafmiiSystem, TaskFlag
from remarkable.models.new_file import NewFile
from remarkable.plugins.nafmii.services import TaskManager
from remarkable.plugins.nafmii.tasks import run_nafmii_task
from remarkable.pw_models.question import NewQuestion

logger = logging.getLogger(__name__)


class NafmiiPredictHook(PredictFinishHook):
    name = "nafmii"

    async def __call__(self):
        file = await NewFile.get_by_id(
            self.question.file.id, prefetch_queries=[NafmiiFileInfo.select(), NafmiiSystem.select()]
        )
        file_info = file.file_info[0]
        if file_info.flag != TaskFlag.only_push:  # 只重新推送的时候, 不需要重跑比对
            async with TaskManager(file, {NafmiiTaskType.T001}) as task:
                await task.run()

        run_nafmii_task.delay(self.question.file.id)


class NafmiiInsightHook(InsightFinishHook):
    name = "nafmii"

    async def __call__(self):
        file_info: NafmiiFileInfo = await pw_db.first(NafmiiFileInfo.select().where(NafmiiFileInfo.file == self.file))
        task_types = file_info.task_types
        logger.info(f"call nafmii insight hook for file {self.file.id}  task_types: {task_types}")
        if task_types is None:
            task_types = [NafmiiTaskType.T001]
            logger.warning(f"no task_types for file {self.file.id} set default task_types: {task_types}")
            await NafmiiFileInfo.create(file=self.file, task_types=task_types, keywords=[])

        if file_info.flag != TaskFlag.only_push:  # 只重新推送的时候, 不需要重跑敏感词和关键词识别
            async with TaskManager(self.file, {NafmiiTaskType.T002, NafmiiTaskType.T003}) as task:
                await task.run()

        if NafmiiTaskType.T001 not in task_types:
            await pw_db.execute(NewQuestion.delete().where(NewQuestion.fid == self.file.id))
            await NewQuestion.create(fid=self.file.id, ai_status=AIStatus.FINISH)

            run_nafmii_task.delay(self.file.id)
