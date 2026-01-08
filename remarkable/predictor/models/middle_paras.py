from remarkable.common.pattern import PatternCollection
from remarkable.common.util import clean_txt, fix_ele_type
from remarkable.predictor.models.syllabus_elt_v2 import SyllabusEltV2
from remarkable.predictor.schema_answer import OutlineResult


class MiddleParas(SyllabusEltV2):
    """
    找到前后两个锚点,取中间的段落
    P
    m1
    m2
    p
    m3
    p

    m: bottom_anchor_pattern能match的段落
    default: 取m1
    bottom_greed为True时,取m3
    bottom_greed & bottom_continue_greed为True时,则取m2
    """

    def __init__(self, options, schema, predictor=None):
        super().__init__(options, schema, predictor=predictor)
        self.top_anchor_pattern = PatternCollection(self.get_config("top_anchor_regs", []))  # 顶部锚点正则
        self.neglect_top_anchor = PatternCollection(self.get_config("neglect_top_anchor", []))  # 非顶部锚点
        self.bottom_anchor_pattern = PatternCollection(self.get_config("bottom_anchor_regs", []))  # 底部锚点正则
        self.neglect_bottom_anchor = PatternCollection(self.get_config("neglect_bottom_anchor", []))  # 非底部锚点

        self.top_anchor_range_regs = PatternCollection(
            self.get_config("top_anchor_range_regs", [])
        )  # 当匹配上这个时，才开始找范围
        self.bottom_anchor_range_regs = PatternCollection(
            self.get_config("bottom_anchor_range_regs", [])
        )  # 当匹配上这个后，后面都不要了
        self.top_anchor_ignore_regs = PatternCollection(
            self.get_config("top_anchor_ignore_regs", [])
        )  # 从这开始, 删掉一些区域
        self.bottom_anchor_ignore_regs = PatternCollection(
            self.get_config("bottom_anchor_ignore_regs", [])
        )  # 删掉一些区域, 从这结束

        self.include_top_anchor = self.get_config("include_top_anchor", True)  # 包含顶部锚点
        self.include_bottom_anchor = self.get_config("include_bottom_anchor", False)  # 包含底部锚点
        self.top_greed = self.get_config("top_greed", True)  # 贪婪模式,即使截出来的middle_paras尽量多
        self.top_continue_greed = self.get_config("top_continue_greed", False)  # 连续贪婪
        self.bottom_greed = self.get_config("bottom_greed", False)
        self.bottom_continue_greed = self.get_config("bottom_continue_greed", False)
        self.top_default = self.get_config("top_default", False)  # 确定顶部锚点失败时可以使用第一个元素块作为顶部锚点
        self.bottom_default = self.get_config("bottom_default", False)
        self.top_content_regs = self.get_config("top_anchor_content_regs")  # 从顶部锚点提取内容的正则
        self.bottom_content_regs = self.get_config("bottom_anchor_content_regs")
        self.middle_content_regs = self.get_config("middle_content_regs")
        self.elements_in_page_range = self.get_config("elements_in_page_range", [])  # 使用指定页码的元素块
        self.elements_not_in_page_range = self.get_config("elements_not_in_page_range", [])  # 排除指定页码的元素块
        # 使用初步定位得分最高的元素块周围的元素块
        self.use_top_crude_neighbor = self.get_config("use_top_crude_neighbor", True)
        self.use_syllabus_model = self.get_config("use_syllabus_model", False)
        self.possible_element_counts = self.get_config("possible_element_counts")  # 可能的元素块数量,不够时向前向后找补
        self.use_direct_elements = self.get_config(
            "use_direct_elements", False
        )  # maybe use elements that are from syllabus_based
        self.table_regarded_as_paras = self.get_config("table_regarded_as_paras")
        self.table_regarded_as_paragraph = self.get_config("table_regarded_as_paragraph")
        self.cell_separator = self.get_config("cell_separator") or ""
        self.multi_blocks = self.get_config("multi_blocks")
        self.keywords = self.get_config("keywords")  # 必须包含的关键词
        self.page_header_patterns = PatternCollection(self.get_config("page_header_patterns", []))
        self.only_use_syllabus_elements = self.get_config("only_use_syllabus_elements", False)
        self.top_page_offset = self.get_config("top_page_offset", 5)
        self.bottom_page_offset = self.get_config("bottom_page_offset", 15)

        self.skip_merged_para = self.get_config("skip_merged_para", False)  # 是否跳过合并的段落
        self.support_element_types = self.get_config("support_element_types", [])  # 支持的元素类型

    def predict_schema_answer(self, elements):
        answer_results = []
        elements_blocks = self.collect_elements(elements)
        for col in self.columns:
            for answer_elements in elements_blocks:
                answer_results.append(self.build_answer(answer_elements, col))
        return answer_results

    def is_meet_condition(self, elements) -> bool:
        return True if self.collect_elements(elements) else False

    def fixed_elements(self, elements):
        fixed_elements = []
        if elements and not self.skip_merged_para:
            self.merge_paginated_paragraphs(self.pdfinsight, elements)
        temp_index = 0
        for ele in elements:
            elt_type = ele["class"]
            elt_type = fix_ele_type(self.pdfinsight, self.page_header_patterns, elt_type, ele)

            if elt_type == "PARAGRAPH" or elt_type in self.support_element_types:
                ele["temp_index"] = temp_index
                temp_index += 1
                fixed_elements.append(ele)
            elif elt_type == "TABLE":
                if self.table_regarded_as_paras:
                    ele["paras"] = self.get_paragraphs_from_table(ele, self.cell_separator)
                    for para in ele["paras"]:
                        para["temp_index"] = temp_index
                        temp_index += 1
                        fixed_elements.append(para)
                elif self.table_regarded_as_paragraph:
                    ele["text"] = "321ed77f-8246-4c48-b102-9d4d6392fec7"
                    ele["temp_index"] = temp_index
                    temp_index += 1
                    fixed_elements.append(ele)
        return fixed_elements

    def collect_elements(self, elements):
        elements = self.collect_crude_elements(elements)
        elements = [x for x in elements if x["page"] not in self.elements_not_in_page_range]

        fixed_elements = self.fixed_elements(elements)
        fixed_elements = self.filter_elements_by_range(fixed_elements)

        if not fixed_elements:
            return []
        elements_blocks = self.get_elements_blocks(fixed_elements)
        for elements_block in elements_blocks:
            for element in elements_block:
                element.pop("temp_index", None)
        return elements_blocks

    def get_elements_blocks(self, elements):
        elements_blocks = []
        element_map = {element["temp_index"]: element for element in elements}

        while True:
            top_element_index, bottom_element_index = self.get_margin_index(elements)
            if bottom_element_index is None or top_element_index > bottom_element_index:
                break
            if top_element_index == bottom_element_index and not (self.top_default or self.bottom_default):
                break

            answer_elements = []
            for ele in elements:
                if ele["temp_index"] >= bottom_element_index:
                    continue
                if ele["temp_index"] <= top_element_index:
                    continue
                if content_ele := self.get_element_with_content_chars(ele, self.middle_content_regs):
                    answer_elements.append(content_ele)

            if self.include_top_anchor:
                top_anchor_element = self.get_element_with_content_chars(
                    element_map[top_element_index], self.top_content_regs
                )
                if top_anchor_element:
                    answer_elements.insert(0, top_anchor_element)
            if self.include_bottom_anchor:
                bottom_anchor_element = self.get_element_with_content_chars(
                    element_map[bottom_element_index], self.bottom_content_regs
                )
                if bottom_anchor_element:
                    answer_elements.append(bottom_anchor_element)

            answer_elements = [ele for ele in answer_elements if not self.is_ignore(ele)]

            if not answer_elements:
                break

            if self.is_matched_keywords(answer_elements):
                elements_blocks.append(answer_elements)

            if top_element_index == bottom_element_index:  # 不再尝试找更多的block
                break

            if not self.multi_blocks:
                break
            new_elements = [ele for ele in elements if ele["temp_index"] >= bottom_element_index]
            if len(elements) == len(new_elements):
                break
            elements = new_elements

        return elements_blocks

    def is_ignore(self, element):
        return self.ignore_pattern and self.ignore_pattern.nexts(clean_txt(element.get("text", "")))

    @staticmethod
    def merge_paginated_paragraphs(pdfinsight_reader, answer_elements):
        def get_paragraph_indices(element):
            return (element.get("page_merged_paragraph") or {}).get("paragraph_indices", [])

        def add_paragraphs(indices):
            for paragraph_index in indices:
                if paragraph_index in [item["index"] for item in answer_elements]:
                    continue
                if temp_ele := pdfinsight_reader.find_element_by_index(paragraph_index)[1]:
                    answer_elements.append(temp_ele)
            answer_elements.sort(key=lambda x: x["index"])

        first_indices = get_paragraph_indices(answer_elements[0])
        if len(answer_elements) == 1:
            add_paragraphs(first_indices)
            return
        add_paragraphs(first_indices)
        add_paragraphs(get_paragraph_indices(answer_elements[-1]))

    def filter_elements_by_range(self, fixed_elements):
        _fix_elements = []

        if self.top_anchor_range_regs.patterns or self.bottom_anchor_range_regs.patterns:
            start = False
            for ele in fixed_elements:
                if not start and self.top_anchor_range_regs.nexts(ele["text"]):
                    start = True
                    _fix_elements.append(ele)
                    continue
                if start:
                    _fix_elements.append(ele)
                    if self.bottom_anchor_range_regs.nexts(ele["text"]):
                        break
            fixed_elements = _fix_elements

        if self.top_anchor_ignore_regs.patterns and self.bottom_anchor_ignore_regs.patterns:
            ranges = []
            curr_range = []
            for index, ele in enumerate(fixed_elements):
                if self.top_anchor_ignore_regs.nexts(ele["text"]):
                    if not curr_range:
                        curr_range = [index, None]
                    else:
                        curr_range[1] = index
                        ranges.append(curr_range)
                        curr_range = None
                        continue

                if self.bottom_anchor_ignore_regs.nexts(ele["text"]):
                    if curr_range and curr_range[0] != index:
                        curr_range[1] = index
                        ranges.append(curr_range)
                        curr_range = None

            if ranges and ranges[-1][-1] is None:
                ranges.pop()

            if ranges:
                _fix_elements = []
                for index, ele in enumerate(fixed_elements):
                    if any(not (start <= index < end) for start, end in ranges):
                        _fix_elements.append(ele)
                fixed_elements = _fix_elements

        return fixed_elements

    def is_matched_keywords(self, blocks):
        match_keywords = True
        if self.keywords:
            if not blocks:
                return False
            for keyword in self.keywords:  # 每一个keyword都要包含
                key_word_pattern = PatternCollection(keyword)
                for element in blocks:
                    if key_word_pattern.nexts(element["text"]):
                        break
                else:
                    match_keywords = False
                    break
        return match_keywords

    def get_margin_index(self, elements):
        default_top_index = elements[0]["temp_index"] if self.top_default else None
        default_bottom_index = elements[-1]["temp_index"] if self.bottom_default else None

        top_element_index = self.get_anchor_index(
            elements[::-1],
            self.top_anchor_pattern,
            default_top_index,
            self.top_greed,
            self.top_continue_greed,
            self.neglect_top_anchor,
        )
        if top_element_index is None:
            return None, None
        all_elements_for_bottom = [element for element in elements if element["temp_index"] > top_element_index]
        bottom_element_index = self.get_anchor_index(
            all_elements_for_bottom,
            self.bottom_anchor_pattern,
            default_bottom_index,
            self.bottom_greed,
            self.bottom_continue_greed,
            self.neglect_bottom_anchor,
        )
        return top_element_index, bottom_element_index

    def collect_crude_elements(self, elements):
        ret = []
        if self.use_direct_elements:
            return elements
        if self.elements_in_page_range:
            for eles in self.pdfinsight.element_dict.values():
                ret.extend([ele.data for ele in eles if ele.data["page"] in self.elements_in_page_range])
            return ret

        if not self.use_top_crude_neighbor and not self.use_syllabus_model:
            # 使用文档的全部元素块, 一般适用于文档页数较少的情况
            for eles in self.pdfinsight.element_dict.values():
                for ele in eles:
                    if self.skip_merged_para and ele.data["class"] == "PARAGRAPH":
                        paragraph_indices = (ele.data["page_merged_paragraph"] or {}).get("paragraph_indices", [])
                        if paragraph_indices and ele.data["index"] != paragraph_indices[0]:
                            continue
                    ret.append(ele.data)
            return ret
        if self.use_syllabus_model:
            answer_results = super().predict_schema_answer(elements)
            ret.extend(self.get_elements_from_answer_results(answer_results))
            if self.only_use_syllabus_elements:
                return ret
        if elements and ((not self.use_syllabus_model and self.use_top_crude_neighbor) or not ret):
            high_score_element_page = elements[0]["page"]
            possible_pages = range(high_score_element_page - 1, high_score_element_page + 2)
            elements.sort(key=lambda x: x["index"])
            start, end = elements[0]["index"], elements[-1]["index"]
            if self.possible_element_counts and self.possible_element_counts > (end - start):
                start -= self.possible_element_counts // 2
                if start < 0:
                    start = 0
                end = start + self.possible_element_counts
                possible_pages = range(
                    high_score_element_page - self.top_page_offset, high_score_element_page + self.bottom_page_offset
                )
            for index in range(start, end + 1):
                _, element = self.pdfinsight.find_element_by_index(index)
                if not element or element["page"] not in possible_pages:
                    continue
                if element["type"] in ("PAGE_FOOTER", "PAGE_HEADER"):
                    continue
                if self.skip_merged_para and element["class"] == "PARAGRAPH":
                    paragraph_indices = (element["page_merged_paragraph"] or {}).get("paragraph_indices", [])
                    if paragraph_indices and element["index"] != paragraph_indices[0]:
                        continue
                ret.append(element)

        if ret:
            next_elements = self.pdfinsight.find_elements_near_by(
                index=ret[-1]["index"],
                amount=2,
                steprange=5,
                aim_types=["PARAGRAPH"],  # amount为2排除跨页段落的干扰
            )
            for ele in next_elements:
                if self.bottom_anchor_pattern.nexts(clean_txt(ele["text"])):
                    ret.append(ele)
                    break
        return sorted({x["index"]: x for x in ret}.values(), key=lambda x: x["index"])

    def get_anchor_index(
        self, all_elements, pattern, anchor_index=None, greed=True, continue_greed=False, neglect_pattern=None
    ):
        matched = False
        for element in all_elements:
            if self.is_anchor_element(element, pattern, neglect_pattern):
                anchor_index = element["temp_index"]
                matched = True
                if not greed:
                    break
            elif matched and continue_greed:
                break

        return anchor_index

    @staticmethod
    def is_anchor_element(element, pattern, neglect_pattern):
        if element["class"] == "PARAGRAPH":
            text = clean_txt(element["text"])
            if pattern.nexts(text):
                if not neglect_pattern or not neglect_pattern.nexts(text):
                    return True
        return False

    def build_answer(self, elements, column):
        page_box = self.pdfinsight.elements_outline(elements)
        element_results = [OutlineResult(page_box=page_box, element=elements[0], origin_elements=elements)]
        answer_result = self.create_result(element_results, column=column)
        return answer_result
