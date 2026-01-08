import json
import os
import re
from datetime import datetime

import xlwt

from remarkable.config import get_config, target_path


def get_file_name_map():
    with open("file-info-map.json") as load_fp:
        file_info_map = json.load(load_fp)
        return file_info_map


def get_file_name_list_from_outputs(set_name):
    file_name_list = []
    base_dir = "/Users/liuchao/Downloads/outputs/"
    full_root_path = os.path.join(base_dir, "outputs_" + set_name, "元素抽取")
    for _file in os.listdir(full_root_path):
        if _file.endswith("json"):
            file_name_list.append(_file.split(".", 1)[0])
    return file_name_list


def output_failed_checker(set_name):
    print("++++++++++++未成功提取到outputs/+++++++++++")
    file_info_map = get_file_name_map()
    file_name_list_from_outputs = get_file_name_list_from_outputs(set_name)
    for data in file_info_map["data"]:
        name = data["filename"]
        if name not in file_name_list_from_outputs:
            print(data["filename"], data["file_id"])


def check_file_name_map():
    print("\n+++++++++++同一份文件对应多个id:++++++++++++")
    file_info_map = get_file_name_map()
    name_list = []
    repeat_name_list = []
    for data in file_info_map["data"]:
        name = data["filename"]
        if name not in name_list:
            name_list.append(name)
        else:
            repeat_name_list.append(name)

    for repeat_name in repeat_name_list:
        print(repeat_name)
        for data in file_info_map["data"]:
            if data["filename"] == repeat_name:
                print(data["file_id"])


def extract_info_from_json():
    ipo_root_path = get_config("zjh.ipo_results_dir")
    target_files = os.listdir(ipo_root_path)
    target_files = [file for file in target_files if file.lower().endswith("json")]
    company_names = []
    client_names = []
    supplier_names = []
    for ipo_data_path in target_files:
        with open(os.path.join(ipo_root_path, ipo_data_path), "r", encoding="utf-8") as file_obj:
            ipo_res = json.load(file_obj)
        company_names.append(ipo_res["发行人基本情况"]["主体名称"])
        client_names.extend([item["客户名称"] for item in ipo_res["主要客户"]])
        supplier_names.extend(item["供应商名称"] for item in ipo_res["主要供应商"])

    workbook = xlwt.Workbook(encoding="utf-8")
    worksheet_company = workbook.add_sheet("主体名称")
    for row, item in enumerate(company_names):
        worksheet_company.write(row, 0, item)

    worksheet_client = workbook.add_sheet("主要客户")
    row = 0
    for item in set(client_names):
        for name in split_company_name(item):
            row += 1
            worksheet_client.write(row, 0, name)

    worksheet_supplier = workbook.add_sheet("主要供应商")
    row = 0
    for item in set(supplier_names):
        for name in split_company_name(item):
            row += 1
            worksheet_supplier.write(row, 0, name)

    workbook.save(target_path("data/zjh", datetime.now().strftime("%Y%m%d-%H%M%S") + "公司名称.xls"))


def split_company_name(company_name):
    ret = []
    pattern_split = re.compile(r"[、，/]")
    if not company_name:
        return ret
    names = pattern_split.split(company_name)
    for name in names:
        if re.compile(r".*有限公司.*有限公司\s*$").search(name):
            ret.extend([f"{x}有限公司" for x in name.split("有限公司") if x])
        else:
            ret.append(name)
    return ret


if __name__ == "__main__":
    # output_failed_checker('kechuang_20190417')
    # check_file_name_map()
    extract_info_from_json()
