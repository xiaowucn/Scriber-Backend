import json
import logging
import os
import re
from collections import namedtuple
from copy import deepcopy

from attr import define, field
from glom import assign, glom
from speedy.peewee_plus.orm import fn

from remarkable.answer.common import create_empty_answer, parse_path
from remarkable.common.callback import http_post_callback
from remarkable.common.constants import AIStatus, AnswerStatus, LLMStatus, MoldType, QuestionStatus
from remarkable.common.multiprocess import run_in_multiprocess
from remarkable.common.schema import Schema
from remarkable.common.storage import localstorage
from remarkable.common.util import outline_to_box
from remarkable.config import get_config
from remarkable.converter.utils import generate_cache_for_diff, generate_customer_answer, push_answer_to_remote
from remarkable.db import pw_db
from remarkable.models.new_file import NewFile
from remarkable.models.new_user import ADMIN, NewAdminUser
from remarkable.optools.export_answers_with_format import format_answer_to_json_tree, get_annotation_answer
from remarkable.predictor.mold_schema import MoldSchema, SchemaItem
from remarkable.pw_models.model import MoldWithFK, NewAnswer, NewMold
from remarkable.pw_models.question import NewQuestion, QuestionWithFK
from remarkable.schema.answer import UserAnswer
from remarkable.security import authtoken
from remarkable.service.new_file import NewFileService
from remarkable.service.statistics import save_stat_result
from remarkable.service.studio import get_trace_result
from remarkable.utils.answer_util import AnswerUtil

logger = logging.getLogger(__name__)


class NewQuestionService:
    @staticmethod
    def question_query_without_answer(
        file_ids: list[int] = None,
        uid: int = None,
        is_answered: bool = None,
        status: int = None,
    ):
        default_health = get_config("web.default_question_health") or 1

        cond = []
        if file_ids:
            cond.append(NewQuestion.fid.in_(file_ids))
        if is_answered:
            cond.append(NewQuestion.mark_uids.contains(uid))
        if status:
            cond.append(NewQuestion.status == status)

        question_fields = [
            NewQuestion.id,
            NewQuestion.fid,
            NewQuestion.name,
            NewQuestion.mold,
            NewQuestion.ai_status,
            NewQuestion.health,
            NewQuestion.updated_utc,
            NewQuestion.fill_in_user,
            NewQuestion.data_updated_utc,
            NewQuestion.fill_in_status,
            NewQuestion.progress,
            NewQuestion.status,
            NewQuestion.num,
            NewQuestion.mark_uids,
            NewQuestion.mark_users,
            fn.COALESCE(NewQuestion.origin_health, default_health).alias("origin_health"),
        ]

        query = (
            NewQuestion.select(*question_fields, NewMold.name.alias("mold_name"))
            .join(NewMold, on=(NewMold.id == NewQuestion.mold))
            .where(*cond)
        )

        return query

    @staticmethod
    async def update_markers(question: NewQuestion):
        mark_uids = []
        mark_users = []
        users = await pw_db.execute(NewAdminUser.select().where(NewAdminUser.deleted_utc == 0))
        users_map = {u.id: u.name for u in users}
        answers = await pw_db.execute(
            NewAnswer.select()
            .where(NewAnswer.qid == question.id, NewAnswer.status.in_((AnswerStatus.VALID, AnswerStatus.UNFINISHED)))
            .order_by(NewAnswer.updated_utc)
        )

        for answer in answers:
            mark_uids.append(answer.uid)
            mark_users.append(users_map.get(answer.uid, f"DELETED_{answer.uid}"))

        await question.update_(**{"mark_uids": mark_uids, "mark_users": mark_users})

    @staticmethod
    async def get_mark_summary(prj_id, tree_ids: list[int], mold_ids: list[int] | None = None):
        user_data = {}
        for user in await pw_db.execute(NewAdminUser.select()):
            user_data[user.id] = {"name": user.name, "login_count": user.login_count}

        cond = (NewFile.pid == prj_id) & (NewQuestion.status != QuestionStatus.TODO.value)

        if tree_ids is not None:
            cond &= NewFile.tree_id.in_(tree_ids)

        if mold_ids is not None:
            cond &= NewQuestion.mold.in_(mold_ids)

        records = await pw_db.execute(
            NewAnswer.select(NewAdminUser.id, fn.COUNT(NewAdminUser.id))
            .join(NewAdminUser, on=(NewAdminUser.id == NewAnswer.uid))
            .join(NewQuestion, on=(NewQuestion.id == NewAnswer.qid))
            .join(NewFile, on=(NewFile.id == NewQuestion.fid))
            .where(cond)
            .group_by(NewAdminUser.id)
            .tuples()
        )
        mark_summary = []
        for uid, markcount in records:
            name = ""
            login_count = -1
            if uid in user_data:
                name = user_data[uid]["name"]
                login_count = user_data[uid]["login_count"]
            mark_summary.append({"uid": uid, "markcount": markcount, "name": name, "login_count": login_count})
        return mark_summary

    @staticmethod
    async def get_question_ai_status(fid):
        questions: list[NewQuestion] = await NewQuestion.find_by_fid(fid)
        for status in (
            AIStatus.DISABLE,
            AIStatus.SKIP_PREDICT,
            AIStatus.TODO,
            AIStatus.DOING,
            AIStatus.FAILED,
            AIStatus.FINISH,
        ):
            for question in questions:
                if question.ai_status == status:
                    return status
        return AIStatus.FAILED

    @staticmethod
    def build_empty_answer(schema: SchemaItem, index: int = 0):
        empty_answer = create_empty_answer(schema, index)
        empty_answer["meta"] = {"placeholder": True}
        return empty_answer

    @classmethod
    def fill_group_with_fixed_length(cls, answer: dict, mold: NewMold, amount: int = 1, ignore_basic_type: bool = True):
        group_answers = {}
        items = glom(answer, "userAnswer.items")
        keys = set()
        basic_type_keys = set()
        for item in items:
            paths = parse_path(item["key"])
            if len(paths) == 2:
                basic_type_keys.add(f"{paths[1][0]}")
            elif len(paths) == 3:
                keys.add(item["key"])
                assign(group_answers, f"{paths[1][0]}.{paths[1][1]}.{paths[2][0]}", item, dict)
            else:
                raise Exception(f"Unsupported key: {item['key']}")

        # 如果分组数量等于0, 则生成一个空答案
        schema = MoldSchema(mold.data)
        for child in schema.root_schema.children:
            if not child.children:
                if child.name not in basic_type_keys and not ignore_basic_type:
                    items.append(cls.build_empty_answer(child, 0))
                continue

            group_answers.setdefault(
                child.name,
                {"0": {c.name: cls.build_empty_answer(c, 0) for c in child.children}},
            )
            for i in range(amount):
                if str(i) not in group_answers[child.name]:
                    # 如果分组数量少于amount, 则补全
                    group = group_answers[child.name][str(i)] = {
                        c.name: cls.build_empty_answer(c, i) for c in child.children
                    }
                else:
                    group = group_answers[child.name][str(i)]
                for c in child.children:
                    if c.name in group:
                        continue
                    group_answers[child.name][str(i)][c.name] = cls.build_empty_answer(c, i)
        items.extend(
            item
            for groups in group_answers.values()
            for group in groups.values()
            for item in group.values()
            if item["key"] not in keys
        )
        assign(answer, "userAnswer.items", items)

    @classmethod
    async def post_pipe(cls, qid, fid, file_meta_info, skip_hook: bool = False, **kwargs):
        """
        Question.set_answer 执行完之后做的一些后续操作
        :return:
        """
        from remarkable.hooks import PredictFinishHook

        if not get_config("data_flow.post_pipe_after_preset", True):
            logging.info(f"Skip post_pipe after preset for question: {qid}")
            return

        logger.info(f"post_pipe after preset for question: {qid}")

        push_predict = get_config("web.push_preset_answer") or False
        customer_answer = get_config("web.customer_answer") or False
        gen_diff_cache = get_config("web.gen_diff_cache") or False

        if push_predict:
            logging.info(f"push_preset_answer for file: {fid}, question: {qid}")
            await push_answer_to_remote(qid)

        if customer_answer:
            logging.info(f"generate_customer_answer for file: {fid}, question: {qid}")
            await generate_customer_answer(qid)
        question = await QuestionWithFK.get_by_id(qid, prefetch_queries=[MoldWithFK.select(), NewFile.select()])
        if not skip_hook:
            await PredictFinishHook(question).__call__()

        if (file_meta_info or {}).get("annotation_callback"):
            logging.info(f"annotation_callback for file: {fid}, question: {qid}")
            await cls.annotation_post_processing(qid)

        if gen_diff_cache:
            logging.info(f"generate_cache_for_diff for file: {fid}, question: {qid}")
            await generate_cache_for_diff(qid)

    @staticmethod
    async def annotation_post_processing(qid):
        """标注完成后续处理：
        1. 重新预测
        2. 重新检查合规
        3. 标注结果推送
        """

        file = await NewFile.find_by_qid(qid)
        file_meta = file.meta_info or {}
        callback_url = file_meta.get("annotation_callback")
        answer_from = file_meta.get("answer_from", "user")
        answer_format = file_meta.get("answer_format", "json_tree")
        if not callback_url:
            logging.error(f"No callback url for file: {file.id}")
            return

        encode_url_for = file_meta.get("encode_url_for")
        if encode_url_for and get_config(f"app.auth.{encode_url_for}"):
            app_id = get_config(f"app.auth.{encode_url_for}.app_id")
            secret_key = get_config(f"app.auth.{encode_url_for}.secret_key")
            if app_id and secret_key:
                callback_url = authtoken.encode_url(callback_url, app_id, secret_key)
            else:
                logging.warning(f"Missing auth section for {encode_url_for}, please check the config file")

        answer_data = await get_annotation_answer(qid, answer_from)
        mold = await pw_db.scalar(NewQuestion.select(NewQuestion.mold).where(NewQuestion.id == qid))
        if answer_data and answer_format == "json_tree":
            answer_data = format_answer_to_json_tree(answer_data, localstorage.mount(file.pdfinsight_path()))
        answer_data["checksum"] = file.hash
        answer_data["question_id"] = qid
        answer_data["schema_id"] = mold
        await http_post_callback(callback_url, json=answer_data)


async def batch_preset(
    start,
    end,
    project=None,
    mold=None,
    overwrite=False,
    save=None,
    workers=0,
    headnum=10,
    vid=0,
    preset_path=None,
    tree_s=None,
    acid=None,
    ctx_method="fork",
    special_rules=None,
    files_ids=None,
):
    questions = await NewQuestion.list_by_range(
        start=start,
        end=end,
        project=project,
        mold=mold,
        have_preset_answer=None if overwrite else False,
        special_cols=["id", "fid"],
        files_ids=files_ids,
    )
    tasks = [
        (
            q.fid,
            q.id,
            vid,
            preset_path,
            special_rules,
        )
        for q in questions
    ]

    async with pw_db.atomic():
        run_in_multiprocess(run_preset_answer, tasks, workers=workers, ctx_method=ctx_method)
        if save:
            await save_stat_result(preset_path, headnum, mold, save, vid, tree_s, acid)


async def run_preset_answer(args):
    from remarkable.predictor.predict import predict_answer

    fid, qid, vid, preset_path, special_rules = args
    question = await NewQuestion.find_by_id(qid)
    file = await NewFile.find_by_id(fid)
    logging.info(f"preset answer for file: {fid}")
    async with pw_db.atomic():
        answer = await predict_answer(question, vid, special_rules)
        await question.set_answer()
        await NewQuestionService.post_pipe(qid, fid, file.meta_info, triggered_by_predict=True)
        await NewFileService.post_pipe(file.id, triggered_by_predict=True)
        if preset_path and os.path.exists(preset_path):
            with open(os.path.join(preset_path, "%s.json" % fid), "w") as file_obj:
                json.dump(answer, file_obj)


def get_extract_key_paths(data, pre_path):
    """递归获取所有路径，使用带类型信息的数据结构"""
    paths = []
    for key, value in data.items():
        # multi = true
        if isinstance(value, list):
            for idx, item in enumerate(value):
                # 基本类型
                if isinstance(item, str):
                    paths.append({"path": pre_path + [{"name": key, "type": "array", "index": idx}], "value": item})
                # 组合类型
                elif isinstance(item, dict):
                    for sub_key, sub_value in item.items():
                        paths.append(
                            {
                                "path": pre_path
                                + [{"name": key, "type": "array", "index": idx}, {"name": sub_key, "type": "normal"}],
                                "value": sub_value,
                            }
                        )
        # multi = false 组合类型
        elif isinstance(value, dict):
            paths.extend(get_extract_key_paths(value, pre_path + [{"name": key, "type": "normal"}]))

        # multi = false 基本类型
        else:
            paths.append({"path": pre_path + [{"name": key, "type": "normal"}], "value": value})
    return paths


def build_answer_from_trace_data(path, trace_data_ref):
    """根据路径在trace_data中查找并构建答案，支持带类型信息的路径格式"""
    # 将路径转换为层级访问
    current_level = trace_data_ref or {}
    path_index = 0

    while path_index < len(path):
        path_element = path[path_index]
        key_name = path_element["name"]
        # 检查键是否存在于当前层级
        if key_name not in current_level:
            return None
        current_level = current_level[key_name]
        # 如果路径元素是数组类型，需要进一步用索引访问
        if path_element["type"] == "array":
            if isinstance(current_level, list):
                try:
                    idx = path_element["index"]
                    if idx < len(current_level):
                        current_level = current_level[idx]
                        path_index += 1
                    else:
                        return None
                except (ValueError, TypeError):
                    return None
            else:
                # 如果不是列表，说明只是普通的带后缀的键名，继续处理
                path_index += 1
        else:
            # 对于普通类型，继续处理
            path_index += 1
    return current_level


def get_answer_item_value(schema, schema_item, value):
    if not schema_item.is_enum:
        return []

    answer_item_value = []
    if (enum_type := schema.get_enum_values(schema_item.type)) and value in enum_type:
        answer_item_value.append(value)
    return answer_item_value


def _create_answer_item(key, schema, value, data):
    schema_item = schema.find_schema_by_path(key)
    return {
        "key": key,
        "data": data,
        "schema": schema_item.to_answer_data(),
        "value": get_answer_item_value(schema, schema_item, value),
    }


def _add_answer_item(answer_items, answer_item):
    item_key = answer_item["key"]
    if item_key in answer_items:
        answer_items[item_key]["data"].extend(answer_item["data"])
    else:
        answer_items[item_key] = answer_item


def _build_path_key(model_name, path):
    path_key = [f"{model_name}:0"]
    for p in path[:-1]:
        if p["type"] == "array":
            path_key.append(f"{p['name']}:{p['index']}")
        else:
            path_key.append(f"{p['name']}:0")
    path_key.append(f"{path[-1]['name']}:0")
    return path_key


def get_answer_items(extract_data, trace_data, model_name, schema):
    answer_items = {}
    key_paths = get_extract_key_paths(extract_data["data"], [])

    for item in key_paths:
        trace_result = None
        path = item["path"]
        text = value = "" if item["value"] is None else str(item["value"])
        path_key = _build_path_key(model_name, path)
        key = json.dumps(path_key, ensure_ascii=False)
        schema_item = schema.find_schema_by_path(key)
        if text != "":
            if schema_item.is_enum and isinstance(extract_data.get("sources"), dict):
                text = build_answer_from_trace_data(path, extract_data["sources"]) or text
            # 检查在trace_data中是否对应路径存在数据
            trace_result = build_answer_from_trace_data(path, trace_data)
            # 临时适配source-fragments api
            if (
                isinstance(trace_result, dict)
                and trace_result.get("data") is None
                and trace_result.get("box") is not None
            ):
                trace_result = {"status": "traced", "data": [trace_result]}

        if schema_item.regex:
            if searched_value := re.compile(schema_item.regex).search(text):
                text = searched_value.group()
            else:
                text = ""

        answer_item_data = []
        answer_item_traces = []
        if trace_result and isinstance(trace_result, dict) and trace_result.get("status") == "traced":
            if trace_result["data"]:
                for data in trace_result["data"]:
                    boxes = []
                    for j, box in enumerate(data["box"]):
                        for page, b in box.items():
                            boxes.append({"page": int(page), "box": outline_to_box(b), "text": text if j == 0 else ""})

                    if not boxes:
                        boxes = [{"text": text}]
                    answer_item_traces.append({"boxes": boxes})
            else:
                answer_item_traces.append({"boxes": [{"text": text}]})
        else:
            answer_item_traces.append({"boxes": [{"text": text}]})

        answer_item_data.append({"items": answer_item_traces, "text": text})
        answer_item = _create_answer_item(key, schema, value, answer_item_data)
        _add_answer_item(answer_items, answer_item)

    return list(answer_items.values())


async def run_extract_answer(fid, upload_id, mold_id, data, question):
    preset_answer = None
    if data["status"] == 100:
        llm_status = LLMStatus.FINISH
        mold = await NewMold.find_by_id(mold_id)
        answer_items = []
        if isinstance(data["data"], dict):
            schema = MoldSchema(mold.data)
            try:
                trace_data = await get_trace_result(mold.studio_app_id, upload_id)
            except Exception as e:
                logging.warning(f"Failed to get trace data: {fid}, {mold_id}: {e}")
                trace_data = {}
            answer_items = get_answer_items(data["data"], trace_data, mold.name, schema)

        preset_answer = {
            "schema": mold.data | {"version": mold.checksum},
            "userAnswer": {"items": answer_items, "version": "2.2"},
        }
        answers_data = [UserAnswer._make([ADMIN.id, ADMIN.name, preset_answer])]
        if mold.mold_type == MoldType.HYBRID and question.exclusive_status == AIStatus.FINISH:
            answers_data.append(UserAnswer._make([ADMIN.id, ADMIN.name, question.preset_answer]))
        preset_answer = AnswerUtil.merge_answers(answers_data, schema_data=mold.data)
    else:
        llm_status = LLMStatus.FAILED
    file = await NewFile.find_by_id(fid)
    await question.update_record(llm_status=llm_status, preset_answer=preset_answer)
    await question.set_answer()
    await NewQuestionService.post_pipe(question.id, fid, file.meta_info, triggered_by_predict=True)
    await NewFileService.post_pipe(fid, triggered_by_predict=True)


def replace_answer_item(origin_answer, new_answer, special_rules):
    items = origin_answer["userAnswer"]["items"]
    items = [item for item in items if json.loads(item["key"])[1].split(":")[0] not in special_rules]
    origin_answer["userAnswer"]["items"] = items + new_answer["userAnswer"]["items"]
    return origin_answer


@define
class MixinSchema:
    mold: NewMold = field()
    schema: Schema = field(init=False)
    mold_schema: MoldSchema = field(init=False)

    def __attrs_post_init__(self):
        self.schema = Schema(self.mold.data)
        self.mold_schema = MoldSchema(self.mold.data)

    @classmethod
    async def initialize(cls, mid: int) -> "MixinSchema":
        mold = await NewMold.find_by_id(mid)
        assert mold, f"No mold found: {mid}"
        return cls(mold)


async def migrate_answers(
    question: NewQuestion,
    *,
    mixin_schema: MixinSchema | None = None,
    overwrite=False,
    safe_mode=False,
    update_timestamp=True,
):
    assert question.mold, f"Question: {question.id}, fid: {question.fid} has no schema yet"
    MixinAnswer = namedtuple("Answer", ["id", "table", "col", "data"])
    answers = await NewAnswer.get_answers_by_qid(question.id)
    all_answers = [MixinAnswer._make([answer.id, "answer", "data", answer.data]) for answer in answers]
    if question.preset_answer:
        all_answers.append(MixinAnswer._make([question.id, "question", "preset_answer", question.preset_answer]))
    if question.answer:
        all_answers.append(MixinAnswer._make([question.id, "question", "answer", question.answer]))

    if not mixin_schema:
        mixin_schema = await MixinSchema.initialize(question.mold)

    for answer in all_answers:
        if answer.data["schema"]["version"] == mixin_schema.mold.checksum and not overwrite:
            logging.info("%s %s has same schema version", answer.table, answer.id)
            continue

        items_to_delete = []
        items_to_remain = []
        for item in answer.data.get("userAnswer", {}).get("items", []):
            need_remain, key_str = mixin_schema.schema.contains_path(item["key"], skip_root=True)
            if need_remain:
                item["key"] = key_str
                # 更新可能的类型变化
                item["schema"] = mixin_schema.mold_schema.find_schema_by_path(key_str).to_answer_data()
                items_to_remain.append(item)
            else:
                items_to_delete.append(item)
        logging.info(
            "%s %s wants to remove items:%s",
            answer.table,
            answer.id,
            "\n".join([item["key"] for item in items_to_delete]),
        )
        logging.info(f"{len(items_to_remain)} items remain")
        if safe_mode:
            logging.warning("running in safe mode, pass this migration")
            continue
        answer.data["userAnswer"]["items"] = items_to_remain
        logging.info(f"{len(items_to_delete)} items deleted")
        answer.data["schema"] = deepcopy(mixin_schema.mold.data)
        answer.data["schema"]["version"] = mixin_schema.mold.checksum
        if answer.table == "answer":
            await NewAnswer.update_by_pk(answer.id, update_timestamp=update_timestamp, data=answer.data)
        if answer.table == "question":
            await NewQuestion.update_by_pk(answer.id, update_timestamp=update_timestamp, **{answer.col: answer.data})
        logging.info("update %s %s schema to version %s", answer.table, answer.id, mixin_schema.mold.checksum)
