import json
import logging
import os
import shutil
import zipfile
from collections import defaultdict
from copy import deepcopy
from datetime import datetime

from speedy.peewee_plus.orm import and_
from typing_extensions import Protocol

from remarkable.answer.common import gen_key_md5
from remarkable.answer.node import AnswerItem
from remarkable.answer.reader import AnswerReader
from remarkable.common.constants import HistoryAction
from remarkable.common.enums import ExportStatus
from remarkable.common.multiprocess import run_by_batch
from remarkable.common.util import generate_timestamp
from remarkable.config import project_root
from remarkable.db import peewee_transaction_wrapper, pw_db
from remarkable.models.new_file import NewFile
from remarkable.models.new_user import ADMIN, NewAdminUser
from remarkable.optools.export_answers_for_szse import export_answer_data_to_csv
from remarkable.plugins.fileapi.common import LabelEncoder
from remarkable.predictor.predict import answer_convert
from remarkable.pw_models.answer_data import AnswerDataExport, NewAnswerData
from remarkable.pw_models.model import NewAnswer, NewFileProject, NewMold, NewSpecialAnswer
from remarkable.pw_models.question import NewQuestion
from remarkable.pw_orm import func
from remarkable.routers.schemas.answer import AnswerDataAdd, AnswerDataDelete, AnswerDataUpdate
from remarkable.schema.answer import UserAnswer
from remarkable.service.new_mold import NewMoldService
from remarkable.utils.answer_util import AnswerUtil
from remarkable.worker.tasks.common_tasks import save_event_log


@peewee_transaction_wrapper
async def set_convert_answer(qid):
    """
    合并答案转换为导出答案
    """
    question = await NewQuestion.find_by_id(qid)
    if not question or not question.answer or not question.answer["userAnswer"]["items"]:
        return
    converted_answer = await answer_convert(question)
    if converted_answer is None:
        return
    existed_answers = await NewSpecialAnswer.get_answers(qid, NewSpecialAnswer.ANSWER_TYPE_EXPORT, top=1)
    if existed_answers:
        mold = await NewMold.find_by_id(question.mold)
        export_answer = existed_answers[0]
        merged_answer = AnswerUtil.merge_answers(
            [
                UserAnswer._make([ADMIN.id, ADMIN.name, export_answer.data]),
                UserAnswer._make([ADMIN.id, ADMIN.name, json.loads(json.dumps(converted_answer, cls=LabelEncoder))]),
            ],
            schema_data=mold.data,
        )
        update_info = {"data": json.dumps(merged_answer, cls=LabelEncoder), "updated_utc": generate_timestamp()}
        await export_answer.update_(**update_info)
    else:
        await NewSpecialAnswer.create(
            **{
                "qid": qid,
                "answer_type": NewSpecialAnswer.ANSWER_TYPE_EXPORT,
                "data": json.dumps(converted_answer, cls=LabelEncoder),
            },
        )


async def delete_custom_field(user: NewAdminUser, qid: int, md5_list: list[str]):
    for answer in await NewAnswer.get_answers_by_qid(qid):
        if not NewQuestion.answer_items(answer.data, "custom_field"):
            continue
        answer.data["custom_field"]["items"] = [
            i for i in answer.data["custom_field"]["items"] if gen_key_md5(i) not in md5_list
        ]
        await answer.update_(data=answer.data)
    question = await NewQuestion.find_by_id(qid)
    items = []
    deleted_item = None
    for item in question.answer["custom_field"]["items"]:
        if gen_key_md5(item) in md5_list:
            deleted_item = item
        else:
            items.append(item)
    question.answer["custom_field"]["items"] = items
    save_event_log.delay(user.id, user.name, HistoryAction.DELETE_CUSTOM_FIELD, qid, deleted_item)
    await question.update_(answer=question.answer)


class SimpleQuestion(Protocol):
    id: int
    fid: int
    mold: int


async def get_master_question_answer(question: SimpleQuestion):
    """
    将answer_data表中的数据组装成普通answer格式
    {
        "schema": {},
        "userAnswer: {}
    }
    :return:
    """
    molds = await NewMoldService.get_related_molds(question.fid, question.mold)
    mold, _ = NewMoldService.master_mold_with_merged_schemas(molds)
    cond = NewAnswerData.qid == question.id
    data = await pw_db.execute(NewAnswerData.select().where(cond).order_by(NewAnswerData.id))
    user_map = await NewAdminUser.get_user_name_map()

    p_molds_name = NewMoldService.get_p_molds_name(molds)

    mold_dict = deepcopy(mold.to_dict())
    schema = mold_dict["data"]
    schema["version"] = mold_dict["checksum"]

    answer = {
        "userAnswer": {
            "items": [x.to_dict(master_mold=molds[0], p_molds_name=p_molds_name, user_map=user_map) for x in data]
        },
        "schema": schema,
    }

    return answer, mold


async def get_master_preset_answer(question: NewQuestion):
    molds = await NewMoldService.get_related_molds(question.fid, question.mold)
    mold, fixed_molds = NewMoldService.master_mold_with_merged_schemas(molds)
    questions = await NewQuestion.find_by_fid_mids(question.fid, [x.id for x in molds])
    answer_datas = []
    if not all(x.preset_answer for x in questions):
        return answer_datas, mold

    mold_reserved_fields = {}
    for fixed_mold in fixed_molds:
        mold_reserved_fields[fixed_mold.name] = fixed_mold.data["schemas"][0]["orders"]

    for question in questions:
        answer_reader = AnswerReader(question.preset_answer)
        for item in answer_reader.items:
            answer_item = AnswerItem(**item)
            if answer_item.first_level_field not in mold_reserved_fields.get(answer_reader.mold_name, []):
                continue

            if not answer_item.value:
                value = []
            elif isinstance(answer_item.value, str):
                value = [answer_item.value]
            elif isinstance(answer_item.value, (list, tuple)):
                value = answer_item.value
            else:
                raise ValueError(f"Invalid {answer_item.value}")

            answer_data = {
                "qid": question.id,
                "uid": answer_item.marker["id"] if answer_item.marker else None,
                "key": answer_item.key,
                "data": answer_item.data,
                "schema": answer_item.schema,
                "value": value,
                "text": answer_item.text,
                "score": answer_item.score,
                "record": None,
                "revise_suggestion": None,
            }
            answer_datas.append(answer_data)

    mold_dict = deepcopy(mold.to_dict())
    schema = mold_dict["data"]
    schema["version"] = mold_dict["checksum"]

    answer = {
        "userAnswer": {"items": answer_datas},
        "schema": schema,
    }

    return answer, mold


async def get_preset_answer_by_mid_qid(mold: NewMold, question: NewQuestion):
    questions = await NewQuestion.find_by_fid_mids(question.fid, [mold.id])
    answer_datas = []
    if not all(x.preset_answer for x in questions):
        return answer_datas, mold

    mold_reserved_fields = {mold.name: mold.data["schemas"][0]["orders"]}

    for question in questions:
        answer_reader = AnswerReader(question.preset_answer)
        for item in answer_reader.items:
            answer_item = AnswerItem(**item)
            if answer_item.first_level_field not in mold_reserved_fields.get(answer_reader.mold_name, []):
                continue

            if not answer_item.value:
                value = []
            elif isinstance(answer_item.value, str):
                value = [answer_item.value]
            elif isinstance(answer_item.value, (list, tuple)):
                value = answer_item.value
            else:
                raise ValueError(f"Invalid {answer_item.value}")

            answer_data = {
                "qid": question.id,
                "uid": answer_item.marker["id"] if answer_item.marker else None,
                "key": answer_item.key,
                "data": answer_item.data,
                "schema": answer_item.schema,
                "value": value,
                "text": answer_item.text,
                "score": answer_item.score,
                "record": None,
                "revise_suggestion": None,
            }
            answer_datas.append(answer_data)

    mold_dict = deepcopy(mold.to_dict())
    schema = mold_dict["data"]
    schema["version"] = mold_dict["checksum"]

    answer = {
        "userAnswer": {"items": answer_datas},
        "schema": schema,
    }

    return answer


async def get_question_answer_by_mid_qid(mold: NewMold, question: NewQuestion):
    if not mold or not question or mold.id != question.mold:
        return {
            "userAnswer": {"items": []},
            "schema": {},
        }
    data = await pw_db.execute(
        NewAnswerData.select().where(NewAnswerData.qid == question.id).order_by(NewAnswerData.id)
    )
    user_map = await NewAdminUser.get_user_name_map()
    mold_dict = deepcopy(mold.to_dict())
    schema = mold_dict["data"]
    schema["version"] = mold_dict["checksum"]

    return {
        "userAnswer": {"items": [x.to_dict(user_map=user_map) for x in data]},
        "schema": schema,
    }


async def edit_answer_data(
    file,
    add: list[AnswerDataAdd],
    update: list[AnswerDataUpdate],
    delete: list[AnswerDataDelete],
    uid: int,
):
    data = {}
    if delete:
        cond = NewAnswerData.id.in_([x.id for x in delete])
        await pw_db.execute(NewAnswerData.delete().where(cond))
    if add:
        molds = [item.mold_id for item in add]
        qid_mold_dict = dict(
            await pw_db.execute(
                NewQuestion.select(NewQuestion.mold, NewQuestion.id)
                .where(NewQuestion.mold.in_(molds), NewQuestion.fid == file.id)
                .tuples()
            )
        )
        fix_add = []
        for item in add:
            if not (qid := qid_mold_dict.get(item.mold_id)):
                continue
            fix_ = item.model_dump(by_alias=True)
            fix_.pop("mold_id")
            fix_["qid"] = qid
            fix_["uid"] = uid
            fix_["record"] = [NewAnswerData.gen_empty_record()]
            fix_add.append(fix_)
        if fix_add:
            added = await NewAnswerData.insert_and_returning(fix_add, returning=[NewAnswerData.id, NewAnswerData.key])
            data["add"] = added
    if update:
        await NewAnswerData.batch_update([item.model_dump(by_alias=True) for item in update], uid)

    return data


async def build_answer_data(file: NewFile):
    """
    将answer_data表中的数据组装成普通answer格式
    [
        {
            "answer_data": {},
            "mold: {}
        }
    ]
    :return:
    """
    user_map = await NewAdminUser.get_user_name_map()
    query = (
        NewMold.select(
            NewMold,
            NewQuestion.id.alias("qid"),
        )
        .join(NewQuestion, on=and_(NewMold.id == NewQuestion.mold, NewQuestion.fid == file.id))
        .group_by(NewMold.id, NewQuestion.id)
        .objects()
    )
    mold_list = list(await pw_db.execute(query))
    qid_list = [item.qid for item in mold_list]
    answer_data_list = list(await pw_db.execute(NewAnswerData.select().where(NewAnswerData.qid.in_(qid_list))))
    answer_data_dict = defaultdict(list)
    for item in answer_data_list:
        answer_data_dict[item.qid].append(item.to_dict(user_map=user_map))
    res = []
    for item in mold_list:
        res.append(
            {
                "answer_data": answer_data_dict.get(item.qid, []),
                "mold": item.to_dict(),
            }
        )
    return res


def get_unique_data_items(data):
    seen_texts = set()
    unique_items = []
    for item in data:
        text_value = item["boxes"][0]["text"] if item.get("text") is None else item["text"]
        if text_value not in seen_texts:
            seen_texts.add(text_value)
            unique_items.append(item)
    return unique_items


async def fetch_all_answer_data(p_id: int, files_ids=None):
    cond = (NewFile.pid == p_id) & (NewFile.id.in_(files_ids))

    fields = [
        NewAnswerData.qid.alias("qid"),
        NewMold.id.alias("mid"),
        NewMold.data.alias("mold_data"),
        NewMold.name.alias("mold_name"),
        func.ARRAY_AGG(NewAnswerData.jsonb_build_object("key", "data", "value")).alias("data_agg"),
        NewFile.id.alias("fid"),
        NewFile.name,
    ]

    query = (
        NewAnswerData.select(*fields)
        .join(NewQuestion, on=(NewAnswerData.qid == NewQuestion.id))
        .join(NewMold, on=NewQuestion.mold == NewMold.id)
        .join(NewFile, on=(NewFile.id == NewQuestion.fid))
        .where(cond)
        .group_by(NewAnswerData.qid, NewFile.id, NewMold.id)
    )

    rows = await pw_db.execute(query.dicts())

    for row in rows:
        mold_ins = NewMold(id=row["mid"], data=row["mold_data"], name=row["mold_name"])
        molds = await NewMold.get_related_molds(mold_ins.id)
        mold, _ = NewMoldService.master_mold_with_merged_schemas(molds)
        p_molds_name = NewMoldService.get_p_molds_name(molds)
        for item in row["data_agg"]:
            item["data"] = get_unique_data_items(item["data"])
            item["key"] = NewMoldService.update_merged_answer_key_path(p_molds_name, mold_ins, item["key"])
        row["data"] = {"schema": mold_ins.data, "userAnswer": {"items": row.pop("data_agg")}}
        row["mold_name"] = mold_ins.name
        row["mold_id"] = mold_ins.id
    return rows


async def export_answer_data_scheduler(p_id, file_ids, task_id):
    project = await NewFileProject.find_by_id(p_id)
    export_data = await AnswerDataExport.find_by_id(task_id)
    if not project:
        logging.error("export answer data error, p_id：%s", p_id)
        await export_data.update_(status=ExportStatus.FAILED)
        return
    # 创建导出目录
    dump_dir = os.path.join(project_root, "data", "export_answer_data", f"{p_id}_{task_id}")
    if not os.path.exists(dump_dir):
        os.makedirs(dump_dir)
    rows = await fetch_all_answer_data(p_id=p_id, files_ids=file_ids)
    tasks = [
        (row["data"], row["fid"], row["name"], row["mold_id"], row["mold_name"], f"{p_id}_{task_id}")
        for row in rows
        if row["data"]
    ]
    if not tasks:
        logging.error("has no answers, p_id：%s", p_id)
        await export_data.update_(status=ExportStatus.FAILED)
        return

    # debug=True，临时不使用多进程
    for dumped_files in run_by_batch(export_answer_data_to_csv, tasks, batch_size=10, workers=8):
        await export_data.update_(task_done=export_data.task_done + len(dumped_files))
    # 压缩并删除临时文件
    zip_path = os.path.join(
        project_root, "data", "export_answer_data", f"{project.name}_{datetime.now().strftime('%Y%m%d%H%M%S')}.zip"
    )
    with zipfile.ZipFile(zip_path, "w") as zfp:
        for _file in os.listdir(dump_dir):
            _file = os.path.join(dump_dir, _file)
            zfp.write(_file, os.path.split(_file)[-1], compress_type=zipfile.ZIP_DEFLATED)
    if os.path.exists(dump_dir):
        shutil.rmtree(dump_dir)
    # 记录下载地址
    await export_data.update_(zip_path=zip_path, status=ExportStatus.FINISH)
