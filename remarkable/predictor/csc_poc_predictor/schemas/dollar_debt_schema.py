"""
美元债债项评级字段抽取
"""

ISSUER_PAGE_SYLLABUS_REGS = [
    r"SUMMARY\s?OF\s?THE\s?PROGRAMME",
    r"THE\s?(OFFERING|offering)",
    r"THE\s?ISSUE",
    r"SUMMARY\s?OF\s?THE\s?(OFFERING|offering)",
    r"OFFER\sSTRUCTURE",
    r"SUMMARY",
    r"Description of the Notes",
]

RATING_AGENCY = r"(Fitch|Moody|S&P|Standard\s?and\s?Poor)"
BONDS = r"([Nn]\s?otes|[Bb]onds|[Ss]ecurities|[Pp]rogramme|Offshore\s?Preference\s?Shares)"
ISSUER = r"([iI]ssuer|company|corporate|Bank)"

isin_pattern = [
    r"(?P<dst>XS\d+)",
    r"(?P<dst>XS\[.\])",
    r"(?P<dst>\[.\])",
]

predictor_options = [
    {
        "path": ["币种-封面"],
        "models": [
            {
                "name": "partial_text",
                "model_alternative": True,
                "multi_elements": True,
                "regs": [
                    r"(?P<dst>U\.?S\.?\$)",
                ],
            },
        ],
    },
    {
        "path": ["币种-发行事项页"],
        "models": [
            {
                "name": "table_kv",
                "width_from_all_rows": True,
                "use_complete_table": True,
                "feature_white_list": [
                    r"__regex__(Issue[^r]|The\s?Bonds|Notes|Securities|The\s?Notes|Size|Notes\s?Offered|Programme)",
                    r"__regex__Description",
                ],
                "regs": [
                    r"(?P<dst>U\.?S\.?\$)",
                ],
                "only_matched_value": True,
                "multi_answer_in_one_cell": True,
            },
        ],
    },
    {
        "path": ["发行人中文名称-封面"],
        "models": [
            {
                "name": "partial_text",
                "page_range": list(range(0, 4)),
                "model_alternative": True,
                "regs": [
                    r"(?P<dst>[\u4e00-\u9fa5]+\s?([(（].+[）)]|[IV]+)?(有\s?限\s?公\s?司|集\s?团)[\s\u4e00-\u9fa5]*)"
                ],
            },
        ],
    },
    {
        "path": ["发行人中文名称-发行事项页"],
        "models": [
            {
                "name": "table_kv",
                "width_from_all_rows": True,
                "feature_white_list": [
                    r"__regex__Issuer",
                ],
                "regs": [r"(?P<dst>[\u4e00-\u9fa5]+\s?([(（].+[）)]|[IV]+)?[\s\u4e00-\u9fa5]*)"],
                "only_matched_value": True,
            },
        ],
    },
    {
        "path": ["发行人英文名称-封面"],
        "models": [
            {
                "name": "partial_text",
            },
        ],
    },
    {
        "path": ["发行人英文名称-发行事项页"],
        "models": [
            {
                "name": "table_kv",
                "width_from_all_rows": True,
                "syllabus_regs": ISSUER_PAGE_SYLLABUS_REGS,
                "feature_white_list": [
                    r"__regex__Issuer",
                ],
                "regs": [
                    r"(?P<dst>[^\u4e00-\u9fa5]+[a-zA-Z)])",
                ],
                "neglect_regs": [
                    r"Identifier",
                ],
                "only_matched_value": True,
            },
            {
                "name": "partial_text",
                "regs": [
                    r"Issuer.*?(?P<dst>[a-zA-Z][^\u4e00-\u9fa5]+[a-zA-Z)])",
                ],
            },
        ],
    },
    {
        "path": ["担保人全称-封面"],
        "models": [
            {
                "name": "elements_collector_based",
                "elements_collect_model": "middle_paras",
                "elements_collect_config": {
                    "elements_in_page_range": list(range(0, 4)),
                    "table_regarded_as_paras": True,
                    "top_anchor_regs": [
                        r"Guaranteed",
                        r"GUARANTEED",
                    ],
                    "bottom_anchor_regs": [
                        r"(?P<dst>.*(LTD|Ltd|LIMITED|Limited))",
                    ],
                    "include_top_anchor": False,
                    "include_bottom_anchor": True,
                },
                "paragraph_model": "partial_text",
                "para_config": {
                    "use_answer_pattern": False,
                    "regs": [
                        r"(by\s?)(?P<dst>.*(LTD|Ltd|LIMITED|Limited))",
                        r"(?P<dst>.*(LTD|Ltd|LIMITED|Limited))",
                    ],
                },
            },
            {
                "name": "fixed_position",
                "pages": list(range(0, 4)),
                "regs": [
                    r"guaranteed\s?by\s?(?P<dst>.*[Ll]imited)",
                ],
            },
            {
                "name": "partial_text",
                "use_answer_pattern": False,
                "model_alternative": True,
                "multi_elements": True,
                "multi_elements_limit": 2,
                "regs": [
                    r"guaranteed\s?by\s?(?P<dst>.*([Ll]imited))",
                ],
            },
        ],
    },
    {
        "path": ["担保人全称-发行事项页"],
        "models": [
            {
                "name": "table_kv",
                "width_from_all_rows": True,
                "syllabus_regs": ISSUER_PAGE_SYLLABUS_REGS,
                "feature_white_list": [
                    r"__regex__(Guarantor|Guarantee|Guarantor\s?or\s?Company)",
                ],
                "regs": [r"(?P<dst>.*(公\s?司|Limited|Ltd)[)）]?)"],
                "only_matched_value": True,
            },
        ],
    },
    {
        "path": ["债券国际评级-发行事项页"],
        "models": [
            {
                "name": "table_kv",
                "use_complete_table": True,
                "width_from_all_rows": True,
                "syllabus_regs": ISSUER_PAGE_SYLLABUS_REGS,
                "feature_white_list": [
                    r"__regex__Ratings?",
                ],
                "regs": [
                    r"(?P<dst>The Notes are expected to be rated.*?after delivery of the Notes)",
                    rf"(?P<dst>The\s?{BONDS}.*?rat(ed|ing).*?){ISSUER}",
                    rf"(?P<dst>The\s?{BONDS}.*?rat(ed|ing).*)",
                ],
                "only_matched_value": True,
            },
        ],
    },
    {
        "path": ["是否次级债-发行事项页"],
        "models": [
            {
                "name": "table_kv",
                "width_from_all_rows": True,
                "feature_white_list": [
                    r"Ranking",
                    rf"__regex__(Status|Ranking)\s?of\s?(the)?\s?{BONDS}",
                    r"__regex__^Status$",
                    r"__regex__^Notes$",
                    r"__regex__^Ranking$",
                    r"__regex__Status\s?of\s?Securities\s?and\s?Guarantee",
                    r"__regex__Rank\s?and\?Status",
                ],
                "neglect_regs": [
                    r"The Notes are:$",
                    r"Status\s?of\s?the\s?Guarantee",
                ],
                "regs": [
                    r"(?P<dst>Senior)",
                    r"(?P<dst>junior)",
                    r"(?P<dst>(?<!un)[Ss]ubordinated(?!\s?(to|ob)))",
                ],
                "multi": True,
            },
        ],
    },
    {
        "path": ["债券到期日-发行事项页"],
        "models": [
            {
                "name": "table_kv",
                "width_from_all_rows": True,
                "feature_white_list": [
                    r"__regex__(Maturity\s?|Maturities)(Date)?",
                ],
                "multi": True,
            },
        ],
    },
    {
        "path": ["偿付顺序"],
        "models": [
            {
                "name": "table_kv",
                "width_from_all_rows": True,
                "feature_white_list": [
                    r"__regex__Statusof\s?(the)?\s?(Bonds|Notes|Securities)",
                    r"__regex__Ranking\s?of\s?the\s?N\s?otes",
                    r"__regex__Status",
                    r"__regex__Ranking\.+",
                ],
            },
        ],
    },
    {
        "path": ["最新可回售/赎回日期-发行事项页"],
        "models": [
            {
                "name": "table_kv",
                "width_from_all_rows": True,
                "feature_white_list": [
                    r"__regex__Distribution\s?Rate",
                    r"__regex__Rate\s?of\s?Distribution",
                ],
                "regs": [
                    r"(?P<dst>\d{1,2}\s*\w*?\s*\d{4}\s*[(]the\s*[“‘]+First\s*Call\s*Date[”’)]+)",
                ],
                "only_matched_value": True,
            },
        ],
    },
    {
        "path": ["当前票面利率-封面"],
        "models": [
            {
                "name": "partial_text",
            },
        ],
    },
    {
        "path": ["当前票面利率-发行事项页"],
        "models": [
            {
                "name": "table_kv",
                "width_from_all_rows": True,
                "syllabus_regs": ISSUER_PAGE_SYLLABUS_REGS,
                "feature_white_list": [
                    "__regex__(Issue[^r]|TheBonds|Description|Notes|Securities|TheNotes)",
                ],
                "neglect_regs": [
                    r"purchase price equal to",
                ],
                "regs": [
                    r"(?P<dst>([\d.]+|\[.\])(\s?per\s?cent|%))",
                ],
                "only_matched_value": True,
                "multi_answer_in_one_cell": True,
                # 'multi': True,
            },
        ],
    },
    {
        "path": ["是否永续债-封面"],
        "models": [
            {
                "name": "partial_text",
                "regs": [
                    rf"Perpetual\s?{BONDS}",
                ],
                "model_alternative": True,
            },
        ],
    },
    {
        "path": ["是否永续债-发行事项页"],
        "models": [
            {
                "name": "table_kv",
                "width_from_all_rows": True,
                "feature_white_list": [
                    r"__regex__Securities (Placed)?[:]",
                ],
            },
            {
                "name": "table_kv",
                "width_from_all_rows": True,
                "feature_white_list": [
                    r"__regex__(Issue|Offering)",
                ],
                "regs": [r"(?P<dst>[Pp]erpetual)"],
                "only_matched_value": True,
            },
        ],
    },
    {
        "path": ["不赎回利率跳升机制"],
        "models": [
            {
                "name": "table_kv",
                "width_from_all_rows": True,
                "feature_white_list": [
                    r"__regex__(Distribution|Dividend)\s?Rate",
                ],
            },
        ],
    },
    {
        "path": ["利息是否可取消"],
        "models": [
            {
                "name": "table_kv",
                "width_from_all_rows": True,
                "feature_white_list": [
                    r"__regex__No\s?Obligation\s?to\s?Pay",
                ],
            },
        ],
    },
    {
        "path": ["是否累计"],
        "models": [
            {
                "name": "table_kv",
                "width_from_all_rows": True,
                "use_complete_table": True,
                "feature_white_list": [
                    r"__regex__Cumulative\s?Deferral",
                    r"__regex__Arrears\s?of\s?Dividend",
                ],
            },
            {
                "name": "table_kv",
                "width_from_all_rows": True,
                "use_complete_table": True,
                "feature_white_list": [
                    r"__regex__Distribution\s?Deferral",
                    r"__regex__Arrears\s?of\s?Dividend",
                ],
            },
        ],
    },
    {
        "path": ["维好人-封面"],
        "models": [
            {
                "name": "elements_collector_based",
                "elements_collect_model": "middle_paras",
                "elements_collect_config": {
                    "elements_in_page_range": list(range(0, 4)),
                    "top_anchor_regs": [
                        r"keep\s?well\s?deed",
                    ],
                    "bottom_anchor_regs": [
                        r"(?P<dst>.*(LTD|Ltd|LIMITED|Limited))",
                    ],
                    "include_top_anchor": False,
                    "include_bottom_anchor": True,
                },
                "paragraph_model": "partial_text",
                "para_config": {
                    "use_answer_pattern": False,
                    "regs": [
                        r"(undertaking\s?by\s?)(?P<dst>.*(LTD|Ltd|LIMITED|Limited))",
                        r"(?P<dst>.*(LTD|Ltd|LIMITED|Limited))",
                    ],
                },
            },
            {
                "name": "partial_text",
            },
        ],
    },
    {
        "path": ["维好人-发行事项页"],
        "models": [
            {
                "name": "table_kv",
                "width_from_all_rows": True,
                "feature_white_list": [
                    r"__regex__Trustee\s?and\s?Security.Trustee",
                ],
                "regs": [
                    r"(?P<dst>[^\d]+)",
                ],
                "only_matched_value": True,
                "use_complete_table": True,
            },
        ],
    },
    {
        "path": ["ISIN-发行事项页"],
        "models": [
            {
                "name": "table_kv",
                "width_from_all_rows": True,
                "syllabus_regs": ISSUER_PAGE_SYLLABUS_REGS,
                "feature_white_list": [
                    r"__regex__(ISIN|ClearanceandSettlement|Security\s?Codes)",
                ],
                "regs": isin_pattern,
                "only_matched_value": True,
                "multi_answer_in_one_cell": True,
            },
            {
                "name": "row_match",
                "merge_row": False,
                "syllabus_regs": ISSUER_PAGE_SYLLABUS_REGS,
                "row_pattern": [
                    r"ISIN",
                    r"(?P<dst>XS\d+)",
                    r"(?P<dst>XS\[.\])",
                ],
                "content_pattern": isin_pattern,
            },
            {"name": "isin"},
        ],
    },
    {
        "path": ["备用信用证开具人-封面"],
        "models": [
            {
                "name": "partial_text",
            },
        ],
    },
    {
        "path": ["备用信用证开具人-发行事项页"],
        "models": [
            {
                "name": "table_kv",
                "width_from_all_rows": True,
                "feature_white_list": [
                    r"__regex__Standby\s?Letter\s?of\s?Credit",
                ],
                "regs": [
                    r"(?P<dst>TheBond.*?issued\s?by\s?the.*?Bank)",
                ],
                "only_matched_value": True,
            },
        ],
    },
    {
        "path": ["转股条款"],
        "models": [
            {
                "name": "table_kv",
                "width_from_all_rows": True,
                "feature_white_list": [
                    r"__regex__HongKong\s?Resolution\s?Authority\s?Power",
                ],
            },
        ],
    },
    {
        "path": ["减记条款"],
        "models": [
            {
                "name": "table_kv",
                "width_from_all_rows": True,
                "feature_white_list": [
                    r"__regex__LossAbsorptionuponaNon-ViabilityEventinrespectoftheNotes",
                ],
            },
        ],
    },
    {
        "path": ["发行人国际评级-发行事项页"],
        "models": [
            {
                "name": "table_kv",
                "use_complete_table": True,
                "width_from_all_rows": True,
                "syllabus_regs": ISSUER_PAGE_SYLLABUS_REGS,
                "feature_white_list": [
                    r"__regex__Ratings?",
                ],
                "regs": [
                    rf"(?<!Guarantor has been assigned a )(?P<dst>({RATING_AGENCY}\s?has\s?assigned\s?a\s?)?"
                    rf"{ISSUER}.*?rat(ed|ing).*?){BONDS}",
                    rf"(?<!Guarantor has been assigned a )(?P<dst>({RATING_AGENCY}\s?has\s?assigned\s?a\s?)?"
                    rf"{ISSUER}.*?rat(ed|ing).*)",
                ],
                "only_matched_value": True,
            },
        ],
    },
    {
        "path": ["ISIN-封面"],
        "models": [
            {
                "name": "partial_text",
            },
        ],
    },
    {
        "path": ["发行人国际评级-封面"],
        "models": [
            {
                "name": "partial_text",
            },
        ],
    },
    {
        "path": ["债券国际评级-封面"],
        "models": [
            {
                "name": "partial_text",
            },
        ],
    },
    {
        "path": ["是否次级债-封面"],
        "models": [
            {
                "name": "partial_text",
            },
        ],
    },
    {
        "path": ["债券到期日-封面"],
        "models": [
            {
                "name": "partial_text",
            },
        ],
    },
    {
        "path": ["最新可回售/赎回日期-封面"],
        "models": [
            {
                "name": "partial_text",
            },
        ],
    },
]

prophet_config = {
    "depends": {},
    "predictor_options": predictor_options,
}
