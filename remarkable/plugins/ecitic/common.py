import difflib
import json
import logging
import re
from collections import defaultdict
from copy import copy
from datetime import datetime

import httpx
from peewee import fn
from speedy.peewee_plus.orm import and_

from remarkable.answer.common import is_empty_answer
from remarkable.answer.node import AnswerItem
from remarkable.answer.reader import AnswerReader
from remarkable.common.constants import EciticExternalSource, EciticTgTaskType, EciticTgTriggerType, SpecialAnswerType
from remarkable.common.convert_number_util import NumberUtil
from remarkable.common.exceptions import CustomError
from remarkable.common.pattern import PatternCollection
from remarkable.common.schema import Schema
from remarkable.common.util import compact_dumps
from remarkable.config import get_config
from remarkable.db import pw_db
from remarkable.models.ecitic import (
    EciticCompareRecord,
    EciticCompareRecordResultRef,
    EciticCompareResult,
    EciticFile,
    EciticFileInfo,
    EciticParaMap,
    EciticPush,
    EciticPushRecord,
    EciticTemplate,
)
from remarkable.models.new_user import NewAdminUser
from remarkable.plugins.ecitic.tg_task import send_email_to_ecitic_tg
from remarkable.pw_models.model import NewFileProject, NewMold, NewSpecialAnswer
from remarkable.pw_models.question import NewQuestion
from remarkable.service.answer import get_master_question_answer

logger = logging.getLogger(__name__)
p_path = re.compile(r"[(](.*)[)]")
p_path_1 = re.compile(r"[(].*[)]")
p_path_before_colon = re.compile(r"(.*?):")

p_clean = PatternCollection(  # https://gitpd.paodingai.com/cheftin/docs_scriber/-/issues/3660
    [
        r"\s+",
        rf"[{NumberUtil.R_CN_NUMBER}]+[只个]",
        r"^[\d.\u2460-\u2480]+",
        r"[（(][一二三四五六七八九十\d]+[）)]",
        r'[,.．、？?，。！!“"：:”\'‘’ ;；（()）]+',
        r"[\d.]+[%％]",
        r"[A-Za-z]+[-+0-9]+",
        r"[A-Za-z]+[-+]?",
    ]
)


def ecitic_path_list(schema_path, keep_tail=True):
    path_list = []
    if not keep_tail:
        schema_path = schema_path[:-1]
    for path in schema_path:
        path_list.extend(split_path(path))
    return path_list


def split_path(path):
    if p_path_1.search(path):
        prefix = p_path.search(path).groups()[0]
        return [prefix] + p_path_1.sub("", path).split("-")
    return path.split("-")


def get_boxes_text(item):
    if text := item.get("text"):
        return text
    return "".join([box["text"] for box in item["boxes"]])


def calc_similarity(std_text, diff_text):
    std_text = p_clean.sub("", std_text)
    diff_text = p_clean.sub("", diff_text)
    matcher = difflib.SequenceMatcher(a=std_text, b=diff_text)
    return matcher.ratio()


def ecitic_answer_handler(answer):
    return {
        "data": answer.data,
        "text": answer.plain_text,
    }


async def create_push_record(
    fid, task_type, push_type, uid, status, data, external_source, compare_record=None
) -> EciticPushRecord:
    """
    :param fid: file id
    :param task_type: 场景: 参数提取/文档对比
    :param push_type: 推送类型
    :param uid: 用户id
    :param status: 状态: 成功/失败 1/0
    :param data:
    :param external_source: 外部参数来源
    :param compare_record: 对比记录的id
    :return:
    """
    params = {
        "fid": fid,
        "task_type": task_type,
        "push_type": push_type,
        "uid": uid,
        "status": status,
        "data": data,
        "external_source": external_source,
        "visible": True,
        "compare_record": compare_record,
    }
    return await pw_db.create(EciticPushRecord, **params)


def get_template_answer(template, root_node):
    template_answer = {}
    answer_dict = root_node.to_dict(item_handler=ecitic_answer_handler)
    mold_name = root_node.schema["orders"][0]
    for key, value in answer_dict[mold_name][0].items():
        if "-".join(ecitic_path_list([key])) in template.fields:
            template_answer[key] = value
    return template_answer


async def get_push_data(
    question_id=None, compare_record_id=None, user_name=None, only_auto_push=False, only_count=False
):
    std_file = None
    if compare_record_id:
        compare_record = await EciticCompareRecord.find_by_id(compare_record_id)
        question = await NewQuestion.find_by_id(compare_record.qid)
        std_question = await NewQuestion.find_by_id(compare_record.std_qid)
        if not (std_question and question):
            raise CustomError("not found file")
        std_file = await EciticFile.find_by_id(std_question.fid, EciticFileInfo.select())
        if not std_file:
            raise CustomError("not found file")
        compare_result_query = (
            EciticCompareResult.select()
            .join(EciticCompareRecordResultRef)
            .where(EciticCompareRecordResultRef.compare_record_id == compare_record_id)
        )
        compare_result = await pw_db.first(compare_result_query)
        answer = compare_result.answer
    else:
        question = await NewQuestion.find_by_id(question_id)
        if not question:
            raise CustomError("not found file")
        answer, master_mold = await get_master_question_answer(question)

    file = await EciticFile.get_by_id(question.fid, EciticFileInfo.select())
    if not file:
        raise CustomError("not found file")
    if not only_count:
        if not file.file_info.version:
            raise CustomError("版本号缺失")
        if std_file:
            if not std_file.file_info.version:
                raise CustomError("版本号缺失")
            if file.file_info.version != std_file.file_info.version:
                raise CustomError("版本号不同")

    file_user = await NewAdminUser.find_by_id(file.uid)

    is_success, converted_answer = await ecitic_para_map_convert(answer, split_fields_only=False)
    reader = AnswerReader(converted_answer)
    root_node, _mapping = reader.build_answer_tree()

    push_data_list = []
    template_cond = EciticTemplate.id.in_(file.file_info.templates)
    templates = await pw_db.execute(EciticTemplate.select().where(template_cond))
    if not templates:
        logger.info(f"文档{file.id=}的模板不存在")
        return file, push_data_list

    project = await NewFileProject.find_by_id(file.pid)
    project_user = await NewAdminUser.find_by_id(project.uid)

    basic_info = {
        "compare_record_id": compare_record_id,
        "file_id": file.id,
        "file_name": file.name,
        "std_file_id": std_file.id if std_file else None,
        "std_file_name": std_file.name if std_file else None,
        "schema_id": question.mold,
        "version": file.file_info.version,
        "batch_no": file.file_info.batch_no,
        "group_name": file.file_info.group_name,
        "task_type": EciticTgTaskType.COMPARE if compare_record_id else EciticTgTaskType.SINGLE,
        "project_name": project.name,
        "project_user": project_user.name,
        "product_name": project.meta["product_name"],
        "product_num": project.meta["product_num"],
        "product_type": project.meta["product_type"],
        "push_user": user_name or file_user.name,
        "push_time": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
    }

    for template in templates:
        template_answer = get_template_answer(template, root_node)
        push_data = copy(basic_info)
        push_data["template_id"] = template.id
        push_data["answer"] = template_answer
        push_data["push_configs"] = await get_push_configs(template, only_auto_push)
        push_data_list.append(push_data)
    return file, push_data_list


async def get_push_configs(template, only_auto_push):
    push_configs_list = []
    push_cond = EciticPush.template == template.id
    if only_auto_push:
        push_cond &= EciticPush.enabled
    push_configs = await pw_db.execute(EciticPush.select().where(push_cond))
    if not push_configs:
        logger.info(f"模板{template.name}的推送配置不存在")
        return push_configs_list

    for push_config in push_configs:
        push_configs_list.append(
            {
                "push_id": push_config.id,
                "push_address": push_config.push_address,
                "email": push_config.email,
            }
        )
    return push_configs_list


async def ecitic_para_map_convert(answer, split_fields_only=True):
    convert_success = True
    data = []
    para_mappings = await get_para_mappings()
    answer_items = [x for x in answer["userAnswer"]["items"] if x.get("data")]
    if not answer_items:
        raise CustomError("答案为空, 无法进行映射关系检查")
    for item in answer_items:
        path_list = json.loads(item["key"])
        if "拆分:0" not in path_list:
            if not split_fields_only:
                data.append(item)
            continue
        path_list = [p_path_before_colon.search(x).groups()[0] for x in path_list]
        path = "-".join(ecitic_path_list(path_list[1:], keep_tail=False))
        for box in item["data"]:
            if path not in para_mappings:
                box["to_value_error"] = "参数值不存在"
                box["to_value"] = []
                convert_success = False
            elif to_value := get_converted_value(get_boxes_text(box), para_mappings[path]):
                box["to_value"] = to_value
            else:
                box["to_value_error"] = "参数映射不存在"
                box["to_value"] = []
                convert_success = False
        data.append(item)

    answer["userAnswer"]["items"] = data
    return convert_success, answer


def get_converted_value(text, mappings) -> list[dict]:
    for key, value in mappings.items():
        if text == key or p_clean.sub("", text) == key:  # key在get_para_mappings()已经clean过了
            return value
    return []


async def get_para_mappings():
    para_mappings = defaultdict(lambda: defaultdict(list))
    for para_mapping in await pw_db.execute(EciticParaMap.select()):
        for value in para_mapping.values:
            value = p_clean.sub("", value)
            para_mappings[para_mapping.field][value].append(
                {
                    "to_value": para_mapping.to_value,
                    "category": para_mapping.category,
                    "group_name": para_mapping.group_name,
                }
            )

    return para_mappings


async def is_valid_mappings(field):
    para_mappings = defaultdict(lambda: defaultdict(list))
    for para_mapping in await pw_db.execute(EciticParaMap.select().where(EciticParaMap.field == field)):
        for value in para_mapping.values:
            clean_value = p_clean.sub("", value)
            if para_mapping.to_value in para_mappings[para_mapping.field][clean_value]:
                raise CustomError(f"[{value}]已经映射到{para_mapping.to_value},请勿重复创建")
            para_mappings[para_mapping.field][clean_value].append(para_mapping.to_value)
    return para_mappings


async def send_fail_email(project_name, file_name, address):
    website = get_config("citics.website")
    subject = f"【{project_name}】《{file_name}》参数推送失败，请登录【中信中证参数提取与稽核】系统进行查看"
    content = f"【{project_name}】《{file_name}》参数推送失败，请登录【中信中证参数提取与稽核】({website})系统进行查看"
    await send_email_to_ecitic_tg(subject, content, address)


async def ecitic_tg_push(project_name, file, uid, push_data_list, task_type, push_type, compare_record_id=None):
    push_records = []
    for push_data in push_data_list:
        push_configs = push_data.pop("push_configs")
        for push_config in push_configs:
            push_data.update(push_config)
            push_records.append(
                await ecitic_tg_push_to_address(
                    project_name, file, uid, push_data, task_type, push_type, compare_record_id
                )
            )
    file_info = await EciticFileInfo.get_by_file_id(file.id)
    # stat_after_push仅控制自动推送,人工推送的都需要加入统计
    if file_info.stat_after_push or push_type == EciticTgTriggerType.MANUAL:
        await pw_db.update(file_info, need_stat=True)

    return push_records


async def ecitic_tg_push_to_address(
    p_name, file, uid, data, task_type, push_type, compare_record_id
) -> EciticPushRecord:
    """
    此函数仅在ecitic_tg_push()里调用
    """

    success = True
    if task_type != EciticTgTaskType.TO_COUNT:  # TO_COUNT仅为了参与统计,不进行数据推送
        async with httpx.AsyncClient(verify=False, timeout=10) as client:
            try:
                response = await client.post(data["push_address"], json=data)
            except Exception as e:
                success = False
                logger.exception(e)
            if not success or response.status_code != 200:
                await send_fail_email(p_name, file.name, data["email"])
    record = await create_push_record(
        fid=file.id,
        task_type=task_type,
        push_type=push_type,
        uid=uid,
        status=int(success),
        data=data,
        external_source="",
        compare_record=compare_record_id,
    )
    logging.info(f"push for {file.id=}, {data['template_id']=}, {data['push_address']=}, {task_type=}, {success=}")
    return record


async def ecitic_tg_diff(question_id, standard_qid, uid, trigger_type=EciticTgTriggerType.MANUAL):
    diff_question = await NewQuestion.find_by_id(question_id)
    standard_question = await NewQuestion.find_by_id(standard_qid)
    if not diff_question or not standard_question:
        raise CustomError("not found file")
    if diff_question.mold != standard_question.mold:
        raise CustomError("不同模型的文件不允许比较")
    diff_file = await EciticFile.find_by_id(diff_question.fid, EciticFileInfo.select())
    standard_file = await EciticFile.find_by_id(standard_question.fid, EciticFileInfo.select())
    if not diff_file.file_info.version or not standard_file.file_info.version:
        raise CustomError("没有版本号的文件不允许比较")
    if diff_file.file_info.version != standard_file.file_info.version:
        raise CustomError("不同版本号的文件不允许比较")
    if not ((diff_file.is_pdf and standard_file.is_word) or (diff_file.is_word and standard_file.is_pdf)):
        raise CustomError("仅支持pdf文件和word文件之间进行比较")
    if diff_file.file_info.group_name != standard_file.file_info.group_name:
        raise CustomError("不属于同一业务组的文件不允许比较")

    if diff_file.is_pdf:
        pdf_question = diff_question
        word_question = standard_question
        word_file = standard_file
    else:
        pdf_question = standard_question
        word_question = diff_question
        word_file = diff_file

    params = {
        "qid": pdf_question.id,
        "std_qid": word_question.id,
        "mold": pdf_question.mold,
        "trigger_type": trigger_type,
        "uid": uid,
        "external_source": word_file.file_info.external_source,
    }
    async with pw_db.atomic():
        compare_record = await pw_db.create(EciticCompareRecord, **params)

        compare_result = await do_ecitic_tg_diff(compare_record.id, pdf_question, word_question)
        ganyi_compare_result = await do_ecitic_tg_diff(
            compare_record.id, pdf_question, word_question, external_source=EciticExternalSource.GANYI
        )

    return compare_record, compare_result, ganyi_compare_result


async def do_ecitic_tg_diff(compare_record_id, pdf_question, word_question, external_source=None):
    pdf_answer, _ = await get_master_question_answer(pdf_question)
    if external_source == EciticExternalSource.GANYI:  # word文档使用感易数据
        word_answer = await EciticExternalAnswerConverter.convert(word_question)
        if not word_answer:  # 文档没有感易数据
            return None
    else:
        word_answer, _ = await get_master_question_answer(word_question)

    if is_empty_answer(pdf_answer, "userAnswer") or is_empty_answer(word_answer, "userAnswer"):
        raise CustomError("Answer not ready yet!")

    pdf_answer_dict = AnswerReader(pdf_answer).to_tile_dict()
    word_answer_dict = AnswerReader(word_answer).to_tile_dict()

    pdf_answer_dict, word_answer_dict, is_diff = diff_two_items(pdf_answer_dict, word_answer_dict)

    pdf_answer["userAnswer"]["items"] = list(pdf_answer_dict.values())
    word_answer["userAnswer"]["items"] = list(word_answer_dict.values())

    params = {
        "is_diff": is_diff,
        "answer": pdf_answer,
        "std_answer": word_answer,
        "external_source": external_source,
    }
    compare_result = await pw_db.create(EciticCompareResult, **params)
    await pw_db.create(
        EciticCompareRecordResultRef, compare_record_id=compare_record_id, compare_result_id=compare_result.id
    )
    return compare_result


def diff_two_items(diff_answer_dict, standard_answer_dict):
    is_diff = False
    for key, item in diff_answer_dict.items():
        similarity = None
        if key in standard_answer_dict:
            similarity = get_item_similarity(standard_answer_dict[key], item)
            if "拆分" in key:
                mark_same_box(standard_answer_dict[key], item)
            standard_answer_dict[key]["similarity"] = similarity
        if similarity is None or similarity < 1.00:
            is_diff = True
        item["similarity"] = similarity

    for key, item in standard_answer_dict.items():
        if key not in diff_answer_dict:
            item["similarity"] = None
            is_diff = True

    return diff_answer_dict, standard_answer_dict, is_diff


def get_item_similarity(std_item, diff_item):
    std_answer_item = AnswerItem(**std_item)
    diff_answer_item = AnswerItem(**diff_item)
    return calc_similarity(std_answer_item.plain_text, diff_answer_item.plain_text)


def mark_same_box(std_item, diff_item):
    for diff_box in diff_item["data"]:
        diff_box["pair_index"] = None

    possible_pairs = []
    matched_std_index = []
    matched_diff_index = []
    for std_idx, std_box in enumerate(std_item["data"]):
        std_box["pair_index"] = None
        for diff_idx, diff_box in enumerate(diff_item["data"]):
            similarity = calc_similarity(get_boxes_text(std_box), get_boxes_text(diff_box))
            possible_pairs.append((similarity, std_idx, diff_idx))

    for pair in sorted(possible_pairs, key=lambda x: x[0], reverse=True):
        similarity, std_idx, diff_idx = pair
        if similarity < 0.75:
            break
        if std_idx in matched_std_index or diff_idx in matched_diff_index:
            continue
        matched_std_index.append(std_idx)
        matched_diff_index.append(diff_idx)
        std_item["data"][std_idx]["pair_index"] = diff_idx
        std_item["data"][std_idx]["similarity"] = similarity
        diff_item["data"][diff_idx]["pair_index"] = std_idx
        diff_item["data"][diff_idx]["similarity"] = similarity

        if len(matched_std_index) == len(std_item["data"]) and len(matched_diff_index) == len(diff_item["data"]):
            break


async def refresh_ecitic_new_file(pid, file_ext, new_mold, new_version, old_mold=None, old_version=None):
    async def update_new_file_tag(mold, version):
        if not (mold and version):
            return

        query = (
            EciticFile.select(EciticFile.id)
            .join(EciticFileInfo)
            .join(NewQuestion, on=(NewQuestion.fid == EciticFile.id))
        )
        cond = and_(
            EciticFile.pid == pid,
            EciticFile.name.ilike(f"%{file_ext}"),
            EciticFileInfo.version == version,
            NewQuestion.mold == mold,
        )
        latest_file = await pw_db.prefetch_one(
            query.where(cond).order_by(EciticFile.id.desc()), EciticFileInfo.select()
        )

        if latest_file:
            if not latest_file.file_info.is_new_file:
                await pw_db.execute(
                    EciticFileInfo.update(is_new_file=True).where(EciticFileInfo.file == latest_file.id)
                )

            with_tag_cond = cond & and_(EciticFileInfo.is_new_file, EciticFile.id != latest_file.id)
            if with_tag_file := await pw_db.first(query.where(with_tag_cond)):
                await pw_db.execute(
                    EciticFileInfo.update(is_new_file=False).where(EciticFileInfo.file == with_tag_file.id)
                )

    if new_mold == old_mold and new_version == old_version:
        return
    await update_new_file_tag(new_mold, new_version)
    await update_new_file_tag(old_mold, old_version)


async def ecitic_get_files_and_questions_by_tree(tid, offset, need_file_count):
    query = (
        EciticFile.select(
            EciticFile,
            EciticFileInfo,
            NewAdminUser.name.alias("user_name"),
        )
        .join(EciticFileInfo)
        .left_outer_join(NewAdminUser, on=(EciticFile.uid == NewAdminUser.id))
        .where(EciticFile.tree_id == tid)
        .order_by(EciticFile.id.desc())
        .dicts()
    )
    query = query.offset(offset).limit(need_file_count)
    files = list(await pw_db.execute(query))
    file_ids = [file["id"] for file in files]
    question_query = (
        NewQuestion.select(
            NewQuestion.id,
            NewQuestion.fid,
            NewQuestion.mold,
            NewQuestion.ai_status,
            NewQuestion.health,
            NewQuestion.updated_utc,
            NewQuestion.fill_in_user,
            NewQuestion.data_updated_utc,
            NewQuestion.updated_utc,
            NewQuestion.fill_in_status,
            NewQuestion.progress,
            NewQuestion.status,
            NewQuestion.health,
            NewQuestion.ai_status,
            NewQuestion.name,
            NewQuestion.num,
            NewQuestion.mark_uids,
            NewQuestion.mark_users,
            fn.COALESCE(NewQuestion.origin_health, 1).alias("origin_health"),
            NewMold.name.alias("mold_name"),
        )
        .join(NewMold, on=(NewQuestion.mold == NewMold.id))
        .where(NewQuestion.fid.in_(file_ids), NewQuestion.deleted_utc == 0)
        .order_by(NewQuestion.fid.desc(), NewQuestion.mold)
        .dicts()
    )
    question_by_fid = defaultdict(list)
    for question in await pw_db.execute(question_query):
        question_by_fid[question["fid"]].append(question)

    for file in files:
        file["questions"] = question_by_fid[file["id"]]

    return files


class EciticExternalAnswerConverter:
    @classmethod
    def is_leaf(cls, data):
        if isinstance(data, list) and all(isinstance(x, str) for x in data):
            return True
        return False

    @classmethod
    def build_answer_items(cls, schema, key_path, data):
        answer_items = []
        if cls.is_leaf(data):
            is_contain, key = schema.contains_path(key_path)
            if not is_contain:
                raise RuntimeError(f"Invalid {key}")

            answer_items.append(
                {
                    "key": compact_dumps(key_path, ensure_ascii=False),
                    "data": [
                        {
                            "text": x,
                            "_external_source": EciticExternalSource.GANYI,
                        }
                        for x in data
                    ],
                }
            )
        elif isinstance(data, dict):
            sub_key_path = copy(key_path)
            answer_items.extend(cls.build_answer(schema, sub_key_path, data))
        else:
            raise RuntimeError("Invalid data structure")
        return answer_items

    @classmethod
    def build_answer(cls, schema: Schema, key_path: list, data: dict) -> list:
        """
        {
            "产品名称": ["凌顶望岳十五号私募证券投资基金"],
            "投资范围(其它-投资监督)":[
                {
                    "原文": ["主板、科创板、创业板"],
                    "拆分": ["主板", "科创板", "创业板"]
                }
            ]
        }
        :return:
        """
        answer_items = []

        for key, value in data.items():
            if cls.is_leaf(value):
                sub_key_path = copy(key_path)
                sub_key_path.append(f"{key}:0")
                answer_items.extend(cls.build_answer_items(schema, sub_key_path, value))
            else:
                for idx, item in enumerate(value):
                    sub_key_path = copy(key_path)
                    sub_key_path.append(f"{key}:{idx}")

                    answer_items.extend(cls.build_answer_items(schema, sub_key_path, item))
        return answer_items

    @classmethod
    async def convert(cls, question):
        """
        把外部的 感易 的数据,转换成通用格式
        {
            "schema": {},
            "userAnswer: {}
        }
        :param question:
        :return:
        """
        mold = await NewMold.find_by_id(question.mold)
        answer = await pw_db.first(
            NewSpecialAnswer.select().where(
                NewSpecialAnswer.qid == question.id, NewSpecialAnswer.answer_type == SpecialAnswerType.JSON_ANSWER
            )
        )
        if not answer:
            return {}
        schema = Schema(mold.data)
        answer_items = cls.build_answer(schema, [f"{mold.name}:0"], answer.data)

        ret = {"schema": mold.data, "userAnswer": {"items": answer_items}}

        return ret


if __name__ == "__main__":
    import asyncio

    asyncio.run(get_push_data(11940))
