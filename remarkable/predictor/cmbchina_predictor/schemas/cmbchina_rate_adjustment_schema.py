"""
费率调整公告
"""

from remarkable.predictor.cmbchina_predictor.schemas import (
    P_ABBR_EXIST_CODE,
    P_CODE_EXIST_ABBR,
    R_FUND_SHORT_NAME,
    R_INTERVAL_END,
    R_INTERVAL_START,
    get_predictor_options,
    p_fund_abbr,
    p_fund_code,
)
from remarkable.predictor.common_pattern import R_CONJUNCTION

R_FUND_SUFFIX = r"([(（]([LF]OF([-][LF]OF)?|QDII)[）)]|(发起式)?联接基金)"
R_ADJUST = r"(结束|开展|调[低整]|降低)"
R_DATE = r"\s*(?P<dst>\d{4}\s*[年/-]\s*\d{1,2}\s*[月/-]\s*\d{1,2}\s*[日])\s*"
R_SINCE = r"(自|于|从)"
R_NOTICE_LATER = r"另行(?:通知或)?公告|另行发布的公告"

ADJUSTED_SERVICE_CONFIG = {
    "use_top_crude_neighbor": False,
    "elements_in_page_range": [0],
    "top_default": True,
    "include_bottom_anchor": True,
    "bottom_anchor_regs": [
        r"销售服务费.*?公告$",
        r"根据《中华人民共和国证券投资基金法》",
        r"^为答谢",
        r"销售服务费.*(调整|恢复)",
    ],
    "keywords": [
        r"销售服务费",
    ],
}

ELEMENTS_NEARBY_FOR_SEGMENTED = {
    "neglect_regs": [
        r"公告基本信息",
        r"本次调低基金费率的相关安排",
    ],
    "amount": 1,
    "step": -1,
}

predictor_options = [
    {
        "path": ["调整后管理费率"],
        "sub_primary_key": ["管理费率", "基金名称"],
        "models": [
            {
                "name": "partial_text",
                "regs": {
                    "基金名称": [
                        r"(?P<dst>本基金)[^,，。;；]*管理费年?费?率?.?按.*?年费率计提",
                    ],
                    "管理费率": [
                        r"本基金[^,，。;；]*管理费年?费?率?.?按.*?(?P<dst>[\d.%％]+)年费率计提",
                    ],
                },
                "elements_nearby": {
                    "regs": [r"修订为[：:]"],
                    "amount": 1,
                    "step": -1,
                },
            },
            {
                "name": "partial_text",
                "regs": {
                    "基金名称": [
                        r"(?P<dst>本基金)[^,，。;；]*管理费年?费?率?.?由.*?.{2}[至为]",
                        r"起降低(?P<dst>.*?投资基金).*的?管理费",
                    ],
                    "管理费率": [
                        r"本基金[^,，。;；]*管理费年?费?率?.?由.*?.{2}[至为](?P<dst>[\d.%％]+)",
                        r"管理费年?率.?由.*?[至为](?P<dst>[\d.%％]+)",
                        r"调整后的?基金管理费[:：]年费率(?P<dst>[\d.%％]+)",
                    ],
                },
            },
            {
                "name": "subscription",
                "main_column": "基金名称",
                "multi_config": {
                    "基金名称": True,
                    "管理费率": False,
                },
                "regs": {
                    "基金名称": [
                        r"降低(?P<dst>.*及.*)的管理费率",
                    ],
                    "管理费率": [r"基金管理费率由.*?降低[至为](?P<dst>[\d.%％]+)"],
                },
                "基金名称": {
                    "split_pattern": r"[及]",
                },
            },
            {
                "name": "table_row",
                "neglect_title_patterns": [r"优惠", r"适用基金$"],
                "neglect_row_header_regs": [r"托管费率"],
                "neglect_patterns": [r"修订"],
                "neglect_row": [r"销售服务费"],
                "feature_white_list": {
                    "管理费率": [r"__regex__管理费率__regex__(调整|修订)后"],
                    "基金名称": [
                        "基金简称",
                    ],
                },
            },
            {
                "name": "cell_partial_text",
                "filter_by": "col",
                "header_pattern": [r"(调整|修订)后"],
                "from_cell": False,
                "regs": {
                    "基金名称": [],
                    "管理费率": [
                        r"本基金的管理费按.*资产净值的?(?P<dst>[\d.%％]+)年费率计提",
                    ],
                },
            },
        ],
    },
    {
        "path": ["调整后销售服务费率"],
        "sub_primary_key": ["基金名称", "销售服务费率"],
        "divide_answers": True,
        "models": [
            {
                "name": "elements_condition",
                "elements_condition_model": "middle_paras",
                "elements_condition_config": ADJUSTED_SERVICE_CONFIG,
                "elements_extract_model": "partial_text",
                "elements_extract_config": {
                    "merge_char_result": False,
                    "multi": True,
                    "regs": {
                        "基金名称": [
                            r"(?P<dst>嘉实中证细分化工产业主题指数型发起式证券投资基金)[(（]以下.*?管理费率及销售服务费率",
                        ],
                        "销售服务费率": [
                            # http://100.64.0.9:55842/scriber/#/project/remark/10424?projectId=43&treeId=62&fileId=1001&schemaId=8
                            r"销售服务费率由.*?降低至(?P<dst>[\d.%]+)",
                        ],
                    },
                },
            },
            {
                "name": "adjusted_rate",
                "elements_nearby": {
                    "neglect_regs": [
                        r"附件",
                    ],
                    "amount": 2,
                    "step": -1,
                },
                "feature_white_list": {
                    "基金名称": [r"__regex__基金(份额)?[简名]称"],
                    "销售服务费率": [
                        r"__regex__(?<!原)(?<!原优惠)销售服务费+",
                    ],
                },
                "feature_black_list": {
                    "基金名称": [r"修订后"],
                    "销售服务费率": [r"修订后"],
                },
                "regs": {
                    "基金名称": [],
                    "销售服务费率": [r"(?P<dst>[\d.%％]+)"],
                },
                "lazy_match": True,
                "parse_by": "col",
                "cell_regs": [r"(?P<dst>[\d.]+[%％]+)(/年)?", r"招商.*?证券投资基金[A-Z]"],
                "neglect_col_header_regs": [r"原优惠活动中销售服务费年费率|调整前"],
            },
            {
                "name": "adjusted_rate",
                "elements_nearby": {
                    "neglect_regs": [
                        r"附件",
                    ],
                    "amount": 2,
                    "step": -1,
                },
                "feature_white_list": {
                    "基金名称": [r"__regex__基金(份额)?[简名]称"],
                    "销售服务费率": [
                        r"__regex__(?<!原)(?<!原优惠)销售服务费+",
                    ],
                },
                "feature_black_list": {
                    "基金名称": [r"修订后"],
                    "销售服务费率": [r"修订后"],
                },
                "regs": {
                    "基金名称": [],
                    "销售服务费率": [r"(?P<dst>[\d.%％]+)"],
                },
                "lazy_match": True,
                "cell_regs": [r"(?P<dst>[\d.%％]+)(/年)?"],
                "neglect_col_header_regs": [r"原优惠活动中销售服务费年费率", "基金合同销售服务费率"],
            },
            {
                "name": "elements_condition",
                "elements_condition_model": "middle_paras",
                "elements_condition_config": ADJUSTED_SERVICE_CONFIG,
                "elements_extract_model": "cell_partial_text",
                "elements_extract_config": {
                    "from_cell": False,
                    "filter_by": "col",
                    "multi": True,
                    "merge_char_result": False,
                    "header_pattern": [
                        r"修订后",
                    ],
                    "regs": {
                        "基金名称": [
                            rf"销售服务费年费率为.*本基金\s*(?P<dst>{R_FUND_SHORT_NAME})的?销售服务费年费率为",
                            rf"[,，。;；](?P<dst>{R_FUND_SHORT_NAME})的?销售服务费年费率为",
                            rf"(?P<dst>{R_FUND_SHORT_NAME})(不收取)?销售服务费",
                            rf"(?P<dst>{R_FUND_SHORT_NAME})和{R_FUND_SHORT_NAME}不收取销售服务费",
                        ],
                        "销售服务费率": [
                            r"销售服务费年费率为(?P<dst>[\d.%]+)",
                            r"不收取销售服务费",
                        ],
                    },
                },
            },
            {
                "name": "elements_condition",
                "elements_condition_model": "middle_paras",
                "elements_condition_config": ADJUSTED_SERVICE_CONFIG,
                "elements_extract_model": "cell_partial_text",
                "elements_extract_config": {
                    "from_cell": False,
                    "multi": True,
                    "merge_char_result": False,
                    "regs": {
                        "基金名称": [
                            rf"销售服务费年费率为.*本基金\s*(?P<dst>{R_FUND_SHORT_NAME})的?销售服务费年费率为",
                            rf"[,，。;；](?P<dst>{R_FUND_SHORT_NAME})的?销售服务费年费率为",
                            rf"(?P<dst>{R_FUND_SHORT_NAME})不收取销售服务费",
                        ],
                        "销售服务费率": [
                            r"销售服务费年费率为(?P<dst>[\d.%]+)",
                            r"不收取销售服务费",
                        ],
                    },
                },
            },
            {
                "name": "elements_collector_based",
                "elements_collect_model": "middle_paras",
                "elements_collect_config": {
                    "use_top_crude_neighbor": False,
                    "elements_in_page_range": [0],
                    "top_default": True,
                    "include_bottom_anchor": True,
                    "ignore_pattern": [
                        r"公告$",
                        r"(方案|详情)如下[：:]$",
                        r"日起开展销售服务.*优惠活动期间",
                    ],
                    "bottom_anchor_regs": [
                        r"^根据相关法律法规",
                        r"(折|优惠)后.*销售服务费",
                        r"销售服务费.*(调整|恢复|降至|优惠至)",
                    ],
                    "top_anchor_regs": [
                        r"调整方案$",
                        r"(优惠)?活动内容$",
                        r"日起开展销售服务.*优惠活动期间",
                    ],
                },
                "paragraph_model": "partial_text",
                "para_config": {
                    "merge_char_result": False,
                    "regs": {
                        "基金名称": [
                            rf"(折|优惠)后.*?(?P<dst>{R_FUND_SHORT_NAME})的?年?销售服务费?年?费率(为|按)",
                            rf"对.*?(?P<dst>{R_FUND_SHORT_NAME})[^,，;；]*销售服务费率优惠",
                            rf"(?P<dst>{R_FUND_SHORT_NAME})[^,，;；]*销售服务费",
                            rf"(?P<dst>{R_FUND_SHORT_NAME})销售服务费费率优惠活动",
                        ],
                        "销售服务费率": [
                            r"本公司(?!曾于).*?销售服务费?年?费率.*?(?<!日起)(?<!日)至.*?(?P<dst>[\d.%]+)",
                            r"(折|优惠)后的?.*销售服务费?年?费率(为|按)(?P<dst>[\d.%]+)",
                            r"销售服务费.*?(优惠至|降(低)?|调整|恢复).*?(?P<dst>[\d.%]+)",
                        ],
                    },
                    "model_alternative": True,
                },
            },
        ],
    },
    {
        "path": ["分级基金"],
        "sub_primary_key": ["基金简称", "基金代码"],
        "divide_answers": True,
        "models": [
            {
                "name": "table_kv",
                "col_num": 2,
                "elements_nearby": ELEMENTS_NEARBY_FOR_SEGMENTED,
                "feature_white_list": {
                    "基金简称": [r"基金简称"],
                    "基金代码": [r"基金代码"],
                },
            },
            {
                "name": "table_row",
                "lazy_match": True,
                "elements_nearby": ELEMENTS_NEARBY_FOR_SEGMENTED,
                "feature_black_list": {
                    "基金简称": [r"__regex__.*"],
                    "基金代码": [r"__regex__.*"],
                },
                "feature_white_list": {
                    "基金简称": [
                        r"__regex__(基金|份额)简称",  # 单配一个提"基金简称"，避免被"基金全称"截胡
                    ],
                    "基金代码": [r"__regex__(基金|份额)主?代码"],
                },
                "cell_regs": {
                    "基金简称": [],
                    "基金代码": [r"(?P<dst>\d{6}(\.[A-Z]{2})?)"],
                },
            },
            {
                "name": "table_row",
                "elements_nearby": ELEMENTS_NEARBY_FOR_SEGMENTED,
                "feature_black_list": {
                    "基金简称": [r"__regex__.*"],
                    "基金代码": [r"__regex__.*"],
                },
                "feature_white_list": {
                    "基金简称": [r"__regex__(基金|份额)[名简全]称"],
                    "基金代码": [r"__regex__(基金|份额)代码"],
                },
                "cell_regs": {
                    "基金简称": [],
                    "基金代码": [r"(?P<dst>\d{6}(\.[A-Z]{2})?)"],
                },
            },
            {
                "name": "table_row",
                "elements_nearby": ELEMENTS_NEARBY_FOR_SEGMENTED,
                "parse_by": "col",
                "feature_black_list": {
                    "基金简称": [r"__regex__.*"],
                    "基金代码": [r"__regex__.*"],
                },
                "feature_white_list": {
                    "基金简称": [r"__regex__(基金|份额)[名简全]称"],
                    "基金代码": [r"__regex__(基金|份额)主?代码"],
                },
                "cell_regs": {
                    "基金简称": [],
                    "基金代码": [r"(?P<dst>\d{6}(\.[A-Z]{2})?)"],
                },
            },
            {
                "name": "partial_text",
                "order_by_index": True,
                "merge_char_result": False,
                "multi_elements": True,
                "multi": True,
                "neglect_patterns": [r"升级"],
                "syllabus_regs": [
                    r"基本(情况|信息)",
                    rf"基金(?:(?:(名|简)称|代码)[{R_CONJUNCTION}]?){{1,2}}",
                    r"基金代码|优惠活动",
                    r"适用基金",
                    r"活动结束说明",
                ],
                "neglect_syllabus_regs": [
                    r"投资者认购",
                ],
                "regs": {
                    "基金简称": P_ABBR_EXIST_CODE,
                    "基金代码": P_CODE_EXIST_ABBR,
                },
                "neglect_answer_patterns": {
                    "基金简称": [
                        r"^\d{6}$",
                        r"[:：]",
                        r"证券代码|认购代码|基金代码",
                    ],
                },
            },
            {
                "name": "elements_collector_based",
                "elements_collect_model": "middle_paras",
                "elements_collect_config": {
                    "use_top_crude_neighbor": False,
                    "top_anchor_regs": [r"(发售|募集)的?基本情况"],
                    "bottom_anchor_regs": [
                        r"基金份额的?类别设置",
                        r"发售规模和发售结构",
                        r"基金的?类型$",
                        r"基金存续期限$",
                    ],
                },
                "paragraph_model": "partial_text",
                "para_config": {
                    "merge_char_result": False,
                    "multi_elements": True,
                    "multi": True,
                    "neglect_patterns": [r"升级"],
                    "neglect_syllabus_regs": [r"份额的?类别"],
                    "regs": {
                        "基金简称": p_fund_abbr,
                        "基金代码": p_fund_code,
                    },
                    "neglect_answer_patterns": {
                        "基金简称": [
                            r"^\d{6}$",
                            r"[:：]",
                            r"证券代码|认购代码|基金代码",
                        ],
                    },
                },
            },
            {
                "name": "partial_text",
                "order_by_index": True,
                "merge_char_result": False,
                "multi_elements": True,
                "multi": True,
                "regs": {
                    "基金简称": p_fund_abbr,
                    "基金代码": p_fund_code,
                },
                "neglect_answer_patterns": {
                    "基金简称": [
                        r"^\d{6}$",
                        r"[:：]",
                        r"证券代码|认购代码|基金代码",
                    ],
                },
                "neglect_patterns": [
                    r"公告$",
                    rf"购买本?基金{R_FUND_SHORT_NAME}",
                ],
            },
        ],
    },
    {
        "path": ["基金名称"],
        "models": [
            {
                "name": "middle_paras",
                "top_anchor_content_regs": [
                    rf"关于{R_ADJUST}?(旗下)?(?P<content>.*)[A-Z]类基金",
                    rf"关于{R_ADJUST}?(旗下)?(?P<content>.*)",
                ],
                "bottom_anchor_content_regs": [
                    rf"(?P<content>.*?基?金(中基金)?{R_FUND_SUFFIX}?)[A-Z]类基金",
                    rf"(?P<content>.*?基?金(中基金)?{R_FUND_SUFFIX}?)",
                ],
                "middle_content_regs": [r"(?P<content>.+)(?:[A-Z]类基金)", r"(?P<content>.+)"],
                "top_anchor_regs": [r"^关于", "公司关于", "关于开展旗下"],
                "bottom_anchor_regs": [r"(销售服务费|管理费).*?公告$"],
                "include_bottom_anchor": True,
            },
            {
                "name": "partial_text",
                "regs": [
                    rf"关于{R_ADJUST}?(旗下)?(?P<dst>.*?(?:联接基金{R_FUND_SUFFIX}?|联接{R_FUND_SUFFIX}))",
                    rf"关于{R_ADJUST}?(旗下)?(?P<dst>.*?基金{R_FUND_SUFFIX}?)",
                    rf"^(?P<dst>.*?基金{R_FUND_SUFFIX}?)[A-Z]类基金份额",
                    rf"^(?P<dst>.*?基金{R_FUND_SUFFIX}?){R_ADJUST}?(管理费|销售服务费).*?公告",
                ],
                "model_alternative": True,
                "neglect_answer_patterns": [
                    r"部分(指数)?基金",
                    r"^南方基金$",
                ],
            },
        ],
    },
    {
        "path": ["基金代码"],
        "models": [
            {
                "name": "partial_text",
            },
        ],
    },
    {
        "path": ["管理费率优惠开始日期"],
        "models": [
            {
                "name": "partial_text",
                "regs": [
                    rf"{R_SINCE}{R_DATE}(.含.)?(起|开始).*?管理费",
                    rf"管理费.*?{R_SINCE}{R_DATE}(.含.)?(起|开始)",
                    rf"管理费.*?生效时间(为)?{R_DATE}",
                ],
            },
            # 在表格中描述
            # http://scriber-cmbchina.test.paodingai.com/scriber/#/project/remark/9170?projectId=8&treeId=15&fileId=283&schemaId=8
            {
                "name": "cell_partial_text",
                "regs": [
                    rf"{R_SINCE}{R_DATE}(.含.)?(起|开始).*?管理费",
                ],
            },
            {
                "name": "elements_condition",
                "elements_condition_model": "middle_paras",
                "elements_condition_config": {
                    "elements_in_page_range": [0],
                    "use_top_crude_neighbor": False,
                    "top_default": True,
                    "include_bottom_anchor": True,
                    "bottom_anchor_regs": [
                        r"(销售服务费|管理费).*?公告$",
                        r"根据《中华人民共和国证券投资基金法》",
                    ],
                    "keywords": [
                        r"管理费",
                    ],
                },
                "elements_extract_model": "partial_text",
                "elements_extract_config": {
                    "regs": [
                        rf"上述修订{R_SINCE}{R_DATE}",
                        rf"修改后[^,，。;；]*{R_SINCE}{R_DATE}",
                    ]
                },
            },
        ],
    },
    {"path": ["管理费率优惠结束日期"], "models": [{"name": "partial_text"}]},
    {
        "path": ["销售服务费率优惠开始日期"],
        "models": [
            {
                "name": "partial_text",
                "regs": [
                    rf"{R_SINCE}{R_DATE}(.含.)?(起|开始|至).*?开展销售服务费.{{0,2}}优惠",
                ],
            },
            {
                "name": "partial_text",
                "elements_nearby": {
                    "regs": [r"销售服务费[费率]{0,2}优惠"],
                    "amount": 10,
                    "step": -1,
                },
                "regs": [rf"{R_SINCE}{R_DATE}(.含.)?(起|开始)"],
                "model_alternative": True,
                "neglect_syllabus_regs": [
                    r"活动结束",
                    "结束销售服务费费率优惠活动",
                    r"申购费率",
                ],
            },
            {
                "name": "partial_text",
                "regs": [
                    rf"{R_SINCE}{R_DATE}(.含.)?(起|开始|发布).*销售服务费",
                    rf"销售服务费.*{R_SINCE}{R_DATE}",
                ],
                "neglect_syllabus_regs": [
                    r"活动结束",
                    "结束销售服务费费率优惠活动",
                ],
            },
            {
                "name": "partial_text",
                "regs": [
                    rf"(?:{R_SINCE}|^){R_DATE}",
                ],
                "syllabus_regs": ["(?:活动时间|优惠时间)$"],
            },
        ],
    },
    {
        "path": ["销售服务费率优惠结束日期"],
        "models": [
            # http://scriber-cmbchina.test.paodingai.com/scriber/#/project/remark/9163?projectId=15&treeId=15&fileId=276&schemaId=8
            {
                "name": "partial_text",
                "regs": [
                    rf"{R_SINCE}{R_DATE}\s*.{{0,5}}结束",
                ],
                "syllabus_regs": [
                    "活动结束",
                    "结束销售服务费费率优惠活动",
                ],
            },
            {
                "name": "partial_text",
                "model_alternative": True,
                "regs": [
                    rf"(结束时间|优惠(活动)?的?方案.*?变化|截止日期).*?(?P<dst>(届时)?将?{R_NOTICE_LATER})",
                    rf"{R_SINCE}起.?具?体?截止日期(?P<dst>{R_NOTICE_LATER}).*?销售服务费",
                    rf"{R_SINCE}.*?至{R_DATE}",
                    rf"{R_SINCE}{R_DATE}(?:起|开始)结束",
                ],
                # "syllabus_regs": [r"(活动|优惠)(时间|期限)", "服务费.*?优惠(的)?公告"],
            },
            {
                "name": "partial_text",
                "regs": [
                    rf"(?:{R_SINCE}|^).*?至{R_DATE}",
                ],
                "syllabus_regs": ["(?:活动时间|优惠时间)$"],
            },
        ],
    },
    {
        "path": ["认购费率"],
        "models": [
            {
                "name": "table_row",
            },
        ],
    },
    {
        "path": ["申购费率"],
        "models": [
            {
                "name": "partial_text",
                "neglect_patterns": [r"申购本基金管理人管理的其他基金不收取申购费"],
                "regs": {
                    "申购费": [
                        r"基金的?申购费率?为(?P<dst>[\d.%％零]+)",
                        r"(?P<dst>不(支付|收取)申购费)",
                        r"基金份额时?(?P<dst>不(支付|收取)申购费)",
                        r"基金份额的?申购费率?为(?P<dst>[\d.%％零]+)",
                        r"本基金的?申购[、和及与]赎回费率为(?P<dst>[\d.%％零]+)",
                        r"份额的投资人.申购费率为(?P<dst>[\d.%％零]+)",
                    ],
                    "基金名称": [
                        rf"(?P<dst>(([A-Z]类|[A-Z])[{R_CONJUNCTION}]?){{1,3}})(基金)?份额时?不(支付|收取)申购费",
                        rf"(?P<dst>(([A-Z]类|[A-Z])[{R_CONJUNCTION}]?){{1,3}})(基金)?份额的投资人.申购费率为",
                        r"(?P<dst>[A-Z]类)基金份额的?申购费率?为",
                    ],
                    "申购区间": [],
                    "购买金额": [],
                    "区间起始值": [],
                    "区间结束值": [],
                },
            },
            {
                "name": "table_row",
                "middle_rows": {
                    "top_anchor_regs": ["调整后|修改为"],
                    "include_top_anchor": False,
                    "include_bottom_anchor": True,
                    "bottom_default": True,
                },
                "feature_white_list": {
                    "申购区间": [
                        r"__regex__申购[金份]额",
                        r"__regex__金额[A-Z]",
                    ],
                    "购买金额": [
                        r"__regex__申购[金份]额",
                        r"__regex__金额[A-Z]",
                    ],
                    "区间起始值": [
                        r"__regex__申购[金份]额",
                        r"__regex__金额[A-Z]",
                    ],
                    "区间结束值": [
                        r"__regex__申购[金份]额",
                        r"__regex__金额[A-Z]",
                    ],
                    "申购费": [
                        r"__regex__申购费率",
                    ],
                    "基金名称": [],
                },
                "neglect_patterns": [
                    r"(申购|基金)(费率|[金份]额)",
                    r"情形|费率|金额",
                ],
                "cell_regs": {
                    "区间起始值": R_INTERVAL_START,
                    "区间结束值": R_INTERVAL_END,
                },
                "基金名称": {
                    "from_title": [
                        r"(?P<dst>([A-Z]类[、和及与])*[A-Z]类)(基金)?份额.{,3}申购费",
                    ],
                    "from_above_row": [
                        r"(?P<dst>([A-Z]类[、和及与])*[A-Z]类)基金份额",
                    ],
                },
            },
        ],
    },
    {
        "path": ["赎回费率"],
        "models": [
            {
                "name": "table_row",
                "cell_regs": {
                    "区间起始值": R_INTERVAL_START,
                    "区间结束值": R_INTERVAL_END,
                },
                "基金名称": {
                    "from_title": [
                        r"(?P<dst>([A-Z]类[、和及与])*[A-Z]类)(基金)?份额.{,3}赎回费",
                    ],
                    "from_above_row": [
                        r"(?P<dst>([A-Z]类[、和及与])*[A-Z]类)基金份额",
                    ],
                },
            },
        ],
    },
]

prophet_config = {
    "depends": {},
    "predictor_options": get_predictor_options(predictor_options),
}
