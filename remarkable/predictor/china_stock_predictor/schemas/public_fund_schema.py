"""银河证券 4 公募-基金合同"""

predictor_options = [
    {
        "path": ["基金名称"],
        "models": [
            {
                "name": "para_match",
                "paragraph_pattern": (r"(?P<content>[(（【)）】1-9a-zA-Z\u4e00-\u9fa5]+)",),
            },
            {
                "name": "score_filter",
                "threshold": 0.1,
            },
        ],
    },
    {
        "path": ["基金管理人", "名称"],
        "models": [
            {
                "name": "partial_text",
                "use_answer_pattern": False,
                "regs": [r"名称[:：](?P<dst>.*)"],
                "model_alternative": True,
            },
        ],
    },
    {
        "path": ["基金管理人", "住所"],
        "models": [
            {
                "name": "partial_text",
                "use_answer_pattern": False,
                "regs": [r"(住所|注册地址)[:：](?P<dst>.*)"],
                "model_alternative": True,
            },
        ],
    },
    {
        "path": ["基金管理人", "法定代表人"],
        "models": [
            {
                "name": "partial_text",
                "use_answer_pattern": False,
            },
        ],
    },
    {
        "path": ["基金管理人", "批准设立机关及批准设立文号"],
        "models": [
            {
                "name": "partial_text",
                "use_answer_pattern": False,
            },
        ],
    },
    {
        "path": ["基金管理人", "联系电话"],
        "models": [
            {
                "name": "partial_text",
                "use_answer_pattern": False,
                "regs": [r"联系电话[:：](?P<dst>.*)"],
                "model_alternative": True,
            },
        ],
    },
    {
        "path": ["基金托管人", "名称"],
        "models": [
            {
                "name": "partial_text",
                "use_answer_pattern": False,
            },
        ],
    },
    {
        "path": ["基金托管人", "住所"],
        "models": [
            {
                "name": "partial_text",
                "use_answer_pattern": False,
                "regs": [r"(住所|注册地址)[:：](?P<dst>.*)"],
                "model_alternative": True,
            },
        ],
    },
    {
        "path": ["基金托管人", "通讯地址"],
        "models": [
            {
                "name": "partial_text",
                "use_answer_pattern": False,
            },
        ],
    },
    {
        "path": ["基金托管人", "法定代表人"],
        "models": [
            {
                "name": "partial_text",
                "use_answer_pattern": False,
            },
        ],
    },
    {
        "path": ["基金托管人", "批准设立机关及批准设立文号"],
        "models": [
            {
                "name": "partial_text",
                "use_answer_pattern": False,
            },
        ],
    },
    {
        "path": ["基金的类别、类型"],
        "models": [
            {
                "name": "partial_text",
                "regs": [
                    r"(?P<dst>.*型(开放式)?证券投资基金)",
                ],
            }
        ],
    },
    {
        "path": ["运作方式"],
        "models": [
            {
                "name": "partial_text",
                "regs": [
                    r"(?P<dst>((契约|交易)型)?(开放|封闭)式)",
                ],
                "model_alternative": True,
            }
        ],
    },
    {
        "path": ["基金的投资目标"],
        "models": [
            {
                "name": "syllabus_elt_v2",
            }
        ],
    },
    {
        "path": ["基金的最低募集份额总额"],
        "models": [
            {
                "name": "syllabus_elt_v2",
            }
        ],
    },
    {
        "path": ["基金份额面值"],
        "models": [
            {
                "name": "para_match",
                "paragraph_pattern": (r"(?P<dst>本基金基金份额(初始)?(发售)?面值为人民币.*?元)",),
            }
        ],
    },
    {
        "path": ["存续期"],
        "models": [
            {
                "name": "syllabus_elt_v2",
            }
        ],
    },
    {
        "path": ["募集期"],
        "models": [
            {
                "name": "syllabus_elt_v2",
            }
        ],
    },
    {
        "path": ["基金存续期内的基金份额持有人数量和资产规模"],
        "models": [
            {
                "name": "syllabus_elt_v2",
            }
        ],
    },
    {
        "path": ["管理人的权利"],
        "models": [
            {
                "name": "syllabus_elt_v2",
            }
        ],
    },
    {
        "path": ["管理人的义务"],
        "models": [
            {
                "name": "syllabus_elt_v2",
            }
        ],
    },
    {
        "path": ["托管人的权利"],
        "models": [
            {
                "name": "syllabus_elt_v2",
            }
        ],
    },
    {
        "path": ["托管人的义务"],
        "models": [
            {
                "name": "syllabus_elt_v2",
            }
        ],
    },
    {
        "path": ["基金份额持有人大会召开事由"],
        "models": [
            {
                "name": "syllabus_elt_v2",
                "inject_syllabus_features": ["__regex__基金份额持有人大会__regex__召开事由"],
            }
        ],
    },
    {
        "path": ["基金份额持有人大会会议召集人及召集方式"],
        "models": [
            {
                "name": "syllabus_elt_v2",
                "inject_syllabus_features": ["__regex__基金份额持有人大会__regex__会议召集人及召集方式"],
            }
        ],
    },
    {
        "path": ["召开基金份额持有人大会的通知时间、通知内容、通知方式"],
        "models": [
            {
                "name": "syllabus_elt_v2",
                "inject_syllabus_features": ["__regex__召开基金份额持有人大会的通知时间、通知内容、通知方式"],
            }
        ],
    },
    {
        "path": ["基金份额持有人大会基金份额持有人出席会议的方式"],
        "models": [
            {
                "name": "syllabus_elt_v2",
                "inject_syllabus_features": ["__regex__基金份额持有人大会__regex__基金份额持有人出席会议的方式"],
            }
        ],
    },
    {
        "path": ["基金份额持有人大会议事内容与程序"],
        "models": [
            {
                "name": "syllabus_elt",
                "基金份额持有人大会议事内容与程序": {
                    "feature_white_list": [
                        r"议事内容与程序",
                    ],
                },
            }
        ],
    },
    {
        "path": ["基金份额持有人大会表决"],
        "models": [
            {
                "name": "syllabus_elt_v2",
                "inject_syllabus_features": ["__regex__基金份额持有人大会__regex__表决"],
            }
        ],
    },
    {
        "path": ["基金份额持有人大会计票"],
        "models": [
            {
                "name": "syllabus_elt_v2",
                "inject_syllabus_features": ["__regex__基金份额持有人大会__regex__计票"],
            }
        ],
    },
    {
        "path": ["基金份额持有人大会生效与公告"],
        "models": [
            {
                "name": "syllabus_elt_v2",
                "inject_syllabus_features": ["__regex__基金份额持有人大会__regex__生效与公告"],
            }
        ],
    },
    {
        "path": ["基金管理人职责终止的情形"],
        "models": [
            {
                "name": "syllabus_elt_v2",
            }
        ],
    },
    {
        "path": ["基金托管人职责终止的情形"],
        "models": [
            {
                "name": "syllabus_elt_v2",
            }
        ],
    },
    {
        "path": ["基金管理人的更换程序"],
        "models": [
            {
                "name": "syllabus_elt_v2",
            }
        ],
    },
    {
        "path": ["基金托管人的更换程序"],
        "models": [
            {
                "name": "syllabus_elt_v2",
            }
        ],
    },
    {
        "path": ["基金管理人与基金托管人同时更换的条件和程序"],
        "models": [
            {
                "name": "syllabus_elt_v2",
            }
        ],
    },
    {
        "path": ["标的指数（释义）"],
        "models": [
            {
                "name": "para_match",
                "paragraph_pattern": (
                    r"(?P<content>标的指数.*?及其未来可能发生的变更(，或基金管理人按照本基金合同约定更换的其他指数)?)",
                    r"(?P<content>标的指数.*?有限公司编制并发布的.*?指数)",
                ),
                "content_pattern": (
                    r"(?P<content>标的指数.*?及其未来可能发生的变更(，或基金管理人按照本基金合同约定更换的其他指数)?)",
                    r"(?P<content>标的指数.*?有限公司编制并发布的.*?指数)",
                ),
            }
        ],
    },
    {
        "path": ["标的指数（正文）"],
        "models": [
            {
                "name": "partial_text",
            }
        ],
    },
    {
        "path": ["标的指数和业绩比较基准"],
        "models": [
            {
                "name": "syllabus_elt_v2",
            }
        ],
    },
    {
        "path": ["完全复制法（释义）"],
        "models": [
            {
                "name": "partial_text",
            }
        ],
    },
    {
        "path": ["完全复制法（基金的投资）"],
        "models": [
            {
                "name": "perfect_copy_method",
                "完全复制法（基金的投资）": {
                    "feature_white_list": [
                        r"投资策略",
                    ],
                },
            }
        ],
    },
    {
        "path": ["侧袋机制（释义）"],
        "models": [
            {
                "name": "partial_text",
            }
        ],
    },
    {
        "path": ["侧袋机制（基金份额的申购与赎回）"],
        "models": [
            {
                "name": "syllabus_elt_v2",
            }
        ],
    },
    {
        "path": ["侧袋机制（基金份额持有人大会）"],
        "models": [
            {
                "name": "syllabus_elt_v2",
            }
        ],
    },
    {
        "path": ["侧袋机制（基金的投资）"],
        "models": [
            {
                "name": "syllabus_elt_v2",
            }
        ],
    },
    {
        "path": ["侧袋机制（基金资产估值）"],
        "models": [
            {
                "name": "syllabus_elt_v2",
            }
        ],
    },
    {
        "path": ["侧袋机制（基金费用与税收）"],
        "models": [
            {
                "name": "syllabus_elt_v2",
            }
        ],
    },
    {
        "path": ["侧袋机制（基金的信息披露）"],
        "models": [
            {
                "name": "syllabus_elt_v2",
            }
        ],
    },
    {
        "path": ["封闭期"],
        "models": [
            {
                "name": "para_match",
                "paragraph_pattern": (
                    r"(?P<dst>基金管理人可根据实际情况依法决定本基金开始办理申购的具体日期.*?具体业务办理时间在((赎回|申购)开始|相关)公告中规定)",
                    r"(?P<dst>基金管理人自基金合同生效之日起不超过\s?[3三]\s?个月开始办理(赎回|申购).*?具体业务办理时间在((赎回|申购)开始|相关)公告(或相关公告)?中规定)",
                    r"(?P<dst>本基金的申购、赎回自基金合同生效之日起不超过30天开始办理.*?有关规定在指定媒介上公告申购与赎回的开始时间)",
                    r"(?P<dst>本基金自转为上市开放式基金.*?具体业务办理时间在((赎回|申购)开始|相关)公告中规定)",
                    r"(?P<dst>基金合同生效后.*?具体业务办理时间在((赎回|申购)开始|相关)公告中规定)",
                    r"(?P<dst>基金管理人自在认购份额的最短持有期到期日之日起.*?具体业务办理时间在((赎回|申购)开始|相关)公告中规定)",
                    r"(?P<dst>在确定申购开始与赎回开始时间后.*?下一开放日该类基金份额申购、赎回的价格)",
                ),
                "multi_elements": True,
                "combine_paragraphs": True,
            }
        ],
    },
    {
        "path": ["开放日"],
        "models": [
            {
                "name": "para_match",
                "paragraph_pattern": (
                    r"(?P<dst>投资[人者]在开放日(的开放时间)?办理基金份额的申购[及/或和]+赎回.*?(赎回时除外|的有关规定在规定媒介上公告))",
                    r"(?P<dst>开放日的具体业务办理时间在招募说明书.*?有关规定在规定媒介上公告)",
                    r"(?P<dst>基金合同生效后.*?有关规定在[指规]定媒介上公告)",
                    r"(?P<dst>开放日的具体业务办理时间见招募说明书或相关公告)",
                ),
                "combine_paragraphs": True,
            }
        ],
    },
    {
        "path": ["结构化安排"],
        "models": [
            {
                "name": "partial_text",
            }
        ],
    },
    {
        "path": ["基金投资范围"],
        "models": [
            {
                "name": "middle_paras",
                "include_title": True,
                "use_syllabus_model": True,
                "include_top_anchor": False,
                "top_anchor_regs": [
                    r"投资范围",
                ],
                "bottom_anchor_regs": [
                    r"投资组合比例|资产比例|备选成份股的比例|投资.*?比例(为|不低于)基金资产|投资策略",
                ],
            }
        ],
    },
    {
        "path": ["投资比例"],
        "models": [
            {
                "name": "middle_paras",
                "use_syllabus_model": True,
                "bottom_default": True,
                "top_anchor_regs": [
                    r"投资组合比例|资产比例|备选成份股的比例|投资.*?比例(为|不低于)基金资产",
                ],
                "bottom_anchor_regs": [
                    r"投资策略|标的指数",
                ],
            }
        ],
    },
    {
        "path": ["投资限制"],
        "models": [
            {
                "name": "middle_paras",
                "inject_syllabus_features": [r"__regex__投资限制$"],
                "use_syllabus_model": True,
                "top_default": True,
                "include_bottom_anchor": True,
                "bottom_anchor_regs": [
                    r"除上述.*?之外|但中国证监会规定的特殊情形除外",
                    r"法律法规(或监管机构)?另有规定的，从其规定。",
                    r"但中国证监会规定的特殊情形或本合同另有约定的除外",
                ],
            }
        ],
    },
    {
        "path": ["建仓期"],
        "models": [
            {
                "name": "partial_text",
            }
        ],
    },
    {
        "path": ["预警线"],
        "models": [
            {
                "name": "partial_text",
            }
        ],
    },
    {
        "path": ["止损线"],
        "models": [
            {
                "name": "partial_text",
            }
        ],
    },
    {
        "path": ["预警止损机制"],
        "models": [
            {
                "name": "partial_text",
            }
        ],
    },
    {
        "path": ["估值日"],
        "models": [
            {
                "name": "syllabus_elt_v2",
            }
        ],
    },
    {
        "path": ["估值原则"],
        "models": [
            {
                "name": "syllabus_elt_v2",
            }
        ],
    },
    {
        "path": ["估值方法"],
        "models": [
            {
                "name": "syllabus_elt",
                "估值方法": {
                    "feature_white_list": [
                        r"估值方法",
                    ],
                },
                "keep_parent": True,
            }
        ],
    },
    {
        "path": ["估值份额净值保留位数"],
        "models": [
            {
                "name": "para_match",
                "paragraph_pattern": (r"(?P<dst>基金份额净值是按照每个.*?日闭市后.*?从其规定)",),
            }
        ],
    },
    {
        "path": ["暂停估值的情形"],
        "models": [
            {
                "name": "syllabus_elt_v2",
            }
        ],
    },
    {
        "path": ["基金管理费率"],
        "models": [
            {
                "name": "partial_text",
                "model_alternative": True,
                "regs": [
                    r"本基金的管理费按前一日基金资产净值的.*?年费率计[提算]。",
                ],
            }
        ],
    },
    {
        "path": ["基金管理费-计提方法、计提标准和支付方式"],
        "models": [
            {
                "name": "middle_paras",
                "top_anchor_regs": [
                    r"管理费的计[提算]方法",
                    r"基金的?管理费.*计[提算].计[提算]方法如下",
                ],
                "bottom_anchor_regs": [
                    r"管理费每日计[算提]",
                    r"基金管理费在基金合同生效后每日计[算提]",
                ],
                "include_top_anchor": True,
                "include_bottom_anchor": True,
                "top_anchor_content_regs": [r"(?P<content>(管理费的)?计[提算]方法如下.*)"],
            }
        ],
    },
    {
        "path": ["基金托管费率"],
        "models": [
            {
                "name": "partial_text",
                "regs": [
                    r"(?P<dst>本基金的托管费按前一日基金资产净值的.*?的年费率计[提算]。)",
                    r"(?P<dst>基金托管人的基金托管费按基金资产净值的.*?年费率计[提算]。)",
                ],
            },
        ],
    },
    {
        "path": ["基金托管费-计提方法、计提标准和支付方式"],
        "models": [
            {
                "name": "middle_paras",
                "top_anchor_regs": [
                    r"托管费的计算方法",
                    r"基金的?托管费.*计[提算]。计[提算]方法如下",
                ],
                "bottom_anchor_regs": [
                    r"托管费每日计[算提]",
                    r"托管费在基金合同生效后每日计[算提]",
                ],
                "include_top_anchor": True,
                "include_bottom_anchor": True,
                "top_anchor_content_regs": [
                    r"(?P<content>(托管费的)?计[提算]方法如下.*)",
                ],
            }
        ],
    },
    {
        "path": ["客户服务费用"],
        "models": [
            {
                "name": "partial_text",
            }
        ],
    },
    {
        "path": ["客户服务费用-计提方法、计提标准和支付方式"],
        "models": [
            {
                "name": "middle_paras",
                "top_anchor_regs": [
                    r"销售服务费计提的计算公式",
                    r"本基金A类基金份额不收取销售服务费",
                    r"销售服务费.*?计算方法如下",
                ],
                "bottom_anchor_regs": [
                    r"销售服务费每日计[算提]",
                    r"销售服务费在基金合同生效后每日计[算提]",
                ],
                "include_top_anchor": True,
                "include_bottom_anchor": True,
                "top_anchor_content_regs": [
                    r"(?P<content>销售服务费计提的计算公式.*)",
                    r"(?P<content>计[提算]方法如下.*)",
                ],
            }
        ],
    },
    {
        "path": ["其它费用"],
        "models": [
            {
                "name": "syllabus_based",
                "inject_syllabus_features": [
                    r"__regex__基金费用与税收__regex__基金费用计[提算]方法、计[提算]标准和支付方式"
                ],
                "only_inject_features": True,
                "paragraph_model": "middle_paras",
                "extract_from": "same_type_elements",
                "para_config": {
                    "use_direct_elements": True,
                    "include_top_anchor": False,
                    "include_bottom_anchor": True,
                    "top_anchor_regs": [
                        r"基金合同生效后的指数许可使用费",
                    ],
                    "bottom_anchor_regs": [
                        r"上述.*项费用，根据有关法规及相应协议规定，按费用实际支出金额列入当期费用，由基金托管人从基金财产中支付",
                    ],
                },
            },
            {
                "name": "partial_text",
            },
        ],
    },
    {
        "path": ["业绩报酬-计算方式"],
        "models": [
            {
                "name": "partial_text",
            }
        ],
    },
    {
        "path": ["业绩报酬-支付方式"],
        "models": [
            {
                "name": "partial_text",
            }
        ],
    },
    {
        "path": ["基金收益分配原则"],
        "models": [
            {
                "name": "syllabus_elt_v2",
            }
        ],
    },
    {
        "path": ["基金收益分配数额的确定原则"],
        "models": [
            {
                "name": "syllabus_elt_v2",
                "inject_syllabus_features": [r"基金收益分配数额的确定原则"],
            }
        ],
    },
    {
        "path": ["收益分配方案"],
        "models": [
            {
                "name": "syllabus_elt_v2",
            }
        ],
    },
    {
        "path": ["信息披露义务人"],
        "models": [
            {
                "name": "syllabus_elt_v2",
            }
        ],
    },
    {
        "path": ["信息披露禁止行为"],
        "models": [
            {
                "name": "syllabus_elt_v2",
            }
        ],
    },
    {
        "path": ["信息披露的文本"],
        "models": [
            {
                "name": "para_match",
                "paragraph_pattern": (
                    r"(?P<dst>本基金公开披露的信息应采用中文文本.*?以中文文本为准)",
                    r"(?P<dst>本基金公开披露的信息(应当)?采用阿拉伯数字.*?除特别说明外，货币单位为人民币元)",
                ),
                "multi_elements": True,
                "combine_paragraphs": True,
            },
        ],
    },
    {
        "path": ["公开披露的基金信息"],
        "models": [
            {
                "name": "publicly_disclosed_information",
            }
        ],
    },
    {
        "path": ["临时报告或信息披露"],
        "models": [
            {
                "name": "syllabus_elt_v2",
            }
        ],
    },
    {
        "path": ["信息披露事务管理"],
        "models": [
            {
                "name": "syllabus_elt_v2",
            }
        ],
    },
    {
        "path": ["信息披露文件的存放与查阅"],
        "models": [
            {
                "name": "syllabus_elt_v2",
            }
        ],
    },
    {
        "path": ["合同的变更"],
        "models": [
            {
                "name": "syllabus_elt_v2",
            }
        ],
    },
    {
        "path": ["合同终止事由"],
        "models": [
            {
                "name": "syllabus_elt_v2",
            }
        ],
    },
    {
        "path": ["基金财产的清算"],
        "models": [
            {
                "name": "syllabus_elt_v2",
            }
        ],
    },
    {
        "path": ["清算费用"],
        "models": [
            {
                "name": "syllabus_elt_v2",
            }
        ],
    },
    {
        "path": ["基金财产清算剩余资产的分配"],
        "models": [
            {
                "name": "syllabus_elt_v2",
            }
        ],
    },
    {
        "path": ["基金财产清算的公告"],
        "models": [
            {
                "name": "syllabus_elt_v2",
            }
        ],
    },
    {
        "path": ["基金财产清算账册及文件的保存"],
        "models": [
            {
                "name": "syllabus_elt_v2",
            }
        ],
    },
    {
        "path": ["合同的效力"],
        "location_threshold": 0.2,
        "models": [
            {
                "name": "syllabus_based",
                "inject_syllabus_features": [
                    r"__regex__基金合同的效力",
                ],
                "paragraph_model": "para_match",
                "para_config": {
                    "paragraph_pattern": (
                        r"(?P<dst>《?基金合同》?经基金管理人、基金托管人双方.*?(并经中国证监会书面确认后生效|或授权代表签字))",
                        r"(?P<dst>《?基金合同》?报经中国证监会注册后.*?同日起失效)",
                        r"(?P<dst>《?基金合同》?的有效期自其生效之日起至基金财产清算结果报中国证监会备案并公告之日止)",
                    ),
                    "multi_elements": True,
                    "combine_paragraphs": True,
                },
            }
        ],
    },
]


def get_predictor_options():
    for option in predictor_options:
        models = option["models"]
        if [x for x in models if x["name"] in ["partial_text", "para_match"]]:
            models.append(
                {
                    "name": "score_filter",
                    "threshold": 0.2,
                    "aim_types": ["PARAGRAPH"],
                    "multi_elements": False,
                }
            )
        for model in models:
            if model["name"] in ["syllabus_elt_v2", "middle_paras"]:
                model["page_header_patterns"] = [r"^\d+[/]\d+$"]
            if model.get("paragraph_model") in ["middle_paras"]:
                model["para_config"]["page_header_patterns"] = [r"^\d+[/]\d+$"]

        option["models"] = models
    return predictor_options


prophet_config = {
    "depends": {},
    "predictor_options": get_predictor_options(),
}
