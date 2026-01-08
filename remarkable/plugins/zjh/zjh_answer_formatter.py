import hashlib
import json
import logging
import re
from collections import OrderedDict
from copy import deepcopy
from decimal import Decimal

from remarkable.answer.common import get_mold_name
from remarkable.answer.node import AnswerItem
from remarkable.answer.reader import dump_scriber_answer, load_scriber_answer
from remarkable.common.util import group_cells
from remarkable.plugins.zjh.knowledge import Knowledge, customer_attribute
from remarkable.plugins.zjh.util import (
    answer_migrated_situation,
    ensure_currency_unit,
    extract_currency_unit,
    format_company_name,
    format_date,
    format_number,
    format_string,
    is_date_field,
    is_left_col_is_num,
    is_number_field,
    longest_common_string,
    normalize_val,
    process_percentage,
    process_unit,
    split_number_and_unit,
    table_rows_to_skip,
    transfer_data_with_known_list,
    transfer_end_date,
    transfer_gender,
    transfer_movement_percentage,
    transfer_nationality,
    transfer_patent_date_field,
    transfer_unit,
)

p_number_enum = re.compile(r"(?P<number>\d)\s?\-")  # 1-xxx 形式的值


def _extract_major_client(answer, **kwargs):
    logging.info("_extract_major_client: start")
    data = {}
    idx = 0
    for item in answer.values():
        item_data = {}
        from_unit = None
        for field_name, field in item.items():
            if field_name == "货币单位":
                from_unit = field.plain_text
                break
        global_unit = from_unit
        for field_name, field in item.items():
            text = field.plain_text
            if any(i in field_name for i in ("占主营收入比例", "占总采购金额比例")):
                value = process_percentage(text)
            elif field_name in ["销售额", "采购额"]:
                global_unit, value = ensure_currency_unit(text, from_unit)
            elif is_date_field(field):
                value = format_date(field)
            elif field_name in ["客户名称", "供应商名称"]:
                value = format_company_name(text)
                if re.compile("前五大|合计").search(value):
                    break
            else:
                value = text

            field.plain_text = value
            item_data[field_name] = field
        else:
            item_data["货币单位"].plain_text = global_unit
            data[idx] = item_data
            idx += 1

    return data


def _search_unfill_fields(person_data, name, *unfill_fields):
    found_fields = {}
    if not unfill_fields:
        return found_fields
    for person_item in person_data.values():
        if person_item["姓名"].plain_text != name:
            continue
        for unfill_field in unfill_fields:
            if unfill_field in found_fields:
                continue
            if person_item[unfill_field] and person_item[unfill_field].plain_text:
                found_fields[unfill_field] = deepcopy(person_item[unfill_field])
        if len(found_fields) == len(unfill_fields):
            return found_fields
    return found_fields


def ensure_education_type(edu_string):
    if not edu_string:
        return ""

    education_list = [
        "学士",
        "本科",
        "硕士",
        "大专",
        "博士",
        "高中",
        "中专",
        "初中",
        "中学",
        "EMBA",
        "专科",
        "MBA",
        "MPAcc",
        "博士后",
        "其他",
    ]
    education_list_str = ",".join(education_list)
    education_map = {
        "学士": "本科",
        "大学": "本科",
        "中学": "高中",
        "研究生": "研究生",
        "大本学历": "本科",
        "硕士在读": "本科",
        "博士在读": "硕士",
        "MBA在读": "其他",
        "MBA研修": "其他",
        "EMBA在读": "其他",
        "EMBA研修": "其他",
    }
    if edu_string in education_map:
        return education_map[edu_string]
    idx, match = longest_common_string(edu_string, education_list_str)
    if len(match) > 1 and match in education_list:
        edu_type = education_map.get(match, match)
    else:
        for backup_key, value in education_map.items():
            if backup_key in edu_string:
                edu_type = value
                break
        else:
            edu_type = "其他"
            logging.warning("can not ensure_education_type: %s", edu_string)
    return edu_type


def _extract_manager_intro(answer, **kwargs):
    data = {}
    idx = 0
    for item in answer.values():
        item_data = {}
        for field_name, field in item.items():
            text = field.plain_text
            if field_name == "出生日期":
                text = format_date(field) if "岁" not in text else "无"
                text = text[:4]
            elif field_name == "境外居留权":
                if not text:
                    pass
                elif any((chars in text for chars in ["无", "未"])):
                    text = "无"
                else:
                    text = "有"
            elif field_name in ["任职日期", "离职日期"]:
                text = format_date(field)
            elif field_name == "性别代码":
                text = transfer_gender(text)
            elif field_name == "学历代码":
                text = ensure_education_type(text)
            elif field_name == "国籍地区代码":
                text = transfer_nationality(text)

            field.plain_text = text
            item_data[field_name] = field

        item_data["任职日期"].plain_text, item_data["离职日期"].plain_text = transfer_end_date(
            item_data["任职日期"].plain_text, item_data["离职日期"].plain_text
        )
        data[idx] = item_data
        idx += 1
    return data


def _extract_shareholder_intro(answer, **kwargs):
    data = {}
    idx = 0
    for item in answer.values():
        item_data = {}
        for field_name, field in item.items():
            text = field.plain_text
            if "名称" in field_name and re.compile(r"不存在|供股股东|实际控制人|^无$").search(text):
                break
            if field_name.endswith("比例"):
                value = process_percentage(text)
            elif "股份数量" in field_name:
                status, value = transfer_unit(text, to_unit="万股", from_unit="股", basic_unit="股")
            elif field_name == "国家及地区代码":
                value = transfer_nationality(text)
            elif field_name == "企业性质":
                value = transfer_data_with_known_list(text, subject="nature_of_business", default="其他")
            else:
                value = text

            field.plain_text = value
            item_data[field_name] = field
        else:
            data[idx] = item_data
            idx += 1
    return data


def reconstruct_major_contract(item_data):
    unit, unit_base = process_unit(item_data["货币单位"].plain_text)
    period_text = item_data["履行期限"].plain_text.replace("_", "-").replace("至", "-")

    global_unit, amount_transfer_res = ensure_currency_unit(
        item_data["合同金额"].plain_text, from_unit=unit, to_unit="万元"
    )
    contract_amount = amount_transfer_res
    if unit_base:
        try:
            contract_amount = str(normalize_val(amount_transfer_res) * Decimal(period_text.replace(unit_base, "")))
        except Exception:
            logging.error(
                "******Can not calc contract amount: period_text %s, unit %s, unit_base %s, contract number %s",
                period_text,
                unit,
                unit_base,
                amount_transfer_res,
            )

    constructed_data = {
        "货币单位": global_unit,
        "合同类型": item_data["合同类型"].plain_text,
        "合同对手方名称": item_data["合同对手方名称"].plain_text,
        "标的": item_data["标的"].plain_text,
        "合同金额": contract_amount,
        "已履行金额": ensure_currency_unit(item_data["已履行金额"].plain_text, from_unit=unit)[1],
        "履行期限": period_text,
        "备注": item_data["备注"].plain_text,
    }

    for field_name, value in constructed_data.items():
        field = item_data.get(field_name)
        if field:
            field.plain_text = value
        else:
            field = value

        constructed_data[field_name] = field

    return constructed_data


def _extract_major_contract(answer, **kwargs):
    logging.info("_extract_major_contract: start")
    p_contract_subject_filter = re.compile(r"(承销)|(保荐)")
    data = {}
    idx = 0
    for item in answer.values():
        item_data = {}
        for field_name, field in item.items():
            if field_name == "合同类型":
                value = field.plain_text or "其他"
            elif field_name == "合同对手方名称":
                value = re.compile("[和及、，]?发行人[和及、，]?").sub("", field.plain_text)
                value = format_company_name(value)
            elif field_name == "标的":
                value = field.plain_text
                if p_contract_subject_filter.search(value):
                    value = None
            else:
                value = field.plain_text

            field.plain_text = value
            item_data[field_name] = field

        data[idx] = reconstruct_major_contract(item_data)
        idx += 1
    return data


def _extract_issuer_profession(answer, **kwargs):
    logging.info("_extract_issuer_profession: start")
    data = {}
    idx = 0
    for item in answer.values():
        item_data = {}
        for field_name, field in item.items():
            if field_name == "行业分类标准":
                value = transfer_data_with_known_list(
                    field.plain_text,
                    subject="industry_classification_standard",
                    default="其他",
                    indistinct_supplement=False,
                )
            elif field_name == "行业分类名称":
                value = transfer_data_with_known_list(
                    field.plain_text,
                    subject="industry_classification_name",
                    indistinct_supplement=False,
                )
            elif field_name == "行业分类代码":
                value = transfer_data_with_known_list(
                    field.plain_text,
                    subject="industry_classification_code",
                    indistinct_supplement=False,
                )
            else:
                logging.error("invalid field_name:%s in _extract_issuer_profession", field_name)
                continue

            field.plain_text = value
            item_data[field_name] = field

        data[idx] = item_data
        idx += 1
    return data


def _extract_profit_ability(answer, **kwargs):
    data = {}
    to_unit = "万元"
    idx = 0
    for item in answer.values():
        item_data = {}
        for field_name, field in item.items():
            if field_name.startswith("占比"):
                value = process_percentage(field.plain_text)
            elif field_name.startswith("变动比例"):
                value = transfer_movement_percentage(field.plain_text)
            elif field_name.startswith("金额"):
                value = format_number(field.plain_text)

            elif is_date_field(field):
                value = format_date(field)
            else:
                value = field.plain_text

            field.plain_text = value
            item_data[field_name] = field

        success, amount = transfer_unit(
            item_data["金额"].plain_text, to_unit, from_unit=item_data["货币单位"].plain_text
        )
        if success:
            item_data["金额"].plain_text = amount
            item_data["货币单位"].plain_text = to_unit

        data[idx] = item_data
        idx += 1
    return data


def remove_duplicates(ipo_data):
    """
    去重
    :param ipo_data:
    :return:
    """
    result = OrderedDict()
    for key, data in ipo_data.items():
        if not (isinstance(data, list) and len(data) > 1):
            result[key] = data
            continue

        ret = OrderedDict()
        for item in data:
            item_dumps = "".join([json.dumps(get_all_boxes(v.data)) for v in item.values()])
            _hash = hashlib.md5(item_dumps.encode()).hexdigest()
            ret.setdefault(_hash, item)

        ret = [dic for _, dic in ret.items()]
        result[key] = ret
    return result


def get_all_boxes(result):
    boxes = []
    for res in result:
        boxes.extend(res["boxes"])

    return boxes


def _fix_answer(answer):
    text = answer.plain_text

    value = answer.value
    if value:  # 枚举类型
        match = p_number_enum.search(value)
        if match:
            text = match.groupdict()["number"]
        else:
            text = value

    if answer.manual:  # 标注人员修改过的[导出的答案]可能会有格式错误
        revised_text = None
        if is_number_field(answer):
            revised_text = format_number(text)
        elif is_date_field(answer):
            revised_text = format_date(answer)

        if revised_text and text != revised_text:
            logging.info("%s is revised to %s", text, revised_text)
            text = revised_text

    text = format_string(text)
    answer.plain_text = text


def fix_answer(answers):
    for value in answers.values():
        if isinstance(value, AnswerItem):
            _fix_answer(value)
        elif isinstance(value, dict):
            fix_answer(value)
        elif isinstance(value, list):
            for item in value:
                fix_answer(item)
        else:
            raise Exception("Invalid answer")


class ZJHAnswerFormatter:
    def __init__(self, reader):
        self.reader = reader
        self.old_handlers = {
            "主要客户": _extract_major_client,
            "主要供应商": _extract_major_client,
            "重大合同": _extract_major_contract,
            "发行人所处行业": _extract_issuer_profession,
            "控股股东简要情况": _extract_shareholder_intro,
            "实际控制人简要情况": _extract_shareholder_intro,
            "盈利能力": _extract_profit_ability,
            "董监高核心人员基本情况": _extract_manager_intro,
        }
        self.handlers = {
            "股权结构": self._extract_ownership_structure,
            "基本财务指标": self._extract_main_financial_indexes,
            "专利": self._extract_patent,
        }

        self.assist_handlers = {
            "董监高核心人员基本情况": self.manager_info_assist,
            "合并资产负债表": self.main_table_assist,
            "合并现金流量表": self.main_table_assist,
            "合并利润表": self.main_table_assist,
        }

    @staticmethod
    def field_skip_revise(field_name, field):
        ignore_keys = [
            re.compile(r"[序编][号码]|时间|标志"),
            re.compile("次/年|倍数|[（(]元[)）]|^<.*>$|^[（(].*[)）]$"),
        ]
        if not field.plain_text:
            return True
        if any(reg.search(field_name) for reg in ignore_keys):
            return True
        return False

    def _revise(self, label, data):
        if not isinstance(data, list):
            return data
        for item in data.values():
            if isinstance(item, dict):
                field_to_update = {}
                for field_name, field in item.items():
                    for _revise_handler in [
                        self._revise_currency_number,
                        self._revise_datetime,
                        self._revise_percentage,
                    ]:
                        success, new_field = _revise_handler(label, field_name, field, item)
                        if success and new_field:
                            field_to_update.update(new_field)
                            break
                for key, value in field_to_update.items():
                    item[key].plain_text = value
            else:
                raise Exception
        return data

    def _revise_currency_number(self, label, field_name, field, fields):
        if self.field_skip_revise(field_name, field) or not is_number_field(field):
            return False, None

        if re.search(r"率|比[重例]|利率|占.*比", field_name):
            return False, None

        val_str, unit = split_number_and_unit(field.plain_text)
        if not val_str:
            return False, None

        unit_field_name = ""
        if field_name:
            for key_word in ["<数量单位>", "<金额单位>", "货币单位", "单位"]:
                if key_word in fields:
                    unit_field_name = key_word
                    break

        if not unit:
            unit = fields[unit_field_name].plain_text if unit_field_name else ""

        if unit == "":
            if field_name in ["注册资本"]:
                unit = "元"

        if unit == "人民币" or unit.endswith("元"):
            to_unit = "万元"
        elif unit == "股":
            to_unit = "万股"
        else:
            to_unit = unit
        status, value = transfer_unit(val_str, from_unit=unit, to_unit=to_unit)
        if status:
            fields[field_name].plain_text = value
            if unit_field_name:
                return True, {unit_field_name: to_unit}
            else:
                return True, None

        return False, None

    def _revise_percentage(self, label, field_name, field, fields):
        if self.field_skip_revise(field_name, field):
            return False, None

        if not field_name or not re.search(r"率|比[重例]|利率|占.*比", field_name):
            return False, None

        unit_field_name = "<百分比单位>"
        unit_field = fields.get(unit_field_name)
        if unit_field and unit_field.plain_text:
            field.plain_text = field.plain_text + unit_field.plain_text
            return True, None

        return False, None

    def _revise_datetime(self, label, field_name, field, fields):
        if self.field_skip_revise(field_name, field):
            return False, None

        if not field_name or not re.search(r"履行期限|折旧年限", field_name):
            return False, None

        unit_field_name = "<时间单位>"
        unit_field = fields.get(unit_field_name)
        if unit_field and unit_field.plain_text:
            field.plain_text = field.plain_text + unit_field.plain_text
            return True, None

        return False, None

    def _simple_text(self, answer):
        if isinstance(answer, AnswerItem):
            return answer.plain_text
        data = self._extract_basic_data(answer)
        return data

    def _extract_basic_data(self, answer):
        data = {}
        idx = 0
        for item in answer.values():
            item_data = {}
            any_value_exist = False
            for field_name, field in item.items():
                text = field.plain_text
                if text:
                    if is_number_field(field):
                        unit = extract_currency_unit(text)
                        value = format_number(text)
                        if value:
                            value += unit
                    elif is_date_field(field):
                        value = format_date(field)
                    else:
                        value = text

                    if value:
                        any_value_exist = True
                    field.plain_text = value
                item_data[field_name] = field
            if any_value_exist:
                data[idx] = item_data
                idx += 1
        return data

    def _extract_ownership_structure(self, label, answer):
        data = self._simple_text(answer)
        data = self._revise(label, data)
        for item in data.values():
            item["股东排名"].plain_text = item["股东排名"].plain_text.split(".")[0]
            item["主体名称"].plain_text = format_company_name(item["主体名称"].plain_text)
        return data

    def _extract_main_financial_indexes(self, label, answer):
        data = self._simple_text(answer)
        return data

    def _extract_patent(self, label, answer):
        data = self._simple_text(answer)
        data = {key: transfer_patent_date_field(item) for key, item in data.items()}
        return data

    def format(self, answers_dict):
        result = {}
        if not answers_dict:
            return result
        answer_tree = load_scriber_answer(answers_dict)
        if not answer_tree:
            return result
        mold_name = get_mold_name(answers_dict)
        root_node = answer_tree[mold_name]

        for label, answers in root_node.items():
            logging.debug(label)  # only for debug
            if "释义" not in label:  # only for debug
                # continue
                pass

            migrate = self.migrated_situation(answers)
            if migrate == "all":  # 该一级字段下的大难都是迁移而来，跳过下面的handler
                result[label] = answers.values()
                continue
            if migrate == "mixed":
                raise Exception("invalid situation")

            if label in self.old_handlers:
                data = self.old_handlers[label](answers, label=label)
            elif label in self.handlers:
                data = self.handlers[label](label, answers)
            else:
                data = self._simple_text(answers)
                data = self._revise(label, data)

            result[label] = data

        result = remove_duplicates(result)
        fix_answer(result)
        return result

    def manager_info_assist(self, answers, **kwargs):
        for answer in answers.values():
            # 补齐为空的字段
            unfill_fields = [field for field, item in answer.items() if not item or item.is_empty]
            found_fields = _search_unfill_fields(answers, answer["姓名"].plain_text, *unfill_fields)
            for key, answer_item in found_fields.items():
                answer[key].plain_text = answer_item.plain_text
                answer[key].text = answer_item.plain_text
                answer[key].value = answer_item.value

        return answers

    def main_table_assist(self, answers, **kwargs):
        for answer in answers.values():
            text = answer["项目"].plain_text
            attr, clean_value = customer_attribute(text)

            if not attr:
                in_pass_subjects = any((Knowledge.is_in_pass_subjects(item) for item in [text, clean_value, attr]))
                if clean_value and attr is None and not in_pass_subjects:
                    logging.warning("%s does not exist in knowledge", text)
                continue

            answer["项目"].plain_text = attr
            answer["项目"].text = attr

        return answers

    def answer_assist(self, answer, column):
        """
        对指定column的答案进行补充/处理
        :param:
        :return:
        """
        answer_tree = load_scriber_answer(answer)
        if not answer_tree:
            return answer

        mold_name = get_mold_name(answer)
        root_node = answer_tree[mold_name]
        root_node[column] = self.assist_handlers[column](root_node[column])
        answer["userAnswer"]["items"] = dump_scriber_answer(root_node)
        return answer

    @staticmethod
    def table_skip_rows(column, table, sample):
        if column in ["合并资产负债表", "合并现金流量表", "合并利润表"]:
            return []
        left_col_is_num = is_left_col_is_num(table)
        cells_by_row, _ = group_cells(table["cells"])
        bottom_box = {}
        for item in sample.values():
            if item.get("common"):  # 跳过公共字段
                continue
            box = item.get("box")
            if not box:
                continue
            if not bottom_box or box["box"][3] > bottom_box["box"][3]:
                bottom_box = box
        skip_after = column in ["释义"]
        rows_to_skip = table_rows_to_skip(column, cells_by_row, left_col_is_num, bottom_box, skip_after)
        return [int(i) for i in rows_to_skip]

    @staticmethod
    def format_table(table):
        for cell in table["cells"].values():
            cell["text"] = format_string(cell["text"])
        return table

    @staticmethod
    def migrated_situation(answers):
        total = 0
        migrated = 0
        for answer in answers.values():
            total += 1
            answer_situation = answer_migrated_situation(answer)
            if answer_situation == "mixed":
                return "mixed"
            elif answer_situation == "all":
                migrated += 1

        if migrated == 0:
            return "none"
        elif migrated == total:
            return "all"
        else:
            return "mixed"

    @classmethod
    def check_migrated_situation(cls, answers):
        answer_tree = load_scriber_answer(answers)
        if not answer_tree:
            return answers

        mold_name = get_mold_name(answers)
        root_node = answer_tree[mold_name]
        for column, answer in root_node.items():
            answer_situation = cls.migrated_situation(answer)
            if answer_situation == "mixed":
                return False, column

        return True, ""
