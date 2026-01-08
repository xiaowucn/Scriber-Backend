# 付息兑付安排公告
from remarkable.predictor.eltype import ElementType

repayment_category = r"([本兑付利息金/或及]{2,})"
p_org_contact_info = [r"相关机构联系人和联系方式", rf"本次{repayment_category}的?[相有]关机构"]
amount_regs = {
    "金额": [
        r"(?P<dst>[零〇ΟOo壹贰叁肆伍陆柒捌玖拾佰仟萬億两一二三四五六七八九十百千万亿]+?)[万亿]元",
        r"(?P<dst>[\d.．,，]+)",
        r"(?P<dst>.*)",
    ],
    "币种": [
        r"(?P<dst>人民币|美元)",
    ],
    "金额单位": [
        r"(?P<dst>.*)?",
    ],
}

R_BOND = r"(债[项券务](融资工具)?|票面)"

R_BASIC_SITUATION = rf"本期{R_BOND}基本情况$"


def get_amount_pattern_for_partial_text(key_word):
    return {
        "币种": [
            rf"{key_word}.*(?P<dst>人民币|美元)",
        ],
        "金额": [
            rf"{key_word}[:：](人民币|美元)?(?P<dst>[零〇ΟOo壹贰叁肆伍陆柒捌玖拾佰仟萬億两一二三四五六七八九十百千万亿]+?)[万亿千]元",
            rf"{key_word}[:：](人民币|美元)?(?P<dst>[\d.．,，]+)",
        ],
        "金额单位": [rf"{key_word}.*?(?P<dst>[亿万千元]+)"],
    }


def get_model_for_basic_situation_paragraph(key_word, para_config=None):
    if not para_config:
        para_config = {
            "paragraph_pattern": [rf"{key_word}([（(]如有[）)])?[:：]?(?P<content>.+)"],
        }
    return {
        "name": "syllabus_based",
        "inject_syllabus_features": [rf"__regex__{R_BASIC_SITUATION}"],
        "only_inject_features": True,
        "extract_from": "same_type_elements",
        "paragraph_model": "para_match",
        "para_config": para_config,
    }


def get_model_for_basic_situation_table(key_word):
    return {
        "name": "syllabus_based",
        "inject_syllabus_features": [rf"__regex__{R_BASIC_SITUATION}"],
        "only_inject_features": True,
        "extract_from": "same_type_elements",
        "paragraph_model": "para_match",
        "para_config": {
            "paragraph_pattern": {
                "金额": [
                    rf"{key_word}[:：].*?(?P<content>[\d.．,，]+)",
                ],
                "币种": [
                    rf"{key_word}[:：](?P<content>人民币|美元)",
                ],
                "金额单位": [
                    rf"{key_word}[:：].*?(?P<content>\d.*[\d亿万千元])",
                ],
            },
        },
    }


predictor_options = [
    {
        "path": ["债项代码01"],
        "models": [
            {
                "name": "elements_collector_based",
                "elements_collect_model": "fixed_position",
                "elements_collect_config": {
                    "target_element": ElementType.TABLE.value,
                    "positions": list(range(0, 1)),
                },
                "table_model": "cell_partial_text",
                "table_config": {
                    "filter_by": "col",
                    "regs": [
                        rf"{R_BOND}代码[:：]?(?P<dst>[^:：]+)",
                    ],
                },
            },
            {
                "name": "fixed_position",
                "positions": list(range(0, 1)),
                "regs": [
                    rf"{R_BOND}代码[:：](?P<dst>[0-9a-zA-Z.]+)",
                    r"(?P<dst>^[0-9a-zA-Z.]+)",
                ],
            },
        ],
    },
    {
        "path": ["债项代码02"],
        "models": [
            {
                "name": "partial_text",
                "use_answer_pattern": False,
                "regs": [
                    rf"{R_BOND}代码?[:：,，]?(?P<dst>[0-9a-zA-Z.]+)[)）]",
                    r"代码[:：,，](?P<dst>[0-9a-zA-Z.]+)[)）]",
                ],
                "model_alternative": True,
            },
        ],
    },
    {
        "path": ["债项代码03"],
        "models": [
            {
                "name": "table_kv",
                "feature_white_list": [
                    rf"__regex__{R_BOND}代码",
                ],
                "elements_nearby": {
                    "regs": [
                        R_BASIC_SITUATION,
                    ],
                    "amount": 2,
                    "step": -1,
                },
            },
            get_model_for_basic_situation_paragraph(key_word=f"{R_BOND}代码"),
        ],
    },
    {
        "path": ["债项简称01"],
        "models": [
            {
                "name": "cell_partial_text",
                "filter_by": "col",
                "from_cell": False,
                "neglect_answer_patterns": [rf"{R_BOND}代码"],
                "regs": [
                    rf"{R_BOND}简称[:：]?(?P<dst>[^:：]+)",
                ],
                "model_alternative": True,
            },
            {
                "name": "bond_abbr",
                "positions": list(range(0, 1)),
                "regs": [
                    rf"{R_BOND}简称[:：]?(?P<dst>[^:：]+){R_BOND}代码",
                    rf"{R_BOND}简称[:：]?(?P<dst>[^:：]+)",
                ],
                "neglect_patterns": [r"^关于|公告$"],
            },
        ],
    },
    {
        "path": ["债项简称02"],
        "models": [
            {
                "name": "partial_text",
                "use_answer_pattern": False,
                "merge_neighbor": [
                    {
                        "amount": 1,
                        "aim_types": [
                            "PARAGRAPH",
                        ],
                    },
                    {
                        "amount": 1,
                        "step": -1,
                        "aim_types": [
                            "PARAGRAPH",
                        ],
                    },
                ],
                "regs": [
                    rf"[(（，]{R_BOND}简称[:：]{R_BOND}简称[:：](?P<dst>[^,；.．，、，（(]*)",
                    rf"[(（，]{R_BOND}简称[:：](?P<dst>[^,；.．，、，]*?)[，（(]债券代码",
                    rf"[(（，]{R_BOND}简称[:：](?P<dst>[^,；.．，、，（(]*)",
                    r"[(（，]简称[:：](?P<dst>[^,；.．，、，（(]*)",
                ],
                "model_alternative": True,
            },
            {
                "name": "syllabus_based",
                "target_element": ElementType.TABLE.value,
                "include_title": False,
                "inject_syllabus_features": [r"__regex__本期债券基本情况$"],
                "only_inject_features": True,
                "table_model": "cell_partial_text",
                "table_config": {
                    "regs": [
                        rf"[(（，]{R_BOND}简称[:：](?P<dst>[^,；.．，、，（(]*)",
                        r"[(（，]简称[:：](?P<dst>[^,；.．，、，（(]*)",
                    ],
                },
            },
        ],
    },
    {
        "path": ["债项简称03"],
        "models": [
            {
                "name": "table_kv",
                "feature_white_list": [
                    rf"__regex__{R_BOND}简称",
                ],
                "elements_nearby": {
                    "regs": [
                        R_BASIC_SITUATION,
                    ],
                    "amount": 2,
                    "step": -1,
                },
            },
            get_model_for_basic_situation_paragraph(key_word=f"{R_BOND}简称"),
        ],
    },
    {
        "path": ["债项全称01"],
        "models": [
            {
                "name": "elements_collector_based",
                "elements_collect_model": "fixed_position",
                "elements_collect_config": {
                    "target_element": ElementType.PARAGRAPH.value,
                    "positions": list(range(0, 3)),
                },
                "paragraph_model": "middle_paras",
                "para_config": {
                    "use_direct_elements": True,
                    "include_bottom_anchor": True,
                    "top_anchor_regs": [
                        r"关于.*",
                        r"^上海机场.*",
                    ],
                    "top_anchor_content_regs": [r"(关于)?(?P<content>.*)"],
                    "bottom_anchor_regs": [r"安排公告"],
                    "bottom_anchor_content_regs": [r"(?P<content>.*?)(\d+年度?)?(兑付|付息|本息)"],
                },
            },
            {
                "name": "fixed_position",
                "target_element": ElementType.PARAGRAPH.value,
                "positions": list(range(0, 3)),
                "regs": [
                    rf"(关于)?(?P<dst>.*)(\d{{4}}年度?{repayment_category})",
                    r"(关于)?(?P<dst>.*?)(兑付|付息|本息)",
                ],
            },
            {
                "name": "fixed_position",
                "target_element": ElementType.PARAGRAPH.value,
                "positions": list(range(0, 3)),
                "anchor_regs": [r"\d{4}年兑付|\d{4}年付息安排公告"],
                "regs": [
                    r"关于(?P<dst>.*)",
                ],
            },
        ],
    },
    {
        "path": ["公告名称"],
        "models": [
            {
                "name": "elements_collector_based",
                "elements_collect_model": "fixed_position",
                "elements_collect_config": {
                    "target_element": ElementType.PARAGRAPH.value,
                    "positions": list(range(0, 3)),
                },
                "paragraph_model": "middle_paras",
                "para_config": {
                    "use_direct_elements": True,
                    "include_bottom_anchor": True,
                    "top_anchor_regs": [
                        r"关于.*",
                    ],
                    "bottom_anchor_regs": [r"公告$"],
                },
            },
            {
                "name": "elements_collector_based",
                "elements_collect_model": "elements_from_depends",
                "elements_collect_config": {
                    "depends": ["债项全称01"],
                },
                "paragraph_model": "para_match",
                "multi_elements": True,
                "para_config": {
                    "paragraph_pattern": [r".*"],
                },
            },
            {
                "name": "para_match",
                "paragraph_pattern": [
                    r"(关于)?.*公告",
                ],
            },
        ],
    },
    {
        "path": ["债项全称02"],
        "models": [
            {
                "name": "partial_text",
                "use_answer_pattern": False,
                "regs": [
                    r"为保证(?P<dst>[^(（，]*?)兑付",
                    rf"为保证(?P<dst>.*)[(（，]{R_BOND}简称",
                    rf"规定[,，](?P<dst>.*)[(（，]{R_BOND}简称",
                    r"为保证(?P<dst>.*)[(（，]简称",
                    rf"为保证(?P<dst>.*)\d{{4}}年{repayment_category}工作",
                ],
                "model_alternative": True,
            },
        ],
    },
    {
        "path": ["债项全称03"],
        "models": [
            {
                "name": "table_kv",
                "feature_white_list": [
                    rf"__regex__{R_BOND}[全名]称",
                ],
                "elements_nearby": {
                    "regs": [
                        R_BASIC_SITUATION,
                    ],
                    "amount": 2,
                    "step": -1,
                },
            },
            get_model_for_basic_situation_paragraph(key_word=f"{R_BOND}[全名]称"),
        ],
    },
    {
        "path": ["发行人名称01"],
        "models": [
            {
                "name": "table_kv",
                "feature_white_list": [
                    r"__regex__(发行人|企业)(名称)?",
                ],
                "elements_nearby": {
                    "regs": [
                        R_BASIC_SITUATION,
                    ],
                    "amount": 2,
                    "step": -1,
                },
            },
            get_model_for_basic_situation_paragraph(key_word="发行人(名称)?"),
        ],
    },
    {
        "path": ["发行人名称02"],
        "models": [
            {
                "name": "partial_text",
                "syllabus_regs": p_org_contact_info,
                "use_answer_pattern": False,
                "regs": [
                    r"(发行人|发起机构|企业)[:：](?P<dst>.*)联系人",
                    r"(发行人|发起机构|企业)[:：](?P<dst>.*?公司)",
                    r"(发行人|发起机构|企业)[:：](?P<dst>.*)",
                ],
                "model_alternative": True,
            },
            {
                "name": "row_match",
                "syllabus_regs": p_org_contact_info,
                "row_pattern": [r"发行人"],
                "content_pattern": [
                    r"(发行人|发起机构|企业)[:：](?P<dst>.*)",
                ],
            },
            {
                "name": "row_match",
                "syllabus_regs": [r"发行人|企业"],
                "row_pattern": [r"名称"],
                "content_pattern": [
                    r"名称[:：](?P<dst>.*)",
                ],
            },
        ],
    },
    {
        "path": ["发行人名称03"],
        "models": [
            {
                "name": "fixed_position",
                "target_element": ElementType.PARAGRAPH.value,
                "positions": list(range(-5, 0))[::-1],
                "neglect_patterns": [r"本页|盖章"],
                "regs": [
                    r"(?P<dst>.{5,}公司)",
                ],
            },
        ],
    },
    {
        "path": ["发行人名称04"],  # 红章
        "models": [
            {
                "name": "company_stamp",
                "target_element": ElementType.STAMP.value,
                "positions": list(range(-4, 0))[::-1],
                "regs": [r"(?P<dst>[\u4e00-\u9fa5(（）)]{5,})"],
                "neglect_patterns": [r"^.{1,3}有限(公司)?"],
            },
        ],
    },
    {
        "path": ["发行人联系人"],
        "models": [
            {
                "name": "partial_text",
                "syllabus_regs": p_org_contact_info,
                "elements_nearby": {
                    "regs": [
                        r"发行人|企业",
                    ],
                    "neglect_regs": [r"管理机构"],
                    "amount": 2,
                    "step": -1,
                },
                "use_answer_pattern": False,
                "regs": [
                    r"联系人[:：](?P<dst>.*)联系方式",
                    r"联系人[:：](?P<dst>.*)",
                ],
                "model_alternative": True,
            },
            {
                "name": "row_match",
                "syllabus_regs": p_org_contact_info,
                "row_pattern": [r"联系人"],
                "content_pattern": [
                    r"联系人[:：](?P<dst>.*)",
                ],
            },
        ],
    },
    {
        "path": ["发行人联系方式"],
        "models": [
            {
                "name": "partial_text",
                "syllabus_regs": p_org_contact_info,
                "elements_nearby": {
                    "regs": [
                        r"发行人",
                    ],
                    "amount": 3,
                    "step": -1,
                },
                "use_answer_pattern": False,
                "regs": [
                    r"(联系方式|电话)[:：](?P<dst>.*)",
                ],
                "model_alternative": True,
            },
            {
                "name": "row_match",
                "syllabus_regs": p_org_contact_info,
                "row_pattern": [
                    r"联系方式",
                    r"电话",
                ],
                "content_pattern": [
                    r"(联系方式|电话)[:：](?P<dst>.*)",
                ],
            },
        ],
    },
    {
        "path": ["发行金额"],
        "models": [
            {
                "name": "table_kv_amount",
                "elements_nearby": {
                    "regs": [
                        R_BASIC_SITUATION,
                    ],
                    "amount": 2,
                    "step": -1,
                },
                "feature_white_list": [
                    r"__regex__发行[金总]+额",
                ],
                "only_matched_value": True,
                "regs": amount_regs,
            },
            get_model_for_basic_situation_table(key_word="发行[金总]+额"),
        ],
    },
    {
        "path": ["起息日"],
        "models": [
            {
                "name": "table_kv",
                "feature_white_list": [
                    r"__regex__起息日",
                ],
                "elements_nearby": {
                    "regs": [
                        R_BASIC_SITUATION,
                    ],
                    "amount": 2,
                    "step": -1,
                },
            },
            get_model_for_basic_situation_paragraph(key_word="起息日"),
        ],
    },
    {
        "path": ["发行期限"],
        "models": [
            {
                "name": "table_kv_amount",
                "feature_white_list": [
                    r"__regex__发行期限",
                ],
                "elements_nearby": {
                    "regs": [
                        R_BASIC_SITUATION,
                    ],
                    "amount": 2,
                    "step": -1,
                },
                "regs": {"期限": [r"(?P<dst>.*?)[年月日天]"], "期限单位": [r"(?P<dst>[年月日天])"]},
            },
            get_model_for_basic_situation_paragraph(
                key_word="(发行|债券)期限",
                para_config={
                    "paragraph_pattern": {
                        "期限": [r"(发行|债券)期限[:：]?(?P<content>.*?)[年月日天]"],
                        "期限单位": [r"(发行|债券)期限[:：]?.*?(?P<content>[年月日天])"],
                    }
                },
            ),
        ],
    },
    {
        "path": ["债项余额"],
        "models": [
            {
                "name": "table_kv_amount",
                "elements_nearby": {
                    "regs": [
                        R_BASIC_SITUATION,
                    ],
                    "amount": 2,
                    "step": -1,
                },
                "feature_white_list": [
                    rf"__regex__{R_BOND}余额",
                ],
                "only_matched_value": True,
                "regs": amount_regs,
            },
            get_model_for_basic_situation_table(key_word=f"{R_BOND}余额"),
        ],
    },
    {
        "path": ["最新评级情况"],
        "models": [
            {
                "name": "table_kv",
                "feature_white_list": [
                    r"__regex__最新(主体)?评级情况",
                    r"__regex__评级情况",
                ],
                "elements_nearby": {
                    "regs": [
                        R_BASIC_SITUATION,
                    ],
                    "amount": 2,
                    "step": -1,
                },
                "regs": [r"(?P<dst>.*?)\d"],
            },
            get_model_for_basic_situation_paragraph(
                key_word=r"评级情况([(（].*[)）])?",
                para_config={
                    "neglect_regs": [r"[:：]$"],
                    "paragraph_pattern": ["评级情况([(（].*[)）])?[:：]?(?P<content>.+)"],
                },
            ),
        ],
    },
    {
        "path": ["偿还类别01"],
        "models": [
            {
                "name": "table_kv",
                "feature_white_list": [
                    r"__regex__偿还类别",
                ],
                "only_matched_value": True,
                "multi": True,
                "regs": [
                    r"[■☑](?P<dst>.*?)(偿还类别|□)",
                    r"[■☑](?P<dst>.*[兑支]付)$",
                ],
            },
            {
                "name": "table_kv",
                "feature_white_list": [
                    r"__regex__偿还类别",
                ],
                "regs": [
                    r"[■☑](?P<dst>.*?)(偿还类别|□)",
                    r"[■☑](?P<dst>.*[兑支]付)$",
                ],
            },
            {
                "name": "partial_text",
                "regs": [
                    r"[■☑](?P<dst>.*?)(偿还类别|□)",
                    r"[■☑](?P<dst>.*[兑支]付)$",
                ],
            },
        ],
    },
    {
        "path": ["偿还类别02"],
        "models": [
            {
                "name": "partial_text",
                "use_answer_pattern": False,
                "regs": [
                    rf"(?P<dst>{repayment_category})(安排)?公告",
                ],
                "model_alternative": True,
            },
        ],
    },
    {
        "path": ["偿还类别03"],
        "models": [
            {
                "name": "partial_text",
                "use_answer_pattern": False,
                "regs": [
                    rf"(?P<dst>{repayment_category})工作的顺利进行",
                ],
                "model_alternative": True,
            },
        ],
    },
    {
        "path": ["偿还类别04"],
        "models": [
            {
                "name": "cell_partial_text",
                "regs": [
                    r"(?P<dst>.*(付息|利息|本金|本息)([支兑]付)?日.*)",
                ],
                "model_alternative": True,
            },
            {
                "name": "syllabus_based",
                "include_title": False,
                "inject_syllabus_features": [r"__regex__本期债券基本情况$"],
                "only_inject_features": True,
                "para_model": "partial_text",
                "para_config": {
                    "regs": [
                        r"(?P<dst>.*(付息|利息|本金|本息)([支兑]付)?日)",
                    ],
                },
            },
        ],
    },
    {
        "path": ["偿还类别05"],
        "models": [
            {
                "name": "cell_partial_text",
                "multi": False,
                "regs": [
                    rf"(?P<dst>(本期)?应偿付{repayment_category}金额)",
                ],
                "model_alternative": True,
            },
            {
                "name": "partial_text",
                "use_answer_pattern": False,
                "regs": [rf"(?P<dst>(本期)?应偿付{repayment_category})"],
            },
            {
                "name": "syllabus_based",
                "include_title": False,
                "inject_syllabus_features": [r"__regex__本期债券基本情况$"],
                "only_inject_features": True,
                "para_model": "partial_text",
                "para_config": {
                    "regs": [
                        rf"(?P<dst>(本期)?应偿付{repayment_category})",
                    ],
                },
            },
        ],
    },
    {
        "path": ["偿还类别06"],
        "models": [
            {
                "name": "partial_text",
                "use_answer_pattern": False,
                "regs": [r"(?P<dst>[^,;:，、]+)(相关事宜|办法)"],
                "model_alternative": True,
            },
        ],
    },
    {
        "path": ["偿还类别07"],
        "models": [
            {
                "name": "partial_text",
                "use_answer_pattern": False,
                "regs": [rf"的{R_BOND}.其(?P<dst>{repayment_category})资金由"],
                "model_alternative": True,
            },
        ],
    },
    {
        "path": ["偿还类别08"],
        "models": [
            {
                "name": "partial_text",
                "use_answer_pattern": False,
                "regs": [
                    rf"由.*?在(?P<dst>{repayment_category})日划付至{R_BOND}持有人",
                    rf"由.*?在(?P<dst>[\d年月日]+)划付至{R_BOND}持有人",
                ],
                "model_alternative": True,
            },
        ],
    },
    {
        "path": ["偿还类别09"],
        "models": [
            {
                "name": "partial_text",
                "use_answer_pattern": False,
                "regs": [
                    rf"日划付至{R_BOND}持有人指定的银行账户.{R_BOND}(?P<dst>{repayment_category})日如遇法定节假日",
                    rf"日划付至{R_BOND}持有人指定的银行账户.{R_BOND}(?P<dst>.*)日如遇法定节假日",
                ],
                "model_alternative": True,
            },
        ],
    },
    {
        "path": ["偿还类别10"],
        "models": [
            {
                "name": "partial_text",
                "use_answer_pattern": False,
                "regs": [
                    rf"路径变更.?应在(?P<dst>{repayment_category})前将新的资金汇划路径",
                    r"路径变更.?应在(?P<dst>[\d年月日]+)前将新的资金汇划路径",
                ],
                "model_alternative": True,
            },
        ],
    },
    {
        "path": ["本计息期债项利率"],
        "models": [
            {
                "name": "table_kv",
                "feature_white_list": [
                    rf"__regex__本计息期{R_BOND}利率",
                ],
                "regs": [r"(?P<dst>[\d.%]+)"],
                "elements_nearby": {
                    "regs": [
                        R_BASIC_SITUATION,
                    ],
                    "amount": 2,
                    "step": -1,
                },
            },
            get_model_for_basic_situation_paragraph(key_word=f"本计息期{R_BOND}(年)?利率?"),
        ],
    },
    {
        "path": ["兑付日"],
        "models": [
            {
                "name": "table_kv",
                "elements_nearby": {
                    "regs": [
                        R_BASIC_SITUATION,
                    ],
                    "amount": 2,
                    "step": -1,
                },
                "feature_white_list": [
                    r"__regex__(兑付|付息|利息)(支付)?日",
                ],
                "regs": [r"(?P<dst>.+[(（].+[）)])"],
            },
            get_model_for_basic_situation_paragraph(key_word="(兑付|付息|利息)(支付)?日"),
        ],
    },
    {
        "path": ["本期应偿付金额"],
        "models": [
            {
                "name": "table_kv_amount",
                "elements_nearby": {
                    "regs": [
                        R_BASIC_SITUATION,
                    ],
                    "amount": 2,
                    "step": -1,
                },
                "feature_white_list": [
                    r"__regex__本期应偿(付|还)(本息|利息)?.*[金总]+额",
                ],
                # "regs": [
                #     r"(?P<dst>[\d,.．，万亿元(（）)]+)",
                #     r"日[）)]?(?P<dst>\d.*)",
                # ],
                "only_matched_value": True,
                "regs": amount_regs,
            },
            get_model_for_basic_situation_table(key_word="本期应偿(付|还)(本息|利息)?.*[金总]+额"),
        ],
    },
    {
        "path": ["宽限期约定"],
        "models": [
            {
                "name": "table_kv",
                "elements_nearby": {
                    "regs": [
                        R_BASIC_SITUATION,
                    ],
                    "amount": 2,
                    "step": -1,
                },
                "feature_white_list": [
                    r"__regex__宽限期约定",
                ],
                "regs": [r"(?P<dst>[无/\\]$)"],
            },
            get_model_for_basic_situation_paragraph(key_word="宽限期约定"),
        ],
    },
    {
        "path": ["主承销商"],
        "models": [
            {
                "name": "table_kv",
                "elements_nearby": {
                    "regs": [
                        R_BASIC_SITUATION,
                    ],
                    "amount": 2,
                    "step": -1,
                },
                "feature_white_list": [
                    r"__regex__主承销商",
                ],
                "regs": [r"(0元)?(?P<dst>[\u4e00-\u9fa5].*)"],
            },
            get_model_for_basic_situation_paragraph(key_word="主承销商"),
        ],
    },
    {
        "path": ["存续期管理机构01"],
        "models": [
            {
                "name": "table_kv",
                "feature_white_list": [
                    r"__regex__存续期管理机构",
                ],
                "elements_nearby": {
                    "regs": [
                        R_BASIC_SITUATION,
                    ],
                    "amount": 2,
                    "step": -1,
                },
            },
            get_model_for_basic_situation_paragraph(key_word="存续期管理机构"),
        ],
    },
    {
        "path": ["存续期管理机构02"],
        "models": [
            {
                "name": "partial_text",
                "syllabus_regs": p_org_contact_info,
                "use_answer_pattern": False,
                "regs": [
                    r"存续期管理机构[:：](?P<dst>.*)联系人",
                    r"存续期管理机构[:：](?P<dst>.*)",
                ],
                "model_alternative": True,
            },
            {
                "name": "partial_text",
                "syllabus_regs": [
                    r"存续期管理机构$",
                ],
                "use_answer_pattern": False,
                "regs": [
                    r"名称[:：](?P<dst>.*)联系人",
                    r"名称[:：](?P<dst>.*)",
                ],
                "model_alternative": True,
            },
            {
                "name": "partial_text",
                "syllabus_regs": [r"存续期管理(机构)?"],
                "use_answer_pattern": False,
                "regs": [
                    r"机构[:：](?P<dst>.*)",
                ],
                "model_alternative": True,
            },
            {
                "name": "row_match",
                "syllabus_regs": p_org_contact_info,
                "row_pattern": [r"存续期管理(机构)?"],
                "content_pattern": [
                    r"存续期管理(机构)?.*[:：](?P<dst>.*)",
                ],
            },
            {
                "name": "para_match",
                "paragraph_pattern": [r".*公司"],
                "anchor_regs": [r"存续期管理(机构)?"],
            },
        ],
    },
    {
        "path": ["存续期管理机构联系人"],
        "models": [
            {
                "name": "partial_text",
                "syllabus_regs": [
                    r"存续期管理(机构)?",
                    *p_org_contact_info,
                ],
                "use_answer_pattern": False,
                "regs": [
                    r"联系人[:：](?P<dst>.*)联系方式",
                    r"联系人[:：](?P<dst>.*)",
                ],
                "model_alternative": True,
            },
            {
                "name": "row_match",
                "syllabus_regs": [r"存续期管理(机构)?"],
                "row_pattern": [r"联系人"],
                "content_pattern": [
                    r"联系人[:：](?P<dst>.*)",
                ],
            },
            {
                "name": "row_match",
                "syllabus_regs": p_org_contact_info,
                "top_anchor_range_patterns": [
                    r"存续期管理(机构)?",
                ],
                "row_pattern": [r"联系人"],
                "content_pattern": [
                    r"联系人[:：](?P<dst>.*)",
                ],
            },
        ],
    },
    {
        "path": ["存续期管理机构联系方式"],
        "models": [
            {
                "name": "partial_text",
                "syllabus_regs": [
                    r"存续期管理(机构)?",
                    *p_org_contact_info,
                ],
                "use_answer_pattern": False,
                "regs": [
                    r"(联系方式|电话)[:：](?P<dst>.*)",
                ],
                "model_alternative": True,
            },
            {
                "name": "row_match",
                "syllabus_regs": [r"存续期管理(机构)?"],
                "row_pattern": [r"(联系方式|电话)"],
                "content_pattern": [
                    r"(联系方式|电话)[:：](?P<dst>.*)",
                ],
            },
            {
                "name": "row_match",
                "syllabus_regs": p_org_contact_info,
                "top_anchor_range_patterns": [
                    r"存续期管理(机构)?",
                ],
                "row_pattern": [r"(联系方式|电话)"],
                "content_pattern": [
                    r"(联系方式|电话)[:：](?P<dst>.*)",
                ],
            },
        ],
    },
    {
        "path": ["受托管理人01"],
        "models": [
            {
                "name": "table_kv",
                "text_regs": [
                    r"受托管理人",
                ],
                "feature_white_list": [
                    r"__regex__受托管理人",
                ],
                "regs": [
                    r"(?P<dst>无)",
                ],
            },
            get_model_for_basic_situation_paragraph(key_word="受托管理人"),
        ],
    },
    {
        "path": ["受托管理人02"],
        "models": [
            {
                "name": "partial_text",
                "syllabus_regs": p_org_contact_info,
                "use_answer_pattern": False,
                "regs": [
                    r"受托管理人.*[:：](?P<dst>.*)联系人",
                    r"受托管理人.*[:：](?P<dst>.*)",
                ],
                "model_alternative": True,
            },
            {
                "name": "para_match",
                "anchor_regs": [r"受托管理人（如有）"],
                "paragraph_pattern": [
                    r"^无$",
                ],
            },
            {
                "name": "row_match",
                "syllabus_regs": p_org_contact_info,
                "row_pattern": [r"受托管理人"],
                "content_pattern": [
                    r"受托管理人.*[:：](?P<dst>.*)",
                ],
            },
        ],
    },
    {
        "path": ["受托管理人联系人"],
        "models": [
            {
                "name": "partial_text",
                "syllabus_regs": [r"受托管理人"],
                "use_answer_pattern": False,
                "regs": [
                    r"联系人[:：](?P<dst>.*)联系方式",
                    r"联系人[:：](?P<dst>.*)",
                ],
                "model_alternative": True,
            },
        ],
    },
    {
        "path": ["受托管理人联系方式"],
        "models": [
            {
                "name": "partial_text",
                "syllabus_regs": [r"受托管理人"],
                "use_answer_pattern": False,
                "regs": [
                    r"(联系方式|电话)[:：](?P<dst>.*)",
                ],
                "model_alternative": True,
            },
            {
                "name": "row_match",
                "syllabus_regs": [r"受托管理人"],
                "row_pattern": [r"(联系方式|电话)"],
                "content_pattern": [
                    r"(联系方式|电话)[:：](?P<dst>.*)",
                ],
            },
        ],
    },
    {
        "path": ["信用增进安排"],
        "models": [
            {
                "name": "table_kv",
                "elements_nearby": {
                    "regs": [
                        R_BASIC_SITUATION,
                    ],
                    "amount": 2,
                    "step": -1,
                },
                "feature_white_list": [
                    r"__regex__信用增进安排",
                ],
                "regs": [r"(?P<dst>无$)"],
            },
            get_model_for_basic_situation_paragraph(key_word="信用增进安排"),
        ],
    },
    {
        "path": ["登记托管机构01"],
        "models": [
            {
                "name": "table_kv",
                "elements_nearby": {
                    "regs": [
                        R_BASIC_SITUATION,
                    ],
                    "amount": 2,
                    "step": -1,
                },
                "feature_white_list": [
                    r"__regex__(登记)?托管机构",
                ],
            },
            get_model_for_basic_situation_paragraph(key_word="托管机构"),
        ],
    },
    {
        "path": ["登记托管机构02"],
        "models": [
            {
                "name": "partial_text",
                "use_answer_pattern": False,
                "regs": [
                    rf"托管在(?P<dst>.*?)([(（]以下简称.*[)）])?的{R_BOND}",
                ],
                "model_alternative": True,
            },
        ],
    },
    {
        "path": ["登记托管机构03"],
        "models": [
            {
                "name": "partial_text",
                "use_answer_pattern": False,
                "regs": [
                    r"划付至(?P<dst>.*?)(指定)?的(收款|银行)账户",
                    r"登记托管机构[:：](?P<dst>.*)",
                ],
                "model_alternative": True,
            },
            {
                "name": "row_match",
                "row_pattern": [r"托管机构"],
                "content_pattern": [
                    r"托管机构[:：](?P<dst>.*)",
                ],
            },
        ],
    },
    {
        "path": ["登记托管机构联系部门"],
        "models": [
            {
                "name": "partial_text",
                "syllabus_regs": [
                    r"(登记)?托管机构",
                    r"相关机构联系人和联系方式",
                    r"本次权利行使相关机构",
                ],
                "elements_nearby": {
                    "regs": [
                        r"托管机构",
                    ],
                    "amount": 2,
                    "step": -1,
                },
                "use_answer_pattern": False,
                "regs": [
                    r"联系部门[:：](?P<dst>.*)联系人",
                    r"联系部门[:：](?P<dst>.*)",
                ],
            },
            {
                "name": "row_match",
                "text_regs": [r"(登记)?托管机构"],
                "row_pattern": [r"联系部门"],
                "content_pattern": [
                    r"联系部门[:：](?P<dst>.*)",
                ],
            },
            {
                "name": "row_match",
                "elements_nearby": {
                    "regs": [
                        r"托管机构",
                    ],
                    "amount": 1,
                    "step": -1,
                },
                "row_pattern": [r"联系部门"],
                "content_pattern": [
                    r"联系部门[:：](?P<dst>.*)",
                ],
            },
            {
                "name": "row_match",
                "syllabus_regs": [
                    *p_org_contact_info,
                ],
                "top_anchor_range_patterns": [
                    r"(登记)?托管机构",
                ],
                "row_pattern": [r"联系部门"],
                "content_pattern": [
                    r"联系部门[:：](?P<dst>.*)",
                ],
            },
            {
                "name": "middle_paras",
                "table_regarded_as_paras": True,
                "use_syllabus_model": True,
                "inject_syllabus_features": [r"__regex__本次权利行使相关机构"],
                "only_inject_features": True,
                "top_anchor_regs": [r"托管机构"],
                "include_top_anchor": False,
                "bottom_anchor_regs": [r"联系部门"],
                "include_bottom_anchor": True,
                "bottom_anchor_content_regs": [
                    r"联系部门[:：](?P<content>.*)",
                ],
            },
        ],
    },
    {
        "path": ["登记托管机构联系人"],
        "models": [
            {
                "name": "partial_text",
                "syllabus_regs": [
                    r"(登记)?托管机构",
                    r"相关机构联系人和联系方式",
                    r"本次权利行使相关机构",
                ],
                "elements_nearby": {
                    "regs": [
                        r"托管机构",
                    ],
                    "amount": 2,
                    "step": -1,
                },
                "use_answer_pattern": False,
                "regs": [
                    r"联系人[:：](?P<dst>.*)联系方式",
                    r"联系人[:：](?P<dst>.*)",
                ],
                "model_alternative": True,
            },
            {
                "name": "row_match",
                "syllabus_regs": [r"(登记)?托管机构"],
                "row_pattern": [r"联系人"],
                "content_pattern": [
                    r"联系人[:：](?P<dst>.*)",
                ],
            },
            {
                "name": "row_match",
                "elements_nearby": {
                    "regs": [
                        r"托管机构",
                    ],
                    "amount": 1,
                    "step": -1,
                },
                "row_pattern": [r"联系人"],
                "content_pattern": [
                    r"联系人[:：](?P<dst>.*)",
                ],
            },
            {
                "name": "row_match",
                "syllabus_regs": [
                    *p_org_contact_info,
                ],
                "top_anchor_range_patterns": [
                    r"(登记)?托管机构",
                ],
                "row_pattern": [r"联系人"],
                "content_pattern": [
                    r"联系人[:：](?P<dst>.*)",
                ],
            },
        ],
    },
    {
        "path": ["登记托管机构联系方式"],
        "models": [
            {
                "name": "partial_text",
                "syllabus_regs": [
                    r"(登记)?托管机构",
                    r"相关机构联系人和联系方式",
                    r"本次权利行使相关机构",
                ],
                "elements_nearby": {
                    "regs": [
                        r"托管机构",
                    ],
                    "amount": 4,
                    "step": -1,
                },
                "use_answer_pattern": False,
                "regs": [
                    r"(联系方式|电话)[:：](?P<dst>.*)",
                ],
                "model_alternative": True,
            },
            {
                "name": "row_match",
                "syllabus_regs": [r"(登记)?托管机构"],
                "row_pattern": [r"(联系方式|电话)"],
                "content_pattern": [
                    r"(联系方式|电话)[:：](?P<dst>.*)",
                ],
            },
            {
                "name": "row_match",
                "elements_nearby": {
                    "regs": [
                        r"托管机构",
                    ],
                    "amount": 1,
                    "step": -1,
                },
                "row_pattern": [r"(联系方式|电话)"],
                "content_pattern": [
                    r"(联系方式|电话)[:：](?P<dst>.*)",
                ],
            },
            {
                "name": "row_match",
                "syllabus_regs": [
                    *p_org_contact_info,
                ],
                "top_anchor_range_patterns": [
                    r"(登记)?托管机构",
                ],
                "row_pattern": [r"(联系方式|电话)"],
                "content_pattern": [
                    r"(联系方式|电话)[:：](?P<dst>.*)",
                ],
            },
        ],
    },
    {
        "path": ["公告披露日期"],
        "models": [
            {
                "name": "fixed_position",
                "target_element": ElementType.PARAGRAPH.value,
                "positions": list(range(-3, 0))[::-1],
                "regs": [
                    r"(?P<dst>.*年.*月.*日)",
                    r"(?P<dst>[\d年月日一二三四五六七八九十]{6,})",
                ],
            },
        ],
    },
    {
        "path": ["登记托管机构04"],
        "models": [
            {
                "name": "partial_text",
                "use_answer_pattern": False,
                "regs": [
                    rf"划付至.*?的收款账户后.由(?P<dst>.*?)在[\d年月日]+划付至{R_BOND}持有人",
                    r"划付至.*?的收款账户后.由(?P<dst>.*?)在(付息|兑付)",
                ],
                "model_alternative": True,
            },
        ],
    },
    {
        "path": ["登记托管机构05"],
        "models": [
            {
                "name": "partial_text",
                "use_answer_pattern": False,
                "regs": [
                    rf"及时通知(?P<dst>.*?).因{R_BOND}",
                ],
                "model_alternative": True,
            },
        ],
    },
    {
        "path": ["登记托管机构06"],
        "models": [
            {
                "name": "partial_text",
                "use_answer_pattern": False,
                "regs": [
                    r"未及时通知(?P<dst>.*?)而不能",
                ],
                "model_alternative": True,
            },
        ],
    },
    {
        "path": ["登记托管机构07"],
        "models": [
            {
                "name": "partial_text",
                "use_answer_pattern": False,
                "regs": [
                    r"(发行人|本公司)及(?P<dst>.*?)不承担[由因]此",
                ],
                "model_alternative": True,
            },
        ],
    },
    {
        "path": ["登记托管机构08"],
        "models": [
            {
                "name": "partial_text",
                "syllabus_regs": p_org_contact_info,
                "use_answer_pattern": False,
                "regs": [
                    r"(登记)?托管机构[:：](?P<dst>.*有限公司)",
                ],
                "model_alternative": True,
            },
            {
                "name": "row_match",
                "syllabus_regs": p_org_contact_info,
                "row_pattern": [r"(登记)?托管机构"],
                "content_pattern": [
                    r"(登记)?托管机构[:：](?P<dst>.*有限公司)",
                ],
            },
        ],
    },
]

prophet_config = {
    "depends": {},
    "predictor_options": predictor_options,
}
