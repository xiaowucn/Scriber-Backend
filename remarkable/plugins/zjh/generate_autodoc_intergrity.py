import csv
import json
import os
import sys
from collections import defaultdict

from remarkable.common.rectangle import Rectangle
from remarkable.plugins.zjh.extract_pos import extract_ipo_position

# file path
file_info_csv_path = "/home/skyrover/server_files/zjs_answers/draft_c5_600_public_file.csv"
all_file_ids_path = "/home/skyrover/server_files/zjs_answers/all_file_ids.txt"
answer_path = "/home/skyrover/server_files/zjs_answers/answers/{file_id}.txt"
ipo_check_result_path = "/home/skyrover/server_files/zjs_answers/ipo_results/output-0413/合规性检查/{filename}.json"

# constant
csv_file_id = 0
csv_file_name = 3
csv_file_checksum = 5

check_item_correct = 0
check_item_wrong = 1
check_item_miss = 2


schema_zjh_order = [
    ["释义"],
    [
        "发行人基本情况",
        [
            "发行人-公司名称",
            "发行人-法定代表人姓名",
            "发行人-统一社会信用代码",
            "发行人-组织机构代码",
            "发行人-成立日期",
            "发行人-注册资本",
            "发行人-注册地址",
            "发行人-办公地址",
            "发行人-电话",
            "发行人-传真号码",
            "发行人-电子邮箱",
            "发行人-邮政编码",
        ],
    ],
    [
        "控股股东简要情况",
        [
            "控股股东-法人",
            "控股股东-自然人",
            "控股股东-其他",
        ],
    ],
    [
        "实际控制人简要情况",
        [
            "实际控制人-国有控股主体",
            "实际控制人-自然人",
            "实际控制人-其他",
        ],
    ],
    ["董事基本情况"],
    ["监事基本情况"],
    ["高管基本情况"],
    ["核心技术人员基本情况"],
    [
        "财务基本情况及财务指标",
        [
            "合并资产负债表",
            "合并利润表",
            "合并现金流量表",
            "基本财务指标",
        ],
    ],
    ["重大诉讼事项"],
    ["募集资金与运用"],
    ["专利"],
    ["主要客户"],
    ["主要供应商"],
    ["重大合同"],
    [
        "发行人所处行业",
        [
            "行业分类标准",
            "行业分类代码",
            "行业分类名称",
        ],
    ],
    [
        "盈利能力",
        [
            "营业收入分析",
            "营业成本分析",
        ],
    ],
]


def read_file_info():
    reader = csv.reader(open(file_info_csv_path))
    file_info = {}
    for line in reader:
        file_info[line[csv_file_id]] = {"filename": line[csv_file_name], "checksum": line[csv_file_checksum]}
    return file_info


def read_valid_file_ids():
    file_ids = []
    for line in open(all_file_ids_path).readlines():
        file_ids.append(line.strip())
    return file_ids


def read_answer(file_id):
    answer = json.load(open(answer_path.format(file_id=file_id), encoding="utf-8"))
    return answer


def read_answer_position(answer):
    position_data = extract_ipo_position(answer["userAnswer"], merged=False)
    return position_data


def read_ipo_check_result(filename):
    ipo_check_result = json.load(open(ipo_check_result_path.format(filename=filename), encoding="utf-8"))
    return ipo_check_result


def init_check_item(second_rule):
    return {
        "rule": "完备性审核",
        "second_rule": second_rule,
        "result": None,  # 0 合规 / 1 不合规 / 2 未出现 / 3 待定，需人工审核
        "comment": "",
        "detail": [],  # position list
    }


def find_item_in_check_result(ipo_check_result, item):
    comment = ""
    last_field = item.split("-")[-1]
    for value in ipo_check_result.values():
        if not isinstance(value, dict):
            continue
        exception_field = value["异常字段"].split("-")[-1]
        if last_field == exception_field or value["异常字段"].startswith(item):
            comment = "披露不完整，需人工审核"
    return bool(comment), comment if comment else "披露完整"


def merge_pos(answer_pos_item):
    check_item_pos = defaultdict(list)
    for pos_info in answer_pos_item:
        if "box" in pos_info:
            check_item_pos[pos_info["page"]].append(pos_info["box"])
        else:
            for item_pos_infos in pos_info.values():
                if not isinstance(item_pos_infos, list):
                    continue
                for item_pos_info in item_pos_infos:
                    check_item_pos[item_pos_info["page"]].append(item_pos_info["box"])
    check_item_result = []
    for page, poses in check_item_pos.items():
        base_rect = Rectangle(*poses[0])
        for pos in poses[1:]:
            base_rect = base_rect.union(Rectangle(*pos))
        check_item_result.append({"out_line": [base_rect.x, base_rect.y, base_rect.xx, base_rect.yy], "page": page})
    return check_item_result


def _merge_output_len_1(item, answer_pos, ipo_check_result):
    check_item = init_check_item(item)
    if item in answer_pos.keys():
        check_item_result = merge_pos(answer_pos[item])
        check_item["detail"] = check_item_result
        exception, comment = find_item_in_check_result(ipo_check_result, item)
        check_item["comment"] = comment
        check_item["result"] = check_item_wrong if exception else check_item_correct
    else:
        check_item["result"] = check_item_miss
        check_item["comment"] = "未披露"
    return check_item


def _merge_output_items(items, answer_pos, ipo_check_result):
    check_items = []
    for item in items:
        check_item = init_check_item(item)
        if item in answer_pos:
            check_item_result = merge_pos(answer_pos[item])
            check_item["detail"] = check_item_result
            exception, comment = find_item_in_check_result(ipo_check_result, item[0])
            check_item["comment"] = comment
            check_item["result"] = check_item_wrong if exception else check_item_correct
        else:
            check_item["result"] = check_item_miss
        check_items.append(check_item)
    return check_items


def _merge_output_data(file_id, file_info):
    answer = read_answer(file_id)
    answer_pos = read_answer_position(answer)
    ipo_check_result = read_ipo_check_result(file_info["filename"].split(".")[0])
    merge_res = []
    for item in schema_zjh_order:
        if len(item) == 1:
            check_item = _merge_output_len_1(item[0], answer_pos, ipo_check_result)
            merge_res.append(check_item)
        else:
            check_items = _merge_output_items(item[1], answer_pos, ipo_check_result)
            merge_res.extend(check_items)
    return merge_res


def merge_autodoc_output_data(path):
    valid_file_ids = read_valid_file_ids()
    file_infos = read_file_info()
    output = {}
    for file_id in valid_file_ids:
        file_info = file_infos.get(file_id)
        if not file_info:
            continue
        print("merge file: {} {} {}".format(file_id, file_info["filename"], file_info["checksum"]))
        merge_res = _merge_output_data(file_id, file_info)
        output[file_info["checksum"]] = merge_res
    json.dump(output, open(os.path.join(path, "zjh_ipo_integrity_check.json"), "w"), ensure_ascii=False)


if __name__ == "__main__":
    merge_autodoc_output_data(sys.argv[1])
