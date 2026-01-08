"""
中信-募集书抽取-附加二
"""

from remarkable.common.diff.mixins import P_SERIAL
from remarkable.predictor.glazer_predictor.schemas.citic_issue_announcement_plus_one_schema import (
    issue_related_institution,
    issuer_basic_pattern,
    issuer_survey_pattern,
)
from remarkable.predictor.glazer_predictor.schemas.citic_issue_announcement_schema import P_BASE_TITLE, P_DETAIL_NAME

p_release_profile = [r"发行(概况|条款)"]
p_bond_variety = [
    r"品种[一二三四五六七八九](?=债?券?(?:全称|简称)为)",
    r"(?<!以下简称.|第.期[)）][(（])品种[一二三四五六七八九](?!的期限延长)(?!债?券?(?:全称|简称)为)",
]

P_INVALID_SUFFIX = r"(?:具体募集资金用途详见.*第.*?节|本.债券募集资金具体使用.{,2}如下)?"

use_of_funds = [
    {
        "name": "partial_text",
        "neglect_syllabus_regs": [r"前次"],
        "use_answer_pattern": False,
        "regs": [
            rf"(?P<dst>本期债券募集资金扣除发行费用后[，,]?[拟将]+(?:(?:不低于.*?资金|全部(?:资金)?)?用于.*)){P_INVALID_SUFFIX}",
            rf"(?P<dst>本次公开发行.*?债券募集资金总额不超过.*?募集资金总额扣除发行费用后(?:主要|全部)?用于以下项目.){P_INVALID_SUFFIX}",
        ],
        "model_alternative": True,
    },
    {
        "name": "para_match",
        "neglect_syllabus_regs": [r"前次"],
        "paragraph_pattern": [
            r"补充.*?(营运|流动)资金",
            r"偿还银行贷款|保障房建设|建设项目|项目建设|项目专项投资",
            r"偿还.*?(负债|债|银行贷款|公司借款)",
            r"(偿还|支付).*?\d+.*?(本金|回收款|利息)",
            r"对全资子公司出资",
            r"补充.*?(营运|流动)资金",
        ],
    },
    {
        "name": "syllabus_based",
        "ignore_syllabus_children": True,
        "max_syllabus_range": 100,
        "paragraph_model": "para_match",
        "para_config": {
            "paragraph_pattern": [
                r"本期债券.*(全部|费用后)用于.*",
                r"本次(公开)?发行的.*?债券募集资金(规模|总额)为?不超过.*?其中.*?元拟用于.*?另外.*元拟用于",
            ],
        },
    },
]


predictor_options = [
    {
        "path": ["批文日期"],
        "models": [
            {
                "name": "partial_text",
                "syllabus_regs": p_release_profile,
                "neglect_syllabus_regs": [r"前次"],
                "regs": [
                    r"(?P<dst>20\d{2}年\d{1,2}月\d{1,2}日).*?下发了.*?字.*?[\d]+号.*?发行不超过.*?债券",
                    r"(?P<dst>20\d{2}年\d{1,2}月\d{1,2}日).?(经|获|通过|领取).*?证监许可.*?\d*号.*?(同意|核准|获准).*?发行[面值总额]*不超过.*?债券",
                    r"(?P<dst>20\d{2}年\d{1,2}月\d{1,2}日).?(经|获|通过|领取).*?(同意|核准|获准).*?证监许可.*?\d*号",
                    r"并于(?P<dst>20\d{2}年\d{1,2}月\d{1,2}日).?(经|获|通过|领取)《[^《》]*?》[（(]证监许可.*?\d*号",
                    r"本次发行已于(?P<dst>20\d{2}年\d{1,2}月\d{1,2}日)通过.*?审核",
                    r"(?P<dst>20\d{2}年\d{1,2}月\d{1,2}日).*?证监许可.*?\d*号.*?(同意|核准|获准).*?发行[面值总额]*不超过.*?债券",
                    r"(?P<dst>20\d{2}年\d{1,2}月\d{1,2}日).*?获.*?同意.*?发行[面值总额]*不超过.*?债券.*?证监许可.*?\d*号",
                    r"(?P<dst>20\d{2}年\d{1,2}月\d{1,2}日).*?(?:收到|获得?).*?证监许可.*?\d*号",
                    r"(?P<dst>20\d{2}年\d{1,2}月\d{1,2}日).经.*同意并经中国证监会注册.*?发行[面值总额]*不超过.*?债券",
                    r"获批文件[:：].*?发行人于(?P<dst>20\d{2}年\d{1,2}月\d{1,2}日).?(经|获|通过).*?上证函",
                    r"(?P<dst>\s*\d{,4}\s*年\s*\d{,2}\s*月\s*\d{,2}\s*日)[,，]?(?:发行人)?(?:获得?|收到|经|通过|领取)"
                    r"(?:上交所|上海证券交易所)(?:出具的?|签发的|同意|无异议|核准|获准)[^,.。;]*上证函",
                ],
                "model_alternative": True,
            },
        ],
    },
    {
        "path": ["核准文号"],
        "models": [
            {
                "name": "partial_text",
                "neglect_syllabus_regs": [r"前次"],
                "regs": [
                    r"证监许可.*?号",
                    r"深证函.*?号",
                    r"上证函.*?号",
                    r"获批文件[:：].*?发行人于20\d{2}年\d{1,2}月\d{1,2}日.?(经|获|通过).*?(?P<dst>上证函[^\)）]+号)",
                    r"注册文件[:：].*?发行人于\s*\d{,4}\s*年\s*\d{,2}\s*月\s*\d{,2}\s*日[,，]?(?:发行人)?(?:获得?|收到|经|通过)"
                    r"(?:上交所|上海证券交易所)(?:出具的?|签发的|同意|无异议|核准|获准).*(?P<dst>上证函[^\)）]+号)",
                ],
                "model_alternative": True,
            },
        ],
    },
    {
        "path": ["核准总额"],
        "models": [
            {
                "name": "partial_text",
                "syllabus_regs": p_release_profile,
                "use_answer_pattern": False,
                "regs": [
                    r"向(专业|合格)投资者(公开)?发行[面值总额]*不超过(（含）)?(人民币)?(?P<dst>[\d.]+)亿元",
                    r"本次公开发行不超过(（含）)?(人民币)?(?P<dst>[\d.]+)亿元.*?的公司债券已经.*?交易所审核通过",
                    r"本公司将在中国境内公开发行不超过(（含）)?(人民币)?(?P<dst>[\d.]+)亿元",
                    r"发行人获准公开发行不超过(（含）)?(人民币)?(?P<dst>[\d.]+)亿元",
                    r"(核准|注册)规模为不超过(（含）)?(人民币)?(?P<dst>[\d.]+)亿元",
                    r"发行人于.*?获.*出具的.*?核准.*?发行总额为不超过(（含）)?(人民币)?(?P<dst>[\d.]+)亿元",
                    r"获批文件[:：].*?本次非?公开发行.?期?公司债券总额不超过(（含）)?(人民币)?(?P<dst>[\d.]+)亿元",
                ],
                "model_alternative": True,
            },
            {
                "name": "syllabus_based",
                "syllabus_level": 2,
                "min_level": 2,
                "inject_syllabus_features": p_release_profile,
                "ignore_syllabus_children": True,
                "max_syllabus_range": 100,
                "multi_elements": False,
                "paragraph_model": "partial_text",
                "para_config": {
                    "use_answer_pattern": False,
                    "regs": [
                        r"向(专业|合格)投资者(公开)?发行[面值总额]*不超过(（含）)?(人民币)?(?P<dst>[\d.]+)亿元",
                        r"本次公开发行不超过(（含）)?(人民币)?(?P<dst>[\d.]+)亿元.*?的公司债券已经.*?交易所审核通过",
                        r"本公司将在中国境内公开发行不超过(（含）)?(人民币)?(?P<dst>[\d.]+)亿元",
                        r"发行人获准公开发行不超过(（含）)?(人民币)?(?P<dst>[\d.]+)亿元",
                        r"(核准|注册)规模为不超过(（含）)?(人民币)?(?P<dst>[\d.]+)亿元",
                        r"发行人于.*?获.*出具的.*?核准.*?发行总额为不超过(（含）)?(人民币)?(?P<dst>[\d.]+)亿元",
                        r"获批文件[:：].*?本次非?公开发行.?期?公司债券总额不超过(（含）)?(人民币)?(?P<dst>[\d.]+)亿元",
                    ],
                    "model_alternative": True,
                },
            },
        ],
    },
    {
        "path": ["发行人披露专员"],
        "models": [
            # 信息披露(事务)?(负责|联络|联系)人(电话|联系方式)   有这种联系方式时 用下面两种
            {
                "name": "elements_collector_based",
                "elements_collect_model": "middle_paras",
                "elements_collect_config": {
                    "table_regarded_as_paras": True,
                    "use_syllabus_model": True,
                    "include_title": True,
                    "inject_syllabus_features": issuer_survey_pattern,
                    "only_inject_features": True,
                    "ignore_syllabus_children": True,
                    "top_anchor_regs": [
                        r"发行人",
                    ],
                    "top_default": True,
                    "bottom_default": True,
                    "include_bottom_anchor": True,
                    "neglect_bottom_anchor": [
                        r"[公司发行人基本]{2,}(信息|情况|概况|资料|概述)",
                    ],
                    "keywords": [r"信息披露(事务)?(负责|联络|联系)人.{,5}(电话|联系方式)"],
                },
                "paragraph_model": "partial_text",
                "para_config": {
                    "multi_elements": True,
                    "column_from_multi_elements": False,
                    "use_answer_pattern": False,
                    "model_alternative": True,
                    "专员": {
                        "column_from_multi_elements": True,
                        "split_pattern": r"[、]",
                        "regs": [
                            r"信息披露(事务)?(负责|联络|联系)人及其职位与联系方式(姓名[/]职位|姓名|信息披露事务负责人|经办人员|联系人|/)*"
                            r"[:：]?(?P<dst>.+?)[;；，/（（]",
                            r"信息披露(事务)?(负责|联络|联系)人及其职位与联系方式(姓名[/]职位|姓名|信息披露事务负责人|经办人员|联系人|/)*"
                            r"[:：]?(?P<dst>.+?)(?:[,，])?(?:总会计|首席|董事|秘书|总裁|职务|职位|电话|联系|传真|负责人职位|地址)",
                            r"信息披露(事务)?(负责|联络|联系)人(姓名[/]职位|姓名|信息披露事务负责人|经办人员|联系人|/)*[:：]?(?P<dst>.+?)"
                            r"(?:[,，])?(?:总会计|首席|董事|秘书|总裁|职务|职位|电话|联系|传真|负责人职位|地址)",
                            r"信息披露(事务)?(负责|联络|联系)人(姓名[/]职位|姓名|信息披露事务负责人|经办人员|联系人|/)*[:：]?(?P<dst>.+)",
                            r"姓名[:：](?P<dst>.+)",
                        ],
                        "neglect_patterns": [
                            r"和联系方式.?$",
                            r"信息披露(事务)?(负责|联络|联系)人联系方式",
                            r"(传真|负责人职位|职务)(?![:：])",
                        ],
                    },
                    "传真号码": {"regs": [r"传真(号码)?[:：]?.*?(?P<dst>[-\d]+)$"]},
                    "电子邮箱": {"regs": [r"电子[邮信]箱[:：]?(?P<dst>.+)"]},
                    "电话号码": {
                        "model_alternative": False,
                        "regs": [
                            r"信息披露(事务)?(负责|联络|联系)人及其职位与联系方式(姓名)?[:：]?.*?(?P<dst>[-\d]{4,})(?![号路])",
                            r"信息披露(事务)?(负责|联络|联系)人(电话|联系方式)(号码)?以?及?(?:传真(号码)?)?[:：]?(?P<dst>[-\d]{4,})(?![号路])",
                            r"信息披露(事务)?(负责|联络|联系)人(电话|联系方式).*?[:：]?(?P<dst>[-\d]{4,})(?![号路])",
                        ],
                    },
                    "电话区号": {
                        "model_alternative": False,
                        "regs": [
                            r"信息披露(事务)?(负责|联络|联系)人及其职位与联系方式(姓名)?[:：]?.*?(?P<dst>[\d]+)\-",
                            r"信息披露(事务)?(负责|联络|联系)人(电话|联系方式)(号码)?[:：]?(?P<dst>\d+)",
                            r"信息披露(事务)?(负责|联络|联系)人(电话|联系方式)(号码)?以?及?(?:传真(号码)?)?[:：]?(?P<dst>[\d]+)",
                            r"信息披露(事务)?(负责|联络|联系)人(电话|联系方式).*?[:：]?(?P<dst>[\d]+)\-",
                        ],
                    },
                },
            },
            {
                "name": "elements_collector_based",
                "elements_collect_model": "middle_paras",
                "elements_collect_config": {
                    "table_regarded_as_paras": True,
                    "use_syllabus_model": True,
                    "include_title": True,
                    "syllabus_level": 2,
                    "min_level": 2,
                    "inject_syllabus_features": issuer_basic_pattern,
                    "only_inject_features": True,
                    "ignore_syllabus_children": True,
                    "top_default": True,
                    "top_anchor_regs": [
                        r"发行人",
                    ],
                    "bottom_default": True,
                    "include_bottom_anchor": True,
                    "neglect_bottom_anchor": [
                        r"[公司发行人基本]{2,}(信息|情况|概况|资料|概述)",
                    ],
                    "keywords": [r"信息披露(事务)?(负责|联络|联系)人.{,5}(电话|联系方式)"],
                },
                "paragraph_model": "partial_text",
                "para_config": {
                    "multi_elements": True,
                    "column_from_multi_elements": False,
                    "use_answer_pattern": False,
                    "model_alternative": True,
                    "专员": {
                        "column_from_multi_elements": True,
                        "split_pattern": r"[、]",
                        "regs": [
                            r"信息披露(事务)?(负责|联络|联系)人及其职位与联系方式(姓名[/]职位|姓名|信息披露事务负责人|经办人员|联系人|/)*"
                            r"[:：]?(?P<dst>.+?)[;；/（（]",
                            r"信息披露(事务)?(负责|联络|联系)人及其职位与联系方式(姓名[/]职位|姓名|信息披露事务负责人|经办人员|联系人|/)*"
                            r"[:：]?(?P<dst>.+?)(?:[,，])?(?:总会计|首席|董事|秘书|总裁|职务|职位|电话|联系|传真|负责人职位|地址)",
                            r"信息披露(事务)?(负责|联络|联系)人(姓名[/]职位|姓名|信息披露事务负责人|经办人员|联系人|/)*[:：]?(?P<dst>.+?)"
                            r"(?:[,，])?(?:总会计|首席|董事|秘书|总裁|职务|职位|电话|联系|传真|负责人职位|地址)",
                            r"信息披露(事务)?(负责|联络|联系)人(姓名[/]职位|姓名|信息披露事务负责人|经办人员|联系人|/)*[:：]?(?P<dst>.+)",
                            r"姓名[:：](?P<dst>.+)",
                        ],
                        "neglect_patterns": [
                            r"和联系方式.?$",
                            r"(传真|负责人职位|职务)(?![:：])",
                            r"信息披露(事务)?(负责|联络|联系)人联系方式",
                        ],
                    },
                    "传真号码": {"regs": [r"传真(号码)?[:：]?.*?(?P<dst>[-\d]+)$"]},
                    "电子邮箱": {"regs": [r"电子[邮信]箱[:：]?(?P<dst>.+)"]},
                    "电话号码": {
                        "model_alternative": False,
                        "regs": [
                            r"信息披露(事务)?(负责|联络|联系)人及其职位与联系方式(姓名)?[:：]?.*?(?P<dst>[-\d]{4,})(?![号路])",
                            r"信息披露(事务)?(负责|联络|联系)人(电话|联系方式)(号码)?以?及?(?:传真(号码)?)?[:：]?(?P<dst>[-\d]{4,})(?![号路])",
                            r"信息披露(事务)?(负责|联络|联系)人(电话|联系方式).*?[:：]?(?P<dst>[-\d]{4,})(?![号路])",
                        ],
                    },
                    "电话区号": {
                        "model_alternative": False,
                        "regs": [
                            r"信息披露(事务)?(负责|联络|联系)人及其职位与联系方式(姓名)?[:：]?.*?(?P<dst>[\d]+)\-",
                            r"信息披露(事务)?(负责|联络|联系)人(电话|联系方式)(号码)?[:：]?(?P<dst>\d+)",
                            r"信息披露(事务)?(负责|联络|联系)人(电话|联系方式)(号码)?以?及?(?:传真(号码)?)?[:：]?(?P<dst>[\d]+)",
                            r"信息披露(事务)?(负责|联络|联系)人(电话|联系方式).*?[:：]?(?P<dst>[\d]+)\-",
                        ],
                    },
                },
            },
            # 信息披露(事务)?(负责|联络|联系)人(电话|联系方式)   没有 这种联系方式时 用下面两种
            {
                "name": "elements_collector_based",
                "elements_collect_model": "middle_paras",
                "elements_collect_config": {
                    "table_regarded_as_paras": True,
                    "use_syllabus_model": True,
                    "include_title": True,
                    "inject_syllabus_features": issuer_survey_pattern,
                    "only_inject_features": True,
                    "ignore_syllabus_children": True,
                    "top_anchor_regs": [
                        r"发行人",
                    ],
                    "top_default": True,
                    "bottom_default": True,
                    "include_bottom_anchor": True,
                    "neglect_bottom_anchor": [
                        r"[公司发行人基本]{2,}(信息|情况|概况|资料|概述)",
                    ],
                    "keywords": [r"信息披露(事务)?(负责|联络|联系)人"],
                },
                "paragraph_model": "partial_text",
                "para_config": {
                    "multi_elements": True,
                    "column_from_multi_elements": False,
                    "use_answer_pattern": False,
                    "model_alternative": True,
                    "专员": {
                        "column_from_multi_elements": True,
                        "split_pattern": r"[、]",
                        "regs": [
                            r"信息披露(事务)?(负责|联络|联系)人及其职位与联系方式(姓名[/]职位|姓名|信息披露事务负责人|经办人员|联系人|/)*"
                            r"[:：]?(?P<dst>.+?)[;；/（（]",
                            r"信息披露(事务)?(负责|联络|联系)人及其职位与联系方式(姓名[/]职位|姓名|信息披露事务负责人|经办人员|联系人|/)*[:：]?"
                            r"(?P<dst>.+?)(?:[,，])?(?:总会计|首席|董事|秘书|总裁|职务|职位|电话|联系|传真|负责人职位|地址)",
                            r"信息披露(事务)?(负责|联络|联系)人(姓名[/]职位|姓名|信息披露事务负责人|经办人员|联系人|/)*[:：]?(?P<dst>.+?)"
                            r"(?:[,，])?(?:总会计|首席|董事|秘书|总裁|职务|职位|电话|联系|传真|负责人职位|地址)",
                            r"信息披露(事务)?(负责|联络|联系)人(姓名[/]职位|姓名|信息披露事务负责人|经办人员|联系人|/)*[:：]?(?P<dst>.+)",
                            r"姓名[:：](?P<dst>.+)",
                        ],
                        "neglect_patterns": [
                            r"和联系方式.?$",
                            r"信息披露(事务)?(负责|联络|联系)人联系方式",
                            r"(传真|负责人职位|职务)",
                        ],
                    },
                    "传真号码": {"regs": [r"传真(号码)?[:：]?.*?(?P<dst>[-\d]+)$"]},
                    "电子邮箱": {"regs": [r"电子[邮信]箱[:：]?(?P<dst>.+)"]},
                    "电话号码": {
                        "regs": [
                            r"信息披露(事务)?(负责|联络|联系)人及其职位与联系方式(姓名)?[:：]?.*?(?P<dst>[-\d]{4,})(?![号路])",
                            r"(电话|联系方式)(号码)?以?及?(?:传真(号码)?)?[:：]?(?P<dst>[-\d]{4,})(?![号路])",
                        ]
                    },
                    "电话区号": {
                        "regs": [
                            r"信息披露(事务)?(负责|联络|联系)人及其职位与联系方式(姓名)?[:：]?.*?(?P<dst>[\d]+)\-",
                            r"(电话|联系方式)(号码)?[:：]?(?P<dst>\d+)",
                            r"(电话|联系方式)(号码)?以?及?(?:传真(号码)?)?[:：]?(?P<dst>[\d]+)",
                        ]
                    },
                },
            },
            {
                "name": "elements_collector_based",
                "elements_collect_model": "middle_paras",
                "elements_collect_config": {
                    "table_regarded_as_paras": True,
                    "use_syllabus_model": True,
                    "include_title": True,
                    "syllabus_level": 2,
                    "min_level": 2,
                    "inject_syllabus_features": issuer_basic_pattern,
                    "only_inject_features": True,
                    "ignore_syllabus_children": True,
                    "top_default": True,
                    "top_anchor_regs": [
                        r"发行人",
                    ],
                    "bottom_default": True,
                    "include_bottom_anchor": True,
                    "neglect_bottom_anchor": [
                        r"[公司发行人基本]{2,}(信息|情况|概况|资料|概述)",
                    ],
                    "keywords": [r"信息披露(事务)?(负责|联络|联系)人"],
                },
                "paragraph_model": "partial_text",
                "para_config": {
                    "multi_elements": True,
                    "column_from_multi_elements": False,
                    "use_answer_pattern": False,
                    "model_alternative": True,
                    "专员": {
                        "column_from_multi_elements": True,
                        "split_pattern": r"[、]",
                        "regs": [
                            r"信息披露(事务)?(负责|联络|联系)人及其职位与联系方式(姓名[/]职位|姓名|信息披露事务负责人|经办人员|联系人|/)*"
                            r"[:：]?(?P<dst>.+?)[;；/（（]",
                            r"信息披露(事务)?(负责|联络|联系)人及其职位与联系方式(姓名[/]职位|姓名|信息披露事务负责人|经办人员|联系人|/)*"
                            r"[:：]?(?P<dst>.+?)(?:[,，])?(?:总会计|首席|董事|秘书|总裁|职务|职位|电话|联系|传真|负责人职位|地址)",
                            r"信息披露(事务)?(负责|联络|联系)人(姓名[/]职位|姓名|信息披露事务负责人|经办人员|联系人|/)*[:：]?(?P<dst>.+?)"
                            r"(?:[,，])?(?:总会计|首席|董事|秘书|总裁|职务|职位|电话|联系|传真|负责人职位|地址)",
                            r"信息披露(事务)?(负责|联络|联系)人(姓名[/]职位|姓名|信息披露事务负责人|经办人员|联系人|/)*[:：]?(?P<dst>.+)",
                            r"姓名[:：](?P<dst>.+)",
                        ],
                        "neglect_patterns": [
                            r"和联系方式.?$",
                            r"(传真|负责人职位|职务)",
                            r"信息披露(事务)?(负责|联络|联系)人联系方式",
                        ],
                    },
                    "传真号码": {"regs": [r"传真(号码)?[:：]?.*?(?P<dst>[-\d]+)$"]},
                    "电子邮箱": {"regs": [r"电子[邮信]箱[:：]?(?P<dst>.+)"]},
                    "电话号码": {
                        "regs": [
                            r"信息披露(事务)?(负责|联络|联系)人及其职位与联系方式(姓名)?[:：]?.*?(?P<dst>[-\d]{4,})(?![号路])",
                            r"(电话|联系方式)(号码)?以?及?(?:传真(号码)?)?[:：]?(?P<dst>[-\d]{4,})(?![号路])",
                        ]
                    },
                    "电话区号": {
                        "regs": [
                            r"信息披露(事务)?(负责|联络|联系)人及其职位与联系方式(姓名)?[:：]?.*?(?P<dst>[\d]+)\-",
                            r"(电话|联系方式)(号码)?[:：]?(?P<dst>\d+)",
                            r"(电话|联系方式)(号码)?以?及?(?:传真(号码)?)?[:：]?(?P<dst>[\d]+)",
                        ]
                    },
                },
            },
            {
                "name": "table_kv",
            },
        ],
    },
    {
        "path": ["SZSE募集资金用途"],
        "models": use_of_funds,
    },
    {
        "path": ["CISP募集资金用途"],
        "models": use_of_funds,
    },
    {
        "path": ["募集资金用途备注"],
        "models": use_of_funds,
    },
    {
        "path": ["评级签字人"],
        "models": [
            {
                "name": "elements_collector_based",
                "elements_collect_model": "middle_paras",
                "elements_collect_config": {
                    "table_regarded_as_paras": True,
                    "use_syllabus_model": True,
                    "inject_syllabus_features": issue_related_institution,
                    "only_inject_features": True,
                    "ignore_syllabus_children": True,
                    "include_top_anchor": False,
                    "top_anchor_regs": [
                        r"评级机构",
                    ],
                    "bottom_anchor_regs": [P_SERIAL.pattern],
                },
                "paragraph_model": "partial_text",
                "para_config": {
                    "multi_elements": True,
                    "multi": True,
                    "use_answer_pattern": False,
                    "split_pattern": r"[、]",
                    "regs": [
                        r"(联系|负责|评级)人员?[:：](?P<dst>.+)",
                    ],
                    "model_alternative": True,
                },
            },
            {
                "name": "table_kv",
            },
        ],
    },
    {
        "path": ["债券选择权条款"],
        "models": [
            {
                "name": "elements_collector_based",
                "elements_collect_model": "middle_paras",
                "elements_collect_config": {
                    "multi_blocks": True,
                    "use_syllabus_model": True,
                    "inject_syllabus_features": [
                        "__regex__发行[概况条款]{2}__regex__.*?债券的?特殊发行条款",
                        *P_BASE_TITLE,
                    ],
                    "multi": True,
                    "multi_level": True,
                    "include_title": True,
                    "top_anchor_regs": [
                        rf"(?:^|{P_SERIAL.pattern})(发行人|投资者)?"
                        r"((?:调整)?票面利率(?:调整)?选择权(?:条款)?|票面利率调整机制|回售(选择)?权(?:条款)?|赎回("
                        r"选择)?权(?:条款)?|债券利率[及或其]*(确定方式|定价流程|、)+|偿付顺序|回售登记期|品种间回拨选择权(?:条款)?"
                        r"|强制付息事件|续期选择权(?:条款)?|递延支付利息((?:选择)?权(?:条款)?|条款)|强制付息事件|利息递延下?的限制(事项)?)"
                        r"(?:[:：]|$)",
                    ],
                    "bottom_anchor_regs": [
                        P_DETAIL_NAME,
                    ],
                    "include_bottom_anchor": False,
                    "bottom_default": True,
                },
                "paragraph_model": "partial_text",
                "para_config": {
                    "use_answer_pattern": False,
                    "regs": [
                        rf"(?:^|{P_SERIAL.pattern})(发行人)?"
                        r"((?:调整)?票面利率(?:调整)?选择权(?:条款)?|票面利率调整机制|投资者回售(选择)?权|赎回("
                        r"选择)?权(?:条款)?|强制付息事件|续期选择权(?:条款)?|递延支付利息(权|条款)|强制付息事件|利息递延下?的限制(事项)?)"
                        r"(?:[:：].*|$)",
                        ".*",
                    ],
                    "multi_elements": True,
                },
            }
        ],
    },
    {
        "path": ["票面利率选择权"],
        "models": [
            {  # 特殊发行条款
                "name": "elements_collector_based",
                "elements_collect_model": "middle_paras",
                "elements_collect_config": {
                    "use_syllabus_model": True,
                    "inject_syllabus_features": ["__regex__发行[概况条款]{2}__regex__.*?债券的?特殊发行条款"],
                    "only_inject_features": True,
                    "multi": True,
                    "multi_level": True,
                    "include_title": True,
                    "top_anchor_regs": [
                        r"(?:调整)?(?:票面利率(?:调整)?选择权(?:条款)?|票面利率调整机制)[:：]",
                        rf"({P_SERIAL.pattern})(?:调整)?(?:票面利率(?:调整)?选择权(?:条款)?|票面利率调整机制)",
                        r"发行人(?:(?:调整)?票面利率(?:调整)?选择权(?:条款)?|票面利率调整机制)[:：]",
                        rf"({P_SERIAL.pattern})发行人(?:(?:调整)?票面利率(?:调整)?选择权(?:条款)?|票面利率调整机制)",
                    ],
                    "bottom_anchor_regs": [
                        P_DETAIL_NAME,
                    ],
                    "include_bottom_anchor": False,
                    "bottom_default": True,
                },
                "paragraph_model": "partial_text",
                "para_config": {
                    "use_answer_pattern": False,
                    "neglect_patterns": [
                        r"选择权(?:条款)?[:：]?$",
                    ],
                    "regs": [r"(?<!按照以下方式确定)(?<!按以下方式确定)[:：](?P<dst>.*)", ".*"],
                    "multi_elements": True,
                },
            },
            {
                "name": "elements_collector_based",
                "elements_collect_model": "middle_paras",
                "elements_collect_config": {
                    "use_syllabus_model": True,
                    "inject_syllabus_features": [
                        "__regex__发行[概况条款]{2}__regex__.*?债券的?特殊发行条款",
                        *P_BASE_TITLE,
                    ],
                    "multi": True,
                    "multi_level": True,
                    "include_title": True,
                    "top_anchor_regs": [
                        r"(?:调整)?(?:票面利率(?:调整)?选择权(?:条款)?|票面利率调整机制)[:：]",
                        rf"({P_SERIAL.pattern})(?:调整)?(?:票面利率(?:调整)?选择权(?:条款)?|票面利率调整机制)",
                        r"发行人(?:(?:调整)?票面利率(?:调整)?选择权(?:条款)?|票面利率调整机制)[:：]",
                        rf"({P_SERIAL.pattern})发行人(?:(?:调整)?票面利率(?:调整)?选择权(?:条款)?|票面利率调整机制)",
                    ],
                    "bottom_anchor_regs": [
                        P_DETAIL_NAME,
                    ],
                    "include_bottom_anchor": False,
                    "bottom_default": True,
                },
                "paragraph_model": "partial_text",
                "para_config": {
                    "use_answer_pattern": False,
                    "neglect_patterns": [
                        r"选择权(?:条款)?[:：]?$",
                    ],
                    "regs": [r"(?<!按照以下方式确定)(?<!按以下方式确定)[:：](?P<dst>.*)", ".*"],
                    "multi_elements": True,
                },
            },
        ],
    },
    {
        "path": ["赎回债券选择权"],
        "models": [
            {  # 特殊发行条款
                "name": "elements_collector_based",
                "elements_collect_model": "middle_paras",
                "elements_collect_config": {
                    "use_syllabus_model": True,
                    "inject_syllabus_features": ["__regex__发行[概况条款]{2}__regex__.*?债券的?特殊发行条款"],
                    "only_inject_features": True,
                    "multi": True,
                    "multi_level": True,
                    "include_title": True,
                    "top_anchor_regs": [
                        r"赎回选择权(?:条款)?[:：]",
                        rf"({P_SERIAL.pattern})赎回选择权(?:条款)?",
                        r"发行人赎回选择权(?:条款)?[:：]",
                        rf"({P_SERIAL.pattern})发行人赎回选择权(?:条款)?",
                    ],
                    "bottom_anchor_regs": [
                        r"^.{,20}(?<!按照以下方式确定)(?<!按以下方式确定)[:：]",
                        P_DETAIL_NAME,
                    ],
                    "include_bottom_anchor": False,
                    "bottom_default": True,
                },
                "paragraph_model": "partial_text",
                "para_config": {
                    "use_answer_pattern": False,
                    "neglect_patterns": [
                        r"选择权(?:条款)?[:：]?$",
                    ],
                    "regs": [r"[:：](?P<dst>.*)", ".*"],
                    "multi_elements": True,
                },
            },
            {
                "name": "elements_collector_based",
                "elements_collect_model": "middle_paras",
                "elements_collect_config": {
                    "use_syllabus_model": True,
                    "inject_syllabus_features": [
                        "__regex__发行[概况条款]{2}__regex__.*?债券的?特殊发行条款",
                        *P_BASE_TITLE,
                    ],
                    "multi": True,
                    "multi_level": True,
                    "include_title": True,
                    "top_anchor_regs": [
                        r"赎回选择权(?:条款)?[:：]",
                        rf"({P_SERIAL.pattern})赎回选择权(?:条款)?",
                        r"发行人赎回选择权(?:条款)?[:：]",
                        rf"({P_SERIAL.pattern})发行人赎回选择权(?:条款)?",
                    ],
                    "bottom_anchor_regs": [
                        r"^.{,20}(?<!按照以下方式确定)(?<!按以下方式确定)[:：]",
                        P_DETAIL_NAME,
                    ],
                    "include_bottom_anchor": False,
                    "bottom_default": True,
                },
                "paragraph_model": "partial_text",
                "para_config": {
                    "use_answer_pattern": False,
                    "neglect_patterns": [
                        r"选择权(?:条款)?[:：]?$",
                    ],
                    "regs": [r"[:：](?P<dst>.*)", ".*"],
                    "multi_elements": True,
                },
            },
        ],
    },
    {
        "path": ["回售债券选择权"],
        "models": [
            {  # 特殊发行条款
                "name": "elements_collector_based",
                "elements_collect_model": "middle_paras",
                "elements_collect_config": {
                    "use_syllabus_model": True,
                    "inject_syllabus_features": ["__regex__发行[概况条款]{2}__regex__.*?债券的?特殊发行条款"],
                    "only_inject_features": True,
                    "include_title": True,
                    "top_anchor_regs": [
                        r"(投资者|发行人)?回售(债券)?选择权(?:条款)?[:：]",
                        rf"({P_SERIAL.pattern})(投资者|发行人)?回售债券选择权(?:条款)?",
                        rf"({P_SERIAL.pattern})(投资者|发行人)?回售选择权(?:条款)?",
                    ],
                    "bottom_anchor_regs": [
                        P_DETAIL_NAME,
                    ],
                    "include_bottom_anchor": False,
                    "bottom_default": True,
                },
                "paragraph_model": "partial_text",
                "para_config": {
                    "use_answer_pattern": False,
                    "neglect_patterns": [
                        r"选择权(?:条款)?[:：]?$",
                    ],
                    "regs": [r"[:：](?P<dst>.*)", ".*"],
                    "multi_elements": True,
                },
            },
            {
                "name": "elements_collector_based",
                "elements_collect_model": "middle_paras",
                "elements_collect_config": {
                    "use_syllabus_model": True,
                    "inject_syllabus_features": [
                        "__regex__发行[概况条款]{2}__regex__.*?债券的?特殊发行条款",
                        *P_BASE_TITLE,
                    ],
                    "include_title": True,
                    "top_anchor_regs": [
                        r"(投资者|发行人)?回售(债券)?选择权(?:条款)?[:：]",
                        rf"({P_SERIAL.pattern})(投资者|发行人)?回售债券选择权(?:条款)?",
                        rf"({P_SERIAL.pattern})(投资者|发行人)?回售选择权(?:条款)?",
                    ],
                    "bottom_anchor_regs": [
                        P_DETAIL_NAME,
                    ],
                    "include_bottom_anchor": False,
                    "bottom_default": True,
                },
                "paragraph_model": "partial_text",
                "para_config": {
                    "use_answer_pattern": False,
                    "neglect_patterns": [
                        r"选择权(?:条款)?[:：]?$",
                    ],
                    "regs": [r"[:：](?P<dst>.*)", ".*"],
                    "multi_elements": True,
                },
            },
        ],
    },
    {
        "path": ["债券期限详情"],
        "sub_primary_key": ["债券品种", "债券简称", "期限A"],
        "models": [
            {
                "name": "bond_period",
                "multi_elements": True,
                "column_from_multi_elements": False,
                "multi": True,
                "neglect_syllabus_regs": [r"前次公司债券募集资金使用情况"],
                "merge_char_result": False,
                "use_answer_pattern": False,
                "债券简称": {
                    "regs": [
                        r"品种[一二三四五六七八九]简称为?[:：“]*(?P<dst>.*?)[;；。，,”]",
                        r"债券([(（]?(品种|第)[一二三四五六七八九]期?[）)]?)?[;；。，,”]*简称为?[:：“]*(?P<dst>.*?)[;；。，,”]",
                        r"品种[一二三四五六七八九]全称[^;；。，,]+[;；。，,](?:债券)?简称为?[:：“]*(?P<dst>.*?)[;；。，,”]",
                    ],
                },
                "债券品种": {
                    "regs": p_bond_variety,
                },
                "债券期限含权情况": {
                    "regs": [
                        r"附.*权",
                        r"有权",
                    ],
                },
                "SZSE债券期限（单位）": {
                    "regs": [
                        r"(债券|品种[一二三四五六七八九])的?(基础)?(期限)?[:：为](?P<dst>\d+[年月日天])期?",
                        r"(债券|品种[一二三四五六七八九])以每(?P<dst>\d+个计息年度)为一个周期",
                        r"(债券|品种[一二三四五六七八九])不超过(?P<dst>\d+年)",
                        r"(可转债|债券|品种[一二三四五六七八九])期限为发行之日起(?P<dst>\d+年)",
                    ],
                    "model_alternative": True,
                },
                "期限A": {
                    "regs": [
                        r"(债券|品种[一二三四五六七八九])的?(基础)?(期限)?[:：为](?P<dst>\d+)[年月日天]期?",
                        r"(债券|品种[一二三四五六七八九])以每(?P<dst>\d+)个计息年度为一个周期",
                        r"(债券|品种[一二三四五六七八九])不超过(?P<dst>\d+)年",
                        r"(可转债|债券|品种[一二三四五六七八九])期限为发行之日起(?P<dst>\d+)年",
                        r"本次债券期限不超过(?P<dst>\d+)年",
                    ],
                    "model_alternative": True,
                },
                "期限B": {
                    "regs": [
                        r"附第(?P<dst>\d+)年末",
                        r"第(?P<dst>\d+)年末附",
                        r"(?:有权|选择权)[^，,。；;]+第(?P<dst>\d+)年末",
                        r"第(?P<dst>\d+)年末[^，,。；;]+有权",
                    ],
                    "model_alternative": True,
                },
            }
        ],
    },
    {
        "path": ["特殊权利条款-提前偿还"],
        "models": [
            {
                "name": "partial_text",
            },
        ],
    },
    {
        "path": ["特殊权利条款-累进利率"],
        "models": [
            {
                "name": "partial_text",
            },
        ],
    },
    {
        "path": ["发行人续期选择权"],
        "models": [
            {
                "name": "partial_text",
            },
        ],
    },
    {
        "path": ["增信担保具体条款"],
        "models": [
            {
                "name": "partial_text",
                "regs": [
                    r"本[期次]债券为无担保债券",
                    r"本[期次]债券无担保",
                    r"本[期次]债券无信用增进安排",
                    r"本[期次]债券采取无担保方式发行",
                    r"本[期次]发行公司债券无担保",
                    r"本.债券由.*提供.*担保",
                    r"本[期次]债券未安排增信",
                    r"本[期次]债券无增信安排",
                    r"担保情况及其他增信措施：(?P<dst>.+)",
                    r"本[期次]债券.*增信措施",
                    r"^无",
                ],
                "model_alternative": True,
            },
            {
                "name": "syllabus_elt_v2",
                "inject_syllabus_features": [r"增信机制"],
                "only_inject_features": True,
            },
        ],
    },
]

prophet_config = {"depends": {}, "predictor_options": predictor_options}
