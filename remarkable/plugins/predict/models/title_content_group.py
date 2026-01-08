import re
from collections import Counter, OrderedDict, defaultdict, namedtuple

from remarkable.common.util import clean_txt
from remarkable.pdfinsight.text_util import clear_syl_title
from remarkable.predictor.predict import CharResult, ResultOfPredictor

from .model_base import PredictModelBase

EXT_TITLE = {
    "发行概况": r"^(本次)?发行概况$",
    "声明": r"^(发行人)?声明$",
    "重大事项提示": r"^重大事项提示$",
    "目录": r"^目录$",
}


class TitleContentGroup(PredictModelBase):
    model_intro = {
        "doc": """
        提取一个章节下的多组（标题+内容）
        eg：
            重大事项提示 > 一级标题 + 一级标题下的内容
            财务会计信息-重要会计政策和会计评估 > 一级标题 + 一级标题下的内容
            公司治理与独立性-关联交易 > 章节名 + 该章节具体内容（原文）
        """,
        "name": "标题内容组",
        "hide": True,
    }

    def __init__(self, *args, **kwargs):
        super(TitleContentGroup, self).__init__(*args, **kwargs)
        self.base_on_crude_element = False
        self.top_title = self.config.get("top_title")
        self.need_training = self.top_title not in EXT_TITLE

    @classmethod
    def model_template(cls):
        template = {
            "top_title": "",
            "need_syl": True,
        }
        default_model_template = cls.default_model_template()
        default_model_template.update(template)
        return default_model_template

    def train(self, dataset, **kwargs):
        model = {}
        dataset = dataset or []
        # print('----------', self.columns, self.config, len(dataset), self.leaf)
        for item in dataset:
            for col in self.columns:
                if re.search(r"内容|原文", col):
                    continue
                leaves = item.answer.get(col, {}).values() if not self.leaf else [item.answer]
                for leaf in leaves:
                    if leaf.data is None:
                        continue
                    _features = self.extract_feature(item, leaf.data)
                    model.setdefault(col, Counter()).update(_features)
        # print('*****', model)
        self.model = model

    @staticmethod
    def extract_feature(anser_item, answer):
        sylls = anser_item.data.get("syllabuses", [])
        syllabus_dict = {syl["element"]: syl for syl in sylls}
        features = Counter()
        for answer_data in answer["data"]:
            if not answer_data["elements"]:
                continue
            for eid in answer_data["elements"]:
                syl = syllabus_dict.get(eid)
                # print('****', syl)
                if syl:
                    parents = sorted(filter(lambda x: syl["index"] in x["children"], sylls), key=lambda s: s["level"])
                    if parents:
                        clear_title = clear_syl_title(parents[-1]["title"])
                        # print('*****', parents[-1]['title'], clear_title)
                        features.update(
                            [
                                clear_title,
                            ]
                        )
        return features

    def split_none_syl_block(self):
        res = OrderedDict()
        if self.pdfinsight.syllabuses:
            for idx in range(self.pdfinsight.syllabuses[0]["element"]):
                elt_typ, elt = self.pdfinsight.find_element_by_index(idx)
                if not elt:
                    continue
                if elt_typ == "PARAGRAPH":
                    for title, reg in EXT_TITLE.items():
                        if re.search(reg, clean_txt(elt["text"])):
                            res.setdefault(title, idx)
                            break
                if len(res) == len(EXT_TITLE):
                    break
            res.setdefault("第一章", self.pdfinsight.syllabuses[0]["element"])
        blocks = namedtuple("blocks", list(res.keys()))
        return blocks(**res)

    def predict(self, elements, **kwargs):
        top_syllabus = self.pdfinsight.find_sylls_by_clear_title(self.top_title, order_by="level")
        if top_syllabus:
            titles, end = top_syllabus[0].get("children", []), None
        elif self.top_title in EXT_TITLE:  # 不在目录中的章节
            blocks = self.split_none_syl_block()
            if not hasattr(blocks, self.top_title):
                return []
            start, end = (
                blocks[blocks.index(getattr(blocks, self.top_title))],
                blocks[blocks.index(getattr(blocks, self.top_title)) + 1],
            )
            titles = []
            for idx in range(start, end):
                elt_typ, elt = self.pdfinsight.find_element_by_index(idx)
                if not elt:
                    continue
                # todo： 完善正则 & 标题层级问题
                title_regs = [r"^[一二三四五六七八九十]+[、]"]
                if elt_typ == "PARAGRAPH":
                    if any(re.search(reg, elt["text"]) for reg in title_regs):
                        # print('****', idx, elt['text'])
                        titles.append(idx)
        else:  # 目录中的章节
            titles = []
            start, end = None, None
            for col in self.columns:
                if re.search(r"内容|原文", col):
                    continue
                title_model = self.model.get(col)
                if not title_model:
                    continue
                aim_syl = defaultdict(list)
                for clear_title, _ in self.model.get(col).most_common():
                    syls = self.pdfinsight.find_sylls_by_clear_title(clear_title)
                    if syls:
                        aim_syl = syls[0]
                        break
                titles = aim_syl["children"]
        results = self._predict(titles, end)
        return results

    def _predict(self, titles, end=None):
        if not titles:
            return []
        answers = []
        if end:  # 非目录
            titles.append(end)
            for from_id, to_id in zip(titles[0::1], titles[1::1]):
                # print(from_id, to_id)
                answer, title_chars, content_chars = {}, [], []
                for elt_idx in range(from_id, to_id):
                    elt_typ, elt = self.pdfinsight.find_element_by_index(elt_idx)
                    if not elt:
                        continue
                    if elt_typ != "PARAGRAPH":
                        continue
                    if elt_idx == from_id:
                        title_chars.extend(elt["chars"])
                    else:
                        content_chars.extend(elt["chars"])
                if title_chars or content_chars:
                    for col in self.columns:
                        if re.search(r"(标题|章节名)$", col):
                            answer[col] = ResultOfPredictor([CharResult(title_chars)], score=1)
                        elif re.search(r"内容", col):
                            answer[col] = ResultOfPredictor([CharResult(content_chars)], score=1)
                    if answer:
                        answers.append(answer)
        else:
            for title_idx in titles:
                syl = self.pdfinsight.syllabus_dict.get(title_idx)
                if not syl:
                    continue
                answer, title_chars, content_chars = {}, [], []
                for idx in range(*syl["range"]):
                    elt_typ, elt = self.pdfinsight.find_element_by_index(idx)
                    if not elt:
                        continue
                    if idx == syl["element"]:
                        title_chars.extend(elt.get("chars", []))
                    else:
                        if elt_typ == "PARAGRAPH":
                            content_chars.extend(elt["chars"])
                        elif elt_typ == "TABLE":
                            # todo
                            pass
                if title_chars and content_chars:
                    for col in self.columns:
                        if re.search(r"(标题|章节名)$", col):
                            answer[col] = ResultOfPredictor([CharResult(title_chars)], score=1)
                        elif re.search(r"内容", col):
                            answer[col] = ResultOfPredictor([CharResult(content_chars)], score=1)
                    if answer:
                        answers.append(answer)
        return answers
