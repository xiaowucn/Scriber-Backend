ALTER TABLE major_client MODIFY `type` VARCHAR(100);

ALTER TABLE major_supplier MODIFY `type` VARCHAR(100);

ALTER TABLE	balance MODIFY contractual_assets VARCHAR(100),
						   MODIFY holding_assets_for_sale VARCHAR(100),
						   MODIFY debt_investment VARCHAR(100),
						   MODIFY other_creditors_rights_investment VARCHAR(100),
						   MODIFY investment_in_other_equity_instruments VARCHAR(100),
						   MODIFY other_non_current_financial_assets VARCHAR(100),
						   MODIFY derivative_financial_liabilities VARCHAR(100),
						   MODIFY contractual_liability VARCHAR(100),
						   MODIFY holding_liabilities_for_sale VARCHAR(100),
						   MODIFY insurance_contract_reserve VARCHAR(100),
						   MODIFY preferred_stock VARCHAR(100),
						   MODIFY perpetual_capital_securities VARCHAR(100),
						   MODIFY other_comprehensive_benefits VARCHAR(100);

ALTER TABLE income MODIFY loss_of_credit_impairment VARCHAR(100),
	                      MODIFY other_income VARCHAR(100),
	                      MODIFY net_open_hedging_income VARCHAR(100),
	                      MODIFY proceeds_from_disposal_of_assets VARCHAR(100),
	                      MODIFY f001 VARCHAR(100),
	                      MODIFY f002 VARCHAR(100),
	                      MODIFY f003 VARCHAR(100),
	                      MODIFY f004 VARCHAR(100),
	                      MODIFY f004_1 VARCHAR(100),
	                      MODIFY f005 VARCHAR(100),
	                      MODIFY f006 VARCHAR(100),
	                      MODIFY f007 VARCHAR(100),
	                      MODIFY f008 VARCHAR(100),
	                      MODIFY f009 VARCHAR(100),
	                      MODIFY f010 VARCHAR(100),
	                      MODIFY f011 VARCHAR(100),
	                      MODIFY f012 VARCHAR(100),
	                      MODIFY f013 VARCHAR(100);

-- 2019-07-22
ALTER TABLE issuer_information MODIFY `sponsor_agency` VARCHAR(100);
ALTER TABLE issuer_information MODIFY `sponsorship_representatives` VARCHAR(100);
ALTER TABLE patent MODIFY `period_of_use` VARCHAR(100);

-- 2019-07-23
ALTER TABLE issuer_information MODIFY lawyer_in_charge VARCHAR(100),
							   MODIFY operating_accountants VARCHAR(100);
ALTER TABLE tax_payment MODIFY project_name VARCHAR(100);
ALTER TABLE notes_to_the_financial_statements MODIFY project_name VARCHAR(100);

-- 2019-07-26
ALTER TABLE depreciation_of_fixed_assets MODIFY name VARCHAR(255);
ALTER TABLE related_transactions MODIFY name VARCHAR(255);
ALTER TABLE patent MODIFY disputes_over_ownership VARCHAR(100);
ALTER TABLE audit_opinion MODIFY statement_of_audit_opinions text;

-- 2019-08-02
ALTER TABLE major_contract MODIFY `comment` text;

-- 2019-08-16
ALTER TABLE issuer_information MODIFY `stock_exchanges_to_be_listed` varchar(100);

-- 2019-08-20
ALTER TABLE issuer_information MODIFY `email` varchar(255),
                               MODIFY `post_code` varchar(100);


-- 2019-11-08
ALTER TABLE audit_opinion MODIFY `disclosure_time_of_audit_opinions` varchar(100);

-- 2020-07-02
ALTER TABLE major_supplier MODIFY `name_of_suppliers` varchar(512);

-- 2020-07-31
ALTER TABLE major_lawsuit MODIFY `issues` text;

-- 2020-09-04
ALTER TABLE major_contract MODIFY `name_of_counter_parties` text;

-- 2020-09-29
ALTER TABLE patent MODIFY `patent_number` varchar(255);

-- 2022-01-07
ALTER TABLE patent MODIFY `patent_name` varchar(512);
