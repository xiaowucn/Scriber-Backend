import json
import logging
import shlex
import subprocess
from collections import OrderedDict
from dataclasses import dataclass, field
from enum import IntEnum
from pathlib import Path, PurePath
from tempfile import TemporaryDirectory
from typing import Literal, TypedDict, Unpack

import peewee
from peewee import fn
from pydantic import ConfigDict, Field
from tornado.httputil import HTTPFile

from remarkable.common.constants import (
    INTERACTION_COST,
    SCANNED_PDF_MULTIPLIER,
    TIME_MULTIPLIER,
    AIStatus,
    PDFParseStatus,
)
from remarkable.common.enums import NafmiiTaskType as TaskType
from remarkable.common.exceptions import CustomError
from remarkable.config import get_config, project_root
from remarkable.db import pw_db
from remarkable.models.nafmii import FileAnswer, NafmiiFileInfo, NafmiiSystem, SensitiveWord, WordType
from remarkable.models.new_file import NewFile
from remarkable.models.new_user import NewAdminUser
from remarkable.models.query_helper import AsyncPagination
from remarkable.pdfinsight.reader import PdfinsightReader
from remarkable.plugins import HTTPFileValidator
from remarkable.plugins.nafmii.diff import single_file_diff
from remarkable.plugins.nafmii.word import KeywordPredictor, SensitiveWordPredictor
from remarkable.pw_models.model import NewFileProject, NewFileTree, NewMold, NewTimeRecord
from remarkable.pw_models.question import NewQuestion
from remarkable.pw_orm import func
from remarkable.schema import PaginateSchema
from remarkable.service.compare import CompareStatus
from remarkable.service.new_file import NewFileService
from remarkable.service.new_file_tree import get_crumbs
from remarkable.service.page_counter import DocumentInspector

logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)


class PaginationParam(TypedDict):
    page: int
    size: int
    order_by: str


class ListFileParam(PaginationParam):
    tree_id: str


class ExitCode(IntEnum):
    SUCCESS = 0
    INVALID_ARGUMENTS = 1
    INVALID_JSON = 2
    MISSING_PARAMETERS = 3
    CONNECTION_TIMEOUT = 4
    CONNECTION_FAILED = 5
    DOWNLOAD_FAILED = 6
    UPLOAD_FAILED = 7
    UNEXPECTED_ERROR = 8
    CONFIG_ERROR = 9


class CreateTaskParam(TypedDict):
    sys_id: int
    user: NewAdminUser
    file_id: str
    filename: str
    file_path: str
    file_type: str
    keywords: list[str]
    task_types: list[str]
    org_code: str
    org_name: str


class _ConfirmStatus(IntEnum):
    all = 1
    pending = 2
    confirmed = 3


ORDER_BY_FIELD = Literal[
    "-created_utc",
    "created_utc",
    "-insight_queue_stamp",
    "insight_queue_stamp",
    "-insight_parse_stamp",
    "insight_parse_stamp",
]


class SearchFileSchema(PaginateSchema):
    model_config = ConfigDict(populate_by_name=True)

    mold_id: int | None = Field(None)
    task_id: int | None = Field(None, alias="id")
    task_types: list[str] = Field(default_factory=list, description="任务类型列表")
    filename: str = Field("", description="文件名", alias="name")
    username: str = Field("", description="用户名", alias="user_name")
    confirm_status: _ConfirmStatus = Field(_ConfirmStatus.all, description="确认状态")
    start: int = Field(0, description="开始时间")
    end: int = Field(0, description="结束时间")
    answered: bool | None = Field(None, description="是否已回答")
    order_by: ORDER_BY_FIELD = Field("-created_utc", description="排序字段")
    file_type: str | None = Field(None, description="文件类型")
    sys_id: int | None = Field(None, description="文件来源")
    status: int | None = Field(None, description="预处理状态")
    pdf_status: PDFParseStatus | None = Field(None, description="预处理状态")
    ai_status: AIStatus | None = Field(None, description="预测状态")


def run_command(command: str):
    logger.info("exec command:  %s", command)
    with subprocess.Popen(command, shell=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE) as sub_process:
        stdout, stderr = sub_process.communicate(timeout=60)
    if sub_process.returncode != 0:
        logger.error(f"{stdout=}, {stderr=}")
        raise Exception(ExitCode(sub_process.returncode).name)
    return stdout.decode()


@dataclass
class FastDFSClient:
    sys: NafmiiSystem
    _dir: TemporaryDirectory = field(init=False, default_factory=TemporaryDirectory)

    @property
    def _save_path(self):
        return Path(self._dir.name).joinpath("file")

    def _send(self, action: Literal["u", "d"], data: dict):
        command = [
            "java",
            "-jar",
            f"{project_root}/data/nafmii/FastDFS-0.0.3.jar",
            f"-{action}",
            shlex.quote(json.dumps(data)),
        ]
        try:
            return run_command(" ".join(command))
        except Exception as e:
            logger.exception(e)
            raise CustomError("get file from dubbo service failed") from e

    def get_file(self, file_id: str) -> bytes:
        data = {
            "fileId": file_id,
            "zookeeper": self.sys.registry,
            "partnerId": self.sys.partner_id,
            "savePath": self._save_path.as_posix(),
        }
        self._send("d", data)
        return self._save_path.read_bytes()

    def save_file(self, file: HTTPFile) -> str:
        path = Path(self._dir.name).joinpath("file")
        path.write_bytes(file.body)
        data = {
            "filePath": path.as_posix(),
            "fileType": PurePath(file.filename).suffix[1:],
            "zookeeper": self.sys.registry,
            "partnerId": self.sys.partner_id,
        }
        text = self._send("u", data)
        return json.loads(text)["fileId"]

    def __enter__(self):
        self._dir.__enter__()
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        self._dir.__exit__(exc_type, exc_val, exc_tb)


@dataclass
class NafmiiApiError(Exception):
    code: str
    msg: str


class NafmiiFileService:
    @classmethod
    async def create_file(
        cls,
        post_file: HTTPFile,
        project: NewFileProject,
        tree_id: int,
        mold_id: int,
        task_types: list[str],
        uid: int,
        source: str,
        keywords: list[str],
    ) -> NewFile:
        sys = await NafmiiSystem.find_by_id(0)
        with FastDFSClient(sys) as client:
            file_path = client.save_file(post_file)
        file = await NewFileService.create_file(
            post_file.filename,
            post_file.body,
            molds=[mold_id] if mold_id else [],
            pid=project.id,
            tree_id=tree_id,
            uid=uid,
            source=source,
            use_default_molds=False,
        )
        await NafmiiFileInfo.create(sys=sys, task_types=task_types, file=file, keywords=keywords, ext_path=file_path)
        return file

    @classmethod
    async def create_task(cls, **kwargs: Unpack[CreateTaskParam]):
        """
        用于外部系统创建任务, 对应内部的file
        """

        sys = await NafmiiSystem.find_by_id(kwargs["sys_id"])
        if not sys:
            raise NafmiiApiError(msg=f"system {kwargs['sys_id']} not found", code="400")
        pid = get_config(f"nafmii.file_types.{kwargs['file_type']}.pid")
        if not pid:
            raise NafmiiApiError(msg=f"pid of {kwargs['file_type']} not configured ", code="400")
        project = await NewFileProject.find_by_id(pid)
        if not project:
            raise NafmiiApiError(msg=f"project {pid} not found", code="400")

        validator = HTTPFileValidator(
            (".doc", ".docx", ".pdf", ".xlsx", ".xls", ".jpeg", ".jpg", ".png", ".ppt", ".pptx"),
            get_config("client.file_size_limit") or 20,
        )
        with FastDFSClient(sys) as client:
            content = client.get_file(kwargs["file_path"])
            post_file = HTTPFile(filename=kwargs["filename"], body=content)
            validator.__call__(post_file)
            file = await NewFileService.create_file(
                post_file.filename,
                post_file.body,
                molds=project.default_molds,
                pid=project.id,
                tree_id=project.rtree_id,
                uid=kwargs["user"].id,
                source=sys.name,
            )
            await NafmiiFileInfo.create(
                task_types=kwargs["task_types"],
                file=file,
                sys=sys,
                ext_id=kwargs["file_id"],
                ext_path=kwargs["file_path"],
                org_name=kwargs["org_name"],
                org_code=kwargs["org_code"],
                keywords=kwargs["keywords"],
            )
        return file

    @classmethod
    async def search_all(
        cls,
        schema: SearchFileSchema,
        mark_user: NewAdminUser,
        project: NewFileProject | None = None,
        user: NewAdminUser | None = None,
    ):
        query = cls.get_file_query()
        if schema.filename:
            query = query.where(NewFile.name.contains(schema.filename))
        if user is not None:
            query = query.where(NewFile.uid == user.id)
        if project is not None:
            query = query.where(NewFile.project == project)
        if schema.username:
            query = query.where(NewAdminUser.name.contains(schema.username))
        if schema.task_id is not None:
            query = query.where(NewFile.id == schema.task_id)
        if schema.mold_id is not None:
            query = query.where(NewFile.molds.contains(schema.mold_id))
        if schema.confirm_status != _ConfirmStatus.all:
            query = query.where(NafmiiFileInfo.confirm_status == schema.confirm_status)
        if schema.start:
            query = query.where(NewFile.created_utc >= schema.start)
        if schema.end:
            query = query.where(NewFile.created_utc <= schema.end)
        if schema.task_types:
            query = query.where(NafmiiFileInfo.task_types.contains_any(schema.task_types))
        if schema.sys_id is not None:
            query = query.where(NafmiiFileInfo.sys_id == schema.sys_id)
        if schema.file_type:
            pid = get_config(f"nafmii.file_types.{schema.file_type}.pid")
            if not pid:
                raise NafmiiApiError(msg=f"pid of {schema.file_type} not configured ", code="400")
            query = query.where(NewFile.project == int(pid))
        if schema.pdf_status is not None:
            if schema.pdf_status == PDFParseStatus.PARSING:
                query = query.where(
                    NewFile.pdf_parse_status.in_(
                        [
                            PDFParseStatus.PARSED,
                            PDFParseStatus.CACHING,
                            PDFParseStatus.PARSING,
                            PDFParseStatus.PDFINSIGHT_PARSING,
                        ]
                    )
                )
            else:
                query = query.where(NewFile.pdf_parse_status == schema.pdf_status)
        subquery = NewQuestion.select().where(NewQuestion.fid == NewFile.id)
        if schema.answered:
            query = query.where(fn.EXISTS(subquery.where(NewQuestion.mark_uids.contains([mark_user.id]))))
        if schema.ai_status is not None:
            query = query.where(fn.EXISTS(subquery.where(NewQuestion.ai_status == schema.ai_status)))
        if schema.status is not None:
            query = query.where(fn.EXISTS(subquery.where(NewQuestion.status == schema.status)))

        order_by = getattr(NewFile, schema.order_by, getattr(NewTimeRecord, schema.order_by))

        res = await AsyncPagination(
            query.order_by(order_by, NewFile.id.desc() if schema.order_by.startswith("-") else NewFile.id).dicts(),
            schema.page,
            schema.size,
        ).data()
        await NafmiiFileService.add_parse_time_on_file(res["items"])
        if project is not None:
            res["crumbs"] = await get_crumbs(project.rtree_id)
        return res

    @classmethod
    async def list_all(cls, **kwargs: Unpack[ListFileParam]):
        res = {"total": 0, "trees": [], "files": [], "page": kwargs["page"], "size": kwargs["size"]}

        mold_cte = (
            NewMold.select(
                func.ARRAY_AGG(NewMold.name).alias("mold_names"),
                NewFileTree.id,
            )
            .join(NewFileTree, on=func.any_in(NewFileTree.default_molds, NewMold.id))
            .group_by(NewFileTree.id)
            .cte("mold_cte")
        )
        query = (
            NewFileTree.select(
                NewFileTree.id,
                NewFileTree.name,
                NewFileTree.meta,
                NewFileTree.pid,
                NewFileTree.ptree_id,
                NewFileTree.uid,
                NewFileTree.default_molds,
                NewAdminUser.name.alias("user_name"),
                NewFileTree.created_utc,
                NewFileTree.updated_utc,
                fn.COALESCE(mold_cte.c.mold_names, func.build_array()).alias("mold_names"),
            )
            .join(NewAdminUser, peewee.JOIN.LEFT_OUTER, on=(NewFileTree.uid == NewAdminUser.id))
            .join(mold_cte, peewee.JOIN.LEFT_OUTER, on=(NewFileTree.id == mold_cte.c.id))
            .where(NewFileTree.ptree_id == kwargs["tree_id"])
            .order_by(NewFileTree.id.desc())
            .with_cte(mold_cte)
            .dicts()
        )
        tree_res = await AsyncPagination(query, kwargs["page"], kwargs["size"]).data()
        res["total"] += tree_res["total"]
        res["trees"].extend(tree_res["items"])

        if len(res["trees"]) < kwargs["size"]:
            query = cls.get_file_query()
            query = query.where(NewFile.tree_id == kwargs["tree_id"])
            file_count = await pw_db.count(query)
            offset = max((kwargs["page"] - 1) * kwargs["size"] - res["total"], 0)
            query = query.limit(kwargs["size"] - len(res["trees"])).offset(offset)
            order_by = getattr(NewFile, kwargs["order_by"], getattr(NewTimeRecord, kwargs["order_by"]))
            file_res = await pw_db.execute(
                query.order_by(
                    order_by, NewFile.id.desc() if kwargs["order_by"].startswith("-") else NewFile.id
                ).dicts()
            )
            res["total"] += file_count
            await NafmiiFileService.add_parse_time_on_file(file_res)
            res["files"].extend(file_res)
        res["crumbs"] = await get_crumbs(int(kwargs["tree_id"]))
        res["default_molds"] = await pw_db.scalar(
            NewFileTree.select(NewFileTree.default_molds).where(NewFileTree.id == kwargs["tree_id"])
        )

        return res

    @classmethod
    def get_file_query(cls):
        mold_cte = (
            NewMold.select(
                func.ARRAY_AGG(NewMold.id).alias("molds"),
                func.ARRAY_AGG(NewMold.name).alias("mold_names"),
                NewFile.id,
            )
            .join(NewFile, on=(func.any_in(NewFile.molds, NewMold.id)))
            .group_by(NewFile.id)
            .cte("mold_cte")
        )
        question_cte = cls.group_question_by_fid()
        query = (
            NewFile.select(
                NewFile.id,
                NewFile.name,
                NewFile.page,
                NewFile.meta_info,
                NewFile.source,
                NewFile.pdf_parse_status,
                NewFile.created_utc,
                NewFile.tree_id,
                NewFile.pid.alias("pid"),
                NewAdminUser.name.alias("user_name"),
                NafmiiFileInfo.task_types,
                NafmiiFileInfo.status,
                NafmiiFileInfo.confirm_status,
                NafmiiFileInfo.revise_file_path,
                NafmiiFileInfo.push_answer_at,
                peewee.Value(5).alias("parse_time"),
                fn.COALESCE(mold_cte.c.molds, func.build_array()).alias("molds"),
                fn.COALESCE(mold_cte.c.mold_names, func.build_array()).alias("mold_names"),
                fn.COALESCE(question_cte.c.questions, func.build_array()).alias("questions"),
                NewTimeRecord.insight_queue_stamp,
                NewTimeRecord.insight_parse_stamp,
            )
            .join(NafmiiFileInfo, peewee.JOIN.LEFT_OUTER, include_deleted=True)
            .join(NewAdminUser, peewee.JOIN.LEFT_OUTER, on=(NewFile.uid == NewAdminUser.id), include_deleted=True)
            .join(NewTimeRecord, peewee.JOIN.LEFT_OUTER, on=(NewFile.id == NewTimeRecord.fid), include_deleted=True)
            .left_outer_join(mold_cte, on=(NewFile.id == mold_cte.c.id))
            .left_outer_join(question_cte, on=(NewFile.id == question_cte.c.fid))
        )
        return query.with_cte(mold_cte, question_cte)

    @classmethod
    def group_question_by_fid(cls):
        return (
            NewQuestion.select(
                func.ARRAY_AGG(
                    NewQuestion.jsonb_build_object(
                        "id",
                        "mold",
                        "ai_status",
                        "health",
                        "fill_in_user",
                        "data_updated_utc",
                        "updated_utc",
                        "fill_in_status",
                        "progress",
                        "status",
                        "name",
                        "num",
                        "mark_uids",
                        "mark_users",
                        origin_health=fn.COALESCE(NewQuestion.origin_health, 1),
                        mold_name=NewMold.name,
                    )
                ).alias("questions"),
                NewQuestion.fid,
            )
            .join(NewMold, join_type=peewee.JOIN.LEFT_OUTER, on=(NewQuestion.mold == NewMold.id), include_deleted=True)
            .group_by(NewQuestion.fid)
            .cte("question_cte")
        )

    @classmethod
    async def add_parse_time_on_file(cls, files: list[dict]):
        waiting_pages = await DocumentInspector.get_page_count_from_pdfinsight()
        max_fid = max((f["id"] for f in files if f["pdf_parse_status"] == PDFParseStatus.PARSING.value), default=0)
        parse_queue = OrderedDict()
        if max_fid:
            parsed_file = await pw_db.execute(
                NewFile.select(
                    NewFile.id,
                    NewFile.page,
                )
                .where(
                    NewFile.id <= max_fid,
                    NewFile.pdf_parse_status.in_([PDFParseStatus.PARSING, PDFParseStatus.PENDING]),
                )
                .order_by(NewFile.id.asc())
            )
            for file in parsed_file:
                parse_queue[file.id] = file.page or 1

        for file in files:
            status = file["pdf_parse_status"]
            if file["meta_info"] and file["meta_info"].get("is_scanned"):
                file_cost = (file["page"] or 1) * SCANNED_PDF_MULTIPLIER
            else:
                file_cost = (file["page"] or 1) * TIME_MULTIPLIER

            if status in [PDFParseStatus.PARSING, PDFParseStatus.PENDING]:
                if file["id"] in parse_queue:
                    cumulative_pages = sum(page for fid, page in parse_queue.items() if fid <= file["id"])
                    if file["meta_info"] and file["meta_info"].get("is_scanned"):
                        parse_time = (cumulative_pages - file["page"] + waiting_pages) * TIME_MULTIPLIER
                        file["parse_time"] = int(parse_time) + file_cost + INTERACTION_COST
                    else:
                        file["parse_time"] = (
                            int((cumulative_pages + waiting_pages) * TIME_MULTIPLIER) + INTERACTION_COST
                        )
                else:
                    new_file = await pw_db.first(NewFile.select().where(NewFile.id == file["id"]))
                    if new_file.pdf_parse_status == PDFParseStatus.PDFINSIGHT_PARSING:
                        if new_file.meta_info and new_file.meta_info.get("is_scanned"):
                            file["parse_time"] = int((new_file.page or 1) * SCANNED_PDF_MULTIPLIER) + INTERACTION_COST
                        else:
                            file["parse_time"] = int((new_file.page or 1) * TIME_MULTIPLIER) + INTERACTION_COST
                    else:
                        logger.info(
                            f"File may be complete: id={file['id']}, status={new_file.pdf_parse_status if new_file else 'Not found'}"
                        )
                        file["parse_time"] = waiting_pages * TIME_MULTIPLIER + file_cost + INTERACTION_COST
            elif file["pdf_parse_status"] == PDFParseStatus.PDFINSIGHT_PARSING:
                file["parse_time"] = file_cost + INTERACTION_COST
            else:
                file["parse_time"] = INTERACTION_COST


class _Answer(TypedDict):
    diff: list
    sensitive_word: list
    keyword: list


@dataclass
class TaskManager:
    file: NewFile
    task_types: set[TaskType]
    _answer: _Answer = field(init=False, default_factory=dict)

    async def __aenter__(self):
        return self

    async def run(self):
        file_info = await NafmiiFileInfo.find_by_kwargs(file_id=self.file.id)
        if not file_info:
            return
        if not self.file.pdfinsight_path():
            logger.info(f"pdfinsight path not found for file {self.file.id}")
            return
        task_types = self.task_types.intersection(file_info.task_types)
        if TaskType.T001 in task_types:
            try:
                self._answer["diff"] = await single_file_diff(self.file)
            except Exception as e:
                logger.exception(e)

        reader = PdfinsightReader(self.file.pdfinsight_path(abs_path=True))

        if TaskType.T002 in task_types:
            logger.info(f"start to predict keyword for file {self.file.id}")
            try:
                predictor = KeywordPredictor(reader, file_info.keywords)
                self._answer["keyword"] = predictor.predict_answer()
            except Exception as e:
                logger.exception(e)
            finally:
                logger.info(f"finish to predict keyword for file {self.file.id}")

        if TaskType.T003 in task_types:
            logger.info(f"start to predict sensitive word for file {self.file.id}")
            sys_ids = [0, file_info.sys_id]
            records = await pw_db.prefetch(
                SensitiveWord.select(SensitiveWord.name, SensitiveWord.type).where(SensitiveWord.sys_id.in_(sys_ids)),
                WordType.select(WordType.id, WordType.name),
            )
            sensitive_words = {word.name: word.type.name for word in records}
            predictor = SensitiveWordPredictor(reader, sensitive_words)

            try:
                self._answer["sensitive_word"] = predictor.predict_answer()
            except Exception as e:
                logger.exception(e)
            finally:
                logger.info(f"finish to predict sensitive word for file {self.file.id}")

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        """如果有任何异常, 将_answer的status改为CompareStatus.FAILED, 最后将_answer插入数据库"""
        if exc_type is not None:
            status = CompareStatus.FAILED
        else:
            status = CompareStatus.DONE
        await FileAnswer.insert_or_update(
            conflict_target=[FileAnswer.file], fid=self.file.id, status=status, **self._answer
        )
