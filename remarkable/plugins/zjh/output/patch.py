import json
import logging
import os
from datetime import datetime

from remarkable.config import project_root
from remarkable.plugins.zjh.util import format_bracket, format_string

file_map = None


def init_file_map(base_dir):
    global file_map
    if file_map is None:
        file_map = {os.path.join(base_dir, "元素抽取"): []}
        try:
            full_root_path = os.path.join(base_dir, "元素抽取")
            for _file in os.listdir(full_root_path):
                if _file.endswith("json"):
                    file_map[full_root_path].append(_file.split(".", 1)[0])
        except Exception as e:
            logging.error(e)
    return file_map


def patch_json_data(file_name, table_name, field, patch_data, base_dir):
    if not patch_data:
        logging.error("Patch is None, skip, %s - %s", file_name, patch_data)
        return
    init_file_map(base_dir)
    path = None
    for key, value in file_map.items():
        if file_name in value:
            path = "{}/{}.json".format(key, file_name)
            break
    if not path:
        logging.error("No path found, %s", file_name)
        return
    mysql_schema_map = json.load(open(os.path.join(project_root, "data/zjh/mysql-schema-map.json"), encoding="utf-8"))
    field_cn_name = mysql_schema_map.get(table_name, {}).get(field)
    if not field_cn_name:
        logging.error("No such key: %s, %s", table_name, field)
        return
    with open(path, encoding="utf-8") as rfile:
        json_string = rfile.read()
        if field_cn_name not in json_string:
            logging.error("No such cn name in json: %s", field_cn_name)
            return
        replace_from = '"{}": "{}"'.format(field_cn_name, patch_data)
        replace_to = '"{}": null'.format(field_cn_name)
        path_json_string = json_string.replace(replace_from, replace_to)
        logging.info("Replace %s to %s in %s", patch_data, "null", file_name)
    with open(path, "w", encoding="utf-8") as wfile:
        wfile.write(path_json_string)


def fix_json_name(base_dir):
    base_dir = base_dir[: base_dir.rfind("/")]
    for tail in ["元素抽取", "合规性检查"]:
        path = os.path.join(base_dir, tail)
        if not os.path.exists(path):
            logging.warning("%s not exists", path)
            continue
        for file_name in os.listdir(path):
            new_name = format_string(format_bracket(file_name))
            old_dir = os.path.join(path, file_name)
            new_dir = os.path.join(path, new_name)

            os.rename(old_dir, new_dir)


def statistics_output_json_data(base_dir):
    init_file_map(base_dir)

    total_data_count = 0
    total_none_count = 0
    detail_data = {}
    detail_data_for_client = {}

    rule_total_data_count = 0
    rule_total_none_count = 0
    rule_detail_data = {}
    rule_detail_data_for_client = {}

    for key, value in file_map.items():
        for file_name in value:
            path = "{}/{}.json".format(key, file_name)
            with open(path, encoding="utf-8") as rfile:
                data = json.load(rfile)
                stat_result = {"data_count": 0, "none_count": 0}
                stat_dict_data(data, stat_result)

                total_data_count += stat_result["data_count"]
                total_none_count += stat_result["none_count"]
                detail_data[file_name] = stat_result
                detail_data_for_client[file_name] = {"data_count": stat_result["data_count"]}

            rule_path = path.replace("元素抽取", "合规性检查")
            with open(rule_path, encoding="utf-8") as rfile:
                data = json.load(rfile)
                rule_stat_result = {"data_count": 0, "none_count": 0}
                stat_dict_data(data, rule_stat_result)

                rule_total_data_count += rule_stat_result["data_count"]
                rule_total_none_count += rule_stat_result["none_count"]
                rule_detail_data[file_name] = rule_stat_result
                rule_detail_data_for_client[file_name] = {"data_count": rule_stat_result["data_count"]}

    for key, value in detail_data.items():
        value["rule_data_count"] = rule_detail_data[key]["data_count"]
        value["rule_none_count"] = rule_detail_data[key]["none_count"]

    for key, value in detail_data_for_client.items():
        value["rule_data_count"] = rule_detail_data_for_client[key]["data_count"]

    stat_output_path = os.path.join(project_root, "remarkable/optools/")
    stat_output = {
        "total_data_count": total_data_count,
        "total_none_count": total_none_count,
        "rule_total_data_count": rule_total_data_count,
        "rule_total_none_count": rule_total_none_count,
        "detail": detail_data,
    }

    stat_output_for_client = {
        "total_data_count": total_data_count,
        "rule_total_data_count": rule_total_data_count,
        "detail": detail_data_for_client,
    }

    json.dump(
        stat_output_for_client,
        open(
            os.path.join(stat_output_path, datetime.now().strftime("%Y%m%d-%H%M%S") + "数据项统计.json"),
            "w",
            encoding="utf-8",
        ),
        ensure_ascii=False,
    )

    json.dump(
        stat_output,
        open(
            os.path.join(stat_output_path, datetime.now().strftime("%Y%m%d-%H%M%S") + "数据项统计(内部).json"),
            "w",
            encoding="utf-8",
        ),
        ensure_ascii=False,
    )


def stat_dict_data(data, stat_result):
    for value in data.values():
        if isinstance(value, dict):
            stat_dict_data(value, stat_result)
        elif isinstance(value, list):
            stat_list_data(value, stat_result)
        else:
            if value is None:
                stat_result["none_count"] += 1
            else:
                stat_result["data_count"] += 1


def stat_list_data(data, stat_result):
    for item in data:
        if isinstance(item, dict):
            stat_dict_data(item, stat_result)
        elif isinstance(item, list):
            stat_list_data(item, stat_result)
        else:
            if item is None:
                stat_result["none_count"] += 1
            else:
                stat_result["data_count"] += 1


def main():
    base_dir = "/Users/liuchao/Downloads/outputs/"
    statistics_output_json_data(base_dir)
    data = {"1": None, "2": [{"3": None}, {"5": 6}], "7": {"8": 9, "10": None}}
    stat_result = {"data_count": 0, "none_count": 0}
    stat_dict_data(data, stat_result)
    assert stat_result["data_count"] == 2
    assert stat_result["none_count"] == 3


if __name__ == "__main__":
    main()
