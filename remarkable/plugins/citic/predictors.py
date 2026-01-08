import functools
import re
from collections import OrderedDict
from copy import deepcopy
from itertools import chain

from remarkable.common.util import clean_txt, index_in_space_string
from remarkable.predictor.predict import AnswerPredictor, CharResult, ParaResult, ResultOfPredictor


def match_regs(regs, text):
    for reg in regs:
        matched = reg.search(text)
        if matched:
            return matched
    return None


class FundationContractPredictor(AnswerPredictor):
    keyword_patterns = {
        "首次认购下限": re.compile(r"\d+[十百千万]*元(人民币)?"),
        "追加认购下限": re.compile(r"\d+[十百千万]*元(人民币)?"),
        "巨额赎回认定标准": re.compile(r"\d+%"),
    }

    def __init__(self, *args, **kwargs):
        super(FundationContractPredictor, self).__init__(*args, **kwargs)
        self.sorted_elements = OrderedDict()

        if self.reader:
            for idx, _ in sorted(self.reader.data["_index"].items(), key=lambda x: x[0]):
                typ, elt = self.reader.find_element_by_index(idx)
                self.sorted_elements.setdefault(idx, elt)

        self.attr2reg = {
            "业绩报酬提取比例": {
                "regs": [
                    re.compile(r"(?P<target>(不[收提]取([^，。]*?的)?|无)业绩报酬)"),
                    re.compile(r"(?P<target>无私募基金管理人业绩报酬)"),
                    re.compile(r"业绩报酬的?提取比例(合计)?[为是](?P<target>\d+%)"),
                    re.compile(r"×(?P<target>\d+%)×T日基金总份额"),
                    re.compile(r"(?P<target>\d+%)(作为|提取|计提)业绩报酬"),
                    re.compile(r"(?P<target>本基金剩余基金资产全部作为业绩报酬归基金管理人所有)"),
                    re.compile(r"×(?P<target>\d+%)×产品结束当日基金份额"),
                    re.compile(r"业绩报酬计提基准[:：为]*(?P<target>【?\d+(\.\d+)%?】?%?)"),
                    re.compile(r"份额基准收益=.*?(?P<target>\d+(\.\d+)%)"),
                    re.compile(r"(?P<target>提取标准是.*?作为业绩报酬)"),
                    re.compile(r"提取(?P<target>[\s\d,%]+)(作为)?业绩报酬"),
                ]
            },
            "托管费支付频率": {
                "regs": [
                    re.compile(r"(?P<target>按(自然)?[年季月日]度?([(（]自然[年季月日]度?[)）])?(支付|收取))"),
                    re.compile(r"(?P<target>逐日累计至每个分配基准日)"),
                    re.compile(r"(?P<target>前\d+[年月日]托管费.*?支付.*?后续.*?支付)"),
                    re.compile(r"(?P<target>自封闭运作日起.*?支付)"),
                    re.compile(r"托管费.*?(?P<target>每半?年([^，。]*?)?应?该?(计提[并和及与])?支付(一次)?)"),
                    re.compile(r"(?P<target>每半?年([^，。]*?)?应?该?(计提[并和及与])?支付(一次)?).*托管费"),
                    re.compile(r"托管费自本基金(的基金)?成立之?日起(计算)?，(?P<target>.*?支付)"),
                    re.compile(r"(?P<target>分.次计提及支付)"),
                    re.compile(r"(?P<target>本计划[^，。]*一次性支付)"),
                ],
                "anchor_reg": re.compile(r"托管费"),
                "anchor_amount": 3,
                "include": True,
            },
            "管理人名称": {
                "regs": [
                    re.compile(
                        r"((基金|资产)管理人|名称)[:：](?P<target>.*(投资|管理|发展|期货|资产|合伙)+([(（].{2,4}[)）])?(集团|股份|有限)*(公司|企业))"
                    ),
                    re.compile(
                        r"本合伙企业之?唯一普通合伙人(的名称)?为【?(?P<target>.*(投资|管理|发展|期货|资产)+([(（].{2,4}[)）])?(集团|股份|有限)*公司)】?"
                    ),
                    re.compile(
                        r"(?P<target>[\u4e00-\u9fa5]{2,5}(投资|管理|发展|期货|资产|合伙){2,}([(（].{2,4}[)）])?(集团|股份|有限)*(公司|企业))"
                    ),
                    re.compile(r"管理人[:：](?P<target>[\u4e00-\u9fa5]+公司)"),
                ]
            },
            "收取管理费开户行": {
                "regs": [
                    re.compile(r"(?P<target>不收取管理费)"),
                    re.compile(r"开户银?行(名称)?[:：](?P<target>.*)"),
                ],
                "anchor_reg": re.compile(r"管理[人费]"),
            },
            "预警线": {
                "regs": [
                    re.compile(r"(?P<target>不设置(预警止损机制|预警线、止损线/补仓止损线))"),
                    re.compile(r"预警线[:：]本?(基金|计划)(份额|单位)净值[【\[]?(?P<target>[\d.]+元?)[】\]]?"),
                    re.compile(r"将(计划|基金)份额净值为?[【\[]?(?P<target>\d+(\.\d+)[】\]]?元?)[】\]]?设置为预警线"),
                    re.compile(r"预警线[:：](?P<target>[\d.]+)"),
                    re.compile(r"预警线、止损线分别为.*?(?P<target>[\d.,]+元)"),
                ]
            },
            "管理人联系地址": {
                "regs": [
                    re.compile(r"((通[讯信]|办公)地址|住所)[:：](?P<target>.*)"),
                    re.compile(r"(?P<target>.*?银行.*?公司)"),
                ],
                "anchor_reg": re.compile(r"管理人"),
            },
            "巨额赎回认定标准": {
                "regs": [
                    re.compile(
                        r"(?P<target>不(设开放日)?(开放|办理|设[置立]?|接受)((基金)?投资者的?)?(申购和?)?赎回(业务|申请)?)"
                    ),
                    # re.compile(r'总份额的【?(?P<target>\d+%)】?时?，即认为(本?(基金|资产管理计划)|是)发生了巨额(赎回|退出)'),
                    re.compile(r"总份额的[[【]?(?P<target>\d+%)[]】]?"),
                ]
            },
            "托管费计算公式-费率": {
                "regs": [
                    re.compile(r"[A-Za-z]\d?[=＝].*?(?P<target>[\d.,]+[%‰])"),
                    re.compile(r"实缴出资额总和的(?P<target>\d+(\.\d+)?[%‰])"),
                    re.compile(r"按.*?基金资产净值的(?P<target>\d+(\.\d+)?[%‰])"),
                    re.compile(r"年费率(.*?)[为是:：](?P<target>\d+(\.\d+)?[%‰])"),
                    re.compile(r"(?P<target>不收取托管费)"),
                ],
                "anchor_reg": re.compile(r"托管费"),
                "anchor_amount": 3,
                "include": True,
            },
            "托管费计算公式-保底费": {
                "regs": [
                    re.compile(r"(?P<target>不收取托管费)"),
                    re.compile(r"年度?托管费为(?P<target>[\u4e00-\u9fa5]*?[\d.,十百千万亿]*元)"),
                    re.compile(r".*?托管费.*?(不?低于|不足)(?P<target>[\d.,十百千万亿【】\[\]]*元)"),
                    re.compile(r".*?托管费.*?最低值为每年(?P<target>[\d.,十百千万亿【】\[\]]*元)"),
                ]
            },
            "认购利息归属": {
                "regs": [
                    re.compile(r"基金成立后(实际结息时归入|的适当时间返还给)(?P<target>.*?)[。，]"),
                    re.compile(
                        r"(认购资金所|初始销售期间?)?(产生|形成)的利息([(（][\u4e00-\u9fa5]+[）)])?[计归]入(?P<target>[\u4e00-\u9fa5]+)"
                    ),
                    re.compile(r"在募集期结束时归入(?P<target>[\u4e00-\u9fa5]+)并"),
                    re.compile(r"实际结息到账金额归入(?P<target>[\u4e00-\u9fa5]+)"),
                    re.compile(r"(产生|形成)的利息([(（][\u4e00-\u9fa5]+[）)])?[计归]入(?P<target>[\u4e00-\u9fa5]+)"),
                    re.compile(r".*利息.*[计归](?P<target>.*?)所有"),
                ]
            },
            "风险等级": {
                "regs": [
                    re.compile(
                        r"本.*?(基金|计划|产品).*?属于[【\[]?(?P<target>.*?)[】\]]?(级基金产品|级?的?风?险?投资品种|风险(等级|级别))"
                    ),
                    re.compile(r"风险.级([:：]|为).*?[【\[]?(?P<target>\w\d)[】\]]?", re.I),
                    re.compile(r"[【\[]?(?P<target>R\d)[】\]]?级?风险投资品种", re.I),
                ]
            },
            "募集户账号": {
                "regs": [
                    re.compile(r"账号[:：](?P<target>[\d\s\[\]【】]*)"),
                ],
                "pass_reg": re.compile(r".*费.*账[户号]"),
            },
            "存续期限": {
                "regs": [
                    re.compile(r"存续期限自交割日.*?起至?满(?P<target>[\d一二三四五六七八九十]+(（\d+）)?年)之日止"),
                    re.compile(r"(?P<target>自本合伙企业首次交割日.*?起至?.*?止)"),
                    re.compile(r"(?P<target>自基金成立日起至.*?之日止)"),
                    re.compile(r"存续期限?[将为是:：]+[【\[]?(?![系指])(?P<target>.*?)[】\]]?(。|$)"),
                    re.compile(r"(?P<target>(不定期|无固定存续期|永续))"),
                    re.compile(r"^[【\[]?(?P<target>[\d\s年月日]*)[】\]]?。?$"),
                    re.compile(r"[【\[]?(?P<target>\d+个?[年月])[】\]]?[，。].*?基金管理人.*提前终止"),
                ],
                "anchor_reg": re.compile(r"存续期限?"),
                "anchor_amount": 3,
                "include": True,
            },
            "开放日": {
                "regs": [
                    re.compile(
                        r"本基金的?开放日为(?P<target>自?基金(成立|封闭期结束)后.*的\d+日(，.遇节假日则顺延至下一(交易|工作)日)?)"
                    ),
                    re.compile(
                        r"(?P<target>本基金的?首个开放日为(基金)?封闭期结束日.*(，.遇节假日则顺延至下一(交易|工作)日)?)"
                    ),
                    re.compile(r"(?P<target>本基金无固定开放日([，。]管理人可.*自主设立临时开放日.*。)?)"),
                    re.compile(r"(?P<target>在?本基金存续期[内间].?不设置固定开放日(..*?申购和赎回.*?管理人)?)"),
                    re.compile(
                        r"(?P<target>在?本基金在?存续期[内间]封闭式?运作[，。]不(办理|开放|接受)([\u4e00-\u9fa5]+)?申购[和、]赎回(业务|申请))"
                    ),
                    re.compile(r"(?P<target>(固定|首个)开放日为.*(如遇节假日则顺延至下一(交易|工作)日[)）]?))"),
                    re.compile(r"(?P<target>可设置临时开放日)"),
                    re.compile(
                        r"(?P<target>本?基金(原则上)?封闭式?运作[，。]但?.*?设立临时开放日[，。].*?申购.*?赎回)"
                    ),
                    re.compile(r"(?P<target>征询.*?期满.*?基金管理人安排临时开放日)"),
                    re.compile(r"(?P<target>本基金原则上封闭式?运行.*?临时开放日仅?允许申购.*?赎回)"),
                    re.compile(r"本基金的开放日[:：](?P<target>.*?)。"),
                    re.compile(r"(?P<target>本计划的退出开放日为.*?遇节假日则顺延至下一工作日)"),
                    re.compile(
                        r"(?P<target>本资产管理人?计划为?(半封闭|开放)式?运作(，无固定开放日)?，管理人可根据需要(增加|设置)临时开放日)"
                    ),
                    re.compile(r"开放日为(?P<target>每个?(自然)?月的?第?\d+日)"),
                    re.compile(r"(本基金)?的?开放日为(?P<target>[^，]*?)。"),
                    re.compile(r"(?P<target>成立之日起.*?设立临时开放日)"),
                    re.compile(r"(?P<target>每个开放日.*?。)"),
                ]
            },
            "认购费归属": {
                "regs": [
                    re.compile(r"(认购|入伙)费用?.*归(?P<target>[^，。]*?)所有"),
                    re.compile(
                        r"(认购|入伙)费用?归[\[【]?(?P<target>(基金管理人|普通合伙人)([(（]?或代销机构[)）]?)?)[】\]]?所有"
                    ),
                    re.compile(r"(?P<target>不收取认购费用?)"),
                ]
            },
            "首次认购下限": {
                "regs": [
                    re.compile(
                        r"""
                        (在(募集|初始销售)期[间限]的认购|发起资金|基金投资者首次净认购|投资者认缴的|初始认购)
                        (出资)?[金数]?额应?不得?[低少]于[\[【]?(?P<target>(人民币)?\d+[十百千万]*元(人民币)?)[】\]]?
                    """,
                        re.X,
                    ),
                    re.compile(r"新入伙(有限|普通)合伙人出资起点为(?P<target>\d+[十百千万]*元)"),
                    re.compile(
                        r"初始委托财产([金数]?额应?)?不得?[低少]于[\[【]?(?P<target>(人民币)?\d+[十百千万]*元(人民币)?)[】\]]?"
                    ),
                ]
            },
            "追加认购下限": {
                "regs": [
                    re.compile(r"追加认购[金数]额应?(不得?[低少]于|为)(?P<target>[\[【]?.*?元人民币[】\]]?)"),
                    re.compile(r"按照?(?P<target>[\d\s,十百千万亿]*元(人民币)?)的整数倍增加"),
                    re.compile(r"追加委托投资金额应为((?P<target>\d+[十百千万]*元(人民币)?)的整数倍)"),
                    re.compile(r"追加委托投资金额单笔最低限额为(?P<target>(人民币)?\d+[十百千万]*元(人民币)?)"),
                ],
            },
            "认购费率": {
                "regs": [
                    re.compile(r"(?P<target>[无不](需[缴交]纳|收取)(认购|入伙)费用?)"),
                    re.compile(
                        r"(认购|入伙)费[用率]为(认购金|实缴出资总?)额的[\[【]?(?P<target>\d+(\.\d+)?[%‰％])[】\]]?"
                    ),
                    re.compile(r"认购费率[:：为是]+[\[【]?(?P<target>\d+(\.\d+)?[%‰％])[】\]]?"),
                    re.compile(r"则(认购|入伙)费[用率]为[\[【]?(?P<target>\d+(\.\d+)?[%‰％])[】\]]?"),
                    re.compile(r"(?P<target>无认购费用)"),
                    re.compile(r"[认申]购/[认申]购费费?率为(?P<target>\d+[%‰％])"),
                    re.compile(r"[缴交]纳[\[【]?(?P<target>\d+(\.\d+)?[%‰％])[】\]]?的?(认购|入伙)费[用率]"),
                ]
            },
        }

        self.regs = {
            "产品基本信息": [
                {"name": "产品名称", "func": self.product_name},
                {"name": "产品类型", "func": self.product_type},
                {
                    "name": "产品成立日",
                    "regs": [
                        re.compile(r"(?P<target>成立日以.*)为准"),
                        re.compile(r"(?P<target>成立公告.*?本计划成立日)"),
                        re.compile(r"(?P<target>本基金(?:初始募集|募集期结束|募集期内).*(基金成立|到达托管账户之日))"),
                        re.compile(r"(?:成立日为)?(?P<target>募集资金到达托管账户之日)"),
                        re.compile(r"(?P<target>(?:资产管理人|委托人).*(?:书面通知|委托).*(?:成立|起始日))"),
                        re.compile(r"[即自从](?P<target>.*?之?日(起|生效).*)"),
                        re.compile(r"(?P<target>私募基金.*基金成立公?告?)"),
                        re.compile(r"(?P<target>以《.+》.*作为.*(成立|起始)日?)"),
                        re.compile(r"(?P<target>(?:计划|募集规模).*可?成立)"),
                        re.compile(r"即(?P<target>.*?之日)"),
                    ],
                },
                {"name": "是否结构化", "func": self.structuralization},
                {
                    "name": "风险等级",
                    "regs": [
                        re.compile(
                            r"本.*?(基金|计划|产品).*?属于[【\[]?(?P<target>.*?)[】\]]?(级基金产品|级?的?风?险?投资品种|风险(等级|级别))"
                        ),
                        re.compile(r"风险.级([:：]|为).*?[【\[]?(?P<target>\w\d)[】\]]?", re.I),
                        re.compile(r"[【\[]?(?P<target>R\d)[】\]]?级?风险投资品种", re.I),
                    ],
                },
                {
                    "name": "投资者风险等级",
                    "regs": [
                        re.compile(r"[（【\[](?P<target>C.*)[】）\]].*投资者"),
                        re.compile(r"[【[](?P<target>[中高]+)[】\]]的合格投资者"),
                        re.compile(r"(?P<target>.{2}型).*投资者"),
                        re.compile(r"[【\[](?P<target>.{2}型.*)[】\]]的合格投资者"),
                        re.compile(r"[^C\d【](?P<target>.{2}型)"),
                        re.compile(r"适合风险识别、评估、承受能力\[(?P<target>.*)\]及以上级别的合格投资者"),
                        re.compile(r"适合风险识别、评估、承受能力\[(?P<target>.*)\]级别的合格投资者"),
                        re.compile(r"属于(?P<target>.*)高收益特征的证券投资品种"),
                        re.compile(r"适配风险评级为(?P<target>.*)级.*?合格投资者及专业投资者"),
                        re.compile(r"适合风险承受能力等级为(?P<target>.*)类投资者"),
                        re.compile(r"适用于风险承受等级为(?P<target>[CR]\d)及以上的委托人"),
                        re.compile(r"适合风险识别、评估、承受能力评?级?为?(?P<target>.*)的合格投资者"),
                        re.compile(r"本计划的风险等级为(?P<target>R\d)"),
                    ],
                },
                {
                    "name": "存续模式",
                    "regs": [
                        re.compile(r"(?<=合伙企业).*起?满(?P<target>.+?[年月日])"),
                        re.compile(r"合伙期限为?(?P<target>.+?[年月日])"),
                    ]
                    + self.attr2reg["存续期限"]["regs"],
                },
                {
                    "name": "存续期",
                    "regs": [
                        re.compile(r"存续期限.*起始运作日起(?P<target>.*?[天月年])"),
                        re.compile(r"本计划自成立之日起的?(?P<target>.*?[天月年])为固定存续期限"),
                        re.compile(r"本集合计划的存续时间为(?P<target>.*?[天月年])"),
                        re.compile(r"委托管理期限为自起始日起满(?P<target>.*?月)止"),
                        re.compile(r"自合同生效之日起(?P<target>.*?[年月日]).*终止本计划.*延长存续期限"),
                        re.compile(r"本计划存续期限(?P<target>.*?[年月日]).*提前终止"),
                        re.compile(r"存续期限?[将为是:：].*?其中(?P<target>.*[天日月年])投资期(?=[，。])"),
                        re.compile(r"存续期限?[将为是:：](?P<target>.*之日)(?=。)"),
                        re.compile(r"存续期限?[将为是:：](?P<target>.*?([年月]))(?=[，。])"),
                        re.compile(
                            r"(?:存续期限自交割日|合伙企业首次交割日).*?起至?满(?P<target>[\d一二三四五六七八九十]+(（\d+）)?年)之日止"
                        ),
                        re.compile(r"(?P<target>自本合伙企业首次交割日.*?起至?.*?止)"),
                        re.compile(r"(?P<target>自基金成立日起至.*?之日止)"),
                        re.compile(r"存续期限?[将为是:：]+[【\[]?(?![系指])(?P<target>.*?)[】\]]?(。|$)"),
                        re.compile(r"(?P<target>(不定期|无固定存续期|永续))"),
                        re.compile(r"^[【\[]?(?P<target>[\d\s年月日]*)[】\]]?。?$"),
                        re.compile(r"[【\[]?(?P<target>\d+个?[年月])[】\]]?[，。].*?基金管理人.*提前终止"),
                        re.compile(r"合伙期限为?(?P<target>.+?[年月日天])"),
                        re.compile(r"(?<=合伙企业).*起?满(?P<target>.+?[年月日天])"),
                    ],
                },
                {
                    "name": "封闭期",
                    "regs": [
                        re.compile(r"本基金的?封闭期([:：]|为)(?P<target>自?(本?基金)?自?成立之?日起\d+个月|无)。?"),
                        re.compile(r"(?P<target>本基金原则上封闭运作.*?本基金封闭运作，不(办理|开放)申购赎回业务。)"),
                        re.compile(r"(?P<target>在?本基金存续期[内间]封闭式?运作[，。]不(办理|开放)申购和赎回业务)"),
                        re.compile(r"本计划封闭期指(?P<target>计划成立之日起至.*止)"),
                        re.compile(r"(?P<target>自[本该]?(基金|计划)成立之日起\d+个月)"),
                        re.compile(r"^(?P<target>无)。"),
                        re.compile(r"(?P<target>本资产管理人计划半封闭运作，管理人可根据需要增加临时开放日)"),
                        re.compile(r"(?P<target>本(资产管理人|集合)计划存续期内封闭式?运[行作])"),
                        re.compile(r"封闭期[：:](?P<target>(本?(基金|计划))?(原则上)?自.*?)。"),
                        re.compile(r"封闭期[：:](?P<target>(本?(基金|计划))?(原则上)?封闭式?运作)。"),
                        re.compile(r"(?P<target>本基金原则上封闭运作.*?临时开放日.*?申购.*?赎回)"),
                        re.compile(r"(?P<target>本基金原则上封闭运行)"),
                        re.compile(r"本基金的封闭期：(?P<target>.*?[年月])"),
                        re.compile(r"本基金的封闭期：本基金的封闭期为(?P<target>.*?[年月])"),
                        re.compile(r"本计划存续期内(?P<target>除开放日.*?期外为封闭期)"),
                        re.compile(r"本有限合伙企业的投资退出封闭期的初始期限为(?P<target>.*?[年月])"),
                        re.compile(r"封闭期自计划成立之日起(?P<target>.*?[年月])"),
                        re.compile(
                            r"(?P<target>有限合伙企业的投资退出封闭期的初始期限为.*，自首次交割日起算，其中前.*为投资期)"
                        ),
                        re.compile(r"(?P<target>[本该]?(基金|计划)[自在]?(成立之日起|存续期[间内]).*?封闭式?运作)"),
                    ],
                },
                {
                    "name": "开放日",
                    "regs": [
                        re.compile(
                            r"本基金的?开放日为(?P<target>自?基金(成立|封闭期结束)后.*的\d+日(，.遇节假日则顺延至下一(交易|工作)日)?)"
                        ),
                        re.compile(
                            r"(?P<target>本基金的?首个开放日为(基金)?封闭期结束日.*(，.遇节假日则顺延至下一(交易|工作)日)?)"
                        ),
                        re.compile(r"(?P<target>本基金无固定开放日([，。]管理人可.*自主设立临时开放日.*。)?)"),
                        re.compile(r"(?P<target>在?本基金存续期[内间].?不设置固定开放日(..*?申购和赎回.*?管理人)?)"),
                        re.compile(
                            r"(?P<target>在?本基金在?存续期[内间]封闭式?运作[，。]不(办理|开放|接受)([\u4e00-\u9fa5]+)?申购[和、]赎回(业务|申请))"
                        ),
                        re.compile(r"(?P<target>(固定|首个)开放日为.*(如遇节假日则顺延至下一(交易|工作)日[)）]?))"),
                        re.compile(r"(?P<target>可设置临时开放日)"),
                        re.compile(
                            r"(?P<target>本?基金(原则上)?封闭式?运作[，。]但?.*?设立临时开放日[，。].*?申购.*?赎回)"
                        ),
                        re.compile(r"(?P<target>征询.*?期满.*?基金管理人安排临时开放日)"),
                        re.compile(r"(?P<target>本基金原则上封闭式?运行.*?临时开放日仅?允许申购.*?赎回)"),
                        re.compile(r"本基金的开放日[:：](?P<target>.*?)。"),
                        re.compile(r"(?P<target>本计划的退出开放日为.*?遇节假日则顺延至下一工作日)"),
                        re.compile(
                            r"(?P<target>本资产管理人?计划为?(半封闭|开放)式?运作(，无固定开放日)?，管理人可根据需要(增加|设置)临时开放日)"
                        ),
                        re.compile(r"开放日为(?P<target>每个?(自然)?月的?第?\d+日)"),
                        re.compile(r"(本基金)?的?开放日为(?P<target>[^，]*?)。"),
                        re.compile(r"(?P<target>成立之日起.*?设立临时开放日)"),
                        re.compile(r"(?P<target>每个开放日.*?。)"),
                        re.compile(r"(?P<target>每月15日)开放申购和赎回"),
                        re.compile(
                            r"(?P<target>每月.*?日开放参与，每季度末月.*?日开放退出，如遇节假日顺延至下一个工作日)"
                        ),
                    ],
                },
                {
                    "name": "运作方式",
                    "regs": [
                        re.compile(r"运作方式：(?P<target>.*?)[，。,]"),
                        re.compile(r"运作方式：(?:本计划为)?[【]?(?P<target>.*式(?:运作|产品)?)[】]?"),
                        re.compile(r"[【](?P<target>.*式?(?:运作|产品)?)[】]"),
                        re.compile(r"(?P<target>原则上.*?)[，。,]"),
                        re.compile(
                            r"(?P<target>本资产管理计划.*成立之日起.*每满3个月.*遇非工作日.*下一个工作日开放参与、退出)"
                        ),
                        re.compile(
                            r"(?P<target>(?:本计划|本资产管理计划)?(?:定期|契约型)?(?:开放|半?封闭)式?运?作?)[。,，]?"
                        ),
                    ],
                    "anchor_reg": re.compile(r"(运作方式|\d+、封闭期)"),
                    "pass_reg": re.compile(r"认缴出资"),
                    "anchor_amount": 3,
                    "include": True,
                    "cnt_of_res": 1,
                },
                {"name": "是否允许合同展期", "func": self.allow_contract_extension},
                {"name": "是否允许临开", "func": self.temp_open},
                {
                    "name": "临开频率",
                    "regs": [
                        re.compile(r"临时开放日.*为(?P<target>\d.*)"),
                        re.compile(r"(?:设置|设立|本计划)临时开放日.*(?P<target>(?:每季度至少一次|连续2个工作日))"),
                    ],
                },
                {
                    "name": "初始面值",
                    "regs": [
                        re.compile(r"初始(?:销售|募集)?面值[为=](?P<target>\d+\.?\d*元)"),
                        re.compile(r"初始(?:销售|募集)?面值均?[为：]人民币(?P<target>\d+\.?\d*元)"),
                        re.compile(r"初始认购价格[为：](?P<target>\d+\.?\d*元)"),
                        re.compile(r"基金份额(?:发售|的)?面值[为：](?P<target>人民币\d+\.?\d*元)"),
                        re.compile(r"入伙价格为面值(?P<target>\d+\.?\d*元)"),
                        re.compile(r"(?P<target>人民币\d+\.?\d*元)"),
                    ],
                },
                {
                    "name": "资产净值精度",
                    "regs": [
                        re.compile(r"资产净值.*(?<!份额净值的计算保留到)小数点后(?P<target>\d+)位.*?"),
                    ],
                },
                {"name": "份额净值精度", "regs": [re.compile(r"份额净值.*小数点后(?P<target>\d+)位")]},
            ],
            "管理人及代销机构信息": [
                {
                    "name": "公司名称",
                    "regs": [
                        re.compile(r"名称[：:]\s?【(?P<target>.*?)】"),
                        re.compile(r"机?构?名称[：:]\s?(?P<target>.*)"),
                        re.compile(r"，[指即](?P<target>.*?公司)"),
                        re.compile(r"唯一普通合伙人的?名称为(?P<target>.*?公司)"),
                        re.compile(r"唯一普通合伙人的?名?称?为【(?P<target>.*?公司)】"),
                    ],
                },
                {
                    "name": "管理人登记编号",
                    "regs": [
                        re.compile(r"【(?P<target>.*?)】"),
                        re.compile(r"其管理人登记编.*?为(?P<target>.*?)。"),
                        re.compile(r"管理人登记编.*?为?[：:]?\s?(?P<target>.*?)。"),
                        re.compile(r"登记编码[：:]?\s?(?P<target>.*?)[\)）]"),
                    ],
                },
                {
                    "name": "住所",
                    "regs": [
                        re.compile(r"(住所|联系地址)[：:]\s?(?P<target>.*)"),
                    ],
                    "anchor_reg": re.compile(
                        r"基金管理人的基本信息|.*?基金管理人.*?的联系方式为|(资产|基金)管理人[简概]况|管理人概况|资产管理人|私募基金管理人"
                    ),
                },
                {
                    "name": "法定代表人/负责人",
                    "regs": [
                        re.compile(r"法定代表人(/负责人|或授权代表)?[：:]\s?(?P<target>.*)"),
                    ],
                },
                {
                    "name": "联系人",
                    "regs": [
                        re.compile(r"联系人[：:]\s?(?P<target>.*)"),
                    ],
                },
                {
                    "name": "联系地址",
                    "regs": [
                        re.compile(r"(联系|办公|通信|通讯)地址[：:]\s?(?P<target>.*)"),
                    ],
                },
                {
                    "name": "联系电话",
                    "regs": [
                        re.compile(r"联系电话[：:]\s?(?P<target>[\d-]*)"),
                        re.compile(r"联系电话[：:]\s?(?P<target>.*)"),
                    ],
                },
                {
                    "name": "代销机构名",
                    "regs": [
                        re.compile(r"名称[：:]\s?(?P<target>.*)"),
                    ],
                    "anchor_reg": re.compile(r"本基金代销(机构|账户)|代理销售处理|基金销售专用账户信息"),
                },
                {
                    "name": "代销机构联系地址",
                    "regs": [
                        re.compile(r"(联系|办公|通信|通讯)地址[：:]\s?(?P<target>.*)"),
                    ],
                    "anchor_reg": re.compile(r"本基金代销(机构|账户)|代理销售处理|基金销售专用账户信息"),
                },
                {
                    "name": "代销机构联系电话",
                    "regs": [
                        re.compile(r"联系电话[：:]\s?(?P<target>.*)"),
                    ],
                    "anchor_reg": re.compile(r"本基金代销(机构|账户)|代理销售处理|基金销售专用账户信息"),
                },
                {
                    "name": "代销机构邮箱",
                    "regs": [
                        re.compile(r"邮箱[：:]\s?(?P<target>.*)"),
                    ],
                    "anchor_reg": re.compile(r"本基金代销(机构|账户)|代理销售处理|基金销售专用账户信息"),
                },
                {
                    "name": "代销机构银行账户名",
                    "regs": [
                        re.compile(r"[开账]?户名称?.*?[：:]\s?[“【]?(?P<target>.*?(公司|（有限合伙）|专户))[”】]?"),
                    ],
                    "anchor_reg": re.compile(r"本基金代销(机构|账户)|代理销售处理|基金销售专用账户信息"),
                },
                {
                    "name": "代销机构银行账户",
                    "regs": [
                        re.compile(r"账号[：:]\s?[“【](?P<target>.*?)[”】]"),
                        re.compile(r"账号[：:]\s?(?P<target>\d*)"),
                    ],
                    "anchor_reg": re.compile(r"本基金代销(机构|账户)|代理销售处理|基金销售专用账户信息"),
                },
                {
                    "name": "代销机构开户行",
                    "regs": [
                        re.compile(r"开户银?行(全称)?[：:]\s?[“【](?P<target>.*?)[”】]"),
                        re.compile(r"开户银?行(全称)?[：:]\s?(?P<target>.*)"),
                    ],
                    "anchor_reg": re.compile(r"本基金代销(机构|账户)|代理销售处理|基金销售专用账户信息"),
                },
            ],
            "投资信息": [
                {"name": "投资范围", "func": self.investment_scope},
                {"name": "最大投资比例", "func": self.investment_ratio},
                {"name": "预警线", "func": self.warning_line},
                {
                    "name": "止损线",
                    "func": self.stop_loss_line,
                },
                {
                    "name": "业绩比较基准",
                    "regs": [
                        re.compile(r"(?P<target>无业绩比较基准)"),
                        re.compile(r"(?P<target>\d+\.?\d*[%％])"),
                        re.compile(r"(?P<target>无)。$"),
                        re.compile(r"业绩比较基准为?[：:](?P<target>.*[^。])"),
                    ],
                    "anchor_reg": re.compile(r"业绩比较[标基]准"),
                },
                {
                    "name": "基金经理姓名",
                    "regs": [
                        re.compile(r"投资经理[：为](?P<target>.*[^。，])[。，]?"),
                        re.compile(r"(?P<target>.*?)(?:女士|先生|：).*任?.*(?:经理|总监)"),
                        re.compile(r"(?P<target>.*?)，[男女]，"),
                    ],
                    "anchor_reg": re.compile(r"(简介|简历|投资经理)"),
                    "include": True,
                },
                {"name": "基金经理介绍", "func": self.manager_introduction},
                {
                    "name": "投资顾问名称",
                    "regs": [
                        re.compile(r"名称：(?P<target>.*)"),
                        re.compile(r"(?P<target>.*(?:不聘请|无)投资顾问)"),
                        re.compile(r"[“【\[](?P<target>[^“].*?)[”】\]].*[为是]投资顾问"),
                        re.compile(r"投资顾问[：]指?(?P<target>.*)"),
                        re.compile(r"(?P<target>本(资产管理)?计划不聘请投资顾问)"),
                        re.compile(r"管理人聘请(?P<target>.*公司)作为本资产管理计划的投资顾问"),
                        re.compile(r"资产管理人聘请【(?P<target>.*)】作为本资产管理计划的投资顾问"),
                    ],
                    "anchor_reg": re.compile(r"投资顾问|[、）]其他|风险提示"),
                    "anchor_amount": 7,
                    "include": True,
                    "step": -1,
                    "rough_fetch": True,
                },
                {
                    "name": "投资顾问住所",
                    "regs": [
                        re.compile(r"住所[：](?P<target>.*)"),
                        re.compile(r"(?P<target>.*(?:不聘请|无)投资顾问)"),
                        re.compile(r"(?P<target>本(资产管理)?计划不聘请投资顾问)"),
                    ],
                    "anchor_reg": re.compile(r"投资顾问|[、）]其他"),
                    "anchor_amount": 7,
                    "step": -1,
                    "rough_fetch": True,
                },
                {
                    "name": "投资顾问法定代表人/负责人",
                    "regs": [
                        re.compile(r"(?P<target>.*(?:不聘请|无)投资顾问)"),
                        re.compile(r"(?:法定代表人|负责任).*[:：](?P<target>.*)"),
                        re.compile(r"(?P<target>本(资产管理)?计划不聘请投资顾问)"),
                    ],
                    "anchor_reg": re.compile(r"投资顾问|[、）]其他"),
                    "anchor_amount": 7,
                    "step": -1,
                    "rough_fetch": True,
                },
                {
                    "name": "投资顾问营业执照号码",
                    "regs": [
                        re.compile(r"(?P<target>.*(?:不聘请|无)投资顾问)"),
                        re.compile(r"(?:营业执照号码|统一社会信用代码).*[:：](?P<target>.*)"),
                        re.compile(r"(?P<target>本(资产管理)?计划不聘请投资顾问)"),
                    ],
                    "anchor_reg": re.compile(r"投资顾问|[、）]其他"),
                    "anchor_amount": 7,
                    "step": -1,
                    "rough_fetch": True,
                },
                {
                    "name": "投资顾问联系人",
                    "regs": [
                        re.compile(r"(?P<target>.*(?:不聘请|无)投资顾问)"),
                        re.compile(r"联系人.*[:：](?P<target>.*)"),
                        re.compile(r"(?P<target>本(资产管理)?计划不聘请投资顾问)"),
                    ],
                    "anchor_reg": re.compile(r"投资顾问|[、）]其他"),
                    "anchor_amount": 7,
                    "step": -1,
                    "rough_fetch": True,
                },
                {
                    "name": "投资顾问通讯地址",
                    "regs": [
                        re.compile(r"(?P<target>.*(?:不聘请|无)投资顾问)"),
                        re.compile(r"(?:通讯地址|住所).*[:：](?P<target>.*)"),
                        re.compile(r"(?P<target>本(资产管理)?计划不聘请投资顾问)"),
                    ],
                    "anchor_reg": re.compile(r"投资顾问|[、）]其他"),
                    "anchor_amount": 7,
                    "step": -1,
                    "rough_fetch": True,
                },
                {
                    "name": "投资顾问联系电话",
                    "regs": [
                        re.compile(r"(?P<target>.*(?:不聘请|无)投资顾问)"),
                        re.compile(r"联系电话.*[:：](?P<target>.*)"),
                        re.compile(r"(?P<target>本(资产管理)?计划不聘请投资顾问)"),
                    ],
                    "anchor_reg": re.compile(r"投资顾问|[、）]其他"),
                    "anchor_amount": 7,
                    "step": -1,
                    "rough_fetch": True,
                },
            ],
            "托管外包信息": [
                {
                    "name": "托管人名称",
                    "regs": [
                        re.compile(r"【(?P<target>.*?)】"),
                        re.compile(r"名称[：:]\s?(?P<target>.*)"),
                        re.compile(r"合伙企业委托(?P<target>.*?公司)作为(资金托管|基金管理)人"),
                    ],
                    "anchor_reg": re.compile(r"托管人|资金托管|托管方式|管理方式"),
                },
                {
                    "name": "外包人名称",
                    "regs": [
                        re.compile(r"【(?P<target>.*?公司)】"),
                        re.compile(r"运营服务机构为(?P<target>.*?公司)"),
                        re.compile(r"(?P<target>.*?公司)作为运营服务机构"),
                        re.compile(r"本基金的外包服务机构为(?P<target>.*?公司)"),
                        re.compile(r"本计划的估值与核算机构为(?P<target>.*?公司)"),
                        re.compile(r"基金管理人委托(?P<target>.*?公司)"),
                        re.compile(r"委托【(?P<target>.*?公司)】作为资金托管人"),
                        re.compile(r"机构名称：(?P<target>.*?公司)"),
                    ],
                    # 'pass_reg': re.compile(r'托管人|资金托管'),
                },
            ],
            "募集期信息": [
                {
                    "name": "最低成立金额",
                    "regs": [
                        re.compile(r"初始.*?不低于【(?P<target>.*?)】"),
                        re.compile(r"初始募集规模不得?低于(?P<target>.*?)。"),
                        re.compile(r"投资者在募集期间累计认购资金不得?低于【(?P<target>.*?)】"),
                        re.compile(r"基金的初始资产合计不得?低于【(?P<target>.*?)】"),
                        re.compile(r"基金募集金额不得?低于(?P<target>.*?)"),
                        re.compile(r"募集规模超过(?P<target>.*?)时即可成立"),
                        re.compile(r"成立时委托财产的初始资产净值不得?低于(?P<target>.*(人民币|万元))"),
                        re.compile(r"初始资产合计不得?低于(?P<target>.*(人民币|万元))"),
                        re.compile(r"初始募集(资金|财产)合计不得?低于(?P<target>.*(人民币|万元))"),
                        re.compile(r"初始资产净值合计不得?低于(?P<target>.*(人民币|万元))"),
                        re.compile(r"最低初始规模应?不得?低于(?P<target>.*(人民币|万元))"),
                        re.compile(r"初始委托财产合?计?不得?低于(?P<target>.*(人民币|万元))"),
                        re.compile(r"集合计划的参与资金总额（含参与费）不低于(?P<target>.*(人民币|万元))"),
                        re.compile(r"募集金额不低于(?P<target>.*(人民币|万元))"),
                        re.compile(r"（小写）(?P<target>.*(人民币|万元))"),
                    ],
                },
                {
                    "name": "最低首次认购金额",
                    "regs": [
                        re.compile(r"募集期限的认购金额不得?低于【(?P<target>.*?)】"),
                        re.compile(r"得低于(?P<target>.*?)（不含认购费用）"),
                        re.compile(r"募集期限的认购金额应?不得?低于(?P<target>.*(人民币|万元))"),
                        re.compile(r"认购本基金的发起资金金额不少于(?P<target>.*(人民币|万元))"),
                        re.compile(r"初始认购金额不低于(?P<target>.*(人民币|万元))"),
                        re.compile(r"投资者认缴的出资额不低于(?P<target>.*(人民币|万元))"),
                        re.compile(r"新入伙有限合伙人出资起点为(?P<target>.*(人民币|万元))"),
                        re.compile(r"最低认购金额为(?P<target>.*(人民币|万元))"),
                        re.compile(r"初始认购本资产管理计划份额资产净值不低于(?P<target>.*(人民币|万元))"),
                        re.compile(r"合伙企业出资不应低于(?P<target>.*(人民币|万?元))"),
                        re.compile(r"认缴出资(应当不|不应)低于(?P<target>.*(人民币|万?元?))"),
                        re.compile(r"首次参与的最低金额为(?P<target>.*(人民币|万元))"),
                        re.compile(r"首次净认购金额应不低于(?P<target>.*(人民币|万元))"),
                    ],
                },
                {
                    "name": "追加认购金额",
                    "regs": [
                        re.compile(r"追加认购.*?不低于【(?P<target>.*?)】"),
                        re.compile(r"初始募集期间追加认购金额(?P<target>无限制)"),
                        re.compile(r"追加金额应不低于【(?P<target>.*?)】"),
                        re.compile(r"追加认购金额应不低于(?P<target>.*?)。"),
                        re.compile(r"超过部分均按照(?P<target>.*?的整数倍)增加"),
                        re.compile(r"认购期间追加委托投资金额应为(?P<target>.*?的整数倍)"),
                        re.compile(r"追加认购金额应不低于(?P<target>.*?的整数倍)"),
                        re.compile(r"追加委托投资金额应不低于(?P<target>.*?的整数倍)"),
                        re.compile(r"认购期间追加委托投资金额应不低于(?P<target>.*(人民币|万元))"),
                        re.compile(r"按(?P<target>.*?的整数倍)"),
                        re.compile(r"超过部分按(?P<target>.*?的整数倍)递增"),
                        re.compile(r"超过部分为(?P<target>.*?的整数倍)"),
                        re.compile(r"追加认购金额应为(?P<target>.*?的整数倍)"),
                    ],
                },
                {
                    "name": "认购费率",
                    "regs": [
                        re.compile(r"(?P<target>基金投资者认购本基金[无不]需交纳认购费用?)"),
                        re.compile(r"本基金(?P<target>不收取认购费用)"),
                        re.compile(r"委托人认购.*?份额时，(?P<target>无需交纳认购费用)"),
                        re.compile(r"认购费用为认购金额的【(?P<target>.*%)】"),
                        re.compile(r"实缴出资总额的【(?P<target>.*%)】"),
                        re.compile(r"(?P<target>本计划不设置认购费)"),
                        re.compile(r"(?P<target>无需缴纳认购费用)"),
                        re.compile(r"认购费率为实缴出资总额的【(?P<target>.*%)】"),
                        re.compile(r"(?P<target>[无不](需[缴交]纳|收取)(认购|入伙)费用?)"),
                        re.compile(
                            r"(认购|入伙)费[用率]为(认购金|实缴出资总?)额的[\[【]?(?P<target>\d+(\.\d+)?[%‰％])[】\]]?"
                        ),
                        re.compile(r"认购费率[:：为是]+[\[【]?(?P<target>\d+(\.\d+)?[%‰％])[】\]]?"),
                        re.compile(r"则(认购|入伙)费[用率]为[\[【]?(?P<target>\d+(\.\d+)?[%‰％])[】\]]?"),
                        re.compile(r"(?P<target>无认购费用)"),
                        re.compile(r"(?P<target>本基金无认购费用)"),
                        re.compile(r"(?P<target>无需交纳认购费用)"),
                        re.compile(r"(?P<target>本合伙企业不收取入伙费)"),
                        re.compile(r"认购/申购费费率为(?P<target>.*%)"),
                        re.compile(r"[认申]购/[认申]购费费?率为(?P<target>\d+[%‰％])"),
                        re.compile(r"[缴交]纳[\[【]?(?P<target>\d+(\.\d+)?[%‰％])[】\]]?的?(认购|入伙)费[用率]"),
                    ],
                },
                {
                    "name": "认购费归属",
                    "regs": [
                        re.compile(r"(?P<target>基金投资者认购本基金[无不]需交纳认购费用?)"),
                        re.compile(r"委托人认购.*?份额时，(?P<target>无需交纳认购费用)"),
                        re.compile(r"(?P<target>认购费用归.*?所有)。"),
                        re.compile(r"(?P<target>(基金|计划)不收取认购费用?)"),
                        re.compile(r"本(基金|计划)(?P<target>不收取认购费用?)"),
                        re.compile(r"(?P<target>认购费归销售机构所有)"),
                        re.compile(r"(?P<target>本计划不设置认购费)"),
                        re.compile(r"(?P<target>无需缴纳认购费用)"),
                        re.compile(r"(?P<target>归管理人所有)"),
                        re.compile(r"(?P<target>本基金无认购费用)"),
                        re.compile(r"(?P<target>无需交纳认购费用)"),
                        re.compile(r"(?P<target>本合伙企业不收取入伙费)"),
                        re.compile(r"(?P<target>归普通合伙人或代销机构所有)"),
                        re.compile(r"(认购|入伙)费用?.*归(?P<target>[^，。]*?)所有"),
                        re.compile(
                            r"(认购|入伙)费用?归[\[【]?(?P<target>(基金管理人|普通合伙人)([(（]?或代销机构[)）]?)?)[】\]]?所有"
                        ),
                        re.compile(r"(?P<target>不收取认购费用?)"),
                        re.compile(r"认购/申购费(?P<target>归销售机构所有?)"),
                    ],
                },
                {
                    "name": "认购份额精度",
                    "regs": [re.compile(r"保留[到至]?小数点后\s?(?P<target>\w?)位")],
                },
                {
                    "name": "募集期利息处理方式",
                    "regs": [
                        re.compile(r"销售行为结束前.*投资者(?P<target>.*?)。"),
                        re.compile(r"(?P<target>初始募集期间产生的利息.*?归委托人所有)"),
                        re.compile(r"(?P<target>认购款在募集账户产生的利息归入基金资产)"),
                        re.compile(r"(?P<target>认购款在募集账户产生的利息归投资者所有)"),
                        re.compile(r"(?P<target>利息收入计入集合资管计划资产)"),
                        re.compile(
                            r"(?P<target>委托人的有效认购款项在初始销售期形成的利息归入计划财产，不折算及增加委托人持有的份额。)"
                        ),
                        re.compile(
                            r"(?P<target>有效认购款项在募集期间产生的利息将折算为基金份额归基金份额持有人所有，其中利息转份额以登记机构的记录为准。)"
                        ),
                        re.compile(
                            r"""(?P<target>基金投资者认购款项在基金募集期间产生的利息自进入注册登记账户之日起算，利息金额按银行同期活期利率计息，
                        不计入基金份额，在基金成立后的适当时间返还给基金投资者。)""",
                            re.X | re.I,
                        ),
                        re.compile(
                            r"""(?P<target>基金投资者认购款项在基金初始募集期间产生的利息自进入注册登记账户之日起算，
                        利息金额按银行同期活期利率计息，不计入基金份额，在基金成立后的适当时间返还给基金投资者，
                        具体金额以份额登记机构记录为准。)""",
                            re.X | re.I,
                        ),
                        re.compile(
                            r"(?P<target>认购款在募集账户产生的利息，按银行同期活期存款利息计算，不折算成份额而直接在基金成立后按实际结息到账金额归入基金资产)"
                        ),
                        re.compile(
                            r"(?P<target>资产委托人的认购参与款项（不含认购费用）在初始销售期形成的利息归入计划财产)"
                        ),
                        re.compile(
                            r"(?P<target>初始销售期间产生的利息（按管理人募集户开户银行同期活期存款利率计算）在资产管理合同生效后折算为资产管理计划份额归委托人所有。)"
                        ),
                    ],
                    "anchor_reg": re.compile(r"利息的?(处理|方式)|认购份额的?计算"),
                },
                {
                    "name": "冷静期时长",
                    "regs": [
                        re.compile(r"为基金投资者设置(?P<target>不少于【.*?】)的?投资冷静期"),
                        re.compile(r"为基金投资者设置(?P<target>不少于.*?)的?投资冷静期"),
                        re.compile(r"为投资者设置(?P<target>.*?)的?投资冷静期"),
                        re.compile(r"投资者完成购买签约与划款后设置(?P<target>.*?)的冷静期"),
                        re.compile(r"给予投资者(?P<target>.*?)的投资冷静期"),
                        re.compile(r"全部认购款项后(?P<target>.*?)内为本基金的认购投资冷静期"),
                        re.compile(r"有限合伙人(?P<target>.*?)的投资冷静期"),
                    ],
                },
                {
                    "name": "是否设置回访",
                    "func": self.return_visit,
                },
            ],
            "申赎信息": [
                {
                    "name": "最低首次申购金额",
                    "regs": [
                        re.compile(r"(?:首次申购金额|首次参与金额).*?(?P<target>\d+\s?[十百千万亿]元?)"),
                        re.compile(r"(?P<target>(?:不办理|不开放)申购)"),
                        re.compile(r"(?P<target>本基金无申购费用)"),
                        re.compile(
                            r"存续期开放日购买资产管理计划份额的，认购资?金额?不得?低于【?(?P<target>.*?元?人民币)】?"
                        ),
                        re.compile(r"(参与|购买)金额应不低于(?P<target>.*?元?人民币)"),
                        re.compile(r"首次认购本资产管理计划金额应不低于(?P<target>.*?元?人民币)"),
                        re.compile(r"在申购开放期内首次净申购金额应不低于(?P<target>.*?元?人民币)"),
                        re.compile(r"本计划初始募集最低金额限制为(?P<target>.*?元?人民币)"),
                    ],
                    "anchor_reg": re.compile(r"申购|参与和退出"),
                },
                {
                    "name": "最低追加申购金额",
                    "regs": [
                        re.compile(r"追加(?:[认申]购金额|金额|购买金额).*?(?P<target>[\s【]?\d+[\s】]?[十百千万亿]元)"),
                        re.compile(r"追加认购/参与金额为(?P<target>.*?元?人民币的整数倍)"),
                        re.compile(r"追加申购金额应不低于(?P<target>.*?元?人民币的整数倍)"),
                        re.compile(r"(?:本基金)?(?P<target>(?:不办理|不开放)申购和赎回业务|无申购费用)"),
                        re.compile(r"(?P<target>本基金无申购费用)"),
                    ],
                },
                {
                    "name": "申购费率",
                    "regs": [
                        re.compile(r"申购费费?率为?(?P<target>\d+\.?\d*%?)[；。]?"),
                        re.compile(r"申购费=.*(?P<target>\d+\.?\d*%?)"),
                        re.compile(
                            r"(?:本基金|本计划)?(?P<target>(?:不办理|不开放)申购和赎回业务|(?:不收取|无|无需交纳|不设置)(?:申购|参与)费?用?)"
                        ),
                        re.compile(r"本基金无申购费用"),
                    ],
                },
                {
                    "name": "申购费归属",
                    "regs": [
                        re.compile(r"(?P<target>归.*所有)"),
                        re.compile(r"申购费用?(?P<target>由.*不列入基金财产)"),
                        re.compile(
                            r"(?:本基金|本计划)?(?P<target>(?:不办理|不开放)申购和赎回业务|(?:不收取|无|无需交纳|不设置|不接受)(?:申购|参与)费?用?)"
                        ),
                        re.compile(r"本基金无申购费用"),
                    ],
                },
                {
                    "name": "赎回费率",
                    "regs": [
                        re.compile(
                            r"(?:本基金|本计划)?(?P<target>(?:不办理|不开放)申购和赎回业务|(?:不收取|无|无需交纳|不设置|不接受)(?:赎回|参与)费?用?)"
                        ),
                        re.compile(r"(?:本基金|本计划)?(?P<target>(?:不开放|不收取)(赎回业务|退出费))"),
                        re.compile(r"赎回费率为【?(?P<target>\d+\.?\d*[%‰％])"),
                        re.compile(r"本(集合|资产管理)计划的?退出费用?为(?P<target>.*)"),
                        re.compile(r"本基金申购开放期内申购费率和赎回费为(?P<target>.*)"),
                        re.compile(r"(?P<target>临时开放日仅允许申购不允许赎回)"),
                        re.compile(r"(?P<target>本基金可设置临时开放日只开放申购，不开放赎回)"),
                        re.compile(r"本基金无赎回费用"),
                    ],
                },
                {
                    "name": "巨额赎回认定标准",
                    "regs": [
                        re.compile(r"(?P<target>(?:本基金|本资产).*(?:巨额赎回|巨额退出))"),
                        re.compile(
                            r"(?P<target>单个开放日，投资者.*超过上一工作日计划总份额数的\d+%时，即为巨额退出。)"
                        ),
                        re.compile(
                            r"(?:本基金|本计划)?(?P<target>(?:不办理|不开放)申购和赎回业务|(?:不收取|无|无需交纳|不设置|不接受)(?:赎回|参与)费?用?)"
                        ),
                        re.compile(r"本基金无赎回费用"),
                    ],
                },
                {
                    "name": "赎回费归属",
                    "regs": [
                        re.compile(
                            r"(?P<target>本?(基金|计划)(?:投资者申购本基金无需交纳赎回费|赎回费用?全部归基金资产|退出费用全部归【管理人】))"
                        ),
                        re.compile(r"本基金存续期间.*?(?P<target>不开放赎回业务)"),
                        re.compile(
                            r"(?P<target>赎回费用由.*基金份额持有人承担.*赎回费用按.*比例归入基金财产，未归入.*部分用于.*费)"
                        ),
                        re.compile(
                            r"""(?P<target>退?出?(?:本基金|本计划)?(
                            (?:不办理|不开放)申购和赎回业务
                            |(?:不收取|无|无需交纳|不设置|不接受)(?:赎回|参与|退出)费?用?
                        ))""",
                            re.X,
                        ),
                        re.compile(r"本基金无赎回费用"),
                    ],
                    "anchor_amount": 10,
                },
                {
                    "name": "申购、赎回资金的利息处理方式",
                    "regs": [
                        re.compile(r"(?P<target>^本基金.*(?:申购|赎回|清算).*不计息)"),
                        re.compile(r"(?P<target>^本基金.*申购.*计入基金财产)"),
                        re.compile(
                            r"(?:本基金|本计划)?(?P<target>(?:不办理|不开放)申购和赎回业务|(?:不收取|无|无需交纳|不设置|不接受)(?:申购|赎回|参与|退出)费?用?)"
                        ),
                        # re.compile(r'本基金无申购费用'),
                    ],
                },
            ],
            "费用信息": [
                {
                    "name": "托管费率",
                    "regs": [
                        re.compile(r"托管费?年?费率.*?(?P<target>\d+\.?\d*[%‰％])"),
                        re.compile(r"托管费.*?(?P<target>\d+\.?\d*[%‰％])年费率计提"),
                    ]
                    + self.attr2reg["托管费计算公式-费率"]["regs"],
                    "anchor_reg": re.compile(r"托管费"),
                },
                {
                    "name": "托管费保底",
                    "regs": [
                        re.compile(r"托管费为?(?:低于|不超过)(?P<target>\d+\.?\d*[十百千万亿]元)"),
                    ]
                    + self.attr2reg["托管费计算公式-保底费"]["regs"],
                },
                {
                    "name": "托管费支付方式",
                    "regs": [
                        re.compile(r"(?P<target>本合伙企业管理人不收取托管费)"),
                        re.compile(r"(?P<target>本?(基金|资管|计划).*托管费.*支付.*)"),
                        re.compile(r"(?P<target>合同生效后，托管费.*?支付.*?顺延至最近可支付日支付)"),
                        re.compile(r"(?P<target>托管费按(自然)?年度支付.*。)"),
                        re.compile(
                            r"(?P<target>委托资产托管费自资产运作起始日起，每日计提，按季支付。由管理人.*?从委托资产中一次性支付给托管人)"
                        ),
                        re.compile(r"(?P<target>本合伙企业的托管费自本?自?本合伙企业首次交割之?日起.*。)"),
                        re.compile(
                            r"(?P<target>托管费于本合伙企业首次交割日及之后每年的首次交割日对日进行计提.*已收取的托管费不予退还)"
                        ),
                        re.compile(r"(?P<target>前\w年.*出资额总和)"),
                        re.compile(r"(?P<target>.*已收取的托管费不予退还)"),
                        re.compile(r"(?P<target>.*已支付的托管费无需退回给合伙企业财产)"),
                        re.compile(r"(?P<target>自首次.*内支付)"),
                        re.compile(r"(?P<target>本合伙企业的年托管费率.*一次性收取.*托管费)"),
                        re.compile(r"(?P<target>合伙企业自.*剩余托管费于产品结束日一次性支付)"),
                        re.compile(r"(?P<target>首年之后的托管费.*)"),
                        re.compile(r"(?P<target>普通合伙人应于.*支付给托管人。合伙企业终止时.*收取)"),
                        re.compile(r"(?P<target>普通合伙人应于首个.*支付给托管人)"),
                        re.compile(r"(?P<target>自首次交割日.*支付)"),
                        re.compile(r"(?P<target>若有限合伙存续.*在基金清算时统一结算支付)"),
                        re.compile(r"(?P<target>合伙企业于首次交割日计提.*托管费)"),
                        re.compile(r"(?P<target>托管费的计算标准和支付办法.*为准)"),
                    ],
                    "cnt_of_res": 5,
                },
                {
                    "name": "外包费率",
                    "regs": [
                        re.compile(r"(?P<target>本合伙企业管理人不收取托管费)"),
                        re.compile(r"(?P<target>本合伙企业管理人不收取运营服务费)"),
                        re.compile(r"(?:运营|外包|代销|销售)(?:服务|管理)费.*年?费?率.*?(?P<target>\d+\.?\d*[%‰％])"),
                        re.compile(r"(?:运营|外包|代销|销售)(?:服务|管理)费.*(?P<target>\d+\.?\d*[%‰％])年?费?率"),
                        re.compile(
                            r"(?:运营|外包|代销|销售)(?:服务|管理)费按.*?(?P<target>\d+\.?\d*[%‰％])的?.?费率计提"
                        ),
                        re.compile(
                            r"合伙企业每年应支付的运营服务费为全体合伙人实缴出资额总和的(?P<target>\d+\.?\d*[%‰％])"
                        ),
                        re.compile(r"计提金额为首次交割日当天实缴出资额总和的(?P<target>\d+\.?\d*[%‰％])"),
                        re.compile(
                            r"合伙企业每年应支付的运营服务费为合伙人实缴出资额总和的(?P<target>\d+\.?\d*[%‰％])"
                        ),
                        re.compile(
                            r"本计划的行政服务费按前一日计划资产净值（成立日按成立规模）的(?P<target>\d+\.?\d*[%‰％])年费率计提"
                        ),
                        re.compile(r"本计划的代销服务费按前一日计划财产净值的(?P<target>\d+\.?\d*[%‰％])年费率计提"),
                        re.compile(r"基金的运营外包服务费率为年费率(?P<target>\d+\.?\d*[%‰％])"),
                        re.compile(r"服务费的?年费率为(?P<target>\d+\.?\d*[%‰％])"),
                        re.compile(r"本计划运营服务费年费率(?P<target>.*)计算"),
                        re.compile(r"资产管理计划财产的运营服务费率为计划财产净值的(?P<target>.*?年)"),
                    ],
                    "anchor_reg": re.compile(r"托管|运营服务|行政服务|外包服务|代销服务"),
                },
                {
                    "name": "外包费保底",
                    "regs": [
                        re.compile(
                            r"(?:运营|外包|代销)(?:服务|管理)费为?(?:低于|不超过).*?(?P<target>\d+\.?\d*[十百千万亿]元)"
                        ),
                        re.compile(r"最低值为每年(?P<target>.*万元)"),
                    ],
                },
                {
                    "name": "管理费率",
                    "regs": [
                        re.compile(r"管理费年?费?率.*?[为:：是]?(?P<target>【?\d+\.?\d*】?%)"),
                        re.compile(r"管理费年?费?率.*?[为:：是]?(?P<target>.*)/年"),
                        re.compile(r"管理费.*?(?P<target>\d+\.?\d*%)(?=年费率计提)"),
                        re.compile(r"集合计划的年管理费为(?P<target>\d+\.?\d*%)"),
                        re.compile(r"管理费=有限合伙人实缴出资金额×(?P<target>\d+\.?\d*%)×.*"),
                        re.compile(r"合伙企业每年应支付的管理费为全?体?合伙人实缴出资额总和的(?P<target>\d+\.?\d*%)。"),
                        re.compile(r"固定管理费的年费率为(?P<target>\d+\.?\d*%)。"),
                        re.compile(r"每年应支付的管理费总额为每一名有限合伙人的认缴出资额的(?P<target>\d+\.?\d*%)"),
                        re.compile(r"计提金额为首次交割日当天实缴出资额总和的(?P<target>\d+\.?\d*%)"),
                        re.compile(
                            r"合伙企业每年应支付的管理费为合伙企业首次交割日全体合伙人实缴出资额总和的(?P<target>\d+\.?\d*%)"
                        ),
                        re.compile(r"管理费按.*的(?P<target>\d+\.?\d*%)按年预付"),
                        re.compile(r"(?P<target>不收取管理费)"),
                        re.compile(r"(?P<target>本合伙型基金无管理费)"),
                    ],
                },
                {
                    "name": "管理费支付方式",
                    "regs": [
                        re.compile(r"(?P<target>不收取管理费)"),
                        re.compile(r"(?P<target>本合伙型基金无管理费)"),
                        re.compile(r"(?P<target>本?(基金|资管|计划).*管理费.*支付.*)"),
                        re.compile(r"(?P<target>管理费按年度支付.*支付。)"),
                        re.compile(r"(?P<target>管理人于首次交割日计提.*普通合伙人有权进行减免)"),
                        re.compile(r"(?P<target>管理费计算期间为首次交割日起至投资退出封闭期（含延长期）届满之日)"),
                        re.compile(r"(?P<target>管理费自基金成立日起计算.*计提新申购份额的管理费)"),
                        re.compile(r"(?P<target>合同生效后，管理费每日计提.*顺延至最近可支付日支付)"),
                        re.compile(r"(?P<target>由托管人根据与管理人核对一致的财务数据.*尚未支付的管理费)"),
                        re.compile(r"(?P<target>第一年的管理费=.*)"),
                        re.compile(r"(?P<target>管理费于本合伙企业首次交割.*已收取的管理费不予退还)"),
                        re.compile(r"(?P<target>委托财产管理费自计划成立日的下一个自然日起，每日计提.*)"),
                        re.compile(r"(?P<target>合伙企业于首次交割日计提.*)"),
                        re.compile(r"(?P<target>于本合伙企业首次交割日计提.*已收取的管理费不予退还)"),
                        re.compile(r"(?P<target>自合伙企业首次交割日.*天数进行收取)"),
                        re.compile(r"(?P<target>存续期前两年的管理费于首次交割日.*一次性支付给管理人)"),
                        re.compile(r"(?P<target>存续期满两年后.*已收取的管理费不予退还)"),
                        re.compile(r"(?P<target>管理费分两次计提及支付。第一次.*已收取的管理费不予退还)"),
                        re.compile(r"(?P<target>第二次管理费计提日为有限合伙企业终止日.*从基金财产中一次性支付)"),
                        re.compile(
                            r"(?P<target>委托财产管理费自计划成立日起，每日计提.*依据清算程序支付尚未支付的管理费)"
                        ),
                        re.compile(r"(?P<target>前\w年.*计提.*支付)"),
                        re.compile(r"(?P<target>年度托管费是指自首次交割日起.*已收取的托管费不予退还)"),
                        re.compile(r"(?P<target>在发生后续交割的情况下.*追加.*托管费)"),
                        re.compile(r"(?P<target>合伙企业存续期间，每年应向管理人支付管理费.*之后的计提日为.*)"),
                    ],
                    "cnt_of_res": 5,
                },
                {
                    "name": "投资顾问费费率",
                    "regs": [
                        re.compile(r"顾问费率.*?[为:：是](?P<target>【?\d+\.?\d*】?%)"),
                        re.compile(r"顾问费.*?(?P<target>\d+\.?\d*%)(?=年费率计提)"),
                        re.compile(r"管理计划的投资顾问费.*?计划资产净值的(?P<target>.*%)(?=年费率计提)"),
                        re.compile(r"(?P<target>本?(基金|资管|计划)(?:无|不聘请)投资顾问)"),
                    ],
                },
                {
                    "name": "投资顾问费支付方式",
                    "regs": [
                        re.compile(r"(?P<target>本?(基金|资管|计划).*投资顾问费.*支付.*)"),
                        re.compile(r"(?P<target>本?(基金|资管|计划)(?:无|不聘请)投资顾问)"),
                        re.compile(r"(?P<target>合同生效后，固定投资顾问费.*付日支付)"),
                    ],
                },
            ],
            "业绩报酬": [
                {
                    "name": "计提方式",
                    "func": self.accrual_method,
                },
                {
                    "name": "计提公式",
                    "regs": [
                        re.compile(r"(?P<target>本基金管理人不[收|提]取业绩报酬)"),
                        re.compile(r"(?P<target>本基金不[收|提]取(管理人)?的?业绩报酬)"),
                        re.compile(r"(?P<target>本基金无业绩报酬)"),
                        re.compile(r"(?P<target>本(产品|基金)管理人不[收|提]取业绩报酬)"),
                        re.compile(r"(?P<target>本基金无私募基金管理人业绩报酬)"),
                        re.compile(r"(?P<target>本计划不提取管理人和投资顾问的业绩报酬)"),
                        re.compile(r"(?P<target>本资产管理计划不计提业绩报酬)"),
                        re.compile(r"(?P<target>本合伙企业(的普通合伙人、)?管理人不收取业绩报酬)"),
                        re.compile(r"(?P<target>基金管理人提取的业绩报酬.*?。)"),
                        re.compile(r"(?P<target>Hi=.*?日份额净值×.*?。)"),
                        re.compile(r"提取.*?业绩报酬，即(?P<target>.*?%)；"),
                        re.compile(r"(?P<target>.*当.*?[><≤].*?(\d%|时).*)"),
                        re.compile(r"(?P<target>基金管理人提取的?业绩报酬.*?。)"),
                        re.compile(r"公式[一二].*?：(?P<target>.*)"),
                        re.compile(r"(?P<target>收益率.*?=.*)"),
                        re.compile(r"(?P<target>基金管理人提取的业绩报酬=MAX.*)"),
                        re.compile(r"(?P<target>H=MAX.*)"),
                        re.compile(r"(?P<target>(水位线|业绩报酬(金额)?)=.*)"),
                        re.compile(r"(?P<target>该有限合伙人累计分配金额=该有限合伙人.*)"),
                        re.compile(r"(?P<target>有限合伙人实缴金额.*)"),
                        re.compile(r"业绩报酬=(?P<target>MAX\{.*\})"),
                    ],
                    "anchor_reg": re.compile(r"计算公式|业绩报酬|现金分配|收益分配"),
                    "cnt_of_res": 2,
                },
                {
                    "name": "计提比例",
                    "regs": [
                        re.compile(r"(?P<target>本基金管理人不[收|提]取业绩报酬)"),
                        re.compile(r"(?P<target>本基金不[收|提]取(管理人)?的?业绩报酬)"),
                        re.compile(r"(?P<target>本基金无业绩报酬)"),
                        re.compile(r"(?P<target>本(产品|基金)管理人不[收|提]取业绩报酬)"),
                        re.compile(r"(?P<target>本基金无私募基金管理人业绩报酬)"),
                        re.compile(r"(?P<target>本计划不提取管理人和投资顾问的业绩报酬)"),
                        re.compile(r"(?P<target>本资产管理计划不计提业绩报酬)"),
                        re.compile(r"(?P<target>本合伙企业(的普通合伙人、)?管理人不收取业绩报酬)"),
                        re.compile(r"业绩报酬的?提取比例[为，](?P<target>.*%)"),
                        re.compile(r"提取\s?(?P<target>.*?%)的业绩报酬"),
                        re.compile(r"按(?P<target>.*?%)的比例计提业绩报酬"),
                        re.compile(r"如有余额，其中(?P<target>.*?%)部分分配给普通合伙人"),
                        re.compile(r"提取(?P<target>.*?%)"),
                        re.compile(r"(?P<target>(不[收提]取([^，。]*?的)?|无)业绩报酬)"),
                        re.compile(r"(?P<target>无私募基金管理人业绩报酬)"),
                        re.compile(r"业绩报酬的?提取比例(合计)?[为是](?P<target>\d+%)"),
                        re.compile(r"×(?P<target>\d+%)×T日基金总份额"),
                        re.compile(r"(?P<target>\d+%)(作为|提取|计提)业绩报酬"),
                        re.compile(r"(?P<target>本基金剩余基金资产全部作为业绩报酬归基金管理人所有)"),
                        re.compile(r"×(?P<target>\d+%)×产品结束当日基金份额"),
                        re.compile(r"业绩报酬计提基准[:：为]*(?P<target>【?\d+(\.\d+)%?】?%?)"),
                        re.compile(r"份额基准收益=.*?(?P<target>\d+(\.\d+)%)"),
                        re.compile(r"(?P<target>提取标准是.*?作为业绩报酬)"),
                        re.compile(r"提取(?P<target>[\s\d,%]+)(作为)?业绩报酬"),
                        re.compile(r"在该周期内超额收益的(?P<target>[\s\d,%]+)(计提)?业绩报酬"),
                        re.compile(r"提取(?P<target>[\s\d,%]+)作为业绩报酬支付给基金管理人"),
                        re.compile(r"(?P<target>[\s\d,%]+)分配给(普通合伙人及管理人|执行事务合伙人)"),
                        re.compile(r"有限合伙人分配到(?P<target>[\s\d,%]+)的收益"),
                        re.compile(r"分红份额当期收益的(?P<target>[\s\d,%]+)作为业绩报酬"),
                        re.compile(r"其余(?P<target>[\s\d,%]+)部分分配给普通合伙人"),
                        re.compile(r"普通合伙人取得剩余(?P<target>[\s\d,%]+)的超额收益"),
                        re.compile(r"其中的?(?P<target>[\s\d,%]+).*?分配给(各有限合伙人|普通合伙人)"),
                        re.compile(r"由普通合伙人收取(?P<target>[\s\d,%]+)作为业绩分成"),
                        re.compile(r"向普通合伙人分配：全部收益的(?P<target>[\s\d,%]+)"),
                    ],
                },
            ],
            "募集账户信息": [
                {
                    "name": "户名",
                    "regs": [
                        re.compile(r"[开账]?户名称?.*?[：:]\s?[“【]?(?P<target>.*?(公司|（有限合伙）|专户.*))[”】]?"),
                    ],
                    "pass_reg": re.compile(r"托管费|管理费|委托财产|运营服务费"),
                },
                {
                    "name": "账号",
                    "regs": [
                        re.compile(r"账号[：:]\s?[“【](?P<target>.*?)[”】]"),
                        re.compile(r"账号[：:]\s?(?P<target>\d*)"),
                    ],
                    "pass_reg": re.compile(r"托管费|管理费|委托财产|运营服务费"),
                },
                {
                    "name": "开户行",
                    "regs": [
                        re.compile(r"开户银?行(全称)?[：:]\s?[“【](?P<target>.*?)[”】]"),
                        re.compile(r"开户银?行(全称)?[：:]\s?(?P<target>.*)"),
                    ],
                    "pass_reg": re.compile(r"托管费|管理费|委托财产|运营服务费"),
                },
                {
                    "name": "大额支付号",
                    "regs": [
                        re.compile(r"大额支付账?号[：:]\s?[“【](?P<target>.*?)[”】]"),
                        re.compile(r"大额支付(账|系?统?行)?号[：:]\s?(?P<target>\d*)"),
                    ],
                    "pass_reg": re.compile(r"托管费|管理费|委托财产|运营服务费"),
                },
            ],
            "托管账户信息": [
                {
                    "name": "户名",
                    "regs": [
                        re.compile(r"[开账]?户?名称?.*?[：:]\s?[“【]?(?P<target>.*?(公司|（有限合伙）|专户))[”】]?"),
                    ],
                    "anchor_reg": re.compile(r"托管人|托管费收费账户信息|托管账号信息|收取托管费用?的?(银行)?账户"),
                },
                {
                    "name": "账号",
                    "regs": [
                        re.compile(r"账号[：:]\s?[“【](?P<target>.*?)[”】]"),
                        re.compile(r"账号[：:]\s?(?P<target>\d*)"),
                    ],
                    "anchor_reg": re.compile(r"托管人|托管费收费账户信息|托管账号信息|收取托管费用?的?(银行)?账户"),
                },
                {
                    "name": "开户行",
                    "regs": [
                        re.compile(r"开户银?行(全称)?[：:]\s?[“【](?P<target>.*?)[”】]"),
                        re.compile(r"开户银?行(全称)?[：:]\s?(?P<target>.*)"),
                    ],
                    "anchor_reg": re.compile(r"托管人|托管费收费账户信息|托管账号信息|收取托管费用?的?(银行)?账户"),
                },
                {
                    "name": "大额支付号",
                    "regs": [
                        re.compile(r"大额支付账?号[：:]\s?[“【](?P<target>.*?)[”】]"),
                        re.compile(r"大额支付(账|系?统?行)?号[：:]\s?(?P<target>\d*)"),
                    ],
                    "anchor_reg": re.compile(r"托管人|托管费收费账户信息|托管账号信息|收取托管费用?的?(银行)?账户"),
                },
            ],
            "管理费账户信息": [
                {
                    "name": "户名",
                    "regs": [
                        re.compile(r"[开账]?户名称?.*?[：:]\s?[“【]?(?P<target>.*?(公司|（有限合伙）|专户))[”】]?"),
                        re.compile(r"(?P<target>本基金(管理人)?不收取业绩报酬)"),
                    ],
                    "anchor_reg": re.compile(r"业绩报酬|管理费|投资顾问费"),
                },
                {
                    "name": "账号",
                    "regs": [
                        re.compile(r"账号[：:]\s?[“【](?P<target>.*?)[”】]"),
                        re.compile(r"账号[：:]\s?(?P<target>\d*)"),
                        re.compile(r"(?P<target>本基金(管理人)?不收取业绩报酬)"),
                    ],
                    "anchor_reg": re.compile(r"业绩报酬|管理费|投资顾问费"),
                },
                {
                    "name": "开户行",
                    "regs": [
                        re.compile(r"开户银?行(全称)?[：:]\s?[“【](?P<target>.*?)[”】]"),
                        re.compile(r"开户银?行(全称)?[：:]\s?(?P<target>.*)"),
                        re.compile(r"开户银行名称[：:]\s?(?P<target>.*)"),
                        re.compile(r"(?P<target>本基金(管理人)?不收取业绩报酬)"),
                    ],
                    "anchor_reg": re.compile(r"业绩报酬|管理费|投资顾问费"),
                    "pass_reg": re.compile(r"管理人业绩报酬收取账户与管理费收取账户相同"),
                },
                {
                    "name": "大额支付号",
                    "regs": [
                        re.compile(r"大额支付账?号[：:]\s?[“【](?P<target>.*?)[”】]"),
                        re.compile(r"大额支付(账|系?统?行)?号[：:]\s?(?P<target>\d*)"),
                        re.compile(r"(?P<target>本基金(管理人)?不收取业绩报酬)"),
                    ],
                    "anchor_reg": re.compile(r"业绩报酬|管理费"),
                },
            ],
            "业绩报酬账户信息": [
                {
                    "name": "户名",
                    "regs": [
                        re.compile(r"[开账]?户名称?.*?[：:]\s?[“【]?(?P<target>.*?(公司|（有限合伙）|专户))[”】]?"),
                        re.compile(r"(?P<target>本基金(管理人)?不收取业绩报酬)"),
                    ],
                    "anchor_reg": re.compile(r"业绩报酬|管理费|投资顾问费"),
                },
                {
                    "name": "账号",
                    "regs": [
                        re.compile(r"账号[：:]\s?[“【](?P<target>.*?)[”】]"),
                        re.compile(r"账号[：:]\s?(?P<target>\d*)"),
                        re.compile(r"(?P<target>本基金(管理人)?不收取业绩报酬)"),
                    ],
                    "anchor_reg": re.compile(r"业绩报酬|管理费|投资顾问费"),
                },
                {
                    "name": "开户行",
                    "regs": [
                        re.compile(r"开户银?行(全称)?[：:]\s?[“【](?P<target>.*?)[”】]"),
                        re.compile(r"开户银?行(全称)?[：:]\s?(?P<target>.*)"),
                        re.compile(r"(?P<target>本基金(管理人)?不收取业绩报酬)"),
                    ],
                    "anchor_reg": re.compile(r"业绩报酬|管理费|投资顾问费"),
                    "pass_reg": re.compile(r"管理人业绩报酬收取账户与管理费收取账户相同"),
                },
                {
                    "name": "大额支付号",
                    "regs": [
                        re.compile(r"大额支付账?号[：:]\s?[“【](?P<target>.*?)[”】]"),
                        re.compile(r"大额支付(账|系?统?行)?号[：:]\s?(?P<target>\d*)"),
                        re.compile(r"(?P<target>本基金(管理人)?不收取业绩报酬)"),
                    ],
                    "anchor_reg": re.compile(r"业绩报酬|管理费"),
                },
            ],
            "投资顾问费账户信息": [
                {
                    "name": "户名",
                    "regs": [
                        re.compile(r"[开账]?户名称?.*?[：:]\s?[“【]?(?P<target>.*?(公司|（有限合伙）|专户))[”】]?"),
                    ],
                    "anchor_reg": re.compile(r"投资顾问费"),
                },
                {
                    "name": "账号",
                    "regs": [
                        re.compile(r"账号[：:]\s?[“【](?P<target>.*?)[”】]"),
                        re.compile(r"账号[：:]\s?(?P<target>\d*)"),
                    ],
                    "anchor_reg": re.compile(r"投资顾问费"),
                },
                {
                    "name": "开户行",
                    "regs": [
                        re.compile(r"开户银?行(全称)?[：:]\s?[“【](?P<target>.*?)[”】]"),
                        re.compile(r"开户银?行(全称)?[：:]\s?(?P<target>.*)"),
                    ],
                    "anchor_reg": re.compile(r"投资顾问费"),
                },
            ],
        }
        for col_name, attrs in self.regs.items():
            self.column_analyzers[col_name] = functools.partial(self.extract_text, attrs)

    def extract_text(self, attrs, **kwargs):
        res = []
        group = {}
        for attr in attrs:
            items = []
            col = attr["name"]
            if attr.get("func"):
                _result_predictor = attr.get("func")(**kwargs)
                group.setdefault(col, _result_predictor)
            else:
                elts = self.get_crude_elements(col, kwargs.get("col_type"))
                anchor_reg = attr.get("anchor_reg")  # 附近必须出现某个关键词
                pass_reg = attr.get("pass_reg")  # 附近不能出现某个关键词
                cnt_of_res = attr.get("cnt_of_res", 1)  # 答案数量
                options = {
                    "anchor_amount": attr.get("anchor_amount", 6),
                    "step": attr.get("step", -1),
                    "include": attr.get("include", False),
                }
                for element in elts:
                    ele_typ, element = self.reader.find_element_by_index(element["element_index"])
                    if ele_typ == "PARAGRAPH":
                        element = self.fix_continued_para(element)  # 修复跨页段落
                        for reg in attr["regs"]:
                            matched = reg.search(clean_txt(element["text"]))
                            if matched:
                                if anchor_reg and not self.is_aim_elt(anchor_reg, element["index"], options):
                                    continue
                                if pass_reg and self.is_not_aim_elt(pass_reg, element["index"], options):
                                    continue
                                items = self.reg_match(reg, element, items)
                                break
                    elif ele_typ == "TABLE":
                        for reg in attr["regs"]:
                            for _, cell in element.get("cells").items():
                                matched = reg.search(clean_txt(cell["text"]))
                                if matched:
                                    if anchor_reg and not self.is_aim_elt(anchor_reg, element["index"], options):
                                        continue
                                    if pass_reg and self.is_not_aim_elt(pass_reg, element["index"], options):
                                        continue
                                    items = self.reg_match(reg, cell, items)
                                    break
                            if len(items) >= cnt_of_res:
                                break
                    if len(items) >= cnt_of_res:
                        break
                if not items and attr.get("rough_fetch", False):
                    items = self.fetch_from_elts(attr)
                if items:
                    items = [
                        CharResult(list(chain(*items))),
                    ]
                group.setdefault(col, ResultOfPredictor(data=items, crude_elts=elts))
        res.append(group)
        return res

    @staticmethod
    def para2chars(items):
        chars = [item.chars for item in items]
        ret_item = list(chain(*chars))
        return [
            CharResult(ret_item),
        ]

    def fetch_from_elts(self, attr):
        items = []
        anchor_reg = attr.get("anchor_reg")
        options = attr.get("options", {})
        regs = attr.get("regs")
        for elt in self.sorted_elements.values():
            if elt["class"] != "PARAGRAPH":
                continue
            if not self.is_aim_elt(anchor_reg, elt["index"], options):
                continue

            if elt.get("continued"):  # 跨页段落
                elt = self.fix_continued_para(elt)
            elt_text = clean_txt(elt["text"])
            # cnt = 0  # 关键词的命中次数
            for reg in regs:
                if reg.search(elt_text):
                    items = self.reg_match(reg, elt, items)
                    if len(items) >= attr.get("cnt_of_res", 1):
                        break
            if len(items) >= attr.get("cnt_of_res", 1):
                break
        return items

    def reg_match(self, reg, element, items):
        for each in reg.finditer(clean_txt(element["text"])):
            c_start, c_end = each.start("target"), each.end("target")
            sp_start, sp_end = index_in_space_string(element["text"], (c_start, c_end))
            chars = element["chars"][sp_start:sp_end]
            if chars and chars not in items:
                items.append(chars)
        return items

    def product_name(self, **kwargs):
        """产品名称匹配规则：
        1.先从ai推荐的答案中查找标题，然后取得标题下一行的产品名称
        2.若ai推荐的答案包含标题及产品名称，则通过正则直接匹配
        """

        def find_title():
            for elm in elms:
                if title_reg.search(elm["text"]):
                    return elm["element_index"]
            return None

        def remove_footer(nears):
            for idx, near in enumerate(nears):
                if near.get("type") == "PAGE_FOOTER":
                    cp_nears = deepcopy(nears)
                    cp_nears.pop(idx)
                    return cp_nears
            return nears

        attr = "产品名称"
        regs = [
            re.compile(r"[“【](?P<target>.*?)[”】]"),
            re.compile(r"基金的名称[：:](?P<target>.*a)"),
            re.compile(r"本计划.*系指[“\"](?P<target>.*)[”\"]"),
            re.compile(r"(?P<target>.*(?:投资基金|资产管理计划|（有限合伙）))"),
        ]
        anchor_reg = re.compile(r"(基金的?名称|资产管理计划|企业名称|有限合伙)")
        title_reg = re.compile(r"(（.+）|.、)(基金的?名称|资产管理计划的名称|本计划名称：)$")
        elms = self.get_crude_elements(attr, kwargs.get("col_type"))
        title_idx = find_title()

        if title_idx is not None:
            near_names = remove_footer(self.reader.find_elements_near_by(title_idx, amount=2))
            names = self.match_elements(near_names, regs)
        else:
            names = self.match_elements(
                elms, regs, amount=3, step=-1, anchor_reg=anchor_reg, include=True
            ) or self.match_elements(elms, regs, amount=3, step=1, anchor_reg=anchor_reg, include=True)

        return ResultOfPredictor(data=names, crude_elts=elms)

    def product_type(self, **kwargs):
        attr = "产品类型"

        type_reg = [re.compile(r"[“【](?P<target>.*?)[”】]")]
        anchor_reg = re.compile(r"类型")

        type_reg2 = [
            re.compile(r"号(?P<target>(定向)?资产管理计划)"),
            re.compile(r"私募基金的名称.*(?P<target>私募基金)"),
            re.compile(r"资产管理计划为(?P<target>.*资产管理计划)"),
            re.compile(r"基金类型[为：](?P<target>.*?基金)"),
            re.compile(r"合伙企业为(?P<target>.*?产品)"),
            re.compile(
                r"""(?P<target>期?货?公?司?
                       (?:固定收益|混合|定向|集合|特定多客户
                       |权益类单一|商品及金融衍生品类单?一?)
                       类?集?合?资产管理计划)""",
                re.X,
            ),
            re.compile(
                r"(?P<target>(?:结构化|权益类|混合类|混合型|股票型发起式)?(?:私募证券|私募股权|私募|证券)投?资?基金)"
            ),
            re.compile(r"[“【].*?号(?P<target>.*?)[”】]"),
            re.compile(r"[“【](?P<target>.*?)[”】]"),
            re.compile(r"名称.*号(?P<target>.*)。$"),
            re.compile(r"名称.*号(?P<target>.*)"),
        ]
        anchor_reg2 = re.compile(r"(投资目标|定向资产管理合同|基金的名称|运作方式|类别|风险收益|类型)")
        special_reg = re.compile(r"系指")

        elms = self.get_crude_elements(attr, kwargs.get("col_type"))
        scope_items = self.match_elements(elms, type_reg, amount=1, anchor_reg=anchor_reg, multi=False)
        if not scope_items:
            # 附近必须存在的字段：向上查找或向下查找，通用正则未找到时用特殊正则再匹配一次
            for regs in [anchor_reg2, special_reg]:
                scope_items = self.match_elements(
                    elms, type_reg2, amount=3, step=1, anchor_reg=regs, include=True
                ) or self.match_elements(elms, type_reg2, amount=3, step=-1, anchor_reg=regs, include=True)
                if scope_items:
                    break
        return ResultOfPredictor(data=scope_items, crude_elts=elms)

    def investment_scope(self, **kwargs):
        """大部分文档的投资范围预测答案位于如（二）投资范围 （三）投资策略之间
        1 匹配起始位置之间的所有元素块
        2 其余文档投资范围是一小段描述，通过正常的正则匹配
        """

        def find_index(pos="start"):
            if pos == "start":
                patterns = [
                    re.compile(r"^(?:[一二三四五六七八九十\d]+[.、]|[（(][一二三四五六七八九十]+[）)])投资(范围|领域)"),
                    re.compile(r"^第\d+\.\d*条投资范围"),
                    re.compile(r"^\d+\.\d+投资(范围|领域)"),
                ]
                opts = {"step": -1, "amount": 6}
            else:
                patterns = [
                    re.compile(
                        r"^(?:[一二三四五六七八九十\d]+[.、]|[（(][一二三四五六七八九十]+[）)])基?金?投资(?!范围|领域)"
                    ),
                    re.compile(r"^第\d+\.\d*条投资(?!范围|领域)"),
                    re.compile(r"^\d+\.\d+投资(?!范围|领域)"),
                ]
                opts = {"step": 1, "amount": 3}
            for elm in elms:
                near_elts = self.reader.find_elements_near_by(elm["element_index"], **opts)
                for near in near_elts:
                    if near["class"] == "PARAGRAPH":
                        matched = match_regs(patterns, clean_txt(near["text"]))
                        if matched:
                            return near, matched
            return None, None

        def find_scope():
            filter_elm = False
            regs = [
                re.compile(r"(?P<target>（\d+）.*)"),
                re.compile(r"(?P<target>\d+[、.].*)"),
            ]
            start, match = find_index("start")
            end = find_index("end")[0]
            scopes = []

            if match and match.re.pattern.startswith(r"第\d+\.\d"):
                # 需要过滤结果，提取例如(1)开头的内容
                filter_elm = True
            if start and end:
                amount = end["index"] - start["index"] - 1
                scope_elms = self.reader.find_elements_near_by(start["index"], amount=amount)
                for element in scope_elms:
                    if element["class"] != "PARAGRAPH":
                        continue
                    if filter_elm:
                        if match_regs(regs, clean_txt(element["text"])):
                            scopes.append(ParaResult(element["chars"], element))
                    else:
                        scopes.append(ParaResult(element["chars"], element))
            return scopes

        attr = "投资范围"
        elms = self.get_crude_elements(attr, kwargs.get("col_type"))
        scope_items = find_scope()

        if not scope_items:
            elms = self.filter_by_score(elms, 0.1)
            scope_reg = [
                re.compile(r"基金投资范围：(?P<target>投资于.*)"),
                re.compile(r"投资范围.*主要为?(?P<target>.*[^。])"),
                re.compile(r"(?P<target>(合伙企业)?的?经营范围为：?.*[^。])"),
            ]
            anchor_reg = re.compile(r"(投资|经营)(范围|目标)")
            pass_reg = re.compile(r"(特别风险|投资限制)")
            scope_items = self.match_elements(
                elms, scope_reg, amount=6, anchor_reg=anchor_reg, pass_reg=pass_reg, multi=True, include=True
            )
        scope_items = self.para2chars(scope_items)
        return ResultOfPredictor(data=scope_items, crude_elts=elms)

    def investment_ratio(self, **kwargs):
        attr = "最大投资比例"
        elms = self.get_crude_elements(attr, kwargs.get("col_type"))
        elms = self.filter_by_score(elms, 0.1)
        scope_reg = [
            re.compile(r"(?P<target>\d+[、.].*)"),
            re.compile(
                r"(?P<target>不得投资于法律法规、中国证监会(?:规定的禁止或限制的投资事项|、中国基金业协会规定的禁止或限制的投资事项))"
            ),
            re.compile(
                r"(?P<target>(?:本基金)?(?:不得以任何直接或间接的形式|不得从事.*?业务|不得进行.*?投资|.*遵循相关法律法规).*)"
            ),
            re.compile(r"(?P<target>本计划在投资运作.*应遵循以下投资限制：.*)"),
            re.compile(r"(?P<target>所有合伙人出资全部为货币出资.*不超过.*元.*以实际.*为准.*)"),
            re.compile(r"(?P<target>本合伙企业实缴规模最高不得超过.*规模达到.*后.*再接纳新的.*)"),
            re.compile(r"(?P<target>（\d+）.*)"),
        ]
        anchor_reg = re.compile(r"(投资限制|组合限制|资产投资策略|出资方式)")
        pass_reg = re.compile(r"投资运作的监督|投资禁止行为")
        scope_items = self.match_elements(
            elms, scope_reg, amount=20, anchor_reg=anchor_reg, pass_reg=pass_reg, multi=True
        )
        scope_items = self.para2chars(scope_items)
        return ResultOfPredictor(data=scope_items, crude_elts=elms)

    def manager_introduction(self, **kwargs):
        """基金经理介绍规则
        1.先通过得分过滤一部分元素
        2.如果匹配到多个元素，优先选择带有先生或女士的简介内容
        3.如果没有匹配到元素，有些情况得分比较低，需要修改score=0，递归再执行一次
        """
        attr = "基金经理介绍"
        regs = [
            re.compile(r"(?P<target>.*(?:具备|业绩|毕业|从业" r"|简介|任职|现为|曾任|从事|现任|丰富经验).*)"),
        ]
        anchor_reg = re.compile(r"(简介|简历|投资经理)")
        score = kwargs.get("score", 0.1)

        elms = self.get_crude_elements(attr, kwargs.get("col_type"))
        if score >= 0:
            elms = self.filter_by_score(elms, score)
        introduction = self.match_elements(elms, regs, anchor_reg=anchor_reg, multi=True)
        for idx, intro in enumerate(introduction):
            if re.search(r"(男|先生|女士?)", intro.elt["text"]) and len(intro.chars) > 25:
                return ResultOfPredictor(data=introduction[idx:], crude_elts=elms)

        if not introduction and score != 0:
            # 某些得分比较低的元素需要递归一次结果
            kwargs["score"] = 0
            return self.manager_introduction(**kwargs)
        introduction = self.para2chars(introduction)
        return ResultOfPredictor(data=introduction, crude_elts=elms)

    def stop_loss_line(self, **kwargs):
        """止损线"""

        def search_stop_line(items):
            """优先选则止损线的答案"""
            ret = []
            for item in items:
                if item.elt["text"].find("止损线") != -1 and item.elt["text"].find("止损线风险") == -1:
                    ret.append(item)
                    return ret

            if not ret:
                for item in items:
                    if item.elt["text"].find("止损机制") != -1:
                        ret.append(item)
                        return ret

            return [items[0]] if items else items

        attr = "止损线"
        regs = [
            re.compile(r"【(?P<target>\d+\.\d*)】元设置为止损线"),
            re.compile(
                r"""(?P<target>本?(?:基金|计划|资产管理计划)?(
                未设预警止损线|不设置预警止损机制|不设置预警线、止损线/补仓止损线
                |不设预警、止损线|未设置预警止损机制|未设止损线))""",
                re.X,
            ),
            re.compile(r"预警线、止损线分别为.*(?P<target>\d+\.\d*元?)"),
            re.compile(r"(?:止损|平仓)线[^\d]*(?P<target>\d+\.?\d*元?)"),
            re.compile(r"计划份额净值等于或小于(?P<target>\d+\.\d*元?)"),
            re.compile(r"平仓触发线[：为].*值【(?P<target>\d+\.\d*)】"),
        ]
        elms = self.get_crude_elements(attr, kwargs.get("col_type"))
        stop_loss_items = self.match_elements(elms, regs, multi=True)
        stop_loss_items = search_stop_line(stop_loss_items)
        stop_loss_items = self.para2chars(stop_loss_items)
        return ResultOfPredictor(data=stop_loss_items, crude_elts=elms)

    def warning_line(self, **kwargs):
        """预警线"""

        def search_warning_line(items):
            """优先选则包含预警线的答案, 然后选择包含预警机制的答案"""
            ret = []
            for item in items:
                if (item.elt["text"].find("预警止损线") != -1 or item.elt["text"].find("预警线") != -1) and item.elt[
                    "text"
                ].find("止损线风险") == -1:
                    ret.append(item)
                    return ret

            if not ret:
                for item in items:
                    if item.elt["text"].find("预警止损机制") != -1:
                        ret.append(item)
                        return ret

            return [items[0]] if items else items

        attr = "预警线"
        regs = [
            re.compile(
                r"""(?P<target>本?(?:基金|计划|资产管理计划)?(
            未设预警止损线|不设置预警止损机制|不设置预警线、止损线/补仓止损线
            |不设预警、止损线|未设置预警止损机制|未设预警线))""",
                re.X,
            ),
            re.compile(r"(?P<target>本?基?金?不设置(预警止损机制|预警线、止损线/补仓止损线))"),
            re.compile(r"预警线[:：]本?(基金|计划)(份额|单位)净值[【\[]?(?P<target>[\d.]+元?)[】\]]?"),
            re.compile(r"将(计划|基金)份额净值为?[【\[]?(?P<target>\d+\.?\d*)[】\]]?元?[】\]]?设置为预警线"),
            re.compile(r"预警线[:：](?P<target>[\d.]+)"),
            re.compile(r"预警线、止损线分别为.*?(?P<target>[\d.,]+元)"),
            re.compile(r"预警线为(?P<target>\d+\.?\d*)元"),
        ]

        elms = self.get_crude_elements(attr, kwargs.get("col_type"))
        warning_items = self.match_elements(elms, regs, multi=True)
        warning_items = search_warning_line(warning_items)
        warning_items = self.para2chars(warning_items)
        return ResultOfPredictor(data=warning_items, crude_elts=elms)

    def filter_by_score(self, elms, score=0.9):
        """通过得分过滤一部分无效的元素，避免正则匹配出现干扰"""
        if score == 0:
            return elms

        ret = []
        for elm in elms:
            if elm["score"] >= score:
                ret.append(elm)
            else:
                break
        return ret

    def is_aim_elt(self, anchor_reg, elt_idx, options):
        """
        附近必须出现某个关键词
        """
        if not anchor_reg:
            return True
        amount = options.get("anchor_amount", 6)
        step = options.get("step", -1)
        include = options.get("include", False)
        pre_elts = self.reader.find_elements_near_by(elt_idx, amount=amount, step=step, include=include)
        for pre_elt in pre_elts:
            # print('~~~~~', anchor_reg.search(clean_txt(pre_elt['text'])), clean_txt(pre_elt['text']))
            if pre_elt["class"] == "PARAGRAPH" and anchor_reg.search(clean_txt(pre_elt["text"])):
                return True
        return False

    def is_not_aim_elt(self, pass_reg, elt_idx, options):
        """
        附近不能出现某个关键词
        """
        if not pass_reg:
            return False
        amount = options.get("pass_amount", 5)
        step = options.get("step", -1)
        include = options.get("include", False)
        pre_elts = self.reader.find_elements_near_by(elt_idx, amount=amount, step=step, include=include)
        for pre_elt in pre_elts:
            # print('~~~~~', pass_reg.search(clean_txt(pre_elt['text'])), clean_txt(pre_elt['text']))
            if pre_elt["class"] == "PARAGRAPH" and pass_reg.search(clean_txt(pre_elt["text"])):
                return True
        return False

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
            next_elts = self.reader.find_elements_near_by(elt["index"], step=1, amount=2)
            for next_elm in next_elts:
                if next_elm["class"] == "PAGE_FOOTER":
                    continue
                if next_elm["class"] == "PARAGRAPH":
                    elt["text"] += next_elm["text"]
                    elt["chars"] += next_elm["chars"]
        return elt

    def simple_reg_extract(self, attr, **kwargs):
        items = []
        elts = self.get_crude_elements(attr, kwargs.get("col_type"))
        options = self.attr2reg[attr]
        anchor_reg = self.attr2reg[attr].get("anchor_reg")  # 附近必须出现某个关键词
        pass_reg = self.attr2reg[attr].get("pass_reg")  # 附近不能出现某个关键词
        for element in elts:
            ele_typ, element = self.reader.find_element_by_index(element["element_index"])
            if ele_typ == "PARAGRAPH":
                element = self.fix_continued_para(element)  # 修复跨页段落
                # print('----------' * 3, idx, element['index'], element['text'], )
                for reg in self.attr2reg[attr]["regs"]:
                    matched = reg.search(clean_txt(element["text"]))
                    if matched:
                        # print('========', matched, reg)
                        if anchor_reg and not self.is_aim_elt(anchor_reg, element["index"], options):
                            continue
                        if pass_reg and self.is_not_aim_elt(pass_reg, element["index"], options):
                            continue
                        for each in reg.finditer(clean_txt(element["text"])):
                            c_start, c_end = each.start("target"), each.end("target")
                            sp_start, sp_end = index_in_space_string(element["text"], (c_start, c_end))
                            chars = element["chars"][sp_start:sp_end]
                            if chars and chars not in items:
                                items.append(chars)
                                # print('*******', [x['text'] for x in element['chars'][sp_start:sp_end]])
        items = [CharResult(chars) for chars in items]
        return ResultOfPredictor(items, crude_elts=elts)

    def temp_open(self, **kwargs):
        attr = "是否允许临开"
        elts = self.get_crude_elements(attr, kwargs.get("col_type"))

        ps_allow = [
            re.compile(
                "(?P<target>管理人(在.*?的前提下，)?可根据基金运作情况(自主)?设立临时开放日([，（](包括|含在).*?)?"
                "[，。]((封闭期内的?)?临时开放日[仅只]?允许(申购|赎回).*?(申购|赎回)|每半?[季|年|月]度?至少[一二三四五]次)"
                "(.*不设置临时开放日[)）]?)?)"
            ),
            re.compile(r"(?P<target>.*?可以?([^。]*?)设[置立定]临时开放日.*?。)"),
            re.compile(
                r"(?P<target>([私公]募)?(基金)?管理人(在.*?的前提下，)?可以?根据基金运[作行]情况(自主)?设[立定]临时开放日([(（].*?[)）]?)?[,，。])"
            ),
            re.compile("(?P<target>可以接[纳受]新的(有限|普通)?合伙人入伙)"),
            re.compile("(?P<target>基金投资者可根据基金运作情况自主.*作为临时开放日.*通知基金管理人)"),
            re.compile("(?P<target>本?基金投资者有权自主决定.*(申购和赎回|开放日))"),
            re.compile("(?P<target>由基金管理人安排临时开放日.*)"),
            re.compile("(?P<target>由?基金管理人.*?设立临时开放日)"),
            re.compile("(?P<target>除非.*?(否则|同意).*?不接[纳受]新的(有限|普通)合伙人入伙)"),
            re.compile("(?P<target>(有限|普通)合伙人入伙.?[需须]取得(有限|普通)合伙人同意)"),
            re.compile("(?P<target>新的?(有限|普通)?合伙人.*?即可入伙)"),
            re.compile("(?P<target>(有限|普通)?合伙人加入合伙企业.?应.*?)。"),
            re.compile("(?P<target>(有限|普通)?合伙人应为.*?接受合伙人入伙)"),
            re.compile("(?P<target>本资产管理人计划半封闭运作，管理人可根据需要增加临时开放日)"),
            re.compile("(?P<target>管理人可根据需要(增加|设置)临时开放日)"),
            re.compile("(?P<target>本基金原则上封闭运作.*?临时开放日.*?申购.*?赎回)"),
        ]

        ps_deny = [
            re.compile(
                r"(?P<target>在?本基金存续期[内间](封闭式?运作)?[，。]?不(办理|开放|能)申购(和赎回业务|参与或退出))"
            ),
            re.compile(r"合伙企业(^[，。]*)?(?P<target>不接[纳受]新的(有限)合伙人入伙)"),
            re.compile(r"(?P<target>存续期间不增?设立?开放日)"),
            re.compile(r"(?P<target>(无|不设[定立置]?)临时开放日)"),
        ]

        pass_reg = re.compile(r"分级基金的?投资风险")
        allow_items = self.match_elements(elts, ps_allow, True, pass_reg=pass_reg, amount=3)
        deny_items = self.match_elements(elts, ps_deny, True, pass_reg=pass_reg, amount=3)
        items, value = [], None
        if deny_items:
            items, value = deny_items, "否"
        elif allow_items:  # 优先考虑允许临开情况
            items.extend(allow_items)
            value = "是"
        items = self.para2chars(items)
        return ResultOfPredictor(data=items, value=value, crude_elts=elts)

    def structuralization(self, **kwargs):
        attr = "是否结构化"
        elts = self.get_crude_elements(attr, kwargs.get("col_type"))

        ps_deny = [re.compile(r"(?P<target>不设置(结构化|分级)安排)")]
        ps_allow = [
            re.compile(r"(?P<target>.*?基金的?分[类级].*)"),  # 出现基金分级标注整段文字
            re.compile(r"(?P<target>分级基金将基础份额结构化.*)"),
            re.compile(r"(?P<target>.*基金资产分为(优先|进取)级.*)"),
        ]
        pass_reg = re.compile(r"基金合同的?变更")
        allow_items = self.match_elements(elts, ps_allow, pass_reg=pass_reg, amount=10)
        deny_items = self.match_elements(elts, ps_deny, pass_reg=pass_reg, amount=10)
        items, value = [], None
        if deny_items:
            items, value = deny_items, "否"
        elif allow_items:
            items.extend(allow_items)
            value = "是"
        return ResultOfPredictor(data=items, value=value, crude_elts=elts)

    def return_visit(self, **kwargs):
        attr = "是否设置回访"
        elts = self.get_crude_elements(attr, kwargs.get("col_type"))
        ps_deny = [re.compile(r"(?P<target>不设回访制度)")]
        ps_allow = [
            re.compile(r"(?P<target>募集机构.*?方式进行.*?回访)"),
            re.compile(r"(?P<target>投资冷静期内进行的回访确认无效)"),
            re.compile(r"(?P<target>[\d\.]*）确认(受访人|投资者).*)"),
            re.compile(r"(?P<target>在投资冷静期满后，普通合伙人应指.*?适当方式进行投资回访)"),
            re.compile(r"(?P<target>回访过程不得出现诱导性陈述)"),
        ]
        pass_reg = False
        allow_items = self.match_elements(elts, ps_allow, pass_reg=pass_reg, amount=10)
        deny_items = self.match_elements(elts, ps_deny, pass_reg=pass_reg, amount=10)
        items, value = [], None
        if deny_items:
            items, value = deny_items, "否"
        elif allow_items:
            items.extend(allow_items)
            value = "是"
        return ResultOfPredictor(data=items, value=value, crude_elts=elts)

    def allow_contract_extension(self, **kwargs):
        attr = "是否允许合同展期"
        elts = self.get_crude_elements(attr, kwargs.get("col_type"))
        ps_deny = [re.compile(r"(?P<target>.*债券回购到期后不展期)")]
        ps_allow = [
            re.compile(r"(?P<target>普通合伙人.*?延长.*?次.*?延长期限.*?。)"),
            re.compile(r"(?P<target>本计划可以提前结束或者展期)"),
            re.compile(r"(?P<target>本集合计划可以展期)"),
            re.compile(r"(?P<target>经各方书面协商一致可展期)"),
            re.compile(r"(?P<target>经委托人同意，可展期)"),
            re.compile(r"(?P<target>(募集期限.*?)?管理人有权延长或缩短募集期)"),
            re.compile(
                r"(?P<target>(私募)?基?金?管理人有权根据本?基?金?(募集|销售的实际)情况(按照相关程序)?(延长或缩短|缩短或延长|提前结束或延长)(初始)?(募集|销售)期.*?适用.*?机构)"
            ),
            re.compile(r"(?P<target>经.*?协商一致后?.*?可以?展期)"),
            re.compile(r"(?P<target>经合伙人会议通过，可以延长本有限合伙企业的合伙期限)"),
            re.compile(
                r"(?P<target>经全体合伙人一致同意，根据本合伙企业投资情况，可将本合伙企业的合伙期限延长.*?每次延长期限不超过.*?年)"
            ),
            re.compile(r"(?P<target>如发生本合同约定的计划提前终止或展期情形时，本计划可提前终止或展期。)"),
            re.compile(
                r"(?P<target>全体存续投资者、管理人和托管人协商一致或经份额持有人大会通过决议，且同时满足展期条件的，本计划可以展期)"
            ),
            re.compile(
                r"(?P<target>资产管理计划存续期届满时，经过.*?决议同意展期，并符合本合同约定的展期条件，本资产管理计划可以展期。)"
            ),
            re.compile(
                r"(?P<target>[经|在].*?协商一致时?，(可对本合同进行提前终止或延期|决定提前终止本计划或进行延长存续期限))"
            ),
            re.compile(r"(?P<target>根据合伙企业的经营需要，普通合伙人有权独立决定将合伙企业的存续期限延长.*?年。)"),
            re.compile(
                r"(?P<target>管理人有权将本合伙企业期限延长至本合伙协议直接或间接所持股权或股票全部变现完成日止)"
            ),
            re.compile(r"(?P<target>本合同自产品成立日起委托期限为.*?年，经各方当事人协商一致，可展期)"),
            re.compile(r"(?P<target>合同到期日前.*?本合同自动续期.*?以后本合同的续期以此办理)"),
            re.compile(r"(?P<target>本资产管理计划在存续期届满前经各方当事人协商一致可以展期)"),
            re.compile(r"(?P<target>经全体委托人协商一致本计划可展期运作.*?个月)"),
            re.compile(r"(?P<target>若资产管理合同期限届满前.*?则本合同自动延期.*?。)"),
            re.compile(r"(?P<target>基金管理人有权根据基金募集情况延长或缩短募集期)"),
        ]
        pass_reg = False
        allow_items = self.match_elements(elts, ps_allow, pass_reg=pass_reg, amount=10)
        deny_items = self.match_elements(elts, ps_deny, pass_reg=pass_reg, amount=10)
        items, value = [], None
        if deny_items:
            items, value = deny_items, "否"
        elif allow_items:
            items.extend(allow_items)
            value = "是"
        return ResultOfPredictor(data=items, value=value, crude_elts=elts)

    def accrual_method(self, **kwargs):
        attr = "计提方式"
        elts = self.get_crude_elements(attr, kwargs.get("col_type"))
        items = []
        regs = [
            re.compile(r"(?P<target>本基金不[收|提]取(管理人)?的?业绩报酬)"),
            re.compile(r"(?P<target>本基金管理人不[收|提]取业绩报酬)"),
            re.compile(r"(?P<target>本基金无业绩报酬)"),
            re.compile(r"(?P<target>本(产品|基金)管理人不[收|提]取业绩报酬)"),
            re.compile(r"(?P<target>本基金无私募基金管理人业绩报酬)"),
            re.compile(r"(?P<target>本计划不提取管理人和投资顾问的业绩报酬)"),
            re.compile(r"(?P<target>本资产管理计划不计提业绩报酬)"),
            re.compile(r"(?P<target>本合伙企业(的普通合伙人、)?管理人不收取业绩报酬)"),
            re.compile(r"(?P<target>基金在向基金投资者进行资产分配及基金清算时不提取业绩报酬)"),
            re.compile(r"(?P<target>如分配完年化收益.*?分配给有限合伙人.*?。)"),
            re.compile(r"本基金采用“(?P<target>.*?)”计算"),
            re.compile(r"(?P<target>本基金在满足产品结束.*?计提业绩报酬)"),
            re.compile(r"(?P<target>本集合计划在终止时.*?计提业绩报酬)"),
            re.compile(r"(?P<target>本基金在产品结束时.*?本基金剩余基金资产全部作为业绩报酬归基金管理人所有)"),
            re.compile(r"(?P<target>本基金在满足一定条件下，基金管理人可以提取业绩报酬.*)"),
            re.compile(r"采用“(?P<target>高水位法)”计算(基金管理人|投资顾问)的业绩报酬"),
            re.compile(r"(?P<target>如仍有余额.*?分配给普通合伙人及管理人.*?投资成本分摊比例分配给该有限合伙人)"),
            re.compile(r"(?P<target>在一个业绩报酬计算周期.*?基金管理人按组合在该周期内超额收益的.*计提业绩报酬)"),
        ]

        special_regs = [
            re.compile(r"(?P<target>^[ACDEF]=.*；)"),
            re.compile(r"(?P<target>^（\d）.*；?)"),
            re.compile(r"(?P<target>业绩报酬计提标准为:)"),
            re.compile(r"(?P<target>当[ACDEF]>[ACDEF]时，提取.*?；)"),
            re.compile(r"(?P<target>在?(基金份额持有人|资产管理计划份额持有人|投资者).*?计提(基准|业绩报酬)。)"),
            re.compile(r"(?P<target>\(\d\)\s?首先向.*?本金)"),
            re.compile(r"(?P<target>\(\d\)\s?如有余额.*)"),
            re.compile(
                r"(?P<target>[\(（]\d[\)）]\s?(合伙企业|剩余资产与收益|如有剩余|按照各合伙人的|向全体有限合伙人|如分配完上述).*)"
            ),
            re.compile(
                r"(?P<target>首先对全体有限合伙人和普通合伙人进行资产分配，直至每位合伙人累计已分得金额达到其实缴金额.*)"
            ),
            re.compile(r"(?P<target>首先向全体合伙人分配，直至全体合伙人收回已实缴的本金.*)"),
            re.compile(
                r"(?P<target>如有余额.*?部分按照有限合伙人的份额比例分配给各有限合伙人，其余部分分配给普通合伙人.*)"
            ),
            re.compile(r"(?P<target>如经过前述分配仍有剩余.*有限合伙人分配收益.*)"),
            re.compile(r"(?P<target>投资超额收益率小于、等于.*)"),
            re.compile(r"(?P<target>优先向各合伙人按照各自在本有限合伙企业中的实缴出资比例分配项目投资本金)"),
            re.compile(
                r"(?P<target>普通合伙人不收取业绩报酬，剩余的超额收益各合伙人按照各自在本有限合伙企业中的实缴出资比例分配)"
            ),
            re.compile(r"(?P<target>投资超额收益率大于.*)"),
            re.compile(r"(?P<target>优先向各合伙人分配各自在本有限合伙企业中的实缴出资本金)"),
            re.compile(r"(?P<target>超额收益的.*?按各合伙人在本有限合伙企业中的实缴出资比例分配给各合伙人。)"),
            re.compile(r"(?P<target>本资产管理计划业绩报酬在委托财产提取日和计划终止日.*?计提)"),
            re.compile(r"(?P<target>初始或追加的委托资产按照先进先出法进行提取.*比例提取业绩报酬。)"),
            re.compile(r"(?P<target>在?投资者退出和本计划终止时.*都按规定计提业绩报酬。)"),
            re.compile(r"(?P<target>如剩余收益不足.*)"),
        ]
        pass_reg = []

        allow_items = self.match_elements(elts, regs, pass_reg=pass_reg, amount=10)
        if not allow_items:
            allow_items = self.match_elements(elts, special_regs, pass_reg=pass_reg, amount=10, multi=True)
        items.extend(allow_items)
        items = sorted(items, key=lambda item: item.elt["index"])
        items = self.para2chars(items)
        return ResultOfPredictor(data=items, crude_elts=elts)

    def match_elements(self, elts, regs, multi=False, pass_reg=None, step=-1, amount=5, anchor_reg=None, **kwargs):
        items = []
        options = {
            "pass_amount": amount,
            "step": step,
            "anchor_amount": amount,
            "include": kwargs.get("include", False),
        }

        for element in elts:
            if "index" in element:
                ele_typ, element = self.reader.find_element_by_index(element["index"])
            else:
                ele_typ, element = self.reader.find_element_by_index(element["element_index"])
            if ele_typ == "PARAGRAPH":
                element = self.fix_continued_para(element)
                c_text = clean_txt(element["text"])
                matched = match_regs(regs, c_text)

                if anchor_reg and not self.is_aim_elt(anchor_reg, element["index"], options):
                    continue
                if matched and not self.is_not_aim_elt(pass_reg, element["index"], options):
                    gr_idx = matched.re.groupindex["target"]
                    c_start, c_end = matched.start(gr_idx), matched.end(gr_idx)
                    sp_start, sp_end = index_in_space_string(element["text"], (c_start, c_end))
                    items.append(ParaResult(element["chars"][sp_start:sp_end], element))
                    if not multi:
                        break
            elif ele_typ == "TABLE":
                for _, cell in element.get("cells").items():
                    c_text = clean_txt(cell["text"])
                    matched = match_regs(regs, c_text)
                    if matched:
                        if anchor_reg and not self.is_aim_elt(anchor_reg, element["index"], options):
                            continue
                        if matched and not self.is_not_aim_elt(pass_reg, element["index"], options):
                            gr_idx = matched.re.groupindex["target"]
                            c_start, c_end = matched.start(gr_idx), matched.end(gr_idx)
                            sp_start, sp_end = index_in_space_string(cell["text"], (c_start, c_end))
                            items.append(ParaResult(cell["chars"][sp_start:sp_end], element))
                            if not multi:
                                break
        return items
