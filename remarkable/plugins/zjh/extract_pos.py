import json
import sys
from collections import defaultdict

from remarkable.common.rectangle import Rectangle
from remarkable.plugins.zjh.util import get_answer_label


def extract_ipo_position(answers, merged=True):
    positions = defaultdict(list)
    detail_list = ["董事基本情况", "监事基本情况", "高管基本情况", "核心技术人员基本情况"]  # 展示每个字段的位置
    union_list = ["募集资金与运用"]  # 同一个答案下同一页的框合并
    for answer in answers["items"]:
        answer_rects = defaultdict(list)
        if get_answer_label(answer) in detail_list + union_list:
            continue
        for item in answer["data"]:
            for field in item["fields"]:
                for component in field["components"]:
                    frame_data = component["frameData"]
                    frame_rect = gen_frame_rect(frame_data)
                    answer_rects[frame_data["page"]].append(frame_rect)

        for page, rects in answer_rects.items():
            for rect in rects:
                positions[get_answer_label(answer)].append({"page": page, "box": [rect.x, rect.y, rect.xx, rect.yy]})

    for answer in answers["items"]:
        if get_answer_label(answer) not in detail_list:
            continue
        rects_list = []
        for item in answer["data"]:
            person_info = defaultdict(list)
            for field in item["fields"]:
                for component in field["components"]:
                    frame_data = component["frameData"]
                    rect = gen_frame_rect(frame_data)
                    person_info[field["name"]].append(
                        {"page": frame_data["page"], "box": [rect.x, rect.y, rect.xx, rect.yy]}
                    )
                if field["name"] == "姓名":
                    person_info["name"] = field["label"]

            rects_list.append(person_info)

        positions[get_answer_label(answer)] = rects_list

    for answer in answers["items"]:
        answer_rects = defaultdict(list)
        if get_answer_label(answer) not in union_list:
            continue
        for item in answer["data"]:
            for field in item["fields"]:
                for component in field["components"]:
                    frame_data = component["frameData"]
                    frame_rect = gen_frame_rect(frame_data)
                    answer_rects[frame_data["page"]].append(frame_rect)

        for page, rects in answer_rects.items():
            base_rect = rects[0]
            for rect in rects[1:]:
                base_rect = base_rect.union(rect)
            positions[get_answer_label(answer)].append(
                {"page": page, "box": [base_rect.x, base_rect.y, base_rect.xx, base_rect.yy]}
            )

    if not merged:
        return positions
    profitability_dict = {}
    main_financial_dict = {}
    key_to_pop = []
    for key in positions:
        if key.startswith("盈利能力"):
            profitability_dict[key] = positions[key]
            key_to_pop.append(key)
        if key.startswith("合并") or key == "主要财务指标":
            main_financial_dict[key] = positions[key]
            key_to_pop.append(key)

    for key in key_to_pop:
        positions.pop(key)

    profitability_list = []
    main_financial_list = []

    for value in profitability_dict.values():
        profitability_list.extend(value)
    for value in main_financial_dict.values():
        main_financial_list.extend(value)

    profitability_list = sorted(profitability_list, key=lambda d: d["page"])
    main_financial_list = sorted(main_financial_list, key=lambda d: d["page"])

    positions["财务基本情况及财务指标"] = main_financial_list
    positions["盈利能力"] = profitability_list

    update_manager_info(positions)
    update_issuer_info(positions)

    return positions


def update_issuer_info(positions):
    issuer_data = {}
    issuer_keys = []
    for key in positions:
        if key.startswith("发行人-"):
            issuer_keys.append(key)
            issuer_data[key.replace("发行人-", "")] = positions[key]

    for key in issuer_keys:
        del positions[key]

    positions["发行人基本情况"] = issuer_data


def update_manager_info(positions):
    manager_list = ["董事基本情况", "监事基本情况", "高管基本情况", "核心技术人员基本情况"]
    filed_list = ["国籍", "境外居留权", "性别", "出生年月", "学历", "职称", "现任职务", "起始日期", "终止日期"]
    the_complete_info = defaultdict(dict)
    for key in manager_list:
        for item in positions[key]:
            name = item["name"]
            data = the_complete_info[name]
            data.update(item)

    for key in manager_list:
        for item in positions[key]:
            for field in filed_list:
                if field not in item:
                    alternative = the_complete_info[item["name"]].get(field)
                    if alternative:
                        item[field] = alternative


def gen_frame_rect(frame_data):
    minx = float(frame_data["left"])
    miny = float(frame_data["top"])
    maxx = minx + float(frame_data["width"])
    maxy = miny + float(frame_data["height"])
    frame_rect = Rectangle(minx, miny, maxx, maxy)
    return frame_rect


def main():
    answer_data_path = sys.argv[1]
    answers = json.load(open(answer_data_path, encoding="utf-8"))
    extract_ipo_position(answers["userAnswer"])


if __name__ == "__main__":
    main()
