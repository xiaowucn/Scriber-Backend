"""广发招募说明书"""

p_summary_of_escrow = [r"基金托管协议的内容摘要"]
R_SEN_END = "[^。；;]"

predictor_options = [
    {
        "path": ["基金全称"],
        "models": [
            {
                "name": "fixed_position",
                "multi_elements": True,
                "positions": [0, 1, 2],
                "regs": [
                    r"(?P<dst>^广发.*[开放式指数基金]+([(（][QDILOF-]+[）)])?)",
                    r"(?P<dst>^(指数|证券投资).*基金([(（][QDILOF-]+[）)])?)",
                ],
            },
        ],
    },
    {
        "path": ["更新时间"],
        "models": [
            {
                "name": "partial_text",
                "regs": [
                    r"^时间[:：](?P<dst>.*)",
                    r"^.{1,4}年.{1,2}月",
                ],
                "model_alternative": True,
            },
        ],
    },
    {
        "path": ["批复号"],
        "models": [
            {
                "name": "partial_text",
                "regs": [
                    r"(?P<dst>证监许可.*?号)",
                    r"(中国)?证监会(?P<dst>.*?号)",
                ],
                "model_alternative": True,
            },
        ],
    },
    {
        "path": ["重要提示"],
        "models": [
            {
                "name": "syllabus_elt_v2",
                "break_para_pattern": [r".{0,2}本次更新的招募说明书"],
            },
        ],
    },
    {
        "path": ["重要提示（更新内容概述）"],
        "models": [
            {
                "name": "syllabus_based",
                "inject_syllabus_features": [r"__regex__重要提示"],
                "paragraph_model": "para_match",
                "para_config": {
                    "paragraph_pattern": [r"本次更新的招募说明书"],
                },
            },
        ],
    },
    {
        "path": ["前言"],
        "models": [
            {"name": "syllabus_elt_v2"},
        ],
    },
    {
        "path": ["释义"],
        "models": [
            {"name": "syllabus_elt_v2"},
        ],
    },
    {
        "path": ["公司名称1"],
        "models": [
            {"name": "partial_text"},
        ],
    },
    {
        "path": ["公司住所1"],
        "models": [
            {"name": "partial_text"},
        ],
    },
    {
        "path": ["公司办公地址1"],
        "models": [
            {
                "name": "middle_paras",
                "top_anchor_regs": [r"办公地址"],
                "top_anchor_content_regs": [r"办公地址.(?P<content>.*)"],
                "bottom_anchor_regs": [r"法定代表人"],
            },
            {"name": "partial_text"},
        ],
    },
    {
        "path": ["公司法定代表人1"],
        "models": [
            {"name": "partial_text"},
        ],
    },
    {
        "path": ["公司设立时间"],
        "models": [
            {"name": "partial_text"},
        ],
    },
    {
        "path": ["公司联系电话1"],
        "models": [
            {"name": "partial_text"},
        ],
    },
    {
        "path": ["公司统一客服热线"],
        "models": [
            {"name": "partial_text"},
        ],
    },
    {
        "path": ["公司联系人"],
        "models": [
            {"name": "partial_text"},
        ],
    },
    {
        "path": ["公司注册资本1"],
        "models": [
            {"name": "partial_text"},
        ],
    },
    {
        "path": ["公司董事会"],
        "models": [
            {"name": "syllabus_elt_v2"},
        ],
    },
    {
        "path": ["公司监事会成员"],
        "models": [
            {"name": "syllabus_elt_v2"},
        ],
    },
    {
        "path": ["总经理"],
        "models": [
            {"name": "para_match", "paragraph_pattern": [r"[:：]\s?总经理"]},
        ],
    },
    {
        "path": ["公司高级管理人员（除总经理）"],
        "models": [
            {
                "name": "middle_paras",
                "top_anchor_regs": [r"[:：]\s?副总经理"],
                "bottom_anchor_regs": [r"^4"],
            },
        ],
    },
    {
        "path": ["基金经理"],
        "models": [
            {
                "name": "syllabus_based",
                "inject_syllabus_features": [r"__regex__基金经理"],
                "paragraph_model": "partial_text",
                "skip_merged_para": True,
                "para_config": {
                    "regs": [r"(?P<dst>.*)(先生|女士)[,，]"],
                },
                "model_alternative": True,
            },
        ],
    },
    {
        "path": ["基金经理信息(招募)"],
        "models": [
            {"name": "syllabus_elt_v2"},
        ],
    },
    {
        "path": ["投资决策委员会成员"],
        "models": [
            {"name": "syllabus_elt_v2"},
        ],
    },
    {
        "path": ["人员亲属关系表述"],
        "models": [
            {"name": "partial_text"},
        ],
    },
    {
        "path": ["基金管理人的职责"],
        "models": [
            {"name": "syllabus_elt_v2"},
        ],
    },
    {
        "path": ["基金管理人和基金经理的承诺"],
        "models": [
            {
                "name": "syllabus_elt_v2",
                "inject_syllabus_features": [r"__regex__基金管理人([及和与]基金经理)?的?承诺"],
            },
        ],
    },
    {
        "path": ["基金管理人的内部控制制度"],
        "models": [
            {"name": "syllabus_elt_v2"},
        ],
    },
    {
        "path": ["基金托管人名称1"],
        "models": [
            {
                "name": "row_match",
                "merge_row": True,
                "row_pattern": [r"^名称"],
                "content_pattern": [
                    r"^名称.(?P<dst>.+)",
                ],
            },
            {"name": "partial_text"},
        ],
    },
    {
        "path": ["托管人设立日期1"],
        "models": [
            {
                "name": "partial_text",
                "regs": [r"(注册|成立|设立)(日期|时间)[:：](?P<dst>.*)"],
                "model_alternative": True,
            },
        ],
    },
    {
        "path": ["基金托管人注册地址"],
        "models": [
            {"name": "partial_text"},
        ],
    },
    {
        "path": ["基金托管人办公地址1"],
        "models": [
            {"name": "partial_text"},
        ],
    },
    {
        "path": ["基金托管人注册资本1"],
        "models": [
            {"name": "partial_text"},
        ],
    },
    {
        "path": ["基金托管人法定代表人1"],
        "models": [
            {"name": "partial_text"},
        ],
    },
    {
        "path": ["托管人行长"],
        "models": [
            {"name": "partial_text"},
        ],
    },
    {
        "path": ["基金托管人文号"],
        "models": [
            {"name": "partial_text"},
        ],
    },
    {
        "path": ["基金托管人电话（招募）"],
        "models": [
            {"name": "partial_text"},
        ],
    },
    {
        "path": ["基金托管人传真（招募）"],
        "models": [
            {
                "name": "syllabus_based",
                "inject_syllabus_features": [r"__regex__基金托管人__regex__基本情况"],
                "paragraph_model": "partial_text",
                "para_config": {"regs": [r"传真[：:]\s?(?P<dst>.*)"], "model_alternative": True},
            },
        ],
    },
    {
        "path": ["基金托管人信息披露负责人（招募）"],
        "models": [
            {
                "name": "partial_text",
                "regs": [r"资产托管部信息披露负责人[：:](?P<dst>.*)"],
            },
        ],
    },
    {
        "path": ["基金份额发售机构"],
        "models": [
            {"name": "syllabus_elt_v2", "inject_syllabus_features": [r"__regex__基金份额[发销]售机构"]},
        ],
    },
    {
        "path": ["注册登记人"],
        "models": [
            {
                "name": "syllabus_elt_v2",
                "inject_syllabus_features": [r"__regex__注册登记机构"],
            },
        ],
    },
    {
        "path": ["注册登记人明细"],
        "models": [
            {
                "name": "fake_kv",
                "closest_syllabus_pattern": [
                    r"(注册)?登记(人|机构)$",
                    r"登记结算(人|机构)$",
                ],
                "use_answer_pattern": False,
                "need_match_length": False,
                "regs": {
                    "公司办公地址2": [r"地址[:：](?P<dst>.*)"],
                    "公司住所2": [r"地址[:：](?P<dst>.*)"],
                },
                "model_alternative": True,
            },
        ],
    },
    {
        "path": ["出具法律意见书的律所名称（招募）"],
        "models": [
            {
                "name": "fake_kv",
                "closest_syllabus_pattern": [
                    r"出具法律意见\w+事务所$",
                ],
                "use_answer_pattern": False,
            },
        ],
    },
    {
        "path": ["律所住所"],
        "models": [
            {
                "name": "fake_kv",
                "closest_syllabus_pattern": [
                    r"出具法律意见\w+事务所$",
                ],
                "use_answer_pattern": False,
                "need_match_length": False,
                "merge_row": True,
                "merge_condition": "：:",
                # '住所：广东省广州市天河区珠江新城珠江东路6号广州周大福金融中心（广州东塔）29'
                # "regs": [
                #     r"住所[：:](?P<dst>.*)",
                # ],
            },
        ],
    },
    {
        "path": ["律所负责人"],
        "models": [
            {
                "name": "fake_kv",
                "closest_syllabus_pattern": [
                    r"出具法律意见\w+事务所$",
                ],
                "use_answer_pattern": False,
            },
        ],
    },
    {
        "path": ["律所电话"],
        "models": [
            {
                "name": "fake_kv",
                "closest_syllabus_pattern": [
                    r"出具法律意见\w+事务所$",
                ],
                "use_answer_pattern": False,
            },
        ],
    },
    {
        "path": ["律所传真"],
        "models": [
            {
                "name": "fake_kv",
                "closest_syllabus_pattern": [
                    r"出具法律意见\w+事务所$",
                    r"律师事务所和经办律师$",
                ],
                "use_answer_pattern": False,
                "regs": [r"传真[：:]\s?(?P<dst>.*)"],
            },
        ],
    },
    {
        "path": ["律所经办律师"],
        "models": [
            {
                "name": "fake_kv",
                "closest_syllabus_pattern": [
                    r"出具法律意见\w+事务所$",
                ],
                "use_answer_pattern": False,
            },
        ],
    },
    {
        "path": ["律所联系人"],
        "models": [
            {
                "name": "fake_kv",
                "closest_syllabus_pattern": [
                    r"出具法律意见\w+事务所$",
                ],
                "use_answer_pattern": False,
            },
        ],
    },
    {
        "path": ["会计事务所名称"],
        "models": [
            {
                "name": "fake_kv",
                "closest_syllabus_pattern": [
                    r"审计\w*?会计\w*?事务所$",
                ],
                "use_answer_pattern": False,
            },
        ],
    },
    {
        "path": ["会计事务所办公地址"],
        "models": [
            {
                "name": "fake_kv",
                "closest_syllabus_pattern": [
                    r"审计\w*?会计\w*?事务所$",
                ],
                "use_answer_pattern": False,
            },
        ],
    },
    {
        "path": ["会计事务所负责人或法人代表"],
        "models": [
            {
                "name": "fake_kv",
                "closest_syllabus_pattern": [
                    r"审计\w*?会计\w*?事务所$",
                ],
                "use_answer_pattern": False,
            },
        ],
    },
    {
        "path": ["会计事务所联系人"],
        "models": [
            {
                "name": "fake_kv",
                "closest_syllabus_pattern": [
                    r"审计\w*?会计\w*?事务所$",
                ],
                "use_answer_pattern": False,
            },
        ],
    },
    {
        "path": ["会计事务所电话"],
        "models": [
            {
                "name": "fake_kv",
                "closest_syllabus_pattern": [
                    r"审计\w*?会计\w*?事务所$",
                ],
                "use_answer_pattern": False,
            },
        ],
    },
    {
        "path": ["会计事务所传真"],
        "models": [
            {
                "name": "fake_kv",
                "closest_syllabus_pattern": [
                    r"审计\w*?会计\w*?事务所$",
                ],
                "use_answer_pattern": False,
            },
            {
                "name": "syllabus_based",
                "inject_syllabus_features": [r"__regex__审计\w*?会计\w*?事务所$"],
                "extract_from": "same_type_elements",
                "paragraph_model": "partial_text",
                "para_config": {
                    "regs": [r"传真[：:]\s?(?P<dst>.*)"],
                },
            },
        ],
    },
    {
        "path": ["会计事务所经办会计师"],
        "models": [
            {
                "name": "fake_kv",
                "closest_syllabus_pattern": [
                    r"审计\w*?会计\w*?事务所$",
                ],
                "use_answer_pattern": False,
            },
        ],
    },
    {
        "path": ["基金募集总括信息"],
        "models": [
            {
                "name": "syllabus_elt_v2",
                "only_first": True,
            },
        ],
    },
    {
        "path": ["基金运作方式"],
        "models": [
            {
                "name": "syllabus_elt_v2",
            },
            {"name": "partial_text"},
        ],
    },
    {
        "path": ["基金类型（招募）"],
        "models": [
            {"name": "syllabus_elt_v2"},
        ],
    },
    {
        "path": ["基金存续期（招募）"],
        "models": [
            {"name": "syllabus_elt_v2"},
        ],
    },
    {
        "path": ["上市交易所"],
        "models": [
            {"name": "syllabus_elt_v2"},
        ],
    },
    {
        "path": ["本基金与目标ETF的联系与区别"],
        "models": [
            {"name": "syllabus_elt_v2"},
        ],
    },
    {
        "path": ["允许认购（申购客户类型）"],
        "models": [
            {"name": "syllabus_elt_v2"},
        ],
    },
    {
        "path": ["募集方式与募集期限"],
        "models": [
            {"name": "syllabus_elt_v2"},
        ],
    },
    {
        "path": ["募集场所"],
        "models": [
            {"name": "syllabus_elt_v2"},
        ],
    },
    {
        "path": ["募集对象"],
        "models": [
            {"name": "syllabus_elt_v2"},
        ],
    },
    {
        "path": ["基金的最低募集份额总额"],
        "models": [
            {"name": "syllabus_elt_v2"},
        ],
    },
    {
        "path": ["发起资金的认购"],
        "models": [
            {"name": "syllabus_elt_v2"},
        ],
    },
    {
        "path": ["发售方式"],
        "models": [
            {"name": "syllabus_elt_v2"},
        ],
    },
    {
        "path": ["基金的份额类别设置"],
        "models": [
            {"name": "syllabus_elt_v2"},
        ],
    },
    {
        "path": ["投资者认购应提交的文件和办理的手续"],
        "models": [
            {"name": "syllabus_elt_v2"},
        ],
    },
    {
        "path": ["基金份额发售面值、认购价格和认购费用"],
        "models": [
            {
                "name": "syllabus_elt_v2",
                "inject_syllabus_features": [r"基金份额发售面值、认购价格和认购费用"],
                "neglect_patterns": [r"基金合同的生效"],
            },
        ],
    },
    {
        "path": ["认购方式"],
        "models": [
            {"name": "partial_text"},
        ],
    },
    {
        "path": ["个人首次认购最低金额（元）"],
        "models": [
            {
                "name": "partial_text",
                "regs": [
                    r"每一基金投资者通过本公司网上交易系统和其他销售机构销售网点每个基金账户首次认购的最低限额为(?P<dst>\d+)元"
                ],
                "model_alternative": True,
            },
        ],
    },
    {
        "path": ["机构首次认购最低金额（元）"],
        "models": [
            {
                "name": "partial_text",
                "regs": [
                    r"每一基金投资者通过本公司网上交易系统和其他销售机构销售网点每个基金账户首次认购的最低限额为(?P<dst>\d+)元"
                ],
                "model_alternative": True,
            },
        ],
    },
    {
        "path": ["个人追加认购最低金额（元）"],
        "models": [
            {"name": "partial_text"},
        ],
    },
    {
        "path": ["机构追加认购最低金额（元）"],
        "models": [
            {"name": "partial_text"},
        ],
    },
    {
        "path": ["投资人对基金份额的认购"],
        "models": [
            {
                "name": "syllabus_elt_v2",
                "inject_syllabus_features": [r"投资人对基金份额的认购"],
            },
        ],
    },
    {
        "path": ["是否利息转份额"],
        "models": [
            {"name": "partial_text"},
        ],
    },
    {
        "path": ["首次募集期间认购资金利息的处理方式"],
        "models": [
            {"name": "syllabus_elt_v2"},
        ],
    },
    {
        "path": ["认购开户"],
        "models": [
            {"name": "syllabus_elt_v2"},
        ],
    },
    {
        "path": ["认购费用"],
        "models": [
            {
                "name": "syllabus_elt_v2",
                "skip_table": True,
                "inject_syllabus_features": [r"__regex__基金份额发售面值、认购价格和认购费用"],
            },
        ],
    },
    {
        "path": ["网上现金认购"],
        "models": [
            {"name": "syllabus_elt_v2"},
        ],
    },
    {
        "path": ["网下现金认购"],
        "models": [
            {"name": "syllabus_elt_v2"},
        ],
    },
    {
        "path": ["网下股票认购"],
        "models": [
            {"name": "syllabus_elt_v2"},
        ],
    },
    {
        "path": ["募集资金利息与募集股票权益的处理方式"],
        "models": [
            {"name": "syllabus_elt_v2"},
        ],
    },
    {
        "path": ["募集期间的资金、股票与费用"],
        "models": [
            {"name": "syllabus_elt_v2"},
        ],
    },
    {
        "path": ["发行联接基金或增设新的份额类别"],
        "models": [
            {"name": "syllabus_elt_v2"},
        ],
    },
    {
        "path": ["基金的募集"],
        "models": [
            {"name": "syllabus_elt_v2", "only_before_first_chapter": True},
        ],
    },
    {
        "path": ["基金备案的条件"],
        "models": [
            {"name": "syllabus_elt_v2"},
        ],
    },
    {
        "path": ["基金合同不能生效时募集资金的处理方式"],
        "models": [
            {"name": "syllabus_elt_v2"},
        ],
    },
    {
        "path": ["基金存续期内的基金份额持有人数量和资金数额"],
        "models": [
            {"name": "syllabus_elt_v2"},
        ],
    },
    {
        "path": ["基金的自动终止"],
        "models": [
            {"name": "syllabus_elt_v2", "syllabus_black_list": [r"基金存续期内的基金份额持有人数量和资金数额"]},
        ],
    },
    {
        "path": ["申购与赎回的场所"],
        "models": [
            {"name": "syllabus_elt_v2"},
        ],
    },
    {
        "path": ["申购与赎回的开放日及时间"],
        "models": [
            {"name": "syllabus_elt_v2", "inject_syllabus_features": [r"__regex__申购与赎回的开放日及时间"]},
        ],
    },
    {
        "path": ["申购方式"],
        "models": [
            {"name": "partial_text"},
        ],
    },
    {
        "path": ["赎回处理顺序"],
        "models": [
            {
                "name": "partial_text",
                "regs": [r"赎回遵循“(?P<dst>.+)”原则"],
                "model_alternative": True,
            },
        ],
    },
    {
        "path": ["申购与赎回的原则"],
        "models": [
            {"name": "syllabus_elt_v2"},
        ],
    },
    {
        "path": ["个人首次申购最低金额（元）"],
        "models": [
            {"name": "partial_text"},
        ],
    },
    {
        "path": ["机构首次申购最低金额（元）"],
        "models": [
            {"name": "partial_text"},
        ],
    },
    {
        "path": ["个人追加申购最低金额（元）"],
        "models": [
            {"name": "partial_text"},
        ],
    },
    {
        "path": ["机构追加申购最低金额（元）"],
        "models": [
            {"name": "partial_text"},
        ],
    },
    {
        "path": ["申购与赎回的数额限制"],
        "models": [
            {"name": "syllabus_elt_v2"},
        ],
    },
    {
        "path": ["申购委托确认日期"],
        "models": [
            {"name": "partial_text"},
        ],
    },
    {
        "path": ["赎回委托确认日期"],
        "models": [
            {"name": "partial_text"},
        ],
    },
    {
        "path": ["申购与赎回的程序"],
        "models": [
            {"name": "syllabus_elt_v2", "inject_syllabus_features": [r"__regex__申购与赎回的程序"]},
        ],
    },
    {
        "path": ["申购费率"],
        "models": [
            {
                "name": "syllabus_elt_v2",
                "skip_table": True,
            },
        ],
    },
    {
        "path": ["赎回费率"],
        "models": [
            {
                "name": "middle_paras",
                "inject_syllabus_features": [r"申购费率、赎回费率"],
                "only_use_syllabus_elements": True,
                "use_syllabus_model": True,
                "table_regarded_as_paras": True,
                "top_anchor_regs": [r"^\d.赎回费率"],
                "include_top_anchor": False,
                "bottom_anchor_regs": [r"^\d.基金管理人可以在履行相关手续后"],
            },
            {"name": "syllabus_elt_v2"},
        ],
    },
    {
        "path": ["赎回方式"],
        "models": [
            {"name": "partial_text"},
        ],
    },
    {
        "path": ["申购份额与赎回金额的计算方式"],
        "models": [
            {
                "name": "syllabus_elt_v2",
                "inject_syllabus_features": [r"申购份额与赎回金额的计算方式"],
            },
        ],
    },
    {
        "path": ["申购与赎回的注册登记"],
        "models": [
            {"name": "syllabus_elt_v2"},
        ],
    },
    {
        "path": ["C类收费模式"],
        "models": [
            {"name": "partial_text"},
        ],
    },
    {
        "path": ["申赎费率的其他规定"],
        "models": [
            {
                "name": "middle_paras",
                "inject_syllabus_features": [r"申购费率、赎回费率"],
                "only_use_syllabus_elements": True,
                "top_anchor_regs": [r"^3"],
                "use_syllabus_model": True,
                "include_bottom_anchor": True,
                "bottom_default": True,
            },
        ],
    },
    {
        "path": ["申购和赎回的对价、费用及其用途"],
        "models": [
            {"name": "syllabus_elt_v2"},
        ],
    },
    {
        "path": ["申购、赎回清单的内容与格式"],
        "models": [
            {
                "name": "syllabus_elt_v2",
                "inject_syllabus_features": [r"__regex__申购、赎回清单的内容与格式"],
                "skip_table": True,
            },
        ],
    },
    {
        "path": ["单一投资者持有比例上限"],
        "models": [
            {"name": "partial_text"},
        ],
    },
    {
        "path": ["拒绝或暂停申购的情形及处理"],
        "models": [
            {"name": "syllabus_elt_v2"},
        ],
    },
    {
        "path": ["暂停赎回或延缓支付赎回款项的情形及处理"],
        "models": [
            {
                "name": "syllabus_elt_v2",
                "inject_syllabus_features": [
                    "__regex__暂停赎回的情形及处理(方式)?",
                    "__regex__拒绝或暂停申购、(暂停)?赎回的情形及处理(方式)?",
                    "拒绝或暂停赎回的情形",
                    "暂停赎回的情形或延缓支付赎回对价的情形",
                ],
            },
        ],
    },
    {
        "path": ["其他申购赎回方式"],
        "models": [
            {"name": "syllabus_elt_v2"},
        ],
    },
    {
        "path": ["巨额赎回的情形及处理方式"],
        "models": [
            {
                "name": "syllabus_elt_v2",
                "inject_syllabus_features": [
                    r"巨额赎回的情形及处理方式",
                    r"巨额赎回的认定及处理方式",
                ],
            },
        ],
    },
    {
        "path": ["暂停申购或赎回的公告和重新开放申购或赎回的公告"],
        "models": [
            {"name": "syllabus_elt_v2"},
        ],
    },
    {
        "path": ["基金的转换"],
        "models": [
            {"name": "syllabus_elt_v2"},
        ],
    },
    {
        "path": ["基金份额的转让"],
        "models": [
            {"name": "syllabus_elt_v2"},
        ],
    },
    {
        "path": ["基金的非交易过户"],
        "models": [
            {"name": "syllabus_elt_v2"},
        ],
    },
    {
        "path": ["定期定额投资计划"],
        "models": [
            {"name": "syllabus_elt_v2"},
        ],
    },
    {
        "path": ["基金的转托管"],
        "models": [
            {"name": "syllabus_elt_v2"},
        ],
    },
    {
        "path": ["基金的冻结、解冻与质押"],
        "models": [
            {"name": "syllabus_elt_v2", "inject_syllabus_features": [r"__regex__基金的冻结和解冻与质押"]},
        ],
    },
    {
        "path": ["实施侧袋机制期间本基金的申购与赎回"],
        "models": [
            {"name": "syllabus_elt_v2"},
        ],
    },
    {
        "path": ["标的指数"],
        "models": [
            {"name": "syllabus_elt_v2"},
        ],
    },
    {
        "path": ["投资目标"],
        "models": [
            {"name": "syllabus_elt_v2"},
        ],
    },
    {
        "path": ["投资范围"],
        "models": [
            {"name": "syllabus_elt_v2"},
        ],
    },
    {
        "path": ["投资理念"],
        "models": [
            {"name": "syllabus_elt_v2"},
        ],
    },
    {
        "path": ["投资策略"],
        "models": [
            {"name": "syllabus_elt_v2", "inject_syllabus_features": [r"__regex__投资策略"], "skip_table": True},
        ],
    },
    {
        "path": ["投资决策依据和投资程序"],
        "models": [
            {"name": "syllabus_elt_v2"},
        ],
    },
    {
        "path": ["投资组合管理"],
        "models": [
            {"name": "syllabus_elt_v2", "inject_syllabus_features": [r"__regex__投资组合管理"]},
        ],
    },
    {
        "path": ["业绩比较基准"],
        "models": [
            {"name": "syllabus_elt_v2"},
        ],
    },
    {
        "path": ["风险收益特征"],
        "models": [
            {"name": "syllabus_elt_v2"},
        ],
    },
    {
        "path": ["收益特征"],
        "models": [
            {"name": "partial_text"},
        ],
    },
    {
        "path": ["组合限制"],
        "models": [
            {"name": "syllabus_elt_v2"},
        ],
    },
    {
        "path": ["禁止行为"],
        "models": [
            {"name": "syllabus_elt_v2"},
        ],
    },
    {
        "path": ["变更规定"],
        "models": [
            {
                "name": "para_match",
                "paragraph_pattern": [
                    r"(?P<content>法律法规或监管部门取消上述组合限制.*)",
                ],
            },
        ],
    },
    {
        "path": ["目标ETF发生相关变更情形时的处理"],
        "models": [
            {"name": "syllabus_elt_v2"},
        ],
    },
    {
        "path": ["基金管理人代表基金行使股东或债权人权利的处理原则及方法"],
        "models": [
            {
                "name": "syllabus_elt_v2",
                "inject_syllabus_features": [
                    r"基金管理人代表基金行使债权人权利的处理原则及方法",
                    r"基金管理人代表基金行使所投资证券产生权利的处理原则及方法",
                    r"基金管理人代表基金行使股东权利的处理原则及方法",
                    r"基金管理人代表基金行使权利的处理原则及方法",
                ],
                "syllabus_black_list": [r"估值日"],
            },
        ],
    },
    {
        "path": ["基金的融资业务"],
        "models": [
            {
                "name": "syllabus_elt_v2",
                "only_inject_features": True,
                "inject_syllabus_features": [r"__regex__基金的融资"],
            },
        ],
    },
    {
        "path": ["侧袋机制的实施和投资运作安排"],
        "models": [
            {"name": "syllabus_elt_v2"},
        ],
    },
    {
        "path": ["未来条件许可情况下的基金模式转换"],
        "models": [
            {"name": "syllabus_elt_v2"},
        ],
    },
    {
        "path": ["基金资产总值"],
        "models": [
            {"name": "syllabus_elt_v2"},
        ],
    },
    {
        "path": ["基金资产净值"],
        "models": [
            {"name": "syllabus_elt_v2"},
        ],
    },
    {
        "path": ["基金财产的账户"],
        "models": [
            {"name": "syllabus_elt_v2"},
        ],
    },
    {
        "path": ["基金财产的保管和处分"],
        "models": [
            {"name": "syllabus_elt_v2"},
        ],
    },
    {
        "path": ["估值日"],
        "models": [
            {"name": "syllabus_elt_v2"},
        ],
    },
    {
        "path": ["估值对象"],
        "models": [
            {"name": "syllabus_elt_v2"},
        ],
    },
    {
        "path": ["估值原则"],
        "models": [
            {"name": "syllabus_elt_v2"},
        ],
    },
    {
        "path": ["估值方法"],
        "models": [
            {"name": "syllabus_elt_v2"},
        ],
    },
    {
        "path": ["估值程序"],
        "models": [
            {"name": "syllabus_elt_v2"},
        ],
    },
    {
        "path": ["净值精度"],
        "models": [
            {"name": "partial_text"},
        ],
    },
    {
        "path": ["估值错误的处理"],
        "models": [
            {"name": "syllabus_elt_v2"},
        ],
    },
    {
        "path": ["暂停估值的情形"],
        "models": [
            {"name": "syllabus_elt_v2"},
        ],
    },
    {
        "path": ["基金净值的确认"],
        "models": [
            {
                "name": "syllabus_elt_v2",
                "neglect_patterns": ["基金资产总值"],
            },
        ],
    },
    {
        "path": ["实施侧袋机制期间的基金资产估值"],
        "models": [
            {
                "name": "syllabus_elt_v2",
                "neglect_patterns": ["基金费用的种类"],
            },
        ],
    },
    {
        "path": ["特殊情形的处理"],
        "models": [
            {"name": "syllabus_elt_v2"},
        ],
    },
    {
        "path": ["基金利润的构成"],
        "models": [
            {"name": "syllabus_elt_v2"},
        ],
    },
    {
        "path": ["基金可供分配利润"],
        "models": [
            {"name": "syllabus_elt_v2"},
        ],
    },
    {
        "path": ["收益分配原则"],
        "models": [
            {"name": "syllabus_elt_v2"},
        ],
    },
    {
        "path": ["基金收益分配数额的确定原则"],
        "models": [
            {
                "name": "syllabus_elt_v2",
                "inject_syllabus_features": [r"基金收益分配数额的确定原则"],
            },
        ],
    },
    {
        "path": ["基金允许的分红方式"],
        "models": [
            {"name": "partial_text"},
        ],
    },
    {
        "path": ["基金默认分红方式"],
        "models": [
            {"name": "partial_text"},
        ],
    },
    {
        "path": ["收益分配方案"],
        "models": [
            {"name": "syllabus_elt_v2"},
        ],
    },
    {
        "path": ["收益分配方案的确定、公告与实施"],
        "models": [
            {"name": "syllabus_elt_v2"},
        ],
    },
    {
        "path": ["基金收益分配中发生的费用"],
        "models": [
            {
                "name": "syllabus_elt_v2",
                "inject_syllabus_features": [r"收益分配中发生的费用"],
            },
        ],
    },
    {
        "path": ["实施侧袋机制期间的收益分配"],
        "models": [
            {
                "name": "syllabus_elt_v2",
                "neglect_patterns": ["证券交易所上市的有价证券的估值"],
            },
        ],
    },
    {
        "path": ["基金费用的种类"],
        "models": [
            {"name": "syllabus_elt_v2"},
        ],
    },
    {
        "path": ["基金管理费表述"],
        "models": [
            {
                "name": "syllabus_elt_v2",
                "inject_syllabus_features": [r"__regex__基金(管理人)?的管理费"],
            },
        ],
    },
    {
        "path": ["管理费率"],
        "models": [
            {
                "name": "partial_text",
                "regs": [
                    r"本基金的管理费按前一日基金资产净值的?(?P<dst>[\d.%]+)的?年费率计提。",
                ],
            },
        ],
    },
    {
        "path": ["托管费率"],
        "models": [
            {
                "name": "partial_text",
                "regs": [
                    r"本基金的托管费按当日计提管理费和托管费前的基金资产净值的?(?P<dst>[\d.%]+)的?年费率计提",
                    r"本基金托管费按前一日基金资产净值扣除.*?后的余额（.*?）的(?P<dst>[\d.%]+)年费率计提",
                    r"本基金A类基金份额的托管费按前一日该类基金份额的基金资产净值扣除.*?后的剩余部分的(?P<dst>[\d.%]+)的年费率计提",
                    r"基金托管费按.*?基金资产净值的(?P<dst>[\d.%]+)的?年费率计提",
                ],
                "model_alternative": True,
            },
        ],
    },
    {
        "path": ["基金托管费表述"],
        "models": [
            {
                "name": "syllabus_elt_v2",
                "inject_syllabus_features": [r"__regex__基金(托管人)?的(基金)?托管费"],
                "break_para_pattern": [r"基金的指数使用许可费"],
            },
        ],
    },
    {
        "path": ["（销售服务费）A类"],
        "models": [
            {
                "name": "partial_text",
                "regs": [
                    r"本基金A类基金份额不收取销售服务费",
                    rf"{R_SEN_END}*A类{R_SEN_END}*销售服务费{R_SEN_END}*[。；;]?",
                ],
                "neglect_syllabus_regs": [r"基金托管人的托管费"],
                "model_alternative": True,
            },
        ],
    },
    {
        "path": ["（销售服务费）C类"],
        "models": [
            {
                "name": "partial_text",
                "regs": [r"C类基金(份额)?的销售服务费按前一日C类基金(份额)?资产净值的?(?P<dst>[\d.%]+)的?年费率计提"],
            },
        ],
    },
    {
        "path": ["基金销售服务费表述"],
        "models": [
            {
                "name": "middle_paras",
                "inject_syllabus_features": [
                    r"__regex__(基金)?的?销售服务费$",
                ],
                "use_syllabus_model": True,
                "top_default": True,
                "bottom_anchor_regs": [
                    r"上述.*根据.*从基金财产中支付",
                    r"(使用许可|许可使用)费",
                ],
                "keywords": [r"销售服务费"],
            },
            {
                "name": "syllabus_elt_v2",
                "inject_syllabus_features": [r"基金的销售服务费"],
            },
        ],
    },
    {
        "path": ["基金费用支付规则表述"],
        "models": [
            {
                "name": "para_match",
                "paragraph_pattern": [
                    r"(?P<content>(上述|除|其它).*?财产中支付.?)",
                    r"(?P<content>(上述|除|其它).*?(基金)?费用.*?列入(或摊入)?当期(基金)?费用.*)",
                ],
            },
        ],
    },
    {
        "path": ["不列入基金费用的项目"],
        "models": [
            {"name": "syllabus_elt_v2"},
        ],
    },
    {
        "path": ["实施侧袋机制期间的基金费用"],
        "models": [
            {"name": "syllabus_elt_v2"},
        ],
    },
    {
        "path": ["基金税收"],
        "models": [
            {"name": "syllabus_elt_v2"},
        ],
    },
    {
        "path": ["费用调整"],
        "models": [
            {"name": "syllabus_elt_v2"},
        ],
    },
    {
        "path": ["基金会计政策"],
        "models": [
            {"name": "syllabus_elt_v2"},
        ],
    },
    {
        "path": ["基金的年度审计"],
        "models": [
            {
                "name": "syllabus_elt_v2",
                "inject_syllabus_features": [r"__regex__基金(年度)?审计"],
            },
        ],
    },
    {
        "path": ["基金侧袋机制综述"],
        "models": [
            {"name": "syllabus_elt_v2", "only_first": True, "inject_syllabus_features": [r"基金的侧袋机制"]},
        ],
    },
    {
        "path": ["侧袋机制的实施条件和程序"],
        "models": [
            {"name": "syllabus_elt_v2"},
        ],
    },
    {
        "path": ["实施侧袋机制期间基金份额的申购与赎回"],
        "models": [
            {"name": "syllabus_elt_v2"},
        ],
    },
    {
        "path": ["实施侧袋机制期间的基金投资"],
        "models": [
            {"name": "syllabus_elt_v2"},
        ],
    },
    {
        "path": ["侧袋账户中特定资产的处置变现和支付"],
        "models": [
            {
                "name": "syllabus_elt_v2",
                "neglect_patterns": ["临时报告"],
            },
        ],
    },
    {
        "path": ["侧袋机制的信息披露"],
        "models": [
            {
                "name": "syllabus_elt_v2",
                "only_inject_features": True,
                "inject_syllabus_features": [r"__regex__侧袋机制的信息披露"],
            },
        ],
    },
    {
        "path": ["侧袋机制履行程序表述"],
        "models": [
            {
                "name": "para_match",
                "paragraph_pattern": [r"本部分关于侧袋机制的相关规定.*持有人大会审议"],
            },
        ],
    },
    {
        "path": ["信披规定表述"],
        "models": [
            {
                "name": "para_match",
                "paragraph_pattern": [r"本基金的信息披露应符合.*?本基金从其最新规定"],
            },
        ],
    },
    {
        "path": ["信息披露义务人"],
        "models": [
            {"name": "syllabus_elt_v2"},
        ],
    },
    {
        "path": ["本基金信息披露义务人承诺公开披露的基金信息，不得有下列行为"],
        "models": [
            {"name": "syllabus_elt_v2"},
        ],
    },
    {
        "path": ["信息披露格式说明"],
        "models": [
            {
                "name": "syllabus_elt_v2",
                "include_title": True,
                "syllabus_black_list": [r"信息披露事务管理"],
                "inject_syllabus_features": [r"__regex__本基金公开披露的信息应采用中文文本"],
            },
        ],
    },
    {
        "path": ["公开披露的基金信息"],
        "models": [
            {"name": "syllabus_elt_v2"},
        ],
    },
    {
        "path": ["单一投资者持有比例上限_整段"],
        "models": [
            {"name": "syllabus_elt_v2"},
        ],
    },
    {
        "path": ["信息披露事务管理"],
        "models": [
            {"name": "syllabus_elt_v2"},
        ],
    },
    {
        "path": ["信息披露文件的存放与查阅"],
        "models": [
            {"name": "syllabus_elt_v2"},
        ],
    },
    {
        "path": ["投资于本基金的主要风险"],
        "models": [
            {
                "name": "syllabus_elt_v2",
                "inject_syllabus_features": [
                    r"__regex__投资于本基金的主要风险",
                    "__regex__本基金特有的风险",
                ],
            },
        ],
    },
    {
        "path": ["声明"],
        "models": [
            {"name": "syllabus_elt_v2"},
        ],
    },
    {
        "path": ["《基金合同》的变更"],
        "models": [
            {"name": "syllabus_elt_v2"},
        ],
    },
    {
        "path": ["《基金合同》的终止事由"],
        "models": [
            {"name": "syllabus_elt_v2"},
        ],
    },
    {
        "path": ["基金财产的清算"],
        "models": [
            {"name": "syllabus_elt_v2"},
        ],
    },
    {
        "path": ["清算费用"],
        "models": [
            {"name": "syllabus_elt_v2"},
        ],
    },
    {
        "path": ["基金财产清算剩余资产的分配"],
        "models": [
            {"name": "syllabus_elt_v2"},
        ],
    },
    {
        "path": ["基金财产清算的公告"],
        "models": [
            {"name": "syllabus_elt_v2"},
        ],
    },
    {
        "path": ["基金财产清算账册及文件的保存"],
        "models": [
            {"name": "syllabus_elt_v2"},
        ],
    },
    {
        "path": ["基金合同当事人及权利义务"],
        "models": [
            {
                "name": "syllabus_elt_v2",
                "inject_syllabus_features": [
                    r"__regex__基金合同当事人[的及]权利(与)?义务",
                    r"__regex__基金份额持有人、基金管理人和基金托管人的权利、义务",
                ],
            },
        ],
    },
    {
        "path": ["基金份额持有人大会召集、议事及表决的程序和规则"],
        "models": [
            {"name": "syllabus_elt_v2"},
        ],
    },
    {
        "path": ["基金合同解除和终止的事由、程序及基金财产的清算方式"],
        "models": [
            {
                "name": "syllabus_elt_v2",
                "min_level": 2,
                "inject_syllabus_features": [
                    r"__regex__基金合同的内容摘要__regex__基金合同解除和终止的事由、程序(以?及基金财产的清算方式)?",
                    r"__regex__基金合同的内容摘要__regex__基金合同的?变更、终止[与和]基金财产的清算",
                ],
            },
        ],
    },
    {
        "path": ["争议的处理"],
        "models": [
            {"name": "syllabus_elt_v2"},
        ],
    },
    {
        "path": ["基金合同存放地和投资者取得合同的方式"],
        "models": [
            {"name": "syllabus_elt_v2"},
        ],
    },
    {
        "path": ["公司名称3"],
        "models": [
            {"name": "partial_text"},
        ],
    },
    {
        "path": ["公司住所3"],
        "models": [
            {"name": "partial_text"},
        ],
    },
    {
        "path": ["公司法定代表人3"],
        "models": [
            {"name": "partial_text"},
        ],
    },
    {
        "path": ["公司设立日期"],
        "models": [
            {"name": "partial_text"},
        ],
    },
    {
        "path": ["公司设立文号"],
        "models": [
            {"name": "partial_text"},
        ],
    },
    {
        "path": ["公司组织形式"],
        "models": [
            {"name": "partial_text"},
        ],
    },
    {
        "path": ["公司注册资本3"],
        "models": [
            {"name": "partial_text"},
        ],
    },
    {
        "path": ["公司存续期限"],
        "models": [
            {"name": "partial_text"},
        ],
    },
    {
        "path": ["公司联系电话2"],
        "models": [
            {
                "name": "syllabus_based",
                "inject_syllabus_features": [r"__regex__基金托管协议的内容摘要"],
                "paragraph_model": "partial_text",
                "para_config": {
                    "regs": [r"电话[：:]\s?(?P<dst>.*)"],
                },
                "model_alternative": True,
            },
        ],
    },
    {
        "path": ["基金托管人名称2"],
        "models": [
            {
                "name": "partial_text",
                "syllabus_regs": p_summary_of_escrow,
            },
        ],
    },
    {
        "path": ["基金托管人住所2"],
        "models": [
            {
                "name": "partial_text",
                "syllabus_regs": p_summary_of_escrow,
            },
        ],
    },
    {
        "path": ["基金托管人办公地址2"],
        "models": [
            {
                "name": "partial_text",
                "syllabus_regs": p_summary_of_escrow,
            },
        ],
    },
    {
        "path": ["基金托管人法定代表人"],
        "models": [
            {"name": "partial_text"},
        ],
    },
    {
        "path": ["基金托管人设立时间2"],
        "models": [
            {
                "name": "partial_text",
                "syllabus_regs": p_summary_of_escrow,
            },
        ],
    },
    {
        "path": ["基金托管人设立文号"],
        "models": [
            {"name": "partial_text"},
        ],
    },
    {
        "path": ["基金托管人组织形式"],
        "models": [
            {
                "name": "partial_text",
                "syllabus_regs": [r"基金托管人"],
            },
        ],
    },
    {
        "path": ["基金托管人注册资本2"],
        "models": [
            {
                "name": "partial_text",
                "syllabus_regs": p_summary_of_escrow,
            },
        ],
    },
    {
        "path": ["基金托管人存续期"],
        "models": [
            {"name": "partial_text"},
        ],
    },
    {
        "path": ["基金托管人对基金管理人的业务监督和核查"],
        "models": [
            {
                "name": "syllabus_elt_v2",
                "inject_syllabus_features": [r"__regex__基金托管人对基金管理人的业务监督[和与、]核查"],
            },
        ],
    },
    {
        "path": ["基金管理人对基金托管人的业务核查"],
        "models": [
            {
                "name": "syllabus_elt_v2",
                "inject_syllabus_features": [
                    r"__regex__基金管理人对基金托管人的业务监督[和与、]核查",
                ],
            },
        ],
    },
    {
        "path": ["基金财产保管"],
        "models": [
            {"name": "syllabus_elt_v2", "inject_syllabus_features": [r"__regex__基金财产的?保管$"]},
        ],
    },
    {
        "path": ["基金资产净值计算和会计核算"],
        "models": [
            {
                "name": "syllabus_elt_v2",
                "inject_syllabus_features": [
                    r"__regex__基金资产净值计算(.估值)?[和与](会计核算|复核)",
                ],
            },
        ],
    },
    {
        "path": ["净值精度_整段"],
        "models": [
            {
                "name": "middle_paras",
                "inject_syllabus_features": [
                    r"__regex__基金资产净值的计算[、及]复核(与完成的时间及)?程序__regex__基金资产净值是指基金资产总值减去基金负债后的价值",
                    r"__regex__基金资产净值的计算[、及]复核(与完成的时间及)?程序__regex__基金资产净值",
                    r"__regex__基金资产净值的计算[、及]复核(与完成的时间及)?程序",
                    r"基金资产净值计算和会计核算",
                    r"基金资产净值是指基金资产总值减去基金负债后的价值",
                ],
                "use_syllabus_model": True,
                "top_anchor_regs": [
                    r"^基金份额",
                    r"基金资产净值是指",
                    r"^1",
                ],
                "bottom_anchor_regs": [r"^2", r"^本基金按以下方法估值", r"^基金管理人", r"^\d[\d.]+\s?"],
            },
        ],
    },
    {
        "path": ["基金份额持有人名册的保管"],
        "models": [
            {"name": "syllabus_elt_v2"},
        ],
    },
    {
        "path": ["争议解决方式"],
        "models": [
            {"name": "syllabus_elt_v2"},
        ],
    },
    {
        "path": ["托管协议的变更、终止与基金财产的清算"],
        "models": [
            {"name": "syllabus_elt_v2", "inject_syllabus_features": [r"__regex__托管协议的变更、终止与基金财产的清算"]},
        ],
    },
    {
        "path": ["对持有人服务引入表述"],
        "models": [
            {"name": "syllabus_elt_v2", "only_before_first_chapter": True},
        ],
    },
    {
        "path": ["持有人注册登记服务"],
        "models": [
            {"name": "syllabus_elt_v2"},
        ],
    },
    {
        "path": ["持有人交易记录查询及对账单服务"],
        "models": [
            {
                "name": "syllabus_elt_v2",
                "inject_syllabus_features": [
                    r"持有人交易记录查询及对账单服务",
                    r"__regex__持有人交易记录查询及(寄送|邮寄)服务",
                ],
                "syllabus_black_list": r"基金交易确认服务",
            },
        ],
    },
    {
        "path": ["信息定制服务"],
        "models": [
            {"name": "syllabus_elt_v2"},
        ],
    },
    {
        "path": ["信息查询"],
        "models": [
            {"name": "syllabus_elt_v2"},
        ],
    },
    {
        "path": ["投诉受理"],
        "models": [
            {"name": "syllabus_elt_v2"},
        ],
    },
    {
        "path": ["服务联系方式"],
        "models": [
            {"name": "syllabus_elt_v2", "inject_syllabus_features": [r"__regex__服务联系方式"]},
        ],
    },
    {
        "path": ["招募说明书存放及查阅方式"],
        "models": [
            {"name": "syllabus_elt_v2"},
        ],
    },
    {
        "path": ["其他应披露事项"],
        "models": [
            {"name": "syllabus_elt_v2"},
        ],
    },
    {
        "path": ["基金份额类别"],
        "models": [
            {"name": "syllabus_elt_v2"},
        ],
    },
    {
        "path": ["申赎费用的其他规定"],
        "models": [
            {"name": "syllabus_elt_v2"},
        ],
    },
    {
        "path": ["份额折算定义"],
        "models": [
            {"name": "syllabus_elt_v2"},
        ],
    },
]
prophet_config = {"depends": {}, "predictor_options": predictor_options}
