import re
from collections import Counter, OrderedDict

from remarkable.pdfinsight.text_util import clear_syl_title
from remarkable.plugins.predict.common import find_nearest_syl
from remarkable.predictor.predict import CharResult, ResultOfPredictor

from .model_base import PredictModelBase


class SimilarSection(PredictModelBase):
    """
    通过标注内容提取对应类似章节下的全部内容
    模型：统计标注内容对应的章节标题
    model 示例:
    {
        "技术风险": Counter({
            "技术风险": 10,
            "技术升级迭代风险": 6,
            ...
        }),
        ...
    }

    """

    model_intro = {
        "doc": """
        提取对应类似章节下的全部内容
        """,
        "name": "相似章节",
        "hide": True,
    }

    def __init__(self, *args, **kwargs):
        super(SimilarSection, self).__init__(*args, **kwargs)
        self.base_on_crude_element = False

    @classmethod
    def model_template(cls):
        template = {}
        default_model_template = cls.default_model_template()
        default_model_template.update(template)
        return default_model_template

    def train(self, dataset, **kwargs):
        model = {}
        dataset = dataset or []
        # print('----------', self.columns, self.config, len(dataset), self.leaf)
        for item in dataset:
            for col in self.columns:
                leaves = item.answer.get(col, {}).values() if not self.leaf else [item.answer]
                for leaf in leaves:
                    if leaf.data is None:
                        continue
                    _features = self.extract_feature(item, leaf.data)
                    model.setdefault(col, Counter()).update(_features)
                    # print(col, model[col])
        self.model = model

    def predict(self, elements, **kwargs):
        answer = {}
        for col in self.columns:
            _model = self.model.get(col)
            common_titles = [
                col,
            ]
            if _model:
                common_titles.extend([title for title, cnt in _model.most_common()])
            # print('=====', col, common_titles)
            aim_syls = OrderedDict()
            for clear_title in common_titles:
                syls = self.pdfinsight.find_sylls_by_pattern(
                    [
                        re.compile(clear_title),
                    ]
                )
                if not syls:
                    continue
                aim_syls.setdefault(tuple(syls[0]["range"]), syls[0])
            # print('*****', [(x, y) for x, y in aim_syls.items()])
            chars_l = []
            for _range, aim_syl in aim_syls.items():
                # 跳过子级标题
                from_id, to_id = _range
                if any(from_id >= s["range"][0] and to_id <= s["range"][1] for r, s in aim_syls.items() if r != _range):
                    continue
                # print('****', aim_syl['title'])
                chars = []
                for idx in range(*aim_syl["range"]):
                    elt_typ, elt = self.pdfinsight.find_element_by_index(idx)
                    if not elt:
                        continue
                    if elt_typ == "PARAGRAPH":
                        chars.extend(elt["chars"])
                    elif elt_typ == "TABLE":
                        for cell in elt["cells"].values():
                            chars.extend(cell["chars"])
                if chars:
                    chars_l.append(chars)

            if chars_l:
                data = []
                for chars in chars_l:
                    data.append(CharResult(chars))
                answer[col] = ResultOfPredictor(data, score=1)
        return [
            answer,
        ]

    @staticmethod
    def extract_feature(anser_item, answer):
        sylls = anser_item.data.get("syllabuses", [])
        syllabus_dict = {syl["element"]: syl for syl in sylls}
        features = Counter()
        for answer_data in answer["data"]:
            if not answer_data["elements"]:
                continue
            if answer_data["elements"][0] not in syllabus_dict:
                # 第一个标注元素块不是标题，即只标注了内容，需要向上找章节标题
                aim_syl = find_nearest_syl(answer_data["elements"][0], sylls)
            else:
                # 第一个标注元素块是标题
                syl = syllabus_dict[answer_data["elements"][0]]
                if all(eid in range(*syl["range"]) for eid in answer_data["elements"]):
                    # 标注了"标题+内容"
                    aim_syl = syl
                else:
                    # 只标注了"内容"，需要向上找章节标题
                    aim_syl = find_nearest_syl(answer_data["elements"][0], sylls)
            if aim_syl:
                clear_syl = clear_syl_title(aim_syl["title"])
                # print('*****', clear_syl, aim_syl)
                features.update(
                    [
                        clear_syl,
                    ]
                )
        return features
