# ruff: noqa

import functools
import re
from collections import OrderedDict
from copy import deepcopy

from remarkable.common.util import clean_txt, group_cells
from remarkable.plugins.citic.predictors import index_in_space_string
from remarkable.predictor.predict import (
    AnswerPredictor,
    CharResult,
    MoldSchema,
    ParaResult,
    ResultOfPredictor,
    TblResult,
)
from remarkable.plugins.hkex.common import Schema

FIRGUE, TERM = range(2)  # 规则类型（固定数值比对、固定条款比对）
DATE_PATTERN = re.compile(r"([-\d]+)年度?([-\d]+月份?)?([-\d]+日)?")


class CsrcRule:
    def __init__(
        self, regs=None, limit=3, cnt_of_anchor_elts=3, anchor_reg=None, cnt_of_res=1, syllabus_reg=None, threshold=0.5
    ):
        self.regs = regs if regs else []  # 关键词列表
        self.limit = limit  # 关键词最少满足个数
        self.anchor_reg = anchor_reg  # 定位元素块
        self.cnt_of_anchor_elts = cnt_of_anchor_elts  # 查找个数
        self.cnt_of_res = cnt_of_res  # 预测答案个数
        self.syllabus_reg = syllabus_reg
        self.threshold = threshold


class CompleteCsrcPredictor(AnswerPredictor):
    SUB_ATTRS = {
        "合并资产负债表-报表日期": {
            "name": "报表日期",
            "regs": [
                re.compile(r"资产|项目"),
            ],
            "row": "0",
        },
    }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.schema_obj = Schema(self.mold)
        self.sorted_elements = OrderedDict()
        for idx, _ in sorted(self.reader.data["_index"].items(), key=lambda x: x[0]):
            typ, elt = self.reader.find_element_by_index(idx)
            self.sorted_elements.setdefault(idx, elt)
        self.register = {
            "No.01": [
                {
                    "attr": "招股说明书名称",
                    "func": self._process_crude,
                    "options": {
                        "regs": [
                            re.compile(r".*?公司$"),
                            re.compile(r"公开发行股票"),
                            re.compile(r"招股说明书"),
                            re.compile(r"申报稿"),
                        ],
                        "limit": 1,
                        "cnt_of_res": 4,
                    },
                },
                {
                    "attr": "释义",
                    "func": self._process_crude,
                    "options": {
                        "regs": [
                            re.compile(r"在本招股说明书中.*?除非文义另有所指.*?下列词语具有如下涵义"),
                            re.compile(r"释义|涵义"),
                            re.compile(r"^指$"),
                        ],
                        "limit": 1,
                        "cnt_of_res": 5,
                    },
                },
                {
                    "attr": "发行人-公司名称",
                    "func": self._tbl_or_paras,
                    "options": {
                        "tbl_regs": [
                            re.compile(r"^(注册)?(发行人|中文|公司)名称[:：]?"),
                            re.compile(r"^(发行人[:：]?)$"),
                        ],
                        "para_regs": [
                            re.compile(r"(发行人|中文|公司)名称[为是:：](?P<dst>.*)[，。]?"),
                        ],
                    },
                },
                {
                    "attr": "发行人-法定代表人姓名",
                    "func": self._tbl_or_paras,
                    "options": {
                        "tbl_regs": [
                            re.compile(r"法定代表人"),
                        ],
                        "para_regs": [
                            re.compile(r"(法定代表人)[为是:：](?P<dst>.*)[，。]?"),
                        ],
                    },
                },
                {
                    "attr": "发行人-统一社会信用代码",
                    "func": self._tbl_or_paras,
                    "options": {
                        "tbl_regs": [
                            re.compile(r"(统一)?(社会)?信用代码号?"),
                        ],
                        "para_regs": [
                            re.compile(r"(统一)?(社会)?信用代码号?[为是:：](?P<dst>[\da-zA-Z]+)[，。]?", re.I),
                        ],
                    },
                },
                {
                    "attr": "发行人-组织机构代码",
                    "func": self._tbl_or_paras,
                    "options": {
                        "tbl_regs": [
                            re.compile(r"组织机构代码"),
                        ],
                        "para_regs": [
                            re.compile(r"(组织|机构)代码[为是:：](?P<dst>[\da-zA-Z]+)[，。]?", re.I),
                        ],
                    },
                },
                {
                    "attr": "发行人-成立日期",
                    "func": self._tbl_or_paras,
                    "options": {
                        "tbl_regs": [
                            re.compile(r"[成建设]立日期"),
                        ],
                        "para_regs": [
                            re.compile(r"[成建设]立日期[为是:：](?P<dst>.*)[，。]?"),
                        ],
                    },
                },
                {
                    "attr": "发行人-注册资本",
                    "func": self._tbl_or_paras,
                    "options": {
                        "tbl_regs": [
                            re.compile(r"注册资本"),
                        ],
                        "para_regs": [
                            re.compile(r"注册资本[为是:：](?P<dst>.*)[，。]?"),
                        ],
                    },
                },
                {
                    "attr": "发行人-注册地址",
                    "func": self._tbl_or_paras,
                    "options": {
                        "tbl_regs": [
                            re.compile(r"^注册地址?"),
                        ],
                        "para_regs": [
                            re.compile(r"注册地址?[为是:：\s]*(?P<dst>.*)[，。]?"),
                        ],
                    },
                },
                {
                    "attr": "发行人-办公地址",
                    "func": self._tbl_or_paras,
                    "options": {
                        "tbl_regs": [
                            re.compile(r"^(公司|办公|经营|营业)?(住所|地址|场所)"),
                        ],
                        "para_regs": [
                            re.compile(r"(公司|办公|经营|营业)?(住所|地址|场所)[为是:：](?P<dst>.*)[，。]?"),
                        ],
                    },
                },
                {
                    "attr": "发行人-电话",
                    "func": self._tbl_or_paras,
                    "options": {
                        "tbl_regs": [
                            re.compile(r"电话(号码)?"),
                        ],
                        "para_regs": [
                            re.compile(r"电话(号码)?[为是:：](?P<dst>[-\d]+)[，。]?"),
                        ],
                    },
                },
                {
                    "attr": "发行人-传真号码",
                    "func": self._tbl_or_paras,
                    "options": {
                        "tbl_regs": [
                            re.compile(r"传真(号码)?"),
                        ],
                        "para_regs": [
                            re.compile(r"传真(号码)?[为是:：](?P<dst>[-\d]+)[，。]?"),
                        ],
                    },
                },
                {
                    "attr": "发行人-电子邮箱",
                    "func": self._tbl_or_paras,
                    "options": {
                        "tbl_regs": [
                            re.compile(r"电子[邮信]箱"),
                        ],
                        "para_regs": [
                            re.compile(r"电子[邮信]箱[为是:：](?P<dst>[\da-zA-Z@]+)[，。]?"),
                        ],
                    },
                },
                {
                    "attr": "发行人-邮政编码",
                    "func": self._tbl_or_paras,
                    "options": {
                        "tbl_regs": [
                            re.compile(r"邮政编码"),
                        ],
                        "para_regs": [
                            re.compile(r"邮政编码[为是:：](?P<dst>\d+)[，。]?"),
                        ],
                    },
                },
                {
                    "attr": "控股股东-法人",
                    "second": [
                        "名称",
                        "企业性质",
                        "直接持股比例",
                        "间接持股比例",
                    ],
                    "func": self._shareholder,
                    "options": {
                        "regs": [
                            re.compile(r"(?P<dst>(无|不存在)(控股股东|实际控制人))"),
                            re.compile(r"(?P<dst>\w+)(作?为|是)本公司的?(控股股东)"),
                            re.compile(r"(?P<dst>\w{3,4})持有.*?股"),
                            re.compile(r"(?P<dst>\w{3,4})[直间]接.*?为公司控股股东"),
                            re.compile(r"(控股股东|实际控制人)[为是](?P<dst>\w+)"),
                            re.compile(r"(控股股东|实际控制人)(?P<dst>\w+)成立于"),
                            re.compile(r"(?P<dst>\w+)(作?为|是)本公司的(发起人|实际控制人)"),
                        ],
                    },
                },
                # {
                #     'attr': '控股股东-自然人',
                #     'second': [
                #         '姓名',
                #         '身份证号',
                #         '国籍',
                #         '直接持股比例',
                #         '间接持股比例'
                #     ],
                #     'func': self._multi_second_rule,
                #     'options': {
                #         'regs': [
                #             re.compile(r'(无|不存在)(控股股东|实际控制人)'),
                #             re.compile(r'(?P<dst>\w+)持有公司'),
                #             re.compile(r'持有公司(?P<dst>[\d\.\s]*%)的?股份'),
                #         ],
                #     },
                # },
                {
                    "attr": "控股股东-自然人",
                    "func": self.shareholder_person,
                },
                {
                    "attr": "控股股东-其他",
                    "second": ["姓名", "性质", "直接持股比例", "间接持股比例"],
                    "func": self._shareholder,
                    "options": {
                        "regs": [
                            re.compile(r"(无|不存在)(控股股东|实际控制人)"),
                            re.compile(r"(?P<dst>\w+)(作?为|是)本?公司的?(发起人|实际控制人)"),
                            re.compile(r"实际控制人为(?P<dst>\w+)"),
                        ],
                    },
                },
                {
                    "attr": "实际控制人-国有控股主体",
                    "second": ["名称", "单位负责人", "直接持股比例", "间接持股比例"],
                    "func": self._shareholder,
                    "options": {
                        "regs": [
                            re.compile(r"(?P<dst>(无|不存在)(控股股东|实际控制人))"),
                            re.compile(r"(?P<dst>\w+)(作?为|是)本公司的(发起人|实际控制人)"),
                            re.compile(r"(?P<dst>\w+)通过其控股子公司"),
                            re.compile(r"(?P<dst>\w+)持有.*?股权"),
                            re.compile(r"实际控制人为?(?P<dst>\w+(国资委|研究所|政府))"),
                            re.compile(r"(?P<dst>\w+(国资委)?).*?[为是系].*?实际控制人"),
                            re.compile(r"(?P<dst>\w+局).*?[为是系].*?实际控制人"),
                        ],
                    },
                },
                {
                    "attr": "实际控制人-自然人",
                    "second": ["姓名", "身份证号", "国籍", "直接持股比例", "间接持股比例"],
                    "func": self._natural_person,
                    "options": {
                        "regs": [
                            re.compile(r"(?P<dst>(无|不存在)(控股股东|实际控制人))"),
                            re.compile(
                                r"(依照|；|，)(?P<dst>\w{2,3})[、和与]?(?P<dst1>\w{2,3})?.*?[为是系].*?(控股股东|实际控制人)"
                            ),
                            re.compile(r"(?P<dst>\w{2,3})直接持有.*?[为是系].*?(控股股东|实际控制人)"),
                            re.compile(
                                r"(?P<dst>\w{2,3})[、和与]?(?P<dst1>\w{2,3})?.*?[为是系].*?(控股股东|实际控制人)"
                            ),
                            re.compile(r"(?P<dst>\w{2,4})(作?为|是)本公司的?(控股股东)"),
                            re.compile(r"(?P<dst>\w+).*?为公司的共同控股股东"),
                            re.compile(r"(?P<dst>\w{2,4})(先生|女士)?(间接|直接)?.*?股[份权]"),
                            re.compile(r"(实际控制人|控股股东)[为是](?P<dst>\w+)、?(?P<dst1>\w{2,3})?"),
                            re.compile(r"(?P<dst>\w{2,3})(先生|女士)?[为是]?.*?(实际控制人|控股股东)"),
                            re.compile(r"(实际控制人|控股股东)[为是](?P<dst>\w{2,4})和(?P<dst1>\w{2,4})"),
                            re.compile(r"(?P<dst>\w+)(间接|直接).*?控制公司"),
                            re.compile(r"(?P<dst>\w{2,4})和(?P<dst1>\w{2,4}).*?分别直接持有公司.*?股"),
                            re.compile(r"(?P<dst>\w{2,4})(先生|女士)"),
                            re.compile(r"(?P<dst>\w+)持有.*?股[份权].*?实际控制人"),
                            re.compile(r"实际控制人[为是](?P<dst>\w{2,4})(先生|女士)"),
                        ],
                    },
                },
                {
                    "attr": "实际控制人-其他",
                    "second": ["名称", "性质", "直接持股比例", "间接持股比例", "其中：质押股份数量"],
                    "func": self._shareholder,
                    "options": {
                        "regs": [
                            re.compile(r"(无|不存在)(控股股东|实际控制人)"),
                            re.compile(r"(?P<dst>.+)持有公司"),
                            re.compile(r"持有公司(?P<dst>.+)股份"),
                            re.compile(r"(?P<dst>\w+).*?为公司(控股股东|实际控制人)"),
                        ],
                    },
                },
                # {
                #     'attr': '董事基本情况',
                #     'second': [
                #         "姓名",
                #         "国籍",
                #         "境外居留权",
                #         "性别",
                #         "出生年月",
                #         "学历",
                #         "职称",
                #         "现任职务",
                #         "起始日期",
                #         "终止日期",
                #         "是否已有简历"
                #     ],
                #     'func': self._multi_paras,
                #     'options': {
                #         'regs': [
                #             re.compile(r'[一二三四五六七八九十]*董事会成员'),
                #             re.compile(r'[一二三四五六七八九十]*监事会成员'),
                #             re.compile(r'[一二三四五六七八九十]*监事会成员'),
                #         ],
                #     },
                # },
                {"attr": "董事基本情况", "func": self.directors},
                # {
                #     'attr': '监事基本情况',
                #     'second': [
                #         "姓名",
                #         "国籍",
                #         "境外居留权",
                #         "性别",
                #         "出生年月",
                #         "学历",
                #         "职称",
                #         "现任职务",
                #         "起始日期",
                #         "终止日期",
                #         "是否已有简历"
                #     ],
                #     'func': self._multi_paras,
                #     'options': {
                #         'regs': [
                #             re.compile(r'[一二三四五六七八九十]*监事会成员'),
                #             re.compile(r'[一二三四五六七八九十]*高级管理人员'),
                #             re.compile(r'[一二三四五六七八九十]*高级管理人员'),
                #         ],
                #     },
                # },
                {"attr": "监事基本情况", "func": self.supervisors},
                {
                    "attr": "高管基本情况",
                    "second": [
                        "姓名",
                        "国籍",
                        "境外居留权",
                        "性别",
                        "出生年月",
                        "学历",
                        "职称",
                        "现任职务",
                        "起始日期",
                        "终止日期",
                        "是否已有简历",
                    ],
                    "func": self._multi_paras,
                    "options": {
                        "regs": [
                            re.compile(r"[一二三四五六七八九十]*高级管理人员$"),
                            re.compile(r"[一二三四五六七八九十]*(其他)?核心.*?人员$"),
                            re.compile(r"[一二三四五六七八九十]*(其他)?核心.*?人员$"),
                        ],
                    },
                },
                # {
                #     'attr': '核心技术人员基本情况',
                #     'second': [
                #         "姓名",
                #         "国籍",
                #         "境外居留权",
                #         "性别",
                #         "出生年月",
                #         "学历",
                #         "职称",
                #         "现任职务",
                #         "起始日期",
                #         "终止日期",
                #         "是否已有简历"
                #     ],
                #     'func': self._multi_paras,
                #     'options': {
                #         'regs': [
                #             re.compile(r'[一二三四五六七八九十]*(其他)?核心.*?人员$'),
                #             re.compile(r'[一二三四五六七八九十]*[董监]事.*?情况$'),
                #             re.compile(r'[一二三四五六七八九十]*[董监]事.*?情况$'),
                #         ],
                #     },
                # },
                {"attr": "核心技术人员基本情况", "func": self.main_tech_person},
                {
                    "attr": "合并资产负债表-报表日期",
                    "func": self._row_group_in_tbl,
                    "options": {
                        "regs": [
                            re.compile(r"资产|项目"),
                        ],
                        "row": "0",
                    },
                },
                {
                    "attr": "合并资产负债表-货币单位",
                    "func": self._get_unit_from_tbl,
                    "options": {
                        "regs": [re.compile(r"单位[:：](?P<dst>\w+)"), re.compile(r"[万美]?元")],
                        "para_regs": [
                            re.compile(r"单位[:：](?P<dst>\w+)"),
                        ],
                        "row": "1",
                    },
                },
                {
                    "attr": "合并资产负债表",
                    "func": self._combine_fin_tbl,
                    "options": {
                        "anchor_regs": [
                            re.compile(r"(合并)?资产负债表"),
                        ],
                        "anchor_range": (-1, 5),
                    },
                },
                {
                    "attr": "合并利润表-报表日期",
                    "func": self._row_group_in_tbl,
                    "options": {
                        "regs": [
                            re.compile(r"资产|项目"),
                        ],
                        "row": "0",
                    },
                },
                {
                    "attr": "合并利润表-货币单位",
                    "func": self._get_unit_from_tbl,
                    "options": {
                        "regs": [re.compile(r"单位[:：](?P<dst>\w+)"), re.compile(r"[万美]?元")],
                        "para_regs": [
                            re.compile(r"单位[:：](?P<dst>\w+)"),
                        ],
                        "row": "1",
                    },
                },
                {
                    "attr": "合并利润表",
                    "func": self._combine_fin_tbl,
                    "options": {
                        "anchor_regs": [
                            re.compile(r"(合并)?利润表"),
                        ],
                        "anchor_range": (-1, 5),
                    },
                },
                {
                    "attr": "合并现金流量表-报表日期",
                    "func": self._row_group_in_tbl,
                    "options": {
                        "regs": [
                            re.compile(r"资产|项目"),
                        ],
                        "row": "0",
                    },
                },
                {
                    "attr": "合并现金流量表-货币单位",
                    "func": self._get_unit_from_tbl,
                    "options": {
                        "regs": [re.compile(r"单位[:：](?P<dst>\w+)"), re.compile(r"[万美]?元")],
                        "para_regs": [
                            re.compile(r"单位[:：](?P<dst>\w+)"),
                        ],
                        "row": "1",
                    },
                },
                {
                    "attr": "合并现金流量表",
                    "func": self._combine_fin_tbl,
                    "options": {
                        "anchor_regs": [
                            re.compile(r"(合并)?现金流量表"),
                        ],
                        "anchor_range": (-1, 5),
                    },
                },
                {
                    "attr": "主要财务指标",
                    "second": [
                        "报表日期",
                        "流动比率(倍)(T-2年)",
                        "流动比率(倍)(T-1年)",
                        "流动比率(倍)(T年)",
                        "流动比率(倍)(最近一期）",
                        "速动比率(倍)(T-2年)",
                        "速动比率(倍)(T-1年)",
                        "速动比率(倍)(T年)",
                        "速动比率(倍)(最近一期）",
                        "资产负债率（合并）(T-2年)",
                        "资产负债率（合并）(T-1年)",
                        "资产负债率（合并）(T年)",
                        "资产负债率（合并）(最近一期）",
                        "资产负债率(母公司）(T-2年)",
                        "资产负债率(母公司）(T-1年)",
                        "资产负债率(母公司）(T年)",
                        "资产负债率(母公司）(最近一期）",
                        "无形资产（扣除土地使用权、水面养殖权和采矿权等后）占净资产的比例（%）(T-2年)",
                        "无形资产（扣除土地使用权、水面养殖权和采矿权等后）占净资产的比例（%）(T-1年)",
                        "无形资产（扣除土地使用权、水面养殖权和采矿权等后）占净资产的比例（%）(T年)",
                        "无形资产（扣除土地使用权、水面养殖权和采矿权等后）占净资产的比例（%）(最近一期）",
                        "应收账款周转率(次/年)(T-2年)",
                        "应收账款周转率(次/年)(T-1年)",
                        "应收账款周转率(次/年)(T年)",
                        "应收账款周转率(次/年)(最近一期）",
                        "存货周转率(次/年)(T-2年)",
                        "存货周转率(次/年)(T-1年)",
                        "存货周转率(次/年)(T年)",
                        "存货周转率(次/年)(最近一期）",
                        "总资产周转率(次/年)(T-2年)",
                        "总资产周转率(次/年)(T-1年)",
                        "总资产周转率(次/年)(T年)",
                        "总资产周转率(次/年)(最近一期）",
                        "息税折旧摊销前利润-单位",
                        "息税折旧摊销前利润(元)(T-2年)",
                        "息税折旧摊销前利润(元)(T-1年)",
                        "息税折旧摊销前利润(元)(T年)",
                        "息税折旧摊销前利润(元)(最近一期）",
                        "利息保障倍数(倍)(T-2年)",
                        "利息保障倍数(倍)(T-1年)",
                        "利息保障倍数(倍)(T年)",
                        "利息保障倍数(倍)(最近一期）",
                        "扣除非经常性损益后的每股基本收益-单位",
                        "扣除非经常性损益后的每股基本收益（元）(T-2年)",
                        "扣除非经常性损益后的每股基本收益（元）(T-1年)",
                        "扣除非经常性损益后的每股基本收益（元）(T年)",
                        "扣除非经常性损益后的每股基本收益（元）(最近一期）",
                        "每股经营活动产生的现金流量-单位",
                        "每股经营活动产生的现金流量(元)(T-2年)",
                        "每股经营活动产生的现金流量(元)(T-1年)",
                        "每股经营活动产生的现金流量(元)(T年)",
                        "每股经营活动产生的现金流量(元)(最近一期）",
                        "每股净现金流量-单位",
                        "每股净现金流量(元)(T-2年)",
                        "每股净现金流量(元)(T-1年)",
                        "每股净现金流量(元)(T年)",
                        "每股净现金流量(元)(最近一期）",
                        "加权平均净资产收益率(T-2年)",
                        "加权平均净资产收益率(T-1年)",
                        "加权平均净资产收益率(T年)",
                        "加权平均净资产收益率(最近一期）",
                    ],
                    "func": self._multi_paras,
                    "options": {
                        "regs": [
                            re.compile(r"(主要|基本)财务指标$"),
                            re.compile(r"净资产收益率"),
                            re.compile(r"盈利预测|主要财务指标|主要资产"),
                        ],
                    },
                },
                {
                    "attr": "重大诉讼事项",
                    "second": [
                        "有/无重大诉讼事项",
                        "事项",
                        "起诉(申请)方",
                        "应诉(被申请)方",
                        "承担连带责任方",
                        "诉讼仲裁类型",
                        "诉讼涉及金额",
                        "预计负债金额",
                    ],
                    "func": self._multi_paras,
                    "options": {
                        "regs": [
                            re.compile(r"(重大)?诉讼或仲裁事项$"),
                            re.compile(r".*?声明$"),
                            re.compile(r".*?声明$"),
                        ],
                    },
                },
                {
                    "attr": "募集资金与运用",
                    "second": ["货币单位", "项目名称", "投资总额", "募集资金投资额", "募集资金投向"],
                    "func": self._multi_paras,
                    "options": {
                        "regs": [
                            re.compile(r"募集资金拟?投资项目$"),
                            re.compile(r"合计"),
                            re.compile(r"合计"),
                        ],
                    },
                },
                {
                    "attr": "专利",
                    "second": [
                        "专利类型",
                        "专利名称",
                        "专利号",
                        "专利权人",
                        "取得成本",
                        "最近一期末账面价值",
                        "取得日期",
                        "使用期限",
                        "是否存在权属纠纷",
                    ],
                    "func": self._whole_table_for_second_rule,
                    "options": {
                        "anchor_regs": [
                            re.compile(r"专利"),
                        ],
                        "limit": 1,
                        "cnt_of_res": 1,
                    },
                },
                # {
                #     'attr': '主要客户',
                #     'second': [
                #         "时间",
                #         "货币单位",
                #         "客户名称",
                #         "下属单位名称",
                #         "销售额",
                #         "占主营收入比例",
                #         "占营业收入比例"
                #     ],
                #     'func': self._whole_table_for_second_rule,
                #     'options': {
                #         'anchor_regs': [
                #             re.compile(r'前[十五][大名]客户'),
                #         ],
                #         'limit': 1,
                #         'cnt_of_res': 1,
                #     }
                # },
                {"attr": "主要客户", "func": self.main_customer},
                # {
                #     'attr': '主要供应商',
                #     'second': [
                #         "时间",
                #         "货币单位",
                #         "供应商名称",
                #         "采购内容",
                #         "采购额",
                #         "占总采购金额比例"
                #     ],
                #     'func': self._whole_table_for_second_rule,
                #     'options': {
                #         'anchor_regs': [
                #             re.compile(r'前[十五][大名]供应商'),
                #         ],
                #         'limit': 1,
                #         'cnt_of_res': 1,
                #     }
                # },
                {"attr": "主要供应商", "func": self.main_supplier},
                {
                    "attr": "重大合同",
                    "second": [
                        "货币单位",
                        "合同类型",
                        "合同对手方名称",
                        "标的",
                        "合同金额",
                        "需要计算的合同金额",
                        "已履行金额",
                        "履行期限",
                        "备注",
                    ],
                    "func": self._important_contract,
                    "options": {
                        "regs": [
                            re.compile(r"(单位[:：])?(?P<dst>[万美]?元)"),
                            re.compile(r"(销售|采购|施工|融资)合同"),
                        ],
                    },
                },
                # {
                #     'attr': '发行人所处行业',
                #     'second': [
                #         "行业分类标准",
                #         "行业分类代码",
                #         "行业分类名称"
                #     ],
                #     'func': self._multi_second_rule,
                #     'options': {
                #         'regs': [
                #             re.compile(r'根据.*?(?P<dst>《.*?》（[\d\w]+）)'),
                #             re.compile(r'(公司|发行人)属于(?P<dst>\w+)'),
                #             re.compile(r'产品代码[:：](?P<dst>\d+)'),
                #         ],
                #     },
                # },
                {
                    "attr": "发行人所处行业",
                    "func": self.issuer_industry,
                },
                {
                    "attr": "盈利能力-收入-产品构成-报表日期",
                    "func": self._row_group_in_tbl,
                    "options": {
                        "regs": [
                            re.compile(r"项目|行业|(主要)?产品(名称|种类)?|业务类型|类别"),
                        ],
                        "row": "0",
                    },
                },
                {
                    "attr": "盈利能力-收入-产品构成-货币单位",
                    "func": self._get_unit_from_tbl,
                    "options": {
                        "regs": [re.compile(r"单位[:：](?P<dst>\w+)"), re.compile(r"[万美]?元")],
                        "para_regs": [
                            re.compile(r"单位[:：](?P<dst>\w+)"),
                        ],
                        "row": "1",
                    },
                },
                {
                    "attr": "盈利能力-收入-产品构成",
                    "second": [
                        "产品类别",
                        "金额(T-2年)",
                        "金额(T-1年)",
                        "金额(T年)",
                        "金额(最近一期）",
                        "占比(T-2年)",
                        "占比(T-1年)",
                        "占比(T年)",
                        "占比(最近一期）",
                        "变动比例(T-2年)",
                        "变动比例(T-1年)",
                        "变动比例(T年)",
                        "变动比例(最近一期）",
                    ],
                    "func": self._whole_table_for_second_rule,
                    "options": {
                        "anchor_regs": [
                            re.compile(r"主营业务收入(按照|分)?产品"),
                        ],
                        "anchor_range": (-2, 3),
                        "limit": 1,
                        "cnt_of_res": 1,
                    },
                },
                {
                    "attr": "盈利能力-收入-业务构成-报表日期",
                    "func": self._row_group_in_tbl,
                    "options": {
                        "regs": [
                            re.compile(r"项目|行业|(主要)?产品(名称|种类)?|业务类型|类别"),
                        ],
                        "row": "0",
                    },
                },
                {
                    "attr": "盈利能力-收入-业务构成-货币单位",
                    "func": self._get_unit_from_tbl,
                    "options": {
                        "regs": [re.compile(r"单位[:：](?P<dst>\w+)"), re.compile(r"[万美]?元")],
                        "para_regs": [
                            re.compile(r"单位[:：](?P<dst>\w+)"),
                        ],
                        "row": "1",
                    },
                },
                {
                    "attr": "盈利能力-收入-业务构成",
                    "second": [
                        "业务类别",
                        "金额(T-2年)",
                        "金额(T-1年)",
                        "金额(T年)",
                        "金额(最近一期）",
                        "占比(T-2年)",
                        "占比(T-1年)",
                        "占比(T年)",
                        "占比(最近一期）",
                        "变动比例(T-2年)",
                        "变动比例(T-1年)",
                        "变动比例(T年)",
                        "变动比例(最近一期）",
                    ],
                    "func": self._whole_table_for_second_rule,
                    "options": {
                        "anchor_regs": [
                            re.compile(r"主营业务收入[按分]业务"),
                        ],
                        "anchor_range": (-2, 3),
                        "limit": 1,
                        "cnt_of_res": 1,
                    },
                },
                {
                    "attr": "盈利能力-成本-产品构成-报表日期",
                    "func": self._row_group_in_tbl,
                    "options": {
                        "regs": [
                            re.compile(r"项目|行业|(主要)?产品(名称|种类)?|业务类型|类别"),
                        ],
                        "row": "0",
                    },
                },
                {
                    "attr": "盈利能力-成本-产品构成-货币单位",
                    "func": self._get_unit_from_tbl,
                    "options": {
                        "regs": [re.compile(r"单位[:：](?P<dst>\w+)"), re.compile(r"[万美]?元")],
                        "para_regs": [
                            re.compile(r"单位[:：](?P<dst>\w+)"),
                        ],
                        "row": "1",
                    },
                },
                {
                    "attr": "盈利能力-成本-产品构成",
                    "second": [
                        "产品类别",
                        "金额(T-2年)",
                        "金额(T-1年)",
                        "金额(T年)",
                        "金额(最近一期）",
                        "占比(T-2年)",
                        "占比(T-1年)",
                        "占比(T年)",
                        "占比(最近一期）",
                        "变动比例(T-2年)",
                        "变动比例(T-1年)",
                        "变动比例(T年)",
                        "变动比例(最近一期）",
                    ],
                    "func": self._whole_table_for_second_rule,
                    "options": {
                        "anchor_regs": [
                            re.compile(r"主营业务成本(按照)?(产品)?(构成)?"),
                        ],
                        "anchor_range": (-2, 3),
                        "limit": 1,
                        "cnt_of_res": 1,
                    },
                },
                {
                    "attr": "盈利能力-成本-业务构成-报表日期",
                    "func": self._row_group_in_tbl,
                    "options": {
                        "regs": [
                            re.compile(r"项目|行业|(主要)?产品(名称|种类)?|业务类型|类别"),
                        ],
                        "row": "0",
                    },
                },
                {
                    "attr": "盈利能力-成本-业务构成-货币单位",
                    "func": self._get_unit_from_tbl,
                    "options": {
                        "regs": [re.compile(r"单位[:：](?P<dst>\w+)"), re.compile(r"[万美]?元")],
                        "para_regs": [
                            re.compile(r"单位[:：](?P<dst>\w+)"),
                        ],
                        "row": "1",
                    },
                },
                {
                    "attr": "盈利能力-成本-业务构成",
                    "second": [
                        "业务类别",
                        "金额(T-2年)",
                        "金额(T-1年)",
                        "金额(T年)",
                        "金额(最近一期）",
                        "占比(T-2年)",
                        "占比(T-1年)",
                        "占比(T年)",
                        "占比(最近一期）",
                        "变动比例(T-2年)",
                        "变动比例(T-1年)",
                        "变动比例(T年)",
                        "变动比例(最近一期）",
                    ],
                    "func": self._whole_table_for_second_rule,
                    "options": {
                        "anchor_regs": [
                            re.compile(r"(主营业务|公司营业)成本构成"),
                        ],
                        "anchor_range": (-2, 3),
                        "limit": 1,
                        "cnt_of_res": 1,
                    },
                },
            ],
        }

        for item in self.register[self.root_schema_name]:
            # if item['attr'] not in ['实际控制人-自然人']:
            #     continue
            if item.get("second"):
                self.column_analyzers.update(
                    {
                        item["attr"]: functools.partial(
                            item["func"], item["attr"], item["second"], **item.get("options", {})
                        ),
                    }
                )
            else:
                self.column_analyzers.update(
                    {
                        item["attr"]: functools.partial(item["func"], item["attr"], **item.get("options", {})),
                    }
                )

    def _whole_table(self, attr, **kwargs):
        items = []
        crude_elts = self.get_crude_elements(attr, kwargs.get("col_type", ""))
        for idx, crude_elt in enumerate(crude_elts):
            ele_typ, elt = self.reader.find_element_by_index(crude_elt["element_index"])
            if ele_typ == "TABLE" and self.is_aim_elt(elt, kwargs):
                elt_syllabus_id = elt.get("syllabus", None)
                if elt_syllabus_id > 0:
                    syllabus_title = self.reader.syllabus_dict[elt_syllabus_id]["title"]
                    title_reg = kwargs.get("anchor_regs", None)
                    if title_reg and any((reg.search(syllabus_title) for reg in title_reg)):
                        items.append(TblResult([], elt))
                if items:
                    break
        return ResultOfPredictor(items)

    def _combine_fin_tbl(self, attr, **kwargs):
        """
        提取整个表格（合并xx表）
        """
        items = []
        crude_elts = self.get_crude_elements(attr, kwargs.get("col_type", ""))
        for idx, crude_elt in enumerate(crude_elts):
            ele_typ, elt = self.reader.find_element_by_index(crude_elt["element_index"])
            # print('--------', idx, ele_typ, elt['page'], self.is_aim_elt(elt, kwargs))
            if ele_typ == "TABLE" and self.is_aim_elt(elt, kwargs):
                items.append(TblResult([], elt))
        return ResultOfPredictor(items)

    def _search_table_from_eles(self, attr, **kwargs):
        items = []
        for elt_idx, elt in self.sorted_elements.items():
            ele_typ = elt["class"]
            if ele_typ == "TABLE" and self.is_aim_elt(elt, kwargs):
                elt_syllabus_id = elt.get("syllabus", None)
                if elt_syllabus_id > 0:
                    syllabus_title = self.reader.syllabus_dict[elt_syllabus_id]["title"]
                    title_reg = kwargs.get("anchor_regs", None)
                    if title_reg and any((reg.search(syllabus_title) for reg in title_reg)):
                        items.append(TblResult([], elt))
                if items:
                    break
        return ResultOfPredictor(items)

    def _whole_table_for_second_rule(self, attr, second_cols, **kwargs):
        item = ResultOfPredictor([], None)
        for second_col in second_cols:
            _item = self._whole_table(second_col, **kwargs)
            if _item.data:
                item = _item
                break
        return [{second_cols[0]: item}]

    def _process_crude(self, attr, **kwargs):
        items = []
        crude_elts = self.get_crude_elements(attr, kwargs.get("col_type", ""))
        for answer in crude_elts[:10]:
            element_index = answer["element_index"]
            elt = self.sorted_elements[element_index]
            if elt["class"] == "PARAGRAPH":
                self.fix_continued_para(elt)
                elt_text = clean_txt(elt["text"])
                cnt = 0
                for reg in kwargs.get("regs"):
                    if reg.search(elt_text):
                        cnt += 1
                if cnt >= kwargs.get("limit"):
                    self.append_item_crude(elt, items)
                if len(items) >= kwargs.get("cnt_of_res"):
                    break
            elif elt["class"] == "TABLE":
                cells = elt["cells"]
                cnt = 0  # 关键词的命中次数
                for index, cell in cells.items():
                    cell_text = clean_txt(cell["text"])
                    for reg in kwargs.get("regs"):
                        if reg.search(cell_text):
                            cnt += 1
                    if cnt >= kwargs.get("limit"):
                        self.append_item_crude(elt, items)
                        break
                if len(items) >= kwargs.get("cnt_of_res"):
                    break
        items = sorted(items, key=lambda _elt: (_elt["page"], _elt["outline"][1]))
        data = [TblResult([], item) if item["class"] == "TABLE" else CharResult(item["chars"]) for item in items]
        return ResultOfPredictor(data)

    @staticmethod
    def append_item_crude(elt, items):
        if elt["class"] == "TABLE":
            items.append(elt)
        else:
            chars = elt.get("chars", [])
            if chars and not any(
                all(char in item["chars"] for char in chars) for item in items if item["class"] == "PARAGRAPH"
            ):
                items.append(elt)

    def append_item(self, chars, items):
        if chars and not any(all(char in item for char in chars) for item in items):
            items.append(chars)

    def get_crude_elements(self, attr, col_type):
        if col_type and col_type not in MoldSchema.basic_types + self.schema_obj.enum_types:
            attr = "-".join([col_type, attr])
        return self.crude_answer.get(attr, [])

    def fix_continued_para(self, elt):
        """
        拼接跨页段落
        """
        elt = deepcopy(elt)

        prev_elts = self.reader.find_elements_near_by(elt["index"], step=-1, amount=1)
        if prev_elts and prev_elts[0] and prev_elts[0]["class"] == "PARAGRAPH" and prev_elts[0]["continued"]:
            elt["text"] = prev_elts[0]["text"] + elt["text"]
            elt["chars"] = prev_elts[0]["chars"] + elt["chars"]

        if elt["continued"]:
            next_elts = self.reader.find_elements_near_by(elt["index"], step=1, amount=3)
            for next_elt in next_elts:
                if next_elt["class"] == "PARAGRAPH":
                    elt["text"] += next_elt["text"]
                    elt["chars"] += next_elt["chars"]
                    break
        return elt

    def _get_char_from_elts(self, attr, **kwargs):
        items = []
        for elt_idx, elt in self.sorted_elements.items():
            if self.is_aim_elt(elt, kwargs):
                if elt["class"] == "PARAGRAPH":
                    elt = self.fix_continued_para(elt)
                    elt_text = clean_txt(elt["text"])
                    cnt = 0  # 关键词的命中次数
                    for reg in kwargs.get("regs"):
                        if reg.search(elt_text):
                            cnt += 1
                    if cnt >= kwargs.get("limit"):
                        self.append_item_crude(elt, items)
                    if len(items) >= kwargs.get("cnt_of_res"):
                        break
                elif elt["class"] == "TABLE":
                    cells = elt["cells"]
                    cnt = 0  # 关键词的命中次数
                    for index, cell in cells.items():
                        cell_text = clean_txt(cell["text"])
                        for reg in kwargs.get("regs"):
                            if reg.search(cell_text):
                                cnt += 1
                        if cnt >= kwargs.get("limit"):
                            self.append_item_crude(elt, items)
                            break
                    if len(items) >= kwargs.get("cnt_of_res"):
                        break
        items = sorted(items, key=lambda _elt: (_elt["page"], _elt["outline"][1]))
        data = [CharResult(item["chars"]) if item["class"] == "PARAGRAPH" else TblResult([], item) for item in items]
        return ResultOfPredictor(data)

    def _tbl_or_paras(self, attr, **kwargs):
        res = self._simple_tbl(attr, **kwargs)
        if res.data:
            return res
        return self._simple_para(attr, **kwargs)

    def _simple_tbl(self, attr, **kwargs):
        """
        处理关键词同cell或下一个cell为结果的情况
            1. 关键词下一个cell为结果，比如：发行人名称|a公司
            2. 同cell, 比如: "持股数量（万股）"中"持股数量"为关键词, "万股"为期望结果, 正则可写为r'持股数量(.*?股)?'
        """
        items = []
        crude_elts = self.get_crude_elements(attr, kwargs.get("col_type", ""))
        regs = kwargs.get("regs", []) + kwargs.get("tbl_regs", [])
        for idx, crude_elt in enumerate(crude_elts):
            ele_typ, elt = self.reader.find_element_by_index(crude_elt["element_index"])
            # print('--------', idx, ele_typ, elt['page'])
            flag = False
            if ele_typ == "TABLE" and self.is_aim_elt(elt, kwargs):
                cells = self.cell_ordering(elt)
                for cell_idx, cell in cells.items():
                    # print('=========', cell_idx, clean_txt(cell['text']))
                    chars = []
                    if not flag:
                        for reg in regs:
                            matched = reg.search(clean_txt(cell["text"]))
                            if matched:
                                tkeys = sorted(
                                    [tkey for tkey in matched.re.groupindex.keys() if tkey.startswith("dst")]
                                )
                                if not tkeys:  # 提取下个cell
                                    flag = True
                                    break
                                for key in tkeys:  # 锚定词与关键字在同一单元格，分组命名为dst
                                    gr_idx = matched.re.groupindex[key]
                                    if -1 not in matched.regs[gr_idx]:
                                        sp_start, sp_end = index_in_space_string(cell["text"], matched.span(key))
                                        chars.extend(cell["chars"][sp_start:sp_end])
                                # print('*****', [x['text'] for x in chars])
                                items.append(chars)
                                # 匹配到一次即返回, 不再处理剩余正则
                                if kwargs.get("oneshot"):
                                    break
                        if flag:
                            continue
                    if flag and not cell.get("dummy"):
                        # print('*****', [x['text'] for x in cell['chars']])
                        items.append(cell["chars"])
                        flag = False
                    # 匹配到一次即返回, 不再处理剩余单元格
                    if kwargs.get("oneshot") and items:
                        break
            if any(items):
                break
        items = [CharResult(chars) for chars in items]
        return ResultOfPredictor(items)

    def _simple_para(self, attr, **kwargs):
        """
        按句式提取段落的一部分作为结果
        如果提供了否定判断的正则`neg_regs`, 即枚举类型, 会在value放置对应规则的枚举值
        """
        items = []
        value = None
        crude_elts = self.get_crude_elements(attr, kwargs.get("col_type", ""))
        regs = kwargs.get("regs", []) + kwargs.get("para_regs", [])
        for idx, elt in enumerate(crude_elts):
            ele_typ, elt = self.reader.find_element_by_index(elt["element_index"])
            if ele_typ == "PARAGRAPH" and self.is_aim_elt(elt, kwargs):
                elt = self.fix_continued_para(elt)  # 修复跨页段落
                # print('----------' * 3, idx, elt['page'], elt['text'], )
                for reg in regs:
                    matched = reg.search(clean_txt(elt["text"]))
                    if matched:
                        tkeys = sorted([tkey for tkey in matched.re.groupindex.keys() if tkey.startswith("dst")])
                        # print('===========', matched, tkeys)
                        chars = []
                        for key in tkeys:
                            gr_idx = matched.re.groupindex[key]
                            if -1 not in matched.regs[gr_idx]:
                                sp_start, sp_end = index_in_space_string(elt["text"], matched.span(key))
                                chars.extend(elt["chars"][sp_start:sp_end])
                        # print('*******', [x['text'] for x in chars])
                        if kwargs.get("neg_regs") and tkeys:
                            # 否定判断, "非负即正"
                            for neg_reg in kwargs.get("neg_regs"):
                                if neg_reg.search(clean_txt(elt["text"])):
                                    value = self.schema_obj.label_enum_value(attr, -1)
                                    break
                            else:
                                value = self.schema_obj.label_enum_value(attr)
                        if chars:
                            items.append(chars)
                        if kwargs.get("oneshot"):
                            break
            if any(items):
                break
        items = [CharResult(chars) for chars in items]
        return ResultOfPredictor(items, value)

    def is_aim_elt(self, elt, options):
        # 上方必须出现某些关键词
        anchor_regs = options.get("anchor_regs", [])
        if anchor_regs:
            anchor_range = options.get("anchor_range", (-1, 3))
            prev_elts = self.reader.find_elements_near_by(
                elt["index"], step=anchor_range[0], amount=anchor_range[1], include=True
            )
            flag = False
            for prev_elt in prev_elts:
                if prev_elt["class"] == "PARAGRAPH":
                    if any(reg.search(clean_txt(prev_elt.get("text", ""))) for reg in anchor_regs):
                        # print('~~~~', clean_txt(prev_elt.get('text', '')))
                        flag = True
                        break
            if not flag:
                return False
        if not options.get("regs"):
            return True
        if elt["class"] == "TABLE":
            for cell_idx, cell in elt.get("cells", {}).items():
                if any(reg.search(clean_txt(cell["text"])) for reg in options.get("regs", [])):
                    return True
        if elt["class"] == "PARAGRAPH":
            if any(reg.search(clean_txt(elt["text"])) for reg in options.get("regs", [])):
                return True
        return False

    def cell_ordering(self, tbl):
        def weight(row_and_col):
            row, col = row_and_col.split("_")
            return int(row) * 10000 + int(col)

        cells = OrderedDict()
        for k, v in sorted(tbl.get("cells").items(), key=lambda x: weight(x[0])):
            cells.setdefault(k, v)
        return cells

    def _multi_second_rule(self, attr, second_cols, **kwargs):
        # attrs = ['-'.join([attr, second_col]) for second_col in second_cols]
        item = ResultOfPredictor([], None)
        for second_col in second_cols:
            _item = self._simple_para(second_col, **kwargs)
            if _item.data:
                item = _item
                break
        return [{second_cols[0]: item}]

    def _shareholder(self, attr, second_cols, **kwargs):
        item = ResultOfPredictor([], None)
        second_col = second_cols[0]
        _item = self._tbl_or_paras(second_col, **kwargs)
        if _item.data:
            item = _item
        return [{second_col: item}]

    def _natural_person(self, attr, second_cols, **kwargs):
        item = ResultOfPredictor([], None)
        second_col = second_cols[0]
        _item = self._simple_para(second_col, **kwargs)
        if _item.data:
            item = _item
        return [{second_col: item}]

    def _row_group_in_tbl(self, attr, **kwargs):
        items = []
        regs = kwargs.get("regs")
        accurate_regs = kwargs.get("accurate_regs")
        select_row = kwargs.get("row")
        crude_elts = self.get_crude_elements(attr, kwargs.get("col_type", ""))
        for idx, crude_elt in enumerate(crude_elts):
            ele_typ, elt = self.reader.find_element_by_index(crude_elt["element_index"])
            if ele_typ == "TABLE" and self.is_aim_elt(elt, {"regs": regs}):
                cells_by_row, cells_by_col = group_cells(elt["cells"])
                items = []
                for sub_idx, cell in cells_by_row[select_row].items():
                    if any((reg.search(clean_txt(cell["text"])) for reg in regs)):
                        continue
                    if not accurate_regs:
                        items.append(CharResult(cell["chars"]))
                    elif any((reg.search(clean_txt(cell["text"])) for reg in accurate_regs)):
                        items.append(CharResult(cell["chars"]))
            else:
                para_regs = kwargs.get("para_regs")
                if para_regs and not items:
                    res = self._simple_para(attr, **kwargs)
                    if res.data:
                        return res
                if items:
                    break
        return ResultOfPredictor(items)

    def _get_unit_from_tbl(self, attr, **kwargs):
        items = []
        regs = kwargs.get("regs")
        crude_elts = self.get_crude_elements(attr, kwargs.get("col_type", ""))
        for idx, crude_elt in enumerate(crude_elts):
            ele_typ, elt = self.reader.find_element_by_index(crude_elt["element_index"])
            if ele_typ == "TABLE" and self.is_aim_elt(elt, {"regs": regs}):
                cells_by_row, cells_by_col = group_cells(elt["cells"])
                cell_dicts = [
                    cells_by_row.get("0"),
                    cells_by_row.get("1"),
                    cells_by_col.get("0"),
                    cells_by_col.get("1"),
                ]
                for cell_dict in cell_dicts:
                    if cell_dict:
                        for sub_idx, cell in cell_dict.items():
                            if any((reg.search(clean_txt(cell["text"])) for reg in regs)):
                                items.append(CharResult(cell["chars"]))
                            if items:
                                break
                    if items:
                        break
            else:
                para_regs = kwargs.get("para_regs")
                if para_regs and not items:
                    res = self._simple_para(attr, **kwargs)
                    if res.data:
                        return res
        return ResultOfPredictor(items)

    def _multi_paras(self, attr, second_cols, **kwargs):
        item = ResultOfPredictor([], None)
        for second_col in second_cols:
            _item = self._paras_with_head_and_tail(second_col, **kwargs)
            if _item.data:
                item = _item
                break
        return [{second_cols[0]: item}]

    def main_tech_person(self, attr, **kwargs):
        """
        二级属性：核心技术人员
        """
        res = []
        options = [
            {
                "name": "姓名",
                "regs": [
                    re.compile(r"^(姓名|成员|名称)$"),
                    re.compile(r"^(\d|[一二三四五六七八九十]*)[、\s]?\w+"),
                    re.compile(r"(先生|女士).*?简历详见"),
                    re.compile(r"无核心技术人员"),
                ],
                "col": None,
            },
        ]
        crude_elts = self.get_crude_elements(options[0]["name"], attr)
        for idx, crude_elt in enumerate(crude_elts):
            ele_typ, elt = self.reader.find_element_by_index(crude_elt["element_index"])
            cond = {"regs": options[0]["regs"], "anchor_regs": [re.compile(r"(核心)?(技术)?人员")]}
            # print('--------', idx, ele_typ, elt['page'], self.is_aim_elt(elt, cond))
            # print(elt.get('text'))
            if not self.is_aim_elt(elt, cond):
                continue
            if ele_typ == "TABLE":
                group = {"姓名": ResultOfPredictor([TblResult(cells=None, elt=elt)])}
                res.append(group)
            elif ele_typ == "PARAGRAPH":
                group = {"姓名": ResultOfPredictor([CharResult(elt["chars"])])}
                res.append(group)
            if res:
                # print('*****')
                break
        return res

    def supervisors(self, attr, **kwargs):
        """
        二级属性：监事基本情况
        """
        res = []
        options = [
            {"name": "姓名", "regs": [re.compile(r"^(姓名|成员|名称)$"), re.compile(r"监事会?")], "col": None},
        ]
        crude_elts = self.get_crude_elements(options[0]["name"], attr)
        for idx, crude_elt in enumerate(crude_elts):
            ele_typ, elt = self.reader.find_element_by_index(crude_elt["element_index"])
            cond = {"regs": options[0]["regs"], "anchor_regs": [re.compile(r"监事会?")], "anchor_range": (-1, 5)}
            # print('--------', idx, ele_typ, elt['page'], self.is_aim_elt(elt, cond))
            # print(elt.get('text'))
            if not self.is_aim_elt(elt, cond):
                continue
            if ele_typ == "TABLE":
                group = {"姓名": ResultOfPredictor([TblResult(cells=None, elt=elt)])}
                res.append(group)
            elif ele_typ == "PARAGRAPH":
                group = {"姓名": ResultOfPredictor([CharResult(elt["chars"])])}
                res.append(group)
            if res:
                # print('******')
                break
        return res

    def directors(self, attr, **kwargs):
        """
        二级属性：董事会成员
        """
        res = []
        options = [
            {"name": "姓名", "regs": [re.compile(r"^(姓名|成员|名称)$"), re.compile(r"董事会?")], "col": None},
        ]
        crude_elts = self.get_crude_elements(options[0]["name"], attr)
        for idx, crude_elt in enumerate(crude_elts):
            ele_typ, elt = self.reader.find_element_by_index(crude_elt["element_index"])
            cond = {"regs": options[0]["regs"], "anchor_regs": [re.compile(r"董事会?")], "anchor_range": (-1, 5)}
            # print('--------', idx, ele_typ, elt['page'], self.is_aim_elt(elt, cond))
            if not self.is_aim_elt(elt, cond):
                continue
            if ele_typ == "TABLE":
                group = {"姓名": ResultOfPredictor([TblResult(cells=None, elt=elt)])}
                res.append(group)
            elif ele_typ == "PARAGRAPH":
                group = {"姓名": ResultOfPredictor([CharResult(elt["chars"])])}
                res.append(group)
            if res:
                break
        return res

    def main_supplier(self, attr, **kwargs):
        """
        二级属性：主要供应商
        """
        res = []
        options = [
            {
                "name": "时间",
                "regs": [re.compile(r"^(时间|年[度份]|期间|报告期)$"), DATE_PATTERN],
            },
        ]
        crude_elts = self.get_crude_elements(options[0]["name"], attr)
        for idx, crude_elt in enumerate(crude_elts):
            ele_typ, elt = self.reader.find_element_by_index(crude_elt["element_index"])
            cond = {"regs": options[0]["regs"], "anchor_regs": [re.compile(r"供[应货]商")], "anchor_range": (-1, 5)}
            # print('--------', idx, ele_typ, elt['page'], self.is_aim_elt(elt, cond))
            # print(elt.get('text'))
            if not self.is_aim_elt(elt, cond):
                continue
            if ele_typ == "TABLE":
                group = {"时间": ResultOfPredictor([TblResult(cells=None, elt=elt)])}
                res.append(group)
            elif ele_typ == "PARAGRAPH":
                group = {"时间": ResultOfPredictor([CharResult(elt["chars"])])}
                res.append(group)
            if res:
                # print('********')
                break
        return res

    def main_customer(self, attr, **kwargs):
        """
        二级属性：主要客户
        """
        res = []
        options = [
            {
                "name": "时间",
                "regs": [re.compile(r"^(时间|年[度份]|期间|报告期)$"), DATE_PATTERN],
            },
        ]
        crude_elts = self.get_crude_elements(options[0]["name"], attr)
        for idx, crude_elt in enumerate(crude_elts):
            ele_typ, elt = self.reader.find_element_by_index(crude_elt["element_index"])
            cond = {"regs": options[0]["regs"], "anchor_regs": [re.compile(r"客户")], "anchor_range": (-1, 5)}
            # print('--------', idx, ele_typ, elt['page'], self.is_aim_elt(elt, cond))
            # print(elt.get('text'))
            if not self.is_aim_elt(elt, cond):
                continue
            if ele_typ == "TABLE":
                group = {"时间": ResultOfPredictor([TblResult(cells=None, elt=elt)])}
                res.append(group)
            elif ele_typ == "PARAGRAPH":
                group = {"时间": ResultOfPredictor([CharResult(elt["chars"])])}
                res.append(group)

            if res:
                # print('********')
                break
        return res

    def shareholder_person(self, attr, **kwargs):
        """
        二级属性：控股股东-自然人
        """
        res = []
        options = [
            {
                "name": "姓名",
                "regs": [],
            },
        ]
        crude_elts = self.get_crude_elements(options[0]["name"], attr)
        for idx, crude_elt in enumerate(crude_elts):
            ele_typ, elt = self.reader.find_element_by_index(crude_elt["element_index"])
            cond = {
                "regs": options[0]["regs"],
                "anchor_regs": [re.compile(r"控股股东")],
            }
            # print('--------', idx, ele_typ, elt['page'], self.is_aim_elt(elt, cond))
            if not self.is_aim_elt(elt, cond):
                continue
            if ele_typ == "PARAGRAPH":
                group = {"姓名": ResultOfPredictor([CharResult(elt["chars"])])}
                res.append(group)
            if res:
                break
        return res

    def issuer_industry(self, attr, **kwargs):
        """
        二级属性：发行人所处行业
        """
        res = []
        options = [
            {
                "name": "行业分类标准",
                "regs": [re.compile(r"(上市公司行业分类指引|国民经济行业分类)")],
            },
        ]
        crude_elts = self.get_crude_elements(options[0]["name"], attr)
        for idx, crude_elt in enumerate(crude_elts):
            ele_typ, elt = self.reader.find_element_by_index(crude_elt["element_index"])
            cond = {
                "regs": options[0]["regs"],
            }
            # print('--------', idx, ele_typ, elt['page'], self.is_aim_elt(elt, cond))
            if not self.is_aim_elt(elt, cond):
                continue
            if ele_typ == "PARAGRAPH":
                group = {"行业分类标准": ResultOfPredictor([CharResult(elt["chars"])])}
                res.append(group)
            if res:
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
        for idx, elt in enumerate(crude_elts):
            ele_typ, elt = self.reader.find_element_by_index(elt["element_index"])
            if ele_typ in ["PARAGRAPH", "TABLE"] or ele_typ is None:
                if ele_typ == "PARAGRAPH":
                    elt = self.fix_continued_para(elt)  # 修复跨页段落
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

    def _important_contract(self, attr, second_cols, **kwargs):
        item = ResultOfPredictor([], None)
        second_col = second_cols[0]
        _item = self._tbl_or_paras(second_cols[0], **kwargs)
        if _item.data:
            item = _item
        return [{second_col: item}]
