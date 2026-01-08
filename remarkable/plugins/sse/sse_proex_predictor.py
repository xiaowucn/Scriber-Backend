from remarkable.config import get_config
from remarkable.plugins.hkex.common import Schema
from remarkable.predictor.predict import ConvertPredictor

from ...pw_models.model import NewMold
from .sse_answer_formatter import SSEAnswerFormatter


class SSEProExPredictor(ConvertPredictor):
    """上交所导出答案预测类
    实现逻辑：
    1. 按照 `标注 schema` 进行初步定位
    2. 使用 SSEAnnoPredictor 预测 `标注 schema` 答案
    3. `标注 schema` 答案 转换为 `导出 schema` 答案
    """

    def __init__(self, *args, **kwargs):
        super(SSEProExPredictor, self).__init__(*args, **kwargs)
        self.schema_obj = Schema(self.mold.data)
        self.anno_answer = kwargs.get("anno_answer")
        self.anno_mold = kwargs.get("anno_mold")
        self.anno_crude_answer = kwargs.get("anno_crude_answer")
        self.formatter = SSEAnswerFormatter(self.reader, schema=self.schema_obj, file=self.file)
        if not self.anno_answer and self.anno_mold:
            from remarkable.plugins.predict.config.sse_anno import SSEAnnoPredictor

            anno_predictor = SSEAnnoPredictor(self.anno_mold, file=self.file, crude_answer=self.anno_crude_answer)
            self.anno_answer = anno_predictor.predict_answer()
        self.export_answer = self.formatter.format(self.anno_answer, need_page_no=False) if self.anno_answer else None

    async def get_anno_mold(self):
        convert_mapping = get_config("web.answer_convert") or {}
        anno_mold_name = None
        for source, aim in convert_mapping.items():
            if aim == self.mold.name:
                anno_mold_name = source
                break
        if not anno_mold_name:
            raise Exception("can't find source schema name for %s (in config web.answer_convert)" % self.mold.name)

        anno_mold = await NewMold.find_by_name(anno_mold_name)
        return anno_mold

    async def get_anno_crude_answer(self, anno_mold):
        from remarkable.service.prompter import predict_crude_answer_delegate

        crude_answer = await predict_crude_answer_delegate(self.file, self.qid, mold=anno_mold)
        return crude_answer
