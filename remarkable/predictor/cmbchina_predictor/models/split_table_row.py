"""根据特殊场景拆分表格为多个表格， 如：
原表格：
| a | b | a | b' |
| - | - | - | - |
| 1 | 2 | 3 | 4 |
| x | y | x' | y' |
拆分成：
table_1:        table_2:
| a | b |       | a | b' |
| - | - |       | - | - |
| 1 | 2 |       | 3 | 4 |
| x | y |       | x' | y' |
"""

from copy import deepcopy

from remarkable.common.pattern import PatternCollection
from remarkable.common.util import clean_txt
from remarkable.predictor.models.table_row import TableRow
from remarkable.predictor.schema_answer import PredictorResult


class SplitTableRow(TableRow):
    @property
    def split_table(self):
        return PatternCollection(self.get_config("split_table"))

    def prepare_table(self, element):
        """准备表格，统一返回表格列表"""
        if not self.split_table:
            # 没有拆分配置，返回单个表格的列表
            table = super().prepare_table(element)
            return [table], [element]

        # 检查是否需要拆分表格
        split_type, split_positions = self._find_split_positions(element)
        if split_type is None or not split_positions:
            # 不需要拆分，返回单个表格的列表
            table = super().prepare_table(element)
            return [table], [element]

        # 根据拆分类型进行拆分
        split_elements = self._split_table_by_type(element, split_positions, split_type)

        # 对每个拆分后的表格调用父类的prepare_table方法
        prepared_tables = []
        _fix_split_elements = []
        for split_element in split_elements:
            table = super().prepare_table(split_element)
            if table:
                prepared_tables.append(table)
                _fix_split_elements.append(split_element)

        return prepared_tables, _fix_split_elements

    def _find_split_positions(self, element) -> tuple[str, list[int]]:
        """找到表格拆分位置，优先左右拆分，其次上下拆分
        返回: (拆分类型, 拆分位置列表)
        拆分类型: 'horizontal' 表示左右拆分, 'vertical' 表示上下拆分
        """
        # 先尝试左右拆分（水平拆分）
        horizontal_positions = self._find_horizontal_split_positions(element)
        if horizontal_positions:
            return "horizontal", horizontal_positions

        # 如果左右拆分不可行，尝试上下拆分（垂直拆分）
        vertical_positions = self._find_vertical_split_positions(element)
        if vertical_positions:
            return "vertical", vertical_positions

        return None, []

    def _record_position(
        self, cell: dict[str, dict], header_texts: dict[str, int], split_cols_row: list[int], is_row: bool
    ):
        cell_text = clean_txt(cell.get("text", ""))
        num = cell["row"] if is_row else cell["col"]
        if match := self.split_table.nexts((cell_text)):
            if "dst" in match.groupdict():
                c_start, c_end = match.span("dst")
                cell_text = cell_text[c_start:c_end]

            if cell_text in header_texts:
                # 发现重复的表头，记录拆分位置
                split_cols_row.append(num)
            else:
                header_texts[cell_text] = num

    def _find_horizontal_split_positions(self, element) -> list[int]:
        """找到左右拆分位置，基于第一行重复的表头模式"""
        split_cols = []
        header_texts = {}

        # 收集第一行的所有单元格文本和列位置
        sorted_cells = sorted(element["cells"].values(), key=lambda x: (x["row"], x["col"]))
        for cell in sorted_cells:
            if not cell["row"] == 0:
                continue
            if cell.get("dummy") is True:
                continue
            self._record_position(cell, header_texts, split_cols, False)

        return sorted(split_cols)

    def _find_vertical_split_positions(self, element) -> list[int]:
        """找到上下拆分位置，基于匹配列的重复表头模式"""
        # 首先找到第一行中与split_table匹配的列
        matching_cols = self._find_matching_columns_in_first_row(element)
        if not matching_cols:
            return []

        split_rows = []

        # 对每个匹配的列，查找重复的表头模式
        for col_idx in matching_cols:
            header_texts = {}

            # 收集该列的所有单元格文本和行位置
            for index, cell in element["cells"].items():
                if not index.endswith(f"_{col_idx}"):  # 指定列
                    continue
                if cell.get("dummy") is True:
                    continue

                self._record_position(cell, header_texts, split_rows, True)

        return sorted(set(split_rows))  # 去重并排序

    def _find_matching_columns_in_first_row(self, element) -> list[int]:
        """找到第一行中与split_table匹配的列索引"""
        matching_cols = []

        # 遍历第一行的所有单元格
        for index, cell in element["cells"].items():
            if not index.startswith("0_"):  # 第一行
                continue
            if cell.get("dummy") is True:
                continue

            col_idx = int(index.split("_")[1])
            cell_text = cell.get("text", "").strip()

            if self.split_table.nexts(cell_text):
                matching_cols.append(col_idx)

        return sorted(matching_cols)

    def _split_table_by_type(self, element, split_positions: list[int], split_type: str) -> list[dict]:
        """根据拆分类型和位置将表格拆分为多个子表格

        Args:
            element: 原始表格元素
            split_positions: 拆分位置列表
            split_type: 拆分类型，'horizontal' 表示左右拆分，'vertical' 表示上下拆分

        Returns:
            拆分后的子表格列表
        """
        if not split_positions:
            return [element]

        ranges = self._calculate_split_ranges(element, split_positions, split_type)
        split_elements = []
        for start, end in ranges:
            sub_element = self._create_sub_table(element, start, end, split_type)
            if sub_element:
                split_elements.append(sub_element)

        return split_elements

    def _calculate_split_ranges(self, element, split_positions: list[int], split_type: str) -> list[tuple[int, int]]:
        """计算拆分范围

        Args:
            element: 原始表格元素
            split_positions: 拆分位置列表
            split_type: 拆分类型，'horizontal' 或 'vertical'

        Returns:
            拆分范围列表，每个元素为 (start, end) 元组
        """
        ranges = []
        start = 0

        for split_pos in split_positions:
            ranges.append((start, split_pos))
            start = split_pos

        # 添加最后一个范围
        if split_type == "horizontal":
            max_index = max(int(idx.split("_")[1]) for idx in element["cells"].keys()) + 1
        else:  # vertical
            max_index = max(int(idx.split("_")[0]) for idx in element["cells"].keys()) + 1

        ranges.append((start, max_index))
        return ranges

    def _create_sub_table(self, element, start: int, end: int, split_type: str) -> dict | None:
        """创建子表格，包含指定范围的单元格

        Args:
            element: 原始表格元素
            start: 起始位置（列索引或行索引）
            end: 结束位置（列索引或行索引）
            split_type: 拆分类型，'horizontal' 表示按列拆分，'vertical' 表示按行拆分

        Returns:
            子表格元素，如果没有单元格则返回None
        """
        sub_element = deepcopy(element)
        sub_element["cells"] = {}

        if split_type == "horizontal":
            # 水平拆分：重新映射列索引
            index_mapping = {}
            new_index = 0

            for idx in range(start, end):
                index_mapping[idx] = new_index
                new_index += 1

            # 复制指定列范围的单元格
            for index, cell in element["cells"].items():
                row_idx, col_idx = map(int, index.split("_"))

                if col_idx in index_mapping:
                    new_col_idx = index_mapping[col_idx]
                    new_index = f"{row_idx}_{new_col_idx}"

                    new_cell = deepcopy(cell)
                    new_cell["index"] = new_index
                    new_cell["col"] = new_col_idx

                    sub_element["cells"][new_index] = new_cell

        else:  # vertical
            # 垂直拆分：重新映射行索引
            index_mapping = {}
            new_index = 0

            for idx in range(start, end):
                index_mapping[idx] = new_index
                new_index += 1

            # 复制指定行范围的单元格
            for index, cell in element["cells"].items():
                row_idx, col_idx = map(int, index.split("_"))

                if row_idx in index_mapping:
                    new_row_idx = index_mapping[row_idx]
                    new_index = f"{new_row_idx}_{col_idx}"

                    new_cell = deepcopy(cell)
                    new_cell["index"] = new_index
                    new_cell["row"] = new_row_idx

                    sub_element["cells"][new_index] = new_cell

        # 如果子表格没有单元格，返回None
        return sub_element if sub_element["cells"] else None

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
