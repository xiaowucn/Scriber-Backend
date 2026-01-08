"""
升降级公告
"""

from remarkable.predictor.cmbchina_predictor import R_DATE
from remarkable.predictor.cmbchina_predictor.schemas import (
    R_FUND_SHORT_NAME,
    R_NON_PUNCTUATION,
    gen_fund_name_regex,
    gen_platform_regex,
    get_predictor_options,
)
from remarkable.predictor.cmbchina_predictor.schemas.cmbchina_prospectus_schema import R_AMOUNT
from remarkable.predictor.common_pattern import R_CN, R_CONJUNCTION

R_CHAPTER_PREFIX = r"[一二三四五六七八九十零〇\d]+[.、]"

R_SALES_PLATFORM = r"(交易平台|(柜|平)台|销售机构)"

R_NON_MULTI_FUND_NAME = r"调整([A-Z][类级][、和或与]?){,2}基金份额最.申购金额[，,]将本基金(?P<dst>[A-Z][类级])"

R_RECOVER = "(取消|暂停|调整|恢复|修改)"
R_FUND_SUFFIX = r"(?:.类|基金|自动|份额|首次)"


predictor_options = [
    {
        "path": ["基金名称"],
        "models": [
            {
                "name": "partial_text",
                "regs": [
                    # 用于识别错误导致段落被截断
                    rf"关于(?P<dst>.*?(?<!类)基金){R_RECOVER}?$",
                    rf"关于{R_RECOVER}(?P<dst>.*?(?<!类)基金){R_FUND_SUFFIX}",
                    rf"关于(?P<dst>.*?基金){R_RECOVER}{R_FUND_SUFFIX}",
                    rf"关于(?P<dst>.*?基金){R_FUND_SUFFIX}",
                    rf"^(?P<dst>.*?基金){R_RECOVER}",
                ],
            },
            {
                "name": "fund_name",
                "combine_regs": [rf"关于{R_RECOVER}?(销售)?(?P<dst>.*?基金).*?升降级"],
                "top_anchor_regs": [r"^关于"],
                "bottom_anchor_regs": [r"自动升降级业务", r"公告$"],
                "include_bottom_anchor": True,
            },
            {
                "name": "partial_text",
                "regs": [
                    rf"关于{R_RECOVER}?(销售)?(?P<dst>.*?基金)",
                    rf"关于(?P<dst>[^(（）)]*?基金){R_RECOVER}(销售)?基金份额",
                    # https://gitpd.paodingai.com/cheftin/docs_scriber/-/issues/5907
                    # rf"(关于)?(?P<dst>.*?基金){R_RECOVER}?(销售)?(.类基金|基金份额)",
                ],
                "model_alternative": True,
            },
        ],
    },
    {
        "path": ["分级基金"],
        "sub_primary_key": ["基金简称", "基金代码"],
        "divide_answers": True,
        "pick_answer_strategy": "all",
        "primary_key_unit": [r"[^A-Z0-9]"],
        "models": [
            {
                "name": "table_row",
                "feature_black_list": {
                    "基金简称": [r"__regex__.*"],
                    "基金代码": [r"__regex__.*"],
                },
                "feature_white_list": {
                    "基金简称": [r"__regex__基金[名简]称"],
                    "基金代码": [r"__regex__基金代码"],
                },
            },
            {
                "name": "cell_partial_text",
                "merge_char_result": False,
                "from_cell": False,
                "neglect_syllabus_regs": [
                    r"附件",
                ],
                "regs": {
                    "基金简称": [
                        r"(?P<dst>.[类级]基金份额).{,5}代码",
                        r"(?P<dst>.[类级]基金份额)\d+",
                    ],
                    "基金代码": [
                        r"代码[:：（(](?P<dst>\d+)",
                        r"[类级]基金份额(?P<dst>\d+)",
                    ],
                },
                "multi": True,
            },
            # http://scriber-cmbchina.test.paodingai.com/scriber/#/project/remark/9458?treeId=14&fileId=239&schemaId=7
            {
                "name": "table_subscription",
                "multi_elements": False,
                "syllabus_regs": [
                    r"基金份额最低(交易|申购)(限|金)额",
                ],
                "cell_regs": {
                    "基金简称": [r"(?P<dst>[A-Z][类级])((基金)?份额)?"],
                    "基金代码": [
                        r"(?P<dst>\d{6})",
                    ],
                },
                "main_column": "基金简称",
                "secondary_column": "基金代码",
                "header_patterns": {"基金简称": [r"[A-Z](类|级)"], "基金代码": [r"基金代码"]},
            },
            {
                "name": "subscription",
                "multi_config": {
                    "基金简称": True,
                    "基金代码": True,
                },
                "regs": {
                    "基金简称": [
                        r"(?<!调整)(?P<dst>[A-Z][类级])((基金)?份额)?.*?\d{6}",
                    ],
                    "基金代码": [
                        r"基金份额\s*(?P<dst>\d{6})",
                        r"代码[:：为]?(?P<dst>\d{6})",
                        r"[A-Z][类级][:：为]?(?P<dst>\d{6})",
                    ],
                },
            },
            # {
            #     "name": "partial_text",
            #     "merge_char_result": False,
            #     "neglect_patterns": [r"升级"],
            #     "regs": {
            #         "基金简称": p_fund_abbr,
            #         "基金代码": p_fund_code,
            #     },
            #     "multi": True,
            # },
        ],
    },
    {
        "path": ["暂停、取消、生效时间"],
        "models": [
            {
                "name": "partial_text",
                # https://gitpd.paodingai.com/cheftin/docs_scriber/-/issues/5034
                # https://gitpd.paodingai.com/cheftin/docs_scriber/-/issues/5822
                "regs": [
                    rf"(自|于)\s*(?P<dst>{R_DATE})\s*起.*{R_RECOVER}.*?(自动|基金份额)升降级",
                ],
                "model_alternative": True,
            },
        ],
    },
    {
        "path": ["是否升降级"],
        "models": [
            # https://gitpd.paodingai.com/cheftin/docs_scriber/-/issues/5030#note_557364
            {
                "name": "middle_paras",
                "top_anchor_content_regs": [rf"{R_CHAPTER_PREFIX}取消基金份额自动升降级业务(?P<content>.*)"],
                "bottom_anchor_content_regs": [rf"(?P<content>.*?){R_CHAPTER_PREFIX}调整本?基金.*?(交易限额|申购金额)"],
                "top_anchor_regs": [rf"{R_CHAPTER_PREFIX}取消基金份额自动升降级业务"],
                "bottom_anchor_regs": [rf"{R_CHAPTER_PREFIX}调整本?基金.*?(交易限额|申购金额)"],
                "include_bottom_anchor": True,
            },
            # https://gitpd.paodingai.com/cheftin/docs_scriber/-/issues/5030#note_557309
            # https://gitpd.paodingai.com/cheftin/docs_scriber/-/issues/5908
            {
                "name": "syllabus_based",
                "inject_syllabus_features": [r"__regex__(恢复|调整)后的?升降级规则"],
                "only_inject_features": True,
                "include_title": False,
                "paragraph_model": "para_match",
                "para_config": {
                    "paragraph_pattern": [r"[升降]级(?!的?数量限制及规则.?由基金管理人在招募说明书中规定)"],
                    "neglect_regs": "C类基金",
                },
            },
            {"name": "para_match", "paragraph_pattern": [r"自动升降级"]},
        ],
    },
    {
        "path": ["单笔申购下限-原文"],
        "location_threshold": 0.1,
        "models": [
            {
                "name": "para_match",
                "multi_elements": True,
                "paragraph_pattern": [
                    rf"(基金|[A-Z]类)份额.*单笔最低(限额|金额|申购).*{R_AMOUNT}",
                    rf"(基金|[A-Z]类)份额.*(单笔|追加)申购(（.*）)?的?(最低|调整为|降至).*{R_AMOUNT}",
                    rf"(基金|[A-Z]类)份额.*(单笔|追加)申购.*(调整|降至|起点)为?{R_AMOUNT}",
                ],
            },
        ],
    },
    {
        "path": ["单笔申购下限"],
        "sub_primary_key": ["基金名称", "销售平台", "最低限额"],
        "post_process": "post_process_sale_platform",
        "models": [
            {
                "name": "table_subscription",
                "multi_elements": False,
                "syllabus_regs": [
                    r"基金份额最低(交易|申购)(限|金)额",
                ],
                "cell_regs": {
                    "基金名称": [r"(?P<dst>.*?货币[A-Z])"],
                    "最低限额": [
                        r"[:：为]?(?P<dst>[\d.\s,，]+千?百?万?(元|份))",
                    ],
                    "销售平台": [r"(?P<dst>.*(交易平台|直销柜台))"],
                },
                "main_column": "基金名称",
                "secondary_column": "销售平台",
                "header_patterns": {
                    "基金名称": [r"货币[A-Z]"],
                    "最低限额": [r"追加申购(单笔)?最低金额"],
                    "销售平台": [r"追加申购(单笔)?最低金额"],
                },
                "splits": r"[(（\n]",
            },
            {
                "name": "table_subscription",
                "multi_elements": False,
                "syllabus_regs": [
                    r"基金份额最低(交易|申购)(限|金)额",
                ],
                "cell_regs": {
                    "基金名称": [r"(?P<dst>.*?货币[A-Z])"],
                    "最低限额": [
                        r"[:：为]?(?P<dst>[\d.\s,，]+千?百?万?(元|份))",
                    ],
                    "销售平台": [r"(?P<dst>.*(交易平台|直销柜台))"],
                },
                "main_column": "基金名称",
                "secondary_column": "销售平台",
                "header_patterns": {
                    "基金名称": [r"货币[A-Z]"],
                    "最低限额": [r"首次申购单笔最低金额"],
                    "销售平台": [r"首次申购单笔最低金额"],
                },
                "splits": r"[(（\n]",
            },
            {
                "name": "table_subscription",
                "elements_nearby": {
                    "neglect_regs": [r"调整前"],
                    "amount": 1,
                    "step": -1,
                },
                "multi_elements": False,
                "syllabus_regs": [
                    r"基金份额最低(交易|申购)(限|金)额",
                    r"投资业务的?公告",
                    r"^\d+.调整基金最低申购金额",
                ],
                "cell_regs": {
                    "基金名称": [r"(?P<dst>.*?[A-Z](类|级)基金份额)"],
                    "最低限额": [
                        r"[:：为]?(?P<dst>[\d.\s,，]+千?百?万?(元|份))",
                    ],
                    "销售平台": [
                        rf"(通过)?(?P<dst>.*{R_SALES_PLATFORM}(或.*{R_SALES_PLATFORM})?)",
                    ],
                },
                "main_column": "基金名称",
                "main_column_by_cell_regs": True,
                "secondary_column": "最低限额",
                "header_patterns": {
                    "基金名称": [r"[A-Z](类|级)基金份额"],
                    "最低限额": [r"追加申购.*最低金额"],
                    "销售平台": [r"追加申购.*最低金额"],
                },
            },
            {
                "name": "table_subscription",
                "elements_nearby": {
                    "neglect_regs": [r"调整前"],
                    "amount": 1,
                    "step": -1,
                },
                "multi_elements": False,
                "syllabus_regs": [
                    r"基金份额最低(交易|申购)(限|金)额",
                    r"投资业务的?公告",
                    r"^\d+.调整基金最低申购金额",
                ],
                "cell_regs": {
                    "基金名称": [r"(?P<dst>.*?[A-Z](类|级)基金份额)"],
                    "最低限额": [
                        r"[:：为]?(?P<dst>[\d.\s,，]+千?百?万?(元|份))",
                    ],
                    "销售平台": [
                        rf"(通过)?(?P<dst>.*{R_SALES_PLATFORM}(或.*{R_SALES_PLATFORM})?)",
                    ],
                },
                "main_column": "基金名称",
                "main_column_by_cell_regs": True,
                "secondary_column": "最低限额",
                "header_patterns": {
                    "基金名称": [r"[A-Z](类|级)基金份额"],
                    "最低限额": [r"首次(单笔)?申购.*最低金额"],
                    "销售平台": [r"首次(单笔)?申购.*最低金额"],
                },
            },
            {
                "name": "table_row",
                "parse_by": "col",
                "elements_nearby": {
                    "regs": [r"调整后"],
                    "amount": 1,
                    "step": -1,
                },
                "multi_elements": False,
                "syllabus_regs": [
                    r"(基金|[A-Z]类)份额最低(交易|申购)(限|金)额",
                    r"投资业务的?公告",
                    r"^\d+.调整基金最低申购金额",
                ],
                "cell_regs": {
                    "基金名称": [r"(?P<dst>.*?[A-Z](类|级)基金份额)"],
                    "最低限额": [
                        r"(?P<dst>[\d.\s,，]+千?百?万?(元|份))",
                    ],
                    "销售平台": [],
                },
                "feature_white_list": {
                    "基金名称": [r"项目"],
                    "最低限额": [r"__regex__追加申购单笔最低[金限]额"],
                    "销售平台": [],
                },
            },
            {
                "name": "table_row",
                "parse_by": "col",
                "elements_nearby": {
                    "regs": [r"调整后"],
                    "amount": 1,
                    "step": -1,
                },
                "multi_elements": False,
                "syllabus_regs": [
                    r"(基金|[A-Z]类)份额最低(交易|申购)(限|金)额",
                    r"投资业务的?公告",
                    r"^\d+.调整基金最低申购金额",
                ],
                "cell_regs": {
                    "基金名称": [r"(?P<dst>.*?[A-Z](类|级)基金份额)"],
                    "最低限额": [
                        r"(?P<dst>[\d.\s,，]+千?百?万?(元|份))",
                    ],
                    "销售平台": [],
                },
                "feature_white_list": {
                    "基金名称": [r"项目"],
                    "最低限额": [r"__regex__首次申购单笔最低[金限]额"],
                    "销售平台": [],
                },
            },
            {
                "name": "syllabus_based",
                "inject_syllabus_features": [
                    r"__regex__单笔最低交易限额调整方案",
                ],
                "table_model": "table_subscription",
                "table_config": {
                    "cell_regs": {
                        "基金名称": [r"(?P<dst>.*?货币[A-Z])"],
                        "最低限额": [
                            r"[:：为]?(?P<dst>[\d.\s,，]+千?百?万?(元|份))",
                        ],
                        "销售平台": [r"(?P<dst>.*(交易平台|直销柜台))"],
                    },
                    "main_column": "基金名称",
                    "secondary_column": "销售平台",
                    "header_patterns": {
                        "基金名称": [r"货币[A-Z]"],
                        "最低限额": [r"追加申购(单笔)?最低金额"],
                        "销售平台": [r"追加申购(单笔)?最低金额"],
                    },
                    "splits": r"[(（\n]",
                },
            },
            {
                "name": "subscription",
                "main_column": "销售平台",
                "depends": ["单笔申购下限-原文"],
                "need_distinct": True,
                "multi_config": {
                    "基金名称": True,
                    "最低限额": False,
                    "销售平台": False,
                },
                "para_regs": [
                    rf"((单|每)[次笔]|首笔|追加)(最.)?(申购(?!各类)[^,.，。；;]*?(人民币)?|金额(下限|起点)?为?){R_AMOUNT}",
                    rf"申购[^。，,]*?((单|每)[次笔]|首笔)[^,.，。；;]*?(人民币)?{R_AMOUNT}",
                    rf"(?<!首次)申购的?((金额)?(下限|起点)|最低金额)为(人民币)?{R_AMOUNT}",
                    r"份额(?P<dst>(无|不设)单笔最低限额)",
                    rf"通过.*?投资本基金{R_FUND_SHORT_NAME}.{{2,3}}申购金额起点",
                    rf"首次申购(本?基金?)?{R_FUND_SHORT_NAME}([{R_CONJUNCTION}]{R_FUND_SHORT_NAME})?的单笔最.限额",
                    rf"{R_FUND_SHORT_NAME}[\w\s]*首次申购的?单笔最.限额",
                ],
                "neglect_patterns": [
                    r"[A-Z][类级]基金(份额)?申购数量的限制由.*?(?!调整为)",
                    rf"^本?基金([{R_CN}]+)?.笔申购最低金额([{R_CN}]+)?管理人([{R_CN}]+)?调整",
                ],
                "regs": {
                    "基金名称": [
                        R_NON_MULTI_FUND_NAME,
                        rf"(((单|每)[次笔]|首笔)申购|[{R_CONJUNCTION}]|基金){R_NON_PUNCTUATION}*?(?<!首次申购)(?P<dst>{R_FUND_SHORT_NAME})[{R_CONJUNCTION}][A-Z][类级]",
                        rf"(((单|每)[次笔]|首笔)申购|[{R_CONJUNCTION}]|基金){R_NON_PUNCTUATION}*?(?<!首次申购)(?P<dst>{R_FUND_SHORT_NAME})(?!(类?(份额)?(基金)?(份额)?)?最.申购金额，将本基金[A-Z][类级])",
                        rf"(((单|每)[次笔]|首笔)申购|[{R_CONJUNCTION}]|基金){R_NON_PUNCTUATION}*?(?P<dst>[^,.，。；;申购]*?货币[A-Z])",
                        rf"(?<!持有本基金)(?P<dst>{R_FUND_SHORT_NAME})([\/、和或与]{R_FUND_SHORT_NAME})?{R_NON_PUNCTUATION}*?((单|每)[次笔]|首笔)申购",
                        r"通过[^;；。]*?(?P<dst>[A-Z][类级]((基金)?份额)?)[^;；。]*?((单|每)[次笔]|首笔)申购",
                        r"通过[^;；。]*?(?P<dst>[A-Z][类级]((基金)?份额)?)[^;；。]*?申购金额起点",
                        rf"首次申购(本?基金?)?{R_NON_PUNCTUATION}*?(?P<dst>{R_FUND_SHORT_NAME})的?单笔最.[限金]额",
                        rf"首次申购(本?基金?)?(?P<dst>{R_FUND_SHORT_NAME})[{R_CONJUNCTION}]{R_FUND_SHORT_NAME}的?单笔最.[限金]额",
                        rf"已持有本基金(?P<dst>{R_FUND_SHORT_NAME})[\w\s]*首次申购的?单笔最.[限金]额",
                    ],
                    "最低限额": [
                        rf"(追加申购[{R_CN}]{{,2}})((单|每)[次笔]|首笔)(首次)?(最.)?(申购(?!各类)[^,.，。；;]*?(人民币)?|金额(起点|下限)?为?){R_AMOUNT}(?!降至|调整为)",
                        rf"追加申购[^。，,]*?((单|每)[次笔]|首笔)[^,.，。；;]*?{R_AMOUNT}(?!降至|调整为)",
                        rf"追加((单|每)[次笔]|首笔)?申购[^,.，。；;]*?{R_AMOUNT}(?!降至|调整为)",
                        rf"追加申购的?((金额)?下限|最低金额)均?为{R_AMOUNT}",
                        rf"首次申购或追加申购各类基金份额时[,，]单笔最低金额为{R_AMOUNT}",
                        rf"首次最低金额及追加申购最低金额分别为.*?和{R_AMOUNT}",
                        # 优先提取追加申购的
                        rf"单笔[^,.，。；;]*?{R_AMOUNT}(?!降至|调整为)",
                        rf"申购金额.*(调整为|降至){R_AMOUNT}",
                    ],
                    "销售平台": [
                        r"(?P<dst>代销机构及直销(网上|电子)交易平台)",  # project/remark/9279?projectId=7&treeId=14&fileId=220&schemaId=7
                        r"(?P<dst>代销机构或本公司网上直销)",  # project/remark/9279?projectId=7&treeId=14&fileId=220&schemaId=7
                        r"(?P<dst>本公司直销中心)",
                        r"交易限额调整为：(?P<dst>.*)基金投资者",
                        *gen_platform_regex("((首次)?申购|每个账户)"),
                    ],
                },
            },
            # http://scriber-cmbchina.test.paodingai.com/scriber/#/project/remark/11036?projectId=39&treeId=64&fileId=1093&schemaId=7
            {
                "name": "subscription",
                "main_column": "基金名称",
                "depends": ["单笔申购下限-原文"],
                "para_regs": [
                    r"首次申购单笔最低",
                ],
                "regs": {
                    "基金名称": [
                        r"调整.(?P<dst>[A-Z]类(基金)?份额)(首次)?申购单笔最低金额",
                    ],
                    "最低限额": [
                        rf"调整.[A-Z]类(基金)?份额(首次)?申购单笔最低金额.?{R_AMOUNT}",
                        rf"单笔[^,.，。；;]*?{R_AMOUNT}(?!降至|调整为)",
                    ],
                },
                "neglect_patterns": [
                    *gen_platform_regex("((首次)?申购|每个账户)"),
                ],
            },
            {
                "name": "partial_text",
            },
        ],
    },
    {
        "path": ["首次申购下限-原文"],
        "models": [
            {
                "name": "kmeans_classification",
                "threshold": 0.48,
                "high_score_elements_count": 2,
                "para_pattern": [
                    rf"[首单每][次笔](单笔)?(最.)?申购.*{R_AMOUNT}",
                    rf"申购.*金额起点.*{R_AMOUNT}",
                ],
            },
            {
                "name": "para_match",
                "paragraph_pattern": [
                    rf"[首单每][次笔](单笔)?(最.)?申购.*{R_AMOUNT}",
                    rf"申购.*金额起点.*{R_AMOUNT}",
                    rf"申购.*[首单每][次笔](单笔)?(最.)?金额.*{R_AMOUNT}",
                ],
            },
        ],
    },
    {
        "path": ["首次申购下限"],
        "sub_primary_key": ["基金名称", "销售平台", "最低限额"],
        "post_process": "post_process_sale_platform",
        "pick_answer_strategy": "all",
        "models": [
            {
                "name": "subscription",
                "main_column": "销售平台",
                "depends": ["首次申购下限-原文"],
                "need_distinct": True,
                "multi_config": {
                    "基金名称": True,
                    "最低限额": True,
                    "销售平台": False,
                },
                "regs": {
                    "基金名称": [
                        r"通过(基金)?管理人.{,10}办理(?P<dst>[^,.，。；;申购]*?货币[A-Z])",
                        *gen_fund_name_regex("[首每单][次笔]申购", "追加[申认]购[A-Z]类"),
                    ],
                    "最低限额": [
                        rf"(?<!追加申购)(?<!追加)[首][次笔](?!追加)[^,.，。；;]*?{R_AMOUNT}(?!.自{R_DATE}起)(?!降至|.?调整为)",
                        r"(?P<dst>无单笔最低限额)",
                        rf"(?<!追加申购[A-Z]类基金份额的)(?<!追加申购)(?<!追加)[每单][次笔](?!追加)[^,.，。；;]*?{R_AMOUNT}(?!.自{R_DATE}起)(?!降至|.?调整为)",
                    ],
                    "销售平台": [
                        r"(?P<dst>代销机构及直销(网上|电子)交易平台)",
                        r"(?P<dst>代销网点、直销网上交易以及直销电话交易).*首次",
                        *gen_platform_regex("((首次)?申购|每个账户)"),
                    ],
                },
                "para_regs": [
                    rf"(申购[^,.，。；;]*?[首每单][次笔](?!追加)|[首每单][次笔](?!追加)[^,.，。；;]*?申购)[^,.，。；;]*?{R_AMOUNT}",
                ],
                "neglect_patterns": [
                    r"[A-Z][类级]基金(份额)?申购数量的限制由.*?(?!调整为)",
                ],
                "splits": [
                    r"[。；;](?![）)])",
                ],
            },
            {
                "name": "table_subscription",
                "multi_elements": False,
                "syllabus_regs": [
                    r"基金份额最低交易限额",
                    r"单笔最低交易限额调整方案",
                ],
                "cell_regs": {
                    "基金名称": [r"(?P<dst>.*?货币[A-Z])"],
                    "最低限额": [
                        rf"[:：为]?{R_AMOUNT}",
                    ],
                    "销售平台": [r"(?P<dst>.*(交易平台|直销柜台))"],
                },
                "main_column": "基金名称",
                "secondary_column": "销售平台",
                "header_patterns": {
                    "基金名称": [r"货币[A-Z]"],
                    "最低限额": [
                        r"首次申购.*最低金额",
                        r"最低申购金额",
                    ],
                    "销售平台": [
                        r"首次申购.*最低金额",
                        r"最低申购金额",
                    ],
                },
                "splits": r"[(（\n]",
            },
            {
                "name": "table_subscription",
                "neglect_syllabus_regs": [  # 避免重复提取前一个table_subscription提过的表格
                    r"基金份额最低交易限额",
                    r"单笔最低交易限额调整方案",
                ],
                "elements_nearby": {
                    "neglect_regs": [r"调整前"],
                    "amount": 1,
                    "step": -1,
                },
                "multi_elements": False,
                # project/remark/9284?projectId=7&treeId=14&fileId=230&schemaId=7
                # "syllabus_regs": [
                #     r"基金份额最低(交易|申购)(限|金)额",
                #     r"投资业务的?公告",
                #     r"调整基金份额最低交易限额的?公告",
                # ],
                "cell_regs": {
                    "基金名称": [r"(?P<dst>.*?[A-Z](类|级)基金份额)", r"(?P<dst>.*?投资基金[A-Z](类|级))"],
                    "最低限额": [
                        rf"[:：为]?{R_AMOUNT}",
                    ],
                    "销售平台": [
                        rf"(通过)?(?P<dst>{R_NON_PUNCTUATION}*{R_SALES_PLATFORM}(或.*{R_SALES_PLATFORM})?)",
                    ],
                },
                "main_column": "基金名称",
                "main_column_by_cell_regs": True,
                "secondary_column": "最低限额",
                "header_patterns": {
                    "基金名称": [r"[A-Z](类|级)基金份额", r"投资基金[A-Z](类|级)"],
                    "最低限额": [r"首次(单笔)?申购.*(最低金额|金额起点)", "申购.*金额起点"],
                    "销售平台": [r"首次(单笔)?申购.*(最低金额|金额起点)", "申购.*金额起点"],
                },
            },
        ],
    },
    {
        "path": ["追加申购下限-原文"],
        "models": [
            {
                "name": "kmeans_classification",
                "threshold": 0.48,
                "high_score_elements_count": 2,
                "para_pattern": [r"追加[^,.，。；;]*申购"],
            },
            {
                "name": "para_match",
                "paragraph_pattern": [r"追加[^,.，。；;]*申购"],
            },
        ],
    },
    {
        "path": ["追加申购下限"],
        "sub_primary_key": ["基金名称", "销售平台", "最低限额"],
        "models": [
            {
                "name": "table_subscription",
                "multi_elements": False,
                "syllabus_regs": [
                    r"基金份额最低交易限额",
                ],
                "cell_regs": {
                    "基金名称": [r"(?P<dst>.*?货币[A-Z])"],
                    "最低限额": [
                        r"[:：为]?(?P<dst>[\d.\s,，]+千?百?万?(元|份))",
                    ],
                    "销售平台": [r"(?P<dst>.*(交易平台|直销柜台))"],
                },
                "main_column": "基金名称",
                "secondary_column": "最低限额",
                "header_patterns": {
                    "基金名称": [r"货币[A-Z]"],
                    "最低限额": [r"追加申购.*最低金额"],
                    "销售平台": [r"追加申购.*最低金额"],
                },
                "splits": r"[(（\n]",
            },
            {
                "name": "table_subscription",
                "elements_nearby": {
                    "neglect_regs": [r"调整前"],
                    "amount": 1,
                    "step": -1,
                },
                "multi_elements": False,
                # "syllabus_regs": [
                #     r"基金份额最低(交易|申购)(限|金)额",
                #     r"投资业务的?公告",
                #     r"调整基金份额最低交易限额的?公告",
                # ],
                "cell_regs": {
                    "基金名称": [r"(?P<dst>.*?[A-Z](类|级)基金份额)", r"(?P<dst>.*?投资基金[A-Z](类|级))"],
                    "最低限额": [
                        r"[:：为]?(?P<dst>[\d.\s,，]+千?百?万?(元|份))",
                    ],
                    "销售平台": [
                        rf"(通过)?(?P<dst>.*{R_SALES_PLATFORM}(或.*{R_SALES_PLATFORM})?)",
                    ],
                },
                "main_column": "基金名称",
                "main_column_by_cell_regs": True,
                "secondary_column": "最低限额",
                "header_patterns": {
                    "基金名称": [r"[A-Z](类|级)基金份额", r"投资基金[A-Z](类|级)"],
                    "最低限额": [r"追加(单笔)?申购.*(最低金额|金额起点)"],
                    "销售平台": [r"追加(单笔)?申购.*(最低金额|金额起点)"],
                },
            },
            {
                "name": "subscription",
                "main_column": "销售平台",
                "depends": ["追加申购下限-原文"],
                "multi_config": {
                    "基金名称": True,
                    "最低限额": False,
                    "销售平台": False,
                },
                "para_regs": [
                    r"追加[^,.，。；;]*?([\d.\s,，]+千?百?万?元|无单笔最低限额)",
                    r"追加申购金额不限",
                ],
                "neglect_patterns": [
                    r"[A-Z][类级]基金(份额)?申购数量的?限制由.*?(?!调整为)",
                ],
                "regs": {
                    "基金名称": [
                        R_NON_MULTI_FUND_NAME,
                        rf"(申购|[、和或与]|(?<!持有本)基金){R_NON_PUNCTUATION}*?(?P<dst>[A-Z][类级]((基金)?份额)?)或[A-Z][类级]",
                        rf"(申购|[、和或与]|(?<!持有本)基金){R_NON_PUNCTUATION}*?(?P<dst>[A-Z][类级]((基金)?份额)?)(?!(类?(份额)?(基金)?(份额)?)?最.申购金额，将本基金[A-Z][类级])",
                        r"通过(基金)?管理人.{,10}办理(?P<dst>[^,.，。；;申购]*?货币[A-Z])",
                        rf"(申购|[、和或与]|(?<!持有本)基金){R_NON_PUNCTUATION}*?(?P<dst>[^,.，。；;申购]*?货币[A-Z])",
                        rf"(?<!持有本基金)(?P<dst>{R_FUND_SHORT_NAME})([\/、和或与]{R_FUND_SHORT_NAME})?{R_NON_PUNCTUATION}*?申购",
                        r"通过[^;；。]*?(?P<dst>[A-Z][类级]((基金)?份额)?)[^;；。]*?申购",
                    ],
                    "最低限额": [
                        rf"追加[^,.，。；;]*?{R_AMOUNT}(?!降至|调整为)",
                        r"追加申购(?P<dst>金额不限)",
                        r"(?P<dst>无单笔最低限额)",
                    ],
                    "销售平台": [
                        r"(?P<dst>代销网点、直销网上交易以及直销电话交易).*追加",
                        *gen_platform_regex("(认购(?!金额)|首次|申购)"),
                    ],
                },
                "neglect_answer_patterns": {
                    "销售平台": [
                        r"转入",
                    ]
                },
                "splits": [
                    r"[。；;](?![）)])",
                ],
                "split_punctuation": [
                    r"。",
                    r"[;；]",
                    r"[，,](?!(最低)?追加申购)",
                ],
            },
            {
                "name": "partial_text",
            },
        ],
    },
    {
        "path": ["调整后管理费率"],
        "models": [],
    },
    {
        "path": ["管理费率优惠开始日期"],
        "models": [],
    },
    {
        "path": ["调整后销售服务费率"],
        "models": [
            {
                "name": "partial_text",
            },
        ],
    },
    {
        "path": ["销售服务费率优惠开始日期"],
        "models": [
            {
                "name": "partial_text",
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
]


prophet_config = {
    "depends": {},
    "predictor_options": get_predictor_options(predictor_options),
}
