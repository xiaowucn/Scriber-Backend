import argparse
import json
from collections import defaultdict

from remarkable.common.pattern import PatternCollection
from remarkable.common.util import loop_wrapper
from remarkable.pw_models.model import NewSpecialAnswer
from remarkable.pw_models.question import NewQuestion

location_map = {
    "综合毛利率（%）": "合并利润表主要数据（万元）",
    "归属于母公司所有者权益": "合并资产负债表主要数据（万元）",
    "非流动负债": "合并资产负债表主要数据（万元）",
    "加权平均净资产收益率（扣除非经常性损益前）（%）": "最近三年一期主要财务指标表",
    "加权平均净资产收益率（扣除非经常性损益后）（%）": "最近三年一期主要财务指标表",
}

skip_reg = PatternCollection(r"报告期|单位|币种")


def get_answer_from_special_answer(key, fill_in_answer):
    res = []
    if not fill_in_answer:
        return res
    answer = fill_in_answer[0].data["json_answer"]
    financial_data = answer["财务基础数据"][0]
    location = location_map[key]
    data = financial_data[location]
    for item in data:
        text = item.get(key, {}).get("text")
        if text:
            res.append(text)

    return res


def get_answer_from_label_answer(key, label_answer, priority):
    res = []
    for item in label_answer["userAnswer"]["items"]:
        label = item["key"]
        if key not in label:
            continue
        if skip_reg.nexts(label):
            continue
        label_keys = json.loads(item["key"])
        second_word = label_keys[1].split(":")[0]
        if second_word in priority:
            text = item["data"][0]["boxes"][0]["text"]
            res.append(text)

    return res


def compare(label_answer, fill_in_answer):
    print(label_answer)
    print(fill_in_answer)
    label_counts = len(label_answer)
    fill_in_counts = len(fill_in_answer)

    if not label_answer:
        return 0, 0
    if not fill_in_answer:
        return 0, label_counts
    if label_answer and fill_in_counts and label_counts > fill_in_counts:  # 填报数据从多个字段中来
        return fill_in_counts, fill_in_counts
    return fill_in_counts, label_counts


def calculate(res):
    for key, stats in res.items():
        predict, sample = 0, 0
        for stat in stats:
            predict += stat[0]
            sample += stat[1]
        recall = predict / sample
        print(f"{key:20}  recall: {recall}   sample: {sample}    predict: {predict}")


@loop_wrapper
async def main():
    orders = {
        "综合毛利率（%）": ["经营成果表", "盈利能力表", "毛利表", "风险因素", "综合毛利率（其他）"],
        "归属于母公司所有者权益": ["合并资产负债表", "八-主要财务指标表", "二-主要财务指标表"],
        "非流动负债": ["合并资产负债表"],
        "加权平均净资产收益率（扣除非经常性损益前）（%）": ["八-净资产收益率表"],
        "加权平均净资产收益率（扣除非经常性损益后）（%）": ["八-净资产收益率表"],
    }
    questions = await NewQuestion.list_by_range(start=args.start, end=args.end, mold=2)
    res = defaultdict(list)
    question_count = 0
    for question in questions:
        label_answer = await question.get_user_merged_answer()
        if not label_answer:
            continue
        question_count += 1
        fill_in_answer = await NewSpecialAnswer.get_answers(question.id, answer_type=NewSpecialAnswer.ANSWER_TYPE_JSON)
        for key, priority in orders.items():
            fill_in_answer_for_key = get_answer_from_special_answer(key, fill_in_answer)
            label_answer_for_key = get_answer_from_label_answer(key, label_answer, priority)
            compare_answer = compare(label_answer_for_key, fill_in_answer_for_key)
            res[key].append(compare_answer)

    calculate(res)
    print(f"question_count: {question_count}")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="stat szse fill_in answer.")
    parser.add_argument("-s", "--start", type=int, nargs="?", default=0, help="stat from file id")
    parser.add_argument("-e", "--end", type=int, nargs="?", default=0, help="stat to file id")
    args = parser.parse_args()
    main()
