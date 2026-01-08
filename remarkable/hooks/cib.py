from remarkable.hooks.base import InsightFinishHook

# 兴业银行POC
# https://gitpd.paodingai.com/cheftin/docs_scriber/-/issues/4710


class CibInsightHook(InsightFinishHook):
    name = "cib"
    """
    1. 使用大模型对 文档分类 （关联schema）, 规则兜底

    2. 对文档进行提取
        2.1 使用大模型提取
        2.2 规则兜底

    3. 审核
    """

    async def __call__(self):
        # reader = PdfinsightReader(localstorage.mount(self.file.pdfinsight_path()))
        # await self.file.update_(source="")
        # make_question
        pass
