from remarkable.common.constants import ZTSProjectStatus
from remarkable.hooks.base import InsightStartHook
from remarkable.pw_models.model import NewFileProject


class ZtsInsightStartHook(InsightStartHook):
    name = "zts"

    async def __call__(self):
        await NewFileProject.update_by_pk(self.file.pid, status=ZTSProjectStatus.DOING.value)
