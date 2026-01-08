# 行权结果公告
from remarkable.predictor.nafmii_predictor.schemas.nafmii_exercise_schema import p_amount
from remarkable.predictor.nafmii_predictor.schemas.nafmii_payment_schema import get_amount_pattern_for_partial_text

syllabus_regs_1 = [r"(行权结果|回售)情况"]
rights_exercise = r"权利行使"
p_org_contact_info = [r"相关机构联系人和联系方式", rf"本次{rights_exercise}的?相关机构", "相关机构"]


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
    },
    {
        "path": ["公告名称"],
    },
    {
        "path": ["债项全称02"],
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
                    r"条款规定，(?P<dst>.*)[（(]债券简称",
                ],
            },
        ],
    },
    {
        "path": ["债项全称03"],
    },
    {
        "path": ["发行人名称01"],
    },
    {
        "path": ["发行人名称02"],
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
                    r"(联系人)[:：](?P<dst>.*)",
                ],
            },
            {
                "name": "partial_text",
                "regs": [
                    r"发行人[:：].*公司联系人[:：](?P<dst>.*)",
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
                        r"发行人|企业",
                    ],
                    "neglect_regs": [r"管理机构"],
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
            },
        ],
    },
    {
        "path": ["行权日"],
        "models": [
            {
                "name": "partial_text",
                "regs": [
                    r"行权日[:：](?P<dst>.*日.*)",
                ],
                "model_alternative": True,
            },
            {
                "name": "table_kv",
                "syllabus_regs": syllabus_regs_1,
            },
        ],
    },
    {
        "path": ["公告披露日期"],
    },
    # 以上字段在[行权公告]中存在 #
    {
        "path": ["本次回售金额"],
        "models": [
            {
                "name": "partial_text",
                "regs": get_amount_pattern_for_partial_text("本次回售金额"),
                "model_alternative": True,
            },
            {
                "name": "table_kv_amount",
                "syllabus_regs": syllabus_regs_1,
                "feature_white_list": [
                    r"__regex__回售金额",
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
        "path": ["未回售金额"],
        "models": [
            {
                "name": "partial_text",
                "regs": get_amount_pattern_for_partial_text("未回售金额"),
                "model_alternative": True,
            },
            {
                "name": "table_kv_amount",
                "syllabus_regs": syllabus_regs_1,
                "feature_white_list": [
                    r"__regex__未回售金额",
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
        "path": ["未回售部分债券票面利率"],
        "models": [
            {
                "name": "partial_text",
                "regs": [
                    r"未回售部分票面利率[:：](?P<dst>.+[%％])",
                ],
                "model_alternative": True,
            },
            {
                "name": "table_kv",
                "feature_white_list": [r"未回售部分票面利率"],
                "syllabus_regs": syllabus_regs_1,
            },
        ],
    },
]


def get_predictor_options():
    """
    [行权公告]中存在的字段，直接复用其配置
    :return:
    """
    from remarkable.predictor.nafmii_predictor.schemas.nafmii_exercise_schema import (
        predictor_options as exercise_options,
    )

    exercise_options_map = {}
    for option in exercise_options:
        path_name = "".join(option["path"])
        exercise_options_map[path_name] = option

    for option in predictor_options:
        path_name = "".join(option["path"])
        if "models" not in option and path_name in exercise_options_map:
            option["models"] = exercise_options_map[path_name]["models"]

    return predictor_options


prophet_config = {
    "depends": {},
    "predictor_options": get_predictor_options(),
}
