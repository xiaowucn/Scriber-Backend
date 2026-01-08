import hashlib
import json
import logging
import os
import re
from collections import defaultdict, namedtuple
from copy import deepcopy
from datetime import datetime
from enum import IntEnum
from pathlib import Path

from remarkable.answer.common import get_mold_name
from remarkable.common.exceptions import NotSupportConvertError, PushError
from remarkable.common.util import clean_txt
from remarkable.config import target_path
from remarkable.converter import AnswerWorkShop, ConverterMaker, SSEBaseConverter
from remarkable.converter.sse.kcb_conv import KCBProspectusConverter
from remarkable.converter.utils import (
    DataPack,
    adjust_decimal_places,
    csv_reader,
    date_from_text,
    push,
)
from remarkable.plugins.sse.sse_answer_formatter import AnswerItem

p_table = re.compile(r"\((?P<table>.*)\)")
p_number = re.compile(r"[0-9.,%/-]+(?!/-$)")
p_decimal_places = re.compile(r".*[\d]+,(?P<dst>[\d]+)")
p_date = re.compile(r"(\d{4})-(\d{1,2})-(\d{1,2})")
p_year = re.compile(r"(\d{4})[年度]*$")
p_year_quarter = re.compile(r"(\d{4})年?.*([1234一二三四])季")
p_year_month = re.compile(r"(\d{4})年?\d.*(\d)月")

DSItem = namedtuple("DataStructInfo", ["param_map", "ds_map", "pop_keys"])


class ParseType(IntEnum):
    SOURCE = 0  # 上游对接
    MANUAL = 1  # 手动上传


class ParaMapType(IntEnum):
    MAIN_BOARD = 0
    KCB = 1
    KCB_PROSPECTUS = 2  # 科创板招股说明书

    @classmethod
    def path2type(cls, path):
        path = Path(path)
        if path.name.startswith("ke_prospectus_"):
            return cls.KCB_PROSPECTUS
        if path.name.startswith("main_"):
            return cls.MAIN_BOARD
        return cls.KCB


class SSEConverterMaker(ConverterMaker):
    """
    NOTE: 资金占用专项、对外投资、证监会交易所披露处罚信息，在二期，先不用处理
    """

    converter_map = {
        # schema_name: converter
        "科创板招股说明书信息抽取": KCBProspectusConverter,
        "科创板招股说明书信息导出json": KCBProspectusConverter,
        # converter_name: converter
        "InterimNoticeAccidentConverter": SSEBaseConverter,  # 13 临时公告-事故
        "InterimAnnIntellectualPropertyConverter": SSEBaseConverter,  # 23 临时公告-知识产权
        "InterimNoticeRevokeConverter": SSEBaseConverter,  # 24 临时公告-公司被责令关闭或吊销经营资质
        "Kcb1001Converter": SSEBaseConverter,  # 1001 异常变动
        "Kcb1901Converter": SSEBaseConverter,  # 1901 可转债上市
        "Kcb2105Converter": SSEBaseConverter,  # 2105 股权激励计划终止
        "Kcb0707Converter": SSEBaseConverter,  # 0707 归还募集资金
        "Kcb1002Converter": SSEBaseConverter,  # 1002 澄清或说明
        "Kcb1601Converter": SSEBaseConverter,  # 1601 进入重大资产重组程序停牌
        "Kcb1602Converter": SSEBaseConverter,  # 1602 重大资产重组停牌期延长
        "Kcb1603Converter": SSEBaseConverter,  # 1603 取消重大资产重组并复牌
        "Kcb1922Converter": SSEBaseConverter,  # 1922 可转债发行
        "Kcb2602Converter": SSEBaseConverter,  # 2602 发生重大债务或重大债权到期未获清偿
        "Kcb1613Converter": SSEBaseConverter,  # 1613 重大资产重组终止
        "Kcb0704Converter": SSEBaseConverter,  # 0704 变更募集资金用途【三】
        "Kcb2702Converter": SSEBaseConverter,  # 2702 变更证券简称
        "Kcb2802Converter": SSEBaseConverter,  # 2802 实施退市风险警示
        "Kcb2806Converter": SSEBaseConverter,  # 2806 撤销退市风险警示
        "Kcb1906Converter": SSEBaseConverter,  # 1906 可转债付息
        "Kcb0425Converter": SSEBaseConverter,  # 0425 签订战略框架协议
        "Kcb2615Converter": SSEBaseConverter,  # 2615 重要前期会计差错更正
    }

    @classmethod
    def get_class_name(cls, name: str) -> str:
        """
        从接口名中取出对应 converter 的类名
        如: "asset_disposal(资产处置公告)" -> "AssetDisposalConverter"
        """
        sep = re.compile(r"（|\(")
        if name.startswith("kcb") or "_" in name:
            cls_name = "".join(t.title() for t in sep.split(name)[0].split("_"))
        else:
            cls_name = name.title()
        return cls_name + "Converter"

    @classmethod
    def init(cls, interface_name, answer):
        """
        加载转换类顺序:
            1. cls.converter_map[schema name]
            2. cls.converter_map[cls_name(接口 xxx 字段拼接:XxxConverter)]
            3. 当前目录下(如 sse/*_conv.* )寻找符合 cls_name 的转换类
            4. NullConverter(没有找到, 即暂未实现转换的 schema)
        """
        mold_name = get_mold_name(answer)
        if mold_name in cls.converter_map:
            return cls.converter_map[mold_name](answer)
        cls_name = cls.get_class_name(interface_name)
        converter = cls.converter_map.get(cls_name) or cls.load_converter(__package__, Path(__file__).parent, cls_name)
        return converter(answer)
