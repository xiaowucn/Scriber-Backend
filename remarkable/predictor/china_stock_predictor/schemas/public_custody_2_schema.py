"""
银河证券 19 公募-托管协议-二
"""

predictor_options = [
    {
        "path": ["基金托管协议的依据、目的和原则"],
        "models": [
            {
                "name": "syllabus_elt_v2",
            },
        ],
    },
    {
        "path": ["托管人对基金管理人选择存款银行进行监督"],
        "models": [
            {
                "name": "para_match",
                "paragraph_pattern": [
                    r"(?P<content>基金投资银行存款的，基金管理人应.*?的约定.*?基金托管人.*?进行监督。)"
                ],
            },
            {
                "name": "syllabus_elt_v2",
            },
        ],
    },
    {
        "path": ["托管人进行监督和核查的信息"],
        "models": [
            {"name": "para_match", "paragraph_pattern": [r"托管人.*?进行监督和核查"]},
        ],
    },
    {
        "path": ["管理人应积极配合托管人的监督和核查"],
        "models": [
            {
                "name": "middle_paras",
                "include_bottom_anchor": True,
                "neglect_top_anchor": [r"^.{1,6}基金托管人发现"],
                "top_anchor_regs": [r"管理人应积极配合(和协助)?(基金)?托管人的监督和核查"],
                "bottom_anchor_regs": [
                    (
                        r"基金管理人应向基金托管人提供履行托管职责所必需的相关材料，并保证向基金托管人提供的材料的真实性、准确性和完整性，"
                        r"由于基金管理人提供材料不实给基金托管人或基金财产造成损失的，由基金管理人承担赔偿责任。"
                    ),
                ],
            },
            {
                "name": "para_match",
                "paragraph_pattern": [
                    r"^.{,4}(基金)?管理人.*?配合.*托管人.*?核查",
                    r"管理人应积极配合(和协助)?(基金)?托管人的监督和核查",
                ],
            },
        ],
    },
    {
        "path": ["托管人的监督程序"],
        "models": [
            {
                "name": "syllabus_based",
                "inject_syllabus_features": [r"__regex__基金托管人对基金管理人的业务监督和核查"],
                "only_inject_features": True,
                "extract_from": "same_type_elements",
                "paragraph_model": "middle_paras",
                "para_config": {
                    "use_direct_elements": True,
                    "include_top_anchor": True,
                    "top_anchor_regs": [
                        r"若基金托管人发现基金管理人.*应当立即通知基金管理人，由此造成的损失由基金管理人承担",
                        r"基金管理人有义务.*托管人.*执行核查。对基金托管人发出的书面提示，基金管理人应在规定时间内答复并改正",
                        r"基金托管人发现基金管理人有重大违规行为，应立即报告中国证监会，同时通知基金管理人限期纠正，并将纠正结果报告中国证监会",
                    ],
                    "bottom_default": True,
                    "include_bottom_anchor": True,
                },
            },
            {
                "name": "syllabus_elt_v2",
                "inject_syllabus_features": [
                    r"__regex__基金托管人对基金管理人的业务监督和核查__regex__管理人.*托管人的监督和核查.*管理人.*提供",
                ],
                "only_inject_features": True,
            },
        ],
    },
    {
        "path": ["基金管理人对基金托管人的业务核查"],
        "models": [
            {
                "name": "syllabus_elt_v2",
            },
        ],
    },
    {
        "path": ["期货结算账户的开立和管理"],
        "models": [
            {
                "name": "syllabus_elt_v2",
            },
        ],
    },
    {
        "path": ["其他账户的开立和管理"],
        "models": [
            {
                "name": "syllabus_elt_v2",
            },
        ],
    },
    {
        "path": ["电子指令方式总体约定"],
        "models": [
            {
                "name": "para_match",
                "paragraph_pattern": [
                    r"基金管理人在运用基金财产时向基金托管人发送.*指令，基金托管人执行.*指令",
                ],
            },
        ],
    },
    {
        "path": ["基金管理人对发送指令人员的书面授权"],
        "models": [
            {
                "name": "syllabus_elt_v2",
            },
        ],
    },
    {
        "path": ["指令的内容"],
        "models": [
            {
                "name": "syllabus_elt_v2",
            },
        ],
    },
    {
        "path": ["指令的发送"],
        "models": [
            {
                "name": "syllabus_elt_v2",
            },
        ],
    },
    {
        "path": ["指令的确认"],
        "models": [
            {
                "name": "syllabus_elt_v2",
            },
        ],
    },
    {
        "path": ["指令的时间和执行"],
        "models": [
            {
                "name": "syllabus_elt_v2",
            },
        ],
    },
    {
        "path": ["基金管理人发送错误指令的情形和处理程序"],
        "models": [
            {
                "name": "syllabus_elt_v2",
            },
        ],
    },
    {
        "path": ["基金托管人依照法律、法规拒绝执行指令的情形和处理程序"],
        "models": [
            {
                "name": "syllabus_elt_v2",
            },
        ],
    },
    {
        "path": ["基金托管人未按照基金管理人指令执行的处理方法"],
        "models": [
            {
                "name": "syllabus_elt_v2",
            },
        ],
    },
    {
        "path": ["被授权人员的更换"],
        "models": [
            {
                "name": "syllabus_elt_v2",
            },
        ],
    },
    {
        "path": ["指令的其他事项"],
        "models": [
            {
                "name": "syllabus_elt_v2",
                "keep_parent": True,
            },
        ],
    },
    {
        "path": ["选择证券、期货买卖的证券、期货经营机构"],
        "models": [
            {
                "name": "syllabus_elt_v2",
            },
        ],
    },
    {
        "path": ["清算与交割"],
        "models": [
            {
                "name": "syllabus_elt_v2",
                "inject_syllabus_features": [r"__regex__清算与交割"],
            },
        ],
    },
    {
        "path": ["交易资金最高额度"],
        "models": [
            {
                "name": "syllabus_elt_v2",
            },
        ],
    },
    {
        "path": ["资金、证券帐目和交易记录的核对"],
        "models": [
            {
                "name": "syllabus_elt_v2",
            },
        ],
    },
    {
        "path": ["交易记录的核对"],
        "models": [
            {
                "name": "syllabus_elt_v2",
            },
        ],
    },
    {
        "path": ["资金账目的核对"],
        "models": [
            {
                "name": "syllabus_elt_v2",
            },
        ],
    },
    {
        "path": ["证券账目的核对"],
        "models": [
            {
                "name": "syllabus_elt_v2",
            },
        ],
    },
    {
        "path": ["实物券账目"],
        "models": [
            {
                "name": "syllabus_elt_v2",
            },
        ],
    },
    {
        "path": ["基金申购、赎回、转换业务处理的基本规定"],
        "models": [
            {
                "name": "syllabus_elt_v2",
            },
        ],
    },
    {
        "path": ["开放式基金申购、赎回和基金转换的资金清算"],
        "models": [
            {
                "name": "syllabus_elt_v2",
            },
        ],
    },
    {
        "path": ["融资业务和转融通证券出借业务"],
        "models": [
            {
                "name": "syllabus_elt_v2",
            },
        ],
    },
    {
        "path": ["申赎净额结算"],
        "models": [
            {
                "name": "syllabus_elt_v2",
            },
        ],
    },
    {
        "path": ["基金转换"],
        "models": [
            {
                "name": "syllabus_elt_v2",
            },
        ],
    },
    {
        "path": ["基金现金分红"],
        "models": [
            {
                "name": "syllabus_elt_v2",
            },
        ],
    },
    {
        "path": ["基金资产净值的计算、复核与完成的时间及程序"],
        "models": [
            {
                "name": "syllabus_elt_v2",
                "inject_syllabus_features": [
                    r"基金资产净值的计算及复核程序",
                ],
            },
        ],
    },
    {
        "path": ["估值对象"],
        "models": [
            {
                "name": "syllabus_elt_v2",
            },
        ],
    },
    {
        "path": ["特殊情况的处理"],
        "models": [
            {
                "name": "syllabus_elt_v2",
            },
        ],
    },
    {
        "path": ["估值错误类型"],
        "models": [
            {
                "name": "syllabus_elt_v2",
            },
        ],
    },
    {
        "path": ["估值错误处理原则"],
        "models": [
            {
                "name": "syllabus_elt_v2",
            },
        ],
    },
    {
        "path": ["估值错误处理程序"],
        "models": [
            {
                "name": "syllabus_elt_v2",
            },
        ],
    },
    {
        "path": ["基金份额净值估值错误处理的方法"],
        "models": [
            {
                "name": "syllabus_elt_v2",
            },
        ],
    },
    {
        "path": ["估值错误损失赔偿"],
        "models": [
            {
                "name": "syllabus_elt_v2",
            },
        ],
    },
    {
        "path": ["免责条款"],
        "models": [
            {
                "name": "syllabus_elt_v2",
            },
        ],
    },
    {
        "path": ["暂停估值的情形"],
        "models": [
            {
                "name": "syllabus_elt_v2",
            },
        ],
    },
    {
        "path": ["基金会计制度"],
        "models": [
            {
                "name": "syllabus_elt_v2",
            },
        ],
    },
    {
        "path": ["基金账册的建立"],
        "models": [
            {
                "name": "syllabus_elt_v2",
            },
        ],
    },
    {
        "path": ["会计数据和财务指标的核对"],
        "models": [
            {
                "name": "syllabus_elt_v2",
            },
        ],
    },
    {
        "path": ["基金定期报告的编制和复核"],
        "models": [
            {
                "name": "syllabus_elt_v2",
            },
        ],
    },
    {
        "path": ["基金收益分配"],
        "models": [
            {
                "name": "syllabus_elt_v2",
            },
        ],
    },
    {
        "path": ["保密义务"],
        "models": [
            {
                "name": "syllabus_elt_v2",
            },
        ],
    },
    {
        "path": ["基金管理人和基金托管人在基金信息披露中的职责和信息披露程序"],
        "models": [
            {
                "name": "syllabus_elt_v2",
                "inject_syllabus_features": [
                    r"__regex__基金管理人和基金托管人在(?:基金)?信息披露中的职责和信息披露程序",
                ],
            },
        ],
    },
    {
        "path": ["暂停或延迟信息披露的情形"],
        "models": [
            {"name": "syllabus_elt_v2", "neglect_patterns": [r"职责"]},
            {
                "name": "syllabus_based",
                "inject_syllabus_features": [r"__regex__^职责$"],
                "only_inject_features": True,
                "extract_from": "same_type_elements",
                "paragraph_model": "middle_paras",
                "para_config": {
                    "use_direct_elements": True,
                    "include_top_anchor": False,
                    "top_anchor_regs": [r"当出现下述情况时，基金管理人和基金托管人可暂停或延迟披露基金相关信息"],
                    "bottom_default": True,
                    "include_bottom_anchor": True,
                },
            },
        ],
    },
    {
        "path": ["基金托管人报告"],
        "models": [
            {
                "name": "syllabus_elt_v2",
            },
        ],
    },
    {
        "path": ["基金费用的其他规则"],
        "models": [
            {
                "name": "para_match",
                "paragraph_pattern": [r"基金的其他费用按照.*?计提和支付。"],
            },
        ],
    },
    {
        "path": ["基金有关文件档案的保存"],
        "models": [
            {
                "name": "syllabus_elt_v2",
                "inject_syllabus_features": [r"__regex__基金有关文件和?档案的保存"],
            },
        ],
    },
    {
        "path": ["更换管理人与托管人的其他约定"],
        "models": [
            {
                "name": "para_match",
                "paragraph_pattern": [
                    r"新.*?(基金)?(管理|托管)人.*?原任?基金(管理|托管)人",
                ],
            },
        ],
    },
    {
        "path": ["禁止行为"],
        "models": [
            {
                "name": "syllabus_elt_v2",
            },
        ],
    },
    {
        "path": ["基金财产清算小组"],
        "models": [
            {
                "name": "para_match",
                "paragraph_pattern": [r"基金财产清算小组[:：]", r"自出现.*?工作日内，成立基金财产清算小组"],
            },
        ],
    },
    {
        "path": ["基金财产清算小组组成"],
        "models": [
            {
                "name": "para_match",
                "paragraph_pattern": [
                    r"基金财产清算小组组成[:：]",
                    r"基金财产清算小组成员由.*组成",
                ],
            },
        ],
    },
    {
        "path": ["基金财产清算小组职责"],
        "models": [
            {
                "name": "para_match",
                "paragraph_pattern": [r"基金财产清算小组职责[:：]", r"基金财产清算小组负责"],
            },
        ],
    },
    {
        "path": ["基金财产清算程序"],
        "models": [
            {
                "name": "syllabus_elt_v2",
            },
        ],
    },
    {
        "path": ["基金财产清算期限"],
        "models": [
            {
                "name": "para_match",
                "paragraph_pattern": [r"基金财产清算的?期限.*"],
            },
        ],
    },
    {
        "path": ["违约责任"],
        "models": [
            {
                "name": "syllabus_elt_v2",
            },
        ],
    },
    {
        "path": ["争议解决方式"],
        "models": [
            {
                "name": "syllabus_elt_v2",
            },
        ],
    },
    {
        "path": ["其他事项"],
        "models": [
            {
                "name": "middle_paras",
                "top_greed": False,
                "include_top_anchor": False,
                "top_anchor_regs": [r"其他事项"],
                "bottom_anchor_regs": [r"(基金)?托管协议的签订"],
            },
        ],
    },
    {
        "path": ["基金托管协议的签订"],
        "models": [
            {
                "name": "para_match",
                "paragraph_pattern": [
                    r"(?P<content>本托管协议双方法定代表人或授权代表签章、签订地、签订日，见签署页。)"
                ],
            },
            {
                "name": "syllabus_elt_v2",
            },
        ],
    },
    {
        "path": ["基金管理人"],
        "models": [
            {
                "name": "syllabus_based",
                "inject_syllabus_features": [r"__regex__托管协议当事人__regex__基金管理人"],
                "paragraph_model": "partial_text",
                "para_config": {
                    "use_answer_pattern": False,
                    "model_alternative": True,
                    "名称": {
                        "regs": [r"名称[:：](?P<dst>.*)"],
                    },
                    "住所": {
                        "regs": [r"(住所|注册地址)[:：](?P<dst>.*)"],
                    },
                    "联系电话": {
                        "regs": [r"电话[:：](?P<dst>.*)"],
                    },
                },
            },
            {
                "name": "row_match",
                "title_patterns": [r"基金管理人"],
                "名称": {
                    "row_pattern": [r"名称"],
                    "content_pattern": [r"名称[:：](?P<dst>.*)"],
                },
            },
        ],
    },
    {
        "path": ["基金托管人"],
        "models": [
            {
                "name": "syllabus_based",
                "inject_syllabus_features": [r"__regex__托管协议当事人__regex__基金托管人"],
                "table_regarded_as_paras": True,
                "paragraph_model": "partial_text",
                "para_config": {
                    "use_answer_pattern": False,
                    "model_alternative": True,
                    "名称": {
                        "regs": [r"名称[:：](?P<dst>.*)"],
                    },
                    "住所": {
                        "regs": [r"(住所|注册地址)[:：](?P<dst>.*)"],
                    },
                    "联系电话": {
                        "regs": [r"电话[:：](?P<dst>.*)"],
                    },
                    "通讯地址": {
                        "regs": [r"通讯地址[:：](?P<dst>.*)"],
                    },
                    "批准设立机关及批准设立文号": {
                        "neglect_patterns": [r"法定代表人"],
                    },
                },
            },
            {
                "name": "row_match",
                "title_patterns": [r"基金托管人"],
                "名称": {
                    "row_pattern": [r"名称"],
                    "content_pattern": [r"名称[:：](?P<dst>.*)"],
                },
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
                "title_patterns": [r"基金托管人"],
                "row_pattern": [r"经营范围"],
                "content_pattern": [r"经营范围[:：](?P<dst>.*)"],
            },
        ],
    },
    {
        "path": ["实施侧袋机制期间的基金资产估值"],
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
