import json
import logging
from copy import deepcopy

from . import FinanceTableConverter, keypath_str

logger = logging.getLogger(__name__)


class SzseFintableConverter(FinanceTableConverter):
    def __init__(self, answer, fintable_schema) -> None:
        super(SzseFintableConverter, self).__init__(answer, fintable_schema)
        self.sys = self.config.SYS_SZSE
        self.table_mapping = {
            "合并资产负债表": "资产负债表",
            "合并利润表": "利润表",
            "合并现金流量表": "现金流量表",
        }

    def convert(self, *args, **kwargs):
        root_schema = self.fintable_schema["schemas"][0]
        root_path = [(root_schema["name"], 0)]
        items = []
        diff_words = set()
        for from_table, to_table in self.table_mapping.items():
            for idx, group in self.answer_node[from_table].items():
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
        if col == "报告期":
            item = deepcopy(node.data)
            item.key = keypath_str(table_path + [("报告期", 0)])
            items.append(item)
        else:
            common_col = self.config.find_common_column(to_table, self.sys, col)
            if not common_col:
                logging.warning(f"can't find common column for {col} in {to_table}")
                return []

            col_path = table_path + [(common_col, 0)]
            for sub_col in ("数值", "单位"):
                if (sub_col, 0) not in node:
                    continue
                item = deepcopy(node[sub_col, 0].data)
                item.key = keypath_str(col_path + [(sub_col, 0)])
                items.append(item)
        return items
