import json
import logging
import re
from collections import OrderedDict, defaultdict
from itertools import groupby

from remarkable.plugins.zjh.knowledge import customer_attribute
from remarkable.plugins.zjh.output.client_field_checker import known_current_title
from remarkable.plugins.zjh.output.output_fields_info import CLASS_CATE, CLASS_TABLE, output_fields
from remarkable.plugins.zjh.util import (
    filter_uncompleted_answer,
    key_field_map,
    longest_common_string,
    p_decimal_point,
    process_text,
    transfer_yes_and_no,
)

paraphrase_title = re.compile(r"名词|释义|词语")
sentence_regexp = re.compile(r"([，。])")


def gen_json_data(export_answer, filename, project_name, publish_date, debug=False):
    if debug:
        return gen_debug_json(export_answer)
    res = {}
    for key, data in export_answer.items():
        answers = []
        for answer in data.values():
            for field_name, ans_item in answer.items():
                answer[field_name] = ans_item.plain_text
            answers.append(answer)
        res[key] = answers

    res = ipo_data_json_style(res, project_name, filename)

    res["招股说明书名称"] = filename
    res["招股说明书申报披露时间"] = publish_date

    res = reorder_ipo_data(res)
    res = standard_output_dict(res)
    res = filter_uncompleted_answer(res)
    return res


def gen_debug_json(export_answer):
    white = [
        "合并资产负债表",
        "合并利润表",
        "合并现金流量表",
        "基本财务指标",
        "发行人基本情况",
        "控股股东简要情况",
        "实际控制人简要情况",
        "发行人所处行业",
        "董监高核心人员基本情况",
        "审计意见",
        "盈利能力",
    ]
    export_answer = filter_span_page_answer(export_answer, white)
    res = defaultdict(list)
    for key, value in export_answer.items():
        for item in value["items"]:
            res[key].append(int(item["index"]) + 1)

    return res


def filter_span_page_answer(export_answer, white):
    """
    找出可能跨页的答案
    :param export_answer:
    :param white:
    :return:
    """

    def get_page(field):
        if not field["data"] or not field["data"][0]["boxes"]:
            return 0
        return field["data"][0]["boxes"][0]["page"]

    def get_index(field):
        parent_key = json.loads(field["key"])[-2]
        return parent_key.split(":")[-1]

    ret = {}
    for key, value in export_answer.items():
        if key in white:
            continue
        for item in value["items"]:
            key_field = get_key_field(key, item)
            item["page"] = get_page(key_field)
            item["index"] = get_index(key_field)

        data = []
        for _, group in groupby(sorted(value["items"], key=lambda x: x["page"]), key=lambda x: x["page"]):
            most_near_to_header = (None, None)
            most_near_to_footer = (None, None)
            group = list(group)
            for item in group:
                key_field = get_key_field(key, item)
                top, bottom = distance_to_page_margin(key_field)
                if not (top and bottom):
                    continue
                if most_near_to_header[0] is None or top < most_near_to_header[1]:
                    most_near_to_header = (item, top)
                if most_near_to_footer[0] is None or bottom > most_near_to_footer[1]:
                    most_near_to_footer = (item, bottom)

            if most_near_to_header[0] and most_near_to_header[1] < 150:
                data.append(most_near_to_header[0])
            if most_near_to_footer[0] and most_near_to_footer[1] > 700:
                data.append(most_near_to_footer[0])

        ret[key] = {"schema": value["schema"], "items": data}
    return ret


def get_key_field(schema, item):
    key_field = key_field_map[schema]
    for field in item.values():
        field_key = field.key or ""
        if key_field in field_key:
            return field
    return None


def distance_to_page_margin(field):
    top = None
    bottom = None
    if field["data"]:
        boxes = field["data"][0]["boxes"]
        if boxes:
            box = boxes[0]["box"]
            top = box["box_top"]
            bottom = box["box_bottom"]
    return top, bottom


def ipo_data_json_style(ipo_data, project_name, filename):
    def format_shareholder_intro(data):
        res = defaultdict(list)
        for item_data in data:
            new_data = {}
            for field_name, val_str in item_data.items():
                if field_name.endswith("比例") and not field_name.endswith("(%)"):
                    field_name = "{}(%)".format(field_name)
                elif "股份数量" in field_name and not field_name.endswith("(万股)"):
                    field_name = "{}(万股)".format(field_name)
                elif field_name.endswith("标志"):
                    val_str = transfer_yes_and_no(val_str)
                new_data[field_name] = val_str
            key_filed = item_data.get("主体类型") or item_data.get("实际控制人类型")
            res[key_filed].append(new_data)
        return res

    def format_major_client(data):
        for item_data in data:
            for field_name, val_str in item_data.items():
                if field_name == "公司关联方标识":
                    val_str = transfer_yes_and_no(val_str)
                elif field_name in ["下属单位名称", "采购内容"]:
                    if not val_str:
                        val_str = "未披露"
                item_data[field_name] = val_str

        return data

    def format_profit_ability(data):
        for item_data in data:
            item_data["类别"] = item_data.pop("产品类别")

        return data

    def format_paraphrase(data):
        for item_data in data:
            item_data["全称"] = re.split(sentence_regexp, item_data["全称"])[0].strip()

        return data

    def format_major_contract(data):
        for item_data in data:
            for field_name, val_str in item_data.items():
                if field_name == "合同类型" and val_str and not val_str.endswith("合同"):
                    val_str = f"{val_str}合同"
                item_data[field_name] = val_str

        return data

    def get_board(project_name, filename):
        if "主" in project_name:
            if "创业板" in filename:
                board = "创业板"
            else:
                board = "主板"
        elif "科" in project_name:
            board = "科创板"
        elif project_name == "创业板":
            board = "创业板"
        else:
            board = "null"
        return board

    def format_issuer_information(data, board):
        if board == "创业板":
            data[0]["拟上市的交易场所代码"] = "深圳证券交易所"
        elif board == "科创板":
            data[0]["拟上市的交易场所代码"] = "上海证券交易所"

        return data

    def format_manager_info(data, company_name):
        for item_data in data:
            for field_name, val_str in item_data.items():
                if field_name == "担任职务":
                    val_str = reconstruct_current_title(val_str, company_name)
                item_data[field_name] = val_str

        return data

    # 三大表数据格式调整
    ipo_data = structure_main_tables_data(ipo_data)
    # 合并 合并报表和主要财务指标
    ipo_data["财务基本情况及财务指标"] = merge_financial_data(ipo_data)

    ipo_data["控股股东简要情况"] = format_shareholder_intro(ipo_data["控股股东简要情况"])
    ipo_data["实际控制人简要情况"] = format_shareholder_intro(ipo_data["实际控制人简要情况"])
    ipo_data["主要客户"] = format_major_client(ipo_data["主要客户"])
    ipo_data["主要供应商"] = format_major_client(ipo_data["主要供应商"])
    ipo_data["盈利能力"] = format_profit_ability(ipo_data["盈利能力"])
    ipo_data["释义"] = format_paraphrase(ipo_data["释义"])
    ipo_data["重大合同"] = format_major_contract(ipo_data["重大合同"])
    ipo_data["板块"] = get_board(project_name, filename)
    ipo_data["发行人基本情况"] = format_issuer_information(ipo_data["发行人基本情况"], ipo_data["板块"])
    ipo_data["董监高核心人员基本情况"] = format_manager_info(
        ipo_data["董监高核心人员基本情况"], ipo_data["发行人基本情况"][0]["主体名称"]
    )

    return ipo_data


def structure_main_tables_data(ipo_data):
    logging.info("structure_tables_data: start")
    ret = {"合并资产负债表": defaultdict(), "合并现金流量表": defaultdict(), "合并利润表": defaultdict()}
    for table_name in ret:
        data = ipo_data[table_name]
        data_dict = defaultdict(dict)
        for item_data in data:
            time = item_data["报表日期"]
            subject = item_data["项目"]
            subject, _ = customer_attribute(subject)
            value = item_data.get("金额")
            data_dict[time][subject] = value

        ipo_data[table_name] = data_dict

    for subject, parents in output_fields.items():
        table_name = parents[CLASS_TABLE]
        for time, values in ipo_data[table_name].items():
            semantic_data = values.get(subject)

            if len(parents) == 2:
                if time not in ret[table_name]:
                    ret[table_name][time] = {subject: semantic_data}
                else:
                    ret[table_name][time][subject] = semantic_data
            elif len(parents) == 3:
                parent_subject = parents[CLASS_CATE]
                if time not in ret[table_name]:
                    ret[table_name][time] = {parent_subject: {subject: semantic_data}}
                elif parent_subject not in ret[table_name][time]:
                    ret[table_name][time][parent_subject] = {subject: semantic_data}
                else:
                    ret[table_name][time][parent_subject][subject] = semantic_data
            else:
                raise Exception
    ipo_data.update(ret)
    return ipo_data


def merge_financial_data(answer_data):
    logging.info("merge_financial_data: start")
    financial_data = answer_data.pop("基本财务指标")

    structure_financial_indexes = defaultdict(dict)
    for item_data in financial_data:
        report_date = item_data["报表日期"]
        if not report_date:
            raise Exception("主要财务指标报表日期缺失!")
        structure_financial_indexes[report_date] = item_data

    table_data = {
        "合并资产负债表": answer_data.pop("合并资产负债表"),
        "合并现金流量表": answer_data.pop("合并现金流量表"),
        "合并利润表": answer_data.pop("合并利润表"),
    }
    # 合并资产负债表的在三年一期之外,可能会有一个单独的存量, 例如[北京国科环宇科技]
    report_dates = table_data["合并资产负债表"].keys()

    merge_res = []
    for time in report_dates:
        item = {"货币单位": "万元", "报表日期": time}
        for table, table_value in table_data.items():
            item[table] = table_value.get(time, [])
        item["主要财务指标表"] = structure_financial_indexes.get(time, [])
        merge_res.append(item)
    return merge_res


def reconstruct_current_title(current_title, company_name):
    entities = {
        "有限公司",
        "厂",
        "学校",
        "大学",
        "学院",
        "总店",
        "宾馆",
        "饭店",
        "商店",
        "酒店",
        "总院",
        "研究院",
        "商会",
        "事务所",
        "设计院",
        "研究所",
        "业务部",
        "研究部",
        "经营部",
        "食品",
        "办事处",
        "销售部",
        "采购部",
        "工程处",
        "贸易部",
        "（有限合伙）",
        "(有限合伙)",
        "协会",
        "人民代表大会",
        "促进会",
        "公司",
        "委员会",
        "控股",
    }
    join_entities = ",".join(entities)
    current_companies = ("发行人", "本公司", "公司", "现任本公司", "本行")
    possible_titles = {
        "财务总监兼董事会秘书",
        "税务主管",
        "监事会主席",
        "职工监事",
        "董事长",
        "执行董事",
        "副董事",
        "副总经理",
        "副秘书长",
        "独立董事",
        "执行主任",
        "管理合伙人",
        "总经理",
        "董事",
        "监事",
        "生产总监",
        "首席执行官兼董事",
        "主任工程师",
        "工程师",
        "研发部总监",
        "研发总监",
        "生产部总监",
        "首席财务官",
        "董事会秘书",
        "职工代表监事",
        "仲裁员",
        "财务总监",
        "总监",
        "董事兼首席财务官",
        "总工程师",
        "律师",
        "主任",
        "教授",
        "技术秘书",
        "副主任",
        "主任委员",
        "常务理事",
        "常务副秘书长",
    }
    known_title_list = known_current_title()
    join_possible_titles = ",".join(possible_titles.union(known_title_list))

    def cross_verify(company, title):
        for entity in entities:
            if entity in title:
                logging.error("******Cross verify failed in title: %s", title)
                return False
        for possible_title in possible_titles:
            if possible_title in company:
                logging.error("******Cross verify failed in company: %s", company)
                return False
        return True

    def known_title_check(titles):
        known_list = known_current_title()
        cross_fields = OrderedDict()
        for title in titles:
            if title in known_list:
                cross_fields[title] = ""
            else:
                cross_fields["其他"] = ""
        return cross_fields.keys()

    current_titles = defaultdict(list)
    errors = []

    p_colon = re.compile(r"[:：]")
    if p_colon.search(current_title):  # 人工做了划分的
        p_separators = re.compile(r"[;；。]")
        sep = p_separators.split(current_title)
        for item in sep:
            if not p_colon.search(item):
                continue
            companys = p_colon.split(item)[0]
            titles = p_colon.split(item)[1]
            for company in re.split(re.compile(r"、"), companys):
                for title in re.split(re.compile(r"、"), titles):
                    clean_value = clean_name(title)
                    if clean_value:
                        current_titles[clean_name(company)].append(clean_value)
    else:
        separators = re.compile(r"[,;；.。、，和]")

        sep_res = re.split(separators, current_title)
        last_company = "本公司"
        for sep_item in sep_res:
            if not sep_item:
                continue
            start, matched = longest_common_string(sep_item, join_entities)
            if len(matched) <= 1 or matched not in entities:
                start, matched = longest_common_string(sep_item, join_possible_titles)
                if len(matched) <= 1 or matched not in possible_titles or start <= 1:
                    logging.warning("++++++sep_item: %s can not be detected!", sep_item)
                    sep_idx = 0
                else:
                    sep_idx = start
            else:
                sep_idx = start + len(matched)
            if sep_idx == 0:
                title = sep_item
                company = last_company
            else:
                company, title = sep_item[:sep_idx], sep_item[sep_idx:]
                last_company = company
            if cross_verify(company, title):
                clean_value = clean_name(title)
                if clean_value:
                    current_titles[clean_name(company)].append(clean_value)
            else:
                logging.error("company: %s, title: %s failed in cross_verify", company, title)
                errors.append(sep_item)

    if len(errors) <= 1:
        for key, value in current_titles.items():
            current_titles[key] = known_title_check(value)
        res = []
        for key, value in current_titles.items():
            for item in current_companies:
                if key.startswith(item):
                    key = company_name  # 发行人+xx部 ==> 发行人公司名全称
                    break
            for value_ele in value:
                res.append("{}:{}".format(key, value_ele))
        return ";".join(res)
    return None


def clean_name(name):
    p_punctuation = re.compile(r"[;；。，]")
    name = p_punctuation.sub("", name)
    clean_attrs = ["兼任", "并兼任", "任"]
    clean_tails = ["一职"]
    for clean_attr in clean_attrs:
        name = name.lstrip(clean_attr)

    for tail in clean_tails:
        if name.endswith(tail):
            name = name.replace(tail, "")

    return name


def reorder_ipo_data(ipo_data):
    orders = [
        "招股说明书申报披露时间",
        "招股说明书名称",
        "板块",
        "释义",
        "发行人基本情况",
        "控股股东简要情况",
        "实际控制人简要情况",
        "董监高核心人员基本情况",
        "财务基本情况及财务指标",
        "重大诉讼事项",
        "募集资金与运用",
        "专利",
        "主要客户",
        "主要供应商",
        "重大合同",
        "发行人所处行业",
        "盈利能力",
        "财务报表附注",
        "发行人员工及结构情况",
        "股权结构",
        "审计意见",
        "非经常性损益情况",
        "关联交易",
        "税款缴纳情况",
        "应收账款",
        "预付账款",
        "存货减值",
        "固定资产折旧",
        "无形资产",
        "净利润与经营活动净现金流量差异",
        "商誉减值准备",
        "基本财务指标",
        "合并资产负债表",
        "合并现金流量表",
        "合并利润表",
    ]
    order_ipo_data = OrderedDict()
    for order in orders:
        if order not in ipo_data:
            logging.warning("++++++缺少字段: %s", order)
        order_ipo_data[order] = ipo_data.get(order)

    return order_ipo_data


def format_data_item(key, value):
    useless = ["-", "", "—", "--", "/", "不适用", "N/A", "（注）", "无"]
    if value is None:
        return None

    if key in ("境外居留权", "有/无重大诉讼事项"):
        useless.pop(-1)

    if key in ["人数"]:
        value = p_decimal_point.sub("", value)

    raw_value = value
    if raw_value in useless:
        text = None
    else:
        text = process_text(raw_value)

    return text


def standard_output_dict(_dict):
    processed_dict = OrderedDict()
    for key, value in _dict.items():
        if isinstance(value, dict):
            _value = standard_output_dict(value)
        elif isinstance(value, list):
            _value = standard_output_list(value)
        else:
            _value = format_data_item(key, value)
        processed_dict[key] = _value
    return processed_dict


def standard_output_list(_list):
    processed_list = []
    for item in _list:
        if isinstance(item, dict):
            _item = standard_output_dict(item)
        elif isinstance(item, list):
            _item = standard_output_list(item)
        else:
            _item = format_data_item(item)  # TODO: 这是干啥的? pylint: disable=no-value-for-parameter
        processed_list.append(_item)
    return processed_list


def find_date_folder_name(file_tree, tree_id):
    folder_name, ptree_id = get_folder_name(file_tree, tree_id)
    if not re.compile(r"\d{8}").search(folder_name):
        if ptree_id == 0:
            raise Exception("No parent folder!")
        folder_name = find_date_folder_name(file_tree, ptree_id)
    return folder_name


def get_folder_name(file_tree, tree_id):
    for file_tree_id, ptree_id, name in file_tree:
        if tree_id == file_tree_id:
            return name, ptree_id
    return None, None
