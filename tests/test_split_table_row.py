from unittest.mock import Mock

from remarkable.common.pattern import PatternCollection
from remarkable.predictor.cmbchina_predictor.models.split_table_row import SplitTableRow


class TestSplitTableRowMethods:
    """测试SplitTableRow类的表格拆分方法"""

    def setup_method(self):
        """为每个测试方法设置实例"""
        self.instance = SplitTableRow.__new__(SplitTableRow)
        self.test_config = {"split_table": ["col_1", "col_2", "section"]}
        self.instance.get_config = Mock(side_effect=lambda key, default=None, column=None:
                                      self.test_config.get(key, default))

    def get_sample_element(self):
        """创建测试用的element数据"""
        return {
            'cells': {
                '0_0': {"text": "col_1", "col": 0, "row": 0, "index": "0_0"},
                '0_1': {"text": "col_2", "col": 1, "row": 0, "index": "0_1"},
                '0_2': {"text": "col_1", "col": 2, "row": 0, "index": "0_2"},
                '0_3': {"text": "col_2", "col": 3, "row": 0, "index": "0_3"},
                '1_0': {"text": "data1", "col": 0, "row": 1, "index": "1_0"},
                '1_1': {"text": "data2", "col": 1, "row": 1, "index": "1_1"},
                '1_2': {"text": "data3", "col": 2, "row": 1, "index": "1_2"},
                '1_3': {"text": "data4", "col": 3, "row": 1, "index": "1_3"},
                '2_0': {"text": "value1", "col": 0, "row": 2, "index": "2_0"},
                '2_1': {"text": "value2", "col": 1, "row": 2, "index": "2_1"},
                '2_2': {"text": "value3", "col": 2, "row": 2, "index": "2_2"},
                '2_3': {"text": "value4", "col": 3, "row": 2, "index": "2_3"},
            },
            'class': 'TABLE',
            'index': 1
        }

    def get_no_split_element(self):
        """创建不需要拆分的element数据"""
        return {
            'cells': {
                '0_0': {"text": "name", "col": 0, "row": 0, "index": "0_0"},
                '0_1': {"text": "age", "col": 1, "row": 0, "index": "0_1"},
                '1_0': {"text": "Alice", "col": 0, "row": 1, "index": "1_0"},
                '1_1': {"text": "25", "col": 1, "row": 1, "index": "1_1"},
            },
            'class': 'TABLE',
            'index': 1
        }

    def test_split_table_property(self):
        """测试split_table属性"""
        result = self.instance.split_table
        assert isinstance(result, PatternCollection)

    def test_find_split_positions_horizontal_priority(self):
        """测试水平拆分优先级"""
        sample_element = self.get_sample_element()
        split_type, split_positions = self.instance._find_split_positions(sample_element)

        # 预期水平拆分，在列2和列3找到重复的"col_1"和"col_2"
        assert split_type == 'horizontal'
        assert split_positions == [2, 3]

    def test_find_split_positions_vertical_fallback(self):
        """测试垂直拆分作为后备选项"""
        # 创建一个只能垂直拆分的表格
        vertical_only_element = {
            'cells': {
                '0_0': {"text": "name", "col": 0, "row": 0, "index": "0_0"},
                '0_1': {"text": "col_1", "col": 1, "row": 0, "index": "0_1"},  # 匹配的表头
                '1_0': {"text": "item1", "col": 0, "row": 1, "index": "1_0"},
                '1_1': {"text": "data1", "col": 1, "row": 1, "index": "1_1"},
                '2_0': {"text": "item2", "col": 0, "row": 2, "index": "2_0"},
                '2_1': {"text": "col_1", "col": 1, "row": 2, "index": "2_1"},  # 重复的"col_1"
            },
            'class': 'TABLE',
            'index': 1
        }

        split_type, split_positions = self.instance._find_split_positions(vertical_only_element)

        # 预期垂直拆分，在行2找到重复的"col_1"
        assert split_type == 'vertical'
        assert split_positions == [2]

    def test_find_split_positions_no_duplicates(self):
        """测试在没有重复表头的情况下查找拆分位置"""
        no_split_element = self.get_no_split_element()
        split_type, split_positions = self.instance._find_split_positions(no_split_element)

        # 预期不拆分
        assert split_type is None
        assert split_positions == []

    def test_find_horizontal_split_positions(self):
        """测试水平拆分位置查找"""
        sample_element = self.get_sample_element()
        split_positions = self.instance._find_horizontal_split_positions(sample_element)

        # 预期在列2和列3找到重复的"col_1"和"col_2"
        assert split_positions == [2, 3]

    def test_find_horizontal_split_positions_no_duplicates(self):
        """测试水平拆分位置查找 - 无重复"""
        no_split_element = self.get_no_split_element()
        split_positions = self.instance._find_horizontal_split_positions(no_split_element)

        # 预期没有拆分位置，因为表头不匹配配置的模式
        assert split_positions == []

    def test_find_horizontal_split_positions_with_partial_match(self):
        """测试水平拆分位置查找 - 部分匹配"""
        element = {
            'cells': {
                '0_0': {"text": "header_col_1", "col": 0, "row": 0, "index": "0_0"},      # 包含"col_1"
                '0_1': {"text": "header_col_2", "col": 1, "row": 0, "index": "0_1"},      # 包含"col_2"
                '0_2': {"text": "header_col_1", "col": 2, "row": 0, "index": "0_2"}, # 重复包含"col_1"
                '0_3': {"text": "other", "col": 3, "row": 0, "index": "0_3"},             # 不匹配
                '1_0': {"text": "data1", "col": 0, "row": 1, "index": "1_0"},
                '1_1': {"text": "data2", "col": 1, "row": 1, "index": "1_1"},
                '1_2': {"text": "data3", "col": 2, "row": 1, "index": "1_2"},
                '1_3': {"text": "data4", "col": 3, "row": 1, "index": "1_3"},
            },
            'class': 'TABLE',
            'index': 1
        }

        split_positions = self.instance._find_horizontal_split_positions(element)

        # 预期在列2找到重复的包含"col_1"的文本
        assert split_positions == [2]

    def test_find_matching_columns_in_first_row_exact_match(self):
        """测试在第一行中查找匹配的列 - 精确匹配"""
        element = {
            'cells': {
                '0_0': {"text": "name", "col": 0, "row": 0, "index": "0_0"},      # 不匹配
                '0_1': {"text": "col_1", "col": 1, "row": 0, "index": "0_1"},     # 匹配
                '0_2': {"text": "value", "col": 2, "row": 0, "index": "0_2"},     # 不匹配
                '0_3': {"text": "col_2", "col": 3, "row": 0, "index": "0_3"},     # 匹配
                '1_0': {"text": "item1", "col": 0, "row": 1, "index": "1_0"},
                '1_1': {"text": "data1", "col": 1, "row": 1, "index": "1_1"},
                '1_2': {"text": "info1", "col": 2, "row": 1, "index": "1_2"},
                '1_3': {"text": "data2", "col": 3, "row": 1, "index": "1_3"},
            },
            'class': 'TABLE',
            'index': 1
        }

        matching_cols = self.instance._find_matching_columns_in_first_row(element)
        # 预期找到列1和列3（包含"col_1"和"col_2"）
        assert matching_cols == [1, 3]

    def test_find_matching_columns_in_first_row_partial_match(self):
        """测试在第一行中查找匹配的列 - 部分匹配（re.search行为）"""
        element = {
            'cells': {
                '0_0': {"text": "header_col_1_info", "col": 0, "row": 0, "index": "0_0"},  # 包含"col_1"
                '0_1': {"text": "column_col_2_data", "col": 1, "row": 0, "index": "0_1"},  # 包含"col_2"
                '0_2': {"text": "other_info", "col": 2, "row": 0, "index": "0_2"},         # 不包含
                '1_0': {"text": "data1", "col": 0, "row": 1, "index": "1_0"},
                '1_1': {"text": "data2", "col": 1, "row": 1, "index": "1_1"},
                '1_2': {"text": "data3", "col": 2, "row": 1, "index": "1_2"},
            },
            'class': 'TABLE',
            'index': 1
        }

        matching_cols = self.instance._find_matching_columns_in_first_row(element)
        # 预期找到列0和列1（包含"col_1"和"col_2"的文本）
        assert matching_cols == [0, 1]

    def test_find_matching_columns_in_first_row_empty(self):
        """测试在第一行中查找匹配的列 - 无匹配"""
        element = {
            'cells': {
                '0_0': {"text": "name", "col": 0, "row": 0, "index": "0_0"},
                '0_1': {"text": "value", "col": 1, "row": 0, "index": "0_1"},
                '1_0': {"text": "item1", "col": 0, "row": 1, "index": "1_0"},
                '1_1': {"text": "data1", "col": 1, "row": 1, "index": "1_1"},
            },
            'class': 'TABLE',
            'index': 1
        }

        matching_cols = self.instance._find_matching_columns_in_first_row(element)
        # 预期没有匹配的列，因为表头不匹配配置的模式
        assert matching_cols == []

    def test_find_matching_columns_in_first_row_with_dummy_cells(self):
        """测试在第一行中查找匹配的列 - 包含dummy单元格"""
        element = {
            'cells': {
                '0_0': {"text": "col_1", "col": 0, "row": 0, "index": "0_0"},                # 匹配
                '0_1': {"text": "col_2", "col": 1, "row": 0, "index": "0_1", "dummy": True}, # dummy单元格，应被忽略
                '0_2': {"text": "section", "col": 2, "row": 0, "index": "0_2"},              # 匹配
                '1_0': {"text": "data1", "col": 0, "row": 1, "index": "1_0"},
                '1_1': {"text": "data2", "col": 1, "row": 1, "index": "1_1"},
                '1_2': {"text": "data3", "col": 2, "row": 1, "index": "1_2"},
            },
            'class': 'TABLE',
            'index': 1
        }

        matching_cols = self.instance._find_matching_columns_in_first_row(element)
        # 预期找到列0和列2（列1的dummy单元格被忽略）
        assert matching_cols == [0, 2]

    def test_find_matching_columns_in_first_row_empty_text(self):
        """测试在第一行中查找匹配的列 - 空文本处理"""
        element = {
            'cells': {
                '0_0': {"text": "", "col": 0, "row": 0, "index": "0_0"},           # 空文本
                '0_1': {"text": "  col_1  ", "col": 1, "row": 0, "index": "0_1"},  # 带空格的文本
                '0_2': {"col": 2, "row": 0, "index": "0_2"},                       # 没有text字段
                '1_0': {"text": "data1", "col": 0, "row": 1, "index": "1_0"},
                '1_1': {"text": "data2", "col": 1, "row": 1, "index": "1_1"},
                '1_2': {"text": "data3", "col": 2, "row": 1, "index": "1_2"},
            },
            'class': 'TABLE',
            'index': 1
        }

        matching_cols = self.instance._find_matching_columns_in_first_row(element)
        # 预期找到列1（文本被正确trim后匹配）
        assert matching_cols == [1]

    def test_find_vertical_split_positions(self):
        """测试垂直拆分位置查找"""
        element = {
            'cells': {
                '0_0': {"text": "name", "col": 0, "row": 0, "index": "0_0"},
                '0_1': {"text": "col_1", "col": 1, "row": 0, "index": "0_1"},     # 匹配列
                '0_2': {"text": "col_2", "col": 2, "row": 0, "index": "0_2"},     # 匹配列
                '1_0': {"text": "item1", "col": 0, "row": 1, "index": "1_0"},
                '1_1': {"text": "data1", "col": 1, "row": 1, "index": "1_1"},
                '1_2': {"text": "info1", "col": 2, "row": 1, "index": "1_2"},
                '2_0': {"text": "item2", "col": 0, "row": 2, "index": "2_0"},
                '2_1': {"text": "col_1", "col": 1, "row": 2, "index": "2_1"},     # 重复的"col_1"
                '2_2': {"text": "info2", "col": 2, "row": 2, "index": "2_2"},
                '3_0': {"text": "item3", "col": 0, "row": 3, "index": "3_0"},
                '3_1': {"text": "data3", "col": 1, "row": 3, "index": "3_1"},
                '3_2': {"text": "col_2", "col": 2, "row": 3, "index": "3_2"},     # 重复的"col_2"
            },
            'class': 'TABLE',
            'index': 1
        }

        split_positions = self.instance._find_vertical_split_positions(element)
        # 预期在行2找到重复的"col_1"，在行3找到重复的"col_2"
        assert split_positions == [2, 3]

    def test_find_vertical_split_positions_no_matching_columns(self):
        """测试垂直拆分位置查找 - 无匹配列"""
        element = {
            'cells': {
                '0_0': {"text": "name", "col": 0, "row": 0, "index": "0_0"},
                '0_1': {"text": "value", "col": 1, "row": 0, "index": "0_1"},
                '1_0': {"text": "item1", "col": 0, "row": 1, "index": "1_0"},
                '1_1': {"text": "data1", "col": 1, "row": 1, "index": "1_1"},
            },
            'class': 'TABLE',
            'index': 1
        }

        split_positions = self.instance._find_vertical_split_positions(element)
        # 预期没有拆分位置，因为第一行没有匹配的列
        assert split_positions == []

    def test_find_vertical_split_positions_with_regex_patterns(self):
        """测试垂直拆分位置查找 - 使用正则模式匹配"""
        element = {
            'cells': {
                '0_0': {"text": "header_section", "col": 0, "row": 0, "index": "0_0"},  # 包含"section"
                '0_1': {"text": "data_column", "col": 1, "row": 0, "index": "0_1"},       # 不匹配
                '1_0': {"text": "item1", "col": 0, "row": 1, "index": "1_0"},
                '1_1': {"text": "value1", "col": 1, "row": 1, "index": "1_1"},
                '2_0': {"text": "header_section", "col": 0, "row": 2, "index": "2_0"}, # 重复包含"section"
                '2_1': {"text": "value2", "col": 1, "row": 2, "index": "2_1"},
            },
            'class': 'TABLE',
            'index': 1
        }

        split_positions = self.instance._find_vertical_split_positions(element)
        # 预期在行2找到重复的包含"section"的文本
        assert split_positions == [2]

    def test_find_vertical_split_positions_deduplication(self):
        """测试垂直拆分位置查找 - 去重功能"""
        element = {
            'cells': {
                '0_0': {"text": "col_1", "col": 0, "row": 0, "index": "0_0"},     # 匹配列
                '0_1': {"text": "col_1", "col": 1, "row": 0, "index": "0_1"},     # 匹配列
                '1_0': {"text": "data1", "col": 0, "row": 1, "index": "1_0"},
                '1_1': {"text": "data2", "col": 1, "row": 1, "index": "1_1"},
                '2_0': {"text": "col_1", "col": 0, "row": 2, "index": "2_0"},     # 重复的"col_1"
                '2_1': {"text": "col_1", "col": 1, "row": 2, "index": "2_1"},     # 重复的"col_1"
            },
            'class': 'TABLE',
            'index': 1
        }

        split_positions = self.instance._find_vertical_split_positions(element)
        # 预期在行2找到重复，但由于去重，只返回一个位置
        assert split_positions == [2]

    def test_split_table_by_type_horizontal(self):
        """测试水平拆分表格"""
        sample_element = self.get_sample_element()
        split_positions = [2]  # 在列2处拆分
        split_elements = self.instance._split_table_by_type(sample_element, split_positions, 'horizontal')

        # 应该拆分成2个子表格
        assert len(split_elements) == 2

        # 第一个子表格应该包含列0和1
        first_table = split_elements[0]
        first_table_cols = {int(idx.split("_")[1]) for idx in first_table["cells"].keys()}
        assert first_table_cols == {0, 1}

        # 第二个子表格应该包含列2和3（重新映射为0和1）
        second_table = split_elements[1]
        second_table_cols = {int(idx.split("_")[1]) for idx in second_table["cells"].keys()}
        assert second_table_cols == {0, 1}

    def test_create_sub_table_horizontal(self):
        """测试创建水平拆分的子表格"""
        sample_element = self.get_sample_element()
        sub_element = self.instance._create_sub_table(sample_element, 0, 2, 'horizontal')

        # 检查子表格包含正确的单元格
        assert len(sub_element["cells"]) == 6  # 3行 × 2列

        # 检查列索引重新映射
        col_indices = {int(idx.split("_")[1]) for idx in sub_element["cells"].keys()}
        assert col_indices == {0, 1}

        # 检查单元格内容
        assert sub_element["cells"]["0_0"]["text"] == "col_1"
        assert sub_element["cells"]["0_1"]["text"] == "col_2"
        assert sub_element["cells"]["1_0"]["text"] == "data1"
        assert sub_element["cells"]["1_1"]["text"] == "data2"

    def test_calculate_split_ranges_horizontal(self):
        """测试水平拆分范围计算"""
        sample_element = self.get_sample_element()

        # 测试单个拆分位置
        ranges = self.instance._calculate_split_ranges(sample_element, [2], 'horizontal')
        assert ranges == [(0, 2), (2, 4)]

        # 测试多个拆分位置
        ranges = self.instance._calculate_split_ranges(sample_element, [1, 3], 'horizontal')
        assert ranges == [(0, 1), (1, 3), (3, 4)]

    def test_calculate_split_ranges_vertical(self):
        """测试垂直拆分范围计算"""
        sample_element = self.get_sample_element()

        # 测试单个拆分位置
        ranges = self.instance._calculate_split_ranges(sample_element, [2], 'vertical')
        assert ranges == [(0, 2), (2, 3)]

        # 测试多个拆分位置
        ranges = self.instance._calculate_split_ranges(sample_element, [1, 2], 'vertical')
        assert ranges == [(0, 1), (1, 2), (2, 3)]

    def test_calculate_split_ranges_empty_positions(self):
        """测试空拆分位置的范围计算"""
        sample_element = self.get_sample_element()

        ranges = self.instance._calculate_split_ranges(sample_element, [], 'horizontal')
        assert ranges == [(0, 4)]  # 整个表格作为一个范围

    def test_create_sub_table_horizontal_edge_cases(self):
        """测试水平拆分子表格创建的边界情况"""
        sample_element = self.get_sample_element()

        # 测试超出范围的列
        sub_element = self.instance._create_sub_table(sample_element, 5, 6, 'horizontal')
        assert sub_element is None

        # 测试起始位置等于结束位置
        sub_element = self.instance._create_sub_table(sample_element, 2, 2, 'horizontal')
        assert sub_element is None

    def test_create_sub_table_vertical_edge_cases(self):
        """测试垂直拆分子表格创建的边界情况"""
        sample_element = self.get_sample_element()

        # 测试超出范围的行
        sub_element = self.instance._create_sub_table(sample_element, 5, 6, 'vertical')
        assert sub_element is None

        # 测试起始位置等于结束位置
        sub_element = self.instance._create_sub_table(sample_element, 1, 1, 'vertical')
        assert sub_element is None

    def test_vertical_split_positions(self):
        """测试垂直拆分位置查找"""
        # 创建一个适合垂直拆分的表格
        # 第一行包含匹配的表头"col_1"，然后在第一列（包含"col_1"的列）中查找重复
        vertical_element = {
            'cells': {
                '0_0': {"text": "col_1", "col": 0, "row": 0, "index": "0_0"},  # 第一行包含"col_1"
                '0_1': {"text": "data1", "col": 1, "row": 0, "index": "0_1"},
                '1_0': {"text": "b", "col": 0, "row": 1, "index": "1_0"},
                '1_1': {"text": "value1", "col": 1, "row": 1, "index": "1_1"},
                '2_0': {"text": "c", "col": 0, "row": 2, "index": "2_0"},
                '2_1': {"text": "value2", "col": 1, "row": 2, "index": "2_1"},
                '3_0': {"text": "col_1", "col": 0, "row": 3, "index": "3_0"},  # 在第0列重复的"col_1"
                '3_1': {"text": "value3", "col": 1, "row": 3, "index": "3_1"},
            },
            'class': 'TABLE',
            'index': 1
        }

        split_positions = self.instance._find_vertical_split_positions(vertical_element)
        # 预期在行3找到重复的"a"（第一次出现在行0，重复出现在行3）
        assert split_positions == [3]

    def test_vertical_split_positions_with_first_row(self):
        """测试垂直拆分位置查找，验证第一行也会被考虑"""
        # 创建一个表格，第一行就有重复的表头
        vertical_element = {
            'cells': {
                '0_0': {"text": "section", "col": 0, "row": 0, "index": "0_0"},
                '0_1': {"text": "data", "col": 1, "row": 0, "index": "0_1"},
                '1_0': {"text": "item1", "col": 0, "row": 1, "index": "1_0"},
                '1_1': {"text": "value1", "col": 1, "row": 1, "index": "1_1"},
                '2_0': {"text": "section", "col": 0, "row": 2, "index": "2_0"},  # 重复的"section"
                '2_1': {"text": "data", "col": 1, "row": 2, "index": "2_1"},
                '3_0': {"text": "item2", "col": 0, "row": 3, "index": "3_0"},
                '3_1': {"text": "value2", "col": 1, "row": 3, "index": "3_1"},
            },
            'class': 'TABLE',
            'index': 1
        }

        # 修改配置以匹配"section"
        self.instance.get_config = Mock(side_effect=lambda key, default=None, column=None:
                                      {"split_table": ["section"]}.get(key, default))

        split_positions = self.instance._find_vertical_split_positions(vertical_element)
        # 预期在行2找到重复的"section"（第一次出现在行0，重复出现在行2）
        assert split_positions == [2]

    def test_find_matching_columns_in_first_row(self):
        """测试在第一行中查找匹配的列"""
        element = {
            'cells': {
                '0_0': {"text": "name", "col": 0, "row": 0, "index": "0_0"},      # 不匹配
                '0_1': {"text": "col_1", "col": 1, "row": 0, "index": "0_1"},         # 匹配
                '0_2': {"text": "value", "col": 2, "row": 0, "index": "0_2"},     # 不匹配
                '0_3': {"text": "col_2", "col": 3, "row": 0, "index": "0_3"},         # 匹配
                '1_0': {"text": "item1", "col": 0, "row": 1, "index": "1_0"},
                '1_1': {"text": "data1", "col": 1, "row": 1, "index": "1_1"},
                '1_2': {"text": "info1", "col": 2, "row": 1, "index": "1_2"},
                '1_3': {"text": "data2", "col": 3, "row": 1, "index": "1_3"},
            },
            'class': 'TABLE',
            'index': 1
        }

        matching_cols = self.instance._find_matching_columns_in_first_row(element)
        # 预期找到列1和列3（包含"a"和"b"）
        assert matching_cols == [1, 3]

    def test_vertical_split_with_multiple_matching_columns(self):
        """测试多个匹配列的垂直拆分"""
        element = {
            'cells': {
                '0_0': {"text": "name", "col": 0, "row": 0, "index": "0_0"},
                '0_1': {"text": "col_1", "col": 1, "row": 0, "index": "0_1"},         # 匹配列
                '0_2': {"text": "col_2", "col": 2, "row": 0, "index": "0_2"},         # 匹配列
                '1_0': {"text": "item1", "col": 0, "row": 1, "index": "1_0"},
                '1_1': {"text": "data1", "col": 1, "row": 1, "index": "1_1"},
                '1_2': {"text": "info1", "col": 2, "row": 1, "index": "1_2"},
                '2_0': {"text": "item2", "col": 0, "row": 2, "index": "2_0"},
                '2_1': {"text": "col_1", "col": 1, "row": 2, "index": "2_1"},         # 重复的"col_1"
                '2_2': {"text": "info2", "col": 2, "row": 2, "index": "2_2"},
                '3_0': {"text": "item3", "col": 0, "row": 3, "index": "3_0"},
                '3_1': {"text": "data3", "col": 1, "row": 3, "index": "3_1"},
                '3_2': {"text": "col_2", "col": 2, "row": 3, "index": "3_2"},         # 重复的"col_2"
            },
            'class': 'TABLE',
            'index': 1
        }

        split_positions = self.instance._find_vertical_split_positions(element)
        # 预期在行2找到重复的"a"，在行3找到重复的"b"
        assert split_positions == [2, 3]

    def test_split_table_by_type_vertical(self):
        """测试垂直拆分表格"""
        vertical_element = {
            'cells': {
                '0_0': {"text": "header1", "col": 0, "row": 0, "index": "0_0"},
                '0_1': {"text": "data1", "col": 1, "row": 0, "index": "0_1"},
                '1_0': {"text": "a", "col": 0, "row": 1, "index": "1_0"},
                '1_1': {"text": "value1", "col": 1, "row": 1, "index": "1_1"},
                '2_0': {"text": "b", "col": 0, "row": 2, "index": "2_0"},
                '2_1': {"text": "value2", "col": 1, "row": 2, "index": "2_1"},
                '3_0': {"text": "a", "col": 0, "row": 3, "index": "3_0"},
                '3_1': {"text": "value3", "col": 1, "row": 3, "index": "3_1"},
            },
            'class': 'TABLE',
            'index': 1
        }

        split_positions = [3]  # 在行3处拆分
        split_elements = self.instance._split_table_by_type(vertical_element, split_positions, 'vertical')

        # 应该拆分成2个子表格
        assert len(split_elements) == 2

        # 第一个子表格应该包含行0,1,2
        first_table = split_elements[0]
        first_table_rows = {int(idx.split("_")[0]) for idx in first_table["cells"].keys()}
        assert first_table_rows == {0, 1, 2}

        # 第二个子表格应该包含行3（重新映射为行0）
        second_table = split_elements[1]
        second_table_rows = {int(idx.split("_")[0]) for idx in second_table["cells"].keys()}
        assert second_table_rows == {0}

    def test_create_sub_table_vertical(self):
        """测试创建垂直拆分的子表格"""
        vertical_element = {
            'cells': {
                '0_0': {"text": "header1", "col": 0, "row": 0, "index": "0_0"},
                '0_1': {"text": "data1", "col": 1, "row": 0, "index": "0_1"},
                '1_0': {"text": "a", "col": 0, "row": 1, "index": "1_0"},
                '1_1': {"text": "value1", "col": 1, "row": 1, "index": "1_1"},
                '2_0': {"text": "b", "col": 0, "row": 2, "index": "2_0"},
                '2_1': {"text": "value2", "col": 1, "row": 2, "index": "2_1"},
            },
            'class': 'TABLE',
            'index': 1
        }

        sub_element = self.instance._create_sub_table(vertical_element, 0, 2, 'vertical')

        # 检查子表格包含正确的单元格
        assert len(sub_element["cells"]) == 4  # 2行 × 2列

        # 检查行索引重新映射
        row_indices = {int(idx.split("_")[0]) for idx in sub_element["cells"].keys()}
        assert row_indices == {0, 1}

        # 检查单元格内容
        assert sub_element["cells"]["0_0"]["text"] == "header1"
        assert sub_element["cells"]["0_1"]["text"] == "data1"
        assert sub_element["cells"]["1_0"]["text"] == "a"
        assert sub_element["cells"]["1_1"]["text"] == "value1"

    def test_calculate_split_ranges(self):
        """测试计算拆分范围"""
        sample_element = self.get_sample_element()

        # 测试水平拆分范围计算
        horizontal_ranges = self.instance._calculate_split_ranges(sample_element, [2], 'horizontal')
        assert horizontal_ranges == [(0, 2), (2, 4)]

        # 测试垂直拆分范围计算
        vertical_ranges = self.instance._calculate_split_ranges(sample_element, [2], 'vertical')
        assert vertical_ranges == [(0, 2), (2, 3)]

    def test_edge_case_empty_element(self):
        """测试空元素的边界情况"""
        empty_element = {
            'cells': {},
            'class': 'TABLE',
            'index': 1
        }
        
        split_type, split_positions = self.instance._find_split_positions(empty_element)
        assert split_type is None
        assert split_positions == []
        
        # 测试空元素的拆分
        split_elements = self.instance._split_table_by_type(empty_element, [], 'horizontal')
        assert len(split_elements) == 1
        assert split_elements[0] == empty_element

    def test_create_sub_table_empty_range(self):
        """测试创建空范围的子表格"""
        sample_element = {
            'cells': {
                '0_0': {"text": "a", "col": 0, "row": 0, "index": "0_0"},
                '0_1': {"text": "b", "col": 1, "row": 0, "index": "0_1"},
            },
            'class': 'TABLE',
            'index': 1
        }

        # 测试超出范围的列
        sub_element = self.instance._create_sub_table(sample_element, 5, 6, 'horizontal')
        assert sub_element is None

    def test_split_table_multiple_positions(self):
        """测试多个拆分位置的情况"""
        element = {
            'cells': {
                '0_0': {"text": "a", "col": 0, "row": 0, "index": "0_0"},
                '0_1': {"text": "b", "col": 1, "row": 0, "index": "0_1"},
                '0_2': {"text": "a", "col": 2, "row": 0, "index": "0_2"},
                '0_3': {"text": "b", "col": 3, "row": 0, "index": "0_3"},
                '0_4': {"text": "a", "col": 4, "row": 0, "index": "0_4"},
                '1_0': {"text": "1", "col": 0, "row": 1, "index": "1_0"},
                '1_1': {"text": "2", "col": 1, "row": 1, "index": "1_1"},
                '1_2': {"text": "3", "col": 2, "row": 1, "index": "1_2"},
                '1_3': {"text": "4", "col": 3, "row": 1, "index": "1_3"},
                '1_4': {"text": "5", "col": 4, "row": 1, "index": "1_4"},
            },
            'class': 'TABLE',
            'index': 1
        }

        split_positions = [2, 4]  # 在列2和列4处拆分
        split_elements = self.instance._split_table_by_type(element, split_positions, 'horizontal')

        # 应该拆分成3个子表格
        assert len(split_elements) == 3

        # 检查每个子表格的列数
        assert len({idx.split("_")[1] for idx in split_elements[0]["cells"].keys()}) == 2  # 列0,1
        assert len({idx.split("_")[1] for idx in split_elements[1]["cells"].keys()}) == 2  # 列2,3 -> 0,1
        assert len({idx.split("_")[1] for idx in split_elements[2]["cells"].keys()}) == 1  # 列4 -> 0

    def test_edge_case_empty_element(self):
        """测试空元素的边界情况"""
        empty_element = {
            'cells': {},
            'class': 'TABLE',
            'index': 1
        }

        split_type, split_positions = self.instance._find_split_positions(empty_element)
        assert split_type is None
        assert split_positions == []

        # 测试空元素的拆分
        split_elements = self.instance._split_table_by_type(empty_element, [], 'horizontal')
        assert len(split_elements) == 1
        assert split_elements[0] == empty_element

    def test_edge_case_single_cell(self):
        """测试单个单元格的边界情况"""
        single_cell_element = {
            'cells': {
                '0_0': {"text": "a", "col": 0, "row": 0, "index": "0_0"},
            },
            'class': 'TABLE',
            'index': 1
        }

        split_type, split_positions = self.instance._find_split_positions(single_cell_element)
        assert split_type is None
        assert split_positions == []

    def test_edge_case_dummy_cells(self):
        """测试包含dummy单元格的情况"""
        element_with_dummy = {
            'cells': {
                '0_0': {"text": "col_1", "col": 0, "row": 0, "index": "0_0"},
                '0_1': {"text": "col_2", "col": 1, "row": 0, "index": "0_1", "dummy": True},  # dummy单元格
                '0_2': {"text": "col_1", "col": 2, "row": 0, "index": "0_2"},
                '1_0': {"text": "data1", "col": 0, "row": 1, "index": "1_0"},
                '1_1': {"text": "data2", "col": 1, "row": 1, "index": "1_1"},
                '1_2': {"text": "data3", "col": 2, "row": 1, "index": "1_2"},
            },
            'class': 'TABLE',
            'index': 1
        }

        split_type, split_positions = self.instance._find_split_positions(element_with_dummy)
        # dummy单元格应该被忽略，所以应该找到重复的"col_1"
        assert split_type == 'horizontal'
        assert split_positions == [2]

    def test_integration_priority_horizontal_over_vertical(self):
        """测试水平拆分优先于垂直拆分的集成测试"""
        # 创建一个既可以水平拆分又可以垂直拆分的表格
        both_split_element = {
            'cells': {
                '0_0': {"text": "col_1", "col": 0, "row": 0, "index": "0_0"},
                '0_1': {"text": "col_2", "col": 1, "row": 0, "index": "0_1"},
                '0_2': {"text": "col_1", "col": 2, "row": 0, "index": "0_2"},  # 水平重复
                '1_0': {"text": "data1", "col": 0, "row": 1, "index": "1_0"},
                '1_1': {"text": "data2", "col": 1, "row": 1, "index": "1_1"},
                '1_2': {"text": "data3", "col": 2, "row": 1, "index": "1_2"},
                '2_0': {"text": "col_1", "col": 0, "row": 2, "index": "2_0"},  # 垂直重复
                '2_1': {"text": "data4", "col": 1, "row": 2, "index": "2_1"},
                '2_2': {"text": "data5", "col": 2, "row": 2, "index": "2_2"},
            },
            'class': 'TABLE',
            'index': 1
        }

        split_type, split_positions = self.instance._find_split_positions(both_split_element)
        # 应该优先选择水平拆分
        assert split_type == 'horizontal'
        assert split_positions == [2]

    def test_performance_large_table(self):
        """测试大表格的性能"""
        # 创建一个较大的表格
        large_element = {'cells': {}, 'class': 'TABLE', 'index': 1}

        # 生成10x10的表格
        for row in range(10):
            for col in range(10):
                index = f"{row}_{col}"
                text = "col_1" if (row == 0 and col in [0, 5]) else f"data_{row}_{col}"
                large_element['cells'][index] = {
                    "text": text,
                    "col": col,
                    "row": row,
                    "index": index
                }

        # 测试拆分功能
        split_type, split_positions = self.instance._find_split_positions(large_element)
        assert split_type == 'horizontal'
        assert split_positions == [5]  # 在列5找到重复的"col_1"

        # 测试拆分执行
        split_elements = self.instance._split_table_by_type(large_element, split_positions, split_type)
        assert len(split_elements) == 2
        assert len(split_elements[0]['cells']) == 50  # 10行 × 5列
        assert len(split_elements[1]['cells']) == 50  # 10行 × 5列
