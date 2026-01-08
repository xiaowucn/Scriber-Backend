"""Field Checker.

Usage:
  field_checker.py [--host=HOST] [--port=PORT] [--username=USERNAME] [--password=PASSWORD] [--database=DATABASE]

Options:
  -h --help            show this help message and exit
  --host=HOST          MySQL host [default: localhost]
  --port=PORT          MySQL port [default: 3306]
  --username=USERNAME  MySQL username [default: root]
  --password=PASSWORD  MySQL password [default: ]
  --database=DATABASE  MySQL database [default: ipo_1212]
"""

import datetime
import logging
import os
import re
import time
from decimal import Decimal, InvalidOperation

import docopt
import pymysql
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

pymysql.install_as_MySQLdb()

db_session = None
date_regexps = [
    re.compile(r"\d{4}年?度?"),
    re.compile(r"\d{4}年\d{1,2}-\d{1,2}月"),
    re.compile(r"\d{4}-\d{1,2}~\d{4}-\d{1,2}"),
]
NON_VAL_RE = re.compile(r"[，,%()]")

SELECT_QUERY = "SELECT * FROM {};"

table_cn_name = {
    "file": "文件信息",
    "compliance": "合规性结果",
    "director_information": "董事基本情况",
    "major_lawsuit": "重大诉讼事项",
    "fund_raising": "募集资金与运用",
    "patent": "专利",
    "issuer_information": "发行人相关信息",
    "major_client": "主要客户",
    "major_supplier": "主要供应商",
    "major_contract": "重大合同",
    "issuer_profession": "发行人所处行业",
    "profitability": "盈利能力",
    "balance": "资产负债表",
    "cash_flow": "现金流量表",
    "income": "利润表",
    "main_financial_indicators": "主要财务指标表",
    "actual_controller_info": "实际控制人情况",
    "paraphrase": "释义",
    "controlling_shareholder_info": "控股股东情况",
    "supervisor_information": "监事基本情况",
    "management_information": "高管基本情况",
    "core_technician_info": "核心技术人员基本情况",
}


class FieldChecker:
    @staticmethod
    def base_check(table_name, checkers):
        """
        对table_name表查出来的每一条记录的字段进行检查
        :param table_name: 表名
        :param checkers: {字段名: check_func ...}
        :return:
        """
        logging.info("%s check %s(%s)%s", "-" * 20, table_name, table_cn_name[table_name], "-" * 20)
        rows = db_session.execute(SELECT_QUERY.format(table_name)).fetchall()
        for row in rows:
            for key, value in row.items():
                check_func = checkers.get(key)
                if not check_func:
                    continue
                check_res = check_func(key, value)
                if not check_res:
                    logging.error(
                        "Detect Wrong Field: Table: %s, row: %s, column: %s, value: %s, checker: %s",
                        table_name,
                        row["pkey"],
                        key,
                        value,
                        check_func.__name__,
                    )

    @staticmethod
    def _check_actual_controller_info(table_name):
        checkers = {
            "pledged_shares": check_number,
            "direct_holding_ratio": check_number,
            "indirect_holding_ratio": check_number,
            "identity_number": check_regex,
            "type": lambda k, x: x in ["国有控股主体", "自然人", "其他"],
        }
        FieldChecker.base_check(table_name, checkers)

    @staticmethod
    def _check_balance(table_name):
        number_columns = [
            "cash_and_bank",
            "provision_for_settlement_fund",
            "funds_lent",
            "financial_assets_held_for_trading",
            "notes_receivable",
            "accounts_receivable",
            "advances_to_customers",
            "insurance_premiums_receivables",
            "reinsurance_receivables",
            "provision_for_reinsurance_receivables",
            "interest_receivables",
            "dividend_receivables",
            "other_receivables",
            "buy_back_resale_financial_assets",
            "inventories",
            "non_current_assets_due_within_one_year",
            "other_current_assets",
            "total_current_assets",
            "loans_and_payments",
            "available_for_sale_financial_assets",
            "held_to_maturity_investments",
            "long_term_receivables",
            "long_term_equity_investments",
            "investment_real_estates",
            "fixed_assets_original_cost",
            "construction_in_progress",
            "construction_supplies",
            "fixed_assets_pending_disposal",
            "bearer_biological_assets",
            "oil_and_natural_gas_assets",
            "intangible_assets",
            "research_and_development_costs",
            "goodwill",
            "long_term_deferred_expenses",
            "deferred_tax_assets",
            "other_non_current_assets",
            "total_non_current_assets",
            "total_assets",
            "short_term_borrowings",
            "borrowings_from_central_bank",
            "deposits_from_customers_and_interbank",
            "deposit_funds",
            "financial_assets_held_for_liabilities",
            "notes_payable",
            "accounts_payable",
            "advances_from_customers",
            "funds_from_sales_of_repurchasement_agreement",
            "handling_charges_and_commissions_payable",
            "employee_benefits_payable",
            "taxes_and_surcharges_payable",
            "interests_payable",
            "dividend_payables",
            "other_payables",
            "reinsurance_premiums_payables",
            "provision_for_insurance_contracts",
            "funds_received_as_agent_of_stock_exchange",
            "funds_received_as_stock_underwrite",
            "non_current_liabilities_maturing_within_one_year",
            "other_current_liabilities",
            "total_currennt_liabilities",
            "long_term_loans",
            "debentures_payables",
            "long_term_payables",
            "specific_payables",
            "accrued_liabilities",
            "deferred_tax_liabilities",
            "other_non_current_liabilities",
            "total_non_current_liabilities",
            "total_liabilities",
            "registered_capital",
            "capital_surplus",
            "less_treasury_stock",
            "special_reserve",
            "surplus_reserve",
            "provision_for_normal_risks",
            "undistributed_profits",
            "exchange_differences_on_translating_foreign_operations",
            "total_owners_equity_belongs_to_parent_company",
            "minority_interest",
            "total_owners_equity",
            "total_liabilities_and_owners_equity",
        ]
        checkers = {key: check_number for key in number_columns}
        checkers["currency_unit"] = lambda k, x: x == "万元"
        checkers["report_date"] = check_date
        FieldChecker.base_check(table_name, checkers)

    @staticmethod
    def _check_cash_flow(table_name):
        number_columns = [
            "cash_flows_from_operating_activities",
            "cash_received_from_the_sales_of_goods_and_services",
            "net_increase_in_deposits_and_placements_from_inter_bank",
            "net_increase_in_loan_from_central_bank",
            "net_increase_in_funds_borrowed_from_other_financial_institutions",
            "cash_premiums_received_on_original_insurance_contracts",
            "cash_received_from_re_insurance_business",
            "net_increase_in_deposits_and_investments_from_insurers",
            "net_increase_in_disposal_of_trading_financial_assets",
            "interest_handling_charges_and_commissions_received",
            "net_increase_in_funds_deposit",
            "net_increase_in_repurchase_agreement_business_funds",
            "receipts_of_tax_refunds",
            "other_cash_received_relating_to_operating_activities",
            "sub_total_of_cash_inflows_from_operating_activities",
            "cash_payments_for_goods_purchased_and_services_received",
            "net_increase_in_loans_and_payments_on_behalf",
            "net_increase_in_deposits_with_centre_bank_and_interbank",
            "payments_of_claims_for_original_insurance_contracts",
            "interests_handling_charges_and_commissions_paid",
            "commissions_on_insurance_policies_paid",
            "cash_payments_to_and_on_behalf_of_employees",
            "payments_of_all_types_of_taxes",
            "other_cash_payments_relating_to_operating_activities",
            "sub_total_of_cash_outflows_from_operating_activities",
            "net_cash_flows_from_operating_activities",
            "cash_flows_from_investing_activities",
            "cash_received_from_disposals_and_withdraw_on_investment",
            "cash_received_from_returns_on_investments",
            "net_cash_received_from_disposals_of_fa_ia_and_long_term_assets",
            "net_cash_received_from_disposals_of_subsidiaries",
            "other_cash_received_relating_to_investing_activities",
            "sub_total_of_cash_inflows_from_investing_activities",
            "cash_payments_for_fa_ia_and_long_term_assets",
            "cash_payments_to_acquire_investments",
            "net_increase_in_secured_loans",
            "net_cash_payments_for_acquisitions_of_subsidiaries_and_others",
            "other_cash_payments_relating_to_investing_activities",
            "sub_total_of_cash_outflows_from_investing_activities",
            "net_cash_flows_from_investing_activities",
            "cash_flows_from_financing_activities",
            "cash_received_from_investment",
            "including_cash_received_from_issuing_shares_of_minority",
            "cash_received_from_borrowings",
            "proceeds_from_issuance_of_bonds",
            "other_cash_received_relating_to_financing_activities",
            "sub_total_of_cash_inflows_from_financing_activities",
            "cash_repayments_of_amounts_borrowed",
            "cash_payments_for_distribution_of_dividends_or_profits",
            "including_subsidiaries_payment_to_minority_for_dividends_profits",
            "other_cash_payments_relating_to_financing_activities",
            "sub_total_of_cash_outflows_from_financing_activities",
            "net_cash_flows_from_financing_activities",
            "foreign_exchange_rate_changes_on_cash_and_cash_equivalents",
            "net_increase_in_cash_and_cash_equivalents",
            "plus_cash_and_cash_equivalents_at_beginning_of_period",
            "cash_and_cash_equivalents_at_end_of_period",
        ]
        checkers = {key: check_number for key in number_columns}
        checkers["currency_unit"] = lambda k, x: x == "万元"
        checkers["report_date"] = check_date
        FieldChecker.base_check(table_name, checkers)

    @staticmethod
    def _check_compliance(table_name):
        pass

    @staticmethod
    def _check_controlling_shareholder_info(table_name):
        checkers = {
            "direct_holding_ratio": check_number,
            "indirect_holding_ratio": check_number,
            "nature_of_business": check_nature_of_business,
            "identity_number": check_regex,
            "type": lambda k, x: x in ["法人", "自然人", "其他"],
        }
        FieldChecker.base_check(table_name, checkers)

    @staticmethod
    def _check_core_technician_info(table_name):
        checkers = {
            "name": None,
            "nationality": check_nationality,
            "overseas_residency": check_has_or_not,
            "gender": check_gender,
            "date_of_birth": check_date,
            "education": check_education,
            "job_title": None,
            "current_title": None,
            "start_date": check_date,
            "end_date": check_date,
        }
        FieldChecker.base_check(table_name, checkers)

    @staticmethod
    def _check_director_information(table_name):
        checkers = {
            "name": None,
            "nationality": check_nationality,
            "overseas_residency": check_has_or_not,
            "gender": check_gender,
            "date_of_birth": check_date,
            "education": check_education,
            "job_title": None,
            "current_title": None,
            "start_date": check_date,
            "end_date": check_date,
        }
        FieldChecker.base_check(table_name, checkers)

    @staticmethod
    def _check_file(table_name):
        pass

    @staticmethod
    def _check_fund_raising(table_name):
        checkers = {"total_investment": check_number, "investment_of_fund_raised": check_number}
        FieldChecker.base_check(table_name, checkers)

    @staticmethod
    def _check_income(table_name):
        number_columns = [
            "overall_sales",
            "revenues",
            "interest_income",
            "insurance_premiums_earned",
            "handling_charges_and_commissions_income",
            "overall_costs",
            "costs_of_sales",
            "interest_expenses",
            "handling_charges_and_commissions_expenses",
            "refund_of_insurance_premiums",
            "net_payments_for_insurance_claims",
            "net_provision_for_insurance_contracts",
            "commissions_on_insurance_policies",
            "reinsurance_charges",
            "sales_tax_and_additions",
            "selling_and_distribution_expenses",
            "general_and_administrative_expenses",
            "financial_expenses",
            "impairment_loss_on_assets",
            "plus_gain_or_loss_from_changes_in_fair_values",
            "investment_income",
            "including_investment_income_from_joint_ventures_and_affiliates",
            "gain_or_loss_on_foreign_exchange_transactions",
            "gross_profit",
            "plus_non_operating_profit",
            "less_non_operating_expenses",
            "including_losses_from_disposal_of_non_current_assets",
            "profit_before_tax",
            "less_income_tax_expenses",
            "net_profit",
            "including_profit_earned_before_consolidation",
            "net_profit_belonging_to_parent_company",
            "minority_interest",
            "earnings_per_share",
            "basic_earnings_per_share",
            "diluted_earnings_per_share",
            "other_comprehensive_income",
            "comprehensive_income",
            "comprehensive_income_belong_to_parent_company",
            "comprehensive_income_belong_to_minority_shareholders",
        ]
        checkers = {key: check_number for key in number_columns}
        checkers["currency_unit"] = lambda k, x: x == "万元"
        checkers["report_date"] = check_date
        FieldChecker.base_check(table_name, checkers)

    @staticmethod
    def _check_issuer_information(table_name):
        regex_columns = ["unified_social_credit_code", "organization_code", "email", "post_code"]
        none_columns = ["company_name", "name_of_legal_representative", "registered_address", "office_address"]

        regex_checkers = {key: check_regex for key in regex_columns}
        none_checkers = {key: None for key in none_columns}
        checkers = {
            "date_of_establishment": check_date,
            "registered_capital": None,
        }
        checkers.update(regex_checkers)
        checkers.update(none_checkers)
        FieldChecker.base_check(table_name, checkers)

    @staticmethod
    def _check_issuer_profession(table_name):
        checkers = {
            "industry_classification_standard": check_industry_class_std,
            "industry_classification_code": check_industry_class_code,
            "industry_classification_name": check_industry_class_name,
        }
        FieldChecker.base_check(table_name, checkers)

    @staticmethod
    def _check_main_financial_indicators(table_name):
        number_columns = [
            "current_ratio",
            "quick_ratio",
            "asset_to_liability_ratio_parent_company",
            "asset_to_liability_ratio_consolidated",
            "intangible_assets",
            "accounts_receivable_turnover_rate",
            "inventory_turnover_rate",
            "earnings_before_interest_taxes_depreciation_and_amortization",
            "interest_coverage_multiple",
            "basic_eps_after_deducting_non_recurring_gains_and_losses",
            "cash_flow_from_operating_activities_per_share",
            "net_cash_flow_per_share",
            "weighted_average_return_on_equity",
        ]
        checkers = {key: check_number for key in number_columns}
        checkers["currency_unit"] = lambda k, x: x == "万元"
        checkers["report_date"] = check_date

        FieldChecker.base_check(table_name, checkers)

    @staticmethod
    def _check_major_client(table_name):
        checkers = {
            "time": check_date,
            "currency_unit": check_currency_unit,
            "name_customers": None,
            "subordinate_unit_name": None,
            "sales": check_number,
            "proportion_of_main_income": check_number,
            "proportion_of_operating_income": check_number,
        }
        FieldChecker.base_check(table_name, checkers)

    @staticmethod
    def _check_major_contract(table_name):
        checkers = {
            "currency_unit": check_currency_unit,
            "types_of_contracts": None,
            "name_of_counter_parties": None,
            "underlying_assets": None,
            "contract_amount": None,
            "amount_fullfilled": check_number,
            "performance_period": None,
            "comment": None,
        }
        FieldChecker.base_check(table_name, checkers)

    @staticmethod
    def _check_major_lawsuit(table_name):
        checkers = {
            "currency_unit": check_currency_unit,
            "issues": None,
            "prosecution_party": None,
            "defending_party": None,
            "joint_and_several_liability": None,
            "litigation_arbitration_type": None,
            "amount_involved": None,
            "estimated_debt_amount": check_number,
        }
        FieldChecker.base_check(table_name, checkers)

    @staticmethod
    def _check_major_supplier(table_name):
        checkers = {
            "time": check_date,
            "currency_unit": check_currency_unit,
            "name_of_suppliers": None,
            "items_purchased": None,
            "purchase_amount": check_number,
            "proportion_of_total_purchase_amount": check_number,
        }
        FieldChecker.base_check(table_name, checkers)

    @staticmethod
    def _check_management_information(table_name):
        checkers = {
            "name": None,
            "nationality": check_nationality,
            "overseas_residency": check_has_or_not,
            "gender": check_gender,
            "date_of_birth": check_date,
            "education": check_education,
            "job_title": None,
            "current_title": None,
            "start_date": check_date,
            "end_date": check_date,
        }
        FieldChecker.base_check(table_name, checkers)

    @staticmethod
    def _check_paraphrase(table_name):
        checkers = {"abbreviation": None, "full_name": None}
        FieldChecker.base_check(table_name, checkers)

    @staticmethod
    def _check_patent(table_name):
        checkers = {
            "patent_type": None,
            "patent_name": None,
            "patent_number": None,
            "patent_owner": None,
            "cost_of_patent": check_number,
            "latest_book_value_at_the_end_of_the_latest_period": check_number,
            "date_of_acquisiton": check_date,
            "period_of_use": None,
            "disputes_over_ownership": check_yes_or_no,
        }
        FieldChecker.base_check(table_name, checkers)

    @staticmethod
    def _check_profitability(table_name):
        checkers = {
            "currency_unit": check_currency_unit,
            "table_date": check_date,
            "amount": check_number,
            "proportion": check_number,
            "movement": check_number,
            "product_type": None,
            "business_type": None,
            "composition_type": None,
        }
        FieldChecker.base_check(table_name, checkers)

    @staticmethod
    def _check_supervisor_information(table_name):
        checkers = {
            "name": None,
            "nationality": check_nationality,
            "overseas_residency": check_has_or_not,
            "gender": check_gender,
            "date_of_birth": check_date,
            "education": check_education,
            "job_title": None,
            "current_title": None,
            "start_date": check_date,
            "end_date": check_date,
        }
        FieldChecker.base_check(table_name, checkers)


def check_nonempty(field, value, fields):
    """
    不能为空
    :param field:
    :param value:
    :param fields:
    :return:
    """
    return bool(value)


def check_percentage(field, number, fields, allow_none=True):
    """
    在满足check_number的基础上，需含有%
    :param field:
    :param number:
    :param fields:
    :param allow_none:
    :return:
    """
    if allow_none and not number:
        return True
    if "%" not in number:
        return False
    return check_number(field, number, fields, allow_none)


def check_number(field, number, fields, allow_none=True):
    """
    检查数字类型是否
        1. 保留两位小数
        2. 是否每3位加一个英文逗号

    ps 允许在末尾含有货币单位
    :param number:
    :return:
    """
    p_unit = re.compile(
        r"""([十百千万亿美欧日港英加镑盾卢布先令比索元]*
                            |(USD)|(JPY)|(EUR)|(Euro)|(人民币)|(印度卢比)|(越南盾)|(肯尼亚先令)|(印尼卢比)|(加拿大元)|(新台币)|(泰铢)|(美金))$""",
        re.X,
    )
    # allow_none = False
    if allow_none and not number:
        return True
    if number == "-":
        return True
    try:
        number = p_unit.sub("", number)

        value = normalize_val(number)
        if "%" in number:
            transfer_value = comma_sep_thousands(value, percentage=True, decimal_places=2)
        else:
            transfer_value = comma_sep_thousands(value, decimal_places=2)
        if number == transfer_value:
            return True
        else:
            return transfer_value
    except Exception:
        return False


def check_date(field, date, fields):
    """
    是否符合2020-11-15的样式
    特例白名单:至今
    :param field:
    :param date:
    :param fields:
    :return:
    """
    if not date:
        return False
    if date in ["至今"]:
        return True
    ldate = len(date)
    for date_regexp in date_regexps:
        match = date_regexp.search(date)
        if match and match.end() - match.start() == ldate:
            return True

    # 2018-01-01
    if ldate > 10:
        return False
    try:
        if 7 < ldate <= 10:
            datetime.datetime.strptime(date, "%Y-%m-%d")
        elif 4 < ldate <= 7:
            datetime.datetime.strptime(date, "%Y-%m")
        else:
            datetime.datetime.strptime(date, "%Y")
    except Exception:
        return False
    return True


def get_regex(key):
    regex_map = {
        "unified_social_credit_code": re.compile(r"^[0-9A-Z]{18}$"),
        "organization_code": re.compile(r"^[0-9A-z]{8}$"),
        "phone_number": re.compile(r"^[0-9]{11}|[(（]?[0-9]{3,4}[)）]?-?[0-9]{7,9}|[0-9]{2}-[0-9]{2}-[0-9]{8}$"),
        "fax_number": re.compile(r"^[0-9]{11}|[0-9]{3,4}-*[0-9]{7,9}$"),
        "email": re.compile(r"(.*?)@(.*?)\.(.{2,3})$"),
        "post_code": re.compile(r"^[0-9]{6}$"),
        "identity_number": re.compile(r"^[0-9a-zA-Z()*]+$"),
    }
    return regex_map[key]


def check_regex(field, text, fields):
    """
    是否满足特定的正则表达式，如：
    邮政编码:6位数字
    手机号码:11位数字
    传真号码:11位数字
    统一社会信用代码:18位数字&大写字母
    组织机构代码:8位数字&字母
    电子邮件:abc@xyz.mn
    证件号码:任意长度的数字&字母&()*

    :param field:
    :param text:
    :param fields:
    :return:
    """
    if not text:
        return True
    regex = get_regex(field)
    if regex.search(text):
        return True
    return False


def check_currency_unit(field, unit, fields):
    """
    暂未检查
    :param field:
    :param unit:
    :param fields:
    :return:
    """
    # return not unit or unit == '万元'
    return True


def check_yes_or_no(field, text, fields):
    """
    是否属于 ['是', '否']
    :param field:
    :param text:
    :param fields:
    :return:
    """
    return not text or text in ["是", "否"]


def check_has_or_not(field, text, fields):
    """
    是否属于 ['有', '无']
    :param field:
    :param text:
    :param fields:
    :return:
    """
    return not text or text in ["有", "无"]


def check_gender(field, text, fields):
    """
    是否属于 ['男', '女']
    :param field:
    :param text:
    :param fields:
    :return:
    """
    return not text or text in ["男", "女"]


def known_nationality():
    known = (
        "菲律宾|荷兰|法国|奥地利|圣基茨和尼维斯联邦|中国澳门|中国|美国|加拿大|中国台湾|中国香港|新加坡|澳大利亚|日本|英国|意大利|马来西亚|韩国|新西兰|葡萄牙|瑞士|德国|印度|比利时|其他"
        "|多米尼加"
    )
    return format_string(known).split("|")


def check_nationality(field, text, fields):
    """
    是否在给定的枚举范围内
    :param field:
    :param text:
    :param fields:
    :return:
    """
    if not text:
        return True
    known_list = known_nationality()
    for item in text.split(";"):
        if item not in known_list:
            return False
    return True


def check_education(field, text, fields):
    """
    是否在给定的枚举范围内
    :param field:
    :param text:
    :param fields:
    :return:
    """
    if not text:
        return True
    known = "本科|硕士|大专|博士|高中|中专|初中|EMBA|研究生|博士研究生|专科|MBA|MPAcc|博士后|其他"
    known_list = format_string(known).split("|")
    for item in text.split(";"):
        if item not in known_list:
            return False
    return True


def known_current_title():
    known = """董事|副总经理|总经理|监事|董事会秘书|财务总监|董事长|监事会主席|副总裁|职工监事|总裁|总经理助理|总工程师|财务负责人|经理|副董事长|执行董事|常务副总经理|副行长|工会主席|
               党委书记|党委副书记|副行长|发行人监事会主席|行长|副总工程师|党委委员|高级副总裁|外部监事|技术总监|执行委员会委员|首席财务官|行政部经理|发行人财务总监|销售部部长|财务经理|
               党委副书记|执行总裁|合伙人|副总经理|高级合伙人|纪委书记|主任|人力资源总监|研发总监|销售总监|技术中心主任|首席行政官|非执行董事|首席技术官|事务代表|副董事长|投资执行事务合伙人|
               总会计师|事务合伙人|首席战略官|行政法务负责人|办公室主任|其他"""
    return format_string(known).split("|")


def check_current_title(field, text, fields):
    """
    是否在给定的枚举范围内
    :param field:
    :param text:
    :param fields:
    :return:
    """
    if not text:
        return True
    known_list = known_current_title()
    for item in text.split(";"):
        if item not in known_list:
            return False
    return True


def check_job_title(field, text, fields):
    """
    是否在给定的枚举范围内
    :param field:
    :param text:
    :param fields:
    :return:
    """
    if not text:
        return True
    known = """工程师|会计师|高级工程师|教授|高级经济师|经济师|高级会计师|研究员|技术员|讲师|中级会计师|总工程师|副教授|中级工程师|总会计师|注册税务师|正高级经济师|政工师|审计师|高级政工师|
               正高级工程师|研究员级高级工程师|副总工程师|高级审计师|注册会计师高级会计师|会计员|国际商务师|城市规划师|特许金融分析师|畜牧兽医师|注册资产评估师|中级审计师|总经济师|技师|统计员|
               国家一级注册建造师|高级工程师助理工程师|正高级会计师|研发工程师|高级工程师总工程师|教授级高级工程师总工程师|高级经营师|中级经济师|二级建造师|中国注册税务师|高级国际财务管理师|
               工程师任总工程师|高级企业文化师|研究院副总工程师|计量工程师|高级建筑师|机械工程师|教授级高级工程师注册一级建造师|高级工程师副总工程师|软件工程师|人力资源管理师|审计员|
               一级注册建造师|高级国际商务师|电子信息技术工程师|中国注册会计师中级会计师|高级人力资源管理师|高级会计师中国注册资产评估师|高级工程师工程师|二级人力资源管理师|副总会计师|
               质量工程师|药师|电气工程师|高级工程师副总经理兼总工程师|中级策划师|助理讲师|中国注册会计师高级经营师|注册会计师注册税务师|资深注册会计师|其他"""

    known_list = format_string(known).split("|")
    for item in text.split(";"):
        if item not in known_list:
            return False
    return True


def check_litigation_type(field, text, fields):
    """
    是否在给定的枚举范围内
    :param field:
    :param text:
    :param fields:
    :return:
    """
    if not text:
        return True
    known = (
        "民事诉讼|民事调解书|民事判决|民事起诉|代理合同纠纷|民事调解|民事裁定|借款合同纠纷|买卖合同纠纷|货款合同纠纷|贷款违约纠纷|财产损害赔偿纠纷|股权转让诉讼|劳动报酬纠纷|行政诉讼|"
        "侵权诉讼|侵犯专利权|债权|商标|产品责任纠纷|解散纠纷|劳动纠纷|买卖合同纠纷及反诉|侵害作品信息网络传播权纠纷|保证合同纠纷|员工竞业限制纠纷|票据追索权纠纷|其他|借款纠纷|"
        "期货经纪合同纠纷|借贷案|财产保全|货款纠纷|中小企业集合私募债券承销协议纠纷|购销合同纠纷|港口纠纷|港口货物保管合同纠纷|贷款纠纷|游戏版权纠纷和不正当竞争纠纷|债权转让合同纠纷|"
        "强行平仓纠纷|房屋买卖合同纠纷|商标权纠纷|行政纠纷|著作权纠纷 |票据纠纷|物业服务合同纠纷|公司解散纠纷|确认合同效力纠纷|软件著作权侵权纠纷|偿债申索纠纷|广告合同纠纷|"
        "承揽加工合同纠纷|技术秘密纠纷|超短融及中票纠纷|安装合同纠纷|融资融券业务纠纷|龙山国际委托贷款纠纷|实现担保物权纠纷|股权转让纠纷|认购权协议纠纷|交通事故责任纠纷|劳动争议纠纷|"
        "劳动合同纠纷|抵债资产纠纷|侵害商标权纠纷|侵害外观设计专利权纠纷|人身损害赔偿纠纷|设备采购纠纷|设工程施工合同纠纷|私募债违约纠纷|经销合同纠纷|金融借款合同纠纷|仓储合同纠纷)|其他"
    )
    known_list = format_string(known).split("|")
    return text in known_list


def known_industry_classification_standard():
    known = """《上市行业分类指引》（2012年修订）|《国民经济行业分类》（GB/T4754-2002）|《国民经济行业分类》（GB/T4754-2011）|《国民经济行业分类》（GB/T4754-2017）|《上市行业分类指引》|
    《国民经济行业分类》|《战略性新兴产业重点产品和服务指导目录（2016版）》|《高收缩涤纶牵伸丝Q/320582LJT5-2014》|《文化及相关产业分类（2018）》|《北京市文化创意产业分类标准》|
    国家统计局发布的《文化及相关产业分类（2012）》|《仿生涤纶异形牵伸丝Q/320582LJT7-2016》|《产业结构调整指导目录（2011年本）》|《非金融机构支付服务管理办法》|《挂牌管理型行业分类指引》|
    《战略性新兴产业重点产品和服务指导目录》（2016年版）| 其他"""
    return format_string(known).split("|")


def check_industry_class_std(field, text, fields):
    """
    是否在给定的枚举范围内
    :param field:
    :param text:
    :param fields:
    :return:
    """
    if not text:
        return True
    known_list = known_industry_classification_standard()
    return text in known_list


def known_industry_classification_code():
    known = """A1|A11|A111|A112|A113|A119|A12|A121|A122|A123|A13|A131|A132|A133|A134|A14|A141|A142|A143|A149|A15|A151|A152|A153|A154|A159|A16|A161|A162|A163|
        A164|A169|A17|A171|A179|A18|A181|A182|A19|A190|A2|A21|A211|A212|A22|A220|A23|A231|A232|A24|A241|A242|A25|A251|A252|A3|A31|A311|A312|A313|A314|A315|A319|
        A32|A321|A322|A323|A329|A33|A330|A39|A391|A392|A399|A4|A41|A411|A412|A42|A421|A422|A5|A51|A511|A512|A513|A514|A515|A519|A52|A521|A522|A523|A529|A53|A531|
        A532|A539|A54|A541|A549|B10|B101|B1011|B1012|B1013|B1019|B102|B1020|B103|B1030|B109|B1091|B1092|B1093|B1099|B11|B111|B1110|B112|B1120|B119|B1190|B12|B120
        |B1200|B6|B61|B610|B62|B620|B69|B690|B7|B71|B711|B712|B72|B721|B722|B8|B81|B810|B82|B820|B89|B890|B9|B91|B911|B912|B913|B914|B915|B916|B917|B919|B92
        |B921|B922|B929|B93|B931|B932|B933|B939|C13|C131|C1311|C1312|C1313|C1314|C1319|C132|C1321|C1329|C133|C1331|C1332|C134|C1340|C135|C1351|C1352|C1353|C136
        |C1361|C1362|C1363|C1369|C137|C1371|C1372|C1373|C139|C1391|C1392|C1393|C1399|C14|C141|C1411|C1419|C142|C1421|C1422|C143|C1431|C1432|C1433|C1439|C144
        |C1441|C1442|C1449|C145|C1451|C1452|C1453|C1459|C146|C1461|C1462|C1469|C149|C1491|C1492|C1493|C1494|C1495|C1499|C15|C151|C1511|C1512|C1513|C1514|C1515
        |C1519|C152|C1521|C1522|C1523|C1524|C1525|C1529|C153|C1530|C16|C161|C1610|C162|C1620|C169|C1690|C17|C171|C1711|C1712|C1713|C172|C1721|C1722|C1723|C173
        |C1731|C1732|C1733|C174|C1741|C1742|C1743|C175|C1751|C1752|C176|C1761|C1762|C1763|C177|C1771|C1772|C1773|C1779|C178|C1781|C1782|C1783|C1784|C1789|C18
        |C181|C1811|C1819|C182|C1821|C1829|C183|C1830|C19|C191|C1910|C192|C1921|C1922|C1923|C1929|C193|C1931|C1932|C1939|C194|C1941|C1942|C195|C1951|C1952|C1953
        |C1954|C1959|C20|C201|C2011|C2012|C2013|C2019|C202|C2021|C2022|C2023|C2029|C203|C2031|C2032|C2033|C2034|C2035|C2039|C204|C2041|C2042|C2043|C2049|C21
        |C211|C2110|C212|C2120|C213|C2130|C214|C2140|C219|C2190|C22|C221|C2211|C2212|C222|C2221|C2222|C2223|C223|C2231|C2239|C23|C231|C2311|C2312|C2319|C232
        |C2320|C233|C2330|C24|C241|C2411|C2412|C2413|C2414|C2419|C242|C2421|C2422|C2423|C2429|C243|C2431|C2432|C2433|C2434|C2435|C2436|C2437|C2438|C2439|C244
        |C2441|C2442|C2443|C2444|C2449|C245|C2451|C2452|C2453|C2454|C2455|C2456|C2459|C246|C2461|C2462|C2469|C25|C251|C2511|C2519|C252|C2521|C2522|C2523|C2524
        |C2529|C253|C2530|C254|C2541|C2542|C26|C261|C2611|C2612|C2613|C2614|C2619|C262|C2621|C2622|C2623|C2624|C2625|C2629|C263|C2631|C2632|C264|C2641|C2642
        |C2643|C2644|C2645|C2646|C265|C2651|C2652|C2653|C2659|C266|C2661|C2662|C2663|C2664|C2665|C2666|C2667|C2669|C267|C2671|C2672|C268|C2681|C2682|C2683|C2684
        |C2689|C27|C271|C2710|C272|C2720|C273|C2730|C274|C2740|C275|C2750|C276|C2761|C2762|C277|C2770|C278|C2780|C28|C281|C2811|C2812|C282|C2821|C2822|C2823
        |C2824|C2825|C2826|C2829|C283|C2831|C2832|C29|C291|C2911|C2912|C2913|C2914|C2915|C2916|C2919|C292|C2921|C2922|C2923|C2924|C2925|C2926|C2927|C2928|C2929
        |C30|C301|C3011|C3012|C302|C3021|C3022|C3023|C3024|C3029|C303|C3031|C3032|C3033|C3034|C3039|C304|C3041|C3042|C3049|C305|C3051|C3052|C3053|C3054|C3055
        |C3056|C3057|C3059|C306|C3061|C3062|C307|C3071|C3072|C3073|C3074|C3075|C3076|C3079|C308|C3081|C3082|C3089|C309|C3091|C3099|C31|C311|C3110|C312|C3120|C313
        |C3130|C314|C3140|C32|C321|C3211|C3212|C3213|C3214|C3215|C3216|C3217|C3218|C3219|C322|C3221|C3222|C3229|C323|C3231|C3232|C3239|C324|C3240|C325|C3251
        |C3252|C3253|C3254|C3259|C33|C331|C3311|C3312|C332|C3321|C3322|C3323|C3324|C3329|C333|C3331|C3332|C3333|C334|C3340|C335|C3351|C3352|C3353|C3359|C336
        |C3360|C337|C3371|C3372|C3373|C3379|C338|C3381|C3382|C3383|C3389|C339|C3391|C3392|C3393|C3394|C3399|C34|C341|C3411|C3412|C3413|C3414|C3415|C3419|C342
        |C3421|C3422|C3423|C3424|C3425|C3429|C343|C3431|C3432|C3433|C3434|C3435|C3436|C3437|C3439|C344|C3441|C3442|C3443|C3444|C3445|C3446|C345|C3451|C3452|C3453
        |C3459|C346|C3461|C3462|C3463|C3464|C3465|C3466|C3467|C347|C3471|C3472|C3473|C3474|C3475|C3479|C348|C3481|C3482|C3483|C3484|C3489|C349|C3491|C3492|C3493
        |C3499|C35|C351|C3511|C3512|C3513|C3514|C3515|C3516|C3517|C352|C3521|C3522|C3523|C3524|C3525|C3529|C353|C3531|C3532|C3533|C3534|C354|C3541|C3542|C3543
        |C3544|C3545|C3546|C3549|C355|C3551|C3552|C3553|C3554|C356|C3561|C3562|C3563|C3569|C357|C3571|C3572|C3573|C3574|C3575|C3576|C3577|C3579|C358|C3581|C3582
        |C3583|C3584|C3585|C3586|C3587|C3589|C359|C3591|C3592|C3593|C3594|C3595|C3596|C3597|C3599|C36|C361|C3611|C3612|C362|C3620|C363|C3630|C364|C3640|C365
        |C3650|C366|C3660|C367|C3670|C37|C371|C3711|C3712|C3713|C3714|C3715|C3716|C3719|C372|C3720|C373|C3731|C3732|C3733|C3734|C3735|C3736|C3737|C3739|C374
        |C3741|C3742|C3743|C3744|C3749|C375|C3751|C3752|C376|C3761|C3762|C377|C3770|C378|C3780|C379|C3791|C3792|C3799|C38|C381|C3811|C3812|C3813|C3819|C382|C3821
        |C3822|C3823|C3824|C3825|C3829|C383|C3831|C3832|C3833|C3834|C3839|C384|C3841|C3842|C3843|C3844|C3849|C385|C3851|C3852|C3853|C3854|C3855|C3856|C3857|C3859
        |C386|C3861|C3862|C3869|C387|C3871|C3872|C3873|C3874|C3879|C389|C3891|C3899|C39|C391|C3911|C3912|C3913|C3914|C3915|C3919|C392|C3921|C3922|C393|C3931
        |C3932|C3933|C3934|C3939|C394|C3940|C395|C3951|C3952|C3953|C396|C3961|C3962|C3963|C3964|C3969|C397|C3971|C3972|C3973|C3974|C3975|C3976|C3979|C398|C3981
        |C3982|C3983|C3984|C3985|C3989|C399|C3990|C40|C401|C4011|C4012|C4013|C4014|C4015|C4016|C4019|C402|C4021|C4022|C4023|C4024|C4025|C4026|C4027|C4028|C4029
        |C403|C4030|C404|C4040|C405|C4050|C409|C4090|C41|C411|C4111|C4119|C412|C4120|C419|C4190|C42|C421|C4210|C422|C4220|C43|C431|C4310|C432|C4320|C433|C4330
        |C434|C4341|C4342|C4343|C4349|C435|C4350|C436|C4360|C439|C4390|D44|D441|D4411|D4412|D4413|D4414|D4415|D4416|D4417|D4419|D442|D4420|D443|D4430|D45|D451
        |D4511|D4512|D4513|D452|D4520|D46|D461|D4610|D462|D4620|D463|D4630|D469|D4690|E47|E471|E4710|E472|E4720|E479|E4790|E48|E481|E4811|E4812|E4813|E4814|E4819
        |E482|E4821|E4822|E4823|E483|E4831|E4832|E4833|E4834|E4839|E484|E4840|E485|E4851|E4852|E4853|E486|E4861|E4862|E4863|E487|E4871|E4872|E4873|E4874|E4875
        |E4879|E489|E4891|E4892|E4893|E4899|E49|E491|E4910|E492|E4920|E499|E4991|E4999|E50|E501|E5011|E5012|E5013|E502|E5021|E5022|E503|E5030|E509|E5090|F51|F511
        |F5111|F5112|F5113|F5114|F5115|F5116|F5117|F5119|F512|F5121|F5122|F5123|F5124|F5125|F5126|F5127|F5128|F5129|F513|F5131|F5132|F5133|F5134|F5135|F5136
        |F5137|F5138|F5139|F514|F5141|F5142|F5143|F5144|F5145|F5146|F5147|F5149|F515|F5151|F5152|F5153|F5154|F516|F5161|F5162|F5163|F5164|F5165|F5166|F5167|F5168
        |F5169|F517|F5171|F5172|F5173|F5174|F5175|F5176|F5177|F5178|F5179|F518|F5181|F5182|F5183|F5184|F5189|F519|F5191|F5192|F5193|F5199|F52|F521|F5211|F5212
        |F5213|F5219|F522|F5221|F5222|F5223|F5224|F5225|F5226|F5227|F5229|F523|F5231|F5232|F5233|F5234|F5235|F5236|F5237|F5238|F5239|F524|F5241|F5242|F5243|F5244
        |F5245|F5246|F5247|F5248|F5249|F525|F5251|F5252|F5253|F5254|F5255|F526|F5261|F5262|F5263|F5264|F5265|F5266|F5267|F527|F5271|F5272|F5273|F5274|F5279|F528
        |F5281|F5282|F5283|F5284|F5285|F5286|F5287|F5289|F529|F5291|F5292|F5293|F5294|F5295|F5296|F5297|F5299|G53|G531|G5311|G5312|G5313|G532|G5320|G533|G5331
        |G5332|G5333|G5339|G54|G541|G5411|G5412|G5413|G5414|G5419|G542|G5421|G5422|G5429|G543|G5431|G5432|G5433|G5434|G5435|G5436|G5437|G5438|G5439|G544|G5441
        |G5442|G5443|G5449|G55|G551|G5511|G5512|G5513|G552|G5521|G5522|G5523|G553|G5531|G5532|G5539|G56|G561|G5611|G5612|G562|G5621|G5622|G5623|G5629|G563|G5631
        |G5632|G5639|G57|G571|G5710|G572|G5720|G58|G581|G5810|G582|G5821|G5822|G5829|G59|G591|G5910|G592|G5920|G593|G5930|G594|G5941|G5942|G5949|G595|G5951|G5952
        |G5959|G596|G5960|G599|G5990|G60|G601|G6010|G602|G6020|G609|G6090|H61|H611|H6110|H612|H6121|H6129|H613|H6130|H614|H6140|H619|H6190|H62|H621|H6210|H622
        |H6220|H623|H6231|H6232|H6233|H6239|H624|H6241|H6242|H629|H6291|H6299|I63|I631|I6311|I6312|I6319|I632|I6321|I6322|I633|I6331|I6339|I64|I641|I6410|I642
        |I6421|I6422|I6429|I643|I6431|I6432|I6433|I6434|I6439|I644|I6440|I645|I6450|I649|I6490|I65|I651|I6511|I6512|I6513|I6519|I652|I6520|I653|I6531|I6532|I654
        |I6540|I655|I6550|I656|I6560|I657|I6571|I6572|I6579|I659|I6591|I6599|J66|J661|J6610|J662|J6621|J6622|J6623|J6624|J6629|J663|J6631|J6632|J6633|J6634|J6635
        |J6636|J6637|J6639|J664|J6640|J665|J6650|J67|J671|J6711|J6712|J672|J6720|J673|J6731|J6732|J6739|J674|J6741|J6749|J675|J6750|J676|J6760|J679|J6790|J68
        |J681|J6811|J6812|J6813|J6814|J682|J6820|J683|J6830|J684|J6840|J685|J6851|J6852|J6853|J686|J6860|J687|J6870|J689|J6890|J69|J691|J6911|J6919|J692|J6920
        |J693|J6930|J694|J6940|J695|J6950|J699|J6991|J6999|K70|K701|K7010|K702|K7020|K703|K7030|K704|K7040|K709|K7090|L71|L711|L7111|L7112|L7113|L7114|L7115
        |L7119|L712|L7121|L7122|L7123|L7124|L7125|L7129|L713|L7130|L72|L721|L7211|L7212|L7213|L7214|L7215|L7219|L722|L7221|L7222|L7223|L7224|L7229|L723|L7231
        |L7232|L7239|L724|L7241|L7242|L7243|L7244|L7245|L7246|L7249|L725|L7251|L7259|L726|L7261|L7262|L7263|L7264|L7269|L727|L7271|L7272|L7279|L728|L7281|L7282
        |L7283|L7284|L7289|L729|L7291|L7292|L7293|L7294|L7295|L7296|L7297|L7298|L7299|M73|M731|M7310|M732|M7320|M733|M7330|M734|M7340|M735|M7350|M74|M741|M7410
        |M742|M7420|M743|M7431|M7432|M7439|M744|M7441|M7449|M745|M7451|M7452|M7453|M7454|M7455|M7459|M746|M7461|M7462|M7463|M747|M7471|M7472|M7473|M7474|M7475
        |M748|M7481|M7482|M7483|M7484|M7485|M7486|M749|M7491|M7492|M7493|M7499|M75|M751|M7511|M7512|M7513|M7514|M7515|M7516|M7517|M7519|M752|M7520|M753|M7530
        |M754|M7540|M759|M7590|N76|N761|N7610|N762|N7620|N763|N7630|N764|N7640|N769|N7690|N77|N771|N7711|N7712|N7713|N7714|N7715|N7716|N7719|N772|N7721|N7722
        |N7723|N7724|N7725|N7726|N7727|N7729|N78|N781|N7810|N782|N7820|N783|N7830|N784|N7840|N785|N7850|N786|N7861|N7862|N7869|N79|N791|N7910|N792|N7920|N793
        |N7930|N794|N7940|N799|N7990|O80|O801|O8010|O802|O8020|O803|O8030|O804|O8040|O805|O8051|O8052|O8053|O806|O8060|O807|O8070|O808|O8080|O809|O8090|O81|O811
        |O8111|O8112|O8113|O8114|O812|O8121|O8122|O8129|O813|O8131|O8132|O819|O8191|O8192|O8193|O8199|O82|O821|O8211|O8219|O822|O8221|O8222|O8223|O8224|O8229
        |O829|O8290|P83|P831|P8310|P832|P8321|P8322|P833|P8331|P8332|P8333|P8334|P8335|P8336|P834|P8341|P8342|P835|P8350|P839|P8391|P8392|P8393|P8394|P8399|Q84
        |Q841|Q8411|Q8412|Q8413|Q8414|Q8415|Q8416|Q842|Q8421|Q8422|Q8423|Q8424|Q8425|Q843|Q8431|Q8432|Q8433|Q8434|Q8435|Q8436|Q849|Q8491|Q8492|Q8499|Q85|Q851
        |Q8511|Q8512|Q8513|Q8514|Q8515|Q8516|Q8519|Q852|Q8521|Q8522|Q8529|R86|R861|R8610|R862|R8621|R8622|R8623|R8624|R8625|R8626|R8629|R87|R871|R8710|R872|R8720
        |R873|R8730|R874|R8740|R875|R8750|R876|R8760|R877|R8770|R88|R881|R8810|R882|R8820|R883|R8831|R8832|R884|R8840|R885|R8850|R886|R8860|R887|R8870|R889|R8890
        |R89|R891|R8911|R8912|R8919|R892|R8921|R8929|R893|R8930|R899|R8991|R8992|R8999|R90|R901|R9011|R9012|R9013|R9019|R902|R9020|R903|R9030|R904|R9041|R9042
        |R9049|R905|R9051|R9052|R9053|R9054|R9059|R909|R9090|S91|S910|S9100|S92|S921|S9210|S922|S9221|S9222|S9223|S9224|S9225|S9226|S923|S9231|S9232|S929|S9291
        |S9299|S93|S931|S9310|S932|S9320|S94|S941|S9411|S9412|S9413|S9414|S9415|S9419|S942|S9420|S949|S9490|S95|S951|S9511|S9512|S9513|S9519|S952|S9521|S9522
        |S9529|S953|S9530|S954|S9541|S9542|S96|S961|S9610|S962|S9620|T97|T970|T9700 """
    return format_string(known).split("|")


def check_industry_class_code(field, text, fields):
    """
    是否在给定的枚举范围内
    :param field:
    :param text:
    :param fields:
    :return:
    """
    if not text:
        return True
    known_list = known_industry_classification_code()
    return text in known_list


def known_industry_classification_name():
    known = """碳酸饮料制造|皮革鞣制加工|自动售货机零售|游乐园|煤炭加工|其他金属工具制造|拖拉机制造|学前教育|人民法院|其他人造板制造|纺织服装、服饰业|金属制日用品制造|口腔科用设备及器具制造|
        木材和竹材采运|财务公司服务|建筑工程用机械制造|互联网安全服务|机床功能部件及附件制造|铜压延加工|合成橡胶制造|互联网信息服务|钨钼冶炼|金属加工机械制造|数字内容服务|经济事务管理机构|
        地下综合管廊工程建筑|证券市场管理服务|专科医院|家用制冷电器具制造|其他家用电力器具制造|自行车修理|广播电视设备制造|餐饮业|洗浴和保健养生服务|饮料及冷饮服务|信息系统集成和物联网技术服务|
        矿产品、建材及化工产品批发|生物基、淀粉基新材料制造|货币经纪公司服务|绿化管理|宠物服务|其他组织管理服务|小吃服务|娱乐船和运动船制造|风能原动设备制造|创业投资基金|图书出版|
        人民政协、民主党派|棉、麻、糖、烟草种植|其他电子元件制造|纤维素纤维原料及纤维制造|集装箱及金属包装容器制造|畜牧良种繁殖活动|金属工具制造|食用菌加工|土地登记代理服务|其他未列明金融业|
        工业颜料制造|农作物病虫害防治活动|软件和信息技术服务业|卫星传输服务|其他农牧产品批发|房地产业|文化娱乐经纪人|餐饮配送服务|塑料人造革、合成革制造|雕塑工艺品制造|气象服务|典当|水力发电|
        年金保险|物业管理|日用品出租|农、林、牧、渔产品批发|毛皮鞣制加工|房屋建筑业|检测服务|宝石、玉石采选|信托公司|维纶纤维制造|渔业产品批发|汽车金融公司服务|陶瓷、石材装饰材料零售|
        五金、家具及室内装饰材料专门零售|其他制造业|其他未列明国家机构|林业产品批发|其他通用设备制造业|专项化学用品制造|健身器材制造|贵金属矿采选|其他提供住宿社会救助|木竹材加工机械制造|
        毛织造加工|基层医疗卫生服务|泵及真空设备制造|集成电路设计|汽车用发动机制造|半导体分立器件制造|其他工艺美术及礼仪用品制造|照明灯具制造|食用植物油加工|生活用燃料零售|厨具卫具及日用杂品批发|
        日用家电零售|危险化学品仓储|味精制造|电车制造|滚动轴承制造|其他乐器及零件制造|其他商务服务业|基层群众自治组织及其他组织|光学仪器制造|石棉及其他非金属矿采选|火力发电工程施工|远洋货物运输|
        建筑用木料及木材组件加工|其他家具制造|研究和试验发展|其他畜牧业|缝制机械制造|其他文化艺术业|陈设艺术陶瓷制造|互联网和相关服务|牲畜屠宰|技术推广服务|钨钼矿采选|宗教活动场所服务|
        铁路运输辅助活动|航空旅客运输|褐煤开采洗选|咨询与调查|食品、饮料、烟草及饲料生产专用设备制造|其他建筑安装业|糕点、面包零售|化学农药制造|砖瓦、石材等建筑材料制造|废弃资源综合利用业|
        金属密封件制造|农、林、牧、渔专业及辅助性活动|疗养院|其他常用有色金属矿采选|医药及医疗器材批发|配电开关控制设备制造|支撑软件开发|计算机、软件及辅助设备批发|成人初中教育|其他道路运输辅助活动|
        其他合成纤维制造|政策性银行服务|期货市场服务|其他化工产品批发|其他体育场地设施管理|保险中介服务|法律服务|其他土木工程建筑施工|工程勘察活动|疾病预防控制中心|灯用电器附件及其他照明器具制造|
        焰火、鞭炮产品制造|非融资担保服务|图书、报刊零售|其他水利管理业|工伤保险|钟表、眼镜零售|塑料鞋制造|柑橘类种植|针织或钩针编织服装制造|资本市场服务|核子及核辐射测量仪器制造|
        医学生产用信息化学品制造|环境保护监测|知识产权服务|其他群众团体|西乐器制造|灯具、装饰物品批发|特殊教育|医疗用品及器材批发|电气设备修理|专科疾病防治院（所、站）|含乳饮料和植物蛋白饮料制造|
        音响设备制造|其他文化艺术经纪代理|照明器具生产专用设备制造|木门窗制造|石棉制品制造|微特电机及组件制造|工艺美术颜料制造|其他电工器材制造|运输设备及生产用计数仪表制造|天然草原割草|
        糖果、巧克力及蜜饯制造|蜜蜂饲养|有色金属冶炼和压延加工业|纺织品、针织品及原料批发|酒、饮料及茶叶零售|智能无人飞行器制造|农用及园林用金属工具制造|铁路工程建筑|鞋帽批发|
        其他农、林、牧、渔业机械制造|其他综合管理服务|社会公共安全设备及器材制造|核电工程施工|涤纶纤维制造|内陆养殖|其他航空运输辅助活动|其他毛皮制品加工|城市轨道交通|运输代理业|广播|机场|蔬菜加工|
        篷、帆布制造|书、报刊印刷|能源矿产地质勘查|其他烟草制品制造|玻璃包装容器制造|橡胶和塑料制品业|食品、酒、饮料及茶生产专用设备制造|空中交通管理|营养和保健品零售|土木工程建筑业|集成电路制造|
        体育用品及器材零售|计算机和办公设备维修|教学专用仪器制造|资本投资服务|绢纺和丝织加工|毛皮服装加工|鞋帽零售|热力生产和供应|阀门和旋塞制造|纸和纸板容器制造|其他技术推广服务|其他电子器件制造|
        其他机械与设备经营租赁|老年人、残疾人养护服务|卷烟制造|建筑用石加工|锌锰电池制造|其他通用零部件制造|石油和天然气开采业|广告业|塑料丝、绳及编织品制造|中医医院|补充保险|客运轮渡运输|电视机制造|
        麻染整精加工|其他法律服务|金属制餐具和器皿制造|环境卫生管理|金属成形机床制造|铁路专用设备及器材、配件制造|切削工具制造|实验分析仪器制造|果品、蔬菜零售|皮革、毛皮及其制品加工专用设备制造|
        酒的制造|其他仪器仪表制造业|丝绢纺织及印染精加工|危险货物道路运输|铁路、船舶、航空航天等运输设备修理|广播电视传输服务|玻璃纤维及制品制造|水产捕捞|其他水泥类似制品制造|其他水产品加工|啤酒制造|
        单板加工|齿轮及齿轮减、变速箱制造|球类制造|应用电视设备及其他广播电视设备制造|石油、煤炭及其他燃料加工业|金属及金属矿批发|新材料技术推广服务|室内娱乐活动|其他金融业|娃娃玩具制造|
        互联网公共服务平台|其他基础化学原料制造|会计、审计及税务服务|银行监管服务|铁路机车车辆配件制造|水产品冷冻加工|海底设施铺设工程建筑|锅炉及原动设备制造|防水建筑材料制造|其他房屋建筑业|
        烟草生产专用设备制造|音像制品出租|染料制造|互联网游戏服务|增材制造装备制造|中西医结合医院|铁路、船舶、航空航天和其他运输设备制造业|通用航空服务|其他饮料及冷饮服务|电气安装|汽车车身、挂车制造|
        危险废物治理|羊的饲养|助动车制造|汽柴油车整车制造|互联网接入及相关服务|豆类种植|体育组织|中药饮片加工|农副食品加工业|瓶（罐）装饮用水制造|其他产业用纺织制成品制造|石墨及其他非金属矿物制品制造|
        宠物饲料加工|职业初中教育|图书批发|专用化学产品制造|肥料制造|水产品罐头制造|电力生产|城市公共交通运输|文体设备和用品出租|石墨及碳素制品制造|社会看护与帮助服务|电气设备批发|贸易代理|本册印制|
        证券期货监管服务|电子真空器件制造|天然气开采|包装专用设备制造|食品制造业|米、面制品制造|广播电视卫星传输服务|铝冶炼|基因工程药物和疫苗制造|管道运输业|干部休养所|文艺创作与表演|
        隔热和隔音材料制造|海洋油气资源开发利用工程建筑|船舶及相关装置制造|普通高中教育|文教、工美、体育和娱乐用品制造业|机制纸及纸板制造|航空客货运输|船舶拆除|海上旅客运输|纤维板制造|劳务派遣服务|
        软木制品及其他木制品制造|其他游览景区管理|核力发电|复混肥料制造|民主党派|环境治理业|中央银行服务|公路管理与养护|普通铁路旅客运输|棉织造加工|广播、电视、电影和录音制作业|生物药品制造|
        黄酒制造|灯具零售|棉花加工机械制造|电光源制造|镍氢电池制造|其他未列明通用设备制造业|合成材料制造|城市轨道交通工程建筑|石油及制品批发|有机化学原料制造|化妆品制造|基本医疗保险|道路运输辅助活动|
        其他未列明制造业|家具零售|医药制造业|麻纺织及染整精加工|皮革、毛皮、羽毛及其制品和制鞋业|互联网批发|冶金专用设备制造|采盐|仪器仪表制造业|陶瓷制品制造|加工纸制造|体育用品设备出租|
        环境与生态监测检测服务|机织服装制造|运动休闲针织服装制造|木材加工和木、竹、藤、棕、草制品业|客运火车站|饼干及其他焙烤食品制造|通用设备修理|农副食品加工专用设备制造|水的生产和供应业|综合零售|
        家具制造业|玻璃纤维增强塑料制品制造|棉纺织及印染精加工|速冻食品制造|石灰石、石膏开采|果菜汁及果菜汁饮料制造|农产品初加工活动|机械设备经营租赁|化学药品制剂制造|飞机制造|粮油零售|其他饲料加工|
        社会保障|危险品仓储|铁路、道路、隧道和桥梁工程建筑|风动和电动工具制造|计算机、通信和其他电子设备制造业|意外伤害保险|麻纤维纺前加工和纺纱|建筑陶瓷制品制造|方便食品制造|石灰和石膏制造|
        其他采矿业|土地调查评估服务|互联网数据服务|房地产中介服务|大型货物道路运输|电工仪器仪表制造|计算机外围设备制造|货运港口|体育场馆建筑|煤炭开采和洗选专业及辅助性活动|图书馆与档案馆|
        其他航空航天器制造|有机肥料及微生物肥料制造|茶馆服务|其他调味品、发酵制品制造|货运火车站（场）|其他农业专业及辅助性活动|游览景区管理|宠物食品用品零售|其他安全保护服务|漆器工艺品制造|
        其他文化、办公用机械制造|内燃机及配件制造|塑料加工专用设备制造|银矿采选|药用辅料及包装材料|妇联|对外事务管理机构|麻织造加工|其他物料搬运设备制造|塑料家具制造|厨具卫具及日用杂品零售|
        其他畜牧专业及辅助性活动|家具和相关物品修理|冷冻饮品及食用冰制造|其他宠物服务|广播电视接收设备制造|房地产租赁经营|科技推广和应用服务业|水力发电工程施工|非专业视听设备制造|电信|
        其他金属制日用品制造|铅蓄电池制造|其他办公设备维修|其他未列明建筑业|窄轨机车车辆制造|正餐服务|盐及调味品批发|园区管理服务|生物质能发电|化学矿开采|工程和技术研究和试验发展|光学玻璃制造|内河货物运输|导航、测绘、气象及海洋专用仪器制造|互联网平台|试验机制造|照相机及器材制造|服饰制造|其他资本市场服务|建筑物清洁服务|口腔清洁用品制造|其他污染治理|其他水的处理、利用与分配|环境污染处理专用药剂材料制造|液力动力机械元件制造|橡胶鞋制造|广播电视节目制作及发射设备制造|密封用填料及类似品制造|鱼糜制品及水产品干腌制加工|职业技能培训|稀有稀土金属矿采选|木片加工|纺织专用设备制造|文化活动服务|儿童乘骑玩耍的童车类产品制造|医疗设备经营租赁|铁合金冶炼|玩具制造|水资源专用机械制造|其他机械和设备修理业|自然科学研究和试验发展|无机盐制造|其他农副食品加工|生物质燃料加工|期刊出版|家禽饲养|商业银行服务|足浴服务|蔬菜种植|其他文化用品零售|茶饮料及其他饮料制造|木质装饰材料零售|其他渔业专业及辅助性活动|建筑幕墙装饰和装修|公共设施管理业|临终关怀服务|烟草制品批发|航标器材及其他相关装置制造|基础地质勘查|科技中介服务|噪声与振动控制服务|智能车载设备制造|计算机整机制造|绘图、计算及测量仪器制造|核燃料加工|其他方便食品制造|铅锌矿采选|其他卫生活动|电容器及其配套设备制造|福利彩票服务|报纸出版|常用有色金属冶炼|零售业|玻璃制造|稀有稀土金属冶炼|社会经济咨询|天使投资|化妆品及卫生用品批发|海洋天然气及可燃冰开采|其他日用产品修理业|镍钴冶炼|制药专用设备制造|土砂石开采|保险业|通信设备零售|饲料生产专用设备制造|鱼油提取及制品制造|花卉种植|金融信息服务|交通及公共管理用金属标牌制造|其他纸制品制造|律师及相关法律服务|计算机和辅助设备修理|文化体育娱乐活动与经纪代理服务|铜冶炼|茶叶种植|镁冶炼|保险资产管理|石油开采|糖果、巧克力制造|玻璃保温容器制造|检验检疫服务|道路运输业|化肥批发|谷物种植|城市公园管理|风力发电|胶合板制造|教育|金属工艺品制造|缫丝加工|质检技术服务|皮革服装制造|多式联运|其他机织服装制造|场地准备活动|煤制合成气生产|铝压延加工|塑料板、管、型材制造|制糖业|高铁设备、配件制造|农、林、牧、渔专用机械制造|针织或钩针编织物印染精加工|医学研究和试验发展|生育保险|货运枢纽（站）|专业公共卫生服务|针织或钩针编织物及其制品制造|体育用品及器材批发|水污染治理|道路货物运输|互联网科技创新平台|小麦种植|其他未包括金融业|歌舞厅娱乐活动|其他食品零售|毛皮鞣制及制品加工|羽毛（绒）制品加工|坚果、含油果、香料和饮料作物种植|家用电器修理|环保工程施工|羽毛（绒）加工|管道工程建筑|港口及航运设施工程建筑|常用有色金属矿采选|紧固件制造|图书出租|其他煤炭采选|控股公司服务|文化、体育用品及器材批发|锑矿采选|化学原料和化学制品制造业|宠物食品用品批发|陆地石油开采|不提供住宿社会工作|含油果种植|非金融机构支付服务|其他自然保护|社会人文科学研究|健身休闲活动|公共电汽车客运|文化用信息化学品制造|信息系统集成服务|铸造及其他金属制品制造|其他通用仪器制造|陆地天然气开采|印刷专用设备制造|化纤织造加工|五金零售|生物基化学纤维制造|综合医院|图书馆|其他贵金属冶炼|煤炭开采和洗选业|日用电器修理|航空货物运输|石墨、滑石采选|半导体照明器件制造|机械化农业及园艺机具制造|生态保护|文化会展服务|烘炉、熔炉及电炉制造|中等职业学校教育|日用陶瓷制品制造|体育会展服务|船舶改装|文化用品设备出租|园艺陶瓷制造|调味品、发酵制品制造|精炼石油产品制造|小麦加工|互联网广告服务|教学用模型及教具制造|体育场馆管理|影视节目制作|丝印染精加工|农业专业及辅助性活动|洗涤机械制造|竹材采运|坚果种植|液化石油气生产和供应业|果品、蔬菜批发|光电子器件制造|交通安全、管制及类似专用设备制造|其他国家机构|其他园艺作物种植|生产专用车辆制造|草种植及割草|氨纶纤维制造|石棉水泥制品制造|节能环保工程施工|其他食品制造|化纤织物染整精加工|肉、禽类罐头制造|医疗诊断、监护及治疗设备制造|互联网生产服务平台|基础化学原料制造|塑料制品业|洗浴服务|皮革制品制造|窗帘、布艺类产品制造|日用杂品制造|谷物仓储|塑胶玩具制造|船用配套设备制造|普通货物道路运输|医疗仪器设备及器械制造|其他林业专业及辅助性活动|金矿采选|毛染整精加工|卫生材料及医药用品制造|固定电信服务|麻类种植|其他水上运输辅助活动|烘炉、风机、包装等设备制造|租赁业|名胜风景区管理|人力资源服务|棉花种植|食用菌种植|搪瓷日用品及其他搪瓷制品制造|集装箱制造|工业自动控制系统装置制造|翻译服务|金属玩具制造|竹、藤家具制造|燃气及类似能源家用器具制造|工程管理服务|机动车燃气零售|体育彩票服务|电子器件制造|休闲娱乐用品设备出租|文化艺术培训|纺织、服装及家庭用品批发|中国共产党机关|林业有害生物防治活动|其他住宿业|粘土及其他土砂石开采|纺织带和帘子布制造|其他房地产业|平板玻璃制造|林业|棉花仓储|其他批发业|金属制品业|土地规划服务|电玩具制造|市场管理服务|商务代理代办服务|水轮机及辅机制造|自然遗迹保护管理|毛条和毛纱线加工|水上运输辅助活动|金属制品、机械和设备修理业|其他科技推广服务业|文教办公用品制造|工会|粘土砖瓦及建筑砌块制造|信息技术咨询服务|其他肥料制造|隧道施工专用机械制造|稀有稀土金属压延加工|家用电力器具专用配件制造|铁路运输设备修理|刀剪及类似日用金属工具制造|玻璃制品制造|非金属废料和碎屑加工处理|精制茶加工|植物园管理服务|电阻电容电感元件制造|显示器件制造|森林改培|银冶炼|电子测量仪器制造|金融资产管理公司|水果和坚果加工|集装箱道路运输|包装服务|化纤浆粕制造|建筑物拆除和场地准备活动|烈士陵园、纪念馆|棉、麻批发|酒精制造|其他食品批发|黑色金属冶炼和压延加工业|货币银行服务|禽类屠宰|包装装潢及其他印刷|林木育种|炼油、化工生产专用设备制造|音像制品出版|街道卫生院|手工具制造|固体饮料制造|木竹材林产品采集|植物油加工|市政设施管理|农业机械批发|高速铁路旅客运输|金属包装容器及材料制造|邮政业|贵金属压延加工|其他货币银行服务|陆地管道运输|铁矿采选|农业科学研究和试验发展|群众文体活动|轻质建筑材料制造|电力电子元器件制造|造纸和纸制品业|其他测绘地理信息服务|抽纱刺绣工艺品制造|鸡的饲养|特殊作业机器人制造|原油加工及石油制品制造|绳、索、缆制造|金属切割及焊接设备制造|其他未列明食品制造|刨花板制造|机动车充电销售|木地板制造|电影和广播电视节目发行|公共就业服务|体育场地设施管理|电视|水下救捞装备制造|殡葬服务|营林及木竹采伐机械制造|种子种苗培育活动|生态资源监测|乳粉制造|珠宝首饰零售|畜牧机械制造|其他专用化学产品制造|锰矿、铬矿采选|铁路运输维护活动|涂料制造|风能发电工程施工|其他玻璃制品制造|葡萄酒制造|其他未列明农副食品加工|文化、体育用品及器材专门零售|畜牧业|狩猎和捕捉动物|橡胶板、管、带制造|行业性团体|非电力家用器具制造|建筑装饰和装修业|供应链管理服务|其他机械设备及电子产品批发|黑色金属铸造|宠物寄托收养服务|烟草制品业|生物基材料制造|教育辅助服务|非金属矿及制品批发|安全、消防用金属制品制造|改装汽车制造|民宿服务|化学试剂和助剂制造|互联网搜索服务|海底管道运输|航空、航天器及设备制造|其他出版业|组织管理服务|人造板制造|电子和电工机械专用设备制造|贵金属冶炼|互联网零售|广播影视设备批发|其他玻璃制造|工业与专业设计及其他专业技术服务|生物质燃气生产和供应业|其他危险品仓储|计量服务|家用清洁卫生电器具制造|医疗、外科及兽医用器械制造|其他未列明非金属矿采选|保险经纪服务|谷物、豆及薯类批发|证券经纪交易服务|冷藏车道路运输|汽车整车制造|水产品加工|金属表面处理及热处理加工|其他开采专业及辅助性活动|屠宰及肉类加工|兽医服务|酒、饮料和精制茶制造业|木竹浆制造|沿海货物运输|电子元件及电子专用材料制造|可穿戴智能设备制造|电子游艺厅娱乐活动|金属家具制造|森林经营、管护和改培|林业专业及辅助性活动|音像制品、电子和数字出版物批发|乡镇卫生院|物联网技术服务|锅炉及辅助设备制造|畜禽粪污处理活动|住宅装饰和装修|营养食品制造|单位后勤管理服务|建筑装饰、装修和其他建筑业|有色金属合金制造|蛋品加工|其他合成材料制造|半导体器件专用设备制造|污水处理及其再生利用|动漫、游戏数字内容服务|地质勘查技术服务|其他文体设备和用品出租|电气信号设备装置制造|汽车租赁|电池制造|门诊部（所）|其他牲畜饲养|烟草种植|深海石油钻探设备制造|煤制品制造|建筑装饰及水暖管道零件制造|其他土木工程建筑|融资租赁服务|清洁服务|草及其他制品制造|首饰、工艺品及收藏品批发|信息处理和存储支持服务|汽车、摩托车等修理与维护|其他互联网平台|服务消费机器人制造|档案馆|人寿保险|铁路运输业|建筑工程机械与设备经营租赁|博物馆|运动防护用具制造|计算器及货币专用设备制造|野生动物保护|海水养殖|通信终端设备制造|发电机及发电机组制造|稻谷种植|广播电视专用配件制造|电子电路制造|野生植物保护|国家机构|木质家具制造|水上运输业|糕点、糖果及糖批发|摩托车制造|其他人力资源服务|记录媒介复制|日用化工专用设备制造|文化艺术业|其他稀有金属冶炼|林木育种和育苗|广播电视集成播控|家用厨房电器具制造|城市轨道交通设备制造|文具用品零售|其他电池制造|硅冶炼|房地产开发经营|中药材种植|其他保险活动|木材加工|专用设备修理|其他电子产品零售|白酒制造|日用玻璃制品制造|光纤制造|新能源车整车制造|医院|乳制品制造|其他未列明体育|盐加工|灌溉活动|架线和管道工程建筑|养生保健服务|其他日用品生产专用设备制造|金属制厨房用器具制造|其他寄递服务|其他道路、隧道和桥梁工程建筑|燃气生产和供应业|皮鞋制造|其他餐饮业|非食用植物油加工|印刷、制药、日化及日用品生产专用设备制造|弹簧制造|牛的饲养|其他彩票服务|衡器制造|箱包零售|模具制造|其他谷物磨制|其他金融信托与管理服务|橡胶制品业|农村资金互助社服务|其他电力生产|信用合作社服务|工艺美术品及收藏品零售|镍钴矿采选|海底隧道工程建筑|无机碱制造|棕制品制造|海洋能源开发利用工程建筑|其他数字内容服务|机械设备、五金产品及电子产品批发|气压动力机械及元件制造|床上用品制造|其他常用有色金属冶炼|通信设备制造|通用设备制造业|液压动力机械及元件制造|蔬菜、食用菌及园艺作物种植|生产专用起重机制造|普通初中教育|高铁车组制造|幻灯及投影设备制造|合成纤维制造|棉纺纱加工|其他海洋工程建筑|固体矿产地质勘查|电影放映|竹制品制造|其他农产品仓储|电线、电缆制造|纸浆制造|自行车制造|小额贷款公司服务|土地登记服务|烟草制品零售|内陆捕捞|计算机、软件及辅助设备零售|国际组织|网吧活动|铸造机械制造|中药零售|数字出版|运行维护服务|涂料、油墨、颜料及类似产品制造|农村集体经济组织管理|木质制品制造|日用家电批发|急救中心（站）服务|其他未列明日用产品修理业|生态保护和环境治理业|鬃毛加工、制刷及清扫工具制造|保险监管服务|葡萄种植|渔业|木材采运|智能照明器具制造|其他木材加工|摩托车整车制造|生产专用搪瓷制品制造|牲畜饲养|其他未列明专业技术服务业|化纤织造及印染精加工|体育表演服务|竹、藤、棕、草等制品制造|其他贵金属矿采选|锦纶纤维制造|农林牧渔专用仪器仪表制造|体育健康服务|珠宝首饰及有关物品制造|专业音响设备制造|制冷、空调设备制造|其他运输代理业|金属制卫生器具制造|公开募集证券投资基金|电子乐器制造|玉米加工|住宅房屋建筑|潜水救捞及其他未列明运输设备制造|建筑物拆除活动|其他公路客运|其他原油制造|其他未列明电气机械及器材制造|社会工作|营养和保健品批发|酒吧服务|汽车零部件及配件制造|航天相关设备制造|猪的饲养|其他软件开发|动物园、水族馆管理服务|种子批发|航空航天器修理|水资源管理|太阳能发电工程施工|仪器仪表修理|咖啡馆服务|工矿工程建筑|行政监督检查机构|其他城市公共交通运输|炼铁|烟煤和无烟煤开采洗选|皮手套及皮装饰制品制造|烟叶复烤|专项运动器材及配件制造|机械式停车设备制造|环保技术推广服务|纸制品制造|天然植物纤维编织工艺品制造|无机酸制造|照明器具制造|制鞋业|管道和设备安装|村卫生室|建材批发|人造纤维（纤维素纤维）制造|宗教组织|消费金融公司服务|铁路机车车辆制造|轮胎制造|搬家运输|其他一般旅馆|服装批发|运动机织服装制造|贸易经纪与代理|金属门窗制造|稀土金属矿采选|公证服务|报刊批发|护理机构服务|文物及非物质文化遗产保护|鱼苗及鱼种场活动|森林经营和管护|农林牧渔技术推广服务|其他期货市场服务|其他服务业|海洋工程建筑|铝矿采选|财产保险|其他传动部件制造|家用电器及电子产品专门零售|海洋环境服务|物料搬运设备制造|一般旅馆|照相器材零售|铅锌冶炼|林产品初级加工活动|草种植|医疗用品及器材零售|农业机械活动|其他社会保障|防洪除涝设施管理|杂粮加工|自行车和残疾人座车制造|环保咨询|公路工程建筑|化妆品及卫生用品零售|其他非货币银行服务|其他文化用品批发|客运索道制造|其他家庭用品批发|铜矿采选|基金会|办公服务|摩托车零部件及配件制造|生物质致密成型燃料加工|家用美容、保健护理电器具制造|矿山机械制造|客运港口|健康咨询|采矿、冶金、建筑专用设备制造|其他未列明教育|核辐射加工|油墨及类似产品制造|服装零售|焙烤食品制造|产业用纺织制成品制造|艺术品代理|野生动物疫源疫病防控监测|其他未列明零售业|城乡市容管理|稻谷加工|票务代理服务|旅游饭店|其他陶瓷制品制造|水利和水运工程建筑|潜水装备制造|外卖送餐服务|其他家用纺织制成品制造|有色金属压延加工|钾肥制造|其他智能消费设备制造|信息安全设备制造|其他电信服务|体校及体育培训|旅行社及相关服务|快递服务|体育咨询|创业空间服务|通用航空生产服务|煤气生产和供应业|节能技术推广服务|资源与产权交易服务|毛纺织及染整精加工|农业机械经营租赁|邮件包裹道路运输|电影机械制造|成人小学教育|其他日用杂品制造|石油和天然气开采专业及辅助性活动|移动电信服务|其他家禽饲养|娱乐业|呼叫中心|临床检验服务|体育经纪人|化学药品原料药制造|泡沫塑料制造|地理遥感信息服务|炸药、火工及焰火产品制造|社区居民自治组织|其他综合零售|公共建筑装饰和装修|艺术表演场馆|炼焦|石油钻采专用设备制造|商业综合体管理服务|人民检察院|低温仓储|电力工程施工|其他金属加工机械制造|安全系统监控服务|科技会展服务|金属丝绳及其制品制造|中等教育|旅客票务代理|技能培训、教育辅助及其他教育|纺织业|其他非金属矿物制品制造|其他仓储业|海洋石油开采|通讯设备修理|其他中药材种植|制镜及类似品加工|金冶炼|其他道路货物运输|汽轮机及辅机制造|兽用药品制造|社区卫生服务中心（站）|其他未列明服务业|饲料加工|体育|专业技术服务业|其他铁路运输辅助活动|婚姻服务|综合管理服务|专用仪器仪表制造|有线广播电视传输服务|其他未列明畜牧业|金属结构制造|摄影扩印服务|城际铁路旅客运输|托儿所服务|有色金属矿采选业|酱油、食醋及类似制品制造|食品、饮料及烟草制品专门零售|其他未列明运输设备制造|通信系统设备制造|谷物磨制|石膏、水泥制品及类似制品制造|造纸|提供住宿社会工作|其他日用品零售|工程技术与设计服务|健康保险|其他专用设备制造|炼钢|罐头食品制造|休闲观光活动|有色金属铸造|肉、禽、蛋、奶及水产品零售|其他非电力家用器具制造|游艺用品及室内游艺器材制造|海水捕捞|涂料零售|康复辅具适配服务|其他体育用品制造|家用电力器具制造|针织或钩针编织物织造|互联网其他信息服务|人民政协|其他电子专用设备制造|合成纤维单（聚合）体制造|锂离子电池制造|塑料零件及其他塑料制品制造|规划设计管理|光伏设备及元器件制造|餐饮配送及外卖送餐服务|玻璃、陶瓷和搪瓷制品生产专用设备制造|其他输配电及控制设备制造|便利店零售|国家权力机构|建筑安装业|群众团体|建筑材料生产专用机械制造|舞台及场地用灯制造|泵、阀门、压缩机及类似机械制造|其他未列明卫生服务|生态保护工程施工|大型车辆装备修理与维护|残疾人座车制造|其他非公开募集证券投资基金|动物用药品零售|洗染服务|太阳能器具制造|机械治疗及病房护理设备制造|其他清洁服务|长途客运|液体乳制造|电动机制造|园林绿化工程施工|其他黑色金属矿采选|海洋服务|林产化学产品制造|笔的制造|文具用品批发|专业设计服务|家用电子产品修理|应用软件开发|工业机器人制造|航天器及运载火箭制造|其他娱乐业|邮政专用机械及器材制造|牲畜批发|艺术品、收藏品拍卖|搪瓷卫生洁具制造|其他土地管理服务|助动车等修理与维护|体育场地设施安装|喷枪及类似器具制造|住宿业|印刷和记录媒介复制业|农林牧渔机械配件制造|安全保护服务|货物运输代理|货币金融服务|航空运输业|公共安全管理机构|其他电气机械及器材制造|社会团体|医疗实验室及医用消毒设备和器具制造|安全服务|企业总部管理|综合事务管理机构|其他建筑安装|金属切削机床制造|热电联产|游艺器材及娱乐用品制造|船舶修理|中药材仓储|批发业|放射性废物治理|自来水生产和供应|市场调查|非公开募集证券投资基金|新闻和出版业|金属制品修理|其他体育组织|体育航空运动服务|动物胶制造|中药批发|电工机械专用设备制造|纺织面料鞋制造|肉、禽、蛋、奶及水产品批发|环保、邮政、社会公共服务及其他专用设备制造|经济型连锁酒店|录音制作|锡矿采选|化学纤维制造业|非金属矿采选业|天然气生产和供应业|其他玩具制造|镁矿采选|纺织、服装和皮革加工专用设备制造|汽车新车零售|生物技术推广服务|铁路货物运输|砼结构构件制造|铁路运输设备制造|太阳能发电|流动货摊零售|互联网生活服务平台|水上旅客运输|制浆和造纸专用设备制造|汽车制造业|工程设计活动|雷达及配套设备制造|手工纸制造|畜牧渔业饲料批发|机动车、电子产品和日用产品修理业|旧货零售|水源及供水设施工程建筑|地质勘查专用设备制造|结构性金属制品制造|地震服务|农用薄膜批发|林木育苗|专业性团体|糕点、面包制造|银行理财服务|自行车等代步设备零售|油气仓储|机动车燃油零售|其他贸易经纪与代理|木制容器制造|非织造布制造|其他橡胶制品制造|其他非金属加工专用设备制造|旅游会展服务|计算机零部件制造|水、二氧化碳等矿产地质勘查|通讯设备批发|动物用药品批发|氮肥制造|公共自行车服务|固体废物治理|商业、饮食、服务专用设备制造|卫生|非木竹材林产品采集|电子元器件与机电组件设备制造|兔的饲养|藤制品制造|摩托车修理与维护|理发及美容服务|日用塑料制品制造|中成药生产|通用零部件制造|文具制造|土壤污染治理与修复服务|通用仓储|环境保护专用设备制造|蔬菜、菌类、水果和坚果加工|计算机制造|汽车及零配件批发|其他专业咨询与调查|家用纺织制成品制造|非金属船舶制造|日用及医用橡胶制品制造|其他制鞋业|骆驼饲养|渔业机械制造|保健食品制造|乐器零售|造林和更新|天然水收集与分配|人造草坪制造|内河旅客运输|糖料种植|食品及饲料添加剂制造|土地管理业|玻璃纤维和玻璃纤维增强塑料制品制造|复印和胶印设备制造|初级形态塑料及合成树脂制造|钢压延加工|孤残儿童收养和庇护服务|其他互联网服务|淀粉及淀粉制品制造|日用化学产品制造|森林防火活动|再生物资回收与批发|体育竞赛组织|其他电机制造|其他未列明商务服务业|汽车、摩托车、零配件和燃料及其他动力销售|航空相关设备制造|电力、热力生产和供应业|航空运输辅助活动|失业保险|建筑、家具用金属配件制造|塑料薄膜制造|光缆制造|蔬菜、水果罐头制造|云母制品制造|酒、饮料及茶叶批发|耐火土石开采|测绘地理信息服务|节能工程施工|客运汽车站|锑冶炼|其他酒制造|工业控制计算机及系统制造|开采专业及辅助性活动|水泥制品制造|玻璃仪器制造|纺织品及针织品零售|塑料包装箱及容器制造|橡胶加工专用设备制造|气体、液体分离及纯净设备制造|海洋气象服务|皮箱、包（袋）制造|生物质液体燃料生产|出版业|摩托车及零配件零售|多式联运和运输代理业|特种陶瓷制品制造|丙纶纤维制造|敏感元件及传感器制造|消防管理机构|软件开发|村民自治组织|香料作物种植|成人高中教育|无线广播电视传输服务|气体压缩机械制造|西药零售|商业养老金|认证认可服务|锡冶炼|宠物饲养|鞋和皮革修理|一般物品拍卖|创业指导服务|五金产品批发|人身保险|其他未列明金属制品制造|快餐服务|音像制品、电子和数字出版物零售|其他室内娱乐活动|水利管理业|电机制造|其他电力工程施工|汽车旧车零售|磷肥制造|仁果类和核果类水果种植|放射性金属矿采选|医药及医疗器材专门零售|黑色金属矿采选业|汽车零配件零售|非货币银行服务|观光游览航空服务|再生橡胶制造|高等教育|宠物美容服务|生物药品制品制造|初等教育|新能源技术推广服务|供应用仪器仪表制造|其他文教办公用品制造|畜牧专业及辅助性活动|电力供应|摩托车及零配件批发|共青团|土地整治服务|家用视听设备批发|邮政基本服务|计算机及通讯设备经营租赁|腈纶纤维制造|鹅的饲养|变压器、整流器和电感器制造|锻件及粉末冶金制品制造|锯材加工|城市配送|其他卫星传输服务|特种玻璃制造|其他罐头食品制造|地质勘探和地震专用仪器制造|其他电子设备制造|肉制品及副产品加工|其他通用航空服务|其他居民服务业|农药制造|滑动轴承制造|民族医院|低速汽车制造|电子专用材料制造|其他乳制品制造|石棉、云母矿采选|健康体检服务|毛巾类制品制造|印刷|装卸搬运和仓储业|稀土金属冶炼|体育保障组织|超级市场零售|其他未列明批发业|米、面制品及食用油批发|其他稀有金属矿采选|输配电及控制设备制造|乐器批发|百货零售|棉印染精加工|油料种植|弹射玩具制造|建筑装饰用石开采|其他医疗设备及器械制造|其他皮革制品制造|其他室内装饰材料零售|木楼梯制造|宗教团体服务|旅游客运|非金属矿物制品业|证券市场服务|技术玻璃制品制造|水泥、石灰和石膏制造|其他日用化学产品制造|基本保险|电子出版物出版|煤制液体燃料生产|搪瓷制品制造|其他社会团体|其他信息技术服务业|卫生陶瓷制品制造|三维（3D)打印技术推广服务|渔业专业及辅助性活动|影视录放设备制造|期货市场管理服务|橡胶零件制造|保险公估服务|轻小型起重设备制造|露营地服务|中草药种植|玉米种植|采供血机构服务|乐器制造|马的饲养|谷物、棉花等农产品仓储|文化、办公用机械制造|环境监测专用仪器仪表制造|商务服务业|化工、木材、非金属加工专用设备制造|体育中介代理服务|新闻业|信用服务|标准化服务|非公路休闲车及零配件制造|其他饮料作物种植|食品、饮料及烟草制品批发|保健辅助治疗器材零售|家用视听设备零售|其他娱乐用品制造|工业设计服务|其他广告服务|大气污染治理|非木竹浆制造|其他针织或钩针编织服装制造|其他不提供住宿社会工作|家用通风电器具制造|其他水果种植|彩票活动|游乐设施工程施工|提供施工设备服务|水文服务|绝缘制品制造|海洋工程装备制造|墨水、墨汁制造|其他运输设备修理|邮购及电视、电话零售|水产养殖|眼镜制造|金属船舶制造|职业中介服务|电气机械和器材制造业|通用仪器仪表制造|林产品采集|市政道路工程建筑|装订及印刷相关服务|其他农业|森林公园管理|电梯、自动扶梯及升降机制造|普通高等教育|普通小学教育|豆类、油料和薯类种植|居民服务业|基础软件开发|轴承、齿轮和传动部件制造|其他基本保险|自然生态系统保护管理|风机、风扇制造|农药批发|电声器件及零件制造|会议、展览及相关服务|人民法院和人民检察院|方便面制造|出租车客运|计划生育技术服务活动|其他质检技术服务|其他原动设备制造|宠物医院服务|其他未列明餐饮业|其他建筑材料制造|肥皂及洗涤剂制造|耐火陶瓷制品及其他耐火材料制造|运动场地用塑胶制造|建筑、安全用金属制品制造|装卸搬运|露天游乐场所游乐设备制造|家用空气调节器制造|其他体育|其他有色金属压延加工|体育场地设施工程施工|西药批发|专用设备制造业|其他专用仪器制造|再保险|中乐器制造|农业|其他计算机制造|保险代理服务|河湖治理及防洪设施工程建筑|汽车修理与维护|针织或钩针编织品制造|生物化学农药及微生物农药制造|工艺美术及礼仪用品制造|康复辅具制造|家庭服务|火力发电|公路旅客运输|妇幼保健院（所、站）|纺织、服装及日用品专门零售|炸药及火工产品制造|金属压力容器制造|其他煤炭加工|地质勘查|水泥制造|机械零部件加工|其他建筑、安全用金属制品制造|群众团体、社会团体和其他成员组织|饮料制造|网络借贷服务|鸭的饲养|地毯、挂毯制造|金属废料和碎屑加工处理|耐火材料制品制造|电线、电缆、光缆及电工器材制造|其他海洋服务|遥感测绘服务|架线及设备工程建筑|货摊、无店铺及其他零售业|羽毛(绒)加工及制品制造|其他未列明信息技术服务业|连续搬运设备制造|智能消费设备制造|薯类种植|成人高等教育|体育用品制造|基本养老保险|社会事务管理机构|煤炭及制品批发|香料、香精制造|金融信托与管理服务|卫生洁具零售|海水淡化处理|其他会议、会展及相关服务|水果种植|其他铁路运输设备制造|钟表与计时仪器制造|工程监理服务|建筑装饰搪瓷制品制造|电信、广播电视和卫星传输服务|香蕉等亚热带水果种植|花画工艺品制造|铁路旅客运输|蜜饯制作|投资与资产管理|水上货物运输|其他谷物种植|国家行政机构|精神康复服务|豆制品制造 """
    return format_string(known).split("|")


def check_industry_class_name(field, text, fields):
    """
    是否在给定的枚举范围内
    :param field:
    :param text:
    :param fields:
    :return:
    """
    if not text:
        return True
    known_list = known_industry_classification_name()
    return text in known_list


def known_nature_of_business():
    known = (
        "有限责任（国有独资）|中央企业|国务院国资委直属中央企业|国有独资|集体资产出资设立|有限合伙|有限责任|豁免的有限责任|股份有限公司|股份有限|贸易和投资|投资控股有限|企业法人有限责任|"
        "其他|全民所有制|根据香港法律设立并合法存续的公司|事业单位|投资有限公司|实业投资|股权投资|控股型母公司|私人豁免有限公司"
    )
    known_list = format_string(known).split("|")
    return known_list


def check_nature_of_business(field, text, fields):
    """
    是否在给定的枚举范围内
    :param field:
    :param text:
    :param fields:
    :return:
    """
    if not text:
        return True
    known_list = known_nature_of_business()
    return text in known_list


def check_nature_of_controller(field, text, fields):
    """
    是否属于['社会团体法人', '事业单位']
    补充：实际控制人类型不是自然人的,实际控制人性质为空,则有可能是错误答案
    :param field:
    :param text:
    :param fields:
    :return:
    """
    if not text:
        return fields["type"] == "自然人"  # 实际控制人类型不是自然人的,实际控制人性质为None,则有可能是错误答案
    return text in ["社会团体法人", "事业单位"]


def normalize_val(val):
    val = val.strip("¥")
    if val in ["-", "—"]:
        return 0
    if "(" in val:
        val = "-" + val
    try:
        normalized_val = Decimal(NON_VAL_RE.sub("", val))
        if "%" in val:
            return normalized_val / 100
        return normalized_val
    except ValueError:
        return None
    except InvalidOperation:
        return None


def format_string(raw_string):
    if not raw_string:
        return raw_string
    value = "".join(raw_string.strip().split())
    return value


def make_format_str(digit, decimal_places=0, percentage=False):
    format_str = ".{}f".format(decimal_places)
    if decimal_places != 0:
        if percentage:
            offset = Decimal(str(-(10 ** (-(decimal_places + 2)))))
        else:
            offset = Decimal(str(-(10 ** (-decimal_places))))
    else:
        offset = 0
    if digit <= offset:
        format_str = "-{:," + format_str + "}"
    elif digit > 0:
        format_str = "{:," + format_str + "}"
    else:
        format_str = "0.00"

    if percentage:
        format_str += "%"
    return format_str


def comma_sep_thousands(decimal, percentage=False, reference=None, decimal_places=0):
    """comma as a thousands separator"""
    if reference is not None:
        percentage = "%" in reference
        origin_val = reference.strip(")%")
        if decimal_places == 0 and "." in origin_val:
            decimal_places = len(origin_val.rsplit(".", 1)[-1])
    format_str = make_format_str(decimal, decimal_places, percentage)
    if percentage:
        value = format_str.format(abs(decimal) * 100)
    else:
        value = format_str.format(abs(decimal))
    return value


def init_db_session(host="localhost", port=3306, username="root", password="", database="ipo"):
    global db_session
    dsn_url = "mysql://%s:%s@%s:%s/%s?charset=utf8" % (username, password, host, port, database)
    engine = create_engine(dsn_url, echo=False)
    DBSession = sessionmaker(engine, autocommit=False)
    db_session = DBSession()


def check_fields():
    for key in FieldChecker.__dict__:
        if not key.startswith("_check"):
            continue
        try:
            func = getattr(FieldChecker, key)
            # _check_<table_name>
            func(key[7:])
        except Exception as e:
            logging.exception(e)


def init_log():
    logger = logging.getLogger()
    logger.setLevel(logging.INFO)
    timestr = time.strftime("%Y%m%d%H%M", time.localtime(time.time()))
    log_path = os.path.dirname(os.getcwd()) + "/log"
    log_name = log_path + timestr + ".log"
    logfile = log_name
    filehandler = logging.FileHandler(logfile, mode="w", encoding="utf-8")
    filehandler.setLevel(logging.INFO)
    formatter = logging.Formatter("%(asctime)s - %(filename)s[line:%(lineno)d] - %(levelname)s: %(message)s")
    filehandler.setFormatter(formatter)
    logger.addHandler(filehandler)
    return logger


def cli():
    args = docopt.docopt(__doc__)
    init_log()
    host = args["--host"]
    port = int(args["--port"])
    username = args["--username"]
    password = args["--password"]
    database = args["--database"]
    logging.info("Connect host: %s, port: %s, database: %s", host, port, database)
    init_db_session(host, port, username, password, database)
    logging.info("Start Checking...")
    check_fields()


if __name__ == "__main__":
    cli()
