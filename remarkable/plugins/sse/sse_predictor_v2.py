import functools
import re
from collections import OrderedDict
from copy import deepcopy

from remarkable.common.util import DATE_PATTERN, clean_txt, group_cells, index_in_space_string
from remarkable.plugins.hkex.common import Schema
from remarkable.predictor.predict import AnswerPredictor, CharResult, ParaResult, ResultOfPredictor, TblResult


class Options:
    def __init__(self, **kwargs):
        self.tbl_regs = kwargs.get("tbl_regs", [])
        self.para_regs = kwargs.get("para_regs", [])
        self.anchor_regs = kwargs.get("anchor_regs", [])  # 附近必须出现某些关键词
        self.near_by = kwargs.get("near_by", {})


class SsePredictor(AnswerPredictor):
    SUB_ATTRS = {
        "主要财务数据和财务指标": [
            {
                "name": "资产总额",
                "regs": [re.compile(r"^资产总额")],
            },
            {
                "name": "归属于母公司所有者权益",
                "regs": [re.compile(r"^归属于母公司(所有者|股东)权益")],
            },
            {
                "name": "时间",
                "regs": [re.compile(r"^项目$")],
            },
        ],
        "合并资产负债表": [
            {
                "name": "货币资金",
                "regs": [
                    re.compile(r"^货币资金"),
                ],
                "anchor_regs": [
                    re.compile(r"合并资产负债表"),
                ],
            },
            {
                "name": "流动资产合计",
                "regs": [re.compile(r"^流动资产[合总]计")],
            },
            {
                "name": "长期股权投资",
                "regs": [re.compile(r"^长期股权投资")],
            },
            {
                "name": "非流动资产合计",
                "regs": [re.compile(r"^非流动资产[合总]计")],
            },
            {
                "name": "资产总计",
                "regs": [re.compile(r"^资产[合总]计")],
            },
            {
                "name": "时间",
                "regs": [re.compile(r"^([科项]目|资产)$")],
            },
        ],
        "前十名股东": [
            {
                "name": "股东姓名/名称",
                "regs": [re.compile(r"股东|发起人")],
            },
            {
                "name": "持股数量",
                "regs": [re.compile(r"持股数量?|所持股份|股数")],
            },
            {
                "name": "持股比例",
                "regs": [re.compile(r"(持股)?(比例|占比)")],
            },
        ],
        "募集资金总量及使用情况": [
            {
                "name": "项目名称",
                "regs": [
                    re.compile(r"项目名称"),
                    re.compile(r"募集资金运用方向"),
                    re.compile(r"投资项目"),
                ],
            },
            {
                "name": "投资总额",
                "regs": [
                    re.compile(r"^(项目)?总投资$"),
                    re.compile(r"投资.*额|预算"),
                ],
            },
            {
                "name": "募集资金投资额",
                "regs": [
                    re.compile(r"募集资金"),
                ],
            },
            {
                "name": "审批文号",
                "regs": [re.compile(r"审批文号")],
            },
        ],
        "前五供应商": [
            {
                "name": "供应商名称",
                "regs": [
                    re.compile(r"^(供[应货]商|项目|单位)(名称)?"),
                ],
            },
            {
                "name": "采购额",
                "regs": [
                    re.compile(r"^(外泄)?(采购)?金?额"),
                ],
            },
            {
                "name": "时间",
                "regs": [re.compile(r"^(时间|年[度份]|期间|报告期)$")],
            },
        ],
    }

    def __init__(self, *args, **kwargs):
        super(SsePredictor, self).__init__(*args, **kwargs)
        self.schema_obj = Schema(self.mold)
        self.register = {
            "科创板招股说明书信息抽取POC": [
                {
                    "attr": "发行人情况-发行人名称",
                    "func": self.tbl_or_para,
                    "options": {
                        "tbl_regs": [
                            re.compile(r"^(注册)?(发行人|中文|公司)名称[:：]?"),
                            re.compile(r"^(发行人[:：]?)$"),
                        ],
                        "para_regs": None,
                    },
                },
                {
                    "attr": "发行人情况-成立日期",
                    "func": self.tbl_or_para,
                    "options": {
                        "tbl_regs": [
                            re.compile(r"[成建设]立日期"),
                        ],
                        "para_regs": None,
                    },
                },
                {
                    "attr": "发行人情况-注册资本",
                    "func": self.tbl_or_para,
                    "options": {
                        "tbl_regs": [
                            re.compile(r"^注册资本$"),
                        ],
                        "para_regs": None,
                    },
                },
                {
                    "attr": "发行人情况-法定代表人",
                    "func": self.tbl_or_para,
                    "options": {
                        "tbl_regs": [
                            re.compile(r"法定代表人"),
                        ],
                        "para_regs": None,
                    },
                },
                {
                    "attr": "发行人情况-注册地址",
                    "func": self.tbl_or_para,
                    "options": {
                        "tbl_regs": [
                            re.compile(r"注册地址"),
                        ],
                        "para_regs": None,
                    },
                },
                {
                    "attr": "发行人情况-主要生产经营地址",
                    "func": self.tbl_or_para,
                    "options": {
                        "tbl_regs": [
                            re.compile(r"主要生产经营地址"),
                        ],
                        "para_regs": None,
                    },
                },
                {
                    "attr": "发行人情况-控股股东",
                    "func": self.tbl_or_para,
                    "options": {
                        "tbl_regs": [
                            re.compile(r"控股股东"),
                        ],
                        "para_regs": None,
                    },
                },
                {
                    "attr": "发行人情况-实际控制人",
                    "func": self.tbl_or_para,
                    "options": {
                        "tbl_regs": [
                            re.compile(r"实际控制人"),
                        ],
                        "para_regs": None,
                    },
                },
                {
                    "attr": "发行人情况-行业分类",
                    "func": self.tbl_or_para,
                    "options": {
                        "tbl_regs": [
                            re.compile(r"行业分类"),
                        ],
                        "para_regs": None,
                    },
                },
                {
                    "attr": "发行人情况-在其他交易场所(申请)挂牌或上市的情况",
                    "func": self.tbl_or_para,
                    "options": {
                        "tbl_regs": [
                            re.compile(r"在其他交易场所[(（]申请[）)]挂牌或上市的?情况"),
                        ],
                        "para_regs": None,
                    },
                },
                # 第二节 中介机构
                {
                    "attr": "中介机构-保荐人",
                    "func": self.tbl_or_para,
                    "options": {
                        "tbl_regs": [
                            re.compile(r"保荐人"),
                        ],
                        "para_regs": None,
                    },
                },
                {
                    "attr": "中介机构-主承销商",
                    "func": self.tbl_or_para,
                    "options": {
                        "tbl_regs": [
                            re.compile(r"主承销商"),
                        ],
                        "para_regs": None,
                    },
                },
                {
                    "attr": "中介机构-发行人律师",
                    "func": self.tbl_or_para,
                    "options": {
                        "tbl_regs": [
                            re.compile(r"发行人律师"),
                        ],
                        "para_regs": None,
                    },
                },
                {
                    "attr": "中介机构-其他承销机构",
                    "func": self.tbl_or_para,
                    "options": {
                        "tbl_regs": [
                            re.compile(r"其他承销机构"),
                        ],
                        "para_regs": None,
                    },
                },
                {
                    "attr": "中介机构-审计机构",
                    "func": self.tbl_or_para,
                    "options": {
                        "tbl_regs": [
                            re.compile(r"审计机构"),
                        ],
                        "para_regs": None,
                    },
                },
                {
                    "attr": "中介机构-评估机构",
                    "func": self.tbl_or_para,
                    "options": {
                        "tbl_regs": [
                            re.compile(r"评估机构"),
                        ],
                        "para_regs": None,
                    },
                },
                # 第二节 发行情况
                {
                    "attr": "发行情况-每股面值",
                    "func": self.tbl_or_para,
                    "options": {
                        "tbl_regs": [
                            re.compile(r"每股面值"),
                        ],
                        "para_regs": None,
                    },
                },
                {
                    "attr": "发行情况-发行股数",
                    "func": self.tbl_or_para,
                    "options": {
                        "tbl_regs": [
                            re.compile(r"发行股数"),
                        ],
                        "para_regs": None,
                    },
                },
                {
                    "attr": "发行情况-发行股数占发行后总股本比例",
                    "func": self.tbl_or_para,
                    "options": {
                        "tbl_regs": [
                            re.compile(r"占发行后总股本的?比例"),
                        ],
                        "para_regs": None,
                    },
                },
                {
                    "attr": "发行情况-发行后总股本",
                    "func": self.tbl_or_para,
                    "options": {
                        "tbl_regs": [
                            re.compile(r"^发行后总股本$"),
                        ],
                        "para_regs": None,
                    },
                },
                {
                    "attr": "发行情况-募集资金总额",
                    "func": self.tbl_or_para,
                    "options": {
                        "tbl_regs": [
                            re.compile(r"^募集资金总额$"),
                        ],
                        "para_regs": None,
                    },
                },
                {
                    "attr": "发行情况-募集资金净额",
                    "func": self.tbl_or_para,
                    "options": {
                        "tbl_regs": [
                            re.compile(r"^(预[计估])?募集资金净额$"),
                        ],
                        "para_regs": None,
                    },
                },
                {
                    "attr": "发行情况-募集资金投资项目",
                    "func": self.tbl_or_para,
                    "options": {
                        "tbl_regs": [
                            re.compile(r"^募集资金投资项目$"),
                        ],
                        "para_regs": None,
                    },
                },
                {
                    "attr": "发行情况-发行费用概算",
                    "func": self.tbl_or_para,
                    "options": {
                        "tbl_regs": [
                            re.compile(r"^发行费用概算$"),
                        ],
                        "para_regs": None,
                    },
                },
                # 第二节 财务数据
                {
                    "attr": "财务数据-货币单位",
                    "func": self.tbl_or_para,
                    "options": {
                        "tbl_regs": [
                            re.compile(r"^资产总额[(（](?P<dst>.*?元)[）)]"),
                        ],
                        "para_regs": None,
                    },
                },
                {
                    "attr": "主要财务数据和财务指标",
                    "func": self.col_group,
                },
                # 第二节 上市标准
                {
                    "attr": "上市标准条款编号",
                    "func": self.tbl_or_para,
                    "options": {
                        "para_regs": [
                            re.compile(
                                r"(?P<dst1>2.1.[23](条款?)?|第?二十二条)[^。]*?([“].*?[”])?[^。]*?(?P<dst2>第?[()（）\[\]【】一二三四五六七八九十]+[项条]?)?"
                            )
                        ],
                        "tbl_regs": None,
                    },
                },
                {
                    "attr": "上市标准具体内容",
                    "func": self.tbl_or_para,
                    "options": {
                        "para_regs": [
                            re.compile(
                                r".*[即:：)）“](?P<dst>[^”。]*?(不低于(人民币)?10亿元).*?(不低于(人民币)?5000万元).*?[。”])"
                            ),
                            re.compile(
                                r".*[即:：)）“](?P<dst>[^”。]*?(不低于(人民币)?10亿元).*?(不低于(人民币)?1亿元).*?[。”])"
                            ),
                            re.compile(
                                r".*[即:：)）“](?P<dst>[^”。]*?(不低于(人民币)?15亿元).*?(不低于(人民币)?2亿元).*?(不低于15%).*?[。”])"
                            ),
                            re.compile(
                                r".*[即:：)）“](?P<dst>[^”。]*?(不低于(人民币)?20亿元).*?(不低于(人民币)?3亿元).*?(不低于(人民币)?1亿元).*?[。”])"
                            ),
                            re.compile(
                                r".*[即:：)）“](?P<dst>[^”。]*?(不低于(人民币)?30亿元).*?(不低于(人民币)?3亿元).*?[。”])"
                            ),
                            re.compile(r".*[即:：)）“](?P<dst>[^”。]*?(不低于(人民币)?40亿元).*?[。”])"),
                            re.compile(r".*[即:：)）“](?P<dst>[^”。]*?(不低于(人民币)?100亿元).*?[。”])"),
                            re.compile(
                                r".*[即:：)）“](?P<dst>[^”。]*?(不低于(人民币)?50亿元).*?(不低于(人民币)?5亿元).*?[。”])"
                            ),
                        ],
                        "tbl_regs": None,
                    },
                },
                # 第三节
                {
                    "attr": "保荐人-机构名称",  # TODO: 机构可能不存在, 或存在形式多样
                    "func": self.func_3_1,
                    "options": {
                        "regs": [
                            re.compile(r"保荐(?:人|机构)"),
                        ],
                        "para_regs": [
                            re.compile(r"保荐(?:人|机构).*[：:](?P<dst>.+)"),
                        ],
                    },
                },
                # {
                #     'attr': '保荐人-法定代表人',
                #     'func': self.func_3_2,
                #     'options': {
                #         'regs': [
                #             re.compile(r'法定代表人'),
                #         ],
                #         'para_regs': [
                #             re.compile(r"法.*人[：:](?P<dst>.+)"),
                #         ]
                #     }
                # },
                # 第五节
                {
                    "attr": "实际控制人-姓名",
                    "func": lambda attr, **kwargs: self.tbl_or_para("发行人情况-实际控制人", **kwargs),
                    "options": {
                        "tbl_regs": [
                            re.compile(r"实际控制人"),
                        ],
                        "para_regs": None,
                    },
                },
                # 第五节
                {
                    "attr": "控股股东/实际控制人股份是否存在质押情况",
                    "func": self.tbl_or_para,
                    "options": {
                        "para_regs": [
                            re.compile(r"(?P<dst>（\w+）\D*?[直间]接\D*?质押\D*?。$)"),
                            re.compile(r"(?P<dst>\D*?[直间]接\D*?质押\D*?。$)"),
                        ],
                        "tbl_regs": None,
                        "neg_regs": [
                            re.compile(r"不存在|没有"),
                        ],
                    },
                },
                # 第五节
                {
                    "attr": "持股数量单位",
                    "func": self.tbl_or_para,
                    "options": {
                        "tbl_regs": [
                            re.compile(r"^持股数量[(（]?(?P<dst>.*?股)?[)）]?"),
                        ],
                        "para_regs": None,
                    },
                },
                # 第五节
                {
                    "attr": "持股比例单位",
                    "func": self.tbl_or_para,
                    "options": {
                        "tbl_regs": [
                            re.compile(r"^持股比例[(（]?(?P<dst>.*%)?[)）]?"),
                        ],
                        "para_regs": None,
                    },
                },
                # 第五节
                {"attr": "前十名股东", "func": self.row_group},
                {"attr": "董事会成员", "func": self.board_officer},
                {
                    "attr": "股东关系",
                    "func": self._paras_with_head_and_tail,
                    "options": {
                        "regs": [
                            re.compile(r"[一二三四五六七八九十]*各股东之?间?.{0,2}的?(关联)?关系"),
                            re.compile(r"除.*外.*股东.*不存在.*关系"),
                            re.compile(r"董事.?监事.?高级管理人员.?核心技术人员.{0,4}(简要)?情况"),
                        ]
                    },
                },
                {
                    "attr": "前五供应商货币单位",
                    "func": self.tbl_or_para,
                    "options": {
                        "para_regs": [
                            re.compile(r"单位[:：]\s*?(?P<dst>\w*元)"),
                        ],
                        "tbl_regs": None,
                    },
                },
                # 第六节
                {
                    "attr": "前五供应商",
                    # 'func': self.main_supplier,
                    "func": self.row_group,
                },
                # 第七节
                {
                    "attr": "发行人协议控制架构情况",
                    "func": self.tbl_or_para,
                    "options": {
                        "para_regs": [
                            # re.compile(r'(?P<dst>发行人协议控制架构\D*?协议控制\w*?情况[.。]?)'),
                            re.compile(r"(?P<dst>\D*?协议.*?控制\w*?情况[.。]?)"),
                        ],
                        "tbl_regs": None,
                        "neg_regs": [re.compile(r"(没有|不存在)\w*?协议控制")],
                    },
                },
                # 第八节
                {
                    "attr": "合并资产负债表货币单位",
                    "func": self.tbl_or_para,
                    "options": {
                        "para_regs": [
                            re.compile(r"单位[:：]\s*?(?P<dst>\w*元)"),
                        ],
                        "tbl_regs": None,
                    },
                },
                {
                    "attr": "合并资产负债表",
                    "func": self.col_group,
                },
                {
                    "attr": "审计意见",
                    "func": self.tbl_or_para,
                    "options": {
                        "para_regs": [
                            re.compile(r"(?P<dst>标准无保留意见)"),
                            re.compile(r"(出具|发表)\w+?(?P<dst>\w+?)的?\w+(?:意见|报告)"),
                            re.compile(r"\D*?[号字]”?(?P<dst>\w+?)的?\w+(?:意见|报告)"),
                        ],
                        "tbl_regs": None,
                        "oneshot": True,
                    },
                },
                {
                    "attr": "营业收入分区域分析货币单位",
                    "func": self.tbl_or_para,
                    "options": {
                        "para_regs": [
                            re.compile(r"单位[:：]\s*?(?P<dst>\w*元)"),
                        ],
                        "tbl_regs": None,
                    },
                },
                # {
                #     'attr': '营业收入分区域分析占比单位',
                #     'func': lambda attr, **kwargs: self.region_analysis('营业收入分区域分析', **kwargs),
                #     'options': {
                #         'unit': '%',
                #         'regs': [
                #             re.compile(r'\d?\.?\d+(?P<dst>%)'),
                #             re.compile(r'\D*?(?P<dst>%)'),
                #         ],
                #         'oneshot': True,  # 取到一个结果即退出
                #     }
                # },
                # {
                #     'attr': '营业收入分区域分析',
                #     'func': self.region_analysis,
                #     'options': {
                #         'regs': [
                #             re.compile(r'^(地区|区域|项目)')
                #         ]
                #     }
                # },
                # 第九节
                {
                    "attr": "募集资金总量及使用情况货币单位",
                    "func": self.tbl_or_para,
                    "options": {
                        "para_regs": [
                            re.compile(r"单位[:：](?P<dst>.*?元)"),
                        ],
                        "tbl_regs": None,
                        "anchor_regs": [
                            re.compile(r"募集资金"),
                        ],
                    },
                },
                {"attr": "募集资金总量及使用情况", "func": self.row_group},
                # 第十一节
                # {
                #     'attr': '重大诉讼情况',
                #     'func': self.major_lawsuit,
                #     'options': {
                #         'regs': [
                #             # re.compile(r'(?P<dst>^\w+、?\s*?.*重大诉讼\D*?[至止到]\D*?重大诉讼\D*?。$)'),
                #             re.compile(r'(?P<dst>\D*?[至止到]\D*?重大.*?诉讼\D*?。$)'),
                #         ],
                #         'neg_regs': [
                #             re.compile(r'(无|不存在|没有|不涉及|未涉及)')
                #         ],
                #         'anchor_regs': [
                #             re.compile(r'重大诉讼'),
                #             re.compile(r'诉讼[及或和与]仲裁'),
                #             re.compile(r'仲裁[及或和与]诉讼'),
                #         ],
                #         'anchor_range': (-1, 1)
                #     }
                # },
            ]
        }
        for item in self.register[self.root_schema_name]:
            # if item['attr'] not in ['前五供应商']:
            #     continue
            self.column_analyzers.update(
                {
                    item["attr"]: functools.partial(item["func"], item["attr"], **item.get("options", {})),
                }
            )

    def tbl_or_para(self, attr, **kwargs):
        items = []
        crude_elts = self.get_crude_elements(attr, kwargs.get("col_type", ""))
        tbl_regs = kwargs.get("tbl_regs", [])
        para_regs = kwargs.get("para_regs", [])
        value = None
        for crude_elt in crude_elts:
            ele_typ, elt = self.reader.find_element_by_index(crude_elt["element_index"])
            # print('-----------', elt['page'], ele_typ)
            # print(elt_text_list(elt))
            if not self.b_aim_elt(elt, [], anchor_regs=kwargs.get("anchor_regs", [])):
                continue
            if ele_typ == "TABLE" and tbl_regs is not None:
                items = self.simple_tbl(elt, tbl_regs)
            elif ele_typ == "PARAGRAPH" and para_regs is not None:
                items = self.simple_para(elt, para_regs)
                # todo： 枚举值
                if kwargs.get("neg_regs") and any(items):
                    # 否定判断, "非负即正"
                    for neg_reg in kwargs.get("neg_regs"):
                        if neg_reg.search(clean_txt(elt["text"])):
                            value = self.schema_obj.label_enum_value(attr, -1)
                            break
                    else:
                        value = self.schema_obj.label_enum_value(attr)
            if any(items):
                # for chars in items:
                #     print('*****', [x['text'] for x in chars])
                break
        items = [CharResult(chars) for chars in items]
        return ResultOfPredictor(items, value)

    @staticmethod
    def sorted_cells(cells, reverse=False):
        sorted_d = sorted(cells.items(), key=lambda k_v: int(k_v[0]), reverse=reverse)
        return OrderedDict(sorted_d)

    def col_group(self, attr, **kwargs):
        """
        二级属性
        财务表格中一列数据作为一组答案的情况
        """
        res = []
        options = self.SUB_ATTRS.get(attr, [])
        if not options:
            return []
        crude_elts = self.get_crude_elements(options[0]["name"], attr)
        for crude_elt in crude_elts:
            ele_typ, elt = self.reader.find_element_by_index(crude_elt["element_index"])
            # print('--------', idx, ele_typ, elt['page'])
            if ele_typ == "TABLE":
                if not self.b_aim_elt(elt, [], anchor_regs=options[0].get("anchor_regs", [])):
                    continue
                res = self.col_group_in_tbl(elt, options)
            if any(res):
                break
        return res

    def row_group(self, attr, **kwargs):
        """
        二级属性
        股东/供应商表格中一行数据作为一组答案的情况
        """
        res = []
        options = self.SUB_ATTRS.get(attr, [])
        if not options:
            return []
        crude_elts = self.get_crude_elements(options[0]["name"], attr)

        def handle_data_row(row, cells, options, tbl_info):
            group = {}
            for col in sorted(cells, key=int):  # 从左到右
                cell = cells[col]
                for sub_attr in options:
                    if sub_attr.get("col") and col == sub_attr["col"]:
                        # print('****', row, col, sub_attr['name'], clean_txt(cell['text']))
                        res_obj = ResultOfPredictor([CharResult(cell["chars"])])
                        group.setdefault(sub_attr["name"], res_obj)
            if group and "时间" not in group:
                _time = tbl_info.meta.get("time", {}).get("chars")
                if _time:
                    # print('****', '_time', [x['text'] for x in _time])
                    group.setdefault("时间", ResultOfPredictor([CharResult(_time)]))
            return group

        for crude_elt in crude_elts:
            ele_typ, elt = self.reader.find_element_by_index(crude_elt["element_index"])
            # print('--------', idx, ele_typ, elt['page'])
            if ele_typ == "TABLE":
                if not self.b_aim_elt(elt, [], anchor_regs=options[0].get("anchor_regs", [])):
                    continue
                pass_regs = [
                    re.compile(r"[合总小]计"),
                ]
                pass_regs.extend(options[0]["regs"])
                res = self.iter_rows(elt, options, row_hanlder=handle_data_row, pass_regs=pass_regs)
            if any(res):
                break
        return res

    def _paras_with_head_and_tail(self, attr, **kwargs):
        """
        目标区域是一连续段落，根据提供的头/尾段落的特征
        :param attr:
        :param kwargs:
        :return:
        """
        items = []
        regs = kwargs.get("regs")
        if not regs or len(regs) != 3:
            print("ERROR, _paras_with_head_and_tail need three regs")
        reg_head = regs[0]
        reg_tail = regs[1]
        reg_tail_suffix = regs[2]

        head_para = None
        crude_elts = self.get_crude_elements(attr, kwargs.get("col_type", ""))
        crude_elts = sorted(crude_elts, key=lambda x: x["element_index"])
        for elt in crude_elts:
            ele_typ, elt = self.reader.find_element_by_index(elt["element_index"])
            if ele_typ in ["PARAGRAPH", "TABLE"] or ele_typ is None:
                elt = self.reader.fix_continued_para(elt)  # 修复跨页段落
                if not head_para:
                    if ele_typ == "PARAGRAPH" and reg_head.search(clean_txt(elt["text"])):
                        items.append(ParaResult(elt["chars"], elt))
                        head_para = elt
                        continue

                else:
                    if ele_typ == "PARAGRAPH":
                        items.append(ParaResult(elt["chars"], elt))
                        if reg_tail.search(clean_txt(elt["text"])):
                            break
                        if reg_tail_suffix.search(clean_txt(elt["text"])):
                            items.pop()
                            break
                    elif ele_typ == "TABLE":
                        items.append(TblResult(elt["cells"], elt))

        return ResultOfPredictor(items)

    def func_3_1(self, attr, **kwargs):
        """
        保荐人-机构名称
        形式: 段落 or 表格
        :param attr:
        :param kwargs:
        :return:
        """

        def _fetch_tbl(elt, reg):
            """从表格中提取关键字(下一单元格即为目标字段)"""
            flag = False
            cells = self.cell_ordering(elt)
            for cell_idx, cell in cells.items():
                txt = clean_txt(cell["text"])
                if flag and not cell.get("dummy"):
                    return TblResult(
                        [
                            cell_idx,
                        ],
                        elt,
                    )
                if not flag:
                    if reg.search(txt):
                        flag = True
                    if reg.search(txt) and re.search(r"公司", txt):
                        # 锚定词与关键词可能在同一单元格内
                        return TblResult(
                            [
                                cell_idx,
                            ],
                            elt,
                        )
            return None

        reg = kwargs.get("regs", [])[0]
        elts = self.get_crude_elements(attr, kwargs.get("col_type", ""))
        items = []
        for element in elts:
            ele_typ, element = self.reader.find_element_by_index(element["element_index"])
            if self.b_aim_elt(
                element,
                regs=[
                    reg,
                ]
                + kwargs.get("para_regs", []),
            ):
                if ele_typ == "TABLE":
                    item = _fetch_tbl(element, reg)
                    if item:
                        items.append(item)
                        break
                elif ele_typ == "PARAGRAPH":
                    for para_reg in kwargs.get("para_regs"):
                        res = para_reg.search(element["text"])
                        if res:
                            _start, _end = res.span("dst")
                            items.append(CharResult(element["chars"][_start:_end]))
                            break
                    ele_typ, element = self.reader.find_element_by_index(element["index"] + 1)
                    if ele_typ == "TABLE":
                        item = _fetch_tbl(element, re.compile(r"名称"))
                        # 锚定词在段落中, 通常紧挨的表格中就有需要的关键字, 但锚定词可能会不同, 比如这里变成了'名称'
                        if item:
                            items.append(item)
                            break
            if items:
                break
        return ResultOfPredictor(items)

    # def func_3_2(self, attr, **kwargs):
    #     items = []
    #     para_regs = kwargs.get("para_regs", [])
    #     elts = self.get_crude_elements(attr, kwargs.get('col_type', ''))
    #     for idx, eitem in enumerate(elts):
    #         if idx >= 3:
    #             break
    #         ele_typ, element = self.reader.find_element_by_index(eitem['element_index'])
    #         if ele_typ == "PARAGRAPH":
    #             for para_reg in para_regs:
    #                 res = para_reg.search(element['text'])
    #                 if res:
    #                     _start, _end = res.span('dst')
    #                     items.append(CharResult(element["chars"][_start: _end]))
    #                     break
    #     if items:
    #         return ResultOfPredictor(items)
    #     else:
    #         return self._simple_tbl(attr, **kwargs)

    def main_supplier(self, attr, **kwargs):
        """
        二级属性：前五供应商
        """
        res = []
        options = [
            {
                "name": "供应商名称",
                "regs": [
                    re.compile(r"^(供[应货]商|项目|单位)(名称)?"),
                ],
            },
            {
                "name": "采购额",
                "regs": [
                    re.compile(r"^(外泄)?(采购)?金?额"),
                ],
            },
            {
                "name": "时间",
                "regs": [re.compile(r"^(时间|年[度份]|期间|报告期)$")],
            },
        ]

        crude_elts = self.get_crude_elements(options[0]["name"], attr)

        def get_tbl_time(tbl_idx):
            """
            表格上方的时间
            """
            prev_elts = self.reader.find_elements_near_by(tbl_idx, step=-1, amount=3)
            for elt in prev_elts:
                if elt["class"] == "PARAGRAPH":
                    matched = DATE_PATTERN.search(clean_txt(elt["text"]))
                    if matched:
                        sp_start, sp_end = index_in_space_string(elt["text"], matched.span(0))
                        return elt["chars"][sp_start:sp_end]
            return []

        def get_row_time(cells):
            chars = []
            cells = [cell for cell in cells.values() if not cell.get("dummy") and clean_txt(cell["text"])]
            if len(cells) == 1 and DATE_PATTERN.search(clean_txt(cells[0]["text"])):
                chars = cells[0]["chars"]
            return chars

        for crude_elt in crude_elts:
            ele_typ, elt = self.reader.find_element_by_index(crude_elt["element_index"])
            cond = {
                "regs": options[0]["regs"],
                "anchor_regs": [re.compile(r"供[应货]商")],
            }
            # 需要跳过的行
            pass_regs = [
                re.compile(r"[合总小]计"),
            ]
            pass_regs.extend(options[0]["regs"])

            # print('--------', idx, ele_typ, elt['page'], self.b_aim_elt(elt, cond))
            if ele_typ == "TABLE" and self.b_aim_elt(elt, **cond):
                tbl_time = get_tbl_time(elt["index"])
                stash_time = None
                cells_by_row, cells_by_col = group_cells(elt["cells"])
                for row in sorted(map(int, cells_by_row.keys())):  # 从上到下
                    group = {}
                    cells = cells_by_row.get(str(row), {})

                    b_header_row, b_time_row, b_sum_row = False, False, False
                    for reg in options[0]["regs"]:
                        if any(reg.search(clean_txt(cell["text"])) for cell in cells.values()):
                            b_header_row = True

                    row_time = get_row_time(cells)
                    if row_time:  # 时间单独一行
                        stash_time = row_time
                        b_time_row = True

                    if any(re.search(r"[合总小]计", clean_txt(cell["text"])) for cell in cells.values()):
                        b_sum_row = True

                    # print('cell_value', row, {k: v['text'] for k, v in cells.items()})
                    # print(b_header_row, b_time_row, b_sum_row)

                    if b_header_row:  # 表头
                        for col, cell in cells.items():
                            if cell.get("dummy"):
                                continue
                            for sub_attr in options:
                                if not sub_attr.get("col") and any(
                                    reg.search(clean_txt(cell["text"])) for reg in sub_attr["regs"]
                                ):
                                    # print('*********', row, col, sub_attr['name'], clean_txt(cell['text']))
                                    sub_attr["col"] = col
                    elif not b_time_row and not b_sum_row:
                        for col, cell in cells.items():
                            for sub_attr in options:
                                if sub_attr.get("col") is not None and col == sub_attr["col"]:
                                    # print('****', row, col, sub_attr['name'], clean_txt(cell['text']))
                                    group.setdefault(sub_attr["name"], ResultOfPredictor([CharResult(cell["chars"])]))
                    if group and "时间" not in group:
                        for _time in [stash_time, tbl_time]:
                            if _time:
                                # print('****', '_time', [x['text'] for x in _time])
                                group.setdefault("时间", ResultOfPredictor([CharResult(_time)]))
                                break
                    if group:
                        res.append(group)
        return res

    def board_officer(self, attr, **kwargs):
        """
        二级属性：董事会成员
        """
        res = []
        options = [
            {"name": "姓名", "regs": [re.compile(r"^(姓名|成员)$")], "col": None},
            {"name": "任职", "regs": [re.compile(r"(职位|任职|职务)")], "col": None},
        ]
        crude_elts = self.get_crude_elements(options[0]["name"], attr)

        def get_resume_chars(name, tbl_idx):
            """
            简历为表格下方的段落，包含董事姓名
            """

            res = []
            stone_para = {}  # 记录姓名出现位置
            next_elts = self.reader.find_elements_near_by(tbl_idx, step=1, amount=100)
            for elt in next_elts:
                if elt["class"] == "PARAGRAPH":
                    para = self.reader.fix_continued_para(elt)
                    name_reg = re.compile(r"%s" % clean_txt(name))

                    if not stone_para:  # 姓名第一次出现
                        if name_reg.search(clean_txt(para["text"])):
                            stone_para = elt
                            res.extend(para["chars"])
                            continue
                    else:
                        if name_reg.search(clean_txt(para["text"])):
                            # 连续出现的段落包含姓名才标注
                            if elt["index"] - 5 >= stone_para["index"]:
                                break
                            else:
                                stone_para = elt
                                res.extend(para["chars"])
                        else:  # 姓名第一次出现的段落，字数小于10
                            if len(stone_para["text"]) <= 10:
                                res.extend(para["chars"])
                                break
            return res

        for crude_elt in crude_elts:
            ele_typ, elt = self.reader.find_element_by_index(crude_elt["element_index"])
            cond = {"regs": options[0]["regs"], "anchor_regs": [re.compile(r"董事")]}
            # print('--------', idx, ele_typ, elt['page'], self.b_aim_elt(elt, cond))
            if ele_typ == "TABLE" and self.b_aim_elt(elt, **cond):
                cells_by_row, cells_by_col = group_cells(elt["cells"])

                # 姓名&任职在表格中
                for row in sorted(cells_by_row, key=int):  # 从上到下
                    group = {}
                    cells = cells_by_row.get(str(row))
                    # print(row, {k: v['text'] for k, v in cells.items()})

                    # 需要跳过的行
                    is_pass_row = False
                    pass_regs = options[0]["regs"]
                    if row != "0":
                        for cell in cells.values():
                            if any(reg.search(clean_txt(cell["text"])) for reg in pass_regs):
                                is_pass_row = True
                                break
                    if is_pass_row:
                        continue

                    # 提取数据
                    for col in sorted(cells, key=int):  # 从左到右
                        cell = cells.get(str(col))
                        if not cell:
                            continue
                        if row == "0":  # 第一行决定子属性出现在哪一列
                            for sub_attr in options:
                                if not sub_attr["col"] and any(
                                    reg.search(clean_txt(cell["text"])) for reg in sub_attr["regs"]
                                ):
                                    # print('*********', row, col, sub_attr['name'], clean_txt(cell['text']))
                                    sub_attr["col"] = col
                        else:  # 标注其余列
                            for sub_attr in options:
                                if sub_attr["col"] is not None and col == sub_attr["col"]:
                                    # print('****', row, col, sub_attr['name'], clean_txt(cell['text']))
                                    res_obj = ResultOfPredictor([CharResult(cell["chars"])])
                                    group.setdefault(sub_attr["name"], res_obj)
                                    if sub_attr["name"] == options[0]["name"]:  # 根据姓名提取简历
                                        resume_chars = get_resume_chars(clean_txt(cell["text"]), elt["index"])
                                        if resume_chars:
                                            # print('*****', '简历', ''.join([x['text'] for x in resume_chars]))
                                            group.setdefault("简历", ResultOfPredictor([CharResult(resume_chars)]))
                    if group:
                        res.append(group)
            if res:
                break
        return res

    def conv2para(self, ids):
        """把表格转成段落"""
        for idx in ids:
            ele_typ, elt = self.reader.find_element_by_index(idx)
            elt = deepcopy(elt)
            if ele_typ == "TABLE":
                elt.setdefault("class", "PARAGRAPH")
                elt.setdefault("chars", [])
                texts = []
                for _, cell in sorted(elt["cells"].items(), key=lambda kv: int(kv[0].replace("_", ""))):
                    texts.append(cell["text"])
                    elt["chars"].extend(cell["chars"])
                elt.setdefault("text", "".join(texts))
                elt.pop("cells")
                yield elt
            if elt.get("text") and elt.get("chars"):
                yield elt

    @staticmethod
    def fix_multi_line_para(elts):
        """多行合入同一段落"""
        new_elt = deepcopy(next(elts))
        for elt in elts:
            x_br, y_br = new_elt["chars"][-1]["box"][2:]  # 最后一个字的右下纵坐标
            pre_h = y_br - new_elt["chars"][-1]["box"][1]
            for char in elt["chars"]:
                # 行间距(1.25倍行距)小于上一行文字高度即看做同一段落
                # 公告编号可能折行, 通常不会过半页, 所以根据横坐标判断一下
                if char["box"][1] - y_br < pre_h * 1.25 or char["box"][0] * 2 < x_br:
                    new_elt["text"] += char["text"]
                    new_elt["chars"].append(char)
                else:
                    yield new_elt
                    new_elt = {
                        "chars": [
                            char,
                        ],
                        "text": char["text"],
                    }
                    # 下一段落, 重置行高
                    pre_h = char["box"][3] - char["box"][1]
                x_br, y_br = char["box"][2:]

    def change_short_name(self, attr, **kwargs):
        """
        变更证券简称公告信息抽取POC
        """
        items = []
        crude_elts = self.get_crude_elements(attr, kwargs.get("col_type", ""))
        idx_list = [elt["element_index"] for elt in crude_elts]
        elts = self.conv2para(idx_list)

        if kwargs.get("prefer") == "pdfinsight":
            idx_list = sorted(self.reader.data["_index"].keys())
            elts = self.fix_multi_line_para(self.conv2para(idx_list))
        if kwargs.get("reverse") and kwargs.get("prefer") == "pdfinsight":
            elts = self.conv2para(idx_list[::-1])

        for elt in elts:
            for reg in kwargs.get("regs", []):
                matched = reg.search(clean_txt(elt["text"]))
                if matched:
                    tkeys = sorted([tkey for tkey in matched.re.groupindex.keys() if tkey.startswith("dst")])
                    # print('===========', matched, tkeys)
                    for key in tkeys:
                        gr_idx = matched.re.groupindex[key]
                        if -1 not in matched.regs[gr_idx]:
                            sp_start, sp_end = index_in_space_string(elt["text"], matched.span(key))
                            items.append(elt["chars"][sp_start:sp_end])
                    if items:
                        break
            if items:
                break
        items = [CharResult(chars) for chars in items]
        return ResultOfPredictor(items)

    # def region_analysis(self, attr, **kwargs):
    #     """
    #     营业收入区域分析
    #     """
    #     res = []
    #     crude_elts = self.crude_answer.get('营业收入分区域分析-时间', [])
    #     unit = kwargs.get('unit')
    #
    #     for idx, crude_elt in enumerate(crude_elts):
    #         ele_typ, elt = self.reader.find_element_by_index(crude_elt['element_index'])
    #
    #         # 营业收入分区域分析占比单位 可能出现在表格或者段落中
    #         if unit and ele_typ == 'PARAGRAPH' and self.b_aim_elt(elt, kwargs):
    #             return self._simple_para('营业收入分区域分析占比单位', **kwargs)
    #         if unit and ele_typ == 'TABLE' and self.b_aim_elt(elt, kwargs):
    #             for _, cell in elt['cells'].items():
    #                 if unit in cell['text']:
    #                     return ResultOfPredictor([CharResult([i for i in cell['chars'] if i['text'] == unit])])
    #             return self._simple_tbl('营业收入分区域分析占比单位', **kwargs)
    #
    #         # 其余二级属性只会出现在表格里
    #         if ele_typ == 'TABLE' and self.b_aim_elt(elt, kwargs):
    #             row_cells, col_cells = group_cells(elt['cells'])
    #             # 取列/行索引
    #             first_row_cells, first_col_cells = self.sorted_cells(row_cells['0'], True), self.sorted_cells(
    #                 col_cells['0'])
    #
    #             # 有无大类
    #             nested = False
    #             for _, cell in list(first_col_cells.items())[1:-1]:
    #                 if re.search(r'其中|合计|共计|总计|总共', cell['text'].strip()):
    #                     nested = True
    #                     break
    #
    #             for row, row_cell in first_col_cells.items():  # 从上到下
    #                 group = {}
    #
    #                 # 跳过表头/最后合计行
    #                 if int(row) < 2 or int(row) + 1 == len(first_col_cells.items()):
    #                     continue
    #                 # 跳过子类
    #                 if nested and re.search(r'(地区|东|西|南|北|中|省|市|自治区|行政区)$', row_cell['text'].strip()):
    #                     continue
    #                 # 跳过跨页表头
    #                 if re.search(r'^(地区|区域|项目)$', row_cell['text'].strip()):
    #                     continue
    #                 # 组装地区
    #                 group.setdefault('地区', ResultOfPredictor([CharResult(row_cell['chars'])]))
    #                 _group = deepcopy(group)
    #                 for col, col_cell in first_row_cells.items():  # 从右到左
    #                     _cell = elt['cells']['{}_{}'.format(row, col)]
    #                     if int(col) == 0:  # 跳过左侧地区列
    #                         break
    #                     # 组装时间
    #                     _group.setdefault('时间', ResultOfPredictor([CharResult(col_cell['chars'])]))
    #
    #                     if col_cell['left'] != int(col):  # '占比'在右侧
    #                         _group.setdefault('占比', ResultOfPredictor([CharResult(_cell['chars'])]))
    #                     if col_cell['left'] == int(col):  # '收入'在左侧
    #                         _group.setdefault('收入', ResultOfPredictor([CharResult(_cell['chars'])]))
    #
    #                     # '收入'会比'占比'晚组装
    #                     if '收入' in _group:
    #                         res.append(_group)  # 组装一个记录
    #                         _group = deepcopy(group)  # 初始化, 继续下一个时间段
    #         if res:
    #             break
    #
    #     # 可能什么都没找到, 需要返回ResultOfPredictor对象
    #     return res if res else ResultOfPredictor([])
    #
    # def major_lawsuit(self, attr, **kwargs):
    #     """重大诉讼情况"""
    #     res = []
    #     elts = self.reader.find_sylls_by_pattern(kwargs.get('anchor_regs'))
    #     if not elts:
    #         return self._simple_para(attr, **kwargs)
    #
    #     elt = deepcopy(elts[0])
    #     value = None
    #     elts = []
    #     while elt['element'] < elt['range'][-1]:
    #         elts.append(self.reader.find_element_by_index(elt['element'])[-1])
    #         elt['element'] += 1
    #
    #     for idx, elt in enumerate(elts):
    #         if idx == 1:
    #             # 紧接着一段如果没有否定词描述, 那就是有重大诉讼情况
    #             for neg_reg in kwargs.get('neg_regs'):
    #                 if neg_reg.search(clean_txt(elt['text'])):
    #                     value = self.schema_obj.label_enum_value(attr, -1)
    #                     break
    #             else:
    #                 value = self.schema_obj.label_enum_value(attr)
    #         if elt and elt['class'] == 'PARAGRAPH':
    #             res.append(elt['chars'])
    #
    #     res = [CharResult(chars) for chars in res]
    #     return ResultOfPredictor(res, value)
