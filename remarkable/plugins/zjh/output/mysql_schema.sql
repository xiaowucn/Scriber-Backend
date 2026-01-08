CREATE TABLE `file` (
`id` varchar(32) NOT NULL COMMENT '招股说明书MD5码',
`prospectus_md5` varchar(32) NOT NULL COMMENT '招股说明书MD5码',
`prospectus_name` varchar(100) NULL COMMENT '招股说明书名',
`prospectus_time` varchar(10) NULL COMMENT '招股说明书申报披露时间',
`board` varchar(10) NOT NULL COMMENT '板块',
`updated_utc` timestamp default current_timestamp COMMENT '最后更新时间',
PRIMARY KEY (`prospectus_md5`)
)
COMMENT = '文件信息';
CREATE TABLE `director_information` (
`id` int(11) NOT NULL AUTO_INCREMENT COMMENT '主键',
`pkey` varchar(32) NOT NULL COMMENT 'md5(招股说明书文件名（删去.pdf后缀）+姓名+出生年月)',
`prospectus_md5` varchar(32) NULL COMMENT 'md5(招股说明书文件名（删去.pdf后缀)',
`name` varchar(40) NULL COMMENT '姓名',
`nationality` varchar(40) NULL COMMENT '国籍地区代码',
`overseas_residency` varchar(20) NULL COMMENT '境外居留权',
`gender` varchar(20) NULL COMMENT '性别代码',
`date_of_birth` varchar(20) NULL COMMENT '出生日期',
`education` varchar(255) NULL COMMENT '学历代码',
`job_title` varchar(255) NULL COMMENT '职称',
`current_title` text NULL COMMENT '担任职务',
`start_date` varchar(100) NULL COMMENT '任职日期',
`end_date` varchar(100) NULL COMMENT '离职日期',
`type` varchar(10) NULL COMMENT '董监高核心人员标志',
`updated_utc` timestamp default current_timestamp COMMENT '最后更新时间',
PRIMARY KEY (`id`) ,
INDEX `fkey_idx` (`prospectus_md5` ASC) USING BTREE
)
COMMENT = '董监高核心人员基本情况';
CREATE TABLE `major_lawsuit` (
`id` int(11) NOT NULL AUTO_INCREMENT COMMENT '主键',
`pkey` varchar(32) NOT NULL COMMENT 'md5（招股说明书文件名（删去.pdf后缀）+起诉(申请)方+应诉(被申请)方）',
`prospectus_md5` varchar(32) NULL COMMENT 'md5(招股说明书文件名（删去.pdf后缀)',
`currency_unit` varchar(100) NULL COMMENT '货币单位',
`issues` text NULL COMMENT '事项',
`prosecution_party` varchar(255) NULL COMMENT '起诉(申请)方',
`defending_party` varchar(255) NULL COMMENT '应诉(被申请)方',
`joint_and_several_liability` varchar(255) NULL COMMENT '承担连带责任方',
`litigation_arbitration_type` varchar(255) NULL COMMENT '诉讼仲裁类型',
`amount_involved` varchar(255) NULL COMMENT '诉讼涉及金额',
`estimated_debt_amount` varchar(40) NULL COMMENT '预计负债金额',
`updated_utc` timestamp default current_timestamp COMMENT '最后更新时间',
PRIMARY KEY (`id`) ,
INDEX `fkey_idx` (`prospectus_md5` ASC) USING BTREE
)
COMMENT = '重大诉讼事项';
CREATE TABLE `fund_raising` (
`id` int(11) NOT NULL AUTO_INCREMENT COMMENT '主键',
`pkey` varchar(32) NOT NULL COMMENT 'md5(招股说明书文件名（删去.pdf后缀）+项目名称)',
`prospectus_md5` varchar(32) NULL COMMENT 'md5(招股说明书文件名（删去.pdf后缀)',
`currency_unit` varchar(100) NULL COMMENT '货币单位',
`project_name` varchar(255) NULL COMMENT '项目名称',
`total_investment` varchar(40) NULL COMMENT '投资总额',
`investment_of_fund_raised` varchar(40) NULL COMMENT '募集资金投资额',
`project_invested_of_fund_raised` text NULL COMMENT '募集资金投向',
`updated_utc` timestamp default current_timestamp COMMENT '最后更新时间',
PRIMARY KEY (`id`) ,
INDEX `fkey_idx` (`prospectus_md5` ASC) USING BTREE
)
COMMENT = '募集资金与运用';
CREATE TABLE `patent` (
`id` int(11) NOT NULL AUTO_INCREMENT COMMENT '主键',
`pkey` varchar(32) NOT NULL COMMENT 'md5(招股说明书文件名（删去.pdf后缀）+专利名称)',
`prospectus_md5` varchar(32) NULL COMMENT 'md5(招股说明书文件名（删去.pdf后缀)',
`patent_type` varchar(20) NULL COMMENT '专利类型',
`patent_name` varchar(512) NULL COMMENT '专利名称',
`patent_number` varchar(255) NULL COMMENT '专利号',
`patent_owner` varchar(255) NULL COMMENT '专利权人',
`cost_of_patent` varchar(40) NULL COMMENT '取得成本',
`latest_book_value_at_the_end_of_the_latest_period` varchar(40) NULL COMMENT '最近一期末账面价值',
`date_of_acquisition` varchar(40) NULL COMMENT '取得日期',
`period_of_use` varchar(100) NULL COMMENT '使用期限',
`disputes_over_ownership` varchar(100) NULL COMMENT '是否存在权属纠纷',
`updated_utc` timestamp default current_timestamp COMMENT '最后更新时间',
PRIMARY KEY (`id`) ,
INDEX `fkey_idx` (`prospectus_md5` ASC) USING BTREE
)
COMMENT = '专利';
CREATE TABLE `issuer_information` (
`id` int(11) NOT NULL AUTO_INCREMENT COMMENT '主键',
`pkey` varchar(32) NOT NULL COMMENT 'md5(招股说明书文件名（删去.pdf后缀）+公司名称)',
`prospectus_md5` varchar(32) NULL COMMENT 'md5(招股说明书文件名（删去.pdf后缀)',
`company_name` varchar(50) NULL COMMENT '主体名称',
`name_of_legal_representative` varchar(100) NULL COMMENT '法定代表人姓名',
`unified_social_credit_code` varchar(20) NULL COMMENT '统一社会信用代码',
`organization_code` varchar(20) NULL COMMENT '组织机构代码',
`date_of_establishment` varchar(40) NULL COMMENT '成立日期',
`registered_capital` varchar(40) NULL COMMENT '注册资本',
`registered_address` varchar(255) NULL COMMENT '注册地址',
`office_address` varchar(255) NULL COMMENT '办公地址',
`phone_number` varchar(100) NULL COMMENT '联系电话',
`fax_number` varchar(100) NULL COMMENT '传真号码',
`email` varchar(255) NULL COMMENT '电子邮箱',
`post_code` varchar(100) NULL COMMENT '邮政编码',
`planned_listing_sector` varchar(10) NULL COMMENT '拟上市的板块代码',
`stock_exchanges_to_be_listed` varchar(100) NULL COMMENT '拟上市的交易场所代码',
`sponsor_agency` varchar(100) NULL COMMENT '保荐人编码',
`sponsorship_representatives` varchar(100) NULL COMMENT '保荐代表人',
`lawyer_firm` varchar(100) NULL COMMENT '律师事务所',
`lawyer_in_charge` varchar(100) NULL COMMENT '经办律师姓名',
`accounting_firm` varchar(100) NULL COMMENT '会计师事务所',
`operating_accountants` varchar(100) NULL COMMENT '经办会计师姓名',
`updated_utc` timestamp default current_timestamp COMMENT '最后更新时间',
PRIMARY KEY (`id`) ,
INDEX `fkey_idx` (`prospectus_md5` ASC) USING BTREE
)
COMMENT = '发行人基本情况';
CREATE TABLE `major_client` (
`id` int(11) NOT NULL AUTO_INCREMENT COMMENT '主键',
`pkey` varchar(32) NOT NULL COMMENT 'md5(招股说明书文件名（删去.pdf后缀），客户名称，下属单位，时间)',
`prospectus_md5` varchar(32) NULL COMMENT 'md5(招股说明书文件名（删去.pdf后缀)',
`time` varchar(100) NULL COMMENT '时间',
`currency_unit` varchar(100) NULL COMMENT '货币单位',
`name_customers` text NULL COMMENT '客户名称',
`subordinate_unit_name` varchar(255) NULL COMMENT '下属单位名称',
`sales` varchar(255) NULL COMMENT '销售额',
`proportion_of_main_income` varchar(20) NULL COMMENT '占主营收入比例（%）',
`proportion_of_operating_income` varchar(255) NULL COMMENT '占营业收入比例',
`is_affiliate` int(1) NULL COMMENT '公司关联方标识',
`type` varchar(100) NULL COMMENT '客户类型',
`updated_utc` timestamp default current_timestamp COMMENT '最后更新时间',
PRIMARY KEY (`id`) ,
INDEX `fkey_idx` (`prospectus_md5` ASC) USING BTREE
)
COMMENT = '主要客户';
CREATE TABLE `major_supplier` (
`id` int(11) NOT NULL AUTO_INCREMENT COMMENT '主键',
`pkey` varchar(32) NOT NULL COMMENT 'md5(招股说明书文件名（删去.pdf后缀）+供应商名称+时间)',
`prospectus_md5` varchar(32) NULL COMMENT 'md5(招股说明书文件名（删去.pdf后缀)',
`time` varchar(20) NULL COMMENT '时间',
`currency_unit` varchar(100) NULL COMMENT '货币单位',
`name_of_suppliers` varchar(512) NULL COMMENT '供应商名称',
`items_purchased` text NULL COMMENT '采购内容',
`purchase_amount` varchar(255) NULL COMMENT '采购额',
`proportion_of_total_purchase_amount` varchar(255) NULL COMMENT '占总采购金额比例（%）',
`is_affiliate` int(1) NULL COMMENT '公司关联方标识',
`type` varchar(100) NULL COMMENT '供应商类型',
`updated_utc` timestamp default current_timestamp COMMENT '最后更新时间',
PRIMARY KEY (`id`) ,
INDEX `fkey_idx` (`prospectus_md5` ASC) USING BTREE
)
COMMENT = '主要供应商';
CREATE TABLE `major_contract` (
`id` int(11) NOT NULL AUTO_INCREMENT COMMENT '主键',
`pkey` varchar(32) NOT NULL COMMENT 'md5(招股说明书文件名（删去.pdf后缀）+合同对手方名称+标的)',
`prospectus_md5` varchar(32) NULL COMMENT 'md5(招股说明书文件名（删去.pdf后缀)',
`currency_unit` varchar(100) NULL COMMENT '货币单位',
`tpyes_of_contracts` varchar(20) NULL COMMENT '合同类型',
`name_of_counter_parties` text NULL COMMENT '合同对手方名称',
`underlying_assets` text NULL COMMENT '标的',
`contract_amount` varchar(255) NULL COMMENT '合同金额',
`amount_fullfilled` varchar(255) NULL COMMENT '已履行金额',
`performance_period` varchar(255) NULL COMMENT '履行期限',
`comment` text NULL COMMENT '备注',
`updated_utc` timestamp default current_timestamp COMMENT '最后更新时间',
PRIMARY KEY (`id`) ,
INDEX `fkey_idx` (`prospectus_md5` ASC) USING BTREE
)
COMMENT = '重大合同';
CREATE TABLE `issuer_profession` (
`id` int(11) NOT NULL AUTO_INCREMENT COMMENT '主键',
`pkey` varchar(32) NOT NULL COMMENT 'md5（招股说明书文件名（删去.pdf后缀），行业分类代码)',
`prospectus_md5` varchar(32) NULL COMMENT 'md5(招股说明书文件名（删去.pdf后缀)',
`industry_classification_standard` varchar(255) NULL COMMENT '行业分类标准',
`industry_classification_code` varchar(30) NULL COMMENT '行业分类代码',
`industry_classification_name` varchar(255) NULL COMMENT '行业分类名称',
`updated_utc` timestamp default current_timestamp COMMENT '最后更新时间',
PRIMARY KEY (`id`) ,
INDEX `fkey_idx` (`prospectus_md5` ASC) USING BTREE
)
COMMENT = '发行人所处行业';
CREATE TABLE `profitability` (
`id` int(11) NOT NULL AUTO_INCREMENT COMMENT '主键',
`pkey` varchar(32) NOT NULL COMMENT 'md5(招股说明书文件名（删去.pdf后缀）+报表日期+盈利能力类型+类别)',
`prospectus_md5` varchar(32) NULL COMMENT 'md5(招股说明书文件名（删去.pdf后缀)',
`currency_unit` varchar(100) NULL COMMENT '货币单位',
`table_date` varchar(100) NULL COMMENT '报表日期',
`amount` varchar(255) NULL COMMENT '金额',
`proportion` varchar(100) NULL COMMENT '占比',
`movement` varchar(100) NULL COMMENT '变动比例',
`composition_type` varchar(100) NULL COMMENT '类别',
`business_type` int(11) NULL COMMENT '营业收入成本分析',
`type` int(11) NULL COMMENT '标记',
`harvest` varchar(100) NULL COMMENT '产量',
`updated_utc` timestamp default current_timestamp COMMENT '最后更新时间',
PRIMARY KEY (`id`) ,
INDEX `fkey_idx` (`prospectus_md5` ASC) USING BTREE
)
COMMENT = '盈利能力';
CREATE TABLE `balance` (
`id` int(11) NOT NULL AUTO_INCREMENT COMMENT '主键',
`pkey` varchar(32) NOT NULL COMMENT '招股说明书文件名（删去.pdf后缀）+报表日期',
`prospectus_md5` varchar(32) NULL COMMENT 'md5(招股说明书文件名（删去.pdf后缀)',
`currency_unit` varchar(100) NULL COMMENT '货币单位',
`report_date` varchar(100) NULL COMMENT '报表日期',
`cash_and_bank` varchar(100) NULL COMMENT '货币资金',
`provision_for_settlement_fund` varchar(100) NULL COMMENT '结算备付金',
`funds_lent` varchar(100) NULL COMMENT '拆出资金',
`financial_assets_held_for_trading` varchar(100) NULL COMMENT '交易性金融资产',
`derivative_financial_assets` varchar(100) NULL COMMENT '衍生金融资产',
`notes_receivable_and_accounts_receivable` varchar(100) NULL COMMENT '应收票据及应收账款',
`advances_to_customers` varchar(100) NULL COMMENT '预付款项',
`insurance_premiums_receivables` varchar(100) NULL COMMENT '应收保费',
`reinsurance_receivables` varchar(100) NULL COMMENT '应收分保账款',
`provision_for_reinsurance_receivables` varchar(100) NULL COMMENT '应收分保合同准备金',
`interest_receivables` varchar(100) NULL COMMENT '应收利息',
`dividend_receivables` varchar(100) NULL COMMENT '应收股利',
`other_receivables` varchar(100) NULL COMMENT '其他应收款',
`buy_back_resale_financial_assets` varchar(100) NULL COMMENT '买入返售金融资产',
`inventories` varchar(100) NULL COMMENT '存货',
`contractual_assets` varchar(100) NULL COMMENT '合同资产',
`holding_assets_for_sale` varchar(100) NULL COMMENT '持有待售资产',
`non_current_assets_due_within_one_year` varchar(100) NULL COMMENT '一年内到期的非流动资产',
`other_current_assets` varchar(100) NULL COMMENT '其他流动资产',
`total_current_assets` varchar(100) NULL COMMENT '流动资产合计',
`loans_and_payments` varchar(100) NULL COMMENT '发放委托贷款及垫款',
`debt_investment` varchar(100) NULL COMMENT '债权投资',
`other_creditors_rights_investment` varchar(100) NULL COMMENT '其他债权投资',
`available_for_sale_financial_assets` varchar(100) NULL COMMENT '可供出售金融资产',
`held_to_maturity_investments` varchar(100) NULL COMMENT '持有至到期投资',
`long_term_receivables` varchar(100) NULL COMMENT '长期应收款',
`long_term_equity_investments` varchar(100) NULL COMMENT '长期股权投资',
`investment_in_other_equity_instruments` varchar(100) NULL COMMENT '其他权益工具投资',
`other_non_current_financial_assets` varchar(100) NULL COMMENT '其他非流动金融资产',
`investment_real_estates` varchar(100) NULL COMMENT '投资性房地产',
`fixed_assets_original_cost` varchar(100) NULL COMMENT '固定资产',
`construction_in_progress` varchar(100) NULL COMMENT '在建工程',
`construction_supplies` varchar(100) NULL COMMENT '工程物资',
`fixed_assets_pending_disposal` varchar(100) NULL COMMENT '固定资产清理',
`bearer_biological_assets` varchar(100) NULL COMMENT '生产性生物资产',
`oil_and_natural_gas_assets` varchar(100) NULL COMMENT '油气资产',
`intangible_assets` varchar(100) NULL COMMENT '无形资产',
`research_and_development_costs` varchar(100) NULL COMMENT '开发支出',
`goodwill` varchar(100) NULL COMMENT '商誉',
`long_term_deferred_expenses` varchar(100) NULL COMMENT '长期待摊费用',
`deferred_tax_assets` varchar(100) NULL COMMENT '递延所得税资产',
`other_non_current_assets` varchar(100) NULL COMMENT '其他非流动资产',
`total_non_current_assets` varchar(100) NULL COMMENT '非流动资产合计',
`total_assets` varchar(100) NULL COMMENT '资产总计',
`short_term_borrowings` varchar(100) NULL COMMENT '短期借款',
`borrowings_from_central_bank` varchar(100) NULL COMMENT '向中央银行借款',
`deposits_from_customers_and_interbank` varchar(100) NULL COMMENT '吸收存款及同业存放',
`deposit_funds` varchar(100) NULL COMMENT '拆入资金',
`financial_assets_held_for_liabilities` varchar(100) NULL COMMENT '交易性金融负债',
`derivative_financial_liabilities` varchar(100) NULL COMMENT '衍生金融负债',
`notes_payable_and_accounts_payable` varchar(100) NULL COMMENT '应付票据及应付账款',
`advances_from_customers` varchar(100) NULL COMMENT '预收款项',
`funds_from_sales_of_repurchasement_agreement` varchar(100) NULL COMMENT '卖出回购金融资产款',
`handling_charges_and_commissions_payable` varchar(100) NULL COMMENT '应付手续费及佣金',
`employee_benefits_payable` varchar(100) NULL COMMENT '应付职工薪酬',
`taxes_and_surcharges_payable` varchar(100) NULL COMMENT '应交税费',
`interests_payable` varchar(100) NULL COMMENT '应付利息',
`dividend_payables` varchar(100) NULL COMMENT '应付股利',
`other_payables` varchar(100) NULL COMMENT '其他应付款',
`reinsurance_premiums_payables` varchar(100) NULL COMMENT '应付分保账款',
`provision_for_insurance_contracts` varchar(100) NULL COMMENT '保险合同准备金',
`funds_received_as_agent_of_stock_exchange` varchar(100) NULL COMMENT '代理买卖证券款',
`funds_received_as_stock_underwrite` varchar(100) NULL COMMENT '代理承销证券款',
`contractual_liability` varchar(100) NULL COMMENT '合同负债',
`holding_liabilities_for_sale` varchar(100) NULL COMMENT '持有待售负债',
`non_current_liabilities_maturing_within_one_year` varchar(100) NULL COMMENT '一年内到期的非流动负债',
`other_current_liabilities` varchar(100) NULL COMMENT '其他流动负债',
`total_currennt_liabilities` varchar(100) NULL COMMENT '流动负债合计',
`insurance_contract_reserve` varchar(100) NULL COMMENT '保险合同准备金',
`long_term_loans` varchar(100) NULL COMMENT '长期借款',
`debentures_payables` varchar(100) NULL COMMENT '应付债券',
`non_current_liabilities_preferred_stock` varchar(100) NULL COMMENT '非流动负债_优先股',
`non_current_liabilities_perpetual_capital_securities` varchar(100) NULL COMMENT '非流动负债_永续债',
`preferred_stock` varchar(100) NULL COMMENT '其中:优先股',
`perpetual_capital_securities` varchar(100) NULL COMMENT '永续债',
`long_term_payables` varchar(100) NULL COMMENT '长期应付款',
`specific_payables` varchar(100) NULL COMMENT '专项应付款',
`accrued_liabilities` varchar(100) NULL COMMENT '预计负债',
`deferred_income` varchar(100) NULL COMMENT '递延收益',
`deferred_tax_liabilities` varchar(100) NULL COMMENT '递延所得税负债',
`other_non_current_liabilities` varchar(100) NULL COMMENT '其他非流动负债',
`total_non_current_liabilities` varchar(100) NULL COMMENT '非流动负债合计',
`total_liabilities` varchar(100) NULL COMMENT '负债合计',
`registered_capital` varchar(100) NULL COMMENT '实收资本（或股本）',
`owner_rights_and_interests_other_equity_instruments` varchar(100) NULL COMMENT '所有者权益_其他权益工具',
`owner_rights_and_interests_preferred_stock` varchar(100) NULL COMMENT '所有者权益_优先股',
`owner_rights_and_interests_perpetual_capital_securities` varchar(100) NULL COMMENT '所有者权益_永续债',
`other_comprehensive_benefits` varchar(100) NULL COMMENT '其他综合收益',
`capital_surplus` varchar(100) NULL COMMENT '资本公积',
`less_treasury_stock` varchar(100) NULL COMMENT '减:库存股',
`owner_rights_and_interests_other_comprehensive_benefits` varchar(100) NULL COMMENT '所有者权益_其他综合收益',
`special_reserve` varchar(100) NULL COMMENT '专项储备',
`surplus_reserve` varchar(100) NULL COMMENT '盈余公积',
`provision_for_normal_risks` varchar(100) NULL COMMENT '一般风险准备',
`undistributed_profits` varchar(100) NULL COMMENT '未分配利润',
`exchange_differences_on_translating_foreign_operations` varchar(100) NULL COMMENT '外币报表折算差额',
`total_owners_equity_belongs_to_parent_company` varchar(100) NULL COMMENT '归属于母公司所有者权益合计',
`minority_interest` varchar(100) NULL COMMENT '少数股东权益',
`total_owners_equity` varchar(100) NULL COMMENT '所有者权益合计',
`total_liabilities_and_owners_equity` varchar(100) NULL COMMENT '负债和所有者权益总计',
`updated_utc` timestamp default current_timestamp COMMENT '最后更新时间',
PRIMARY KEY (`id`) ,
INDEX `fkey_idx` (`prospectus_md5` ASC) USING BTREE
)
COMMENT = '资产负债表';
CREATE TABLE `cash_flow` (
`id` int(11) NOT NULL AUTO_INCREMENT COMMENT '主键',
`pkey` varchar(32) NOT NULL COMMENT '招股说明书文件名（删去.pdf后缀）+报表日期',
`prospectus_md5` varchar(32) NULL COMMENT 'md5(招股说明书文件名（删去.pdf后缀)',
`currency_unit` varchar(100) NULL COMMENT '货币单位',
`report_date` varchar(100) NULL COMMENT '报表日期',
`cash_flows_from_operating_activities` varchar(100) NULL COMMENT '经营活动产生的现金流量',
`cash_received_from_the_sales_of_goods_and_services` varchar(100) NULL COMMENT '销售商品、提供劳务收到的现金',
`net_increase_in_deposits_and_placements_from_inter_bank` varchar(100) NULL COMMENT '客户存款和同业存放款项净增加额',
`net_increase_in_loan_from_central_bank` varchar(100) NULL COMMENT '向中央银行借款净增加额',
`net_increase_in_funds_borrowed_from_other_financial_institutions` varchar(100) NULL COMMENT '向其他金融机构拆入资金净增加额',
`cash_premiums_received_on_original_insurance_contracts` varchar(100) NULL COMMENT '收到原保险合同保费取得的现金',
`cash_received_from_re_insurance_business` varchar(100) NULL COMMENT '收到再保险业务现金净额',
`net_increase_in_deposits_and_investments_from_insurers` varchar(100) NULL COMMENT '保户储金及投资款净增加额',
`net_increase_in_disposal_of_trading_financial_assets` varchar(100) NULL COMMENT '处置交易性金融资产净增加额',
`interest_handling_charges_and_commissions_received` varchar(100) NULL COMMENT '收取利息、手续费及佣金的现金',
`net_increase_in_funds_deposit` varchar(100) NULL COMMENT '拆入资金净增加额',
`net_increase_in_repurchase_agreement_business_funds` varchar(100) NULL COMMENT '回购业务资金净增加额',
`agents_securities_net_cash` varchar(100) NULL COMMENT '代理买卖证券收到的现金净额',
`receipts_of_tax_refunds` varchar(100) NULL COMMENT '收到的税费返还',
`other_cash_received_relating_to_operating_activities` varchar(100) NULL COMMENT '收到其他与经营活动有关的现金',
`sub_total_of_cash_inflows_from_operating_activities` varchar(100) NULL COMMENT '经营活动现金流入小计',
`cash_payments_for_goods_purchased_and_services_received` varchar(100) NULL COMMENT '购买商品、接受劳务支付的现金',
`net_increase_in_loans_and_payments_on_behalf` varchar(100) NULL COMMENT '客户贷款及垫款净增加额',
`net_increase_in_deposits_with_centre_bank_and_interbank` varchar(100) NULL COMMENT '存放中央银行和同业款项净增加额',
`payments_of_claims_for_original_insurance_contracts` varchar(100) NULL COMMENT '支付原保险合同赔付款项的现金',
`net_increase_in_financial_assets_held_for_trading_purposes` varchar(100) NULL COMMENT '为交易目的而持有的金融资产净增加额',
`net_increase_in_dismantled_funds` varchar(100) NULL COMMENT '拆出资金净增加额',
`interests_handling_charges_and_commissions_paid` varchar(100) NULL COMMENT '支付利息、手续费及佣金的现金',
`commissions_on_insurance_policies_paid` varchar(100) NULL COMMENT '支付保单红利的现金',
`cash_payments_to_and_on_behalf_of_employees` varchar(100) NULL COMMENT '支付给职工以及为职工支付的现金',
`payments_of_all_types_of_taxes` varchar(100) NULL COMMENT '支付的各项税费',
`other_cash_payments_relating_to_operating_activities` varchar(100) NULL COMMENT '支付其他与经营活动有关的现金',
`sub_total_of_cash_outflows_from_operating_activities` varchar(100) NULL COMMENT '经营活动现金流出小计',
`net_cash_flows_from_operating_activities` varchar(100) NULL COMMENT '经营活动产生的现金流量净额',
`cash_flows_from_investing_activities` varchar(100) NULL COMMENT '投资活动产生的现金流量',
`cash_received_from_disposals_and_withdraw_on_investment` varchar(100) NULL COMMENT '收回投资收到的现金',
`cash_received_from_returns_on_investments` varchar(100) NULL COMMENT '取得投资收益收到的现金',
`net_cash_received_from_disposals_of_fa_ia_and_long_term_assets` varchar(100) NULL COMMENT '处置固定资产、无形资产和其他长期资产收回的现金净额',
`net_cash_received_from_disposals_of_subsidiaries` varchar(100) NULL COMMENT '处置子公司及其他营业单位收到的现金净额',
`other_cash_received_relating_to_investing_activities` varchar(100) NULL COMMENT '收到其他与投资活动有关的现金',
`sub_total_of_cash_inflows_from_investing_activities` varchar(100) NULL COMMENT '投资活动现金流入小计',
`cash_payments_for_fa_ia_and_long_term_assets` varchar(100) NULL COMMENT '购建固定资产、无形资产和其他长期资产支付的现金',
`cash_payments_to_acquire_investments` varchar(100) NULL COMMENT '投资支付的现金',
`net_increase_in_secured_loans` varchar(100) NULL COMMENT '质押贷款净增加额',
`net_cash_payments_for_acquisitions_of_subsidiaries_and_others` varchar(100) NULL COMMENT '取得子公司及其他营业单位支付的现金净额',
`other_cash_payments_relating_to_investing_activities` varchar(100) NULL COMMENT '支付其他与投资活动有关的现金',
`sub_total_of_cash_outflows_from_investing_activities` varchar(100) NULL COMMENT '投资活动现金流出小计',
`net_cash_flows_from_investing_activities` varchar(100) NULL COMMENT '投资活动产生的现金流量净额',
`cash_flows_from_financing_activities` varchar(100) NULL COMMENT '筹资活动产生的现金流量',
`cash_received_from_investment` varchar(100) NULL COMMENT '吸收投资收到的现金',
`including_cash_received_from_issuing_shares_of_minority` varchar(100) NULL COMMENT '其中：子公司吸收少数股东投资收到的现金',
`cash_received_from_borrowings` varchar(100) NULL COMMENT '取得借款收到的现金',
`proceeds_from_issuance_of_bonds` varchar(100) NULL COMMENT '发行债券收到的现金',
`other_cash_received_relating_to_financing_activities` varchar(100) NULL COMMENT '收到其他与筹资活动有关的现金',
`sub_total_of_cash_inflows_from_financing_activities` varchar(100) NULL COMMENT '筹资活动现金流入小计',
`cash_repayments_of_amounts_borrowed` varchar(100) NULL COMMENT '偿还债务支付的现金',
`cash_payments_for_distribution_of_dividends_or_profits` varchar(100) NULL COMMENT '分配股利、利润或偿付利息支付的现金',
`including_subsidiaries_payment_to_minority_for_dividends_profits` varchar(100) NULL COMMENT '其中：子公司支付给少数股东的股利、利润',
`other_cash_payments_relating_to_financing_activities` varchar(100) NULL COMMENT '支付其他与筹资活动有关的现金',
`sub_total_of_cash_outflows_from_financing_activities` varchar(100) NULL COMMENT '筹资活动现金流出小计',
`net_cash_flows_from_financing_activities` varchar(100) NULL COMMENT '筹资活动产生的现金流量净额',
`foreign_exchange_rate_changes_on_cash_and_cash_equivalents` varchar(100) NULL COMMENT '汇率变动对现金及现金等价物的影响',
`net_increase_in_cash_and_cash_equivalents` varchar(100) NULL COMMENT '现金及现金等价物净增加额',
`plus_cash_and_cash_equivalents_at_beginning_of_period` varchar(100) NULL COMMENT '加：期初现金及现金等价物余额',
`cash_and_cash_equivalents_at_end_of_period` varchar(100) NULL COMMENT '期末现金及现金等价物余额',
`updated_utc` timestamp default current_timestamp COMMENT '最后更新时间',
PRIMARY KEY (`id`) ,
INDEX `fkey_idx` (`prospectus_md5` ASC) USING BTREE
)
COMMENT = '现金流量表';
CREATE TABLE `income` (
`id` int(11) NOT NULL AUTO_INCREMENT COMMENT '主键',
`pkey` varchar(32) NOT NULL COMMENT '招股说明书文件名（删去.pdf后缀）+报表日期',
`prospectus_md5` varchar(32) NULL COMMENT 'md5(招股说明书文件名（删去.pdf后缀)',
`currency_unit` varchar(100) NULL COMMENT '货币单位',
`report_date` varchar(100) NULL COMMENT '报表日期',
`overall_sales` varchar(100) NULL COMMENT '营业总收入',
`revenues` varchar(100) NULL COMMENT '营业收入',
`interest_expense` varchar(100) NULL COMMENT '其中:利息费用',
`interest_income` varchar(100) NULL COMMENT '利息收入',
`insurance_premiums_earned` varchar(100) NULL COMMENT '已赚保费',
`handling_charges_and_commissions_income` varchar(100) NULL COMMENT '手续费及佣金收入',
`overall_costs` varchar(100) NULL COMMENT '营业总成本',
`costs_of_sales` varchar(100) NULL COMMENT '其中：营业成本',
`interest_expenses` varchar(100) NULL COMMENT '利息支出',
`handling_charges_and_commissions_expenses` varchar(100) NULL COMMENT '手续费及佣金支出',
`refund_of_insurance_premiums` varchar(100) NULL COMMENT '退保金',
`net_payments_for_insurance_claims` varchar(100) NULL COMMENT '赔付支出净额',
`net_provision_for_insurance_contracts` varchar(100) NULL COMMENT '提取保险合同准备金净额',
`commissions_on_insurance_policies` varchar(100) NULL COMMENT '保单红利支出',
`reinsurance_charges` varchar(100) NULL COMMENT '分保费用',
`sales_tax_and_additions` varchar(100) NULL COMMENT '营业税金及附加',
`selling_and_distribution_expenses` varchar(100) NULL COMMENT '销售费用',
`general_and_administrative_expenses` varchar(100) NULL COMMENT '管理费用',
`research_and_development_expenses` varchar(100) NULL COMMENT '研发费用',
`financial_expenses` varchar(100) NULL COMMENT '财务费用',
`impairment_loss_on_assets` varchar(100) NULL COMMENT '资产减值损失',
`loss_of_credit_impairment` varchar(100) NULL COMMENT '信用减值损失',
`plus_gain_or_loss_from_changes_in_fair_values` varchar(100) NULL COMMENT '加：公允价值变动收益（损失以“-”号填列）',
`other_income` varchar(100) NULL COMMENT '其他收益',
`net_open_hedging_income` varchar(100) NULL COMMENT '净敞口套期收益（损失以“-”号填列）',
`proceeds_from_disposal_of_assets` varchar(100) NULL COMMENT '资产处置收益（损失以“-”号填列）',
`investment_income` varchar(100) NULL COMMENT '投资收益（损失以“-”号填列）',
`including_investment_income_from_joint_ventures_and_affiliates` varchar(100) NULL COMMENT '其中：对联营企业和合营企业的投资收益',
`gain_or_loss_on_foreign_exchange_transactions` varchar(100) NULL COMMENT '汇兑收益（损失以“-”号填列）',
`gross_profit` varchar(100) NULL COMMENT '营业利润（损失以“-”号填列）',
`plus_non_operating_profit` varchar(100) NULL COMMENT '加：营业外收入',
`less_non_operating_expenses` varchar(100) NULL COMMENT '减：营业外支出',
`including_losses_from_disposal_of_non_current_assets` varchar(100) NULL COMMENT '其中：非流动资产处置损失',
`profit_before_tax` varchar(100) NULL COMMENT '利润总额（损失以“-”号填列）',
`less_income_tax_expenses` varchar(100) NULL COMMENT '减：所得税费用',
`net_profit` varchar(100) NULL COMMENT '净利润（净损失以“-”号填列）',
`continuous_operating_net_profit` varchar(100) NULL COMMENT '(一)按经营持续性分类1.持续经营净利润(净亏损以“-”号填列)',
`termination_of_net_operating_profit` varchar(100) NULL COMMENT '2.终止经营净利润(净亏损以“-”号填列)',
`including_profit_earned_before_consolidation` varchar(100) NULL COMMENT '其中：被合并方在合并前实现的净利润',
`net_profit_belonging_to_parent_company` varchar(100) NULL COMMENT '(二)按所有权归属分类1.归属于母公司股东的净利润(净亏损以“-”号填列)',
`minority_interest` varchar(100) NULL COMMENT '2.少数股东损益(净亏损以“-”号填列)',
`f001` varchar(100) NULL COMMENT '(一)归属于母公司所有者的其他综合收益的税后净额',
`f002` varchar(100) NULL COMMENT '1.不能重分类进损益的其他综合收益',
`f003` varchar(100) NULL COMMENT '(1)重新计量设定受益计划变动额',
`f004` varchar(100) NULL COMMENT '(2)权益法下不能转损益的其他综合收益',
`f004_1` varchar(100) NULL COMMENT '(3)其他权益工具投资公允价值变动',
`f005` varchar(100) NULL COMMENT '(4)企业自身信用风险公允价值变动',
`f006` varchar(100) NULL COMMENT '2.将重分类进损益的其他综合收益',
`f007` varchar(100) NULL COMMENT '(1)权益法下可转损益的其他综合收益',
`f008` varchar(100) NULL COMMENT '(2)其他债权投资公允价值变动',
`f009` varchar(100) NULL COMMENT '(3)金融资产重分类计入其他综合收益的金额',
`f010` varchar(100) NULL COMMENT '(4)其他债权投资信用减值准备',
`f011` varchar(100) NULL COMMENT '(5)现金流量套期储备',
`f012` varchar(100) NULL COMMENT '(6)外币财务报表折算差额',
`f013` varchar(100) NULL COMMENT '(二)归属于少数股东的其他综合收益的税后净额',
`earnings_per_share` varchar(100) NULL COMMENT '每股收益',
`basic_earnings_per_share` varchar(100) NULL COMMENT '基本每股收益',
`diluted_earnings_per_share` varchar(100) NULL COMMENT '稀释每股收益',
`other_comprehensive_income` varchar(100) NULL COMMENT '其他综合收益',
`comprehensive_income` varchar(100) NULL COMMENT '综合收益总额',
`comprehensive_income_belong_to_parent_company` varchar(100) NULL COMMENT '归属于母公司所有者的综合收益总额',
`comprehensive_income_belong_to_minority_shareholders` varchar(100) NULL COMMENT '归属于少数股东的综合收益总额',
`updated_utc` timestamp default current_timestamp COMMENT '最后更新时间',
PRIMARY KEY (`id`) ,
INDEX `fkey_idx` (`prospectus_md5` ASC) USING BTREE
)
COMMENT = '利润表';
CREATE TABLE `main_financial_indicators` (
`id` int(11) NOT NULL AUTO_INCREMENT COMMENT '主键',
`pkey` varchar(32) NOT NULL COMMENT '招股说明书文件名（删去.pdf后缀）+报表日期',
`prospectus_md5` varchar(32) NULL COMMENT 'md5(招股说明书文件名（删去.pdf后缀)',
`currency_unit` varchar(100) NULL COMMENT '货币单位',
`report_date` varchar(100) NULL COMMENT '报表日期',
`current_ratio` varchar(100) NULL COMMENT '流动比率(倍)',
`quick_ratio` varchar(100) NULL COMMENT '速动比率(倍)',
`asset_to_liability_ratio_parent_company` varchar(100) NULL COMMENT '资产负债率(母公司）',
`asset_to_liability_ratio_consolidated` varchar(100) NULL COMMENT '资产负债率（合并）',
`intangible_assets` varchar(100) NULL COMMENT '无形资产（扣除土地使用权、水面养殖权和采矿权等后）占净资产的比例（%）',
`accounts_receivable_turnover_rate` varchar(100) NULL COMMENT '应收账款周转率(次/年)',
`inventory_turnover_rate` varchar(100) NULL COMMENT '存货周转率(次/年)',
`total_asset_turnover_rate` varchar(100) NULL COMMENT '总资产周转率(次/年)',
`earnings_before_interest_taxes_depreciation_and_amortization` varchar(100) NULL COMMENT '息税折旧摊销前利润(元)',
`interest_coverage_multiple` varchar(100) NULL COMMENT '利息保障倍数(倍)',
`basic_eps_after_deducting_non_recurring_gains_and_losses` varchar(100) NULL COMMENT '扣除非经常性损益后的每股基本收益（元）',
`cash_flow_from_operating_activities_per_share` varchar(100) NULL COMMENT '每股经营活动产生的现金流量(元)',
`net_cash_flow_per_share` varchar(100) NULL COMMENT '每股净现金流量(元)',
`weighted_average_return_on_equity` varchar(100) NULL COMMENT '加权平均净资产收益率',
`updated_utc` timestamp default current_timestamp COMMENT '最后更新时间',
PRIMARY KEY (`id`) ,
INDEX `fkey_idx` (`prospectus_md5` ASC) USING BTREE
)
COMMENT = '主要财务指标表';
CREATE TABLE `actual_controller_info` (
`id` int(11) NOT NULL AUTO_INCREMENT COMMENT '主键',
`pkey` varchar(32) NOT NULL COMMENT 'md5(招股说明书文件名（删去.pdf后缀）+名称)',
`prospectus_md5` varchar(32) NULL COMMENT 'md5(招股说明书文件名（删去.pdf后缀)',
`name` varchar(255) NULL COMMENT '主体名称',
`principal` varchar(255) NULL COMMENT '负责人标识',
`direct_holding_ratio` varchar(100) NULL COMMENT '直接持股比例(%)',
`indirect_holding_ratio` varchar(100) NULL COMMENT '间接持股比例(%)',
`identity_number` varchar(30) NULL COMMENT '证件号码',
`nationality` varchar(30) NULL COMMENT '国家及地区代码',
`nature` varchar(20) NULL COMMENT '实际控制人性质',
`pledged_shares` varchar(20) NULL COMMENT '质押股份数量(万股)',
`type` varchar(20) NULL COMMENT '实际控制人类型',
`is_indirect_total` int(1) NULL COMMENT '间接合计持股标志',
`is_direct_total` int(1) NULL COMMENT '直接合计持股标志',
`updated_utc` timestamp default current_timestamp COMMENT '最后更新时间',
PRIMARY KEY (`id`) ,
INDEX `fkey_idx` (`prospectus_md5` ASC) USING BTREE
)
COMMENT = '实际控制人简要情况';
CREATE TABLE `paraphrase` (
`id` int(11) NOT NULL AUTO_INCREMENT COMMENT '主键',
`pkey` varchar(32) NOT NULL COMMENT 'md5(招股说明书文件名（删去.pdf后缀）+简称)',
`prospectus_md5` varchar(32) NULL COMMENT 'md5(招股说明书文件名（删去.pdf后缀)',
`abbreviation` varchar(255) NULL COMMENT '简称',
`full_name` text NULL COMMENT '全称',
`updated_utc` timestamp default current_timestamp COMMENT '最后更新时间',
PRIMARY KEY (`id`) ,
INDEX `fkey_idx` (`prospectus_md5` ASC) USING BTREE
)
COMMENT = '释义';
CREATE TABLE `controlling_shareholder_info` (
`id` int(11) NOT NULL AUTO_INCREMENT COMMENT '主键',
`pkey` varchar(32) NOT NULL COMMENT 'md5(招股说明书文件名（删去.pdf后缀）+名称)',
`prospectus_md5` varchar(32) NULL COMMENT 'md5(招股说明书文件名（删去.pdf后缀)',
`name` varchar(255) NULL COMMENT '主体名称',
`nature_of_business` varchar(255) NULL COMMENT '企业类型代码',
`direct_holding_ratio` varchar(100) NULL COMMENT '直接持股比例(%)',
`indirect_holding_ratio` varchar(100) NULL COMMENT '间接持股比例(%)',
`identity_number` varchar(20) NULL COMMENT '证件号码',
`nationality` varchar(30) NULL COMMENT '国家及地区代码',
`nature` varchar(20) NULL COMMENT '机构性质',
`type` varchar(20) NULL COMMENT '主体类型',
`is_indirect_total` int(1) NULL COMMENT '间接合计持股标志',
`is_direct_total` int(1) NULL COMMENT '直接合计持股标志',
`share_freezing_ratio` varchar(10) NULL COMMENT '股份冻结比例(%)',
`share_pledge_ratio` varchar(10) NULL COMMENT '股份质押比例(%)',
`updated_utc` timestamp default current_timestamp COMMENT '最后更新时间',
PRIMARY KEY (`id`) ,
INDEX `fkey_idx` (`prospectus_md5` ASC) USING BTREE
)
COMMENT = '控股股东简要情况';
CREATE TABLE `depreciation_of_fixed_assets` (
`id` int(11) NOT NULL AUTO_INCREMENT COMMENT '主键',
`pkey` varchar(32) NOT NULL COMMENT 'md5(招股说明书文件名（删去.pdf后缀）+ 项目名称 + 时间)',
`prospectus_md5` varchar(32) NULL COMMENT 'md5(招股说明书文件名（删去.pdf后缀)',
`name` varchar(255) NULL COMMENT '项目名称',
`date` varchar(32) NULL COMMENT '时间',
`unit` varchar(32) NULL COMMENT '货币单位',
`primary_value_of_fixed_assets` varchar(32) NULL COMMENT '固定资产原值',
`accumulated_depreciation` varchar(32) NULL COMMENT '累计折旧',
`allowance_for_impairment` varchar(32) NULL COMMENT '减值准备',
`net_fixed_assets` varchar(32) NULL COMMENT '固定资产净值',
`book_value` varchar(32) NULL COMMENT '账面价值',
`depreciation_method` varchar(32) NULL COMMENT '折旧方法',
`useful_life_of_fixed_assets` varchar(32) NULL COMMENT '折旧年限',
`salvage_rate` varchar(32) NULL COMMENT '残值率',
`updated_utc` timestamp default current_timestamp COMMENT '最后更新时间',
PRIMARY KEY (`id`),
INDEX `fkey_idx` (`prospectus_md5` ASC) USING BTREE
)
COMMENT = '固定资产折旧';
CREATE TABLE `accounts_receivable` (
`id` int(11) NOT NULL AUTO_INCREMENT COMMENT '主键',
`pkey` varchar(32) NOT NULL COMMENT 'md5(招股说明书文件名（删去.pdf后缀）+ 账龄分析法类型 + 时间)',
`prospectus_md5` varchar(32) NULL COMMENT 'md5(招股说明书文件名（删去.pdf后缀)',
`type` varchar(32) NULL COMMENT '账龄分析法的类型',
`book_balance` varchar(32) NULL COMMENT '账面余额',
`proportion` varchar(32) NULL COMMENT '坏账准备计提比例',
`bad_debt_preparation` varchar(32) NULL COMMENT '坏账准备',
`date` varchar(32) NULL COMMENT '时间',
`age_of_zccount` varchar(32) NULL COMMENT '账龄',
`unit` varchar(255) NULL COMMENT '货币单位',
`updated_utc` timestamp default current_timestamp COMMENT '最后更新时间',
PRIMARY KEY (`id`),
INDEX `fkey_idx` (`prospectus_md5` ASC) USING BTREE
)
COMMENT = '应收账款';
CREATE TABLE `inventory_impairment` (
`id` int(11) NOT NULL AUTO_INCREMENT COMMENT '主键',
`pkey` varchar(32) NOT NULL COMMENT 'md5(招股说明书文件名（删去.pdf后缀）+ 项目名称 + 时间)',
`prospectus_md5` varchar(32) NULL COMMENT 'md5(招股说明书文件名（删去.pdf后缀)',
`name` varchar(255) NULL COMMENT '项目名称',
`date` varchar(255) NULL COMMENT '时间',
`unit` varchar(255) NULL COMMENT '货币单位',
`book_balance` varchar(255) NULL COMMENT '账面余额',
`depreciation_reserve` varchar(255) NULL COMMENT '跌价准备',
`value` varchar(255) NULL COMMENT '账面价值',
`updated_utc` timestamp default current_timestamp COMMENT '最后更新时间',
PRIMARY KEY (`id`),
INDEX `fkey_idx` (`prospectus_md5` ASC) USING BTREE
)
COMMENT = '存货减值';
CREATE TABLE `ownership_structure` (
`id` int(11) NOT NULL AUTO_INCREMENT COMMENT '主键',
`pkey` varchar(32) NOT NULL COMMENT 'md5(招股说明书文件名（删去.pdf后缀）+ 主体名称)',
`prospectus_md5` varchar(32) NULL COMMENT 'md5(招股说明书文件名（删去.pdf后缀)',
`shareholder_name` varchar(255) NULL COMMENT '主体名称',
`shareholding_quantity` varchar(255) NULL COMMENT '股份持有数量',
`unit` varchar(255) NULL COMMENT '单位',
`proportion` varchar(255) NULL COMMENT '持股比例',
`order_number` varchar(255) NULL COMMENT '股东排名',
`updated_utc` timestamp default current_timestamp COMMENT '最后更新时间',
PRIMARY KEY (`id`),
INDEX `fkey_idx` (`prospectus_md5` ASC) USING BTREE
)
COMMENT = '股权结构';
CREATE TABLE `different_table` (
`id` int(11) NOT NULL AUTO_INCREMENT COMMENT '主键',
`pkey` varchar(32) NOT NULL COMMENT 'md5(招股说明书文件名（删去.pdf后缀）+ 项目名称 + 时间)',
`prospectus_md5` varchar(32) NULL COMMENT 'md5(招股说明书文件名（删去.pdf后缀)',
`prohect_name` varchar(255) NULL COMMENT '项目',
`time` varchar(255) NULL COMMENT '时间',
`amount_of_money` varchar(255) NULL COMMENT '金额',
`unit` varchar(255) NULL COMMENT '单位',
`updated_utc` timestamp default current_timestamp COMMENT '最后更新时间',
PRIMARY KEY (`id`),
INDEX `fkey_idx` (`prospectus_md5` ASC) USING BTREE
)
COMMENT = '净利润与经营活动净现金流量差异';
CREATE TABLE `non_recurrent_gains_and_losses` (
`id` int(11) NOT NULL AUTO_INCREMENT COMMENT '主键',
`pkey` varchar(32) NOT NULL COMMENT 'md5(招股说明书文件名（删去.pdf后缀）+ 项目名称 + 时间)',
`prospectus_md5` varchar(32) NULL COMMENT 'md5(招股说明书文件名（删去.pdf后缀)',
`project_name` varchar(255) NULL COMMENT '项目',
`time` varchar(255) NULL COMMENT '时间',
`money` varchar(255) NULL COMMENT '金额',
`unit` varchar(255) NULL COMMENT '单位',
`updated_utc` timestamp default current_timestamp COMMENT '最后更新时间',
PRIMARY KEY (`id`),
INDEX `fkey_idx` (`prospectus_md5` ASC) USING BTREE
)
COMMENT = '非经常性损益情况';
CREATE TABLE `issuance_staff_and_structure` (
`id` int(11) NOT NULL AUTO_INCREMENT COMMENT '主键',
`pkey` varchar(32) NOT NULL COMMENT 'md5(招股说明书文件名（删去.pdf后缀）+ 分类名 + 类型)',
`prospectus_md5` varchar(32) NULL COMMENT 'md5(招股说明书文件名（删去.pdf后缀)',
`classifiation_name` varchar(32) NULL COMMENT '分类名',
`type` varchar(32) NULL COMMENT '员工类型',
`time` varchar(32) NULL COMMENT '时间',
`units` varchar(32) NULL COMMENT '单位',
`number` varchar(32) NULL COMMENT '人数',
`updated_utc` timestamp default current_timestamp COMMENT '最后更新时间',
PRIMARY KEY (`id`),
INDEX `fkey_idx` (`prospectus_md5` ASC) USING BTREE
)
COMMENT = '发行人员工及结构情况';
CREATE TABLE `advance_payment` (
`id` int(11) NOT NULL AUTO_INCREMENT COMMENT '主键',
`pkey` varchar(32) NOT NULL COMMENT 'md5(招股说明书文件名（删去.pdf后缀）+ 分类名 + 类型)',
`prospectus_md5` varchar(32) NULL COMMENT 'md5(招股说明书文件名（删去.pdf后缀)',
`age_of_account` varchar(32) NULL COMMENT '账龄',
`time` varchar(32) NULL COMMENT '时间',
`unit` varchar(32) NULL COMMENT '单位',
`book_balance` varchar(32) NULL COMMENT '账面余额',
`updated_utc` timestamp default current_timestamp COMMENT '最后更新时间',
PRIMARY KEY (`id`),
INDEX `fkey_idx` (`prospectus_md5` ASC) USING BTREE
)
COMMENT = '预付账款';
CREATE TABLE `tax_payment` (
`id` int(11) NOT NULL AUTO_INCREMENT COMMENT '主键',
`pkey` varchar(32) NOT NULL COMMENT 'md5(招股说明书文件名（删去.pdf后缀）+ 分类名 + 类型)',
`prospectus_md5` varchar(32) NULL COMMENT 'md5(招股说明书文件名（删去.pdf后缀)',
`project_name` varchar(255) NULL COMMENT '项目',
`time` varchar(32) NULL COMMENT '时间',
`amount_of_money` varchar(32) NULL COMMENT '金额',
`unit` varchar(32) NULL COMMENT '单位',
`updated_utc` timestamp default current_timestamp COMMENT '最后更新时间',
PRIMARY KEY (`id`),
INDEX `fkey_idx` (`prospectus_md5` ASC) USING BTREE
)
COMMENT = '税款缴纳情况';
CREATE TABLE `intangible_assets` (
`id` int(11) NOT NULL AUTO_INCREMENT COMMENT '主键',
`pkey` varchar(32) NOT NULL COMMENT 'md5(招股说明书文件名（删去.pdf后缀）+ 无形资产类别 + 时间)',
`prospectus_md5` varchar(32) NULL COMMENT 'md5(招股说明书文件名（删去.pdf后缀)',
`intangible_type` varchar(32) NULL COMMENT '无形资产类别',
`entry_value` varchar(32) NULL COMMENT '入账价值',
`accumulated_amortization` varchar(32) NULL COMMENT '累积摊销',
`book_value` varchar(32) NULL COMMENT '账面价值',
`units` varchar(32) NULL COMMENT '单位',
`book_value_radio` varchar(32) NULL COMMENT '账面价值占比',
`time` varchar(32) NULL COMMENT '时间',
`updated_utc` timestamp default current_timestamp COMMENT '最后更新时间',
PRIMARY KEY (`id`),
INDEX `fkey_idx` (`prospectus_md5` ASC) USING BTREE
)
COMMENT = '无形资产';
CREATE TABLE `goodwill_impairment_provision` (
`id` int(11) NOT NULL AUTO_INCREMENT COMMENT '主键',
`pkey` varchar(32) NOT NULL COMMENT 'md5(招股说明书文件名（删去.pdf后缀）+ 项目名称 + 时间)',
`prospectus_md5` varchar(32) NULL COMMENT 'md5(招股说明书文件名（删去.pdf后缀)',
`entry_name` varchar(32) NULL COMMENT '项目名称',
`time` varchar(32) NULL COMMENT '时间',
`units` varchar(32) NULL COMMENT '单位',
`original_value_of_account` varchar(32) NULL COMMENT '账面原值',
`allowance_for_impairment` varchar(32) NULL COMMENT '减值准备',
`book_value` varchar(32) NULL COMMENT '账面价值',
`updated_utc` timestamp default current_timestamp COMMENT '最后更新时间',
PRIMARY KEY (`id`),
INDEX `fkey_idx` (`prospectus_md5` ASC) USING BTREE
)
COMMENT = '商誉减值准备';
CREATE TABLE `audit_opinion` (
`id` int(11) NOT NULL AUTO_INCREMENT COMMENT '主键',
`pkey` varchar(32) NOT NULL COMMENT 'md5(招股说明书文件名（删去.pdf后缀）+ 审计机构 + 披露时间)',
`prospectus_md5` varchar(32) NULL COMMENT 'md5(招股说明书文件名（删去.pdf后缀)',
`auditing_body` varchar(32) NULL COMMENT '审计机构',
`types_of_audit_opinions` varchar(32) NULL COMMENT '审计意见类型',
`disclosure_time_of_audit_opinions` varchar(100) NULL COMMENT '审计意见对应年报时间',
`statement_of_audit_opinions` text NULL COMMENT '审计意见说明',
`updated_utc` timestamp default current_timestamp COMMENT '最后更新时间',
PRIMARY KEY (`id`),
INDEX `fkey_idx` (`prospectus_md5` ASC) USING BTREE
)
COMMENT = '审计意见';
CREATE TABLE `related_transactions` (
`id` int(11) NOT NULL AUTO_INCREMENT COMMENT '主键',
`pkey` varchar(32) NOT NULL COMMENT 'md5(招股说明书文件名（删去.pdf后缀）+ 名称 + 类型 + 时间)',
`prospectus_md5` varchar(32) NULL COMMENT 'md5(招股说明书文件名（删去.pdf后缀)',
`type` varchar(32) NULL COMMENT '关联类型',
`name` varchar(255) NULL COMMENT '名称',
`time` varchar(32) NULL COMMENT '时间',
`amount_of_money` varchar(32) NULL COMMENT '金额',
`unit` varchar(32) NULL COMMENT '单位',
`updated_utc` timestamp default current_timestamp COMMENT '最后更新时间',
PRIMARY KEY (`id`),
INDEX `fkey_idx` (`prospectus_md5` ASC) USING BTREE
)
COMMENT = '关联交易';
CREATE TABLE `notes_to_the_financial_statements` (
`id` int(11) NOT NULL AUTO_INCREMENT COMMENT '主键',
`pkey` varchar(32) NOT NULL COMMENT 'md5(招股说明书文件名（删去.pdf后缀）+ 项目 + 时间)',
`prospectus_md5` varchar(32) NULL COMMENT 'md5(招股说明书文件名（删去.pdf后缀)',
`project_name` varchar(255) NULL COMMENT '项目名',
`type` varchar(32) NULL COMMENT '财务附注类型',
`time` varchar(32) NULL COMMENT '时间',
`amount_of_money` varchar(32) NULL COMMENT '金额',
`unit` varchar(32) NULL COMMENT '单位',
`updated_utc` timestamp default current_timestamp COMMENT '最后更新时间',
PRIMARY KEY (`id`),
INDEX `fkey_idx` (`prospectus_md5` ASC) USING BTREE
)
COMMENT = '财务报表附注';


ALTER TABLE `director_information` ADD CONSTRAINT `fk_person_information_person_information_1` FOREIGN KEY (`prospectus_md5`) REFERENCES `file` (`prospectus_md5`);
ALTER TABLE `major_lawsuit` ADD CONSTRAINT `fk_major_lawsuit_major_lawsuit_1` FOREIGN KEY (`prospectus_md5`) REFERENCES `file` (`prospectus_md5`);
ALTER TABLE `issuer_information` ADD CONSTRAINT `fk_issuer_information_issuer_information_1` FOREIGN KEY (`prospectus_md5`) REFERENCES `file` (`prospectus_md5`);
ALTER TABLE `fund_raising` ADD CONSTRAINT `fk_fund_raising_fund_raising_1` FOREIGN KEY (`prospectus_md5`) REFERENCES `file` (`prospectus_md5`);
ALTER TABLE `patent` ADD CONSTRAINT `fk_patent_patent_1` FOREIGN KEY (`prospectus_md5`) REFERENCES `file` (`prospectus_md5`);
ALTER TABLE `major_client` ADD CONSTRAINT `fk_major_client_major_client_1` FOREIGN KEY (`prospectus_md5`) REFERENCES `file` (`prospectus_md5`);
ALTER TABLE `major_supplier` ADD CONSTRAINT `fk_major_supplier_major_supplier_1` FOREIGN KEY (`prospectus_md5`) REFERENCES `file` (`prospectus_md5`);
ALTER TABLE `issuer_profession` ADD CONSTRAINT `fk_issuer_profession_issuer_profession_1` FOREIGN KEY (`prospectus_md5`) REFERENCES `file` (`prospectus_md5`);
ALTER TABLE `major_contract` ADD CONSTRAINT `fk_major_contract_major_contract_1` FOREIGN KEY (`prospectus_md5`) REFERENCES `file` (`prospectus_md5`);
ALTER TABLE `profitability` ADD CONSTRAINT `fk_profitability_profitability_1` FOREIGN KEY (`prospectus_md5`) REFERENCES `file` (`prospectus_md5`);
ALTER TABLE `actual_controller_info` ADD CONSTRAINT `fk_actual_controller_info_actual_controller_info_1` FOREIGN KEY (`prospectus_md5`) REFERENCES `file` (`prospectus_md5`);
ALTER TABLE `main_financial_indicators` ADD CONSTRAINT `fk_main_financial_indicators_main_financial_indicators_1` FOREIGN KEY (`prospectus_md5`) REFERENCES `file` (`prospectus_md5`);
ALTER TABLE `balance` ADD CONSTRAINT `fk_balance_balance_1` FOREIGN KEY (`prospectus_md5`) REFERENCES `file` (`prospectus_md5`);
ALTER TABLE `income` ADD CONSTRAINT `fk_income_income_1` FOREIGN KEY (`prospectus_md5`) REFERENCES `file` (`prospectus_md5`);
ALTER TABLE `cash_flow` ADD CONSTRAINT `fk_cash_flow_cash_flow_1` FOREIGN KEY (`prospectus_md5`) REFERENCES `file` (`prospectus_md5`);
ALTER TABLE `paraphrase` ADD CONSTRAINT `fk_paraphrase_paraphrase_1` FOREIGN KEY (`prospectus_md5`) REFERENCES `file` (`prospectus_md5`);
ALTER TABLE `controlling_shareholder_info` ADD CONSTRAINT `fk_controlling_shareholder_info_controlling_shareholder_info_1` FOREIGN KEY (`prospectus_md5`) REFERENCES `file` (`prospectus_md5`);
ALTER TABLE `depreciation_of_fixed_assets` ADD CONSTRAINT `fk_depreciation_of_fixed_assets_depreciation_of_fixed_assets_1` FOREIGN KEY (`prospectus_md5`) REFERENCES `file` (`prospectus_md5`);
ALTER TABLE `accounts_receivable` ADD CONSTRAINT `fk_accounts_receivable_accounts_receivable_1` FOREIGN KEY (`prospectus_md5`) REFERENCES `file` (`prospectus_md5`);
ALTER TABLE `inventory_impairment` ADD CONSTRAINT `fk_inventory_impairment_inventory_impairment_1` FOREIGN KEY (`prospectus_md5`) REFERENCES `file` (`prospectus_md5`);
ALTER TABLE `ownership_structure` ADD CONSTRAINT `fk_ownership_structure_ownership_structure_1` FOREIGN KEY (`prospectus_md5`) REFERENCES `file` (`prospectus_md5`);
ALTER TABLE `different_table` ADD CONSTRAINT `fk_different_table_different_table_1` FOREIGN KEY (`prospectus_md5`) REFERENCES `file` (`prospectus_md5`);
ALTER TABLE `non_recurrent_gains_and_losses` ADD CONSTRAINT `fk_non_recurrent_non_recurrent_1` FOREIGN KEY (`prospectus_md5`) REFERENCES `file` (`prospectus_md5`);
ALTER TABLE `advance_payment` ADD CONSTRAINT `fk_advance_payment_advance_payment_1` FOREIGN KEY (`prospectus_md5`) REFERENCES `file` (`prospectus_md5`);
ALTER TABLE `issuance_staff_and_structure` ADD CONSTRAINT `fk_issuance_staff_and_structure_issuance_staff_and_structure_1` FOREIGN KEY (`prospectus_md5`) REFERENCES `file` (`prospectus_md5`);
ALTER TABLE `tax_payment` ADD CONSTRAINT `fk_tax_payment_tax_payment_1` FOREIGN KEY (`prospectus_md5`) REFERENCES `file` (`prospectus_md5`);
ALTER TABLE `intangible_assets` ADD CONSTRAINT `fk_intangible_assets_intangible_assets_1` FOREIGN KEY (`prospectus_md5`) REFERENCES `file` (`prospectus_md5`);
ALTER TABLE `goodwill_impairment_provision` ADD CONSTRAINT `fk_goodwill_impairment_provision_goodwill_impairment_provision_1` FOREIGN KEY (`prospectus_md5`) REFERENCES `file` (`prospectus_md5`);
ALTER TABLE `audit_opinion` ADD CONSTRAINT `fk_audit_opinion_audit_opinion_1` FOREIGN KEY (`prospectus_md5`) REFERENCES `file` (`prospectus_md5`);
ALTER TABLE `related_transactions` ADD CONSTRAINT `fk_related_transactions_related_transactions_1` FOREIGN KEY (`prospectus_md5`) REFERENCES `file` (`prospectus_md5`);
ALTER TABLE `notes_to_the_financial_statements` ADD CONSTRAINT `fk_notes_notes_1` FOREIGN KEY (`prospectus_md5`) REFERENCES `file` (`prospectus_md5`)
