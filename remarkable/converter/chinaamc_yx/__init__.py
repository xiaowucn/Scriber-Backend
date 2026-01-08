from peewee import fn

from remarkable.common.constants import AIStatus
from remarkable.converter import AnswerWorkShop
from remarkable.db import pw_db
from remarkable.models.chinaamc_yx import CompareTask
from remarkable.models.new_file import NewFile
from remarkable.pw_models.question import NewQuestion


class ChinaAmcYxAnswerWorkShop(AnswerWorkShop):
    async def work(self):
        from remarkable.plugins.chinaamc_yx.tasks import run_compare_task

        all_file_finish = ~fn.EXISTS(
            NewFile.select(1)
            .left_outer_join(
                NewQuestion,
                on=(NewQuestion.fid == NewFile.id),
            )
            .where(
                NewFile.id == fn.ANY(CompareTask.fids),
                NewQuestion.ai_status != AIStatus.FINISH,
            )
        )
        task_ids = await pw_db.scalars(
            CompareTask.select(CompareTask.id).where(
                CompareTask.started, CompareTask.fids.contains_any([self.file.id]), all_file_finish
            )
        )

        for task_id in task_ids:
            run_compare_task.delay(task_id)
