import logging
import os
import re
from collections import defaultdict

from remarkable.common.util import excel_row_iter
from remarkable.config import project_root
from remarkable.plugins.zjh.knowledge import Knowledge, customer_attribute
from remarkable.plugins.zjh.output.output_fields_info import (
    clean_field_name,
    is_in_output_fields,
    output_fields,
)
from remarkable.plugins.zjh.util import gen_field_dict


def check_main_table_output_fields():
    """
    主表科目完备性检查
    :return:
    """
    success = True
    path = os.path.join(project_root, "data/zjh/data_dictionary_20190704.xlsx")
    data_dictionary = defaultdict(list)
    for row in excel_row_iter(path, skip_rows=1, values_only=True):
        table = row[4]
        if table in ["合并现金流量表", "合并利润", "合并资产负债"]:
            name = row[5]
            name = clean_field_name(name)
            name = re.compile(r"\*$").sub("", name)
            if name not in ["报表日期", "货币单位", "唯一标识码", "外键", "编码"]:
                data_dictionary[table].append(name)

    # 检查数据字典中的科目是否都已写入output_fields
    for columns in data_dictionary.values():
        for column in columns:
            if not is_in_output_fields(column):
                success = False
                logging.error("output_fields lack %s, column")

    # 检查output_fields中的是否都在数据字典中
    for column, belongs in output_fields.items():
        if "合并现金流量表" in belongs:
            columns = data_dictionary["合并现金流量表"]
        elif "合并利润表" in belongs:
            columns = data_dictionary["合并利润"]
        elif "合并资产负债表" in belongs:
            columns = data_dictionary["合并资产负债"]
        else:
            success = False
            logging.error("unknown case")
            break
        if column not in columns:
            success = False
            logging.error("output_fields %s dos not exist in the data dictionary", column)

    # 检查output_fields中的科目是否在mysql_schema.sql中有对应列
    sql_fields = gen_field_dict()
    for column, belongs in output_fields.items():
        if "合并现金流量表" in belongs:
            columns = sql_fields["现金流量表"]
        elif "合并利润表" in belongs:
            columns = sql_fields["利润表"]
        elif "合并资产负债表" in belongs:
            columns = sql_fields["资产负债表"]
        else:
            success = False
            logging.error("unknown case")
            break
        if column not in columns["field_name_to_column"]:
            success = False
            logging.error("mysql_schema.sql lack %s", column)

    # 检查知识库的hack_subjects是否完备
    all_std_subjects = []
    for attrs in Knowledge.get_subjects().values():
        for attr in attrs:
            all_std_subjects.append(clean_field_name(attr["name"]))
    for subject, hack_sub in Knowledge.hack_subjects().items():
        if hack_sub == subject:
            logging.error("no necessary %s in hack_subjects", subject)
        if subject not in all_std_subjects:
            success = False
            logging.error("%s in hack_subjects not in Knowledge", subject)
    for column, _ in output_fields.items():
        if column not in all_std_subjects:
            # 数据字典中，不在知识库标准科目名中的，都应该在hack_subjects中配置其对应的标准科目
            if column not in Knowledge.hack_subjects().values():
                if column in [
                    "负债所有者权益",
                    "非流动负债_优先股",
                    "非流动负债_永续债",
                ]:  # 对应的标准科目已经配了其他别名，给定的数据字典的问题
                    continue
                success = False
                logging.error("%s should add into Knowledge.hack_subjects", column)

    # 检查是否有已有别名的标准科目在customer_subjects_to_alias中作key
    for subject in Knowledge.customer_subjects_to_alias():
        if subject in Knowledge.hack_subjects():
            logging.error(
                "%s in customer_subjects_to_alias should replaced with %s", subject, Knowledge.hack_subjects()[subject]
            )

    # 检查知识库的hack_subjects中来自数据字典的科目是否与最新数据字典一致
    for subject in Knowledge.hack_subjects().values():
        if not is_in_output_fields(subject):
            logging.error("Knowledge.hack_subjects %s not in output_fields", subject)
            success = False

    # hack_subjects中的key不应该存在于output_fields中,除非数据字典中确有该key
    for subject in Knowledge.hack_subjects():
        if is_in_output_fields(subject):
            # 这几个科目在数据字典中有同义科目,为了归并到同一个科目在hack_subjects中增加了映射关系
            white_list = ["筹资活动产生现金流量净额", "投资活动产生现金流量净额", "经营活动产生现金流量净额"]
            if subject in white_list:
                continue
            logging.error(
                "Knowledge.hack_subjects's key %s should not in output_fields as the same time, something wrong in "
                "data_dictionary",
                subject,
            )
            success = False

    # 检查知识库的customer_subjects_to_alias中来自数据字典的科目是否与最新数据字典一致
    for subject in Knowledge.customer_subjects_to_alias():
        if not is_in_output_fields(subject):
            logging.error("Knowledge.customer_subjects_to_alias %s not in output_fields", subject)
            success = False

    # output_fields中的科目不能存在于pass_subjects中
    for subject in output_fields:
        if Knowledge.is_in_pass_subjects(subject):
            logging.error("output_fields's subject %s can not in pass_subjects", subject)
            success = False

    # 检查Knowledge.hack_subject中的科目能否被转换成预期值
    for std_sub, customer_attr in Knowledge.hack_subjects().items():
        _customer_attr, _ = customer_attribute(std_sub)
        if _customer_attr != customer_attr:
            logging.error("%s should convert to %s, but %s", std_sub, customer_attr, _customer_attr)
            success = False

    # 检查Knowledge.customer_subjects_to_alias中的科目能否被转换成预期值
    for customer_attr, alias_list in Knowledge.customer_subjects_to_alias().items():
        for alias in alias_list:
            _customer_attr, _ = customer_attribute(alias)
            if _customer_attr != customer_attr:
                logging.error("%s should be convert to %s, but %s", alias, customer_attr, _customer_attr)
                success = False

    if not success:
        raise Exception("Miss the check about merge table fields")
    logging.info("Passed the check_main_table_output_fields.")


if __name__ == "__main__":
    check_main_table_output_fields()
