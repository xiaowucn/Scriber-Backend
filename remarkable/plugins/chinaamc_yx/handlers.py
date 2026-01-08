import http
import logging
import pickle
from collections import Counter
from contextlib import suppress
from datetime import date, datetime, time, timezone
from itertools import chain
from operator import and_
from pathlib import Path
from typing import NamedTuple, TypedDict
from uuid import uuid4

import httpx
import peewee
import zstandard
from peewee import fn
from speedy.peewee_plus import orm
from webargs import fields

from remarkable.base_handler import Auth, BaseHandler
from remarkable.common import field_validate
from remarkable.common.apispec_decorators import use_kwargs
from remarkable.common.constants import (
    AIStatus,
    ChinaAMCChapterDiffStatus,
    ChinaAmcCompareStatus,
    ChinaAmcFileStatus,
    ChinaAmcProjectSource,
    ChinaAmcProjectStatus,
    HistoryAction,
)
from remarkable.common.exceptions import CustomError
from remarkable.config import get_config
from remarkable.db import pw_db
from remarkable.models.chinaamc_yx import ChinaamcProject, CompareTask, FileAnswer, ProjectInfo, UserInfo
from remarkable.models.new_file import NewFile
from remarkable.models.new_user import NewAdminUser
from remarkable.models.query_helper import AsyncPagination
from remarkable.plugins import Plugin, PostFileValidator
from remarkable.plugins.chinaamc_yx.schemas import I_SELF_CONFIG, file_type_kwargs
from remarkable.plugins.chinaamc_yx.service import ChinaAmcYxFileService
from remarkable.plugins.chinaamc_yx.tasks import run_chapter_diff_task, run_compare_task
from remarkable.pw_models.model import NewFileProject, NewHistory, NewMold
from remarkable.pw_models.question import NewQuestion, QuestionWithFK
from remarkable.service.chinaamc_yx import (
    ChinaamcProjectService,
    DiffResult,
    MinimalFile,
    MinimalTask,
    TaskStatusCalculator,
    is_file_ready,
    is_ready_to_diff,
)
from remarkable.worker.tasks import process_file

plugin = Plugin(Path(__file__).parent.name)
logger = logging.getLogger(__name__)


async def decrypt_file(file_content: bytes):
    uri = get_config("chinaamc_yx.crypt.decrypt_url")

    headers = {"method~name": "fileDecryptionRest", "data~fileOffset": "0", "data~counSize": str(len(file_content))}

    async with httpx.AsyncClient(transport=httpx.AsyncHTTPTransport(verify=False, retries=3), timeout=60) as client:
        response = await client.post(uri, headers=headers, content=file_content)
        return_flag = response.headers.get("data~returnFlag", "1")
        if return_flag == "0":
            return response.content
        if return_flag == "2":
            return file_content
        logger.error("解密失败, return_flag: %s, return_tip: %s", return_flag, response.headers.get("data~returnTip"))
    raise CustomError(f"文件解密失败, {return_flag=}", resp_status_code=http.HTTPStatus.BAD_REQUEST)


@plugin.route(r"/sec-server/s/rs/uni/")
class DecryptHandler(BaseHandler):
    def post(self):
        self.set_header("data~returnFlag", "0")
        self.write(self.request.body)


@plugin.route(r"/projects")
class ProjectsHandler(BaseHandler):
    """目前只有客户会走调用接口创建项目的流程, 界面上只能在创建比对任务的同时创建项目"""

    param = {
        "name": fields.Str(),
        "source": fields.Int(
            load_default=ChinaAmcProjectSource.XINGYUN.value,
            validate=field_validate.OneOf(ChinaAmcProjectSource.member_values()),
        ),
        "deptid": fields.Str(load_default=""),
    }

    @Auth("browse")
    @use_kwargs(param, location="json")
    async def post(self, name: str, source: int, deptid: str):
        """
        通过项目名称查找已存在的来源为星云系统的项目, 否则就创建一个新的
        """
        from_xingyun = fn.EXISTS(
            ProjectInfo.select(1).where(
                ProjectInfo.project == ChinaamcProject.id,
                ProjectInfo.source == ChinaAmcProjectSource.XINGYUN,
            )
        )
        if project := await pw_db.first(
            ChinaamcProject.select(ChinaamcProject.id, ChinaamcProject.name)
            .where(ChinaamcProject.name == name, from_xingyun)
            .dicts()
        ):
            return self.data(project)

        user_dept_ids = await pw_db.first(UserInfo.select(UserInfo.dept_ids).where(UserInfo.user == self.current_user))
        dept_ids = [deptid] if deptid else user_dept_ids

        async with pw_db.atomic():
            project = await ChinaamcProjectService.create(
                name,
                uid=self.current_user.id,
                source=source,
                dept_ids=dept_ids or [],
            )
            await NewHistory.save_operation_history(
                project.id,
                self.current_user.id,
                HistoryAction.CREATE_PROJECT.value,
                self.current_user.name,
                meta=project.to_dict(),
            )

        return self.data(project.to_dict(only=[NewFileProject.id, NewFileProject.name]))


@plugin.route(r"/projects/(\d+)")
class ProjectHandler(BaseHandler):
    param = {"name": fields.Str()}

    @Auth("browse")
    @use_kwargs(param, location="json")
    async def put(self, pid: str, name: str):
        project = await ChinaamcProject.get_by_id(pid)
        assert project is not None, CustomError(_("not found project"), resp_status_code=404)
        await pw_db.update(project, name=name)
        return self.data(None)


@plugin.route(r"/projects/(\d+)/files")
class ProjectFilesHandler(BaseHandler):
    @Auth("browse")
    @use_kwargs(file_type_kwargs, location="form")
    @use_kwargs(
        {
            "post_files": fields.List(
                fields.Raw(validate=PostFileValidator.check),
                required=True,
                data_key="file",
                validate=field_validate.Length(min=1, max=5),
            )
        },
        location="files",
    )
    async def post(self, pid: str, post_files, file_type: str):
        project = await ChinaamcProject.get_by_id(pid)
        if not project:
            return self.error(_("not found project"), status_code=404)

        data = []
        new_files = []
        for file in post_files:
            new_file = await ChinaAmcYxFileService.create(
                project, file.filename, file.body, file_type, self.current_user.id
            )
            data.append(new_file.to_dict())
            new_files.append(new_file)
        for new_file in new_files:
            await process_file(new_file)
        return self.data(data)


@plugin.route(r"/projects/(\d+)/compare-tasks")
class ProjectCompareTaskHandler(BaseHandler):
    """用于星云系统创建比对任务"""

    @Auth("browse")
    @use_kwargs({"fids": fields.List(fields.Int(required=True))}, location="json")
    async def post(self, pid: str, fids: list[int]):
        files = await pw_db.execute(NewFile.select().where(NewFile.pid == pid, NewFile.id.in_(fids)))
        counter = Counter(x.source for x in files)
        for file_type in I_SELF_CONFIG.file_types:
            if counter[file_type.name] > file_type.quantity_limit:
                raise CustomError(f"{file_type.name}数量超过限制", resp_status_code=400)
        if not is_file_ready(files):
            raise CustomError(
                "缺少必选文档, 请勾选《基金合同》、《招募说明书》和《托管协议》后重新提交", resp_status_code=400
            )
        today = date.today()
        async with pw_db.atomic():
            project = await ChinaamcProject.get_by_id(
                pid,
                CompareTask.select(include_deleted=True).where(
                    CompareTask.created_utc > datetime.combine(today, time(), timezone.utc).timestamp()
                ),
                for_update=True,
            )
            name = f"{project.name}{today.strftime('%Y%m%d')}"
            if len(project.compare_tasks) > 0:
                name = f"{name}({len(project.compare_tasks)})"
            try:
                task = await pw_db.create(
                    CompareTask,
                    pid=pid,
                    uid=self.current_user.id,
                    fids=[file.id for file in files],
                    name=name,
                    started=True,
                )
            except peewee.IntegrityError as e:
                raise CustomError("任务名称已存在", resp_status_code=400) from e
        if await is_ready_to_diff(files):
            run_compare_task.delay(task.id)
        return self.data(task.to_dict(only=[CompareTask.id, CompareTask.name]))


class CompareStatusByTask(TypedDict):
    task_id: int
    status: int


class FileWithStatus(NamedTuple):
    id: int
    name: str
    source: str
    created_utc: int
    pdf_parse_status: int
    ai_statuses: list[int]
    compare_statuses: list[CompareStatusByTask]


@plugin.route(r"/compare-tasks")
class CompareTaskListHandler(BaseHandler):
    """Scriber中创建/查看比对任务"""

    param = {"name": fields.Str(required=True, validate=field_validate.Length(min=1))}

    @Auth("browse")
    @use_kwargs(param, location="json")
    async def post(self, name: str):
        dept_ids = await pw_db.scalars(
            UserInfo.select(fn.UNNEST(UserInfo.dept_ids)).where(UserInfo.user == self.current_user)
        )
        async with pw_db.atomic():
            try:
                project = await ChinaamcProjectService.create(
                    f"{name}_{uuid4().hex}",  # 确保每次的项目名称都不一样
                    uid=self.current_user.id,
                    source=ChinaAmcProjectSource.LOCAL.value,
                    dept_ids=dept_ids,
                )
                await NewHistory.save_operation_history(
                    project.id,
                    self.current_user.id,
                    HistoryAction.CREATE_PROJECT.value,
                    self.current_user.name,
                    meta=project.to_dict(),
                )
                await pw_db.create(CompareTask, name=name, pid=project.id, uid=self.current_user.id)
            except peewee.IntegrityError as e:
                raise CustomError("任务名称已存在", resp_status_code=400) from e
        return self.data(None)

    @Auth("browse")
    @use_kwargs(AsyncPagination.web_args, location="query")
    async def get(self, page: int, size: int):
        pid = self.get_secure_cookie("pid")
        query = (
            CompareTask.select(
                CompareTask.id,
                CompareTask.fids,
                CompareTask.name,
                CompareTask.status,
                CompareTask.started,
                CompareTask.chapter_status,
                fn.COALESCE(ProjectInfo.source, ChinaAmcProjectSource.LOCAL).alias("source"),
                CompareTask.created_utc,
                NewAdminUser.name.alias("user_name"),
            )
            .join(NewAdminUser)
            .left_outer_join(ProjectInfo, on=(ProjectInfo.project == CompareTask.project))
            .where(
                orm.TRUE if self.current_user.is_admin else CompareTask.user == self.current_user,
                CompareTask.project == pid if pid else orm.TRUE,
            )
            .order_by(CompareTask.id.desc())
            .dicts()
        )
        res = await AsyncPagination(query, page, size).data()

        records = await pw_db.execute(
            NewFile.select(
                NewFile.id,
                NewFile.source,
                NewFile.name,
                NewFile.pdf_parse_status,
                NewFile.created_utc,
                fn.ARRAY_AGG(NewQuestion.ai_status).alias("ai_statuses"),
                fn.JSONB_AGG(
                    fn.JSONB_BUILD_OBJECT(
                        "task_id",
                        FileAnswer.task_id,
                        "status",
                        FileAnswer.status,
                    )
                ).alias("compare_statuses"),
            )
            .left_outer_join(NewQuestion, on=(NewFile.id == NewQuestion.fid))
            .left_outer_join(
                FileAnswer,
                on=and_(NewFile.id == FileAnswer.fid, FileAnswer.task_id.in_([task["id"] for task in res["items"]])),
            )
            .where(
                NewFile.source.is_null(False),
                NewFile.id.in_(set(chain.from_iterable(task["fids"] for task in res["items"]))),
            )
            .group_by(NewFile.id)
            .namedtuples()
        )
        record_by_fid: dict[int, FileWithStatus] = {record.id: record for record in records}

        for task in res["items"]:
            files = [record_by_fid[fid] for fid in task["fids"] if fid in record_by_fid]
            compare_status_by_fid = {
                file.id: compare_status["status"] or 0
                for file in files
                for compare_status in file.compare_statuses
                if compare_status["task_id"] is None or compare_status["task_id"] == task["id"]
            }
            task["files"] = [
                {
                    "id": file.id,
                    "file_type": file.source,
                    "name": file.name,
                    "created_utc": file.created_utc,
                }
                for fid in set(task["fids"])
                if (file := record_by_fid.get(fid))
            ]
            task["files"] = sorted(task["files"], key=CompareTaskFilesHandler.sort_file_type)

            calculator = TaskStatusCalculator(
                task=MinimalTask.model_validate(task),
                files=[
                    MinimalFile(
                        id=file["id"],
                        source=file["file_type"],
                        ai_statuses=record_by_fid[file["id"]].ai_statuses,
                        pdf_parse_status=record_by_fid[file["id"]].pdf_parse_status,
                        compare_status=compare_status_by_fid.get(file["id"], 0),
                    )
                    for file in task["files"]
                ],
            )
            task["status"] = calculator.status
            task["retryable"] = calculator.retryable
            for file in task["files"]:
                file["status"] = calculator.status_by_fid[file["id"]]

        return self.data(res)


@plugin.route(r"/compare-tasks/(\d+)")
class CompareTaskHandler(BaseHandler):
    @Auth("browse")
    async def delete(self, task_id: str):
        task = await CompareTask.get_by_id(task_id)
        assert task is not None, CustomError("比对任务不存在", resp_status_code=404)
        await pw_db.update(task, deleted_utc=datetime.utcnow().timestamp())
        return self.data(None)


@plugin.route(r"/compare-tasks/(\d+)/sync")
class CompareTaskSyncHandler(BaseHandler):
    @Auth("browse")
    async def get(self, task_id: str):
        rows = []
        task = await CompareTask.get_by_id(task_id, (NewAdminUser.select(), ChinaamcProject.select()))
        if not task:
            return self.error("比对比对任务不存在", status_code=404)
        rows.append(task)
        for user in await pw_db.execute(UserInfo.select().where(UserInfo.user == task.user)):
            rows.append(user)
        for project in await pw_db.execute(ProjectInfo.select().where(ProjectInfo.project == task.project)):
            rows.append(project)
        for answer in await pw_db.execute(FileAnswer.select().where(FileAnswer.task == task)):
            rows.append(answer)

        cctx = zstandard.ZstdCompressor()
        return self.write(cctx.compress(pickle.dumps(rows)))


async def check_file_type(task: CompareTask, file_type: str):
    sources = await pw_db.scalars(NewFile.select(NewFile.source).where(NewFile.id.in_(task.fids)))
    counter = Counter(sources)
    counter.update([file_type])
    for file_type in I_SELF_CONFIG.file_types:
        if counter[file_type.name] > file_type.quantity_limit:
            return False
    return True


@plugin.route(r"/compare-tasks/(\d+)/files")
class CompareTaskFilesHandler(BaseHandler):
    @Auth("browse")
    @use_kwargs(file_type_kwargs, location="form")
    @use_kwargs(
        {
            "files": fields.List(
                fields.Raw(validate=PostFileValidator.check),
                required=True,
                data_key="file",
                validate=field_validate.Length(max=5),
            )
        },
        location="files",
    )
    async def post(self, task_id: str, files: list, file_type: str):
        for file in files:
            # force_decrypt为false时才会通过文件头判断是否加密
            logger.info("start to decrypt file in task %s", task_id)
            if not get_config("chinaamc_yx.crypt.force_decrypt"):
                with suppress(UnicodeDecodeError):
                    if not file.body[:32].decode("latin-1").replace("\x00", "").endswith("E-SafeNetLOCK"):
                        continue

            logger.info("decrypted file signature: %s", file.body[:32].decode("latin-1"))
            file.body = await decrypt_file(file.body)
        async with pw_db.atomic():
            task = await CompareTask.get_by_id(task_id, ChinaamcProject.select(), for_update=True)
            assert task is not None, CustomError("比对任务不存在", resp_status_code=404)

            if not await check_file_type(task, file_type):
                return self.error("文档类型不符合要求", status_code=400)

            data = []
            new_files = []
            for file in files:
                new_file = await ChinaAmcYxFileService.create(
                    task.project, file.filename, file.body, file_type, self.current_user.id
                )
                data.append(new_file.to_dict())
                await pw_db.update(task, fids=sorted(set(task.fids) | {new_file.id}))
                new_files.append(new_file)
        for file in new_files:
            await process_file(file)
        return self.data(data)

    @Auth("browse")
    async def get(self, task_id: str):
        task = await CompareTask.get_by_id(task_id)
        query = (
            NewFile.select(
                NewFile.id,
                NewFile.name,
                NewFile.created_utc,
                NewFile.source.alias("file_type"),
                NewFile.pdf_parse_status,
                fn.MIN(fn.COALESCE(FileAnswer.status, 0)).alias("compare_status"),
                fn.ARRAY_AGG(fn.COALESCE(NewQuestion.ai_status, AIStatus.TODO)).alias("ai_statuses"),
            )
            .left_outer_join(FileAnswer, on=and_(NewFile.id == FileAnswer.fid, FileAnswer.task_id == task.id))
            .left_outer_join(NewQuestion, on=(NewFile.id == NewQuestion.fid))
            .where(NewFile.id.in_(task.fids))
            .group_by(NewFile.id)
            .dicts()
        )
        files = sorted(await pw_db.execute(query), key=self.sort_file_type)
        for file in files:
            file["status"] = MinimalFile.model_validate({**file, "source": file["file_type"]}).status
        return self.data(files)

    @staticmethod
    def sort_file_type(item: dict):
        with suppress(ValueError):
            return I_SELF_CONFIG.valid_types.index(item["file_type"]), item["id"]
        return 100, item["id"]


@plugin.route(r"/compare-tasks/(\d+)/files/(\d+)")
class CompareTaskFileHandler(BaseHandler):
    @Auth("browse")
    async def delete(self, task_id: str, fid: str):
        async with pw_db.atomic():
            task = await CompareTask.get_by_id(task_id, for_update=True)
            assert task is not None, CustomError("比对任务不存在", resp_status_code=404)
            file = await NewFile.get_by_id(fid)
            assert file is not None, CustomError(_("not found file"), resp_status_code=404)
            await pw_db.update(task, fids=sorted(set(task.fids) - {file.id}))
        return self.data(None)


@plugin.route(r"/compare-tasks/(\d+)/files/(\d+)/answer")
class ProjectFileCompareAnswerHandler(BaseHandler):
    @Auth("browse")
    async def get(self, task_id: str, fid: str):
        answer = await pw_db.first(FileAnswer.select().where(FileAnswer.fid == fid, FileAnswer.task_id == task_id))
        return self.data(answer.to_dict(exclude=[FileAnswer.task, FileAnswer.file], extra_attrs=["task_id", "fid"]))


@plugin.route(r"/compare-tasks/(\d+)/consistency-answer")
class CompareConsistencyAnswerHandler(BaseHandler):
    @Auth("browse")
    async def get(self, task_id: str):
        answer = await pw_db.first(
            CompareTask.select(
                CompareTask.id,
                CompareTask.consistency_status,
                CompareTask.consistency_answer,
                fn.JSONB_AGG(
                    fn.JSONB_BUILD_OBJECT("id", NewFile.id, "name", NewFile.name, "file_type", NewFile.source)
                ).alias("files"),
            )
            .join(NewFile, on=(NewFile.id == fn.ANY(CompareTask.fids)))
            .where(CompareTask.id == task_id)
            .group_by(CompareTask.id)
            .dicts()
        )
        assert answer is not None, CustomError("比对任务不存在", resp_status_code=404)
        assert answer["consistency_status"] == ChinaAmcCompareStatus.DONE.value, CustomError(
            "一致性比对尚未完成", resp_status_code=400
        )
        return self.data(answer)


@plugin.route(r"/compare-tasks/(\d+)/chapter-diff-answer")
class ChapterDiffAnswerHandler(BaseHandler):
    @Auth("browse")
    @use_kwargs(
        {"doc_type": fields.Str(validate=field_validate.OneOf(list(DiffResult.model_fields)))},
        location="query",
    )
    async def get(self, task_id: str, doc_type: str = None):
        task = await CompareTask.get_by_id(task_id, fields=(CompareTask.chapter_status, CompareTask.chapter_answer))
        if task is None:
            return self.error("比对任务不存在", status_code=404)
        if task.chapter_status != ChinaAMCChapterDiffStatus.DONE:
            return self.error("章节比对尚未完成", status_code=400)
        return self.data(task.chapter_answer[doc_type] if doc_type else task.chapter_answer)


@plugin.route(r"/compare-tasks/(\d+)/actions/start")
class CompareTaskStartHandler(BaseHandler):
    @Auth("browse")
    async def get(self, task_id: int):
        async with pw_db.atomic():
            task = await CompareTask.get_by_id(task_id, ChinaamcProject.select(), for_update=True)
            if not task:
                return self.error(_("not found project"), status_code=404)
            query = NewFile.select(NewFile.id).where(
                fn.EXISTS(
                    NewQuestion.select(1).where(NewFile.id == NewQuestion.fid, NewQuestion.ai_status == AIStatus.FINISH)
                ),  # 此环境暂无多schema
                NewFile.id.in_(task.fids),
            )
            finish_fids = await pw_db.scalars(query)
            await pw_db.update(task, started=True)
            if set(finish_fids).issuperset(task.fids):
                run_compare_task.delay(task.id)
        return self.data(None)


@plugin.route(r"/compare-tasks/(\d+)/actions/redo")
class CompareTaskRedoHandler(BaseHandler):
    @Auth("browse")
    async def get(self, task_id: int):
        redo_files = []
        async with pw_db.atomic():
            task = await CompareTask.get_by_id(task_id, ChinaamcProject.select(), for_update=True)
            if not task:
                raise CustomError("任务不存在", resp_status_code=404)
            files = await pw_db.prefetch(NewFile.select().where(NewFile.id.in_(task.fids)), QuestionWithFK.select())
            calculator = TaskStatusCalculator(
                MinimalTask.model_validate(task),
                files=[
                    MinimalFile.model_validate(file).with_ai_statuses(
                        [question.ai_status for question in file.questions]
                    )
                    for file in files
                ],
            )
            if not calculator.retryable:
                raise CustomError("处理中, 无法重试", resp_status_code=400)
            await pw_db.update(task, started=True, status=0, chapter_status=0)
            if calculator.status == ChinaAmcProjectStatus.DIFF_DONE:
                redo_files.extend(files)
            elif calculator.status == ChinaAmcProjectStatus.DIFF_FAILED:
                run_compare_task.delay(task.id)
            else:
                for file in files:
                    if calculator.status_by_fid[file.id] <= ChinaAmcFileStatus.AI_FINISH:
                        redo_files.append(file)
            await pw_db.execute(
                NewQuestion.update(ai_status=AIStatus.DOING).where(
                    NewQuestion.fid.in_([file.id for file in redo_files])
                )
            )
        for file in redo_files:
            await process_file(file, force_predict=True)
        return self.data(None)


@plugin.route(r"/compare-tasks/(\d+)/chapter-diff/actions/redo")
class CompareTaskChapterRedoHandler(BaseHandler):
    @Auth("browse")
    async def get(self, task_id: int):
        async with pw_db.atomic():
            task = await CompareTask.get_by_id(task_id, ChinaamcProject.select(), for_update=True)
            if not task:
                raise CustomError("任务不存在", resp_status_code=404)
            if task.chapter_status != ChinaAMCChapterDiffStatus.FAILED:
                raise CustomError("只能重试章节比对失败的任务", resp_status_code=400)
        run_chapter_diff_task.delay(task.id)
        return self.data(None)


@plugin.route(r"/projects/(\d+)/view")
class SingleCompareTaskViewHandler(BaseHandler):
    @Auth("browse")
    async def get(self, pid: str):
        self.set_secure_cookie("pid", pid)
        return self.redirect("/#/chinaamc_yx/tasks")


@plugin.route(r"/projects/view")
class CompareTaskViewHandler(BaseHandler):
    @Auth("browse")
    async def get(self):
        self.clear_cookie("pid")
        return self.redirect("/#/chinaamc_yx/tasks")


@plugin.route(r"/samples")
class SamplesHandler(BaseHandler):
    @Auth("browse")
    async def get(self):
        project_name = get_config("chinaamc_yx.sample_project")
        project = await NewFileProject.find_by_kwargs(name=project_name)
        if not project:
            return self.error("范文不存在", status_code=404)
        query = (
            NewFile.select(NewFile.id.alias("fid"), NewQuestion.id.alias("qid"), NewMold.name.alias("mold_name"))
            .join(NewQuestion, on=(NewFile.id == NewQuestion.fid))
            .join(NewMold, on=(NewQuestion.mold == NewMold.id))
        )

        files = await pw_db.execute(query.where(NewFile.pid == project.id).dicts())
        ret = {}
        for file in files:
            ret[file["mold_name"]] = file

        if not ret:
            return self.error("范文不存在", status_code=404)

        return self.data(ret)
