import json
import logging
from collections import Counter
from copy import deepcopy

from . import FinanceTableConverter, keypath_str

logger = logging.getLogger(__name__)


class CsrcFintableConverter(FinanceTableConverter):
    def __init__(self, answer, fintable_schema) -> None:
        super(CsrcFintableConverter, self).__init__(answer, fintable_schema)
        self.sys = self.config.SYS_CSRC
        self.table_mapping = {
            "合并资产负债表": "资产负债表",
            "合并利润表": "利润表",
            "合并现金流量表": "现金流量表",
        }
        self.groupid_sequence = Counter()

    def convert(self, *args, **kwargs):
        root_schema = self.fintable_schema["schemas"][0]
        root_path = [(root_schema["name"], 0)]
        items = []

        diff_words = set()
        for from_table, to_table in self.table_mapping.items():
            group_keys = []
            for item in self.answer_node[from_table].values():
                datas = self.handle_item(item, to_table, root_path, group_keys)
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

    def handle_item(self, item, to_table, root_path, group_keys):
        items = []
        item_date = item["报表日期"].get(0)
        item_name = item["项目"].get(0)
        item_value = item["金额"].get(0)
        item_unit = item["货币单位"].get(0)

        if item_date is None or item_name is None:
            return []

        col = item_name.data.plain_text
        common_col = self.config.find_common_column(to_table, self.sys, col)
        if not common_col:
            logger.warning(f"can't find common column for {col} in {to_table}")
            return []

        group_key = item_date.data.plain_text
        new_group = False
        if group_key not in group_keys:
            group_keys.append(group_key)
            new_group = True
        table_path = root_path + [(to_table, group_keys.index(group_key))]

        if new_group:
            item = deepcopy(item_date.data)
            item.key = keypath_str(table_path + [("报告期", 0)])
            items.append(item)
        if item_value is not None:
            item = deepcopy(item_value.data)
            item.key = keypath_str(table_path + [(common_col, 0), ("数值", 0)])
            items.append(item)
        if item_unit is not None:
            item = deepcopy(item_unit.data)
            item.key = keypath_str(table_path + [(common_col, 0), ("单位", 0)])
            items.append(item)
        return items
