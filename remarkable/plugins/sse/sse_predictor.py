import functools
import re
from collections import OrderedDict
from copy import deepcopy

from remarkable.common.util import clean_txt, group_cells, index_in_space_string
from remarkable.plugins.hkex.common import Schema
from remarkable.predictor.predict import (
    AnswerPredictor,
    CharResult,
    MoldSchema,
    ParaResult,
    ResultOfPredictor,
    TblResult,
)

DATE_PATTERN = re.compile(r"(\d+)年度?(\d+月份?)?(\d+日)?")
R_CN_NUM = r"一二三四五六七八九十"


class SsePredictor(AnswerPredictor):
    SUB_ATTRS = {
        "主要财务数据和财务指标": [
            {"name": "资产总额", "regs": [re.compile(r"^资产总额")], "row": None},
            {"name": "归属于母公司所有者权益", "regs": [re.compile(r"^归属于母公司(所有者|股东)权益")], "row": None},
            {"name": "时间", "regs": [re.compile(r"^项目$")], "row": None},
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
                "row": None,
            },
            {"name": "流动资产合计", "regs": [re.compile(r"^流动资产[合总]计")], "row": None},
            {"name": "长期股权投资", "regs": [re.compile(r"^长期股权投资")], "row": None},
            {"name": "非流动资产合计", "regs": [re.compile(r"^非流动资产[合总]计")], "row": None},
            {"name": "资产总计", "regs": [re.compile(r"^资产[合总]计")], "row": None},
            {"name": "时间", "regs": [re.compile(r"^[科项]目$")], "row": None},
        ],
        "前十名股东": [
            {"name": "股东姓名/名称", "regs": [re.compile(r"股东|发起人")], "col": None},
            {"name": "持股数量", "regs": [re.compile(r"持股数量?|所持股份|股数")], "col": None},
            {"name": "持股比例", "regs": [re.compile(r"(持股)?(比例|占比)")], "col": None},
        ],
        "募集资金总量及使用情况": [
            {
                "name": "项目名称",
                "regs": [
                    re.compile(r"项目名称"),
                    re.compile(r"募集资金运用方向"),
                    re.compile(r"投资项目"),
                ],
                "col": None,
            },
            {"name": "投资总额", "regs": [re.compile(r"投资.*额|总投资|预算")], "col": None},
            {
                "name": "募集资金投资额",
                "regs": [
                    re.compile(r"募集资金"),
                ],
                "col": None,
            },
            {"name": "审批文号", "regs": [re.compile(r"审批文号")], "col": None},
        ],
    }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.schema_obj = Schema(self.mold)
        self.register = {
            "科创板招股说明书信息抽取POC": [
                # 第二节 发行人情况
                {
                    "attr": "发行人情况-发行人名称",
                    "func": self._simple_tbl,
                    "options": {
                        "regs": [
                            re.compile(r"^(发行人|中文)名称"),
                        ],
                    },
                },
                {
                    "attr": "发行人情况-成立日期",
                    "func": self._simple_tbl,
                    "options": {
                        "regs": [
                            re.compile(r"成立日期"),
                        ],
                    },
                },
                {
                    "attr": "发行人情况-注册资本",
                    "func": self._simple_tbl,
                    "options": {
                        "regs": [
                            re.compile(r"^注册资本$"),
                        ],
                    },
                },
                {
                    "attr": "发行人情况-法定代表人",
                    "func": self._simple_tbl,
                    "options": {
                        "regs": [
                            re.compile(r"法定代表人"),
                        ],
                    },
                },
                {
                    "attr": "发行人情况-注册地址",
                    "func": self._simple_tbl,
                    "options": {
                        "regs": [
                            re.compile(r"注册地址"),
                        ],
                    },
                },
                {
                    "attr": "发行人情况-主要生产经营地址",
                    "func": self._simple_tbl,
                    "options": {
                        "regs": [
                            re.compile(r"主要生产经营地址"),
                        ],
                    },
                },
                {
                    "attr": "发行人情况-控股股东",
                    "func": self._simple_tbl,
                    "options": {
                        "regs": [
                            re.compile(r"控股股东"),
                        ],
                    },
                },
                {
                    "attr": "发行人情况-实际控制人",
                    "func": self._simple_tbl,
                    "options": {
                        "regs": [
                            re.compile(r"实际控制人"),
                        ],
                    },
                },
                {
                    "attr": "发行人情况-行业分类",
                    "func": self._simple_tbl,
                    "options": {
                        "regs": [
                            re.compile(r"行业分类"),
                        ],
                    },
                },
                {
                    "attr": "发行人情况-在其他交易场所(申请)挂牌或上市的情况",
                    "func": self._simple_tbl,
                    "options": {
                        "regs": [
                            re.compile(r"在其他交易场所[(（]申请[）)]挂牌或上市的?情况"),
                        ],
                    },
                },
                # 第二节 中介机构
                {
                    "attr": "中介机构-保荐人",
                    "func": self._simple_tbl,
                    "options": {
                        "regs": [
                            re.compile(r"保荐人"),
                        ],
                    },
                },
                {
                    "attr": "中介机构-主承销商",
                    "func": self._simple_tbl,
                    "options": {
                        "regs": [
                            re.compile(r"主承销商"),
                        ],
                    },
                },
                {
                    "attr": "中介机构-发行人律师",
                    "func": self._simple_tbl,
                    "options": {
                        "regs": [
                            re.compile(r"发行人律师"),
                        ],
                    },
                },
                {
                    "attr": "中介机构-其他承销机构",
                    "func": self._simple_tbl,
                    "options": {
                        "regs": [
                            re.compile(r"其他承销机构"),
                        ],
                    },
                },
                {
                    "attr": "中介机构-审计机构",
                    "func": self._simple_tbl,
                    "options": {
                        "regs": [
                            re.compile(r"审计机构"),
                        ],
                    },
                },
                {
                    "attr": "中介机构-评估机构",
                    "func": self._simple_tbl,
                    "options": {
                        "regs": [
                            re.compile(r"评估机构"),
                        ],
                    },
                },
                # 第二节 发行情况
                {
                    "attr": "发行情况-每股面值",
                    "func": self._simple_tbl,
                    "options": {
                        "regs": [
                            re.compile(r"每股面值"),
                        ],
                    },
                },
                {
                    "attr": "发行情况-发行股数",
                    "func": self._simple_tbl,
                    "options": {
                        "regs": [
                            re.compile(r"发行股数"),
                        ],
                    },
                },
                {
                    "attr": "发行情况-发行股数占发行后总股本比例",
                    "func": self._simple_tbl,
                    "options": {
                        "regs": [
                            re.compile(r"占发行后总股本的?比例"),
                        ],
                    },
                },
                {
                    "attr": "发行情况-发行后总股本",
                    "func": self._simple_tbl,
                    "options": {
                        "regs": [
                            re.compile(r"^发行后总股本$"),
                        ],
                    },
                },
                {
                    "attr": "发行情况-募集资金总额",
                    "func": self._simple_tbl,
                    "options": {
                        "regs": [
                            re.compile(r"^募集资金总额$"),
                        ],
                    },
                },
                {
                    "attr": "发行情况-募集资金净额",
                    "func": self._simple_tbl,
                    "options": {
                        "regs": [
                            re.compile(r"^募集资金净额$"),
                        ],
                    },
                },
                {
                    "attr": "发行情况-募集资金投资项目",
                    "func": self._simple_tbl,
                    "options": {
                        "regs": [
                            re.compile(r"^募集资金投资项目$"),
                        ],
                    },
                },
                {
                    "attr": "发行情况-发行费用概算",
                    "func": self._simple_tbl,
                    "options": {
                        "regs": [
                            re.compile(r"^发行费用概算$"),
                        ],
                    },
                },
                # 第二节 财务数据
                {
                    "attr": "财务数据-货币单位",
                    "func": self._simple_tbl,
                    "options": {
                        "regs": [
                            re.compile(r"^资产总额[(（](?P<dst>.*?元)[）)]"),
                        ],
                    },
                },
                {
                    "attr": "主要财务数据和财务指标",
                    "func": self._col_group_in_tbl,
                },
                # 第二节 上市标准
                {
                    "attr": "上市标准条款编号",
                    "func": self._simple_para,
                    "options": {
                        "regs": [
                            re.compile(
                                rf"(?P<dst1>2.1.[23](条款?)?|第?二十二条)[^。]*?(“.*?”)?[^。]*?(?P<dst2>第?[()（）\[\]【】{R_CN_NUM}]+[项条]?)?"
                            )
                        ],
                    },
                },
                {
                    "attr": "上市标准具体内容",
                    "func": self._simple_para,
                    "options": {
                        "regs": [
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
                    },
                },
                # @zhangjianfei
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
                # 第三节
                {
                    "attr": "保荐人-法定代表人",
                    "func": self.func_3_2,
                    "options": {
                        "regs": [
                            re.compile(r"法定代表人"),
                        ],
                        "para_regs": [
                            re.compile(r"法.*人[：:](?P<dst>.+)"),
                        ],
                    },
                },
                # 第五节
                {
                    "attr": "实际控制人-姓名",
                    "func": lambda attr, **kwargs: self._simple_tbl("发行人情况-实际控制人", **kwargs),
                    "options": {
                        "regs": [
                            re.compile(r"实际控制人"),
                        ],
                    },
                },
                # 第五节
                {
                    "attr": "控股股东/实际控制人股份是否存在质押情况",
                    "func": self._simple_para,
                    "options": {
                        "regs": [
                            re.compile(r"(?P<dst>（\w+）\D*?[直间]接\D*?质押\D*?。$)"),
                            re.compile(r"(?P<dst>\D*?[直间]接\D*?质押\D*?。$)"),
                        ],
                        "neg_regs": [
                            re.compile(r"不存在|没有"),
                        ],
                    },
                },
                # 第五节
                {
                    "attr": "持股数量单位",
                    "func": self._simple_tbl,
                    "options": {
                        "regs": [
                            re.compile(r"^持股数量[(（]?(?P<dst>.*?股)?[)）]?"),
                        ],
                    },
                },
                # 第五节
                {
                    "attr": "持股比例单位",
                    "func": self._simple_tbl,
                    "options": {
                        "regs": [
                            re.compile(r"^持股比例[(（]?(?P<dst>.*%)?[)）]?"),
                        ],
                    },
                },
                # 第五节
                {"attr": "前十名股东", "func": self._row_group_in_tbl},
                {"attr": "董事会成员", "func": self.board_officer},
                # 第五节
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
                # 第六节
                {
                    "attr": "前五供应商货币单位",
                    "func": self._simple_para,
                    "options": {
                        "regs": [
                            re.compile(r"单位[:：]\s*?(?P<dst>\w*元)"),
                        ],
                    },
                },
                # 第六节
                {"attr": "前五供应商", "func": self.main_supplier},
                # 第七节
                {
                    "attr": "发行人协议控制架构情况",
                    "func": self._simple_para,
                    "options": {
                        "regs": [
                            # re.compile(r'(?P<dst>发行人协议控制架构\D*?协议控制\w*?情况[.。]?)'),
                            re.compile(r"(?P<dst>\D*?协议控制\w*?情况[.。]?)"),
                        ],
                        "neg_regs": [re.compile(r"(没有|不存在)\w*?协议控制")],
                    },
                },
                # 第八节
                {
                    "attr": "合并资产负债表货币单位",
                    "func": self._simple_para,
                    "options": {
                        "regs": [
                            re.compile(r"单位[:：]\s*?(?P<dst>\w*元)"),
                        ],
                    },
                },
                # 第八节
                {
                    "attr": "合并资产负债表",
                    "func": self._col_group_in_tbl,
                },
                # 第八节
                {
                    "attr": "审计意见",
                    "func": self._simple_para,
                    "options": {
                        "regs": [
                            re.compile(r"(?P<dst>标准无保留意见)"),
                            re.compile(r"(出具|发表)\w+?(?P<dst>\w+?)的?\w+(?:意见|报告)"),
                            re.compile(r"\D*?[号字]”?(?P<dst>\w+?)的?\w+(?:意见|报告)"),
                        ],
                        "oneshot": True,
                    },
                },
                # 第八节
                {
                    "attr": "营业收入分区域分析货币单位",
                    "func": self._simple_para,
                    "options": {
                        "regs": [
                            re.compile(r"单位[:：]\s*?(?P<dst>\w*元)"),
                        ],
                    },
                },
                # 第八节
                {
                    "attr": "营业收入分区域分析占比单位",
                    "func": lambda attr, **kwargs: self.region_analysis("营业收入分区域分析", **kwargs),
                    "options": {
                        "unit": "%",
                        "regs": [
                            re.compile(r"\d?\.?\d+(?P<dst>%)"),
                            re.compile(r"\D*?(?P<dst>%)"),
                        ],
                        "oneshot": True,  # 取到一个结果即退出
                    },
                },
                # 第八节
                {
                    "attr": "营业收入分区域分析",
                    "func": self.region_analysis,
                    "options": {"regs": [re.compile(r"^(地区|区域|项目)")]},
                },
                # 第九节
                {
                    "attr": "募集资金总量及使用情况货币单位",
                    "func": self._simple_para,
                    "options": {
                        "regs": [
                            re.compile(r"单位[:：](?P<dst>.*?元)"),
                        ],
                        "anchor_regs": [
                            re.compile(r"募集资金"),
                        ],
                        "anchor_range": (-1, 3),
                    },
                },
                {"attr": "募集资金总量及使用情况", "func": self._row_group_in_tbl},
                # 第十一节
                {
                    "attr": "重大诉讼情况",
                    "func": self.major_lawsuit,
                    "options": {
                        "regs": [
                            # re.compile(r'(?P<dst>^\w+、?\s*?.*重大诉讼\D*?[至止到]\D*?重大诉讼\D*?。$)'),
                            re.compile(r"(?P<dst>\D*?[至止到]\D*?重大.*?诉讼\D*?。$)"),
                        ],
                        "neg_regs": [re.compile(r"(无|不存在|没有|不涉及|未涉及)")],
                        "anchor_regs": [
                            re.compile(r"重大诉讼"),
                            re.compile(r"诉讼[及或和与]仲裁"),
                            re.compile(r"仲裁[及或和与]诉讼"),
                        ],
                        "anchor_range": (-1, 1),
                    },
                },
            ],
            "变更证券简称公告信息抽取POC": [
                {
                    "attr": "证券代码",
                    "func": self.change_short_name,
                    "options": {
                        "regs": [
                            re.compile(r"(?:证券|股票)[代编][号码][：:]?(?P<dst>\d+)"),
                            re.compile(r"(?P<dst>\d{6})"),
                        ],
                        "prefer": "pdfinsight",
                    },
                },
                {
                    "attr": "证券简称",
                    "func": self.change_short_name,
                    "options": {
                        "regs": [
                            re.compile(
                                r"(?:证券|股票)[简名]称[：:]\s*?(?P<dst1>[＊\w\*\s]+).*(?P<dst2>\w{2,}\s*?[AB]\s*?股)"
                            ),
                            re.compile(r"(?:证券|股票)[简名]称[：:]\s*?(?P<dst>.*科技)"),
                            re.compile(r"(?:证券|股票)[简名]称[：:]\s*?(?P<dst>[＊\w\*]+)公告编号"),
                            re.compile(r"(?:证券|股票)[简名]称[：:]\s*?(?P<dst>[＊\w\*]+)编号"),
                            re.compile(r"(?:证券|股票)[简名]称[：:]\s*?(?P<dst>[＊\w\*]+)\s*?"),
                        ],
                        "prefer": "pdfinsight",
                    },
                },
                {
                    "attr": "公告编号",
                    "func": self.change_short_name,
                    "options": {
                        "regs": [
                            re.compile(r"编?\s?[码号][：:]?\s?(?P<dst>\w\s*?\d+[-—－]\d+)"),
                            re.compile(r".*[码号][：:]\s*?(?P<dst>.*?)\s*?$"),
                        ],
                        "prefer": "pdfinsight",
                    },
                },
                {
                    "attr": "变更后的证券简称",
                    "func": self.change_short_name,
                    "options": {
                        "regs": [
                            re.compile(
                                r"A股[：:]\s*?[\"“]?(?P<dst1>[＊\w\*\s]+).*?B股[：:]\s*?[\"“]?(?P<dst2>[＊\w\*\s]+)"
                            ),
                            re.compile(r"变更为[\"“](?P<dst>[＊\w\*\s]+)[\"”]"),
                            re.compile(r"变更\w[^日期]*?[：:]\s*?[\"“]?(?P<dst>[＊\w\*\s]+)[\"”]?$"),
                            re.compile(r"变更\w[^日期]*?[：:]\s*?[\"“]?(?P<dst>[＊\w\*\s]+)[\"”]?[，,]?"),
                        ],
                        # 'prefer': 'pdfinsight'
                    },
                },
                {
                    "attr": "变更日期",
                    "func": self.change_short_name,
                    "options": {
                        "regs": [
                            re.compile(
                                r"[从自至]\s*?(?P<dst>\d{4}\s*?年\s*?\d{1,2}\s*?月\s*?\d{1,2}\s?[日号])\s*?(?:起|开始)"
                            ),
                            re.compile(
                                r"变更.*?日期?[：:]?\s?(?P<dst>\d{4}\s*?年\s*?\d{1,2}\s*?月\s*?\d{1,2}\s?[日号])"
                            ),
                        ],
                    },
                },
                {
                    "attr": "公告日",
                    "func": self.change_short_name,
                    "options": {
                        "regs": [re.compile(r"(?P<dst>\w[0O○Ｏ〇零]\w+\s*?年\s*?\w+\s*?月\s*?\w+\s*?日)")],
                        "reverse": True,  # 倒序取, 基本上最后一个元素块即公告日
                        "prefer": "pdfinsight",
                    },
                },
            ],
        }
        for item in self.register.get(self.root_schema_name, []):
            # if item['attr'] not in ['变更日期']:
            #     continue
            self.column_analyzers.update(
                {
                    item["attr"]: functools.partial(item["func"], item["attr"], **item.get("options", {})),
                }
            )

    def get_crude_elements(self, attr, col_type):
        if col_type and col_type not in MoldSchema.basic_types + self.schema_obj.enum_types:
            attr = "-".join([col_type, attr])
        return self.crude_answer.get(attr, [])

    def is_aim_elt(self, elt, options):
        if not options.get("regs"):
            return True

        # 上方必须出现某些关键词
        anchor_regs = options.get("anchor_regs", [])
        if anchor_regs:
            anchor_range = options.get("anchor_range", (-1, 3))
            prev_elts = self.reader.find_elements_near_by(elt["index"], step=anchor_range[0], amount=anchor_range[1])
            flag = False
            for prev_elt in prev_elts:
                if prev_elt["class"] == "PARAGRAPH":
                    if any(reg.search(clean_txt(prev_elt.get("text", ""))) for reg in anchor_regs):
                        flag = True
                        break
            return flag

        if elt["class"] == "TABLE":
            for cell in elt.get("cells", {}).values():
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

    @staticmethod
    def sorted_cells(cells, reverse=False):
        sorted_d = sorted(cells.items(), key=lambda k_v: int(k_v[0]), reverse=reverse)
        return OrderedDict(sorted_d)

    def _simple_tbl(self, attr, **kwargs):
        """
        处理关键词同cell或下一个cell为结果的情况
            1. 关键词下一个cell为结果，比如：发行人名称|a公司
            2. 同cell, 比如: "持股数量（万股）"中"持股数量"为关键词, "万股"为期望结果, 正则可写为r'持股数量(.*?股)?'
        """
        items = []
        crude_elts = self.get_crude_elements(attr, kwargs.get("col_type", ""))
        regs = kwargs.get("regs", [])
        for crude_elt in crude_elts:
            ele_typ, elt = self.reader.find_element_by_index(crude_elt["element_index"])
            # print('--------', idx, ele_typ, elt['page'])
            flag = False
            if ele_typ == "TABLE" and self.is_aim_elt(elt, kwargs):
                cells = self.cell_ordering(elt)
                for cell in cells.values():
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

    def _col_group_in_tbl(self, attr, **kwargs):
        """
        二级属性
        财务表格中一列数据作为一组答案的情况
        """
        res = []
        options = self.SUB_ATTRS.get(attr)
        if not options:
            return []
        for sub_attr in options:
            sub_attr["row"] = None
            sub_attr["col"] = None
        crude_elts = self.get_crude_elements(options[0]["name"], attr)
        for crude_elt in crude_elts:
            ele_typ, elt = self.reader.find_element_by_index(crude_elt["element_index"])
            # print('--------', idx, ele_typ, elt['page'])
            elt_syllabus_id = elt.get("syllabus", None)
            if elt_syllabus_id:
                syllabus_title = self.reader.syllabus_dict[elt_syllabus_id]["title"]
                title_reg = options[0].get("anchor_regs", None)
                if title_reg and not any((reg.search(syllabus_title) for reg in title_reg)):
                    continue
            if ele_typ == "TABLE" and self.is_aim_elt(elt, {"regs": options[0]["regs"]}):
                _, cells_by_col = group_cells(elt["cells"])
                for col in sorted(cells_by_col, key=int):  # 从左到右
                    group = {}
                    cells = cells_by_col.get(str(col))
                    for row in sorted(cells, key=int):  # 从上到下
                        cell = cells.get(str(row))
                        if col == "0":  # 第一列决定子属性出现在哪一行
                            for sub_attr in options:
                                if not sub_attr["row"] and any(
                                    reg.search(clean_txt(cell["text"])) for reg in sub_attr["regs"]
                                ):
                                    # print('****', col, row, sub_attr['name'], clean_txt(cell['text']))
                                    sub_attr["row"] = row
                        else:  # 标注其余列
                            for sub_attr in options:
                                # print(sub_attr['name'], sub_attr['row'], row == sub_attr['row'])
                                if sub_attr["row"] is not None and row == sub_attr["row"]:
                                    # print('****', col, row, sub_attr['name'], clean_txt(cell['text']))
                                    res_obj = ResultOfPredictor([CharResult(cell["chars"])])
                                    group.setdefault(sub_attr["name"], res_obj)
                    if group:
                        res.append(group)
            if res:
                break
        return res

    def _row_group_in_tbl(self, attr, **kwargs):
        """
        二级属性
        股东/供应商表格中一行数据作为一组答案的情况
        """
        res = []
        options = self.SUB_ATTRS.get(attr)
        if not options:
            return []
        for sub_attr in options:
            sub_attr["row"] = None
            sub_attr["col"] = None
        crude_elts = self.get_crude_elements(options[0]["name"], attr)

        for crude_elt in crude_elts:
            ele_typ, elt = self.reader.find_element_by_index(crude_elt["element_index"])
            # print('--------', idx, ele_typ, elt['page'], self.is_aim_elt(elt, {'regs': options[0]['regs']}))

            # 需要跳过的行
            pass_regs = [
                re.compile(r"[合总小]计"),
            ]
            pass_regs.extend(options[0]["regs"])

            if ele_typ == "TABLE" and self.is_aim_elt(elt, {"regs": options[0]["regs"]}):
                cells_by_row, cells_by_col = group_cells(elt["cells"])
                header_rows = [str(i) for i in range(elt["cells"]["0_0"]["bottom"])]
                # header_rows = ["0"]
                for row in sorted(cells_by_row, key=int):  # 从上到下
                    group = {}
                    cells = cells_by_row.get(str(row))
                    # print(row, {k: v['text'] for k, v in cells.items()})

                    # 需要跳过的行
                    is_pass_row = False
                    if row not in header_rows:
                        for cell in cells.values():
                            if any(reg.search(clean_txt(cell["text"])) for reg in pass_regs):
                                is_pass_row = True
                                break
                    if is_pass_row:
                        # print('pass row ...')
                        continue

                    # 提取数据
                    for col in sorted(cells, key=int):  # 从左到右
                        cell = cells.get(str(col))
                        if not cell:
                            continue
                        if row in header_rows:  # 第一行决定子属性出现在哪一列
                            for sub_attr in options:
                                if not sub_attr["col"] and any(
                                    reg.search(clean_txt(cell["text"])) for reg in sub_attr["regs"]
                                ):
                                    # print('*********', row, col, sub_attr['name'], clean_txt(cell['text']))
                                    sub_attr["col"] = col
                        else:  # 标注其余列
                            for sub_attr in options:
                                # print(sub_attr['name'], sub_attr['row'], row == sub_attr['row'])
                                if sub_attr["col"] is not None and col == sub_attr["col"]:
                                    # print('****', row, col, sub_attr['name'], clean_txt(cell['text']))
                                    res_obj = ResultOfPredictor([CharResult(cell["chars"])])
                                    group.setdefault(sub_attr["name"], res_obj)
                    if group:
                        res.append(group)
            if res:
                break
        return res

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

    def _simple_para(self, attr, **kwargs):
        """
        按句式提取段落的一部分作为结果
        如果提供了否定判断的正则`neg_regs`, 即枚举类型, 会在value放置对应规则的枚举值
        """
        items = []
        value = None
        crude_elts = self.get_crude_elements(attr, kwargs.get("col_type", ""))
        for elt in crude_elts:
            ele_typ, elt = self.reader.find_element_by_index(elt["element_index"])
            if ele_typ == "PARAGRAPH" and self.is_aim_elt(elt, kwargs):
                elt = self.fix_continued_para(elt)  # 修复跨页段落
                # print('----------' * 3, idx, elt['page'], elt['text'], )
                for reg in kwargs.get("regs", []):
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
            if self.is_aim_elt(element, {"regs": [reg] + kwargs.get("para_regs", [])}):
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

    def func_3_2(self, attr, **kwargs):
        items = []
        para_regs = kwargs.get("para_regs", [])
        elts = self.get_crude_elements(attr, kwargs.get("col_type", ""))
        for idx, eitem in enumerate(elts):
            if idx >= 3:
                break
            ele_typ, element = self.reader.find_element_by_index(eitem["element_index"])
            if ele_typ == "PARAGRAPH":
                for para_reg in para_regs:
                    res = para_reg.search(element["text"])
                    if res:
                        _start, _end = res.span("dst")
                        items.append(CharResult(element["chars"][_start:_end]))
                        break
        if items:
            return ResultOfPredictor(items)
        return self._simple_tbl(attr, **kwargs)

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

            # print('--------', idx, ele_typ, elt['page'], self.is_aim_elt(elt, cond))
            if ele_typ == "TABLE" and self.is_aim_elt(elt, cond):
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
                    para = self.fix_continued_para(elt)
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
            # print('--------', idx, ele_typ, elt['page'], self.is_aim_elt(elt, cond))
            if ele_typ == "TABLE" and self.is_aim_elt(elt, cond):
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

    def region_analysis(self, attr, **kwargs):
        """
        营业收入区域分析
        """
        res = []
        crude_elts = self.crude_answer.get("营业收入分区域分析-时间", [])
        unit = kwargs.get("unit")

        for crude_elt in crude_elts:
            ele_typ, elt = self.reader.find_element_by_index(crude_elt["element_index"])

            # 营业收入分区域分析占比单位 可能出现在表格或者段落中
            if unit and ele_typ == "PARAGRAPH" and self.is_aim_elt(elt, kwargs):
                return self._simple_para("营业收入分区域分析占比单位", **kwargs)
            if unit and ele_typ == "TABLE" and self.is_aim_elt(elt, kwargs):
                for _, cell in elt["cells"].items():
                    if unit in cell["text"]:
                        return ResultOfPredictor([CharResult([i for i in cell["chars"] if i["text"] == unit])])
                return self._simple_tbl("营业收入分区域分析占比单位", **kwargs)

            # 其余二级属性只会出现在表格里
            if ele_typ == "TABLE" and self.is_aim_elt(elt, kwargs):
                row_cells, col_cells = group_cells(elt["cells"])
                # 取列/行索引
                first_row_cells, first_col_cells = (
                    self.sorted_cells(row_cells["0"], True),
                    self.sorted_cells(col_cells["0"]),
                )

                # 有无大类
                nested = False
                for _, cell in list(first_col_cells.items())[1:-1]:
                    if re.search(r"其中|合计|共计|总计|总共", cell["text"].strip()):
                        nested = True
                        break

                for row, row_cell in first_col_cells.items():  # 从上到下
                    group = {}

                    # 跳过表头/最后合计行
                    if int(row) < 2 or int(row) + 1 == len(first_col_cells.items()):
                        continue
                    # 跳过子类
                    if nested and re.search(r"(地区|东|西|南|北|中|省|市|自治区|行政区)$", row_cell["text"].strip()):
                        continue
                    # 跳过跨页表头
                    if re.search(r"^(地区|区域|项目)$", row_cell["text"].strip()):
                        continue
                    # 组装地区
                    group.setdefault("地区", ResultOfPredictor([CharResult(row_cell["chars"])]))
                    _group = deepcopy(group)
                    for col, col_cell in first_row_cells.items():  # 从右到左
                        _cell = elt["cells"]["{}_{}".format(row, col)]
                        if int(col) == 0:  # 跳过左侧地区列
                            break
                        # 组装时间
                        _group.setdefault("时间", ResultOfPredictor([CharResult(col_cell["chars"])]))

                        if col_cell["left"] != int(col):  # '占比'在右侧
                            _group.setdefault("占比", ResultOfPredictor([CharResult(_cell["chars"])]))
                        if col_cell["left"] == int(col):  # '收入'在左侧
                            _group.setdefault("收入", ResultOfPredictor([CharResult(_cell["chars"])]))

                        # '收入'会比'占比'晚组装
                        if "收入" in _group:
                            res.append(_group)  # 组装一个记录
                            _group = deepcopy(group)  # 初始化, 继续下一个时间段
            if res:
                break

        # 可能什么都没找到, 需要返回ResultOfPredictor对象
        return res if res else ResultOfPredictor([])

    def major_lawsuit(self, attr, **kwargs):
        """重大诉讼情况"""
        res = []
        elts = self.reader.find_sylls_by_pattern(kwargs.get("anchor_regs"))
        if not elts:
            return self._simple_para(attr, **kwargs)

        elt = deepcopy(elts[0])
        value = None
        elts = []
        while elt["element"] < elt["range"][-1]:
            elts.append(self.reader.find_element_by_index(elt["element"])[-1])
            elt["element"] += 1

        for idx, elt in enumerate(elts):
            if idx == 1:
                # 紧接着一段如果没有否定词描述, 那就是有重大诉讼情况
                for neg_reg in kwargs.get("neg_regs"):
                    if neg_reg.search(clean_txt(elt["text"])):
                        value = self.schema_obj.label_enum_value(attr, -1)
                        break
                else:
                    value = self.schema_obj.label_enum_value(attr)
            if elt and elt["class"] == "PARAGRAPH":
                res.append(elt["chars"])

        res = [CharResult(chars) for chars in res]
        return ResultOfPredictor(res, value)
