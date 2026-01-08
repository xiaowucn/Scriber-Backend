from copy import deepcopy

from remarkable.common.pattern import PatternCollection
from remarkable.common.util import clean_txt
from remarkable.pdfinsight.reader import PdfinsightSyllabus
from remarkable.predictor.models.syllabus_elt import SyllabusElt
from remarkable.predictor.mold_schema import SchemaItem
from remarkable.predictor.schema_answer import OutlineResult

LETTER_TITLE_REG = r"(?P<flag>^(\([abci+]\)))"
SPECIAL_LETTER_TITLE_REG = r"选择权"

TITLE_PATTERN = PatternCollection(
    [
        r"(?P<flag>^([\d.]+))",
        LETTER_TITLE_REG,
    ]
)

SPECIAL_KEYWORD_PATTERN = PatternCollection([r"信托财产包括但不限于"])

"""
"通常为3.5.1段落
不是【基础资产的信托】，是后面一个
"""

SPECIAL_SERIAL_NUMBER = PatternCollection(r"3.5.1")

INVALID_ROOT_SYLLABUS_PATTERN = PatternCollection(
    [
        r"附件",
    ]
)

SPECIAL_ADD_PARA_PATTERN = PatternCollection(
    [
        r"^([\d.]+)清仓回购是委托人的一项选择权。$",
        r"^([\d.]+)“?信托财产”?还包括“?信托账户”?内所有资金",
    ]
)

FIRST_PARA_PATTERN = PatternCollection(
    [
        r"本信托的信托财产范围包括",
    ]
)

NEED_ALL_SYLLABUS_PATTERNS = PatternCollection(
    [
        r"基础资产的信托",
    ]
)


class ClearanceRepo(SyllabusElt):
    def __init__(self, options: dict, schema: SchemaItem, predictor):
        super(ClearanceRepo, self).__init__(options, schema, predictor=predictor)

    def predict_schema_answer(self, elements):
        ret = []
        for col in self.columns:
            model_data = self.get_model_data(col)
            aim_syllabuses = self.get_aim_syllabus(self.revise_model(model_data))

            all_elements = []
            for aim_syllabuse in aim_syllabuses:
                root_syllabus = self.pdfinsight_syllabus.get_root_syllabus(aim_syllabuse)
                if INVALID_ROOT_SYLLABUS_PATTERN.nexts(clean_txt(root_syllabus["title"])):
                    continue
                syl_matcher = TITLE_PATTERN.nexts(clean_txt(aim_syllabuse["title"]))
                if not syl_matcher:
                    continue
                serial_number = syl_matcher.group("flag")
                for index in range(*aim_syllabuse["range"]):
                    if index == aim_syllabuse["element"]:
                        continue
                    elt_typ, elt = self.pdfinsight.find_element_by_index(index)
                    if elt_typ != "PARAGRAPH":
                        continue
                    all_elements.append(elt)
                if self.need_all_syllabus(serial_number, all_elements, aim_syllabuse):
                    para_range = {"range": (all_elements[0]["index"], all_elements[-1]["index"] + 1)}
                else:
                    aim_section = self.get_aim_section(all_elements, serial_number)
                    if not aim_section:
                        continue
                    para_range = {"range": (aim_section[0]["index"], aim_section[-1]["index"] + 1)}
                ret.extend(self.paras2outline(para_range))
                break
        if not ret:
            return super(ClearanceRepo, self).predict_schema_answer(elements)
        return ret

    def need_all_syllabus(self, serial_number, all_elements, aim_syllabuse):
        if SPECIAL_SERIAL_NUMBER.nexts(serial_number):
            return True
        if self.special_first_element(all_elements):
            return True
        if NEED_ALL_SYLLABUS_PATTERNS.nexts(clean_txt(aim_syllabuse["title"])):
            return True
        return False

    @staticmethod
    def special_first_element(elements):
        if not elements:
            return False
        element = elements[0]
        return FIRST_PARA_PATTERN.nexts(clean_txt(element["text"]))

    def get_aim_section(self, elements, serial_number):
        sections = {}
        current_chief = None
        merged_para_idx = set()
        add_para_section = []
        is_letter_title = None
        need_next_section = False
        for element in elements:
            if SPECIAL_KEYWORD_PATTERN.nexts(clean_txt(element["text"])):
                return None
            sub_chief, is_letter_title = self.get_sub_chief(element, serial_number, is_letter_title)
            if sub_chief:
                current_chief = sub_chief
            if not current_chief:
                continue
            if element["continued"]:
                page_merged_paragraph_idx = deepcopy(element["page_merged_paragraph"]["paragraph_indices"])
                if element["index"] in page_merged_paragraph_idx:
                    page_merged_paragraph_idx.remove(element["index"])
                merged_para_idx = merged_para_idx.union(set(page_merged_paragraph_idx))
            if element["index"] in merged_para_idx:
                continue
            if SPECIAL_ADD_PARA_PATTERN.nexts(clean_txt(element["text"])):
                need_next_section = True
            sections.setdefault(current_chief, []).append(element)
            add_para_pattern = PatternCollection(self.config.get("add_para_pattern", []))
            add_matcher = add_para_pattern.nexts(clean_txt(element["text"]))
            if not add_matcher:
                continue
            add_para_section.append(add_matcher.group("dst"))
        if not sections:
            return None
        aim_section = list(sections.values())[0]
        if need_next_section:
            aim_section.extend(list(sections.values())[1])
        for section_flag in add_para_section:
            aim_section.extend(sections.get(section_flag, []))
        return aim_section

    def paras2outline(self, para_range):
        answer_results = []
        page_box = PdfinsightSyllabus.syl_outline(para_range, self.pdfinsight, include_title=True)
        elements = []
        for i in page_box:
            elements.extend(i["elements"])
        if not elements:
            return answer_results
        element_results = [OutlineResult(page_box=page_box, element=elements[0])]
        answer_result = self.create_result(element_results, column=self.schema.name)
        answer_results.append(answer_result)
        return answer_results

    @staticmethod
    def get_sub_chief(para, serial_number, is_letter_title):
        chief = None
        clean_text = clean_txt(para["text"])
        match = TITLE_PATTERN.nexts(clean_text)
        if match:
            chief = match.group("flag")
            # 标题的长度大于父级标题长度+2时，认为其不是一个可以进行分组的标志
            # serial_number 为14 14.1为chief 14.1.1不是chief
            if chief and len(chief) > len(serial_number) + 2:
                return None, is_letter_title
            if PatternCollection(LETTER_TITLE_REG).nexts(clean_text):
                if is_letter_title is None:
                    if PatternCollection(SPECIAL_LETTER_TITLE_REG).nexts(clean_text):
                        is_letter_title = True
                        return chief, is_letter_title
                    is_letter_title = False
                    return None, is_letter_title
                if is_letter_title:  # is_letter_title maybe ture or false
                    return chief, is_letter_title
                return None, is_letter_title
        return chief, is_letter_title
