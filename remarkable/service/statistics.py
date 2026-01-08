import json
import logging
import os
import shutil
from dataclasses import dataclass
from datetime import datetime

import numpy
import openpyxl

from remarkable.models.new_file import NewFile
from remarkable.optools.stat_scriber_answer import StatScriberAnswer
from remarkable.pw_models.model import NewMold, NewTimeRecord
from remarkable.pw_models.question import NewQuestion


@dataclass
class ParsingTime:
    upload_stamp: datetime
    insight_parse_stamp: datetime
    pdf_parse_stamp: datetime
    prompt_stamp: datetime
    preset_stamp: datetime
    whole_process_time: int


async def parsing_time_for_file(fid, time_threshold=None):
    time_record = await NewTimeRecord.find_by_fid(fid)
    if not time_record:
        return None
    if not time_record.upload_stamp or not time_record.preset_stamp:
        return None
    upload_stamp = datetime.fromtimestamp(time_record.upload_stamp)
    insight_parse_stamp = datetime.fromtimestamp(time_record.insight_parse_stamp)
    pdf_parse_stamp = datetime.fromtimestamp(time_record.pdf_parse_stamp)
    prompt_stamp = datetime.fromtimestamp(time_record.prompt_stamp) if time_record.prompt_stamp else None
    preset_stamp = datetime.fromtimestamp(time_record.preset_stamp)
    whole_process_time = (preset_stamp - upload_stamp).total_seconds()
    if time_threshold and whole_process_time > time_threshold:
        # 超过指定时间的数据 认为是重跑后的数据 跳过
        return None

    result = ParsingTime(
        upload_stamp, insight_parse_stamp, pdf_parse_stamp, prompt_stamp, preset_stamp, whole_process_time
    )
    return result


def get_avg_parsing_time(stamp):
    avg_stamp = int(numpy.mean(stamp))
    if avg_stamp >= 60:
        return f"{avg_stamp // 60}分{avg_stamp % 60}秒"
    return f"{avg_stamp}秒"


async def get_stat_data_for_octopus():
    res = []
    molds = await NewMold.list_by_range()
    mold_map = {mold.id: mold.name for mold in molds}
    files = await NewFile.list_by_range()
    for file in files:
        questions = await NewQuestion.find_by_fid(file.id)
        if not questions:
            continue
        mold_name = mold_map.get(questions[0].mold)
        if not mold_name:
            continue
        upload_date = datetime.fromtimestamp(file.created_utc)
        parsing_complete_date = datetime.fromtimestamp(file.updated_utc)
        whole_process_time = (parsing_complete_date - upload_date).total_seconds()
        res.append((file.id, file.name, mold_name, upload_date, whole_process_time))
    return res


async def stat_octopus_parsing_time():
    items = await get_stat_data_for_octopus()
    workbook = openpyxl.Workbook()
    worksheet = workbook.active
    worksheet.title = "解析时间"
    first_row = ["明细表"]
    second_row = [
        "ID",
        "文件名",
        "文件类型",
        "上传时间",
        "解析时间(单位:秒)",
    ]
    worksheet.append(first_row)
    worksheet.append(second_row)
    for row in items:
        worksheet.append(row)
    excel_path = "stat_octopus.xlsx"
    workbook.save(excel_path)
    logging.info(f"run completed, file_path: {excel_path}")


async def save_stat_result(
    preset_path,
    headnum,
    mold,
    save,
    vid,
    tree_s,
    acid,
    test_accuracy=False,
    export_excel=False,
    files_ids=None,
    diff_model=None,
):
    answers = {}
    if preset_path and os.path.exists(preset_path):
        for root, _, names in os.walk(preset_path):
            for name in names:
                fid, ext = os.path.splitext(name)
                if fid.isdigit() and ext == ".json":
                    with open(os.path.join(root, name)) as file_obj:
                        answer = json.load(file_obj)
                        answers.setdefault(int(fid), answer)
        shutil.rmtree(preset_path)
    await StatScriberAnswer(
        headnum=headnum,
        mold=mold,
        save=save,
        vid=vid,
        answers=answers,
        tree_s=tree_s,
        acid=acid,
        test_accuracy_online=test_accuracy,
        export_excel=export_excel,
        files_ids=files_ids,
        diff_model=diff_model,
    ).stat_preset_answer()
