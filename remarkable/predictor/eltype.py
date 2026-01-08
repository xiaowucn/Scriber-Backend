import logging
from enum import Enum, unique

from remarkable.common.constants import IntEnumBase, TableType


class ElementType(IntEnumBase):
    """
    元素块类型
    """

    # NOTE: 枚举值不允许为`0`
    PARAGRAPH = (1, "paragraph", "段落")
    TABLE = (10, "table", "表格")
    TABLE_TUPLE = (2, "table_tuple", "表格-元组（行头、列头均会当作特征）")
    TABLE_KV = (3, "table_kv", "表格-键值对（只有两列的表格）")
    TABLE_ROW = (4, "table_row", "表格-行（只把行头作为特征）")
    TABLE_ONE_COL = (5, "table_one_col", "表格-单列（相邻的段落被识别成只有一列的表格）")
    STAMP = (20, "stamp", "印章")


@unique
class ElementClass(Enum):
    PARAGRAPH = "PARAGRAPH"
    TABLE = "TABLE"
    PAGE_HEADER = "PAGE_HEADER"
    PAGE_FOOTER = "PAGE_FOOTER"
    IMAGE = "IMAGE"
    STAMP = "STAMP"
    INFOGRAPHIC = "INFOGRAPHIC"
    SHAPE = "SHAPE"
    FOOTNOTE = "FOOTNOTE"


class ElementClassifier:
    PARA_LIKE = {"PARAGRAPH", "INFOGRAPHIC", "SHAPE", "IMAGE", "FOOTNOTE", "PAGE_HEADER", "PAGE_FOOTER"}

    @classmethod
    def get_type(cls, element: dict) -> ElementType | None:
        # TODO: more table types
        if element["class"] == "TABLE":
            return cls.table_type(element)
        if element["class"] in ("PARAGRAPH", "PAGE_HEADER", "PAGE_FOOTER", "FOOTNOTE"):
            return ElementType.PARAGRAPH
        if element["class"] == "STAMP":
            return ElementType.STAMP
        if element["class"] not in ("IMAGE", "INFOGRAPHIC", "SHAPE"):
            logging.warning(f"Can't distinguish the element type for {element['class']}")

    @classmethod
    def table_type(cls, element: dict) -> ElementType:
        from remarkable.pdfinsight.parser import parse_table

        table = parse_table(element, tabletype=TableType.TUPLE.value)
        # todo: table_kv 暂未判断四列的情形
        if all(len(row) == 2 for row in table.rows):  # 表格每一行均有两列
            if all(
                all(not cell.dummy for cell in row) for row in table.rows[1:]
            ):  # 允许第一行合并 有可能是汇总性的表头
                return ElementType.TABLE_KV
        if all(len(row) == 1 for row in table.rows):
            return ElementType.TABLE_ONE_COL
        return ElementType.TABLE_TUPLE  # 默认返回tuple auto模型会根据model是否有值来判断使用table_row还是table_tuple

    @classmethod
    def like_paragraph(cls, element):
        return element["class"] in cls.PARA_LIKE

    @classmethod
    def is_table(cls, element):
        return element["class"] == "TABLE"

    @classmethod
    def is_stamp(cls, element):
        return element["class"] == "STAMP"
