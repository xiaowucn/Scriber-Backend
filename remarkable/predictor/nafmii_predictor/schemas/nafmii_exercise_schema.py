# 行权公告
from remarkable.predictor.eltype import ElementType
from remarkable.predictor.nafmii_predictor.schemas.nafmii_payment_schema import get_amount_pattern_for_partial_text

rights_exercise = r"权利行使"
p_org_contact_info = [r"相关机构联系人和联系方式", rf"本次{rights_exercise}的?相关机构", "相关机构"]
p_amount = [
    r"(?P<dst>[\d,.]+)",
    r"(?P<dst>[零〇ΟOo壹贰叁肆伍陆柒捌玖拾佰仟萬億两一二三四五六七八九十百千万亿]+?)[万亿]元",
    r"(?P<dst>.*)",
]

# 投资人回售选择权
syllabus_regs_1 = [r"回售", r"权利行使基本情况"]
elements_nearby_1 = {
    "regs": [
        r"回售",
    ],
    "neglect_regs": [r"调整|重置|赎回"],
    "amount": 4,
    "step": -1,
}

# 发行人调整利率选择权
syllabus_regs_2 = [r"调整", r"本次权利行使基本情况"]


# 发行人重置债券基准利率选择权
syllabus_regs_3 = [r"重置", "本期.*基本情况"]
neglect_syllabus_regs_3 = [r"递延"]


# 发行人赎回选择权
elements_nearby_4 = {
    "regs": [
        r"赎回",
    ],
    "neglect_regs": [r"调整|重置|回售"],
    "amount": 4,
    "step": -1,
}

predictor_options = [
    {
        "path": ["债项代码01"],
    },
    {
        "path": ["债项代码02"],
    },
    {
        "path": ["债项代码03"],
    },
    {
        "path": ["债项简称01"],
    },
    {
        "path": ["债项简称02"],
    },
    {
        "path": ["债项简称03"],
    },
    {
        "path": ["债项全称01"],
        "models": [
            {
                "name": "fixed_position",
                "target_element": ElementType.PARAGRAPH.value,
                "merge_neighbor": [
                    {
                        "amount": 1,
                        "break_pattern": [
                            r"简称|代码",
                        ],
                        "aim_types": [
                            "PARAGRAPH",
                        ],
                    },
                    {
                        "amount": 1,
                        "break_pattern": [
                            r"简称|代码",
                        ],
                        "step": -1,
                        "aim_types": [
                            "PARAGRAPH",
                        ],
                    },
                ],
                "positions": list(range(0, 3)),
                "neglect_patterns": [r"简称|代码"],
                "regs": [
                    r"(关于)?(?P<dst>.*?)(\d+年)?(发行|投资)[者人].*(行权|结果)公告$",
                    r"(关于)?(?P<dst>.*?)行使.*公告$",
                    r"(关于)?(?P<dst>.*票据[）)]?)",
                ],
            },
        ],
    },
    {
        "path": ["公告名称"],
    },
    {
        "path": ["债项全称02"],
    },
    {
        "path": ["债项全称03"],
    },
    {
        "path": ["发行人名称01"],
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
    },
    {
        "path": ["发行人名称04"],  # 红章
    },
    {
        "path": ["发行人联系人"],
        "models": [
            {
                "name": "partial_text",
                "syllabus_regs": p_org_contact_info,
                "use_answer_pattern": False,
                "elements_nearby": {
                    "regs": [
                        r"发行人|企业[:：]",
                    ],
                    "amount": 2,
                    "step": -1,
                },
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
                        r"发行人|企业[:：]",
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
                "row_pattern": [r"(联系方式|电话)"],
                "content_pattern": [
                    r"(联系方式|电话)[:：](?P<dst>.*)",
                ],
            },
        ],
    },
    {
        "path": ["发行金额"],
    },
    {
        "path": ["起息日"],
    },
    {
        "path": ["发行期限"],
    },
    {
        "path": ["债项余额"],
    },
    {
        "path": ["最新评级情况"],
    },
    {
        "path": ["本计息期债项利率"],
    },
    {
        "path": ["主承销商"],
    },
    {
        "path": ["存续期管理机构01"],
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
                "name": "row_match",
                "elements_nearby": {
                    "regs": [
                        r"存续期管理",
                    ],
                    "amount": 1,
                    "step": -1,
                },
                "row_pattern": [r"单位名称"],
                "content_pattern": [
                    r"单位名称[:：](?P<dst>.*)",
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
    },
    {
        "path": ["存续期管理机构联系方式"],
    },
    {
        "path": ["受托管理人01"],
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
    },
    {
        "path": ["受托管理人联系方式"],
    },
    {
        "path": ["信用增进安排"],
    },
    {
        "path": ["登记托管机构01"],
    },
    {
        "path": ["登记托管机构02"],
    },
    {
        "path": ["登记托管机构03"],
    },
    {
        "path": ["登记托管机构联系部门"],
    },
    {
        "path": ["登记托管机构联系人"],
    },
    {
        "path": ["登记托管机构联系方式"],
    },
    {
        "path": ["公告披露日期"],
    },
    # 以上字段在[付息兑付安排公告]中存在 #
    {
        "path": ["行权类别01"],
        "models": [
            {
                "name": "partial_text",
                "regs": [
                    r"(?P<dst>(投资[人者]|发行[人者]|利率调整).*?)的?行[权使]公告",
                ],
                "split_pattern": r"[及和与、/]",
                "model_alternative": True,
            },
        ],
    },
    {
        "path": ["行权类别02"],
        "models": [
            {
                "name": "partial_text",
                "regs": [
                    r"(?P<dst>(投资|发行)[人者][\u4e00-\u9fa5、/“”]+(选择权|条款))",
                ],
                "split_pattern": r"”、“|[及和与、/]",
                "model_alternative": True,
            },
        ],
    },
    {
        "path": ["投资人回售申请开始日"],
        "models": [
            {
                "name": "partial_text",
                "regs": [r"投资[人者]回售申请开始日[:：](?P<dst>.+)"],
                "model_alternative": True,
            },
            {
                "name": "table_kv",
                "syllabus_regs": syllabus_regs_1,
            },
            {
                "name": "row_match",
                "row_pattern": [r"投资[人者]回售申请开始日"],
                "content_pattern": [r"[:：](?P<dst>.+)"],
                "syllabus_regs": syllabus_regs_1,
            },
        ],
    },
    {
        "path": ["投资人回售申请截止日"],
        "models": [
            {
                "name": "partial_text",
                "regs": [r"投资[人者]回售申请截止日[:：](?P<dst>.+)"],
                "model_alternative": True,
            },
            {
                "name": "table_kv",
                "syllabus_regs": syllabus_regs_1,
                "regs": [r"(?P<dst>.*?日)"],
            },
            {
                "name": "row_match",
                "row_pattern": [r"投资[人者]回售申请截止日"],
                "content_pattern": [r"[:：](?P<dst>.+)"],
                "syllabus_regs": syllabus_regs_1,
            },
        ],
    },
    {
        "path": ["回售价格"],
        "models": [
            {
                "name": "partial_text",
            },
            {
                "name": "table_kv",
                "syllabus_regs": syllabus_regs_1,
                "regs": [r"日(?P<dst>.*)"],
            },
            {
                "name": "row_match",
                "row_pattern": [r"回售价格"],
                "content_pattern": [r"[:：](?P<dst>.+)"],
                "syllabus_regs": syllabus_regs_1,
            },
        ],
    },
    {
        "path": ["行权日01"],
        "models": [
            {
                "name": "partial_text",
                "elements_nearby": elements_nearby_1,
                "regs": [
                    r"行权日[:：](?P<dst>.*日.*)",
                ],
                "model_alternative": True,
            },
            {
                "name": "table_kv",
                "syllabus_regs": syllabus_regs_1,
                "text_regs": [
                    r"回售",
                ],
            },
            {
                "name": "row_match",
                "row_pattern": [r"行权日"],
                "content_pattern": [r"[:：](?P<dst>.+)"],
                "syllabus_regs": syllabus_regs_1,
            },
        ],
    },
    {
        "path": ["原票面利率"],
        "models": [
            {
                "name": "partial_text",
            },
            {
                "name": "table_kv",
                "syllabus_regs": syllabus_regs_2,
            },
            {
                "name": "row_match",
                "row_pattern": [r"原票面利率"],
                "content_pattern": [r"[:：](?P<dst>.+)"],
                "syllabus_regs": syllabus_regs_2,
            },
        ],
    },
    {
        "path": ["上调、下调"],
        "models": [
            {
                "name": "partial_text",
                "regs": [
                    r"[:：](?P<dst>(上调|下调|调[减增]).*BP)",
                ],
                "model_alternative": True,
            },
            {
                "name": "table_kv",
                "feature_white_list": [r"票面利率调整|(调整|上调.下调)[(（]BP[）)]"],
                "syllabus_regs": syllabus_regs_2,
            },
            {
                "name": "row_match",
                "row_pattern": [r"^(上调|下调)"],
                "content_pattern": [r"(?P<dst>.+)"],
                "syllabus_regs": syllabus_regs_2,
            },
            {
                "name": "row_match",
                "row_pattern": [r"票面利率调整|(调整|上调.下调)[(（][Bb][Pp][）)]"],
                "content_pattern": [r"(票面利率调整|(调整|上调.下调)[(（][Bb][Pp][）)])[:：](?P<dst>.+)"],
                "syllabus_regs": syllabus_regs_2,
            },
        ],
    },
    {
        "path": ["调整后票面利率"],
        "models": [
            {
                "name": "partial_text",
                "regs": [
                    r"调整后票面利率[:：](?P<dst>.+)",
                ],
                "model_alternative": True,
            },
            {
                "name": "table_kv",
                "syllabus_regs": syllabus_regs_2,
            },
            {
                "name": "row_match",
                "row_pattern": [r"调整后票面利率"],
                "content_pattern": [r"[:：](?P<dst>.+)"],
                "syllabus_regs": syllabus_regs_2,
            },
        ],
    },
    {
        "path": ["利率生效日01"],
        "models": [
            {
                "name": "partial_text",
                "regs": [
                    r"利率生效日[:：](?P<dst>.*)",
                ],
                "model_alternative": True,
            },
            {
                "name": "table_kv",
                "syllabus_regs": syllabus_regs_2,
            },
            {
                "name": "row_match",
                "row_pattern": [r"利率生效日"],
                "content_pattern": [r"[:：](?P<dst>.+)"],
                "syllabus_regs": syllabus_regs_2,
            },
        ],
    },
    {
        "path": ["发行人赎回债券金额"],
        "models": [
            {
                "name": "table_kv_amount",
                "feature_white_list": [
                    r"__regex__发行人赎回(债券金额|面额)",
                ],
                "only_matched_value": True,
                "regs": {
                    "币种": [
                        r"(?P<dst>人民币|美元)",
                    ],
                    "金额": p_amount,
                    "金额单位": [
                        r"(?P<dst>.*)",
                    ],
                },
            },
            {
                "name": "partial_text",
                "regs": get_amount_pattern_for_partial_text("(发行人)?赎回(债券)?(金额|面额)"),
            },
        ],
    },
    {
        "path": ["赎回价格"],
        "models": [
            {
                "name": "table_kv",
            },
            {
                "name": "partial_text",
                "regs": [
                    r"赎回价格([(（].*[)）])?[:：](?P<dst>.*)",
                ],
            },
        ],
    },
    {
        "path": ["行权日02"],
        "models": [
            {
                "name": "table_kv",
                "text_regs": [
                    r"赎回",
                ],
            },
            {
                "name": "partial_text",
                "elements_nearby": elements_nearby_4,
                "regs": [
                    r"行权日[:：](?P<dst>.*日.*)",
                ],
            },
        ],
    },
    {
        "path": ["原基准利率"],
        "models": [
            {
                "name": "partial_text",
                "syllabus_regs": syllabus_regs_3,
            },
            {
                "name": "table_kv",
                "syllabus_regs": syllabus_regs_3,
            },
        ],
    },
    {
        "path": ["重置后基准利率"],
        "models": [
            {
                "name": "partial_text",
                "syllabus_regs": syllabus_regs_3,
                "neglect_syllabus_regs": neglect_syllabus_regs_3,
            },
            {
                "name": "table_kv",
                "syllabus_regs": syllabus_regs_3,
                "neglect_syllabus_regs": neglect_syllabus_regs_3,
            },
        ],
    },
    {
        "path": ["利率生效日02"],
        "models": [
            {
                "name": "partial_text",
                "syllabus_regs": syllabus_regs_3,
                "neglect_syllabus_regs": neglect_syllabus_regs_3,
            },
            {
                "name": "table_kv",
                "syllabus_regs": syllabus_regs_3,
                "neglect_syllabus_regs": neglect_syllabus_regs_3,
            },
        ],
    },
    {
        "path": ["本期利息支付总额"],
        "models": [
            {
                "name": "table_kv_amount",
                "feature_white_list": [
                    r"__regex__本期利息支付总额",
                ],
                "only_matched_value": True,
                "regs": {
                    "币种": [
                        r"(?P<dst>人民币|美元)",
                    ],
                    "金额": p_amount,
                    "金额单位": [
                        r"(?P<dst>.*)",
                    ],
                },
            },
        ],
    },
    {
        "path": ["本期利息递延支付金额"],
        "models": [
            {
                "name": "table_kv_amount",
                "feature_white_list": [
                    r"__regex__本期利息递延支付金额",
                ],
                "only_matched_value": True,
                "regs": {
                    "币种": [
                        r"(?P<dst>人民币|美元)",
                    ],
                    "金额": p_amount,
                    "金额单位": [
                        r"(?P<dst>.*)",
                    ],
                },
            },
        ],
    },
    {
        "path": ["下一个支付日"],
        "models": [
            {
                "name": "table_kv",
            },
        ],
    },
    {
        "path": ["下一支付日应付利息总额"],
        "models": [
            {
                "name": "table_kv_amount",
                "feature_white_list": [
                    r"__regex__下一支付日应付利息总额",
                ],
                "only_matched_value": True,
                "regs": {
                    "币种": [
                        r"(?P<dst>人民币|美元)",
                    ],
                    "金额": p_amount,
                    "金额单位": [
                        r"(?P<dst>.*)",
                    ],
                },
            },
        ],
    },
]


def get_predictor_options():
    """
    [付息兑付安排公告]中存在的字段，直接复用其配置
    :return:
    """
    from remarkable.predictor.nafmii_predictor.schemas.nafmii_payment_schema import predictor_options as payment_options

    payment_options_map = {}
    for option in payment_options:
        path_name = "".join(option["path"])
        payment_options_map[path_name] = option

    for option in predictor_options:
        path_name = "".join(option["path"])
        if "models" not in option and path_name in payment_options_map:
            option["models"] = payment_options_map[path_name]["models"]

    return predictor_options


prophet_config = {
    "depends": {},
    "predictor_options": get_predictor_options(),
}
