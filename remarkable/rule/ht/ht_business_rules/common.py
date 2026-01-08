import difflib
import re
from decimal import Decimal
from itertools import groupby

from remarkable.rule.common import lower2upper

party_employee_regs = {
    "乙方项目人员-应急处理原条款": re.compile(
        r"乙方项目人员必须严格遵守安全生产法律.*?熟练掌握事故防范措施和事故应急处理"
    ),
    "乙方项目人员-人员专业性条款": re.compile(r"乙方必须对其项目人员进行安全教育和安全技术培训"),
    "乙方项目人员-消防安全条款": re.compile(r"乙方项目人员必须配合甲方做好消防安全工作"),
    "乙方项目人员-安全培训条款": re.compile(r"乙方必须配合甲方加强安全培训.*?工作"),
    "乙方项目人员-网络安全条款": re.compile(r"乙方项目人员必须配合甲方.*?网络安全知识"),
    "乙方项目人员-安全规定条款": re.compile(r"甲方对乙方人员执行规章制度及履行安全职责情况"),
}

partyb_obligations_regs = {
    "备案监督条款": [
        re.compile(r"定期向中国证监会和国务院有关主管部门按照规定备案"),
        re.compile(r"实施监督管理"),
    ],
    "违规监督条款": [
        re.compile(r"涉嫌违法违规被立案调查"),
        re.compile(r"情节严重或影响提供信息技术系统服务的"),
    ],
    "纠纷、仲裁告知条款": [
        re.compile(r"因执业行为与委托人.*?投资者发生民事纠纷"),
        re.compile(r"进行诉讼或者仲裁"),
    ],
    "违规采购条款": [
        re.compile(r"配合甲方对服务机构日常管理、采购管理和评价管理事务"),
        re.compile(r"若采购过程中有违规行为或被甲方评价不合格的"),
    ],
    "合规管理条款": [
        re.compile(r"对乙方的日常管理及评价管理工作"),
        re.compile(r"日常工作过程中有违规行为或被甲方评价不合格的"),
    ],
    "质量控制条款": [
        re.compile(r"健全内部质量控制机制.*?定期监测相关产品或服务"),
        re.compile(r"立即核实有关情况.*?采取必要的处理措施.*?明确修复完成时限"),
    ],
}

NUM_CHARS = r"^[1234567890一二三四五六七八九十、（）\(\)\s]*"

obligations_template_regs = {
    "partyb_record_supervision": re.compile(
        rf"""{NUM_CHARS}
                乙方从事证券服务业务应当定期向中国证监会和国务院有关主管部门按照规定备案，
                乙方应配合主管部门依法对备案行为实施监督管理。""",
        re.X | re.I,
    ),
    "partyb_violation_supervision": re.compile(
        rf"""{NUM_CHARS}
                乙方及其备案的从业人员因职业行为涉嫌违法违规被立案调查，
                或被司法机关立案侦查，以及受到刑事处罚、行政处罚、监督管理措施等时，
                应及时告知甲方，甲方有权要求乙方改正，情节严重或影响提供信息技术系统服务的，
                甲方有权终止合同和停止后续所有合作。""",
        re.X | re.I,
    ),
    "partyb_arbitration_notice": re.compile(
        rf"""{NUM_CHARS}
                乙方及其备案的从业人员因执业行为与委托人.*?投资者发生民事纠纷.*?进行诉讼或者仲裁.*?
                应及时告知甲方.*?影响提供信息技术系统服务的.*?甲方有权终止合同和停止后续所有合作。""",
        re.X | re.I,
    ),
    "partyb_illegal_procurement": re.compile(
        rf"""{NUM_CHARS}
                乙方需按法律法规和甲方相关规定，配合甲方对服务机构日常管理、采购管理和评价管理事务，
                若采购过程中有违规行为或被甲方评价不合格的，甲方有权按规定执行违约处罚或终止合作。""",
        re.X | re.I,
    ),
    "partyb_compliance_management": re.compile(
        rf"""{NUM_CHARS}
                乙方项目负责人需配合甲方对乙方的日常管理及评价管理工作，
                若乙方项目人员日常工作过程中有违规行为或被甲方评价不合格的，
                甲方有权按规定执行违约处罚或终止合作。""",
        re.X | re.I,
    ),
    "partyb_quality_control": re.compile(
        rf"""{NUM_CHARS}
                乙方应当健全内部质量控制机制，定期监测相关产品或服务，在提供服务过程中出现明显质量问题的，
                应当立即核实有关情况，采取必要的处理措施，明确修复完成时限，及时完成修复工作""",
        re.X | re.I,
    ),
}


def lower_currency(num):
    lower_pattern = re.compile(r"[￥¥(人民币)][\d,]*\.?\d{2}")
    if not lower_pattern.search(str(num)):
        return "<em>✘</em>缺失<em>币种</em>", "<em>￥</em>" + str(num)
    return "", num


def upper_currency(num):
    upper_pattern = re.compile(r"人民币.*?([元圆角分]整?)$")
    if not upper_pattern.search(str(num)):
        return "<em>✘</em>缺少<em>币种</em>", "<em>人民币</em>" + str(num)
    return "", num


def zheng_check(upper_amount):
    if re.compile(r"[角分]整").search(upper_amount):
        return "<em>✘</em>多了<em>整</em>", upper_amount
    if not re.compile(r".*?([元圆]整|角|分)$").search(upper_amount):
        return "<em>✘</em>缺少<em>整</em>", upper_amount + "<em>整</em>"
    return "", upper_amount


def zero_check(upper_amount, lower_amount, upper_amount_ori):
    lower_amount = re.sub(r"[￥¥]", "", lower_amount)
    if not lower_amount:
        return "", upper_amount
    convert_upper = lower2upper(lower_amount)
    convert_upper = convert_upper.replace("整", "")
    upper_amount4loop = upper_amount_ori.replace("人民币", "")
    upper_amount4loop = upper_amount4loop.replace("整", "")
    if upper_amount4loop == convert_upper:
        return "", upper_amount
    if re.compile(r"\d*\.0[1-9]").search(lower_amount) and "元零" not in upper_amount4loop:
        return "<em>✘</em>缺少<em>零</em> ", upper_amount
    if re.compile(r"[万元]零").search(convert_upper) and remove_zero(upper_amount4loop) == remove_zero(convert_upper):
        return "", upper_amount
    if exist_error(upper_amount4loop, convert_upper):
        return "<em>✘</em>大写数字不规范", upper_amount
    diff_execter = difflib.Differ()
    diff_result = list(diff_execter.compare(convert_upper.splitlines(), upper_amount4loop.splitlines()))
    label_index = []
    if diff_result[0][0] == "-" and diff_result[1][0] == "?":
        for _index, compare_flag in enumerate(diff_result[1][2:]):
            if compare_flag == "-":
                label_index.append(_index)
            else:
                label_index.append(-1)
    if not label_index:
        return "", upper_amount
    # 获取单独的缺失字段和连续的缺失字段
    all_miss_index = []
    res = ""
    for _, _miss_index in groupby(enumerate(label_index), lambda x: x[1] - x[0]):
        all_miss_index.append([_index for _, _index in _miss_index])

    for miss_index in all_miss_index:
        if len(miss_index) != 1:
            res += "<em>✘</em>缺少<em>{}</em> ".format(convert_upper[miss_index[0] : miss_index[-1] + 1])
        elif miss_index[0] > 1:
            res += "<em>✘</em>缺少<em>零</em> "

    return res, upper_amount


def keep2decimals(lower_amount):
    # 去除 <em>
    lower_amount = re.sub(r"(￥|¥|人民币)", "", lower_amount)
    if not lower_amount:
        return "<em>✘</em>应保留两位小数", ""
    try:
        standard = str(Decimal(lower_amount).quantize(Decimal("0.00")))
    except Exception:
        standard = lower_amount
    if str(standard) != lower_amount:
        num, dec = standard.split(".")
        return "<em>✘</em>应保留两位小数", "{}<em>.{}</em>".format(num, dec)
    return "", lower_amount


def remove_zero(upper):
    items = (("万零", "万"), ("元零", "元"), ("圆零", "圆"))
    for origin_word, replace_word in items:
        if origin_word in upper:
            upper = re.sub(origin_word, replace_word, upper)
    return upper


def remove_misc(upper):
    upper = re.sub("壹拾万", "拾万", upper)
    return upper


def exist_error(upper_ori, convert_upper):
    if re.compile(r"万元.*?元").search(upper_ori):
        return True
    if remove_misc(convert_upper) == upper_ori:
        return True
    if re.compile(r"[佰仟]零").search(remove_zero(upper_ori)):
        return False
    if "零" in remove_zero(upper_ori):
        return True
    upper_word = {"〇", "一", "二", "三", "四", "五", "六", "七", "八", "九", "十", "百", "千"}
    if set(upper_ori).intersection(upper_word):
        return True
    return False


def is_similar_str(str1, str2, threshold=0.8):
    return difflib.SequenceMatcher(None, str1, str2).ratio() >= threshold


if __name__ == "__main__":
    pass
