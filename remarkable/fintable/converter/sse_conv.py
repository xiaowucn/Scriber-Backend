import json
import logging
from collections import Counter
from copy import deepcopy

from . import FinanceTableConverter, keypath_str

logger = logging.getLogger(__name__)


class SseFintableConverter(FinanceTableConverter):
    def __init__(self, answer, fintable_schema) -> None:
        super(SseFintableConverter, self).__init__(answer, fintable_schema)
        self.sys = self.config.SYS_SSE
        self.table_mapping = {
            "IPO资产负债表（合并）": "资产负债表",
            "IPO利润表（合并）": "利润表",
            "IPO现金流量表（合并）": "现金流量表",
            "IPO资产负债表（母公司）": "资产负债表",
            "IPO利润表（母公司）": "利润表",
            "IPO现金流量表（母公司）": "现金流量表",
        }
        self.groupid_sequence = Counter()

    def convert(self, *args, **kwargs):
        root_schema = self.fintable_schema["schemas"][0]
        root_path = [(root_schema["name"], 0)]
        items = []
        diff_words = set()
        for from_table, to_table in self.table_mapping.items():
            for _, group in self.answer_node[from_table].items():
                idx = self.groupid_sequence[to_table]
                self.groupid_sequence.update([to_table])
                table_path = root_path + [(to_table, idx)]
                for (col, _), node in group.items():
                    datas = self.handle_node(node, col, table_path, to_table)
                    for data in datas:
                        schema_word = json.loads(data["key"])[2].split(":")[0]
                        if schema_word not in self.all_schema_orders:
                            diff_words.add(schema_word)
                            continue
                        items.append(data)

        if diff_words:
            logger.warning(f"col not found in schema, {sorted(diff_words)}")

        fintable_answer = {
            "schema": self.fintable_schema,
            "userAnswer": {
                "items": [i.to_dict() for i in items],
                "version": "2.2",
            },
        }

        return fintable_answer

    def handle_node(self, node, col, table_path, to_table):
        items = []
        if col == "年度":
            common_col = "报告期"
            item = deepcopy(node.data)
            item.key = keypath_str(table_path + [(common_col, 0)])
            items.append(item)
        elif col == "币种":
            return []
        else:
            common_col = self.config.find_common_column(to_table, self.sys, col)
            if not common_col:
                logging.warning(f"can't find common column for {col} in {to_table}")
                return []
            if not node.data["data"][0]:
                logging.warning(f"{col} answer is null")
                return []
            item = deepcopy(node.data)
            item.key = keypath_str(table_path + [(common_col, 0), ("数值", 0)])
            items.append(item)
        return items
