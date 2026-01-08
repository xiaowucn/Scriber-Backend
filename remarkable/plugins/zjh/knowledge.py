import gzip
import json
import logging

import requests

from remarkable.config import project_root, target_path
from remarkable.plugins.zjh.util import clean_field_name


def customer_attribute(value):
    """
    返回的standard_attr也是经过clean_field_name处理的，
    在insert_into_db.py插入数据库时，将列名也clean之后做比对
    :param value:
    :return:
    """
    clean_value = clean_field_name(value)

    standard_attr = Knowledge.get_customer_subject_name(value) or Knowledge.get_customer_subject_name(clean_value)
    if (
        Knowledge.is_in_pass_subjects(value)
        or Knowledge.is_in_pass_subjects(clean_value)
        or Knowledge.is_in_pass_subjects(standard_attr)
    ):
        standard_attr = None
    return standard_attr, clean_value


class Knowledge:
    DATA_URL = "http://l.paodingai.com/1/knowledge/export/struct"  # with version
    SUBJECTS_DATA = None  # type: dict
    SUBJECTS_MAPPING = None  # type: dict
    LAST_UPDATE = "-"
    LOCAL_FILE = None
    EXTEND_PASS_SUBJECTS = {}

    # Knowledge standard subject -> Customer subject
    _hack_subjects = {
        # 资产负债表
        "总资产": "资产总计",
        "总负债": "负债合计",
        "预收账款": "预收款项",
        "其他综合收益": "所有者权益_其他综合收益",
        "其他权益工具": "所有者权益_其他权益工具",
        "永续债": "所有者权益_永续债",
        "优先股": "所有者权益_优先股",
        "卖出回购金融资产": "卖出回购金融资产款",
        # 利润表
        "汇兑净收益": "汇兑收益（损失以“-”号填列）",
        "公允价值变动损益": "加：公允价值变动收益（损失以“-”号填列）",
        "归属于母公司所有者的净利润": "(二)按所有权归属分类1.归属于母公司股东的净利润(净亏损以“-”号填列)",
        "综合收益": "综合收益总额",
        "归属于母公司所有者的综合收益": "归属于母公司所有者的综合收益总额",
        "归属母公司所有者权益": "归属于母公司所有者权益",
        # 现金流量表
        "质押委托贷款": "质押贷款净增加额",
        "筹资活动产生的现金流量净额": "筹资活动产生的现金流量",
        "投资活动产生的现金流量净额": "投资活动产生的现金流量",
        "经营活动产生的现金流量净额": "经营活动产生的现金流量",
        "现金及现金等价物净增加": "现金及现金等价物净增加额",
    }

    # Customer -> possible table field
    _customer_subjects_to_alias = {
        # 资产负债表
        "应收分保合同准备金": ["应收分保合同准备金"],
        "保险合同准备金": ["保险合同准备金"],
        "应收分保账款": ["应收分保账款"],
        "应收保费": ["应收保费"],
        "代理承销证券款": ["代理承销证券款"],
        "应付手续费及佣金": ["应付手续费及佣金"],
        "外币财务报表折算差额": ["外币报表折算差额", "外币财务报表折算差额", "外币报表折算差异"],
        "应付分保账款": ["应付分保账款"],
        "向中央银行借款": ["向中央银行借款"],
        "负债和所有者权益总计": ["负债及股东权益", "负债及所有者权益", "负债和股东/所有者权益", "负债和股东权益总计"],
        "一年内到期的非流动资产": ["一年内到期的非流动"],
        "资产总计": ["资产总额"],
        "负债合计": ["负债总额"],
        "所有者权益合计": ["股东权益总额"],
        "实收资本（或股本）": ["股本/实收资本"],
        "盈余公积": ["盈余公积/储备基金"],
        "财务费用": ["财务费用"],
        "所有者权益_永续债": ["非流动负债_永续债"],
        "所有者权益_优先股": ["非流动负债_优先股"],
        "应收票据及应收账款": ["应收账款及应收票据", "应收票据及应收款"],
        "应付票据及应付账款": ["应付票据及应付款项", "应付票据及应付款"],
        # 现金流量表
        "期末现金及现金等价物余额": ["年末现金及现金等价物余额", "期/年末现金及现金等价物余额", "年末现金及现金等价物"],
        "汇率变动对现金及现金等价物的影响": [
            "汇率变动对现金及现金等价物的影响",
            "汇率变动对现金的影响",
            "汇率变动对现金及现金等价物的影响额",
        ],
        "加：期初现金及现金等价物余额": [
            "加:年初现金及现金等价物余额",
            "加：年初现金及现金等价物余额",
            "期初现金及现金等价物余额",
            "期/年初现金及现金等价物余额",
            "期初现金及现金等价物的余额",
            "期初现金及现金等价物",
        ],
        "存放中央银行和同业款项净增加额": ["存放中央银行和同业款项净增加额", "存放中央银行及同业款项净增加额"],
        "经营活动产生的现金流量": ["经营活动(使用)/产生的现金流量净额", "经营活动产生/的现金流量净额"],
        "现金及现金等价物净增加额": [
            "现金及现金等价物净增加/(减少)额",
            "现金及现金等价物净增加/额",
            "现金及现金等价物净",
            "现金及现金等价物增加额",
        ],
        "投资活动产生的现金流量": ["投资活动产生/(使用)的现金流量净额", "投资活动产生的现"],
        "筹资活动产生的现金流量": [
            "筹资活动(使用)/产生的现金流量",
            "筹资活动(使用)/产生的现金流量净额",
            "筹资活动产生/的现金流量净额",
        ],
        "基本每股收益": ["基本每股收益", "基本每股收益（元/股）"],
        "处置子公司及其他营业单位收到的现金净额": [
            "处置子公司收回的现金",
            "处置子公司及其他营业单位收到的现金",
            "处置子公司收到的现金净额",
        ],
        "处置固定资产、无形资产和其他长期资产收回的现金净额": [
            "处置固定资产、油气资产、无形资产和其他长期资产收回的现金净额",
            "处置固定资产和无形资产收回的现金净额",
            "处置固定资产、无形资产和其他长期资产收回",
            "处置固定资产、无形资产和其他长期资产所收回的现金净额",
            "处置固定资产、无形资产和其他长期资产而收回的现金净额",
            "处置固定资产、无形资产和其他长期资产所收回的现金",
        ],
        "支付其他与经营活动有关的现金": ["支付的其他与经营活动有关的现金", "支付其他与经营活动有关的现"],
        "购建固定资产、无形资产和其他长期资产支付的现金": [
            "购建固定资产、油气资产、无形资产和其他长期资产支付的现金",
            "购建固定资产和无形资产支付的现金",
            "购置固定资产、无形资产和其他长期资产支付的现金",
        ],
        "加：公允价值变动收益（损失以“-”号填列）": ["公允价值变动净收益", "公允价值变动收益/", "公允价值变动损失"],
        "汇兑收益": ["汇兑/收益"],
        "收取利息、手续费及佣金的现金": ["收取利息、手续费及佣金收到的现金", "支付利息支出、手续费及佣金的现金"],
        "分配股利、利润或偿付利息支付的现金": [
            "分配股利或偿付利息支付的现金",
            "分配股利、利润或偿付利息支付的",
            "分配股利或偿付利息所支付的现金",
            "分配股利、利润或偿付利息支付现金",
            "分配股利、利润和偿付利息支付的现金",
        ],
        "筹资活动现金流入小计": ["筹资活动现金流入小"],
        "收回投资收到的现金": ["收回投资所收到的现金"],
        "收到其他与投资活动有关的现金": ["收到其他与投资活动有关的现金", "收到其他与投资活动有关的现"],
        "收到其他与经营活动有关的现金": [
            "收到其他与经营活动有关的现金",
            "收到的其他与经营活动",
            "收到的其他与经营活动有关的现",
            "收到其他与经营活动",
        ],
        "取得借款收到的现金": ["取得借款收到的现金", "借款所收到的现金"],
        "支付其他与投资活动有关的现金": ["支付其他与投资活动有关的现金", "支付其他与投资"],
        "销售商品、提供劳务收到的现金": ["销售商品、提供劳务收到的现金", "销售商品、提供更劳务收到的现金"],
        "支付给职工以及为职工支付的现金": ["支付给职工及为职工支付的现金"],
        "取得子公司及其他营业单位支付的现金净额": ["取得子公司及其他营业单位支付现金净额"],
        # 利润表
        "归属于母公司所有者的综合收益总额": ["归属于母公司股东的综合收益总额", "归属于母公司股东/所有者的综合收益总额"],
        "归属于母公司所有者权益合计": [
            "归属于母公司股东的所有者权益",
            "归属于母公司股东的所有者权益",
            "归属于母公司股东/所有者权益",
            "归属于母公司股东权",
            "股东/所有者权益",
            "归属于母公司所有权益",
            "归属于母公司股东权益合计",
        ],
        "归属于少数股东的综合收益总额": [],
        "营业收入": ["其中：营业收入"],
        "投资收益（损失以“-”号填列）": ["加：投资收益"],
        "手续费及佣金收入": ["手续费收入"],
        "管理费用": ["业务及管理费用"],
        "长期待摊费用": ["长摊待摊费用"],
        "其中：子公司支付给少数股东的股利、利润": ["子公司支付少数股东的现金股利"],
        "稀释每股收益": ["每股稀释收益"],
        "持续经营净利润": ["持续经净利润"],
    }

    pass_subjects = {
        "对联营企业的投资损失",
        "资产处置损失",
        "以后不能重分类进损益的其他综合收益",
        "归属于少数股东的其他综合收益",
        "重新计量设定受益计划净负债或净资产的变动",
        "权益法下在被投资单位不能重分类进损益的其他综合收益中享有的份额",
        "以后将重分类进损益的其他综合收益",
        "权益法下在被投资单位以后将重分类进损益的其他综合收益中享有的份额",
        "可供出售金融资产公允价值变动损益",
        "持有至到期投资重分类为可供出售金融资产损益",
        "外币财务",
        "现金流量套期损益的有效部分",
        "其他",
        "处置以公允价值计量且其变动计入当期损益的金融资产净增加额",
        "其他综合收益的税后净额",
        "归属母公司所有者的其他综合收益的税后净额",
        "归属母公司股东的其他综合收益的税后净额",
        "存出保证金",
        "期货会员投资资格",
        "应付货币保证金",
        "应付质押保证金",
        "期货风险准备金",
        "应付期货投资者保障基金",
        "应收货币保证金",
        "应收质押保证金",
        "应收结算担保金",
        "应收风险损失款",
        "提取期货风险准备金",
        "以现金支付的业务及管理费",
        "代理买卖证券支付的现金净额",
        "收回投资收到的现",
        "归属于母公司股东的",
        "现金及存放中央银行款项",
        "应收款项类投资",
        "同业及其他金融机构存放款项",
        "期货保证金存款",
        "期货会员资格投资",
        "提取期货风险准",
        "处置风险管理业务相关金融资产净增加额",
        "应收货币保证金及应收质押保证金净减少额",
        "应付货币保证金及应付质押保证金净增加额",
        "使用受限制的货币资金净减少额",
        "原始到期日三个月以上的定期存款净减少额",
        "支付利息及佣金的现金",
        "处置风险管理业务相关金融资产净减少额",
        "同一控制下企业合并支付的现金",
        "取得贷款收到的现金",
        "同一控制下企业合并前收到的资本投入",
        "公开发行股票收到的现金净额",
        "购买金融资产所支付的现金",
        "应收货币保证金及应收质押保证金净增加额",
        "应付货币保证金及应付质押保证金净减少额",
        "使用受限制的货币资金净增加额",
        "以现金支付的业务及管理费用",
        "以公允价值计量且变动计入当期损益的金融负债",
        "现金及现金等价物余额",
        "以后能重分类进损益的其他综合收益",
        "项目",
        "持续经营损益",
        "归属于母公司股东的其他综合收益的税后净额",
        "按经营持续性分类",
        "按所有权归属分类",
        "取得子公司及其他营业单位",
        "归属于少数股东的其他综合收益总额",
        "归属母公司所有者",
        "扣除非经常损益后归属于母公司股东的净利润",
        "归属少数股东的其他综合收益的税后净额",
        "贵金属",
        "存放同业及其他金融机构款项",
        "发放贷款及垫款，净额",
        "归属于本行股东权益",
        "归属于本行股东的净利润",
        "归属于本行股东的其他综合收益的税后净额以后将重分类进损益的其他综合收益-可供出售金融资产公允价值变动",
        "归属于本行股东的综合收益",
        "归属于少数股东的综合收益",
        "客户存款净增加额",
        "存放同业款项净减少额",
        "拆出资金净减少额",
        "同业及其他金融机构存入资金净增加额",
        "买入返售金融资产净减少额",
        "卖出回购金融资产净增加额",
        "同业及其他金融机构存入资金净减少额",
        "存放中央银行净增加额",
        "买入返售金融资产净增加额",
        "归属于母公司所有者",
        "吸收投资收到的",
        "取得投资收益及收回应收现金股利所收到的现金",
        "归属于母公司所有者的其他综合收益的税后净额—以后能重分类进损益的其他综合收益",
        "处置子公司及其他营业单位支付的现金",
        "非流动资产损毁报废损失",
        "非流动资产损毁报废利得",
        "收到的其他与",
        "拆入资金净减少额",
    }

    @classmethod
    def get_customer_subject_name(cls, alias, default=None, overdrive=False):
        name = cls.get_subjects_mapping().get(alias, default)
        if overdrive and name:
            name = clean_field_name(name)
        return name

    @classmethod
    def get_subjects_mapping(cls):
        if cls.SUBJECTS_MAPPING is None:
            cls.SUBJECTS_MAPPING = {}
            for _, attrs in cls.get_subjects().items():
                for attr in attrs:
                    cls.add_subjects_mapping(attr["name"], attr["nickname"])
            for std_attr, alias_list in cls.supplement_knowledge()["std_subjects_to_alias"].items():
                cls.add_subjects_mapping(std_attr, alias_list)

            for customer_subject, nicknames in cls.customer_subjects_to_alias().items():
                if not nicknames:
                    continue
                cls.SUBJECTS_MAPPING[customer_subject] = customer_subject
                for nickname in nicknames:
                    cls.SUBJECTS_MAPPING[nickname] = customer_subject

        return cls.SUBJECTS_MAPPING

    @classmethod
    def add_subjects_mapping(cls, std_attr, alias_list):
        origin_name = clean_field_name(std_attr)
        if origin_name in cls.hack_subjects():
            hack_name = cls.hack_subjects()[origin_name]
            cls.SUBJECTS_MAPPING[hack_name] = hack_name
            name = hack_name
        else:
            name = origin_name
        cls.SUBJECTS_MAPPING[origin_name] = name
        for alias in alias_list:
            cls.SUBJECTS_MAPPING[clean_field_name(alias)] = name

    @classmethod
    def reset(cls):
        cls.SUBJECTS_DATA = None  # type: dict
        cls.SUBJECTS_MAPPING = None  # type: dict

    @classmethod
    def last_update(cls, refresh=False):
        cls.get_subjects(refresh=refresh)
        return cls.LAST_UPDATE

    @classmethod
    def get_subjects(cls, refresh=False):
        if cls.SUBJECTS_DATA and not refresh:
            return cls.SUBJECTS_DATA
        data = cls.remote_subjects()
        if not data:
            raise ValueError("knowledge none")
        cls.SUBJECTS_DATA = data["data"]
        cls.LAST_UPDATE = data["last_update"]
        return cls.SUBJECTS_DATA

    @classmethod
    def remote_subjects(cls, refresh=False):
        if not refresh:
            return json.loads(gzip.open(f"{project_root}/data/tests/knowledge_struct.json.gz", "rt").read())
        try:
            response = requests.get(cls.DATA_URL, timeout=30)
            if response.status_code // 200 == 1:
                data = response.json()
                return data
        except Exception as e:
            logging.error("visit knowledge error: %s", e)
        return None

    @classmethod
    def is_in_pass_subjects(cls, subject):
        if not cls.EXTEND_PASS_SUBJECTS:
            pass_subjects = set(list(cls.pass_subjects) + cls.supplement_knowledge()["pass_subjects"])
            cls.EXTEND_PASS_SUBJECTS = {clean_field_name(item) for item in pass_subjects}

        return subject in cls.EXTEND_PASS_SUBJECTS

    @classmethod
    def hack_subjects(cls):
        return {clean_field_name(k): clean_field_name(v) for k, v in cls._hack_subjects.items()}

    @classmethod
    def customer_subjects_to_alias(cls):
        res = {}
        for customer_subject, alias in cls._customer_subjects_to_alias.items():
            alias = [clean_field_name(x) for x in alias]
            res[clean_field_name(customer_subject)] = alias
        return res

    @staticmethod
    def supplement_knowledge():
        path = target_path("data/zjh/knowledge_supplement.json")
        with open(path, "r") as _fp:
            data = json.load(_fp)
        return data
