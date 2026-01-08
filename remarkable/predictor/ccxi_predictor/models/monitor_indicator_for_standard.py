from copy import deepcopy

from remarkable.common.pattern import PatternCollection
from remarkable.common.util import clean_txt
from remarkable.predictor.ccxi_predictor.models.fake_model import FakeModel
from remarkable.predictor.mold_schema import SchemaItem
from remarkable.predictor.schema_answer import CharResult

LEVEL_REG = r"(【?A+[\+-＋]?】?|【?B+[\+＋]?】?)"

# 评级公司
RATING_FIRMS_FLAG = PatternCollection(r"评级机构")
RATING_FIRMS1 = PatternCollection(
    [
        r"(?<!主体)评级机构.*?[：:].*?([是系])?指“?(?P<dst>.*?)[和。”.与]",
        r"资信等级跟踪评估.*?[：:](?P<dst>.*?公司)",
        r"(?<!主体)评级机构.*?[：:；].*?([是系])?指?“?(?P<dst>.*公司)",
    ]
)
RATING_FIRMS2 = PatternCollection(r"(?<!主体)评级机构.*?[：:].*?[是系]指.*?[和与]“?(?P<dst>.*?)[。,”.]")

# 阈值_必备评级等级条款
INVALID_RATING_TERM_FLAG = PatternCollection(r"委托人")
RATING_TERM_FLAG = PatternCollection(r"必备评级等级")
RATING_TERM_PATTERN_COMMON = [
    r"就任一“评级机构”而言，系指主体长期信用等级(?P<dst>(高于或)?等于A+[\+-]?级|低于A+[\+-]?级)",
    rf"就.*?和.*?而言.*指(?P<dst>{LEVEL_REG}级及更高的主体长期信用等级)",
]

RATING_TERM1 = r"{}.*?主体长期信用[等评]级(?P<dst>高于或等于A+[\+-]?级|低于A+[\+-]?级)"
RATING_TERM1_LIST = RATING_TERM_PATTERN_COMMON + [
    rf"(?P<dst>{LEVEL_REG}级及更高的主体长期信用等级)",
    rf"(?<!给予“委托人”的)主体长期信用[等评]级均?(?P<dst>高于或等于{LEVEL_REG}级?|低于{LEVEL_REG}级?(\(不含{LEVEL_REG}级\))?|不低于{LEVEL_REG}级但低于{LEVEL_REG}级|等于(低于)?{LEVEL_REG}级?)",
    r"必备评级等级.*?长期主体信用[等评]级均?(?P<dst>高于或等于【?A+[\+-]?】?级)",
    r"必备评级等级.*?(?P<dst>【?A+[\+-]?】?级(及更高)?).*?信用[等评]",
]
RATING_TERM2 = r"(；|且|或者?).*?{}.*?主体长期信用[等评]级(?P<dst>高于或等于A+[\+-]?级|低于A+[\+-]?级)。"
RATING_TERM2_LIST = RATING_TERM_PATTERN_COMMON + [
    rf"(；|且|或者?).*?(?P<dst>{LEVEL_REG}级及更高的主体长期信用等级)",
    rf"(；|且|或者?).*?主体长期信用[等评]级均?(?P<dst>高于或等于{LEVEL_REG}级?|低于{LEVEL_REG}级?(\(不含{LEVEL_REG}级\))?|不低于{LEVEL_REG}级但低于{LEVEL_REG}级|等于(低于)?{LEVEL_REG}级?)",
    r"[,;；].*?(?P<dst>【?A+[\+-]?】?级(及更高)?).*?信用[等评]",
    r"[,;；].*?期主体信用[等评]级均?(?P<dst>高于或等于【?A+[\+-]?】?级)",
    r"必备评级等级.*?(；|且|或者?).*?信用[等评]级(?P<dst>高于或等于【?B+[\+＋]?】?级)",
]

# 资产服务机构主体等级条款
INVALID_AGENCY_CLAUSE_FLAG = PatternCollection(r'(给予["“]?委托人|基础债务人)')
AGENCY_CLAUSE_FLAG = PatternCollection(
    r"回收款转付(期间|日)|权利完善事件|加速归集事件|加速清偿事件|回收款归集日|处置收入转付(期间|日)|个别通知事件"
)
AGENCY_CLAUSE_PATTERN_COMMON = [
    r"((贷款|资产)服务机构).*?信用[等评]级均(?P<dst>(下降至)?不?[等高低]于(或?[高低等]于)?“?(【?A+[\+-＋]?】?|【?B+\+＋】?)”?级?(但?[(（]?不?(包?含|低于).*?级[)）]?)?)",
]
AGENCY_CLAUSE1 = r"{}.*?信用[等评]级(?P<dst>高于或等于A+[\+-]?级|低于A+[\+-]?级|低于A+[\+-]?级(（不包?含A+[\+-]?级）)?)"
AGENCY_CLAUSE1_LIST = AGENCY_CLAUSE_PATTERN_COMMON + [
    r"((贷款|资产)服务机构).*?信用[等评]级均?(?P<dst>低于AAA（不含AAA）)",
    r"((贷款|资产)服务机构).*?信用[等评]级(?P<dst>(下降至)?不?[等高低]于(或?[高低等]于)?“?(【?A+[\+-＋]?】?|【?B+\+＋】?)”?级?(但?[(（]?不?(包?含|低于).*?级[)）]?)?(（不含）)?)",
    r"((贷款|资产)服务机构).*?信用[等评]级均?(?P<dst>(高于或)?[等高低]于[【(（]?A+[\+-][】)）]?级)",
]
AGENCY_CLAUSE2 = r"(；|且|或者?).*?{}.*?信用[等评]级(?P<dst>高于或等于A+[\+-]?级|低于A+[\+-]?级|低于A+[\+-]?级(（不包?含A+[\+-]?级）)?)"
AGENCY_CLAUSE2_LIST = AGENCY_CLAUSE_PATTERN_COMMON + [
    r"(且|或[者“]).*?((贷款|资产)服务机构).*?信用[等评]级(?P<dst>(下降至)?不?[等高低]于(或?[高低等]于)?“?(【?A+[\+-＋]?】?|【?B+\+＋】?)”?级?(但?[(（]?不?(包?含|低于).*?级[)）]?)?(（不含）)?)",
    r"(；|且|或者?).*?((贷款|资产)服务机构).*?信用[等评]级(?P<dst>(下降至)?不?[等高低]于(或?[高低等]于)?【?B+[\+＋]?】?级?)",
]

# 委托人/发起人主体等级条款
ORIGINATOR_TERM_FLAG = PatternCollection(r"权利完善事件|贷款提前到期事件|个别通知事件|加速清偿事件|内部归集日")
ORIGINATOR_TERM_PATTERN_COMMON = [
    rf"(某一家|任一).*?委托人.*?主体长期信用等级(?P<dst>高于或等于{LEVEL_REG}级|低于【?A+[\+-]?】?(级（不含）)?|低于A)",
    r"(发起机构|委托人).*?(?P<dst>(不?再?具备(任一)?“必备评级等级”(任一)?|丧失(任一)?“必备评级等级”(之一)?))",
]
ORIGINATOR_TERM1 = r"{}.*?委托人.*?主体长期信用[等评]级(?P<dst>高于或等于A+[\+-]?级|低于A+[\+-]?级)"
ORIGINATOR_TERM1_LIST = ORIGINATOR_TERM_PATTERN_COMMON + [
    rf"委托人.*?主体长期信用[等评]级均?(?P<dst>高于或等于{LEVEL_REG}级|低于{LEVEL_REG}级([（\(]不含{LEVEL_REG}级[\)）])?|不低于{LEVEL_REG}级但低于{LEVEL_REG}级)",
    r"发起机构.*?(?P<dst>(不?具备任一“必备评级等级”|丧失任一“必备评级等级”|降低至【AA】等级及以下级别))",
    rf"(委托人|原始权益人).*?信用[等评]级(?P<dst>低于(或等于)?{LEVEL_REG}级([\(（]不包?含{LEVEL_REG}级[\)）])?)",
    r"(委托人|原始权益人).*?.*?信用[等评]级(的评级)?(?P<dst>(下?(降至)?(低于)?【?A+[\+-]?】?级?(以下)?[(（]?不含【?A+[\+-]?】?级?[)）]?|降至A))",
    r"(委托人|原始权益人).*?(信用|主体)[等评]级(?P<dst>下降到A+[\+-]?（不含）以下|低于【A+[\+-]?\(不含\)】级|(等于)?或?(低于)?A+[\+-]?级?|([高低]于)?或?(等于)?【?A+[\+-]?】?级?)",
    r"评级机构给予(国家电投|文化租赁).*?(信用|主体)[等评]级(?P<dst>下降到A+[\+-]?（不含）以下|低于【A+[\+-]?\(不含\)】级|(等于)?或?(低于)?A+[\+-]?级?|([高低]于)?或?(等于)?A+[\+-]?级?)",
    rf"发起机构.*?(信用)?[等评]级(?P<dst>低于(或等于)?{LEVEL_REG}级?)",
    r"评级机构给予中车的主体长期信用等级(?P<dst>低于AA\+级)",
]
ORIGINATOR_TERM2 = r"(；|且|或者?).*?{}.*?委托人.*?主体长期信用[等评]级(?P<dst>高于或等于A+[\+-]?级|低于A+[\+-]?级)。"
ORIGINATOR_TERM2_LIST = ORIGINATOR_TERM_PATTERN_COMMON + [
    rf"(；|且|或者?).*?委托人.*?信用[等评]级均?(?P<dst>高于或等于{LEVEL_REG}级|低于{LEVEL_REG}级([（\(]不含{LEVEL_REG}级[\)）])?|不低于{LEVEL_REG}级但低于{LEVEL_REG}级)",
    r"发起机构.*?(?P<dst>(不?具备任一“必备评级等级”|丧失任一“必备评级等级”))",
    rf"(；|且|或者?).*?委托人.*?信用[等评]级(?P<dst>低于(或等于)?{LEVEL_REG}级([\(（]不包?含{LEVEL_REG}级[\)）])?)",
]

# 提取 资金保管机构主体等级条款
INVALID_CUSTODIAN_TERM_FLAG = PatternCollection(r"委托人")
CUSTODIAN_TERM_FLAG = PatternCollection(r"(资[产金]保管机构|保管银行|[托保]管人)解任事件")
CUSTODIAN_TERM_PATTERN_COMMON = [
    r"((某|任)一).*?“?(资金保管机构|保管银行|托管人总行)”?.*?信用[等评]级均?(?P<dst>(下降至)?不?[等高低]于(或?[高低等]于)?“?(【?A+[\+-＋]?】?|【?B+\+＋】?)”?级?(但?[(（]?不?(包?含|低于).*?级[)）]?)?)",
    rf"评级机构中某一家对资金保管机构.*?信用[等评]级级(?P<dst>高于或等于{LEVEL_REG}级|低于{LEVEL_REG}级)",
    r"(资金保管机构|保管银行|托管人总行).*?(?P<dst>(不?具备任一“必备评级等级”|丧失(任一)?“必备评级等级”|丧失“?必备评级等级”?之一|低于“?必备评级等级”?))",
]
CUSTODIAN_TERM1 = r"{}.*?.*?信用[等评]级均?(?P<dst>(下降至)?不?[等高低]于(或?[高低等]于)?“?(【?A+[\+-＋]?】?|【?B+\+＋】?)”?级?(但?[(（]?不?(包?含|低于).*?级[)）]?)?)"
CUSTODIAN_TERM1_LIST = CUSTODIAN_TERM_PATTERN_COMMON + [
    r"(资金保管机构|保管银行|托管人总行).*?信用[等评]级均?(?P<dst>(下降至)?不?[等高低]于(或?[高低等]于)?“?(【?A+[\+-＋]?】?|【?B+\+＋】?)”?级?(但?[(（]?不?(包?含|低于).*?级[)）]?)?)",
]
CUSTODIAN_TERM2 = r"{}.*?.*?信用[等评]级均?(?P<dst>(下降至)?不?[等高低]于(或?[高低等]于)?“?(【?A+[\+-＋]?】?|【?B+\+＋】?)”?级?(但?[(（]?不?(包?含|低于).*?级[)）]?)?)"

CUSTODIAN_TERM2_LIST_STANDARD = CUSTODIAN_TERM_PATTERN_COMMON + [
    r"(；|且|或者?).*?长期主体信用[等评]级均?(?P<dst>高于或等于【?A+[\+-]?】?级|低于【?A+[\+-]?】?级)",
]

# 提取 增信主体等级条款
INVALID_CREDIT_TERM_FLAG = PatternCollection(r"委托人|贷款服务机构")
CREDIT_TERM_FLAG = PatternCollection(
    [
        r"回收款转付日|回收款转付期间|权利完善事件|(信托贷款|自动生效的)?加速清偿事件|贷款提前到期事件|回收款归集日|处分启动事件|提前终止事件",
        r"运营维持(承诺人|保证人)",
    ]
)
CREDIT_TERM1 = r"{}.*?主体长期信用[等评]级(?P<dst>高于或等于A+[\+-]?级|低于A+[\+-]?级)"
CREDIT_PREFIX = r"(共同债务人|差额(支付|补足)承诺人|专项计划担保人|“?借款人”?|担保人|回购义务人|流动性支持承诺人|运营维持(承诺人|保证人)|履约保证人)"
CREDIT_TERM1_LIST = [
    rf"{CREDIT_PREFIX}.*?[等评]级均?(?P<dst>下?降[至为]【?A+\+?】?级?([(（]不?含A*?[）)])?([及或]?以下)?)",
    rf"{CREDIT_PREFIX}.*?[等评]级均?(?P<dst>(下降至)?不?[等高低]于(或?[高低等]于)?“?(【?A+[\+-＋]?】?|【?B+\+＋】?)”?级?(但?[(（]?不?(包?含|低于).*?级[)）]?)?(（不含）)?)",
    rf"{CREDIT_PREFIX}.*?[等评]级均?(?P<dst>下降至【AA\+】级以下（不含）)",
    rf"{CREDIT_PREFIX}.*?[等评]级均?(?P<dst>下?降至【?A+\+?】?级?(或?以下)?([(（]不含A+[）)])?)",
    rf"{CREDIT_PREFIX}.*?[等评]级均?(?P<dst>降至“AA”以下（含“AA”）)",
]
CREDIT_TERM2 = r"(；|且|或者?).*?{}.*?主体长期信用[等评]级(?P<dst>高于或等于A+[\+-]?级|低于A+[\+-]?级)。"
CREDIT_TERM2_LIST = [
    rf"(；|且|或者?).*?{CREDIT_PREFIX}.*?主体长期信用[等评]级(?P<dst>高于或等于{LEVEL_REG}级|低于{LEVEL_REG}级(\(不含{LEVEL_REG}级\))?)",
]

# 提取 产品等级条款
INVALID_PRODUCT_TERM_FLAG = PatternCollection(r"委托人|资产支持证券")
PRODUCT_TERM_FLAG = PatternCollection(
    [
        r"(加速|提前)清偿事件|合格投资|评级下调事件|贷款提前到期事件|处分启动事件|市场化处置期起始日|信用级别|提前终止事件",
        r"质押财产回收计算日",
        r"债券提前到期事件",
    ]
)
PRODUCT_TERM1 = r"{}.*?主体长期信用[等评]级(?P<dst>高于或等于A+[\+-]?级|低于A+[\+-]?级)"  # 不会出现主体信用评级
PRODUCT_TERM1_LIST = [
    r"优先[AB]?[级档]资产支持票据.*?评级(?P<dst>(低于A+\+?sf|下调至【AA\+】及以下级别|下降至低于A级（不含A级）|下调至【】及以下级别))",
]
PRODUCT_TERM2 = r"(；|且|或者?).*?{}.*?主体长期信用[等评]级(?P<dst>高于或等于A+[\+-]?级|低于A+[\+-]?级)。"
PRODUCT_TERM2_LIST = [
    rf"(；|且|或者?).*?主体长期信用[等评]级(?P<dst>高于或等于{LEVEL_REG}级|低于{LEVEL_REG}级(\(不含{LEVEL_REG}级\))?)",
]

# 标准条款
PRODUCT_TERM1_STANDARD = [
    r"资产支持证券(的信用)?(评级|级别|等级)为(?P<dst>.*?级)",
    r"资产支持证券的?评级均?为?(?P<dst>(降为.*?及以下|.*?级))",
    r"资产支持证券的?(最近一次)?((信用)?评级|信用等级)(?P<dst>低于.*?(级|\+))",
    r"资产支持证券获得评级机构给予的(?P<dst>.*?)评级",
    r"资产支持证券的信用评级(分别为)?(?P<dst>.*?)[。,，]",
    r"资产支持证券债项评级(?P<dst>降为【A+】级或以下)",
    r"资产支持证券的?(评级|信用等级|信用级别)为?(?P<dst>[高低等].*?(级|下))",
    r"(评级均为|信用级别为)(?P<dst>A+sf)",
    r"资产支持证券的?(最近一次)?((信用)?评级|信用等级)(?P<dst>下降至.*?\))",
    r"资产支持证券为(?P<dst>.*?级)",
    r"资产支持证券债项评级(?P<dst>降为.*?下)",
    r"跟踪评级(?P<dst>(下调.*?别|下调.*?\)))",
    r"资产支持证券(?P<dst>.*?级)的?评级",
    r"资产支持证券获得.*?给予的(?P<dst>.*?级)",
    r"受益凭证评级为(?P<dst>.*?级)",
]


INVALID_RATE_NAME = PatternCollection(
    [
        r"^评级公司$",
        r"于任何日期.*?委托机构",
    ]
)
COMMON_INVALID_FLAG = PatternCollection(r"(日|期间|事件|等级|信用级别)$")
INVALID_ROOT_SYLLABUS_PATTERN = PatternCollection(r"定义")

COMPANY_MAP = {
    "中诚信": [
        "中诚信",
        "中诚信国际信用评级有限责任公司",
    ],
    "中诚信国际信用评级有限责任公司": [
        "中诚信",
        "中诚信国际信用评级有限责任公司",
    ],
    "中债资信": [
        "中债资信",
        "中债资信评估有限责任公司",
    ],
    "中债资信评估有限责任公司": [
        "中债资信",
        "中债资信评估有限责任公司",
    ],
}


class MonitorIndicatorForStandard(FakeModel):
    def __init__(self, options: dict, schema: SchemaItem, predictor):
        super(MonitorIndicatorForStandard, self).__init__(options, schema, predictor=predictor)

    def train(self, dataset, **kwargs):
        pass

    def predict_schema_answer(self, elements):
        answer_results = []
        sections = self.parse_sections()
        # 提取 评级公司
        rating_firms1_name, rating_firms2_name = self.get_company(sections, answer_results)
        # 提取 阈值_必备评级等级条款
        self.parser_answer_from_section(
            sections,
            answer_results,
            rating_firms1_name,
            rating_firms2_name,
            RATING_TERM_FLAG,
            "阈值_必备评级等级条款（评级1）",
            "阈值_必备评级等级条款（评级2）",
            RATING_TERM1,
            RATING_TERM2,
            deepcopy(RATING_TERM1_LIST),
            deepcopy(RATING_TERM2_LIST),
            invalid_flags=INVALID_RATING_TERM_FLAG,
        )

        # 提取 资产服务机构主体等级条款
        self.parser_answer_from_section(
            sections,
            answer_results,
            rating_firms1_name,
            rating_firms2_name,
            AGENCY_CLAUSE_FLAG,
            "阈值_资产服务机构主体等级条款（评级1）",
            "阈值_资产服务机构主体等级条款（评级2）",
            AGENCY_CLAUSE1,
            AGENCY_CLAUSE2,
            deepcopy(AGENCY_CLAUSE1_LIST),
            deepcopy(AGENCY_CLAUSE2_LIST),
            invalid_flags=INVALID_AGENCY_CLAUSE_FLAG,
        )

        # 提取 委托人/发起人主体等级条款
        self.parser_answer_from_section(
            sections,
            answer_results,
            rating_firms1_name,
            rating_firms2_name,
            ORIGINATOR_TERM_FLAG,
            "阈值_委托人/发起人主体等级条款（评级1）",
            "阈值_委托人/发起人主体等级条款（评级2）",
            ORIGINATOR_TERM1,
            ORIGINATOR_TERM2,
            deepcopy(ORIGINATOR_TERM1_LIST),
            deepcopy(ORIGINATOR_TERM2_LIST),
        )

        custodian_list2 = deepcopy(CUSTODIAN_TERM2_LIST_STANDARD)

        # 提取 资金保管机构主体等级条款
        self.parser_answer_from_section(
            sections,
            answer_results,
            rating_firms1_name,
            rating_firms2_name,
            CUSTODIAN_TERM_FLAG,
            "阈值_资金保管机构主体等级条款（评级1）",
            "阈值_资金保管机构主体等级条款（评级2）",
            CUSTODIAN_TERM1,
            CUSTODIAN_TERM2,
            deepcopy(CUSTODIAN_TERM1_LIST),
            custodian_list2,
        )
        # 提取 增信主体等级条款
        self.parser_answer_from_section(
            sections,
            answer_results,
            rating_firms1_name,
            rating_firms2_name,
            CREDIT_TERM_FLAG,
            "阈值_增信主体等级条款（评级1）",
            "阈值_增信主体等级条款（评级2）",
            CREDIT_TERM1,
            CREDIT_TERM2,
            deepcopy(CREDIT_TERM1_LIST),
            deepcopy(CREDIT_TERM2_LIST),
            invalid_flags=INVALID_CREDIT_TERM_FLAG,
        )
        product_term1_list = deepcopy(PRODUCT_TERM1_LIST)
        product_term1_list += deepcopy(PRODUCT_TERM1_STANDARD)
        # 提取 产品等级条款
        self.parser_answer_from_section(
            sections,
            answer_results,
            rating_firms1_name,
            rating_firms2_name,
            PRODUCT_TERM_FLAG,
            "阈值_产品等级条款（评级1）",
            "阈值_产品等级条款（评级2）",
            PRODUCT_TERM1,
            PRODUCT_TERM2,
            product_term1_list,
            deepcopy(PRODUCT_TERM2_LIST),
            invalid_flags=INVALID_PRODUCT_TERM_FLAG,
        )
        return answer_results

    def parser_answer_from_section(
        self,
        sections,
        answer_results,
        rating_firms1_name,
        rating_firms2_name,
        section_flag,
        column1,
        column2,
        column1_reg,
        column2_reg,
        column1_reg_list,
        column2_reg_list,
        invalid_flags=None,
    ):
        for firm1_reg in COMPANY_MAP.get(rating_firms1_name, [rating_firms1_name]):
            column1_reg_list.insert(0, column1_reg.format(firm1_reg))
        if rating_firms2_name:
            for firm2_reg in COMPANY_MAP.get(rating_firms2_name, [rating_firms2_name]):
                column2_reg_list.insert(0, column2_reg.format(firm2_reg))
        for flag, section in sections.items():
            if section_flag.nexts(flag):
                if not COMMON_INVALID_FLAG.nexts(flag):
                    continue
                # if not self.belong_valid_syllabus(section):
                #     continue
                for para in section:
                    if invalid_flags and invalid_flags.nexts(clean_txt(para["text"])):
                        continue
                    matchers = PatternCollection(column1_reg_list).finditer(clean_txt(para["text"]))
                    self.add_answer_from_matcher(matchers, answer_results, para, column1)
                    matchers = PatternCollection(column2_reg_list).finditer(clean_txt(para["text"]))
                    self.add_answer_from_matcher(matchers, answer_results, para, column2)

    def add_answer_from_matcher(self, matchers, answer_results, para, column):
        for matcher in matchers:
            if matcher:
                dst_chars = self.get_dst_chars_from_matcher(matcher, para)
                if dst_chars:
                    answer_results.append(self.create_result([CharResult(para, dst_chars)], column=column))
                    break

    def get_company(self, sections, answer_results):
        rating_firms1_name, rating_firms2_name = "", ""
        for flag, section in sections.items():
            if not RATING_FIRMS_FLAG.nexts(flag):
                continue
            for para in section:
                matcher = RATING_FIRMS1.nexts(clean_txt(para["text"]))
                if matcher:
                    dst_chars = self.get_dst_chars_from_matcher(matcher, para)
                    if dst_chars:
                        rating_firms1_name = "".join([char["text"] for char in dst_chars])
                        if INVALID_RATE_NAME.nexts(rating_firms1_name):
                            continue
                        answer_results.append(
                            self.create_result([CharResult(para, dst_chars)], column="监测指标定义_评级公司1")
                        )
                matcher = RATING_FIRMS2.nexts(clean_txt(para["text"]))
                if matcher:
                    dst_chars = self.get_dst_chars_from_matcher(matcher, para)
                    if dst_chars:
                        rating_firms2_name = "".join([char["text"] for char in dst_chars])
                        answer_results.append(
                            self.create_result([CharResult(para, dst_chars)], column="监测指标定义_评级公司2")
                        )
                if rating_firms1_name and rating_firms2_name:
                    break
            if rating_firms1_name and rating_firms2_name:
                break

        return rating_firms1_name, rating_firms2_name

    def belong_valid_syllabus(self, sections):
        if not sections:
            return False
        first_para = sections[0]
        cur_syllabus = self.pdfinsight_syllabus.syllabus_dict[first_para["syllabus"]]
        all_syllabus = self.pdfinsight_syllabus.full_syll_path(cur_syllabus)
        for syllabus in all_syllabus:
            if INVALID_ROOT_SYLLABUS_PATTERN.nexts(clean_txt(syllabus["title"])):
                return True
        return False
