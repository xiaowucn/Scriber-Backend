"""根据特性重新组合表格， 如：
原表格：
| x | a | a' |
| - | - | - |
| 1 | 2 | 3 |
| x | d | d' |
重组为：
table_1:       table_2:
| x | a |       | x | a' |
| - | - |       | - | - |
| 1 | 2 |       | 1 | 3 |
| x | d |       | x | d' |
"""

from copy import deepcopy

from remarkable.common.pattern import PatternCollection
from remarkable.common.util import clean_txt
from remarkable.predictor.models.table_row import TableRow
from remarkable.predictor.schema_answer import PredictorResult


class TableRegroup(TableRow):
    @property
    def main_col(self):
        """主列模式，用于识别需要保留在每个子表格中的列"""
        return PatternCollection(self.get_config("main_col", default=[]))

    @property
    def assistant_col(self):
        """辅助列模式，用于识别需要分组的列"""
        return PatternCollection(self.get_config("assistant_col", default=[]))

    def prepare_table(self, element) -> tuple[list[dict], list[dict]]:
        """
        根据特性重新组合表格

        约束条件:
        1. 主列和辅助列必须同时存在
        2. 主列只能有一列
        3. 辅助列必须大于1列

        Args:
            element: 原始表格元素

        Returns:
            tuple[list[dict], list[dict]]: (重组后的表格列表, 对应的元素列表)
        """
        # 识别主列和辅助列
        main_cols, assistant_cols = self._identify_columns(element)

        # 验证约束条件
        if not self._validate_columns(main_cols, assistant_cols):
            # 如果不满足约束条件，返回空结果
            return [], []

        # 根据辅助列分组重组表格
        regrouped_tables = self._regroup_tables(element, main_cols[0], assistant_cols)

        # 为每个重组后的表格创建对应的元素
        regrouped_elements = [element] * len(regrouped_tables)

        return regrouped_tables, regrouped_elements

    def _validate_columns(self, main_cols: list[int], assistant_cols: list[int]) -> bool:
        """
        验证列的约束条件

        约束条件:
        1. 主列和辅助列必须同时存在
        2. 主列只能有一列
        3. 辅助列必须大于1列

        Args:
            main_cols: 主列索引列表
            assistant_cols: 辅助列索引列表

        Returns:
            bool: 是否满足约束条件
        """
        # 检查主列和辅助列是否同时存在
        if not main_cols or not assistant_cols:
            return False

        # 检查主列只能有一列
        if len(main_cols) != 1:
            return False

        # 检查辅助列必须大于1列
        if len(assistant_cols) <= 1:
            return False

        return True

    def _identify_columns(self, element) -> tuple[list[int], list[int]]:
        """
        识别主列和辅助列

        Args:
            element: 表格元素

        Returns:
            tuple[list[int], list[int]]: (主列索引列表, 辅助列索引列表)
        """
        main_cols = []
        assistant_cols = []

        # 遍历第一行，识别列类型
        for index, cell in element["cells"].items():
            if not index.startswith("0_"):  # 只处理第一行
                continue
            if cell.get("dummy") is True:
                continue

            col_idx = int(index.split("_")[1])
            cell_text = cell.get("text", "").strip()

            # 检查是否为主列
            if self.main_col.nexts(cell_text):
                main_cols.append(col_idx)
            # 检查是否为辅助列
            elif self.assistant_col.nexts(clean_txt(cell_text)):
                assistant_cols.append(col_idx)

        return sorted(main_cols), sorted(assistant_cols)

    def _regroup_tables(self, element, main_col: int, assistant_cols: list[int]) -> list[dict]:
        """
        根据主列和辅助列重组表格

        Args:
            element: 原始表格元素
            main_col: 主列索引
            assistant_cols: 辅助列索引列表

        Returns:
            list[dict]: 重组后的表格列表
        """
        regrouped_tables = []

        # 为每个辅助列创建一个新表格
        for assistant_col in assistant_cols:
            new_table = self._create_regrouped_table(element, main_col, assistant_col)
            if new_table:
                regrouped_tables.append(new_table)

        return regrouped_tables

    def _create_regrouped_table(self, element, main_col: int, assistant_col: int) -> dict | None:
        """
        创建重组后的表格，包含主列和指定的辅助列

        Args:
            element: 原始表格元素
            main_col: 主列索引
            assistant_col: 辅助列索引

        Returns:
            Optional[dict]: 重组后的表格，如果没有有效数据则返回None
        """
        new_element = deepcopy(element)
        new_element["cells"] = {}

        # 确定新表格的列映射
        target_cols = [main_col, assistant_col]
        target_cols = sorted(set(target_cols))  # 去重并排序

        # 创建列索引映射
        col_mapping = {}
        for new_col_idx, old_col_idx in enumerate(target_cols):
            col_mapping[old_col_idx] = new_col_idx

        # 复制相关列的单元格
        for index, cell in element["cells"].items():
            row_idx, col_idx = map(int, index.split("_"))

            if col_idx in col_mapping:
                new_col_idx = col_mapping[col_idx]
                new_index = f"{row_idx}_{new_col_idx}"

                new_cell = deepcopy(cell)
                new_cell["index"] = new_index
                new_cell["col"] = new_col_idx

                new_element["cells"][new_index] = new_cell

        # 如果新表格没有单元格，返回None
        if not new_element["cells"]:
            return None

        # 使用父类的prepare_table方法处理新表格
        return super().prepare_table(new_element)

    def predict_schema_answer(self, elements) -> list[dict[str, list[PredictorResult]]]:
        """预测模式答案，支持拆分表格的处理"""
        answer_results = []
        elements = self.revise_elements(elements)

        if self.multi_elements:
            elements.sort(key=lambda x: x["index"])

        for element in elements:
            if element["class"] != "TABLE":
                # AutoModel中 filter_elements_by_target设置为None 所以这里需要再次过滤下
                continue
            if self.neglect_title_pattern and self.neglect_title_pattern.nexts(clean_txt(element.get("title"))):
                continue
            prepared_tables, split_elements = self.prepare_table(element)
            if not prepared_tables:
                continue

            # 处理表格列表（统一为列表类型）
            for index, table in enumerate(prepared_tables):
                super().process_table_items(table, split_elements[index], answer_results)

        return answer_results
