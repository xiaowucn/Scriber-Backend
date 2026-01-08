# 富国基金

R_COMPARE = r"(低于|高于|超过)"

predictor_options = [
    {
        "path": ["基金合同类型"],
        "models": [
            {
                "name": "middle_paras",
                "table_regarded_as_paras": True,
                "top_anchor_regs": [
                    r"富国基金管理有限公司",
                ],
                "bottom_anchor_regs": [
                    r"基金管理人",
                ],
                "top_anchor_range_regs": [r".*"],
                "bottom_anchor_range_regs": [r"目录|前言"],
                "include_top_anchor": False,
            },
            {
                "name": "fixed_position",
                "pages": [0],
                "regs": [
                    r"(富国基金管理有限公司)?(?P<dst>.*(开放|债券?|股票|混合|联接|货币|FOF|ETF|QDII?).*)",
                ],
            },
            {
                "name": "syllabus_based",
                "inject_syllabus_features": [r"__regex__基金的基本情况__regex__基金的?名称"],
                "only_inject_features": True,
                "paragraph_model": "para_match",
                "para_config": {
                    "paragraph_pattern": [
                        r"开放|债券?|股票|混合|联接|货币|FOF|ETF|QDII?",
                    ],
                },
            },
            {
                "name": "syllabus_elt_v2",
                "inject_syllabus_features": [r"__regex__基金的基本情况__regex__基金的?类别"],
                "only_inject_features": True,
            },
        ],
    },
    {
        "path": ["60001 产品中文全称"],
        "models": [
            {
                "name": "syllabus_elt_v2",
                "break_para_pattern": [
                    r"^[一二三四五]、",
                ],
            },
        ],
    },
    {
        "path": ["60011 产品中文简称_监管报送"],
        "models": [
            {
                "name": "product_abb_submission",
                "depends": ["60001 产品中文全称"],
                "replace_pairs": (
                    # 替换/去除规则：
                    #     1、首先在60001提取答案的基础上去掉“证券投资基金”
                    #     2、其次检索到以“市场基金”结尾，直接在60001的基础上去掉“市场基金”这4个字
                    #     3、然后如果60001的答案中还能匹配到“交易型开放式指数”，需要用“ETF”将该段中文字样转换
                    #     4、匹配到““XXX证券投资基金联接基金””，还需要把最后的那个“基金”去除
                    #     5、最后如果还检测到“混合型”、“债券型”、“股票型”、“指数型”，需要把“型”去掉
                    #     6、最后如果有FOF, 又检测到“基金中基金”，需要把“基金中基金”去除
                    (r"证券投资基金", ""),
                    (r"(.*)(?:证券投资|市场)基金$", r"\1"),
                    (r"交易型开放式指数", "ETF"),
                    (r"(.*联接)基金$", r"\1"),
                    (r"(.*(?:混合|债券|股票|指数))型", r"\1"),
                    (r"基金中[的得]?基金(?=[(（]?FOF[)）]?)", ""),
                ),
            },
        ],
    },
    {
        "path": ["200136 产品中文简称（内部使用）"],
        "models": [
            {
                "name": "product_abb_submission",
                "depends": ["60011 产品中文简称_监管报送"],
                "replace_pairs": (
                    # 替换/去除规则：
                    #     1、首先在60011的基础上去掉“富国”这两个字
                    #     2、其次如果还能检测到‘灵活配置’、‘发起式’，还需要去掉这两个
                    (r"^富国", ""),
                    (r"灵活配置|发起式", ""),
                ),
            },
        ],
    },
    {
        "path": ["203427 产品类别"],
        "models": [
            {
                "name": "default",
                "default_text": "共同基金",
            },
        ],
    },
    {
        "path": ["201481 产品投资类型"],
        "models": [
            {
                "name": "product_abb_submission",
                "depends": ["203501 资产配置比例条款"],
            },
        ],
    },
    {
        "path": ["204029 基金类别"],
        "models": [
            {
                "name": "syllabus_elt_v2",
            },
        ],
    },
    {
        "path": ["200043 A级基金简称"],
        "models": [
            {
                "name": "product_abb_submission",
                "depends": ["60011 产品中文简称_监管报送", "基金合同类型"],
            },
        ],
    },
    {
        "path": ["200044 C级基金简称"],
        "models": [
            {
                "name": "product_abb_submission",
                "depends": ["60011 产品中文简称_监管报送", "基金合同类型"],
            },
        ],
    },
    {
        "path": ["204039 产品开放频率"],
        "models": [
            {
                "name": "syllabus_elt_v2",
            },
        ],
    },
    {
        "path": ["200286 境内托管机构名称"],
        "models": [
            {
                "name": "table_kv",
                "feature_white_list": [r"基金托管人"],
                "regs": [r"指?(?P<dst>.*有限公司)"],
            },
            {
                "name": "partial_text",
                "regs": [r"基金托管人[:：]指(?P<dst>.*有限公司)"],
                "model_alternative": True,
            },
        ],
    },
    {
        "path": ["203509 招募说明书或资管合同约定的注册登记机构"],
        "models": [
            {
                "name": "table_kv",
                "feature_white_list": [r"基金注册登记机构"],
                "regs": [r"(?P<dst>.*有限公司)"],
            },
            {
                "name": "partial_text",
                "regs": [
                    r"登记(机构|部门)(是|为|:|：)(?P<dst>富国基金\w+?公司)(或|和|及)",
                    r"指办理登记业务的(机构|部门).*?登记(机构|部门)(是|为|:|：)(?P<dst>[^.。，,]*)",
                    r"登记(机构|部门)(是|为|:|：)(?P<dst>[^.。，,]*)",
                ],
            },
        ],
    },
    {
        "path": ["202309 结算模式"],
        "models": [
            {
                "name": "table_kv",
                "feature_white_list": [r"基金托管人"],
                "regs": [r"指?(?P<dst>.*有限公司)"],
            },
            {
                "name": "partial_text",
            },
        ],
    },
    {
        "path": ["203395 基金合同的投资范围是否包含港股通投资标的"],
        "models": [
            {
                "name": "syllabus_elt_v2",
            },
        ],
    },
    {
        "path": ["205463 投资范围是否包含其他基金"],
        "models": [
            {
                "name": "product_abb_submission",
                "depends": [
                    "203500 投资范围条款",
                ],
            },
        ],
    },
    {
        "path": ["203429 基金合同的投资范围是否包含股指期货投资标的"],
        "models": [
            {
                "name": "syllabus_elt_v2",
            },
        ],
    },
    {
        "path": ["203301 是否为发起式基金"],
        "models": [
            {
                "name": "syllabus_elt_v2",
            },
        ],
    },
    {
        "path": ["100209946 基金合同中是否有对风格股票的约定"],
        "models": [
            {
                "name": "stock_style_conv",
                "inject_syllabus_features": [r"__regex__个股(投资|选择)策略"],
            },
        ],
    },
    {
        "path": ["203504 基金是否是指数基金"],
        "models": [
            {
                "name": "syllabus_elt_v2",
            },
        ],
    },
    {
        "path": ["203431 基金合同中是否有上市条款"],
        "models": [
            {
                "name": "syllabus_elt_v2",
                "keep_parent": True,
                "inject_syllabus_features": ["__regex__基金份额的上市交易__regex__基金份额的上市交易"],
                "only_first": True,
            },
        ],
    },
    {
        "path": ["204480 上市地点"],
        "models": [
            {
                "name": "partial_text",
                "syllabus_regs": [r"基金(份额)?的(上市)?交易"],
                "regs": [r"(?P<dst>(深圳|上海|北京)证券交易所)"],
            },
        ],
    },
    {
        "path": ["20001106 ETF基金类型"],
        "models": [
            {
                "name": "etf_fund_type",
                "depends": ["基金合同类型", "60001 产品中文全称", "204480 上市地点"],
            },
        ],
    },
    {
        "path": ["204030 混合投资偏向性"],
        "models": [
            {
                "name": "syllabus_elt_v2",
            },
        ],
    },
    {
        "path": ["203209 产品类型"],
        "models": [
            {
                "name": "syllabus_elt_v2",
            },
        ],
    },
    {
        "path": ["205233 小微基金模式"],
        "models": [
            {
                "name": "syllabus_elt_v2",
            },
        ],
    },
    {
        "path": ["205234 小微触发清盘工作日连续天数"],
        "models": [
            {
                "name": "partial_text",
                "regs": [
                    r"连续(?P<dst>\d+)个工作日出现\D*(基金合同(自动|应当)?终止|终止基金合同|本基金终止)",
                ],
            },
        ],
    },
    {
        "path": ["205265 小微基金人数触发条件"],
        "models": [
            {
                "name": "partial_text",
            },
        ],
    },
    {
        "path": ["20001503 权益类资产下限(%)"],
        "models": [
            {
                "name": "partial_text",
                "regs": [
                    r"(权益.*?资产|股票|存托凭证|股票[型类]基金|偏股混合[型类]基金|目标ETF)[^。，,;；]*?(?P<dst>\d+(\.\d+)?)(%|％)?(-|—|~|至|到)\d+(\.\d+)?(%|％)",
                    r"(权益.*?资产|股票|存托凭证|股票[型类]基金|偏股混合[型类]基金|目标ETF)[^。，,;；]*?不\w{,3}[低小][于至过].*?(?P<dst>\d+(\.\d+)?)(%|％)",
                ],
            },
            {
                "name": "default",
                "default_text": "0",
            },
        ],
    },
    {
        "path": ["205267 小微基金规模触发条件"],
        "models": [
            {
                "name": "partial_text",
            },
        ],
    },
    {
        "path": ["203773 产品托管费率（%）"],
        "models": [
            {"name": "partial_text", "regs": [r"H.*?E.*?(?P<dst>[\d.]+)[%％]÷当年天数"]},
            {
                "name": "syllabus_based",
                "include_title": False,
                "inject_syllabus_features": [r"__regex__基金托管人的托管费"],
                "paragraph_model": "partial_text",
                "para_config": {"regs": [r"H.*?E.*?(?P<dst>[\d.]+)[%％].当年天数"]},
                "table_model": "cell_partial_text",
                "table_config": {"regs": [r"H.*?E.*?(?P<dst>[\d.]+)[%％].当年天数"]},
            },
            {
                "name": "partial_text",
            },
        ],
    },
    {
        "path": ["203430 产品运作方式"],
        "models": [
            {
                "name": "syllabus_elt_v2",
            },
        ],
    },
    {
        "path": ["203629 合同终止情形条款"],
        "models": [
            {
                "name": "syllabus_elt_v2",
            },
        ],
    },
    {
        "path": ["203633 业绩（基准或报酬）条款"],
        "models": [
            {
                "name": "syllabus_elt_v2",
            },
        ],
    },
    {
        "path": ["203631 其他费用条款(若有)"],
        "models": [
            {
                "name": "syllabus_elt_v2",
                "inject_syllabus_features": [
                    r"__regex__基金费用与税收__regex__基金费用计提方法__regex__基金(份额)?的(销售)?服务费",
                    r"__regex__基金费用与税收__regex__基金费用计提方法__regex__基金(份额)?的基金财产中计提的基金(销售)?服务费",
                ],
                "neglect_patterns": ["释义"],
                "break_para_pattern": [r"上述.?一"],
            },
        ],
    },
    {
        "path": ["202669 投资目标"],
        "models": [
            {
                "name": "syllabus_elt_v2",
            },
        ],
    },
    {
        "path": ["203500 投资范围条款"],
        "models": [
            {
                "name": "syllabus_elt_v2",
                "break_para_pattern": [
                    r"基金的?投资.*?比例",
                    rf"比例不{R_COMPARE}基金资产的",
                ],
                "include_break_para": False,
            },
        ],
    },
    {
        "path": ["203501 资产配置比例条款"],
        "models": [
            {
                "name": "middle_paras",
                "use_syllabus_model": True,
                "syllabus_level": 2,
                "inject_syllabus_features": [r"__regex__基金的投资__regex__投资范围"],
                "only_inject_features": True,
                "only_use_syllabus_elements": True,
                "top_greed": True,
                "top_anchor_regs": [
                    r"基金的投资组合比例",
                    rf"本基金对.*投资比例(不{R_COMPARE}|占|为)",
                    rf"本基金投资.*的比例(不{R_COMPARE}|占|为)",
                    rf"资产的?投资比例(不{R_COMPARE}|占|为)基金资产的\d+",
                    r"投资占基金资产的比例为\d+",
                    rf"投资于.*资产的?比例(不{R_COMPARE}|占|为)基金资产(净值)?的\d+",
                    r"本基金\d+[%％]以上的资产投资于",
                    r"投资比例限制",
                ],
                "bottom_anchor_regs": [
                    r"如果?法律法规",
                    r"本基金管理人自基金合同生效之日起6个月内使基金的投资组合比例符合上述相关规定",
                    r"适当程序后，可以调整上述投资品种的投资比例",
                ],
                "include_bottom_anchor": True,
                "bottom_default": True,
            },
            {
                "name": "middle_paras",
                "use_syllabus_model": True,
                "syllabus_level": 2,
                "inject_syllabus_features": [r"__regex__基金的投资__regex__投资范围"],
                "only_inject_features": True,
                "only_use_syllabus_elements": True,
                "top_greed": False,
                "include_top_anchor": False,
                "top_anchor_regs": [
                    r"基金的?投资.*?比例",
                    r"如法律法规.*可以将其纳入投资范围",
                ],
                "include_bottom_anchor": True,
                "bottom_default": True,
            },
            {
                "name": "para_match",
                "syllabus_regs": [r"投资范围"],
                "paragraph_pattern": [
                    r"基金的投资组合比例",
                    r"本基金以.*为主要投资对象",
                    r"本基金主要投资于",
                    r"本基金.*投资.*的?比例",
                    r"资产的?投资比例(不低于|占)基金资产的\d+",
                    r"投资于.*资产的比例(不低于|占)基金资产的\d+",
                    r"投资占基金资产的比例为\d+",
                    r"投资比例限制",
                ],
                "neglect_regs": [
                    r"如果?法律法规",
                ],
            },
            {
                "name": "syllabus_elt_v2",
                "inject_syllabus_features": [r"__regex__基金的投资__regex__投资范围"],
                "only_inject_features": True,
            },
        ],
    },
    {
        "path": ["100209947 基金合同中对风格股票库界定标准"],
        "models": [
            {
                "name": "default",
                "default_text": "无",
            },
        ],
    },
    {
        "path": ["203502 投资限制条款"],
        "models": [
            {
                "name": "syllabus_elt_v2",
                "inject_syllabus_features": [r"投资限制"],
                "neglect_patterns": [r"禁止行为"],
                "break_para_pattern": [
                    r"禁止行为",
                ],
                "include_break_para": False,
            },
        ],
    },
    {
        "path": ["202672 风险收益特征"],
        "models": [
            {
                "name": "syllabus_elt_v2",
            },
        ],
    },
    {
        "path": ["201491 产品分红条款"],
        "models": [
            {
                "name": "syllabus_elt_v2",
            },
        ],
    },
    {
        "path": ["205163 国债期货投资策略"],
        "models": [
            {
                "name": "syllabus_elt_v2",
            },
        ],
    },
    {
        "path": ["205161 股指期货投资策略"],
        "models": [
            {
                "name": "syllabus_elt_v2",
            },
        ],
    },
    {
        "path": ["201291 管理费（%）"],
        "models": [
            {
                "name": "syllabus_based",
                "include_title": False,
                "inject_syllabus_features": [r"基金管理人的管理费"],
                "paragraph_model": "partial_text",
                "para_config": {
                    "regs": [
                        r"管理费率为(?P<dst>\d+(\.\d+)?)[%|％]",
                    ],
                    "model_alternative": True,
                    "multi": True,
                },
            },
            {
                "name": "partial_text",
                "regs": [
                    r"(费|值).*?(?P<dst>\d+(\.\d+)?)[%|％].*?计提",
                ],
                "model_alternative": True,
                "multi": True,
            },
        ],
    },
    {
        "path": ["203625 管理费条款"],
        "models": [
            {
                "name": "syllabus_elt_v2",
                "keep_parent": True,
                "inject_syllabus_features": [
                    r"基金的费用与税收|基金费用计提方法、计提标准和支付方式|基金管理人的管理费",
                ],
                "syllabus_black_list": [
                    r"__regex__基金转型的情况",
                    r"__regex__托管费",
                ],
                "syllabus_level": 4,
            },
        ],
    },
    {
        "path": ["202671 业绩比较基准"],
        "models": [
            {
                "name": "syllabus_based",
                "include_title": False,
                "neglect_patterns": [r"基金转型的情况"],
                "syllabus_level": 4,
                "extract_from": "same_type_elements",
                "paragraph_model": "para_match",
                "para_config": {
                    "paragraph_pattern": [
                        r".*",  # 取第一段
                    ],
                },
            },
            {
                "name": "syllabus_based",
                "include_title": False,
                "neglect_patterns": [r"基金转型的情况"],
                "inject_syllabus_features": [r"__regex__基金的投资__regex__业绩评价基准"],
                "only_inject_features": True,
                "extract_from": "same_type_elements",
                "paragraph_model": "para_match",
                "para_config": {
                    "paragraph_pattern": [
                        r".*",  # 取第一段
                    ],
                },
            },
        ],
    },
]

prophet_config = {
    "depends": {},
    "predictor_options": predictor_options,
}
