"""银河证券 6 公募-资产管理合同"""

P_TITLE_HEAD = r"^[(（]?[\d一二三四五六七八九十]+[）)、.]?"

P_ACCRUAL_METHOD = [r"__regex__费用计提方[法式]、计提标准和支付方式", r"费用计提标准、计提方式、支付方式及费率调整"]

predictor_options = [
    {
        "path": ["计划名称"],
        "models": [
            {
                "name": "syllabus_based",
                "inject_syllabus_features": [r"释义"],
                "only_inject_features": True,
                "ignore_syllabus_children": True,
                "max_syllabus_range": 100,
                "extract_from": "same_type_elements",
                "para_config": {
                    "regs": [
                        r"资产管理合同.*《(?P<dst>.*资产管理计划)",
                        r"指资产委托人、资产管理人[及和]资产托管人(三方)?签署的《(?P<dst>.*资产管理计划)",
                    ],
                },
            },
            {"name": "fixed_position", "positions": list(range(0, 3)), "regs": [r"(?P<dst>.*资产管理计划)"]},
        ],
    },
    {
        "path": ["管理人承诺"],
        "models": [
            {
                "name": "syllabus_elt_v2",
            },
        ],
    },
    {
        "path": ["托管人承诺"],
        "models": [
            {
                "name": "syllabus_elt_v2",
            },
        ],
    },
    {
        "path": ["委托人声明"],
        "models": [
            {
                "name": "syllabus_elt_v2",
            },
        ],
    },
    {
        "path": ["投资者名称"],
        "models": [
            {
                "name": "fixed_position",
                "positions": list(range(2, 6)),
                "regs": [
                    r"(投资者|委托人)[:：]?\s?(?P<dst>.*?)管理人",
                    r"(投资者|委托人)[:：]?\s?(?P<dst>.*)",
                ],
            },
        ],
    },
    {
        "path": ["计划管理人"],
        "models": [
            {
                "name": "elements_collector_based",
                "elements_collect_model": "middle_paras",
                "elements_collect_config": {
                    "use_syllabus_model": True,
                    "include_title": True,
                    "top_anchor_regs": [r"管理人的基本(情况|信息)", r"资产管理人(概况)?"],
                    "bottom_anchor_regs": [r"管理人的权利", r"托管人"],
                    "table_regarded_as_paras": True,
                },
                "paragraph_model": "partial_text",
                "para_config": {
                    "multi_elements": True,
                    "use_answer_pattern": False,
                    "model_alternative": True,
                    "名称": {
                        "regs": [r"名称[:：](?P<dst>.*)"],
                    },
                    "住所": {
                        "regs": [r"住所[:：](?P<dst>.*)"],
                    },
                    "法定代表人或授权代表": {
                        "regs": [
                            r"(?:(?:法定代表人|授权代表)或?){1,2}[:：](?P<dst>.*)",
                        ],
                    },
                    "批准设立机关及批准设立文号": {
                        "regs": [r"批准设立机关及批准设立文号[:：](?P<dst>.*)"],
                    },
                    "联系电话": {
                        "regs": [r"联系电话[:：](?P<dst>.*)"],
                    },
                    "统一社会信用代码": {
                        "regs": [r"统一社会信用代码[:：](?P<dst>.*)"],
                    },
                    "联系人": {
                        "regs": [r"联系人[:：](?P<dst>.*)"],
                    },
                    "通讯地址": {
                        "regs": [r"通讯地址[:：](?P<dst>.*)"],
                    },
                    "邮政编码": {
                        "regs": [r"邮政编码[:：](?P<dst>.*)"],
                    },
                    "传真": {
                        "regs": [r"传真[:：](?P<dst>.*)"],
                    },
                    "信息披露网址": {
                        "regs": [r"(信息披露网(站地)?址|网站)[:：](?P<dst>.*)"],
                    },
                },
            },
            {
                "name": "partial_text",
                "multi_elements": True,
                "use_answer_pattern": False,
            },
        ],
    },
    {
        "path": ["计划托管人"],
        "models": [
            {
                "name": "elements_collector_based",
                "elements_collect_model": "middle_paras",
                "elements_collect_config": {
                    "use_syllabus_model": True,
                    "include_title": True,
                    "top_anchor_regs": [r"托管人的基本(情况|信息)", r"托管人(概况)?"],
                    "bottom_anchor_regs": [r"(托管人|投资者|委托人)的(权利|义务)"],
                    "table_regarded_as_paras": True,
                },
                "paragraph_model": "partial_text",
                "para_config": {
                    "multi_elements": True,
                    "use_answer_pattern": False,
                    "model_alternative": True,
                    "名称": {
                        "regs": [r"名称[:：](?P<dst>.*)"],
                    },
                    "住所": {
                        "regs": [r"住所[:：](?P<dst>.*)"],
                    },
                    "通讯地址": {
                        "regs": [r"通讯地址[:：](?P<dst>.*)"],
                    },
                    "法定代表人或授权代表": {
                        "regs": [
                            r"(?:(?:法定代表人|授权代表)或?){1,2}[:：](?P<dst>.*)",
                        ],
                    },
                    "批准设立机关及批准设立文号": {
                        "regs": [r"批准设立机关及批准设立文号[:：](?P<dst>.*)"],
                    },
                    "统一社会信用代码": {
                        "regs": [r"统一社会信用代码[:：](?P<dst>.*)"],
                    },
                    "联系人": {
                        "regs": [r"联系人[:：](?P<dst>.*)"],
                    },
                    "联系电话": {
                        "regs": [r"联系电话[:：](?P<dst>.*)"],
                    },
                    "传真": {
                        "regs": [r"传真[:：](?P<dst>.*)"],
                    },
                },
            },
        ],
    },
    {
        "path": ["计划的类别、类型"],
        "models": [
            {
                "name": "syllabus_elt_v2",
            },
        ],
    },
    {
        "path": ["运作方式"],
        "models": [
            {
                "name": "syllabus_elt_v2",
            },
        ],
    },
    {
        "path": ["基金中基金资产管理计划（FOF）或管理人中管理人资产管理计划（MOM）特别标识"],
        "models": [
            {
                "name": "syllabus_elt_v2",
                "inject_syllabus_features": [
                    r"__regex__基金中基金资产管理计划.*?或管理人中管理人资产管理计划.*?特别标识"
                ],
            },
            {
                "name": "para_match",
                "paragraph_pattern": [
                    r"基金中基金资产管理计划（FOF）或管理人中管理人资产管理计划（MOM）特别标识(?P<content>无)"
                ],
                "content_pattern": [
                    r"基金中基金资产管理计划（FOF）或管理人中管理人资产管理计划（MOM）特别标识(?P<content>无)"
                ],
            },
        ],
    },
    {
        "path": ["计划的投资目标"],
        "models": [
            {
                "name": "partial_text",
            },
            {
                "name": "score_filter",
                "threshold": 0.5,
                "aim_types": ["PARAGRAPH"],
                "multi_elements": False,
            },
        ],
    },
    {
        "path": ["最低初始规模"],
        "models": [
            {
                "name": "syllabus_elt_v2",
            },
        ],
    },
    {
        "path": ["份额的初始募集面值"],
        "models": [
            {
                "name": "syllabus_elt_v2",
                "inject_syllabus_features": [r"__regex__份额的初始募集面值", r"初始销售面值"],
                "only_inject_features": True,
            },
            {
                "name": "partial_text",
                "regs": [r"计划每?份额的?初始(募集)?面值[:：为]*(?P<dst>.*元)"],
            },
        ],
    },
    {
        "path": ["存续期"],
        "models": [
            {
                "name": "syllabus_elt_v2",
                "inject_syllabus_features": [r"__regex__基金存续期限"],
            },
        ],
    },
    {
        "path": ["产品风险等级/风险收益特征"],
        "models": [
            {
                "name": "para_match",
                "paragraph_pattern": r"产品(风险等级|风险收益特征)[:：](?P<content>.+)",
                "content_pattern": r"产品(风险等级|风险收益特征)[:：](?P<content>.+)",
            },
            {
                "name": "middle_paras",
                "use_syllabus_model": True,
                "inject_syllabus_features": [r"__regex__(基金|资产管理计划)的基本情况"],
                "only_inject_features": True,
                "top_anchor_regs": [r"(产品|计划)的?风险等级[:：]?$", r"风险收益特征[:：]?$"],
                "bottom_anchor_regs": [
                    r"存续期限[:：]?$",
                    r"(基金|资产管理计划)份额的初始募集",
                    r"(基金|资产管理计划)的份额登记",
                ],
                "include_top_anchor": False,
                "top_greed": False,
            },
        ],
    },
    {
        "path": ["募集期限"],
        "models": [
            {
                "name": "syllabus_elt_v2",
            },
        ],
    },
    {
        "path": ["募集方式"],
        "models": [
            {
                "name": "syllabus_elt_v2",
            },
        ],
    },
    {
        "path": ["募集对象"],
        "models": [
            {
                "name": "syllabus_elt_v2",
            },
        ],
    },
    {
        "path": ["资产管理计划的最低认购金额和支付方式"],
        "models": [
            {
                "name": "syllabus_elt_v2",
            },
        ],
    },
    {
        "path": ["资产管理计划份额的认购费用"],
        "models": [
            {
                "name": "syllabus_elt_v2",
            },
        ],
    },
    {
        "path": ["初始募集期的认购程序"],
        "models": [
            {
                "name": "syllabus_elt_v2",
            },
        ],
    },
    {
        "path": ["管理人拒绝委托人认购的情形"],
        "models": [
            {
                "name": "middle_paras",
                "use_syllabus_model": True,
                "top_anchor_regs": [r"拒绝委托人的认购[:：]"],
                "bottom_anchor_regs": [r"如果委托人的认购被拒绝"],
                "include_top_anchor": False,
            },
        ],
    },
    {
        "path": ["初始认购资金的管理及利息处理方式"],
        "models": [
            {
                "name": "syllabus_elt_v2",
            },
        ],
    },
    {
        "path": ["认购份额的计算方式"],
        "models": [
            {
                "name": "syllabus_elt_v2",
            },
        ],
    },
    {
        "path": ["募集结算专用账户和销售机构委托募集账户"],
        "models": [
            {
                "name": "para_match",
                "paragraph_pattern": r"本资产管理计划募集结算专用账户",
            },
        ],
    },
    {
        "path": ["募集账户", "户名"],
        "models": [
            {
                "name": "syllabus_based",
                "inject_syllabus_features": [r"__regex__(基金|资产管理计划)(份额)?的(初始)?募集"],
                "only_inject_features": True,
                "extract_from": "same_type_elements",
                "ignore_syllabus_children": True,
                "max_syllabus_range": 100,
                "paragraph_model": "partial_text",
                "para_config": {
                    "use_answer_pattern": False,
                    "multi_elements": True,
                },
            },
        ],
    },
    {
        "path": ["募集账户", "账号"],
        "models": [
            {
                "name": "syllabus_based",
                "inject_syllabus_features": [r"__regex__(基金|资产管理计划)(份额)?的(初始)?募集"],
                "only_inject_features": True,
                "extract_from": "same_type_elements",
                "ignore_syllabus_children": True,
                "max_syllabus_range": 100,
                "paragraph_model": "partial_text",
                "para_config": {
                    "use_answer_pattern": False,
                    "multi_elements": True,
                },
            },
        ],
    },
    {
        "path": ["募集账户", "开户行名称"],
        "models": [
            {
                "name": "syllabus_based",
                "inject_syllabus_features": [r"__regex__(基金|资产管理计划)(份额)?的(初始)?募集"],
                "only_inject_features": True,
                "extract_from": "same_type_elements",
                "ignore_syllabus_children": True,
                "max_syllabus_range": 100,
                "paragraph_model": "partial_text",
                "para_config": {
                    "use_answer_pattern": False,
                    "multi_elements": True,
                },
            },
        ],
    },
    {
        "path": ["资产管理计划成立的条件 "],
        "models": [
            {
                "name": "syllabus_elt_v2",
            },
        ],
    },
    {
        "path": ["初始募集规模"],
        "models": [
            {
                "name": "para_match",
                "paragraph_pattern": r"(?P<content>初始募集规模.*)",
                "content_pattern": r"(?P<content>初始募集规模.*)",
            },
        ],
    },
    {
        "path": ["投资者人数"],
        "models": [
            {
                "name": "para_match",
                "paragraph_pattern": r"(?P<content>投资者人数.*)",
                "content_pattern": r"(?P<content>投资者人数.*)",
            },
        ],
    },
    {
        "path": ["资产管理计划的成立与备案"],
        "models": [
            {
                "name": "syllabus_elt_v2",
                "inject_syllabus_features": [r"资产管理计划的成立与备案|资产管理计划的成立与备案"],
            },
        ],
    },
    {
        "path": ["资产管理合同的生效"],
        "models": [
            {
                "name": "syllabus_elt_v2",
                "inject_syllabus_features": [r"资产管理合同的生效"],
                "only_inject_features": True,
            },
        ],
    },
    {
        "path": ["无法获得基金业协会的备案或不予备案"],
        "models": [
            {
                "name": "syllabus_elt_v2",
            },
        ],
    },
    {
        "path": ["资产管理计划不能满足成立条件的处理方式/募集失败的处理方式"],
        "models": [
            {
                "name": "syllabus_elt_v2",
                "inject_syllabus_features": [r"__regex__资产管理计划(不能满足成立条件|(募集|备案)失败)的处理方式"],
                "only_inject_features": True,
            },
        ],
    },
    {
        "path": ["参与和退出场所"],
        "models": [
            {
                "name": "syllabus_elt_v2",
            },
        ],
    },
    {
        "path": ["注册登记机构"],
        "models": [
            {
                "name": "partial_text",
            },
        ],
    },
    {
        "path": ["参与和退出的方式、价格、程序及确认等"],
        "models": [
            {
                "name": "syllabus_elt_v2",
            },
        ],
    },
    {
        "path": ["参与和退出的金额限制"],
        "models": [
            {
                "name": "syllabus_elt_v2",
            },
        ],
    },
    {
        "path": ["参与和退出的费用"],
        "models": [
            {
                "name": "syllabus_elt_v2",
            },
        ],
    },
    {
        "path": ["参与费率"],
        "models": [
            {
                "name": "syllabus_elt_v2",
            },
        ],
    },
    {
        "path": ["退出费率"],
        "models": [
            {
                "name": "syllabus_elt_v2",
            },
        ],
    },
    {
        "path": ["参与份额和退出金额的计算方式"],
        "models": [
            {
                "name": "syllabus_elt_v2",
            },
        ],
    },
    {
        "path": ["参与资金的利息处理方式"],
        "models": [
            {
                "name": "syllabus_elt_v2",
            },
        ],
    },
    {
        "path": ["在如下情况下，资产管理人可以拒绝接受投资者的参与申请"],
        "models": [
            {
                "name": "syllabus_based",
                "extract_from": "same_type_elements",
                "inject_syllabus_features": [
                    r"__regex__(基金|资产管理计划)的参与、退出(、非交易过户、冻结)?[与和](份额)?转让",
                ],
                "only_inject_features": True,
                "paragraph_model": "middle_paras",
                "para_config": {
                    "use_direct_elements": True,
                    "top_anchor_regs": [r"资产管理人可以拒绝接受投资者的参与申请"],
                    "bottom_anchor_regs": [r"暂停接受"],
                    "include_top_anchor": False,
                },
            },
        ],
    },
    {
        "path": ["在如下情况下，资产管理人可以暂停接受投资者的参与申请"],
        "models": [
            {
                "name": "syllabus_based",
                "extract_from": "same_type_elements",
                "inject_syllabus_features": [
                    r"__regex__(基金|资产管理计划)的参与、退出(、非交易过户、冻结)?[与和](份额)?转让",
                ],
                "only_inject_features": True,
                "paragraph_model": "middle_paras",
                "para_config": {
                    "use_direct_elements": True,
                    "top_anchor_regs": [r"资产管理人可以暂停接受投资者的参与申请"],
                    "bottom_anchor_regs": [r"退出申请"],
                    "include_top_anchor": False,
                },
            },
        ],
    },
    {
        "path": ["在如下情况下，资产管理人可以暂停接受资产委托人的退出申请"],
        "models": [
            {
                "name": "syllabus_based",
                "extract_from": "same_type_elements",
                "inject_syllabus_features": [
                    r"__regex__(基金|资产管理计划)的参与、退出(、非交易过户、冻结)?[与和](份额)?转让",
                ],
                "only_inject_features": True,
                "paragraph_model": "middle_paras",
                "para_config": {
                    "use_direct_elements": True,
                    "top_anchor_regs": [
                        r"资产管理人可以暂停接受资产委托人的退出申请",
                        r"管理人可以拒绝或暂停受理委托人的退出申请",
                    ],
                    "bottom_anchor_regs": [
                        r"暂停(基金|资产管理计划)的参与、退出时",
                        r"[和及]处理方式",
                    ],
                    "include_top_anchor": False,
                },
            },
        ],
    },
    {
        "path": ["延期支付及延期退出的情形和处理方式"],
        "models": [
            {
                "name": "syllabus_elt_v2",
            },
        ],
    },
    {
        "path": ["大额退出的通知"],
        "models": [
            {
                "name": "syllabus_elt_v2",
            },
        ],
    },
    {
        "path": ["巨额退出的认定"],
        "models": [
            {
                "name": "syllabus_elt_v2",
            },
        ],
    },
    {
        "path": ["巨额退出的处理方式"],
        "models": [
            {
                "name": "syllabus_elt_v2",
            },
        ],
    },
    {
        "path": ["巨额退出的通知"],
        "models": [
            {
                "name": "para_match",
                "paragraph_pattern": r"(?P<content>巨额退出.*(通知|公告))",
            },
        ],
    },
    {
        "path": ["份额转让"],
        "models": [
            {
                "name": "syllabus_elt_v2",
            },
        ],
    },
    {
        "path": ["非交易过户认定及处理方式"],
        "models": [
            {
                "name": "syllabus_elt_v2",
            },
        ],
    },
    {
        "path": ["冻结"],
        "models": [
            {
                "name": "syllabus_elt_v2",
            },
        ],
    },
    {
        "path": ["资产管理人自有资金参与"],
        "models": [
            {
                "name": "syllabus_elt_v2",
            },
        ],
    },
    {
        "path": ["投资顾问更换"],
        "models": [
            {
                "name": "para_match",
                "paragraph_pattern": r"投资顾问更换",
            },
        ],
    },
    {
        "path": ["委托人的权利"],
        "models": [
            {
                "name": "syllabus_elt_v2",
                "inject_syllabus_features": [r"__regex__(委托人|投资者)的权利"],
                "only_inject_features": True,
            },
        ],
    },
    {
        "path": ["委托人的义务"],
        "models": [
            {
                "name": "syllabus_elt_v2",
                "inject_syllabus_features": [r"__regex__(委托人|投资者)的义务"],
                "only_inject_features": True,
            },
        ],
    },
    {
        "path": ["管理人的权利"],
        "models": [
            {
                "name": "syllabus_elt_v2",
                "inject_syllabus_features": [r"__regex__管理人的权利"],
                "only_inject_features": True,
            },
        ],
    },
    {
        "path": ["管理人的义务"],
        "models": [
            {
                "name": "syllabus_elt_v2",
                "inject_syllabus_features": [r"__regex__管理人的义务"],
                "only_inject_features": True,
            },
        ],
    },
    {
        "path": ["托管人的权利"],
        "models": [
            {
                "name": "syllabus_elt_v2",
                "inject_syllabus_features": [r"__regex__托管人的权利"],
                "only_inject_features": True,
            },
        ],
    },
    {
        "path": ["托管人的义务"],
        "models": [
            {
                "name": "syllabus_elt_v2",
                "inject_syllabus_features": [r"__regex__托管人的义务"],
                "only_inject_features": True,
            },
        ],
    },
    {
        "path": ["计划份额持有人大会召开事由"],
        "models": [
            {
                "name": "syllabus_elt_v2",
            },
        ],
    },
    {
        "path": ["计划份额持有人大会会议召集人及召集方式"],
        "models": [
            {
                "name": "syllabus_elt_v2",
            },
        ],
    },
    {
        "path": ["召开计划份额持有人大会的通知时间、通知内容、通知方式"],
        "models": [
            {
                "name": "syllabus_elt_v2",
            },
        ],
    },
    {
        "path": ["计划份额持有人大会计划份额持有人出席会议的方式"],
        "models": [
            {
                "name": "syllabus_elt_v2",
            },
        ],
    },
    {
        "path": ["计划份额持有人大会议事内容与程序"],
        "models": [
            {
                "name": "middle_paras",
                "use_syllabus_model": True,
                "inject_syllabus_features": [r"份额持有人大会及日常机构"],
                "only_inject_features": True,
                "top_anchor_regs": [r"议事内容和程序"],
                "bottom_anchor_regs": [r"决议形成"],
                "include_top_anchor": False,
            },
        ],
    },
    {
        "path": ["决议形成"],
        "models": [
            {
                "name": "syllabus_elt_v2",
            },
        ],
    },
    {
        "path": ["计划份额持有人大会计票"],
        "models": [
            {
                "name": "syllabus_elt_v2",
                "inject_syllabus_features": [r"计票"],
                "only_inject_features": True,
            },
            {
                "name": "para_match",
                "paragraph_pattern": r"本计划不设置份额持有人大会机制",
            },
        ],
    },
    {
        "path": ["计划份额持有人大会生效与公告"],
        "models": [
            {
                "name": "middle_paras",
                "use_syllabus_model": True,
                "inject_syllabus_features": [r"份额持有人大会及日常机构"],
                "only_inject_features": True,
                "top_anchor_regs": [r"生效与公告"],
                "include_top_anchor": False,
                "bottom_anchor_regs": [P_TITLE_HEAD],
            },
            {
                "name": "para_match",
                "paragraph_pattern": r"本计划不设置份额持有人大会机制",
            },
        ],
    },
    {
        "path": ["注册登记机构履行如下职责"],
        "models": [
            {
                "name": "middle_paras",
                "use_syllabus_model": True,
                "inject_syllabus_features": [r"__regex__(基金|资产管理计划)份额的登记"],
                "only_inject_features": True,
                "top_anchor_regs": [r"注册登记机构(履行如下|的)职责"],
                "bottom_anchor_regs": [r"^[(（]?四", r"履行上述职责后", r"(基金|资产管理计划)的投资"],
                "include_top_anchor": False,
            },
        ],
    },
    {
        "path": ["封闭期"],
        "models": [
            {
                "name": "syllabus_elt_v2",
            },
        ],
    },
    {
        "path": ["开放日"],
        "models": [
            {
                "name": "syllabus_elt_v2",
            },
        ],
    },
    {
        "path": ["资产管理计划的分级安排"],
        "models": [
            {
                "name": "syllabus_elt_v2",
                "inject_syllabus_features": [r"__regex__(基金|资产管理计划)的分级安排[:：]?"],
                "only_inject_features": True,
            },
            {
                "name": "para_match",
                "paragraph_pattern": (
                    r"(基金|资产管理计划)的分级安排.(?P<content>本计划不分级)",
                    r"(?P<content>本资产管理计划无分级安排)",
                ),
                "content_pattern": r"(基金|资产管理计划)的分级安排.(?P<content>本计划不分级)",
            },
        ],
    },
    {
        "path": ["计划投资范围"],
        "models": [
            {
                "name": "middle_paras",
                "use_syllabus_model": True,
                "syllabus_elt_v2": {
                    "syllabus_level": 3,
                    # "multi": True,
                    # "reverse": True,
                    "inject_syllabus_features": [
                        r"__regex__^(基金|资产管理计划)的基本情况$",
                        r"__regex__^(基金|资产管理计划)的投资$",
                    ],
                    "only_inject_features": True,
                },
                "top_anchor_regs": [
                    r"投资.*(方向|范围)）?[:：]$",
                    r"([（）一二三四五六七八九]+|[\d、]+).*投资.*(方向|范围)$",
                    r"投资范围及比例[:：]?$",
                ],
                "bottom_anchor_regs": [
                    r"(^[（）一二三四五六七八九]+|^[\d、]+).*投资范围的.+$",
                    r"投资[比例及限制策略、]+[:：]$",
                    r"([（）一二三四五六七八九]+|[\d、]+).*投资[比例及限制策略、]+$",
                    r"产品风险等级[:：]$",
                ],
                "include_top_anchor": False,
            },
        ],
    },
    {
        "path": ["投资策略"],
        "models": [
            {
                "name": "syllabus_elt_v2",
                "inject_syllabus_features": [r"__regex__投资策略"],
                "only_inject_features": True,
            },
        ],
    },
    {
        "path": ["业绩比较基准"],
        "models": [
            {
                "name": "syllabus_elt_v2",
            },
        ],
    },
    {
        "path": ["所投资资产管理产品的选择标准"],
        "models": [
            {
                "name": "syllabus_elt_v2",
                "inject_syllabus_features": [r"__regex__所投资资产管理产品的选择标准"],
                "only_inject_features": True,
                "include_title": True,
            },
        ],
    },
    {
        "path": ["投资比例及限制", "资产管理计划的基本情况"],
        "models": [
            {
                "name": "middle_paras",
                "use_syllabus_model": True,
                "inject_syllabus_features": [r"__regex__(基金|资产管理计划)的基本情况"],
                "only_inject_features": True,
                "top_anchor_regs": [
                    r".*投资比例[、及](投资)?限制[:：]$",
                    r"([（）一二三四五六七八九]+|[\d、]+).*投资比例[、及](投资)?限制[:：]?$",
                ],
                "bottom_anchor_regs": [
                    r".*(风险等级|存续期限|风险收益特征)[:：]$",
                    r"([（）一二三四五六七八九]+|[\d、]+).*(风险等级|存续期限|风险收益特征)[:：]?$",
                    "投资比例超限",
                ],
                "include_top_anchor": False,
            },
            {
                "name": "partial_text",
                "regs": [r"本计划的主要投资方向与投资比例：详见本合同.*第.*"],
            },
        ],
    },
    {
        "path": ["投资比例及限制", "资产管理计划的投资"],
        "models": [
            {
                "name": "syllabus_elt_v2",
                "inject_syllabus_features": [r"资产管理计划的投资|投资比例及限制"],
                "only_inject_features": True,
            },
        ],
    },
    {
        "path": ["投资限制", "资产管理计划的基本情况"],
        "models": [
            {
                "name": "middle_paras",
                "use_syllabus_model": True,
                "inject_syllabus_features": [r"__regex__(基金|资产管理计划)的基本情况"],
                "only_inject_features": True,
                "top_anchor_regs": [
                    r"(?<!投资比例[、及])投资限制[:：]$",
                    r"([（）一二三四五六七八九]+|[\d、]+).*(?<!投资比例[、及])投资限制[:：]$",
                ],
                "bottom_anchor_regs": [
                    r".*(风险等级|存续期限|风险收益特征)[:：]$",
                    r"([（）一二三四五六七八九]+|[\d、]+).*(风险等级|存续期限|风险收益特征)[:：]?$",
                    "投资比例超限",
                ],
                "include_top_anchor": False,
            },
        ],
    },
    {
        "path": ["投资限制", "资产管理计划的投资"],
        "models": [
            {
                "name": "syllabus_elt_v2",
                "inject_syllabus_features": [
                    r"__regex__^(基金|资产管理计划)的投资$__regex__^(本计划的)?投资限制$",
                ],
                "only_inject_features": True,
            },
        ],
    },
    {
        "path": ["投资比例", "资产管理计划的基本情况"],
        "models": [
            {
                "name": "middle_paras",
                "use_syllabus_model": True,
                "inject_syllabus_features": [r"__regex__(基金|资产管理计划)的基本情况"],
                "only_inject_features": True,
                "top_anchor_regs": [
                    r".*投资比例[:：]$",
                    r"([（）一二三四五六七八九]+|[\d、]+).*投资比例[:：]?$",
                ],
                "bottom_anchor_regs": [
                    r".*(风险等级|存续期限|风险收益特征)[:：]$",
                    r"([（）一二三四五六七八九]+|[\d、]+).*(风险等级|存续期限|风险收益特征)[:：]?$",
                    "投资比例超限",
                ],
                "include_top_anchor": False,
            },
            {
                "name": "middle_paras",
                "use_syllabus_model": True,
                "inject_syllabus_features": [r"__regex__(基金|资产管理计划)的基本情况"],
                "only_inject_features": True,
                "top_anchor_regs": [
                    r"投资比例[:：]本资产管理计划",
                ],
                "top_anchor_content_regs": [r"投资比例[:：](?P<content>.*)"],
                "bottom_anchor_regs": [r"产品风险收益特征"],
            },
        ],
    },
    {
        "path": ["投资比例", "资产管理计划的投资"],
        "models": [
            {
                "name": "syllabus_elt_v2",
                "inject_syllabus_features": [
                    r"资产管理计划的投资|投资比例",
                    r"资产管理计划的投资|投资范围及比例|投资比例",
                ],
                "only_inject_features": True,
            },
            {
                "name": "middle_paras",
                "use_syllabus_model": True,
                "inject_syllabus_features": [r"__regex__^(基金|资产管理计划)的投资$__regex__投资范围及比例"],
                "only_inject_features": True,
                "top_anchor_regs": [
                    r".*投资比例为?[:：]$",
                    r"([（）一二三四五六七八九]+|[\d、]+).*投资比例为?[:：]?$",
                ],
                "bottom_anchor_regs": [
                    r".*(风险等级|存续期限|风险收益特征)[:：]$",
                    r"([（）一二三四五六七八九]+|[\d、]+).*(风险等级|存续期限|风险收益特征)[:：]?$",
                    r"投资比例超限",
                    r"特别提示",
                ],
                "include_top_anchor": False,
            },
            {
                "name": "middle_paras",
                "use_syllabus_model": True,
                "inject_syllabus_features": [r"__regex__(基金|资产管理计划)的投资"],
                "only_inject_features": True,
                "top_anchor_regs": [
                    r"([（）一二三四五六七八九]+|[\d、]+).*投资范围及投资比例[:：]?$",
                ],
                "bottom_anchor_regs": [
                    r"([（）一二三四五六七八九]+|[\d、]+).*(投资策略)[:：]?$",
                ],
                "include_top_anchor": False,
            },
            {
                "name": "para_match",
                "paragraph_pattern": [
                    r"本计划投资于.*?类资产不低于本计划总资产的\d+%，为固定收益类资产管理产品。",
                    r"本计划为权益类资产管理计划，投资组合比例为：投资于权益类资产的比例不低于资产管理计划总资产的\d+%。",
                    r"如果法律法规或中国证监会变更投资品种的投资比例限制，管理人在履行适当程序后，可以调整上述投资品种的投资比例。",
                ],
            },
        ],
    },
    {
        "path": ["投资的资产组合的流动性与追加、提取安排"],
        "models": [
            {
                "name": "syllabus_elt_v2",
                "neglect_patterns": [r"投资禁止"],
            },
            {
                "name": "para_match",
                "paragraph_pattern": r"追加、提取安排相匹配",
            },
        ],
    },
    {
        "path": ["投资禁止"],
        "models": [
            {
                "name": "syllabus_elt_v2",
            },
        ],
    },
    {
        "path": ["投资政策的变更"],
        "models": [
            {
                "name": "syllabus_elt_v2",
            },
        ],
    },
    {
        "path": ["建仓期"],
        "models": [
            {
                "name": "syllabus_elt_v2",
            },
        ],
    },
    {
        "path": ["预警线"],
        "models": [
            {
                "name": "partial_text",
                "regs": [r"(?P<dst>本计划不设预警、止损线)"],
                "model_alternative": True,
                "use_answer_pattern": False,
            },
        ],
    },
    {
        "path": ["止损线"],
        "models": [
            {
                "name": "partial_text",
                "regs": [
                    r"(?P<dst>本计划成立日计划资产净值的80%)",
                    r"(?P<dst>本计划不设预警、止损线)",
                    r"本计划止损线为【(?P<dst>[\d.]+)】元",
                ],
                "model_alternative": True,
                "use_answer_pattern": False,
            },
        ],
    },
    {
        "path": ["预警止损机制"],
        "models": [
            {
                "name": "syllabus_elt_v2",
            },
        ],
    },
    {
        "path": ["投资的资产组合的流动性与参与、退出安排"],
        "models": [
            {
                "name": "syllabus_elt_v2",
            },
        ],
    },
    {
        "path": ["投资非证券交易所或期货交易所发行、上市交易的投资标的"],
        "models": [
            {
                "name": "syllabus_based",
                "inject_syllabus_features": [r"__regex__目录__regex__(基金|资产管理计划)的投资__regex__其他"],
                "only_inject_features": True,
                "paragraph_model": "para_match",
                "para_config": {
                    "paragraph_pattern": (r"非证券交易所或期货交易所发行、上市(交易)?的投资标的", r"^无.?$")
                },
            },
            {
                "name": "syllabus_based",
                "inject_syllabus_features": [r"__regex__(基金|资产管理计划)的投资"],
                "only_inject_features": True,
                "paragraph_model": "para_match",
                "para_config": {
                    "paragraph_pattern": (r"非证券交易所或期货交易所发行、上市(交易)?的投资标的", r"^无.?$")
                },
            },
        ],
    },
    {
        "path": ["投资顾问"],
        "models": [
            {
                "name": "syllabus_elt_v2",
            },
        ],
    },
    {
        "path": ["关联交易及利益冲突情形"],
        "models": [
            {
                "name": "syllabus_elt_v2",
            },
        ],
    },
    {
        "path": ["关联交易及利益冲突的应对及处理"],
        "models": [
            {
                "name": "syllabus_elt_v2",
            },
        ],
    },
    {
        "path": ["投资经理的指定与变更"],
        "models": [
            {
                "name": "syllabus_elt_v2",
            },
        ],
    },
    {
        "path": ["资产管理计划财产的保管与处分"],
        "models": [
            {
                "name": "syllabus_elt_v2",
            },
        ],
    },
    {
        "path": ["资产管理计划财产相关账户的开立和管理"],
        "models": [
            {
                "name": "syllabus_elt_v2",
            },
        ],
    },
    {
        "path": ["委托财产的移交"],
        "models": [
            {
                "name": "syllabus_elt_v2",
            },
        ],
    },
    {
        "path": ["委托财产的追加"],
        "models": [
            {
                "name": "syllabus_elt_v2",
            },
        ],
    },
    {
        "path": ["委托财产的提取"],
        "models": [
            {
                "name": "syllabus_elt_v2",
            },
        ],
    },
    {
        "path": ["交易清算授权"],
        "models": [
            {
                "name": "syllabus_elt_v2",
            },
        ],
    },
    {
        "path": ["投资指令的内容"],
        "models": [
            {
                "name": "syllabus_elt_v2",
            },
        ],
    },
    {
        "path": ["投资指令的发送、确认和执行的时间和程序"],
        "models": [
            {
                "name": "syllabus_elt_v2",
            },
        ],
    },
    {
        "path": ["资产托管人依法暂缓、拒绝执行指令的情形和处理程序"],
        "models": [
            {
                "name": "syllabus_elt_v2",
            },
        ],
    },
    {
        "path": ["资产管理人发送错误指令的情形和处理程序"],
        "models": [
            {
                "name": "syllabus_elt_v2",
            },
        ],
    },
    {
        "path": ["更换投资指令被授权人的程序"],
        "models": [
            {
                "name": "syllabus_elt_v2",
            },
        ],
    },
    {
        "path": ["投资指令的保管"],
        "models": [
            {
                "name": "syllabus_elt_v2",
            },
        ],
    },
    {
        "path": ["投资指令-其他相关责任"],
        "models": [
            {
                "name": "syllabus_elt_v2",
            },
        ],
    },
    {
        "path": ["越权交易的界定"],
        "models": [
            {
                "name": "syllabus_elt_v2",
                "inject_syllabus_features": [r"越权交易的界定|越权交易的界定"],
            },
        ],
    },
    {
        "path": ["越权交易的处理程序"],
        "models": [
            {
                "name": "syllabus_elt_v2",
                "inject_syllabus_features": [r"__regex__越权交易的处理程序"],
                "only_inject_features": True,
            },
        ],
    },
    {
        "path": ["不属于越权交易的情形"],
        "models": [
            {
                "name": "syllabus_elt_v2",
                "neglect_patterns": [r"资产托管人对资产管理人投资运作的监督"],
            },
            {
                "name": "syllabus_based",
                "extract_from": "same_type_elements",
                "inject_syllabus_features": [r"资产托管人对资产管理人投资运作的监督"],
                "only_inject_features": True,
                "paragraph_model": "middle_paras",
                "para_config": {
                    "use_direct_elements": True,
                    "top_anchor_regs": [r"越权交易的例外"],
                    "bottom_anchor_regs": [r"资产托管人对资产管理计划"],
                    "include_top_anchor": False,
                },
            },
        ],
    },
    {
        "path": ["选择代理证券买卖的证券经营机构的程序"],
        "models": [
            {
                "name": "syllabus_elt_v2",
            },
        ],
    },
    {
        "path": ["资金清算交收安排"],
        "models": [
            {
                "name": "syllabus_elt_v2",
                "inject_syllabus_features": [r"资金清算交收安排"],
                "feature_black_list": [r"__regex__投资证券后"],
            },
        ],
    },
    {
        "path": ["资金、证券账目及交易记录的核对"],
        "models": [
            {
                "name": "syllabus_elt_v2",
            },
        ],
    },
    {
        "path": ["参与、退出的资金清算"],
        "models": [
            {
                "name": "syllabus_elt_v2",
            },
        ],
    },
    {
        "path": ["追加、提取的资金清算"],
        "models": [
            {
                "name": "syllabus_elt_v2",
            },
        ],
    },
    {
        "path": ["无法按时清算的责任认定及处理程序"],
        "models": [
            {
                "name": "syllabus_elt_v2",
            },
        ],
    },
    {
        "path": ["估值目的"],
        "models": [
            {
                "name": "syllabus_elt_v2",
            },
        ],
    },
    {
        "path": ["估值时间及估值程序"],
        "models": [
            {
                "name": "syllabus_elt_v2",
            },
        ],
    },
    {
        "path": ["估值依据"],
        "models": [
            {
                "name": "syllabus_elt_v2",
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
        "path": ["估值方法"],
        "models": [
            {
                "name": "syllabus_elt_v2",
            },
        ],
    },
    {
        "path": ["估值错误的处理"],
        "models": [
            {
                "name": "syllabus_elt_v2",
            },
        ],
    },
    {
        "path": ["估值调整的情形与处理"],
        "models": [
            {
                "name": "syllabus_elt_v2",
            },
        ],
    },
    {
        "path": ["资产管理计划份额净值的确认"],
        "models": [
            {
                "name": "syllabus_elt_v2",
            },
        ],
    },
    {
        "path": ["资产管理计划净值的确认"],
        "models": [
            {
                "name": "syllabus_elt_v2",
                "inject_syllabus_features": [r"__regex__(基金|资产管理计划)净值的确认"],
                "only_inject_features": True,
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
        "path": ["特殊情况的处理"],
        "models": [
            {
                "name": "syllabus_elt_v2",
            },
        ],
    },
    {
        "path": ["资产管理计划的会计政策"],
        "models": [
            {
                "name": "syllabus_elt_v2",
            },
        ],
    },
    {
        "path": ["资产管理业务费用的种类"],
        "models": [
            {
                "name": "syllabus_elt_v2",
            },
        ],
    },
    {
        "path": ["计划管理费率"],
        "models": [
            {
                "name": "partial_text",
                "regs": [r"管理费(年费)?率为?(?P<dst>[\d.,【】%]*)"],
                "model_alternative": True,
            },
        ],
    },
    {
        "path": ["计划管理费-计提方法、计提标准和支付方式"],
        "models": [
            {
                "name": "middle_paras",
                "use_syllabus_model": True,
                "inject_syllabus_features": P_ACCRUAL_METHOD,
                "only_inject_features": True,
                "top_anchor_regs": [rf"{P_TITLE_HEAD}.*管理费"],
                "include_top_anchor": False,
                "bottom_anchor_regs": [
                    r"账户[信息名称]+|收[取入款](.{2,5}费[和业绩报酬的]*)?(银行)?账[户号]|户名",
                    rf"{P_TITLE_HEAD}.*托管费",
                ],
            },
        ],
    },
    {
        "path": ["管理费收费账户信息", "账户名称"],
        "models": [
            {
                "name": "elements_collector_based",
                "elements_collect_model": "middle_paras",
                "elements_collect_config": {
                    "use_syllabus_model": True,
                    "inject_syllabus_features": P_ACCRUAL_METHOD,
                    "only_inject_features": True,
                    "table_regarded_as_paras": True,
                    "top_anchor_regs": [rf"{P_TITLE_HEAD}.*管理费"],
                    "bottom_anchor_regs": [r"账号|开户|大额", rf"{P_TITLE_HEAD}.*((托管|服务|顾问)费|业绩报酬)"],
                    "bottom_greed": True,
                    "bottom_continue_greed": True,
                    "include_bottom_anchor": True,
                },
                "paragraph_model": "partial_text",
                "para_config": {
                    "use_answer_pattern": False,
                    "regs": [r"(账户名称|户名).*[:：](?P<dst>.*)"],
                },
            },
        ],
    },
    {
        "path": ["管理费收费账户信息", "开户银行"],
        "models": [
            {
                "name": "elements_collector_based",
                "elements_collect_model": "middle_paras",
                "elements_collect_config": {
                    "use_syllabus_model": True,
                    "inject_syllabus_features": P_ACCRUAL_METHOD,
                    "only_inject_features": True,
                    "table_regarded_as_paras": True,
                    "top_anchor_regs": [rf"{P_TITLE_HEAD}.*管理费"],
                    "bottom_anchor_regs": [r"账号|开户|大额", rf"{P_TITLE_HEAD}.*((托管|服务|顾问)费|业绩报酬)"],
                    "bottom_greed": True,
                    "bottom_continue_greed": True,
                    "include_bottom_anchor": True,
                },
                "paragraph_model": "partial_text",
                "para_config": {
                    "use_answer_pattern": False,
                    "regs": [r"开户银?行[:：](?P<dst>.*)"],
                },
            },
        ],
    },
    {
        "path": ["管理费收费账户信息", "银行账号"],
        "models": [
            {
                "name": "elements_collector_based",
                "elements_collect_model": "middle_paras",
                "elements_collect_config": {
                    "use_syllabus_model": True,
                    "inject_syllabus_features": P_ACCRUAL_METHOD,
                    "only_inject_features": True,
                    "table_regarded_as_paras": True,
                    "top_anchor_regs": [rf"{P_TITLE_HEAD}.*管理费"],
                    "bottom_anchor_regs": [r"账号|开户|大额", rf"{P_TITLE_HEAD}.*((托管|服务|顾问)费|业绩报酬)"],
                    "bottom_greed": True,
                    "bottom_continue_greed": True,
                    "include_bottom_anchor": True,
                },
                "paragraph_model": "partial_text",
                "para_config": {
                    "use_answer_pattern": False,
                    "regs": [r"(银行)?账号[:：](?P<dst>.*)"],
                },
            },
        ],
    },
    {
        "path": ["管理费收费账户信息", "大额支付行号"],
        "models": [
            {
                "name": "elements_collector_based",
                "elements_collect_model": "middle_paras",
                "elements_collect_config": {
                    "use_syllabus_model": True,
                    "inject_syllabus_features": P_ACCRUAL_METHOD,
                    "only_inject_features": True,
                    "table_regarded_as_paras": True,
                    "top_anchor_regs": [rf"{P_TITLE_HEAD}.*管理费"],
                    "bottom_anchor_regs": [r"账号|开户|大额", rf"{P_TITLE_HEAD}.*((托管|服务|顾问)费|业绩报酬)"],
                    "bottom_greed": True,
                    "bottom_continue_greed": True,
                    "include_bottom_anchor": True,
                },
                "paragraph_model": "partial_text",
                "para_config": {
                    "regs": [r"大额(支付|联)行?号[:：](?P<dst>.*)"],
                    "use_answer_pattern": False,
                },
            },
        ],
    },
    {
        "path": ["计划托管费率"],
        "models": [
            {
                "name": "partial_text",
                "regs": [r"托管费率为(?P<dst>[\d.,【】%]*)"],
                "model_alternative": True,
            },
        ],
    },
    {
        "path": ["计划托管费-计提方法、计提标准和支付方式"],
        "models": [
            {
                "name": "middle_paras",
                "use_syllabus_model": True,
                "inject_syllabus_features": P_ACCRUAL_METHOD,
                "only_inject_features": True,
                "top_anchor_regs": [rf"{P_TITLE_HEAD}.*托管费"],
                "include_top_anchor": False,
                "bottom_anchor_regs": [
                    r"账户[信息名称]+|收[取入款](.{2,5}费[和业绩报酬的]*)?(银行)?账[户号]|户名",
                    rf"{P_TITLE_HEAD}.*服务费",
                    r"中所列其他费用根据有关法规及相应协议",
                ],
            },
        ],
    },
    {
        "path": ["资产托管人指定收取托管费的银行账户"],
        "models": [
            {
                "name": "elements_collector_based",
                "elements_collect_model": "middle_paras",
                "elements_collect_config": {
                    "use_syllabus_model": True,
                    "inject_syllabus_features": P_ACCRUAL_METHOD,
                    "only_inject_features": True,
                    "table_regarded_as_paras": True,
                    "top_anchor_regs": [rf"{P_TITLE_HEAD}.*托管费"],
                    "bottom_anchor_regs": [r"账号|开户|大额", rf"{P_TITLE_HEAD}.*((管理|服务|顾问)费|业绩报酬)"],
                    "bottom_default": True,
                    "bottom_greed": True,
                    "bottom_continue_greed": True,
                    "include_bottom_anchor": True,
                },
                "paragraph_model": "partial_text",
                "para_config": {
                    "multi_elements": True,
                    "use_answer_pattern": False,
                },
            },
        ],
    },
    {
        "path": ["服务机构的服务费"],
        "models": [
            {
                "name": "partial_text",
                "regs": [r"服务费(年费)?率为?(?P<dst>[\d.,【】%]*)"],
                "model_alternative": True,
            },
        ],
    },
    {
        "path": ["服务机构的服务费计提方法、计提标准和支付方式"],
        "models": [
            {
                "name": "middle_paras",
                "use_syllabus_model": True,
                "inject_syllabus_features": P_ACCRUAL_METHOD,
                "only_inject_features": True,
                "top_anchor_regs": [rf"{P_TITLE_HEAD}.*服务费"],
                "include_top_anchor": False,
                "bottom_anchor_regs": [
                    r"账户[信息名称]+|收[取入款](.{2,5}费[和业绩报酬的]*)?(银行)?账[户号]|户名",
                    rf"{P_TITLE_HEAD}.*顾问费",
                ],
            },
        ],
    },
    {
        "path": ["服务机构指定收取服务费的银行账户", "户名"],
        "models": [
            {
                "name": "elements_collector_based",
                "elements_collect_model": "middle_paras",
                "elements_collect_config": {
                    "use_syllabus_model": True,
                    "inject_syllabus_features": P_ACCRUAL_METHOD,
                    "only_inject_features": True,
                    "table_regarded_as_paras": True,
                    "top_anchor_regs": [rf"{P_TITLE_HEAD}.*服务费"],
                    "bottom_anchor_regs": [r"账号|开户|大额", rf"{P_TITLE_HEAD}.*((管理|托管|顾问)费|业绩报酬)"],
                    "bottom_default": True,
                    "bottom_greed": True,
                    "bottom_continue_greed": True,
                    "include_bottom_anchor": True,
                },
                "paragraph_model": "partial_text",
                "para_config": {
                    "use_answer_pattern": False,
                },
            },
        ],
    },
    {
        "path": ["服务机构指定收取服务费的银行账户", "开户行"],
        "models": [
            {
                "name": "elements_collector_based",
                "elements_collect_model": "middle_paras",
                "elements_collect_config": {
                    "use_syllabus_model": True,
                    "inject_syllabus_features": P_ACCRUAL_METHOD,
                    "only_inject_features": True,
                    "table_regarded_as_paras": True,
                    "top_anchor_regs": [rf"{P_TITLE_HEAD}.*服务费"],
                    "bottom_anchor_regs": [r"账号|开户|大额", rf"{P_TITLE_HEAD}.*((管理|托管|顾问)费|业绩报酬)"],
                    "bottom_default": True,
                    "bottom_greed": True,
                    "bottom_continue_greed": True,
                    "include_bottom_anchor": True,
                },
                "paragraph_model": "partial_text",
                "para_config": {
                    "use_answer_pattern": False,
                    "regs": [r"开户行[:：](?P<dst>.*)"],
                    "model_alternative": True,
                },
            },
        ],
    },
    {
        "path": ["服务机构指定收取服务费的银行账户", "账号"],
        "models": [
            {
                "name": "elements_collector_based",
                "elements_collect_model": "middle_paras",
                "elements_collect_config": {
                    "use_syllabus_model": True,
                    "inject_syllabus_features": P_ACCRUAL_METHOD,
                    "only_inject_features": True,
                    "table_regarded_as_paras": True,
                    "top_anchor_regs": [rf"{P_TITLE_HEAD}.*服务费"],
                    "bottom_anchor_regs": [r"账号|开户|大额", rf"{P_TITLE_HEAD}.*((管理|托管|顾问)费|业绩报酬)"],
                    "bottom_default": True,
                    "bottom_greed": True,
                    "bottom_continue_greed": True,
                    "include_bottom_anchor": True,
                },
                "paragraph_model": "partial_text",
                "para_config": {
                    "use_answer_pattern": False,
                },
            },
        ],
    },
    {
        "path": ["服务机构指定收取服务费的银行账户", "大额支付号"],
        "models": [
            {
                "name": "elements_collector_based",
                "elements_collect_model": "middle_paras",
                "elements_collect_config": {
                    "use_syllabus_model": True,
                    "inject_syllabus_features": P_ACCRUAL_METHOD,
                    "only_inject_features": True,
                    "table_regarded_as_paras": True,
                    "top_anchor_regs": [rf"{P_TITLE_HEAD}.*服务费"],
                    "bottom_anchor_regs": [r"账号|开户|大额", rf"{P_TITLE_HEAD}.*((管理|托管|顾问)费|业绩报酬)"],
                    "bottom_default": True,
                    "bottom_greed": True,
                    "bottom_continue_greed": True,
                    "include_bottom_anchor": True,
                },
                "paragraph_model": "partial_text",
                "para_config": {
                    "use_answer_pattern": False,
                },
            },
        ],
    },
    {
        "path": ["投资顾问费年费率"],
        "models": [
            {
                "name": "partial_text",
            },
        ],
    },
    {
        "path": ["投资顾问费计提方法、计提标准和支付方式"],
        "models": [
            {
                "name": "middle_paras",
                "use_syllabus_model": True,
                "inject_syllabus_features": P_ACCRUAL_METHOD,
                "only_inject_features": True,
                "top_anchor_regs": [rf"{P_TITLE_HEAD}.*顾问费"],
                "include_top_anchor": False,
                "bottom_anchor_regs": [
                    r"账户[信息名称]+|收[取入款](.{2,5}费[和业绩报酬的]*)?(银行)?账[户号]|户名",
                    rf"{P_TITLE_HEAD}.*服务费",
                ],
            },
        ],
    },
    {
        "path": ["投资顾问指定收取投资顾问费的银行账户", "户名"],
        "models": [
            {
                "name": "elements_collector_based",
                "elements_collect_model": "middle_paras",
                "elements_collect_config": {
                    "use_syllabus_model": True,
                    "inject_syllabus_features": P_ACCRUAL_METHOD,
                    "only_inject_features": True,
                    "table_regarded_as_paras": True,
                    "top_anchor_regs": [rf"{P_TITLE_HEAD}.*顾问费"],
                    "bottom_anchor_regs": [r"账号|开户|大额", rf"{P_TITLE_HEAD}.*((管理|托管|服务)费|业绩报酬)"],
                    "bottom_default": True,
                    "bottom_greed": True,
                    "bottom_continue_greed": True,
                    "include_bottom_anchor": True,
                },
                "paragraph_model": "partial_text",
                "para_config": {
                    "use_answer_pattern": False,
                },
            },
        ],
    },
    {
        "path": ["投资顾问指定收取投资顾问费的银行账户", "开户行"],
        "models": [
            {
                "name": "elements_collector_based",
                "elements_collect_model": "middle_paras",
                "elements_collect_config": {
                    "use_syllabus_model": True,
                    "inject_syllabus_features": P_ACCRUAL_METHOD,
                    "only_inject_features": True,
                    "table_regarded_as_paras": True,
                    "top_anchor_regs": [rf"{P_TITLE_HEAD}.*顾问费"],
                    "bottom_anchor_regs": [r"账号|开户|大额", rf"{P_TITLE_HEAD}.*((管理|托管|服务)费|业绩报酬)"],
                    "bottom_default": True,
                    "bottom_greed": True,
                    "bottom_continue_greed": True,
                    "include_bottom_anchor": True,
                },
                "paragraph_model": "partial_text",
                "para_config": {
                    "use_answer_pattern": False,
                    "need_match_length": False,
                },
            },
        ],
    },
    {
        "path": ["投资顾问指定收取投资顾问费的银行账户", "账号"],
        "models": [
            {
                "name": "elements_collector_based",
                "elements_collect_model": "middle_paras",
                "elements_collect_config": {
                    "use_syllabus_model": True,
                    "inject_syllabus_features": P_ACCRUAL_METHOD,
                    "only_inject_features": True,
                    "table_regarded_as_paras": True,
                    "top_anchor_regs": [rf"{P_TITLE_HEAD}.*顾问费"],
                    "bottom_anchor_regs": [r"账号|开户|大额", rf"{P_TITLE_HEAD}.*((管理|托管|服务)费|业绩报酬)"],
                    "bottom_default": True,
                    "bottom_greed": True,
                    "bottom_continue_greed": True,
                    "include_bottom_anchor": True,
                },
                "paragraph_model": "partial_text",
                "para_config": {
                    "use_answer_pattern": False,
                },
            },
        ],
    },
    {
        "path": ["投资顾问指定收取投资顾问费的银行账户", "大额支付号"],
        "models": [
            {
                "name": "elements_collector_based",
                "elements_collect_model": "middle_paras",
                "elements_collect_config": {
                    "use_syllabus_model": True,
                    "inject_syllabus_features": P_ACCRUAL_METHOD,
                    "only_inject_features": True,
                    "table_regarded_as_paras": True,
                    "top_anchor_regs": [rf"{P_TITLE_HEAD}.*顾问费"],
                    "bottom_anchor_regs": [r"账号|开户|大额", rf"{P_TITLE_HEAD}.*((管理|托管|服务)费|业绩报酬)"],
                    "bottom_default": True,
                    "bottom_greed": True,
                    "bottom_continue_greed": True,
                    "include_bottom_anchor": True,
                },
                "paragraph_model": "partial_text",
                "para_config": {
                    "use_answer_pattern": False,
                },
            },
        ],
    },
    {
        "path": ["客户服务费用"],
        "models": [
            {
                "name": "partial_text",
            },
        ],
    },
    {
        "path": ["客户服务费用-计提方法、计提标准和支付方式"],
        "models": [
            {
                "name": "middle_paras",
                "use_syllabus_model": True,
                "inject_syllabus_features": P_ACCRUAL_METHOD,
                "only_inject_features": True,
                "top_anchor_regs": [rf"{P_TITLE_HEAD}.*系统服务费"],
                "include_top_anchor": False,
                "bottom_anchor_regs": [
                    r"账户[信息名称]+|收[取入款](.{2,5}费[和业绩报酬的]*)?(银行)?账[户号]|户名",
                    rf"{P_TITLE_HEAD}.*业绩报酬",
                ],
            },
        ],
    },
    {
        "path": ["客户服务机构收取客户服务费用的银行账户", "户名"],
        "models": [
            {
                "name": "elements_collector_based",
                "elements_collect_model": "middle_paras",
                "elements_collect_config": {
                    "use_syllabus_model": True,
                    "inject_syllabus_features": P_ACCRUAL_METHOD,
                    "only_inject_features": True,
                    "table_regarded_as_paras": True,
                    "top_anchor_regs": [rf"{P_TITLE_HEAD}.*系统服务费"],
                    "bottom_anchor_regs": [r"账号|开户|大额", rf"{P_TITLE_HEAD}.*((管理|托管|顾问)费|业绩报酬)"],
                    "bottom_default": True,
                    "bottom_greed": True,
                    "bottom_continue_greed": True,
                    "include_bottom_anchor": True,
                },
                "paragraph_model": "partial_text",
                "para_config": {
                    "use_answer_pattern": False,
                    "regs": ["户名[:：](?P<dst>.*)"],
                },
            },
        ],
    },
    {
        "path": ["客户服务机构收取客户服务费用的银行账户", "开户行"],
        "models": [
            {
                "name": "elements_collector_based",
                "elements_collect_model": "middle_paras",
                "elements_collect_config": {
                    "use_syllabus_model": True,
                    "inject_syllabus_features": P_ACCRUAL_METHOD,
                    "only_inject_features": True,
                    "table_regarded_as_paras": True,
                    "top_anchor_regs": [rf"{P_TITLE_HEAD}.*系统服务费"],
                    "bottom_anchor_regs": [r"账号|开户|大额", rf"{P_TITLE_HEAD}.*((管理|托管|顾问)费|业绩报酬)"],
                    "bottom_default": True,
                    "bottom_greed": True,
                    "bottom_continue_greed": True,
                    "include_bottom_anchor": True,
                },
                "paragraph_model": "partial_text",
                "para_config": {
                    "use_answer_pattern": False,
                    "regs": ["开户银?行[:：](?P<dst>.*)"],
                },
            },
        ],
    },
    {
        "path": ["客户服务机构收取客户服务费用的银行账户", "账号"],
        "models": [
            {
                "name": "elements_collector_based",
                "elements_collect_model": "middle_paras",
                "elements_collect_config": {
                    "use_syllabus_model": True,
                    "inject_syllabus_features": P_ACCRUAL_METHOD,
                    "only_inject_features": True,
                    "table_regarded_as_paras": True,
                    "top_anchor_regs": [rf"{P_TITLE_HEAD}.*系统服务费"],
                    "bottom_anchor_regs": [r"账号|开户|大额", rf"{P_TITLE_HEAD}.*((管理|托管|顾问)费|业绩报酬)"],
                    "bottom_default": True,
                    "bottom_greed": True,
                    "bottom_continue_greed": True,
                    "include_bottom_anchor": True,
                },
                "paragraph_model": "partial_text",
                "para_config": {
                    "use_answer_pattern": False,
                    "regs": ["账号[:：](?P<dst>.*)"],
                },
            },
        ],
    },
    {
        "path": ["客户服务机构收取客户服务费用的银行账户", "大额支付号"],
        "models": [
            {
                "name": "elements_collector_based",
                "elements_collect_model": "middle_paras",
                "elements_collect_config": {
                    "use_syllabus_model": True,
                    "inject_syllabus_features": P_ACCRUAL_METHOD,
                    "only_inject_features": True,
                    "table_regarded_as_paras": True,
                    "top_anchor_regs": [rf"{P_TITLE_HEAD}.*系统服务费"],
                    "bottom_anchor_regs": [r"账号|开户|大额", rf"{P_TITLE_HEAD}.*((管理|托管|顾问)费|业绩报酬)"],
                    "bottom_default": True,
                    "bottom_greed": True,
                    "bottom_continue_greed": True,
                    "include_bottom_anchor": True,
                },
                "paragraph_model": "partial_text",
                "para_config": {
                    "use_answer_pattern": False,
                },
            },
        ],
    },
    {
        "path": ["其它费用"],
        "models": [
            {
                "name": "syllabus_elt_v2",
            },
        ],
    },
    {
        "path": ["业绩报酬-计算方式"],
        "models": [
            {"name": "para_match", "paragraph_pattern": r"本计划不计提业绩报酬"},
            {
                "name": "middle_paras",
                "use_syllabus_model": True,
                "inject_syllabus_features": P_ACCRUAL_METHOD,
                "only_inject_features": True,
                "top_anchor_regs": [rf"{P_TITLE_HEAD}.*管理人.*的业绩报酬"],
                "bottom_anchor_regs": [r"管理人.*的业绩报酬支付时"],
                "include_top_anchor": False,
                "include_bottom_anchor": False,
                "bottom_anchor_content_regs": [r"(?P<content>.*?)管理人(和投资顾问)?的业绩报酬支付时"],
            },
        ],
    },
    {
        "path": ["业绩报酬-支付方式"],
        "models": [
            {"name": "para_match", "paragraph_pattern": r"本计划不计提业绩报酬"},
            {
                "name": "middle_paras",
                "use_syllabus_model": True,
                "inject_syllabus_features": P_ACCRUAL_METHOD,
                "only_inject_features": True,
                "top_anchor_regs": [
                    r"管理人.*的业绩报酬支付时",
                    r"业绩报酬收取账户信息如下：",
                    r"业绩报酬的支付",
                    r"由资产管理人向资产托管人发送划款指令",
                    r"(资产管理人的)?业绩报酬.*计算.*支付",
                    r"业绩报酬由份额登记机构负责计算",
                ],
                "top_anchor_content_regs": [
                    r"(?P<content>管理人(和投资顾问)?的业绩报酬支付时.*)",
                    r"(?P<content>业绩报酬收取账户信息如下：)",
                    r"(?P<content>由资产管理人向资产托管人发送划款指令.*)",
                    r"(?P<content>业绩报酬的支付.*)",
                    r"(?P<content>(资产管理人的)?业绩报酬.*计算.*支付.*)",
                    r"(?P<content>.*业绩报酬由份额登记机构负责计算.*)",
                ],
                "bottom_anchor_regs": [r"账号|开户|大额"],
                "bottom_greed": True,
                "bottom_continue_greed": True,
                "include_bottom_anchor": True,
            },
            {
                "name": "middle_paras",
                "use_syllabus_model": True,
                "inject_syllabus_features": P_ACCRUAL_METHOD,
                "only_inject_features": True,
                "top_anchor_regs": [
                    r"管理人.*的业绩报酬支付时",
                    r"业绩报酬收取账户信息如下：",
                    r"业绩报酬的支付",
                    r"由资产管理人向资产托管人发送划款指令",
                    r"(资产管理人的)?业绩报酬.*计算.*支付",
                    r"业绩报酬由份额登记机构负责计算",
                ],
                "top_anchor_content_regs": [
                    r"(?P<content>管理人(和投资顾问)?的业绩报酬支付时.*)",
                    r"(?P<content>业绩报酬收取账户信息如下：)",
                    r"(?P<content>由资产管理人向资产托管人发送划款指令.*)",
                    r"(?P<content>业绩报酬的支付.*)",
                    r"(?P<content>(资产管理人的)?业绩报酬.*计算.*支付.*)",
                    r"(?P<content>.*业绩报酬由份额登记机构负责计算.*)",
                ],
                "bottom_anchor_regs": [P_TITLE_HEAD],
            },
        ],
    },
    {
        "path": ["不列入资产管理业务费用的项目"],
        "models": [
            {
                "name": "syllabus_elt_v2",
            },
        ],
    },
    {
        "path": ["费用调整"],
        "models": [
            {
                "name": "syllabus_elt_v2",
            },
        ],
    },
    {
        "path": ["税收"],
        "models": [
            {
                "name": "syllabus_elt_v2",
            },
        ],
    },
    {
        "path": ["可供分配利润的构成"],
        "models": [
            {
                "name": "syllabus_elt_v2",
            },
        ],
    },
    {
        "path": ["计划收益分配原则"],
        "models": [
            {
                "name": "syllabus_elt_v2",
            },
        ],
    },
    {
        "path": ["收益分配次数限制（如有）"],
        "models": [
            {
                "name": "para_match",
                "paragraph_pattern": r"最多分配.次|至多进行.收利益分配|不做收益分配",
            },
        ],
    },
    {
        "path": ["收益分配方案的确定与通知"],
        "models": [
            {
                "name": "syllabus_elt_v2",
            },
        ],
    },
    {
        "path": ["收益分配的执行方式"],
        "models": [
            {
                "name": "syllabus_elt_v2",
            },
        ],
    },
    {
        "path": ["向资产委托人提供的报告"],
        "models": [
            {
                "name": "syllabus_elt_v2",
                "inject_syllabus_features": [r"向资产委托人提供的报告"],
                "only_inject_features": True,
            },
        ],
    },
    {
        "path": ["向投资者提供的报告"],
        "models": [
            {
                "name": "syllabus_elt_v2",
                "inject_syllabus_features": [r"向投资者提供的报告"],
                "only_inject_features": True,
            },
        ],
    },
    {
        "path": ["年度报告"],
        "models": [
            {
                "name": "syllabus_elt_v2",
            },
        ],
    },
    {
        "path": ["季度报告"],
        "models": [
            {
                "name": "syllabus_elt_v2",
            },
        ],
    },
    {
        "path": ["净值报告"],
        "models": [
            {
                "name": "syllabus_elt_v2",
                "inject_syllabus_features": [r"净值报告"],
                "only_inject_features": True,
            },
            {"name": "para_match", "paragraph_pattern": r"管理人.*?将.*?复核的.*?净值以各方认可的形式提交投资者。"},
        ],
    },
    {
        "path": ["临时报告"],
        "models": [
            {
                "name": "syllabus_elt_v2",
            },
        ],
    },
    {
        "path": ["向资产委托人提供报告及资产委托人信息查询的方式"],
        "models": [
            {
                "name": "syllabus_elt_v2",
            },
        ],
    },
    {
        "path": ["向监管机构提供的报告"],
        "models": [
            {
                "name": "syllabus_elt_v2",
                "inject_syllabus_features": [r"向监管机构提供的报告"],
                "only_inject_features": True,
            },
        ],
    },
    {
        "path": ["信息保密义务"],
        "models": [
            {
                "name": "syllabus_elt_v2",
            },
        ],
    },
    {
        "path": ["特殊风险揭示"],
        "models": [
            {
                "name": "syllabus_elt_v2",
                "inject_syllabus_features": [r"__regex__特殊风险揭示"],
                "only_inject_features": True,
            },
        ],
    },
    {
        "path": ["一般风险揭示"],
        "models": [
            {
                "name": "syllabus_elt_v2",
                "inject_syllabus_features": [r"__regex__一?般风险揭示", "资产管理计划面临的一般风险"],
                "only_inject_features": True,
            },
        ],
    },
    {
        "path": ["投资标的的风险"],
        "models": [
            {
                "name": "syllabus_elt_v2",
                "inject_syllabus_features": [r"__regex__投资标的的?(相关|特有)?风险"],
                "only_inject_features": True,
            },
        ],
    },
    {
        "path": ["风险揭示-特别提示"],
        "models": [
            {
                "name": "syllabus_elt_v2",
                "inject_syllabus_features": [r"该产品的特别提示"],
                "only_inject_features": True,
            },
        ],
    },
    {
        "path": ["合同的变更"],
        "models": [
            {
                "name": "middle_paras",
                "use_syllabus_model": True,
                "inject_syllabus_features": [r"__regex__资产管理(计划)?合同的(变更|成立)"],
                "only_inject_features": True,
                "top_default": True,
                "bottom_anchor_regs": [
                    r"展期|资产管理合同的变更与终止|(计划|合同)终止|管理人与托管人变更",
                ],
            },
        ],
    },
    {
        "path": ["以下事项可由资产管理人自行决定变更"],
        "models": [
            {
                "name": "middle_paras",
                "use_syllabus_model": True,
                "inject_syllabus_features": [r"__regex__资产管理(计划)?合同的(变更|成立)"],
                "only_inject_features": True,
                "top_anchor_regs": [
                    r"以下事项可由(资产)?管理人自行决定变更",
                    r"合同变更事项可由管理人自行决定",
                    r"资产管理人有权(单独)?变更合同内容的情形",
                ],
                "bottom_anchor_regs": [
                    r"由(资产)?管理人和(资产)?托管人协商",
                    r"对上述资产管理人有权单独变更合同的内容进行变更后",
                    r"对资产管理合同任何形式的变更",
                    r"对于资产管理人有权自主决定变更合同的情形",
                    r"(基金|资产管理计划)由其他管理人承接",
                ],
            },
        ],
    },
    {
        "path": ["以下事项可由资产管理人和资产托管人协商后变更"],
        "models": [
            {
                "name": "syllabus_elt_v2",
                "inject_syllabus_features": [
                    r"__regex__以下.*事项可由(资产)?管理人和(资产)?托管人协商(一致)?后(变更|决定)",
                    r"__regex__(资产)?管理人(有权)?[和与](资产)?托管人协商(一致)?后.变更合同",
                ],
                "only_inject_features": True,
            },
            {
                "name": "middle_paras",
                "use_syllabus_model": True,
                "inject_syllabus_features": [r"资产管理合同的变更"],
                "only_inject_features": True,
                "top_anchor_regs": [
                    rf"{P_TITLE_HEAD}.*以下事项可由(资产)?管理人和(资产)?托管人协商(一致)?后变更",
                    rf"{P_TITLE_HEAD}.*以下.*事项可由(资产)?管理人和(资产)?托管人协商(一致)?后(变更|决定)",
                    rf"{P_TITLE_HEAD}.*(资产)?管理人(有权)?[和与](资产)?托管人协商(一致)?后.变更合同",
                ],
                "bottom_anchor_regs": [
                    rf"{P_TITLE_HEAD}.*(资产管理人被依法撤销|其余事项如需发生变更)",
                    r"资产管理人应当及时将资产合同变更的具体内容告知投资者",
                ],
                "include_top_anchor": False,
            },
        ],
    },
    {
        "path": ["计划终止（含提前终止）的情形包括下列事项"],
        "models": [
            {
                "name": "middle_paras",
                "use_syllabus_model": True,
                "inject_syllabus_features": [r"__regex__资产管理(计划)?合同的(变更|成立)"],
                "only_inject_features": True,
                "top_anchor_regs": [rf"{P_TITLE_HEAD}.*(计划|合同)的?终止"],
                "include_top_anchor": False,
                "bottom_anchor_regs": [
                    rf"{P_TITLE_HEAD}.*计划的?([财资]产)?的?清算",
                    rf"{P_TITLE_HEAD}.*本计划的展期",
                    rf"{P_TITLE_HEAD}清算",
                    rf"{P_TITLE_HEAD}.*清算组的成立",
                ],
            },
        ],
    },
    {
        "path": ["计划的展期"],
        "models": [
            {
                "name": "syllabus_elt_v2",
            },
        ],
    },
    {
        "path": ["计划财产的清算"],
        "models": [
            {
                "name": "syllabus_elt_v2",
                "inject_syllabus_features": [
                    r"__regex__资产管理(计划)?合同的(变更|成立)(、终止与财产清算|与终止)__regex__清算",
                    r"__regex__(基金|资产管理计划)的财产清算|清算程序",
                ],
                "only_inject_features": True,
            },
        ],
    },
    {
        "path": ["清算小组"],
        "models": [
            {
                "name": "syllabus_elt_v2",
            },
        ],
    },
    {
        "path": ["清算程序"],
        "models": [
            {
                "name": "syllabus_elt_v2",
            },
        ],
    },
    {
        "path": ["清算费用的来源和支付方式"],
        "models": [
            {
                "name": "syllabus_elt_v2",
            },
        ],
    },
    {
        "path": ["清算剩余财产的支付"],
        "models": [
            {
                "name": "syllabus_elt_v2",
            },
        ],
    },
    {
        "path": ["资产管理计划延期清算处理方式"],
        "models": [
            {
                "name": "syllabus_elt_v2",
            },
            {
                "name": "para_match",
                "paragraph_pattern": [r"(?P<content>.*?)资产管理计划财产清算报告的告知安排"],
            },
        ],
    },
    {
        "path": ["清算报告的告知安排"],
        "models": [
            {
                "name": "syllabus_elt_v2",
                "neglect_patterns": [r"(基金|资产管理计划)延期清算处理方式", r"清算剩余财产的支付"],
            },
            {
                "name": "syllabus_based",
                "extract_from": "same_type_elements",
                "inject_syllabus_features": [r"__regex__资产管理计划财产清算报告的告知安排.?$"],
                "only_inject_features": True,
                "paragraph_model": "middle_paras",
                "para_config": {
                    "use_direct_elements": True,
                    "top_anchor_regs": [r"清算报告的告知安排"],
                    "bottom_anchor_regs": [r"清算账册及文件由管理人保[管存]"],
                    "include_top_anchor": False,
                    "include_bottom_anchor": True,
                },
            },
            {
                "name": "syllabus_based",
                "extract_from": "same_type_elements",
                "inject_syllabus_features": [r"__regex__(基金|资产管理计划)延期清算处理方式"],
                "only_inject_features": True,
                "paragraph_model": "middle_paras",
                "para_config": {
                    "use_direct_elements": True,
                    "top_anchor_regs": [r"清算报告的告知安排"],
                    "bottom_anchor_regs": [r"清算账册及文件由管理人保[管存]"],
                    "include_top_anchor": False,
                    "include_bottom_anchor": True,
                },
            },
        ],
    },
    {
        "path": ["计划财产清算账册及文件的保存"],
        "models": [
            {
                "name": "para_match",
                "paragraph_pattern": r"计划.*(清算|会计)账册.*文件.*保存",
            },
        ],
    },
    {
        "path": ["合同的效力"],
        "models": [
            {
                "name": "syllabus_elt_v2",
            },
        ],
    },
    {
        "path": ["合同签署方式"],
        "models": [
            {
                "name": "syllabus_elt_v2",
                "inject_syllabus_features": [r"合同签署方式"],
                "only_inject_features": True,
            },
            {
                "name": "para_match",
                "paragraph_pattern": (
                    r"(?P<content>(本合同的签署采用纸质合同方式进行的，)?(委托|投资)[人者]为.*人.*的.*盖.章.*签字.*(成立|生效))",
                    r"(?P<content>本资管合同的签署.*由(管理人|责任方)承担)",
                ),
                "content_pattern": True,
            },
        ],
    },
    {
        "path": ["合同成立"],
        "models": [
            {
                "name": "syllabus_elt_v2",
                "inject_syllabus_features": [r"合同成立"],
                "only_inject_features": True,
            },
            {
                "name": "para_match",
                "paragraph_pattern": (r"(?P<content>(.*合同.*之日起(成立|生效)))",),
                "content_pattern": True,
            },
        ],
    },
    {
        "path": ["资产管理计划成立"],
        "models": [
            {
                "name": "para_match",
                "paragraph_pattern": (
                    r"公告资产管理计划成立",
                    r"本资产管理计划自.*备案.*备案证明之日起生效",
                    r"管理人.*通知投资者.*资产管理计划成立",
                ),
            },
        ],
    },
    {
        "path": ["本合同的通知在下列日期视为送达被通知方"],
        "models": [
            {
                "name": "middle_paras",
                "use_syllabus_model": True,
                "inject_syllabus_features": [r"其他事项"],
                "only_inject_features": True,
                "top_anchor_regs": [r"视为送达"],
                "bottom_anchor_regs": [r"无正文"],
            },
            {
                "name": "syllabus_elt_v2",
                "inject_syllabus_features": [r"通知与送达"],
                "only_inject_features": True,
            },
        ],
    },
    {
        "path": ["资产管理计划的份额登记、估值与核算、信息技术系统等服务机构"],
        "models": [
            {
                "name": "syllabus_elt_v2",
                "neglect_patterns": [r"募集面值"],
            },
            {
                "name": "middle_paras",
                "use_syllabus_model": True,
                "inject_syllabus_features": [r"__regex__(基金|资产管理计划)的基本情况"],
                "only_inject_features": True,
                "top_anchor_regs": [r"(基金|资产管理计划)的份额登记、估值与核算、信息技术系统等服务机构"],
                "bottom_anchor_regs": [r"计划份额净值的计算"],
                "include_top_anchor": False,
            },
        ],
    },
    {
        "path": ["计划份额净值的计算"],
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
