"""
中信-募集书抽取
"""

from remarkable.common.diff.mixins import P_SERIAL
from remarkable.predictor.eltype import ElementType

P_SUB_TITLE = r"(?:(?:一般|专[业用])术语|常用词语?|释义)[:：]?"

P_ISSUER_NAME = r"本公司|发行人"
P_LEAD_UNDERWRITER = r"主承销商"
P_MAIN_LEAD_UNDERWRITER = r"牵头主承销商"
P_CO_LEAD_UNDERWRITER = r"联席主承销商"
P_CURRENT_BOND = r"本次(?:公司)?债券"
P_PERIOD_BOND = r"本期(?:公司)?债券"
P_CURRENT_PUBLISH = r"本次(?:公开)?发行"
P_PERIOD_PUBLISH = r"本期(?:公开)?发行"
P_RATING_AGENCY = r"(?:资信)?评级机构"
P_INVESTOR = r"(?:公司)?(?:债券)?(?:投资|持有)[者人]"
P_BOOKKEEPER = r"簿记管理人"
P_TRUSTEE = r"(?:公司)?(?:债券)?受托管理人"
P_LAWYER = r"(?:发行人)?律师(?:事务所)?"
P_ACCOUNTANT = r"(?:发行人)?审计机构|会计师(?:事务所)?"
P_PROSPECTUS = r"募集说明书"
P_PROSPECTUS_SUMMARY = r"募集说明书摘要"
P_UNIT = r"元|万元|亿元"

P_RATING_AGENCY_SUFFIX = r"(?:信用)?(?:评估|评级)(?:股份)?(?:有限)?(?:责任)?公司$"
P_ACCOUNTANT_SUFFIX = r"(?<!^)(?<!发行人)会计师事务所(?:[（(](?:(?:特殊)?(?:普通)?(?:合伙|合作伙伴))[)）])?$"
P_LAWYER_SUFFIX = r"(?<!^)(?<!发行人)律师事务所(?:[（(](?:(?:特殊)?(?:普通)?(?:合伙|合作伙伴))[)）])?$"

P_LEGAL_HOLIDAYS = r"^(?:法定节假日[/.,、或]休息日|法定节假日|休息日)$"
P_WEEKDAYS = r"^(?:交易日[/.,、或]工作日|工作日[/.,、或]交易日|工作日)$"
P_TRADING_DAY = r"(?:交易日[/.,、或]工作日|工作日[/.,、或]交易日|交易日)$"


P_DETAIL_NAME = "|".join(
    rf"(?:^{P_SERIAL.pattern}|^)\s*{item}\s*(?:[:：]|$)"
    for item in [
        ".*选择权(?:条款)?",
        "赎回选择权",
        "付息日",
        "信用级别及资信评级机构",
        "债券利率及确定方式",
        "债券名称",
        "债券形式",
        "债券期限",
        "兑付日",
        "兑付登记日",
        "利息登记日",
        "到期日",
        "募集资金专项账户",
        "募集资金用途",
        "发行主体",
        "发行人赎回选择权",
        "发行方式和发行对象",
        "发行规模",
        "向公司股东配售安排",
        "回售申报",
        "承销方式",
        "投资者回售选择权",
        "担保方式",
        "拟上市交易场所",
        "支付金额",
        "票面金额及发行价格",
        "税务提示",
        "联席主承销商",
        "调整票面利率选择权",
        "起息日",
        "还本付息方式",
        "配售规则",
        "上市交易流通场所",
        "发行主体",
        "发行公告日",
        "还本付息方式",
        "递延支付利息权",
        "债券利率或其确定方式",
        "强制付息事件",
        "起息日",
        "债券形式",
        "利息登记日",
        "利息递延下的限制事项",
        "还本付息方式及支付金额",
        "付息日",
        "偿付顺序",
        "发行方式与发行对象",
        "发行人赎回选择权",
        "本金兑付日",
        "配售规则",
        "会计处理",
        "担保情况",
        "向公司股东配售安排",
        "付息方式",
        "募集资金专项账户",
        "发行首日及起息日",
        "信用级别及资信评级机构",
        "起息日",
        "利息登记日",
        "付息债权登记日",
        "债券受托管理人",
        "付息日",
        "付息日",
        "承销方式",
        "计息期限",
        "发行主体",
        "债券名称",
        "发行首日",
        "拟上市交易场所",
        "本金兑付日",
        "兑付登记日",
        "付息、兑付方式",
        "募集资金用途",
        "兑付日",
        "信用级别及资信评级机构",
        "新质押式回购安排",
        "本息支付方式",
        "牵头主承销商、簿记管理人",
        "税务提示",
        "信用级别及资信评级机构",
        "联席主承销商",
        "牵头主承销商、债券受托管理人",
        "债券受托管理人",
        "联席主承销商",
        "发行方式及发行对象",
        "承销方式",
        "配售规则",
        "拟上市交易场所",
        "承销方式",
        "募集资金及偿债资金专项账户",
        "拟上市交易场所",
        "募集资金用途",
        "债券名称",
        "债券期限及品种",
        "发行期限",
        "发行规模",
        "新质押式回购",
        "质押式回购安排",
        "募集资金用途",
        "税务提示",
        "募集资金专项账户",
        "税务提示",
        "发行规模",
        "债券票面金额及发行价格",
        "发行规模",
        "债券票面金额及发行价格",
        "债券期限及品种",
        "债券票面金额和发行价格",
        "债券期限",
        "债券利率及其确定方式",
        "担保方式",
        "发行人调整票面利率选择权",
        "债券形式",
        "发行方式、发行对象及配售安排",
        "投资者回售选择权",
        "债券利率及其确定方式",
        "配售规则",
        "回售登记期",
        "债券形式",
        "发行人续期选择权",
        "担保情况",
        "《递延支付利息公告》内容应包括但不限于",
        "上市交易场所",
        "上市交易安排",
        "上市和交易流通安排",
        "上市场所",
        "上市安排",
        "专项偿债账户",
        "中文名称",
        "主承销商",
        "主承销商、债券受托管理人",
        "主承销商、受托管理人、簿记管理人",
        "主承销商、簿记管理人",
        "主承销商、簿记管理人、债券受托管理人",
        "主承销团成员",
        "交易场所",
        "付息、兑付方式",
        "付息债券登记日",
        "付息债权登记日",
        "付息方式",
        "付息日",
        "付息日期",
        "会计处理",
        "传真",
        "信用安排",
        "信用等级及资信评级机构",
        "信用级别",
        "信用级别及信用评级机构",
        "信用级别及资信评级机构",
        "信用评级",
        "信用评级机构及信用评级结果",
        "债券全称",
        "债券利率及其定价流程",
        "债券利率及其确定方式",
        "债券利率及其确定方式、定价流程",
        "债券利率及确定方式",
        "债券利率或其确定方式",
        "债券利率或其确定方式、定价流程",
        "债券利率确定方式",
        "债券受托管理人",
        "债券名称",
        "债券品种",
        "债券品种及期限",
        "债券品种和期限",
        "债券形式",
        "债券形式及托管方式",
        "债券性质",
        "债券担保",
        "债券期限",
        "债券期限及利率",
        "债券期限及品种",
        "债券期限和品种",
        "债券期限：本期债券分为两个品种，其中",
        "债券票面金额",
        "债券票面金额及发行价格",
        "债券票面金额和发行价格",
        "债券简称及代码",
        "债券简称和代码：本期债券简称为",
        "债券规模",
        "债券认购单位",
        "债券转让",
        "债券违约后争议解决机制",
        "债券面值和发行价格",
        "债权代理人",
        "偿付顺序",
        "兑付价格",
        "兑付债权登记日",
        "兑付兑息登记日",
        "兑付方式",
        "兑付日",
        "兑付日期",
        "兑付日：本期债券的兑付日为",
        "兑付登记日",
        "兑付金额",
        "公司债券上市或转让安排",
        "公司名称",
        "公司类型",
        "公司网址",
        "利息登记日",
        "利息递延下的限制事项",
        "利率",
        "到期日",
        "办公地址",
        "募集资金与专项偿债账户监管人",
        "募集资金专户",
        "募集资金专项账户",
        "募集资金使用专项账户",
        "募集资金及偿债资金专项账户",
        "募集资金用途",
        "发行主体",
        "发行人",
        "发行人全称",
        "发行人续期选择权",
        "发行人调整票面利率公告日期",
        "发行人调整票面利率选择权",
        "发行人赎回权",
        "发行人赎回选择权",
        "发行价格",
        "发行公告刊登日期",
        "发行公告刊登的日期",
        "发行公告日",
        "发行对象",
        "发行对象及向公司股东配售安排",
        "发行对象及向公司股东配售的安排",
        "发行总额",
        "发行方式",
        "发行方式、发行对象",
        "发行方式、发行对象与配售规则",
        "发行方式、发行对象及向公司股东配售的安排",
        "发行方式与发行对象",
        "发行方式及发行对象",
        "发行方式和发行对象",
        "发行方式和对象",
        "发行日",
        "发行日和起息日",
        "发行日期",
        "发行期限",
        "发行范围和对象",
        "发行规模",
        "发行规模及分期发行安排",
        "发行规模及发行安排",
        "发行规模及发行方式",
        "发行费用概算",
        "发行金额",
        "发行首日",
        "发行首日、网下认购起始日",
        "发行首日与起息日",
        "发行首日及起息日",
        "受托管理人",
        "向公司股东配售",
        "向公司股东配售安排",
        "向公司股东配售的安排",
        "向发行人股东配售的安排",
        "品种一",
        "品种二",
        "品种间回拨选择权",
        "回售提示性公告日期",
        "回售申报",
        "回售申报期",
        "回售登记期",
        "回售选择权",
        "回售部分债券付款方式",
        "回售部分债券回售价格",
        "基准利率的确定方式",
        "增信措施",
        "大额产品支付号",
        "大额支付号",
        "大额支付系统号",
        "实缴资本",
        "开户行",
        "开户银行",
        "弹性配售选择权",
        "强制付息事件",
        "强制付息及递延支付利息的限制",
        "强制配售触发条款",
        "成立日期",
        "户名",
        "托管方式",
        "承销团成员",
        "承销方式",
        "投资者回售登记期",
        "投资者回售选择权",
        "担保人及担保方式",
        "担保情况",
        "担保情况及其他增信措施",
        "担保方式",
        "拟上市交易场所",
        "拟上市地",
        "拟上市场所",
        "支付方式",
        "支付金额",
        "收款账号",
        "新质押式回购",
        "新质押式回购安排",
        "本息兑付方式",
        "本息支付方式",
        "本期债券上市安排",
        "本期债券利息递延下的限制事项",
        "本期债券发行总额",
        "本期债券受托管理人",
        "本期债券名称",
        "本期债券品种和期限",
        "本期债券牵头主承销商、簿记管理人",
        "本期债券的强制付息事件",
        "本期债券联席主承销商",
        "本期发行规模",
        "本金兑付日",
        "本金兑付日期",
        "本金支付日",
        "本金支付日（兑付日）",
        "次级条款",
        "法定代表人",
        "注册地址",
        "注册文件",
        "注册资本",
        "注册资本2",
        "注册通知文号",
        "流动性安排",
        "清偿顺序",
        "牵头主承销商",
        "牵头主承销商、债券受托管理人、簿记管理人",
        "牵头主承销商、受托管理人、簿记管理人",
        "牵头主承销商、簿记管理人",
        "牵头主承销商、簿记管理人、债券受托管理人",
        "牵头主承销商、簿记管理人及债券受托管理人",
        "牵头主承销商及簿记管理人",
        "独家主承销商、债券受托管理人",
        "登记、托管机构",
        "登记托管",
        "监管银行",
        "票面利率公式为",
        "票面利率及其确定方式",
        "票面利率或其确定方式",
        "票面利率调整机制",
        "票面利率重置日",
        "票面金额",
        "票面金额及发行价格",
        "票面金额和发行价格",
        "税务处理",
        "税务提示",
        "簿记建档日",
        "簿记日",
        "簿记管理人",
        "经营范围",
        "统一社会信用代码",
        "续期选择权",
        "缴款日",
        "网下发行期",
        "网下发行期限",
        "网下簿记建档日",
        "网下配售原则",
        "联席主承销商",
        "联席主承销商、债券受托管理人",
        "联系人",
        "联系电话",
        "英文名称",
        "计息年度天数",
        "计息期限",
        "调整票面利率选择权",
        "账号",
        "账户",
        "账户一",
        "账户一：账户名称",
        "账户三：账户名称",
        "账户二",
        "账户二：账户名称",
        "账户及资金监管人",
        "账户号码",
        "账户名",
        "账户名称",
        "账户户名",
        "质押式回购",
        "质押式回购安排",
        "资信评级机构及信用级别",
        "赎回方式",
        "起息日",
        "起息日期",
        "还本付息方式",
        "还本付息方式及支付金额",
        "还本付息期限和方式",
        "还本付息的期限和方式",
        "递延支付利息权",
        "递延支付利息条款",
        "递延支付利息选择权",
        "邮政编码",
        "配售原则",
        "配售方式",
        "配售规则",
        "银行大额支付系统号",
        "银行账号",
        "银行账户",
        "预计发行期限",
        "首个票面利率重置日",
    ]
)

P_BASE_TITLE = [
    r"__regex__发行[概况条款]{2}__regex__(?:本[期次]|债券).*[基本主要]{2}条款",
    r"__regex__发行[概况条款]{2}__regex__本[次期]发行的基本情况__regex__本[期次].*[基本主要]{2}条款",
]


def render_pattern(key_pattern):
    return f"(?:^|[./、，,或])(?:{key_pattern})(?:$|[./、，,或])"


def render_model(pattern):
    pattern = render_pattern(pattern)
    return {
        "name": "interpretation_table_row",
        "multi": False,
        "简称": {
            "feature_white_list": [rf"origin__regex__{pattern}__regex__{P_SUB_TITLE}", rf"origin__regex__{pattern}"],
            "feature_from": "self",
        },
        "全称": {
            "feature_from": "left_cells",
            "feature_white_list": [
                rf"origin__regex__{pattern}__regex__{P_SUB_TITLE}__regex__指",
                rf"origin__regex__{pattern}__regex__指",
            ],
        },
    }


def render_suffix_model(pattern):
    return {
        "name": "interpretation_table_row",
        "multi": False,
        "简称": {
            "feature_white_list": [
                rf"origin__regex__{pattern}__regex__{P_SUB_TITLE}__regex__指",
                rf"origin__regex__{pattern}__regex__指",
            ],
            "feature_from": "right_cells",
        },
        "全称": {
            "feature_from": "self",
            "feature_white_list": [
                rf"origin__regex__{pattern}__regex__{P_SUB_TITLE}",
                rf"origin__regex__{pattern}",
            ],
        },
    }


predictor_options = [
    {
        "path": ["重大事项提示", "信用风险评估"],
        "models": [
            {
                "name": "paragraph_selector",
                "top_anchor_regs": [r"重大事项提示"],
                "bottom_anchor_regs": [
                    r"^(?:目\s*录|释\s*义)$",
                ],
                "include_top_anchor": False,
                "include_bottom_anchor": False,
                "use_top_crude_neighbor": False,
                "paragraph_model": "partial_text",
                "para_config": {
                    "regs": [
                        r"^[0-9一二三四五六七八九十]*[、.．\s]?"
                        r"(?P<dst>.*经.{,15}(?:信用)?评[级估](?:投资服务)?(?:股份)?(?:有限)?(?:责任)?公司(?:[(（].*?[)）])?综合评定[:：,，]"
                        r"(?:本公司|发行人)的?主体信用等级为.{,8}级.*)$",
                        r"^[0-9一二三四五六七八九十]*[、.．\s]?"
                        r"(?P<dst>.*(?:评级展望|(?:本[期次]债券|(?:发行人?|公司))的?主体(?:长期)?(?:信用)?(?:等级|评级|级别)(?:结果)?)[为是].*)$",
                        r"^[0-9一二三四五六七八九十]*[、.．\s]?(?P<dst>.*为(?:公司|发行人)本次发行出具了?《.*?信用评级报告》.*)$",
                        r"^[0-9一二三四五六七八九十]*[、.．\s]?(?P<dst>.*[、.，,]信用等级为.{,6}级.发行规模不超过.*)$",
                        r"^[0-9一二三四五六七八九十]*[、.．\s]?"
                        r"(?P<dst>.*本[期次][^，,。]*?(?:债券|债项)的?(?:主体)?(?:信用)?(?:等级|评级|级别)[为是].*)$",
                        r"^[0-9一二三四五六七八九十]*[、.．\s]?(?P<dst>.*已经[^,，。]*公司评级.*出具了[^,，。]*信用评级报告.*)$",
                        r"^[0-9一二三四五六七八九十]*[、.．\s]?(?P<dst>.*本[期次]债券的?信用质量[很为是].*)$",
                        r"^[0-9一二三四五六七八九十]*[、.．\s]?"
                        r"(?P<dst>.*给予本[期次][^，,。]*?(?:债券|债项)(?:主体)?(?:信用)?(?:等级|评级|级别)[为是]?.*)$",
                        r"^[0-9一二三四五六七八九十]*[、.．\s]?(?P<dst>.*本[次期]债券.*信用(?:等级|评级|级别)[为是]?为.*)$",
                    ]
                },
            },
        ],
    },
    {
        "path": ["发行人基本情况", "发行人"],
        "models": [
            {
                "name": "syllabus_based",
                # 'use_crude_answer': True,
                "neglect_patterns": [r"本次发行概况"],
                "syllabus_level": 2,
                "min_level": 2,
                "ignore_syllabus_children": True,
                "max_syllabus_range": 150,
                "inject_syllabus_features": [
                    r"__regex__发行人基本情况__regex__^[0-9一二三四五六七八九十]*[、.．\s]*(?:发行人概(?:况|述)|(?:发行人|公司)?基本(?:情况|信息))$"
                ],
                "multi_elements": False,
                "paragraph_model": "para_match",
                "para_config": {
                    "paragraph_pattern": r"(?:(?:(?:发行人|公司|企业|注册)(?:法定)?(?:中文)?|中文|法定)?(?:名称|全称)"
                    r"|^(?:名称|全称))"
                    r"[:：]"
                    r"(?P<content>.*公司)",
                    "content_pattern": r"(?:(?:(?:发行人|公司|企业|注册)(?:法定)?(?:中文)?|中文|法定)?(?:名称|全称)"
                    r"|^(?:名称|全称))"
                    r"[:：]"
                    r"(?P<content>.*公司)",
                },
                "table_model": "table_kv",
                "table_config": {
                    "feature_white_list": [
                        r"__regex__(?:(?:(?:发行人|公司|企业|注册)(?:法定)?(?:中文)?|中文|法定)(?:名称|全称)|^(?:名称|全称))[:：]?"
                    ],
                    "regs": [r"(?P<dst>.*公司)"],
                    "only_matched_value": True,
                },
            },
        ],
    },
    {
        "path": ["释义", "募集说明书"],
        "models": [render_model(P_PROSPECTUS)],
    },
    {
        "path": ["释义", "募集说明书摘要"],
        "models": [render_model(P_PROSPECTUS_SUMMARY)],
    },
    {
        "path": ["释义", "中国证监会、证监会"],
        "models": [
            {
                "name": "interpretation_table_row",
                "multi": False,
                "简称": {
                    "feature_from": "self",
                    "feature_black_list": [r"__regex__^((?!证监会).)*$"],
                },
                "全称": {
                    "feature_from": "left_cells",
                    "feature_black_list": [r"__regex__^((?!证监会).)*$__regex__指"],
                },
            },
        ],
    },
    {
        "path": ["释义", "上交所"],
        "models": [
            {
                "name": "interpretation_table_row",
                "multi": False,
                "简称": {
                    "feature_from": "self",
                },
                "全称": {
                    "feature_from": "left_cells",
                },
            },
        ],
    },
    {
        "path": ["释义", "深交所"],
        "models": [
            {
                "name": "interpretation_table_row",
                "multi": False,
                "简称": {
                    "feature_from": "self",
                },
                "全称": {
                    "feature_from": "left_cells",
                },
            },
        ],
    },
    {
        "path": ["释义", "投资人、持有人"],
        "models": [render_model(P_INVESTOR)],
    },
    {
        "path": ["释义", "牵头主承销商"],
        "models": [render_model(P_MAIN_LEAD_UNDERWRITER)],
    },
    {
        "path": ["释义", "簿记管理人"],
        "models": [render_model(P_BOOKKEEPER)],
    },
    {
        "path": ["释义", "债券受托管理人"],
        "models": [render_model(P_TRUSTEE)],
    },
    {
        "path": ["释义", "联席主承销商"],
        "models": [render_model(P_CO_LEAD_UNDERWRITER)],
    },
    {
        "path": ["释义", "主承销商"],
        "models": [render_model(P_LEAD_UNDERWRITER)],
    },
    {
        "path": ["释义", "发行人律师、律师"],
        "models": [render_model(P_LAWYER), render_suffix_model(P_LAWYER_SUFFIX)],
    },
    {
        "path": ["释义", "审计机构、会计师"],
        "models": [render_model(P_ACCOUNTANT), render_suffix_model(P_ACCOUNTANT_SUFFIX)],
    },
    {
        "path": ["释义", "资信评级机构、评级机构"],
        "models": [
            render_model(P_RATING_AGENCY),
            render_suffix_model(P_RATING_AGENCY_SUFFIX),
        ],
    },
    {
        "path": ["释义", "网下询价日（T-1日）"],
        "models": [
            {
                "name": "interpretation_table_row",
                "multi": False,
                "简称": {
                    "feature_from": "self",
                },
                "全称": {
                    "feature_from": "left_cells",
                },
            },
        ],
    },
    {
        "path": ["释义", "发行首日、网下认购起始日（T日）"],
        "models": [
            {
                "name": "interpretation_table_row",
                "multi": False,
                "简称": {
                    "feature_from": "self",
                },
                "全称": {
                    "feature_from": "left_cells",
                },
            },
        ],
    },
    {
        "path": ["释义", "交易日"],
        "models": [
            {
                "name": "interpretation_table_row",
                "multi": False,
                "简称": {
                    "feature_white_list": [
                        rf"origin__regex__{P_TRADING_DAY}__regex__{P_SUB_TITLE}",
                        rf"origin__regex__{P_TRADING_DAY}",
                    ],
                    "feature_from": "self",
                },
                "全称": {
                    "feature_from": "left_cells",
                    "feature_white_list": [
                        rf"origin__regex__{P_TRADING_DAY}__regex__{P_SUB_TITLE}__regex__指",
                        rf"origin__regex__{P_TRADING_DAY}__regex__指",
                    ],
                },
            }
        ],
    },
    {
        "path": ["释义", "工作日"],
        "models": [
            {
                "name": "interpretation_table_row",
                "multi": False,
                "简称": {
                    "feature_white_list": [
                        rf"origin__regex__{P_WEEKDAYS}__regex__{P_SUB_TITLE}",
                        rf"origin__regex__{P_WEEKDAYS}",
                    ],
                    "feature_from": "self",
                },
                "全称": {
                    "feature_from": "left_cells",
                    "feature_white_list": [
                        rf"origin__regex__{P_WEEKDAYS}__regex__{P_SUB_TITLE}__regex__指",
                        rf"origin__regex__{P_WEEKDAYS}__regex__指",
                    ],
                },
            }
        ],
    },
    {
        "path": ["释义", "法定节假日或休息日"],
        "models": [
            {
                "name": "interpretation_table_row",
                "multi": False,
                "简称": {
                    "feature_white_list": [
                        rf"origin__regex__{P_LEGAL_HOLIDAYS}__regex__{P_SUB_TITLE}",
                        rf"origin__regex__{P_LEGAL_HOLIDAYS}",
                    ],
                    "feature_from": "self",
                },
                "全称": {
                    "feature_from": "left_cells",
                    "feature_white_list": [
                        rf"origin__regex__{P_LEGAL_HOLIDAYS}__regex__{P_SUB_TITLE}__regex__指",
                        rf"origin__regex__{P_LEGAL_HOLIDAYS}__regex__指",
                    ],
                },
            }
        ],
    },
    {
        "path": ["释义", "元、万元、亿元"],
        "models": [render_model(P_UNIT)],
    },
    {
        "path": ["释义", "余额包销"],
        "models": [
            {
                "name": "interpretation_table_row",
                "multi": False,
                "简称": {
                    "feature_from": "self",
                },
                "全称": {
                    "feature_from": "left_cells",
                },
            },
        ],
    },
    {
        "path": ["释义", "管理办法"],
        "models": [
            {
                "name": "interpretation_table_row",
                "multi": False,
                "简称": {
                    "feature_from": "self",
                },
                "全称": {
                    "feature_from": "left_cells",
                },
            },
        ],
    },
    {
        "path": ["释义", "薄记建档"],
        "models": [
            {
                "name": "interpretation_table_row",
                "multi": False,
                "简称": {
                    "feature_from": "self",
                },
                "全称": {
                    "feature_from": "left_cells",
                },
            },
        ],
    },
    {
        "path": ["释义", "《网下利率询价及申购申请表》"],
        "models": [
            {
                "name": "interpretation_table_row",
                "multi": False,
                "简称": {
                    "feature_from": "self",
                },
                "全称": {
                    "feature_from": "left_cells",
                },
            },
        ],
    },
    {
        "path": ["释义", "《配售缴款通知书》"],
        "models": [
            {
                "name": "interpretation_table_row",
                "multi": False,
                "简称": {
                    "feature_from": "self",
                },
                "全称": {
                    "feature_from": "left_cells",
                },
            },
        ],
    },
    {
        "path": ["释义", "《适当性管理办法》"],
        "models": [
            {
                "name": "interpretation_table_row",
                "multi": False,
                "简称": {
                    "feature_from": "self",
                },
                "全称": {
                    "feature_from": "left_cells",
                },
            },
        ],
    },
    {
        "path": ["释义", "合规申购"],
        "models": [
            {
                "name": "interpretation_table_row",
                "multi": False,
                "简称": {
                    "feature_from": "self",
                },
                "全称": {
                    "feature_from": "left_cells",
                },
            },
        ],
    },
    {
        "path": ["释义", "有效申购"],
        "models": [
            {
                "name": "interpretation_table_row",
                "multi": False,
                "简称": {
                    "feature_from": "self",
                },
                "全称": {
                    "feature_from": "left_cells",
                },
            },
        ],
    },
    {
        "path": ["释义", "有效申购金额"],
        "models": [
            {
                "name": "interpretation_table_row",
                "multi": False,
                "简称": {
                    "feature_from": "self",
                },
                "全称": {
                    "feature_from": "left_cells",
                },
            },
        ],
    },
    {
        "path": ["释义", "上市规则"],
        "models": [
            {
                "name": "interpretation_table_row",
                "multi": False,
                "简称": {
                    "feature_from": "self",
                },
                "全称": {
                    "feature_from": "left_cells",
                },
            },
        ],
    },
    {
        "path": ["释义", "报告期"],
        "models": [
            {
                "name": "interpretation_table_row",
                "multi": False,
                "简称": {
                    "feature_from": "self",
                },
                "全称": {
                    "feature_from": "left_cells",
                },
            },
        ],
    },
    {
        "path": ["释义", "最近三年、近三年"],
        "models": [
            {
                "name": "interpretation_table_row",
                "multi": False,
                "简称": {
                    "feature_from": "self",
                },
                "全称": {
                    "feature_from": "left_cells",
                },
            },
        ],
    },
    {
        "path": ["释义", "最近三年及一期、近三年及一期"],
        "models": [
            {
                "name": "interpretation_table_row",
                "multi": False,
                "简称": {
                    "feature_from": "self",
                },
                "全称": {
                    "feature_from": "left_cells",
                },
            },
        ],
    },
    {
        "path": ["释义", "最近一期"],
        "models": [
            {
                "name": "interpretation_table_row",
                "multi": False,
                "简称": {
                    "feature_from": "self",
                },
                "全称": {
                    "feature_from": "left_cells",
                },
            },
        ],
    },
    {
        "path": ["释义", "发行人、公司"],
        "models": [render_model(P_ISSUER_NAME)],
    },
    {
        "path": ["释义", "本期债券"],
        "models": [render_model(P_PERIOD_BOND)],
    },
    {
        "path": ["释义", "本期发行"],
        "models": [render_model(P_PERIOD_PUBLISH)],
    },
    {
        "path": ["释义", "本次债券"],
        "models": [render_model(P_CURRENT_BOND)],
    },
    {
        "path": ["释义", "本次发行"],
        "models": [render_model(P_CURRENT_PUBLISH)],
    },
    {
        # NOTE: 如何区分这些XXX公司的类型: 公司/发行人/承销商...?
        # https://mm.paodingai.com/cheftin/pl/p87owj8mzir8xrone94ibtpgiw
        "path": ["释义", "公司名"],
        "sub_primary_key": ["简称", "全称"],
        "models": [
            {
                "name": "interpretation_table_row",
                "neglect_patterns": [
                    "发行(人|主体)$",
                    "^发行(人|主体)",
                    "管理人$",
                    "^兑付方式$",
                    "^付息$",
                    "^债券受托管理人机构信息$",
                    "^债券简称$",
                    "^付息日$",
                    "^计息方式$",
                    "^本期发行规模$",
                    "^兑付日$",
                    "^债券全称$",
                    "^债券期限$",
                    "^担保情况$",
                    "^簿记管理人机构信息$",
                    "承销商$",
                    "证评$",
                    "^债券登记机构$",
                    "香港联交所$",
                    "债券登记机构$",
                    "登记机构$",
                    "董事会$",
                    "中国证监会$",
                    "证监会$",
                    "上交所$",
                    "深交所$",
                    "监事会$",
                    "股东大会$",
                    "发行人律师$",
                    "资信评级机构$",
                    "评级机构$",
                    "公司董事会$",
                    "发行人律师$",
                    "审计机构$",
                    "会计师事务所$",
                    "人民银行$",
                    "财政部$",
                    "住建部$",
                    "中国银保监会$",
                    "市国资委$",
                    "实际控制人$",
                    "国土资源部$",
                    "国家发改委$",
                    "审计署$",
                    "监察部$",
                    "下属子公司$",
                    "发改委$",
                    "承销团$",
                    "财务顾问$",
                    "国投财务$",
                    "监管银行$",
                    "账户监管人$",
                    "中证协$",
                    "国家统计局$",
                    "商务部$",
                    "农业部$",
                    "国家工商总局$",
                    "上市交易场所$",
                    "市政府$",
                ],
                "简称": {
                    # 'feature_black_list': [r'__regex__指__regex__'],
                    "feature_white_list": [r"__regex__指__regex__(公司|研究院|学院)$"],
                    "feature_from": "right_cells",
                },
                "全称": {
                    "feature_from": "self",
                    # 'feature_black_list': [r'__regex__摘要$__regex__指'],
                    "feature_white_list": [r"__regex__(公司|研究院|学院)$"],
                },
            },
        ],
    },
    {
        "path": ["发行概况-发行人基本情况", "发行人"],
        "models": [
            {
                "name": "syllabus_based",
                "syllabus_level": 2,
                "min_level": 2,
                "inject_syllabus_features": [r"__regex__发行人(?:基本)?情况__regex__公司基本信息"],
                "multi_elements": False,
                "paragraph_model": "para_match",
                "para_config": {
                    "paragraph_pattern": r"(公司|注册|中文|发行人)名称[:：](?P<content>.*公司)",
                    "content_pattern": r"(公司|注册|中文|发行人)名称[:：](?P<content>.*公司)",
                },
                "table_model": "table_kv",
                "table_config": {
                    "regs": [r"(?P<dst>.*公司)"],
                    "only_matched_value": True,
                },
            },
        ],
    },
    {
        "path": ["发行概况-核准情况及核准规模"],
        "models": [
            {
                "name": "partial_text",
            },
        ],
    },
    {
        "path": ["发行概况-核准情况及核准规模", "本次发行规模"],
        "models": [
            {
                "name": "partial_text",
                "regs": [
                    r"本次债券.*?发行(?:总?规模|总额)[为余额:：]*不超过(人民币|美元)?\s?(?P<dst>[\d.,]+)",
                    r"(?:公司|发行人)(?:获准)?面向合格投资者公开发行(?:面值)?(?:总额|总?规模)?不超过(人民币|美元)?\s?(?P<dst>[\d.,]+).*的公司债券",
                    r"本次非公开发行短期公司债券总额不超过(人民币|美元)?\s?(?P<dst>[\d.,]+)",
                    r"(?:证监许可|上证函|深证函|出具的.*?公开发行.*?债券注册).*?注册规模(?:为|是)(?:不超过)?(人民币|美元)?\s*(?P<dst>[\d.,]+)",
                ],
                "model_alternative": True,
            },
        ],
    },
    {
        "path": ["发行概况-核准情况及核准规模", "证监许可号"],
        "models": [
            {
                "name": "securities_license_key",
                "neglect_syllabus_regs": [r"前次"],
                "regs": [r"(?P<dst>(证监许可|上证函|深证函).*号)"],
            },
        ],
    },
    {
        "path": ["发行概况-核准情况及核准规模", "批文日期"],
        "models": [
            {
                "name": "syllabus_based",
                "target_element": ElementType.PARAGRAPH.value,
                "multi_elements": False,
                "paragraph_model": "partial_text",
                "ignore_syllabus_children": True,
                "max_syllabus_range": 100,
                "inject_syllabus_features": [
                    r"__regex__发行概况__regex__发行条款__regex__(?:核准情况以?及核准规模|中国证监会注册情况|核准情况|注册文件)$",
                    r"__regex__发行条款__regex__(?:核准情况以?及核准规模|中国证监会注册情况|核准情况|注册文件)$",
                    r"__regex__发行(概况|条款)__regex__本(期|次)(债券)?(?:发行的基本情况|(?:主要|基本)(?:发行)?条款)"
                    r"__regex__(?:核准情况以?及核准规模|中国证监会注册情况|(核|批)准情况|注册文件)$",
                    r"__regex__发行(概况|条款)__regex__本(期|次)(债券)?的?(?:发行的基本情况|(?:主要|基本)(?:发行)?条款)",
                ],
                "para_config": {
                    "regs": [
                        r"(?P<dst>\s*\d{,4}\s*年\s*\d{,2}\s*月\s*\d{,2}\s*日)[,，]?(?:发行人|公司)?(?:获得?|收到|经|通过)"
                        r"(?:上交所|上海证券交易所|深交所|深圳证券交易所|中国证券监督管理委员)"
                        r"(?:出具的?|签发的|同意|无异议|核准|获准)[^,.。;]*(?:证监许可|上证函|深证函)",
                        r"于(?P<dst>\s*\d{,4}\s*年\s*\d{,2}\s*月\s*\d{,2}\s*日)(?:发行人|公司)?"
                        r"(?:领取的?|获得?|签发的?|印发的)[^,.。;]*(?:证监许可|上证函|深证函)",
                        r"(?P<dst>\s*\d{,4}\s*年\s*\d{,2}\s*月\s*\d{,2}\s*日)[,，]"
                        r"(?:发行人|公司)?获得?[^,.。;]*(?:签发的|同意|出具的)[^,.。;]*(?:证监许可|上证函|深证函)",
                        r"(?P<dst>\s*\d{,4}\s*年\s*\d{,2}\s*月\s*\d{,2}\s*日)[,，]?"
                        r"(?:上交所|深交所)出具了[^,.。;]*(?:签发的|同意|无异议|出具的)[^,.。;]*(?:证监许可|上证函|深证函)",
                    ],
                    "model_alternative": True,
                },
            },
        ],
    },
    {
        "path": ["发行概况-核准情况及核准规模", "是否分期发行"],
        "models": [
            {
                "name": "partial_text",
            },
        ],
    },
    {
        "path": ["发行概况-基本条款"],
        "models": [
            {
                "name": "partial_text",
            },
        ],
    },
    {
        "path": ["发行概况-基本条款", "是否分期发行"],
        "models": [
            {
                "name": "syllabus_based",
                "use_crude_answer": True,
                "target_element": ElementType.PARAGRAPH.value,
                "multi_elements": False,
                "paragraph_model": "para_match",
                "para_config": {
                    "paragraph_pattern": r"发行规模.*(?P<content>(分|首)期发行)",
                    "content_pattern": r"发行规模.*(?P<content>(分|首)期发行)",
                },
            },
        ],
    },
    {
        "path": ["发行概况-基本条款", "发行人"],
        "models": [
            {
                "name": "syllabus_based",
                "use_crude_answer": True,
                "syllabus_level": 2,
                "min_level": 2,
                "multi_elements": False,
                "inject_syllabus_features": [
                    r"__regex__发行概况__regex__^(?:本期)?(?:债券)?(?:发行)?的?(?:基本情况(?:和|以?及))?(?:基本|主要)?(?:发行)?条款$"
                ],
                "ignore_syllabus_children": True,
                "max_syllabus_range": 100,
                "paragraph_model": "para_match",
                "para_config": {
                    "paragraph_pattern": r"发行(?:主体|人)[:：](?P<content>.*公司)",
                    "content_pattern": r"发行(?:主体|人)[:：](?P<content>.*公司)",
                    "anchor_regs": (r"发行(?:主体|人)[:：]?$",),
                    "current_regs": (r"^(?P<content>[^,。，]*?)(?:[,，。]|$)",),
                },
            },
        ],
    },
    {
        "path": ["发行概况-基本条款", "本期发行规模"],
        "models": [
            {
                "name": "partial_text",
                "regs": [
                    r"本期(公司)?债券.*?(?:(发行|面值)(?:总?规模|总金?额|金额)+)为?(?:不超过)?(?:人民币|美元)?\s?(?P<dst>[\d.,]+)"
                ],
                "model_alternative": True,
            }
        ],
    },
    {
        "path": ["发行概况-基本条款", "债券简称详情"],
        "models": [
            {
                "name": "bond_abbreviation",
                "max_syllabus_range": 100,
                "ignore_syllabus_children": True,
                "para_config": {
                    "债券简称": {
                        "regs": [
                            r"债券简称为?[:：“]*(?P<dst>.*?)[;；。，,”]",
                            r"（品种[一二]）”，简称为?[:：“]*(?P<dst>.*?)[;；。，,”]",
                        ],
                        "use_answer_pattern": False,
                    },
                    "债券品种": {
                        "regs": [
                            r"[（(](?P<dst>品种[一二])[）)]”，简称",
                        ],
                        "use_answer_pattern": False,
                    },
                    "model_alternative": True,
                    "multi": True,
                    "merge_char_result": False,
                },
            }
        ],
        "sub_primary_key": ["债券简称"],
    },
    {
        "path": ["发行概况-基本条款", "债券期限"],
        "models": [
            {
                "name": "syllabus_based",
                "extract_from": "same_type_elements",
                "inject_syllabus_features": [
                    r"__regex__发行概况__regex__本[期次].*[基本主要]{2}(?:发行)?条款",
                    r"__regex__发行[概况条款]{2}__regex__本[次期]发行的基本情况__regex__本期债券的(?:基本|主要)(?:发行)?条款",
                    r"__regex__发行条款__regex__本[期次]债券的(?:基本|主要)发行条款",
                ],
                "min_level": 2,
                "syllabus_level": 2,
                "max_syllabus_range": 220,
                "ignore_syllabus_children": True,
                "neglect_patterns": [r"发行主体[:：]"],
                "paragraph_model": "middle_paras",
                "para_config": {
                    "use_direct_elements": True,
                    "top_anchor_regs": [
                        r"(?:(?:债券|发行)(?:(?:品种|利率)(?:以?及|和))?期限(?:(?:以?及|和)(?:品种|利率))?"
                        r"|债券期限(?:以?及|和|或|、)?[^:：]{,10})"
                        r"(?:[】:：]+|[】:：]?$)"
                    ],
                    "top_anchor_content_regs": [
                        r"(?:(?:债券|发行)(?:(?:品种|利率)(?:以?及|和))?期限(?:(?:以?及|和)(?:品种|利率))?"
                        r"|债券期限(?:以?及|和|或|、)?[^:：]{,10})"
                        r"[】:：]+[\s]*(?P<content>.*)"
                    ],
                    "bottom_anchor_regs": [
                        r"(?:付息的期限(?:以?及|和|或)?其?方式"
                        r"|债券形式"
                        r"|起息日"
                        r"|发行规模"
                        r"|债券名称"
                        r"|强制付息(?:以?及|和|或)递延支付利息的限制"
                        r"|赎回方式"
                        r"|发行(?:对象|方式)|确定方式"
                        r"|担保情况"
                        r"|会计处理"
                        r"|回售登记期"
                        r"|递延支付利息权"
                        r"|票面金额(?:(?:以?及|和|或)发行价格)?"
                        r"|(?:发行人|投资者|调整票面利率|票面利率调整|赎回|续期)选择权)"
                        r"(?:[】:：]|$)"
                    ],
                },
            }
        ],
    },
    {
        "path": ["发行概况-基本条款", "担保情况"],
        "models": [
            {
                "name": "syllabus_based",
                "use_crude_answer": True,
                "ignore_syllabus_children": True,
                "max_syllabus_range": 100,
                "target_element": ElementType.PARAGRAPH.value,
                "neglect_patterns": [r"发行主体[:：]"],
                "multi_elements": False,
                "paragraph_model": "para_match",
                "para_config": {
                    "paragraph_pattern": r"(?:担保(?:情况|方式)|增信措施|信用安排|担保事项|担保人以?及担保方式|债券担保)[:：](?P<content>.*)$",
                    "content_pattern": r"(?:担保(?:情况|方式)|增信措施|信用安排|担保事项|担保人以?及担保方式|债券担保)[:：](?P<content>.*)$",
                    "anchor_regs": (
                        r"(?:担保(?:情况|方式)|增信措施|信用安排|担保事项|担保人以?及担保方式|债券担保)[:：]?$",
                    ),
                    "current_regs": (r"^(?P<content>.*担保.*)$",),
                },
            }
        ],
    },
    {
        "path": ["发行概况-基本条款", "发行人主体评级"],
        "models": [
            {
                "name": "partial_text",
                "regs": [
                    r"(?:信用评级机构以?及信用评级结果|信用等级以?及资信评级机构)[:：]"
                    r".*(?:公司|发行人)的?主体信用(?:等级|级别|评级)[为是](?P<dst>[^级,，；;。]*?)[级,，；;。]",
                ],
                "model_alternative": True,
            }
        ],
    },
    {
        "path": ["发行概况-基本条款", "债项评级"],
        "models": [
            {
                "name": "partial_text",
                "regs": [
                    r"(?:信用评级机构以?及信用评级结果|信用等级以?及资信评级机构)[:：].*本.债券的?.{,2}(?:等级|级别|评级)[为是](?P<dst>[^级,，；;。]*?)[级,，；;。]"
                ],
                "model_alternative": True,
            }
        ],
    },
    {
        "path": ["发行概况-基本条款", "主承销商"],
        "models": [
            {
                "name": "main_consignee",
                "location_threshold": 0.3,
                "use_answer_pattern": False,
                "multi": True,
                "multi_elements": True,
            }
        ],
    },
    {
        "path": ["发行概况-基本条款", "簿记管理人"],
        "models": [
            {
                "name": "partial_text",
                "use_answer_pattern": False,
            }
        ],
    },
    {
        "path": ["发行概况-基本条款", "发行方式"],
        "models": [
            {
                "name": "partial_text",
            }
        ],
    },
    {
        "path": ["发行概况-基本条款", "配售原则"],
        "models": [
            {
                "name": "partial_text",
                "regs": [r"配售(?:规|原)则[】:：]+(?P<dst>.*)"],
                "model_alternative": True,
            },
        ],
    },
    {
        "path": ["发行概况-基本条款", "交易场所"],
        "models": [
            {
                "name": "partial_text",
                "regs": [
                    r"(交易|上市)(流通)?(场所|地)[:：](?P<dst>.*?)[;；。，,”]",
                    r"[深上北][圳海京]?(证券交易|交)所",
                ],
            },
            {
                "name": "syllabus_based",
                "inject_syllabus_features": [r"__regex__释义"],
                "table_model": "row_match",
                "table_config": {
                    "merge_row": True,
                    "row_pattern": [
                        r"[深上北][圳海京]?(证券交易|交)所",
                    ],
                    "content_pattern": [
                        r"指(?P<dst>.*)",
                    ],
                },
            },
        ],
    },
    {
        "path": ["发行概况-基本条款", "品种间回拨选择权"],
        "models": [
            {
                "name": "partial_text",
                "regs": [r"品种间回拨选择权(?:条款)?[】:：]+[\s]*(?P<dst>.*)$"],
                "model_alternative": True,
            }
        ],
    },
    {
        "path": ["发行概况-基本条款", "发行人调整票面利率选择权"],
        "models": [
            {
                "name": "syllabus_based",
                "extract_from": "same_type_elements",
                "one_result_per_feature": False,
                "inject_syllabus_features": [
                    r"__regex__发行概况__regex__本[期次].*[基本主要]{2}(?:发行)?条款",
                    r"__regex__发行[概况条款]{2}__regex__本[次期]发行的基本情况__regex__本期债券的(?:基本|主要)(?:发行)?条款",
                    r"__regex__发行条款__regex__本[期次]债券的(基本|特殊)发行条款",
                ],
                "min_level": 2,
                "syllabus_level": 2,
                "max_syllabus_range": 100,
                "ignore_syllabus_children": True,
                "neglect_patterns": [r"发行主体[:：]"],
                "paragraph_model": "middle_paras",
                "para_config": {
                    "use_direct_elements": True,
                    "top_anchor_regs": [r"(?:调整票面利率|票面利率调整)选择权(?:条款)?[】:：]+"],
                    "top_anchor_content_regs": [
                        r"(?:调整票面利率|票面利率调整)选择权(?:条款)?[】:：]+[\s]*(?P<content>.*)"
                    ],
                    "bottom_anchor_regs": [
                        r"(强制付息及递延支付利息的限制|赎回方式|票面金额(?:以?及发行价格)?|会计处理|(发行人|投资者|赎回).*选择权(?:条款)?)[】:：]+"
                    ],
                },
            },
        ],
    },
    {
        "path": ["发行概况-基本条款", "投资者回售选择权"],
        "models": [
            {
                "name": "partial_text",
                "regs": [r"回售选择权(?:条款)?[】:：]+[\s]*(?P<dst>.*)$"],
                "model_alternative": True,
            }
        ],
    },
    {
        "path": ["发行概况-基本条款", "发行人赎回选择权"],
        "models": [
            {
                "name": "syllabus_based",
                "extract_from": "same_type_elements",
                "one_result_per_feature": False,
                "inject_syllabus_features": [
                    r"__regex__发行概况__regex__本[期次].*[基本主要]{2}(?:发行)?条款",
                    r"__regex__发行[概况条款]{2}__regex__本[次期]发行的基本情况__regex__本期债券的(?:基本|主要)(?:发行)?条款",
                    r"__regex__发行条款__regex__本[期次]债券的(基本|特殊)发行条款",
                ],
                "min_level": 2,
                "syllabus_level": 2,
                "max_syllabus_range": 100,
                "ignore_syllabus_children": True,
                "paragraph_model": "middle_paras",
                "para_config": {
                    "use_direct_elements": True,
                    "top_anchor_regs": [r"(?:发行人)?赎回(选择)?权(?:条款)?[】:：]+"],
                    "top_anchor_content_regs": [r"(?:发行人)?赎回(选择)?权(?:条款)?[】:：]+(?P<content>.*)"],
                    "bottom_anchor_regs": [
                        r"(强制付息及递延支付利息的限制|赎回方式|票面金额(?:以?及发行价格)?|会计处理|(发行人|投资者|调整票面利率|票面利率调整|赎回).*选择权(?:条款)?)[】:：]+"
                    ],
                },
            },
        ],
    },
    {
        "path": ["发行概况-基本条款", "回售登记期"],
        "models": [
            {
                "name": "partial_text",
            }
        ],
    },
    {
        "path": ["发行概况-基本条款", "债券利率及其确定方式"],
        "models": [
            {
                "name": "syllabus_based",
                "extract_from": "same_type_elements",
                "inject_syllabus_features": [
                    r"__regex__发行概况__regex__发行的基本情况$__regex__^(?:本期)?(?:债券)?(?:发行)?的?(?:基本情况(?:和|以?及))?(?:基本|主要)?(?:发行)?条款$",
                    r"__regex__发行概况__regex__^(?:本期)?(?:债券)?(?:发行)?的?(?:基本情况(?:和|以?及))?(?:基本|主要)(?:发行)?条款$",
                ],
                "min_level": 2,
                "syllabus_level": 2,
                "max_syllabus_range": 300,
                "ignore_syllabus_children": True,
                "paragraph_model": "middle_paras",
                "para_config": {
                    "use_direct_elements": True,
                    "top_anchor_regs": [r"(?:债券|票面)利率(?:以?及|和|或)其?确定方式(?:、?定价流程)?[:：]?|债券利率$"],
                    "top_anchor_content_regs": [
                        r"(?:债券|票面)利率(?:以?及|和|或)其?确定方式(?:、?定价流程)?[】:：]+(?P<content>.*)"
                    ],
                    "bottom_anchor_regs": [
                        r"(?:付息的期限(?:以?及|和|或)?其?方式"
                        r"|债券形式"
                        r"|起息日"
                        r"|强制付息(?:以?及|和|或)递延支付利息的限制"
                        r"|赎回方式"
                        r"|发行(?:对象|方式)"
                        r"|担保情况"
                        r"|会计处理"
                        r"|回售登记期"
                        r"|递延支付利息权"
                        r"|票面金额(?:(?:以?及|和|或)发行价格)?"
                        r"|(?:发行人|投资者|调整票面利率|票面利率调整|赎回|续期)选择权(?:条款)?)"
                        r"(?:[】:：]|$)"
                    ],
                },
            }
        ],
    },
    {
        "path": ["发行概况-基本条款", "发行人续期选择权"],
        "models": [
            {
                "name": "partial_text",
                "regs": [r"发行人续期选择权(?:条款)?[】:：]+[\s]*(?P<dst>.*)$"],
                "model_alternative": True,
            }
        ],
    },
    {
        "path": ["发行概况-基本条款", "递延支付利息权"],
        "models": [
            {
                "name": "partial_text",
                "regs": [r"递延支付利息权(?:条款)?[】:：]+[\s]*(?P<dst>.*)$"],
                "model_alternative": True,
            }
        ],
    },
    {
        "path": ["发行概况-基本条款", "强制付息事件"],
        "models": [
            {
                "name": "partial_text",
            }
        ],
    },
    {
        "path": ["发行概况-基本条款", "利息递延下的限制事项"],
        "models": [
            {
                "name": "partial_text",
            }
        ],
    },
    {
        "path": ["发行概况-基本条款", "偿付顺序"],
        "models": [
            {
                "name": "partial_text",
            }
        ],
    },
    {
        "path": ["发行概况-基本条款", "债券基本条款"],
        "models": [
            {
                "name": "syllabus_elt_v2",
                "inject_syllabus_features": [
                    r"__regex__发行概况__regex__本[期次].*[基本主要]{2}(?:发行)?条款",
                    r"__regex__发行[概况条款]{2}__regex__本[次期]发行的基本情况__regex__本[次期]债券的(?:基本|主要)(?:发行)?条款",
                    r"__regex__发行条款__regex__本[期次]债券的(?:基本|主要)(?:发行)?条款",
                ],
            },
        ],
    },
    {
        "path": ["发行概况-基本条款", "债券特殊条款"],
        "models": [
            {
                "name": "syllabus_elt_v2",
                "inject_syllabus_features": [
                    r"__regex__发行[概况条款]{2}__regex__本[期次].*特殊(?:发行)?条款",
                    r"__regex__发行[概况条款]{2}__regex__本[次期]发行的基本情况__regex__本[次期]债券的特殊(?:发行)?条款",
                ],
                "only_inject_features": True,
            },
        ],
    },
    {
        "path": ["发行概况-基本条款", "计息方式"],
        "models": [
            {
                "name": "partial_text",
                "regs": [
                    r"记息方式[:：][\s]*(?P<dst>.*)$",
                    r"(?:债券利率以?及其?确定方式|调整票面利率选择权(?:条款)?)[:：][\s]*(?P<dst>.*计息.*)$",
                ],
                "model_alternative": True,
            },
        ],
    },
    {
        "path": ["发行概况-基本条款", "付息日"],
        "models": [
            {
                "name": "partial_text",
                "regs": [r"付息日期?[:：][\s]*(?P<dst>.*)$"],
                "model_alternative": True,
            },
        ],
    },
    {
        "path": ["发行概况-基本条款", "付息、兑付方式"],
        "crude_answer_path": ["发行概况-基本条款", "付息、兑付方式"],
        "models": [
            {
                "name": "para_match",
                "paragraph_pattern": r"(付息、兑付|还本付息(的期限和)?)方式[:：]?(?P<content>.*)",
                "content_pattern": r"(付息、兑付|还本付息(的期限和)?)方式[:：]?(?P<content>.*)",
            },
        ],
    },
    {
        "path": ["发行概况-基本条款", "兑付日"],
        "models": [
            {
                "name": "partial_text",
            },
        ],
    },
    {
        "path": ["发行概况-基本条款", "债券全称"],
        "models": [
            {
                "name": "syllabus_based",
                "inject_syllabus_features": [
                    r"__regex__发行概况__regex__本[期次].*[基本主要]{2}(?:发行)?条款",
                    r"__regex__发行[概况条款]{2}__regex__本[次期]发行的基本情况__regex__本期债券的主要(?:发行)?条款",
                    r"__regex__发行条款__regex__本[期次]债券的基本发行条款",
                ],
                "use_crude_answer": True,
                "ignore_syllabus_children": True,
                "max_syllabus_range": 100,
                "target_element": ElementType.PARAGRAPH.value,
                "multi_elements": False,
                "paragraph_model": "para_match",
                "para_config": {
                    "paragraph_pattern": [
                        r'本期债券分为两个品种.其中品种一债券全称为[：:"“](?P<content>.*?)[(（]品种一',
                        r"(?:^[(（]?[一二三四五六七八九0-9]*[)）]?[、.．\s]*"
                        r"(?:本期)?(?<!本次)债券(名|全)称(?:及代码)?[:：](?!本次债券)(?!本期债券分.个)"
                        r"|^[(（]?[一二三四五六七八九0-9]*[)）]?[、.．\s]*(?:本期)?(?<!本次)债券(名|全)称(?:及代码)?[:：]"
                        r'.*?债券全称为[：:"“])'
                        r"(?:品种.{,2}[:：]\s*)?"
                        r"(?P<content>[^:，：]+?(?:[(（](?!品种)(?!简称)(?!债券代码)(?!债券简称)(?!债券品种)[^）)]+?[)）])?)"
                        r'(?:[(（](?:(?:债?券?品种|债?券?简称|债?券?代码))?|[;；。，,”"]|$)',
                    ],
                    "anchor_regs": (r"(?:本期)?债券(名|全)称(?:及代码)?[:：]?$",),
                    "current_regs": (r"^(?P<content>[^,。，]*?)(?:[,，。．]|$)",),
                },
            },
        ],
    },
    {
        "path": ["发行概况-基本条款", "债券品种"],
        "models": [{"name": "partial_text", "multi": True, "regs": [r'(?<![”"“])品种[一二三四五六七八九]']}],
    },
    {
        "path": ["发行概况-有关机构", "发行人机构信息"],
        "models": [
            {
                "name": "syllabus_elt_v2",
                "inject_syllabus_features": [
                    r"__regex__发行概况__regex__本[期次].*[有相]关机构__regex__发行人(.*公司)?",
                    r"__regex__(?:(?:本[期次]债券)?发行的?[有相]关机构|发行人以?及中介机构基本信息)__regex__发行人(?![与和])(.*公司)?",
                ],
            },
        ],
    },
    {
        "path": ["发行概况-有关机构", "主承销商机构信息"],
        "models": [
            {
                "name": "consignee_info",
                "min_level": 2,
                "syllabus_level": 2,
                "one_result_per_feature": False,
                "inject_syllabus_features": [
                    r"__regex__(?:(?:本次债券)?发行的?[有相]关机构|发行人以?及中介机构基本信息)"
                    r"__regex__(?:^|[/.,，．／、或以及\)）]+)(?<!副)(主承销商|主?承销机构)+(?:[、／/:：,，或以及]+|$)",
                    r"__regex__(?:(?:本次债券)?发行的?[有相]关机构|发行人以?及中介机构基本信息)"
                    r"__regex__(?:^|[/.,，．／、或以及\)）]+)联席(主承销(?:商|机构)+|承销机构)(?:[、／/:：,，或以及]+|$)",
                    r"__regex__(?:(?:本次债券)?发行的?[有相]关机构|发行人以?及中介机构基本信息)"
                    r"__regex__(?:^|[/.,，．／、或以及\)）]+)牵头(主承销(?:商|机构)+|承销机构)(?:[、／/:：,，或以及]+|$)",
                ],
                "multi": True,
                "neglect_patterns": [r"副主承销商", r"风险提示|厉害关系|备查文件|查阅地点", r"分销商[:：]"],
                "para_config": {
                    "regs": [r"(?P<dst>(牵头|联席)?(主承销(?:商|机构)+|承销机构)(?:(?!以?及其他承销机构).)*)$"]
                },
            },
            {
                "name": "consignee_info",
                "min_level": 3,
                "syllabus_level": 3,
                "one_result_per_feature": False,
                "inject_syllabus_features": [
                    r"__regex__(?:(?:本次债券)?发行的?[有相]关机构|发行人以?及中介机构基本信息)"
                    r"__regex__(承销|发行的有关)机构"
                    r"__regex__(?:^|[/.,，．／、或以及\)）]+)(?<!副)主承销(?:商|机构)+(?:[、／/:：,，或以及]+|$)",
                    r"__regex__(?:(?:本次债券)?发行的?[有相]关机构|发行人以?及中介机构基本信息)"
                    r"__regex__(承销|发行的有关)机构"
                    r"__regex__(?:^|[/.,，．／、或以及\)）]+)联席(主承销(?:商|机构)+|承销机构)(?:[、／/:：,，或以及]+|$)",
                    r"__regex__(?:(?:本次债券)?发行的?[有相]关机构|发行人以?及中介机构基本信息)"
                    r"__regex__(承销|发行的有关)机构"
                    r"__regex__(?:^|[/.,，．／、或以及\)）]+)牵头(主承销(?:商|机构)+|承销机构)(?:[、／/:：,，或以及]+|$)",
                ],
                "multi": True,
                "neglect_patterns": [r"副主承销商", r"风险提示|厉害关系|备查文件|查阅地点", r"分销商[:：]"],
                "para_config": {
                    "regs": [r"(?P<dst>(牵头|联席)?(主承销(?:商|机构)+|承销机构)(?:(?!以?及其他承销机构).)*)$"]
                },
            },
        ],
        "sub_primary_key": ["主承销商名称"],
    },
    {
        "path": ["发行概况-有关机构", "簿记管理人联系人（指定收款银行）"],
        "models": [
            {
                "name": "syllabus_based",
                "inject_syllabus_features": [r"__regex__^[一二三四五六七八九十]*[.、]*簿记管理人收款银行$"],
                "multi_elements": False,
                "paragraph_model": "para_match",
                "para_config": {
                    "paragraph_pattern": r"联系人[:：]?(?P<content>.*)",
                    "content_pattern": r"联系人[:：]?(?P<content>.*)",
                    "split_pattern": r"[、]",
                },
                "table_model": "table_kv",
                "table_config": {
                    "regs": {
                        "簿记管理人联系人（指定收款银行）": [r"联系人"],
                    }
                },
            },
        ],
    },
    {
        "path": ["发行概况-有关机构", "簿记管理人收款联系电话（指定收款银行）"],
        "models": [
            {
                "name": "syllabus_based",
                "inject_syllabus_features": ["簿记管理人收款银行"],
                "multi_elements": False,
                "paragraph_model": "para_match",
                "para_config": {
                    "paragraph_pattern": r"电话[:：]?(?P<content>.*)",
                    "content_pattern": r"电话[:：]?(?P<content>.*)",
                    "split_pattern": r"[、]",
                },
                "table_model": "table_kv",
                "table_config": {
                    "regs": {
                        "簿记管理人收款联系电话（指定收款银行）": [r"电话"],
                    }
                },
            },
        ],
    },
    {
        "path": ["发行概况-有关机构", "簿记管理人联系人（簿记管理人）"],
        "models": [
            {
                "name": "syllabus_based",
                "inject_syllabus_features": [
                    r"__regex__(?:(?:本次债券)?发行的?[有相]关机构|发行人以?及中介机构基本信息)__regex__簿记管理人",
                ],
                "multi_elements": False,
                "paragraph_model": "para_match",
                "para_config": {
                    "paragraph_pattern": r"联系人[:：]?(?P<content>.*)",
                    "content_pattern": r"联系人[:：]?(?P<content>.*)",
                    "split_pattern": r"[、]",
                },
                "table_model": "table_kv",
                "table_config": {
                    "regs": {
                        "簿记管理人联系人（簿记管理人）": [r"联系人"],
                    }
                },
            },
        ],
    },
    {
        "path": ["发行概况-有关机构", "簿记管理人收款联系电话（簿记管理人）"],
        "models": [
            {
                "name": "syllabus_based",
                "inject_syllabus_features": [
                    r"__regex__(?:(?:本次债券)?发行的?[有相]关机构|发行人以?及中介机构基本信息)__regex__簿记管理人",
                ],
                "multi_elements": False,
                "paragraph_model": "para_match",
                "para_config": {
                    "paragraph_pattern": r"电话[:：]?(?P<content>.*)",
                    "content_pattern": r"电话[:：]?(?P<content>.*)",
                    "split_pattern": r"[、]",
                },
                "table_model": "table_kv",
                "table_config": {
                    "regs": {
                        "簿记管理人收款联系电话（簿记管理人）": [r"电话"],
                    }
                },
            },
        ],
    },
    {
        "path": ["发行概况-有关机构", "债券受托管理人"],
        "models": [
            {
                "name": "bond_manager",
                "inject_syllabus_features": [
                    r"__regex__(?:(?:本次债券)?发行的?[有相]关机构|发行人以?及中介机构基本信息)__regex__债券受托管理人",
                ],
            }
        ],
    },
]

prophet_config = {"depends": {}, "predictor_options": predictor_options}
