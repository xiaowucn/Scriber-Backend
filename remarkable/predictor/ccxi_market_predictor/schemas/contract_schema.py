"""
合同提取
"""

from remarkable.converter.utils import p_chinese_number

CHINESE_NUMBER = p_chinese_number.pattern
amount = rf"(?P<dst>人民币([\d.]+万元整?[/期年]*（大写：?{CHINESE_NUMBER}元(整|人民币)|{CHINESE_NUMBER}元整（￥[\d.]+)[，不含税]*）)"

predictor_options = [
    {
        "path": ["合同编号"],
        "models": [
            {
                "name": "fixed_position",
                "positions": list(range(0, 3)),
                "regs": [r"编号[:：]?(?P<dst>[^:：]+)", r"(?P<dst>^\d[\d\-—–一]+\d$)"],
            },
        ],
    },
    {
        "path": ["企业名称"],
        "models": [
            {
                "name": "partial_text",
                "use_answer_pattern": False,
                "regs": [r"(委托|甲)方[:：](?P<dst>.*?公司)"],
                "model_alternative": True,
            },
        ],
    },
    {
        "path": ["合同签署第三方"],
        "models": [
            {
                "name": "partial_text",
            },
        ],
    },
    {
        "path": ["地区"],
        "models": [
            {
                "name": "table_kv",
            },
            {
                "name": "fixed_position",
                "positions": list(range(0, 10)),
                "regs": [r"签[订约]地点[:：]?(?P<dst>[^:：签]+)"],
            },
        ],
    },
    {
        "path": ["项目名称"],
        "models": [
            {
                "name": "partial_text",
                "regs": [r"项目名称[：:](?P<dst>[^委]*)"],
            },
            {
                "name": "table_kv",
                "feature_white_list": [r"__regex__项目名称[：:]"],
            },
            {
                "name": "table_kv",
                "split_single_column_table": True,
                "feature_white_list": [r"__regex__项目名称"],
                "regs": {
                    "项目名称": [r"项目名称[：:](?P<dst>.*)"],
                },
            },
        ],
    },
    {
        "path": ["签订日期"],
        "models": [
            {
                "name": "table_kv",
            },
            {
                "name": "fixed_position",
                "positions": list(range(0, 10)),
                "regs": [r"签订(日期|时间)[:：]?(?P<dst>[^:：]+)"],
            },
        ],
    },
    {
        "path": ["品种"],
        "models": [
            {
                "name": "partial_text",
            },
            {
                "name": "fixed_position",
                "positions": list(range(0, 10)),
                "regs": [r"项目名称[:：]?(?P<dst>[^:：委]+)", r"(?P<dst>.*?信用评级服务)"],
            },
        ],
    },
    {
        "path": ["首次金额（债券）"],
        "models": [
            {
                "name": "partial_text",
                "multi_elements": True,
                "multi": True,
                "regs": [
                    rf"((首次|初始)(债项)?|主体信用)评级费用(（包含第一期）)?(总计|均?为){amount}",
                    rf"首次评级费用及跟踪评级费用总计为{amount}",
                ],
                "model_alternative": True,
            },
        ],
    },
    {
        "path": ["主体续作费用"],
        "models": [
            {
                "name": "partial_text",
            },
        ],
    },
    {
        "path": ["分期金额"],
        "models": [
            {
                "name": "partial_text",
                "multi_elements": True,
                "regs": [
                    rf"((各[期债券]+另行收取|一次性支付当期)债项评级费用|分期发行的?评级费用为每期){amount}",
                    rf"(各品种各期另行收取债项评级费用|其他期债项评级费用收取){amount}",
                    rf"分期发行的评级费用[（(]不含.*?费用[）)]为每期{amount}",
                ],
            },
        ],
    },
    {
        "path": ["更新金额（一年内）"],
        "models": [
            {
                "name": "partial_text",
                "neglect_patterns": [r"跟踪"],
                "regs": [
                    rf"不超过一年的，乙方需重新进场访谈。甲方应.*支付报告更新评级费用{amount}",
                ],
                "model_alternative": True,
            },
        ],
    },
    {
        "path": ["更新金额（超过一年内）"],
        "models": [
            {
                "name": "partial_text",
                "neglect_patterns": [r"跟踪"],
                "regs": [
                    rf"[^不]超过一年的，乙方需重新进场访谈。甲方应.*支付报告更新评级费用{amount}",
                ],
                "model_alternative": True,
            },
        ],
    },
    {
        "path": ["跟踪金额（第一年）"],
        "models": [
            {
                "name": "partial_text",
                "neglect_patterns": [r"更新"],
                "regs": [
                    rf"甲方为本债券的跟踪评级每年向乙方支付{amount}的跟踪评级费用",
                    rf"甲方应为跟踪评级向乙方支付跟踪评级费用{amount}",
                    rf"甲方每年只需向乙方支付一笔跟踪评级费用，共计{amount}",
                    rf"跟踪评级费用为{amount}",
                    rf"各债券的跟踪评级以及.*?，合并收取一笔评级费用，每年共计{amount}",
                ],
                "model_alternative": True,
            },
        ],
    },
    {
        "path": ["跟踪金额（第一年之后）"],
        "models": [
            {
                "name": "partial_text",
                "neglect_patterns": [r"更新"],
                "regs": [
                    rf"从第.年起的跟踪评级费用为{amount}",
                    rf"乙方每年对甲方已成功发行并委托乙方评级的各债券的跟踪评级.*?每年共计{amount}",
                    rf"跟踪评级费用为{amount}",
                ],
            },
        ],
    },
    {
        "path": ["违约责任"],
        "models": [
            {
                "name": "syllabus_elt_v2",
            },
        ],
    },
    {
        "path": ["评级报告的用途"],
        "models": [
            {
                "name": "para_match",
                "paragraph_pattern": (
                    r"乙方同意向甲方提供的.*?用于.*?使用",
                    r"甲方不得引用乙方所出具的.*?发行[任何其他的]+债务融资工具",
                    r"如果甲方在.*的发行文件中引用乙方出具的.*，应当经过乙方事先书面同意",
                    r"乙方所出具的.*是乙方对甲方.*的客观意见；乙方所出具的.*不等.?于甲方发行的任何债务融资工具的信用评级结果",
                    r"未经乙方事先书面(许可|同意)，甲方不得在其他融资工具的发行文件中引用乙方出具的主体信用评级报告和信用评级结果",
                    r"甲方不得引用乙方所出具的主体信用评级结果和主体信用评级报告发行除大额存单和同业存单外的其他债务融资工具",
                ),
            }
        ],
    },
]

prophet_config = {"depends": {}, "predictor_options": predictor_options}
