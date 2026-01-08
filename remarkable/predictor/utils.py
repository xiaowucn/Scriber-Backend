import functools
import gzip
import logging
import os
import re
from functools import lru_cache
from typing import Pattern

import attr
import numpy as np

from remarkable.common.constants import TableType
from remarkable.common.pattern import PatternCollection
from remarkable.common.util import clean_txt, kmeans
from remarkable.config import project_root
from remarkable.pdfinsight.parser import parse_table
from remarkable.pdfinsight.reader import PdfinsightReader


def is_chinese_address(address):
    pattern_path = os.path.join(project_root, "data", "districts_cn.gz")
    return make_pattern(pattern_path, is_path=True).search(address)


def is_overseas_assets(content):
    return "否" if is_chinese_address(content) else "是"


def whether_or_not(content):
    """
    通用的`是/否`逻辑
    """
    if re.search(r"[不无未否]", content):
        return "否"
    return "是"


def is_correlation(content):
    """
    是否有关联关系
    """
    if re.search(r"子公司", content):
        return "是"
    return "否"


def guarantee_type(content, multi=False):
    """
    担保类型：借贷/买卖/货物运输
    """
    val_patterns = [("借贷", [r"(借款|借贷|授信|贷款)"]), ("买卖", [r"(买|卖|销售|采购)"]), ("货物运输", [r"货物运输"])]

    enum_value = []
    for val, patterns in val_patterns:
        if any(re.search(reg, content) for reg in patterns):
            enum_value.append(val)
            if not multi:
                break
    return enum_value


def guarantee_method(content, multi=False):
    """
    担保方式：一般责任/连带责任
    """
    val_patterns = [("一般责任", [r"一般责任"]), ("连带责任", [r"连带责任"])]
    enum_value = []
    for val, patterns in val_patterns:
        if any(re.search(reg, content) for reg in patterns):
            enum_value.append(val)
            if not multi:
                break
    return enum_value


def subject_type(content):
    """
    主体类型
    """
    val_patterns = [
        ("控股股东", [r"控股股东"]),
        ("合计持有5%以上股份的股东及其一致行动人", [r"5%以上"]),
        ("董事", [r"董事"]),
        ("监事", [r"监事"]),
        ("高级管理人员", [r"(高级管理人员|高管)"]),
        ("大股东", [r"大股东"]),
    ]
    enum_value = None
    for val, patterns in val_patterns:
        if any(re.search(reg, content) for reg in patterns):
            enum_value = val
            break
    return enum_value


def contribution_method(content):
    """
    出资方式
    """
    val_patterns = [
        (
            "战略合作",
            [
                r"(共同.*增资|合作|参与)",
            ],
        ),
        ("认购基金份额", [r"认购.*基金"]),
        ("成立私募基金", [r"(发起|设立).*基金"]),
        ("签订财务顾问协议", [r"签[订署]"]),
        ("其他", [r".*"]),
    ]
    enum_value = None
    for val, patterns in val_patterns:
        if any(re.search(reg, content) for reg in patterns):
            enum_value = val
            break
    return enum_value


def item_category(content, multi=False):
    """
    事项类别：付息/兑付/部分兑付
    """
    val_patterns = [("付息", [r"付息"]), ("部分兑付", [r"部分兑付"]), ("兑付", [r"兑付"])]
    enum_value = []
    for val, patterns in val_patterns:
        if any(re.search(reg, content) for reg in patterns):
            enum_value.append(val)
            if not multi:
                break
    return enum_value


def whether_review(content, multi=False):
    """
    审议情况：尚待审议/无需审议/其他
    """
    val_patterns = [("尚待审议", [r"尚[待需].*审议"]), ("无需审议", [r"[无不]需.*审议"]), ("其他", [r".*"])]
    enum_value = []
    for val, patterns in val_patterns:
        if any(re.search(reg, content) for reg in patterns):
            enum_value.append(val)
            if not multi:
                break
    return enum_value


def vote(content, multi=False):
    """
    投票情况：反对/弃权
    """
    val_patterns = [
        ("反对", [r"反对"]),
        ("弃权", [r"弃权"]),
    ]
    enum_value = []
    for val, patterns in val_patterns:
        if any(re.search(reg, content) for reg in patterns):
            enum_value.append(val)
            if not multi:
                break
    return enum_value


def convert_list_to_tuple(func):
    @functools.wraps(func)
    def wrapper(obj_in, **kwargs):
        if isinstance(obj_in, list):
            obj_in = tuple(obj_in)
        return func(obj_in, **kwargs)

    return wrapper


@convert_list_to_tuple
@lru_cache(maxsize=1024)
def make_pattern(obj_in: str | None | Pattern | tuple, is_path=False) -> PatternCollection:
    if is_path:
        if not os.path.exists(obj_in):
            raise FileNotFoundError
        with gzip.open(obj_in, "rt") as file_obj:
            obj_in = rf"{file_obj.read().rstrip()}"
    return PatternCollection(obj_in)


def calc_distance(element, target_element):
    return element["index"] - target_element["index"]


def filter_table_cross_page(elements):
    """
    过滤重复的跨页表格
    """
    return [e for e in elements if e.get("fragment", False) is False]


def get_elements_from_kmeans(elements, classification_by="score"):
    if not elements:
        return []
    if len(elements) < 3:
        return elements
    nums = [[element[classification_by]] for element in elements]
    kmeans_result = kmeans(np.asarray(nums))
    ret = [element for num, element in zip(kmeans_result, elements) if num == 0]
    return ret


def get_box_distance(box1, box2):
    ret = (box1["box_left"] - box2["box_left"]) ** 2 + (box1["box_top"] - box2["box_top"]) ** 2
    return ret**0.5


class SafeFileName:
    char_map = {
        "/": "#slash#",
        " ": "#space#",
        ".": "#dot#",
        "-": "#minus#",
        "+": "#plus#",
        "@": "#at#",
        "*": "#asterisk#",
        "|": "#or#",
        "&": "#and#",
        ":": "#colon#",
    }
    reverse_char_map = {v: k for k, v in char_map.items()}

    @staticmethod
    def _replace(src_str, char_map):
        for src, dst in char_map.items():
            src_str = src_str.replace(src, dst)
        return src_str

    @classmethod
    def escape(cls, name_str):
        return cls._replace(name_str, cls.char_map)

    @classmethod
    def restore(cls, escaped_str):
        return cls._replace(escaped_str, cls.reverse_char_map)


@attr.s
class ElementCollector:
    elements: list = attr.ib()  # 初步定位元素块 已经经过阈值过滤
    pdfinsight: PdfinsightReader = attr.ib()

    def collect(
        self,
        pattern,
        special_class=None,
        multi_elements=None,
        neglect_pattern=None,
        neglect_title_above_pattern=None,
        add_additional=False,
        filter_later_elements=False,
    ):
        ret = []
        if not self.elements:
            return []
        if pattern.patterns or neglect_pattern.patterns:
            index_in_ret = []
            for element in self.elements:
                element_result = self.parse_element(
                    element, special_class, pattern, neglect_pattern, neglect_title_above_pattern
                )
                if element_result:
                    ret.append(element_result)
                    index_in_ret.append(element["index"])
                if not multi_elements and ret:
                    break

            if add_additional:
                additional = self.get_elements_from_full_pages(
                    index_in_ret, special_class, pattern, neglect_pattern, neglect_title_above_pattern, multi_elements
                )
                ret += additional
        else:
            ret = self.elements
        if len(ret) > 1 and filter_later_elements:
            # 过滤位置靠后的元素块 filter_later_elements
            if len(ret) == 2 and ret[0]["page"] + 1 == ret[1]["page"]:
                # 两个元素块是连续的 可能是merge_table
                return ret
            ret.sort(key=lambda x: x["score"], reverse=True)  # 按照score降序排列 kmeans分类后 返回的是分数高的一类
            ret = get_elements_from_kmeans(ret, classification_by="score")
            if len(ret) > 2:
                ret = get_elements_from_kmeans(ret, classification_by="score")
        return ret

    def parse_element(self, element, special_class, pattern, neglect_pattern, neglect_title_above_pattern):
        parsed_table = None
        element_class = element["class"]
        special_title_patterns = pattern if pattern.patterns else None
        if special_class and element_class != special_class:
            return None
        if element_class == "TABLE":
            table_titles, parsed_table = self.get_table_titles(element, special_title_patterns=special_title_patterns)
            texts = [clean_txt(i) for i in table_titles]
        elif element_class == "PARAGRAPH":
            texts = [clean_txt(element["text"])]
        else:
            return None
        matcher = True
        if pattern.patterns:
            for text in texts:
                matcher = pattern.nexts(text)
                if matcher:
                    break
        neglect_matcher = False
        if neglect_pattern.patterns:
            for text in texts:
                neglect_matcher = neglect_pattern.nexts(text)
                if neglect_matcher:
                    break
        if element_class == "TABLE" and matcher and neglect_title_above_pattern:
            # https://gitpd.paodingai.com/cheftin/docs_scriber/-/issues/639#note_174526
            above_para = self.get_above_para(parsed_table, element)
            if above_para and neglect_title_above_pattern.nexts(above_para):
                matcher = False
        if matcher and not neglect_matcher:
            return element
        return None

    def get_table_titles(self, element, special_title_patterns=None):
        table_titles = set()
        if element.get("title"):
            table_titles.add(element.get("title"))
        try:
            _, element = self.pdfinsight.find_element_by_index(element["index"])
            table = parse_table(
                element,
                tabletype=TableType.TUPLE,
                pdfinsight_reader=self.pdfinsight,
                special_title_patterns=special_title_patterns,
            )
        except Exception as e:
            logging.exception(e)
            return table_titles, None
        if table.title:
            table_titles.add(table.title.text)
        return table_titles, table

    def get_above_para(self, parsed_table, element):
        if not parsed_table or not parsed_table.title:
            title_element_index = element["index"] - 1
        else:
            title_element_index = parsed_table.title.element.get("index")
        _, above_element = self.pdfinsight.find_element_by_index(title_element_index - 1)
        if not above_element or above_element["class"] != "PARAGRAPH":
            return None
        return clean_txt(above_element["text"])

    def get_elements_from_full_pages(
        self,
        index_in_ret,
        special_class,
        pattern,
        neglect_pattern,
        neglect_title_above_pattern,
        multi_elements,
    ):
        additional = []
        # todo 这里会让提取的整体时间变长 需要优化下 添加下面的逻辑是为了规避表格解析的问题
        for items in self.pdfinsight.element_dict.values():
            for ele_info in items:
                element = ele_info.data
                if element["index"] in index_in_ret:
                    continue
                element_result = self.parse_element(
                    element, special_class, pattern, neglect_pattern, neglect_title_above_pattern
                )
                if element_result:
                    additional.append(element_result)
                if not multi_elements and additional:
                    break
            if not multi_elements and additional:
                break

        return additional


def classify_by_kmeans(elements, classification_by="score"):
    if not elements:
        return []
    if len(elements) < 3:
        return elements
    nums = [[element[classification_by]] for element in elements]
    items = [element[classification_by] for element in elements]
    if len(set(items)) == 1:
        return elements[:1]
    kmeans_result = kmeans(np.asarray(nums))
    ret = [element for num, element in zip(kmeans_result, elements) if num == 0]
    return ret
