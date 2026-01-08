from remarkable.plugins.hkex.common import Schema
from remarkable.plugins.zjh.zjh_answer_formatter import ZJHAnswerFormatter
from remarkable.predictor.predict import ConvertPredictor


class ZJHExportPredictor(ConvertPredictor):
    """
    证监会导出答案预测类
    """

    def __init__(self, *args, **kwargs):
        super(ZJHExportPredictor, self).__init__(*args, **kwargs)
        self.schema_obj = Schema(self.mold.data)
        self.anno_answer = kwargs.get("anno_answer")
        self.formatter = ZJHAnswerFormatter(self.reader)
        self.export_answer = self.formatter.format(self.anno_answer)
