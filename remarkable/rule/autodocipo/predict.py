import functools
import re
from collections import OrderedDict
from copy import deepcopy

from remarkable.common.util import clean_txt
from remarkable.predictor.predict import AnswerPredictor, CharResult, ResultOfPredictor, TblResult

FIRGUE, TERM = range(2)  # 规则类型（固定数值比对、固定条款比对）


class TermRule:
    def __init__(
        self,
        regs=None,
        limit=3,
        cnt_of_anchor_elts=3,
        anchor_reg=None,
        cnt_of_res=1,
        syllabus_reg=None,
        threshold=0.5,
        traverse_num=20,
    ):
        self.regs = regs if regs else []  # 关键词列表
        self.limit = limit  # 关键词最少满足个数
        self.anchor_reg = anchor_reg  # 定位元素块
        self.cnt_of_anchor_elts = cnt_of_anchor_elts  # 查找个数
        self.cnt_of_res = cnt_of_res  # 预测答案个数
        self.syllabus_reg = syllabus_reg
        self.threshold = threshold
        self.traverse_num = traverse_num


class CompletePredictor(AnswerPredictor):
    def __init__(self, *args, **kwargs):
        super(CompletePredictor, self).__init__(*args, **kwargs)
        self.sorted_elements = OrderedDict()
        self.schema_map = {
            "科创版-招股说明书-完整性检查-初步": Prospectus,
        }

        for idx, _ in sorted(self.reader.data["_index"].items(), key=lambda x: x[0]):
            typ, elt = self.reader.find_element_by_index(idx)
            self.sorted_elements.setdefault(idx, elt)
        if self.crude_answer:
            for schema_key, answers in self.crude_answer.items():
                self.column_analyzers.update(
                    {
                        schema_key: functools.partial(
                            self._process_crude,
                            answers,
                            self.schema_map[self.root_schema_name]().term_patterns[schema_key],
                        ),
                    }
                )
        else:
            if self.schema_map.get(self.root_schema_name):
                # 固定条款比对
                for attr, patterns in self.schema_map[self.root_schema_name]().term_patterns.items():
                    self.column_analyzers.update(
                        {
                            attr: functools.partial(self._term_label, TermRule(**patterns)),
                        }
                    )

    def _process_crude(self, answers, term_rule, **kwargs):
        items = []
        if answers and answers[0]["score"] > term_rule.get("threshold", 0.5):
            traverse_num = 0
            for answer in answers:
                next_flag = term_rule.get("traverse_num") and traverse_num < term_rule.get("traverse_num")
                if answer["score"] > term_rule.get("threshold", 0.5) or next_flag:
                    syllabus_dict = self.reader.syllabus_dict
                    element_index = answer["element_index"]
                    elt = self.sorted_elements[element_index]
                    syllabus_id = elt.get("syllabus", -1)
                    syllabus_reg = term_rule.get("syllabus_reg", None)

                    syllabus_ids = []
                    self.get_syllabus_id(syllabus_id, syllabus_ids)
                    syllabus_ids.insert(0, syllabus_id)

                    syllabus_titles = [
                        syllabus_dict.get(syllabus_id, {}).get("title", "") for syllabus_id in syllabus_ids
                    ]
                    syllabus_titles = {self.format_syllabus(syllabus_title) for syllabus_title in syllabus_titles}

                    if not syllabus_reg or any(
                        (syllabus_reg.search(syllabus_title) for syllabus_title in syllabus_titles)
                    ):
                        self.append_item_crude(elt, items)
                    traverse_num += 1
        items = sorted(items, key=lambda _elt: (_elt["page"], _elt["outline"][1]))
        data = [TblResult([], item) if item["class"] == "TABLE" else CharResult(item["chars"]) for item in items]
        if not data and term_rule.get("regs"):
            return self._term_label(TermRule(**term_rule))
        return ResultOfPredictor(data)

    @staticmethod
    def format_syllabus(syllabus_title):
        syllabus_title = re.sub(r"^[（）一二三四五六七八九十123456789]*、?\s?", "", syllabus_title)
        syllabus_title = re.sub(r"^第[一二三四五六七八九十]*节、?\s?|\s", "", syllabus_title)
        return syllabus_title

    def get_syllabus_id(self, _syllabus_id, _syllabus_ids):
        item = self.reader.syllabus_dict.get(_syllabus_id, {})
        parent_id = item.get("parent", -1)
        if parent_id == -1:
            return _syllabus_ids
        else:
            _syllabus_ids.append(parent_id)
            return self.get_syllabus_id(parent_id, _syllabus_ids)

    def b_aim_elt(self, elt_idx, rule):
        """
        是否为目标元素块
        """
        if rule.anchor_reg is None:
            return True
        for idx in range(elt_idx - rule.cnt_of_anchor_elts, elt_idx):
            elt = self.sorted_elements.get(idx)
            if elt:
                if rule.anchor_reg.search(elt.get("text", "")):
                    return True
        return False

    def fix_para_cross_pages(self, elt_idx):
        elt = deepcopy(self.sorted_elements.get(elt_idx, {}))
        if elt.get("continued"):
            for idx, ele in self.sorted_elements.items():
                if idx > elt_idx and ele["class"] == "PARAGRAPH":  # next_elt
                    elt["text"] += ele.get("text", "")
                    elt["chars"].extend(ele.get("chars", []))
                    elt["continued_elt"] = ele
                    break
        return elt

    def append_item_crude(self, elt, items):
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

    def _figue_label(self, rule, **kwargs):
        items = []
        for elt_idx, elt in self.sorted_elements.items():
            if elt["class"] != "PARAGRAPH":
                continue
            if elt.get("continued"):  # 跨页段落
                elt = self.fix_para_cross_pages(elt_idx)
            if not self.b_aim_elt(elt_idx, rule):
                continue

            elt_text = elt["text"]
            for reg in rule.regs:  # 不同的句式
                if reg.search(elt_text):
                    for item in reg.finditer(elt_text):
                        chars = elt["chars"][item.start("tar") : item.end("tar")]
                        if chars:
                            self.append_item(chars, items)
                            break
                if len(items) >= rule.cnt_of_res:
                    break
            if len(items) >= rule.cnt_of_res:
                break
        data = [CharResult(item) for item in items]
        return ResultOfPredictor(data)

    def _term_label(self, rule, **kwargs):
        items = []
        for elt_idx, elt in self.sorted_elements.items():
            if not rule.regs:
                break
            if not self.b_aim_elt(elt_idx, rule):
                continue
            if elt["class"] == "PARAGRAPH":
                if elt.get("continued"):  # 跨页段落
                    elt = self.fix_para_cross_pages(elt_idx)
                elt_text = clean_txt(elt["text"])
                cnt = 0  # 关键词的命中次数
                for reg in rule.regs:
                    if reg.search(elt_text):
                        # print('==============', elt_idx, reg.search(elt_text), elt_text)
                        cnt += 1
                if cnt >= rule.limit:
                    # print('*******', ''.join([x['text'] for x in elt['chars']]))
                    self.append_item_crude(elt, items)
                if len(items) >= rule.cnt_of_res:
                    break
            elif elt["class"] == "TABLE":
                cells = elt["cells"]
                cnt = 0  # 关键词的命中次数
                for cell in cells.values():
                    cell_text = clean_txt(cell["text"])
                    for reg in rule.regs:
                        if reg.search(cell_text):
                            cnt += 1
                    if cnt >= rule.limit:
                        self.append_item_crude(elt, items)
                        break
                if len(items) >= rule.cnt_of_res:
                    break
        items = sorted(items, key=lambda _elt: (_elt["page"], _elt["outline"][1]))
        data = [CharResult(item["chars"]) if item["class"] == "PARAGRAPH" else TblResult([], item) for item in items]
        return ResultOfPredictor(data)


class Prospectus:
    def __init__(self):
        self.firgue_patterns = {
            "合同总金额大写": {
                "regs": [
                    re.compile(r"合同总额[:：]?￥(.*?)[(（]大写[:：]?人民币(?P<tar>.*?)[）)]"),
                ]
            },
        }

        self.term_patterns = {
            "报告名称": {
                "regs": [
                    re.compile(r".*?公司$"),
                    re.compile(r"公开发行股票"),
                    re.compile(r"招股说明书"),
                    re.compile(r"申报稿"),
                ],
                "syllabus_reg": re.compile(r""),
                "limit": 1,
                "cnt_of_res": 4,
                "traverse_num": 3,
            },
            "发行人": {
                "regs": [
                    re.compile(r".*?股份有限公司"),
                    re.compile(r".*?Co., Ltd."),
                ],
                "syllabus_reg": re.compile(r""),
                "limit": 1,
                "cnt_of_res": 1,
                "threshold": 0.4,
            },
            "保荐人": {
                "regs": [
                    re.compile(r".*?证券(.*有限公司)?$"),
                    re.compile(r".*?LIMITED"),
                ],
                "syllabus_reg": re.compile(r""),
                "limit": 1,
                "cnt_of_res": 1,
                "threshold": 0.1,
            },
            "主承销商-名称": {
                "regs": [
                    re.compile(r".*?证券(.*有限公司)?$"),
                ],
                "syllabus_reg": re.compile(r""),
                "limit": 1,
                "cnt_of_res": 1,
                "threshold": 0.2,
            },
            "主承销商-住所": {
                "regs": [
                    re.compile(r"(中国（上海）自由贸易试验区)?.*?路?\d*号\d*层?"),
                ],
                "syllabus_reg": re.compile(r""),
                "limit": 1,
                "cnt_of_res": 1,
            },
            "科创版投资风险提示声明": {
                "regs": [
                    re.compile(
                        """
                    本次股票发行后拟在科创板市场上市，该市场具有较高的投资风险。
                    科创板公司具有研发投入大、经营风险高、业绩不稳定、退市风险高等特点，
                    投资者面临较大的市场风险。投资者应充分了解科创板市场的投资风险及本
                    公司所披露的风险因素，审慎作出投资决定。""",
                        re.X | re.I,
                    )
                ],
                "syllabus_reg": re.compile(r""),
                "limit": 1,
                "cnt_of_res": 1,
            },
            "扉页-声明": {
                "regs": [
                    re.compile(r"中国证监会、交易所对本次发行所做的任何决定或意见"),
                    re.compile(r"根据《证券法》的规定"),
                ],
                "syllabus_reg": re.compile(r""),
                "limit": 1,
                "cnt_of_res": 2,
            },
            "发行人声明": {
                "regs": [
                    re.compile(r"高级管理人员承诺招股说明书及其他信息披露资料不存在虚假记载"),
                    re.compile(r"实际控制人承诺本招股说明书不存在虚假记载"),
                    re.compile(r"会计机构负责人保证招股说明书中财务会计资料真实"),
                    re.compile(r"承诺因发行人招股说明书"),
                    re.compile(r"保荐人及证券服务机构承诺因其为发行人本次公开发行制作"),
                ],
                "syllabus_reg": re.compile(r""),
                "limit": 1,
                "cnt_of_res": 5,
            },
            "扉页-发行情况": {
                "regs": [
                    re.compile(r"每股发行价格"),
                    re.compile(r"发行后总股本"),
                    re.compile(r"每股面值"),
                    re.compile(r"发行股数"),
                    re.compile(r"招股说明书签署日期?"),
                    re.compile(r"拟上市的(证券)?交易所"),
                    re.compile(r"主承销商"),
                    re.compile(r"保荐(人|机构)"),
                    re.compile(r"预计发行日期"),
                    re.compile(r"发行股票类型"),
                ],
                "syllabus_reg": re.compile(r""),
                "limit": 1,
                "cnt_of_res": 10,
            },
            "需特别关注的重要事项": {
                "regs": [],
                "syllabus_reg": re.compile(r""),
                "limit": 1,
                "cnt_of_res": 1,
            },
            "提醒投资者认真阅读招股说明书正文内容": {
                "regs": [
                    re.compile(
                        """
                    本概览仅对招股说明书全文作扼要提示。投资者作出投资决策前，应认真阅
                    读招股说明书全文。""",
                        re.X | re.I,
                    )
                ],
                "syllabus_reg": re.compile(r""),
                "limit": 1,
                "cnt_of_res": 1,
                "threshold": 0.2,
            },
            "释义章节": {
                "regs": [],
                "syllabus_reg": re.compile(r"释义"),
                "limit": 1,
                "cnt_of_res": 1,
            },
            "概览-声明": {
                "regs": [
                    re.compile(
                        """
                    本概览仅对招股说明书全文做扼要提示。投资者作出投资决策前，应认真阅
                    读招股说明书全文。""",
                        re.X | re.I,
                    )
                ],
                "syllabus_reg": re.compile(r"概.*?览"),
                "limit": 1,
                "cnt_of_res": 1,
            },
            "概览-发行人基本情况": {
                "regs": [
                    re.compile(r"中文名称"),
                    re.compile(r"英文名称"),
                    re.compile(r"有限公司成立日期"),
                    re.compile(r"股份公司成立日期"),
                    re.compile(r"发行人名称"),
                    re.compile(r"发行人英文名称"),
                    re.compile(r"成立日期"),
                    re.compile(r"注册资本"),
                    re.compile(r"法定代表人"),
                    re.compile(r"注册地址"),
                    re.compile(r"主要生产经营地址"),
                    re.compile(r"控股股东"),
                    re.compile(r"实际控制人"),
                    re.compile(r"行业分类"),
                    re.compile(r"""在其他交易场所（申请）挂牌或上市的情况""", re.X | re.I),
                ],
                "syllabus_reg": re.compile(
                    r"中介机构|本次发行概况|普通术语|释义|发行人基本情况|发行人概况|当事人基本情况"
                ),
                "limit": 1,
                "cnt_of_res": 10,
            },
            "概览-中介机构": {
                "regs": [
                    re.compile(r"保荐人"),
                    re.compile(r"主承销商"),
                    re.compile(r"发行人律师"),
                    re.compile(r"联席主承销商"),
                    re.compile(r"其他承销机构"),
                    re.compile(r"资产评估复核机构"),
                    re.compile(r"保荐人（主承销商）律师"),
                    re.compile(r"审计机构"),
                    re.compile(r"评估机构"),
                    re.compile(r"验资机构"),
                ],
                "syllabus_reg": re.compile(r"中介机构|当事人基本情况"),
                "limit": 1,
                "cnt_of_res": 6,
            },
            "概览-本次发行基本情况": {
                "regs": [
                    re.compile(r"股票种类"),
                    re.compile(r"每股面值"),
                    re.compile(r"发行股数"),
                    re.compile(r"占发行后总股本比例"),
                    re.compile(r"其中：发行新股数量"),
                    re.compile(r"股东公开发售股份数量"),
                    re.compile(r"发行后总股本"),
                    re.compile(r"每股发行价格"),
                    re.compile(r"发行市盈率"),
                    re.compile(r"发行前每股净资产"),
                    re.compile(r"发行费用概算"),
                ],
                "syllabus_reg": re.compile(r"本次发行概况|本次发行的?(基本)?情况"),
                "limit": 1,
                "cnt_of_res": 11,
            },
            "概览-发行上市重要日期": {
                "regs": [
                    re.compile(r"刊登发行公告日期"),
                    re.compile(r"开始询价推介日期"),
                    re.compile(r"刊登定价公告日期"),
                    re.compile(r"申购日期和缴款日期"),
                    re.compile(r"股票上市日期"),
                ],
                "syllabus_reg": re.compile(r"发行上市的?重要日期|发行上市时间|本次发行概况"),
                "limit": 1,
                "cnt_of_res": 5,
            },
            "概览-主要财务数据和财务指标": {
                "regs": [
                    re.compile(r"资产总额（万元）"),
                    re.compile(r"归属于母公司所有者权益（万元）"),
                    re.compile(r"资产负债率（母公司）"),
                    re.compile(r"营业收入（万元）"),
                    re.compile(r"净利润（万元）"),
                    re.compile(r"归属于母公司所有者的净利润（万元）"),
                    re.compile(r"扣除非经常性损益后归属于母公司所有者的净利润（万元）"),
                    re.compile(r"基本每股收益（元）"),
                    re.compile(r"稀释每股收益（元）"),
                    re.compile(r"加权平均净资产收益率"),
                    re.compile(r"现金分红（万元）"),
                    re.compile(r"研发投入占营业收入的比例"),
                ],
                "syllabus_reg": re.compile(r"主要财务数据.*?财务指标|主要业务经营情况|主营业务"),
                "limit": 1,
                "cnt_of_res": 12,
            },
            "概览-主营业务经营情况-主要业务或产品": {
                "regs": [],
                "syllabus_reg": re.compile(r"主(营|要)业务(经营情况)?"),
                "limit": 1,
                "cnt_of_res": 1,
            },
            "概览-主营业务经营情况-主要经营模式": {
                "regs": [],
                "syllabus_reg": re.compile(r"主(营|要)业务(经营情况)?"),
                "limit": 1,
                "cnt_of_res": 1,
            },
            "概览-主营业务经营情况-竞争地位": {
                "regs": [],
                "syllabus_reg": re.compile(r"主(营|要)业务(经营情况)?"),
                "limit": 1,
                "cnt_of_res": 1,
            },
            "概览-技术先进性": {
                "regs": [],
                "syllabus_reg": re.compile(r"(发行人的)?(技术先进性|模式创新性)"),
                "limit": 1,
                "cnt_of_res": 1,
            },
            "概览-模式创新性": {
                "regs": [],
                "syllabus_reg": re.compile(r"(发行人的)?(模式创新性|技术先进性)|技术创新"),
                "limit": 1,
                "cnt_of_res": 1,
            },
            "概览-研发技术产业化情况": {
                "regs": [],
                "syllabus_reg": re.compile(r"(发行人|公司)?(研发)?技术产业化情况|技术创新|先进技术产业化"),
                "limit": 1,
                "cnt_of_res": 1,
            },
            "概览-未来发展战略": {
                "regs": [],
                "syllabus_reg": re.compile(r"战略|未来发展规划"),
                "limit": 1,
                "cnt_of_res": 1,
            },
            "概览-上市标准": {
                "regs": [],
                "syllabus_reg": re.compile(r"上市标准"),
                "limit": 1,
                "cnt_of_res": 1,
            },
            "概览-重要事项": {
                "regs": [],
                "syllabus_reg": re.compile(r"(发行人|公司)治理的?特殊安排"),
                "limit": 1,
                "cnt_of_res": 1,
            },
            "概览-募集资金用途": {
                "regs": [],
                "syllabus_reg": re.compile(r"募[集投]资金(的)?(主要)?(用途|使用|运用)|关联交易"),
                "limit": 1,
                "cnt_of_res": 1,
            },
            "发行概况-本次发行基本情况": {
                "regs": [
                    re.compile(r"股票种类"),
                    re.compile(r"每股面值"),
                    re.compile(r"发行股数"),
                    re.compile(r"每股发行价"),
                    re.compile(r"发行市盈率"),
                    re.compile(r"预测净利润"),
                    re.compile(r"发行市净率"),
                    re.compile(r"发行方式"),
                    re.compile(r"发行对象"),
                    re.compile(r"承销方式"),
                    re.compile(r"发行费用概算"),
                ],
                "syllabus_reg": re.compile(r"本次发行的?基本情况"),
                "limit": 1,
                "cnt_of_res": 10,
            },
            "发行概况-机构信息": {
                "regs": [
                    re.compile(r"发行人"),
                    re.compile(r"保荐(人|机构)"),
                    re.compile(r"主承销商"),
                    re.compile(r"联席承销商"),
                    re.compile(r"律师事务所"),
                    re.compile(r"会记事务所"),
                    re.compile(r"资产评估机构"),
                    re.compile(r"股票登记机构"),
                    re.compile(r"收款银行"),
                ],
                "syllabus_reg": re.compile(r"本次发行(的中介机构基本情况|概况)"),
                "limit": 1,
                "cnt_of_res": 6,
            },
            "发行概况-机构之间的股权关系或其他权益关系": {
                "regs": [re.compile(r"不存在直接或间接的股权关系或其他权益关系")],
                "syllabus_reg": re.compile(r"股权关系或其他权益关系|本次发行概况"),
                "limit": 1,
                "cnt_of_res": 1,
            },
            "发行概况-重要日期": {
                "regs": [
                    re.compile(r"股票上市日期"),
                    re.compile(r"刊登发行公告的?日期"),
                    re.compile(r"开始询价推介的?日期"),
                    re.compile(r"刊登定价公告的?日期"),
                    re.compile(r"申购日期"),
                    re.compile(r"缴款日期"),
                ],
                "syllabus_reg": re.compile(r"发行并?(上市)?的?(有关)?的?重要日期|发行上市时间|时间表|重要时间安排"),
                "limit": 1,
                "cnt_of_res": 5,
            },
            "技术风险": {
                "regs": [],
                "syllabus_reg": re.compile(r"技术风险|核心技术(及?先进性)?|公司经营(相关)?的?风险|研发风险|风险因素"),
                "limit": 1,
                "cnt_of_res": 1,
            },
            "经营风险": {
                "regs": [],
                "syllabus_reg": re.compile(r"经营风险|经销商管理风险|公司经营(相关)?的?风险|经营与研发风险|风险因素"),
                "limit": 1,
                "cnt_of_res": 1,
            },
            "内控风险": {
                "regs": [],
                "syllabus_reg": re.compile(r"内控风险|所处行业的?竞争|管理风险|兼职情况|风险因素"),
                "limit": 1,
                "cnt_of_res": 1,
            },
            "财务风险": {
                "regs": [],
                "syllabus_reg": re.compile(r"财务风险|公司经营(相关)?的?风险|风险因素"),
                "limit": 1,
                "cnt_of_res": 1,
            },
            "法律风险": {
                "regs": [],
                "syllabus_reg": re.compile(r"政策及监管风险|法律诉讼风险|风险因素"),
                "limit": 1,
                "cnt_of_res": 1,
            },
            "发行失败风险": {
                "regs": [],
                "syllabus_reg": re.compile(r"发行失败的?风险|风险因素"),
                "limit": 1,
                "cnt_of_res": 1,
            },
            "尚未盈利或存在累计未弥补亏损的风险": {
                "regs": [],
                "syllabus_reg": re.compile(r"风险|风险因素"),
                "limit": 1,
                "cnt_of_res": 1,
            },
            "特别表决权股份或类似公司治理特殊安排的风险": {
                "regs": [],
                "syllabus_reg": re.compile(r"风险|风险因素"),
                "limit": 1,
                "cnt_of_res": 1,
            },
            "可能严重影响公司持续经营的其他因素": {
                "regs": [],
                "syllabus_reg": re.compile(r"可能严重影响公司持续经营的其他因素|风险因素"),
                "limit": 1,
                "cnt_of_res": 1,
            },
            "风险对策": {
                "regs": [],
                "syllabus_reg": re.compile(r"风险|风险因素"),
                "limit": 1,
                "cnt_of_res": 1,
            },
            "发行人竞争优势": {
                "regs": [],
                "syllabus_reg": re.compile(r"发行人竞争优势"),
                "limit": 1,
                "cnt_of_res": 1,
            },
            "发行人基本信息": {
                "regs": [
                    re.compile(r"公司名称"),
                    re.compile(r"英文名称"),
                    re.compile(r"注册资本"),
                    re.compile(r"法定代表人"),
                    re.compile(r"有限公司成立日期"),
                    re.compile(r"股份公司设立日期"),
                    re.compile(r"住所"),
                    re.compile(r"邮政编码 "),
                    re.compile(r"联系电话 "),
                    re.compile(r"传真"),
                    re.compile(r"互联网地址"),
                    re.compile(r"邮箱"),
                    re.compile(r"负责信息披露和投资者关系的部门"),
                    re.compile(r"董事会办公室负责人"),
                    re.compile(
                        r"董事会办公室负责人电话号码",
                    ),
                ],
                "syllabus_reg": re.compile(r"(发行人|公司)基本(资料|情况|信息)"),
                "limit": 1,
                "cnt_of_res": 1,
            },
            "发行人设立情况": {
                "regs": [
                    re.compile(r"有限公司设立情况"),
                    re.compile(r"股份公司的?设立(方式|情况)?"),
                ],
                "syllabus_reg": re.compile(r"发行人股本.*情况|发行人基本情况"),
                "limit": 1,
                "cnt_of_res": 1,
            },
            "发行人报告期内股本和股东变化情况": {
                "regs": [],
                "syllabus_reg": re.compile(r"发行人(股|基)本.*?情况|股本和股东变化情况"),
                "limit": 1,
                "cnt_of_res": 1,
            },
            "发行人有限责任公司的设立情况": {
                "regs": [],
                "syllabus_reg": re.compile(r"发行人股本.*情况|设立情况|(有限公司|发行人)设立"),
                "limit": 1,
                "cnt_of_res": 1,
            },
            "发行人报告期内重大资产重组情况": {
                "regs": [re.compile(r"[未不](进行|存在|发生)过?重大资产重组")],
                "syllabus_reg": re.compile(r"在其他证券市场的上市.*?挂牌情况|重?[大要]?资产(及业务)?重组情况"),
                "limit": 1,
                "cnt_of_res": 1,
            },
            "在其他证券市场的上市/挂牌情况": {
                "regs": [],
                "syllabus_reg": re.compile(r"重大资产重组|在.*?挂牌|[境海]外红筹架构"),
                "limit": 1,
                "cnt_of_res": 1,
            },
            "股权结构图": {
                "regs": [],
                "syllabus_reg": re.compile(r"股[权东]结构图?|组织结构"),
                "limit": 1,
                "cnt_of_res": 1,
            },
            "发行人控股子公司及对发行人有重大影响的参股公司情况": {
                "regs": [],
                "syllabus_reg": re.compile(r"发行人.*?公司情况|发行人基本情况|公司基本情况"),
                "limit": 1,
                "cnt_of_res": 1,
            },
            "发行人其他参股公司的情况": {
                "regs": [],
                "syllabus_reg": re.compile(r"发行人.*?公司(情况)?|控股子?公司|参股子?公司"),
                "limit": 1,
                "cnt_of_res": 1,
            },
            "控股股东的基本情况-法人": {
                "regs": [],
                "syllabus_reg": re.compile(r"(控股)?股东.*?实际控制人|人员简介|控股股东基本情况|控股子公司"),
                "limit": 1,
                "cnt_of_res": 1,
            },
            "控股股东的基本情况-自然人": {
                "regs": [],
                "syllabus_reg": re.compile(r"(控股)?股东.*?实际控制人的?基本情况|人员简介|共同控股股东|实际控制人"),
                "limit": 1,
                "cnt_of_res": 1,
            },
            "控股股东的基本情况-非法人组织": {
                "regs": [],
                "syllabus_reg": re.compile(r"(控股)?股东.*?实际控制人的?基本情况|人员简介|共同控股股东"),
                "limit": 1,
                "cnt_of_res": 1,
            },
            "实际控制人的基本情况-法人": {
                "regs": [],
                "syllabus_reg": re.compile(r"(控股)?股东.*?实际控制人的?基本情况|人员简介|共同控股股东|实际控制人"),
                "limit": 1,
                "cnt_of_res": 1,
            },
            "实际控制人的基本情况-自然人": {
                "regs": [],
                "syllabus_reg": re.compile(r"(控股)?股东.*?实际控制人的?基本情况|人员简介|共同控股股东|实际控制人"),
                "limit": 1,
                "cnt_of_res": 1,
            },
            "实际控制人的基本情况-非法人组织": {
                "regs": [],
                "syllabus_reg": re.compile(r"(控股)?股东.*?实际控制人的?基本情况"),
                "limit": 1,
                "cnt_of_res": 1,
            },
            "控股股东和实际控制人直接或间接持有发行人的股份存在质押或其他有争议的情况": {
                "regs": [],
                "syllabus_reg": re.compile(r"质押或者?其他.*?争议的?情况|实际控制人.*?情况"),
                "limit": 1,
                "cnt_of_res": 1,
            },
            "是否有控股股东": {
                "regs": [],
                "syllabus_reg": re.compile(r""),
                "limit": 1,
                "cnt_of_res": 1,
            },
            "是否有实际控制人": {
                "regs": [],
                "syllabus_reg": re.compile(r""),
                "limit": 1,
                "cnt_of_res": 1,
            },
            "对发行人有重大影响的股东情况-法人": {
                "regs": [],
                "syllabus_reg": re.compile(r"股东.*?(情况)?"),
                "limit": 1,
                "cnt_of_res": 1,
            },
            "对发行人有重大影响的股东情况-自然人": {
                "regs": [],
                "syllabus_reg": re.compile(r"股东.*?(情况)?"),
                "limit": 1,
                "cnt_of_res": 1,
            },
            "对发行人有重大影响的股东情况-非法人组织": {
                "regs": [],
                "syllabus_reg": re.compile(r"股东.*?(情况)?"),
                "limit": 1,
                "cnt_of_res": 1,
            },
            "主要股东的基本情况-法人": {
                "regs": [],
                "syllabus_reg": re.compile(r"主要股东.*?(情况)?|控股股东|发行人股本|股东情况"),
                "limit": 1,
                "cnt_of_res": 1,
            },
            "主要股东的基本情况-自然人": {
                "regs": [],
                "syllabus_reg": re.compile(r"主要股东.*?(情况)?|控股股东|发行人股本"),
                "limit": 1,
                "cnt_of_res": 1,
            },
            "主要股东的基本情况-非法人组织": {
                "regs": [],
                "syllabus_reg": re.compile(r"主要股东.*?(情况)?|控股股东"),
                "limit": 1,
                "cnt_of_res": 1,
            },
            "本次发行前的总股本": {
                "regs": [],
                "syllabus_reg": re.compile(r"(发行人)?(股本情况|股权结构|股本变化)"),
                "limit": 1,
                "cnt_of_res": 1,
            },
            "本次发行及公开发售的股份及占比": {
                "regs": [],
                "syllabus_reg": re.compile(r"(发行人)?(股本情况|股权结构|股本变化)"),
                "limit": 1,
                "cnt_of_res": 1,
            },
            "本次发行的前十名股东": {
                "regs": [],
                "syllabus_reg": re.compile(r"前十大?.*?股东"),
                "limit": 1,
                "cnt_of_res": 1,
            },
            "本次发行前的前十名自然人股东情况": {
                "regs": [],
                "syllabus_reg": re.compile(r"前十大?.*?自然人股东|前十名股东|自然人股东"),
                "limit": 1,
                "cnt_of_res": 1,
            },
            "国有股份数量": {
                "regs": [],
                "syllabus_reg": re.compile(r""),
                "limit": 1,
                "cnt_of_res": 1,
            },
            "国有股份情况": {
                "regs": [],
                "syllabus_reg": re.compile(r""),
                "limit": 1,
                "cnt_of_res": 1,
            },
            "外资股份数量": {
                "regs": [],
                "syllabus_reg": re.compile(r""),
                "limit": 1,
                "cnt_of_res": 1,
            },
            "外资股份情况": {
                "regs": [],
                "syllabus_reg": re.compile(r""),
                "limit": 1,
                "cnt_of_res": 1,
            },
            "最近一年发行人新增股东情况": {
                "regs": [],
                "syllabus_reg": re.compile(
                    r"最近一年(发行人)?新增股东.*?情况|新增股东|股东及实际控制人基本情况|股本情况"
                ),
                "limit": 1,
                "cnt_of_res": 1,
            },
            "本次发行前各股东间的关联关系情况": {
                "regs": [],
                "syllabus_reg": re.compile(r"(发行人|公司)?各?股东之?间?的?关联关系(及各?关联股东的?各?自?持股比例)?"),
                "limit": 1,
                "cnt_of_res": 1,
            },
            "发行人股东公开发售股份的影响": {
                "regs": [],
                "syllabus_reg": re.compile(r"(发行人)?(股东)?公开发售股份(的情况)?|发行人公开发售"),
                "limit": 1,
                "cnt_of_res": 1,
            },
            "提示投资者关注股东公开发售股份事项": {
                "regs": [],
                "syllabus_reg": re.compile(r""),
                "limit": 1,
                "cnt_of_res": 1,
            },
            "董事的简要情况": {
                "regs": [],
                "syllabus_reg": re.compile(
                    r"董事|(人员|董事)简介|人员的?(简要)?情况|董事.*?控制.*?企业|.*?与公司的?关联关系|不?存在的?近?亲属关系|兼职情况|实际控制人"
                ),
                "limit": 1,
                "cnt_of_res": 1,
            },
            "监事的简要情况": {
                "regs": [],
                "syllabus_reg": re.compile(
                    r"监事|(人员|监事)简介|人员的?(简要)?情况|.*?与公司的?关联关系|亲属关系|兼职情况"
                ),
                "limit": 1,
                "cnt_of_res": 1,
            },
            "高级管理人员的简要情况": {
                "regs": [],
                "syllabus_reg": re.compile(
                    r"高级管理人员|人员简介|人员的?(简要)?情况|.*?与公司的?关联关系|不?存在的?近?亲属关系|兼职情况"
                ),
                "limit": 1,
                "cnt_of_res": 1,
            },
            "核心技术人员的简要情况": {
                "regs": [],
                "syllabus_reg": re.compile(r"核心(技术)?人员(简[介要])?"),
                "limit": 1,
                "cnt_of_res": 1,
            },
            "董事签定协议情况": {
                "regs": [],
                "syllabus_reg": re.compile(
                    r"与?(发行人|公司)?与?.*?签[订定署].*?协议|协议及履行情况|简要情况|有关协议|重要承诺"
                ),
                "limit": 1,
                "cnt_of_res": 1,
            },
            "监事签定协议情况": {
                "regs": [],
                "syllabus_reg": re.compile(
                    r"与?(发行人|公司)?与?.*?签[订定署].*?协议|协议及履行情况|简要情况|有关协议|重要承诺"
                ),
                "limit": 1,
                "cnt_of_res": 1,
            },
            "高级管理人员签定协议情况": {
                "regs": [],
                "syllabus_reg": re.compile(
                    r"与?(发行人|公司)?与?.*?签[订定署].*?协议|协议及履行情况|简要情况|有关协议|重要承诺"
                ),
                "limit": 1,
                "cnt_of_res": 1,
            },
            "核心技术人员签定协议情况": {
                "regs": [],
                "syllabus_reg": re.compile(
                    r"与?(发行人|公司)?与?.*?签[订定署].*?协议|协议及履行情况|简要情况|有关协议|重要承诺"
                ),
                "limit": 1,
                "cnt_of_res": 1,
            },
            "董事所持股份受限情况": {
                "regs": [],
                "syllabus_reg": re.compile(r"所持股份.*?情[形|况]|人员所持股份|人员作出的重要承诺"),
                "limit": 1,
                "cnt_of_res": 1,
            },
            "监事所持股份受限情况": {
                "regs": [],
                "syllabus_reg": re.compile(r"所持股份.*?情形[形|况]|人员所持股份|人员作出的重要承诺|技术人员情况简介"),
                "limit": 1,
                "cnt_of_res": 1,
            },
            "高级管理人员所持股份受限情况": {
                "regs": [],
                "syllabus_reg": re.compile(r"所持股份.*?情[形|况]|人员所持股份|人员作出的重要承诺"),
                "limit": 1,
                "cnt_of_res": 1,
            },
            "核心技术人员所持股份受限情况": {
                "regs": [],
                "syllabus_reg": re.compile(r"所持股份.*?情[形|况]|人员所持股份|人员作出的重要承诺"),
                "limit": 1,
                "cnt_of_res": 1,
            },
            "最近2年董事变动情况": {
                "regs": [],
                "syllabus_reg": re.compile(r"董事的?.*?变动情况|人员的?简要情况|董事.*?控制.*?企业|关联自然人"),
                "limit": 1,
                "cnt_of_res": 1,
            },
            "最近2年监事变动情况": {
                "regs": [],
                "syllabus_reg": re.compile(r"监事的?.*?变动情况|人员的?简要情况"),
                "limit": 1,
                "cnt_of_res": 1,
            },
            "最近2年高级管理人员变动情况": {
                "regs": [],
                "syllabus_reg": re.compile(r"高级管理人员的?.*?变动情况"),
                "limit": 1,
                "cnt_of_res": 1,
            },
            "最近2年核心技术人员变动情况": {
                "regs": [],
                "syllabus_reg": re.compile(r"核心技术人员的?.*?变动情况|核心人员的薪酬领取"),
                "limit": 1,
                "cnt_of_res": 1,
            },
            "董监高技与发行人极其业务相关的对外投资情况": {
                "regs": [],
                "syllabus_reg": re.compile(r"对?外投资|发行人董事、监事、高级管理人员及核心技术人员"),
                "limit": 1,
                "cnt_of_res": 1,
            },
            "董事亲属持股情况": {
                "regs": [],
                "syllabus_reg": re.compile(r"亲属持股情况|(近?亲属|间接)持有(发行人|公司)股份|发行人基本情况"),
                "limit": 1,
                "cnt_of_res": 1,
            },
            "监事亲属持股情况": {
                "regs": [],
                "syllabus_reg": re.compile(r"亲属持股情况|(近?亲属|间接)持有(发行人|公司)股份|发行人基本情况"),
                "limit": 1,
                "cnt_of_res": 1,
            },
            "高级管理人员亲属持股情况": {
                "regs": [],
                "syllabus_reg": re.compile(r"亲属持股情况|(近?亲属|间接)持有(发行人|公司)股份|发行人基本情况"),
                "limit": 1,
                "cnt_of_res": 1,
            },
            "核心技术人员亲属持股情况": {
                "regs": [],
                "syllabus_reg": re.compile(r"亲属持股情况|(近?亲属|间接)持有(发行人|公司)股份|发行人基本情况"),
                "limit": 1,
                "cnt_of_res": 1,
            },
            "薪酬组成": {
                "regs": [],
                "syllabus_reg": re.compile(r"薪酬(组成|情况|政策)|领薪情况"),
                "limit": 1,
                "cnt_of_res": 1,
            },
            "确定依据": {
                "regs": [],
                "syllabus_reg": re.compile(r"确定依据|发行人基本情况"),
                "limit": 1,
                "cnt_of_res": 1,
            },
            "履行程序": {
                "regs": [],
                "syllabus_reg": re.compile(r"履行的?程序"),
                "limit": 1,
                "cnt_of_res": 1,
            },
            "薪酬总额情况": {
                "regs": [],
                "syllabus_reg": re.compile(r"薪酬(总额|情况|组成)|领取收入|领薪情况"),
                "limit": 1,
                "cnt_of_res": 1,
            },
            "最近一年从发行人及其关联企业领取收入的情况": {
                "regs": [],
                "syllabus_reg": re.compile(r"薪酬情况|领取收入|领薪情况|薪酬组成"),
                "limit": 1,
                "cnt_of_res": 1,
            },
            "所享受的其他待遇和退休金计划": {
                "regs": [],
                "syllabus_reg": re.compile(r"薪酬情况|领取收入|领薪情况|薪酬组成"),
                "limit": 1,
                "cnt_of_res": 1,
            },
            "股权激励及相关安排": {
                "regs": [],
                "syllabus_reg": re.compile(r"股权激励|股份支付的执行情况|技术人员的薪酬情况"),
                "limit": 1,
                "cnt_of_res": 1,
            },
            "员工人数及报告期内的变化情况": {
                "regs": [],
                "syllabus_reg": re.compile(r"员工人数|员工情况|社会保障"),
                "limit": 1,
                "cnt_of_res": 1,
            },
            "员工专业结构": {
                "regs": [],
                "syllabus_reg": re.compile(r"员工(专业)?结构|发行人员工情况|职工基本情况|员工人数|专业(结构|构成)"),
                "limit": 1,
                "cnt_of_res": 1,
            },
            "报告期内社会保险和注方公积金缴纳情况": {
                "regs": [],
                "syllabus_reg": re.compile(r"社会保[险障](情况)?|员工构成"),
                "limit": 1,
                "cnt_of_res": 1,
            },
            "主营业务、主要产品或服务的基本情况": {
                "regs": [],
                "syllabus_reg": re.compile(r"主营业务"),
                "limit": 1,
                "cnt_of_res": 1,
            },
            "主营业务收入的主要构成": {
                "regs": [],
                "syllabus_reg": re.compile(r"主营业务(收入)?"),
                "limit": 1,
                "cnt_of_res": 1,
            },
            "主要经营模式": {
                "regs": [],
                "syllabus_reg": re.compile(r"经营模式|主营业务|服务模式|主要业务"),
                "limit": 1,
                "cnt_of_res": 1,
            },
            "采用目前经营模式的原因": {
                "regs": [],
                "syllabus_reg": re.compile(r"经营模式"),
                "limit": 1,
                "cnt_of_res": 1,
            },
            "影响经营模式的关键因素": {
                "regs": [],
                "syllabus_reg": re.compile(r"经营模式|经营发展的影响"),
                "limit": 1,
                "cnt_of_res": 1,
            },
            "经营模式和影响因素在报告期内的变化情况及未来变化趋势": {
                "regs": [],
                "syllabus_reg": re.compile(r"经营模式|经营发展的影响"),
                "limit": 1,
                "cnt_of_res": 1,
            },
            "业务及其模式的独特性、创新内容及持续创新机制": {
                "regs": [],
                "syllabus_reg": re.compile(r""),
                "limit": 1,
                "cnt_of_res": 1,
            },
            "设立以来主营业务、主要产品或服务、主要经营模式的演变情况": {
                "regs": [],
                "syllabus_reg": re.compile(r"主营业务"),
                "limit": 1,
                "cnt_of_res": 1,
            },
            "主要产品的工艺流程图或服务的流程图": {
                "regs": [],
                "syllabus_reg": re.compile(r"(工艺|服务|产品)的?流程|业务流程|设计研发流程|生产流程图"),
                "limit": 1,
                "cnt_of_res": 1,
            },
            "生产经营中涉及的主要环境污染物、主要处理设施及处理能力": {
                "regs": [],
                "syllabus_reg": re.compile(r"主要环境污染物|质量控制|环境保护情况|环保情况|安全生产情况"),
                "limit": 1,
                "cnt_of_res": 1,
            },
            "所属行业情况": {
                "regs": [],
                "syllabus_reg": re.compile(r"(所处)?行业的?(基本情况|竞争情况)|所属行业|专业术语"),
                "limit": 1,
                "cnt_of_res": 1,
            },
            "行业主管部门": {
                "regs": [],
                "syllabus_reg": re.compile(r"(行业)?(主管|管理)部门|行业监管体制"),
                "limit": 1,
                "cnt_of_res": 1,
            },
            "行业监管体制": {
                "regs": [],
                "syllabus_reg": re.compile(r"(行业)?(监管|管理)(体制|制度|机制|体系)"),
                "limit": 1,
                "cnt_of_res": 1,
            },
            "行业主要法律法规政策": {
                "regs": [],
                "syllabus_reg": re.compile(
                    r"(行业主要)?(法规政策|法律法规[和与]?(政策)?)|国家产业政策|行业政策|行业主要政策|行业监管体制"
                ),
                "limit": 1,
                "cnt_of_res": 1,
            },
            "行业主要法律法规政策对发行人经营发展的影响": {
                "regs": [],
                "syllabus_reg": re.compile(
                    r"法规政策|相关政策法规|国家产业政策|固定资产|无形资产|法律法规|行业政策及法规|对发行人经营发展的影响"
                ),
                "limit": 1,
                "cnt_of_res": 1,
            },
            "所属行业近三年的发展情况": {
                "regs": [],
                "syllabus_reg": re.compile(
                    r"发展(情况|趋势)|所处行业的?基本情况|行业竞争情况|行业基本情况|发行人竞争状况"
                ),
                "limit": 1,
                "cnt_of_res": 1,
            },
            "所属行业未来发展趋势": {
                "regs": [],
                "syllabus_reg": re.compile(r"发展(情况|趋势)|所处行业的?基本情况|所处行业竞争状况"),
                "limit": 1,
                "cnt_of_res": 1,
            },
            "发行人取得的科技成果与产业深度融合的具体情况": {
                "regs": [],
                "syllabus_reg": re.compile(r"产业深度融合|无形资产|专利|软件著作权|科技成果|产业融合"),
                "limit": 1,
                "cnt_of_res": 1,
            },
            "发行人产品或服务的市场地位": {
                "regs": [],
                "syllabus_reg": re.compile(r"市场地位|行业竞争|发行人所处行业基本情况|竞争地位"),
                "limit": 1,
                "cnt_of_res": 1,
            },
            "发行人产品或服务的技术水平及特点": {
                "regs": [],
                "syllabus_reg": re.compile(
                    r"技术水平[及与]((技术)?特点|行业特征)|发行人的?市场地位|行业主要特点|产品技术水平|竞争地位"
                ),
                "limit": 1,
                "cnt_of_res": 1,
            },
            "行业内的主要企业": {
                "regs": [],
                "syllabus_reg": re.compile(
                    r"行业内的?主要企业|同行业其他企业情况|行业中的市场地位|竞争对手|行业竞争格局|竞争地位|主要企业|行业竞争状况|行业地位分析"
                ),
                "limit": 1,
                "cnt_of_res": 1,
            },
            "竞争优势与劣势": {
                "regs": [],
                "syllabus_reg": re.compile(r"优势|劣势"),
                "limit": 1,
                "cnt_of_res": 1,
            },
            "行业发展态势": {
                "regs": [],
                "syllabus_reg": re.compile(r"行业发展(态势|情况|概况|趋势)|所处行业情况|行业竞争态势"),
                "limit": 1,
                "cnt_of_res": 1,
            },
            "面临的机遇与挑战": {
                "regs": [],
                "syllabus_reg": re.compile(r"行业发展态势|面临的?机遇|发展机遇|挑战|不利因素|有利因素"),
                "limit": 1,
                "cnt_of_res": 1,
            },
            "所属行业情况在报告期内的变化": {
                "regs": [],
                "syllabus_reg": re.compile(r"行业发展态势|可预见的?变化趋势|未来(发展)?趋势"),
                "limit": 1,
                "cnt_of_res": 1,
            },
            "所属行业情况未来可预见的变化趋势": {
                "regs": [],
                "syllabus_reg": re.compile(r"行业发展态势|可预见的?变化趋势|未来(发展)?趋势"),
                "limit": 1,
                "cnt_of_res": 1,
            },
            "发行人与同行业可比公司比较情况": {
                "regs": [],
                "syllabus_reg": re.compile(
                    r"同行业可比公司的?(比较)?(情况|分析)?|所处行业的基本情况及竞争状况|发行人市场竞争|发行人与行业内主要企业"
                    r"|发行人与同业公司的比较情况|行业内主要企业以及与发行人的比较情况"
                ),
                "limit": 1,
                "cnt_of_res": 1,
            },
            "主要产品或服务的规模": {
                "regs": [],
                "syllabus_reg": re.compile(r"主要产品|公司治理与独立|产量及销量情况"),
                "limit": 1,
                "cnt_of_res": 1,
            },
            "主要产品或服务的销售收入": {
                "regs": [],
                "syllabus_reg": re.compile(r"销售收入|销售情况"),
                "limit": 1,
                "cnt_of_res": 1,
            },
            "主要产品或服务的主要客户群体": {
                "regs": [],
                "syllabus_reg": re.compile(r"主要客户(群体)?|销售情况"),
                "limit": 1,
                "cnt_of_res": 1,
            },
            "主要产品或服务的销售价格": {
                "regs": [],
                "syllabus_reg": re.compile(r"售价|销售情况"),
                "limit": 1,
                "cnt_of_res": 1,
            },
            "销售模式情况": {
                "regs": [],
                "syllabus_reg": re.compile(r"销售模式|销售情况|营销模式|经销模式|经营模式"),
                "limit": 1,
                "cnt_of_res": 1,
            },
            "向前五名客户销售情况": {
                "regs": [],
                "syllabus_reg": re.compile(r"主要客户(群体)?|关联关系|关联交易|前五大客户"),
                "limit": 1,
                "cnt_of_res": 1,
            },
            "向单个客户销售比例超过总额50%的情况": {
                "regs": [],
                "syllabus_reg": re.compile(r"主要客户(群体)?|关联关系|关联交易|前五大客户"),
                "limit": 1,
                "cnt_of_res": 1,
            },
            "前五名客户中存在新增客户的情况": {
                "regs": [],
                "syllabus_reg": re.compile(r"前五[名大]客户|主要客户(群体)?|发行人关联方"),
                "limit": 1,
                "cnt_of_res": 1,
            },
            "前五名客户中存在严重依赖于少数客户的情况": {
                "regs": [],
                "syllabus_reg": re.compile(r"(前五[名大]客户)|主要客户(群体)?|发行人关联方"),
                "limit": 1,
                "cnt_of_res": 1,
            },
            "发行人关联方客户情况": {
                "regs": [],
                "syllabus_reg": re.compile(r"主要客户(群体)?"),
                "limit": 1,
                "cnt_of_res": 1,
            },
            "采购情况": {
                "regs": [],
                "syllabus_reg": re.compile(r"采购(情况|产品)|供应商(情况)?|原材料.*?供应情况"),
                "limit": 1,
                "cnt_of_res": 1,
            },
            "向前五名供应商采购情况": {
                "regs": [],
                "syllabus_reg": re.compile(r"采购情况|供应商(情况)?|关联关系|关联交易"),
                "limit": 1,
                "cnt_of_res": 1,
            },
            "向单个客供应商的采购比例超过总额的50%的情况": {
                "regs": [],
                "syllabus_reg": re.compile(r"采购情况|供应商情况"),
                "limit": 1,
                "cnt_of_res": 1,
            },
            "前五名供应商中存在新增供应商的情况": {
                "regs": [],
                "syllabus_reg": re.compile(r"采购情况|供应商情况|关联交易"),
                "limit": 1,
                "cnt_of_res": 1,
            },
            "前五名供应商中存在严重依赖于少数供应商的情况": {
                "regs": [],
                "syllabus_reg": re.compile(r"采购情况|供应商情况"),
                "limit": 1,
                "cnt_of_res": 1,
            },
            "固定资产构成": {
                "regs": [],
                "syllabus_reg": re.compile(r"固定资产|生产经营场所|主要资产|募集资金(运用|投资)"),
                "limit": 1,
                "cnt_of_res": 1,
            },
            "固定资产与所提供产品或服务的内在联系": {
                "regs": [],
                "syllabus_reg": re.compile(r"固定资产|主要资产"),
                "limit": 1,
                "cnt_of_res": 1,
            },
            "固定资产是否存在瑕疵、纠纷和潜在纠纷": {
                "regs": [],
                "syllabus_reg": re.compile(r"固定资产"),
                "limit": 1,
                "cnt_of_res": 1,
            },
            "固定资产是否对发行人持续经营存在重大不利影响": {
                "regs": [],
                "syllabus_reg": re.compile(r"固定资产"),
                "limit": 1,
                "cnt_of_res": 1,
            },
            "无形资产构成": {
                "regs": [],
                "syllabus_reg": re.compile(r""),
                "limit": 1,
                "cnt_of_res": 1,
            },
            "无形资产与所提供产品或服务的内在联系": {
                "regs": [],
                "syllabus_reg": re.compile(r"无形资产"),
                "limit": 1,
                "cnt_of_res": 1,
            },
            "无形资产是否存在瑕疵、纠纷和潜在纠纷": {
                "regs": [],
                "syllabus_reg": re.compile(r"无形资产"),
                "limit": 1,
                "cnt_of_res": 1,
            },
            "无形资产是否对发行人持续经营存在重大不利影响": {
                "regs": [],
                "syllabus_reg": re.compile(r"无形资产"),
                "limit": 1,
                "cnt_of_res": 1,
            },
            "发行人与他人共享资源要素情况": {
                "regs": [],
                "syllabus_reg": re.compile(r"无形资产"),
                "limit": 1,
                "cnt_of_res": 1,
            },
            "核心技术": {
                "regs": [],
                "syllabus_reg": re.compile(r"核心技术"),
                "limit": 1,
                "cnt_of_res": 1,
            },
            "技术来源": {
                "regs": [],
                "syllabus_reg": re.compile(r"技术来源|核心技术"),
                "limit": 1,
                "cnt_of_res": 1,
            },
            "技术先进性及具体特征": {
                "regs": [],
                "syllabus_reg": re.compile(r"核心技术|具体特征|技术先进性|在研技术的先进性分析"),
                "limit": 1,
                "cnt_of_res": 1,
            },
            "核心技术是否取得专利": {
                "regs": [],
                "syllabus_reg": re.compile(r"核心技术|技术先进性"),
                "limit": 1,
                "cnt_of_res": 1,
            },
            "核心技术的其他技术保护措施": {
                "regs": [],
                "syllabus_reg": re.compile(r"核心技术"),
                "limit": 1,
                "cnt_of_res": 1,
            },
            "核心技术在主营业务及产品或服务中的应用和贡献情况": {
                "regs": [],
                "syllabus_reg": re.compile(r"核心技术"),
                "limit": 1,
                "cnt_of_res": 1,
            },
            "核心技术的科研实力": {
                "regs": [],
                "syllabus_reg": re.compile(r"核心技术的(科研实力|成果情况)|核心技术|研发|技术水平"),
                "limit": 1,
                "cnt_of_res": 1,
            },
            "核心技术的成果情况": {
                "regs": [],
                "syllabus_reg": re.compile(r"核心技术|科研实力|[研开]发情况|技术水平|科技成果与产业融合"),
                "limit": 1,
                "cnt_of_res": 1,
            },
            "正在从事的研发项目情况": {
                "regs": [],
                "syllabus_reg": re.compile(r"研发的?项目|科研项目|[研开]发情况|在研项目|科研情况"),
                "limit": 1,
                "cnt_of_res": 1,
            },
            "科研项目与行业技术水平的比较": {
                "regs": [],
                "syllabus_reg": re.compile(r"研发项目|科研项目|技术水平|研发情况"),
                "limit": 1,
                "cnt_of_res": 1,
            },
            "研发投入构成情况": {
                "regs": [],
                "syllabus_reg": re.compile(r"研发投入|研发费用|技术水平|研发支出"),
                "limit": 1,
                "cnt_of_res": 1,
            },
            "合作研发情况": {
                "regs": [],
                "syllabus_reg": re.compile(r"合作研发|同行业可比公司|研究开发"),
                "limit": 1,
                "cnt_of_res": 1,
            },
            "核心技术相关人员情况": {
                "regs": [],
                "syllabus_reg": re.compile(r"(核心)?(研发|技术)人员|技术与研发情况|研发团队建设"),
                "limit": 1,
                "cnt_of_res": 1,
            },
            "核心技术人员的学历背景构成": {
                "regs": [],
                "syllabus_reg": re.compile(
                    r"(研发|技术)(人员)?(储备)?情况|主要固定资产和无形资产|人员简介|核心技术人员"
                ),
                "limit": 1,
                "cnt_of_res": 1,
            },
            "取得的专业资质及重要科研成果和获得奖项情况": {
                "regs": [],
                "syllabus_reg": re.compile(r"(研发|技术)(人员)?情况|人员简介|特许经营权|资质情况"),
                "limit": 1,
                "cnt_of_res": 1,
            },
            "对公司研发的具体贡献": {
                "regs": [],
                "syllabus_reg": re.compile(r"(研发|技术)(人员)?情况"),
                "limit": 1,
                "cnt_of_res": 1,
            },
            "发行人对核心技术人员实施的约束激励措施": {
                "regs": [],
                "syllabus_reg": re.compile(r"(研发|技术)(人员)?情况|研发创新机制|约束激励措施"),
                "limit": 1,
                "cnt_of_res": 1,
            },
            "报告期内核心技术人员的主要变动情况": {
                "regs": [],
                "syllabus_reg": re.compile(r"(研发|技术)(人员)?情况|关联交易|人员简介"),
                "limit": 1,
                "cnt_of_res": 1,
            },
            "报告期内核心技术人员的主要变动情况对发行人的影响": {
                "regs": [],
                "syllabus_reg": re.compile(r"(研发|技术)(人员)?情况|关联交易|人员简介"),
                "limit": 1,
                "cnt_of_res": 1,
            },
            "保持技术不断创新的机制、技术储备及技术创新的安排": {
                "regs": [],
                "syllabus_reg": re.compile(r"技术创新机制|研发创新机制|创新激励机制|创新的?机制|技术储备|技术创新体制"),
                "limit": 1,
                "cnt_of_res": 1,
            },
            "境外生产经营的总体情况": {
                "regs": [],
                "syllabus_reg": re.compile(
                    r"境外经营.*?情况|境外生产经营|境外控股子公司|境外进行生产经营情况|发行人基本情况|境外资产"
                ),
                "limit": 1,
                "cnt_of_res": 1,
            },
            "境外生产经营业务活动的地域性分析": {
                "regs": [],
                "syllabus_reg": re.compile(r"境外经营.*?情况|境外生产经营情况|发行人基本情况|境外资产"),
                "limit": 1,
                "cnt_of_res": 1,
            },
            "境外资产情况": {
                "regs": [],
                "syllabus_reg": re.compile(r"境外经营.*?情况|境外生产经营情况|发行人基本情况|境外资产"),
                "limit": 1,
                "cnt_of_res": 1,
            },
            "股东大会制度的建立健全及运行情况": {
                "regs": [],
                "syllabus_reg": re.compile(r"股东大会|公司治理制度的建立健全"),
                "limit": 1,
                "cnt_of_res": 1,
            },
            "董事会制度的建立健全及运行情况": {
                "regs": [],
                "syllabus_reg": re.compile(r"董事会|公司治理制度(的建立健全)?及运行"),
                "limit": 1,
                "cnt_of_res": 1,
            },
            "监事会制度的建立健全及运行情况": {
                "regs": [],
                "syllabus_reg": re.compile(r"监事会|公司治理制度的建立健全及运行"),
                "limit": 1,
                "cnt_of_res": 1,
            },
            "独立董事制度的建立健全及运行情况": {
                "regs": [],
                "syllabus_reg": re.compile(r"(独立)?董事"),
                "limit": 1,
                "cnt_of_res": 1,
            },
            "董事会秘书制度的建立健全及运行情况": {
                "regs": [],
                "syllabus_reg": re.compile(r"董事会秘书"),
                "limit": 1,
                "cnt_of_res": 1,
            },
            "股东大会履行职责的情况": {
                "regs": [],
                "syllabus_reg": re.compile(r"股东大会"),
                "limit": 1,
                "cnt_of_res": 1,
            },
            "董事会履行职责的情况": {
                "regs": [],
                "syllabus_reg": re.compile(r"董事会"),
                "limit": 1,
                "cnt_of_res": 1,
            },
            "监事会履行职责的情况": {
                "regs": [],
                "syllabus_reg": re.compile(r"监事会"),
                "limit": 1,
                "cnt_of_res": 1,
            },
            "独立董事履行职责的情况": {
                "regs": [],
                "syllabus_reg": re.compile(r"独立董事"),
                "limit": 1,
                "cnt_of_res": 1,
                "threshold": 0.2,
            },
            "董事会秘书履行职责的情况": {
                "regs": [],
                "syllabus_reg": re.compile(r"董事会秘书"),
                "limit": 1,
                "cnt_of_res": 1,
            },
            "专门委员会的设置情况": {
                "regs": [],
                "syllabus_reg": re.compile(r"专门委员会"),
                "limit": 1,
                "cnt_of_res": 1,
            },
            "设置特表表决权安排的股东大会决议": {
                "regs": [],
                "syllabus_reg": re.compile(r"公司治理"),
                "limit": 1,
                "cnt_of_res": 1,
            },
            "特别表决权安排运行期限": {
                "regs": [],
                "syllabus_reg": re.compile(r"公司治理"),
                "limit": 1,
                "cnt_of_res": 1,
            },
            "特别表决权持有人资格": {
                "regs": [],
                "syllabus_reg": re.compile(r"公司治理"),
                "limit": 1,
                "cnt_of_res": 1,
            },
            "特别表决权股份拥有的表决权数量与普通股份拥有的表决权数量的比例安排": {
                "regs": [],
                "syllabus_reg": re.compile(r"公司治理"),
                "limit": 1,
                "cnt_of_res": 1,
            },
            "持有人所持特别表决权股份能够参与表决的股东大会事项范围": {
                "regs": [],
                "syllabus_reg": re.compile(r"公司治理"),
                "limit": 1,
                "cnt_of_res": 1,
            },
            "特别表决权股份锁定安排及转让限制": {
                "regs": [],
                "syllabus_reg": re.compile(r"公司治理"),
                "limit": 1,
                "cnt_of_res": 1,
            },
            "差异化表决安排可能导致的相关风险和对公司治理的影响": {
                "regs": [],
                "syllabus_reg": re.compile(r"公司治理"),
                "limit": 1,
                "cnt_of_res": 1,
            },
            "相关投资者保护措施": {
                "regs": [],
                "syllabus_reg": re.compile(r"公司治理"),
                "limit": 1,
                "cnt_of_res": 1,
            },
            "协议控制架构的具体安排": {
                "regs": [],
                "syllabus_reg": re.compile(r"公司治理"),
                "limit": 1,
                "cnt_of_res": 1,
            },
            "公司管理层对内部控制的自我评估意见": {
                "regs": [],
                "syllabus_reg": re.compile(r"内部控制|对内控制度"),
                "limit": 1,
                "cnt_of_res": 1,
            },
            "注册会计师对公司内部控制的鉴证意见": {
                "regs": [],
                "syllabus_reg": re.compile(r"(公司|发行人|会计师).*?内部控制"),
                "limit": 1,
                "cnt_of_res": 1,
            },
            "注册会计师是否指出公司内部控制存在缺陷": {
                "regs": [],
                "syllabus_reg": re.compile(r"(会计师|发行人|公司).*?内部控制"),
                "limit": 1,
                "cnt_of_res": 1,
            },
            "发行人针对缺陷披露的改进措施": {
                "regs": [],
                "syllabus_reg": re.compile(r"内部控制"),
                "limit": 1,
                "cnt_of_res": 1,
            },
            "违法违规行为及受到处罚的情况": {
                "regs": [],
                "syllabus_reg": re.compile(r"公司治理与独立性|合法合规情况|违法违规行为"),
                "limit": 1,
                "cnt_of_res": 1,
                "threshold": 0.14,
            },
            "违法违规行为及受到的处罚对发行人的影响": {
                "regs": [],
                "syllabus_reg": re.compile(r"规范运作情况|违法违规"),
                "limit": 1,
                "cnt_of_res": 1,
            },
            "资金被控股股东、实际控制人及其控制的其他企业占用的情况": {
                "regs": [],
                "syllabus_reg": re.compile(r"对外担保情况|资金占用|被.*?其他企业占用|资金被占用"),
                "limit": 1,
                "cnt_of_res": 1,
            },
            "为控股股东、实际控制人及其控制的其他企业担保的情况": {
                "regs": [],
                "syllabus_reg": re.compile(r"公司治理与独立性|对外担保情况"),
                "limit": 1,
                "cnt_of_res": 1,
                "threshold": 0.3,
            },
            "资产完整方面": {
                "regs": [],
                "syllabus_reg": re.compile(r"资产完整|持续运营|独立情况|独立经营"),
                "limit": 1,
                "cnt_of_res": 1,
            },
            "人员独立方面": {
                "regs": [],
                "syllabus_reg": re.compile(r"人员独立|独立经营|独立情况"),
                "limit": 1,
                "cnt_of_res": 1,
            },
            "财务独立方面": {
                "regs": [],
                "syllabus_reg": re.compile(r"财务独立|公司治理与独立性|独立情况"),
                "limit": 1,
                "cnt_of_res": 1,
            },
            "机构独立方面": {
                "regs": [],
                "syllabus_reg": re.compile(r"机构独立|持续运营情况|独立情况"),
                "limit": 1,
                "cnt_of_res": 1,
            },
            "业务独立方面": {
                "regs": [],
                "syllabus_reg": re.compile(r"业务独立|独立情况"),
                "limit": 1,
                "cnt_of_res": 1,
            },
            "发行人主营业务、控制权、管理团队和核心技术人员稳定情况": {
                "regs": [],
                "syllabus_reg": re.compile(
                    r"发行人.*?(变动(情况)?|持续经营能力)|不利影响|(人员)?稳定(情况)?|独立性|主营业务.*?变化(情况)?|其他影响独立性的情形"
                    r"|持续运营情况|独立经营情况|风险因素"
                ),
                "limit": 1,
                "cnt_of_res": 1,
            },
            "重大权属纠纷、偿债风险、重大或有事项、经营环境重大变化等情况": {
                "regs": [],
                "syllabus_reg": re.compile(
                    r"影响.*?经营|不利影响|持续经营有重大影响|经营稳定性方面|持续经营|公司治理与独立性"
                ),
                "limit": 1,
                "cnt_of_res": 1,
            },
            "同业竞争情况": {
                "regs": [],
                "syllabus_reg": re.compile(r"同业竞争"),
                "limit": 1,
                "cnt_of_res": 1,
            },
            "避免新增同业竞争承诺": {
                "regs": [],
                "syllabus_reg": re.compile(r"同业竞争|相同.*?业务"),
                "limit": 1,
                "cnt_of_res": 1,
            },
            "关联方、关联关系": {
                "regs": [],
                "syllabus_reg": re.compile(r"关联方|关联关系|发行人基本情况|同业竞争"),
                "limit": 1,
                "cnt_of_res": 1,
            },
            "经常性关联交易": {
                "regs": [],
                "syllabus_reg": re.compile(r"关联交易"),
                "limit": 1,
                "cnt_of_res": 1,
            },
            "偶发性关联交易": {
                "regs": [],
                "syllabus_reg": re.compile(r"偶发性关联交易|关联交易|重大资产重组"),
                "limit": 1,
                "cnt_of_res": 1,
            },
            "关联交易简要汇总表": {
                "regs": [],
                "syllabus_reg": re.compile(r"关联交易(汇总)?"),
                "limit": 1,
                "cnt_of_res": 1,
            },
            "关联交易是否履行了公司章程规定的程序": {
                "regs": [],
                "syllabus_reg": re.compile(r"关联交易"),
                "limit": 1,
                "cnt_of_res": 1,
            },
            "独立董事董事对关联交易履行的审计程序是否合法及交易交割是否公允的意见": {
                "regs": [],
                "syllabus_reg": re.compile(r"关联交易制度的执行情况|对?关联交易.*?意见|"),
                "limit": 1,
                "cnt_of_res": 1,
            },
            "关联方的变化情况": {
                "regs": [],
                "syllabus_reg": re.compile(r"关联方的?变化情况|关联交易|关联方"),
                "limit": 1,
                "cnt_of_res": 1,
            },
            "提示投资者阅读财务报告及审计报告全文": {
                "regs": [],
                "syllabus_reg": re.compile(r"财务会计信息"),
                "limit": 1,
                "cnt_of_res": 1,
            },
            "影响因素分析": {
                "regs": [],
                "syllabus_reg": re.compile(r"财务会计信息"),
                "limit": 1,
                "cnt_of_res": 1,
            },
            "合并资产负债表": {
                "regs": [],
                "syllabus_reg": re.compile(r"(合并)?资产负债表|合并财务报表"),
                "limit": 1,
                "cnt_of_res": 1,
            },
            "合并利润表": {
                "regs": [],
                "syllabus_reg": re.compile(r"(合并)?(利润|现金流量)表|财务会计信息与管理层分析"),
                "limit": 1,
                "cnt_of_res": 1,
            },
            "合并现金流量表": {
                "regs": [],
                "syllabus_reg": re.compile(r"(合并)?(利润|现金流量)表|财务报表|财务会计信息与管理层分析"),
                "limit": 1,
                "cnt_of_res": 1,
            },
            "母公司资产负债表": {
                "regs": [],
                "syllabus_reg": re.compile(r"母公司资产负债表|母公司财务报表"),
                "limit": 1,
                "cnt_of_res": 1,
            },
            "母公司利润表": {
                "regs": [],
                "syllabus_reg": re.compile(r"母公司利润表|母公司现金流量表|合并利润表|财务会计信息与管理层分析"),
                "limit": 1,
                "cnt_of_res": 1,
            },
            "母公司现金流量表": {
                "regs": [],
                "syllabus_reg": re.compile(r"母公司利润表|母公司现金流量表|合并现金流量表"),
                "limit": 1,
                "cnt_of_res": 1,
            },
            "会计师事务所的审计意见类型": {
                "regs": [],
                "syllabus_reg": re.compile(r"审计意见|财务会计信息与管理层分析"),
                "limit": 1,
                "cnt_of_res": 1,
            },
            "报表的编制基础": {
                "regs": [],
                "syllabus_reg": re.compile(r"报表的?编制基础|财务会计信息与管理层分析"),
                "limit": 1,
                "cnt_of_res": 1,
            },
            "合并范围及变化情况": {
                "regs": [],
                "syllabus_reg": re.compile(
                    r"合并(财务)?报表范围(的|及其?)?变化|重要合同|合并范围|财务会计信息与管理层分析"
                ),
                "limit": 1,
                "cnt_of_res": 1,
            },
            "会计政策和会计估计": {
                "regs": [],
                "syllabus_reg": re.compile(r"会计政策和会计估计|合并财务报表|财务会计信息与管理层分析"),
                "limit": 1,
                "cnt_of_res": 1,
            },
            "非经常性损益明细表": {
                "regs": [],
                "syllabus_reg": re.compile(
                    r"非经常性损益|主要财务指标重大资产重组|经营成果分析|财务会计信息与管理层分析"
                ),
                "limit": 1,
                "cnt_of_res": 1,
            },
            "适用税种、税率": {
                "regs": [],
                "syllabus_reg": re.compile(r"(税种)?和?税率|税费|所得税|税|财务会计信息与管理层分析"),
                "limit": 1,
                "cnt_of_res": 1,
            },
            "税收优惠政策": {
                "regs": [],
                "syllabus_reg": re.compile(r"税收优惠"),
                "limit": 1,
                "cnt_of_res": 1,
            },
            "税收优惠": {
                "regs": [],
                "syllabus_reg": re.compile(r"税收优惠|财务会计信息与管理层分析"),
                "limit": 1,
                "cnt_of_res": 1,
            },
            "是否对税收优惠存在依赖": {
                "regs": [],
                "syllabus_reg": re.compile(r"税收优惠|关联交易|财务会计信息与管理层分析"),
                "limit": 1,
                "cnt_of_res": 1,
            },
            "未来税收优惠的可持续性": {
                "regs": [],
                "syllabus_reg": re.compile(r"税收优惠"),
                "limit": 1,
                "cnt_of_res": 1,
            },
            "主要财务指标": {
                "regs": [],
                "syllabus_reg": re.compile(r"主要财务指标|偿债能力|财务会计信息与管理层分析"),
                "limit": 1,
                "cnt_of_res": 1,
            },
            "营业收入/主营业务收入的构成分析": {
                "regs": [],
                "syllabus_reg": re.compile(r"(经营成果|营业收入|主营业务).*?(分析|构成)|财务会计信息与管理层分析"),
                "limit": 1,
                "cnt_of_res": 1,
            },
            "营业成本成本构成分析": {
                "regs": [],
                "syllabus_reg": re.compile(r"(经营成果|营业收入|营业成本).*?(分析|构成)?|财务会计信息与管理层分析"),
                "limit": 1,
                "cnt_of_res": 1,
            },
            "毛利的构成分析": {
                "regs": [],
                "syllabus_reg": re.compile(r"毛利率?|财务会计信息与管理层分析"),
                "limit": 1,
                "cnt_of_res": 1,
            },
            "期间费用构成分析": {
                "regs": [],
                "syllabus_reg": re.compile(r"(期间)?费用(分析)?|财务会计信息与管理层分析"),
                "limit": 1,
                "cnt_of_res": 1,
            },
            "研发费用详情": {
                "regs": [],
                "syllabus_reg": re.compile(r"研发费用|财务费用|费用率|财务会计信息与管理层分析"),
                "limit": 1,
                "cnt_of_res": 1,
            },
            "非经常性损益项目": {
                "regs": [],
                "syllabus_reg": re.compile(r"非经常性损益|其他收益|财务会计信息与管理层分析"),
                "limit": 1,
                "cnt_of_res": 1,
            },
            "未纳入合并报表范围但对公司稳定性存在影响的投资主体或理财工具": {
                "regs": [],
                "syllabus_reg": re.compile(r"费用|分析"),
                "limit": 1,
                "cnt_of_res": 1,
            },
            "政府补助分析": {
                "regs": [],
                "syllabus_reg": re.compile(
                    r"政府补助|盈利能力|营业外收入|战略新兴产业发展专项基金|其他收益|财务会计信息与管理层分析"
                ),
                "limit": 1,
                "cnt_of_res": 1,
            },
            "税费": {
                "regs": [],
                "syllabus_reg": re.compile(r"纳税情况|税款|所得税|税费|税收|税项|缴税|税金|财务会计信息与管理层分析"),
                "limit": 1,
                "cnt_of_res": 1,
            },
            "尚未盈利或存在累计未弥补亏损对公司的影响": {
                "regs": [],
                "syllabus_reg": re.compile(r"未弥补亏损"),
                "limit": 1,
                "cnt_of_res": 1,
            },
            "金融资产详情": {
                "regs": [],
                "syllabus_reg": re.compile(r"金融资产|资产结构分析|资产(质量)?分析|投资收益|资产状况"),
                "limit": 1,
                "cnt_of_res": 1,
            },
            "应收账款详情": {
                "regs": [],
                "syllabus_reg": re.compile(r"应收账款|资产结构分析|应收款|财务会计信息与管理层分析"),
                "limit": 1,
                "cnt_of_res": 1,
            },
            "存货详情": {
                "regs": [],
                "syllabus_reg": re.compile(r"存货|财务会计信息与管理层分析"),
                "limit": 1,
                "cnt_of_res": 1,
            },
            "固定资产详情": {
                "regs": [],
                "syllabus_reg": re.compile(r"固定资产|资产分析|财务会计信息与管理层分析"),
                "limit": 1,
                "cnt_of_res": 1,
            },
            "对外投资项目": {
                "regs": [],
                "syllabus_reg": re.compile(r"对外投资|资产分析|资产总体构成|资产状况|资产构成"),
                "limit": 1,
                "cnt_of_res": 1,
            },
            "无形资产、开发支出": {
                "regs": [],
                "syllabus_reg": re.compile(r"无形资产|非流动资产|资产减值|财务会计信息与管理层分析"),
                "limit": 1,
                "cnt_of_res": 1,
                "threshold": 0.3,
            },
            "商誉详情": {
                "regs": [],
                "syllabus_reg": re.compile(r"商誉"),
                "limit": 1,
                "cnt_of_res": 1,
            },
            "偿债相关财务数据": {
                "regs": [],
                "syllabus_reg": re.compile(r"负债(情况|结构)|偿债能力|应收账款|财务会计信息与管理层分析"),
                "limit": 1,
                "cnt_of_res": 1,
            },
            "股利分配的具体实施情况": {
                "regs": [],
                "syllabus_reg": re.compile(r"股利分配|日后事项"),
                "limit": 1,
                "cnt_of_res": 1,
            },
            "现金流情况": {
                "regs": [],
                "syllabus_reg": re.compile(r"现金流|流动性及持续经营能力"),
                "limit": 1,
                "cnt_of_res": 1,
            },
            "重大资本性支出情况": {
                "regs": [],
                "syllabus_reg": re.compile(r"资(本性|产)支出"),
                "limit": 1,
                "cnt_of_res": 1,
            },
            "流动性情况": {
                "regs": [],
                "syllabus_reg": re.compile(r"流动性|财务会计信息与管理层分析"),
                "limit": 1,
                "cnt_of_res": 1,
            },
            "持续经营能力": {
                "regs": [],
                "syllabus_reg": re.compile(r"持续经营能力|持续盈利能力|财务会计信息与管理层分析"),
                "limit": 1,
                "cnt_of_res": 1,
            },
            "重大资本性支出与资产业务重组": {
                "regs": [],
                "syllabus_reg": re.compile(
                    r"(重大)?(投资|资本性|资产|投资或资本性)支出|关联交易|财务会计信息与管理层分析|重大资产(业务)?重组"
                ),
                "limit": 1,
                "cnt_of_res": 1,
            },
            "资产负债表日后事项": {
                "regs": [],
                "syllabus_reg": re.compile(r"资产负债表日后事项|期后事项|其他事项"),
                "limit": 1,
                "cnt_of_res": 1,
            },
            "或有事项": {
                "regs": [],
                "syllabus_reg": re.compile(r"或有事项|财务会计信息与管理层分析|其他事项"),
                "limit": 1,
                "cnt_of_res": 1,
            },
            "其他重要事项": {
                "regs": [],
                "syllabus_reg": re.compile(r"其他重要事项|财务会计信息与管理层分析"),
                "limit": 1,
                "cnt_of_res": 1,
            },
            "重大担保事项": {
                "regs": [],
                "syllabus_reg": re.compile(r"(重大)?(诉讼|担保)|财务会计信息与管理层分析"),
                "limit": 1,
                "cnt_of_res": 1,
            },
            "重大诉讼事项": {
                "regs": [],
                "syllabus_reg": re.compile(r"(重大)?(诉讼|担保)|财务会计信息与管理层分析"),
                "limit": 1,
                "cnt_of_res": 1,
            },
            "盈利预测信息": {
                "regs": [],
                "syllabus_reg": re.compile(r"盈利预测|盈利能力"),
                "limit": 1,
                "cnt_of_res": 1,
            },
            "盈利预测信息声明": {
                "regs": [],
                "syllabus_reg": re.compile(r"财务会计信息与管理层分析"),
                "limit": 1,
                "cnt_of_res": 1,
            },
            "盈利预测信息提示": {
                "regs": [],
                "syllabus_reg": re.compile(r"财务会计信息与管理层分析"),
                "limit": 1,
                "cnt_of_res": 1,
            },
            "盈利预测信息披露提示": {
                "regs": [],
                "syllabus_reg": re.compile(r"财务会计信息与管理层分析"),
                "limit": 1,
                "cnt_of_res": 1,
            },
            "前瞻性信息": {
                "regs": [],
                "syllabus_reg": re.compile(r"财务会计信息与管理层分析"),
                "limit": 1,
                "cnt_of_res": 1,
            },
            "依据": {
                "regs": [],
                "syllabus_reg": re.compile(r"财务会计信息与管理层分析"),
                "limit": 1,
                "cnt_of_res": 1,
            },
            "基础假设": {
                "regs": [],
                "syllabus_reg": re.compile(r"财务会计信息与管理层分析"),
                "limit": 1,
                "cnt_of_res": 1,
            },
            "未来实现盈利情况声明": {
                "regs": [],
                "syllabus_reg": re.compile(r"财务会计信息与管理层分析"),
                "limit": 1,
                "cnt_of_res": 1,
            },
            "募集资金使用管理制度": {
                "regs": [],
                "syllabus_reg": re.compile(r"募集资金(使用|运用)?[的与]?(基本情况|管理制度|未来发展规划)"),
                "limit": 1,
                "cnt_of_res": 1,
            },
            "募集资金重点投向科技创新领域的具体安排": {
                "regs": [re.compile(r"拟投入募集资金")],
                "syllabus_reg": re.compile(r"募集资金(投资|运用|用途)"),
                "limit": 1,
                "cnt_of_res": 1,
            },
            "募集资金的投资方向、使用安排表": {
                "regs": [],
                "syllabus_reg": re.compile(r"募集资金(投资|运用)"),
                "limit": 1,
                "cnt_of_res": 1,
            },
            "募集资金具体运用情况": {
                "regs": [],
                "syllabus_reg": re.compile(r"募集资金的?运用(情况)?"),
                "limit": 1,
                "cnt_of_res": 1,
            },
            "募集资金用于研发投入、科技创新、新产品开发生产情况": {
                "regs": [],
                "syllabus_reg": re.compile(r"募集资金的?运用(情况)?"),
                "limit": 1,
                "cnt_of_res": 1,
            },
            "战略规划情况": {
                "regs": [],
                "syllabus_reg": re.compile(r"(战略|战略|发展)规划|发展(战略|目标)"),
                "limit": 1,
                "cnt_of_res": 1,
            },
            "信息披露制度和流程": {
                "regs": [],
                "syllabus_reg": re.compile(r"投资者保护|商标|信息披露制度和流程"),
                "limit": 1,
                "cnt_of_res": 1,
            },
            "投资者沟通渠道的建立情况": {
                "regs": [],
                "syllabus_reg": re.compile(r"投资者(保护|关系)"),
                "limit": 1,
                "cnt_of_res": 1,
            },
            "未来开展投资者关系管理的规划": {
                "regs": [],
                "syllabus_reg": re.compile(r"投资者(保护|关系)"),
                "limit": 1,
                "cnt_of_res": 1,
            },
            "发行后的股利分配政策和决策程序": {
                "regs": [],
                "syllabus_reg": re.compile(r"股利分配政策|股利分配的?原则"),
                "limit": 1,
                "cnt_of_res": 1,
            },
            "本次发行前后股利分配政策的差异情况": {
                "regs": [],
                "syllabus_reg": re.compile(r"(股利|利润)分配政策的差异"),
                "limit": 1,
                "cnt_of_res": 1,
            },
            "本次发行完成前滚存利润的分配安排和已履行的决策程序": {
                "regs": [],
                "syllabus_reg": re.compile(r"滚存利润的?(分配|安排)|投资者保护"),
                "limit": 1,
                "cnt_of_res": 1,
            },
            "采取累积投票制选举公司董事": {
                "regs": [],
                "syllabus_reg": re.compile(r"股东投票(累积)?(机制|制度)"),
                "limit": 1,
                "cnt_of_res": 1,
            },
            "中小投资者单独计票机制": {
                "regs": [],
                "syllabus_reg": re.compile(r"股东投票(累积)?(机制|制度)"),
                "limit": 1,
                "cnt_of_res": 1,
            },
            "法定事项采取网络投票方式召开股东大会进行审议表决": {
                "regs": [],
                "syllabus_reg": re.compile(r"股东投票(累积)?(机制|制度)"),
                "limit": 1,
                "cnt_of_res": 1,
            },
            "征集投票权的相关安排": {
                "regs": [],
                "syllabus_reg": re.compile(r"股东投票(累积)?(机制|制度)"),
                "limit": 1,
                "cnt_of_res": 1,
            },
            "特别表决权股份、协议控制架构或类似特殊安排": {
                "regs": [],
                "syllabus_reg": re.compile(r"股东投票(累积)?(机制|制度)|特别表决权股份|特别表决权.*?措施"),
                "limit": 1,
                "cnt_of_res": 1,
            },
            "作出的重要承诺": {
                "regs": [],
                "syllabus_reg": re.compile(
                    r"股东.*?承诺|投资者保护|稳定股价的.*?措施(和承诺)?|承诺事项|业务和技术|重要承诺|关于.*?承诺"
                ),
                "limit": 1,
                "cnt_of_res": 1,
            },
            "未能履行承诺的约束措施": {
                "regs": [],
                "syllabus_reg": re.compile(r"未能?履行.*?措施|履行情况|约束措施|稳定.*?承诺"),
                "limit": 1,
                "cnt_of_res": 1,
            },
            "已触发履行条件的承诺事项的履行情况": {
                "regs": [],
                "syllabus_reg": re.compile(r"投资者(权益)?保护"),
                "limit": 1,
                "cnt_of_res": 1,
            },
            "合同情况": {
                "regs": [],
                "syllabus_reg": re.compile(r"重[大要](商务)?合同|合同管理|"),
                "limit": 1,
                "cnt_of_res": 1,
            },
            "对外担保情况": {
                "regs": [],
                "syllabus_reg": re.compile(r"对外担保(情况|的制度)?|对外投资和担保事项|发行人独立性"),
                "limit": 1,
                "cnt_of_res": 1,
            },
            "诉讼或仲裁事项-发行人": {
                "regs": [],
                "syllabus_reg": re.compile(
                    r"重大(诉讼或?仲裁)?|被.*?(调查|侦查|处罚)(情况)?|重大违法行为|诉讼[及与和或]仲裁事项"
                ),
                "limit": 1,
                "cnt_of_res": 1,
            },
            "刑事诉讼、重大诉讼或仲裁事项-董监高技": {
                "regs": [],
                "syllabus_reg": re.compile(
                    r"重大(诉讼或?仲裁)?|被.*?(调查|侦查|处罚)(情况)?|重大违法行为|诉讼[及与和或]仲裁事项|行政处罚|涉及刑事诉讼的情况|其他重要事项"
                ),
                "limit": 1,
                "cnt_of_res": 1,
            },
            "行政处罚、被司法机关立案侦查、被中国证监会立案调查情况-董监高技": {
                "regs": [],
                "syllabus_reg": re.compile(
                    r"重大(诉讼或?仲裁)?(事项)?|被.*?(调查|侦查|处罚)(情况)?|重大违法行为|诉讼[及和与或]仲裁事项|符合法律|行政处罚|"
                    r"涉及刑事诉讼的情况|其他重要事项"
                ),
                "limit": 1,
                "cnt_of_res": 1,
            },
            "重大违法行为-控股股东、实际控制人": {
                "regs": [],
                "syllabus_reg": re.compile(
                    r"重大(诉讼或?仲裁)?|被.*?(调查|侦查|处罚)(情况)?|重大违法|诉讼[及和与或]仲裁事项|符合法律|合法合规情况|兼职情况|"
                    r"守法情况|其他重要事项"
                ),
                "limit": 1,
                "cnt_of_res": 1,
            },
            "尾页声明": {
                "regs": [],
                "syllabus_reg": re.compile(r"声明"),
                "limit": 1,
                "cnt_of_res": 1,
            },
            "正文后声明": {
                "regs": [],
                "syllabus_reg": re.compile(r"声明|兼职情况"),
                "limit": 1,
                "cnt_of_res": 1,
            },
            "保荐人（主承销商）声明": {
                "regs": [],
                "syllabus_reg": re.compile(r"声明|保荐人|主承销商"),
                "limit": 1,
                "cnt_of_res": 1,
            },
            "律师声明": {
                "regs": [],
                "syllabus_reg": re.compile(r"声明"),
                "limit": 1,
                "cnt_of_res": 1,
            },
            "会计师事务所声明": {
                "regs": [],
                "syllabus_reg": re.compile(r"声明|会计师事务所"),
                "limit": 1,
                "cnt_of_res": 1,
            },
            "资产评估机构声明": {
                "regs": [],
                "syllabus_reg": re.compile(r"声明|资产情况"),
                "limit": 1,
                "cnt_of_res": 1,
            },
            "验资机构声明": {
                "regs": [],
                "syllabus_reg": re.compile(r"声明|验资.*?机构"),
                "limit": 1,
                "cnt_of_res": 1,
            },
            "附件内容": {
                "regs": [],
                "syllabus_reg": re.compile(r"附件|备查文件|声明|第.*?条"),
                "limit": 1,
                "cnt_of_res": 1,
            },
        }
