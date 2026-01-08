import datetime
import hashlib
import logging
import os
import platform
import re
import time
from collections import defaultdict
from itertools import chain
from operator import and_
from typing import Literal

import msgspec
from bs4 import BeautifulSoup
from peewee import JOIN
from speedy.peewee_plus.orm import fn

from remarkable.answer.common import get_first_level_field
from remarkable.answer.node import AnswerItem
from remarkable.answer.reader import AnswerReader
from remarkable.common.constants import (
    AIStatus,
    MoldType,
    PDFFlag,
    PDFParseStatus,
    TagType,
)
from remarkable.common.enums import ClientName, TaskType
from remarkable.common.exceptions import CustomError, InvalidInterdocError, PDFInsightNotFound
from remarkable.common.storage import LocalStorage, localstorage
from remarkable.common.util import compact_dumps, generate_timestamp, read_zip_first_file, ready_for_annotate_notify
from remarkable.config import get_config
from remarkable.db import IS_MYSQL, pw_db
from remarkable.models.new_file import NewFile
from remarkable.models.new_user import NewAdminUser
from remarkable.pdfinsight.reader import PdfinsightReader
from remarkable.pw_models.answer_data import (
    DEFAULT_FILE_ANSWER_MERGE_STRATEGY,
    NewAnswerData,
    NewAnswerDataStat,
)
from remarkable.pw_models.model import (
    NewFileMeta,
    NewFileProject,
    NewFileTree,
    NewMold,
    NewTag,
    NewTagRelation,
    NewTimeRecord,
)
from remarkable.pw_models.question import NewQuestion
from remarkable.rule.szse_poc.rules import get_date_range
from remarkable.schema.answer import AnswerGroup
from remarkable.service.cmfchina.util import sync_answer_data_stat
from remarkable.service.mold_field import MoldFieldService
from remarkable.service.new_file_project import NewFileProjectService
from remarkable.service.new_mold import NewMoldService
from remarkable.service.page_counter import DocumentInspector

logger = logging.getLogger(__name__)


class _ModelVersion(msgspec.Struct):
    model_version: dict = {}


class _OutLine(msgspec.Struct):
    outline: list[float]
    merged: list = []
    grid: dict = {}
    cells: dict[str, dict] = {}
    type: (
        Literal[
            "table",
            "page_header",
            "paragraph",
            "page_footer",
            "footnote",
            "shape",
            "image",
            "infographic",
            "syllabus",
            "stamp",
        ]
        | None
    ) = None

    def to_dict(self):
        if self.cells:
            return {
                "outline": self.outline,
                "merged": self.merged,
                "grid": self.grid,
                "cells": self.cells,
                "type": self.type,
            }
        return {"outline": self.outline, "type": self.type}


class _Doc(msgspec.Struct):
    tables: list[dict] = []
    paragraphs: list[dict] = []
    page_headers: list[dict] = []
    page_footers: list[dict] = []
    images: list[dict] = []  # 图片
    shapes: list[dict] = []  # 柱状图、折线图等
    footnotes: list[dict] = []
    infographics: list[dict] = []  # 艺术字sync
    nested_tables: dict = {}  # 嵌套表格
    syllabuses: list[dict] = []
    stamps: list[dict] = []

    @property
    def non_tables(self) -> list[tuple[str, list[dict]]]:
        syllabus_indexes = {x["element"] for x in self.syllabuses}
        return [
            ("page_header", self.page_headers),
            ("paragraph", [x for x in self.paragraphs if x["index"] not in syllabus_indexes]),
            ("page_footer", self.page_footers),
            ("footnote", self.footnotes),
            ("image", self.images),
            ("shape", self.shapes),
            ("infographic", self.infographics),
            ("syllabus", [x for x in self.paragraphs if x["index"] in syllabus_indexes]),
            ("stamp", self.stamps),
        ]


class NewFileService:
    @classmethod
    async def create_file_from_link(cls, url: str, *, tree: NewFileTree, uid: int, mold_ids: list[int]):
        newfile = await pw_db.create(
            NewFile,
            **{
                "tree_id": tree.id,
                "pid": tree.pid,
                "name": "",
                "hash": "",
                "size": 0,
                "page": None,
                "molds": [],
                "pdf": None,
                "docx": None,
                "uid": uid,
                "pdfinsight": None,
                "pdf_flag": PDFFlag.NEED_CONVERT.value,
                "pdf_parse_status": PDFParseStatus.PENDING.value,
                "meta_info": {
                    "url": url,
                    "client_name": get_config("client.name"),
                    "created_from_link": True,
                    "failed_reason": "",
                },
                "task_type": TaskType.EXTRACT.value,
                "deleted_utc": generate_timestamp(),
                "source": None,
                "sysfrom": None,
            },
        )

        mold_ids = mold_ids or await NewFileTree.find_default_molds(tree.id)
        await cls.update_molds(newfile, mold_ids)

        return newfile

    @classmethod
    async def update_file_body(
        cls,
        file_id: int,
        data: dict,
    ):
        file = await NewFile.find_by_id(file_id, include_deleted=True)
        if not file:
            logger.error(f"Can't find file to update body: {file_id}")

        body = data["body"]

        filename = data["filename"]
        if not get_config("web.allow_same_name_file_in_project", True):
            if await pw_db.exists(NewFile.select().filter(name=filename, pid=file.pid)):
                file.meta_info = file.meta_info | {"failed_reason": "同名文件已存在"}
                await pw_db.update(file, only=["meta_info"])
                return None

        file.name = filename
        file.size = len(body)
        file.hash = hashlib.md5(body).hexdigest()
        file.docx = file.hash if file.name.lower().endswith(".docx") else None
        file.pdf = file.hash if file.name.lower().endswith(".pdf") else None
        file.deleted_utc = 0

        await pw_db.update(file, only=["name", "size", "hash", "docx", "pdf", "deleted_utc"])

        localstorage.write_file(file.path(), body, encrypt=bool(get_config("app.file_encrypt_key")))
        logger.info(f"File updated successfully, id:{file.id} name:{filename}")

        return file

    @classmethod
    async def create_file(
        cls,
        name: str,
        body: bytes,
        molds: list[int],
        pid: int,
        tree_id: int,
        uid: int,
        question_name: str | None = None,
        question_num: str | None = None,
        interdoc_raw: bytes | None = None,
        meta_info: dict | None = None,
        link: str | None = None,
        task_type=None,
        sysfrom=None,
        source=None,
        rank: int = 0,
        priority: int = 9,
        use_default_molds: bool = True,
        scenario_id: int | None = None,
    ) -> NewFile:
        logger.info(f"Start creating the file: {name}")
        new_file_hash = hashlib.md5(body).hexdigest()
        new_file_pdf = new_file_hash if name.lower().endswith(".pdf") else None
        new_file_pdfinsight = hashlib.md5(interdoc_raw).hexdigest() if interdoc_raw else None

        use_pdfinsight_cache_limit_hours = get_config("web.use_pdfinsight_cache_limit_hours")
        same_file = None
        if use_pdfinsight_cache_limit_hours:
            same_file = await pw_db.first(
                NewFile.select()
                .where(and_(NewFile.hash == new_file_hash, NewFile.pdfinsight.is_null(False)))
                .order_by(NewFile.id.desc())
            )

        if same_file:
            logger.info(
                f"Same file {same_file.id} found, with pdf: {same_file.pdf}, pdfinsight: {same_file.pdfinsight}"
            )
            new_file_pdf = new_file_pdf or same_file.pdf

            if same_file.pdfinsight_path() and not new_file_pdfinsight:
                pdfinsight_cache_path = localstorage.mount(same_file.pdfinsight_path())
                if os.path.exists(pdfinsight_cache_path):
                    time_interval = int(time.time()) - int(os.path.getmtime(pdfinsight_cache_path))
                    if time_interval <= use_pdfinsight_cache_limit_hours:
                        logger.info(f"{time_interval=}s < {use_pdfinsight_cache_limit_hours=}s, use pdfinsight cache")
                        new_file_pdfinsight = same_file.pdfinsight
                    else:
                        logger.info(
                            f"{time_interval=}s > {use_pdfinsight_cache_limit_hours=}s, don't use pdfinsight cache"
                        )

        if not get_config("web.allow_same_name_file_in_project", True):
            if await pw_db.exists(NewFile.select().filter(name=name, pid=pid)):
                raise CustomError(_("该项目下已存在同名的文件"))

        newfile = await pw_db.create(
            NewFile,
            tree_id=tree_id,
            pid=pid,
            name=name,
            hash=new_file_hash,
            size=len(body),
            page=None,
            molds=[],
            pdf=new_file_pdf,
            docx=new_file_hash if name.lower().endswith(".docx") else None,
            uid=uid,
            pdfinsight=new_file_pdfinsight,
            pdf_flag=PDFFlag.CONVERTED.value if new_file_pdf else PDFFlag.NEED_CONVERT.value,
            pdf_parse_status=PDFParseStatus.COMPLETE.value if new_file_pdfinsight else PDFParseStatus.PENDING.value,
            meta_info=meta_info,
            link=link,
            task_type=task_type or TaskType.EXTRACT.value,
            sysfrom=sysfrom,
            source=source,
            rank=rank,
            priority=priority,
            scenario_id=scenario_id,
        )

        if same_file:
            time_record = await pw_db.first(NewTimeRecord.select().where(NewTimeRecord.fid == same_file.id).dicts())
            if time_record:
                logger.info(f"{newfile.id} find same file {same_file.id} time record: {time_record}")
                time_record.pop("id")
                time_record.update({"fid": newfile.id})
                await pw_db.create(NewTimeRecord, **time_record)
            else:
                logger.info(f"file {same_file.id} time record not found, may be have not parsed")
        localstorage.write_file(newfile.path(), body, encrypt=bool(get_config("app.file_encrypt_key")))

        page = cls.estimate_page_count(newfile)
        await newfile.update_(page=page)
        if get_config("client.name") == "nafmii" and newfile.is_pdf:
            if cls.is_scanned_pdf(newfile):
                meta_info = newfile.meta_info or {} | {"is_scanned": True}
                await newfile.update_(meta_info=meta_info)

        if interdoc_raw:
            localstorage.write_file(newfile.pdfinsight_path(), interdoc_raw)
        logger.info(f"NewFile created successfully, id:{newfile.id} name:{name}")

        if not molds and use_default_molds:
            molds = await NewFileTree.find_default_molds(tree_id)

        await cls.update_molds(newfile, molds, question_name, question_num)
        return newfile

    @classmethod
    async def update_molds(
        cls,
        file: NewFile,
        mold_ids: list[int],
        question_name: str | None = None,
        question_num: str | None = None,
    ):
        logger.info(f"file: {file.id}, update_molds: {mold_ids}")
        if not await NewMold.all_ids_exists(mold_ids):
            raise CustomError(_("Not all ids valid."))

        add_molds = set(mold_ids) - set(file.molds)
        for mid in add_molds:
            await NewQuestion.create_by_mold(file.id, mid, question_name, question_num)

        delete_molds = set(file.molds) - set(mold_ids)
        for mid in delete_molds:
            await NewQuestion.delete_by_mold(file.id, mid)

        await pw_db.update(file, molds=mold_ids)
        logger.info(f"NewFile update_molds, fid:{file.id}, start call process_file")
        return add_molds, delete_molds

    @staticmethod
    def check_pdfinsight(file: NewFile) -> list[dict]:
        if not file.pdfinsight or not os.path.exists(localstorage.mount(file.pdfinsight_path())):
            raise PDFInsightNotFound(
                f"Interdoc not ready for file: {file.id=}, {file.name=}, {file.hash=}, {file.pdf_parse_status=}. "
                f"Did we receive the right callback from the pdfinsight service?"
            )
        reader = PdfinsightReader(localstorage.mount(file.pdfinsight_path()))
        elements = list(
            chain(
                (para for para in reader.paragraphs if "......" not in para["text"] and not para.get("fragment")),
                (elt for elt in reader.tables if not elt.get("fragment")),
                reader.page_headers,
                reader.page_footers,
                reader.shapes,
                reader.infographics,
                reader.images,
            )
        )
        if not elements:
            raise InvalidInterdocError(
                f"Possible invalid interdoc found: {file.id=}, {file.name=}, {file.hash=}, {file.pdf_parse_status=}."
            )
        return elements

    @classmethod
    def file_query(
        cls,
        tree_ids: list[int] = None,
        mold: int = None,
        pid: int = None,
        fileid: int = None,
        filename: str = None,
        uid: int = None,
        is_answered: bool = None,
        question_status: int = None,
        is_manager: bool = True,
    ):
        file_tag = (
            NewTagRelation.select(
                NewTagRelation.relational_id.alias("file_id"),
                NewTag.id,
            )
            .join(NewTag, on=(NewTagRelation.tag_id == NewTag.id))
            .where(NewTag.tag_type == TagType.FILE.value)
            .alias("file_tag")
        )
        cond = cls.query_cond(
            tree_ids,
            mold,
            pid,
            fileid,
            filename,
            uid,
            is_answered,
            question_status,
            is_manager,
        )
        query = (
            NewFile.select(
                NewFile,
                NewAdminUser.name.alias("user_name"),
                fn.array_remove(fn.array_agg(file_tag.c.id.distinct()), None).alias("tags"),
            )
            .distinct(NewFile.id)
            .join(NewFileProject, on=(NewFileProject.id == NewFile.pid))
            .join(NewAdminUser, join_type=JOIN.LEFT_OUTER, on=(NewAdminUser.id == NewFile.uid), include_deleted=True)
            .join(NewQuestion, join_type=JOIN.LEFT_OUTER, on=(NewQuestion.fid == NewFile.id), include_deleted=True)
            .join(file_tag, join_type=JOIN.LEFT_OUTER, on=(file_tag.c.file_id == NewFile.id), include_deleted=True)
            .group_by(
                NewFile.id,
                NewAdminUser.name,
            )
        )
        return query.where(*cond).order_by(NewFile.id.desc())

    @classmethod
    def query_cond(
        cls,
        tree_ids: list[int] = None,
        mold: int = None,
        pid: int = None,
        fileid: int = None,
        filename: str = None,
        uid: int = None,
        is_answered: bool = None,
        question_status: int = None,
        is_manager: bool = True,
        mold_ids: list[int] = None,
        search_mid: int | None = None,
    ):
        cond = []
        if tree_ids:
            cond.append(NewFile.tree_id.in_(tree_ids))

        if mold:
            cond.append(NewFile.molds.contains(mold))

        if mold_ids is not None:
            # mold_ids 权限包含的场景id列表，文件场景列表包含任意一个权限场景 或者 为空 都满足
            cond.append((NewFile.molds.contains_any(mold_ids) | (NewFile.molds == [])))
        if search_mid is not None:
            # 按场景搜索条件
            cond.append(NewFile.molds.contains(search_mid))

        if pid:
            cond.append(NewFile.pid == pid)
        else:
            cond.append(NewFileProject.visible)

        if fileid:
            cond.append(NewFile.id == fileid)

        if filename:
            cond.append(NewFile.name.contains(filename))

        if is_answered:
            cond.append(NewQuestion.mark_uids.contains(uid))

        if question_status:
            cond.append(NewQuestion.status == question_status)

        if not is_manager:
            cond.append((NewFileProject.uid == uid) | NewFileProject.public)

        return cond

    @staticmethod
    async def find_fids_by_tag_and_mold(tag_id, mold_id):
        query = (
            NewFile.select(NewFile.id)
            .join(NewTagRelation, on=(NewFile.id == NewTagRelation.relational_id))
            .where(NewTagRelation.tag_id == tag_id, NewFile.molds.contains(mold_id))
        )
        data = await pw_db.execute(query)
        return [x.id for x in data]

    @staticmethod
    def estimate_page_count(file) -> int:
        origin_path = localstorage.mount(file.path())
        if file.is_pdf:
            page = DocumentInspector.get_pdf_page_count(origin_path)
        elif file.is_image:
            page = 1
        elif file.is_excel:
            page = 1
        elif file.is_word:
            page = DocumentInspector.get_word_page_count(origin_path)
        elif file.is_ppt:
            page = DocumentInspector.get_ppt_page_count(origin_path)
        else:
            logger.error(f"unknown file type {file.id}-{file.name}")
            page = 1
        return page

    @staticmethod
    def is_scanned_pdf(file):
        return DocumentInspector.is_scanned(localstorage.mount(file.path()))

    @classmethod
    def get_or_create_outlines(cls, file: NewFile, force=False, fail_count=0) -> dict[str, list[dict]]:
        work_dir = LocalStorage(file.label_cache_dir)
        # 删除旧缓存
        work_dir.delete_file("label_tables.json.gz")

        outlines_path = work_dir.mount("outlines.json.gz")
        if not force and work_dir.exists(outlines_path):
            try:
                raw_data = work_dir.read_file(outlines_path, open_pack="gzip")
            except Exception:
                logger.exception(f"Load label cache failed for file:{file.id}, path:{outlines_path}")
                work_dir.delete_file(outlines_path)
                if fail_count > 3:
                    logger.error(f"Max fail count reached for file:{file.id}, path:{outlines_path}")
                    return {}
                return cls.get_or_create_outlines(file, force, fail_count + 1)

            return {
                k: [o.to_dict() for o in v]
                for k, v in msgspec.json.decode(raw_data, type=dict[str, list[_OutLine]]).items()
            }

        data = read_zip_first_file(localstorage.mount(file.pdfinsight_path()), msgspec_type=_Doc)
        outlines = defaultdict(list)
        if data.nested_tables:
            # 内嵌表格，{'1-5_2':[{'class': 'TABLE', 'index': None, 'page': 0, ...}]}
            # 1-5_2: 表格index为1, 5_2为cell的index
            data.tables.extend([ele for table in data.nested_tables.values() for ele in table])
        for table in data.tables:
            thin_table = {k: v for k, v in table.items() if k in ("outline", "merged", "grid")}
            thin_table["cells"] = {k: {"box": v["box"]} for k, v in table["cells"].items()}
            thin_table["type"] = "table"
            thin_table["index"] = table["index"]
            outlines[str(table["page"])].append(thin_table)
        for typ, elements in data.non_tables:
            for element in elements:
                outlines[str(element["page"])].append(
                    {"outline": element["outline"], "type": typ, "index": element["index"]}
                )
        for page in outlines:
            elements = outlines[page]
            if len(elements) > 1:
                # ↓ → 排序保存
                outlines[page].sort(key=lambda e: (e["outline"][1], e["outline"][0]))
        work_dir.write_file(outlines_path, msgspec.json.encode(outlines), open_pack="gzip")
        return outlines

    @classmethod
    async def post_pipe(cls, fid, triggered_by_predict: bool = False, **kwargs):
        """
        file关联的questions 预测答案跑完之后做的一些后续操作
        :return:
        """
        from remarkable.service.rule import do_inspect_rule_pipe

        if get_config("data_flow.file_answer.generate") or get_config("web.enable_llm_extract"):
            logging.info(f"generate_file_answer for file: {fid}")
            await cls.update_answer_data(
                fid=fid,
                merge_groups=ClientName.cmfchina != get_config("client.name")
                and not get_config("web.enable_llm_extract"),
                merge_strategy=kwargs.get("file_answer_merge_strategy"),
                triggered_by_predict=triggered_by_predict,
            )

        questions = await NewQuestion.find_by_fid(fid)
        # 仅在questions都预测成功的情况下, 才继续执行
        if any(question.ai_status != AIStatus.FINISH for question in questions):
            logging.info(f"question.ai_status is not FINISH, file: {fid}")
            return

        # 调用update_answer_data()后, file_answer已更新,审核结果也要更新
        await do_inspect_rule_pipe(
            fid,
            audit_preset_answer=triggered_by_predict
            and get_config("client.name") == ClientName.cmfchina
            and "cmfchina_checker" == get_config("inspector.package_name"),
        )

    @classmethod
    async def update_answer_data(cls, fid, merge_groups=True, merge_strategy=None, triggered_by_predict=False):
        if merge_groups:  # qid统一纪为master_question.id
            if not merge_strategy:
                merge_strategy = DEFAULT_FILE_ANSWER_MERGE_STRATEGY
            logging.info(f"{merge_strategy=}")
            master_question = await NewQuestion.get_master_question(fid)
            if not master_question:
                logging.info(f"No master_question, no answer_data, fid: {fid}")
                return
            qids = [master_question.id]
            old_groups = await get_old_groups(master_question)
            new_groups = await get_new_groups(master_question)
            answer_datas = NewAnswerData.merge_groups(old_groups, new_groups, merge_strategy)
            for data in answer_datas:
                if isinstance(data.get("score"), (int, float)):
                    data["score"] = str(data["score"])
        else:
            answer_datas, questions = await update_answer_data_by_mold_question(
                fid, gen_for_llm_mold=triggered_by_predict
            )
            qids = [q.id for q in questions]
            if answer_datas is None or questions is None:
                return

        async with pw_db.atomic():
            await pw_db.execute(NewAnswerData.delete().where(NewAnswerData.qid.in_(qids)))
            await pw_db.execute(NewAnswerDataStat.delete().where(NewAnswerDataStat.qid.in_(qids)))
            if IS_MYSQL:
                await NewAnswerData.bulk_insert(answer_datas)
                ids = await pw_db.scalars(NewAnswerData.select(NewAnswerData.id).where(NewAnswerData.qid.in_(qids)))
            else:
                ids = list(await NewAnswerData.bulk_insert(answer_datas, iter_ids=True))
            if ids:
                await sync_answer_data_stat(ids)


async def get_old_groups(master_question: NewQuestion):
    answer_data_groups = defaultdict(AnswerGroup)
    items = await NewAnswerData.find_by_kwargs(qid=master_question.id, delegate="all")
    for item in items:
        item = item.to_dict(exclude=["id", "created_utc", "updated_utc"])
        first_level_field = get_first_level_field(item["key"])
        group = answer_data_groups[first_level_field]
        group.items.append(item)
        group.manual = group.manual or bool(item["record"])

    return answer_data_groups


async def get_new_groups(master_question: NewQuestion):
    molds = await NewMoldService.get_related_molds(master_question.fid, master_question.mold)
    answer_data_groups = defaultdict(AnswerGroup)
    questions = await NewQuestion.find_by_fid_mids(master_question.fid, [x.id for x in molds])
    if not all(x.answer for x in questions):
        logging.info(f"Not all questions have answer, no answer_data, {master_question.fid=}")
        return answer_data_groups

    _, fixed_molds = NewMoldService.master_mold_with_merged_schemas(molds)
    mold_reserved_fields = {}
    for mold in fixed_molds:
        mold_reserved_fields[mold.name] = mold.data["schemas"][0]["orders"]

    for question in questions:
        answer_reader = AnswerReader(question.answer)
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
                "qid": master_question.id,
                "uid": answer_item.marker["id"] if answer_item.marker else None,
                "key": answer_item.key,
                "data": answer_item.data,
                "schema": answer_item.schema,
                "value": value,
                # "text": answer_item.text,
                "score": answer_item.score,
                "record": None,
                "revise_suggestion": None,
            }
            answer_data_groups[answer_item.first_level_field].items.append(answer_data)
    return answer_data_groups


async def update_answer_data_by_mold_question(fid, gen_for_llm_mold=False):
    # 多schema情况下，合并answer_data，会修改qid，造成根据模型统计时数据丢失, 根据各对应的qid存储各自的answer_data
    questions = await NewQuestion.find_by_fid(fid)
    answer_datas = []
    if not questions:
        logging.info(f"No question, no answer_data, fid: {fid}")
        return None, None
    for question in questions:
        mold = await NewMold.find_by_id(question.mold)
        if not mold:
            logging.info(f"No mold, mold:{mold.id}")
            return None, None
        has_llm_field = mold.mold_type in [MoldType.LLM, MoldType.HYBRID]
        if gen_for_llm_mold is False and has_llm_field:
            return None, None
        mold_reserved_fields = {mold.name: mold.data["schemas"][0]["orders"]}
        mold_field_mapping = await MoldFieldService.get_mold_field_uuid_path(mold.id)
        result = {compact_dumps(row.path): row.id for row in mold_field_mapping}
        answer = question.preset_answer if has_llm_field else question.answer
        if not answer:
            continue
        answer_reader = AnswerReader(answer)
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
                # "text": answer_item.text,
                "score": answer_item.score,
                "record": None,
                "mold_field_id": result.get(answer_item.md5),
                "revise_suggestion": None,
            }
            answer_datas.append(answer_data)
    return answer_datas, questions


class NewFileMetaService:
    @classmethod
    async def create(cls, doc: NewFile, **meta) -> NewFileMeta | None:
        logger.info(
            f"Start creating meta info for file: {doc.name}",
        )
        essential_cols = [
            "stock_code",
            "stock_name",
            "report_year",
            "doc_type",
            "publish_time",
        ]
        meta.setdefault("doc_type", "年报")
        pub_time = meta.get("publish_time") or datetime.datetime.now().strftime("%Y-%m-%d")
        meta["publish_time"] = int(datetime.datetime.strptime(pub_time, "%Y-%m-%d").timestamp())
        cols = [c for c in essential_cols if c not in meta or not meta[c]]
        if cols:
            logger.warning(f"Missing the follow keys: {cols}")
            return None
        meta["hash"] = doc.hash
        meta["title"] = os.path.splitext(doc.name)[0]
        meta["stock_code"] = meta["stock_code"].rjust(6, "0")
        meta["file_id"] = doc.id
        meta["raw_data"] = {"source": "autodoc"}
        return await NewFileMeta.create_or_update(**meta)

    @classmethod
    async def get_file_metas(cls, file_id: int) -> dict[str, list[NewFileMeta]]:
        ret = defaultdict(list)
        file_meta: NewFileMeta = await NewFileMeta.find_by_kwargs(file_id=file_id)
        if not file_meta:
            logger.warning(f"No meta info found: {file_id}")
            return ret

        date_range = get_date_range(file_meta.report_year)
        items = await pw_db.execute(
            NewFileMeta.select(NewFileMeta, NewFile)
            .join(NewFile, on=(NewFile.id == NewFileMeta.file_id))
            .where(
                NewFileMeta.stock_code == file_meta.stock_code,
                NewFileMeta.publish_time >= date_range[0],
                NewFileMeta.publish_time <= date_range[1],
            )
            .order_by(NewFileMeta.publish_time.desc())
        )
        for item in items:
            questions = []
            for mid in item.file.molds:
                question = await NewQuestion.find_by_fid_mid(item.file.id, mid)
                questions.append(question)
            item.questions = questions
            ret[item.doc_type].append(item)
        return ret


def _get_report_types():
    default_types = {
        "not_small_scattered": {"molds": ["非“小而分散”类资产"], "name": "非“小而分散”类资产"},
        "small_scattered": {"molds": ["“小而分散”类资产"], "name": "“小而分散”类资产"},
    }
    return get_config("ecitic.report_types") or default_types


class CITICFileService:
    report_types = _get_report_types()

    @classmethod
    async def get_mids(cls, prj_type):
        mids = []
        for mold_name in cls.report_types[prj_type]["molds"]:
            mold = await NewMold.find_by_name(mold_name)
            if mold:
                mids.append(mold.id)
        return mids

    @classmethod
    async def create(cls, file_name, body, project_name, project_type, uid):
        root_name = cls.report_types[project_type]["name"]
        project = await NewFileProjectService.create(name=root_name, uid=uid, public=False)
        mids = await cls.get_mids(project_type)
        return await NewFileService.create_file(
            file_name,
            body,
            mids,
            project.id,
            project.rtree_id,
            uid=uid,
            meta_info={"project_name": project_name},
        )


async def octopus_html2pdf(text: str) -> (str, bytes):
    soup = BeautifulSoup(text, "lxml")
    detail_box = soup.find("div", class_="allDetailBox")
    filename = f"{detail_box.find('input', id='fullTitle').attrs['value'].strip()}.pdf"

    lines = [
        """<!DOCTYPE html>
<html>
<head>
    <style>
        h2,
        h3 {
            text-align: center;
        }

        .right-align {
            text-align: right;
        }

        h2,
        h3,
        p {
            white-space: pre-wrap;
        }
    </style>
</head>

<body>""",
    ]
    title_elt = soup.find("p", class_="allDetailTitle")
    if title_elt:
        lines.append(f"<h2>{title_elt.text.strip()}</h2>")
    sub_title_elt = soup.find("p", class_="allDeatilTwoTitle")
    if sub_title_elt:
        lines.append(f"<h3>{sub_title_elt.text}</h3>")
    for elt in soup.find("div", id="hiddenContent") or []:
        if not elt or not hasattr(elt, "text") or not hasattr(elt, "attrs"):
            continue
        text = elt.text.strip()
        if not text:
            continue
        if re.search(r"^[一二三四五六七八九十]+、", text):
            # 段落标题
            text = f"<h4>{text}</h4>"
        if (elt.attrs.get("style") or "").endswith("right;"):
            # 落款署名&日期
            text = f'<p class="right-align">{text}</p>'
        else:
            # 默认段落
            text = f"<p>{text}</p>"
        lines.append(text)
    lines.append("</body></html>\n")
    return filename, await html2pdf("\n".join(lines))


async def html2pdf(html: str) -> bytes:
    from playwright.async_api import async_playwright

    async with async_playwright() as p:
        if platform.system() == "Darwin":
            # Macos 系统需要开发者 手动安装下对应的依赖
            browser = await p.chromium.launch()
        else:
            executable_path = get_config("playwright.executable") or "/usr/bin/google-chrome"
            browser = await p.chromium.launch(executable_path=executable_path)
        page = await browser.new_page()
        await page.set_content(html)
        content = await page.pdf(format="A4")
        await browser.close()
        return content


async def create_pdf_cache(file: NewFile, force=False, by_pdfinsight=None):
    from remarkable.plugins.fileapi.worker import PDFCache

    await file.update_(pdf_parse_status=PDFParseStatus.CACHING)
    try:
        pdf_cache = PDFCache(file, by_pdfinsight)
        pdf_cache.build(force)
    except Exception:
        await file.update_(pdf_parse_status=PDFParseStatus.FAIL)
        raise

    await file.update_(pdf_parse_status=pdf_cache.get_pdf_parse_status())
    if get_config("notification.ready_for_annotate_notify") and file.pdf_parse_status == PDFParseStatus.COMPLETE:
        await ready_for_annotate_notify(file.id, file.name)


if __name__ == "__main__":
    import asyncio

    asyncio.run(NewFileService.file_query([632]))
