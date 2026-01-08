import collections
import logging
from pathlib import Path

import xlwt

from remarkable.answer.common import parse_path
from remarkable.common.util import loop_wrapper
from remarkable.config import project_root
from remarkable.models.new_file import NewFile
from remarkable.pw_models.model import NewAnswer

EXPORT_PATH = Path(project_root) / "data" / "szse_label_answer.xls"

EXPORT_FIELDS = ["五-员工持股与股权激励计划"]

employee_shareholding = "员工持股"


equity_incentive = "股权激励"


async def load_answer(file):
    answer = await NewAnswer.find_standard(file.qid)
    if not answer:
        return None
    answer = answer.data
    field_answers = []
    for item in answer["userAnswer"]["items"]:
        key_path = parse_path(item["key"])
        first_field = key_path[1][0]
        if first_field not in EXPORT_FIELDS:
            continue
        second_field = key_path[2][0]
        text = ""
        for datum in item["data"]:
            for box_info in datum.get("boxes"):
                text += box_info["text"]
        if not text:
            continue
        field_answers.append([file.id, second_field, "", text])
    return field_answers


def classification(answers):
    ret = collections.defaultdict(list)
    for answer in answers:
        answer_text = answer[3]
        if employee_shareholding in answer_text and equity_incentive not in answer_text:
            ret["只包含员工持股"].append(answer)
        if employee_shareholding not in answer_text and equity_incentive in answer_text:
            ret["只包含股权激励"].append(answer)
        if employee_shareholding in answer_text and equity_incentive in answer_text:
            ret["同时包含股权激励和员工持股"].append(answer)
        if employee_shareholding not in answer_text and equity_incentive not in answer_text:
            ret["都不包含"].append(answer)

    return ret


def save_to_excel(answers):
    workbook = xlwt.Workbook(encoding="ascii")
    for key, items in answers.items():
        worksheet = workbook.add_sheet(key)
        worksheet.col(1).width = 256 * 20
        worksheet.col(3).width = 256 * 200

        for index, value in enumerate(["文件ID", "字段", "是/否", "标注答案"]):
            worksheet.write(0, index, value)

        for row_index, answer in enumerate(items, start=1):
            for index, value in enumerate(answer):
                worksheet.write(row_index, index, value)
    workbook.save(EXPORT_PATH)


@loop_wrapper
async def main(start=None, end=None):
    # find file
    files = await NewFile.list_by_range(start=start, end=end)
    # load answer
    answers = []
    for file in files:
        answer = await load_answer(file)
        if not answer:
            continue
        logging.info(f"loading file {file.id}")
        answers.extend(answer)
    # classification
    answers = classification(answers)
    # export to excel
    save_to_excel(answers)


if __name__ == "__main__":
    main()
