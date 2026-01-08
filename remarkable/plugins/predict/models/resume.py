import re

from remarkable.common.util import clean_txt
from remarkable.predictor.predict import CharResult, ParaResult, ResultOfPredictor, TblResult

from .model_base import PredictModelBase


class Resume(PredictModelBase):
    model_intro = {
        "doc": """
        根据姓名获取同章节下的简历内容
        eg：发行人基本情况-董事会成员 > 简历
        """,
        "name": "简历模型",
        "hide": True,
    }

    def __init__(self, *args, **kwargs):
        super(Resume, self).__init__(*args, **kwargs)
        self.base_on_crude_element = False
        self.need_training = False

    @classmethod
    def model_template(cls):
        template = {}
        default_model_template = cls.default_model_template()
        default_model_template.update(template)
        return default_model_template

    def train(self, dataset, **kwargs):
        model = {}
        self.model = model

    def predict(self, elements, **kwargs):
        answers = []
        parent_answer = kwargs.get("parent_answer", {})
        key_answer_item = parent_answer.get(self.config.get("_key"))
        if key_answer_item:
            for item in key_answer_item.data:
                if isinstance(item, TblResult):
                    # print(item.cells, item.elt['class'], item.elt['index'])
                    syls = self.pdfinsight.find_syllabuses_by_index(item.elt["index"])
                    if not (item.cells and syls):
                        continue
                    # print('-------', [x['title'] for x in syls], syls[-1])
                    for cell_idx in item.cells:
                        answer_chars = []
                        _text = clean_txt(item.elt.get("cells", {}).get(cell_idx, {}).get("text", ""))
                        if _text:
                            # print('~~~~', cell_idx, _text)
                            for elt_idx in range(*syls[-1]["range"]):
                                elt_typ, elt = self.pdfinsight.find_element_by_index(elt_idx)
                                if not elt:
                                    continue
                                if elt_typ == "PARAGRAPH":
                                    # print('-------', elt_idx, elt['class'], elt.get('text'))
                                    if re.search(
                                        r"^[一二三四五六七八九十\d\s()（）.、]*%s" % _text, clean_txt(elt["text"])
                                    ):
                                        if any(
                                            syl["element"] == elt_idx for syl in self.pdfinsight.syllabus_dict.values()
                                        ):
                                            chars = self.additional_section(elt_idx)
                                            # print('***1', ''.join([x['text'] for x in chars]))
                                        else:
                                            chars = (
                                                elt["page_merged_paragraph"]["chars"]
                                                if elt["page_merged_paragraph"]
                                                else elt["chars"]
                                            )
                                            # print('***2', ''.join([x['text'] for x in chars]))
                                        answer_chars.extend(chars)
                        if answer_chars:
                            answer = {self.columns[0]: ResultOfPredictor([CharResult(chars=answer_chars, elt=elt)])}
                            answers.append(answer)
                elif isinstance(item, ParaResult):
                    pass
                elif isinstance(item, CharResult):
                    pass
        return answers

    def additional_section(self, elt_idx):
        """
        姓名作为章节标题的情况
        """
        chars = []
        for _, syl in self.pdfinsight.syllabus_dict.items():
            if syl["element"] != elt_idx:
                continue
            # print('!!!!', syl)
            for idx in range(*syl["range"]):
                elt_typ, elt = self.pdfinsight.find_element_by_index(idx)
                if not elt:
                    continue
                if elt_typ == "PARAGRAPH":
                    chars.extend(elt["chars"])
        return chars
