import asyncio
import base64
import glob
import html
import http
import io
import json
import logging
import os
import random
import re
import shutil
import tempfile
import time
import zipfile
from collections import defaultdict
from datetime import datetime
from importlib import import_module
from json import JSONDecodeError
from pathlib import Path

import attr
import openpyxl
import peewee_async
import redis_lock
from asyncpg import UniqueViolationError
from openpyxl.styles import Font
from peewee import JOIN
from speedy.peewee_plus.orm import TRUE
from sqlalchemy import and_
from webargs import ValidationError, fields

from remarkable import config
from remarkable.answer.common import gen_key_md5
from remarkable.base_handler import Auth, BaseHandler, DbQueryHandler, PermCheckHandler, route
from remarkable.common import field_validate
from remarkable.common.apispec_decorators import use_kwargs
from remarkable.common.constants import (
    AccuracyRecordStatus,
    AccuracyTest,
    AnswerResult,
    AnswerStatus,
    AnswerType,
    CommonStatus,
    FeatureSchema,
    HistoryAction,
    ModelEnableStatus,
    ModelType,
    MoldType,
    PredictorTrainingStatus,
    QuestionStatus,
)
from remarkable.common.enums import ClientName, ExportStatus, NafmiiEventStatus, NafmiiEventType
from remarkable.common.exceptions import ConfigError, CustomError, CustomReError, InvalidMoldError
from remarkable.common.file_progress import QuestionProgress
from remarkable.common.file_util import copy_model_file
from remarkable.common.redis_cache import QUESTION_POST_PIPE_KEY
from remarkable.common.schema import Schema
from remarkable.common.util import (
    answer_type_to_history_action_type,
    compact_dumps,
    dump_data_to_worksheet,
    generate_timestamp,
    run_singleton_task,
)
from remarkable.config import get_config
from remarkable.converter.utils import get_answer_workshop
from remarkable.db import db, init_rdb, peewee_transaction_wrapper, pw_db
from remarkable.models.cmf_china import CmfMoldModelRef
from remarkable.models.ecitic import EciticTemplate
from remarkable.models.model_version import NewModelVersion
from remarkable.models.new_file import NewFile
from remarkable.models.new_user import NewAdminUser
from remarkable.models.query_helper import AsyncPagination
from remarkable.optools.export_answers_for_szse import fetch_all_answers
from remarkable.predictor.custom_config import model_config_map
from remarkable.predictor.predict import predict_answer
from remarkable.pw_models.audit_rule import NewAuditRule
from remarkable.pw_models.model import (
    MoldWithFK,
    NewAccuracyRecord,
    NewAdminOp,
    NewAnswer,
    NewFileTree,
    NewHistory,
    NewMold,
    NewSpecialAnswer,
    NewSystemConfig,
    NewTrainingData,
)
from remarkable.pw_models.question import NewQuestion, QuestionWithFK
from remarkable.routers.schemas.mold import MoldDataSchema
from remarkable.security.package_encrypt import AES256GCMEncryptor, PackageEncrypt
from remarkable.service.answer import delete_custom_field
from remarkable.service.api_cleaner import post_pipe_after_api
from remarkable.service.new_file_tree import NewFileTreeService
from remarkable.service.new_mold import NewMoldService
from remarkable.service.new_question import NewQuestionService, migrate_answers
from remarkable.service.predictor import PREDICTOR_MODEL_FILES
from remarkable.service.prompter import PROMPTER_MODEL_FILES, archive_model, get_files_data
from remarkable.service.studio import create_app, delete_app, get_llm_list, update_app
from remarkable.service.sync import clear_sync_schedule_lock
from remarkable.service.user import gen_salt
from remarkable.worker.tasks import (
    celery,
    preset_answers_for_mold_online,
    process_file,
    question_post_pipe_task,
    save_event_log,
    update_model_v2,
    update_predict_model,
)

tmp_dir = get_config("web.tmp_dir")
if not os.path.exists(tmp_dir):
    os.makedirs(tmp_dir)

logger = logging.getLogger(__name__)

model_args = {
    "schema_id": fields.Int(required=True),
    "model_type": fields.Int(validate=field_validate.OneOf(ModelType.member_values())),
}

manage_model_args = {
    "name": fields.String(required=True),
    "schema_id": fields.Int(required=True),
    "tree_l": fields.List(fields.Int(), load_default=[]),
    "vid": fields.Int(load_default=-1),
    "files_ids": fields.List(fields.Int(), load_default=[]),
    "export_excel": fields.Bool(load_default=False),
}
vid_update_args = {"vid": fields.Int(required=True), "update": fields.Int(required=True)}


def _validate_export_type(export_type):
    support_types = ["csv", "json", "txt"]
    if ClientName.cmfchina == config.get_config("client.name"):
        support_types.append("excel")
    if export_type not in support_types:
        raise ValidationError(f"Valid types: {support_types}")
    if export_type == "csv":
        export_answer_csv = config.get_config("client.export_answer_csv")
        export_inspect_result = config.get_config("feature.export_inspect_result")
        if not (export_answer_csv or export_inspect_result):
            raise ValidationError("client.export_answer_csv config not ready")
    if export_type == "json" and not config.get_config("client.export_label_data"):
        raise ValidationError("client.export_label_data config not ready")
    if export_type == "txt" and not config.get_config("client.export_label_txt"):
        raise ValidationError("client.export_label_txt config not ready")


def _validate_export_action(export_action):
    support_actions = HistoryAction.member_values()
    if export_action not in support_actions:
        raise ValidationError(f"Valid types: {support_actions}")


@route(r"/project/(?P<project_id>\d+)/question")
class QuestionHandler(DbQueryHandler):
    @Auth("browse")
    @use_kwargs({"status": fields.Int(load_default=0)}, location="query")
    async def get(self, project_id, status):
        sql = """
            select {{}}
            from question
            left join file on question.fid = file.id
            left join answer on answer.qid = question.id and answer.status = 1 and answer.uid = %(uid)s
            where question.deleted_utc=0 and file.pid=%(project_id)s and question.status = {status}
        """.format(status=status)
        columns = [
            "question.id",
            "question.data as data",
            "answer.data as answer",
            "question.status",
            "question.updated_utc",
        ]
        pagedata = await self.pagedata_from_request(
            self,
            sql,
            columns,
            orderby="order by updated_utc desc",
            params={"uid": self.current_user.id, "project_id": project_id},
        )
        return self.data(pagedata)


@route(r"/question/mine")
class MineAnswerHandler(DbQueryHandler):
    @Auth("browse")
    async def get(self):
        extra_filter = []
        result = self.get_query_argument("result", default=AnswerResult.NONE.value)
        if int(result) != AnswerResult.NONE.value:
            extra_filter.append(" and answer.result=%(answer_result)s")

        sql = """select {{}}
            from question inner join answer on answer.qid = question.id and answer.status = 1 and answer.uid = %(uid)s
              {} where question.deleted_utc=0;""".format("".join(extra_filter))

        columns = [
            "question.id",
            "question.data as data",
            "answer.data as answer",
            "question.status",
            "answer.updated_utc",
        ]
        pagedata = await self.pagedata_from_request(
            self,
            sql,
            columns,
            orderby="order by answer.updated_utc desc",
            params={"uid": self.current_user.id, "answer_result": result},
        )
        return self.data({"uid": self.current_user.id, **pagedata})


@route(r"/question/(id|checksum)/(.*)")
class SingleQuestionHandler(PermCheckHandler):
    @Auth("browse")
    async def get(self, *args):
        (col, val) = args
        if col == "id":
            if not val.isdigit():
                return self.error(_("Invalid input parameters."), status_code=http.HTTPStatus.BAD_REQUEST)
            val = int(val)
        elif col == "checksum":
            val = "'{}'".format(val)

        question = await NewQuestion.find_by_kwargs(**{col: val})
        if not question:
            return self.error(_("The question does not exists."), status_code=http.HTTPStatus.NOT_FOUND)
        await migrate_answers(question, update_timestamp=False)
        question = await NewQuestion.find_by_id(question.id)
        await self.check_question_permission(question.id)
        question.answers = await self.get_answers(question.id)
        export_answer = await NewSpecialAnswer.get_answers(question.id, NewSpecialAnswer.ANSWER_TYPE_EXPORT, top=1)
        question.export_answer = export_answer[0].data if export_answer else None
        data = question.to_dict(
            only=[
                getattr(NewQuestion, col)
                for col in ["id", "data", "status", "health", "origin_health", "answer", "preset_answer", "ai_status"]
            ]
        )
        data["answers"] = question.answers
        data["export_answer"] = question.export_answer
        return self.data(data)

    @staticmethod
    async def get_answers(qid: int):
        answers = list(
            await pw_db.execute(
                NewAnswer.select(
                    NewAnswer,
                    NewAdminUser.name.alias("name"),
                )
                .join(NewAdminUser, JOIN.LEFT_OUTER, on=NewAdminUser.id == NewAnswer.uid)
                .where(NewAnswer.qid == qid)
                .order_by(NewAnswer.updated_utc.desc())
                .dicts()
            )
        )
        for answer in answers:
            answer["name"] = answer["name"] or f"User_{answer.uid}"
        return answers


@route(r"/questions/(?P<question_id>\d+)/custom_fields/(?P<md5>\w+)")
class CustomFieldHandler(PermCheckHandler):
    async def delete(self, question_id, md5):
        """删除给定的自定义字段"""
        qid = int(question_id)
        await self.check_question_permission(qid)
        await delete_custom_field(self.current_user, qid, [md5])
        return self.data(None)


@route(r"/questions/(?P<question_id>\d+)/custom_fields")
class CustomFieldsHandler(PermCheckHandler):
    @use_kwargs({"md5_list": fields.List(fields.Str(), required=True)}, location="json")
    async def delete(self, question_id, md5_list):
        """批量删除给定的自定义字段"""
        qid = int(question_id)
        await self.check_question_permission(qid)
        await delete_custom_field(self.current_user, qid, md5_list)
        return self.data(None)


@route(r"/question/(?P<question_id>\d+)/answer")
class AnswerHandler(PermCheckHandler):
    post_query_schema = {
        "save_data_only": fields.Int(load_default=0),
        "answer_migrate": fields.Int(load_default=0, data_key="migrate"),
        "is_export_answer": fields.Bool(load_default=False),
    }

    async def get(self, **kwargs):
        qid = int(kwargs["question_id"])
        await self.check_question_permission(qid)
        query = (
            NewAnswer.select(
                NewAnswer.id,
                NewAnswer.qid,
                NewAnswer.uid,
                NewAnswer.data,
                NewQuestion.data.alias("question_data"),
                NewQuestion.preset_answer,
                NewAnswer.created_utc,
                NewAnswer.updated_utc,
            )
            .join(NewQuestion, on=NewQuestion.id == NewAnswer.qid)
            .where(
                NewAnswer.qid == qid,
                NewAnswer.uid == self.current_user.id,
            )
            .order_by(NewAnswer.id.asc())
        )
        answer = await pw_db.first(query.dicts())
        return self.data(answer if answer else {})

    @use_kwargs(post_query_schema, location="query")
    @use_kwargs(
        {
            "skip_hook": fields.Bool(load_default=False),
            "answer": fields.Dict(load_default=None, data_key="data"),
        },
        location="json",
    )
    @Auth("browse")
    async def post(self, question_id, save_data_only, answer_migrate, is_export_answer, skip_hook, answer):
        qid = int(question_id)
        await self.check_question_permission(qid)
        if answer is None:
            return self.error(_("Empty data cannot be saved."), status_code=http.HTTPStatus.BAD_REQUEST)
        _file = await NewFile.find_by_qid(qid)

        lock_expired = random.randint(590, 610)
        lock = redis_lock.Lock(init_rdb(), QUESTION_POST_PIPE_KEY.format(qid=qid), expire=lock_expired)
        if not lock.acquire(blocking=False):
            await self.record_failed(_file)
            return self.error("提交答案过于频繁, 请稍后重试", status_code=http.HTTPStatus.BAD_REQUEST)
        try:
            question = await self.save_answer_by_qid(
                qid, _file, answer, is_export_answer, answer_migrate, save_data_only
            )
        except CustomError as exp:
            init_rdb().delete(f"lock:{QUESTION_POST_PIPE_KEY.format(qid=qid)}")
            return self.error(str(exp), status_code=http.HTTPStatus.BAD_REQUEST)
        if question is None:
            init_rdb().delete(f"lock:{QUESTION_POST_PIPE_KEY.format(qid=qid)}")
            return self.data({})
        # NOTE: stop support for model auto update
        # await update_model_for_question(qid)
        await question.set_answer()
        question_post_pipe_task.delay(qid, _file.id, _file.meta_info, skip_hook)

        await post_pipe_after_api(_file.id, qid, HistoryAction.SUBMIT_ANSWER.value)
        await self.record_success(_file)
        return self.data({})

    async def save_answer_by_qid(self, qid, file, answer, is_export_answer, answer_migrate, save_data_only):
        # update export_answer for sse
        if is_export_answer:
            await NewSpecialAnswer.update_or_create(qid, NewSpecialAnswer.ANSWER_TYPE_EXPORT, answer)
            return None

        run_predict = config.get_config("web.preset_answer") or False
        question = await NewQuestion.find_by_id(qid)
        if answer_migrate and run_predict:
            await predict_answer(question)

        answer["userAnswer"]["items"] = [i for i in answer["userAnswer"]["items"] if i and isinstance(i, dict)]

        # 保存答案之前,就对答案能否满足answer_converter里的要求进行检查
        if get_config("web.check_before_submit"):
            mold = await NewMold.find_by_id(question.mold)
            workshop = get_answer_workshop(mold.name)
            workshop.check_before_submit(answer)

        if save_data_only == 1:  # 保存草稿
            ret, msg = await self.save_draft_answer(question, self.current_user.id, answer)
            if not ret:
                raise CustomError(msg)
            await self.record_success(file)
            await question.set_answer()
            return None

        ret, msg = await self.save_answer(question, self.current_user.id, answer)
        if not ret:
            raise CustomError(msg)
        return question

    async def record_success(self, file):
        if get_config("client.name") == "nafmii":
            await NewHistory.save_operation_history(
                None,
                self.current_user.id,
                HistoryAction.NAFMII_DEFAULT.value,
                self.current_user.name,
                meta=None,
                nafmii=self.get_nafmii_event(
                    status=NafmiiEventStatus.SUCCEED.value,
                    type=NafmiiEventType.ADD.value,
                    menu="识别文件管理",
                    subject="要素提取答案",
                    content=f"标注{file.id}成功",
                ),
            )

    async def record_failed(self, file):
        user = self.current_user
        await NewHistory.save_operation_history(
            None,
            action=HistoryAction.NAFMII_DEFAULT,
            user_name=user.name,
            meta=None,
            uid=user.id,
            nafmii=self.get_nafmii_event(
                status=NafmiiEventStatus.FAILED.value,
                type=NafmiiEventType.MODIFY.value,
                menu="识别文件管理",
                subject="要素提取答案",
                content=f"标注{file.id}失败",
            ),
        )

    async def exists_user_answer(self, qid, uid):
        count = await pw_db.count(
            NewAnswer.select().where(
                NewAnswer.qid == qid, NewAnswer.uid == uid, NewAnswer.status != AnswerStatus.UNFINISHED.value
            )
        )
        return count > 0

    async def get_answered_user(self, qid) -> list[tuple[int, int]]:
        answered_user = await pw_db.execute(
            NewAnswer.select(NewAnswer.uid, NewAnswer.standard)
            .where(NewAnswer.qid == qid, NewAnswer.status != AnswerStatus.UNFINISHED.value)
            .tuples()
        )
        return answered_user

    async def save_answer(self, question, uid, answer):
        qid = question.id
        health = question.health
        status = question.status
        modify_answer = await self.exists_user_answer(qid, uid)

        logging.info(f"(uid:qid) health,status,modify_answer: ({uid}:{qid}) {health},{status},{modify_answer}")
        standard = 0

        # 答题次数不受限制
        if get_config("web.mode_unlimited_answers"):
            status = QuestionStatus.FINISH.value
            answer_type = AnswerType.USER_DO.value
            await self._save_answer(question, uid, standard, answer_type, answer, status, health)
            return True, ""
        if not modify_answer and health < 1:
            return False, _("The number of label has reached the upper limit.")

        if status in (QuestionStatus.TODO.value, QuestionStatus.DOING.value):
            if not modify_answer:
                health -= 1
            status = QuestionStatus.DOING.value
            if health <= 0:
                status = QuestionStatus.FINISH.value
            answer_type = AnswerType.USER_DO.value
        elif status == QuestionStatus.FINISH.value:
            answer_type = AnswerType.ADMIN_DO_1.value
        elif status in (
            QuestionStatus.VERIFY.value,
            QuestionStatus.DISACCORD.value,
            QuestionStatus.STANDARD_CONFIRMED.value,
        ):
            if not await self.has_question_permission(qid):
                logging.error("to save answer for `verify` or `disaccord`, user must be admin")
                return (
                    False,
                    _("Answers could not added when question's status under already feedback or compare finished."),
                )

            answered_user = await self.get_answered_user(qid)
            if (uid, 0) in answered_user:
                return False, _("Standard answers could not be pointed by answered administrator.")

            if status == QuestionStatus.VERIFY.value:
                answer_type = AnswerType.ADMIN_VERIFY.value
            else:
                answer_type = AnswerType.ADMIN_JUDGE.value
            status = QuestionStatus.FINISH.value
            health = 0
            standard = 1
        elif status == QuestionStatus.ACCORDANCE.value:
            if not await self.has_question_permission(qid):
                logging.error("to save answer for `accord`, user must be admin")
                return False, _("No more answers can be added to which questions completed.")

            answered_user = await self.get_answered_user(qid)
            if (uid, 0) in answered_user:
                return False, _("Standard answers could not be pointed by answered administrator.")

            status = QuestionStatus.FINISH.value
            standard = 1
            answer_type = AnswerType.ADMIN_DO_2.value
        else:
            return False, _("Undefined question status.")

        await self._save_answer(question, uid, standard, answer_type, answer, status, health)

        return True, ""

    @peewee_transaction_wrapper
    async def _save_answer(self, question, uid, standard, answer_type, answer, status, health):
        save_event_log.delay(
            self.current_user.id, self.current_user.name, answer_type_to_history_action_type(answer_type), question.id
        )
        current_answer = await NewAnswer.find_by_kwargs(qid=question.id, uid=self.current_user.id)
        if not current_answer:
            current_answer = await NewAnswer.create(
                **{"qid": question.id, "uid": uid, "data": answer, "standard": standard, "answer_type": answer_type}
            )
        else:
            # 合并已有自定义字段+新增or修改的自定义字段
            current_answer_items = {
                gen_key_md5(i): i for i in NewQuestion.answer_items(current_answer.data, "custom_field")
            }
            for item in answer.setdefault("custom_field", {"version": "2.2", "items": []}).setdefault("items", []):
                current_answer_items[gen_key_md5(item)] = item
            answer["custom_field"]["items"] = list(current_answer_items.values())
            await current_answer.update_(data=answer, status=AnswerStatus.VALID)

        if standard == 1:  # 如果当前答案被设置为标准答案,需要确保其他答案都不是标准答案
            await pw_db.execute(NewAnswer.update(standard=0).where(NewAnswer.qid == question.id, NewAnswer.uid != uid))

        if answer_type in (AnswerType.ADMIN_JUDGE.value, AnswerType.ADMIN_VERIFY.value):
            await NewAdminOp.create(
                **{"uid": uid, "qid": question.id, "op_type": answer_type, "answer": current_answer.id}
            )

        logging.info(f"(uid:qid) update status=>{uid} {question.id} {status}")

        await question.update_(health=health, status=status, diff_detail=None)

        await self.update_mark_progress(question)

    @staticmethod
    async def update_mark_progress(question):
        try:
            question_progress = QuestionProgress(question.id)
            await question_progress.update_progress()
        except Exception as exp:
            logging.error(f"update file progress exception: {question.id}")
            logging.exception(exp)

        await NewQuestionService.update_markers(question)

    @peewee_transaction_wrapper
    async def save_draft_answer(self, question, uid, answer):
        """答题中保存答题数据，在实际提交前不算答题完毕，但可以通过这些数据恢复上次离开时的答题进度"""
        if question.status not in (QuestionStatus.TODO.value, QuestionStatus.DOING.value):
            return False, _("The question is not under the answer status therefore answers could not be saved.")

        if not (get_config("web.mode_unlimited_answers")) and question.health < 1:
            return False, _("The number of label has reached the upper limit.")

        current_answer = await NewAnswer.find_by_kwargs(qid=question.id, uid=self.current_user.id)
        if not current_answer:
            await NewAnswer.create(
                **{"qid": question.id, "uid": uid, "data": answer, "status": AnswerStatus.UNFINISHED}
            )
        else:
            # 合并已有自定义字段+新增or修改的自定义字段
            current_answer_items = {
                gen_key_md5(i): i for i in NewQuestion.answer_items(current_answer.data, "custom_field")
            }
            for item in answer.setdefault("custom_field", {"version": "2.2", "items": []}).setdefault("items", []):
                current_answer_items[gen_key_md5(item)] = item
            answer["custom_field"]["items"] = list(current_answer_items.values())
            await current_answer.update_(data=answer, status=AnswerStatus.UNFINISHED)

        await self.update_mark_progress(question)
        await question.update_(status=QuestionStatus.DOING)
        return True, ""


@route(r"/question/(?P<question_id>\d+)/confirm")
class ConfirmInfoHandler(PermCheckHandler):
    @Auth(["remark"])
    async def post(self, **kwargs):
        qid = kwargs["question_id"]
        await self.check_question_permission(qid, mode="write")
        data = self.get_json_body()
        answer = data.get("data", None)
        await NewQuestion.update_by_pk(qid, preset_answer=answer, confirmed_answer=answer)

        _file = await NewFile.find_by_qid(qid)
        await process_file(_file, force_predict=True)

        return self.data({})


@route(r"/question/(\d+)/verify")
class VerifyHandler(BaseHandler):
    @Auth("browse")
    async def post(self, *args):
        (qid,) = args
        await NewQuestion.update_by_pk(qid, status=QuestionStatus.VERIFY)

        return self.data({})


# 管理员确认反馈接口.
# 在反馈处理页面, 管理员同意用户最初的反馈, 或者管理员对该问题也做了反馈, 则视为管理员确认了反馈.
# 在导出答案的时候, 题目确认反馈后视作答题完成.
@route(r"/question/(\d+)/confirm_verify")
class ConfirmVerifyHandler(BaseHandler):
    async def _check_param(self, qid):
        question = await NewQuestion.find_by_id(qid)
        status = question.status if question else None
        if status is None or int(status) != QuestionStatus.VERIFY.value:
            logging.error(f"question not in `verify` state: {status}")
            return False, _("The status is not to be reviewed and feedback of the question.")
        return True, ""

    @Auth("manage_prj")
    async def post(self, *args):
        (qid,) = args
        ret, msg = await self._check_param(qid)
        if not ret:
            return self.error(msg)

        await self.set_question_status(self.current_user.id, qid, QuestionStatus.VERIFY_CONFIRMED.value)

        return self.data({})

    @peewee_transaction_wrapper
    async def set_question_status(self, admin_uid, qid, status):
        await NewAdminOp.create(**{"uid": admin_uid, "qid": qid, "op_type": AnswerType.ADMIN_VERIFY.value})
        await NewQuestion.update_by_pk(qid, status=status)


@route(r"/question/report/(\d+)")
class ReportHandler(BaseHandler):
    @Auth("browse")
    async def get(self, *args):
        (q_status,) = args
        if int(q_status) == 0:
            result = {}
            for status_idx in QuestionStatus.member_values():
                count = await NewQuestion.count(NewQuestion.status == status_idx)
                result[status_idx] = count
            self.data({"query": "all status", "result": result})
        else:
            count = await NewQuestion.count(NewQuestion.status == q_status)

            self.data({"query": q_status, "result": count})


def validate_model_name(value):
    if not value:
        return value

    llm_list = get_llm_list()
    llm_names = [llm["model"] for llm in llm_list]

    if value not in llm_names:
        raise ValidationError(f"大模型必须是以下选项之一: {llm_names}")

    return value


# TODO: 更严格的校验规则
mold_data_schema = fields.Nested(
    {
        "schemas": fields.List(
            fields.Dict(validate=lambda x: isinstance(x.get("name"), str) and isinstance(x.get("schema"), dict))
        ),
        "schema_types": fields.List(fields.Dict(), load_default=[]),
    }
)


@route(r"/mold")
class MoldHandler(BaseHandler):
    get_kwargs = {
        "mid": fields.Int(load_default=None, data_key="id"),
        "name": fields.Str(load_default=""),
        "is_master": fields.Bool(load_default=False),
        "includes": fields.DelimitedList(fields.Str(), load_default=list, data_key="fields"),
        "order_by": fields.Str(load_default="-created_utc"),
        **AsyncPagination.web_args,
    }
    post_kwargs = {
        "name": fields.Str(validate=field_validate.Length(min=1, max=128)),
        "data": mold_data_schema,
        "mold_type": fields.Int(
            load_default=MoldType.COMPLEX.value, validate=field_validate.OneOf(choices=MoldType.member_values())
        ),
        "model_name": fields.Str(load_default=None, validate=validate_model_name),
    }

    @Auth("browse")
    @use_kwargs(get_kwargs, location="query")
    async def get(self, mid, name, is_master, includes, order_by, page, size):
        cond = TRUE
        if not self.current_user.is_admin:
            cond &= MoldWithFK.public | (MoldWithFK.user == self.current_user.id)
        if name:
            cond &= MoldWithFK.name.contains(name)
        if is_master:
            cond &= MoldWithFK.master.is_null()  # Mold.master为空的,即为master_mold
        if mid is not None:
            cond &= MoldWithFK.id == mid

        includes = list(set(includes) | {"uid"}) if includes else []

        selects = [f for f in (getattr(MoldWithFK, i, None) for i in includes) if f] if includes else []
        query = MoldWithFK.select(*selects).where(cond).order_by(getattr(MoldWithFK, order_by), MoldWithFK.id.desc())
        data = await AsyncPagination(query, page, size).data(
            NewAdminUser.select(NewAdminUser.id, NewAdminUser.name, include_deleted=True),
            fields=includes,
            dump_func=self.packer,
        )

        if self.trigger_source == "auto":
            return self.data(data)
        if any([name, is_master, mid]):
            subject = "算法模型列表"
            content = "查询算法模型列表成功"
        else:
            subject = "算法模型列表页面"
            content = "查看算法模型列表页面成功"
        await NewHistory.save_operation_history(
            None,
            action=HistoryAction.NAFMII_DEFAULT,
            user_name=self.current_user.name,
            meta=None,
            uid=self.current_user.id,
            nafmii=self.get_nafmii_event(
                status=NafmiiEventStatus.SUCCEED.value,
                type=NafmiiEventType.VIEW.value,
                menu="算法模型管理",
                subject=subject,
                content=content,
            ),
        )
        return self.data(data)

    @staticmethod
    def packer(row, fields):
        readonly_mold_list = config.get_config("web.readonly_mold_list") or []
        try:
            ret = row.to_dict()
        except AssertionError:
            # user 可能不存在
            row.user = None
            ret = row.to_dict()
        ret["readonly"] = row.name in readonly_mold_list or row.id in readonly_mold_list
        ret["user_name"] = row.user.name if ret["user"] else None
        ret.pop("user", None)
        return {k: v for k, v in ret.items() if k in fields} if fields else ret

    @Auth("browse")
    @use_kwargs(post_kwargs, location="json")
    async def post(self, data, name, mold_type, model_name):
        mold = await NewMoldService.create(data, name, mold_type, self.current_user.id, model_name)
        await NewHistory.save_operation_history(
            mold.id,
            self.current_user.id,
            HistoryAction.CREATE_MOLD.value,
            self.current_user.name,
            meta=data,
            nafmii=self.get_nafmii_event(
                status=NafmiiEventStatus.SUCCEED.value,
                type=NafmiiEventType.ADD.value,
                menu="算法模型管理",
                subject="算法模型",
                content=f"新增算法模型{name}成功",
            ),
        )
        return self.data(mold.to_dict(recurse=False))


@route(r"/mold/(\d+)/intro_words")
class MoldIntroHandler(BaseHandler):
    @Auth("browse")
    async def get(self, mid):
        mold = await NewMold.find_by_id(mid)
        if not mold:
            return self.error(message=_("Item Not Found"), status_code=404)
        schema = Schema(mold.data)
        intro = {}
        for _path, item in schema.iter_schema_attr(need_detail=True):
            intro["_".join(_path)] = item.get("words")
        # for schema in mold.data["schemas"]:
        #     schema_intro = {}
        #     for key, col in schema["schema"].items():
        #         schema_intro[key] = col.get("words")
        #     intro[schema["name"]] = schema_intro
        return self.data(intro)


@route(r"/mold/(?P<mid>\d+)")
class MoldIdHandler(PermCheckHandler):
    args_schema = {
        "name": fields.String(validate=field_validate.Length(min=1, max=128), required=True),
        "data": mold_data_schema,
        "predictors": fields.List(fields.Dict, required=True),
        "checksum": fields.String(),
        "created_utc": fields.Integer(),
        "updated_utc": fields.Integer(),
        "id": fields.Integer(),
        "mold_type": fields.Integer(),
        "meta": fields.Dict(),
        "model_name": fields.Str(load_default=None, validate=validate_model_name),
    }

    @Auth("browse")
    async def get(self, mid):
        mold = await NewMold.find_by_id(mid)
        if mold is None:
            return self.error(message=_("Item Not Found"), status_code=404)
        if get_config("web.model_manage", True) and not mold.predictors:
            from remarkable.predictor.helpers import create_predictor_prophet

            try:
                prophet = await asyncio.get_event_loop().run_in_executor(None, create_predictor_prophet, mold)
                mold.predictors = prophet.predictor_options
            except Exception as exp:
                logger.warning(f"Exception when load mold({mold.id}) predictors: {exp}")
        if get_config("client.name") == "nafmii" and self.trigger_source != "auto":
            await NewHistory.save_operation_history(
                None,
                action=HistoryAction.NAFMII_DEFAULT,
                user_name=self.current_user.name,
                meta=None,
                uid=self.current_user.id,
                nafmii=self.get_nafmii_event(
                    status=NafmiiEventStatus.SUCCEED.value,
                    type=NafmiiEventType.VIEW.value,
                    menu="算法模型管理",
                    subject="算法模型详情页面",
                    content=f"查看{mold.name}详情页面成功",
                ),
            )
        return self.data(mold.to_dict())

    @Auth("browse")
    @use_kwargs(args_schema, location="json")
    async def put(self, mid, **kwargs):
        mold = await NewMold.find_by_id(mid)
        if not mold:
            return self.error(message=_("Item Not Found"), status_code=http.HTTPStatus.NOT_FOUND)
        await self.new_check_mold_permission(mold)
        mold_data = MoldDataSchema.model_validate(kwargs.get("data"))
        studio_app_id = mold.studio_app_id
        if mold_data.need_llm_extract:
            if not kwargs.get("model_name"):
                raise InvalidMoldError("请选择大模型")
            if not studio_app_id:
                schema_app = await create_app(mold.name, kwargs.get("model_name"), {"schemas": {}})
                studio_app_id = schema_app["id"]
        if studio_app_id:
            await update_app(
                kwargs.get("name"),
                kwargs.get("model_name"),
                mold_data,
                studio_app_id,
            )
        mold = await NewMoldService.update(mold, studio_app_id=studio_app_id, mold_type=mold_data.mold_type, **kwargs)
        await NewHistory.save_operation_history(
            mold.id,
            self.current_user.id,
            HistoryAction.MODIFY_MOLD.value,
            self.current_user.name,
            meta=kwargs,
        )
        if get_config("client.name") == "nafmii":
            await NewHistory.save_operation_history(
                None,
                action=HistoryAction.NAFMII_DEFAULT,
                user_name=self.current_user.name,
                meta=None,
                uid=self.current_user.id,
                nafmii=self.get_nafmii_event(
                    status=NafmiiEventStatus.SUCCEED.value,
                    type=NafmiiEventType.MODIFY.value,
                    menu="算法模型管理",
                    subject="算法模型详情页面",
                    content=f"修改{mold.name}成功",
                ),
            )

        return self.data(mold.to_dict())

    @Auth("browse")
    async def delete(self, mid):
        mold = await MoldWithFK.get_by_id(mid, QuestionWithFK.select(QuestionWithFK.mold))
        rule_exists = await pw_db.exists(NewAuditRule.select().where(NewAuditRule.schema_id == mid))
        if not mold:
            return self.error(message=_("Item Not Found"), status_code=404)
        related_tree = await NewFileTreeService.get_by_default_molds([mold.id])
        if mold.questions or related_tree or rule_exists:
            if get_config("client.name") == ClientName.cmfchina:
                messages = []
                if rule_exists:
                    messages.append("审核规则")
                if mold.questions or related_tree:
                    messages.append("项目和文档")
                return self.error(f"该场景已关联{'、'.join(messages)}，请解除关联后再进行删除", status_code=400)
            elif get_config("client.name") == "nafmii":
                return self.error(_("算法模型正在使用中,不能被删除"), status_code=400)
            return self.error(_("Schema is in use, cannot be deleted"), status_code=400)
        if get_config("client.name") == "ecitic-tg":
            if await pw_db.exists(EciticTemplate.select().where(EciticTemplate.mold == mid)):
                return self.error(_("Schema is in use at Template, cannot be deleted"), status_code=400)
        await pw_db.execute(CmfMoldModelRef.delete().where(CmfMoldModelRef.mold == mold))
        if mold.studio_app_id:
            await delete_app(mold.studio_app_id)
        await mold.soft_delete()
        await NewHistory.save_operation_history(
            int(mid),
            self.current_user.id,
            HistoryAction.DELETE_MOLD.value,
            self.current_user.name,
            {"mold_id": int(mid)},
        )
        if get_config("client.name") == "nafmii":
            await NewHistory.save_operation_history(
                None,
                action=HistoryAction.NAFMII_DEFAULT,
                user_name=self.current_user.name,
                meta=None,
                uid=self.current_user.id,
                nafmii=self.get_nafmii_event(
                    status=NafmiiEventStatus.SUCCEED.value,
                    type=NafmiiEventType.DELETE.value,
                    menu="算法模型管理",
                    subject="算法模型",
                    content=f"删除算法模型-{mold.name}成功",
                ),
            )

        return self.data(None)


@route(r"/training_data/(?P<task_id>\d+)")
class MoldExportHandler(BaseHandler):
    get_args = {"export_action": fields.Int(validate=_validate_export_action)}

    @Auth("browse")
    @use_kwargs(get_args, location="query")
    async def get(self, task_id, export_action=HistoryAction.EXPORT_TRAINING_DATA):
        """zip文件下载"""
        if not (config.get_config("client.export_label_data") or config.get_config("client.export_answer_csv")):
            raise CustomError(_("don't support export_label_data"))
        from remarkable.data.services.training_data_service import download_training_zip

        data, filename = await download_training_zip(task_id)
        if get_config("client.name") == "nafmii":
            name = await pw_db.scalar(
                NewMold.select(NewMold.name)
                .join(NewTrainingData, on=(NewMold.id == NewTrainingData.mold))
                .where(NewTrainingData.id == task_id)
            )
            filename = f"{name}-提取结果导出-{datetime.now().strftime('%Y%m%d%H%M')}.zip"

            await NewHistory.save_operation_history(
                None,
                action=HistoryAction.NAFMII_DEFAULT,
                user_name=self.current_user.name,
                meta=None,
                uid=self.current_user.id,
                nafmii=self.get_nafmii_event(
                    status=NafmiiEventStatus.SUCCEED.value,
                    type=NafmiiEventType.EXPORT.value,
                    menu="算法模型管理",
                    subject="提取结果记录",
                    content=f"下载{name}提取结果记录{task_id}成功",
                ),
            )
        # 操作记录
        await NewHistory.save_operation_history(
            int(task_id),
            self.current_user.id,
            export_action,
            self.current_user.name,
            {"task_id": task_id},
        )

        return await self.export(data, filename)

    @Auth("manage_mold")
    @use_kwargs(get_args, location="query")
    @peewee_transaction_wrapper
    async def delete(self, task_id, export_action=HistoryAction.DELETE_TRAINING_DATA):
        if not (config.get_config("client.export_label_data") or config.get_config("client.export_answer_csv")):
            raise CustomError(_("don't support export_label_data"))
        from remarkable.data.services.training_data_service import delete_training_task

        name = await pw_db.scalar(
            NewMold.select(NewMold.name)
            .join(NewTrainingData, on=(NewMold.id == NewTrainingData.mold))
            .where(NewTrainingData.id == task_id)
        )
        await delete_training_task(task_id)
        # 操作记录
        await NewHistory.save_operation_history(
            int(task_id),
            self.current_user.id,
            export_action,
            self.current_user.name,
            {"task_id": int(task_id)},
        )

        if get_config("client.name") == "nafmii":
            await NewHistory.save_operation_history(
                None,
                action=HistoryAction.NAFMII_DEFAULT,
                user_name=self.current_user.name,
                meta=None,
                uid=self.current_user.id,
                nafmii=self.get_nafmii_event(
                    status=NafmiiEventStatus.SUCCEED.value,
                    type=NafmiiEventType.DELETE.value,
                    menu="算法模型管理",
                    subject="提取结果记录",
                    content=f"删除{name}提取结果记录{task_id}成功",
                ),
            )

        return self.data(None)


@route(r"/mold_cata/(\d+)")
class MoldCataHandler(PermCheckHandler):
    get_args = {
        "export_type": fields.Str(load_default="json", validate=_validate_export_type),
        "export_action": fields.Int(load_default=HistoryAction.CREATE_TRAINING_DATA, validate=_validate_export_action),
    }

    @Auth("browse")
    @use_kwargs(get_args, location="query")
    async def get(self, schema_id, export_type, export_action):
        schema_id = int(schema_id)
        # 校验mold
        await self.check_mold_permission(schema_id)
        trees = await NewFileTree.get_all_trees(self.current_user)
        root = trees[0]

        visible_files = await self.get_visible_files(schema_id, export_type, export_action)
        visible_file_tree_ids = [file.tree_id for file in visible_files]
        visible_trees = await self.get_visible_trees(trees, visible_files)

        def show_tree(tree: dict, valid_trees: set[int]):
            for sub_tree in tree["children"]:
                sub_tree["show"] = sub_tree["id"] in valid_trees  # 该文件夹或其子文件夹下有目标file
                sub_tree["show_file"] = sub_tree["id"] in visible_file_tree_ids  # 该文件夹下有目标file
                show_tree(sub_tree, valid_trees)

        show_tree(root, visible_trees)
        branch_files_details = await self.get_files_details(visible_files)
        self.insert_to_branch(root, branch_files_details)
        return self.data(root)

    @staticmethod
    async def get_visible_files(mold_id: int, export_type: str, export_action: int) -> peewee_async.AsyncQueryWrapper:
        files = []
        if export_action == HistoryAction.CREATE_TRAINING_DATA:
            # 跟后面实际导出时使用同一个方法,避免两边口径不一致
            data_items = await fetch_all_answers(mold_id, export_type=export_type, only_fid=True)
            files = await pw_db.execute(NewFile.select().where(NewFile.id.in_([x["fid"] for x in data_items])))
        elif export_action in (HistoryAction.TESTING_SCHEMA, HistoryAction.TRAINING_SCHEMA):
            files = await NewFile.find_by_mold_labeled(mold_id)
        elif export_action == HistoryAction.CREATE_TABLE_OF_CONTENT:
            files = await NewFile.find_by_mold_parsed(mold_id)
        elif export_action == HistoryAction.CREATE_INSPECT_RESULT:
            files = await NewFile.find_by_mold_inspected(mold_id)
        elif export_action == HistoryAction.DIFF_MODEL:
            enable_vid = await NewModelVersion.get_enabled_version(mold_id, only_developed=True)
            if not enable_vid:
                raise CustomError(_("No enabled develop model version!"))
            files = await NewFile.find_by_mold_with_model_answer(mold_id, enable_vid)

        return files

    async def get_visible_trees(self, trees: list[dict], files: list[NewFile]) -> set[int]:
        visible_trees = set()
        for file in files:
            nodes = self.build_branch_nodes(trees, file.tree_id)
            for node in nodes:
                visible_trees.add(node["id"])

        return visible_trees

    @staticmethod
    def build_branch_nodes(tree_data, leaf_id):
        nodes = []
        current_node = next((i for i in tree_data if i["id"] == leaf_id), None)
        while current_node:
            nodes.insert(0, current_node)
            parent_id = current_node["ptree_id"]
            current_node = next((i for i in tree_data if i["id"] == parent_id), None)
            is_root = current_node["id"] == 0
            if is_root:
                break

        return nodes

    @staticmethod
    async def get_files_details(files):
        """
        获取节点树下的所有文件信息
        """
        files_dict = defaultdict(list)
        for file in files:
            file_info = {"file_id": file.id, "file_tree_id": file.tree_id, "file_name": file.name}
            files_dict[file.tree_id].append(file_info)
        return files_dict

    @staticmethod
    def insert_to_branch(root, files_details):
        def insert(tree):
            for sub_tree in tree["children"]:
                sub_tree["file_details"] = []
                if sub_tree["id"] in files_details:
                    sub_tree["file_details"] = files_details[sub_tree["id"]]
                if sub_tree["children"]:
                    insert(sub_tree)

        insert(root)


@route(r"/model_class/(\d+)")
class ModelClassHandler(DbQueryHandler):
    @Auth("browse")
    async def get(self, mold_id):
        """获取模型类别"""
        mold = await NewMold.find_by_id(mold_id)
        if not mold:
            return self.error(message="mold does not existed", status_code=400)
        data = {name: model_class.model_intro for name, model_class in model_config_map.items()}
        model_config = get_config("available_models") or {}
        if model_config:
            data = {k: v for k, v in data.items() if k in model_config}
        utils_module_from_code = import_module("remarkable.predictor")
        try:
            utils_module_from_code.load_prophet_config(mold)
        except ModuleNotFoundError:
            # 如果没有配置prophet，则不显示config_in_code
            data = {k: v for k, v in data.items() if k != "config_in_code"}
        return self.data(data)


@route(r"/training_data")
class MoldExportTaskHandler(DbQueryHandler):
    get_args = {
        "schema_id": fields.Int(required=True, validate=lambda x: x > 0),
        "export_type": fields.Str(load_default="json", validate=_validate_export_type),
        "export_action": fields.Int(load_default=HistoryAction.CREATE_TRAINING_DATA, validate=_validate_export_action),
        "status": fields.Int(load_default=None, validate=field_validate.OneOf(ExportStatus.member_values())),
        "page": fields.Int(load_default=1),
        "size": fields.Int(load_default=20),
    }

    @Auth("browse")
    @use_kwargs(get_args, location="query")
    async def get(self, schema_id, export_type, export_action, status, page, size):
        from remarkable.data.services.training_data_service import get_training_tasks

        data = await get_training_tasks(schema_id, export_type, export_action, status, page, size)
        if get_config("client.name") == "nafmii":
            name = await NewMold.get_name_by_id(schema_id)
            await NewHistory.save_operation_history(
                None,
                action=HistoryAction.NAFMII_DEFAULT,
                user_name=self.current_user.name,
                meta=None,
                uid=self.current_user.id,
                nafmii=self.get_nafmii_event(
                    status=NafmiiEventStatus.SUCCEED.value,
                    type=NafmiiEventType.VIEW.value,
                    menu="算法模型管理",
                    subject="导出提取结果记录列表",
                    content=f"查看{name}导出提取结果成功",
                ),
            )

        return self.data(data)

    post_args = {
        "schema_id": fields.Int(required=True, validate=lambda x: x > 0),
        "export_type": fields.Str(load_default="json", validate=_validate_export_type),
        "tree_l": fields.List(fields.Int(), load_default=[]),
        "files_ids": fields.List(fields.Int(), load_default=[]),
        "export_action": fields.Int(load_default=HistoryAction.CREATE_TRAINING_DATA, validate=_validate_export_action),
    }

    @Auth("manage_mold")
    @use_kwargs(post_args, location="json")
    async def post(self, schema_id, export_type, tree_l, files_ids, export_action):
        from remarkable.data.services.training_data_service import mold_export_task

        # https://gitpd.paodingai.com/cheftin/docs_scriber/-/issues/1181
        mold_name = await NewMold.get_name_by_id(schema_id)
        if mold_name in (config.get_config("customer_settings.ignore_insert_schema") or []):
            raise CustomError(msg="暂不支持导出申请表提取结果", resp_status_code=400)
        training_data = await mold_export_task(schema_id, export_type, tree_l, files_ids, export_action)
        # 操作记录
        await NewHistory.save_operation_history(
            training_data.id,
            self.current_user.id,
            export_action,
            self.current_user.name,
            {"task_id": training_data.id},
        )

        if get_config("client.name") == "nafmii":
            await NewHistory.save_operation_history(
                None,
                action=HistoryAction.NAFMII_DEFAULT,
                user_name=self.current_user.name,
                meta=None,
                uid=self.current_user.id,
                nafmii=self.get_nafmii_event(
                    status=NafmiiEventStatus.SUCCEED.value,
                    type=NafmiiEventType.ADD.value,
                    menu="算法模型管理",
                    subject="提取结果记录",
                    content=f"新增{mold_name}提取结果记录{training_data.id}成功",
                ),
            )

        return self.data(training_data.to_dict())


@route(r"/model_testing")
class ModelTestingHandler(DbQueryHandler):
    @Auth("manage_mold")
    @use_kwargs(
        {
            **vid_update_args,
            "files_ids": fields.List(fields.Int(), required=True),
            "export_excel": manage_model_args["export_excel"],
            "diff_model": fields.Bool(load_default=False),
        },
        location="json",
    )
    async def post(self, vid, update, files_ids, export_excel, diff_model):
        """
        测试模型
        """
        if not (config.get_config("web.model_manage")):
            return self.error(message=_("don't support model_manage"), status_code=400)
        if config.get_config("prompter.mode") != "v2":
            return self.error(message=_("unsupported mode version"), status_code=400)
        model_version = await NewModelVersion.find_by_id(vid)
        if not model_version:
            return self.error(message=_("Item Not Found"), status_code=404)
        schema_id, status, _type = model_version.mold, model_version.status, model_version.model_type

        files = await pw_db.execute(NewFile.select().where(NewFile.id.in_(files_ids)))
        files_ids = [file.id for file in files]
        tree_s = [file.tree_id for file in files]

        if not diff_model and len(files) < 3:  # 比较模型版本差异时不限制
            return self.error(message="测试样本数量最少为 3", status_code=400)

        data = {}
        if diff_model:
            old_version = await NewModelVersion.get_last_with_model_answer(schema_id, vid)
            model_version = await NewModelVersion.find_by_id(vid)
            data["old_version_name"] = old_version.name
            data["version_name"] = model_version.name

        # 生成测试记录
        sql_params = {
            "type": _type,
            "test": AccuracyTest.DIFF_MODEL.value if diff_model else AccuracyTest.TEST.value,
            "data": data,
            "mold": schema_id,
            "vid": vid,
            "dirs": tree_s,
            "files": files_ids,
        }
        acc_record = await NewAccuracyRecord.create(**sql_params)
        if status == PredictorTrainingStatus.DONE.value:
            # 生成preset_answer，统计准确率
            preset_path = None
            if update != 0:  # 更新测试样本的预测答案
                preset_path = os.path.join(
                    get_config("training_cache_dir"), str(schema_id), str(vid), "preset", str(generate_timestamp())
                )
                if not os.path.exists(preset_path):
                    os.makedirs(preset_path)
            preset_answers_for_mold_online.delay(
                schema_id,
                vid,
                preset_path=preset_path,
                save=AccuracyTest.DIFF_MODEL.value if diff_model else AccuracyTest.TEST.value,
                tree_s=tree_s,
                files_ids=files_ids,
                acid=acc_record.id,
                test_accuracy=True,
                export_excel=export_excel,
                diff_model=diff_model,
            )
        else:
            acc_record.status = AccuracyRecordStatus.FAILED.value
            await pw_db.update(acc_record, only=["status"])
            return self.error(message=_("unsupported mode type"), status_code=400)

        # 操作记录
        await NewHistory.save_operation_history(
            int(vid),
            self.current_user.id,
            HistoryAction.TESTING_SCHEMA.value,
            self.current_user.name,
            {"vid": int(vid), "files_ids": files_ids, "diff_model": diff_model},
        )

        if get_config("client.name") == "nafmii":
            name = await NewMold.get_name_by_id(model_version.mold)
            await NewHistory.save_operation_history(
                None,
                action=HistoryAction.NAFMII_DEFAULT,
                user_name=self.current_user.name,
                meta=None,
                uid=self.current_user.id,
                nafmii=self.get_nafmii_event(
                    status=NafmiiEventStatus.SUCCEED.value,
                    type=NafmiiEventType.ADD.value,
                    menu="算法模型管理",
                    subject="准确率验证记录",
                    content=f"新增{name}准确率验证记录成功",
                ),
            )

        return self.data({"schema_id": schema_id, "vid": vid})


# 启用模型 + 停用模型
@route(r"/model_manage")
class ModelManHandler(DbQueryHandler):
    req_args = {
        "vid": fields.Int(required=True),
        "update": fields.Int(required=True),
        "enable": fields.Int(validate=field_validate.OneOf([0, 1]), load_default=1),
    }

    @Auth("manage_mold")
    @use_kwargs(req_args, location="json")
    async def post(self, vid, enable, update):
        if not config.get_config("web.model_manage"):
            return self.error(message=_("We don't support model management yet"), status_code=400)
        model_version = await NewModelVersion.find_by_id(vid)
        if not model_version:
            return self.error(message=_("The specified model version does not exist"), status_code=404)
        if model_version.status != PredictorTrainingStatus.DONE.value:
            return self.error(message=_("Model training in progress, please wait"))
        if enable == 1:  # 启用模型
            # https://mm.paodingai.com/cheftin/pl/gtdfkqb4tp8etkymhoifkdoi7c
            # https://gitpd.paodingai.com/cheftin/docs_scriber/-/issues/4987
            model_dir = Path(get_config("training_cache_dir")) / str(model_version.mold) / str(vid)
            if not all((model_dir / file).exists() for file in PROMPTER_MODEL_FILES):
                return self.error(message=_("The model files do not exist"), status_code=400)

            action = HistoryAction.ENABLE_MODEL.value
            if update != 0:  # 重新预测现有文档 初步+精确
                get_lock, lock = run_singleton_task(
                    preset_answers_for_mold_online,
                    model_version.mold,
                    vid,
                    lock_key=f"preset_answers_for_mold_online_{model_version.mold}_{vid}",
                    lock_expired=60,
                )
                if not get_lock:
                    return self.error(_("The model is predicting, please try again later"))
            await NewModelVersion.enable_model(vid)
        else:  # 停用模型
            model_version.enable = ModelEnableStatus.DISABLE.value
            await pw_db.update(model_version)
            action = HistoryAction.DISABLE_MODEL.value
        # 操作记录
        await NewHistory.save_operation_history(
            int(vid),
            self.current_user.id,
            action,
            self.current_user.name,
            {"vid": int(vid), "update": update},
        )

        if get_config("client.name") == "nafmii":
            name = await NewMold.get_name_by_id(model_version.mold)
            if enable == 1:
                content = f"启用{name}-{model_version.name}成功"
            else:
                content = f"停用{name}-{model_version.name}成功"
            await NewHistory.save_operation_history(
                None,
                action=HistoryAction.NAFMII_DEFAULT,
                user_name=self.current_user.name,
                meta=None,
                uid=self.current_user.id,
                nafmii=self.get_nafmii_event(
                    status=NafmiiEventStatus.SUCCEED.value,
                    type=NafmiiEventType.MODIFY.value,
                    menu="算法模型管理",
                    subject="模型版本状态",
                    content=content,
                ),
            )

        return self.data({"vid": vid})


@route(r"/model_training")
class ModelTrainingHandler(DbQueryHandler):
    @Auth("browse")
    @use_kwargs(AsyncPagination.web_args, location="query")
    @use_kwargs({"schema_id": fields.Int(required=True)}, location="query")
    async def get(self, page, size, schema_id):
        """
        模型版本列表
        """
        if not config.get_config("web.model_manage"):
            return self.error(message=_("don't support model management"), status_code=400)
        if config.get_config("prompter.mode") != "v2":
            return self.error(message=_("unsupported mode version"), status_code=400)

        cond = NewModelVersion.mold == schema_id
        cond &= NewModelVersion.model_type != ModelType.PROMPTER.value
        order_by = (NewModelVersion.model_type.desc(), NewModelVersion.id.desc())
        query = NewModelVersion.select().where(cond)
        if config.get_config("web.enable_llm_extract"):
            order_by = (NewModelVersion.enable.desc(), *order_by)
            query = query.limit(1)
        query = query.order_by(*order_by)
        data = await AsyncPagination(query, page=page, size=size).data()
        for item in data.get("items", []):
            item["created_time"] = time.strftime("%Y.%m.%d %H:%M:%S", time.localtime(item["created_utc"]))  # 训练时间
            item["file_count"] = len(item.get("files", []))  # 训练文件基数
            item["status"] = item["status"]
            item["enable"] = item["enable"]  # 启用状态
            cond = (NewAccuracyRecord.vid == item["id"]) & (NewAccuracyRecord.deleted_utc == 0)
            recent = await NewAccuracyRecord.get_first_one(cond, NewAccuracyRecord.created_utc.desc())
            item["precision"] = recent.data.get("total_percent") if recent and recent.data else None  # 最新准确率
            del item["files"]

        if get_config("client.name") == "nafmii":
            name = await NewMold.get_name_by_id(schema_id)
            await NewHistory.save_operation_history(
                None,
                action=HistoryAction.NAFMII_DEFAULT,
                user_name=self.current_user.name,
                meta=None,
                uid=self.current_user.id,
                nafmii=self.get_nafmii_event(
                    status=NafmiiEventStatus.SUCCEED.value,
                    type=NafmiiEventType.VIEW.value,
                    menu="算法模型管理",
                    subject="模型版本列表页",
                    content=f"查看{name}模型版本列表页成功",
                ),
            )

        return self.data(data)

    create_model_version = {
        "copy_from": fields.Int(load_default=None),
        "name": fields.String(required=True),
        "schema_id": fields.Int(required=True),
        "predictors": fields.List(fields.Dict(), load_default=[]),
    }

    @Auth("manage_mold")
    @use_kwargs(create_model_version, location="json")
    async def post(self, **kwargs):
        # 新建模型版本
        if not config.get_config("web.model_manage"):
            return self.error(message=_("don't support model_manage"), status_code=400)
        if config.get_config("prompter.mode") != "v2":
            return self.error(message=_("unsupported mode version"), status_code=400)
        # 校验mold
        schema_id = kwargs["schema_id"]
        mold = await NewMold.find_by_id(schema_id)
        if not mold:
            return self.error(message=f"schema: [ {schema_id} ] does not existed", status_code=400)
        copy_from_version_id = kwargs["copy_from"]
        old_model_version = None
        if copy_from_version_id:
            old_model_version = await NewModelVersion.find_by_id(copy_from_version_id)
            status = old_model_version.status
            train_dirs = old_model_version.dirs
            train_files = old_model_version.files
        else:
            status = PredictorTrainingStatus.CREATE.value
            train_dirs = []
            train_files = []
        try:
            current_model_version = await NewModelVersion.create(
                **{
                    "mold": schema_id,
                    "name": kwargs["name"],
                    "model_type": ModelType.PREDICT.value,
                    "status": status,
                    "dirs": train_dirs,
                    "files": train_files,
                    "enable": ModelEnableStatus.DISABLE.value,
                    "predictors": kwargs["predictors"],
                    "predictor_option": mold.predictor_option,
                },
            )
        except UniqueViolationError:
            return self.error(message="模型版本名称重复", status_code=400)
        if old_model_version and old_model_version.status == PredictorTrainingStatus.DONE.value:
            # 复制版本 若已有版本已经训练完成，则复制已有版本的模型
            training_cache_dir = Path(get_config("training_cache_dir"))
            old_version_model_dir = training_cache_dir / str(schema_id) / str(old_model_version.id)
            current_version_model_dir = training_cache_dir / str(schema_id) / str(current_model_version.id)
            for file_name in PREDICTOR_MODEL_FILES + PROMPTER_MODEL_FILES:
                copy_model_file(old_version_model_dir, current_version_model_dir, file_name)
        # 操作记录
        await NewHistory.save_operation_history(
            current_model_version.id,
            self.current_user.id,
            HistoryAction.CREATE_MODEL_VERSION.value,
            self.current_user.name,
            kwargs,
        )

        if get_config("client.name") == "nafmii":
            name = await NewMold.get_name_by_id(schema_id)
            await NewHistory.save_operation_history(
                None,
                action=HistoryAction.NAFMII_DEFAULT,
                user_name=self.current_user.name,
                meta=None,
                uid=self.current_user.id,
                nafmii=self.get_nafmii_event(
                    status=NafmiiEventStatus.SUCCEED.value,
                    type=NafmiiEventType.ADD.value,
                    menu="算法模型管理",
                    subject="模型版本",
                    content=f"新增{name}模型版本成功",
                ),
            )

        return self.data({"schema_id": schema_id})


@route(r"/model_training/(\d+)")
class ModelTrainingEachHandler(DbQueryHandler):
    model_train_args = {
        "tree_l": fields.List(fields.Int(), load_default=[]),
        "files_ids": fields.List(fields.Int(), load_default=[]),
    }

    @Auth("manage_mold")
    @use_kwargs(model_train_args, location="json")
    async def post(self, vid, **kwargs):
        # 训练模型
        model_version = await NewModelVersion.find_by_id(vid)
        if not model_version.predictors:
            return self.error(message="字段均未设置提取模式，不能训练", status_code=400)
        if model_version.status in (PredictorTrainingStatus.PREPARE.value, PredictorTrainingStatus.TRAINING.value):
            return self.error(message="模型正在训练中，不能重复训练", status_code=400)

        schema_id = model_version.mold
        # 文件范围
        prompter_cond = ""
        tree_s = list(set(kwargs["tree_l"]))
        if tree_s:
            prompter_cond += " and file.tree_id in (%s)" % ",".join(map(str, tree_s))
        if files_ids := list(set(kwargs["files_ids"])):
            prompter_cond += " and file.id in (%s)" % ",".join(map(str, files_ids))

        # 检查是否有需要预测的文档
        prompt_files_need_training = await get_files_data(schema_id, cond=prompter_cond)
        predict_files_need_training = await NewFile.find_by_mold_labeled(schema_id, tree_s, files_ids)
        if not prompt_files_need_training or not predict_files_need_training:
            return self.error(message="文件尚未预处理或标注完成，请稍后再试", status_code=400)
        if len(prompt_files_need_training) < 3 or len(predict_files_need_training) < 3:
            return self.error(message="训练样本数量最少为 3", status_code=400)

        # 更新model_version
        file_ids = [i.id for i in predict_files_need_training]
        await model_version.update_(dirs=tree_s, files=file_ids, status=PredictorTrainingStatus.PREPARE.value)

        process_flow = celery.chain(
            update_model_v2.si(schema_id, prompter_cond, vid),
            update_predict_model.si(schema_id, vid, tree_l=tree_s),
        )
        process_flow()

        await NewHistory.save_operation_history(
            model_version.id,
            self.current_user.id,
            HistoryAction.TRAINING_SCHEMA.value,
            self.current_user.name,
            kwargs,
        )
        if get_config("client.name") == "nafmii":
            name = await NewMold.get_name_by_id(schema_id)
            await NewHistory.save_operation_history(
                None,
                action=HistoryAction.NAFMII_DEFAULT,
                user_name=self.current_user.name,
                meta=None,
                uid=self.current_user.id,
                nafmii=self.get_nafmii_event(
                    status=NafmiiEventStatus.SUCCEED.value,
                    type=NafmiiEventType.MODIFY.value,
                    menu="算法模型管理",
                    subject="模型版本",
                    content=f"{name}-{model_version.name}-训练模型成功",
                ),
            )

        return self.data({"schema_id": schema_id})

    update_model_version = {"predictors": fields.Dict(load_default={})}

    @Auth("manage_mold")
    @use_kwargs(update_model_version, location="json")
    async def put(self, vid, **kwargs):
        # 更新模型配置信息
        mv_obj = await NewModelVersion.find_by_id(vid)
        if not mv_obj:
            return self.error("未找到版本模型", status_code=http.HTTPStatus.NOT_FOUND)
        predictors = mv_obj.predictors or []
        schema_config = kwargs["predictors"]
        try:
            schema_config = self.supplementary_data(schema_config)
        except CustomReError:
            return self.error("正则表达式错误", status_code=http.HTTPStatus.BAD_REQUEST)
        except ValueError:
            logger.warning(f"{schema_config}")
            return self.error("配置有误，请联系管理员", status_code=http.HTTPStatus.BAD_REQUEST)
        schema_path = "_".join(schema_config["path"])
        config_map = {"_".join(predictor["path"]): predictor for predictor in predictors}
        config_map[schema_path] = schema_config
        try:
            config_map = await self.integrate_config(mv_obj, config_map, schema_path, schema_config)
        except CustomError as e:
            return self.error(str(e), status_code=http.HTTPStatus.BAD_REQUEST)
        predictors = list(config_map.values())
        predictors = NewMoldService.revise_model_config(predictors)
        await mv_obj.update_(predictors=predictors)
        need_train_again = False
        for item in predictors:
            for model in item["models"]:
                if model.get("need_train_again"):
                    need_train_again = True
                    break
            if need_train_again:
                break
        if need_train_again:
            await mv_obj.update_(status=PredictorTrainingStatus.NEED_TRAIN_AGAIN.value)

        await NewHistory.save_operation_history(
            mv_obj.id,
            self.current_user.id,
            HistoryAction.UPDATE_MODEL_PREDICTOR.value,
            self.current_user.name,
            kwargs,
        )
        if get_config("client.name") == "nafmii":
            name = await NewMold.get_name_by_id(mv_obj.mold)
            await NewHistory.save_operation_history(
                None,
                action=HistoryAction.NAFMII_DEFAULT,
                user_name=self.current_user.name,
                meta=None,
                uid=self.current_user.id,
                nafmii=self.get_nafmii_event(
                    status=NafmiiEventStatus.SUCCEED.value,
                    type=NafmiiEventType.MODIFY.value,
                    menu="算法模型管理",
                    subject="模型要素提取模式",
                    content=f"修改{name}-{mv_obj.name}模型要素提取模式成功",
                ),
            )

        return self.data("success")

    @staticmethod
    async def integrate_config(mv_obj, all_config, current_schema_path, current_schema_config):
        if len(current_schema_config["models"]) == 0:
            # 长度为0 代表着在删除模型
            return all_config
        mold = await NewMold.find_by_id(mv_obj.mold)
        schema_map = {i["name"]: i["orders"] for i in mold.data["schemas"]}
        if len(current_schema_config["path"]) == 1 and not schema_map.get(current_schema_config["path"][0]):
            # 非组合字段
            return all_config

        current_model_name = current_schema_config["models"][0]["name"]
        is_combination_field = len(current_schema_config["path"]) == 1
        combination_key = current_schema_config["path"][0]
        if is_combination_field:
            sub_field_configs = []
            for column in schema_map[combination_key]:
                sub_config = all_config.get(f"{combination_key}_{column}")
                if sub_config and len(sub_config["models"]) > 0:  # 有可能有脏数据，最好是新建一个版本
                    sub_item_model = sub_config["models"][0]["name"]
                    if not get_config("allow_different_models") and sub_item_model != current_model_name:
                        raise CustomError("组合字段和子项模型配置不一致")
                    sub_field_configs.append(sub_config)

            if sub_field_configs:
                for sub_config in sub_field_configs:
                    unupdated_items = {}
                    model_config = sub_config["models"][0]
                    for key, value in model_config.items():
                        if not key.endswith(("regs", "patterns")):
                            continue
                        unupdated_items[key] = value
                    current_schema_config["models"][0].update({sub_config["path"][-1]: unupdated_items})
                all_config[combination_key] = current_schema_config
                for column in schema_map[combination_key]:
                    # 子项配置仅在界面展示，预测是会忽略
                    all_config[f"{combination_key}_{column}"]["just_show"] = True
        else:
            unupdated_items = {}
            model_config = current_schema_config["models"][0]
            for key, value in model_config.items():
                if not key.endswith(("regs", "patterns")):
                    continue
                unupdated_items[key] = value
            current_config = {current_schema_config["path"][-1]: unupdated_items}
            if combination_field_config := all_config.get(combination_key):
                parent_config = combination_field_config["models"]
                if not parent_config:
                    current_schema_config["just_show"] = True  # 子项配置仅在界面展示，预测是会忽略
                    all_config[current_schema_path] = current_schema_config
                    return all_config

                if not get_config("allow_different_models") and parent_config[0]["name"] != current_model_name:
                    raise CustomError("组合字段和子项模型配置不一致")
                combination_field_config["models"][0].update(current_config)
                all_config[combination_key] = combination_field_config

        return all_config

    @staticmethod
    def supplementary_data(schema_config):
        def filter_invalid_data(attribute, value):
            # 模型配置中有很多默认值，界面设置之后在保存到数据前会添加一些默认值
            # 在接口返回给界面时，需要去掉这些默认值，此filter方法就是为了去掉这些默认值
            if isinstance(value, bool):
                return True
            if isinstance(value, list):
                if not value or (len(set(value)) == 1 and value[0] == ""):
                    return False
                return True
            if isinstance(value, (int, float)):
                return True
            return bool(value)

        data = {"path": schema_config["path"]}
        models = []
        for page_model in schema_config["models"]:
            page_model.pop("__config", None)
            model_obj = model_config_map.get(page_model["name"])
            if not model_obj:
                continue
            for key, value in page_model.items():
                if key.endswith(("regs", "patterns")) and isinstance(value, list):
                    page_model[key] = [html.unescape(pattern) for pattern in value]
                    try:
                        [re.compile(i) for i in page_model[key]]
                    except (TypeError, re.error) as e:
                        raise CustomReError("正则表达式错误") from e
            try:
                model_ins = model_obj(**page_model)
            except ConfigError as config_error:
                raise config_error from config_error
            models.append(attr.asdict(model_ins, filter=filter_invalid_data))
        data["models"] = models
        if (sub_primary_key := schema_config.get("sub_primary_key")) is not None:
            logger.debug(f"{sub_primary_key=}")
            data["sub_primary_key"] = sub_primary_key
            data["group"] = {
                "sources": ["element", "syllabuses", "context_elements"]
            }  # 添加主键时需要同时添加该配置，自动分组
        return data

    @peewee_transaction_wrapper
    async def delete(self, vid):
        """删除模型版本"""
        model_version = await NewModelVersion.find_by_id(vid)
        if not model_version:
            return self.error("未找到版本模型", status_code=400)
        # 状态:待训练、训练完成、训练异常且模型状态 未启用 的才可以删除
        if (
            model_version.status
            not in (
                PredictorTrainingStatus.CREATE.value,
                PredictorTrainingStatus.DONE.value,
                PredictorTrainingStatus.ERROR.value,
            )
            or model_version.enable != ModelEnableStatus.DISABLE.value
        ):
            return self.error("模型版本不能删除", status_code=400)
        if model_version.name == "后端预置版本":  # 后端预置版本通过inv添加
            return self.error("预置模型版本不能删除", status_code=400)
        await model_version.soft_delete()
        await NewHistory.save_operation_history(
            model_version.id,
            self.current_user.id,
            HistoryAction.DELETE_MODEL_PREDICTOR.value,
            self.current_user.name,
            {"vid": vid},
        )

        if get_config("client.name") == "nafmii":
            name = await NewMold.get_name_by_id(model_version.mold)
            await NewHistory.save_operation_history(
                None,
                action=HistoryAction.NAFMII_DEFAULT,
                user_name=self.current_user.name,
                meta=None,
                uid=self.current_user.id,
                nafmii=self.get_nafmii_event(
                    status=NafmiiEventStatus.SUCCEED.value,
                    type=NafmiiEventType.DELETE.value,
                    menu="算法模型管理",
                    subject="模型版本",
                    content=f"删除{name}模型版本{model_version.id}成功",
                ),
            )

        return self.data("success")


# 模型测试记录
@route(r"/model_statistics")
class ModelStatHandler(DbQueryHandler):
    @Auth("browse")
    @use_kwargs({"vid": vid_update_args["vid"], "diff_model": fields.Bool(load_default=False)}, location="query")
    @use_kwargs(AsyncPagination.web_args, location="query")
    async def get(self, vid, diff_model, page, size):
        if not config.get_config("web.model_manage"):
            return False, self.error(message=_("don't support model_manage"), status_code=400)

        cond = NewAccuracyRecord.vid == vid
        if diff_model:
            cond &= NewAccuracyRecord.test == AccuracyTest.DIFF_MODEL.value
        else:
            cond &= NewAccuracyRecord.test == AccuracyTest.TEST.value
        query = NewAccuracyRecord.select().where(cond).order_by(NewAccuracyRecord.id.desc())
        page_data = await AsyncPagination(query, page=page, size=size).data()

        for item in page_data.get("items", []):
            item["precision"] = (item.get("data") or {}).get("total_percent")  # 整体准确率

        if get_config("client.name") == "nafmii":
            mold_id = await pw_db.scalar(
                NewAccuracyRecord.select(NewAccuracyRecord.mold).where(NewAccuracyRecord.vid == vid)
            )
            name = await NewMold.get_name_by_id(mold_id)
            await NewHistory.save_operation_history(
                None,
                action=HistoryAction.NAFMII_DEFAULT,
                user_name=self.current_user.name,
                meta=None,
                uid=self.current_user.id,
                nafmii=self.get_nafmii_event(
                    status=NafmiiEventStatus.SUCCEED.value,
                    type=NafmiiEventType.VIEW.value,
                    menu="算法模型管理",
                    subject="模型要素提取准确率列表页",
                    content=f"查看{name}模型要素提取准确率列表页成功",
                ),
            )

        return self.data(page_data)


@route(r"/accuracy-records/(\d+)")
class ModelTestingExportHandler(DbQueryHandler):
    args = {"export_excel": fields.Bool(load_default=False)}

    @Auth("manage_mold")
    @use_kwargs(args, location="query")
    async def get(self, acid, export_excel):
        accuracy_record = await NewAccuracyRecord.find_by_id(acid)
        if not accuracy_record:
            return self.error(_("Item Not Found"))

        if get_config("client.name") == "nafmii":
            name = await NewMold.get_name_by_id(accuracy_record.mold)
            await NewHistory.save_operation_history(
                None,
                action=HistoryAction.NAFMII_DEFAULT,
                user_name=self.current_user.name,
                meta=None,
                uid=self.current_user.id,
                nafmii=self.get_nafmii_event(
                    status=NafmiiEventStatus.SUCCEED.value,
                    type=NafmiiEventType.EXPORT.value,
                    menu="算法模型管理",
                    subject="准确率测试报告",
                    content=f"导出{name}准确率测试报告成功",
                ),
            )

        if export_excel:
            if accuracy_record.export_path:
                return await self.export(accuracy_record.export_path)
            return self.error(_("data not ready"))
        return self.data(accuracy_record.to_dict())


# 历史测试样本
@route(r"/history_dirs/(\d+)")
class HistoryDirsHandler(DbQueryHandler):
    @Auth("browse")
    async def get(self, *args):
        (vid,) = args
        # 校验mold
        res = await pw_db.first(
            NewModelVersion.select(
                NewModelVersion.id,
                NewModelVersion.mold,
                NewModelVersion.created_utc,
                NewModelVersion.files,
                NewModelVersion.model_type,
            )
            .where(NewModelVersion.id == vid)
            .tuples()
        )
        if not res:
            return self.error(message=_("Item Not Found"), status_code=404)

        vid, mold, v_time, files, _type = res
        v_time = time.strftime("%Y.%m.%d %H:%M:%S", time.localtime(v_time))
        v_cnt = len(files or [])

        rows = await pw_db.execute(
            NewAccuracyRecord.select(
                NewAccuracyRecord.id,
                NewAccuracyRecord.created_utc,
                NewAccuracyRecord.dirs,
                NewAccuracyRecord.file_count,
            )
            .where(NewAccuracyRecord.mold == mold, NewAccuracyRecord.type == _type)
            .order_by(NewAccuracyRecord.created_utc.desc())
            .tuples()
        )

        data = []
        # TODO: pagination
        for each in rows:
            acid, created_utc, dirs, file_count = each
            ac_time = time.strftime("%Y.%m.%d %H:%M:%S", time.localtime(created_utc))
            data.append(
                {
                    "acid": acid,
                    "text": "测试集：%s/%s样本（模型：%s/%s样本）" % (ac_time, file_count, v_time, v_cnt),
                    "dirs": dirs or [],
                }
            )
        return self.data(data)


# 历史配置版本（提取模型）
@route(r"/history_predictors/(\d+)")
class HistoryPredHandler(DbQueryHandler):
    @Auth("browse")
    async def get(self, *args):
        (schema_id,) = args
        # 校验mold
        mold = await NewMold.find_by_id(schema_id)
        if not mold:
            return self.error(message="schema_id: [ {} ] does not existed".format(schema_id), status_code=400)

        sql = (
            "select id,created_utc,predictors from model_version "
            "where mold=%(mold)s and deleted_utc=0 and type=%(type)s and status=%(status)s order by id desc;"
        )
        versions = await db.raw_sql(
            sql,
            "all",
            **{
                "mold": int(schema_id),
                "type": ModelType.PREDICT.value,
                "status": PredictorTrainingStatus.DONE.value,
            },
        )

        data = []
        # TODO: pagination
        for each in versions:
            vid, created_utc, predictors = each
            _time = time.strftime("%Y.%m.%d %H:%M:%S", time.localtime(created_utc))
            data.append(
                {
                    "id": vid,
                    "text": "%s 训练版本（id：%s）" % (_time, vid),
                    "predictors": predictors,
                }
            )
        return self.data(data)


@route(r"/config")
class ClientConfigHandler(BaseHandler):
    async def get(self):
        # 无论登录与否必须提前获取的信息
        data = {"salt": gen_salt()}
        key_pairs = [
            ("client_name", "client.name"),
            ("trident_url", "app.auth.trident.url"),
            # 是否加密指定的几个接口的 request body，前端已经写死，所以只需要布尔值即可
            ("encrypted_handshake", "web.encrypted_routes"),
            ("http_secure_map", "web.http_secure_map"),
            ("encrypted_request_routes", "web.encrypted_request_routes"),
        ]
        for key, path in key_pairs:
            if value := get_config(path):
                data[key] = bool(value) if key == "encrypted_handshake" else value
        self.set_header(
            "X-PAI-Protobuf",
            base64.b64encode(
                AES256GCMEncryptor((get_config("web.share_key") or "hkx85vMOBSM7M7W")).encrypt(compact_dumps(data))
            ).decode(),
        )
        if binary_key := (get_config("web.hex_binary_key") or get_config("web.binary_key")):
            if self.hex_binary_key:
                self.set_header("X-BINARY-ALG", "HexSm4")
            self.set_header(
                "X-BINARY-KEY",
                base64.b64encode(
                    PackageEncrypt((get_config("web.share_key") or "hkx85vMOBSM7M7W")).encrypt(binary_key.encode())
                ).decode(),
            )
        if not self.current_user:
            self.set_status(http.HTTPStatus.NO_CONTENT)
            return self.finish()

        client_config = {
            "app_id": get_config("app.app_id", "remarkable"),
            "support_multiple_molds": get_config("client.support_multiple_molds", False),
            "check_schema_base_type": get_config("client.check_schema_base_type", False),
            "show_prompt_element_button": get_config("client.show_prompt_element_button", False),
            "export_label_data": get_config("client.export_label_data", False),
            "export_label_txt": get_config("client.export_label_txt", False),
            "export_answer_csv": get_config("client.export_answer_csv", False),
            "stat_accuracy": get_config("client.stat_accuracy", False),
            "answer_version": get_config("prompter.answer_version", "2.2"),
            "single_answer": get_config("web.default_question_health", 1),
            "confirm_needed_cols": get_config("client.confirm_needed_cols", []),
            "show_all_predict_items": get_config("client.show_all_predict_items", True),
            "show_ai_modules": get_config("client.show_ai_modules", True),
            "show_ai_score": get_config("client.show_ai_score", True),
            "export_single_answer": get_config("client.export_single_answer", False),
            "record_manual": get_config("web.record_manual", False),
            "show_merge_answer": get_config("web.show_merge_answer", False),
            "show_export_answer": get_config("web.show_export_answer", False),
            "show_marker": get_config("web.show_marker", False),
            "answer_default_display_level": get_config("client.answer_default_display_level", 5),
            "show_push_to_autodoc_btn": get_config("client.show_push_to_autodoc_btn", False),
            "user_system_provider": get_config("web.user_system_provider", "self"),
            "cas_logout_url": get_config("app.auth.trident.cas_logout_url", None),
            "unsure_warnning_score": get_config("web.unsure_warnning_score", 0),
            "data_abroad": get_config("web.data_abroad", False),
            "model_abroad": get_config("web.model_abroad", False),
            "unlimit_answer_mode": get_config("web.mode_unlimited_answers", False),
            "table_association": get_config("web.table_association", False),
            "table_association_postfix": get_config("web.table_association_postfix", False),
            "chapter_assist": get_config("web.chapter_assist", False),
            "http_headers": get_config("web.http_headers", {}),
            "encoding_gzip": get_config("web.encoding_gzip", False),
            "default_page": get_config("web.default_page", "default"),
            "only_szse_ipo": get_config("web.only_szse_ipo", False),
            "crude_answer_threshold": get_config("web.crude_answer_threshold", 0),
            "stencil_host": get_config("web.apis.stencil_host", ""),
            "page_image_format": "jpg",  # TODO 过渡方案,jpg格式不依赖缓存;待前端完全去掉对这块数据的依赖后去除
            "parse_pdf": get_config("web.parse_pdf", True),
            "calliper_diff": get_config("client.calliper_diff", False),
            "enable_pdf2word": get_config("web.enable_pdf2word", False),
            "export_special_data": get_config("web.export_special_data", False),  # poc for ebscn
            "schema_manager_display_other_tabs": get_config("web.schema_manager_display_other_tabs", {}),  #
            "gffund_parse_excel": get_config("customer_settings.parse_excel", False),  # 广发excel解析入库
            "file_size_limit": get_config("client.file_size_limit", 20),  # 文件大小限制
            "show_file_scenario": get_config("client.show_file_scenario", False),  # 打开文件场景, 支持大模型审核
            "enable_llm_extract": get_config("web.enable_llm_extract", False),
        }

        # 合并feature下的配置项
        client_config.update(FeatureSchema.from_config().model_dump())

        # 标注页面的导出按钮
        answer_convert = {}
        for m1_name, m2_name in (get_config("web.answer_convert") or {}).items():
            query1 = NewMold.select(NewMold.id).where(NewMold.name == m1_name)
            query2 = NewMold.select(NewMold.id).where(NewMold.name == m2_name)
            mold_ids = await pw_db.scalars(query1.union_all(query2))
            if len(mold_ids) == 2:
                answer_convert.setdefault(mold_ids[0], mold_ids[1])
        client_config.update({"answer_convert": answer_convert})
        # config for ht
        is_fund = get_config("ht_fund") or False
        if is_fund:
            show_formula_check = get_config("ht.fund_show_formula_check") or False
        else:
            show_formula_check = get_config("ht.soft_show_formula_check") or False
        client_config["show_formula_check"] = show_formula_check
        client_name = get_config("client.name")
        if client_name == ClientName.nafmii:
            client_config["nafmii.urls"] = get_config("nafmii.urls")

        # convert
        client_config["single_answer"] = client_config["single_answer"] == 1
        return self.data(client_config, binary=bool(get_config("web.encrypt_config")))


@route(r"/question/(?P<question_id>\d+)/answer_schema")
class AnswerSchemaHandler(PermCheckHandler):
    @Auth(["remark"])
    async def put(self, **kwargs):
        qid = int(kwargs["question_id"])
        await self.check_question_permission(qid, mode="write")
        data = self.get_json_body()
        for ans_data in data["ans_data"]:
            uid = int(ans_data["uid"])
            data = ans_data["data"]
            await pw_db.execute(
                NewAnswer.update(data=data, updated_utc=generate_timestamp()).where(
                    and_(NewAnswer.qid == qid, NewAnswer.uid == uid)
                )
            )
        # 重跑预测
        file = await NewFile.find_by_qid(qid)
        await process_file(file, force_predict=True)

        return self.data(None)


@route(r"/config/(?P<key>.+)")
class ConfigHandler(PermCheckHandler):
    @Auth("remark_management")
    async def get(self, **kwargs):
        key = kwargs["key"]
        config_index = self.get_config_index()
        config_item = await NewSystemConfig.find_by_name(key, config_index)
        return self.data(config_item.to_dict() if config_item else None)

    @Auth("remark_management")
    async def post(self, **kwargs):
        key = kwargs["key"]
        config_index = self.get_config_index()
        data = self.get_json_body()
        config_item = await NewSystemConfig.find_by_name(key, index=config_index)
        if config_item:
            await config_item.update(data=data)
        else:
            await NewSystemConfig.create(
                **{
                    "name": key,
                    "data": data,
                    "index": config_index,
                }
            )
        if key in ("answer_sync_db", "sync_external_file"):
            clear_sync_schedule_lock()
        return self.data(None)

    def get_config_index(self):
        index_dict = {
            "schema": self.get_argument("schema", default=None),
        }
        return NewSystemConfig.index_str(**index_dict)


@route(r"/enable_config/(?P<key>.+)/(?P<enable>\d)")
class ConfigEnableHandler(PermCheckHandler):
    @Auth("remark_management")
    async def post(self, **kwargs):
        enable = int(kwargs["enable"])
        if enable not in CommonStatus.value2member_map():
            return self.error(message="{}".format("enable") + _(" illegal"), status_code=400)
        key = kwargs["key"]
        config_index = self.get_config_index()
        config_item = await NewSystemConfig.find_by_name(key, index=config_index)
        if not config_item:
            return self.error(message="{}".format("config_key") + _(" illegal"), status_code=400)
        await NewSystemConfig.update_by_pk(config_item.id, enable=enable)
        return self.data(None)

    def get_config_index(self):
        index_dict = {
            "schema": self.get_argument("schema", default=None),
        }
        return NewSystemConfig.index_str(**index_dict)


@route(r"/model_version/export/(\d+)")
class ModelVersionExportHandler(PermCheckHandler):
    @Auth("manage_mold")
    async def get(self, vid):
        # 导出版本模型
        model_version = await NewModelVersion.find_by_id(vid)
        if not model_version:
            return self.error("model version not exists", status_code=400)
        # todo 是否仅可导出已启用的模型 待确认
        schema_id = model_version.mold
        mold_obj = await NewMold.find_by_id(schema_id)
        export_file_name = f"{mold_obj.name}_{vid}.zip"
        with tempfile.NamedTemporaryFile() as model_version_file:
            with open(model_version_file.name, "w", encoding="utf-8") as file_obj:
                json.dump(model_version.to_dict(), file_obj, ensure_ascii=False)
            with tempfile.NamedTemporaryFile() as export_file:
                result = archive_model(export_file.name, PREDICTOR_MODEL_FILES + PROMPTER_MODEL_FILES, schema_id, vid)
                with zipfile.ZipFile(result, "a") as zipf:
                    zipf.write(model_version_file.name, "model_version.json")
                return await self.export(result, file_name=export_file_name)


query_args = {
    "schema_id": fields.Str(required=True),
    "model_version_name": fields.Str(required=True),
}


@route(r"/model_version/import")
class ModelVersionImportHandler(PermCheckHandler):
    @Auth("manage_mold")
    @use_kwargs({"file": fields.Raw(required=True)}, location="files")
    @use_kwargs(query_args, location="query")
    @peewee_transaction_wrapper
    async def post(self, schema_id, model_version_name, file):
        # 导入版本模型
        model_version = await NewModelVersion.find_by_kwargs(name=model_version_name)
        if model_version:
            return self.error(message="模型版本名称重复", status_code=400)
        mold = await NewMold.find_by_id(schema_id)
        schema_fields = [mold.name]
        for item in mold.data["schemas"]:
            schema_fields.extend(item["orders"])
        # 校验模型是否属于该schema
        with tempfile.TemporaryDirectory() as import_temp_dir:
            with zipfile.ZipFile(io.BytesIO(file["body"])) as zip_file:
                zip_file.extractall(import_temp_dir)
            model_version_file = os.path.join(import_temp_dir, "model_version.json")
            if not os.path.exists(model_version_file):
                return self.error(message="导入模型文件中未包含提取模型配置", status_code=400)
            with open(model_version_file, "r", encoding="utf-8") as model_version_file:
                model_version = json.load(model_version_file)
            for model_file in glob.glob(f"{os.path.join(import_temp_dir, 'predictors')}/*.pkl"):
                field_name = os.path.splitext(os.path.basename(model_file))[0].split("_")[-1]
                if field_name != "SUBSTITUE" and field_name not in schema_fields:
                    logging.info("""{} not in schema""".format(field_name))
                    return self.error(message="导入模型有误，请检查模型文件是否属于该Schema", status_code=400)

            new_model_version = await NewModelVersion.create(
                **{
                    "mold": schema_id,
                    "name": model_version_name,
                    "model_type": model_version["model_type"],
                    "status": model_version["status"],
                    "dirs": [],
                    "files": [],
                    "enable": ModelEnableStatus.DISABLE.value,
                    "predictors": model_version["predictors"],
                    "predictor_option": model_version["predictor_option"],
                },
            )
            training_cache_dir = Path(get_config("training_cache_dir"))
            model_dir = training_cache_dir / str(schema_id) / str(new_model_version.id)
            shutil.copytree(import_temp_dir, model_dir)
        return self.data(new_model_version.to_dict())


@route(r"/schema/export/(\d+)")
class SchemaExportHandler(PermCheckHandler):
    @Auth("manage_mold")
    async def get(self, mold):
        mold_obj = await NewMold.find_by_id(mold)
        if not mold_obj:
            return self.error(message=_("can't find the mold"), status_code=400)

        data = await NewMoldService.export_schema(mold_obj)
        return await self.export(json.dumps(data, ensure_ascii=False).encode(), f"{mold_obj.name}.json")


@route(r"/schema/import")
class SchemaImportHandler(PermCheckHandler):
    user_args = {
        "rewrite": fields.String(required=False, load_default=""),
        "rename": fields.String(required=False, load_default=""),  # 谨慎使用,避免跟模型不匹配
    }

    @Auth("manage_mold")
    @use_kwargs({"file": fields.Raw(required=True)}, location="files")
    @use_kwargs(user_args, location="form")
    @peewee_transaction_wrapper
    async def post(self, file, rewrite, rename):
        meta, info = self.check_json_file(file)
        if not meta:
            return info
        success, msg = await NewMoldService.sync_mold_and_rule(meta, rewrite, rename)
        if not success:
            return self.error(_(msg))
        return self.data({})

    def check_json_file(self, file):
        try:
            params = json.loads(file["body"])
        except JSONDecodeError:
            return False, self.error(message=_("Payload is not dict"), status_code=400)

        if not isinstance(params, dict):
            return False, self.error(message=_("Payload is not dict"), status_code=400)
        columns = ("mold", "extract_method", "rule_class", "rule_item")
        for column in columns:
            if column not in params:
                return False, self.error(message="{}".format(column) + _(" is required"), status_code=400)
        return params, None


@route(r"/question/(?P<question_id>\d+)/special_answer")
class AnswerExportHandler(PermCheckHandler):
    @Auth("browse")
    async def get(self, **kwargs):
        from remarkable.converter.ebscn import (
            CONVERT_MAP,
        )

        qid = int(kwargs["question_id"])
        await self.check_question_permission(qid)
        question = await NewQuestion.find_by_id(qid)
        if not question:
            return False, _("The question does not exists.")
        file = await NewFile.find_by_qid(qid)
        if not file:
            raise CustomError(_("not found file"))
        special_datas = await NewSpecialAnswer.get_answers(qid, NewSpecialAnswer.ANSWER_TYPE_JSON, top=1)
        if not question.preset_answer or not special_datas:
            return self.error(_("The file is being processed, please try again later"))
        special_data = special_datas[0].data
        workbook = openpyxl.Workbook()
        headers = ["字段", "转义后文本"]
        data = []
        for key in CONVERT_MAP:
            data.append([key, special_data.get(key, "")])

        worksheet = dump_data_to_worksheet(workbook, headers, data)
        worksheet["A1"].font = Font(size=13, bold=True)
        worksheet["B1"].font = Font(size=13, bold=True)

        worksheet.column_dimensions["A"].auto_size = True
        worksheet.column_dimensions["B"].auto_size = True
        with io.BytesIO() as bytes_io:
            workbook.save(bytes_io)
            return await self.export(bytes_io.getvalue(), f"{file.name}.xlsx")
