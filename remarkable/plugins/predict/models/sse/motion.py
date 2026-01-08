import re

from remarkable.common.util import clean_txt, index_in_space_string
from remarkable.plugins.predict.models.model_base import PredictModelBase
from remarkable.plugins.predict.models.partial_text_v3 import PartialTextV3
from remarkable.predictor.predict import CharResult, ResultOfPredictor

title_regs = [
    re.compile(r"(?P<dst>《.*议案》?)$"),
    re.compile(r"(?P<dst>.*议案》?)$"),
]

result_regs = [
    re.compile(
        r"(同意|赞成)\s*(?P<agree>[\d\s]+票).*(反对)\s*(?P<against>[\d\s]+票).*(弃权)\s*(?P<abstention>[\d\s]+票)"
    ),
    re.compile(
        r"(?P<agree>[\d\s]+票)\s*(同意|赞成).*(?P<against>[\d\s]+票)\s*(反对).*(?P<abstention>[\d\s]+票)\s*(弃权)"
    ),
]


class Motion(PredictModelBase):
    model_intro = {
        "doc": """
        议案名称和表决结果
        eg：
        [
            ('（一）审议通过了《1号议案》', '表决结果：同意3票，反对0票，1票弃权'),
            ('《2号议案》', '表决结果：2票赞成，2票反对，0票放弃'),
            ....
        ]
        """,
        "name": "议案模型",
        "hide": True,
    }

    @classmethod
    def model_template(cls):
        template = {}
        default_model_template = cls.default_model_template()
        default_model_template.update(template)
        return default_model_template

    def __init__(self, mold, config, **kwargs):
        self._model = {}
        super(Motion, self).__init__(mold, config, **kwargs)
        self.run_sub_predictors = False
        self.main_partial_text = PartialTextV3(mold, config, **kwargs)

    def train(self, dataset, **kwargs):
        pass

    def predict(self, elements, **kwargs):
        answers = []
        for elt in elements:
            answer = {}
            if elt["class"] != "PARAGRAPH":
                continue
            content = clean_txt(elt["text"])
            aim_chars = []
            for reg in title_regs:
                matched = reg.search(content)
                if matched:
                    start, end = matched.span()
                    aim_chars = elt["chars"][start:end]

                if aim_chars:
                    break
            if not aim_chars:
                continue
            _text = "".join([x["text"] for x in aim_chars])
            # print('---------', elt['index'], elt['text'])
            # print('****', _text)
            answer[self.columns[0]] = ResultOfPredictor([CharResult(chars=aim_chars, text=_text, elt=elt)])
            self.motion_result_in_section(elt, answer)  # 填充议案对应的表决结果
            answers.append(answer)
        return answers

    def motion_result_in_section(self, elt, answer):
        """
        填充议案对应的表决结果
        :param elt: 议案名称所在元素块
        :param answer:
        :return:
        """
        section = (elt["index"], len(self.pdfinsight.data["_index"]))  # 缺省值
        for syll in self.pdfinsight.syllabuses:
            if syll["element"] == elt["index"]:
                section = syll["range"]
                break
        # print('section', section)
        for elt_idx in range(*section):
            pairs = answer.setdefault("（四级）", [])
            etype, element = self.pdfinsight.find_element_by_index(elt_idx)
            if etype != "PARAGRAPH":
                continue
            content = clean_txt(element["text"])
            for reg in result_regs:
                matched = reg.search(content)
                if matched:
                    for _val, _key in [
                        ("同意", "agree"),
                        ("反对", "against"),
                        ("弃权", "abstention"),
                    ]:
                        pair = self.generate_result(element, matched, _key, _val)
                        pairs.append(pair)
                    break
            if pairs:
                break
        return answer

    @staticmethod
    def generate_result(element, matched, key, val):
        pair = {}
        sp_start, sp_end = index_in_space_string(element["text"], matched.span(key))
        _chars = element["chars"][sp_start:sp_end]
        _text = matched.groupdict()[key]
        pair["表决结果"] = ResultOfPredictor(data=[CharResult(chars=[])], value=val, score=1)
        pair["表决结果票数"] = ResultOfPredictor([CharResult(chars=_chars, text=_text)], score=1)

        return pair
