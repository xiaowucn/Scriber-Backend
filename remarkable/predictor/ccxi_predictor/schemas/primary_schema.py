"""主定义表"""

predictor_options = [
    {
        "path": ["资产类"],
        "models": [
            {
                "name": "syllabus_elt",
                "keep_parent": True,
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
                "para_flag": r"^基础资产$|^资产$|^信贷资产$|资产/基础资产|基础资产/资产|\d+\.基础资产$",
            },
        ],
    },
    {
        "path": ["资产类", "合格标准"],
        "models": [
            {
                "name": "qualification_criteria",
                "para_flag": r"合格标准|质押标准",
                "invalid_flag": [r"受托(人|机构)合格标准"],
            },
        ],
    },
    {
        "path": ["资产类", "灭失资产"],
        "models": [
            {
                "name": "para_match",
                "paragraph_pattern": r"灭失资产.*?[:：]?(?P<content>.*)",
                "content_pattern": r"灭失资产.*?[:：]?(?P<content>.*)",
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
                    r"(?P<dst>(超过)?【?\d+】?[日天][\(（]不含第?【?\d+】?[日天][）\)])",
                    r"(?P<dst>超过（含）【?\d+】?个自然日)",
                    r"(?P<dst>超过【?\d+】?个月)",
                    r"清收日期届满后(?P<dst>【?\d+】?日)仍未偿还",
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
        "path": ["资产类", "不合格资产"],
        "models": [
            {
                "name": "qualification_criteria",
                "para_flag": r"不合格(信贷|基础|质押)?[资财]产",
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
                "name": "para_match",
                "paragraph_pattern": r"(初始起算日|基准日|封包日).*?[:：]?(?P<content>.*)",
                "content_pattern": r"(初始起算日|基准日|封包日).*?[:：]?(?P<content>.*)",
            },
        ],
    },
    {
        "path": ["日期类", "计算日"],
        "models": [
            {
                "name": "qualification_criteria",
                "para_flag": r"计算日",
            },
        ],
    },
    {
        "path": ["日期类", "归集日"],
        "models": [
            {
                "name": "para_match",
                "paragraph_pattern": r"(归集日|租金划转日).*?[:：]?(?P<content>.*)",
                "content_pattern": r"(归集日|租金划转日).*?[:：]?(?P<content>.*)",
            },
        ],
    },
    {
        "path": ["日期类", "回收款转付日"],
        "models": [
            {
                "name": "qualification_criteria",
                "para_flag": [
                    r"回收款转付日|处置收入转付日|回收款划转日|监管账户划款日",
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
                "para_flag": r"(^支付日|兑付日|兑付兑息日|基金收益支付日)(/?T\s?日)?",
                "multi": True,
            },
        ],
    },
    {
        "path": ["日期类", "核算日/信托利益核算日"],
        "models": [
            {
                "name": "para_match",
                "paragraph_pattern": r"(核算日|信托利益核算日).*?[:：]?(?P<content>.*)",
                "content_pattern": r"(核算日|信托利益核算日).*?[:：]?(?P<content>.*)",
            },
        ],
    },
    {
        "path": ["日期类", "差额支付划款日"],
        "models": [
            {
                "name": "para_match",
                "paragraph_pattern": r"(差额支付.*?划款日|差额补足划款日|保证人划款日).*?[:：]?(?P<content>.*)",
                "content_pattern": r"(差额支付.*?划款日|差额补足划款日|保证人划款日).*?[:：]?(?P<content>.*)",
                "multi": True,
            },
        ],
    },
    {
        "path": ["日期类", "差额支付启动日"],
        "models": [
            {
                "name": "para_match",
                "paragraph_pattern": r"(差额(补足|支付)(启动|通知)日).*?[:：]?(?P<content>.*)",
                "content_pattern": r"(差额(补足|支付)(启动|通知)日).*?[:：]?(?P<content>.*)",
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
                "name": "collection_payment",
                "para_flag": r"回收款转付日|回收款归集日",
                "paragraph_pattern": [
                    r"(?P<dst>“?回收款转付日”?为.*?工作日”?，但应不晚于.*?工作日)",
                    r"(?P<dst>“?回收款转付日”?为每个.*?[后前]的?第.*?个“?工作日”?)",
                    r"(?P<dst>具体指贷款服务机构.*?回收款后的当日.*?不超过.*?日)",
                    r"(?P<dst>回收款转付日为信托生效日之后每个支付日.*?工作日和信托终止日)",
                    r"(?P<dst>系指“资产服务机构”将“回收款”转付到“信托账户”之日.*?日)",
                    r"(?P<dst>回收款归集日为每个支付日前的第.*?个工作日.*?日)",
                    r"(?P<dst>内回收款转付日.*?个自然月.*?日)",
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
                "name": "collection_payment",
                "para_flag": r"回收款转付日|回收款归集日",
                "paragraph_pattern": [
                    r"(?P<dst>则?“?回收款转付日.*?回收款.*?后.*?工作日”)",
                    r"(?P<dst>资产服务机构”?应.*?后.*?工作日.*?信托[账专]户)",
                    r"(?P<dst>后续回收款转付日为首个回收款转付日后每个自然月的对应日)",
                    r"(?P<dst>回收款归集日为.*?个工作日、调整当月起.*?个工作日)",
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
                "name": "collection_payment",
                "para_flag": r"支付日|(本息)?兑付日",
                "paragraph_pattern": [
                    r"支付日[:：]?(?P<dst>系指.*?日)",
                    r"支付日[:：]?(?P<dst>为自.*?满.*?对应日)",
                    r"支付日(（T日）).*?[:：](?P<dst>系指.*?日)",
                    r"(本息)?兑付日.*?[:：].*?(?P<dst>系指.*)",
                    r"(?P<dst>后续支付日为每个回收款转付日后第.*?个工作日)",
                    r"(?P<dst>系指信托设立后每个应收账款回收计算日次月的.*?日)",
                    r"(?P<dst>系指“回收款归集日”后第.*?个工作日)",
                    r"(?P<dst>系指“预期到期日”当日)",
                    r"(?P<dst>信托终止日后的第五个工作日)",
                    r"(?P<dst>资产支持票据的预计到期日；)",
                ],
                "invalid_paragraph_pattern": [
                    r"((普通|处分|清算|终止|期间)分配|计息年度)兑付日.*?[:：]",
                ],
                "multi": True,
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
                "para_flag": r"发行收入缴款账户|募集资金(收款)?账户|募集专用账户",
                "multi": True,
            },
        ],
    },
    {
        "path": ["账户类", "收款账户/回收款账户"],
        "models": [
            {
                "name": "qualification_criteria",
                "para_flag": r"收款账户",
                "invalid_flag": r"信托|募集资金",
                "multi": True,
            },
        ],
    },
    {
        "path": ["账户类", "信托账户/专项计划账户"],
        "models": [
            {
                "name": "qualification_criteria",
                "para_flag": r"信托账户|专项计划账户|信托(财产|保管)?专户",
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
                "paragraph_pattern": r"(本金账|本金分账户).*?[:：]?(?P<content>.*)",
                "content_pattern": r"(本金账|本金分账户).*?[:：]?(?P<content>.*)",
            },
        ],
    },
    {
        "path": ["账户类", "收入分账户/科目"],
        "models": [
            {
                "name": "para_match",
                "paragraph_pattern": r"(收益账|收(入|益)分账户).*?[:：]?(?P<content>.*)",
                "content_pattern": r"(收益账|收(入|益)分账户).*?[:：]?(?P<content>.*)",
            },
        ],
    },
    {
        "path": ["账户类", "储备金分账户/科目"],
        "models": [
            {
                "name": "qualification_criteria",
                "para_flag": r"(服务转移和通知准备金账|信托.*?储备账户?|流动性储备金账|赎回准备金科目)",
                "multi": True,
            },
        ],
    },
    {
        "path": ["账户类", "保证金分账户/科目"],
        "models": [
            {
                "name": "qualification_criteria",
                "para_flag": r"(保证金分?账户?|备付保(障|证)金科目)",
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
                    r"(?P<dst>本信托优先级资产支持票据预计到期日，本信托项下应付未付的优先级资产支持票据的本金或利息未获足额分配时，则于该日发生违约事件)",
                    r"(?P<dst>在未发生加速清偿事件的情形下.*?足额支付优先级资产支持票据或次优先级资产支持票据应付未付本金的)",
                    r"(?P<dst>(截至|在).*预期到期日.*支付完毕.*应付本金余额)",
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
                "para_flag": r"加速清偿事件|违约事件",
                "paragraph_pattern": [
                    r"(?P<dst>在.*?支付日.*?后.*)",
                    r"(?P<dst>受托人.*?在本息兑付日后.*?内.*?应付未付利息的)",
                    r"(?P<dst>本信托项下任一支付日当日.*?本信托项.*?该支付日发生违约事件)",
                    r"(?P<dst>“信托账户.*?支付日.*?足额支付.*?应付未付利息及本金及相关税收、费用和报酬的)",
                    r"(?P<dst>信托账户内可供分配资金.*?兑付日不能足额支付当期应分配的优先级资产支持票据的应付预期收益或本金.*?的)",
                    r"(?P<dst>在未发生加速清偿事件的情形下.*?足额支付优先级资产支持票据或次优先级资产支持票据应付未付(利息|本金)的)",
                    r"(?P<dst>在发生加速清偿事件的情形下.*?足额支付次优先级资产支持票据应付未付(利息|本金).*?的)",
                    r"(?P<dst>信托账户内可供分配资金在兑付日不能足额支付当期应分配的优先级资产支持票据的未付预期收益或本金的)",
                    r"(?P<dst>“.*?未能在.*?工作日.*?足额支付.*?应付未付利息的)",
                    r"(?P<dst>“差额支付承诺人.*?不足以支付相应的.*?的预期收益和/或本金的)",
                    r"(?P<dst>截至.*?支付日.*?资金不足以.*?应付的.*?的预期收益)",
                    r"(?P<dst>在信托终止日.*?支付日.*?信托资金不足.*?分配顺序在相应支付日得到足额偿付的.*?）)",
                    r"(?P<dst>在差额支付启动事件发生后的任何一个差额支付划款日.*?信托账户内可供分配的资金不足.*?预期收益和/或本金)",
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
                "para_flag": r"违约事件",
                "paragraph_pattern": [
                    r"(?P<dst>.*在.*?法定(最终)?到期日.*?后.*)",
                    r"(?P<dst>信托账户内可供分配资金在.*?法定(最终)?到期日.*)",
                ],
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
        "path": ["事件类", "权利完善事件"],
        "models": [
            {
                "name": "qualification_criteria",
                "para_flag": r"权利完善事件",
            },
        ],
    },
    {
        "path": ["事件类", "差额支付启动事件/担保启动事件"],
        "models": [
            {
                "name": "qualification_criteria",
                "para_flag": r"差额(补足|支付)启动事件|流动性支持(启动|触发)事件|(保证|物权)担保启动事件",
                "multi": True,
            },
        ],
    },
    {
        "path": ["事件类", "基础资产赎回事件"],
        "models": [
            {
                "name": "qualification_criteria",
                "para_flag": r"一般赎回事件|差额赎回事件|特殊赎回事件",
                "multi": True,
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
        "path": ["事件类", "评级下调事件"],
        "models": [
            {
                "name": "qualification_criteria",
                "para_flag": r"评级下调事件",
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
                "para_flag": r"后续入池基础资产|基础资产|^资产$",
                "special_keyword": [r"循环购买|持续购买|附件.*?所列的合格资产标准"],
            },
        ],
    },
    {
        "path": ["循环购买类", "循环购买资产合格标准"],
        "models": [
            {
                "name": "qualification_criteria",
                "para_flag": r"^合格标准$|合格标准/合格资产标准",
                "special_keyword": [r"循环购买|持续购买|附件.*?所列的合格资产标准"],
            },
        ],
    },
    {
        "path": ["循环购买类", "初始折价率"],
        "models": [
            {
                "name": "qualification_criteria",
                "para_flag": r"初始折价比例|初始折算比例",
            },
            # {
            #     'name': 'sub_chief_member',
            #     'para_flag': r'折价率|应收账款折价率',
            #     'paragraph_pattern': r'(初始折算比例|应收账款折价率)=(?P<dst>.*?%)',
            # },
        ],
    },
    {
        "path": ["循环购买类", "循环购买折价方法"],
        "models": [
            {
                "name": "qualification_criteria",
                "para_flag": r"折价比例|^折算比例|折价率|“?资产折价率”?",
            },
        ],
    },
    {
        "path": ["循环购买类", "循环购买日"],
        "models": [
            {
                "name": "qualification_criteria",
                "para_flag": r"(持续|循环)购买日(（(S|T-1)日）)?",
            },
        ],
    },
    {
        "path": ["循环购买类", "循环购买期"],
        "models": [
            {
                "name": "qualification_criteria",
                "para_flag": r"持续购买期|循环期$|循环购买期",
            },
        ],
    },
    {
        "path": ["循环购买类", "提前摊还事件"],
        "models": [
            {
                "name": "qualification_criteria",
                "para_flag": r"提前摊还事件|(\d+\.?)?循环(购买)?期提前结束事件",
            },
        ],
    },
    {
        "path": ["循环购买类", "循环购买不足事件", "循环购买不足事件"],
        "models": [
            {
                "name": "sub_chief_member",
                "para_flag": r"提前摊还事件",
                "paragraph_pattern": [
                    r"(?P<dst>持续购买日.*?余额超过.*?未偿本金余额)",
                    r"(?P<dst>未用于持续购买的.*?日超过.*?未偿本金余额”?的.*?%)",
                    r"(?P<dst>.*?持续购买日.*?已收到但尚未用于持续购买或者分配的.*?未偿本金余额”?的.*?%)",
                ],
            },
        ],
    },
    {
        "path": ["循环购买类", "循环购买不足事件", "循环购买率"],
        "models": [
            {
                "name": "sub_chief_member",
                "para_flag": r"提前摊还事件",
                "paragraph_pattern": [
                    r"(?P<dst>持续购买日.*?余额超过.*?未偿本金余额)",
                    r"(?P<dst>未用于持续购买的.*?日超过.*?未偿本金余额”?的.*?%)",
                    r"(?P<dst>.*?持续购买日.*?已收到但尚未用于持续购买或者分配的.*?未偿本金余额”?的.*?%)",
                ],
            },
        ],
    },
    {
        "path": ["监测指标定义及阈值类"],
        "models": [
            {
                "name": "monitor_indicator",
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
                "para_flag": r"加速清偿事件|循环期提前结束事件|权利完善事件|提前终止事件",
                "paragraph_pattern": [
                    r"(?P<dst>(某一“收款期间|在任一信托利益核算日|在“信托”存续期间内|本信托项下累计违约率).*)",
                    r"(?P<dst>某一收款期间结束时的累计违约率超过与之相对应的(如下)?数值.*)",
                    r"(?P<dst>第.*?年.*?%.*)",
                    r"(?P<dst>“?累计违约率”?超过.*?以后.*)",
                    r"(?P<dst>当“?(基础资产|信托基础资产)”?的“?累计违约率”?超过.*%)",
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
                "para_flag": r"资产支持票据终止事件",
                "paragraph_pattern": r"(?P<dst>自基准日起.*?次或者累计发生.*?次及以上保证担保启动事件.*?支持票据提前终止的)",
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
    "depends": {
        "预期到期日事件": ["违约事件", "加速清偿事件"],
        "利息支付事件": ["违约事件", "加速清偿事件"],
        "法定到期日事件": ["违约事件", "加速清偿事件"],
    },
    "predictor_options": predictor_options,
}
