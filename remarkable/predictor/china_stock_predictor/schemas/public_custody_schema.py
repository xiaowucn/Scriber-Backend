"""银河证券 5 公募-托管协议"""

predictor_options = [
    {
        "path": ["基金名称"],
        "models": [
            {
                "name": "fixed_position",
                "positions": list(range(5, 100)),
                "regs": [r"担任(?P<dst>.*基金.{0,5})的基金管理人", r"《(?P<dst>[^、《]*基金.{0,5})基金合同"],
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
            {
                "name": "row_match",
                "row_pattern": [r"名称"],
                "content_pattern": [r"名称[:：](?P<dst>.*)"],
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
            {
                "name": "row_match",
                "row_pattern": [r"住所|注册地址"],
                "content_pattern": [r"(住所|注册地址)[:：](?P<dst>.*)"],
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
            {
                "name": "row_match",
                "row_pattern": [r"法定代表人"],
                "content_pattern": [r"法定代表人[:：](?P<dst>.*)"],
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
            {
                "name": "row_match",
                "row_pattern": [r"批准设立机关及批准设立文号"],
                "content_pattern": [r"批准设立机关及批准设立文号[:：](?P<dst>.*)"],
            },
        ],
    },
    {
        "path": ["基金管理人", "联系电话"],
        "models": [
            {
                "name": "partial_text",
                "use_answer_pattern": False,
                "regs": [r"电话[:：](?P<dst>.*)"],
                "model_alternative": True,
            },
            {
                "name": "row_match",
                "row_pattern": [r"(联系)?电话"],
                "content_pattern": [r"(联系)?电话[:：](?P<dst>.*)"],
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
            {
                "name": "row_match",
                "row_pattern": [r"名称"],
                "content_pattern": [r"名称[:：](?P<dst>.*)"],
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
            {
                "name": "row_match",
                "row_pattern": [r"住所|注册地址"],
                "content_pattern": [r"(住所|注册地址)[:：](?P<dst>.*)"],
            },
        ],
    },
    {
        "path": ["基金托管人", "通讯地址"],
        "models": [
            {
                "name": "partial_text",
                "use_answer_pattern": False,
                "regs": [r"通讯地址[:：](?P<dst>.*)"],
                "model_alternative": True,
            },
            {
                "name": "row_match",
                "row_pattern": [r"通讯地址"],
                "content_pattern": [r"通讯地址[:：](?P<dst>.*)"],
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
            {
                "name": "row_match",
                "row_pattern": [r"法定代表人"],
                "content_pattern": [r"法定代表人[:：](?P<dst>.*)"],
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
            {
                "name": "row_match",
                "row_pattern": [r"批准设立机关及批准设立文号"],
                "content_pattern": [r"批准设立机关及批准设立文号[:：](?P<dst>.*)"],
            },
        ],
    },
    {
        "path": ["基金托管人-经营范围"],
        "models": [
            {
                "name": "para_match",
                "paragraph_pattern": r"经营范围[:：](?P<content>.*)",
                "content_pattern": r"经营范围[:：](?P<content>.*)",
            },
            {
                "name": "row_match",
                "row_pattern": [r"经营范围"],
                "content_pattern": [r"经营范围[:：](?P<dst>.*)"],
            },
        ],
    },
    {
        "path": ["托管人对管理人的监督"],
        "models": [
            {
                "name": "syllabus_based",
                "extract_from": "same_type_elements",
                "inject_syllabus_features": [
                    r"目录|基金托管人对基金管理人的业务监督和核查",
                    "__regex__基金托管人对基金管理人的业务监督和核查.?$",
                ],
                "neglect_patterns": [r"基金合同"],
                "ignore_syllabus_children": True,
                "max_syllabus_range": 200,
                "include_title": True,
                "paragraph_model": "middle_paras",
                "para_config": {
                    "use_direct_elements": True,
                    "include_top_anchor": True,
                    "bottom_default": True,
                    "top_anchor_regs": [
                        r"《?基金合同》?明确约定",
                        r"基金管理人应将本基金拟投资的",
                        r"基金管理人可以根据实际情况的变化，对各投资品种的具体范围予以更新和调整",
                        r"本基金的投资范围为具有良好流动性的金融工具",
                        r"本基金主要投资于标的指数成份股和备选成份股",
                        r"本基金的投资范围主要为标的指数成份股及备选成份股",
                        r"本基金将投资于以下金融工具",
                    ],
                    "bottom_anchor_regs": [
                        r"基金托管人根据有关法律法规的规定.*进行监督",
                        # r'基金管理人在履行适当程序后，可以将其纳入投资范围',
                        # r'部门规章及基金合同禁止投资的投资工具',
                        # r'其他金融工具的投资比例符合法律法规和监管机构的规定',
                        # r'本基金可根据法律法规的规定参与融资业务以及转融通证券出借业务',
                        # r'本基金投资于目标ETF的资产比例.*本基金应当保持不低于.*，其中现金不包括结算备付金.*等。',
                        # r'股票资产占基金资产的比例为.*本基金.*在扣除.*后，应当保持不低于.*现金或者到期日在一年以内的政府债券。',
                        # r'基金托管人对基金管理人业务进行监督和核查的义务自基金合同生效日起开始履行'
                    ],
                    "top_anchor_content_regs": [
                        r"(?P<content>《?基金合同》?明确约定.*)",
                        r"(?P<content>基金管理人应将本基金拟投资的.*)",
                        # r'(?P<content>.*《?基金合同》?和本协议的约定.*)',
                        r"(?P<content>本基金主要投资于标的指数成份股和备选成份股.*)",
                        r"(?P<content>本基金的投资范围.*)",
                    ],
                },
            }
        ],
    },
    {
        "path": ["投资比例监督"],
        "models": [
            {
                "name": "middle_paras",
                "use_syllabus_model": True,
                "top_default": True,
                "bottom_default": True,
                "include_top_anchor": False,
                "inject_syllabus_features": [r"__regex__基金托管人对基金管理人的业务监督和核查.?$"],
                "only_inject_features": True,
                "top_anchor_regs": [
                    r"基金托管人根据有关.*的[约规]定.*对.*投融?资.*比例进行监督",
                ],
                "bottom_anchor_regs": [
                    r"基金托管人根据有关法律法规的规定.*?基金投资禁止行为.*进行监督",
                    r"基金财产不得用于下列投资或者活动",
                ],
            }
        ],
    },
    {
        "path": ["基金财产不得用于下列投资或者活动"],
        "models": [
            {
                "name": "middle_paras",
                "use_syllabus_model": True,
                "inject_syllabus_features": [r"基金托管人对基金管理人的投资行为行使监督权"],
                "include_top_anchor": True,
                "include_bottom_anchor": True,
                "top_default": True,
                "bottom_greed": True,
                "top_anchor_regs": [
                    r"根据(有关)?法律法规的规定.*?本基金禁止从事下列行为",
                    r"基金财产(不得)?用于下列投资或者活动",
                ],
                "bottom_anchor_regs": [
                    r"法律.*?行政法规和中国证监会规定禁止的其他活动",
                    r"依照法律法规有关规定.*?由中国证监会规定禁止的其他活动",
                    r"如法律法规或监管部门取消上述禁止性规定.*?如适用于本基金.*?则本基金投资不再受相关限制",
                    r"法律、行政法规和国务院证券监督管理机构规定禁止的其他活动",
                    r"根据法律法规有关基金从事的关联交易的规定，基金管理人.*事先相互提供与本机构有控股.*并负责及时将更新后的名单发送给对方",
                ],
            },
            {
                "name": "para_match",
                "paragraph_pattern": (
                    r"承销证券.*?违反规定向他人贷款或者提供担保.*?从事承担无限责任的投资.*?禁止的其他活动",
                ),
            },
        ],
    },
    {
        "path": ["对基金管理人参与银行间债券市场进行监督"],
        "models": [
            {
                "name": "syllabus_elt_v2",
                "only_inject_features": True,
                "inject_syllabus_features": [r"__regex__对基金管理人参与银行间债券市场进行监督.?$"],
            },
            {
                "name": "syllabus_based",
                "extract_from": "same_type_elements",
                "only_inject_features": True,
                "inject_syllabus_features": [
                    r"目录|基金托管人对基金管理人的业务监督和核查",
                    "__regex__基金托管人对基金管理人的业务监督和核查.?$",
                ],
                "neglect_patterns": [r"基金合同"],
                "ignore_syllabus_children": True,
                "max_syllabus_range": 200,
                "paragraph_model": "middle_paras",
                "para_config": {
                    "use_direct_elements": True,
                    "include_top_anchor": True,
                    "include_bottom_anchor": True,
                    "bottom_default": True,
                    "top_anchor_regs": [
                        r"基金托管人[根依]据有关法律法规的规定[及和]《?基金合同》?的约定，?对基金管理人参与银行间债券市场进行监督",
                    ],
                    "bottom_anchor_regs": [
                        r"基金管理人应在基金投资运作之前向基金托管人提供经慎重选择的.*基金托管人不承担由此造成的任何损失和责任。$",
                        r"基金托管人应及时提醒基金管理人，基金托管人不承担由此造成的任何损失和责任。",
                    ],
                    "top_anchor_content_regs": [
                        r"对基金管理人参与银行间债券市场进行监督。(?P<content>.*)",
                    ],
                },
            },
        ],
    },
    {
        "path": ["对基金管理人投资流通受限证券进行监督"],
        "models": [
            {
                "name": "middle_paras",
                "use_syllabus_model": True,
                "inject_syllabus_features": [
                    r"__regex__基金托管人对基金管理人的业务监督和核查.?$",
                ],
                "include_top_anchor": True,
                "include_bottom_anchor": True,
                "bottom_default": True,
                "top_anchor_regs": [
                    r"基金(管理人)?投资流通受限证券.*进行监督",
                    # r'(?<!本)基金(管理人)?投资流通受限证券(?!的比例)',
                ],
                "bottom_anchor_regs": [
                    r"基金投资中期票据",
                    r"相关法律法规对基金投资(流通)?受限证券有新规定的，从其规定",
                ],
                "top_anchor_content_regs": [r"(?P<content>基金管理人投资流通受限证券.*)"],
            }
        ],
    },
    {
        "path": ["基金财产保管的原则"],
        "models": [
            {
                "name": "syllabus_elt_v2",
            },
        ],
    },
    {
        "path": ["基金合同生效时募集资产的验证"],
        "models": [
            {
                "name": "syllabus_elt_v2",
            },
        ],
    },
    {
        "path": ["基金的银行存款账户的开立和管理"],
        "models": [
            {
                "name": "syllabus_elt_v2",
            },
        ],
    },
    {
        "path": ["基金证券账户及结算备付金账户的开立和管理"],
        "models": [
            {
                "name": "syllabus_elt_v2",
            },
        ],
    },
    {
        "path": ["债券托管账户的开立和管理"],
        "models": [
            {
                "name": "syllabus_elt_v2",
            },
        ],
    },
    {
        "path": ["基金财产投资的有关实物证券、银行存款定期存单等有价凭证的保管"],
        "models": [
            {
                "name": "syllabus_elt_v2",
            },
            {
                "name": "para_match",
                "paragraph_pattern": [
                    r"基金财产投资的有关实物证券、银行(存款|定期){2}存单等有价凭证的保管(?P<content>.*)"
                ],
            },
        ],
    },
    {
        "path": ["与基金财产有关的重大合同的保管"],
        "models": [
            {
                "name": "syllabus_elt_v2",
            },
        ],
    },
    {
        "path": ["基金投资证券后的清算交收安排"],
        "models": [
            {"name": "syllabus_elt_v2", "neglect_patterns": [r"清算与交割", r"基金清算和交收中的责任"]},
        ],
    },
    {
        "path": ["投资银行存款"],
        "models": [
            {
                "name": "middle_paras",
                "use_syllabus_model": True,
                "top_default": True,
                "inject_syllabus_features": [r"投资银行存款的特别约定"],
                "only_inject_features": True,
                "bottom_anchor_regs": [
                    r"\d.基金资产净值计算和会计核算",
                ],
            },
            {
                "name": "syllabus_elt_v2",
            },
        ],
    },
    {
        "path": ["估值方法"],
        "models": [
            {
                "name": "syllabus_elt_v2",
                "inject_syllabus_features": [
                    "__regex__估值方法$",
                    "__regex__证券交易所上市的有价证券的估值",
                    "__regex__目标ETF的估值",
                ],
            },
        ],
    },
    {
        "path": ["基金份额净值错误的处理方式"],
        "models": [
            {
                "name": "syllabus_elt_v2",
                "inject_syllabus_features": [
                    r"__regex__估值(错误|差错)的?处理",
                    r"__regex__基金份额净值估值错误处理的方法如下",
                ],
            },
        ],
    },
    {
        "path": ["信息披露文件"],
        "models": [
            {
                "name": "para_match",
                "paragraph_pattern": (
                    r"基金的信息披露(内容)?主要包括.*",
                    r"本基金信息披露的文件.*",
                    r"基金托管人应当按照相关法律.*等公开披露的.*复核.*基金托管人应.*发布临时公告",
                ),
            },
        ],
    },
    {
        "path": ["托管费率"],
        "models": [
            {
                "name": "para_match",
                "paragraph_pattern": (
                    r"(?P<content>本?基金的?托管费按前一日基金资产净值.*?年费率计提)",
                    r"(?P<content>本基金的托管费率为年费率.*?。)",
                    r"(?P<content>基金托管费按基金资产净值的.*?计提。)",
                    r"(?P<content>在通常情况下.*?按前一日基金资产净值.*?年费率计提)",
                ),
                "content_pattern": r"(?P<content>.*)托管费的计算方法如下",
            },
            {
                "name": "middle_paras",
                "use_syllabus_model": True,
                "top_default": True,
                "include_top_anchor": True,
                "top_anchor_content_regs": [
                    r"(?P<content>.*)托管费的计算方法如下",
                ],
                "top_anchor_regs": [
                    r"基金托管费的计提比例和计提方法",
                ],
                "bottom_anchor_regs": [
                    r"÷当年天数",
                ],
            },
        ],
    },
    {
        "path": ["托管费计提及支付方式"],
        "models": [
            {
                "name": "middle_paras",
                "use_syllabus_model": True,
                "include_top_anchor": False,
                "bottom_default": True,
                "top_anchor_regs": [
                    r"托管费.*?计算方法如下",
                ],
                "bottom_anchor_regs": [
                    r"期货交易费用",
                    r"[(（][一二三四五六七八九十]+[)）].*费",
                ],
            },
        ],
    },
    {
        "path": ["管理费率"],
        "models": [
            {
                "name": "para_match",
                "paragraph_pattern": (
                    r"(?P<content>本?基金的?管理费.*?基金资产净值的.*?年费率计提。|本基金的管理费率为年费率。)",
                    r"(?P<content>本?基金的?管理费按前一日基金资产净值扣除.*?年费率计提)",
                    r"(?P<content>在通常情况下.*?按前一日基金资产净值.*?年费率计提)",
                    r"(?P<content>本基金的管理费率为年费率.*?。)",
                ),
                "content_pattern": r"(?P<content>.*)管理费的计算方法如下",
            }
        ],
    },
    {
        "path": ["管理费计提及支付方式"],
        "models": [
            {
                "name": "middle_paras",
                "use_syllabus_model": True,
                "bottom_default": True,
                "include_top_anchor": False,
                "top_anchor_regs": [
                    r"管理费.*?的?计算方法如下",
                ],
                "bottom_anchor_regs": [
                    r"[(（][一二三四五六七八九十]+[)）].*费",
                ],
            },
        ],
    },
    {
        "path": ["基金份额持有人名册的保管"],
        "models": [
            {
                "name": "syllabus_elt_v2",
            },
        ],
    },
    {
        "path": ["基金管理人职责终止的情形"],
        "models": [
            {
                "name": "middle_paras",
                "use_syllabus_model": True,
                "include_top_anchor": True,
                "include_bottom_anchor": True,
                "bottom_default": True,
                "top_anchor_regs": [
                    r"有下列情形之一的，基金管理人职责终止",
                ],
                "bottom_anchor_regs": [r"法律法规及中国证监会规定的和《?基金合同》?约定的其他情形。?"],
            },
        ],
    },
    {
        "path": ["基金托管人职责终止的情形"],
        "models": [
            {
                "name": "middle_paras",
                "use_syllabus_model": True,
                "include_top_anchor": True,
                "include_bottom_anchor": True,
                "bottom_default": True,
                "top_anchor_regs": [r"有下列情形之一的，基金托管人职责终止", r"有下列情形之一的，可以更换基金托管人"],
                "bottom_anchor_regs": [r"法律法规及中国证监会规定的和《?基金合同》?约定的其他情形。?"],
            },
        ],
    },
    {
        "path": ["基金管理人的更换程序"],
        "models": [
            {
                "name": "middle_paras",
                "use_syllabus_model": True,
                "bottom_default": True,
                "top_anchor_regs": [
                    r"更换基金管理人必须依照如下程序进行",
                ],
                "bottom_anchor_regs": [
                    r"替换或删除基金名称中与原任?基金管理人有关的名称",
                ],
            },
        ],
    },
    {
        "path": ["基金托管人的更换程序"],
        "models": [
            {
                "name": "middle_paras",
                "use_syllabus_model": True,
                "include_title": True,
                "include_top_anchor": False,
                "include_bottom_anchor": True,
                "top_anchor_regs": [
                    r"基金托管人的更换程序",
                ],
                "bottom_anchor_regs": [
                    r"审计.*?基金托管人职责终止的",
                ],
            },
        ],
    },
    {
        "path": ["基金管理人与基金托管人同时更换的条件和程序"],
        "models": [
            {"name": "syllabus_elt_v2", "inject_syllabus_features": [r"基金管理人与基金托管人同时更换(和程序)?"]},
        ],
    },
    {
        "path": ["基金托管协议的变更"],
        "models": [
            {
                "name": "para_match",
                "paragraph_pattern": r"(?P<dst>本协议双方当事人经协商一致.*?其内容不得与《?基金合同》?的规定有任何冲突.*?报中国证监会备案)",
            }
        ],
    },
    {
        "path": ["基金托管协议的终止"],
        "models": [
            {
                "name": "middle_paras",
                "use_syllabus_model": True,
                "include_top_anchor": True,
                "include_bottom_anchor": True,
                "bottom_default": True,
                "top_default": True,
                "top_anchor_regs": [
                    r"《基金合同》终止",
                ],
                "bottom_anchor_regs": [
                    r"发生法律法规.*?规定的终止事项",
                ],
            },
        ],
    },
    {
        "path": ["基金财产的清算"],
        "models": [
            {
                "name": "middle_paras",
                "use_syllabus_model": True,
                "include_top_anchor": True,
                "top_default": True,
                "top_anchor_regs": [
                    r"1.基金财产的清算",
                ],
                "bottom_anchor_regs": [
                    r"清算费用",
                ],
            },
        ],
    },
    {
        "path": ["清算费用"],
        "models": [
            {
                "name": "para_match",
                "paragraph_pattern": r"(?P<content>清算费用是指基金(财产)?清算小组在进行基金(财产)?清算过程中发生的所有合理费用.*)",
            },
        ],
    },
    {
        "path": ["基金财产清算剩余资产的分配"],
        "models": [
            {
                "name": "para_match",
                "paragraph_pattern": r"依据基金财产清算的分配方案，将基金财产清算后的全部剩余资产扣除基金财产清算费用.*",
            },
            {
                "name": "middle_paras",
                "use_syllabus_model": True,
                "include_title": True,
                "include_top_anchor": False,
                "include_bottom_anchor": True,
                "bottom_default": True,
                "top_anchor_regs": [
                    r"基金财产按下列顺序清偿",
                ],
                "bottom_anchor_regs": [
                    r"不分配给基金份额持有人",
                    r"基金财产清算的公告",
                ],
            },
        ],
    },
    {
        "path": ["基金财产清算的公告"],
        "models": [
            {
                "name": "middle_paras",
                "use_syllabus_model": True,
                "include_top_anchor": False,
                "top_anchor_regs": [
                    r"基金财产清算的公告",
                ],
                "bottom_anchor_regs": [
                    r"基金财产清算账册及文件的保存",
                ],
            },
            {
                "name": "para_match",
                "paragraph_pattern": r"清算过程中的有关重大事项须及时公告.*?清算小组进行公告",
            },
        ],
    },
    {
        "path": ["基金财产清算账册及文件的保存"],
        "models": [
            {
                "name": "para_match",
                "paragraph_pattern": r"基金财产清算账册及有关文件由基金托管人保存.*",
            },
        ],
    },
    {
        "path": ["基金托管协议的效力"],
        "models": [
            {
                "name": "syllabus_elt_v2",
            },
        ],
    },
]
prophet_config = {
    "depends": {},
    "predictor_options": predictor_options,
}
