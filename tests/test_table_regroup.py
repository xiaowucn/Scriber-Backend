from unittest.mock import Mock

from remarkable.common.pattern import PatternCollection
from remarkable.predictor.cmbchina_predictor.models.table_regroup import TableRegroup


class TestTableRegroup:
    """测试TableRegroup类的表格重组功能"""

    def setup_method(self):
        """为每个测试方法设置实例"""
        self.instance = TableRegroup.__new__(TableRegroup)
        self.test_config = {
            "main_col": ["mian_col"],  # 主列模式
            "assistant_col": ["assistant_col_\\d+"]  # 辅助列模式（正则）
        }
        self.instance.get_config = Mock(side_effect=lambda key, default=None, column=None: 
                                      self.test_config.get(key, default))

    def get_sample_element(self):
        """创建测试用的element数据"""
        return {
            'cells': {
                '0_0': {"text": "mian_col", "col": 0, "row": 0, "index": "0_0"},
                '0_1': {"text": "assistant_col_0", "col": 1, "row": 0, "index": "0_1"},
                '0_2': {"text": "assistant_col_1", "col": 2, "row": 0, "index": "0_2"},
                '0_3': {"text": "assistant_col_2", "col": 3, "row": 0, "index": "0_3"},
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

    def test_main_col_property(self):
        """测试main_col属性"""
        result = self.instance.main_col
        assert isinstance(result, PatternCollection)

    def test_assistant_col_property(self):
        """测试assistant_col属性"""
        result = self.instance.assistant_col
        assert isinstance(result, PatternCollection)

    def test_identify_columns(self):
        """测试列识别功能"""
        sample_element = self.get_sample_element()
        main_cols, assistant_cols = self.instance._identify_columns(sample_element)

        # 预期主列为第0列，辅助列为第1、2、3列
        assert main_cols == [0]
        assert assistant_cols == [1, 2, 3]

    def test_validate_columns_success(self):
        """测试列验证功能 - 成功情况"""
        main_cols = [0]  # 1个主列
        assistant_cols = [1, 2, 3]  # 3个辅助列

        result = self.instance._validate_columns(main_cols, assistant_cols)
        assert result is True

    def test_validate_columns_no_main_col(self):
        """测试列验证功能 - 没有主列"""
        main_cols = []
        assistant_cols = [1, 2, 3]

        result = self.instance._validate_columns(main_cols, assistant_cols)
        assert result is False

    def test_validate_columns_no_assistant_col(self):
        """测试列验证功能 - 没有辅助列"""
        main_cols = [0]
        assistant_cols = []

        result = self.instance._validate_columns(main_cols, assistant_cols)
        assert result is False

    def test_validate_columns_multiple_main_cols(self):
        """测试列验证功能 - 多个主列"""
        main_cols = [0, 1]  # 2个主列，不符合要求
        assistant_cols = [2, 3, 4]

        result = self.instance._validate_columns(main_cols, assistant_cols)
        assert result is False

    def test_validate_columns_single_assistant_col(self):
        """测试列验证功能 - 只有1个辅助列"""
        main_cols = [0]
        assistant_cols = [1]  # 只有1个辅助列，不符合要求

        result = self.instance._validate_columns(main_cols, assistant_cols)
        assert result is False

    def test_identify_columns_no_match(self):
        """测试列识别功能 - 无匹配"""
        element = {
            'cells': {
                '0_0': {"text": "other_col", "col": 0, "row": 0, "index": "0_0"},
                '0_1': {"text": "another_col", "col": 1, "row": 0, "index": "0_1"},
                '1_0': {"text": "data1", "col": 0, "row": 1, "index": "1_0"},
                '1_1': {"text": "data2", "col": 1, "row": 1, "index": "1_1"},
            },
            'class': 'TABLE',
            'index': 1
        }

        main_cols, assistant_cols = self.instance._identify_columns(element)

        # 预期没有匹配的列
        assert main_cols == []
        assert assistant_cols == []

    def test_create_regrouped_table(self):
        """测试创建重组表格"""
        sample_element = self.get_sample_element()
        main_col = 0  # 使用第一个主列
        assistant_col = 1

        # Mock父类的prepare_table方法
        mock_table = {"test": "table"}
        self.instance.__class__.__bases__[0].prepare_table = Mock(return_value=mock_table)

        result = self.instance._create_regrouped_table(sample_element, main_col, assistant_col)

        # 验证返回结果
        assert result == mock_table

    def test_regroup_tables(self):
        """测试表格重组功能"""
        sample_element = self.get_sample_element()
        main_col = 0  # 使用第一个主列
        assistant_cols = [1, 2, 3]

        # Mock父类的prepare_table方法
        mock_table = {"test": "table"}
        self.instance.__class__.__bases__[0].prepare_table = Mock(return_value=mock_table)

        result = self.instance._regroup_tables(sample_element, main_col, assistant_cols)

        # 预期生成3个重组后的表格
        assert len(result) == 3
        assert all(table == mock_table for table in result)

    def test_prepare_table_success(self):
        """测试prepare_table成功重组"""
        sample_element = self.get_sample_element()
        
        # Mock父类的prepare_table方法
        mock_table = {"test": "table"}
        self.instance.__class__.__bases__[0].prepare_table = Mock(return_value=mock_table)
        
        tables, elements = self.instance.prepare_table(sample_element)
        
        # 预期生成3个重组后的表格和对应的元素
        assert len(tables) == 3
        assert len(elements) == 3
        assert all(table == mock_table for table in tables)
        assert all(elem == sample_element for elem in elements)

    def test_prepare_table_invalid_columns(self):
        """测试prepare_table不满足约束条件的情况"""
        # 情况1: 没有匹配的列
        no_match_element = {
            'cells': {
                '0_0': {"text": "other_col", "col": 0, "row": 0, "index": "0_0"},
                '0_1': {"text": "another_col", "col": 1, "row": 0, "index": "0_1"},
                '1_0': {"text": "data1", "col": 0, "row": 1, "index": "1_0"},
                '1_1': {"text": "data2", "col": 1, "row": 1, "index": "1_1"},
            },
            'class': 'TABLE',
            'index': 1
        }

        tables, elements = self.instance.prepare_table(no_match_element)

        # 预期返回空结果（因为不满足约束条件）
        assert tables == []
        assert elements == []

    def test_prepare_table_insufficient_assistant_cols(self):
        """测试prepare_table辅助列不足的情况"""
        # 只有1个辅助列，不满足约束条件
        element = {
            'cells': {
                '0_0': {"text": "mian_col", "col": 0, "row": 0, "index": "0_0"},
                '0_1': {"text": "assistant_col_0", "col": 1, "row": 0, "index": "0_1"},
                '1_0': {"text": "data1", "col": 0, "row": 1, "index": "1_0"},
                '1_1': {"text": "data2", "col": 1, "row": 1, "index": "1_1"},
            },
            'class': 'TABLE',
            'index': 1
        }

        tables, elements = self.instance.prepare_table(element)

        # 预期返回空结果（因为辅助列不足）
        assert tables == []
        assert elements == []

    def test_prepare_table_multiple_main_cols(self):
        """测试prepare_table多个主列的情况"""
        # 修改配置以匹配多个主列
        self.test_config["main_col"] = ["main_col"]

        element = {
            'cells': {
                '0_0': {"text": "main_col", "col": 0, "row": 0, "index": "0_0"},
                '0_1': {"text": "main_column", "col": 1, "row": 0, "index": "0_1"},
                '0_2': {"text": "assistant_col_0", "col": 2, "row": 0, "index": "0_2"},
                '0_3': {"text": "assistant_col_1", "col": 3, "row": 0, "index": "0_3"},
                '1_0': {"text": "data1", "col": 0, "row": 1, "index": "1_0"},
                '1_1': {"text": "data2", "col": 1, "row": 1, "index": "1_1"},
                '1_2': {"text": "data3", "col": 2, "row": 1, "index": "1_2"},
                '1_3': {"text": "data4", "col": 3, "row": 1, "index": "1_3"},
            },
            'class': 'TABLE',
            'index': 1
        }

        tables, elements = self.instance.prepare_table(element)

        # 预期返回空结果（因为主列超过1个）
        assert tables == []
        assert elements == []

    def test_edge_case_dummy_cells(self):
        """测试包含dummy单元格的情况"""
        element = {
            'cells': {
                '0_0': {"text": "mian_col", "col": 0, "row": 0, "index": "0_0"},
                '0_1': {"text": "assistant_col_0", "col": 1, "row": 0, "index": "0_1", "dummy": True},
                '0_2': {"text": "assistant_col_1", "col": 2, "row": 0, "index": "0_2"},
                '1_0': {"text": "data1", "col": 0, "row": 1, "index": "1_0"},
                '1_1': {"text": "data2", "col": 1, "row": 1, "index": "1_1"},
                '1_2': {"text": "data3", "col": 2, "row": 1, "index": "1_2"},
            },
            'class': 'TABLE',
            'index': 1
        }

        main_cols, assistant_cols = self.instance._identify_columns(element)

        # dummy单元格应该被忽略，导致辅助列不足
        assert main_cols == [0]
        assert assistant_cols == [2]  # 列1被忽略，只剩1个辅助列

        # 验证不满足约束条件
        assert self.instance._validate_columns(main_cols, assistant_cols) is False

    def test_edge_case_multiple_main_cols(self):
        """测试多个主列的情况"""
        # 修改配置以匹配多个主列
        self.test_config["main_col"] = ["mian_col", "main_column"]

        element = {
            'cells': {
                '0_0': {"text": "mian_col", "col": 0, "row": 0, "index": "0_0"},
                '0_1': {"text": "main_column", "col": 1, "row": 0, "index": "0_1"},
                '0_2': {"text": "assistant_col_0", "col": 2, "row": 0, "index": "0_2"},
                '0_3': {"text": "assistant_col_1", "col": 3, "row": 0, "index": "0_3"},
                '1_0': {"text": "data1", "col": 0, "row": 1, "index": "1_0"},
                '1_1': {"text": "data2", "col": 1, "row": 1, "index": "1_1"},
                '1_2': {"text": "data3", "col": 2, "row": 1, "index": "1_2"},
                '1_3': {"text": "data4", "col": 3, "row": 1, "index": "1_3"},
            },
            'class': 'TABLE',
            'index': 1
        }

        main_cols, assistant_cols = self.instance._identify_columns(element)

        # 应该识别出2个主列和2个辅助列
        assert main_cols == [0, 1]
        assert assistant_cols == [2, 3]

        # 验证不满足约束条件（主列超过1个）
        assert self.instance._validate_columns(main_cols, assistant_cols) is False

    def test_integration_full_workflow(self):
        """集成测试 - 完整工作流程"""
        sample_element = self.get_sample_element()
        
        # Mock父类的prepare_table方法
        def mock_prepare_table(elem):
            # 简化的表格结构
            return {
                "rows": len({idx.split("_")[0] for idx in elem["cells"].keys()}),
                "cols": len({idx.split("_")[1] for idx in elem["cells"].keys()}),
                "cells": elem["cells"]
            }
        
        self.instance.__class__.__bases__[0].prepare_table = Mock(side_effect=mock_prepare_table)
        
        tables, elements = self.instance.prepare_table(sample_element)
        
        # 验证结果
        assert len(tables) == 3  # 3个辅助列，生成3个表格
        assert len(elements) == 3
        
        # 验证每个表格都包含主列和一个辅助列
        for table in tables:
            assert table["rows"] == 3  # 原始行数保持不变
            assert table["cols"] == 2  # 主列 + 1个辅助列
