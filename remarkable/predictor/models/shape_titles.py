# -*- coding: utf-8 -*-
"""根据表格标题提取整个图表以及标题"""

import re

from remarkable.common.pattern import PatternCollection
from remarkable.common.util import clean_txt
from remarkable.predictor.dataset import DatasetItem
from remarkable.predictor.models.base_model import BaseModel
from remarkable.predictor.schema_answer import OutlineResult


class ShapeTitle(BaseModel):
    def extract_feature(self, elements, answer):
        pass

    @property
    def regs(self):
        return PatternCollection(self.get_config("regs", []), re.I)

    @property
    def neglect_regs(self):
        return PatternCollection(self.get_config("neglect_regs", []), re.I)

    @property
    def use_all_elements(self) -> bool:
        return self.get_config("use_all_elements", False)

    @property
    def force_use_all_elements(self) -> bool:
        return self.get_config("force_use_all_elements", False)

    @property
    def include_title(self) -> bool:
        return self.get_config("include_title", True)

    @property
    def filter_blew_types(self) -> set:
        return {"IMAGE", "SHAPE", "INFOGRAPHIC"}

    @property
    def ignore_regs_before_shape(self):  # title 和 shape 之间需要忽略的干扰element
        return PatternCollection(self.get_config("ignore_regs_before_shape", []), flags=re.I)

    def train(self, dataset: list[DatasetItem], **kwargs):
        pass

    def predict_schema_answer(self, elements):
        if self.force_use_all_elements or (not elements and self.use_all_elements):
            elements = self.get_special_elements(["PARAGRAPH"])
            elements.sort(key=lambda x: x["index"])
        answer_results = []
        near_paras = self.pretreatment(elements)
        for para in near_paras:
            para_text = clean_txt(para["text"])
            if self.neglect_regs and self.neglect_regs.nexts(para_text):
                continue
            if not (self.regs and self.regs.nexts(para_text)):
                continue
            answer_elements = []
            if shape_element := self.filter_blew_shape(para):
                answer_elements.append(shape_element)
            else:
                continue
            if self.include_title:
                answer_elements.insert(0, para)
            if not self.multi_elements and answer_results:
                continue
            page_boxes = self.pdfinsight.elements_outline(answer_elements)
            if not page_boxes:
                return answer_results
            if page_boxes[-1]["text"] == "" and not self.include_title:
                page_boxes[-1]["text"] = para_text
            display_text = ""
            for item in page_boxes:
                display_text += item["text"]
            element_results = [
                OutlineResult(
                    page_box=page_boxes, text=display_text, element=answer_elements[0], origin_elements=elements
                )
            ]
            answer_result = self.create_result(element_results, text=display_text, column=self.predictor.schema.name)
            answer_results.append(answer_result)

            if not self.multi_elements:
                break

        if not answer_results:
            answer_results = self.get_answer_from_shape(elements)
        return answer_results

    def get_answer_from_shape(self, elements):
        answer_results = []
        for element in elements:
            if element["class"] == "SHAPE":
                para_text = clean_txt(element.get("title", ""))
                if self.neglect_regs and self.neglect_regs.nexts(para_text):
                    continue
                if not (self.regs and self.regs.nexts(para_text)):
                    continue
                page_box = self.pdfinsight.elements_outline([element])
                if not page_box:
                    return answer_results
                element_results = [
                    OutlineResult(page_box=page_box, text=para_text, element=element, origin_elements=[element])
                ]
                answer_result = self.create_result(element_results, text=para_text, column=self.predictor.schema.name)
                answer_results.append(answer_result)
        return answer_results

    @staticmethod
    def pretreatment(elements):
        near_paras = [element for element in elements if element["class"] == "PARAGRAPH"]
        return near_paras
        # ret = ''.join(clean_txt(i['text']) for i in near_paras)
        # return ret

    def filter_blew_shape(self, paragraph):
        next_element_index = paragraph["index"] + 1
        try:
            ele_type, element = self.pdfinsight.find_element_by_index(next_element_index)
        except IndexError:
            pass
        else:
            if ele_type in self.filter_blew_types:
                return element

        # 双栏排版引起的,或shape上方有类似'总计'这种干扰element, title下的shape可能与title的index不止差1
        while True:
            next_element_index += 1
            try:
                ele_type, element = self.pdfinsight.find_element_by_index(next_element_index)
            except IndexError:
                break
            if not element:
                continue
            if element["outline"][1] > paragraph["outline"][1]:
                if ele_type in self.filter_blew_types:
                    return element
                if element.get("text") and self.ignore_regs_before_shape.nexts(element["text"]):
                    continue
                break
            if element["page"] > paragraph["page"]:
                break

        return None

    def get_blew_shapes_same_page(self, paragraph):
        ret = []
        next_element_index = paragraph["index"]
        while True:
            next_element_index += 1
            try:
                ele_type, element = self.pdfinsight.find_element_by_index(next_element_index)
            except IndexError:
                break
            if not element:
                continue
            if element["outline"][1] > paragraph["outline"][1]:
                if ele_type in ("IMAGE", "SHAPE"):
                    ret.append(element)
                if element.get("text") and self.ignore_regs_before_shape.nexts(element["text"]):
                    continue
            if element.get("syllabus") and element["syllabus"] in self.pdfinsight_syllabus.elt_syllabus_dict:
                break
            if element["page"] > paragraph["page"]:
                break
        return ret
