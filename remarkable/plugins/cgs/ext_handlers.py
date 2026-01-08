"""
此handler用作给客户提供源码的预留，暂时不同handler.py合并
"""

import functools
import io
import logging
import os
from datetime import datetime
from zipfile import ZipFile

from marshmallow import ValidationError
from utensils.zip import ZipFilePlus
from webargs import fields

from remarkable import config
from remarkable.answer.node import AnswerItem
from remarkable.answer.reader import MasterAnswerReader
from remarkable.common import field_validate
from remarkable.common.apispec_decorators import use_kwargs
from remarkable.common.constants import AIStatus, HistoryAction
from remarkable.common.enums import TaskType
from remarkable.common.exceptions import CGSException, CustomError
from remarkable.common.schema import Schema
from remarkable.common.util import get_key_path
from remarkable.converter import SimpleJSONConverter
from remarkable.data.services.training_data_service import (
    delete_training_task,
    download_training_zip,
    mold_export_task,
)
from remarkable.db import peewee_transaction_wrapper, pw_db
from remarkable.models.new_file import NewFile
from remarkable.models.new_user import ADMIN, NewAdminUser
from remarkable.plugins.cgs import CGSHandler, plugin
from remarkable.plugins.cgs.auth import CgsTokenValidator, login_from_api
from remarkable.plugins.cgs.common.utils import get_review_fields
from remarkable.plugins.cgs.globals import ALLOWED_FILE_TYPE
from remarkable.plugins.cgs.services import compare_result
from remarkable.pw_models.audit_rule import NewAuditResult
from remarkable.pw_models.model import NewAuditStatus, NewFileProject, NewFileTree, NewHistory, NewMold, NewTrainingData
from remarkable.pw_models.question import NewQuestion
from remarkable.service.answer import get_master_question_answer
from remarkable.service.new_file import NewFileService
from remarkable.service.new_file_project import NewFileProjectService
from remarkable.service.new_question import NewQuestionService
from remarkable.worker.tasks import process_file

DISPLAY_BASE_URL = config.get_config("cgs.display_base_url")


logger = logging.getLogger(__name__)


@plugin.route(r"/files/(?P<file_id>\d+)/schemas/(?P<schema_id>\d+)/ai-status")
class GetResultHandlerForCGS(CGSHandler):
    @CgsTokenValidator()
    async def get(self, file_id, schema_id):
        """获取文档分析结果接口"""
        file = await NewFile.find_by_id(file_id)
        if not file:
            raise CustomError(msg="Invalid file_id", resp_status_code=400)

        schema = await NewMold.find_by_id(schema_id)
        if not schema:
            raise CustomError(msg="Invalid schema_id", resp_status_code=400)

        master_question = await NewQuestion.get_master_question(int(file_id))
        if not master_question:
            return self.error(f"can't find master_question for {file_id}")

        audit_status = None
        if master_question:
            audit_status = await NewAuditStatus.find_latest_status(fid=file.id)
        return self.data(await self.build_resp_body(file, master_question, audit_status, schema_id))

    @classmethod
    async def build_resp_body(cls, file, question, audit_status, schema_id):
        return {
            "file": {"id": file.id, "pdf_parse_status": file.pdf_parse_status},
            "question": await cls.get_question_data(question) if question else None,
            "audit": {"id": audit_status.id, "status": audit_status.status} if audit_status else None,
            "url": f"{DISPLAY_BASE_URL}/api/v1/plugins/cgs/files/{file.id}/schemas/{schema_id}/audit",
        }

    @staticmethod
    async def get_question_data(question):
        questions_data = {}
        if question:
            questions_data["id"] = question.id
            questions_data["ai_status"] = await NewQuestionService.get_question_ai_status(question.fid)
        return questions_data


@plugin.route(r"/files/upload")
class UploadHandlerForCGS(CGSHandler):
    form_args = {
        "schema_id": fields.Int(load_default=None),
        "tree_id": fields.Int(load_default=None),
        "task_type": fields.Str(
            load_default="", validate=field_validate.OneOf([""] + [item.value for item in TaskType])
        ),
        "scenario_id": fields.Int(load_default=None),
        "sysfrom": fields.Str(load_default="-", validate=field_validate.OneOf(["PIF", "OAS", "FMP"])),
        "source": fields.Str(load_default="", validate=field_validate.OneOf(["Glazer"])),
        "glazer_project_id": fields.Int(load_default=None),
    }

    @CgsTokenValidator()
    @use_kwargs(form_args, location="form")
    @use_kwargs({"post_files": fields.List(fields.Raw(), required=True, data_key="file")}, location="files")
    async def post(self, post_files, schema_id, task_type, tree_id, scenario_id, sysfrom, source, glazer_project_id):
        if tree_id is not None:
            file_tree = await NewFileTree.find_by_id(tree_id)
            if not file_tree:
                return self.error(_("Invalid tree_id"))

            molds = await NewFileTree.find_default_molds(file_tree.id)
            project = await NewFileProject.find_by_id(file_tree.pid)
        else:
            if schema_id is None:
                return self.error(_("Invalid schema_id"))

            schema = await NewMold.find_by_id(schema_id)
            if not schema:
                return self.error(_("Invalid schema_id"))
            molds = await NewMold.get_related_molds(schema_id)
            if not molds:
                return self.error(_("Invalid schema_id"))
            molds = [mold.id for mold in molds]

            project = await NewFileProjectService.create(name=schema.name, default_molds=molds)
            file_tree = await NewFileTree.find_by_id(project.rtree_id)

        meta_info = {"glazer_project_id": glazer_project_id}
        if not task_type:
            default = await NewFileTree.find_default(file_tree.id)
            if default:
                task_type = default.default_task_type
                scenario_id = default.default_scenario_id
            else:
                task_type = TaskType.EXTRACT.value
                scenario_id = None

        data = []
        for file in post_files:
            suffix = os.path.splitext(file.filename)[1].lower()
            if suffix == ".zip":
                _data = await self.upload_for_zip(
                    molds, file, project, file_tree.id, task_type, scenario_id, sysfrom, source, meta_info
                )
                data.extend(_data)
            elif suffix in ALLOWED_FILE_TYPE:
                _data = await self.upload_for_single_file(
                    molds, file, project, file_tree.id, task_type, scenario_id, sysfrom, source, meta_info
                )
                data.extend(_data)
            else:
                logger.error(f"Unsupported file type, {file.filename}")

        return self.data(data)

    @staticmethod
    async def upload_for_single_file(
        molds, post_files, project, tree_id, task_type, scenario_id, sysfrom, source, meta_info
    ):
        doc_name = post_files.filename
        doc_raw = post_files.body
        file = await NewFileService.create_file(
            doc_name,
            doc_raw,
            molds,
            project,
            tree_id,
            uid=ADMIN.id,
            task_type=task_type,
            sysfrom=sysfrom,
            source=source,
            meta_info=meta_info,
            scenario_id=scenario_id,
        )
        await process_file(file, force_predict=True)
        return [{"id": file.id, "filename": doc_name}]

    @staticmethod
    async def upload_for_zip(molds, post_files, project, tree_id, task_type, scenario_id, sysfrom, source, meta_info):
        tree_dict = {}
        data = []
        with ZipFile(io.BytesIO(post_files.body)) as zfp:
            for doc_path in zfp.namelist():
                if os.path.splitext(doc_path)[1].lower() not in ALLOWED_FILE_TYPE:
                    continue
                with zfp.open(doc_path, mode="r") as fpin:
                    fixed_path = ZipFilePlus.fix_encoding(doc_path)
                    spliced_path = fixed_path.split(os.path.sep)
                    real_tree_id = await UploadHandlerForCGS.get_real_tree_id(
                        molds, project, spliced_path, tree_dict, tree_id
                    )

                    file = await NewFileService.create_file(
                        spliced_path[-1],
                        fpin.read(),
                        molds,
                        project,
                        real_tree_id,
                        uid=ADMIN.id,
                        task_type=task_type,
                        sysfrom=sysfrom,
                        source=source,
                        meta_info=meta_info,
                        scenario_id=scenario_id,
                    )
                    await process_file(file, force_predict=True)
                    data.append({"id": file.id, "filename": fixed_path})
        return data

    @staticmethod
    async def get_real_tree_id(molds, project, spliced_path, tree_dict, tree_id):
        """获取zip包中文件所属的真实tree_id，此函数会根据zip中的目录结构创建新的tree节点"""
        parent_tree_id = tree_id
        if len(spliced_path) > 1:
            parent_dir = ""
            for _dir in spliced_path[:-1]:
                curr_dir = os.path.join(parent_dir, _dir)
                parent_dir = curr_dir
                if not tree_dict.get(curr_dir):
                    new_tree = await NewFileTree.create(
                        **{
                            "ptree_id": parent_tree_id,
                            "pid": project.id,
                            "name": _dir,
                            "default_molds": molds,
                            "uid": ADMIN.id,
                        }
                    )
                    parent_tree_id = new_tree.id
                    tree_dict[curr_dir] = new_tree.id
                else:
                    parent_tree_id = tree_dict.get(curr_dir)
        return parent_tree_id


@plugin.route(r"/questions/(?P<qid>\d+)")
class QuestionHandlerForCGS(CGSHandler):
    @CgsTokenValidator()
    async def get(self, qid):
        question = await NewQuestion.find_by_id(qid)
        if not question:
            return self.error(_("Question not found"))
        master_question = await NewQuestion.get_master_question(question.fid)
        if not master_question:
            return self.error(f"can't find master_question for {question.fid}")
        answer, master_mold = await get_master_question_answer(master_question)

        return self.data(answer)


def _validate_export_type(export_type):
    if export_type != "csv":
        raise ValidationError(f"Invalid types: {export_type}")
    if not config.get_config("client.export_answer_csv"):
        raise ValidationError("client.export_answer_csv config not ready")


@plugin.route(r"/training_data")
class TrainingTaskHandler(CGSHandler):
    get_args = {
        "schema_id": fields.Int(required=True, validate=lambda x: x > 0),
        "export_type": fields.Str(load_default="csv", validate=_validate_export_type),
        "tree_l": fields.List(fields.Int(), load_default=[]),
    }

    @CgsTokenValidator()
    @use_kwargs(get_args, location="query")
    async def get(self, schema_id, export_type, tree_l):
        cond = [
            NewTrainingData.mold == schema_id,
            NewTrainingData.export_type == export_type,
            NewTrainingData.task_action == HistoryAction.CREATE_TRAINING_DATA,
        ]
        query = NewTrainingData.select().where(*cond).order_by(NewTrainingData.id.desc())
        data = list(await pw_db.execute(query))
        return self.data({"items": [x.to_dict() for x in data]})

    @CgsTokenValidator()
    @use_kwargs(get_args, location="json")
    async def post(self, schema_id, export_type, tree_l):
        training_data = await mold_export_task(schema_id, export_type, tree_l)
        # 操作记录
        await NewHistory.save_operation_history(
            training_data.id,
            ADMIN.id,
            HistoryAction.CREATE_TRAINING_DATA.value,
            ADMIN.name,
            {"task_id": training_data.id},
        )
        return self.data(training_data.to_dict())


@plugin.route(r"/training_data/(?P<task_id>\d+)")
class TrainingDataHandler(CGSHandler):
    @CgsTokenValidator()
    async def get(self, task_id):
        """zip文件下载"""
        if not (config.get_config("client.export_label_data") or config.get_config("client.export_answer_csv")):
            raise CGSException(_("don't support export_label_data"))
        data, filename = await download_training_zip(task_id)
        await NewHistory.save_operation_history(
            int(task_id),
            ADMIN.id,
            HistoryAction.EXPORT_TRAINING_DATA.value,
            ADMIN.name,
            {"task_id": task_id},
        )
        return await self.export(data, filename)

    @CgsTokenValidator()
    @peewee_transaction_wrapper
    async def delete(self, task_id):
        if not (config.get_config("client.export_label_data") or config.get_config("client.export_answer_csv")):
            raise CGSException(_("don't support export_label_data"))
        await delete_training_task(task_id)
        await NewHistory.save_operation_history(
            int(task_id),
            ADMIN.id,
            HistoryAction.DELETE_TRAINING_DATA.value,
            ADMIN.name,
            {"task_id": int(task_id)},
        )
        return self.data(None)


@plugin.route(r"/files/(?P<file_id>\d+)/schemas/(?P<schema_id>\d+)/compare-result")
class ResultExportHandler(CGSHandler):
    @CgsTokenValidator()
    @use_kwargs({"export_type": fields.String(required=True)}, location="query")
    async def get(self, file_id, schema_id, export_type):
        schema = await NewMold.find_by_id(schema_id)
        if not schema:
            return self.error(_("Invalid schema_id"), status_code=400)
        file = await NewFile.find_by_id(file_id)
        if not file:
            return self.error(_("Invalid file_id"), status_code=400)
        results = await NewAuditResult.get_results(
            file_id, [schema_id], self.current_user.is_admin, self.current_user.id, only_incompliance=True
        )
        if export_type == "csv":
            csv_bytes = await compare_result.get_csv_bytes(results)
            return await self.export(csv_bytes, file_name="compare-result.csv")
        return self.data([item.to_result_item() for item in results])


@plugin.route(r"/files/(?P<file_id>\d+)/schemas/(?P<schema_id>\d+)/audit")
class AuditPageHandler(CGSHandler):
    @CgsTokenValidator()
    @login_from_api()
    @use_kwargs({"is_iframe": fields.Bool(load_default=False)}, location="query")
    async def get(self, file_id, schema_id, is_iframe):
        question = await NewQuestion.find_by_fid_mid(file_id, schema_id)
        if not question:
            raise CustomError(msg="Invalid file_id or schema_id", resp_status_code=404)

        file = await NewFile.find_by_id(file_id)
        if not file:
            raise CustomError(msg="Invalid file_id", resp_status_code=404)

        url = (
            f"{DISPLAY_BASE_URL}/#/project/inspect/{question.id}?treeId={file.tree_id}&fileId={file.id}"
            f"&schemaId={question.mold}&projectId={file.pid}&task_type={file.task_type}&fileName={file.name}&answerType=merged-answer"
        )
        if is_iframe:
            url += "&isIframe=true"
        logger.info(f"redirect to {url}")
        return self.redirect(url)


@plugin.route(r"/files/(?P<file_id>\d+)/edited-answer")
class CgsEditedAnswerHandler(CGSHandler):
    @CgsTokenValidator()
    @use_kwargs({"export": fields.Bool(load_default=False)}, location="query")
    async def get(self, file_id, export):
        file_id = int(file_id)
        question = await NewQuestion.get_master_question(file_id)
        if not question:
            return self.error(f"can't find master_question for {file_id}")
        if question.ai_status != AIStatus.FINISH.value:
            return self.error("文档处理中!")

        file = await NewFile.find_by_id(file_id)
        if not file:
            return self.error(_("not found file"))
        answer, mold = await get_master_question_answer(question)
        glazer_id = (file.meta_info or {}).get("glazer_project_id")
        if not glazer_id:
            return self.error("review_fields_url not found")
        try:
            review_fields = await get_review_fields(glazer_id)
            logger.info(f"{review_fields=}")
            if not review_fields:
                return self.error(f"invalid empty review_fields for fid: {file_id}")
            if invalid_fields := self.invalid_review_fields(mold.data, review_fields):
                return self.error(f"invalid review_fields {invalid_fields}: for fid: {file_id}")
        except CustomError as err:
            return self.error(str(err))
        review_items = [x for x in answer["userAnswer"]["items"] if get_key_path(x["key"], "|") in review_fields]
        logger.info(f"{review_items=}")
        answer["userAnswer"]["items"] = review_items

        enum_types = [x["label"] for x in mold.data["schema_types"] if x["type"] == "enum"]
        try:
            self.is_valid_answer(enum_types, review_fields, answer)
        except CustomError as e:
            logger.exception(e)
            return self.error(f"invalid answer for fid: {file_id}")
        edited_items = [x for x in answer["userAnswer"]["items"] if x["record"]]
        answer["userAnswer"]["items"] = edited_items

        if export:
            format_func = functools.partial(SimpleJSONConverter.cgs_csv_text, enum_types)
            try:
                csv_bytes = SimpleJSONConverter(answer).to_csv(sep="|", format_func=format_func, keep_index=True)
            except CustomError as e:
                logger.exception(e)
                return self.error(f"invalid answer for fid: {file_id}")
            except Exception as e:
                logger.exception(e)
                return self.error(f"failed generate {file_id}_edited_answer.csv")
            return await self.export(csv_bytes, file_name=f"{file_id}_edited_answer.csv")
        return self.data({"edited_items": len(edited_items)})

    @classmethod
    def fill_tree_node(cls, tree, keys):
        first_item = keys.pop(0)
        if first_item not in tree:
            tree[first_item] = {}
        if keys:
            cls.fill_tree_node(tree[first_item], keys)

    def is_valid_answer(self, enum_types, review_fields, answer):
        review_fields_tree = {}
        for field in review_fields:
            keys = field.split("|")
            self.fill_tree_node(review_fields_tree, keys)

        reader = MasterAnswerReader(answer)
        root_node, _ = reader.build_answer_tree()
        logger.info(f"{root_node.to_dict()=}")
        answer_dict = root_node.to_dict()[reader.mold_name][0]
        self.is_valid_node(enum_types, review_fields_tree, answer_dict)

    def is_valid_node(self, enum_types, fields_tree, answer_dict):
        for key, sub_keys in fields_tree.items():
            key_answer = answer_dict.get(key)
            logger.info(f"{key=}, {sub_keys=}")
            if not key_answer:
                raise CustomError("invalid answer")

            if sub_keys:  # 非叶子节点
                if not isinstance(key_answer, list):
                    raise CustomError("invalid answer")
                for item in key_answer:
                    self.is_valid_node(enum_types, sub_keys, item)
            else:
                text = key_answer.simple_text(clear=False, enum=False)
                if isinstance(text, list):
                    text = "\n".join(text)
                if not text:
                    raise CustomError("invalid answer")

                if key_answer.schema["data"]["type"] in enum_types:
                    if not key_answer.value:
                        raise CustomError("invalid answer")

    @staticmethod
    def invalid_review_fields(mold_data, review_fields):
        mold_schema = Schema(mold_data)
        column_path = ["|".join(x[1:]) for x in mold_schema.iter_schema_attr()]

        return [x for x in review_fields if x not in column_path]


@plugin.route(r"/files/(\d+)/answer_data/history")
class CgsAnswerDataHistoryHandler(CGSHandler):
    @CgsTokenValidator()
    @use_kwargs({"only_suggestion": fields.Bool(load_default=True)}, location="query")
    async def get(self, fid, only_suggestion):
        fid = int(fid)
        question = await NewQuestion.get_master_question(fid)
        if not question:
            return self.error(f"can't find master_question for {fid}")
        answer, _ = await get_master_question_answer(question)
        user_map = await NewAdminUser.get_user_name_map()
        item_handler = functools.partial(self.item_handler, user_map, only_suggestion)
        data = SimpleJSONConverter(answer).convert(item_handler=item_handler)
        return self.data(self.post_process(data))

    @staticmethod
    def item_handler(users, only_suggestion, item):
        kwargs = item["kwargs"]
        if only_suggestion and not kwargs["revise_suggestion"]:
            return {}
        record = kwargs.get("record")
        if not record:
            return {}

        data = []
        record.append(
            {
                "data": item["data"],
                "uid": kwargs["uid"],
                "updated_utc": kwargs["updated_utc"],
            }
        )
        for idx, item in enumerate(record):
            user, date, text = "", "", ""
            if item["data"]:
                text = AnswerItem(item["data"]).origin_text
            elif idx == 0:
                user = "AI"  # 无预测答案的情形
            else:
                text = "当前无答案"

            if uid := item["uid"] or "":
                user = users.get(uid)
                user = "AI" if (idx == 0 and user == "admin") else user

            if item["updated_utc"]:
                date = datetime.fromtimestamp(item["updated_utc"]).strftime("%Y-%m-%d %H:%M:%S")

            data.append({"user": user, "date": date, "text": text})
        return {"record": data}

    def post_process(self, data):
        if isinstance(data, list):
            result = []
            for item in data:
                if ret := self.post_process(item):
                    result.append(ret)
            return result

        elif isinstance(data, dict):
            result = {}
            for key, value in data.items():
                if isinstance(value, (str, bool)):
                    result[key] = value

                elif value := self.post_process(value):
                    result[key] = value
            return result
