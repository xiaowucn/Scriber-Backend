import re

from remarkable.common.util import clean_txt, group_cells
from remarkable.plugins.predict.common import is_paragraph_elt
from remarkable.predictor.predict import CharResult, ResultOfPredictor

from .model_base import PredictModelBase


class FixedPosition(PredictModelBase):
    model_intro = {
        "doc": """
        在文档固定位置出现的属性，如证券代码、证券简称、公告编号等
        """,
        "name": "固定位置提取",
        "hide": True,
    }

    def __init__(self, *args, **kwargs):
        super(FixedPosition, self).__init__(*args, **kwargs)
        self.base_on_crude_element = False
        self.need_training = False

    @classmethod
    def model_template(cls):
        template = {"positions": [], "regs": [], "anchor_regs": []}
        default_model_template = cls.default_model_template()
        default_model_template.update(template)
        return default_model_template

    def train(self, dataset, **kwargs):
        model = {}
        self.model = model

    def predict(self, elements, **kwargs):
        results = []
        for position in map(int, self.config.get("positions", [])):
            elt_idx = position if position >= 0 else len(self.pdfinsight.data["_index"]) + position + 1
            etype, ele = self.pdfinsight.find_element_by_index(elt_idx)
            # print(position, elt_idx, etype)
            if not ele:
                continue
            answers = []
            if is_paragraph_elt(ele):
                answers = self._predict_from_para(ele, **kwargs)
            elif etype == "TABLE":
                answers = self._predict_from_tbl(ele, **kwargs)
            if answers:
                results.extend(answers)
                break
        return results

    def _predict_from_para(self, element, **kwargs):
        answer = {}
        content = clean_txt(element.get("text", ""))
        anchor_regs = self.config.get("anchor_regs", [])
        is_aim_elt = not anchor_regs
        if anchor_regs:
            prev_elts = self.pdfinsight.find_elements_near_by(element["index"], step=1, amount=3)
            for prev_elt in prev_elts:
                if is_paragraph_elt(prev_elt):
                    if any(re.search(reg, clean_txt(prev_elt["text"])) for reg in anchor_regs):
                        is_aim_elt = True
                        break
        if is_aim_elt:
            chars = [i for i in element["chars"] if not re.search(r"^\s+$", i["text"])]
            for col in self.columns:
                for pattern in self.config.get("regs", []):
                    if re.search(pattern, content):
                        for item in re.finditer(pattern, content):
                            dst_chars = chars[item.start("dst") : item.end("dst")]
                            answer[col] = ResultOfPredictor([CharResult(dst_chars)], score=1)
                            break
        answers = []
        if answer:
            answers.append(answer)
        return answers

    def _predict_from_tbl(self, element, **kwargs):
        """
        公司代码/公司简称/公告编号 误识别为table的情况
        """
        answers = []
        anchor_regs = self.config.get("anchor_regs", [])
        is_aim_elt = not anchor_regs
        if anchor_regs:
            prev_elts = self.pdfinsight.find_elements_near_by(element["index"], step=1, amount=3)
            for prev_elt in prev_elts:
                if is_paragraph_elt(prev_elt):
                    if any(re.search(reg, clean_txt(prev_elt["text"])) for reg in anchor_regs):
                        is_aim_elt = True
                        break
        if not is_aim_elt:
            return []
        answer = {}
        cells_by_row, _ = group_cells(element["cells"])
        for cells in cells_by_row.values():
            for col, cell in cells.items():
                # print('----', row, col, cell['text'])
                content = clean_txt(cell.get("text", ""))
                chars = [i for i in cell["chars"] if not re.search(r"^\s+$", i["text"])]
                for col in self.columns:
                    if col in answer:
                        continue
                    for pattern in self.config.get("regs", []):
                        if re.search(pattern, content):
                            for item in re.finditer(pattern, content):
                                dst_chars = chars[item.start("dst") : item.end("dst")]
                                # print('***', [x['text'] for x in dst_chars])
                                answer[col] = ResultOfPredictor([CharResult(dst_chars)], score=1)
                                break
                        if col in answer:
                            break
        if answer:
            answers.append(answer)
        return answers
