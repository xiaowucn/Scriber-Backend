import logging

from remarkable.hooks.base import InsightFinishHook

logger = logging.getLogger(__name__)


class GJZQInsightFinishHook(InsightFinishHook):
    name = "gjzq"

    async def __call__(self):
        from remarkable.service.cmfchina.filed_file_service import CmfFiledFileService

        await CmfFiledFileService.filed_file(self.file)
