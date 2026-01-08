import logging
import re

from remarkable.common.constants import TableType
from remarkable.common.pattern import PatternCollection
from remarkable.common.util import clean_txt
from remarkable.pdfinsight.parser import parse_table
from remarkable.predictor.csc_poc_predictor.schemas.dollar_debt_schema import isin_pattern
from remarkable.predictor.models.table_row import TableRow
from remarkable.predictor.schema_answer import CellCharResult

logger = logging.getLogger(__name__)

isin_flag_pattern = PatternCollection(r"isin", re.I)
black_isin_flag_pattern = PatternCollection(r"^\[●\]$", re.I)


class Isin(TableRow):
    def predict_schema_answer(self, elements):
        ret = []
        if not elements:
            return ret
        elements = self.get_elements(elements)
        for element in elements:
            table = parse_table(
                element,
                tabletype=TableType.TUPLE.value,
                pdfinsight_reader=self.pdfinsight,
            )
            find_flag = False
            flag_index = 0
            for idx, row in enumerate(table.rows):
                row_texts = "".join([clean_txt(cell.text) for cell in row if not cell.dummy])
                matcher = PatternCollection(isin_pattern, re.I).nexts(row_texts)
                flag_matcher = isin_flag_pattern.nexts(row_texts)
                if not matcher and not flag_matcher:
                    continue
                for cell in row:
                    clean_text = clean_txt(cell.text)
                    if not find_flag:
                        if isin_flag_pattern.nexts(clean_text):
                            find_flag = True
                            flag_index = cell.rowidx
                    else:
                        matchers = PatternCollection(isin_pattern, re.I).finditer(clean_text)
                        for matcher in matchers:
                            if black_isin_flag_pattern.nexts(matcher.group()):
                                continue
                            dst_chars = self.get_dst_chars_from_matcher(matcher, cell.raw_cell)
                            element_results = CellCharResult(element, dst_chars, [cell])
                            ret.append(self.create_result([element_results], column=self.schema.name))
                            logger.info(f"find isin from page: {element['page']}")
                if len(ret) >= 2:
                    break
                if find_flag and idx > flag_index + 3:
                    break
            if ret:  # 一个表格里预测到就跳出
                break
        return ret

    def get_elements(self, elements):
        # 根据初步定位的一个元素 一般是发行事项页的表格 page < 20
        # 往下找几页 定位到对应的表格
        ret = []
        first_crude_element = elements[0]
        first_crude_element_index = first_crude_element["index"]
        for idx in range(first_crude_element_index, first_crude_element_index + 10):
            ele_type, element = self.pdfinsight.find_element_by_index(idx)
            if ele_type != "TABLE":
                continue
            if element["page"] > 40:
                break
            ret.append(element)
        return ret
