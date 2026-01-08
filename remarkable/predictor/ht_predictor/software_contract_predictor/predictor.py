import functools
import logging
import re
from collections import OrderedDict
from copy import deepcopy
from sre_constants import error as ReError

from remarkable.common.constants import ExtractMethodType
from remarkable.common.pattern import RE_TYPE
from remarkable.common.util import clean_txt, index_in_space_string
from remarkable.predictor.predict import AnswerPredictor, CharResult, ResultOfPredictor
from remarkable.rule.ht.ht_business_rules.common import party_employee_regs, partyb_obligations_regs


class FigueTermRule:
    def __init__(self, method_type, regs=None, cnt_of_anchor_elts=None, anchor_reg=None, cnt_of_res=None):
        self.method_type = method_type  # 枚举值:ExtractMethodType
        self.regs = regs or []
        self.anchor_reg = anchor_reg  # 定位元素块
        self.cnt_of_anchor_elts = cnt_of_anchor_elts if cnt_of_anchor_elts else 3  # 查找个数
        self.cnt_of_res = cnt_of_res if cnt_of_res else 1  # 预测答案个数


class HtPredictor(AnswerPredictor):
    def __init__(self, *args, **kwargs):
        super(HtPredictor, self).__init__(*args, **kwargs)
        self.sorted_elements = OrderedDict()
        self._patterns = {}
        if self.reader:
            for idx, _ in sorted(self.reader.data["_index"].items(), key=lambda x: x[0]):
                _, elt = self.reader.find_element_by_index(idx)
                self.sorted_elements.setdefault(idx, elt)

        if self.extract_methods:
            for attr, pattern in self.patterns.items():
                label_func = (
                    self._figue_label if pattern["method_type"] == ExtractMethodType.FIRGUE else self._term_label
                )
                self.column_analyzers.update(
                    {
                        attr: functools.partial(label_func, FigueTermRule(**pattern)),
                    }
                )

    @property
    def patterns(self):
        if not self._patterns:
            for extract_method in self.extract_methods:
                data = extract_method.data
                for key, value in data.items():
                    try:
                        if key.endswith("regs") and value:
                            data[key] = [re.compile(rf"{x}") if not isinstance(x, RE_TYPE) else x for x in value]
                        if key.endswith("reg") and value:
                            data[key] = re.compile(rf"{value}") if not isinstance(value, RE_TYPE) else value
                    except ReError as ex:
                        logging.error(f"{key}: {value}")
                        logging.exception(ex)
                        data[key] = None
                data["method_type"] = extract_method.method_type

                self._patterns[extract_method.path] = data
        return self._patterns

    @staticmethod
    def get_contract_map():
        return {
            "硬件采购合同": HardWarePurchase,
            "软件使用许可合同": SoftwareLicense,
            "软件开发外包合同": SoftwareOutsource,
        }

    def is_aim_elt(self, elt_idx, rule):
        """
        是否为目标元素块
        """
        try:
            if rule.anchor_reg is None:
                return True
            for idx in range(elt_idx - int(rule.cnt_of_anchor_elts), elt_idx + 1):
                if idx == elt_idx:
                    continue
                elt = self.sorted_elements.get(idx)
                if elt:
                    if rule.anchor_reg.search(clean_txt(elt.get("text", ""))):
                        return True
        except Exception as ex:
            logging.exception(ex)

        return False

    def fix_para_cross_pages(self, elt_idx):
        elt = deepcopy(self.sorted_elements.get(elt_idx, {}))
        if elt.get("continued"):
            for idx, ele in self.sorted_elements.items():
                if idx > elt_idx and ele["class"] == "PARAGRAPH":  # next_elt
                    # elt['text'] += ele.get('text', '')
                    for char in ele["chars"]:
                        if char not in elt["chars"]:
                            elt["chars"].append(char)
                            elt["text"] += char.get("text", "")
                    elt["continued_elt"] = ele
                    break
        return elt

    @staticmethod
    def append_item(chars, items):
        if chars and not any(all(char in item for char in chars) for item in items):
            items.append(chars)

    def _figue_label(self, rule, **kwargs):
        items = []
        schema_name = kwargs["col"]["schema"]["data"]["label"]
        for elt_idx, elt in self.sorted_elements.items():
            if elt["class"] != "PARAGRAPH":
                continue
            if elt.get("continued"):  # 跨页段落
                elt = self.fix_para_cross_pages(elt_idx)
            if not self.is_aim_elt(elt_idx, rule):
                continue

            elt_text = elt["text"]
            for reg in rule.regs:  # 不同的句式
                if not reg.search(clean_txt(elt_text)):
                    continue
                for each in reg.finditer(clean_txt(elt["text"])):
                    c_start, c_end = each.start("tar"), each.end("tar")
                    sp_start, sp_end = index_in_space_string(elt["text"], (c_start, c_end))
                    chars = elt["chars"][sp_start:sp_end]
                    if chars and self.is_valid_format(schema_name, chars):
                        self.append_item(chars, items)
                        if len(items) >= rule.cnt_of_res:
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
            if elt["class"] != "PARAGRAPH":
                continue
            if not self.is_aim_elt(elt_idx, rule):
                continue

            if elt.get("continued"):  # 跨页段落
                elt = self.fix_para_cross_pages(elt_idx)
            elt_text = clean_txt(elt["text"])
            for reg in rule.regs:
                if reg.search(elt_text):
                    # print('==============', elt_idx, reg.search(elt_text), elt_text)
                    # print('*******', ''.join([x['text'] for x in elt['chars']]))
                    self.append_item(elt["chars"], items)
            if len(items) >= rule.cnt_of_res:
                break
        data = [CharResult(item) for item in items]
        return ResultOfPredictor(data)

    @staticmethod
    def is_valid_format(schema_name, chars):
        answer = "".join([char["text"] for char in chars])
        answer = re.sub(r"(￥|¥|人民币|\.|元|圆|\s|，|,)", "", answer)
        if "大写" in schema_name:
            return answer.isalpha()
        if "小写" in schema_name:
            return answer.isdecimal()
        return True


class HardWarePurchase:
    """
    硬件采购合同
    todo：段落误识别为表格/跨页段落效果
    """

    firgue_patterns = {
        "甲方公司名称": {
            "regs": [
                re.compile(r"甲方\s*([(（].*[）)])?\s*[:：](?P<tar>.*)"),
            ],
            # 'anchor_reg': re.compile(r'甲方\s*([(（].*[）)])?\s*[:：]'),
            # 'cnt_of_anchor_elts': 2,
        },
        "乙方公司名称": {
            "regs": [
                re.compile(r"乙方\s*([(（].*[）)])?\s*[:：](?P<tar>.*)"),
            ],
            # 'anchor_reg': re.compile(r'乙方\s*([(（].*[）)])?\s*[:：]'),
            # 'cnt_of_anchor_elts': 2,
        },
        "甲方法人": {
            "regs": [
                re.compile(r"(法人|法定代表人)\s*([(（].*[）)])?\s*[:：](?P<tar>.*?)\s*职务"),
            ],
            "anchor_reg": re.compile(r"甲方\s*([(（].*[）)])?\s*[:：]"),
            "cnt_of_anchor_elts": 2,
        },
        "乙方法人": {
            "regs": [
                re.compile(r"(法人|法定代表人)\s*([(（].*[）)])?\s*[:：](?P<tar>.*?)\s*职务"),
            ],
            "anchor_reg": re.compile(r"乙方\s*([(（].*[）)])?\s*[:：]"),
            "cnt_of_anchor_elts": 2,
        },
        "甲方公司地址": {
            "regs": [
                re.compile(r"(地址|住址)\s*([(（].*[）)])?\s*[:：](?P<tar>.*)(邮编\s*[:：].*)"),
                re.compile(r"(地址|住址)\s*([(（].*[）)])?\s*[:：](?P<tar>.*)"),
            ],
            "anchor_reg": re.compile(r"甲方\s*([(（].*[）)])?\s*[:：]"),
            "cnt_of_anchor_elts": 2,
        },
        "乙方公司地址": {
            "regs": [
                re.compile(r"(地址|住址)\s*([(（].*[）)])?\s*[:：](?P<tar>.*)(邮编\s*[:：].*)"),
                re.compile(r"(地址|住址)\s*([(（].*[）)])?\s*[:：](?P<tar>.*)"),
            ],
            "anchor_reg": re.compile(r"乙方\s*([(（].*[）)])?\s*[:：]"),
            "cnt_of_anchor_elts": 2,
        },
        "合同总金额大写": {
            "regs": [
                re.compile(r"合同总额[:：]?[￥¥]?(.*?)[(（](大写)?[:：]?(?P<tar>(人民币)?.*?)[）)]"),
                re.compile(r"合同总额[:：]?[￥¥]?(?P<tar>.*?)[(（](大写)?[:：]?(人民币)?(.*?)[）)]"),
            ]
        },
        "合同总金额小写": {
            "regs": [
                re.compile(r"合同总额[:：]?(?P<tar>[￥¥]?.*?)[(（](大写)?[:：]?(人民币)?(.*?)[）)]"),
                re.compile(r"合同总额[:：]?[￥¥]?(.*?)[(（](大写)?[:：]?(人民币)?(?P<tar>.*?)[）)]"),
            ]
        },
        "第一笔付款大写": {
            "regs": [
                re.compile(r"(第一次付款[:：]?.*?)[(（]\s?(即|计)\s?[￥¥]?(.*?)，(?P<tar>(人民币)?.*?)[）)]"),
            ]
        },
        "第一笔付款小写": {
            "regs": [
                re.compile(r"(第一次付款[:：]?.*?)[(（]\s?(即|计)\s?(?P<tar>[￥¥]?.*?)，(人民币)?(.*?)[）)]"),
            ]
        },
        "第一笔付款比例": {
            "regs": [
                re.compile(r"第一次付款[:：]?.*?合同总金?额\s?的?\s*(?P<tar>.*?[%％])"),
            ]
        },
        "第二笔付款大写": {
            "regs": [
                re.compile(r"第二次付款[:：]?.*?[(（]\s?(即|计)\s?[￥¥]?(.*?)，(?P<tar>(人民币)?.*?)[）)]"),
            ]
        },
        "第二笔付款小写": {
            "regs": [
                re.compile(r"第二次付款[:：]?.*?[(（]\s?(即|计)\s?(?P<tar>[￥¥]?.*?)，(人民币)?(.*?)[）)]"),
            ]
        },
        "第二笔付款比例": {
            "regs": [
                re.compile(r"第二次付款[:：]?.*?合同总金?额\s?的?\s*(?P<tar>.*?[%％])"),
            ]
        },
        "第三笔付款大写": {
            "regs": [
                re.compile(r"第三次付款[:：]?.*?[(（]\s?(即|计)\s?[￥¥](.*?)，(?P<tar>(人民币)?.*?)[）)]"),
                re.compile(r"第三次付款[:：]?.*?[(（]\s?(即|计)\s?[￥¥](.*?)(?P<tar>人民币.*?)[）)]"),
            ]
        },
        "第三笔付款小写": {
            "regs": [
                re.compile(r"第三次付款[:：]?.*?[(（]\s?(即|计)\s?(?P<tar>[￥¥].*?)[，\s](人民币)?(.*?)[）)]"),
                re.compile(r"第三次付款[:：]?.*?[(（]\s?(即|计)\s?(?P<tar>[￥¥].*?)人民币(.*?)[）)]"),
            ]
        },
        "第三笔付款比例": {
            "regs": [
                re.compile(r"第三次付款[:：]?.*?合同总金?额\s?的?\s*(?P<tar>.*?[%％])"),
            ]
        },
        "第四笔付款大写": {
            "regs": [
                re.compile(r"第四次付款[:：]?.*?[(（]\s?(即|计)\s?[￥¥]?(.*?)，(?P<tar>(人民币)?.*?)[）)]"),
            ]
        },
        "第四笔付款小写": {
            "regs": [
                re.compile(r"第四次付款[:：]?.*?[(（]\s?(即|计)\s?(?P<tar>[￥¥]?.*?)，(人民币)?(.*?)[）)]"),
            ]
        },
        "第四笔付款比例": {
            "regs": [
                re.compile(r"第四次付款[:：]?.*?合同总金?额\s?的?\s*(?P<tar>.*?[%％])"),
            ]
        },
        "第五笔付款大写": {
            "regs": [
                re.compile(r"第五次付款[:：]?.*?[(（]\s?(即|计)\s?[￥¥](.*?)，(?P<tar>(人民币)?.*?)[）)]"),
            ]
        },
        "第五笔付款小写": {
            "regs": [
                re.compile(r"第五次付款[:：]?.*?[(（]\s?(即|计)\s?(?P<tar>[￥¥].*?)，(人民币)?(.*?)[）)]"),
            ]
        },
        "第五笔付款比例": {
            "regs": [
                re.compile(r"第五次付款[:：]?.*?合同总金?额\s?的?\s*(?P<tar>.*?[%％])"),
            ]
        },
        "第六笔付款大写": {
            "regs": [
                re.compile(r"第六次付款[:：]?.*?[(（]\s?(即|计)\s?[￥¥](.*?)，(?P<tar>(人民币)?.*?)[）)]"),
            ]
        },
        "第六笔付款小写": {
            "regs": [
                re.compile(r"第六次付款[:：]?.*?[(（]\s?(即|计)\s?(?P<tar>[￥¥].*?)，(人民币)?(.*?)[）)]"),
            ]
        },
        "第六笔付款比例": {
            "regs": [
                re.compile(r"第六次付款[:：]?.*?合同总金?额\s?的?\s*(?P<tar>.*?[%％])"),
            ]
        },
        "不含税合同总金额小写": {
            "regs": [
                re.compile(r"不含税价(?P<tar>.*?元)"),
            ]
        },
        "税款小写": {
            "regs": [
                re.compile(r"增值税额?[:：]?(?P<tar>[￥¥][\d,，.\s]*元?)"),
            ]
        },
        "增值税适用税率": {
            "regs": [
                re.compile(r"适用税率为(?P<tar>.*?)[。]"),
            ]
        },
        "乙方纳税人资质": {
            "regs": [
                re.compile(r"乙方声明具有增值税(?P<tar>.*?)[，。]"),
            ]
        },
        "甲方项目经理": {
            "regs": [
                re.compile(r"甲方指定[:：](?P<tar>.*?)为甲方在该项目上的全权代表"),
            ]
        },
        "乙方项目经理": {
            "regs": [
                re.compile(r"乙方指定[:：](?P<tar>.*?)为乙方在该项目上的全权代表"),
            ]
        },
    }

    term_patterns = {
        "增值税涉税固定条款1": {
            "regs": [
                re.compile(r"劳务清单"),
                re.compile(r"税收法规或税务机关"),
                re.compile(r"直接与间接损失"),
                re.compile(r"行政机关"),
            ],
            "limit": 3,
        },
        "增值税涉税固定条款2": {
            "regs": [
                re.compile(r"挂号信件"),
                re.compile(r"特快专递"),
                re.compile(r"逾期送达"),
                re.compile(r"重新开具合法发票"),
            ],
            "limit": 3,
        },
        "增值税涉税固定条款3": {
            "regs": [
                re.compile(r"丢失或被盗"),
                re.compile(r"未顺利送达"),
                re.compile(r"遭受的经济损失"),
                re.compile(r"负责赔偿"),
            ],
            "limit": 3,
        },
        "增值税涉税固定条款4": {
            "regs": [
                re.compile(r"相关票据"),
                re.compile(r"按照相关税收法律法规提供有关资料"),
            ],
            "limit": 2,
        },
        "代码及功能规范条款": {
            "regs": [
                re.compile(r"恶意代码或未授权"),
                re.compile(r"证券期货行业有关技术规范"),
                re.compile(r"技术指引"),
            ],
            "limit": 2,
        },
        "信息安全条款": {
            "regs": [
                re.compile(r"信息安全延伸检查"),
                re.compile(r"证券期货行业监管部门"),
            ],
            "limit": 2,
        },
        "系统漏洞条款": {
            "regs": [
                re.compile(r"软件后门"),
                re.compile(r"其他软件"),
                re.compile(r"第三方的损失"),
            ],
            "limit": 2,
        },
        "重大事项告知条款": {
            "regs": [
                re.compile(r"产品结束"),
                re.compile(r"公司更换"),
                re.compile(r"发生重大事项"),
            ],
            "limit": 2,
        },
        "应急预案条款": {
            "regs": [
                re.compile(r"重大异常情况"),
                re.compile(r"内部应急处置规则"),
                re.compile(r"变更协议合作方"),
                re.compile(r"应急处置工作"),
            ],
            "limit": 3,
        },
        "数据安全条款": {
            "regs": [
                re.compile(r"因软件自身漏洞"),
                re.compile(r"甲方客户的数据"),
            ],
            "limit": 2,
        },
        "保密责任条款": {
            "regs": [
                re.compile(r"甲方的任何资料"),
                re.compile(r"无论是书面的还是电子的"),
                re.compile(r"任何交付物"),
                re.compile(r"擅自使用"),
                re.compile(r"公开发表"),
            ],
            "limit": 3,
        },
        "保密责任": {
            "regs": [
                re.compile(r"如拥有另一方"),
                re.compile(r"必要的步骤"),
                re.compile(r"违反本条造成损失"),
            ],
            "limit": 2,
        },
        "违约责任1": {
            "regs": [
                re.compile(r"甲方逾期付款"),
                re.compile(r"逾期交货"),
                re.compile(r"任何一方违反本合同约定的"),
                re.compile(r"承担违约责任"),
            ],
            "limit": 2,
        },
        "违约责任2": {
            "regs": [
                re.compile(r"产品规格型号"),
                re.compile(r"不符合合同规定"),
                re.compile(r"包换或包修"),
                re.compile(r"因甲方原因导致本合同提前解除"),
                re.compile(r"乙方不退还甲方已经支付的服务费用。"),
            ],
            "limit": 2,
        },
        "违约责任3": {
            "regs": [
                re.compile(r"质量问题"),
                re.compile(r"权利瑕疵"),
                re.compile(r"正规厂家生产"),
                re.compile(r"需要支付违约金或赔偿金"),
                re.compile(r"承担的金额不超过本合同的标的金额"),
            ],
            "limit": 2,
        },
        "附件-项目保密协议": {
            "regs": [
                re.compile(r"(?P<tar>.*项目保密协议\s*$)"),
                re.compile(r"(?P<tar>.*项目保密协议》)"),
            ],
            "limit": 1,
        },
        "售后服务": {
            "regs": [
                re.compile(r"原厂的保修服务"),
                re.compile(r"保修期限内"),
                re.compile(r"设备故障"),
                re.compile(r"解决问题"),
                re.compile(r"故障排除"),
                re.compile(r"系统的巡检"),
                re.compile(r"乙方所提供的上述服务"),
                re.compile(r"电话咨询服务"),
            ],
            "limit": 2,
            "cnt_of_res": 5,
        },
        "乙方服务承诺": {
            "regs": [
                re.compile(r"信息技术服务"),
                re.compile(r"服务的任何环节"),
                re.compile(r"转委托第三方"),
                re.compile(r"设置技术壁垒"),
                re.compile(r"违反现行法律法规"),
                re.compile(r"中国证监会禁止的"),
                re.compile(r"截取.*?存储.*?转发"),
                re.compile(r"社会公开发布.*?系统压力测试.*?网络安全信息"),
            ],
            "limit": 1,
            "cnt_of_res": 8,
        },
        "合同生效和变更": {
            "regs": [
                re.compile(r"双方签字盖章"),
                re.compile(r"本合同一经签署"),
                re.compile(r"随意更改本合同"),
                re.compile(r"同等效力"),
                re.compile(r"签订书面协议"),
            ],
            "limit": 1,
            "cnt_of_res": 4,
        },
        "乙方义务-备案监督条款": {
            "regs": partyb_obligations_regs["备案监督条款"],
            "limit": 1,
            "cnt_of_res": 2,
        },
        "乙方义务-违规监督条款": {
            "regs": partyb_obligations_regs["违规监督条款"],
            "limit": 1,
            "cnt_of_res": 2,
        },
        "乙方义务-纠纷、仲裁告知条款": {
            "regs": partyb_obligations_regs["纠纷、仲裁告知条款"],
            "limit": 1,
            "cnt_of_res": 2,
        },
        "乙方义务-违规采购条款": {
            "regs": partyb_obligations_regs["违规采购条款"],
            "limit": 1,
            "cnt_of_res": 2,
        },
        "乙方义务-合规管理条款": {
            "regs": partyb_obligations_regs["合规管理条款"],
            "limit": 1,
            "cnt_of_res": 2,
        },
        "乙方义务-质量控制条款": {
            "regs": partyb_obligations_regs["质量控制条款"],
            "limit": 1,
            "cnt_of_res": 2,
        },
    }


class SoftwareLicense:
    """
    软件使用许可合同
    todo:第n笔付款的句式
    """

    firgue_patterns = {
        "甲方公司名称": {
            "regs": [
                re.compile(r"甲方\s*([(（].*[）)])?\s*[:：](?P<tar>.*)"),
            ],
            # 'anchor_reg': re.compile(r'甲方\s*([(（].*[）)])?\s*[:：]'),
            # 'cnt_of_anchor_elts': 2,
        },
        "乙方公司名称": {
            "regs": [
                re.compile(r"乙方\s*([(（].*[）)])?\s*[:：](?P<tar>.*)"),
            ],
            # 'anchor_reg': re.compile(r'乙方\s*([(（].*[）)])?\s*[:：]'),
            # 'cnt_of_anchor_elts': 2,
        },
        "甲方法人": {
            "regs": [
                re.compile(r"(法人|法定代表人)\s*([(（].*[）)])?\s*[:：](?P<tar>.*?)\s*职务"),
            ],
            "anchor_reg": re.compile(r"甲方\s*([(（].*[）)])?\s*[:：]"),
            "cnt_of_anchor_elts": 2,
        },
        "乙方法人": {
            "regs": [
                re.compile(r"(法人|法定代表人)\s*([(（].*[）)])?\s*[:：](?P<tar>.*?)\s*职务"),
            ],
            "anchor_reg": re.compile(r"乙方\s*([(（].*[）)])?\s*[:：]"),
            "cnt_of_anchor_elts": 2,
        },
        "甲方公司地址": {
            "regs": [
                re.compile(r"(地址|住址)\s*([(（].*[）)])?\s*[:：](?P<tar>.*)(邮编\s*[:：].*)"),
                re.compile(r"(地址|住址)\s*([(（].*[）)])?\s*[:：](?P<tar>.*)"),
            ],
            "anchor_reg": re.compile(r"甲方\s*([(（].*[）)])?\s*[:：]"),
            "cnt_of_anchor_elts": 2,
        },
        "乙方公司地址": {
            "regs": [
                re.compile(r"(地址|住址)\s*([(（].*[）)])?\s*[:：](?P<tar>.*)(邮编\s*[:：].*)"),
                re.compile(r"(地址|住址)\s*([(（].*[）)])?\s*[:：](?P<tar>.*)"),
            ],
            "anchor_reg": re.compile(r"乙方\s*([(（].*[）)])?\s*[:：]"),
            "cnt_of_anchor_elts": 2,
        },
        "合同总金额大写": {
            "regs": [
                re.compile(r"本合同总金额为[:：]?(.*?元?)[(（]大写[:：]?(?P<tar>.*?)[）)]"),
                re.compile(r"本合同总金额[(（]大写[）)](人民币)?(?P<tar>.*?)；?[(（]小写[）)][￥¥]?(.*?)。"),
                re.compile(r"本合同总金额为\s*[:：]?[￥¥](?P<tar>.*?)[(（]大写[:：]?(.*?)[）)]"),
            ]
        },
        "合同总金额小写": {
            "regs": [
                re.compile(r"本合同总金额为[:：]?(?P<tar>.*?元?)[(（]大写[:：]?(.*?)[）)]"),
                re.compile(r"本合同总金额[(（]大写[）)](人民币)?(.*?)；?[(（]小写[）)]?(?P<tar>[￥¥][\s\d,，]*)"),
                re.compile(r"本合同总金额为[:：]?(.*?元?)[(（]大写[:：]?(人民币)?(?P<tar>.*?)[）)]"),
            ]
        },
        "第一笔付款大写": {
            "regs": [
                re.compile(r"在签订本合同后.*个工作日内.*?(即|计)\s?(.*?)元?[(（]大写[:：]?(?P<tar>.*?)[）)]"),
                re.compile(
                    r"在签订本合同后.*个工作日内.*?(即|计)\s?[￥¥][\d，.,\s]*?(?P<tar>[零壹贰叁肆伍陆柒捌玖拾佰仟亿元整分角圆万]+)"
                ),
                re.compile(
                    r"在签订本合同后.*个工作日内.*?(即|计)(?P<tar>(人民币)?[(（]大写[）)]?[零壹贰叁肆伍陆柒捌玖拾佰仟亿元整分角圆万]+)"
                ),
            ]
        },
        "第一笔付款小写": {
            "regs": [
                re.compile(r"在签订本合同后.*个工作日内.*?(即|计).*[(（]小写[）)](?P<tar>[￥¥][\d，.,\s]*)"),
                re.compile(r"在签订本合同后.*个工作日内.*?(即|计)\s?(?P<tar>.*?元?)[(（]大写[:：]?(.*?)[）)]"),
                re.compile(r"在合同签订后.*个工作日内.*?合计人民币[￥¥]?(?P<tar>.*?元?)"),
                re.compile(r"在签订本合同后.*个工作日内.*?(即|计)\s?(?P<tar>[￥¥][\d，.,\s]*)"),
            ]
        },
        "第一笔付款比例": {
            "regs": [
                re.compile(r"在签订本合同后.*个工作日内.*?合同总金?额的?\s*(?P<tar>.*[%％])"),
                re.compile(r"在合同签订后.*个工作日内.*?合同总金?额的?\s*(?P<tar>.*[%％])"),
            ]
        },
        "第二笔付款大写": {
            "regs": [
                re.compile(r"在许可软件安装调试运行并验收合格后.*?(即|计)\s?(.*?)元?[(（]大写[:：]?(?P<tar>.*?)[）)]"),
                re.compile(
                    r"系统正式验收后.*个工作日内.*?(即|计)(?P<tar>(人民币)?[(（]大写[）)]?[零壹贰叁肆伍陆柒捌玖拾佰仟亿元整分角圆万]+)"
                ),
            ]
        },
        "第二笔付款小写": {
            "regs": [
                re.compile(r"在许可软件安装调试运行并验收合格后.*?(即|计)\s?(?P<tar>.*?元?)[(（]大写[:：]?(.*?)[）)]"),
                re.compile(r"系统验收合格后.*个工作日内.*?合计人民币[￥¥]?(?P<tar>.*?元)"),
                re.compile(r"系统正式验收后.*个工作日内.*?(即|计).*[(（]小写[）)](?P<tar>[￥¥][\d，.,\s]*)"),
            ]
        },
        "第二笔付款比例": {
            "regs": [
                re.compile(r"在许可软件安装调试运行并验收合格后.*?合同总金?额的?\s*(?P<tar>.*[%％])"),
                re.compile(r"系统验收合格后.*个工作日内.*?(软件|模块)金?额的?\s*(?P<tar>.*[%％])"),
                re.compile(r"系统正式验收后.*个工作日内.*?合同总?金?额的?(?P<tar>.*[%％])"),
            ]
        },
        "第三笔付款大写": {
            "regs": [
                re.compile(r"在.*?届满.*年后.*?(即|计)\s?(.*?)元?[(（]大写[:：]?(?P<tar>.*?)[）)]"),
                re.compile(
                    r"系统正式验收届满一年.*个工作日内.*?(即|计)[:：](?P<tar>(人民币)?[(（]大写[）)]?[零壹贰叁肆伍陆柒捌玖拾佰仟亿元整分角圆万]+)"
                ),
            ]
        },
        "第三笔付款小写": {
            "regs": [
                re.compile(r"在.*?届满.*年后.*?(即|计)\s?(?P<tar>.*?元?)[(（]大写[:：]?(.*?)[）)]"),
                re.compile(r"系统正式上线运行.*个工作日内.*?合计人民币[￥¥]?(?P<tar>.*?元)"),
                re.compile(r"系统正式验收届满一年.*个工作日内.*?(即|计).*[(（]小写[）)](?P<tar>[￥¥][\d，.,\s]*)"),
            ]
        },
        "第三笔付款比例": {
            "regs": [
                re.compile(r"在.*?届满.*年后.*?合同总金?额的?\s*(?P<tar>.*[%％])"),
                re.compile(r"系统正式上线运行.*个工作日内.*?(软件|模块)金?额的?\s*(?P<tar>.*[%％])"),
                re.compile(r"系统正式验收届满一年.*个工作日内.*?合同总?金?额的?(?P<tar>.*[%％])"),
            ]
        },
        "第四笔付款大写": {"regs": []},
        "第四笔付款小写": {"regs": []},
        "第四笔付款比例": {"regs": []},
        "不含税合同总金额大写": {
            "regs": [
                re.compile(r"(其中不含税价|不含税金额为)：?(.*?)元?[(（]大写[:：]?(?P<tar>.*?)[）)]"),
            ]
        },
        "不含税合同总金额小写": {
            "regs": [
                re.compile(r"不含税金额为：?(?P<tar>.*?元?)[(（]大写[:：]?(.*?)[）)]"),
                re.compile(r"不含税价(?P<tar>.*?元)"),
            ]
        },
        "税款大写": {
            "regs": [
                re.compile(r"增值税款?为?：?(.*?)元?[(（]大写[:：]?(?P<tar>.*?)[）)]"),
            ]
        },
        "税款小写": {
            "regs": [
                re.compile(r"增值税款?为?：?(?P<tar>.*?元?)[(（]大写[:：]?(.*?)[）)]"),
                re.compile(r"、增值税(?P<tar>.*?元)"),
            ]
        },
        "维护费用大写": {
            "regs": [
                re.compile(
                    r"甲方应向乙方支付维护培训服务费用.*?每年费用为合同总金额.*?(即|计)\s?(.*?)元?[(（]大写[:：]?(?P<tar>.*?)[）)]"
                ),
                re.compile(r"甲方应向乙方支付维护培训服务费用合计(.*?元?)[(（]大写[:：]?(?P<tar>.*?)[）)]"),
                re.compile(r"甲方应向乙方支付维护培训服务费用收取标准为(?P<tar>.*合同金额的.*%)"),
            ]
        },
        "维护费用小写": {
            "regs": [
                re.compile(
                    r"甲方应向乙方支付维护培训服务费用.*?每年费用为合同总金额.*?(即|计)\s?(?P<tar>.*?元?)[(（]大写[:：]?(.*?)[）)]"
                ),
                re.compile(r"甲方应向乙方支付维护培训服务费用合计(?P<tar>.*?元?)[(（]大写[:：]?(.*?)[）)]"),
                re.compile(r"甲方应向乙方支付维护培训服务费用收取标准为(?P<tar>.*合同金额的.*%)"),
            ]
        },
        "增值税税率": {
            "regs": [
                re.compile(r"适用税率为[:：]?(?P<tar>.*?)[。]"),
            ]
        },
        "乙方纳税人资质": {
            "regs": [
                re.compile(r"乙方声明具有增值税(?P<tar>.*?)[，。]"),
            ]
        },
        "最后一笔付款条件": {
            "regs": [
                re.compile(r"(?P<tar>在.*?届满.*?)[，。]"),
            ]
        },
        "甲方项目经理": {
            "regs": [
                re.compile(r"甲方指定[:：]?(?P<tar>.*?)为甲方在该项目上的全权代表"),
            ]
        },
        "乙方项目经理": {
            "regs": [
                re.compile(r"乙方指定[:：]?(?P<tar>.*?)为乙方在该项目上的全权代表"),
            ]
        },
    }

    term_patterns = {
        "增值税涉税固定条款1": {
            "regs": [
                re.compile(r"劳务清单"),
                re.compile(r"税收法规或税务机关"),
                re.compile(r"直接与间接损失"),
                re.compile(r"行政机关"),
            ],
        },
        "增值税涉税固定条款2": {
            "regs": [
                re.compile(r"挂号信件"),
                re.compile(r"特快专递"),
                re.compile(r"逾期送达"),
                re.compile(r"重新开具合法发票"),
            ],
        },
        "增值税涉税固定条款3": {
            "regs": [
                re.compile(r"丢失或被盗"),
                re.compile(r"未能?顺利送达"),
                re.compile(r"[遭承经]受的经济损失"),
                re.compile(r"负责赔偿"),
            ],
        },
        "增值税涉税固定条款4": {
            "regs": [
                re.compile(r"相关票据"),
                re.compile(r"按照相关税收法律法规提供有关资料"),
            ],
            "limit": 2,
        },
        "代码功能及规范条款": {
            "regs": [
                re.compile(r"恶意代码或未授权"),
                re.compile(r"证券期货行业有关技术规范"),
                re.compile(r"技术指引"),
            ],
            "limit": 2,
        },
        "信息安全条款": {
            "regs": [
                re.compile(r"信息安全延伸检查"),
                re.compile(r"证券期货行业监管部门"),
            ],
            "limit": 2,
        },
        "系统漏洞条款": {
            "regs": [
                re.compile(r"软件后门"),
                re.compile(r"其他软件"),
                re.compile(r"第三方的损失"),
            ],
            "limit": 2,
        },
        "数据安全条款": {
            "regs": [
                re.compile(r"软件自身漏洞"),
                re.compile(r"甲方客户的?数据"),
            ],
            "limit": 2,
        },
        "重大事项告知条款": {
            "regs": [
                re.compile(r"产品结束"),
                re.compile(r"公司更换"),
                re.compile(r"发生重大事项"),
            ],
            "limit": 2,
        },
        "应急预案条款": {
            "regs": [
                re.compile(r"重大异常情况"),
                re.compile(r"乙方应协助"),
                re.compile(r"降到最低"),
            ],
            "limit": 3,
        },
        "保密责任条款": {
            "regs": [
                re.compile(r"甲方的任何资料"),
                re.compile(r"无论是书面的还是电子的"),
                re.compile(r"任何交付物"),
                re.compile(r"擅自使用"),
                re.compile(r"公开发表"),
            ],
        },
        "保密责任": {
            "regs": [
                re.compile(r"如拥有另一方"),
                re.compile(r"必要的步骤"),
                re.compile(r"违反本条造成损失"),
            ],
            "limit": 2,
        },
        "违约责任1": {
            "regs": [
                re.compile(r"甲方逾期付款"),
                re.compile(r"支付违约金"),
                re.compile(r"单方解除合同"),
                re.compile(r"违约方支付"),
            ],
        },
        "违约责任2": {
            "regs": [
                re.compile(r"所列指标要求"),
                re.compile(r"权利瑕疵"),
                re.compile(r"提供合格软件"),
                re.compile(r"大于违约金数额"),
            ],
        },
        "违约责任3": {
            "regs": [
                re.compile(r"法律允许的范围内"),
                re.compile(r"另有约定"),
                re.compile(r"有关的全部责任"),
            ],
            "limit": 2,
        },
        "违约责任4": {
            "regs": [
                re.compile(r"身体伤害"),
                re.compile(r"恶意或严重疏忽"),
                re.compile(r"财产损失所应承担"),
            ],
            "limit": 2,
        },
        "违约责任5": {
            "regs": [
                re.compile(r"上述规定在本合同终止或到期后仍然有效"),
            ],
            "limit": 1,
        },
        "附件-项目工作说明书": {
            "regs": [
                re.compile(r"(?P<tar>.*项?目?工作说明书\s*$)"),
            ],
            "limit": 1,
        },
        "附件-项目保密协议": {
            "regs": [
                re.compile(r"(?P<tar>.*项目保密协议\s*$)"),
            ],
            "limit": 1,
        },
        "售后服务": {
            "regs": [
                re.compile(r"系统保持稳定且正常运行"),
                re.compile(r"报修电话"),
                re.compile(r"诊断并排除"),
                re.compile(r"乙方应为甲方提供"),
                re.compile(r"系统的巡检"),
                re.compile(r"电话咨询服务"),
                re.compile(r"产品使用培训工作"),
            ],
            "limit": 4,
            "cnt_of_res": 5,
        },
        "质量考核标准": {
            "regs": [
                re.compile(r"质量考核标准"),
            ],
            # 'anchor_reg': re.compile(r'项目工作说明书'),
            # 'cnt_of_anchor_elts': 10,
            "cnt_of_res": 1,
            "limit": 1,
        },
        "持续监控机制": {
            "regs": [
                re.compile(r"持续监控机制"),
            ],
            # 'anchor_reg': re.compile(r'项目工作说明书'),
            # 'cnt_of_anchor_elts': 10,
            "cnt_of_res": 1,
            "limit": 1,
        },
        "项目变更管理": {
            "regs": [
                re.compile(r"项目变更管理"),
                re.compile(r"导致工作量增加"),
                re.compile(r"超过部分"),
                re.compile(r"补充协议"),
            ],
            "limit": 4,
        },
        "应急预案条款（甲方）": {
            "regs": [
                re.compile(r"甲方有权"),
                re.compile(r"重大异常情况"),
                re.compile(r"变更协议合作方"),
                re.compile(r"应急处置流程"),
            ],
            "limit": 4,
        },
        "乙方服务承诺": {
            "regs": [
                re.compile(r"信息技术服务"),
                re.compile(r"服务的任何环节"),
                re.compile(r"转委托第三方"),
                re.compile(r"设置技术壁垒"),
                re.compile(r"违反现行法律法规"),
                re.compile(r"中国证监会禁止的"),
                re.compile(r"截取.*?存储.*?转发"),
                re.compile(r"社会公开发布.*?系统压力测试.*?网络安全信息"),
            ],
            "limit": 1,
            "cnt_of_res": 8,
        },
        "合同效力": {
            "regs": [
                re.compile(r"本合同一经签署"),
                re.compile(r"随意更改本合同"),
                re.compile(r"同等效力"),
                re.compile(r"签订书面协议"),
            ],
            "limit": 3,
        },
        "乙方义务-备案监督条款": {
            "regs": partyb_obligations_regs["备案监督条款"],
            "limit": 1,
            "cnt_of_res": 2,
        },
        "乙方义务-违规监督条款": {
            "regs": partyb_obligations_regs["违规监督条款"],
            "limit": 1,
            "cnt_of_res": 2,
        },
        "乙方义务-纠纷、仲裁告知条款": {
            "regs": partyb_obligations_regs["纠纷、仲裁告知条款"],
            "limit": 1,
            "cnt_of_res": 2,
        },
        "乙方义务-违规采购条款": {
            "regs": partyb_obligations_regs["违规采购条款"],
            "limit": 1,
            "cnt_of_res": 2,
        },
        "乙方义务-合规管理条款": {
            "regs": partyb_obligations_regs["合规管理条款"],
            "limit": 1,
            "cnt_of_res": 2,
        },
        "乙方义务-质量控制条款": {
            "regs": partyb_obligations_regs["质量控制条款"],
            "limit": 1,
            "cnt_of_res": 2,
        },
    }


class SoftwareOutsource:
    """
    软件开发外包合同
    todo:第n笔付款的句式
    """

    firgue_patterns = {
        "甲方公司名称": {
            "regs": [
                re.compile(r"甲方\s*([(（].*[）)])?\s*[:：](?P<tar>.*公司)"),
                re.compile(r"甲方\s*([(（].*[）)])?\s*[:：](?P<tar>.*)"),
            ],
            # 'anchor_reg': re.compile(r'甲方\s*([(（].*[）)])?\s*[:：]'),
            # 'cnt_of_anchor_elts': 2,
        },
        "乙方公司名称": {
            "regs": [
                re.compile(r"乙方\s*([(（].*[）)])?\s*[:：](?P<tar>.*)"),
            ],
            # 'anchor_reg': re.compile(r'乙方\s*([(（].*[）)])?\s*[:：]'),
            # 'cnt_of_anchor_elts': 2,
        },
        "甲方法人": {
            "regs": [
                re.compile(r"(法人|法定代表人)\s*([(（].*[）)])?\s*[:：](?P<tar>.*?)\s*职务"),
            ],
            "anchor_reg": re.compile(r"甲方\s*([(（].*[）)])?\s*[:：]|合同"),
            "cnt_of_anchor_elts": 2,
        },
        "乙方法人": {
            "regs": [
                re.compile(r"(法人|法定代表人)\s*([(（].*[）)])?\s*[:：](?P<tar>.*?)\s*职务"),
            ],
            "anchor_reg": re.compile(r"乙方\s*([(（].*[）)])?\s*[:：]"),
            "cnt_of_anchor_elts": 2,
        },
        "甲方公司地址": {
            "regs": [
                re.compile(r"(地址|住址)\s*([(（].*[）)])?\s*[:：](?P<tar>.*)(邮编\s*[:：].*)"),
                re.compile(r"(地址|住址)\s*([(（].*[）)])?\s*[:：](?P<tar>.*)"),
            ],
            "anchor_reg": re.compile(r"甲方\s*([(（].*[）)])?\s*[:：]|合同"),
            "cnt_of_anchor_elts": 2,
        },
        "乙方公司地址": {
            "regs": [
                re.compile(r"(地址|住址)\s*([(（].*[）)])?\s*[:：](?P<tar>.*)(邮编\s*[:：].*)"),
                re.compile(r"(地址|住址)\s*([(（].*[）)])?\s*[:：](?P<tar>.*)"),
            ],
            "anchor_reg": re.compile(r"乙方\s*([(（].*[）)])?\s*[:：]"),
            "cnt_of_anchor_elts": 2,
        },
        "合同总金额大写": {
            "regs": [
                re.compile(r"甲方应付总金额为[:：]?(.*?元?)[(（]大写[:：]?(?P<tar>.*?)[）)]"),
                re.compile(r"甲方应付开发费总金额为[:：]?[(（]小写[）)](.*?元?)[(（]大写[）)](?P<tar>.*?)。"),
                re.compile(r"甲方应付总金额为[:：]?[￥¥]?(?P<tar>.*?元?)[(（]大写[:：]?(.*?)[）)]"),
            ]
        },
        "合同总金额小写": {
            "regs": [
                re.compile(r"甲方应付总金额为[:：]?(?P<tar>.*?元?)[(（]大写[:：]?(.*?)[）)]"),
                re.compile(r"甲方应付开发费总金额为[:：]?[(（]小写[）)](?P<tar>.*?元?)[(（]大写[）)](.*?)。"),
                re.compile(r"甲方应付总金额为[:：]?(.*?元?)[(（]大写[:：]?(人民币)(?P<tar>.*?)[）)]"),
            ]
        },
        "第一笔付款大写": {
            "regs": [
                re.compile(r"在.*合同.*后.*个工作日内.*?(即|计)\s?(.*?元?)[(（]大写[:：]?(?P<tar>.*?)[）)]"),
                re.compile(
                    r"在签订本合同后.*个工作日内.*?（合计[(（]小写[）)](.*?元?)(人民币)?[(（]大写[）)](?P<tar>.*?)）"
                ),
            ]
        },
        "第一笔付款小写": {
            "regs": [
                re.compile(r"在.*合同.*后.*个工作日内.*?(即|计)\s?(?P<tar>.*?元?)[(（]大写[:：]?(.*?)[）)]"),
                re.compile(
                    r"在签订本合同后.*个工作日内.*?（合计[(（]小写[）)](?P<tar>.*?元?)(人民币)?[(（]大写[）)](.*?)）"
                ),
            ]
        },
        "第一笔付款比例": {
            "regs": [
                re.compile(r"在.*合同.*后.*个工作日内.*?合同总金?额的?\s*(?P<tar>.*[%％])"),
            ]
        },
        "第二笔付款大写": {
            "regs": [
                re.compile(r"验收合格后.*个工作日内.*?(即|计)\s?(.*?元?)[(（]大写[:：]?(?P<tar>.*?)[）)]"),
                re.compile(
                    r".*年.*月.*日前，甲方应支付.*?（合计[(（]小写[）)](.*?元?)(人民币)?[(（]大写[）)](?P<tar>.*?)）"
                ),
            ]
        },
        "第二笔付款小写": {
            "regs": [
                re.compile(r"验收合格后.*个工作日内.*?(即|计)\s?(?P<tar>.*?元?)[(（]大写[:：]?(.*?)[）)]"),
                re.compile(
                    r".*年.*月.*日前，甲方应支付.*?（合计[(（]小写[）)](?P<tar>.*?元?)(人民币)?[(（]大写[）)](.*?)）"
                ),
            ]
        },
        "第二笔付款比例": {
            "regs": [
                re.compile(r"验收合格后.*个工作日内.*?合同总金?额的?\s*(?P<tar>.*[%％])"),
                re.compile(r".*年.*月.*日前，甲方应支付合同总金?额的?\s*(?P<tar>.*[%％])"),
            ]
        },
        "第三笔付款大写": {
            "regs": [
                re.compile(
                    r"在软件(试运行|验收合格后).*月(后|内).*?(即|计)\s?(.*?元?)[(（]大写[:：]?(?P<tar>.*?)[）)]"
                ),
                re.compile(r"在软件验收合格届满.*年后.*?(即|计)\s?(.*?元?)[(（]大写[:：]?(?P<tar>.*?)[）)]"),
                re.compile(r"本项目外包期限到期后.*?（合计[(（]小写[）)](.*?元?)(人民币)?[(（]大写[）)](?P<tar>.*?)）"),
            ]
        },
        "第三笔付款小写": {
            "regs": [
                re.compile(
                    r"在软件(试运行|验收合格后).*月(后|内).*?(即|计)\s?(?P<tar>.*?元?)[(（]大写[:：]?(.*?)[）)]"
                ),
                re.compile(r"在软件验收合格届满.*年后.*?(即|计)\s?(?P<tar>.*?元?)[(（]大写[:：]?(.*?)[）)]"),
                re.compile(r"本项目外包期限到期后.*?（合计[(（]小写[）)](?P<tar>.*?元?)(人民币)?[(（]大写[）)](.*?)）"),
            ]
        },
        "第三笔付款比例": {
            "regs": [
                re.compile(r"在软件(试运行|验收合格后).*月(后|内).*?合同总金?额的\s*(?P<tar>.*[%％])"),
                re.compile(r"在软件验收合格届满.*年后.*?合同总金?额的\s*(?P<tar>.*[%％])"),
                re.compile(r"本项目外包期限到期后.*合同总金?额的?\s*(?P<tar>.*[%％])"),
            ]
        },
        "第四笔付款大写": {"regs": []},
        "第四笔付款小写": {"regs": []},
        "第四笔付款比例": {"regs": []},
        "不含税合同总金额大写": {
            "regs": [
                re.compile(r"不含税金额为[:：]?(.*?元?)[(（]大写[:：]?(?P<tar>.*?)[）)]"),
            ]
        },
        "不含税合同总金额小写": {
            "regs": [
                re.compile(r"不含税金额为[:：]?(?P<tar>.*?元?)[(（]大写[:：]?(.*?)[）)]"),
                re.compile(r"不含税价[:：]?(人民币)?(?P<tar>.*?元)，"),
            ]
        },
        "税款大写": {
            "regs": [
                re.compile(r"增值税款为[:：]?(.*?)元?[(（]大写[:：]?(?P<tar>.*?)[）)]"),
            ]
        },
        "税款小写": {
            "regs": [
                re.compile(r"增值税款为[:：]?(?P<tar>.*?元?)[(（]大写[:：]?(.*?)[）)]"),
                re.compile(r"不含税价[:：]?(人民币)?(.*?元?)，增值税[:：]?(人民币)?(?P<tar>.*?元)。"),
            ]
        },
        "维护费用大写": {
            "regs": [
                re.compile(
                    r"甲方应向乙方支付维护培训服务费用.*?每年费用为合同总金额.*?(即|计)\s?(.*?)元?[(（]大写[:：]?(?P<tar>.*?)[）)]"
                ),
                re.compile(r"甲方应向乙方支付维护培训服务费用合计(.*?元?)[(（]大写[:：]?(?P<tar>.*?)[）)]"),
                re.compile(r"甲方应向乙方支付维护培训服务费用收取标准为(?P<tar>.*合同金额的.*%)"),
                re.compile(r"甲方应向乙方支付维护培训服务费用.*?(?P<tar>合同总?金额的.*%)"),
            ]
        },
        "维护费用小写": {
            "regs": [
                re.compile(
                    r"甲方应向乙方支付维护培训服务费用.*?每年费用为合同总金额.*?(即|计)\s?(?P<tar>.*?元?)，?[(（]大写[:：]?(.*?)[）)]"
                ),
                re.compile(r"甲方应向乙方支付维护培训服务费用合计(?P<tar>.*?元?)[(（]大写[:：]?(.*?)[）)]"),
                re.compile(r"甲方应向乙方支付维护培训服务费用收取标准为(?P<tar>.*合同金额的.*%)"),
                re.compile(r"甲方应向乙方支付维护培训服务费用.*?(?P<tar>合同总?金额的.*%)"),
            ]
        },
        "最后一笔费用支付": {
            "regs": [
                re.compile(r"(?P<tar>在软件验收合格届满.*?)[，。]"),
            ]
        },
        "增值税使用税率": {
            "regs": [
                re.compile(r"适用税率为[:：]?(?P<tar>.*?)[。]"),
            ]
        },
        "乙方纳税人资质": {
            "regs": [
                re.compile(r"乙方声明具有增值税(?P<tar>.*?)[，。]"),
            ]
        },
        "甲方项目经理": {
            "regs": [
                re.compile(r"甲方指定[:：]?(?P<tar>.*?)为甲方在该项目上的全权代表"),
            ]
        },
        "乙方项目经理": {
            "regs": [
                re.compile(r"乙方指定[:：]?(?P<tar>.*?)为乙方在该项目上的全权代表"),
            ]
        },
    }

    term_patterns = {
        "增值税涉税固定条款1": {
            "regs": [
                re.compile(r"劳务清单"),
                re.compile(r"税收法规或税务机关"),
                re.compile(r"直接与间接损失"),
                re.compile(r"行政机关"),
            ],
            "limit": 3,
        },
        "增值税涉税固定条款2": {
            "regs": [
                re.compile(r"挂号信件"),
                re.compile(r"特快专递"),
                re.compile(r"逾期送达"),
                re.compile(r"重新开具合法发票"),
            ],
            "limit": 3,
        },
        "增值税涉税固定条款3": {
            "regs": [
                re.compile(r"丢失或被盗"),
                re.compile(r"未顺利送达"),
                re.compile(r"遭受的经济损失"),
                re.compile(r"负责赔偿"),
            ],
            "limit": 3,
        },
        "增值税涉税固定条款4": {
            "regs": [
                re.compile(r"相关票据"),
                re.compile(r"按照相关税收法律法规提供有关资料"),
            ],
            "limit": 2,
        },
        "知识产权": {
            "regs": [
                re.compile(r"根据本合同产生的全部开发成果"),
                re.compile(r"知识产权全部"),
                re.compile(r"进行后续改进"),
                re.compile(r"本协议交付的开发成果为基础进行后续改进"),
                re.compile(r"权利归属"),
                re.compile(r"各类素材"),
                re.compile(r"知识产权或信息专有"),
                re.compile(r"提出侵权指控"),
            ],
            "limit": 2,
            "cnt_of_res": 5,
        },
        "代码功能范围条款": {
            "regs": [
                re.compile(r"恶意代码或未授权"),
                re.compile(r"证券期货行业有关技术规范"),
                re.compile(r"技术指引"),
            ],
            "limit": 2,
        },
        "信息安全条款": {
            "regs": [
                re.compile(r"信息安全延伸检查"),
                re.compile(r"证券期货行业监管部门"),
            ],
            "limit": 2,
        },
        "系统漏洞条款": {
            "regs": [
                re.compile(r"软件后门"),
                re.compile(r"其他软件"),
                re.compile(r"第三方的损失"),
            ],
            "limit": 2,
        },
        "数据安全条款": {
            "regs": [
                re.compile(r"因软件自身漏洞"),
                re.compile(r"甲方客户的数据"),
            ],
            "limit": 2,
        },
        "重大事项告知条款": {
            "regs": [
                re.compile(r"产品结束"),
                re.compile(r"公司更换"),
                re.compile(r"发生重大事项"),
            ],
            "limit": 2,
        },
        "应急预案条款": {
            "regs": [
                re.compile(r"重大异常情况"),
                re.compile(r"乙方应协助"),
                re.compile(r"降到最低"),
            ],
            "limit": 3,
        },
        "乙方权利和义务-保密责任": {
            "regs": [
                re.compile(r"甲方的任何资料"),
                re.compile(r"无论是书面的还是电子的"),
                re.compile(r"任何交付物"),
                re.compile(r"擅自使用"),
                re.compile(r"公开发表"),
            ],
            "limit": 3,
        },
        "保密责任": {
            "regs": [
                re.compile(r"如拥有另一方"),
                re.compile(r"必要的步骤"),
                re.compile(r"违反本条造成损失"),
            ],
            "limit": 2,
        },
        "违约责任1": {
            "regs": [
                re.compile(r"甲方逾期付款"),
                re.compile(r"单方解除合同"),
                re.compile(r"违约方支付合同总价款"),
            ],
            "limit": 2,
        },
        "违约责任2": {
            "regs": [
                re.compile(r"项目软件符合甲方要求"),
                re.compile(r"质量问题"),
                re.compile(r"排除缺陷"),
                re.compile(r"性能和质量不符合"),
            ],
            "limit": 2,
        },
        "违约责任3": {
            "regs": [
                re.compile(r"在法律允许的范围内"),
                re.compile(r"全部责任不超过"),
            ],
            "limit": 2,
        },
        "违约责任4": {
            "regs": [
                re.compile(r"上述规定在本合同终止或到期后仍然有效"),
            ],
            "limit": 1,
        },
        "附件-项目工作说明书": {
            "regs": [
                re.compile(r"(?P<tar>.*项?目?工作说明书\s*$)"),
            ],
            "limit": 1,
        },
        "附件-保密协议": {
            "regs": [
                re.compile(r"(?P<tar>.*项目保密协议\s*$)"),
            ],
            "limit": 1,
        },
        "售后服务支持": {
            "regs": [
                re.compile(r"在验收合格后"),
                re.compile(r"免费的售后服务"),
                re.compile(r"出现故障时应及时"),
                re.compile(r"特殊情况双方协商"),
                re.compile(r"诊断并排除"),
            ],
            "limit": 2,
            "cnt_of_res": 5,
        },
        "质量考核标准": {
            "regs": [
                re.compile(r"质量考核标准"),
            ],
            "anchor_reg": re.compile(r"项目工作说明书"),
            "cnt_of_anchor_elts": 10,
            "cnt_of_res": 1,
            "limit": 1,
        },
        "持续监控机制": {
            "regs": [
                re.compile(r"持续监控机制"),
            ],
            "anchor_reg": re.compile(r"项目工作说明书"),
            "cnt_of_anchor_elts": 10,
            "cnt_of_res": 1,
            "limit": 1,
        },
        "项目变更管理": {
            "regs": [
                re.compile(r"项目变更管理"),
                re.compile(r"导致工作量增加"),
                re.compile(r"超过部分"),
                re.compile(r"补充协议"),
            ],
            "limit": 4,
        },
        "应急预案条款（甲方）": {
            "regs": [
                re.compile(r"甲方有权"),
                re.compile(r"重大异常情况"),
                re.compile(r"变更协议合作方"),
                re.compile(r"应急处置流程"),
            ],
            "limit": 4,
        },
        "乙方服务承诺": {
            "regs": [
                re.compile(r"信息技术服务"),
                re.compile(r"服务的任何环节"),
                re.compile(r"转委托第三方"),
                re.compile(r"设置技术壁垒"),
                re.compile(r"违反现行法律法规"),
                re.compile(r"中国证监会禁止的"),
                re.compile(r"截取.*?存储.*?转发"),
                re.compile(r"社会公开发布.*?系统压力测试.*?网络安全信息"),
            ],
            "limit": 1,
            "cnt_of_res": 8,
        },
        "合同效力": {
            "regs": [
                re.compile(r"本合同一经签署"),
                re.compile(r"随意更改本合同"),
                re.compile(r"同等效力"),
                re.compile(r"签订书面协议"),
            ],
            "limit": 3,
        },
        "乙方权利和义务-安全生产相关条款": {
            "regs": [
                re.compile(r"熟练掌握事故防范措施和事故应急处理预案"),
                re.compile(r"建立健全各项劳动安全制度以及相应的劳动安全保护措施"),
            ],
            "limit": 2,
            "cnt_of_res": 1,
        },
        "乙方项目人员-安全生产相关条款": {
            "regs": party_employee_regs.values(),
            "limit": 1,
            "cnt_of_res": 6,
        },
        "乙方义务-备案监督条款": {
            "regs": partyb_obligations_regs["备案监督条款"],
            "limit": 1,
            "cnt_of_res": 2,
        },
        "乙方义务-违规监督条款": {
            "regs": partyb_obligations_regs["违规监督条款"],
            "limit": 1,
            "cnt_of_res": 2,
        },
        "乙方义务-纠纷、仲裁告知条款": {
            "regs": partyb_obligations_regs["纠纷、仲裁告知条款"],
            "limit": 1,
            "cnt_of_res": 2,
        },
        "乙方义务-违规采购条款": {
            "regs": partyb_obligations_regs["违规采购条款"],
            "limit": 1,
            "cnt_of_res": 2,
        },
        "乙方义务-合规管理条款": {
            "regs": partyb_obligations_regs["合规管理条款"],
            "limit": 1,
            "cnt_of_res": 2,
        },
        "乙方义务-质量控制条款": {
            "regs": partyb_obligations_regs["质量控制条款"],
            "limit": 1,
            "cnt_of_res": 2,
        },
    }
