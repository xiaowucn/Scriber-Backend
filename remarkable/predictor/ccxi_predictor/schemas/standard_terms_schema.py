"""标准条款"""

predictor_options = [
    {
        "path": ["资产类"],
        "models": [
            {
                "name": "syllabus_elt",
                "keep_parent": True,
                "order_by": "level",
                "reverse": True,
            },
            {
                "name": "table_kv",
            },
        ],
    },
    {
        "path": ["资产类", "基础资产"],
        "models": [
            {
                "name": "qualification_criteria",
                "para_flag": r"^基础资产$|^资产$|信贷资产|资产/基础资产|基础资产/资产|\d+\.基础资产$|“基础资产”|基础资产/",
            },
        ],
    },
    {
        "path": ["资产类", "信托财产/专项计划资产"],
        "models": [
            {
                "name": "clearance_repo",
                "keep_parent": True,
                "order_by": "level",
                "reverse": True,
                "信托财产/专项计划资产": {
                    "feature_white_list": [r"专项计划资产$"],
                },
            },
            {
                "name": "qualification_criteria",
                "para_flag": r"专项计划的?资产包括但不限于以下资产|专项计划资产由以下资产构成",
            },
        ],
    },
    {
        "path": ["资产类", "封包期利息是否入池"],
        "models": [
            {
                "name": "period_interest",
                "keep_parent": True,
                "order_by": "level",
                "reverse": True,
                "封包期利息是否入池": {
                    "feature_white_list": [r"信托财产的范围$"],
                },
            },
            # {
            #     'name': 'qualification_criteria',
            #     'para_flag': r'初始起算日|^["“]?基准日["”]?$|^["“]?封包日["”]?$|基准日/封包日|基准日（R-7工作日）|初始基准日|初始日/基准日',
            #     'invalid_flag': r'基准日.*?余额',
            # },
            # {
            #     'name': 'para_match',
            #     'paragraph_pattern': r'(?P<content>(专项计划设立后.*属于专项计划的(其他)?资产|专项计划的资产收益|管理人管理.*全部资产和收益))',
            #     'content_pattern': r'(?P<content>(专项计划设立后.*属于专项计划的(其他)?资产|专项计划的资产收益|管理人管理.*全部资产和收益))',
            # },
        ],
        "pick_answer_strategy": "all",
    },
    {
        "path": ["资产类", "合格标准"],
        "models": [
            {
                "name": "qualification_criteria",
                "para_flag": r"合格标准",
            },
        ],
    },
    {
        "path": ["资产类", "资产保证"],
        "models": [
            {
                "name": "qualification_criteria",
                "para_flag": r"资产保证",
            },
        ],
    },
    {
        "path": ["资产类", "不合格资产"],
        "models": [
            {
                "name": "qualification_criteria",
                "para_flag": r"不合格(信贷|基础|质押)?[资财]产",
                "invalid_flag": r"不合格资产赎回价格|不合格基础资产回购",
            },
        ],
    },
    {
        "path": ["资产类", "灭失资产"],
        "models": [
            {
                "name": "para_match",
                "paragraph_pattern": r'(?P<content>["“]?灭失(基础)?资产.*?[:：]?.*)',
                "content_pattern": r'(?P<content>["“]?灭失(基础)?资产.*?[:：]?.*)',
            },
        ],
    },
    {
        "path": ["资产类", "违约资产", "违约资产"],
        "models": [
            {
                "name": "qualification_criteria",
                "para_flag": r"违约资产|违约(抵押)?贷款|违约账单分期|违约(基础)?资产|不良(基础)?资产",
            },
        ],
    },
    {
        "path": ["资产类", "违约资产", "违约资产_天数定义"],
        "models": [
            {
                "name": "qualification_criteria",
                "para_flag": r"违约资产|违约(抵押)?贷款|违约账单分期|违约(基础)?资产|不良(基础)?资产",
                "content_pattern": [
                    r"(?P<dst>(超过)?【?\d+】?[日天]（不含第?【?\d+】?[日天]）)",
                    r"(?P<dst>超过([(（]含[)）])?【?\d+】?个自然日)",
                    r"(?P<dst>超过【?\d+】?(个月|天|日))",
                    r"(?P<dst>【?\d+】?个自然日内?)",
                    r"清收日期届满后(?P<dst>【?\d+】?日)仍未偿还",
                    r"(?P<dst>预期付款日后第一个.*?计算日前\d+个工作日)",
                ],
            },
        ],
    },
    {
        "path": ["资产类", "严重拖欠资产", "严重拖欠资产"],
        "models": [
            {
                "name": "qualification_criteria",
                "para_flag": r"严重拖欠(资产|抵押贷款)",
            },
        ],
    },
    {
        "path": ["资产类", "严重拖欠资产", "严重拖欠资产_天数定义"],
        "models": [
            {
                "name": "qualification_criteria",
                "para_flag": r"严重拖欠(资产|抵押贷款)",
                "content_pattern": [
                    r"(?P<dst>超过\d+[日天][\(（]不含\d+[日天][\)）](但不超过\d+[日天](（含\d+[日天]）)?)?)",
                ],
            },
        ],
    },
    {
        "path": ["日期类"],
        "models": [
            {
                "name": "table_kv",
            },
        ],
    },
    {
        "path": ["日期类", "初始起算日/基准日/封包日"],
        "models": [
            {
                "name": "qualification_criteria",
                "para_flag": r"(初始起算日|基准日|封包日)",
                "invalid_flag": r"基准日.*?余额",
                "multi": True,
            },
        ],
    },
    {
        "path": ["日期类", "计算日"],
        "models": [
            {
                "name": "para_match",
                "paragraph_pattern": r"计算日(/T日)?.*?[:：]?(?P<content>.*)",
                "content_pattern": r"计算日(/T日)?.*?[:：]?(?P<content>.*)",
            },
        ],
    },
    {
        "path": ["日期类", "归集日"],
        "models": [
            {
                "name": "qualification_criteria",
                "para_flag": r"(归集日|租金划转日|回收款归集日)",
            },
        ],
    },
    {
        "path": ["日期类", "回收款转付日"],
        "models": [
            {
                "name": "qualification_criteria",
                "para_flag": [
                    r"回收款转付日|现金流划转日|私募基金转付日|转付日[”\"].*?T-.*?日",
                    # 以下关键词由客户直接提供 https://mm.paodingai.com/cheftin/pl/zc4mjthe4jd8bq4yfa6rjhqh1a
                    r"处置收入转付日",
                    r"监管账户划款日",
                    r"债务人/共同债务人划款日",
                    r"物业运营收入划付日",
                    r"监管银行划款日",
                    r"转付日",
                    r"现金流划转日",
                ],
            },
        ],
    },
    {
        "path": ["日期类", "支付日/兑付日"],
        "models": [
            {
                "name": "qualification_criteria",
                "para_flag": r"(^支付日|兑付日|兑付兑息日|基金收益支付日)(/T 日)?",
                "multi": True,
            },
        ],
    },
    {
        "path": ["日期类", "差额支付启动日"],
        "models": [
            {
                "name": "qualification_criteria",
                "para_flag": r"(((差额支付|担保责任|流动性补足|差额补足)(启动|通知)日)|物业运营方补足义务启动日)",
            },
        ],
    },
    {
        "path": ["日期类", "差额支付划款日"],
        "models": [
            {
                "name": "para_match",
                "paragraph_pattern": r'(?P<content>["“]?(差额(支付|补足).*?日|保证人划款日|物业运营方支付日|(差额支付|流动性补足)承诺人划款日).*?[:：]?.*)',
                "content_pattern": r'(?P<content>["“]?(差额(支付|补足).*?日|保证人划款日|物业运营方支付日|(差额支付|流动性补足)承诺人划款日).*?[:：]?.*)',
                "multi": True,
            },
        ],
    },
    {
        "path": ["归集划付类"],
        "models": [
            {
                "name": "table_kv",
            },
        ],
    },
    {
        "path": ["归集划付类", "归集转付频率（事件前）"],
        "fake_leaf": True,
        "models": [
            {
                "name": "collection_payment_for_standard",
                "para_flag": r"回收款转付日|回收款归集日|现金流划转日|私募基金转付日|“转付日",
                "paragraph_pattern": [
                    r"(?P<dst>应为专项计划存续期间内的每个工作日)",
                    r"(?P<dst>回收款转付日为每个(计算日起|兑付日前|应收账款回收计算日后)的?第.*?个工作日([（(].*?日】?[）)])?)",
                    r"(?P<dst>(为|即)(回收款计算日|回收款归集日)之?(后的第.*?个工作日|当日))",
                    r"(?P<dst>(系指)?专项计划存续期间内每个兑付日前的第.*?个工作日(\(.*?日\))?)",
                    r"(?P<dst>为“?兑付日”?前的第.*?个“工作日.*?的任意一日)",
                    r'(?P<dst>(“?回收款转付日"?)?为每个“?兑付日”?前的第.*?工作日.*?日)',
                    r"(?P<dst>为(每个)?(回收款|收入)归集日(之后的第.*?个工作日|当日|后的第.*?日))",
                    r"(?P<dst>为“?专项计划设立日.*?起每届满.*?的对应日的前一个“?工作日”?)",
                    r"(?P<dst>则第一个专项计划收款日为专项计划设立日后.*?个交易日.*?其余专项计划收款日为该次分配兑付日前的第.*?个交易日)",
                    r"(?P<dst>专项计划收款日应在该次分配之兑付日前的第.*?个交易日（.*?交易日）)",
                    r"(?P<dst>兑付日.*?前第.*?工作日.*?即.*?工作日)",
                    r"专项计划账户.*(?P<dst>为第.*?工作日.*?即.*?工作日)",
                    r"(?P<dst>普通分配中的T-.*?(即A\+.*?)日)",
                    r"(?P<dst>(后续现金流划转日)?(为|即)?(每个|每个循环购买日|后续循环购买日).*?兑付日前的第.*?日[\(（].*[\)）])",
                    r"(?P<dst>“?资产服务机构.*?回收款转付日.*?兑付日.*?工作日”?)",
                    r"(?P<dst>回收款转付日为每个计算日后的?第.*?个工作日.*?晚于当期.*?兑息日.*?日([（(].*?日】?[）)])?)",
                ],
                "multi": True,
            },
        ],
    },
    {
        "path": ["归集划付类", "归集转付频率（事件后）"],
        "fake_leaf": True,
        "models": [
            {
                "name": "collection_payment_for_standard",
                "para_flag": r"回收款转付日|回收款归集日|私募基金转付日|“转付日",
                "paragraph_pattern": [
                    r"(?P<dst>专项计划终止后的回收款转付日为终止事由发生后的.*?个工作日)",
                    r"(?P<dst>回收款转付日.*?收到每笔.*?回收款”?后的第.*?个“?工作日)",
                    r"(?P<dst>“?回收款转付日.*?(中孰早的一个).*?工作日\"?(\(.*?日\))?)",
                    r"(?P<dst>资产服务机构.*?直接支付至专项计划账户)",
                    r"“?资产服务机构”?仍收到“?回收款”?.*?(?P<dst>为“?计算日”后的第.*?工作日.*?的任意一日)",
                    r"(?P<dst>应为自“加速清偿事件.*?加速清偿初始核算日.*工作日”?)",
                    r"(?P<dst>回收款转付日为前述事件发生后第.*?个工作日和前述事件发生之日的每个自然月的对应日后第.*?个工作日)",
                    r"专项计划账户.*?(?P<dst>为.*?基准日”?后第.*?个工作日)",
                    r"(?P<dst>系指专项计划提前终止事件发生之日后第.*?个工作日)",
                    r"(?P<dst>系指加速清偿事件发生之日起每个自然月的倒数第.*?个工作日)",
                    r"(?P<dst>回收款转付日为每个月的最后一个自然日)",
                    r"(?P<dst>在处分分配中，仅在被处置的特定资产为项目公司股权和股东借款债权、或者物业资产的情况下，为.*?日)",
                    r"(?P<dst>(为每个收入归集日|即回收款计算日)后的第.*?个工作日)",
                    r"(?P<dst>回收款转付日.*?长期信用等级.*?后的第.*?个工作日)",
                    r"(?P<dst>在处分分配中.*?仅在被处置的.*?物业资产的情况下.*?日)",
                ],
                "multi": True,
            },
        ],
    },
    {
        "path": ["归集划付类", "支付频率"],
        "fake_leaf": True,
        "models": [
            {
                "name": "collection_payment_for_standard",
                "para_flag": r"支付日|(本息)?兑付日|兑付兑息日",
                "paragraph_pattern": [
                    r"兑付日/T日.*?[:：].*?(?P<dst>(指|即).*日)",
                    r"专项计划存续期间内.*?(?P<dst>兑付兑息日为每个自然年度的.*日)",
                    r"(?P<dst>专项计划在循环期.*?兑付日.*?提前分配基准日后第.*?日\(.*?工作日\))",
                    r"(?P<dst>“?专项计划.*?兑付日.*?基准日.*?后的.*?工作日”)",
                    r"(?P<dst>应为“初始核算日”后的第.*?工作日”?)",
                    r"(?P<dst>专项计划存续期间内.*?每年.*?月.*?日)",
                    r"(?P<dst>系指“预期到期日”当日|各预期到期日|系指每个基金收益核算日当日)",
                    r"(?P<dst>兑付兑息日为清算小组制定的清算方案中的指定日期以及计划管理人完成专项计划清算之日的后五个工作日内的任一工作日)",
                    r"(?P<dst>在专项计划终止日之后，为管理人根据清算方案确定的专项计划资产清算分配之日)",
                    r"兑付日.*?(?P<dst>系?指每年.*日)",
                    r"兑付日/?\(?[RT]日\)?.*?[:：].*?(?P<dst>(指|即).*日)",
                    r"(?P<dst>本专项计划兑付日为.*?日)",
                    r"(?P<dst>为回收款计算日后的第.*?个工作日)",
                    r"(?P<dst>专项计划存续期间每年.*(对应|】)日)",
                    r"(?P<dst>分配基准日.*?个工作日[\(（].*?日[\)）])",
                    r"场外分配而言.*?(?P<dst>系?指每年.*?日)",
                    r"(?P<dst>(本专项计划付息日|专项计划设立日).*日)",
                ],
                "invalid_paragraph_pattern": [
                    r"((普通|处分|清算|终止)分配|计息年度)兑付日.*?[:：]",
                ],
                "multi": True,
            },
        ],
    },
    {
        "path": ["归集划付类", "账户划付设置"],
        "models": [
            {
                "name": "syllabus_elt",
                "keep_parent": True,
                "order_by": "level",
                "reverse": True,
            },
        ],
    },
    {
        "path": ["现金流类"],
        "models": [
            {
                "name": "cash_flow",
                "keep_parent": True,
                "order_by": "level",
                "reverse": True,
                "include_title": True,
                "违约事件发生前的回收款分配（不分账）": {
                    "feature_white_list": [
                        r"专项计划的分配顺序$",
                        r"专项计划资产的分配|分配顺序$",
                    ],
                },
                "违约事件发生后的回收款分配": {
                    "feature_white_list": [
                        r"__regex__(?<!未)发生违约事件情况下的资产收益分配顺序",
                        r"专项计划的分配顺序$",
                    ],
                },
            },
        ],
    },
    {
        "path": ["账户类"],
        "models": [
            {
                "name": "table_kv",
            },
        ],
    },
    {
        "path": ["账户类", "收款账户/回收款账户"],
        "models": [
            {
                "name": "qualification_criteria",
                "para_flag": r"收款账户|归集账户$",
                "invalid_flag": r"信托|募集资金",
                "multi": True,
            },
        ],
    },
    {
        "path": ["账户类", "监管账户"],
        "models": [
            {
                "name": "qualification_criteria",
                "para_flag": r"监管账户",
            },
        ],
    },
    {
        "path": ["账户类", "发行收入缴款账户/募集资金账户"],
        "models": [
            {
                "name": "qualification_criteria",
                "para_flag": r"发行收入缴款[账专]户|募集资金(收款|专用)?[账专]户|募集(专用)?[账专]户|(专项)?计划募集[账专]户|计划推广专户",
                "multi": True,
            },
        ],
    },
    {
        "path": ["账户类", "信托账户/专项计划账户"],
        "models": [
            {
                "name": "qualification_criteria",
                "para_flag": r'^["“]?(信托账户|专项计划账户|信托(财产|保管)?专户|支持计划账户|专项计划账户/托管账户)["”]?$',
                "invalid_flag": r"单一资金信托账户",
                "multi": True,
            },
        ],
    },
    {
        "path": ["账户类", "本金分账户/科目"],
        "models": [
            {
                "name": "para_match",
                "paragraph_pattern": r"(本金账|本金分账户|本金科目).*?[:：]?(?P<content>.*)",
                "content_pattern": r"(本金账|本金分账户|本金科目).*?[:：]?(?P<content>.*)",
            },
        ],
    },
    {
        "path": ["账户类", "收入分账户/科目"],
        "models": [
            {
                "name": "para_match",
                "paragraph_pattern": r"(收益账|收入分账户|收入科目).*?[:：]?(?P<content>.*)",
                "content_pattern": r"(收益账|收入分账户|收入科目).*?[:：]?(?P<content>.*)",
            },
        ],
    },
    {
        "path": ["账户类", "储备金分账户/科目"],
        "models": [
            {
                "name": "para_match",
                "paragraph_pattern": r"(储备金科目).*?[:：]?(?P<content>.*)",
                "content_pattern": r"(储备金科目).*?[:：]?(?P<content>.*)",
                "multi_elements": True,
            },
        ],
    },
    {
        "path": ["账户类", "保证金分账户/科目"],
        "models": [
            {
                "name": "para_match",
                "paragraph_pattern": r"(保证金[子分]?账户?|备付保障金科目|保证金科目).*?[:：]?(?P<content>.*)",
                "content_pattern": r"(保证金[子分]?账户?|备付保障金科目|保证金科目).*?[:：]?(?P<content>.*)",
            },
        ],
    },
    {
        "path": ["账户类", "差额补足分账户"],
        "models": [
            {
                "name": "para_match",
                "paragraph_pattern": r"(差额补足分账户).*?[:：]?(?P<content>.*)",
                "content_pattern": r"(差额补足分账户).*?[:：]?(?P<content>.*)",
            },
        ],
    },
    {
        "path": ["事件类"],
        "models": [
            {
                "name": "table_kv",
            },
        ],
    },
    {
        "path": ["事件类", "加速清偿事件"],
        "models": [
            {
                "name": "qualification_criteria",
                "para_flag": r"加速清偿事件",
            },
        ],
    },
    {
        "path": ["事件类", "违约事件"],
        "models": [
            {
                "name": "qualification_criteria",
                "para_flag": r"违约事件",
            },
        ],
    },
    {
        "path": ["事件类", "预期到期日事件"],
        "models": [
            {
                "name": "sub_chief_member",
                "para_flag": r"加速清偿事件|违约事件",
                "paragraph_pattern": [
                    r"(?P<dst>在.*?预期到期日.*?[规约]定.*?未偿本金余额)",
                    r"(?P<dst>(信托账户内可供分配资金|受托人”?)?在.*?预期到期日.*?本金(余额)?的?)",
                    r"(?P<dst>按照.*?[规约]定.*?未偿本金余额)",
                    r"(?P<dst>本信托优先级资产支持票据预计到期日.*?应付未付的优先级资产支持票据的本金或利息未获足额分配.*?该日发生违约事件)",
                    r"(?P<dst>在未发生加速清偿事件的情形下.*?足额支付优先级资产支持票据或次优先级资产支持票据应付未付本金的)",
                    r"(?P<dst>截至任一档优先级资产支持证券的预期到期日.*?该档优先级资产支持证券的预期收益.*?本金仍未兑付完毕)",
                    r"(?P<dst>截至任何一个预期到期日.*?不足以偿付.*?应付本金.*支付承诺人划款日补足差额资金)",
                ],
                "multi": True,
            },
        ],
    },
    {
        "path": ["事件类", "利息支付事件"],
        "models": [
            {
                "name": "sub_chief_member",
                "para_flag": r"违约事件|加速清偿事件",
                "paragraph_pattern": [
                    r"(?P<dst>资产支持证券预期支付额未能在兑付日.*?得到足额支付)",
                    r"(?P<dst>.*兑付(兑息)?日.*?(不足以(支付|偿还)|无法支付|足额分配).*?(预期收益|专项计划费用|全部或部分本金).*)",
                    r"(?P<dst>.*(差额支付划款日|计划管理人报告日|专项计划账户内可供分配的资金不足以).*?(预期收益|专项计划费用|全部或部分本金|所需资金).*)",
                ],
                "multi": True,
            },
        ],
    },
    {
        "path": ["事件类", "法定到期日事件"],
        "models": [
            {
                "name": "sub_chief_member",
                "para_flag": r"违约事件|加速清偿事件",
                "paragraph_pattern": r"(?P<dst>在.*?法定到期日.*?后.*)",
            },
        ],
    },
    {
        "path": ["事件类", "权利完善事件"],
        "models": [
            {
                "name": "qualification_criteria",
                "para_flag": r"权利完善事件",
            },
        ],
    },
    {
        "path": ["事件类", "个别通知事件"],
        "models": [
            {
                "name": "qualification_criteria",
                "para_flag": r"个别通知事件",
            },
        ],
    },
    {
        "path": ["事件类", "提前终止事件"],
        "models": [
            {
                "name": "qualification_criteria",
                "para_flag": r"提前终止事件|发行载体终止事件|资产支持票据提前到期|资产支持票据终止事件|贷款提前到期事件",
            },
        ],
    },
    {
        "path": ["事件类", "储备金划付事件"],
        "models": [
            {
                "name": "qualification_criteria",
                "para_flag": r"储备金划付事件",
            },
        ],
    },
    {
        "path": ["事件类", "运营净收入下跌事件/现金流不足事件 "],
        "models": [
            {
                "name": "qualification_criteria",
                "para_flag": r"运营净收入下跌事件|现金流不足事件",
            },
        ],
    },
    {
        "path": ["事件类", "评估值下降事件"],
        "models": [
            {
                "name": "qualification_criteria",
                "para_flag": r"评估值下降事件",
            },
        ],
    },
    {
        "path": ["事件类", "评级下调事件"],
        "models": [
            {
                "name": "qualification_criteria",
                "para_flag": r"(?<!发生)评级下调事件",
            },
        ],
    },
    {
        "path": ["事件类", "差额支付启动事件/担保启动事件"],
        "models": [
            {
                "name": "qualification_criteria",
                "para_flag": r"差额(补足|支付)(启动|生效)?事件|流动性(支持|补足)启动事件|担保责任(启动)?事件|(保证|物权)?担保启动事件|流动性支持触发事件",
                "multi": True,
            },
        ],
    },
    {
        "path": ["事件类", "基础资产赎回事件"],
        "models": [
            {
                "name": "qualification_criteria",
                "para_flag": r"基础资产赎回事件|一般赎回事件|差额赎回事件|特殊赎回事件",
            },
        ],
    },
    {
        "path": ["循环购买类"],
        "models": [
            {
                "name": "table_kv",
            },
        ],
    },
    {
        "path": ["循环购买类", "循环购买资产"],
        "models": [
            {
                "name": "revolving_purchase_assets",
                "para_flag": r"后续入池基础资产|基础资产[”\"]?$|^资产$",
                "special_keyword": [r"循环期|循环购买|持续购买|附件.*?所列的合格资产标准"],
            },
        ],
    },
    {
        "path": ["循环购买类", "循环购买资产合格标准"],
        "models": [
            {
                "name": "qualification_criteria",
                "para_flag": r'^合格标准$|合格标准/合格资产标准|基础资产合格标准|["“]合格标准["”]',
                "special_keyword": [r"循环购买|持续购买|附件.*?所列的合格资产标准"],
            },
        ],
    },
    {
        "path": ["循环购买类", "初始折价率"],
        "models": [
            {
                "name": "sub_chief_member",
                "para_flag": r"折价率|应收账款折价率|资产计算参数",
                "paragraph_pattern": [
                    r"(初始折算比例|应收账款折价率|资产计算参数)=(?P<dst>.*?%)",
                    r"(初始折算比例|应收账款折价率|资产计算参数)[：:](?P<dst>.*)",
                ],
            },
            {
                "name": "qualification_criteria",
                "para_flag": r"初始折价比例|初始折算比例|资产计算参数",
            },
        ],
    },
    {
        "path": ["循环购买类", "循环购买折价方法"],
        "models": [
            {
                "name": "qualification_criteria",
                "para_flag": r"折价比例|^折算比例|折价率|资产折价率[”\"]?$|应收账款折现率|电价补贴收益折现率",
            },
        ],
    },
    {
        "path": ["循环购买类", "循环购买日"],
        "models": [
            {
                "name": "qualification_criteria",
                "para_flag": r"(持续|循环)购买日(（(S|T-1)日）)?|循环购买执行日",
            },
        ],
    },
    {
        "path": ["循环购买类", "循环购买期"],
        "models": [
            {
                "name": "qualification_criteria",
                "para_flag": r"持续购买期|循环期[”\"]?$|循环购买期",
            },
        ],
    },
    {
        "path": ["循环购买类", "提前摊还事件"],
        "models": [
            {
                "name": "qualification_criteria",
                "para_flag": r"提前摊还事件|提前结束循环(购买|循环)?期事件",
            },
        ],
    },
    {
        "path": ["循环购买类", "循环购买不足事件", "循环购买不足事件"],
        "models": [
            {
                "name": "sub_chief_member",
                "para_flag": r"提前结束循环购买期事件|提前摊还事件|加速清偿事件”?$|^循环购买$",
                "paragraph_pattern": [
                    r"(?P<dst>持续购买日.*?余额超过.*?未偿本金余额)",
                    r"(?P<dst>在(专项计划存续|整个循环购买)期.*?循环购买.*?超过(专项计划募集资金|资产池中未偿价款余额).*)",
                    r"(?P<dst>除.*?另有约定外.*?循环购买.*?低于当期专项计划账户内可用于循环购买的资金金额.*)",
                    r"(?P<dst>在任意一次循环购买时.*?循环购买.*?应收账款余额的比例超过.*)",
                    r"(?P<dst>.*循环期.*?资产池.*?未达到.*?[金余]额.*)",
                    r"(?P<dst>循环期内.*?累计两次实际完成循环购买的资金金额达不到当期可用于循环购买资金金额的.*?%)",
                    r"(?P<dst>除《标准条款》另有约定外.*?约定足额提供用以循环购买的基础资产.*?未能足额购买新增基础资产或者计划管理人在某一个循环购买日拟用于循环购买的资金金额低于当期专项计划账户内可用于循环购买的资金金额的.*?%的)",
                ],
                "multi": True,
            },
        ],
    },
    {
        "path": ["循环购买类", "循环购买不足事件", "阈值_循环购买率"],
        "models": [
            {
                "name": "sub_chief_member",
                "para_flag": r"提前结束循环购买期事件|提前摊还事件|加速清偿事件”?$|^循环购买$",
                "paragraph_pattern": [
                    r"(?P<dst>持续购买日.*?余额超过.*?未偿本金余额)",
                    r"(?P<dst>在(专项计划存续|整个循环购买)期.*?循环购买.*?超过(专项计划募集资金|资产池中未偿价款余额).*)",
                    r"(?P<dst>除.*?另有约定外.*?循环购买.*?低于当期专项计划账户内可用于循环购买的资金金额.*)",
                    r"(?P<dst>在任意一次循环购买时.*?循环购买.*?应收账款余额的比例超过.*)",
                    r"(?P<dst>.*循环期.*?资产池.*?未达到.*?[金余]额.*)",
                    r"(?P<dst>循环期内.*?累计两次实际完成循环购买的资金金额达不到当期可用于循环购买资金金额的.*?%)",
                    r"(?P<dst>除《标准条款》另有约定外.*?约定足额提供用以循环购买的基础资产.*?未能足额购买新增基础资产或者计划管理人在某一个循环购买日拟用于循环购买的资金金额低于当期专项计划账户内可用于循环购买的资金金额的.*?%的)",
                ],
                "multi": True,
            },
        ],
    },
    {
        "path": ["其他类"],
        "models": [
            {
                "name": "syllabus_elt",
                "keep_parent": True,
                "order_by": "level",
                "reverse": True,
            },
        ],
    },
    {
        "path": ["其他类", "不合格基础资产赎回"],
        "models": [
            {
                "name": "qualification_criteria",
                "para_flag": r'^["“]?赎回["”]?$|不合格(基础)?资产赎回$|["“]置换["”]',
                "multi": True,
            },
            {
                "name": "para_match",
                "paragraph_pattern": r"(?P<content>(专项计划存续期间|在清仓回购条件成就的前提下).*(赎回该笔不合格基础资产|不合格基础资产不再属于专项计划资产|享有向管理人申请清仓回购的权利))",
            },
        ],
    },
    {
        "path": ["其他类", "特定基础资产赎回/置换"],
        "models": [
            {
                "name": "para_match",
                "paragraph_pattern": r"(赎回|置换|回转)[:：](?P<content>.*(灭失基础资产|不良基础资产|涉诉基础资产|违约基础资产|风险基础资产).*)",
                "content_pattern": r"(赎回|置换|回转)[:：](?P<content>.*(灭失基础资产|不良基础资产|涉诉基础资产|违约基础资产|风险基础资产).*)",
                "multi_elements": True,
            },
        ],
    },
    {
        "path": ["其他类", "清仓回购"],
        "models": [
            {
                "name": "clearance_repo",
                "keep_parent": True,
                "order_by": "level",
                "reverse": True,
                "neglect_patterns": [
                    r"其他定义",
                ],
                "add_para_pattern": [
                    r"满足本合同第(?P<dst>([\d.]+))[条款]约定的条件的情况下",
                ],
                "清仓回购": {
                    "feature_white_list": [r"\d+清仓回购$"],
                },
                # 'multi': True,
            },
            {
                "name": "qualification_criteria",
                "para_flag": r"清仓回购$",
            },
        ],
    },
    {
        "path": ["监测指标定义及阈值类"],
        "models": [
            {
                "name": "monitor_indicator_for_standard",
            },
        ],
    },
    {
        "path": ["监测指标定义及阈值类", "监测指标定义_累计违约率"],
        "models": [
            {
                "name": "qualification_criteria",
                "para_flag": r"累计违约率|当期违约率",
            },
        ],
    },
    {
        "path": ["监测指标定义及阈值类", "阈值_累计违约率阈值"],
        "models": [
            {
                "name": "sub_chief_member",
                "para_flag": r"加速清偿事件|循环期提前结束事件|专项计划提前终止事件|提前终止事件",
                "paragraph_pattern": [
                    r"(?P<dst>(在专项计划存续期间?内，?)?(某|任)一(应收账款|租金|工程尾款)?.*?(回收)?累计违约率(达到|超过).*?%(及以上)?)",
                    r"(?P<dst>当专项计划基础资产的累计违约率超过.*?%)",
                    r"(?P<dst>在“?专项计划存续期间”?内第1年连续.*?第二年.*?第三年.*)",
                    r"(?P<dst>在“?专项计划存续期间”?内连续.*?日.*?超过.*(及以上)?)",
                    r"(?P<dst>在“?专项计划存续期间”?.*?某月最后一日.*?达到.*(及以上)?)",
                    r"(?P<dst>累计基础资产不良率超过.*?%([（(]不含.*】?[）)])?)",
                    r"(?P<dst>累计基础资产不良率超过.*|一旦发生累计基础资产不良率大于.*?的情况|当累计基础资产不良率超过.*?时|累计基础资产不良率未能在.*?周内恢复至.*?以下的)",
                    r"(?P<dst>任一.*?(租金)?回收期间.*?结束时的.*?累计违约率.*)",
                    r"(?P<dst>并自发现累计基础资产不良率大于.*?%之日起每周向计划管理人提供累计基础资产不良率情况)",
                    r"(?P<dst>(直至|如)累计基础资产不良率.*?恢复至7%以下)",
                    r"(?P<dst>在未发生违约事件和加速清偿事件的情况下.*?违约率不超过.*?情况下?)",
                    r"(?P<dst>若该兑付日为循环期内的兑付日.*?违约率不超过.*收益)",
                ],
                "neglect_patterns": [r"受托人解任事件：系指以下任一事件："],
                "multi": True,
            },
        ],
    },
    {
        "path": ["监测指标定义及阈值类", "监测指标定义_严重拖欠率"],
        "models": [
            {
                "name": "qualification_criteria",
                "para_flag": r"严重拖欠率",
            },
        ],
    },
    {
        "path": ["监测指标定义及阈值类", "阈值_严重拖欠率阈值"],
        "models": [
            {
                "name": "sub_chief_member",
                "para_flag": r"加速清偿事件",
                "paragraph_pattern": r"(?P<dst>连续.*?收款期间.*?平均“严重拖欠率”.*)",
            },
        ],
    },
    {
        "path": ["监测指标定义及阈值类", "阈值_差额支付启动次数"],
        "models": [
            {
                "name": "sub_chief_member",
                "para_flag": r"加速清偿事件|提前终止事件",
                "paragraph_pattern": [
                    r"(?P<dst>累计发生两次差额支付生效事件[（(]含担保责任启动事件[）)])",
                    r"(?P<dst>专项计划存续期间累计发生.*?次差额支付生效事件[（(]含担保责任启动事件[）)])",
                    r"(?P<dst>启动差额支付事件累计超过.*?次[（(]不含.*?次[）)])",
                ],
                "multi": True,
            },
        ],
    },
    {
        "path": ["监测指标定义及阈值类", "阈值_现金流不足次数"],
        "models": [
            {
                "name": "sub_chief_member",
                "para_flag": r"资产支持票据终止事件",
                "paragraph_pattern": r"(?P<dst>自基准日起，连续发生.*?次实际质押物业费收入低于.*?支持票据提前终止的)",
            },
        ],
    },
]

prophet_config = {
    "depends": {},
    "predictor_options": predictor_options,
}
