"""
中信-募集书抽取-附加一
"""

from remarkable.common.diff.mixins import P_PUNCTUATION, P_SERIAL

issuer_basic_pattern = [
    r"__regex__(发行人|本期发行的)(基本)?情况__regex__[公司发行人基本]{2,}(信息|情况|概况|资料|概述)",
]

issuer_survey_pattern = [
    r"__regex__发行概况__regex__(公司|发行人|本[期次][债券发行]{2,})的?((基本|简要)情况|简介)",
]

issue_related_institution = [
    r"__regex__(本期债券)?发行的?[有相]关机构$",
    r"与本期发行有关的当事人",
]

predictor_options = [
    {
        "path": ["发行公告日"],
        "models": [
            {
                "name": "partial_text",
                "neglect_patterns": [
                    r"发行首日",
                ],
            },
            {
                "name": "table_kv",
            },
            {
                "name": "table_row",
                "feature_from": "right_cells",
            },
        ],
    },
    {
        "path": ["承销方式"],
        "models": [
            {
                "name": "partial_text",
            },
        ],
    },
    {
        "path": ["CISP发行方式"],
        "models": [
            {
                "name": "partial_text",
                "regs": [
                    r"向符合.*规定的专业(机构)?投资者公开发行",
                    r"面向专业(机构)?投资者公开发行",
                ],
                "neglect_patterns": [
                    r"根据网下向专业投资者的簿记",
                ],
                "model_alternative": True,
            },
        ],
    },
    {
        "path": ["SZSE发行方式"],
        "models": [
            {
                "name": "partial_text",
            },
        ],
    },
    {
        "path": ["本金偿还方式"],
        "models": [
            {
                "name": "partial_text",
                "regs": [r"(本期债券按年付息|每年付息一次).(?P<dst>到期一次还本)"],
                "model_alternative": True,
            },
        ],
    },
    {
        "path": ["SZSE还本方式"],
        "models": [
            {
                "name": "partial_text",
            },
        ],
    },
    {
        "path": ["发行人评级机构"],
        "models": [
            {
                "name": "partial_text",
                "use_answer_pattern": False,
                "regs": [
                    r"信用评级机构及信用评级结果.经(?P<dst>.*?(?:公司)?)(?:综合)?评定",
                    r"经(?P<dst>.*?(?:公司)?)(?:综合)?评定.*?(?:本?公司|发行人)的?"
                    r"(?:长期)?(?:主体)?(?:长期)?(?:信用(?:等级|评级)|信?用?评级结果)(?:是|为)",
                    r"(?:根据|依据)?(?P<dst>[^,，。；]*?(?:公司)?)(?:为(?:本?公司|发行人)的?本.发行)?出具[^,，；。，]*?"
                    r"评级.*主体(?:长期)?信用(?:等级|评级)(?:是|为)",
                ],
            },
        ],
    },
    {
        "path": ["债券评级机构"],
        "models": [
            {
                "name": "partial_text",
                "use_answer_pattern": False,
            },
        ],
    },
    {
        "path": ["利率类型"],  # 忽略
        "models": [
            {
                "name": "partial_text",
            },
        ],
    },
    {
        "path": ["担保机构全称"],
        "models": [
            {
                "name": "partial_text",
                "use_answer_pattern": False,
                "neglect_syllabus_regs": [
                    r"(控股股东|公司|受托管理人|发行人)基本情况",
                    r"(公司|发行人)(基本)?(信息|情况|概况|资料|概述)",
                ],
                "regs": [
                    r"公司名称[:：]",
                    r"由(?P<dst>.*)提供连带责任保证担保",
                ],
            },
        ],
    },
    {
        "path": ["SZSE期数"],
        "models": [
            {
                "name": "partial_text",
            },
        ],
    },
    {
        "path": ["受托管理人传真"],
        "models": [
            {
                "name": "elements_collector_based",
                "elements_collect_model": "middle_paras",
                "elements_collect_config": {
                    "use_syllabus_model": True,
                    "inject_syllabus_features": [
                        *issue_related_institution,
                        r"__regex__债券受托管理人$__regex__债券受托管理人$",
                    ],
                    "only_inject_features": True,
                    "ignore_syllabus_children": True,
                    "include_bottom_anchor": True,
                    "top_anchor_regs": [
                        r"受托管理人",
                    ],
                    "bottom_anchor_regs": [
                        r"传真",
                    ],
                    "table_regarded_as_paras": True,
                },
                "paragraph_model": "partial_text",
                "para_config": {
                    "regs": [r"传真[号码]*[:：](?P<dst>.+)"],
                },
            },
            {
                "name": "table_kv",
            },
            # {
            #     'name': 'partial_text',
            #     'regs': [r'传真[号码]*[:：](?P<dst>.+)'],
            # }
        ],
    },
    {
        "path": ["SZSE利率形式"],  # 忽略
        "models": [
            {
                "name": "partial_text",
            },
        ],
    },
    {
        "path": ["债券形式"],
        "models": [
            {
                "name": "partial_text",
            },
        ],
    },
    {
        "path": ["计划发行金额"],
        "models": [
            {
                "name": "partial_text",
                "use_answer_pattern": False,
                "regs": [r"本期债券(发行)?(规模|金额)为?不超过(人民币)?(?P<dst>[\d.]+?)亿元"],
                "model_alternative": True,
            },
        ],
    },
    {
        "path": ["发行价格"],
        "models": [
            {
                "name": "partial_text",
                "use_answer_pattern": False,
            },
        ],
    },
    {
        "path": ["派息周期"],
        "models": [
            {
                "name": "partial_text",
            },
        ],
    },
    {
        "path": ["主营业务"],
        "models": [
            {
                "name": "middle_paras",
                "use_syllabus_model": True,
                "syllabus_level": 2,
                "min_level": 2,
                "inject_syllabus_features": issuer_basic_pattern,
                "only_inject_features": True,
                "ignore_syllabus_children": True,
                "max_syllabus_range": 100,
                "include_top_anchor": False,
                "top_anchor_regs": [
                    r"^经营范围[:：]$",
                ],
                "bottom_anchor_regs": [P_SERIAL.pattern],
            },
            {
                "name": "syllabus_based",
                "syllabus_level": 2,
                "min_level": 2,
                "inject_syllabus_features": issuer_basic_pattern,
                "only_inject_features": True,
                "ignore_syllabus_children": True,
                "max_syllabus_range": 100,
                "paragraph_model": "para_match",
                "para_config": {
                    "paragraph_pattern": r"(主营业务|经营范围)[:：](?P<content>.+)",
                    "content_pattern": r"(主营业务|经营范围)[:：](?P<content>.+)",
                },
                "table_model": "table_kv",
                "table_config": {},
            },
            {
                "name": "partial_text",
                "use_answer_pattern": False,
            },
        ],
    },
    {
        "path": ["实际控制人"],
        "models": [
            {
                "name": "partial_text",
                "use_answer_pattern": False,
                "regs": [
                    r"(?:实际控制人|控股股东)名称[:：](?P<dst>.*)",
                    r"(?:签署之日，)?(?P<dst>[^,，;；。]*)[为是系](?:公司|发行人)的?[^，，;；。]*实际控制人",
                    r"(?P<dst>.*)持有发行人100%的股权，是(?:发行人|公司)的?控股股东兼实际控制人",
                    rf"({P_PUNCTUATION.pattern})(?P<dst>.*(?:有限公司|办公室)).*发行人控股股东.实际控制人",
                    r"(?P<dst>[^，，;；。]*)[为是系][^，，;；。]*实际控制人",
                    rf"(?:发行人|公司|[，，;；。])的?(?:(?:控股股东|实际控制人)+及?)+均?[是为](?P<dst>[^，，;；。]*?)({P_PUNCTUATION.pattern})",
                    r"(?P<dst>[^，，;；。]+)直接持有公司.*?股权.为控股股东及实际控制人",
                ],
                "model_alternative": True,
            },
        ],
    },
    {
        "path": ["SZSE评级展望"],
        "models": [
            {
                "name": "partial_text",
                "regs": [r"评级展望为(?P<dst>(正面|稳定|负面))"],
                "model_alternative": True,
            },
        ],
    },
    {
        "path": ["SSE评级展望"],
        "models": [
            {
                "name": "partial_text",
                "regs": [r"评级展望为(?P<dst>(正面|稳定|负面))"],
                "model_alternative": True,
            },
        ],
    },
    {
        "path": ["发行人最近三年平均可分配利润"],
        "models": [
            {
                "name": "partial_text",
                "use_answer_pattern": False,
            },
        ],
    },
    {
        "path": ["债券简称详情"],
        "models": [
            {
                "name": "bond_abbreviation",
                "max_syllabus_range": 100,
                "ignore_syllabus_children": True,
                "para_config": {
                    "债券简称": {
                        "regs": [r"债券简称为?[:：“]*(?P<dst>.*?)[;；。，,”]"],
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
        "path": ["发行人基本信息"],
        "models": [
            {
                "name": "elements_collector_based",
                "elements_collect_model": "middle_paras",
                "elements_collect_config": {
                    "table_regarded_as_paras": True,
                    "use_syllabus_model": True,
                    "include_title": True,
                    "inject_syllabus_features": issue_related_institution,
                    "only_inject_features": True,
                    "ignore_syllabus_children": True,
                    "top_anchor_regs": [
                        r"发行人",
                    ],
                    "bottom_anchor_regs": [
                        r"主承销商",
                        r"承销机构",
                    ],
                },
                "paragraph_model": "partial_text",
                "para_config": {
                    "multi_elements": True,
                    "column_from_multi_elements": False,
                    "发行人联系人": {
                        "regs": [r"(联系人|有关经办人员)[:：]?(?P<dst>.+)"],
                        "column_from_multi_elements": True,
                    },
                    "发行人固定电话": {
                        "regs": [r"电话(号码)?[:：]?(?P<dst>.+)"],
                    },
                    "发行人联系手机号码": {
                        "regs": [r"(联系方式|手机号码|电话)[:：]?(?P<dst>1\d{10})"],
                    },
                    "发行人电子邮箱": {
                        "regs": [r"电子[邮信]箱?[:：]?(?P<dst>.+)"],
                    },
                },
            },
            {
                "name": "table_kv",
            },
        ],
    },
    {
        "path": ["法定代表人"],
        "models": [
            {
                "name": "syllabus_based",
                "syllabus_level": 2,
                "min_level": 2,
                "inject_syllabus_features": issuer_basic_pattern,
                "only_inject_features": True,
                "ignore_syllabus_children": True,
                "max_syllabus_range": 100,
                "multi_elements": False,
                "paragraph_model": "partial_text",
                "para_config": {
                    "use_answer_pattern": False,
                    "regs": [r"法人代表[:：](?P<dst>.+)"],
                    "model_alternative": True,
                },
                "table_model": "table_kv",
                "table_config": {},
            },
            {
                "name": "syllabus_based",
                "syllabus_level": 2,
                "min_level": 2,
                "inject_syllabus_features": issuer_survey_pattern,
                "only_inject_features": True,
                "ignore_syllabus_children": True,
                "max_syllabus_range": 100,
                "multi_elements": False,
                "paragraph_model": "partial_text",
                "para_config": {
                    "use_answer_pattern": False,
                },
                "table_model": "table_kv",
                "table_config": {},
            },
            {
                "name": "partial_text",
                "use_answer_pattern": False,
            },
        ],
    },
    {
        "path": ["所属行业"],
        "models": [
            {
                "name": "partial_text",
                "use_answer_pattern": False,
                "multi": True,
                "multi_elements": True,
            },
            {
                "name": "table_kv",
            },
        ],
    },
    {
        "path": ["主承销商详情"],
        "sub_primary_key": ["主承销商"],
        "group": {
            "sources": ["element", "context_elements", "syllabuses"],
            "lookup_strategy": "lookahead",
            "range_num": 10,
        },
        "models": [
            {
                "name": "consignee_info_detail",
                "inject_syllabus_features": issue_related_institution,
                "only_inject_features": True,
                "ignore_syllabus_children": True,
                "max_syllabus_range": 200,
                "table_regarded_as_paras": True,
                "paragraph_model": "partial_text",
                "para_config": {
                    "multi_elements": True,
                    "column_from_multi_elements": False,
                    "use_answer_pattern": False,
                    "主承销商": {
                        "regs": [
                            r"(?P<dst>(牵头|联席)?(主承销(?:商|机构)+|承销机构)(?:(?!以?及其他承销机构).)*)$",
                        ],
                        "neglect_patterns": [
                            r"副主承销(?:商|机构)+",
                            r"风险提示|厉害关系|备查文件|查阅地点",
                            r"分销商[:：]",
                            r"收款银行",
                        ],
                    },
                    "主承销商经办人": {
                        "column_from_multi_elements": True,
                        "regs": [r"(项目组?)?(联系|负责|经办|协办|其他|项目组)[成人员]+([/]联系人)?[:：]?(?P<dst>.+)"],
                        "split_pattern": r"[、]",
                    },
                    "主承销商经办人电话区号": {
                        "regs": [r"(联系)?电话(号码)?[:：]?(?P<dst>\d+)[-]"],
                    },
                    "主承销商经办人电话号码": {
                        "regs": [r"(联系)?电话(号码)?[:：]?(?P<dst>.+)"],
                    },
                    "主承销商经办人传真号码": {
                        "regs": [r"传真(号码)?[:：]?(?P<dst>.+)"],
                    },
                    "经办人手机号码": {
                        "regs": [r"(联系方式|手机|电话)(号码)?[:：]?(?P<dst>1\d{10})"],
                    },
                    "经办人电子邮箱": {
                        "regs": [r"电子[邮信]箱?[:：]?(?P<dst>.+)"],
                    },
                },
                # 'table_model': 'table_kv',
                # 'table_config': {
                #     'multi': True,
                #     '主承销商经办人': {
                #         'split_pattern': r'[、]',
                #     },
                #     '主承销商经办人电话区号': {
                #         'regs': [r'(?P<dst>\d+)[-]'],
                #     },
                #     '主承销商经办人电话号码': {
                #         'regs': [r'(?P<dst>.+)'],
                #     },
                #     '主承销商经办人传真号码': {
                #         'regs': [r'(?P<dst>.+)'],
                #     },
                # },
            },
        ],
    },
    {
        "path": ["会计师事务所"],
        "sub_primary_key": ["名称"],
        "group": {
            "sources": ["element", "context_elements", "syllabuses"],
            "lookup_strategy": "lookahead",
            "range_num": 10,
        },
        "models": [
            {
                "name": "elements_collector_based",
                "elements_collect_model": "middle_paras",
                "active_model": {"match_all_fields": True},
                "elements_collect_config": {
                    "multi_blocks": True,
                    "use_syllabus_model": True,
                    "inject_syllabus_features": [r"__regex__[相有]关人员声明$"],
                    "only_inject_features": True,
                    "ignore_syllabus_children": True,
                    "table_regarded_as_paras": True,
                    "cell_separator": "、",
                    "top_anchor_regs": [
                        r"(经办|签字|注册)?会计师(?:.签[字名].)?[:：]",
                        r"经办人员?(?:.签[字名].)?[:：]",
                    ],
                    "top_anchor_range_regs": [
                        r"(?:会计师(?:事务所)?|审计机构)声明$",
                    ],
                    "bottom_anchor_range_regs": [
                        r".{,4}\s*年.{,2}\s*月.{,2}\s*日\s*$",
                        r"声明$",
                        r"会计师事务所([（(]特殊普通合伙[）)])?$",
                    ],
                    "bottom_anchor_regs": [
                        P_SERIAL.pattern,
                        r"会计师事务所([（(]特殊普通合伙[）)])?$",
                        r".{,4}\s*年.{,2}\s*月.{,2}\s*日\s*$",
                        r"声明$",
                    ],
                    "top_anchor_ignore_regs": [
                        r"项目组成员(?:.签[字名].)?[:：]?",
                        r"法定代表人?(?:.签[字名].)?[:：]?",
                        r"(负责|联系)人(?:.签[字名].)?[:：]?",
                    ],
                    "bottom_anchor_ignore_regs": [
                        r"(经办|签字|注册)?律师(?:.签[字名].)?[:：]?",
                        r"经办人员?(?:.签[字名].)?[:：]?",
                        r"项目组成员(?:.签[字名].)?[:：]?",
                        r"法定代表人?(?:.签[字名].)?[:：]?",
                        r"(负责|联系)人(?:.签[字名].)?[:：]?",
                        r"会计师事务所$",
                        r".{,4}\s*年.{,2}\s*月.{,2}\s*日$",
                        r"声明$",
                    ],
                    "neglect_bottom_anchor": [r"[\d]+[室楼号]"],
                },
                "paragraph_model": "partial_text",
                "para_config": {
                    "multi_elements": True,
                    "名称": {
                        "column_from_multi_elements": False,
                        "regs": [
                            r"(审计机构|会计师事务所|名称|^\d)[:：、](?P<dst>.+会计师事务所([（(]特殊普通合伙[）)])?)",
                            r"(?P<dst>[^:：]+会计师事务所([（(]特殊普通合伙[）)])?)",
                        ],
                        "neglect_patterns": [
                            r"律师",
                            r"住所|地址",
                        ],
                    },
                    "签字会计师": {
                        "regs": [
                            r"(经办|签字|注册)?会计师(?:.签[字名].)?[:：]?(?P<dst>[^:：事]+)",
                            r"经办人员(?:.签[字名].)?[:：]?(?P<dst>[^:：]+)",
                            r"^\s*(?P<dst>[^:：]+)\s*$",
                        ],
                        "neglect_patterns": [
                            r"会计师事务所",
                            r"公司|说明|声明|附注|中国|北京|上海|深圳|【\s*】",
                            r"律师",
                            r"住所|地址",
                            r"^[一二三四五六七八九][、]会计师事务所.?$",
                        ],
                        "split_pattern": r"[、]",
                    },
                    "model_alternative": True,
                    "use_answer_pattern": False,
                },
            },
            {
                "name": "elements_collector_based",
                "elements_collect_model": "middle_paras",
                "elements_collect_config": {
                    "multi_blocks": True,
                    "use_syllabus_model": True,
                    "inject_syllabus_features": issue_related_institution,
                    "only_inject_features": True,
                    "ignore_syllabus_children": True,
                    "table_regarded_as_paras": True,
                    "top_anchor_regs": [
                        r"发行人会计师|会计师事务所",
                    ],
                    "neglect_top_anchor": [rf"({P_SERIAL.pattern})会计师事务所[:：]?$"],
                    "bottom_anchor_regs": [
                        P_SERIAL.pattern,
                        r"会计师事务所",
                    ],
                    "neglect_bottom_anchor": [r"[\d]+[室楼号]"],
                },
                "paragraph_model": "partial_text",
                "para_config": {
                    "multi_elements": True,
                    "名称": {
                        "column_from_multi_elements": False,
                        "regs": [
                            r"(审计机构|会计师事务所|名称|^\d)[:：、](?P<dst>[^:：]+会计师事务所([（(]特殊普通合伙[）)])?)",
                            r"(?P<dst>.+会计师事务所([（(]特殊普通合伙[）)])?)",
                        ],
                        "neglect_patterns": [
                            r"律师",
                            r"住所|地址",
                            r"^[一二三四五六七八九][、]会计师事务所.?$",
                        ],
                    },
                    "签字会计师": {
                        "regs": [
                            r"(经办|签字|注册)?会计师(?:.签[字名].)?[:：]?(?P<dst>[^:：事]+)",
                            r"(负责|联系)人(?:.签[字名].)?[:：]?(?P<dst>[^:：]+)",
                            r"经办人员(?:.签[字名].)?[:：]?(?P<dst>[^:：]+)",
                            r"项目组成员(?:.签[字名].)?[:：]?(?P<dst>[^:：]+)",
                            r"法定代表人?(?:.签[字名].)?[:：]?(?P<dst>[^:：]+)",
                        ],
                        "split_pattern": r"[、]",
                    },
                    "model_alternative": True,
                    "use_answer_pattern": False,
                },
            },
        ],
    },
    {
        "path": ["律师事务所", "名称"],
        "models": [
            {
                "name": "elements_collector_based",
                "elements_collect_model": "middle_paras",
                "elements_collect_config": {
                    "use_syllabus_model": True,
                    "table_regarded_as_paras": True,
                    "inject_syllabus_features": issue_related_institution,
                    "only_inject_features": True,
                    "ignore_syllabus_children": True,
                    "top_anchor_regs": [
                        r"发行人律师|律师事务所",
                    ],
                    "bottom_anchor_regs": [P_SERIAL.pattern],
                },
                "paragraph_model": "partial_text",
                "para_config": {
                    "use_answer_pattern": False,
                    "regs": [r"名称[:：]?(?P<dst>[^:：]+)"],
                    "model_alternative": True,
                },
            },
            {
                "name": "table_kv",
            },
        ],
    },
    {
        "path": ["律师事务所", "签字律师"],
        "models": [
            {
                "name": "elements_collector_based",
                "elements_collect_model": "middle_paras",
                "elements_collect_config": {
                    "multi_blocks": True,
                    "use_syllabus_model": True,
                    "inject_syllabus_features": [r"__regex__[有相关]人员声明"],
                    "only_inject_features": True,
                    "ignore_syllabus_children": True,
                    "table_regarded_as_paras": True,
                    "cell_separator": "、",
                    "top_anchor_regs": [
                        r"(经办|签字|注册)?律师(?:.签[字名].)?[:：]",
                    ],
                    "top_anchor_range_regs": [
                        r"律师(?:事务所)?声明$",
                    ],
                    "bottom_anchor_range_regs": [
                        r"律师事务所$",
                        r".{,4}\s*年.{,2}\s*月.{,2}\s*日$",
                        r"声明$",
                    ],
                    "top_anchor_ignore_regs": [
                        r"项目组成员(?:.签[字名].)?[:：]?",
                        r"法定代表人?(?:.签[字名].)?[:：]?",
                        r"(负责|联系)人(?:.签[字名].)?[:：]?",
                    ],
                    "bottom_anchor_ignore_regs": [
                        r"(经办|签字|注册)?律师(?:.签[字名].)?[:：]?",
                        r"经办人员?(?:.签[字名].)?[:：]?",
                        r"项目组成员(?:.签[字名].)?[:：]?",
                        r"法定代表人?(?:.签[字名].)?[:：]?",
                        r"(负责|联系)人(?:.签[字名].)?[:：]?",
                        r"律师事务所$",
                        r".{,4}\s*年.{,2}\s*月.{,2}\s*日$",
                        r"声明$",
                    ],
                    "bottom_anchor_regs": [
                        P_SERIAL.pattern,
                        r"律师事务所$",
                        r".{,4}\s*年.{,2}\s*月.{,2}\s*日$",
                        r"声明$",
                    ],
                },
                "paragraph_model": "partial_text",
                "para_config": {
                    "multi_elements": True,
                    "multi": True,
                    "use_answer_pattern": False,
                    "split_pattern": r"[、\s]+",
                    "regs": [
                        r"(经办|签字|注册)?律师(?:.签[字名].)?[:：]?(?P<dst>[^:：事]+)",
                        r"经办人员?(?:.签[字名].)?[:：]?(?P<dst>[^:：]+)",
                        r"^(?P<dst>[^:：]+)$",
                    ],
                    "neglect_patterns": [
                        r"[:：]$",
                        r"事务所|公司|说明|声明|附注|中国|北京|上海|深圳|【\s*】",
                        r"会计师",
                        r"住所|地址",
                        r"^[一二三四五六七八九][、]会计师事务所.?$",
                    ],
                    "model_alternative": True,
                },
            },
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
                        r"发行人律师|律师事务所",
                    ],
                    "bottom_anchor_regs": [P_SERIAL.pattern, "会计师事务所"],
                },
                "paragraph_model": "partial_text",
                "para_config": {
                    "multi_elements": True,
                    "multi": True,
                    "use_answer_pattern": False,
                    "split_pattern": r"[、]",
                    "regs": [
                        r"(联系|负责|经办)人员?([/]联系人)?(?:.签[字名].)?[:：]?(?P<dst>.+)",
                        r"律师(?:.签[字名].)?[:：]?(?P<dst>.+)",
                    ],
                    "neglect_patterns": [r"事务所"],
                    "model_alternative": True,
                },
            },
            {
                "name": "table_kv",
            },
        ],
    },
]

prophet_config = {"depends": {}, "predictor_options": predictor_options}
