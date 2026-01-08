import re

from remarkable.common.pattern import PatternCollection
from remarkable.common.util import clean_txt
from remarkable.pdfinsight.reader import PdfinsightSyllabus
from remarkable.predictor.models.syllabus_elt_v2 import P_NUM_START, SyllabusEltV2
from remarkable.predictor.mold_schema import SchemaItem
from remarkable.predictor.schema_answer import OutlineResult


class FilterPdfinsightSyllabus(PdfinsightSyllabus):
    @classmethod
    def syl_outline(
        cls,
        syllabus,
        pdfinsight,
        include_title=False,
        ignore_pattern=None,
        only_before_first_chapter=None,
        include_sub_title=True,
        break_para_pattern=None,
        skip_table=False,  # 跳过syllabus里的表格
        page_header_patterns=None,
    ):
        """
        获取章节外框
        """
        elements = []
        start, end = syllabus["range"]
        element_indexes = set()
        for idx in range(start + 1, end):
            elt_type, elt = pdfinsight.find_element_by_index(idx)
            if elt and elt_type not in ["PAGE_HEADER", "PAGE_FOOTER"] and elt["index"] not in element_indexes:
                if end - start <= 2:
                    elements.append(elt)
                else:
                    clean_element_text = clean_txt(elt.get("text", ""))

                    if P_NUM_START.search(clean_element_text) and not clean_element_text.endswith("基金计价方法说明"):
                        if elements:
                            break
                        elements.append(elt)
                    else:
                        if elements:
                            elements.append(elt)
                        else:
                            continue
                if elt.get("page_merged_paragraph"):
                    for elt_index in elt["page_merged_paragraph"]["paragraph_indices"]:
                        element_indexes.add(elt_index)
                else:
                    element_indexes.add(elt["index"])
        return cls.elements_outline(elements)


class GFFoundsSyllabusFilter(SyllabusEltV2):
    def __init__(self, options: dict, schema: SchemaItem, predictor):
        super().__init__(options, schema, predictor=predictor)
        self.important_split = self.get_config("important_split", False)  # 重要提示拆分
        self.is_first_part = self.get_config("is_first_part", False)  # 拆分顺序
        self.filter_table = self.get_config("filter_table", False)  # 过滤表格段落
        self.first_num_para = self.get_config("first_num_para", False)  # 获取syllabus下面第一个带有数字的段落内容
        self.last_paragraph = self.get_config("last_paragraph", False)  # 获取syllabus下面第一个带有数字的段落内容

    def predict_schema_answer(self, elements):
        self.load_model_data()
        answer_results = []
        for col in self.columns:
            if not (model_data := self.get_model_data(col)):
                return answer_results
            if not (
                aim_syllabuses := self.get_aim_syllabus(
                    model_data,
                    min_level=self.min_level,
                    max_level=self.syllabus_level,
                    syllabus_black_list=PatternCollection(self.get_config("syllabus_black_list", column=col)),
                )
            ):
                return answer_results
            for aim_syl in aim_syllabuses:
                if self.last_paragraph:
                    if not (answer_result := self.create_syl_result(aim_syl, last=True)):
                        continue
                    answer_results.extend(answer_result)
                    return answer_results
                if self.filter_table:
                    ele_type, _ = self.pdfinsight.find_element_by_index(aim_syl["element"] + 1)
                    if ele_type != "PARAGRAPH":
                        continue
                if self.only_first:
                    if answer_result := self.create_syl_result(aim_syl):
                        answer_results.extend(answer_result)
                elif self.first_num_para:
                    page_box = FilterPdfinsightSyllabus.syl_outline(aim_syl, self.pdfinsight)
                    if not page_box:
                        continue
                    # https://gitpd.paodingai.com/cheftin/docs_scriber/-/issues/2177
                    # 应该只用去掉第一个box的行首数字
                    text = re.sub(P_NUM_START, "", page_box[0]["text"].strip())
                    page_box[0]["text"] = text
                    elements = self.get_elements_from_page_box(page_box)
                    if not elements:
                        continue
                    element_results = [
                        OutlineResult(page_box=page_box, text=text, element=elements[0], origin_elements=elements)
                    ]
                    answer_result = self.create_result(element_results, text=text, column=col)
                    answer_results.append(answer_result)
                else:
                    page_box = PdfinsightSyllabus.syl_outline(
                        aim_syl,
                        self.pdfinsight,
                        include_title=self.include_title,
                    )
                    text = "\n".join(i["text"] for i in page_box)
                    elements = self.get_elements_from_page_box(page_box)
                    if not elements:
                        continue
                    if self.important_split:
                        elements = elements[:-1] if self.is_first_part else elements[-1:]
                        text = "\n".join(i["text"] for i in elements)
                        page_box[0]["elements"] = elements
                        page_box[0]["text"] = text
                        if self.is_first_part:
                            page_box[0]["outline"][-1] = elements[-1]["outline"][-1]
                        else:
                            page_box[0]["outline"] = elements[0]["outline"]
                    element_results = [
                        OutlineResult(page_box=page_box, text=text, element=elements[0], origin_elements=elements)
                    ]
                    answer_result = self.create_result(element_results, text=text, column=col)
                    answer_results.append(answer_result)
        return answer_results

    def create_syl_result(self, aim_syl, last=False):
        answer_results = []
        idx = aim_syl["range"][1] - 1 if last else aim_syl["element"] + 1
        ele_type, aim_para = self.pdfinsight.find_element_by_index(idx)
        if ele_type != "PARAGRAPH":
            return answer_results
        if aim_para:
            aim_elements = []
            if self.include_title:
                ele_type, aim_syl_para = self.pdfinsight.find_element_by_index(aim_syl["element"])
                aim_elements.append(aim_syl_para)
            aim_elements.append(aim_para)
            outline_result = [OutlineResult(self.pdfinsight.elements_outline(aim_elements), element=aim_elements[0])]
            answer_result = self.create_result(outline_result, column=self.schema.name)
            answer_results.append(answer_result)
        return answer_results
