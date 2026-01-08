import copy
import json
import logging
import os
import re
from collections import defaultdict
from decimal import Decimal

from remarkable.answer.node import AnswerItem
from remarkable.common.constants import SZSETableAnswerStatus
from remarkable.common.pattern import PatternCollection
from remarkable.config import project_root
from remarkable.converter import SZSEBaseConverter
from remarkable.plugins.zjh.util import comma_sep_thousands, grep_date, normalize_val, transfer_unit, unit_map

p_multiple = re.compile(r".*(倍[)）]?|比率)$")
p_not_abbr = re.compile(r"(说明书|公司)$|发行人|招股")
p_employment_period = re.compile(r"现任|至今")
p_digital = re.compile(r"^[\d\.%]+$")
p_tmp_ignore_group_key = PatternCollection(r"报告期")


class AnswerNodeCalculator:
    @classmethod
    def calc(cls, formula_list: list[str], field: str = "") -> str | None:
        priority = {"(": 1, "+": 3, "-": 3, "*": 5, "/": 5}  # 定义优先级别
        num_stack = []  # 数据栈
        op_stack = []  # 运算符栈
        for char in formula_list:
            if not cls.is_operator(char):
                num_stack.append(char)
            elif not op_stack or char == "(":
                op_stack.append(char)
            elif char == ")":
                while op_stack and op_stack[-1] != "(":
                    num_stack.append(cls.process(op_stack, num_stack, field))
                if not op_stack:
                    raise SyntaxError("missing (")
                op_stack.pop()
            else:  # char in [+ - * /]
                while op_stack and priority[op_stack[-1]] >= priority[char]:  # 栈中计算符的优先级高(或相等),先计算
                    num_stack.append(cls.process(op_stack, num_stack, field))
                op_stack.append(char)

        while op_stack:
            if op_stack[-1] == "(":
                raise SyntaxError("extra (")
            num_stack.append(cls.process(op_stack, num_stack, field))

        if len(num_stack) == 1:
            return num_stack[0]
        logging.error("error in calc answer_node: %s", num_stack)
        return None

    @staticmethod
    def is_operator(char):
        return char in ["+", "-", "*", "/", "(", ")"]

    @staticmethod
    def is_number(char):
        return p_digital.search(char)

    @classmethod
    def process(cls, op_stack, num_stack, field):
        """
        数据栈出栈2个数据，符号栈出栈一个计算符
        :return:
        """
        operator = op_stack.pop()
        num_b = num_stack.pop()
        num_a = num_stack.pop()
        return cls._calc_item([num_a, operator, num_b], field)

    @classmethod
    def fill_formula_with_answer_node(cls, data, formula_list):
        """
        把公式里的科目名换成对应的answer_node
        :return:
        """
        ret = []
        for char in formula_list:
            if cls.is_operator(char):
                ret.append(char)
            elif cls.is_number(char):
                ret.append(char)
            else:
                val = CYBProspectusConverter.get_text_in_dump_node(data.get(char))
                if not val:
                    return False, None
                ret.append(val)
        return True, ret

    @staticmethod
    def _calculate(num_a, operator, num_b):
        if operator == "+":
            ret = num_a + num_b
        elif operator == "-":
            ret = num_a - num_b
        elif operator == "*":
            ret = num_a * num_b
        elif operator == "/":
            ret = num_a / num_b
        else:
            raise Exception("Unknown operator %s" % operator)

        return ret

    @classmethod
    def _calc_item(cls, formula_list, field=""):
        """
        处理二元四则运算
        :param field:
        :param formula_list:
        :return:
        """
        try:
            eval_operators = []
            percentage = False  # 计算结果是否转换成百分数
            is_plusminus = False  # 是否是加减法
            is_all_percentage = True  # 参与计算的数值是否都是百分数
            for oper in formula_list:
                if oper in ["/", "*", "+", "-"]:
                    eval_operators.append(oper)
                    if oper == "/" and not p_multiple.search(field):  # 类似 流动比率（倍）的不用转成百分数
                        percentage = True
                    elif oper in ["+", "-"]:
                        is_plusminus = True
                else:
                    if "%" not in oper:
                        is_all_percentage = False
                    success, val = transfer_unit(oper, to_unit="1")  # 处理成量纲为1的数值
                    if not success:
                        return None
                    eval_operators.append(normalize_val(val))

            if not percentage:
                percentage = is_all_percentage

            ret = cls._calculate(*eval_operators)

            if is_plusminus:  # 加减法的计算结果重新赋予单位
                to_unit = SZSEBaseConverter.get_to_unit(field)
                ret = Decimal(ret) / unit_map[to_unit]
                ret = comma_sep_thousands(ret, percentage, decimal_places=2)
                ret += to_unit
            else:
                ret = comma_sep_thousands(ret, percentage, decimal_places=2)

            return ret
        except Exception as e:
            logging.error("error in _calc_item")
            logging.error(e)
            return None


class CYBProspectusConverter(SZSEBaseConverter):
    """创业板招股说明书信息抽取"""

    num_map = {1: "一", 2: "二", 3: "三"}

    @property
    def json_schema(self):
        export_config = {"创业板招股说明书信息抽取": self.export_schema}
        ret = []

        def _gen_json_schema(export_config):
            for name, value in export_config.items():
                is_leaf = "custom_handler" in value
                if is_leaf:
                    orders = value.get("orders", [])
                    schema = {k: {"type": "str", "is_leaf": is_leaf} for k in orders}
                else:
                    orders = list(value.keys())
                    schema = {k: {"type": k, "is_leaf": is_leaf} for k in orders}
                ret.append({"name": name, "orders": orders, "schema": schema})

                if not is_leaf:
                    _gen_json_schema(value)

        _gen_json_schema(export_config)
        return {"schemas": ret}

    @property
    def default_schema_path(self):
        # '深交所信息抽取-创业板-注册制-财务基础数据|非经常性损益表|报告期'
        ret = {}
        base_schema_path = "深交所信息抽取-创业板-注册制-财务基础数据"
        for tab, export_config in self.export_schema.items():
            tab_schema = {}  # 财务基础数据中 标注科目==导出科目, 只需要在后面补一级 '数值'
            for export_field, config in export_config.items():
                export_field_schema_path = defaultdict(dict)
                to_be_picked_by_order = self.to_be_picked_by_order(config)
                for schema, value in to_be_picked_by_order.items():
                    if isinstance(value, dict):
                        schema_table_name = list(value.keys())[0]
                        schema_alias = value[schema_table_name][0]
                    else:  # isinstance of list:
                        schema_table_name = value[0]
                        schema_alias = schema

                    schema_path = f"{base_schema_path}|{schema_table_name}|{schema_alias}"
                    if tab == "财务基础数据":
                        schema_path += "|数值"
                    export_field_schema_path[schema] = schema_path

                for schema, path in config.get("default_path", {}).items():
                    if isinstance(path, str):
                        schema_path = f"{base_schema_path}|{path}"
                        export_field_schema_path[schema] = schema_path
                    elif isinstance(path, dict):
                        for key, val in path.items():
                            schema_path = f"{base_schema_path}|{val}"
                            export_field_schema_path[schema].update({key: schema_path})

                tab_schema[export_field] = export_field_schema_path
            ret[tab] = tab_schema

        return ret

    @property
    def export_schema(self):
        issuer_information_tables = "五-发行人基本情况||二-发行人基本情况"
        institution_schema = {
            "姓名": "三-本次发行的有关机构|人员信息|姓名",
            "身份证号/护照号": "三-本次发行的有关机构|人员信息|身份证号",
            "办公电话": "三-本次发行的有关机构|人员信息|办公电话",
            "传真": "三-本次发行的有关机构|人员信息|传真",
            "EMAIL地址": "三-本次发行的有关机构|人员信息|EMAIL地址",
            "手机": "三-本次发行的有关机构|人员信息|手机",
        }
        core_staff_schema = {
            "姓名": "五-董监高核情况-表格|姓名",
            "身份证号/护照号": "五-董监高核情况-表格|身份证号",
            "办公电话": "五-董监高核情况-表格|办公电话",
            "传真": "五-董监高核情况-表格|传真",
            "EMAIL地址": "五-董监高核情况-表格|EMAIL地址",
            "手机": "五-董监高核情况-表格|手机",
        }
        institution_name_schema = "三-本次发行的有关机构|名称"
        institution_code_schema = "三-本次发行的有关机构|统一社会信用代码"

        return {
            "项目基本情况表": {
                "发行人信息": {
                    "custom_handler": self.custom_issuer_information,
                    "default_path": {
                        "实际控制人": "五-发行人基本情况|实际控制人情况|名称",
                        "实际控制人持股比例（%）": "五-发行人基本情况|实际控制人情况|持股比例",
                        "拟发行股数占发行后总股本比例（%）": "三-本次发行的基本情况|拟发行量（万股）",
                        "是否存在员工持股计划、股权激励计划": "五-员工持股与股权激励计划|是否存在员工持股计划",
                    },
                    "picked_fields": {
                        issuer_information_tables: [
                            "申报企业（全称）",
                            "申报企业（简称）",
                            "申报企业曾用名",
                            "公司类型",
                            "统一社会信用代码",
                            "公司设立时间",
                            "注册地（省市或境外）",
                            "注册地（市区县）",
                            "法人代表",
                        ],
                        "六-主营业务||二-主营业务": [
                            "主营业务",
                        ],
                        "五-最近一次增资": [
                            "最近一次增资日期",
                            "最近一次增资比例",
                            "最近一次增资金额",
                            "最近一次增资前金额",
                            "最近一次增资后金额",
                        ],
                    },
                    "to_be_picked_by_order": {
                        "证监会行业": {
                            "六-行业基本情况（证监会）": ["证监会行业"],
                        },
                        "证监会行业细分": {
                            "六-行业基本情况（证监会）": ["证监会行业细分"],
                        },
                        "申万一级行业": {
                            "六-行业基本情况（申万）": ["申万一级行业"],
                        },
                        "申万二级行业": {
                            "六-行业基本情况（申万）": ["申万二级行业"],
                        },
                        "最近一期审计基准日": ["八-注册会计师的审计意见"],
                        "采用的会计准则": ["八-财务报表编制基础"],
                        "拟发行量（万股）": ["三-本次发行的基本情况", "二-本次发行概况"],
                        "发行前总股本（万股）": {
                            "五-发行人股本情况-总股本": ["发行前总股本"],
                            "三-本次发行的基本情况": ["发行前总股本（万股）"],
                            "二-本次发行概况": ["发行前总股本（万股）"],
                        },
                        "预计募集资金总额（万元）": ["三-本次发行的基本情况", "二-本次发行概况"],
                        "预计募集资金净额（万元）": ["三-本次发行的基本情况", "二-本次发行概况"],
                        "上市标准": ["二-发行人上市标准"],
                    },
                    "fields_need_calc": {
                        "拟发行股数占发行后总股本比例（%）": [
                            "拟发行量（万股）",
                            "/",
                            "(",
                            "拟发行量（万股）",
                            "+",
                            "发行前总股本（万股）",
                            ")",
                        ],
                        "最近一次增资后金额": ["最近一次增资前金额", "+", "最近一次增资金额"],
                        "最近一次增资前金额": ["最近一次增资后金额", "-", "最近一次增资金额"],
                        "最近一次增资比例（%）": [
                            "(",
                            "最近一次增资后金额",
                            "-",
                            "最近一次增资前金额",
                            ")",
                            "/",
                            "最近一次增资前金额",
                        ],
                    },
                },
                "发行前股本结构（万股）": {
                    "custom_handler": self.custom_stock_structure,
                    "default_path": {
                        "国有股东持有股份": "五-国有股东和外资股东情况|持股数量",
                        "境内民营机构或自然人持有股份": "五-国有股东和外资股东情况|持股数量",
                        "境外股东持有股份": "五-国有股东和外资股东情况|持股数量",
                        "其他": "五-国有股东和外资股东情况|持股数量",
                        "合计": "五-国有股东和外资股东情况|持股数量",
                    },
                },
                "持股5%以上（含5%）股东信息": {
                    "custom_handler": self.custom_holder,
                    "picked_fields": {"五-发行人股本情况": ["名称", "持股比例", "股东性质"]},
                },
            },
            "联系方式": {
                "发行人": {
                    "custom_handler": self.custom_issuer,
                    "default_path": {
                        "注册地址": "二-发行人基本情况|注册地（省市或境外）",
                        "董事长": core_staff_schema,
                        "总经理": core_staff_schema,
                        "董秘": core_staff_schema,
                    },
                    "picked_fields": {
                        issuer_information_tables: ["公司网址", "通讯地址", "邮编"],
                        "二-发行人基本情况": ["注册地（省市或境外）", "注册地（市区县）"],
                    },
                },
                "保荐机构": {
                    "custom_handler": self.custom_sponsor_institution,
                    "default_path": {
                        "保荐机构一名称": institution_name_schema,
                        "保荐机构二名称": institution_name_schema,
                        "保荐机构三名称": institution_name_schema,
                        "统一社会信用代码": institution_code_schema,
                        "保荐业务负责人": institution_schema,
                        "保荐代表人A": institution_schema,
                        "保荐代表人B": institution_schema,
                        "项目协办人": institution_schema,
                    },
                },
                "会计师事务所": {
                    "custom_handler": self.custom_accounting_firm,
                    "default_path": {
                        "会计师事务所名称": institution_name_schema,
                        "统一社会信用代码": institution_code_schema,
                        "会计师事务所负责人": institution_schema,
                        "签字会计师A": institution_schema,
                        "签字会计师B": institution_schema,
                        "签字会计师C": institution_schema,
                    },
                },
                "律师事务所": {
                    "custom_handler": self.custom_law_firm,
                    "default_path": {
                        "律师事务所名称": institution_name_schema,
                        "统一社会信用代码": institution_code_schema,
                        "律师事务所负责人": institution_schema,
                        "签字律师A": institution_schema,
                        "签字律师B": institution_schema,
                        "签字律师C": institution_schema,
                    },
                },
                "资产评估机构": {
                    "custom_handler": self.custom_assets_appraisal_firm,
                    "default_path": {
                        "资产评估机构一": institution_name_schema,
                        "资产评估机构二": institution_name_schema,
                        "统一社会信用代码": institution_code_schema,
                        "评估事务所负责人": institution_schema,
                        "签字评估师A": institution_schema,
                        "签字评估师B": institution_schema,
                        "签字评估师C": institution_schema,
                    },
                },
            },
            "财务基础数据": {
                "合并资产负债表主要数据（万元）": {
                    "orders": [
                        "项目-1（审计基准日）",
                        "流动资产",
                        "非流动资产",
                        "资产总额",
                        "流动负债",
                        "非流动负债",
                        "负债总额",
                        "净资产",
                        "归属于母公司所有者权益",
                    ],
                    "custom_handler": self.custom_financial,
                    "default_path": {
                        "资产总额": "合并资产负债表|流动资产",
                        "负债总额": "合并资产负债表|流动负债",
                        "净资产": "合并资产负债表|流动资产",
                    },
                    "picked_fields": {
                        "合并资产负债表": [
                            "报告期",
                            "流动资产",
                            "非流动资产",
                            "流动负债",
                            "非流动负债",
                            "归属于母公司所有者权益",
                        ],
                        "八-主要财务指标表": ["归属于母公司所有者权益"],
                        "二-主要财务指标表": ["归属于母公司所有者权益"],
                    },
                    "to_be_picked_by_order": {
                        "归属于母公司所有者权益": ["合并资产负债表", "八-主要财务指标表", "二-主要财务指标表"],
                        "项目-1（审计基准日）": {
                            "合并资产负债表": ["报告期"],
                        },
                    },
                    "fields_need_calc": {
                        "资产总额": ["流动资产", "+", "非流动资产"],
                        "负债总额": ["流动负债", "+", "非流动负债"],
                        "净资产": ["资产总额", "-", "负债总额"],
                    },
                },
                "合并利润表主要数据（万元）": {
                    "orders": [
                        "项目-2",
                        "营业收入",
                        "营业利润",
                        "综合毛利率（%）",
                        "管理费用/营业收入（%）",
                        "销售费用/营业收入（%）",
                        "财务费用/营业收入（%）",
                        "利润总额",
                        "净利润",
                        "综合收益总额",
                        "归属于母公司所有者的净利润",
                        "扣除所得税影响后的非经常性损益",
                        "扣除非经常性损益后的归属于母公司所有者净利润",
                    ],
                    "custom_handler": self.custom_financial,
                    "default_path": {
                        "管理费用/营业收入（%）": "合并利润表|管理费用",
                        "销售费用/营业收入（%）": "合并利润表|销售费用",
                        "财务费用/营业收入（%）": "合并利润表|财务费用",
                    },
                    "picked_fields": {
                        "合并利润表": [
                            "报告期",
                            "营业收入",
                            "营业利润",
                            "利润总额",
                            "净利润",
                            "综合收益总额",
                            "管理费用",
                            "销售费用",
                            "财务费用",
                        ],
                        "期间费用表": ["管理费用/营业收入（%）", "销售费用/营业收入（%）", "财务费用/营业收入（%）"],
                        "非经常性损益表": ["扣除所得税影响后的非经常性损益"],
                    },
                    "to_be_picked_by_order": {
                        "综合毛利率（%）": [
                            "经营成果表",
                            "盈利能力表",
                            "毛利表",
                            "风险因素",
                            "综合毛利率（其他）",
                        ],  # 可能的来源，顺序即优先级
                        "扣除非经常性损益后的归属于母公司所有者净利润": ["非经常性损益表", "八-主要财务指标表"],
                        "归属于母公司所有者的净利润": ["合并利润表", "八-主要财务指标表", "二-主要财务指标表"],
                        "项目-2": {
                            "合并利润表": ["报告期"],
                        },
                    },
                    "fields_need_calc": {
                        "管理费用/营业收入（%）": ["管理费用", "/", "营业收入"],
                        "销售费用/营业收入（%）": ["销售费用", "/", "营业收入"],
                        "财务费用/营业收入（%）": ["财务费用", "/", "营业收入"],
                    },
                },
                "合并现金流量表主要数据（万元）": {
                    "orders": [
                        "项目-3",
                        "经营活动产生的现金流量净额",
                        "投资活动产生的现金流量净额",
                        "筹资活动产生的现金流量净额",
                        "现金及现金等价物净增加额",
                    ],
                    "custom_handler": self.custom_financial,
                    "picked_fields": {
                        "合并现金流量表": [
                            "报告期",
                            "经营活动产生的现金流量净额",
                            "投资活动产生的现金流量净额",
                            "筹资活动产生的现金流量净额",
                            "现金及现金等价物净增加额",
                        ]
                    },
                    "to_be_picked_by_order": {
                        "项目-3": {
                            "合并现金流量表": ["报告期"],
                        },
                    },
                },
                "最近三年一期主要财务指标表": {
                    "orders": [
                        "项目-4",
                        "流动比率（倍）",
                        "速动比率（倍）",
                        "资产负债率（母公司报表）（%）",
                        "资产负债率（合并报表）（%）",
                        "利息保障倍数（倍）",
                        "应收账款周转率（次）",
                        "存货周转率（次）",
                        "研发投入/营业收入（%）",
                        "现金分红（万元）",
                        "每股净资产（元）",
                        "每股经营活动现金流量（元）",
                        "每股净现金流量（元）",
                        "基本每股收益（元）",
                        "稀释每股收益（元）",
                        "加权平均净资产收益率（扣除非经常性损益前）（%）",
                        "加权平均净资产收益率（扣除非经常性损益后）（%）",
                    ],
                    "custom_handler": self.custom_financial,
                    "picked_fields": {
                        "八-净资产收益率表": [
                            "报告期",
                            "加权平均净资产收益率（扣除非经常性损益前）（%）",
                            "加权平均净资产收益率（扣除非经常性损益后）（%）",
                        ],
                    },
                    "to_be_picked_by_order": {
                        "研发投入/营业收入（%）": ["八-主要财务指标表", "二-主要财务指标表"],
                        "现金分红（万元）": ["八-主要财务指标表", "二-主要财务指标表", "二-主要财务指标表"],
                        "基本每股收益（元）": ["合并利润表", "八-主要财务指标表", "二-主要财务指标表"],
                        "稀释每股收益（元）": ["合并利润表", "八-主要财务指标表", "二-主要财务指标表"],
                        "资产负债率（母公司报表）（%）": ["八-主要财务指标表", "二-主要财务指标表"],
                        "利息保障倍数（倍）": ["八-主要财务指标表", "偿债能力表", "二-主要财务指标表"],
                        "速动比率（倍）": ["八-主要财务指标表", "二-主要财务指标表"],
                        "应收账款周转率（次）": ["八-主要财务指标表", "二-主要财务指标表"],
                        "存货周转率（次）": ["八-主要财务指标表", "二-主要财务指标表"],
                        "每股净资产（元）": {
                            "八-主要财务指标表": ["每股净资产（元）", "归属于母公司所有者的每股净资产"],
                            "二-主要财务指标表": ["每股净资产（元）", "归属于母公司所有者的每股净资产"],
                        },
                        "每股经营活动现金流量（元）": ["八-主要财务指标表", "二-主要财务指标表"],
                        "每股净现金流量（元）": ["八-主要财务指标表", "二-主要财务指标表"],
                        "项目-4": {
                            "八-主要财务指标表": ["报告期"],
                        },
                    },
                },
                # TODO 暂时隐藏填报界面的的其他指标
                # '其他指标': {
                #     'orders': ['项目-5', '研发人员数量（硕士及以上学历）（人）', '发明专利数量 （件）'],
                #     'custom_handler': self.custom_financial,
                #     'to_be_picked_by_order': {
                #         '研发人员数量（硕士及以上学历）（人）': ['员工人数表', '员工薪酬表'],
                #         '发明专利数量 （件）': ['其他指标（临时）'],
                #         '项目-5': {
                #             '员工人数表': ['报告期'],
                #         },
                #     },
                # },
            },
            "产品及其他情况表": {
                "主要产品市场占有率": {
                    "custom_handler": self.custom_common,
                    "picked_fields": {
                        "": [
                            "产品名称",
                            "报告期",
                            "报告期营业收入占比（%）",
                            "国内市场占有率（%）",
                            "国内市场占有率排名",
                            "国际市场占有率（%）",
                            "国际市场占有率排名",
                        ]
                    },
                },
                "重大科技专场": {
                    "custom_handler": self.custom_common,
                    "picked_fields": {
                        "": [
                            "项目名称",
                            "项目开始时间",
                            "项目状态",
                            "参与角色",
                            "项目总经费（万元）",
                            "财政拨款经费（万元）",
                            "发行人自筹经费（万元）",
                            "备注",
                        ]
                    },
                },
                "参与标准制定情况": {
                    "custom_handler": self.custom_common,
                    "picked_fields": {
                        "": [
                            "参与制定标准名称",
                            "标准层级",
                            "参与角色",
                            "标准状态",
                            "备注",
                        ]
                    },
                },
                "产品实现进口代替情况": {
                    "custom_handler": self.custom_common,
                    "picked_fields": {
                        "": [
                            "产品名称",
                            "初次上市时间",
                            "国内市场占有率（ % ）",
                            "上市前进口产品市场占有率（ % ）",
                            "目前进口产品市场占有率（ % ）",
                            "实现替代情况描述",
                            "备注",
                        ]
                    },
                },
            },
            "发行人相关人员情况": {
                "发行人相关人员情况": {
                    "custom_handler": self.custom_issuer_people,
                    "default_path": {"任职机构": "五-控股股东和实际控制人情况|任职机构情况|任职机构"},
                    "picked_fields": {issuer_information_tables: ["申报企业（全称）", "申报企业（简称）"]},
                    "to_be_picked_by_order": {
                        "代码": {
                            "二-发行人基本情况": ["统一社会信用代码"],
                        }
                    },
                }
            },
        }

    handlers = {}

    def export_fields(self, export_config):
        fields = set()

        for key in self.to_be_picked_by_order(export_config):
            fields.add(key)

        for key in self.fields_need_calc(export_config):
            fields.add(key)

        return fields

    @staticmethod
    def to_be_picked_by_order(export_config):
        """
        picked_fields: key表示来源,value是一个list,表示需要提取的字段
        to_be_picked_by_order: key表示字段,value表示可能的来源,顺序即优先级
        一般,一个字段不应同时出现在picked_fields和to_be_picked_by_order中;如果同时出现,会采用picked_fields
        :param export_config:
        :return:
        """
        to_be_picked_by_order = export_config.get("to_be_picked_by_order", {})
        for key, value in export_config.get("picked_fields", {}).items():
            possible_tables = key.split("||")
            for field in value:
                to_be_picked_by_order[field] = possible_tables
        return to_be_picked_by_order

    @staticmethod
    def fields_need_calc(export_config):
        return export_config.get("fields_need_calc", {})

    def custom_common(self, data, export_config, group_by=None):
        ret = {}
        to_be_picked_by_order = self.to_be_picked_by_order(export_config)
        fields_need_calc = self.fields_need_calc(export_config)

        for key, possible_tables in to_be_picked_by_order.items():
            ret[key] = self.pick_one_by_order(data, possible_tables, key, assist_field=group_by)

        ret = self.make_group(ret, group_by)
        # 放到make_group后计算，因为可能需要用到来自不同一级字段的二级字段
        ret = self.calc_fields(ret, fields_need_calc)

        return ret

    def custom_financial(self, data, export_config):
        ret = self.custom_common(data, export_config, group_by="报告期")
        ret = self.replenish_default_value(ret, self.export_fields(export_config))
        return ret

    def custom_issuer_information(self, data, export_config):
        ret = self.custom_common(data, export_config)
        ret = ret[0] if ret else {}
        abbr = self.get_abbr_from_paraphrase(data)
        if abbr:
            ret["申报企业（简称）"] = abbr

        if not self.get_text_in_dump_node(ret.get("统一社会信用代码")):
            institution_issuer = (self.get_institutions(data, "发行人") or [{}])[0]
            ret["统一社会信用代码"] = institution_issuer.get("统一社会信用代码")

        table_1 = data.get("五-发行人基本情况")
        table_2 = data.get("二-发行人基本情况")
        fields_map = {
            "证监会行业": ["行业分类（证监会）", "证监会行业"],
            "证监会行业细分": ["行业分类（证监会）", "证监会行业细分"],
            "申万一级行业": ["行业分类（申万）", "申万一级行业"],
            "申万二级行业": ["行业分类（申万）", "申万二级行业"],
            "实际控制人": ["实际控制人情况", "名称"],
            "实际控制人持股比例（%）": ["实际控制人情况", "持股比例"],
        }
        for table in (table_1, table_2):
            for item in table:
                for field, path in fields_map.items():
                    path_item = item.get(path[0]) or [{}]
                    if not self.get_text_in_dump_node(ret.get(field)):
                        if field == "实际控制人":
                            ret[field] = self.recombine_answer(path_item, path[1], "join", ",")
                        elif field == "实际控制人持股比例（%）":
                            ret[field] = self.recombine_answer(path_item, path[1], "addition")
                        else:
                            ret[field] = path_item[0].get(path[1])

        return [ret]

    def custom_stock_structure(self, data, export_config):
        table_1 = data.get("五-国有股东和外资股东情况")
        table_2 = data.get("五-发行人股本情况")

        names = []
        stat = {}
        for table, nature_field in ((table_1, "股东类型"), (table_2, "股东性质")):
            for item in table:
                name = self.get_text_in_dump_node(item.get("名称"))
                if not name or name in names:
                    continue
                nature = self.get_text_in_dump_node(item.get(nature_field))
                if not nature:
                    continue
                nature = self.convert_nature_of_holder(nature)
                count = self.get_text_in_dump_node(item.get("持股数量"))
                if not count:
                    continue
                if nature not in stat:
                    stat[nature] = copy.deepcopy(item["持股数量"])
                else:
                    formula_list = [stat[nature]["text"], "+", count]
                    stat[nature]["text"] = AnswerNodeCalculator.calc(formula_list, "持股数量")
        total = None
        for item in stat.values():
            if not total:
                total = copy.deepcopy(item)
            else:
                formula_list = [total["text"], "+", item["text"]]
                total["text"] = AnswerNodeCalculator.calc(formula_list, "持股数量")
        stat["合计股份"] = total
        return [stat]

    @staticmethod
    def convert_nature_of_holder(nature):
        if nature.startswith("国有"):
            nature = "国有股东持有股份"
        elif nature.startswith("境内"):
            nature = "境内民营机构或自然人持有股份"
        elif nature.startswith("境外"):
            nature = "境外股东持有股份"
        else:
            nature = "其他股份"

        return nature

    def custom_holder(self, data, export_config):
        """
        条件：持股比例>=5%
        :param data:
        :param export_config:
        :return:
        """
        threshold = 0.05
        ret = self.custom_common(data, export_config, group_by="名称")
        valid_ret = []
        for item in ret:
            percentage = normalize_val(self.get_text_in_dump_node(item.get("持股比例")))
            if not percentage:
                logging.debug("五-发行人股本情况:缺少持股比例")
                logging.debug(item)
                continue
            if percentage >= threshold:
                valid_ret.append(item)

        return valid_ret

    def get_institutions(self, data: dict, institutional_type: str) -> list:
        institution = []
        for item in data.get("三-本次发行的有关机构"):
            if institutional_type == self.get_text_in_dump_node(item.get("机构类型")):
                institution.append(item)

        return institution

    def custom_issuer(self, data, export_config):
        ret = self.custom_common(data, export_config)
        ret = ret[0] if ret else {}
        core_staff = {}
        core_staff_table = data.get("五-董监高核情况-表格")
        core_staff_para = data.get("五-董监高核情况-段落")
        institution_issuer = (self.get_institutions(data, "发行人") or [{}])[0]

        for items in [core_staff_table, core_staff_para]:
            for item in items:
                staff_type = item.get("董监高身份")
                if not staff_type:
                    continue
                for s_type in staff_type.get("value") or []:
                    if s_type in ["董事长", "总经理", "董秘"] and s_type not in core_staff:
                        item["身份证号/护照号"] = self.join_answer_by_keys(item, ["身份证号", "护照号"], "；")
                        core_staff[s_type] = item

        for item in institution_issuer.get("人员信息", []):
            staff_type = item.get("身份", {}).get("value")
            if not staff_type:
                continue
            if staff_type in ["董事长", "总经理", "董秘"] and staff_type not in core_staff:
                item["身份证号/护照号"] = self.join_answer_by_keys(item, ["身份证号", "护照号"], "；")
                core_staff[staff_type] = item

        ret.update(core_staff)
        ret["注册地址"] = self.join_answer_by_keys(ret, ("注册地（省市或境外）", "注册地（市区县）"))
        self.replenish_fields(ret, ["注册地址", "公司网址", "通讯地址"], institution_issuer)

        return [ret]

    def custom_sponsor_institution(self, data, export_config):
        institutions = self.get_institutions(data, "保荐机构")
        for index, institution in enumerate(institutions[:3]):
            institution[f"保荐机构{self.num_map[index + 1]}名称"] = institution.get("名称")

            for item in institution.get("人员信息", []):
                staff_type = item.get("身份", {}).get("value")
                if not staff_type:
                    continue
                item["身份证号/护照号"] = self.join_answer_by_keys(item, ["身份证号", "护照号"], "；")
                if staff_type in ["保荐业务负责人", "项目协办人"] and staff_type not in institution:
                    institution[staff_type] = item
                elif staff_type == "保荐代表人":
                    if "保荐代表人A" not in institution:
                        institution["保荐代表人A"] = item
                    elif "保荐代表人B" not in institution:
                        institution["保荐代表人B"] = item

        return institutions

    def custom_accounting_firm(self, data, export_config):
        institutions = self.get_institutions(data, "会计师事务所")
        for institution in institutions:
            institution["会计师事务所名称"] = institution.get("名称")

            for item in institution.get("人员信息", []):
                staff_type = item.get("身份", {}).get("value")
                if not staff_type:
                    continue
                item["身份证号/护照号"] = self.join_answer_by_keys(item, ["身份证号", "护照号"], "；")
                if staff_type == "会计师事务所负责人" and staff_type not in institution:
                    institution[staff_type] = item
                elif staff_type == "签字会计师":
                    if "签字会计师A" not in institution:
                        institution["签字会计师A"] = item
                    elif "签字会计师B" not in institution:
                        institution["签字会计师B"] = item
                    elif "签字会计师C" not in institution:
                        institution["签字会计师C"] = item

        return institutions

    def custom_law_firm(self, data, export_config):
        institutions = self.get_institutions(data, "律师事务所")
        for institution in institutions:
            institution["律师事务所名称"] = institution.get("名称")

            for item in institution.get("人员信息", []):
                staff_type = item.get("身份", {}).get("value")
                if not staff_type:
                    continue
                item["身份证号/护照号"] = self.join_answer_by_keys(item, ["身份证号", "护照号"], "；")
                if staff_type == "律师事务所负责人" and staff_type not in institution:
                    institution[staff_type] = item
                elif staff_type == "签字律师":
                    if "签字律师A" not in institution:
                        institution["签字律师A"] = item
                    elif "签字律师B" not in institution:
                        institution["签字律师B"] = item
                    elif "签字律师C" not in institution:
                        institution["签字律师C"] = item

        return institutions

    def custom_assets_appraisal_firm(self, data, export_config):
        institutions = self.get_institutions(data, "资产评估机构")
        for index, institution in enumerate(institutions[:2]):
            institution[f"资产评估机构{self.num_map[index + 1]}"] = institution.get("名称")

            for item in institution.get("人员信息", []):
                staff_type = item.get("身份", {}).get("value")
                if not staff_type:
                    continue
                item["身份证号/护照号"] = self.join_answer_by_keys(item, ["身份证号", "护照号"], "；")
                if staff_type == "评估事务所负责人" and staff_type not in institution:
                    institution[staff_type] = item
                elif staff_type == "签字评估师":
                    if "签字评估师A" not in institution:
                        institution["签字评估师A"] = item
                    elif "签字评估师B" not in institution:
                        institution["签字评估师B"] = item
                    elif "签字评估师C" not in institution:
                        institution["签字评估师C"] = item

        return institutions

    def custom_issuer_people(self, data, export_config):
        ret = self.custom_common(data, export_config)
        ret = ret[0] if ret else {}
        institution_issuer = (self.get_institutions(data, "发行人") or [{}])[0]
        if self.get_text_in_dump_node(institution_issuer.get("统一社会信用代码")):
            ret["代码"] = institution_issuer["统一社会信用代码"]
        ret["法人或自然人名称（包括全称及简称）"] = self.join_answer_by_keys(
            ret, ["申报企业（全称）", "申报企业（简称）"], "；"
        )
        ret["职位"] = {"data": [], "text": "发行人"}
        ret["任职机构"] = {}

        holder = data["五-控股股东和实际控制人情况"]
        for item in holder:
            item["法人或自然人名称（包括全称及简称）"] = self.join_answer_by_keys(item, ["全称", "简称"], "；")
            item["代码"] = self.join_answer_by_keys(item, ["股票代码", "统一社会信用代码", "身份证号", "护照号", "；"])
            offices = []
            for employment in item.get("任职机构情况") or [{}]:
                period = self.get_text_in_dump_node(employment.get("任职期间"))
                if period and p_employment_period.search(period):
                    offices.append(employment.get("任职机构"))
            if offices:
                item["任职机构"] = self.join_answers(offices, "；")

        core_staff = {}
        core_staff_table = data.get("五-董监高核情况-表格")
        core_staff_para = data.get("五-董监高核情况-段落")

        for items in [core_staff_table, core_staff_para]:
            for item in items:
                item["法人或自然人名称（包括全称及简称）"] = item.get("姓名")
                item["代码"] = self.join_answer_by_keys(item, ["身份证号", "护照号"], "；")
                if self.get_text_in_dump_node(ret["法人或自然人名称（包括全称及简称）"]):
                    item["任职机构"] = ret["法人或自然人名称（包括全称及简称）"]
                else:
                    item["任职机构"] = {"data": [], "text": "发行人"}
                staff_type = self.get_text_in_dump_node(item.get("董监高身份"))
                if not staff_type:
                    continue
                item["职位"] = copy.deepcopy(item["董监高身份"])
                staff_text = (
                    item["职位"]["text"].replace("董事长", "董事").replace("总经理", "高管").replace("其他", "")
                )
                staff_text = "；".join([x for x in staff_text.split("\n") if x])
                if not staff_text:
                    continue
                item["职位"]["text"] = staff_text

                name = self.get_text_in_dump_node(item.get("姓名"))
                if not name:
                    continue
                if name in core_staff:
                    continue
                core_staff[name] = item

        return [ret] + holder + list(core_staff.values())

    def join_answer_by_keys(self, answer, keys, separator=""):
        items = []
        for key in keys:
            items.append(answer.get(key))
        return self.join_answers(items, separator)

    def join_answers(self, answers, separator=""):
        words = []
        ans = []
        data = []
        for answer in answers:
            word = self.get_text_in_dump_node(answer)
            if word:
                words.append(word)
                ans.append(answer)
                data.extend(answer["data"])
        if not words:
            return None
        text = separator.join(words)
        new_ans = copy.deepcopy(ans[0])
        new_ans["text"] = text
        new_ans["data"] = data
        return new_ans

    def recombine_answer(self, answer_list: list, field: str, mode: str = "join", separator: str = "") -> dict | None:
        index_keys = []
        index_answer = {}
        for index, answer in enumerate(answer_list):
            if not answer or not answer.get(field):
                continue
            index_key = "_".join((field, str(index)))
            index_keys.append(index_key)
            index_answer[index_key] = answer[field]

        if not index_keys:
            return None

        if mode == "join":
            return self.join_answer_by_keys(index_answer, index_keys, separator)
        if mode == "addition":
            formula_list = []
            for key in index_keys:
                formula_list.append(key)
                formula_list.append("+")
            formula_list.pop()
            success, formula_list = AnswerNodeCalculator.fill_formula_with_answer_node(index_answer, formula_list)
            if success:
                if len(formula_list) == 1:
                    return formula_list[0]
                text = AnswerNodeCalculator.calc(formula_list)
                new_ans = copy.deepcopy(index_answer[index_keys[0]])
                new_ans["text"] = text
                return new_ans
        return None

    def get_abbr_from_paraphrase(self, data):
        paraphrase = data["一-释义"]
        if not paraphrase:
            return None
        for item in paraphrase[:3]:
            abbr_text = self.get_text_in_dump_node(item.get("简称"))
            full_text = self.get_text_in_dump_node(item.get("全称/释义"))
            if not (abbr_text and full_text):
                continue
            match = re.compile(r"[,、，]").split(abbr_text)
            if match:
                for text in match[::-1]:
                    if not text:
                        continue
                    if p_not_abbr.search(text):
                        continue
                    if text[-1] in full_text and text[-2] in full_text:
                        abbr = copy.deepcopy(item.get("简称"))
                        abbr["text"] = text
                        return abbr

        return None

    def replenish_fields(self, data, fields, source):
        """
        如果缺失field,则尝试从source里提取
        :param data:
        :param fields:
        :param source: 备选来源
        :return:
        """
        for field in fields:
            if self.get_text_in_dump_node(data.get(field)):
                continue
            if self.get_text_in_dump_node(source.get(field)):
                data[field] = source[field]

    def find_postcode(self, address):
        city_postcodes = self.get_city_postcodes()
        citys = "|".join(city_postcodes.keys())
        city_pattern = re.compile(re.compile(r"{}".format(citys)))
        match = city_pattern.search(self.get_text_in_dump_node(address))
        if match:
            city = match.group()
            return city_postcodes[city]
        return None

    @staticmethod
    def get_city_postcodes():
        city_postcodes_file = os.path.join(project_root, "data/szse_output/city_postcodes.json")
        with open(city_postcodes_file) as file_obj:
            city_postcodes = json.load(file_obj)
        return city_postcodes

    @staticmethod
    def replenish_default_value(ret: list, fields: set) -> list:
        """
        按照导出需要的fields,将ret重新组织一遍,没有的赋值{}
        :return:
        """
        if not ret:
            answer = {}
            for field in fields:
                answer[field] = {}
            ret.append(answer)
            return ret

        new_ret = []
        for answer in ret:
            new_ans = {}
            for field in fields:
                item = answer.get(field, {}) or {}
                new_ans[field] = item
            new_ret.append(new_ans)
        return new_ret

    def post_process(self, ret: list) -> list:
        for answer in ret:
            for field, item in answer.items():
                self.convert_currency_unit(field, item)

        return ret

    def calc_fields(self, data: list, fields_need_calc: dict) -> list:
        for item in data:
            for field, operators in fields_need_calc.items():
                if item.get(field):  # 已有field字段,则不再计算
                    continue
                success, formula_list = AnswerNodeCalculator.fill_formula_with_answer_node(item, operators)
                if not success:
                    continue
                val = AnswerNodeCalculator.calc(formula_list, field)
                if not val:
                    continue
                operator_items = copy.deepcopy([item.get(x) for x in operators if item.get(x)])
                for operator_item in operator_items[1:]:
                    operator_items[0]["data"].extend(operator_item["data"])
                operator_items[0]["text"] = val
                item[field] = operator_items[0]
                item[field]["formula"] = self.gen_formula_for_display(field, operators, item, val)
        return data

    @staticmethod
    def gen_formula_for_display(field, operators, data, formula_res):
        operators = copy.deepcopy(operators)
        data = copy.deepcopy(data)
        formula = [{"item": field, "data": formula_res}, {"item": "=", "data": {}}]
        for char in operators:
            if AnswerNodeCalculator.is_operator(char) or AnswerNodeCalculator.is_number(char):
                formula.append({"item": char, "data": {}})
            else:
                val = data.get(char)
                val.pop("manual", None)
                val.pop("schema_path", None)
                formula.append({"item": char, "data": val})
        return formula

    @staticmethod
    def pick_fields(data, key, required_fields, assist_field=None):
        if assist_field:
            required_fields.append(assist_field)
        ret = []
        for item in data[key]:
            if not item:
                continue
            ret.append({k: v for k, v in item.items() if k in required_fields})
        return ret

    def pick_one_by_order(self, data, possible_tables, origin_field, assist_field=None):
        """
        按照给定的优先级possible_tables，选出origin_field & assist_field都存在的数据
        :param data:
        :param origin_field: 提取的字段
        :param assist_field: 必须同时存在才能提取
        :param possible_tables: [table1, table2] or {table1:[col1, col2], table2:[col3, col4]}
        :return:
        """
        ret = []
        multi_field_alias = isinstance(possible_tables, dict)
        picked_field = ""
        picked_table = ""
        for table_name in possible_tables:
            table_data = data.get(table_name)
            if not table_data:
                continue
            if assist_field and not self.get_text_in_dump_node(table_data[0].get(assist_field)):
                continue

            if multi_field_alias:
                possible_fields = possible_tables[table_name]
            else:
                possible_fields = [origin_field]

            for field in possible_fields:
                """
                有的字段可能从多个表格中提取 该字段在第一个表格里提取不到 第二个表格可以提取到
                此时 会有多组答案，  可能有8个 table_data，  前四个answer没有该字段的答案，  后四个有
                此前判断第一个table_data中没有这个字段的答案级就跳出了 现在修改成遍历所有的答案
                实际问题是schema设置的问题
                速动比率 在此前的设定中 只会从 ['八-主要财务指标表', '二-主要财务指标表']中提取
                现在出现的badcase(810 软通动力)中，答案出现在另外一个表格中，于是对应的提取配置就需要打开multi_elements
                """
                for sub_table_data in table_data:
                    node = sub_table_data.get(field)
                    if not node:
                        continue
                    if self.get_text_in_dump_node(node):
                        picked_field = field
                        picked_table = table_name
                        break
                if picked_field:
                    break
            if picked_field:
                break

        if not picked_field:
            return ret

        for item in data[picked_table]:
            field_ret = {origin_field: item.get(picked_field)}
            if assist_field:
                field_ret[assist_field] = item.get(assist_field)
            ret.append(field_ret)
        return ret

    @staticmethod
    def get_text_in_dump_node(dump_node):
        if not dump_node:
            return None

        return dump_node.get("text")

    def dump_leaf_node(self, answer):
        schema_path = None
        if self.is_amount_node(answer):
            keyword = "数值" if "数值" in answer else "金额"
            if not answer[keyword]:
                return {"data": [], "text": "", "manual": False, schema_path: schema_path}
            text = answer[keyword].plain_text
            if text in ["-", "-注"]:
                text = "0.00"
            elif answer["单位"] and answer["单位"].plain_text not in text:
                text += answer["单位"].plain_text
                # 数值跟单位是两个框时 单位的框不显示
                # answer[keyword].data.extend(answer['单位'].data)
            schema_path = "|".join([item.split(":")[0] for item in json.loads(answer[keyword]["key"])])
            return {"data": answer[keyword].data, "text": text, "manual": False, "schema_path": schema_path}
        if isinstance(answer, AnswerItem):
            schema_path = "|".join([item.split(":")[0] for item in json.loads(answer["key"])])
            self.revise(answer)
            return {
                "data": answer.data,
                "text": answer.plain_text,
                "value": answer.value,
                "manual": False,
                "schema_path": schema_path,
            }
        raise Exception("Unsupported leaf node to dump!")

    def answer_dump(self, answer):
        if not answer:
            return answer
        for ans in answer:
            if self.is_amount_node(ans):  # amount_node肯定是叶子节点,只有一个 ans
                return self.dump_leaf_node(ans)
            for col, val in ans.items():
                if isinstance(val, AnswerItem):
                    val = self.dump_leaf_node(val)
                else:
                    val = self.answer_dump(val)
                ans[col] = val
        return answer

    def common_handler(self, answer):
        answer = self.answer_dump(answer)

        return answer

    def revise(self, answer):
        for revise_handler in [self.revise_datetime]:
            success = revise_handler(answer)
            if success:
                break

    def revise_datetime(self, answer):
        if answer.schema["data"]["type"] != "日期":
            return False

        text = answer.plain_text
        if "报告期" in answer.key:  # 表示时间点的日期转成"2020/12/31"格式
            success, grep_res = grep_date(text)
            if success:
                text = self.format_date(*grep_res, dformat="/" if "合并资产负债表" in answer.key else "period")

        answer.plain_text = text
        return True

    @staticmethod
    def format_date(year, month, day, dformat="/"):
        # 时期，年 或者 年+月
        if dformat == "period":
            text = f"{year}年"
            if month and month != "12":
                text += f"1-{month}月"
            return text

        # 缺省为时间点，`/` 风格
        return "/".join([n for n in (year, month, day) if n])

    @staticmethod
    def is_contain_year(date):
        success, _ = grep_date(date)
        return success

    def make_group(self, answers: dict | defaultdict, group_by: str) -> list:
        """
        :param group_by:
        :param answers:
            {
                '科目A':[{'报告期': '2020', '科目1':'10'}, {'报告期': '2019', '科目1':'1'}],
                '科目B':[{'报告期': '2020', '科目3':'20'}, {'报告期': '2019', '科目3':'2'}],
                '科目C':[{'报告期': '2020', '科目5':'30'}, {'报告期': '2019', '科目5':'3'}],
            }
        :return:
            [
                {'报告期': '2020', '科目1':'10', '科目3':'20', '科目5':'30'},
                {'报告期': '2019', '科目1':'1', '科目3': '2', '科目5':'3'},
            ]
        """

        def sort_answer(_item):
            # 将有答案的item排在前面
            for key, value in _item.items():
                if key == "报告期":
                    continue
                if not value:
                    return 1
                return 0
            return 1

        if not answers:
            return []

        words = []
        data = defaultdict(dict)
        num = -1
        report_periods_desc = []
        if not group_by:  # group_by为空时,answer里的数据只保留第一个
            num = 1
        elif group_by == "报告期":  # 正常数据包含的年份数量是3或4
            num = 4
            report_periods = answers.get("报告期", [])
            report_periods_desc = [report_period["报告期"]["text"] for report_period in report_periods]
        for answer in answers.values():
            if not answer:
                continue
            answer.sort(key=sort_answer)
            items = answer[:num]
            group_keys = []
            for index, item in enumerate(items):
                group_key = self.get_text_in_dump_node(item.get(group_by))
                if group_key and p_tmp_ignore_group_key.nexts(group_key):
                    # 处理报告期描述是`报告期各期`的情况，一般都是段落中提取到四个答案的情况
                    # 时间描述是 报告期各期 这时提取到的数据是时间是正序，为了跟其他时间一致，需要倒序
                    if not report_periods_desc:
                        continue
                    if len(report_periods_desc) != len(items):
                        continue
                    group_key = report_periods_desc[::-1][index]
                if group_by == "报告期":
                    group_key = group_key[:4] if group_key else None  # 只保留年份
                if group_key not in words:
                    words.append(group_key)
                if (
                    group_key in group_keys
                ):  # 一个字段同一group_key只要一个,避免没有答案的item覆盖了有答案的,参见sort_answer()
                    continue
                group_keys.append(group_key)
                data[group_key].update(item)

        if group_by == "报告期":
            if len(words) > 1:  # 仅在只有一组答案时，允许其报告期为None
                words = [x for x in words if x]
                words = sorted(words, reverse=True)
                words = words[:num]
            ret = [data[word] for word in words if self.is_contain_year(word) or not word]
        else:
            ret = [data[word] for word in words]
        return ret

    def recalculation_adjust(self, key, data):
        if key == "财务基础数据":
            group_by = "报告期"
            fields_group_by_year = self.make_group(data, group_by)
            fields_need_calc = {
                "流动比率（倍）": ["流动资产", "/", "流动负债"],
                "资产负债率（合并报表）（%）": ["负债总额", "/", "资产总额"],
            }
            fields_group_by_year = self.calc_fields(fields_group_by_year, fields_need_calc)
            calc_fields = []
            for item in fields_group_by_year:
                calc_fields.append({k: v for k, v in item.items() if k in fields_need_calc or k == "报告期"})
            ans = {"最近三年一期主要财务指标表": data["最近三年一期主要财务指标表"], "calc": calc_fields}
            data["最近三年一期主要财务指标表"] = self.make_group(ans, group_by)

        return data

    @staticmethod
    def rename_adjust(key, data):
        if key == "项目基本情况表":
            for item in data["发行前股本结构（万股）"]:
                if "其他股份" in item:
                    item["其他"] = item.pop("其他股份")
                if "合计股份" in item:
                    item["合计"] = item.pop("合计股份")

        return data

    def convert(self, *args, **kwargs):
        ret = defaultdict(list)
        if not self.answer_node:
            return ret
        answer_dict = defaultdict(dict)
        for field in self.answer_node.schema["orders"]:
            answer = [x.to_dict() for x in self.answer_node[field].values()] if self.answer_node else []
            answer_dict[field] = self.answer_dump(answer)

        for key, value in self.export_schema.items():
            data = defaultdict(dict)
            for export_field, export_config in value.items():
                data[export_field] = self._convert(export_config["custom_handler"], answer_dict, export_config)

            data = self.recalculation_adjust(key, data)
            data = self.rename_adjust(key, data)
            ret[key].append(data)

        return ret

    def _convert(self, custom_handler, answer_dict, export_config):
        ret = custom_handler(answer_dict, export_config)
        ret = self.post_process(ret)
        return ret

    def gen_answer_status(self):
        ret = {}
        for key, value in self.export_schema.items():
            status_ret = {export_field: SZSETableAnswerStatus.UNCONFIRMED.value for export_field in value}
            ret[key] = status_ret
        return ret
