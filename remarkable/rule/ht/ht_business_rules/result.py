import decimal
import difflib
import re

from remarkable.common.constants import ComplianceStatus
from remarkable.rule.common import lower2upper
from remarkable.rule.ht.ht_business_rules.common import (
    keep2decimals,
    lower_currency,
    remove_zero,
    upper_currency,
    zero_check,
    zheng_check,
)
from remarkable.rule.ht.ht_business_rules.patterns import HT_PATTERNS, simplified_expression


def ops_amount_res(xpath, ops_amount_ori, schema_cols, specific_num):
    comment_name = "ops_compute_res"
    comment_detail = []
    con_amount = specific_num["con_amount_lower"]["texts"]
    ratio_pattern = HT_PATTERNS["ratio_pattern"]
    try:
        con_amount = decimal.Decimal(HT_PATTERNS["lower_sub_pattern"].sub("", con_amount))
        matcher = ratio_pattern.search(ops_amount_ori)
        ratio = int(matcher.group(1).strip())
        ops_amount = con_amount * ratio / 100
    except Exception:
        result = ComplianceStatus.NONCOMPLIANCE.value
        comment_detail.append("未提取到维护费用")
    else:
        result = ComplianceStatus.COMPLIANCE.value
        comment_detail.append(str(ops_amount))

    ret = (schema_cols, result, "", xpath, second_rules[comment_name], {"comment_detail": comment_detail})
    return ret


def amount_res(upper, lower, specific_num, comment_name, pdfinsight):
    xpath = {}
    schema_cols = [specific_num[upper].get("schema_key", ""), specific_num[lower].get("schema_key", "")]

    if not specific_num[upper]["texts"] or not specific_num[lower]["texts"]:
        if upper in ["con_amount_upper5", "con_amount_upper6"]:
            return None
        result = ComplianceStatus.NONCOMPLIANCE.value
        comment = "未提取到数据"
        label_info = "未提取到" + comments[comment_name]
        ret = ([], result, comment, xpath, second_rules[comment_name], {"label_info": label_info})
        return ret

    xpath = get_xpath(specific_num[upper], pdfinsight) or get_xpath(specific_num[lower], pdfinsight)

    lower_amount_ori = specific_num[lower]["texts"].strip()
    upper_amount_ori = specific_num[upper]["texts"].strip()
    if upper == "ops_amount_upper" and lower_amount_ori == re.sub(r"\s", "", upper_amount_ori):
        return ops_amount_res({"xpath": xpath}, lower_amount_ori, schema_cols, specific_num)
    upper_amount_ori = re.sub("\\s", "", upper_amount_ori)
    lower_amount_ori = re.sub("\\s", "", lower_amount_ori)
    lower_check_res, upper_check_res = [], []
    for handler in [lower_currency, keep2decimals]:
        check_res, _ = handler(lower_amount_ori)
        lower_check_res.append(check_res)

    upper_amount = upper_amount_ori
    for handler in [upper_currency, zheng_check, zero_check]:
        if handler == zero_check:
            check_res, upper_amount = handler(upper_amount, lower_amount_ori, upper_amount_ori)
        else:
            check_res, upper_amount = handler(upper_amount)
        upper_check_res.append(check_res)

    # 提取的大写
    upper_amount_com = re.sub("人民币|整|[（(]大写[)）]", "", upper_amount_ori)
    upper_remove_zero = remove_zero(upper_amount_com)
    upper_convert_yuan = upper_amount_com.replace("圆", "元")
    # 小写转换的大写
    convert_amount_com = re.sub(
        "整", "", lower2upper(lower_amount_ori[1:] if lower_amount_ori[0] in ("￥", "¥") else lower_amount_ori)
    )
    convert_amount_com1 = remove_zero(convert_amount_com)
    # 比较结果
    ori_compare_res = upper_amount_com in [convert_amount_com, convert_amount_com1]
    remove_zero_compare_res = upper_remove_zero in [convert_amount_com, convert_amount_com1]
    convert_yuan_compare_res = upper_convert_yuan in [convert_amount_com, convert_amount_com1]
    res = ori_compare_res or remove_zero_compare_res or convert_yuan_compare_res
    if not any(lower_check_res) and not any(upper_check_res):
        result = ComplianceStatus.COMPLIANCE.value if res else ComplianceStatus.NONCOMPLIANCE.value
    else:
        result = ComplianceStatus.NONCOMPLIANCE.value

    comment_detail = []
    comment_detail.append("格式:")
    comment_detail.append(
        "大写: {} {}".format(
            upper_amount, ";".join([upper_check_re for upper_check_re in upper_check_res if upper_check_re])
        )
    )
    comment_detail.append(
        "付款小写: {} {}".format(
            lower_amount_ori, ";".join([lower_check_re for lower_check_re in lower_check_res if lower_check_re])
        )
    )

    comment_detail.append("一致性:")
    comment_detail.append(
        "大写: {} {}".format(
            re.sub("人民币|[（(]大写[)）]", "", upper_amount_ori), "" if res else "<em>✘</em>与小写转大写对比不一致"
        )
    )
    comment_detail.append(
        "小写: {} （转大：{}）".format(
            lower_amount_ori,
            lower2upper(lower_amount_ori[1:] if lower_amount_ori[0] in ("￥", "¥") else lower_amount_ori),
        )
    )
    lower_label, upper_label = "", ""
    if any(lower_check_res):
        lower_check_res = [res for res in lower_check_res if res]
        lower_label = "小写：" + re.sub(r"<em>|</em>", "", ";".join(lower_check_res)) + "\n"
    if any(upper_check_res):
        upper_check_res = [res for res in upper_check_res if res]
        upper_label = "大写：" + re.sub(r"<em>|</em>", "", ";".join(upper_check_res)) + "\n"
    no_compliance_laebl = lower_label + upper_label
    if not res:
        no_compliance_laebl += "✘大写与小写对比不一致"
    label_info = comments[comment_name] if result == ComplianceStatus.COMPLIANCE.value and res else no_compliance_laebl

    ret = (
        schema_cols,
        result,
        "",
        {"xpath": xpath},
        second_rules[comment_name],
        {"comment_detail": comment_detail, "label_info": label_info},
    )
    return ret


def get_diff_res(compare_text, origin_pattern):
    add = []
    delete = []
    modify = []
    diff_execter = difflib.Differ()
    if compare_text == "0":
        compare_text = ""
    compare_text = re.sub("(^[1234567890一二三四五六七八九十]*、?|\\s)", "", compare_text)
    compare_text = re.sub("[1234567890一二三四五六七八九十]、", "", compare_text)
    compare_texts = re.sub("^（[1234567890一二三四五六七八九十]*）", "", compare_text)

    origin_texts = simplified_expression(origin_pattern)

    diff = diff_execter.compare(origin_texts.splitlines(), compare_texts.splitlines())
    diff_res = list(diff)
    # line_num = 0
    if len(diff_res) == 1:
        if diff_res[0][0] == "-":
            delete.append(diff_res[0][1:])
    elif len(diff_res) > 2:
        last_res = diff_res[-1]
        if last_res[0] == "?":
            if diff_res[-3][0] == "?":
                parse_diff_res(diff_res[0], diff_res[1], modify, add, delete)
                parse_diff_res(diff_res[2], diff_res[3], modify, add, delete)
            else:
                index_str = diff_res[-1]  # 包含比较结果的行
                compare_sub_text = diff_res[-2]  # 原始字符串
                parse_diff_res(compare_sub_text, index_str, modify, add, delete)
        elif last_res[0] in ("+", "-"):
            index_str = diff_res[-2]  # 包含比较结果的行
            compare_sub_text = diff_res[-3]  # 原始字符串
            if index_str[0] == "?":
                parse_diff_res(compare_sub_text, index_str, modify, add, delete)

    modify = [datum for datum in modify if datum in compare_texts]

    except_str = ',，.、“”""'
    modify = [datum for datum in modify if datum not in except_str]
    delete = [datum for datum in delete if datum not in except_str]
    add = [datum for datum in add if datum not in except_str]
    return {
        "add": add,
        "delete": delete,
        "modify": modify,
    }


def parse_diff_res(compare_sub_text, index_str, modify, add, delete):
    delete_res, add_res, modify_res = "", "", ""
    for compare_text, index in zip(compare_sub_text, index_str):
        if index == " ":
            delete_res += " "
            add_res += " "
            modify_res += " "
        elif index == "-":
            delete_res += compare_text
        elif index == "+":
            add_res += compare_text
        elif index == "^":
            modify_res += compare_text
    if delete_res:
        delete.extend([datum for datum in re.sub("\\s+", " ", delete_res).split(" ") if datum])
    if modify_res:
        modify.extend([datum for datum in re.sub("\\s+", " ", modify_res).split(" ") if datum])
    if add_res:
        add.extend([datum for datum in re.sub("\\s+", " ", add_res).split(" ") if datum])


def get_sub_str(text, sub_str):
    start = 0
    res = []
    while True:
        index = text.find(sub_str, start)
        if index == -1:
            break
        res.append(index)
        start = index + 1
    return res


def get_rule_by_key(key):
    return key.split('"')[-2][:-2]


def convert_key(key):
    return key.split('"')[1::2]


comments = {
    "con_amount_res": "合同金额大小写",
    "con_amount_res1": "第一笔大小写",
    "con_amount_res2": "第二笔大小写",
    "con_amount_res3": "第三笔大小写",
    "con_amount_res4": "第四笔大小写",
    "con_amount_res5": "第五笔大小写",
    "con_amount_res6": "第六笔大小写",
    "payment_ratio1": "第一笔付款比例",
    "payment_ratio2": "第二笔付款比例",
    "payment_ratio3": "第三笔付款比例",
    "payment_ratio4": "第四笔付款比例",
    "payment_ratio5": "第五笔付款比例",
    "payment_ratio6": "第六笔付款比例",
    "point_sum_res": "合同总金额与分笔付款总和{}匹配",
    "notax_amount_res": "不含税金额大小写比对结果正确",
    "tax_res": "税款金额大小写比对结果正确",
    "ops_charge": "维护费用大小写比对结果正确",
    "amount_tax_res": "税款校验不通过，税款、含税总金额总和与含税合同总金额{}匹配",
    "tax_rate": "增值税税率{}",
    "last_charge": "最后一笔付款时间{}于验收后一年",
    "fix_term": "固定条款条款{}",
    "pm": "请确认项目负责人",
    "accessory": "附件为空",
}

second_rules = {
    "con_amount_res": "合同总额大小写对比结果",
    "con_amount_res1": "第一笔付款大小写对比结果",
    "con_amount_res2": "第二笔付款大小写对比结果",
    "con_amount_res3": "第三笔付款大小写对比结果",
    "con_amount_res4": "第四笔付款大小写对比结果",
    "con_amount_res5": "第五笔付款大小写对比结果",
    "con_amount_res6": "第六笔付款大小写对比结果",
    "payment_ratio1": "第一笔付款比例校验",
    "payment_ratio2": "第二笔付款比例校验",
    "payment_ratio3": "第三笔付款比例校验",
    "payment_ratio4": "第四笔付款比例校验",
    "payment_ratio5": "第五笔付款比例校验",
    "payment_ratio6": "第六笔付款比例校验",
    "point_sum_res": "合同总额 = 第一次付款 + 第二次付款 + 第三次付款 + 第四笔付款 + 第五笔付款 + 第六笔付款",
    "notax_amount_res": "不含税金额大小写对比结果",
    "tax_res": "税款金额大小写对比结果",
    "ops_charge": "维护费用大小写对比结果",
    "ops_compute_res": "维护费用计算结果",
    "amount_tax_res": "含税合同总金额 = 不含税合同总金额 + 税款",
    "tax_amount": "不含税价 * 税率 = 税款",
    "tax_rate": "增值税税率满足纳税人类型要求",
    "tax_rate_formula": "(含税价-不含税价)/不含税价=税率",
    "last_charge": "最后一笔付款时间应大于验收后一年",
    "fix_term": "{}需与模板一致",
    "pm": "{}项目负责人校验",
    "accessory": "是否含有附件《{}》",
}


def get_xpath(ele_info, pdfinsight) -> str:
    xpath = None
    if ele_info["texts"]:
        ele = pdfinsight.find_element_by_outline(
            ele_info["line_infos"][0]["page"], ele_info["line_infos"][0]["out_line"]
        )
        if ele[1]:
            xpath = ele[1].get("docx_meta", {}).get("xpath")
    return xpath
