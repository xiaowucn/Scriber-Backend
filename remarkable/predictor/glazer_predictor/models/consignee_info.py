"""
主承销商机构信息
"""

import re
from itertools import chain

from remarkable.common.constants import TableType
from remarkable.common.pattern import PatternCollection
from remarkable.common.util import clean_txt
from remarkable.optools.table_util import P_SPACE
from remarkable.pdfinsight.parser import parse_table
from remarkable.pdfinsight.reader import PdfinsightSyllabus
from remarkable.predictor.models.syllabus_based import SyllabusBased
from remarkable.predictor.schema_answer import CellCharResult, CharResult, OutlineResult, TableResult


class ConsigneeInfo(SyllabusBased):
    P_COMPANY_IN_PARAGRAPH = PatternCollection(
        [
            r"(?P<company>五矿证券有限公司)",
            r"[(（]?[\d一二三四五六七八九十]*[)）]?[、.．\s]*(?:名称|公司名称 )?[:：]?(?P<company>[^:：]*公司)$",
        ]
    )
    P_COMPANY_IN_TITLE = re.compile(
        r"(?:(?:^[(（]?[\d一二三四五六七八九十]*[)）]?[、.．\s]*|[、/或])"
        r"[（(]?(?:牵头|联席)?(?<!副)主承销商[)）]?.*?|主承销商)"
        r"[:：、](?P<company>[^:：]*公司)$"
    )
    P_COMPANY_IN_GROUP = re.compile(r"(?:公司)?名\s*称[:：\s]*(?P<company>[^:：]*公司)$")
    P_COMPANY_IN_TABLE = [re.compile(r"名称|公司名称"), re.compile(r"(?P<company>[^:：]*公司)$")]

    P_PREFIX = re.compile(
        r"\s*(?P<prefix>(名称|住所|地址|法定代表人|联系人|联系电话|传真|邮编))[:：\s]+(?P<text>.*)\s*$"
    )

    COMPANY_FIELD = "主承销商名称"

    def predict_schema_answer(self, elements):
        answer_results = []
        syllabus_results = super(ConsigneeInfo, self).predict_schema_answer(elements)

        company_names = set()
        for syllabus_result in self.sort_syllabus_results(syllabus_results):
            for item in self.find_answer(syllabus_result[self.COMPANY_FIELD]):
                if item and item["company"].text not in company_names:
                    company_names.add(item["company"].text)
                    answer_results.append(self.create_consignee_result(item))

        return answer_results

    @classmethod
    def sort_syllabus_results(cls, syllabus_results):
        main_consignee = []
        consignee = []
        for result in syllabus_results:
            if cls.COMPANY_FIELD not in result:
                continue
            if [item for item in result[cls.COMPANY_FIELD] if "牵头" in item.text]:
                main_consignee.append(result)
            else:
                consignee.append(result)
        return main_consignee + consignee

    def create_consignee_result(self, item):
        if "info" in item:
            start = min(item["info"], key=lambda x: x["index"])["index"] - 1
            end = max(item["info"], key=lambda x: x["index"])["index"] + 1
            elements = []
            page_box = self.pdfinsight_syllabus.syl_outline({"range": (start, end)}, pdfinsight=self.pdfinsight)
            for i in page_box:
                elements.extend(i["elements"])
            if not elements:
                return None
            text = "\n".join(i["text"] for i in page_box)
            outline_result = OutlineResult(page_box=page_box, text=text, element=elements[0], origin_elements=elements)
            info_result = self.create_result([outline_result], text=text, column="主承销商机构信息")
        else:
            info_result = self.create_result([TableResult(item["table"], item["cells"])], column="主承销商机构信息")
        answer_result = {
            self.COMPANY_FIELD: [self.create_result([item["company"]], column=self.COMPANY_FIELD)],
            "主承销商机构信息": [info_result],
        }
        return answer_result

    def find_answer(self, syllabus_result):
        """
        思路：
            1.先按  公司名单独一行的段落拆分组
            2.对只有一组的 从目录标题里去找公司名称
            3.开始按组处理
                3.1 对于每个组，先检查是不是需要再次拆分（多个表格，机构数据在表格里）
                3.2 对于每个组，生成预测答案
        :param syllabus_result: 预测目录
        :return: 预测的答案
        """
        for syllabus_result_groups in self.find_element_groups(syllabus_result):
            result = []
            for group in syllabus_result_groups:
                result.extend(self.split_multi_company_in_group(group))
            if result:
                result = [
                    item
                    for item in result
                    if not isinstance(item["company"].element, dict)
                    or "分销商" not in (item["company"].element.get("text") or "")
                ]
                return result
        return []

    @classmethod
    def split_multi_company_in_table(cls, table):
        groups = []
        last_group = {"company": None, "rows": []}
        for row in table.rows:
            if row:
                row_index = row[-1].rowidx
                if row[-1].text.endswith("公司"):
                    if last_group["rows"]:
                        groups.append(last_group)
                        last_group = {"company": None, "rows": []}
                    if P_SPACE.sub("", row[0].text).startswith("名称"):
                        last_group["rows"].append(row_index)
                    last_group["company"] = row[-1]
                else:
                    last_group["rows"].append(row_index)

        if last_group["rows"]:
            groups.append(last_group)

        if len(groups) == 1 and len(groups[0]["rows"]) == len(table.raw_rows):
            yield None, table, 0, len(table.raw_rows), None
        else:
            for group in groups:
                cells = []
                if group["rows"]:
                    for row_index in group["rows"]:
                        for cell in table.rows[row_index]:
                            cells.append(cell)
                    yield cells, table, group["rows"][0], group["rows"][-1] + 1, group["company"]

    def split_multi_company_in_group(self, group):
        result = []
        table_index = 0
        for item in group["info"]:
            if item["class"] != "TABLE":
                continue
            table = parse_table(item, tabletype=TableType.TUPLE.value, pdfinsight_reader=self.pdfinsight)
            for cells, table_item, start_row, _, company_cell in self.split_multi_company_in_table(table):
                table_index += 1
                if not company_cell:
                    # 如果是第一个表格部分 那么 公司名可能在标题里
                    if table_index == 1 and group["company"]:
                        result.append({"company": group["company"], "table": table_item.element, "cells": cells})
                        continue

                    if not table_item.rows:
                        continue

                    row = table_item.rows[start_row]
                    if not row:
                        continue

                    if len(row) < 2:
                        prefix_matched = self.P_PREFIX.search(row[0].text)
                        if prefix_matched:
                            result.append(
                                {
                                    "company": CellCharResult(
                                        element=table_item.element,
                                        cells=[row[0]],
                                        chars=row[0].raw_cell["chars"][slice(*prefix_matched.span("text"))],
                                    ),
                                    "table": table_item.element,
                                    "cells": cells,
                                }
                            )
                    else:
                        if self.P_COMPANY_IN_TABLE[0].search(P_SPACE.sub("", row[0].text)):
                            matched = self.P_COMPANY_IN_TABLE[1].search(row[1].text)
                            if matched:
                                result.append(
                                    {
                                        "company": CellCharResult(
                                            element=table_item.element,
                                            cells=[row[1]],
                                            chars=row[1].raw_cell["chars"][slice(*matched.span("company"))],
                                        ),
                                        "table": table_item.element,
                                        "cells": cells,
                                    }
                                )
                else:
                    # 如果表格按公司名分段了，那么分段处就是公司名
                    dst_chars = self.get_dst_chars_from_pattern(self.P_COMPANY_IN_TABLE[1], cell=company_cell)
                    result.append(
                        {
                            "company": CellCharResult(
                                element=table_item.element,
                                cells=[company_cell],
                                chars=dst_chars or company_cell.raw_cell["chars"],
                            ),
                            "table": table_item.element,
                            "cells": cells,
                        }
                    )
        if result:
            return result
        if group and not group["company"]:
            return []
        return [group]

    def find_element_groups(self, predictor_results):
        for item in predictor_results:
            # 找到目录下所有段落
            result_element = item.element_results[0].element
            syllabus = self.pdfinsight_syllabus.elt_syllabus_dict.get(result_element["index"])
            if not syllabus:
                continue
            page_boxes = PdfinsightSyllabus.syl_outline(
                syllabus, self.pdfinsight, include_title=self.config.get("include_title", False)
            )
            groups = []
            last_group = {"company": None, "info": []}
            elements = []
            for element in chain(*[page_box["elements"] for page_box in page_boxes]):
                if element.get("fragment"):
                    continue
                if element["class"] == "TABLE" and self.get_config("table_regarded_as_paras"):
                    elements.extend(self.get_paragraphs_from_table(element))
                else:
                    elements.append(element)

            for element in elements:
                # 先按 公司独在一行的段落分组
                if element["class"] == "PARAGRAPH" and self.P_COMPANY_IN_PARAGRAPH.nexts(element["text"]):
                    matched = self.P_COMPANY_IN_PARAGRAPH.nexts(element["text"])
                    if last_group["info"]:
                        groups.append(last_group)
                    last_group = {
                        "company": CharResult(element, element["chars"][slice(*matched.span("company"))]),
                        "info": [],
                    }

                    # 如果 公司没有单独写一行 直接 名称:xxx公司，名称也在信息里
                    if self.P_COMPANY_IN_GROUP.search(element["text"]):
                        last_group["info"].append(element)
                else:
                    last_group["info"].append(element)

            if last_group["info"]:
                groups.append(last_group)

            # 第一个item 没有找到公司名字，名字可能在标题里
            if groups and not groups[0]["company"]:
                matched = self.P_COMPANY_IN_TITLE.search(clean_txt(result_element["text"]))
                if matched:
                    groups[0]["company"] = CharResult(
                        result_element, result_element["chars"][slice(*matched.span("company"))]
                    )
            yield groups

    def get_dst_chars_from_pattern(self, pattern, cell, group_key="company"):
        if matcher := PatternCollection(pattern).nexts(clean_txt(cell.text)):
            return self.get_dst_chars_from_matcher(matcher, cell.raw_cell, group_key=group_key)
        return None
