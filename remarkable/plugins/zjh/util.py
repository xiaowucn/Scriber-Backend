import logging
import os
import re
from datetime import datetime, timedelta
from decimal import Decimal, InvalidOperation

from dateutil.relativedelta import relativedelta

from remarkable.common.util import group_cells
from remarkable.config import project_root
from remarkable.plugins.zjh.output.client_field_checker import (
    known_nationality,
)

non_val_re = re.compile(r"[，,%()（）: ：。\]\[注]")
non_cn_pattern = re.compile(r"([^\u4e00-\u9fa5]+)")
cn_pattern = re.compile(r"([\u4e00-\u9fa5]+)")
date_regexp = re.compile(r"(\d{2,4})[.年—/出-]?(?:1-)?(\d{0,2})?[./—月-]?(\d{0,2})?日?")
year_regexp = re.compile(r"(\d{4})")
year_month_day_regexp = re.compile(r"(\d{7,8})")
sp_date_regexp = re.compile(r"(\d+)年(\d{1,2})[-—~～到至](\d{1,2})月")
name_regexp = re.compile(r"(.*?(?<=[）)]))[(（](.*?)[)）]")  # '流动比率(倍)(T-2年)'
name_regexp_1 = re.compile(r"(.*?)[(（](.*?)[)）]")  # '金额(T-2年)'
split_operator = re.compile(r"([/／])")
punctuation_regexp = re.compile(r"([，。、, .])")
p_time_range = re.compile(
    r"(\d{4})[./—年-](\d{1,2})[./—月-]?(\d{1,2})?[日号]?起?.*?[至到~—-～]?(\d{4})[./—年-](\d{1,2})[./—月-]?(\d{1,2})?日?"
)
p_time_range_sp = re.compile(r"(\d{4})[-—~～到至](\d{4})年度?")
p_time_join = re.compile("[&、\n]")
p_decimal_point = re.compile(r"\..*")
file_date_regexp = re.compile(r"招股说明书.*?日期(.*?)$")
date_pattern = re.compile(r"(\d+)年度?(.*月份?)?(.*日)?|(\d{4}[\.\-]\d{1,2}[\.\-]\d{1,2})")
p_formated_date = [re.compile(r"\d{4}-01~\d{4}-\d{2}")]
date_base = re.compile(r"([年月日][^元])")
already_date_period = re.compile(r"^(\d+)年$|([一二三四五六七八九十]+)年$")
p_digital = re.compile(r"[\d,\.\-%％零一二三四五六七八九十壹贰叁肆伍陆柒捌玖拾佰仟()]+")
p_serial_number = re.compile(r"^[序号列编]{2}$")
p_clean_punctuation_list = [
    re.compile(r"[：，、。:,.．\s]+"),
]

p_clean_list = [
    re.compile(r"[的及和与下](?!属)|[·*\-/—☐]+|人民币元|按.*分类[)）.1-9]+"),
    re.compile(r"[/（(]+[^（()）]*[)）]?"),
    re.compile(r"^(其中)?(一(?![年般]))?[二三四五六七八九十0-9加减]?"),
    re.compile(r"[(（]?净?[损失亏]*(总额)?以[“\-－”号填列]*[)）]?"),
    re.compile(r"([(（]?(?<!减值)净?(损失|亏损)|注\d+|[总合小]计|[A-z0-9]+|[(（]元[)）]?)$"),
]

p_fix_list = [
    (re.compile(r"流动负$"), "流动负债"),
    (re.compile(r"流动资$"), "流动资产"),
    (re.compile(r"营业利$"), "营业利润"),
    (re.compile(r"其它"), "其他"),
    (re.compile(r"及其变动"), "且其变动"),
    (re.compile(r"支付现$"), "支付现金"),
]

p_proportion = re.compile(r"占.*(之比|比[例重])")
p_summation = re.compile(r"^合计$")
p_tbl_skip = re.compile(r"[^组][合总小]计$|^[合总小]计$")

p_column_tbl_skip = {
    "主要客户": [re.compile(r"销售总额")],
    "股权结构": [re.compile(r"本次发行|公开发行|社会公众|流通股")],
    "关联交易": [p_proportion],
    "财务报表附注": [p_proportion],
    "释义": [re.compile("专(业|用技术)[术语释义名词]+")],
}

keyword_col_label = {
    "重大合同": ["合同金额", "合同对手方名称"],
    "专利": ["专利号", "专利名称"],
    "股权结构": ["主体名称", "股份持有数量", "持股比例"],
    "重大诉讼事项": ["诉讼涉及金额"],
    "主要客户": ["客户名称"],
    "主要供应商": ["供应商名称", "采购额"],
    "非经常性损益情况2": ["项目"],
    "净利润与经营活动净现金流量差异": ["项目"],
}

key_field_map = {
    "释义": "简称",
    "股权结构": "主体名称",
    "发行人员工及结构情况": "人数",
    "主要客户": "客户名称",
    "主要供应商": "供应商名称",
    "专利": "专利名称",
    "关联交易": "名称",
    "非经常性损益情况": "项目",
    "税款缴纳情况": "项目",
    "财务报表附注": "项目名",
    "应收账款": "账龄",
    "预付账款": "账龄",
    "存货减值": "项目名称",
    "固定资产折旧": "项目名称",
    "无形资产": "无形资产类别",
    "商誉减值准备": "项目名称",
    "净利润与经营活动净现金流量差异": "项目",
    "募集资金与运用": "项目名称",
    "重大合同": "合同对手方名称",
    "重大诉讼事项": "事项",
}

unit_map = {
    "亿元": Decimal("100000000"),
    "亿": Decimal("100000000"),
    "万元": Decimal("10000"),
    "百万": Decimal("1000000"),
    "百万元": Decimal("1000000"),
    "千万元": Decimal("10000000"),
    "千万元人民币": Decimal("10000000"),
    "万": Decimal("10000"),
    "万元人民币": Decimal("10000"),
    "万人民币": Decimal("10000"),
    "千万": Decimal("10000000"),
    "元": Decimal("1"),
    "人民币元": Decimal("1"),
    "人民币万元": Decimal("10000"),
    "人民币亿元": Decimal("100000000"),
    "千元": Decimal("1000"),
    "人民币": Decimal("1"),
    "股": Decimal("1"),
    "万股": Decimal("10000"),
    "人": Decimal("1"),
    "个": Decimal("1"),
    "": Decimal("1"),
    "1": Decimal("1"),
}

# 更新时需同步更新check_number()
foreign_currency = [
    "港元",
    "港币",
    "欧",
    "欧元",
    "美元",
    "USD",
    "JPY",
    "EUR",
    "Euro",
    "美金",
    "日元",
    "英镑",
    "越南盾",
    "肯尼亚先令",
    "印度卢比",
    "印尼卢比",
    "加拿大元",
    "新台币",
    "泰铢",
    "澳元",
]

foreign_currency_name_map = {"USD": "美元", "JPY": "日元", "EUR": "欧元", "Euro": "欧元"}


def process_unit(unit):
    if not unit:
        return unit, None
    search_res = date_base.search(unit)
    if search_res:
        unit_base = search_res.group(1)
        remain_unit = cn_pattern.search(unit.replace(unit_base, ""))
        if not remain_unit:
            logging.error("******Unit: %s format error", unit)
            return unit, unit_base
        return remain_unit.group(1), unit_base
    return unit, None


def get_row_time(cells):
    time_res = []
    other_res = []
    for cell in cells:
        if cell.get("dummy"):
            continue
        cell_time = date_pattern.search(format_string(cell["value"]))
        if cell_time:
            time_field = {"chars": cell["chars"], "text": cell_time.group()}
            time_res.append(time_field)
        else:
            other_res.append(cell["value"])

    if other_res:
        if not (len(other_res) == 1 and other_res[0] in ["项目", "序号", ""]):
            return False, ""

    if len(time_res) == 1:
        return True, time_res[0]

    return False, ""


def is_left_col_is_num(table):
    cell_0_0 = table["cells"].get("0_0")
    left_col_is_num = False
    if cell_0_0 and cell_0_0["text"] == "序号":
        left_col_is_num = True
    return left_col_is_num


def table_rows_to_skip(column, cells_by_row, left_col_is_num, bottom_box, skip_after):
    rows_to_skip = []
    regs = []
    if column not in ["关联交易", "非经常性损益情况", "商誉减值准备", "募集资金与运用", "释义"]:
        regs.append(p_tbl_skip)
    regs.extend(p_column_tbl_skip.get(column, []))

    rows = list(cells_by_row.keys())
    for idx, row in enumerate(cells_by_row):
        row_cells = cells_by_row[row]
        if not row_cells:
            continue
        row_cells = sorted(row_cells.items(), key=lambda x: x[0])
        first_cell = row_cells[0][1]
        if first_cell["page"] == bottom_box["page"] and first_cell["box"][3] < bottom_box["box"][3]:
            continue
        first_cell_text = first_cell.get("text") or ""

        if column in ["关联交易"]:
            if p_summation.match(first_cell_text):
                rows_to_skip.extend(rows[idx:])
                return rows_to_skip

        if column in ["募集资金与运用", "主要供应商"] and left_col_is_num:
            if first_cell.get("dummy") or not first_cell_text or not is_digital(first_cell_text):
                rows_to_skip.append(row)
                continue

        for _, cell in row_cells:
            for reg in regs:
                if reg.search(cell.get("text") or ""):
                    if skip_after:
                        rows_to_skip.extend(rows[idx:])
                        return rows_to_skip
                    rows_to_skip.append(row)
                    break
            if row in rows_to_skip:
                break

    return rows_to_skip


def fill_data_with_previous(data_items):  # 未迁到新的表格标注逻辑中
    for idx, data_item in enumerate(data_items[1:]):
        for field in data_item["fields"]:
            if is_date_field(field) and not field["text"]:
                for _field in data_items[idx]["fields"]:  # data_items[idx]刚好就是data_item的前一条答案
                    if get_field_name(field) == get_field_name(_field):
                        field["text"] = _field["text"]
                        field["chars"] = _field.get("chars", [])
                        field["data"] = _field.get("data", [])
                        break
                break
    return data_items


def get_answer_label(answer):
    label = answer["schema"]["data"]["label"]
    return label


def get_field_type(field):
    if not field.schema:
        return ""
    label = field.schema["data"]["type"]
    return label


def get_field_name(field):
    if not field.schema:
        return ""
    name = field.schema["data"]["label"]
    return name


def is_text_field(field):
    if get_field_type(field) == "文本":
        return True
    if get_field_name(field) in ["专利号", "股东排名"]:
        return True
    if get_field_type(field) in ["数字", "日期"]:
        return False

    return False


def is_date_field(field):
    if get_field_type(field) in ["文本", "数字"]:
        return False
    if is_text_field(field):
        return False
    if get_field_name(field).endswith("期限"):
        return False

    return get_field_type(field) == "日期" or get_field_name(field).endswith("日期") or get_field_name(field) == "时间"


def is_number_field(field):
    if is_date_field(field):
        return False
    if get_field_type(field) in ["文本", "日期"]:
        return False

    if is_text_field(field):
        return False

    if get_field_type(field) == "数字":
        return True

    number_field_name = re.compile(
        "(成本|资本|比例|数量|人数|"
        "投资额|销售额|采购额|金额|总额"
        "|价值|原值|净值|余额|收入|成本|毛利)$"
        "|占.*比例|(坏账|跌价|减值)准备|累计摊销"
    )
    if number_field_name.search(get_field_name(field)):
        return True

    return False


def format_string(raw_string):
    if not raw_string:
        return raw_string
    value = "".join(raw_string.strip().split())
    return value


def transfer_patent_date_field(patent):
    deadline = patent["使用期限"].plain_text
    if deadline:
        two_time_point = extract_two_time_point(deadline)
        if not two_time_point:
            if not is_date_duration(deadline):
                success1, gain_date = grep_date(patent["取得日期"].plain_text)
                success2, end_date = grep_date(deadline)
                if success1 and success2:
                    patent["使用期限"].plain_text = ".".join(gain_date) + "至" + ".".join(end_date)

    return patent


def format_date(field):
    field_name = get_field_name(field)
    field_key = field.key or ""
    if field_name == "报表日期" or any(
        x in field_key
        for x in [
            "主要客户",
            "主要供应商",
            "关联交易",
            "非经常性损益情况",
            "财务报表附注",
            "税款缴纳情况",
            "净利润与经营活动净现金流量差异",
        ]
    ):
        value = transfer_date(field.plain_text)
    else:
        status, grep_res = grep_date(field.plain_text)
        if status:
            value = construct_standard_date(*grep_res)
        else:
            value = grep_res

    return value


def transfer_date(raw_value):
    """
    3年一期有很多表述方式，
    2013年、2014年、2015年、2016年6月
    2013年12月31日、2014年12月31日、2015年12月31日、2016年6月30日 等等
    我们需要统一，整年的就是2019,2018，不到一年的就是 2019-01~2019-06
    :param raw_value:
    :return:
    """
    value = format_string(raw_value)
    # 已经是标准化了的格式,直接返回
    if not value or value == "-" or any(pattern.match(raw_value) for pattern in p_formated_date):
        return raw_value

    p_exception = re.compile(r"(\d{2})(-)(\d{2}年.*)")  # 处理被错误识别成"20-17年1-9月"的情况, 去掉第一个-
    value = p_exception.sub(r"\1\3", value)

    sp_search_res = sp_date_regexp.search(value)
    if sp_search_res:
        year, start_month, end_month = sp_search_res.groups()
        month_int = int(end_month)
        month_str = str(month_int) if month_int >= 10 else "0" + str(month_int)
        return f"{year}-01~{year}-{month_str}"

    search_res = date_regexp.search(value)
    if not search_res:
        logging.warning("++++++transfer_date: Date not matched - %s", value)
        return raw_value
    year, month, day = search_res.groups()
    if not year:
        logging.warning("++++++transfer_date: Date not matched - %s", value)
        return raw_value
    if not month or int(month) == 12:
        if year.startswith("0") and len(year) == 3:
            year = "2" + year
        elif year.startswith("9") and len(year) == 3:
            year = "1" + year
        return "{}".format(year)
    # week, days = calendar.monthrange(int(year), int(month))
    month_int = int(month)
    month_str = str(month_int) if month_int >= 10 else "0" + str(month_int)
    return f"{year}-01~{year}-{month_str}"


def extract_currency_unit(header):
    if not header:
        return ""
    p_unit = re.compile(r"[十百千万亿美欧日港澳英加镑盾卢布先令比索元]+")  # 更新时需同步跟新check_number()
    match = p_unit.findall(format_string(header))
    if match:
        return "".join(match)
    return ""


def check_foreign_currency(value):
    if "$" in value:
        logging.info("Detect foreign currency: %s", value)
        value = value.replace("$", "")
        return True, value + "美元"
    for currency in foreign_currency:
        if currency in value:
            logging.info("Detect foreign currency: %s", value)
            if currency in foreign_currency_name_map:
                value = value.replace(currency, foreign_currency_name_map[currency])
            return True, value
    return False, value


def ensure_currency_unit(raw_value, from_unit, to_unit="万元"):
    if not raw_value:
        return from_unit, raw_value
    raw_value = str(raw_value)
    _foreign, value = check_foreign_currency(raw_value)
    if _foreign:
        search_res = cn_pattern.search(value)
        return search_res.group(1) if search_res else from_unit, format_number(value)
    status, value = transfer_unit(raw_value, to_unit=to_unit, from_unit=from_unit)
    return to_unit if status or not value else from_unit, value


def format_number(raw_value):
    """
    将数值格式化成123,456.78 12.23%
    :param raw_value:
    :param reference:
    :return:
    """
    if not raw_value:
        return None
    value = format_string(raw_value)
    search_res = non_cn_pattern.search(value)
    if search_res:
        _, value = transfer_unit(search_res.group(1), to_unit="", from_unit="", reference=raw_value)
        return value
    return raw_value


def transfer_unit(raw_value, to_unit, from_unit=None, basic_unit="元", reference=None):
    if not raw_value or raw_value in ["-", "－", "‐", "--", "——", "N/A", "NA", "N.A.", "/"]:
        return False, raw_value
    if "|_|_|" in raw_value:
        calc_res = Decimal("0")
        for ele in raw_value.split("|_|_|"):
            if not ele:
                continue
            try:
                calc_res += normalize_val(transfer_unit(ele, to_unit, from_unit, basic_unit)[1])
            except Exception:
                logging.error("******Can not transfer |_|_| in value, %s", raw_value)
                return False, raw_value
        return True, comma_sep_thousands(calc_res, decimal_places=2)

    value = "".join(raw_value.strip().split())
    if not value:
        return False, raw_value
    search_res = non_cn_pattern.search(value)
    if search_res:
        val = normalize_val(search_res.group(1))
        unit_in_value = extract_currency_unit(value)
        if not from_unit:
            from_unit = unit_in_value or basic_unit
        unit_res = cn_pattern.search(from_unit)
        from_unit = unit_res.group(1) if unit_res else from_unit
        if unit_in_value not in from_unit and from_unit not in value:
            from_unit = unit_in_value + from_unit

        _foreign, _ = check_foreign_currency(from_unit)
        if not _foreign:
            from_unit = from_unit.replace("人民币", "").replace("人民", "")
            try:
                origin_val = val / (unit_map[to_unit] / unit_map[from_unit])
                converted_val = comma_sep_thousands(origin_val, decimal_places=2, reference=reference)
                if (
                    converted_val == "0.00"
                ):  # 取两位小数结果是0.00时，再尝试下保留3位小数 hardcode 应该将decimal_places加到配置里 todo
                    converted_val = comma_sep_thousands(origin_val, decimal_places=3, reference=reference)
                    if converted_val == "0.000":
                        converted_val = "0.00"
                return True, converted_val
            except Exception:
                logging.error("******Transfer Unit: cannot transfer %s, from_unit %s", raw_value, from_unit)

    return False, raw_value


def longest_common_string(string_a, string_b):
    """
    最长公共子串
    :param string_a:
    :param string_b:
    :return: 开始位置，匹配字符串
    """
    lstr_a = len(string_a)
    lstr_b = len(string_b)
    record = [[0 for i in range(lstr_b + 1)] for j in range(lstr_a + 1)]
    max_len = 0
    end = 0

    for i in range(lstr_a):
        for j in range(lstr_b):
            if string_a[i] == string_b[j]:
                record[i + 1][j + 1] = record[i][j] + 1
                if record[i + 1][j + 1] > max_len:
                    max_len = record[i + 1][j + 1]
                    end = i + 1
    return end - max_len, string_a[end - max_len : end]


def transfer_nationality(nationalitys):
    if not nationalitys:
        return None
    remove_regexp = re.compile(r"[()（）]")
    nationalitys = remove_regexp.sub(r"", nationalitys)
    nationalitys = punctuation_regexp.sub(r";", nationalitys)

    if re.compile(".*省|.*市").search(nationalitys):
        return "中国"

    known_nationalitys = known_nationality()
    nationality_list = ",".join(known_nationalitys)

    na_list = set()
    for nationality in nationalitys.split(";"):
        idx, match = longest_common_string(nationality, nationality_list)
        if match:
            if match in known_nationalitys:
                na_list.add(match)
            else:
                match_res = [na for na in known_nationalitys if match in na]
                if len(match_res) == 1:
                    na_list.add(match_res[0])
                else:
                    na_list.add("其他")
                    logging.error("transfer_nationality fail, input: %s", nationalitys)

    if na_list:
        return ";".join(na_list)
    return "其他"


def transfer_data_with_known_list(raw_item, subject, default=None, indistinct_supplement=True):
    """
    用已知标准数据的list来尝试标准化raw_item
    对应科目的known_subject()函数写好后,即可使用此函数
    :param raw_item:
    :param subject: 'known_' + subject 对应的函数能返回一个list
    :param default:
    :param indistinct_supplement:
    :return:
    """
    if not raw_item:
        return default

    func_get_known_list = globals().get("known_" + subject)
    known_list = func_get_known_list()

    if raw_item in known_list:
        return raw_item

    if not indistinct_supplement:
        return default

    known_list_str = ",".join(known_list)
    _, match = longest_common_string(raw_item, known_list_str)  # 求最长公共子串
    if not match:
        return default

    match_res = [item for item in known_list if match in item]
    if len(match_res) == 1:  # 如果list中有且只有一个元素包含最长公共子串,返回该元素
        return match_res[0]
    if not match_res:
        logging.warning(
            "Fail to transfer_data_with_known_list, can not match anything, raw_item:%s, subject:%s",
            raw_item,
            subject,
        )
    else:
        logging.warning(
            "Fail to transfer_data_with_known_list, matched more than one, raw_item:%s, subject:%s, matched:%s",
            raw_item,
            subject,
            match_res,
        )
    return default


def transfer_yes_and_no(data):
    if not data:
        return data
    if data == "是":
        ret = "1"
    elif data == "否":
        ret = "0"
    else:
        ret = data
    return ret


def transfer_gender(gender):
    ret = None

    if not gender:
        return ret

    if "男" in gender:
        ret = "男"
    elif "女" in gender:
        ret = "女"

    if not ret:
        gender = non_cn_pattern.sub("", gender)
        gender_map = {"先生": "男", "先": "男", "生": "男"}
        ret = gender_map.get(gender)

    return ret


def transfer_end_date(date_start, date_end):
    sp_end_date = re.compile(r"(?P<num>[\u4e00-\u9fa5]{1,3})年")

    if not date_end and date_start:
        date_end = "至今"

    date_end = date_end.replace("迄今", "至今")

    ret = sp_end_date.search(date_end)
    if not ret:
        return date_start, date_end

    num = ret.groupdict().get("num")
    num = cn2digt(num)
    status, grep_res = grep_date(date_start)
    if not status:
        return date_start, date_end

    grep_res = list(grep_res)
    grep_res[0] = str(int(grep_res[0]) + num)
    date_end = construct_standard_date(*grep_res)

    return date_start, date_end


def transfer_movement_percentage(raw_value):
    if "增长" in raw_value:
        value = cn_pattern.sub("", raw_value)
    elif "下降" in raw_value or "降低" in raw_value:
        value = cn_pattern.sub("-", raw_value)
    else:
        value = raw_value

    return process_percentage(value)


def cn2digt(cn_chars):
    cn_num = {
        "〇": 0,
        "一": 1,
        "二": 2,
        "三": 3,
        "四": 4,
        "五": 5,
        "六": 6,
        "七": 7,
        "八": 8,
        "九": 9,
        "零": 0,
        "壹": 1,
        "贰": 2,
        "叁": 3,
        "肆": 4,
        "伍": 5,
        "陆": 6,
        "柒": 7,
        "捌": 8,
        "玖": 9,
        "貮": 2,
        "两": 2,
    }
    cn_unit = {
        "十": 10,
        "拾": 10,
        "百": 100,
        "佰": 100,
        "千": 1000,
        "仟": 1000,
        "万": 10000,
        "萬": 10000,
        "亿": 100000000,
        "億": 100000000,
        "兆": 1000000000000,
    }

    lcn = list(cn_chars)
    unit = 0  # 当前的单位
    ldig = []  # 临时数组

    while lcn:
        cndig = lcn.pop()

        if cndig in cn_unit:
            unit = cn_unit.get(cndig)
            if unit == 10000:
                ldig.append("w")  # 标示万位
                unit = 1
            elif unit == 100000000:
                ldig.append("y")  # 标示亿位
                unit = 1
            elif unit == 1000000000000:  # 标示兆位
                ldig.append("z")
                unit = 1
        else:
            dig = cn_num.get(cndig)

            if unit:
                dig = dig * unit
                unit = 0

            ldig.append(dig)

    if unit == 10:  # 处理10-19的数字
        ldig.append(10)

    ret = 0
    tmp = 0

    while ldig:
        x = ldig.pop()

        if x == "w":
            tmp *= 10000
            ret += tmp
            tmp = 0

        elif x == "y":
            tmp *= 100000000
            ret += tmp
            tmp = 0

        elif x == "z":
            tmp *= 1000000000000
            ret += tmp
            tmp = 0

        else:
            tmp += x

    ret += tmp
    return ret


def process_text(raw_value):
    p_tail = re.compile(r"[的，。、；,.;]+$")

    if not raw_value:
        return None

    if is_in_white_list(raw_value):
        return raw_value

    raw_value = p_tail.sub("", raw_value)

    if "|_|_|" in raw_value:
        logging.warning("++++++Process text: %s", raw_value)
        return format_string(raw_value.replace("|_|_|", ";"))
    return format_string(raw_value)


def process_percentage(raw_value):
    p_tail = re.compile(r"[的，。、；,.;]+$")

    if not raw_value:
        return raw_value

    if "全部" in raw_value:
        return "100.00%"

    raw_value = p_tail.sub("", raw_value)

    if "|_|_|" in raw_value:
        calc_res = Decimal("0")
        for ele in raw_value.split("|_|_|"):
            if not ele:
                continue
            try:
                transfer_ele = process_percentage(ele)
                calc_res += normalize_val(transfer_ele)
            except Exception:
                logging.error("******Can not transfer |_|_| in value, %s", raw_value)
                return raw_value
        return comma_sep_thousands(calc_res, percentage=True, decimal_places=2)
    value = raw_value.replace("%", "")
    value = "".join(value.strip().split())

    try:
        value = normalize_val(value)
        value = comma_sep_thousands(value, decimal_places=2)
    except Exception:
        logging.error("******Can not process percentage: %s", raw_value)
        return raw_value
    return value + "%"


def grep_date(raw_value):
    """
    将日期转换为(YYYY,MM,DD)
    :param raw_value:
    :return:
    """
    if not raw_value:
        return False, raw_value
    if p_time_join.search(raw_value):
        grep_rets = [grep_date(d) for d in p_time_join.split(raw_value)]
        if all(ret[0] for ret in grep_rets):
            ret = "、".join([construct_standard_date(*ret[1]) for ret in grep_rets])
            return False, ret
        return False, raw_value
    if raw_value is None or raw_value == "至今":
        return False, raw_value
    value = format_string(raw_value)
    if not value or value == "-":
        return False, raw_value
    search_res = year_month_day_regexp.search(value)
    if not search_res:
        search_res = date_regexp.search(value)
        if not search_res:
            search_res = year_regexp.search(value)
            if not search_res:
                logging.warning("++++++grep_date: Date not matched - %s", raw_value)
                return False, raw_value
            return True, (search_res.group(1), "", "")
        year, month, day = search_res.groups()
        if not year:
            logging.warning("++++++grep_date: Date not matched - %s", raw_value)
            return False, raw_value
        return True, (year, month, day)
    date_res = search_res.group(1)
    if len(date_res) == 7:
        ret = (date_res[:4], date_res[4:5], date_res[5:])
    else:
        ret = (date_res[:4], date_res[4:6], date_res[6:])
    return True, ret


def construct_standard_date(year, month, day):
    res = year
    for ele in (month, day):
        if ele:
            if len(ele) == 1:
                ele = "0{}".format(ele)
            res += "-{}".format(ele)
        else:
            break
    return res


def ensure_duration(time_start, time_end, base):
    if time_end < time_start:
        logging.info("time_end:%s less than time_start:%s is invalid", time_end, time_start)
        return None

    year_1800 = datetime.strptime("1800-01-01", "%Y-%m-%d")
    if time_start < year_1800 or time_end < year_1800:
        logging.info("time_end:%s or time_start:%s is less than 1800", time_end, time_start)
        return None
    time_end = time_end - timedelta(days=1)
    delta = relativedelta(time_end, time_start)
    if not base or base == "年":
        return "{}年".format(delta.years + 1)
    if base == "月":
        return "{}月".format((delta.years * 12 + delta.months) + 1)
    return "{}天".format((time_end - time_start).days)


def is_date_duration(date_str):
    if already_date_period.search(date_str):
        return True
    return False


def extract_two_time_point(date_str):
    matched = p_time_range.search(date_str)
    if matched:
        start_year, start_month, start_day, end_year, end_month, end_day = matched.groups()
        try:
            if int(start_year) < 2000 or int(start_year) > 3000 or int(end_year) > 3000 or int(end_year) < 2000:
                return None
            time_start = datetime(int(start_year), int(start_month), start_day and int(start_day) or 1)
            time_end = datetime(int(end_year), int(end_month), end_day and int(end_day) or 1)
        except ValueError:
            logging.info("++++++extract_two_time_point: can not extract %s", date_str)
            return None
        return time_start, time_end
    matched = p_time_range_sp.search(date_str)
    if matched:
        start_year, end_year = matched.groups()
        time_start, time_end = datetime(int(start_year), 1, 1), datetime(int(end_year), 1, 1)
        return time_start, time_end
    if date_str:
        logging.info("++++++extract_two_time_point: can not extract %s", date_str)
    return None


def normalize_val(val):
    if val is None:
        return None
    val = val.strip("¥").strip("RMB").strip("rmb")
    if "(" in val:
        val = "-" + val
    try:
        normalized_val = Decimal(non_val_re.sub("", val))
        if "%" in val:
            return normalized_val / 100
        return normalized_val
    except ValueError:
        return None
    except InvalidOperation:
        return None


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


def table_size(cells):
    """

    :param cells:
    :return: [width, height]
    """
    keys = cells.keys()
    if not keys:
        return 0, 0
    rows, cols = zip(*[key.split("_") for key in keys])

    rows = map(int, rows)
    cols = map(int, cols)

    return max(cols) + 1, max(rows) + 1


def is_digital(value):
    """
    是否数字
    :param value:
    :return:
    """
    if not value:
        return False
    values = p_digital.findall(value)
    return len(values) and len(values[0]) == len(value)


def format_company_name(name):
    if not name:
        return name

    if is_in_white_list(name):
        return name

    name = remove_middle_char(name)
    name = use_chinese_parentheses(name)
    name = remove_tail_parentheses(name)
    name = clear_tail(name)
    name = remove_tail_parentheses(name)
    name = fix_tail(name)

    return name


def is_in_white_list(text):
    white_list = ["美的"]
    if text in white_list:
        return True

    return False


def remove_middle_char(raw_string):
    pattern = re.compile(r"[/\n\s]+")
    string = pattern.sub("", raw_string)
    return string


def use_chinese_parentheses(raw_string):
    pattern = re.compile(r"[\u4e00-\u9fa5]+[（(][\u4e00-\u9fa5]+[)）][\u4e00-\u9fa5]+")
    if pattern.search(raw_string):
        return raw_string.replace("(", "（").replace(")", "）")
    return raw_string


def remove_tail_parentheses(raw_string):
    pattern_0 = re.compile(r"^[\[【（(]|[)）】\]]$|[①②③④⑤⑥⑦⑧⑨⑩⑪⑫⑬⑭⑮]$")
    string = pattern_0.sub("", raw_string)

    pattern_1 = re.compile(r"[\[【（(][^)）】\]]*$")
    string = pattern_1.sub("", string)

    pattern_2 = re.compile(r"[\[【（(]$")
    string = pattern_2.sub(r"", string)
    return string


def clear_tail(raw_string):
    pattern = re.compile(r"[\[【]?([注]?\d{1,2})?$|的?总部$|的[统合]称|关联方$|为主$")
    string = pattern.sub("", raw_string)
    pattern_1 = re.compile(r"(.*[\u4e00-\u9fa5]+)[1-9]$")
    string = pattern_1.sub(r"\1", string)
    pattern_2 = re.compile(r"及受?其.*|及$|合[并计]$")
    string = pattern_2.sub("", string)
    pattern_3 = re.compile(r"等.*|")
    string = pattern_3.sub("", string) if not re.compile(r"[中高]等") else string
    return string


def fix_tail(raw_string):
    pattern_0 = re.compile(r"有限公$|有限司$|有限$")
    string = pattern_0.sub("有限公司", raw_string)
    pattern_1 = re.compile(r"(.*有限公司).$")
    pattern_2 = re.compile(r"^[，、。:,.．;]")
    string = pattern_1.sub(r"\1", string)
    if string.endswith("有限公司"):
        names = [pattern_2.sub("", x) for x in string.split("有限公司") if x]
        string = "、".join([f"{x}有限公司" for x in names])
    return string


def split_number_and_unit(text):
    if not text:
        return None, None
    res = re.match(r"^(?P<val>-?\d+(,\d+)*(\.\d+)?)(?P<unit>\D{0,4})$", text)
    if res:
        return res.group("val"), res.group("unit")
    return None, None


def format_bracket(string):
    return string.replace("（", "(").replace("）", ")")


def clean_field_name(name):
    name = format_string(format_bracket(name))
    for pattern in p_clean_punctuation_list:
        name = pattern.sub("", name)

    for pattern in p_clean_list:
        name = pattern.sub("", name)

    for pattern, patch in p_fix_list:
        name = pattern.sub(patch, name)

    return name


def filter_uncompleted_answer(answers_data):
    for table, items in answers_data.items():
        if not items or table not in key_field_map:
            continue

        completed_items = []
        for item in items:
            key_field = key_field_map[table]
            if item.get(key_field):
                completed_items.append(item)

        answers_data[table] = completed_items
    return answers_data


def split_by_table(sql_file):
    p_word = re.compile(r"\w+")

    sql = sql_file.read()
    sql_line_list = sql.split("\n")
    ret = {}
    table_item = {}
    create_table_sql = []
    table_name = ""
    for line in sql_line_list:
        if line.startswith("ALTER") or line.startswith("DROP"):
            continue
        if line.startswith("CREATE TABLE"):
            create_table_sql = []
            table_name = ""
            table_item = {}
            match = p_word.search(line.split("CREATE TABLE")[1])
            if match:
                table_name = match.group()
        if line.startswith("COMMENT =") and line.endswith(";"):
            match = p_word.search(line.split("COMMENT =")[1])
            if match:
                table_name_comment = match.group()
            else:
                raise Exception
            table_item["table_name"] = table_name
            table_item["create_table_sql"] = create_table_sql
            ret[table_name_comment] = table_item
        create_table_sql.append(line)

    return ret


def gen_field_dict(sql_file_path=None):
    if not sql_file_path:
        sql_file_path = os.path.join(project_root, "remarkable/plugins/zjh/output/mysql_schema.sql")
    with open(sql_file_path, encoding="utf-8") as file_obj:
        data_by_table = split_by_table(file_obj)

    for value in data_by_table.values():
        field_dict = {}
        field_name_to_column = {}
        create_table_sql_lines = value["create_table_sql"]
        for line in create_table_sql_lines:
            if line.startswith("COMMENT"):
                continue
            if "COMMENT" in line:
                line_list = line.split()
                column = line_list[0].strip("`")
                field_name = line_list[-1].strip("',")
                field_name = clean_field_name(field_name)
                if len(column) > 64:
                    logging.warning("%s %s", column, field_name)
                field_type = line_list[1]
                field_dict[column] = (field_name, field_type)
                field_name_to_column[field_name] = column
        value["field_dict"] = field_dict
        value["field_name_to_column"] = field_name_to_column

    return data_by_table


def select_table_file(ipo_db):
    sql_dict = gen_field_dict()
    fields = list(sql_dict["文件信息"]["field_dict"].keys())
    return select_from_db(ipo_db, "file", fields)


def select_from_db(ipo_db, table, fields, order_by=None):
    sql = """
        SELECT {} FROM {}
    """.format(",".join(fields), table)
    if order_by:
        sql += f"order by {order_by}"

    all_data = ipo_db.execute(sql).fetchall()
    ret = convert_query_rows_to_dict_list(all_data, fields)
    for item in ret:
        item["updated_utc"] = str(item["updated_utc"])
    return ret


def convert_query_rows_to_dict_list(all_data, fields):
    ret = []
    for data in all_data:
        data_dict = {}
        for idx, item in enumerate(data):
            field_name = fields[idx]
            data_dict[field_name] = item
        ret.append(data_dict)
    return ret


def answer_migrated_situation(answer):
    """
    一条答案各字段是否是迁移而来
    :param answer:
    :return:
    """
    total = 0
    migrated = 0
    for ans_item in answer.values():
        if ans_item.is_empty:  # 空答案不统计
            continue
        total += 1
        if ans_item._migrated:
            migrated += 1

    if migrated == 0:
        return "none"
    if migrated == total:
        return "all"
    return "mixed"


def fix_span_pages_row(label, label_to_col_idxes, tables):  # 未迁到新的表格标注逻辑中
    def copy_from_previous_table(cells, row, pre_table):
        width, height = table_size(pre_table["cells"])
        for col in range(width):
            cell = cells.get("{}_{}".format(row, col))
            pre_cell = pre_table["cells"].get("{}_{}".format(height - 1, col))
            if cell and cell["value"] == "" and pre_cell:
                cell["value"] = cell["value"] + pre_cell["value"]

    def merge_into_previous_table(cells, row, pre_table):
        width, height = table_size(pre_table["cells"])
        for col in range(width):
            cell = cells.pop("{}_{}".format(row, col), None)
            pre_cell = pre_table["cells"].get("{}_{}".format(height - 1, col))
            if cell and pre_cell:
                pre_cell["value"] = pre_cell["value"] + cell["value"]

    def fix_table_with_key_col():
        """
        指定的列[key col]为空即可认为是跨页
        :return:
        """
        first_table = tables[0]
        nul_col = get_num_col_idx(first_table)
        if nul_col is None:
            return
        for idx, table in enumerate(tables[1:]):
            cells = table["cells"]
            for row in [0, 1]:
                span_pages_row = cells.get("{}_{}".format(row, nul_col), {}).get("value") == ""
                independent_row = is_independent_row(label, label_to_col_idxes, row, table)
                if span_pages_row:
                    pre_table = tables[idx]
                    if independent_row:
                        copy_from_previous_table(cells, row, pre_table)
                    else:
                        merge_into_previous_table(cells, row, pre_table)
                    break

    def fix_table_with_col_header():
        """
        指定的列有内容,其他的都是空,认为是跨页
        :return:
        """
        for idx, table in enumerate(tables[1:]):
            cells = table["cells"]
            pre_table = tables[idx]
            for row in [0, 1]:
                if is_span_pages_row(label, label_to_col_idxes, row, table):
                    merge_into_previous_table(cells, row, pre_table)

    if label in keyword_col_label:
        fix_table_with_key_col()
        fix_table_with_col_header()


def get_num_col_idx(table):
    cells = table["cells"]
    width, height = table_size(cells)
    for col in range(width):
        cell_text = cells.get(f"0_{col}", {}).get("value", "")
        if p_serial_number.search(format_string(cell_text)):
            return col

    return None


def is_independent_row(label, label_to_col_idxes, row, table):
    for key_col in keyword_col_label[label]:
        col_idx = label_to_col_idxes.get(key_col)
        if not col_idx:
            continue
        cell = table["cells"].get("{}_{}".format(row, col_idx[0]))
        if not cell or not cell["value"]:
            return False
    return True


def is_span_pages_row(label, label_to_col_idxes, row, table):
    for key_col in keyword_col_label[label]:
        col_idx = label_to_col_idxes.get(key_col)
        if not col_idx:
            continue
        cells_by_row, _ = group_cells(table["cells"])

        row = str(row)
        row_cells = cells_by_row.get(row)
        if not row_cells:
            continue
        key_cell = row_cells.get(col_idx[0], {})
        other_cells = [cell for key, cell in row_cells.items() if key != col_idx[0]]
        if key_cell.get("value") and all((cell.get("value", "") == "" for cell in other_cells)):
            return True

    return False
