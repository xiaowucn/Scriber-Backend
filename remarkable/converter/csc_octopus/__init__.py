import logging
import re
from decimal import Decimal, InvalidOperation

from remarkable.common.constants import OctopusUnit
from remarkable.common.pattern import PatternCollection
from remarkable.common.util import clean_txt, is_number_str
from remarkable.converter import BaseConverter
from remarkable.converter.csc_octopus.data_formater import (
    MoneyUnit,
    PeriodUnit,
    data_format,
    split_num_and_unit,
    thousands_pattern,
)
from remarkable.converter.utils import date_from_text

reg_short_date = re.compile(r"\d{4}-\d{2}-\d{2}")
reg_date_time = re.compile(r"\d{4}-\d{2}-\d{2}\s\d{2}:\d{2}:00")
p_number = re.compile(r"^\d[\d,.]+\d$")
DATE_FORMAT = "%Y-%m-%d"
DATE_PATTERN = r"\d{4}[年/\.—–-]\d{1,2}[月/\.—–-]\d{1,2}[日/\.—–-]?"
time_range_pattern = PatternCollection(
    [
        r"[至到]",
        rf"{DATE_PATTERN}[~～到至—–-]{DATE_PATTERN}",
    ]
)


class OctopusConverter(BaseConverter):
    number_fields = (
        "prHoldNum",
        "prHoldAmountAmount",
        "prPledgedFrozenTotal",
        "prPutRegistrationNumAmount",
        "amount",
        "unsuccessfulAmount",
        "planAmount",
    )

    def convert(self, *args, **kwargs):
        converter_handler = {
            "国债发行公告": self.treasury_bonds_converter,
            "发行情况公告": self.issuance_bonds_converter,
            "《【上清所】债券持有人名册 》": self.csc_bondholders_register,
            "《【深中登】债券持有人名册》": self.csc_register_bondholders,
            "《【深中登】回售结果明细表》": self.csc_results_breakdown,
            "产品承销/认购额度表": self.subscription_quota,
        }
        ret = converter_handler[self.mold_name]()
        ret = self.post_process(ret)
        return ret

    def post_process(self, ret):
        if not ret:
            return ret
        if isinstance(ret, list):
            return [self.post_process(x) for x in ret]
        for key, value in ret.items():
            if not isinstance(value, (int, float)) and not value:
                value = None
            elif isinstance(value, str) and p_number.search(value):
                value = value.replace(",", "")

            if key in self.number_fields:  # 客户要转换成BigDecimal的字段,如果不是数字字符串,则转换成None
                if isinstance(value, str) and not is_number_str(value):
                    value = None

            ret[key] = value
        return ret

    def treasury_bonds_converter(self):
        answer_dict = self.answer_node.to_dict(item_handler=lambda n: n.plain_text)
        ret = {k: data_format(k, v) for k, v in answer_dict.items()}
        return self.customer_treasury_bonds(ret)

    def issuance_bonds_converter(self):
        ret = {}
        customer_map = {
            "bondName": "债券名称",
            "bondAbbreviation": "债券简称",
            "bondCode": "债券代码",
            "issueRate": "发行利率（%）",
        }
        answer_dict = self.answer_node.to_dict(item_handler=lambda n: n.plain_text)
        adjusted_answer = {}
        for key, value in answer_dict.items():
            if isinstance(value, list) and value:
                adjusted_answer.update(value[0])  # 都只会有一条答案
            else:
                adjusted_answer[key] = value

        for key, value in customer_map.items():
            ret[key] = adjusted_answer.get(value)

        issue_scale = adjusted_answer.get("金额")
        unit = adjusted_answer.get("单位")
        ret["issueScaleAmount"] = issue_scale
        unit_enum = MoneyUnit.get_enum(unit)
        ret["issueScaleUnit"] = unit_enum.value if unit_enum else None
        if issue_scale and unit:
            issue_scale += unit
        ret["issueScale"] = issue_scale
        return ret

    def csc_register_bondholders(self):
        customer_map = {
            "prHoldName": "持有人名称",
            "prCodeAccountNumber": "一码通账户号码",
            "prCertificateAccountCode": "证券账户号码",
            "prIdentificationNumber": "证件号码",
            "prHoldAmount": "持有金额（元）",
            "prHoldProportion": "持有比例",
            "prPledgedFrozenTotal": "质押/冻结总数",
            "prPhone": "联系电话",
        }
        answer_dict = self.answer_node.to_dict(item_handler=lambda n: n.plain_text)
        bondabbreviation = clean_txt(answer_dict.get("债券简称") or "")
        bondcode = clean_txt(answer_dict.get("债券代码") or "")
        prequityregistrationdate = self.format_date(clean_txt(answer_dict.get("权益登记日") or ""))
        ret = []
        for item in answer_dict.get("前N名证券持有人名册", []):
            answer = {
                "bondAbbreviation": bondabbreviation,
                "bondCode": bondcode,
                "prEquityRegistrationDate": prequityregistrationdate,
            }
            for key, value in customer_map.items():
                answer[key] = clean_txt(item.get(value) or "")
            amount = answer.get("prHoldAmount", "")
            amount_res = self.get_amount_res(amount, "prHoldAmountAmount", "prHoldAmountUnit")
            answer.update(amount_res)
            ret.append(answer)
        return ret

    @staticmethod
    def get_amount_res(amount, amount_word, unit_word, multiply=True):
        amount_text, unit = None, None
        if amount:
            amount = thousands_pattern.sub("", amount)
            try:
                amount_text = int(Decimal(amount))
                if multiply:
                    amount_text = int(Decimal(amount) * 100)
            except InvalidOperation:
                logging.info(f"amount convert to Decimal error, amount: {amount}, set amount_text to 0")
                amount_text = 0
            unit = OctopusUnit.YUAN.value  # amount_text 是持有数量*100或者回售数量*100得来的 所以单位默认是元
        return {
            amount_word: amount_text,
            unit_word: unit,
        }

    def csc_bondholders_register(self):
        customer_map = {
            "prCertificateAccountCode": "证券账户号码",
            "prHoldName": "持有人名称",
            "prHoldAmount": "持有金额（元）",
            "prOrganizationName": "持有机构",
        }
        answer_dict = self.answer_node.to_dict(item_handler=lambda n: n.plain_text)
        bondabbreviation = clean_txt(answer_dict.get("债券简称") or "")
        bondcode = clean_txt(answer_dict.get("债券代码") or "")
        prequityregistrationdate = self.format_date(clean_txt(answer_dict.get("权益登记日") or ""))
        ret = []
        for item in answer_dict.get("持有人名册", []):
            answer = {
                "bondAbbreviation": bondabbreviation,
                "bondCode": bondcode,
                "prEquityRegistrationDate": prequityregistrationdate,
            }
            for key, value in customer_map.items():
                answer[key] = clean_txt(item.get(value) or "")
            amount = answer.get("prHoldAmount", "")
            amount_res = self.get_amount_res(amount, "prHoldAmountAmount", "prHoldAmountUnit", multiply=False)
            answer.update(amount_res)
            ret.append(answer)
        return ret

    def csc_results_breakdown(self):
        customer_map = {
            "prCertificateAccountCode": "证券账户号码",
            "prHoldName": "持有人名称",
            "prManagedUnit": "托管单元",
            "prManagedUnitName": "托管单元名称",
            "prPutRegistrationNum": "回售登记金额（元）",
            "prEntrustmentDate": "回售委托日期",
            "prResalePhone": "回售电话号码",
        }
        answer_dict = self.answer_node.to_dict(item_handler=lambda n: n.plain_text)
        bondabbreviation = clean_txt(answer_dict.get("债券简称") or "")
        bondcode = clean_txt(answer_dict.get("债券代码") or "")
        prresaledeclarationdate = self.format_date(clean_txt(answer_dict.get("回售申报日期") or ""))
        ret = []
        for item in answer_dict.get("证券回售明细表", []):
            answer = {
                "bondAbbreviation": bondabbreviation,
                "bondCode": bondcode,
                "prResaleDeclarationDate": prresaledeclarationdate,
            }
            for key, value in customer_map.items():
                cleaned_value = clean_txt(item.get(value) or "")
                if key == "prEntrustmentDate":
                    cleaned_value = self.format_date(cleaned_value)
                answer[key] = cleaned_value
            amount = answer.get("prPutRegistrationNum", "")
            amount_res = self.get_amount_res(amount, "prPutRegistrationNumAmount", "prPutRegistrationNumUnit")
            answer.update(amount_res)
            ret.append(answer)
        return ret

    def subscription_quota(self):
        ret = []
        customer_map = {
            "bondName": "债券名称",
            "content": "第一段内容整体文字",
            "issuerName": "发行人中文全称",
            "issuerAccount": "发行人账户账号",
            "productAbbr": "产品简称",
            "productCode": "产品代码",
            "unsuccessfulAmount": "未成功发行额度（万元）",
            "planAmount": "计划发行额度（万元）",
        }
        investor_map = {
            "investorName": "持有人全称",
            "investorAccount": "持有人账号",
            "amount": "承销/认购金额（万元）",
        }
        answer_dict = self.answer_node.to_dict(item_handler=lambda n: n.plain_text)
        customer_answer = {}
        for key, value in customer_map.items():
            cleaned_value = clean_txt(answer_dict.get(value) or "")
            customer_answer[key] = cleaned_value

        for index, item in enumerate(answer_dict.get("持有人", [])):
            investor = {"orderNum": index + 1}
            for key, value in investor_map.items():
                cleaned_value = clean_txt(item.get(value) or "")
                investor[key] = cleaned_value
            investor.update(customer_answer)
            ret.append(investor)
        return ret

    @staticmethod
    def customer_treasury_bonds(input_data):
        """和客户约定，各字段都可能为空值"""
        total_issuing_size = input_data["总发行规模"]
        value_date = input_data["起息日（年份）"] + "-" + input_data["起息日（具体日期）"]
        payment_date = input_data["缴款日期"]
        bidding_date = input_data["招标日期"]
        bidding_start_time = input_data["招标日期"] + " " + input_data["招标时间（起）"] + ":00"
        bidding_end_time = input_data["招标日期"] + " " + input_data["招标时间（止）"] + ":00"
        listing_date = input_data["起息日（年份）"] + "-" + input_data["上市日期"]
        issue_period = input_data["发行期限"]

        total_issuing_size_amount, total_issuing_size_unit = split_num_and_unit(total_issuing_size, MoneyUnit)
        issue_period_amount, issue_period_unit = split_num_and_unit(issue_period, PeriodUnit)

        ret = {
            "bondName": input_data["债券名称"],
            "totalIssuingSize": total_issuing_size,
            "totalIssuingSizeAmount": total_issuing_size_amount,
            "totalIssuingSizeUnit": total_issuing_size_unit,
            "valueDate": value_date if reg_short_date.search(value_date) else None,
            "paymentDate": payment_date if reg_short_date.search(payment_date) else None,
            "biddingDate": bidding_date if reg_short_date.search(bidding_date) else None,
            "biddingStartTime": bidding_start_time if reg_date_time.search(bidding_start_time) else None,
            "biddingEndTime": bidding_end_time if reg_date_time.search(bidding_end_time) else None,
            "biddingWay": input_data["招标方式"],
            "announcementFee": input_data["公告手续费"],
            "listingDate": listing_date if reg_short_date.search(listing_date) else None,
            "issuePeriod": issue_period,
            "issuePeriodAmount": issue_period_amount,
            "issuePeriodUnit": issue_period_unit,
            "couponRate": input_data["票面利率"],
            "interestPaymentWay": input_data["付息方式"],
        }

        return ret

    @staticmethod
    def format_date(date):
        if time_range_pattern.nexts(date):
            return date
        parse_date = date_from_text(date, languages=("zh", "zh-Hans"))
        if not parse_date:
            return date
        return parse_date.strftime(DATE_FORMAT)
