import asyncio
import http
import io
import logging
import os
from collections import defaultdict
from io import BytesIO
from itertools import groupby
from operator import attrgetter, or_
from pathlib import Path, PurePath
from typing import TypedDict, Unpack

import pandas as pd
import peewee
from marshmallow import Schema, fields
from peewee import fn
from speedy.peewee_plus import orm
from tornado.httputil import HTTPFile
from utensils.zip import ZipFilePlus
from webargs.tornadoparser import use_kwargs

from remarkable.base_handler import Auth, BaseHandler
from remarkable.common import field_validate
from remarkable.common.apispec_decorators import doc
from remarkable.common.constants import AIStatus, FeatureSchema, FileAnswerMergeStrategy, HistoryAction, PDFParseStatus
from remarkable.common.enums import NafmiiEventStatus, NafmiiEventType, NafmiiTaskType
from remarkable.common.exceptions import CustomError
from remarkable.common.util import arun_singleton_task, generate_timestamp
from remarkable.config import get_config, project_root
from remarkable.db import pw_db
from remarkable.models.nafmii import (
    FileAnswer,
    Knowledge,
    KnowledgeDetail,
    NafmiiFileInfo,
    NafmiiSystem,
    SensitiveWord,
    WordType,
)
from remarkable.models.new_file import NewFile
from remarkable.models.new_user import NewAdminUser
from remarkable.models.query_helper import AsyncPagination
from remarkable.plugins import HTTPFileValidator, Plugin, PostFileValidator
from remarkable.plugins.nafmii.enums import ErrorType, KnowledgeType, TaskStatus
from remarkable.plugins.nafmii.pipeline import prepare_nafmii_answer
from remarkable.plugins.nafmii.schema import (
    CreateKnowledgeDetailSchema,
    CreateKnowledgeSchema,
    CreateProjectSchema,
    CreateSensitiveWordSchema,
    CreateTaskSchema,
    CreateWordTypeSchema,
    ExportSystemLogSchema,
    FileDeleteSchema,
    ListFileSchema,
    ListKnowledgeDetailSchema,
    ListKnowledgeSchema,
    ListSystemLogSchema,
    SearchProjectSchema,
    SearchSensitiveWordSchema,
    UpdateFileAnswerSchema,
    UpdateKnowledgeDetailSchema,
    UpdateKnowledgeSchema,
    UpdateProjectSchema,
    UpdateSensitiveWordSchema,
    UpdateTaskAnswerSchema,
    UploadFileSchema,
)
from remarkable.plugins.nafmii.services import FastDFSClient, NafmiiApiError, NafmiiFileService, _ConfirmStatus
from remarkable.pw_db_services import PeeweeService
from remarkable.pw_models.answer_data import DEFAULT_FILE_ANSWER_MERGE_STRATEGY
from remarkable.pw_models.model import (
    NafmiiEvent,
    NafmiiUser,
    NewFileProject,
    NewFileTree,
    NewHistory,
    NewMold,
    NewSpecialAnswer,
)
from remarkable.pw_models.question import NewQuestion, QuestionWithFK
from remarkable.pw_orm import func
from remarkable.service.compare import CompareStatus
from remarkable.service.new_file_project import NewFileProjectService
from remarkable.service.new_file_tree import get_crumbs

plugin = Plugin(Path(__file__).parent.name)
logger = logging.getLogger(__name__)


def get_task_status(file: NewFile):
    msg = "成功"
    if file.pdf_parse_status in (PDFParseStatus.PENDING, PDFParseStatus.PARSING):
        task_status = TaskStatus.TODO
    elif file.pdf_parse_status in (PDFParseStatus.PDFINSIGHT_PARSING, PDFParseStatus.CACHING, PDFParseStatus.PARSED):
        task_status = TaskStatus.DOING
    elif file.pdf_parse_status in (PDFParseStatus.FAIL, PDFParseStatus.CANCELLED):
        task_status = TaskStatus.FAIL
        msg = ErrorType.PARSE.value
    elif any(q.ai_status == AIStatus.FAILED for q in file.questions):
        task_status = TaskStatus.FAIL
        msg = ErrorType.PREDICT.name
    elif any(q.ai_status == AIStatus.DISABLE for q in file.questions):
        task_status = TaskStatus.FAIL
        msg = ErrorType.MODEL.value
    elif any(q.ai_status == AIStatus.DOING for q in file.questions):
        task_status = TaskStatus.DOING
        msg = ErrorType.MODEL.value
    elif any(ans.status == CompareStatus.FAILED for ans in file.answers):
        task_status = TaskStatus.FAIL
        msg = ErrorType.COMPARE.value
    elif all(ans.status == CompareStatus.DONE for ans in file.answers):
        task_status = TaskStatus.DONE
    else:
        task_status = TaskStatus.DOING
    return msg, task_status


@plugin.route(r"/tasks")
class TaskListHandler(BaseHandler):
    @use_kwargs(CreateTaskSchema, location="json")
    async def post(
        self,
        sys_id,
        user_id,
        username,
        org_code,
        org_name,
        file_type,
        task_types,
        filename,
        file_path,
        file_id,
        keywords,
    ):
        from remarkable.worker.tasks import process_file

        user = await pw_db.first(
            NafmiiUser.select().where(or_(NafmiiUser.ext_id == user_id, NafmiiUser.name == username))
        )
        if not user:
            return self.send_json(
                {"resultCode": "400", "resultMsg": f"user not found, ext_id: {user_id}, name: {username}"}
            )
        async with pw_db.atomic():
            try:
                task = await NafmiiFileService.create_task(
                    sys_id=sys_id,
                    file_type=file_type,
                    task_types=task_types,
                    keywords=keywords,
                    file_id=file_id,
                    filename=filename,
                    file_path=file_path,
                    org_code=org_code,
                    org_name=org_name,
                    user=user,
                )

                await NewHistory.save_operation_history(
                    task.id,
                    user.id,
                    HistoryAction.CREATE_FILE.value,
                    user.name,
                    meta=task.to_dict(),
                )
            except NafmiiApiError as e:
                return self.send_json({"resultCode": e.code, "resultMsg": e.msg})
        await process_file(task)
        item = task.to_dict()
        await NafmiiFileService.add_parse_time_on_file([item])
        return self.send_json(
            {"resultCode": "200", "resultMsg": "成功", "task_id": task.id, "wait_time": item["parse_time"]}
        )


@plugin.route(r"/tasks/(\d+)")
class TaskHandler(BaseHandler):
    async def get(self, task_id: str):
        if not (
            (
                file := await NewFile.get_by_id(
                    task_id,
                    prefetch_queries=[QuestionWithFK.select(), NafmiiFileInfo.select(), FileAnswer.select()],
                )
            )
            and all(fi.sys_id is not None for fi in file.file_info)
        ):
            return self.send_json({"resultCode": "400", "resultMsg": "task not found"})
        msg, task_status = get_task_status(file)
        if task_status == TaskStatus.FAIL:
            code = "400"
        else:
            code = "200"
        data = file.to_dict()
        await NafmiiFileService.add_parse_time_on_file([data])
        return self.send_json(
            {
                "resultCode": code,
                "resultMsg": msg,
                "task_id": file.id,
                "task_status": task_status,
                "wait_time": data["parse_time"],
            }
        )


@plugin.route(r"/projects")
class ProjectListHandler(BaseHandler):
    @Auth("manage_all")
    @use_kwargs(CreateProjectSchema, location="json")
    async def post(self, name, comment, public, default_molds):
        project = await NewFileProject.find_by_kwargs(name=name)
        if project:
            raise CustomError("识别文件集已存在，请勿重复创建")
        async with pw_db.atomic():
            project = await NewFileProjectService.create(
                name,
                uid=self.current_user.id,
                meta={"comment": comment},
                public=public,
                default_molds=default_molds,
            )
            await NewHistory.save_operation_history(
                project.id,
                self.current_user.id,
                HistoryAction.CREATE_PROJECT.value,
                self.current_user.name,
                meta=project.to_dict(),
                nafmii=self.get_nafmii_event(
                    status=NafmiiEventStatus.SUCCEED.value,
                    type=NafmiiEventType.ADD.value,
                    menu="识别文件管理",
                    subject="识别文件集",
                    content="新增识别文件集成功",
                ),
            )

        return self.data(None)

    @Auth("manage_all")
    @use_kwargs(SearchProjectSchema, location="query")
    async def get(self, pid: int, start: int, end: int, name: str, username: str, order_by: str, page: int, size: int):
        file_cte = (
            NewFile.select(fn.COUNT(1).alias("count"), NewFile.pid.alias("id")).group_by(NewFile.pid).cte("file_cte")
        )
        query = (
            NewFileProject.select(
                NewFileProject.id,
                NewFileProject.name,
                NewFileProject.meta,
                NewFileProject.default_molds,
                NewFileProject.created_utc,
                NewFileProject.public,
                NewFileProject.rtree_id,
                NewAdminUser.name.alias("user_name"),
                fn.COALESCE(file_cte.c.count, 0).alias("file_count"),
            )
            .left_outer_join(NewAdminUser, on=(NewFileProject.uid == NewAdminUser.id))
            .left_outer_join(file_cte, on=(NewFileProject.id == file_cte.c.id))
            .where(
                NewFileProject.name.contains(name),
                orm.or_(NewFileProject.public, NewFileProject.uid == self.current_user.id),
            )
        )
        if pid is not None:
            query = query.where(NewFileProject.id == pid)
        if username:
            query = query.where(NewAdminUser.name.contains(username))
        if start:
            query = query.where(NewFileProject.created_utc >= start)
        if end:
            query = query.where(NewFileProject.created_utc <= end)

        query = query.with_cte(file_cte).order_by(getattr(NewFileProject, order_by)).dicts()
        data = await AsyncPagination(query, page, size).data()

        records = await pw_db.execute(
            (
                NewFileProject.select(NewMold.name, NewFileProject.id)
                .join(NewMold, on=func.any_in(NewFileProject.default_molds, NewMold.id))
                .where(NewFileProject.id.in_([item["id"] for item in data["items"]]))
                .order_by(NewFileProject.id)
                .distinct()
            ).namedtuples()
        )
        names_by_pid = defaultdict(list)
        for _pid, items in groupby(records, key=attrgetter("id")):
            names_by_pid[_pid].extend(item.name for item in items)
        for item in data["items"]:
            item["mold_names"] = names_by_pid.get(item["id"], [])

        if self.request.headers.get("x-trigger-source") == "auto":
            return self.data(data)
        if any([pid, username, name, start, end]):
            subject = "识别文件集列表"
            content = "查询识别文件集列表成功"
        else:
            subject = "识别文件集列表页面"
            content = "查看识别文件集列表页面成功"
        await NewHistory.save_operation_history(
            None,
            self.current_user.id,
            HistoryAction.NAFMII_DEFAULT.value,
            self.current_user.name,
            meta=None,
            nafmii=self.get_nafmii_event(
                status=NafmiiEventStatus.SUCCEED.value,
                type=NafmiiEventType.VIEW.value,
                menu="识别文件管理",
                subject=subject,
                content=content,
            ),
        )
        return self.data(data)


@plugin.route(r"/projects/(\d+)")
class ProjectHandler(BaseHandler):
    @Auth("manage_all")
    @use_kwargs(UpdateProjectSchema, location="json")
    async def put(self, pid: str, name: str, comment: str, default_molds: list[int], is_public: bool):
        if not (project := await NewFileProject.get_by_id(pid)):
            return self.error(_("not found project"), status_code=http.HTTPStatus.NOT_FOUND)
        update_data = {}
        if name and name != project.name:
            if await NewFileProject.find_by_kwargs(name=name):
                raise CustomError("识别文件集已存在，请勿重复创建")
            update_data["name"] = name
        if comment is not None:
            meta = project.meta or {}
            meta["comment"] = comment
            update_data["meta"] = meta
        if project.public != is_public and not project.public:
            update_data["public"] = is_public
        if default_molds is not None:
            update_data["default_molds"] = default_molds
        async with pw_db.atomic():
            await project.update_(**update_data)
            if "default_molds" in update_data:
                await pw_db.execute(
                    NewFileTree.update(default_molds=default_molds).where(NewFileTree.id == project.rtree_id)
                )
            if name:
                await pw_db.execute(NewFileTree.update(name=name).where(NewFileTree.id == project.rtree_id))
            await NewHistory.save_operation_history(
                project.id,
                self.current_user.id,
                HistoryAction.MODIFY_PROJECT.value,
                self.current_user.name,
                meta=project.to_dict(),
                nafmii=self.get_nafmii_event(
                    status=NafmiiEventStatus.SUCCEED.value,
                    type=NafmiiEventType.MODIFY.value,
                    menu="识别文件管理",
                    subject="识别文件集",
                    content=f"修改{project.id}{default_molds[0] if default_molds else ''}成功",
                ),
            )
        return self.data(None)


class _ZipFileValidator(PostFileValidator):
    valid_suffixes = [".zip"]


@plugin.route(r"/trees/(\d+)/zips")
class ProjectZipFilesHandler(BaseHandler):
    @Auth("manage_all")
    @use_kwargs(UploadFileSchema, location="form")
    @use_kwargs(
        {"post_zip": fields.Raw(validate=_ZipFileValidator.check, required=True, data_key="file")},
        location="files",
    )
    async def post(self, tree_id: str, post_zip: HTTPFile, mold_id: int, task_types: list[str], keywords: list[str]):
        from remarkable.worker.tasks import process_file

        tree = await NewFileTree.find_by_id(int(tree_id))
        if not tree:
            raise CustomError(_("can't find the tree"), resp_status_code=http.HTTPStatus.NOT_FOUND)

        project = await NewFileProject.find_by_id(tree.pid)
        if not project:
            raise CustomError(_("can't find the project"), resp_status_code=http.HTTPStatus.NOT_FOUND)

        files = []
        with BytesIO(post_zip.body) as f, ZipFilePlus(f) as zipped:
            async with pw_db.atomic():
                for zip_info in zipped.filelist:
                    post_file = HTTPFile(filename=PurePath(zip_info.filename).name, body=zipped.read(zip_info.filename))
                    try:
                        _FileValidator.check(post_file)
                    except CustomError:
                        continue
                    file = await NafmiiFileService.create_file(
                        post_file,
                        project=project,
                        tree_id=tree.id,
                        mold_id=mold_id,
                        source="本地上传",
                        uid=self.current_user.id,
                        task_types=task_types,
                        keywords=keywords,
                    )
                    files.append(file)
                await NewHistory.save_operation_history(
                    None,
                    self.current_user.id,
                    HistoryAction.UPLOAD_ZIP.value,
                    self.current_user.name,
                    meta=None,
                    nafmii=self.get_nafmii_event(
                        status=NafmiiEventStatus.SUCCEED.value,
                        type=NafmiiEventType.ADD.value,
                        menu="识别文件管理",
                        subject="识别任务",
                        content=f"上传文件《{post_zip.filename}》成功",
                    ),
                )

        for file in files:
            await process_file(file)

        return self.data(None)


class _FileValidator(PostFileValidator):
    valid_suffixes = FeatureSchema.from_config().supported_suffixes


@plugin.route(r"/trees/(\d+)/files")
class TreeFileListHandler(BaseHandler):
    @Auth("manage_all")
    @use_kwargs(UploadFileSchema, location="form")
    @use_kwargs(
        {
            "post_file": fields.Raw(validate=_FileValidator.check, required=True, data_key="file"),
        },
        location="files",
    )
    async def post(self, tree_id: str, post_file: HTTPFile, mold_id: int, task_types: list[str], keywords: list[str]):
        from remarkable.worker.tasks import process_file

        tree = await NewFileTree.find_by_id(int(tree_id))
        if not tree:
            raise CustomError(_("can't find the tree"), resp_status_code=http.HTTPStatus.NOT_FOUND)

        project = await NewFileProject.find_by_id(tree.pid)
        if not project:
            raise CustomError(_("can't find the project"), resp_status_code=http.HTTPStatus.NOT_FOUND)

        async with pw_db.atomic():
            file = await NafmiiFileService.create_file(
                post_file,
                project=project,
                tree_id=tree.id,
                mold_id=mold_id,
                source="本地上传",
                uid=self.current_user.id,
                task_types=task_types,
                keywords=keywords,
            )
            await NewHistory.save_operation_history(
                None,
                self.current_user.id,
                HistoryAction.CREATE_FILE.value,
                self.current_user.name,
                meta=None,
                nafmii=self.get_nafmii_event(
                    status=NafmiiEventStatus.SUCCEED.value,
                    type=NafmiiEventType.ADD.value,
                    menu="识别文件管理",
                    subject="识别任务",
                    content=f"上传文件《{file.name}》成功",
                ),
            )
        await process_file(file)
        return self.data(None)

    @Auth(["manage_all", "manage_task"])
    @use_kwargs(ListFileSchema, location="query")
    async def get(self, ptree_id: str, order_by: str, page: int, size: int):
        project_name = await pw_db.scalar(
            NewFileTree.select(NewFileProject.name)
            .join(NewFileProject, on=(NewFileProject.id == NewFileTree.pid))
            .where(NewFileTree.id == int(ptree_id))
        )
        if not project_name:
            raise CustomError(_("can't find the tree"), resp_status_code=http.HTTPStatus.NOT_FOUND)
        res = await NafmiiFileService.list_all(tree_id=ptree_id, page=page, size=size, order_by=order_by)

        if self.request.headers.get("x-trigger-source") == "auto":
            return self.data(res)
        await NewHistory.save_operation_history(
            None,
            self.current_user.id,
            HistoryAction.NAFMII_DEFAULT.value,
            self.current_user.name,
            meta=None,
            nafmii=self.get_nafmii_event(
                status=NafmiiEventStatus.SUCCEED.value,
                type=NafmiiEventType.VIEW.value,
                menu="识别文件管理",
                subject="识别任务列表页面",
                content="查看识别任务列表页面成功",
            ),
        )
        return self.data(res)


@plugin.route(r"/files/(\d+)")
class FileHandler(BaseHandler):
    @Auth(["manage_all", "manage_task"])
    async def get(self, fid):
        file = await NewFile.find_by_id(fid, prefetch_queries=[NafmiiFileInfo.select()])
        if not file:
            raise CustomError(_("not found file"), resp_status_code=http.HTTPStatus.NOT_FOUND)

        data = file.to_dict()
        tree = await NewFileTree.find_by_id(file.tree_id)
        data["task_types"] = [tt for fi in file.file_info for tt in fi.task_types or []]
        data["keywords"] = [kw for fi in file.file_info for kw in fi.keywords or []]
        data["crumbs"] = await get_crumbs(tree.id)

        if self.trigger_source == "label":
            subject = "标注页面"
            content = "查看标注页面成功"
        else:
            subject = "识别详情页"
            content = f"查看{file.id}识别详情页面成功"
        await NewHistory.save_operation_history(
            None,
            self.current_user.id,
            HistoryAction.NAFMII_DEFAULT.value,
            self.current_user.name,
            meta=None,
            nafmii=self.get_nafmii_event(
                status=NafmiiEventStatus.SUCCEED.value,
                type=NafmiiEventType.VIEW.value,
                menu=self.record_menu,
                subject=subject,
                content=content,
            ),
        )

        return self.data(data)


@plugin.route(r"/tasks/(\d+)/answers")
class TaskAnswerHandler(BaseHandler):
    async def get(self, task_id):
        file = await NewFile.find_by_id(
            task_id,
            prefetch_queries=[QuestionWithFK.select(), NafmiiFileInfo.select(), FileAnswer.select()],
        )

        if not (file and file.file_info and all(fi.sys_id is not None for fi in file.file_info)):
            return self.send_json({"resultCode": "400", "resultMsg": "文件不存在"})

        file_info: NafmiiFileInfo = file.file_info[0]
        question: QuestionWithFK = file.questions[0]
        msg, task_status = get_task_status(file)
        if task_status == TaskStatus.DONE:
            if file_info.confirm_status == _ConfirmStatus.confirmed:
                cond = (NewSpecialAnswer.qid == question.id) & (
                    NewSpecialAnswer.answer_type == NewSpecialAnswer.ANSWER_TYPE_NAFMII
                )
                task_answer = await NewSpecialAnswer.get_first_one(cond)
                answer = task_answer.data
            else:
                answer = await prepare_nafmii_answer(file)
        else:
            answer = {"result_info": [], "check_points": [], "words_answers": []}
        return self.send_json(
            {
                "resultCode": "200",
                "resultMsg": msg,
                "task_id": str(file.id),
                "task_status": task_status,
                "afile_id": file_info.revise_file_path,
            }
            | answer
        )

    @use_kwargs(UpdateTaskAnswerSchema, location="json")
    async def post(self, task_id, **kwargs):
        file = await NewFile.find_by_id(
            task_id,
            prefetch_queries=[QuestionWithFK.select(), NafmiiFileInfo.select(), FileAnswer.select()],
        )

        if not (file and file.file_info and all(fi.sys_id is not None for fi in file.file_info)):
            return self.send_json({"resultCode": "400", "resultMsg": "文件不存在"})

        file_info: NafmiiFileInfo = file.file_info[0]
        msg, task_status = get_task_status(file)
        if task_status != TaskStatus.DONE:
            return self.error(_(f"task status is not {TaskStatus.DONE}"))

        async with pw_db.atomic():
            await NafmiiFileInfo.update_by_pk(file_info.id, confirm_status=_ConfirmStatus.confirmed)
            await NewSpecialAnswer.create(
                qid=file.questions[0].id, answer_type=NewSpecialAnswer.ANSWER_TYPE_NAFMII, data=kwargs
            )

        return self.send_json({"resultCode": "200", "resultMsg": "成功", "task_id": task_id})


@plugin.route(r"/files/(\d+)/answer")
class ProjectFileCompareAnswerHandler(BaseHandler):
    @Auth(["manage_all", "manage_task"])
    async def get(self, fid: str):
        answer = await pw_db.first(
            FileAnswer.select(
                FileAnswer.id,
                FileAnswer.diff,
                FileAnswer.keyword,
                FileAnswer.sensitive_word,
                NewFile.source.alias("file_type"),
                NewFile.name,
            )
            .join(NewFile)
            .where(FileAnswer.fid == fid)
            .dicts()
        )
        if self.trigger_source == "auto":
            return self.data(answer)
        await NewHistory.save_operation_history(
            None,
            self.current_user.id,
            HistoryAction.NAFMII_DEFAULT.value,
            self.current_user.name,
            meta=None,
            nafmii=self.get_nafmii_event(
                status=NafmiiEventStatus.SUCCEED.value,
                type=NafmiiEventType.VIEW.value,
                menu="识别任务管理",
                subject="关键字敏感词答案页面",
                content="获取关键字敏感词答案",
            ),
        )

        return self.data(answer)

    @Auth(["manage_all", "manage_task"])
    @use_kwargs(UpdateFileAnswerSchema, location="json")
    async def put(self, fid: str, field: str, words: list[dict]):
        await pw_db.execute(FileAnswer.update(**{field: words}).where(FileAnswer.fid == fid))
        return self.data(None)


@plugin.route(r"/files/(\d+)/revise-file")
class ReviseFileHandler(BaseHandler):
    @Auth("manage_task", "manage_all")
    async def get(self, fid: str):
        file = await NewFile.get_by_id(fid, prefetch_queries=[NafmiiFileInfo.select(), NafmiiSystem.select()])
        if not file or not file.file_info:
            raise CustomError(_("not found file"), resp_status_code=http.HTTPStatus.NOT_FOUND)

        file_info: NafmiiFileInfo = file.file_info[0]
        try:
            if file_info.revise_file_path is None:
                raise FileNotFoundError
            with FastDFSClient(sys=file_info.sys) as client:
                binary_data = client.get_file(file_info.revise_file_path)
        except Exception:
            raise CustomError(
                "文件服务器异常，请联系文件服务管理员处理", resp_status_code=http.HTTPStatus.BAD_REQUEST
            ) from None
        file_name = os.path.splitext(file.name)[0]
        suffix = "批注文件.docx" if file.is_docx else "批注文件.pdf"

        await NewHistory.save_operation_history(
            None,
            action=HistoryAction.NAFMII_DEFAULT,
            user_name=self.current_user.name,
            meta=None,
            uid=self.current_user.id,
            nafmii=self.get_nafmii_event(
                status=NafmiiEventStatus.SUCCEED.value,
                type=NafmiiEventType.EXPORT.value,
                menu=self.record_menu,
                subject="批注文件",
                content="下载批注文件成功",
            ),
        )

        # Set headers to disable browser caching
        self.set_header("Cache-Control", "no-cache, no-store, must-revalidate")
        self.set_header("Pragma", "no-cache")
        self.set_header("Expires", "0")

        await self.export(binary_data, f"{file_name}.{suffix}")


@plugin.route(r"/sensitive-words")
class SensitiveWordListHandler(BaseHandler):
    @use_kwargs(SearchSensitiveWordSchema, location="query")
    async def get(self, page, size, start, end, word_id, name, sys_id, type_id, username, order_by):
        conditions = [orm.TRUE]
        if word_id is not None:
            conditions.append(SensitiveWord.id == word_id)
        if name:
            conditions.append(SensitiveWord.name.contains(name))
        if sys_id is not None:
            conditions.append(SensitiveWord.sys_id == sys_id)
        if type_id is not None:
            conditions.append(SensitiveWord.type_id == type_id)
        if username:
            conditions.append(
                fn.EXISTS(
                    NafmiiUser.select().where(
                        NafmiiUser.id == SensitiveWord.user_id, NafmiiUser.name.contains(username)
                    )
                )
            )
        if start:
            conditions.append(SensitiveWord.created_utc >= start)
        if end:
            conditions.append(SensitiveWord.created_utc <= end)
        query = SensitiveWord.select().where(*conditions)
        data = await AsyncPagination(
            query.order_by(
                getattr(SensitiveWord, order_by),
                SensitiveWord.id.desc() if order_by.startswith("-") else SensitiveWord.id,
            ),
            page,
            size,
        ).data(
            NafmiiUser.select(NafmiiUser.id, NafmiiUser.name),
            WordType.select(),
            NafmiiSystem.select(NafmiiSystem.id, NafmiiSystem.name),
        )
        user = self.current_user or await pw_db.first(NafmiiUser.select().where(NafmiiUser.name == username))
        if not user:
            raise CustomError("无权限访问", resp_status_code=http.HTTPStatus.UNAUTHORIZED)

        if self.request.headers.get("x-trigger-source") == "auto":
            return self.data(data)
        if any([word_id, name, sys_id, type_id, username, start, end]):
            subject = "敏感词管理列表"
            content = "查询敏感词管理列表成功"
        else:
            subject = "敏感词管理列表页"
            content = "查看敏感词管理列表页成功"

        await NewHistory.save_operation_history(
            None,
            action=HistoryAction.NAFMII_DEFAULT,
            user_name=user.name,
            meta=None,
            uid=user.id,
            nafmii=self.get_nafmii_event(
                status=NafmiiEventStatus.SUCCEED.value,
                type=NafmiiEventType.VIEW.value,
                menu="敏感词管理",
                subject=subject,
                content=content,
            ),
        )
        return self.data(data)

    @use_kwargs(CreateSensitiveWordSchema, location="json")
    async def post(self, sys_id: int, type_id: int, name: str, user_id: str, username: str):
        if not self.current_user and not (user_id or username):
            raise CustomError("无权限访问", resp_status_code=http.HTTPStatus.UNAUTHORIZED)
        user = self.current_user or await pw_db.first(
            NafmiiUser.select().where(or_(NafmiiUser.ext_id == user_id, NafmiiUser.name == username))
        )
        if not user:
            raise CustomError("无权限访问", resp_status_code=http.HTTPStatus.UNAUTHORIZED)
        word_type = await WordType.find_by_id(type_id)
        if not word_type:
            raise CustomError("敏感词类型不存在", resp_status_code=http.HTTPStatus.NOT_FOUND)
        sys = await NafmiiSystem.find_by_id(sys_id)
        if not sys:
            raise CustomError("归属系统不存在", resp_status_code=http.HTTPStatus.NOT_FOUND)
        exists = await pw_db.exists(SensitiveWord.select().where(SensitiveWord.name == name, SensitiveWord.sys == sys))
        if not exists:
            sens = await SensitiveWord.create(sys=sys, type=word_type, user_id=user.id, name=name)

            await NewHistory.save_operation_history(
                None,
                action=HistoryAction.NAFMII_DEFAULT,
                user_name=user.name,
                meta=None,
                uid=user.id,
                nafmii=self.get_nafmii_event(
                    status=NafmiiEventStatus.SUCCEED.value,
                    type=NafmiiEventType.ADD.value,
                    menu="敏感词管理",
                    subject="敏感词",
                    content=f"新增敏感词{sens.id}成功",
                ),
            )
        else:
            await NewHistory.save_operation_history(
                None,
                action=HistoryAction.NAFMII_DEFAULT,
                user_name=user.name,
                meta=None,
                uid=user.id,
                nafmii=self.get_nafmii_event(
                    status=NafmiiEventStatus.FAILED.value,
                    type=NafmiiEventType.ADD.value,
                    menu="敏感词管理",
                    subject="敏感词",
                    content=f"归属系统中{sys}中敏感词{name}已存在",
                ),
            )
            raise CustomError("敏感词已存在", resp_status_code=http.HTTPStatus.CONFLICT) from None
        return self.data(None)


class _ExcelValidator(PostFileValidator):
    valid_suffixes = (".xlsx",)


@plugin.route(r"/sensitive-words/file")
class SensitiveWordFileHandler(BaseHandler):
    @Auth("manage_all")
    async def get(self):
        path = PurePath(f"{project_root}").joinpath("data/nafmii/sensitive_template.xlsx")
        user = self.current_user
        await NewHistory.save_operation_history(
            None,
            action=HistoryAction.NAFMII_DEFAULT,
            user_name=user.name,
            meta=None,
            uid=user.id,
            nafmii=self.get_nafmii_event(
                status=NafmiiEventStatus.SUCCEED.value,
                type=NafmiiEventType.EXPORT.value,
                menu="敏感词管理",
                subject="敏感词导入模板",
                content="下载敏感词导入模板成功",
            ),
        )
        await self.export(path.as_posix(), file_name="敏感词模板.xlsx")

    @Auth("manage_all")
    @use_kwargs({"files": fields.List(fields.Raw(validate=_ExcelValidator.check), data_key="file")}, location="files")
    @use_kwargs({"sys_id": fields.Int()}, location="form")
    async def post(self, sys_id: int, files: list[HTTPFile]):
        user = self.current_user
        sys = await NafmiiSystem.find_by_id(sys_id)
        if not sys:
            await self.record_failed()
            raise CustomError("归属系统不存在", resp_status_code=http.HTTPStatus.NOT_FOUND)
        word_types = {
            name: word_id for name, word_id in await pw_db.execute(WordType.select(WordType.name, WordType.id).tuples())
        }
        row_by_name = {}
        for file in files:
            df = pd.read_excel(
                BytesIO(file.body),
                dtype={
                    "敏感词": str,
                    "敏感词类型": str,
                },
            )
            if df.size == 0:
                await self.record_failed()
                raise CustomError(f"{file.filename}内容为空", resp_status_code=http.HTTPStatus.BAD_REQUEST)
            if set(df.columns.tolist()) != {"敏感词", "敏感词类型"}:
                await self.record_failed()
                raise CustomError(
                    f"{file.filename}格式错误，请修改后重新上传", resp_status_code=http.HTTPStatus.BAD_REQUEST
                )
            types = df["敏感词类型"].unique().tolist()
            if extra_types := set(types).difference(word_types):
                await self.record_failed()
                raise CustomError(
                    f"{file.filename}内容错误，{','.join(extra_types)}敏感词类型不存在，请修改后重新上传",
                    resp_status_code=http.HTTPStatus.BAD_REQUEST,
                )
            for row in df.itertuples(index=False):
                row_by_name[row[0]] = {
                    "name": row[0],
                    "type_id": word_types[row[1]],
                    "sys_id": sys_id,
                    "user_id": self.current_user.id,
                }
        exist_names = await pw_db.scalars(
            SensitiveWord.select(SensitiveWord.name).where(
                SensitiveWord.name.in_(list(row_by_name)), SensitiveWord.sys_id == sys_id
            )
        )
        for name in exist_names:
            row_by_name.pop(name, None)
        if not row_by_name:
            await self.record_failed()
            return self.error(message="文件中的敏感词已存在，没有新的敏感词被导入")
        async with pw_db.atomic():
            await SensitiveWord.bulk_insert(row_by_name.values())

        await NewHistory.save_operation_history(
            None,
            action=HistoryAction.NAFMII_DEFAULT,
            user_name=user.name,
            meta=None,
            uid=user.id,
            nafmii=self.get_nafmii_event(
                status=NafmiiEventStatus.SUCCEED.value,
                type=NafmiiEventType.ADD.value,
                menu="敏感词管理",
                subject="敏感词",
                content="导入文件新增敏感词成功",
            ),
        )
        return self.data(None)

    async def record_failed(self):
        user = self.current_user
        await NewHistory.save_operation_history(
            None,
            action=HistoryAction.NAFMII_DEFAULT,
            user_name=user.name,
            meta=None,
            uid=user.id,
            nafmii=self.get_nafmii_event(
                status=NafmiiEventStatus.FAILED.value,
                type=NafmiiEventType.ADD.value,
                menu="敏感词管理",
                subject="敏感词",
                content="导入文件新增敏感词失败",
            ),
        )


@plugin.route(r"/sensitive-words/(\d+)")
class SensitiveWordHandler(BaseHandler):
    @Auth("manage_all")
    @use_kwargs(UpdateSensitiveWordSchema, location="json")
    async def put(self, word_id: int, name: str, sys_id: int, type_id: int):
        word = await SensitiveWord.find_by_id(word_id)
        if not word:
            raise CustomError("敏感词不存在", resp_status_code=http.HTTPStatus.NOT_FOUND)
        param = {}
        if name is not None:
            param["name"] = name
        if sys_id is not None:
            sys = await NafmiiSystem.find_by_id(sys_id)
            if not sys:
                raise CustomError("归属系统不存在", resp_status_code=http.HTTPStatus.NOT_FOUND)
            param["sys"] = sys
        if type_id is not None:
            word_type = await WordType.find_by_id(type_id)
            if not word_type:
                raise CustomError("敏感词类型不存在", resp_status_code=http.HTTPStatus.NOT_FOUND)
            param["type"] = word_type
        try:
            await word.update_(**param)

            await NewHistory.save_operation_history(
                None,
                action=HistoryAction.NAFMII_DEFAULT,
                user_name=self.current_user.name,
                meta=None,
                uid=self.current_user.id,
                nafmii=self.get_nafmii_event(
                    status=NafmiiEventStatus.SUCCEED.value,
                    type=NafmiiEventType.MODIFY.value,
                    menu="敏感词管理",
                    subject="敏感词",
                    content=f"修改敏感词{word.id}成功",
                ),
            )
        except peewee.IntegrityError:
            await NewHistory.save_operation_history(
                None,
                action=HistoryAction.NAFMII_DEFAULT,
                user_name=self.current_user.name,
                meta=None,
                uid=self.current_user.id,
                nafmii=self.get_nafmii_event(
                    status=NafmiiEventStatus.FAILED.value,
                    type=NafmiiEventType.MODIFY.value,
                    menu="敏感词管理",
                    subject="敏感词",
                    content=f"修改敏感词{name}失败",
                ),
            )
            raise CustomError("敏感词已存在", resp_status_code=http.HTTPStatus.CONFLICT) from None
        return self.data(None)

    @Auth("manage_all")
    async def delete(self, word_id: int):
        word = await SensitiveWord.find_by_id(word_id)
        if not word:
            raise CustomError("敏感词不存在", resp_status_code=http.HTTPStatus.NOT_FOUND)
        await pw_db.delete(word)

        await NewHistory.save_operation_history(
            None,
            action=HistoryAction.NAFMII_DEFAULT,
            user_name=self.current_user.name,
            meta=None,
            uid=self.current_user.id,
            nafmii=self.get_nafmii_event(
                status=NafmiiEventStatus.SUCCEED.value,
                type=NafmiiEventType.DELETE.value,
                menu="敏感词管理",
                subject="敏感词",
                content=f"删除敏感词{word.id}成功",
            ),
        )
        return self.data(None)


@plugin.route(r"/word-types")
class WordTypeHandler(BaseHandler):
    @Auth("manage_all")
    async def get(self):
        records = await pw_db.execute(WordType.select(WordType.id, WordType.name).order_by(WordType.id.desc()).dicts())
        return self.data(list(records))

    @Auth("manage_all")
    @use_kwargs(CreateWordTypeSchema)
    async def post(self, name: str):
        try:
            word_type = await WordType.create(name=name)
        except peewee.IntegrityError:
            raise CustomError("item already exists", resp_status_code=http.HTTPStatus.CONFLICT) from None
        return self.data(word_type.to_dict())


@plugin.route(r"/systems")
class SystemHandler(BaseHandler):
    @Auth("manage_all")
    async def get(self):
        query = NafmiiSystem.select(NafmiiSystem.id, NafmiiSystem.name).order_by(NafmiiSystem.id.desc())
        return self.data(list(await pw_db.execute(query.dicts())))


@plugin.route(r"/config")
class ConfigHandler(BaseHandler):
    @Auth("manage_all")
    async def get(self):
        config = {}
        readonly_molds = get_config("client.readonly_molds")
        if readonly_molds is not None:
            config["readonly_molds"] = readonly_molds.split(";")
        else:
            config["readonly_molds"] = []
        return self.data(config)


@plugin.route(r"/files")
class FileBatchHandler(BaseHandler):
    @Auth(["manage_all", "manage_task"])
    @use_kwargs(FileDeleteSchema)
    async def delete(self, file_ids: list[int], tree_ids: list):
        service = PeeweeService.create()
        async with pw_db.atomic():
            await pw_db.execute(FileAnswer.delete().where(FileAnswer.fid.in_(file_ids)))
            files = await pw_db.execute(NewFile.select().where(NewFile.id.in_(file_ids)))
            for file in files:
                await NewHistory.save_operation_history(
                    file.id,
                    self.current_user.id,
                    HistoryAction.DELETE_FILE.value,
                    self.current_user.name,
                    meta=file.to_dict(),
                    nafmii=self.get_nafmii_event(
                        status=NafmiiEventStatus.SUCCEED.value,
                        type=NafmiiEventType.DELETE.value,
                        menu=self.record_menu,
                        subject="识别任务",
                        content=f"删除{file.id}成功",
                    ),
                )
                await file.soft_delete()
            trees = await pw_db.execute(NewFileTree.select().where(NewFileTree.id.in_(tree_ids)))
            for tree in trees:
                await NewHistory.save_operation_history(
                    tree.id,
                    self.current_user.id,
                    HistoryAction.DELETE_TREE.value,
                    self.current_user.name,
                    meta=tree.to_dict(),
                    nafmii=self.get_nafmii_event(
                        status=NafmiiEventStatus.SUCCEED.value,
                        type=NafmiiEventType.DELETE.value,
                        menu=self.record_menu,
                        subject="文件夹",
                        content=f"删除文件夹{tree.id}成功",
                    ),
                )
                await service.trees.delete_by_tree(tree)
        return self.data(None)


@plugin.route(r"/knowledge-types")
class KnowledgeTypeHandler(BaseHandler):
    @Auth("manage_all")
    async def get(self):
        return self.data([k.dict() for k in KnowledgeType])  # noqa


@plugin.route(r"/knowledges")
class KnowledgeListHandler(BaseHandler):
    @Auth("manage_all")
    @use_kwargs(ListKnowledgeSchema, location="query")
    async def get(
        self, page: int, size: int, id_: int, type_: int, name: str, username: str, start: int, end: int, order_by: str
    ):
        conditions = []
        if id_ is not None:
            conditions.append(Knowledge.id == id_)
        if type_ is not None:
            conditions.append(Knowledge.type == type_)
        if name:
            conditions.append(Knowledge.name.contains(name))
        if start is not None:
            conditions.append(Knowledge.created_utc >= start)
        if end is not None:
            conditions.append(Knowledge.created_utc <= end)
        if username:
            conditions.append(NafmiiUser.name.contains(username))
        query = (
            Knowledge.select(
                Knowledge.id,
                Knowledge.name,
                Knowledge.type,
                NafmiiUser.jsonb_build_object("id", "name").alias("user"),
                Knowledge.created_utc,
                Knowledge.updated_utc,
            )
            .join(NafmiiUser, peewee.JOIN.LEFT_OUTER)
            .where(*conditions)
            .order_by(
                getattr(Knowledge, order_by),
                Knowledge.id.desc() if order_by.startswith("-") else Knowledge.id.asc(),
            )
        )
        data = await AsyncPagination(query.dicts(), page=page, size=size).data()
        for item in data["items"]:
            item["type"] = KnowledgeType(item["type"]).dict()

        if self.request.headers.get("x-trigger-source") == "auto":
            return self.data(data)
        if any([id_, type_, name, username, start, end]):
            subject = "数据知识列表"
            content = "查询数据知识列表成功"
        else:
            subject = "数据知识列表页"
            content = "查看数据知识列表页成功"
        await NewHistory.save_operation_history(
            None,
            action=HistoryAction.NAFMII_DEFAULT,
            user_name=self.current_user.name,
            meta=None,
            uid=self.current_user.id,
            nafmii=self.get_nafmii_event(
                status=NafmiiEventStatus.SUCCEED.value,
                type=NafmiiEventType.VIEW.value,
                menu="数据知识管理",
                subject=subject,
                content=content,
            ),
        )
        return self.data(data)

    @Auth("manage_all")
    @use_kwargs(CreateKnowledgeSchema, location="json")
    async def post(self, name: str, type_: int):
        exists = await pw_db.exists(Knowledge.select().where(Knowledge.name == name, Knowledge.type == type_))
        if not exists:
            knowledge = await pw_db.create(Knowledge, name=name, type=type_, user=self.current_user)
            await NewHistory.save_operation_history(
                None,
                action=HistoryAction.NAFMII_DEFAULT,
                user_name=self.current_user.name,
                meta=None,
                uid=self.current_user.id,
                nafmii=self.get_nafmii_event(
                    status=NafmiiEventStatus.SUCCEED.value,
                    type=NafmiiEventType.ADD.value,
                    menu="数据知识管理",
                    subject="数据知识",
                    content=f"新增数据知识{knowledge.id}成功",
                ),
            )
        else:
            await NewHistory.save_operation_history(
                None,
                action=HistoryAction.NAFMII_DEFAULT,
                user_name=self.current_user.name,
                meta=None,
                uid=self.current_user.id,
                nafmii=self.get_nafmii_event(
                    status=NafmiiEventStatus.FAILED.value,
                    type=NafmiiEventType.ADD.value,
                    menu="数据知识管理",
                    subject="数据知识",
                    content=f"数据知识{name}已存在，请勿重复添加",
                ),
            )
            raise CustomError("数据知识已存在，请勿重复添加", resp_status_code=http.HTTPStatus.CONFLICT) from None
        return self.data(None)


@plugin.route(r"/knowledges/(\d+)")
class KnowledgeHandler(BaseHandler):
    @Auth("manage_all")
    @use_kwargs(UpdateKnowledgeSchema, location="json")
    async def put(self, model_id: str, **kwargs):
        knowledge = await Knowledge.find_by_id(model_id)
        try:
            await knowledge.update_(**kwargs)
            await NewHistory.save_operation_history(
                None,
                action=HistoryAction.NAFMII_DEFAULT,
                user_name=self.current_user.name,
                meta=None,
                uid=self.current_user.id,
                nafmii=self.get_nafmii_event(
                    status=NafmiiEventStatus.SUCCEED.value,
                    type=NafmiiEventType.MODIFY.value,
                    menu="数据知识管理",
                    subject="数据知识",
                    content=f"编辑数据知识{knowledge.id}成功",
                ),
            )
        except peewee.IntegrityError:
            await NewHistory.save_operation_history(
                None,
                action=HistoryAction.NAFMII_DEFAULT,
                user_name=self.current_user.name,
                meta=None,
                uid=self.current_user.id,
                nafmii=self.get_nafmii_event(
                    status=NafmiiEventStatus.FAILED.value,
                    type=NafmiiEventType.MODIFY.value,
                    menu="数据知识管理",
                    subject="数据知识",
                    content="数据知识已存在，请勿重复添加",
                ),
            )
            raise CustomError("数据知识已存在，请勿重复添加", resp_status_code=http.HTTPStatus.CONFLICT) from None
        return self.data(None)

    @Auth("manage_all")
    async def delete(self, model_id: str):
        knowledge = await Knowledge.find_by_id(model_id)
        if knowledge is None:
            return self.error("数据知识不存在", status_code=http.HTTPStatus.NOT_FOUND)
        await pw_db.delete(knowledge)
        await NewHistory.save_operation_history(
            None,
            action=HistoryAction.NAFMII_DEFAULT,
            user_name=self.current_user.name,
            meta=None,
            uid=self.current_user.id,
            nafmii=self.get_nafmii_event(
                status=NafmiiEventStatus.SUCCEED.value,
                type=NafmiiEventType.DELETE.value,
                menu="数据知识管理",
                subject="数据知识",
                content=f"删除数据知识{knowledge.id}成功",
            ),
        )
        return self.data(None)

    @Auth("manage_all")
    @use_kwargs(ListKnowledgeDetailSchema, location="query")
    async def get(self, model_id: str, type_: int, title: str):
        subquery = KnowledgeDetail.select(
            KnowledgeDetail.id,
            KnowledgeDetail.type,
            KnowledgeDetail.title,
            KnowledgeDetail.content,
            KnowledgeDetail.file_path,
            KnowledgeDetail.filename,
            KnowledgeDetail.created_utc,
            KnowledgeDetail.knowledge,
        )

        if type_ is not None:
            subquery = subquery.where(KnowledgeDetail.type == type_)

        if title:
            subquery = subquery.where(KnowledgeDetail.title.contains(title))

        knowledge = await Knowledge.find_by_id(
            model_id,
            [
                subquery.order_by(KnowledgeDetail.id.desc()),
                NafmiiUser.select(NafmiiUser.id, NafmiiUser.name),
            ],
        )
        item = knowledge.to_dict(extra_attrs=["details"])
        item["details"] = [detail.to_dict(exclude=[KnowledgeDetail.knowledge]) for detail in item["details"]]
        if any([type_, title]):
            subject = "知识列表"
            content = "查询知识列表成功"
        else:
            subject = "数据知识详情页"
            content = "查看数据知识详情页成功"

        await NewHistory.save_operation_history(
            None,
            action=HistoryAction.NAFMII_DEFAULT,
            user_name=self.current_user.name,
            meta=None,
            uid=self.current_user.id,
            nafmii=self.get_nafmii_event(
                status=NafmiiEventStatus.SUCCEED.value,
                type=NafmiiEventType.VIEW.value,
                menu="数据知识管理",
                subject=subject,
                content=content,
            ),
        )
        return self.data(item)


async def save_file(file: HTTPFile):
    def inner():
        with FastDFSClient(system) as client:
            return client.save_file(file)

    file_path = filename = ""
    if file is not None:
        filename = file.filename
        system = await NafmiiSystem.find_by_id(0)
        file_path = await asyncio.to_thread(inner)

    return {"file_path": file_path, "filename": filename}


@plugin.route(r"/knowledges/(\d+)/details")
class KnowledgeDetailListHandler(BaseHandler):
    @Auth("manage_all")
    @use_kwargs(CreateKnowledgeDetailSchema, location="form")
    @use_kwargs(
        {
            "file": fields.Raw(
                validate=HTTPFileValidator((".pdf",), get_config("client.file_size_limit") or 20),
                load_default=None,
                data_key="file",
            )
        },
        location="files",
    )
    async def post(self, model_id: str, type_: int, title: str, content: str, file: HTTPFile):
        knowledge = await Knowledge.find_by_id(model_id)
        if knowledge is None:
            return self.error("数据知识不存在", status_code=http.HTTPStatus.NOT_FOUND)
        file_meta = await save_file(file)
        await pw_db.create(KnowledgeDetail, knowledge=knowledge, type=type_, title=title, content=content, **file_meta)

        await NewHistory.save_operation_history(
            None,
            action=HistoryAction.NAFMII_DEFAULT,
            user_name=self.current_user.name,
            meta=None,
            uid=self.current_user.id,
            nafmii=self.get_nafmii_event(
                status=NafmiiEventStatus.SUCCEED.value,
                type=NafmiiEventType.ADD.value,
                menu="数据知识管理",
                subject="知识",
                content=f"数据知识{knowledge.id}新增知识成功",
            ),
        )
        return self.data(None)


@plugin.route(r"/knowledge-details/(\d+)")
class KnowledgeDetailHandler(BaseHandler):
    @Auth("manage_all")
    @use_kwargs(UpdateKnowledgeDetailSchema, location="form")
    @use_kwargs(
        {
            "file": fields.Raw(
                validate=HTTPFileValidator((".pdf",), get_config("client.file_size_limit") or 20),
                load_default=None,
                data_key="file",
            )
        },
        location="files",
    )
    async def put(self, model_id: str, file: HTTPFile, **kwargs):
        detail = await KnowledgeDetail.find_by_id(model_id)
        if file is not None:
            kwargs.update(await save_file(file))
        if kwargs.get("file_path") == "":
            kwargs["filename"] = ""
        kwargs = {k: v for k, v in kwargs.items() if v is not None}
        await detail.update_(**kwargs)

        await NewHistory.save_operation_history(
            None,
            action=HistoryAction.NAFMII_DEFAULT,
            user_name=self.current_user.name,
            meta=None,
            uid=self.current_user.id,
            nafmii=self.get_nafmii_event(
                status=NafmiiEventStatus.SUCCEED.value,
                type=NafmiiEventType.MODIFY.value,
                menu="数据知识管理",
                subject="文件/词条",
                content=f"修改数据知识{detail.id}文件/词条成功",
            ),
        )
        return self.data(None)

    @Auth("manage_all")
    async def delete(self, model_id: str):
        detail = await KnowledgeDetail.find_by_id(model_id)
        if detail is not None:
            await detail.soft_delete()

        await NewHistory.save_operation_history(
            None,
            action=HistoryAction.NAFMII_DEFAULT,
            user_name=self.current_user.name,
            meta=None,
            uid=self.current_user.id,
            nafmii=self.get_nafmii_event(
                status=NafmiiEventStatus.SUCCEED.value,
                type=NafmiiEventType.DELETE.value,
                menu="数据知识管理",
                subject="知识",
                content=f"删除数据知识-{detail.id}成功",
            ),
        )
        return self.data(None)


@plugin.route(r"/knowledge-details/(\d+)/file")
class KnowledgeDetailFileHandler(BaseHandler):
    @Auth("manage_all")
    async def get(self, model_id: str):
        detail = await KnowledgeDetail.find_by_id(model_id)
        system = await NafmiiSystem.find_by_id(0)

        await NewHistory.save_operation_history(
            None,
            action=HistoryAction.NAFMII_DEFAULT,
            user_name=self.current_user.name,
            meta=None,
            uid=self.current_user.id,
            nafmii=self.get_nafmii_event(
                status=NafmiiEventStatus.SUCCEED.value,
                type=NafmiiEventType.VIEW.value,
                menu="数据知识管理",
                subject="文件",
                content=f"查看数据知识{detail.id}-文件成功",
            ),
        )
        with FastDFSClient(system) as client:
            content = client.get_file(detail.file_path)

        self.set_header("Content-Type", "application/octet-stream")
        self.write(content)


class SystemLogParams(TypedDict):
    start: int | None
    end: int | None
    username: str | None
    user_id: str | None
    type: str | None
    status: int | None
    menu: str | None
    subject: str | None


@plugin.route(r"/events")
class SystemEventsHandler(BaseHandler):
    @Auth("manage_all")
    @use_kwargs(ListSystemLogSchema, location="query")
    async def get(self, page: int, size: int, **kwargs: Unpack[SystemLogParams]):
        query = NafmiiEvent.select(NafmiiEvent, NafmiiUser.name.alias("user_name")).join(NafmiiUser)

        if kwargs["start"] is not None:
            query = query.where(NafmiiEvent.created_utc >= kwargs["start"])  # noqa
        if kwargs["end"] is not None:
            query = query.where(NafmiiEvent.created_utc <= kwargs["end"])
        if kwargs["username"]:
            query = query.where(NafmiiUser.name.contains(kwargs["username"]))
        if kwargs["user_id"] is not None:
            query = query.where(NafmiiUser.id == kwargs["user_id"])
        if kwargs["menu"] is not None:
            query = query.where(NafmiiEvent.menu.contains(kwargs["menu"]))
        if kwargs["subject"] is not None:
            query = query.where(NafmiiEvent.subject.contains(kwargs["subject"]))
        if NafmiiEventType.ALL != kwargs["type"]:
            query = query.where(NafmiiEvent.type == (kwargs["type"]))
        if NafmiiEventStatus.ALL != kwargs["status"]:
            query = query.where(NafmiiEvent.status == (kwargs["status"]))
        if any([kwargs["username"], kwargs["user_id"], kwargs["menu"], kwargs["subject"]]):
            subject = "系统日志列表"
            content = "查询系统日志列表成功"
        else:
            subject = "系统日志列表页"
            content = "查看系统日志列表页成功"
        await NewHistory.save_operation_history(
            None,
            action=HistoryAction.NAFMII_DEFAULT,
            user_name=self.current_user.name,
            meta=None,
            uid=self.current_user.id,
            nafmii=self.get_nafmii_event(
                status=NafmiiEventStatus.SUCCEED.value,
                type=NafmiiEventType.VIEW.value,
                menu="系统日志管理",
                subject=subject,
                content=content,
            ),
        )
        data = await AsyncPagination(query.order_by(NafmiiEvent.id.desc()).dicts(), page=page, size=size).data()
        return self.data(data)


@plugin.route(r"/events/(\d+)")
class SystemEventHandler(BaseHandler):
    @Auth("manage_all")
    async def get(self, model_id: str):
        event = await NafmiiEvent.find_by_id(model_id, NafmiiUser.select(NafmiiUser.id, NafmiiUser.name))
        if event is None:
            return self.error("日志不存在", status_code=http.HTTPStatus.NOT_FOUND)
        return self.data(event.to_dict(exclude=[NafmiiEvent.history]))


@plugin.route(r"/events/export")
class SystemEventExportHandler(BaseHandler):
    @Auth("manage_all")
    @use_kwargs(ExportSystemLogSchema, location="query")
    async def get(self, start: int, end: int):
        records = await pw_db.execute(
            NafmiiEvent.select(
                NafmiiEvent.created_utc.alias("时间"),
                NafmiiUser.name.alias("用户"),
                NafmiiEvent.user_id.alias("用户ID"),
                NafmiiEvent.menu.alias("功能菜单"),
                NafmiiEvent.type.alias("类型"),
                NafmiiEvent.subject.alias("对象"),
                NafmiiEvent.status.alias("状态"),
                NafmiiEvent.ip.alias("IP地址"),
                NafmiiEvent.client.alias("浏览器版本"),
            )
            .join(NafmiiUser)
            .where(
                NafmiiEvent.created_utc >= start,
                NafmiiEvent.created_utc <= end,
            )
            .order_by(NafmiiEvent.id.desc())
            .dicts()
        )

        for record in records:
            record["类型"] = NafmiiEventType(record["类型"]).values[1]
            record["状态"] = NafmiiEventStatus(record["状态"]).values[1]

        df = pd.DataFrame(records)
        if df.size == 0:
            return self.error("没有数据")

        await NewHistory.save_operation_history(
            None,
            action=HistoryAction.NAFMII_DEFAULT,
            user_name=self.current_user.name,
            meta=None,
            uid=self.current_user.id,
            nafmii=self.get_nafmii_event(
                status=NafmiiEventStatus.SUCCEED.value,
                type=NafmiiEventType.EXPORT.value,
                menu="系统日志管理",
                subject="日志",
                content="导出日志成功",
            ),
        )
        with io.BytesIO() as buffer:
            df = df[["时间", "用户", "用户ID", "功能菜单", "类型", "对象", "状态", "IP地址", "浏览器版本"]]
            df["时间"] = (
                pd.to_datetime(df["时间"], unit="s", utc=True)
                .dt.tz_convert("Asia/Shanghai")
                .dt.strftime("%Y-%m-%d %H:%M:%S")
            )
            df.to_excel(buffer, index=False)
            start_date = pd.Timestamp(start, unit="s", tz="UTC").tz_convert("Asia/Shanghai").strftime("%Y-%m-%d")
            end_date = pd.Timestamp(end, unit="s", tz="UTC").tz_convert("Asia/Shanghai").strftime("%Y-%m-%d")
            return await self.export(buffer.getvalue(), f"智能文本识别系统日志-{start_date}--{end_date}.xlsx")


class PredictFileHandlerSchema(Schema):
    dirs = fields.List(fields.Int(), load_default=list)
    fids = fields.List(fields.Int(), load_default=list)
    merge_strategy = fields.Str(
        load_default=DEFAULT_FILE_ANSWER_MERGE_STRATEGY,
        validate=field_validate.OneOf(FileAnswerMergeStrategy.member_values()),
    )
    task = fields.Str(required=True, validate=field_validate.OneOf(["predict"]))


@plugin.route(r"/files/execute")
class PredictFileHandler(BaseHandler):
    @doc(summary="文件批量预测/审核", tag="file-management")
    @Auth("browse")
    @use_kwargs(PredictFileHandlerSchema, location="json")
    async def post(self, task: str, dirs: list[int], fids: list[int], merge_strategy: str):
        if not (dirs or fids):
            return self.error(_("Invalid input parameters."), status_code=http.HTTPStatus.BAD_REQUEST)
        fids += await NewFileTree.get_fids(*dirs)
        lock_expired = get_config("web.run_lock_expired", 600)
        for fid in sorted(fids, reverse=True):
            get_lock, lock = await arun_singleton_task(self._do, task, fid, merge_strategy, lock_expired=lock_expired)
            if not get_lock:
                await NewHistory.save_operation_history(
                    None,
                    self.current_user.id,
                    HistoryAction.NAFMII_DEFAULT.value,
                    self.current_user.name,
                    meta=None,
                    nafmii=self.get_nafmii_event(
                        status=NafmiiEventStatus.FAILED.value,
                        type=NafmiiEventType.MODIFY.value,
                        menu=self.record_menu,
                        subject="识别任务",
                        content=f"重新识别{fid}失败",
                    ),
                )
                raise CustomError(
                    f"操作过于频繁,  请至少间隔{max(1, lock_expired // 60)}分钟",
                    resp_status_code=http.HTTPStatus.TOO_MANY_REQUESTS,
                )
        await NewHistory.save_operation_history(
            None,
            self.current_user.id,
            HistoryAction.NAFMII_DEFAULT.value,
            self.current_user.name,
            meta=None,
            nafmii=self.get_nafmii_event(
                status=NafmiiEventStatus.SUCCEED.value,
                type=NafmiiEventType.MODIFY.value,
                menu=self.record_menu,
                subject="识别任务",
                content=f"重新识别{fids[0]}成功",
            ),
        )
        return self.data({})

    @staticmethod
    async def _do(task: str, fid: int, merge_strategy: str):
        if task != "predict":
            raise CustomError("Invalid task type")

        await pw_db.execute(NewFile.update(updated_utc=generate_timestamp()).where(NewFile.id == fid))
        await pw_db.execute(NafmiiFileInfo.update(revise_file_path=None).where(NafmiiFileInfo.file_id == fid))
        await pw_db.execute(
            NewQuestion.update(updated_utc=generate_timestamp(), ai_status=AIStatus.TODO).where(NewQuestion.fid == fid)
        )
        file = await pw_db.first(NewFile.select().where(NewFile.id == fid))
        logger.info(f"{file.id=}, {file.name=} preset nafmii answer")
        from remarkable.hooks.nafmii import NafmiiInsightHook

        await NafmiiInsightHook(file).__call__()

        task_types = await pw_db.scalar(
            NafmiiFileInfo.select(NafmiiFileInfo.task_types).where(NafmiiFileInfo.file == file)
        )
        if NafmiiTaskType.T001 in task_types:
            from remarkable.worker.tasks.predict_tasks import preset_answer_by_fid_task

            preset_answer_by_fid_task.delay(fid, force_predict=True, file_answer_merge_strategy=merge_strategy)
