import asyncio
import glob
import http
import io
import json
import logging
import os
import random
import re
import urllib
from datetime import datetime, timedelta
from typing import Iterator
from uuid import uuid4
from zipfile import ZipFile

import httpx
import openpyxl
import pandas as pd
from mako.template import Template
from marshmallow import Schema as MMSchema
from marshmallow import ValidationError, validates
from pdfparser.pdftools.split_pdf import (
    pick_page_from_pdf,
)
from tornado import httpclient
from tornado.httputil import HTTPFile, HTTPServerRequest
from traceback_with_variables import LoggerAsFile, print_exc
from webargs import fields

from remarkable import config
from remarkable.answer.common import is_empty_answer
from remarkable.answer.reader import AnswerReader as CommonAnswerReader
from remarkable.base_handler import Auth, BaseHandler, DbQueryHandler, PermCheckHandler
from remarkable.checker.helpers import create_inspector
from remarkable.common import field_validate
from remarkable.common.apispec_decorators import doc, use_kwargs
from remarkable.common.constants import AIStatus, IntEnumBase, PDFParseStatus, RuleID, RuleType
from remarkable.common.enums import AuditAnswerType, ClientName, TaskType
from remarkable.common.exceptions import CustomError
from remarkable.common.storage import localstorage, tmp_storage
from remarkable.common.util import dump_data_to_worksheet
from remarkable.config import get_config
from remarkable.converter import SimpleJSONConverter
from remarkable.db import pw_db
from remarkable.models.new_file import NewFile
from remarkable.models.new_user import ADMIN, NewAdminUser
from remarkable.optools.export_answers_with_format import get_annotation_answer
from remarkable.plugins.ext_api import plugin
from remarkable.plugins.ext_api.answer import AnswerReader, parser_answer_node
from remarkable.plugins.ext_api.common import convert_image_to_pdf
from remarkable.plugins.ext_api.gffund_handler_extension import GFFundUploadFile
from remarkable.pw_models.audit_rule import NewAuditResult
from remarkable.pw_models.model import (
    NewAccessToken,
    NewAnswer,
    NewAuditStatus,
    NewFileProject,
    NewFileTree,
    NewMold,
    NewRuleResult,
    NewTimeRecord,
)
from remarkable.pw_models.question import NewQuestion
from remarkable.schema.cgs.rules import AuditStatusType
from remarkable.service.gffund_fax_process import process_df_fax
from remarkable.service.gtja_checklist_parser import parse
from remarkable.service.new_file import NewFileMetaService, NewFileService
from remarkable.service.new_file_project import NewFileProjectService
from remarkable.service.new_mold import NewMoldService
from remarkable.user.handlers import gen_password
from remarkable.worker.tasks import (
    cache_pdf_file,
    convert_to_docx,
    download_file,
    preset_answer_by_qid,
    process_file,
)

logger = logging.getLogger(__name__)

P_NUM_FIELD = re.compile(r"(?P<num>^\d+)\s(?P<field>.+)")


@plugin.route(r"/upload")
@plugin.route(r"/scriber_fund/upload")
class UploadHandler(BaseHandler):
    args_schema = {
        "tree_id": fields.Integer(load_default=0),
        "req_id": fields.Integer(load_default=None),
        "schema_id": fields.Integer(load_default=None),
        "schema_name": fields.Str(load_default=None),
        "csc_tree_id": fields.Integer(data_key="treeId", load_default=0),
        "csc_req_id": fields.Integer(data_key="reqId", load_default=None),
        "csc_schema_id": fields.Integer(data_key="schemaId", load_default=None),
        "meta": fields.Str(load_default=None),
        "username": fields.Str(load_default=None),
        "post_text": fields.Str(data_key="text", load_default=None),
        "filename": fields.Str(load_default=""),
        "file_url": fields.Str(load_default=None),
        "priority": fields.Integer(load_default=9, validate=field_validate.Range(min=0, max=9)),
    }

    @Auth("browse")
    @use_kwargs(args_schema, location="form")
    @use_kwargs(
        {
            "post_files": fields.List(
                fields.Raw(),
                data_key="file",
                required=False,
                load_default=[],
            ),
            "post_interdocs": fields.Raw(data_key="interdoc", required=False),
        },
        location="files",
    )
    async def post(
        self,
        tree_id,
        req_id,
        schema_id,
        schema_name,
        csc_tree_id,
        csc_req_id,
        csc_schema_id,
        meta,
        username,
        post_text,
        filename,
        file_url,
        priority,
        post_files: list[HTTPFile],
        post_interdocs=None,
    ):
        if (config.get_config("client.name") or "") == "csc":
            tree_id = csc_tree_id
            req_id = csc_req_id
            schema_id = csc_schema_id

        if not schema_id and schema_name:
            mold = await NewMold.find_by_name(schema_name)
            schema_id = mold.id if mold else None
        schema_ids = None
        if not tree_id:
            if project_name := get_config("feature.project_for_external_file"):
                file_project = await NewFileProjectService.create(name=project_name)
                tree_id = file_project.rtree_id
        file_tree = await NewFileTree.find_by_id(tree_id)

        if not file_tree:
            return self.ext_error(_("Invalid treeId"), req_id=req_id)
        if meta:
            meta = json.loads(meta)
            if meta.get("annotation_callback"):
                answer_from = meta.get("answer_from", "user")
                answer_format = meta.get("answer_format", "json_tree")
                if not (
                    answer_from in ["user", "merge", "special_answer"] and answer_format in ["origin", "json_tree"]
                ):
                    return self.ext_error(_("Invalid meta"), req_id=req_id)
            schema_ids = meta.get("schema_ids", [])
        # 分析使用的 schema id，缺省使用目录对应的默认 schema
        molds = await NewFileTree.find_default_molds(tree_id)
        if schema_id and not schema_ids:
            schema_ids = [schema_id]
        if schema_ids:
            for mold_id in schema_ids:
                mold_obj = await NewMold.find_by_id(mold_id)
                if not mold_obj:
                    return self.ext_error(_("Invalid schemaId"), req_id=req_id)
            molds = [int(x) for x in schema_ids]

        project = await NewFileProject.find_by_id(file_tree.pid)

        files = []
        for file in post_files:
            files.append([file.filename, file.body, None])
        if post_text:
            if not filename:
                filename = f"{datetime.now().strftime('%Y%m%d%H%M%S')}-{post_text[:10]}"
            files.append([f"{filename}.txt", post_text.encode("utf-8", errors="ignore"), None])
        if file_url:
            if files and get_config("client.name") == ClientName.cmbchina:
                raise CustomError("不支持同时指定file_url和file", resp_status_code=http.HTTPStatus.BAD_REQUEST)
            if not filename:
                raise CustomError("指定file_url时需要指定filename", resp_status_code=http.HTTPStatus.BAD_REQUEST)
            try:
                async with httpx.AsyncClient(
                    transport=httpx.AsyncHTTPTransport(retries=3),
                    verify=False,
                    timeout=30,
                ) as client:
                    rsp = await client.get(file_url)
                    if rsp.status_code != 200:
                        return self.error(
                            f"获取文件异常, status: {rsp.status_code}, msg :{rsp.text}",
                            status_code=http.HTTPStatus.BAD_REQUEST,
                        )
                    body = rsp.content
            except httpx.TimeoutException as e:
                raise CustomError("获取文件超时, 请检查文件服务器", resp_status_code=http.HTTPStatus.BAD_REQUEST) from e
            except Exception as e:
                logger.exception(e)
                raise CustomError("获取文件失败", resp_status_code=http.HTTPStatus.BAD_REQUEST) from e
            files.append([filename, body, None])
        if not files:
            return self.ext_error(_("Invalid file"), req_id=req_id)

        uid = ADMIN.id
        if username:
            user = await NewAdminUser.find_by_kwargs(name=username)
            if not user:
                return self.error("Invalid username")
            uid = user.id
        if post_interdocs:
            files[0][-1] = post_interdocs.body
        ret = []
        for doc_name, doc_raw, interdoc_raw in files:
            # 创建文档记录/保存上传文件
            file = await NewFileService.create_file(
                doc_name,
                doc_raw,
                molds,
                project.id,
                tree_id,
                uid=uid,
                interdoc_raw=interdoc_raw,
                meta_info=meta,
                priority=priority,
            )
            if meta and isinstance(meta, dict):
                await NewFileMetaService.create(file, **meta)

            await NewTimeRecord.update_record(file.id, "upload_stamp")
            if interdoc_raw:
                # 随机延迟几秒再执行生成缓存任务
                cache_pdf_file.apply_async(args=(file.id,), kwargs={"force": True}, countdown=random.randrange(3, 10))
            await process_file(file, force_predict=True)
            item = {"id": file.id, "filename": file.name, "schema_ids": molds}
            if get_config("client.name") == "guosen":
                question = await NewQuestion.get_master_question(file.id)
                item["project_id"] = file.pid
                item["tree_id"] = file.tree_id
                if question:
                    item["qid"] = question.id
                    item["mid"] = question.mold
                else:
                    item["qid"] = item["mid"] = None
            ret.append(item)
            if len(files) == 1:
                return self.ext_data(msg="成功", req_id=req_id, data=ret[0]) if req_id else self.data(ret[0])
        return self.ext_data(msg="成功", req_id=req_id, data=ret) if req_id else self.data(ret)


class FileStat(IntEnumBase):
    PROCESSING = (0, "processing", "文件正在处理中", "处理中")
    FAILED = (-1, "failed", "文件处理失败", "失败")
    SUCCESS = (1, "success", "文件处理成功", "成功")


async def get_file_status(file: NewFile):
    status = (
        FileStat.FAILED
        if file.pdf_parse_status
        in {
            PDFParseStatus.FAIL,
            PDFParseStatus.OCR_EXPIRED,
            PDFParseStatus.CANCELLED,
            PDFParseStatus.UN_CONFIRMED,
            PDFParseStatus.UNSUPPORTED_FILE,
        }
        else FileStat.PROCESSING
    )

    extra = {"ai_status": [], "parse_status": file.pdf_parse_status}
    urls = []
    for question in await pw_db.execute(
        NewQuestion.select(NewQuestion.id, NewQuestion.ai_status, NewQuestion.mold).where(NewQuestion.fid == file.id)
    ):
        if status == FileStat.PROCESSING:
            if question.ai_status == AIStatus.FINISH:
                status = FileStat.SUCCESS
            elif question.ai_status in {AIStatus.SKIP_PREDICT, AIStatus.FAILED, AIStatus.DISABLE}:
                status = FileStat.FAILED
            else:
                status = FileStat.PROCESSING
        extra["ai_status"].append(
            {
                "qid": question.id,
                "status": question.ai_status,
            }
        )
        urls.append(
            f"/#/project/remark/{question.id}?projectId={file.pid}&treeId={file.tree_id}&fileId={file.id}&schemaId={question.mold}"
        )
    return status, extra, urls


class FilesStatusSchema(MMSchema):
    file_ids = fields.List(fields.Int(), load_default=list)


@plugin.route("/files_status")
class FilesStatusHandler(BaseHandler):
    _doc = """接口示例：

    ```js
    status: 200
    ---
    {
        "status": "ok",
        "data": [
            {
                "file_id": 1,
                "status": "success",  // 三种状态：processing/failed/success
                "message": "文件处理成功",
                "url": "http://host:port/#/project/remark/12566?projectId=261&treeId=315&fileId=3605&schemaId=147",
            },
            {
                "file_id": 2,
                "status": "failed",  // 三种状态：processing/failed/success
                "message": "文件处理失败",
            }
        ]
    }
    ```

    错误响应：

    ```js
    status: 404
    ---
    {
        "status": "error",
        "message": "File not found",
        "errors": {}
    }
    ```"""

    @doc(summary="获取文件处理状态", tags=["external-api"], description=_doc)
    @Auth("browse")
    @use_kwargs(FilesStatusSchema, location="json")
    async def post(self, file_ids: list[int]):
        files = await pw_db.execute(NewFile.select(include_deleted=True).where(NewFile.id.in_(file_ids)))
        results = []
        for file in files:
            if file.deleted:
                if not file.created_from_link:
                    continue

                if file.failed_reason:
                    results.append(
                        {
                            "file_id": file.id,
                            "status": FileStat.FAILED.phrase,
                            "message": file.failed_reason,
                        }
                    )
                    continue

            status, _, _ = await get_file_status(file)
            molds = await pw_db.execute(NewMold.select().where(NewMold.id.in_(file.molds)))
            master_mold, _ = NewMoldService.master_mold_with_merged_schemas(molds)
            question = await NewQuestion.find_by_kwargs(fid=file.id, mold=master_mold.id)
            file_data = {
                "file_id": file.id,
                "status": status.phrase,
                "message": status.label,
            }
            if status == FileStat.SUCCESS:
                inspect_route = f"/#/project/inspect/{question.id}?projectId={file.pid}&treeId={file.tree_id}&fileId={file.id}&schemaId={question.mold}&task_type=extract"
                file_data["url"] = self.get_url(inspect_route)
            results.append(file_data)

        return self.data(results)


@plugin.route(r"/files/(?P<fid>\d+)/status")
class FileStatusHandler(BaseHandler):
    _doc = """接口示例：

```js
status: 200
---
{
    "status": "ok",
    "data": {
        "status": "success",  // 三种状态：processing/failed/success
        "extra": {  // Scriber 内部状态，客户无需关心
            "ai_status": [
                {
                    "qid": 10468,
                    "status": 3
                }
            ],
            "parse_status": 4
        },
        "message": "文件处理成功",
        "url": "/#/project/remark/12566?projectId=261&treeId=315&fileId=3605&schemaId=147",
    }
}
```

错误响应：

```js
status: 404
---
{
    "status": "error",
    "message": "File not found",
    "errors": {}
}
```"""

    @doc(summary="获取文件处理状态", tags=["external-api"], description=_doc)
    @Auth("browse")
    async def get(self, fid: str):
        file = await NewFile.find_by_id(int(fid))
        if not file:
            return self.error("File not found", 404)
        need_url = get_config("client.name") != ClientName.cmfchina
        status, extra, urls = await get_file_status(file)
        data = {
            "status": status.phrase,
            "extra": extra,
            "message": status.label,
        }
        if need_url:
            data.update({"url": urls[0] if len(urls) == 1 else urls})
        return self.data(data)

    @doc(summary="获取文件处理状态", tags=["external-api"], description=_doc)
    @Auth("browse")
    async def post(self, fid: str):
        file = await NewFile.find_by_id(int(fid))
        if not file:
            return self.error("File not found", 404)
        status, extra, urls = await get_file_status(file)
        data = {
            "status": status.phrase,
            "extra": extra,
            "message": status.label,
            "url": urls[0] if len(urls) == 1 else urls,
        }
        return self.data(data)


@plugin.route(r"/questions/(?P<qid>\d+)")
class GetQuestionAnswerHandler(BaseHandler):
    args = {
        "answer_type": fields.Str(load_default="merge", required=False),
        "add_element_index": fields.Bool(load_default=False, required=False),
    }

    @Auth("browse")
    @use_kwargs(args, location="query")
    async def get(self, qid, answer_type, add_element_index):
        """获取原始合并答案"""
        qid = int(qid)
        data = await get_annotation_answer(qid, answer_type, add_element_index=add_element_index)
        if not data:
            return self.error(_("Question not found"))
        return self.data(data)


class GetResultSchema(MMSchema):
    mold = fields.Int(load_default=0)
    json_style = fields.Int(data_key="simple", load_default=0)

    @validates("json_style")
    def validate_json_style(self, value, data_key):
        if get_config("client.name") == "fullgoal":
            if value != 2:
                raise ValidationError("simple must be 2.")

        return field_validate.OneOf([0, 1, 2])(value)


@plugin.route(r"/file/(?P<file_id>\d+)/result/(?P<file_format>json|csv)")
class GetResultHandler(DbQueryHandler):
    @staticmethod
    def convert(fid: int, answers: dict):
        if get_config("client.name") == "fullgoal":
            answer = list(answers.values())[0]
            ret = []
            for key, value in answer.items():
                if match := P_NUM_FIELD.search(key):
                    value = value or {}
                    value["title"] = match.group("field")
                    value["context"] = value.pop("text", None)
                    ret.append({match.group("num"): value})
            return {"fileID": fid, "answer": ret}
        return answers

    async def get_result(self, file, questions, file_format, json_style):
        answer_readers = []
        for question in questions:
            if is_empty_answer(question.answer):
                continue
            answer_readers.append(CommonAnswerReader(question.answer))

        if not answer_readers:
            return None, None

        if file_format == "json":
            answers = {}
            for answer_reader in answer_readers:
                answers[answer_reader.mold_name] = answer_reader.to_json(json_style)
            answers = self.convert(file.id, answers)
            data = json.dumps(answers, ensure_ascii=False, indent=4)
            data = bytes(data, "utf-8")
        else:  # csv
            if len(answer_readers) == 1:
                data = answer_readers[0].to_csv()
            else:
                file_format = "zip"
                res = io.BytesIO()
                with ZipFile(res, "w") as res_fp:
                    for answer_reader in answer_readers:
                        data = answer_reader.to_csv()
                        res_fp.writestr(f"{answer_reader.mold_name}.csv", data)
                res.seek(0)
                data = res.read()

        file_name = f"{os.path.splitext(file.name)[0]}.{file_format}"
        return data, file_name

    @staticmethod
    async def get_questions(fid, mold):
        questions = []
        if mold:
            if question := await NewQuestion.find_by_fid_mid(fid, mold):
                questions.append(question)
        else:
            questions = await NewQuestion.find_by_fid(fid)
        return questions

    @Auth("browse")
    @use_kwargs(GetResultSchema, location="query")
    async def get(self, file_id, file_format, mold, json_style):
        """获取文档分析结果接口"""
        file = await NewFile.find_by_id(file_id)
        if not file:
            return self.error(_("Item Not Found"), http.HTTPStatus.NOT_FOUND)
        if file.pdf_parse_status != PDFParseStatus.COMPLETE:
            return self.error(_("The file is being processed, please try again later"), http.HTTPStatus.ACCEPTED)

        questions = await self.get_questions(file.id, mold)
        if not questions:
            return self.error(_("Item Not Found"), http.HTTPStatus.NOT_FOUND)

        data, file_name = await self.get_result(file, questions, file_format, json_style)
        if not data:
            return self.error(_("data not ready"), http.HTTPStatus.ACCEPTED)

        return await self.export(data, file_name)

    @Auth("browse")
    @use_kwargs(GetResultSchema, location="query")
    async def post(self, file_id, file_format, mold, json_style):
        """获取文档分析结果接口"""
        file = await NewFile.find_by_id(file_id)
        if not file:
            return self.error(_("Item Not Found"), http.HTTPStatus.NOT_FOUND)
        if file.pdf_parse_status != PDFParseStatus.COMPLETE:
            return self.error(_("The file is being processed, please try again later"), http.HTTPStatus.ACCEPTED)

        questions = await self.get_questions(file.id, mold)
        if not questions:
            return self.error(_("Item Not Found"), http.HTTPStatus.NOT_FOUND)

        data, file_name = await self.get_result(file, questions, file_format, json_style)
        if not data:
            return self.error(_("data not ready"), http.HTTPStatus.ACCEPTED)

        return await self.export(data, file_name)


@plugin.route(r"/meeting/(?P<date>\d{8})")
class GetMeetingInfoHandler(DbQueryHandler):
    @Auth("browse")
    async def get(self, **kwargs):
        """按日期获取会议信息"""
        date = datetime.strptime(kwargs["date"], "%Y%m%d")
        start = date.timestamp()
        end = (date + timedelta(days=1)).timestamp()

        mold = await NewMold.find_by_name("会议通知")
        if not mold:
            raise CustomError("can't find schema，this api is not avliable")

        result = {}
        for _file in await NewFile.list_by_range(mold=mold.id, created_from=start, created_to=end):
            question = await NewQuestion.find_by_fid_mid(_file.id, mold.id)
            answer = await NewAnswer.find_standard(question.id)
            if not answer:
                continue
            converter = SimpleJSONConverter(answer.data)
            for column, groups in converter.convert().items():
                if groups:
                    result.setdefault(column, []).extend(groups if isinstance(groups, list) else [groups])
        self.finish(result)


@plugin.route(r"/schemaResult")
class GetFileResultHandler(DbQueryHandler):
    """中信建投定制"""

    @Auth("browse")
    async def get(self):
        """获取文档完整标注结果"""
        file_id = int(self.get_argument("fileId", "0"))
        file_format = self.get_argument("format", "json")
        req_id = self.get_argument("reqId", "")
        mold = int(self.get_argument("mold", "0"))

        _file = await NewFile.find_by_id(file_id)
        if not _file:
            return self.ext_error(_("Invalid file_id"), req_id=req_id)

        answer_data = None
        if mold:
            question = await NewQuestion.find_by_fid_mid(_file.id, mold)
        else:
            if config.get_config("client.support_multiple_molds"):
                raise CustomError("mold is needed when support_multiple_molds is open")
            questions = await NewQuestion.find_by_fid(_file.id)
            question = questions[0] if questions else None
        if question:
            answer_data = (
                question.answer if question.answer.get("userAnswer", {}).get("items", []) else question.preset_answer
            )
        if not answer_data:
            return self.ext_error(_("Answer not ready yet"), req_id=req_id)

        if file_format == "json":
            data = {
                "statusCode": 200,
                "reqId": req_id,
                "msg": "成功",
                "data": {
                    "id": file_id,
                    "filename": _file.name,
                    "answer": answer_data,
                },
            }
            data = json.dumps(data).encode()
        else:
            data = SimpleJSONConverter(answer_data).to_csv()

        if not data:
            return self.ext_error(_("occur error in handling file"), req_id=req_id)

        export_file_name = os.path.splitext(urllib.parse.quote(_file.name))[0]
        self.set_header("Content-Type", "text/{}".format(file_format))
        self.set_header(
            "Content-Disposition", "attachment; filename={}_{}.{}".format(_file.id, export_file_name, file_format)
        )
        self.finish(data)
        return None


async def get_page_details(fileobj):
    url = config.get_config("app.auth.pdfinsight.url") + "/api/v1/pdf/elements?chars=1&column=1&ocr=1"
    files = {"file": ("name", fileobj)}
    async with httpx.AsyncClient(verify=False, timeout=30) as client:
        response = await client.post(url, files=files)
        if response.status_code != 200:
            logging.info("OCR insight text within frame failed")
            return None
        page_details = response.json()
        rsp_data = page_details.get("data")
        return rsp_data


def delete_by_prefix(prefix):
    for path in glob.glob(tmp_storage.mount(prefix + "*")):
        if tmp_storage.exists(path):
            logging.debug(f"delete temp file: {path}")
            tmp_storage.delete_file(path)


@plugin.route(r"/ocr/convert_html")
class ConvertHTMLHandler(DbQueryHandler):
    @Auth("browse")
    async def post(self):
        page_no = self.get_argument("page", "0")
        if not page_no.isdigit():
            return self.ext_error(_("Page number must be an integer"))
        req_file = self.request.files.get("file")
        if not req_file:
            return self.ext_error(_("No file uploaded"))
        filename = req_file[0]["filename"]
        basename, ext = os.path.splitext(filename)
        ext = ext.lower()
        if ext not in (".pdf", ".jpg", ".jpeg"):
            return self.ext_error(_("only pdf, jpg and jpeg are supported"))
        filebody = req_file[0]["body"]

        _uuid = uuid4().hex
        pdf_save_path = tmp_storage.mount("{}.pdf".format(_uuid))
        if ext in (".jpeg", ".jpg"):
            image_save_path = tmp_storage.mount("{}.jpg".format(_uuid))
            with open(image_save_path, "wb") as w_f:
                w_f.write(filebody)
            converted = convert_image_to_pdf(image_save_path, pdf_save_path)
            if not converted:
                logging.error("image file not converted")
                delete_by_prefix(_uuid)
                return self.ext_error(_("image file not converted"))
        else:
            with open(pdf_save_path, "wb") as w_f:
                w_f.write(filebody)

        page_no = int(page_no) - 1 if ext == ".pdf" else 0
        out_path = tmp_storage.mount("{}.0.pdf".format(_uuid))
        pick_page_from_pdf(pdf_save_path, page_no, out_path)
        with open(out_path, "rb") as r_f:
            filebody = r_f.read()
        try:
            # 可能失败的原因: 超时/模板填充错误等返回统一报错信息
            converted_html = await self.convert_to_html(filebody)
        except httpclient.HTTPError as exp:
            logging.error(f"Possible timeout error: {exp}")
            return self.ext_error(_("Request timed out"))
        except Exception as exp:
            logging.error(f"Convert to html failed: {exp}")
            return self.ext_error(_("Convert to html failed"))
        else:
            self.finish(converted_html)
        finally:
            delete_by_prefix(_uuid)

    async def convert_to_html(self, fileobj):
        page_details = await get_page_details(fileobj)
        all_elements_list = self.get_current_page_elements_sorted(page_details)
        all_blocks_list = self.construct_elements_before_plot(all_elements_list)
        html = self.get_html(all_blocks_list)
        return html

    @staticmethod
    def get_current_page_elements_sorted(page_details):
        # all elements sorted by its index
        target_elements = []
        for ele in page_details:
            if ele in ["tables", "paragraphs", "page_headers", "page_footers", "image"]:
                for para_cell in page_details[ele]:
                    para_cell.update({"element_type": ele})
                    target_elements.append(para_cell)
        return sorted(target_elements, key=lambda x: (x.get("outline")[1], x.get("outline")[0]))

    def construct_elements_before_plot(self, target_elements):
        all_block_list = []
        for block in target_elements:
            if block:
                if block["element_type"] == "tables":
                    table_list = self.convert_table2cells_list(block)
                    table_list.append("table")
                    all_block_list.append(table_list)
                elif block["element_type"] == "image":
                    all_block_list.append([block.get("url"), "image"])
                elif block["element_type"] in ["paragraphs", "page_headers", "page_footers"]:
                    if "chars" in block:
                        style_body = block["chars"][0]
                    else:
                        style_body = {}
                    all_block_list.append([style_body, block.get("text", ""), block["element_type"]])

        return all_block_list

    @staticmethod
    def get_html(all_block_list):
        page_template_path = os.path.join(config.project_root, "template", "page.html")
        page_html = Template(filename=page_template_path).render(all_block_list=all_block_list)
        return page_html

    @staticmethod
    def convert_table2cells_list(table_block):
        row_count = len(table_block["grid"]["rows"])
        column_count = len(table_block["grid"]["columns"])
        table_list = []
        for each_row in range(row_count + 1):
            row_list = []
            for each_column in range(column_count + 1):
                if str(each_row) + "_" + str(each_column) in table_block["cells"]:
                    each_cells = table_block["cells"][str(each_row) + "_" + str(each_column)]
                    if "chars" in each_cells:
                        each_cells.pop("chars")
                    if "box" in each_cells:
                        each_cells.pop("box")
                    if "page" in each_cells:
                        each_cells.pop("page")
                    if "styles_diff" in each_cells:
                        each_cells.pop("styles_diff")
                    if each_cells["styles"].get("italic"):
                        each_cells["styles"]["italic"] = "italic"
                    else:
                        each_cells["styles"]["italic"] = "normal"
                    row_list.append(table_block["cells"][str(each_row) + "_" + str(each_column)])
                else:
                    row_list.append({})
            table_list.append(row_list)

        for merge_data in table_block["merged"]:
            target_cell = merge_data[0]

            rowspan = set()
            colspan = set()
            for each_merge in merge_data:
                rowspan.add(each_merge[0])
                colspan.add(each_merge[1])

            table_list[target_cell[0]][target_cell[1]]["rowspan"] = len(rowspan)
            table_list[target_cell[0]][target_cell[1]]["colspan"] = len(colspan)
        return table_list


@plugin.route(r"/extractResult")
class GetAnswerHandler(DbQueryHandler):
    """中信建投定制"""

    @Auth("browse")
    async def get(self):
        """获取精简结果"""
        file_id = int(self.get_argument("fileId", "0"))
        req_id = self.get_argument("reqId", None)
        is_export = self.get_argument("isExport", "false")
        mold = int(self.get_argument("mold", "0"))
        _file = await NewFile.find_by_id(file_id)
        if not _file:
            return self.ext_error(_("Invalid file_id"), req_id=req_id)

        if mold:
            question = await NewQuestion.find_by_fid_mid(_file.id, mold)
            if not question:
                raise CustomError(f"can't find question for ({_file.id}, {mold})")
        else:
            if config.get_config("client.support_multiple_molds"):
                raise CustomError("mold is needed when support_multiple_molds is open")
            questions = await NewQuestion.find_by_fid(_file.id)
            if not questions:
                raise CustomError(f"can't find question for ({_file.id}, {mold})")
            question = questions[0]
            logging.warning("query result with no mold, return the first question by default")

        answer_data = question.answer if question.answer else question.preset_answer
        if not answer_data:
            return self.ext_error(_("Answer not ready yet"), req_id=req_id)

        answer_reader = AnswerReader(answer_data)
        answer_node = answer_reader.tree
        data = {}
        data = parser_answer_node(answer_node, data)
        if not data:
            return self.ext_error(_("occur error in handling file"), req_id=req_id)

        data = self.convert_format(data)
        if is_export == "true":
            data = json.dumps(data).encode()
            self.set_header("Content-Type", "text/{}".format(json))
            self.set_header(
                "Content-Disposition",
                "attachment; filename={}_{}.{}".format(file_id, urllib.parse.quote(_file.name), "json"),
            )
            self.finish(data)
            return None
        return self.ext_data(msg="成功", req_id=req_id, data=data)

    @staticmethod
    def convert_format(data):
        def format_answer(data, schema_name, extract_result):
            for item_name, item_contents in data[schema_name].items():
                item_content_res = []
                if isinstance(item_contents, dict):
                    if "texts" not in item_contents:
                        for sec_item_name, sec_item_content in item_contents.items():
                            sec_texts = sec_item_content["texts"]
                            score = sec_item_content["score"]
                            if sec_texts and isinstance(sec_texts[0], dict):
                                _sec_item_content = sec_texts[0].get("原文", [])
                                sec_item_choice = sec_texts[0].get("答案", "")
                                item_content_res.append(
                                    {
                                        "secItemName": sec_item_name,
                                        "secItemChoice": sec_item_choice,
                                        "secItemContent": [
                                            _sec_item_content,
                                        ],
                                        "secItemScore": score if _sec_item_content else None,
                                    }
                                )
                            else:
                                item_content_res.append(
                                    {
                                        "secItemName": sec_item_name,
                                        "secItemContent": sec_texts,
                                        "secItemScore": score if sec_texts else None,
                                    }
                                )
                    else:
                        # 处理只有二级字段的情况
                        texts = item_contents.get("texts")
                        score = item_contents.get("score")
                        item_content_res.append(
                            {
                                "secItemName": item_name,
                                "secItemContent": texts,
                                "secItemScore": score if item_contents else None,
                            }
                        )
                    item_res = {
                        "itemName": item_name,
                        "itemContent": item_content_res,
                    }
                    extract_result.append(item_res)
                elif isinstance(item_contents, list):
                    for content in item_contents:
                        if isinstance(content, dict):
                            item_content_res.append(
                                {
                                    "itemName": item_name,
                                    "itemChoice": content.get("答案", ""),
                                    "itemContent": content.get("原文", []),
                                }
                            )
                        else:
                            item_content_res.append(
                                {
                                    "itemName": item_name,
                                    "itemContent": content,
                                }
                            )
                        extract_result.append(item_content_res)
            return extract_result

        extract_result = []
        schema_name = list(data.keys())[0]
        result = format_answer(data, schema_name, extract_result)
        return result


# @plugin.route(r"/file/(?P<fid>\d+)/prompt/elements")
# class AllCrudeAnswerHandler(BaseHandler):
#
#     async def get(self, *args):
#         fid = int(args[0])
#         res = {}
#         group_by = self.get_query_argument("groupby", "item")
#         if not fid:
#             raise CustomError(_("need fid"))
#
#         _file = await NewFile.find_by_id(fid)
#         if not _file:
#             raise CustomError(_("can't find file"))
#
#         crude_answer = await Question.select("crude_answer").where(Question.fid == _file.id).gino.scalar()
#         mold_data = await Mold.select("data").where(Mold.id == _file.mold).gino.scalar()
#         schema = Schema(mold_data)
#         for path in schema.iter_schema_attr():
#             aid = attribute_id(path)
#             items = predict_element(crude_answer, aid, group_by)
#             for item in items:
#                 for key in ["score", "outlines"]:
#                     if key in item:
#                         item.pop(key)
#             res["|".join(path)] = items
#
#         return self.data(res)


@plugin.route(r"/file/(?P<fhash>[^/]+)")
class FileUrlHandler(BaseHandler):
    async def get(self, fhash):
        res = {}
        _file = await NewFile.find_by_hash(fhash)
        if _file:
            params = {"domain": config.get_config("web.domain"), "id": _file.id}
            res = {
                "pdf": "http://%(domain)s/api/v1/plugins/fileapi/external/file/%(id)s/pdf" % params,
                "pdfinsight": "http://%(domain)s/api/v1/plugins/fileapi/external/file/%(id)s/pdfinsight" % params,
            }

        return self.data(res)


@plugin.route(r"/files/(\d+)/(origin|pdf|pdfinsight|docx|clean-files|scanned-pdf-restore)")
class ExternalFileHandler(BaseHandler):
    @Auth("browse")
    async def get(self, fid, which):
        file = await NewFile.find_by_id(int(fid))
        if not file:
            raise CustomError(_("not found file"), resp_status_code=http.HTTPStatus.NOT_FOUND)

        if which == "clean-files":
            # 专为清稿文件提供
            if (
                file.is_word
                and file.task_type == TaskType.CLEAN_FILE.value
                and file.pdf_parse_status == PDFParseStatus.COMPLETE
            ):
                filename = os.path.splitext(file.name)[0] + ".docx"
                return await self.export(localstorage.mount(file.docx_path()), filename)
            return await self.export(localstorage.mount(file.path()), file.name)

        if which == "origin":
            return await self.export(localstorage.mount(file.path()), file.name)

        if which == "pdf":
            if not file.pdf or not localstorage.exists(file.pdf_path()):
                raise CustomError(_("the pdf file is not ready"), resp_status_code=http.HTTPStatus.NOT_FOUND)
            return await self.export(localstorage.mount(file.pdf_path()), f"{file.name}.pdf")

        if which == "docx":
            if not file.docx:
                docx_hash = await convert_to_docx(file)
                if not docx_hash:
                    raise CustomError(_("the docx file is not ready"), resp_status_code=http.HTTPStatus.NOT_FOUND)
            data = localstorage.read_file(file.docx_path(), auto_detect=True)
            return await self.export(data, os.path.splitext(file.name)[0] + ".docx")

        if which == "scanned-pdf-restore":
            meta_info = file.meta_info or {}
            if meta_info.get("revise_pdf") == "failed":
                return self.error(_("the scanned-pdf restore failed"))
            if not file.revise_pdf or not localstorage.exists(file.revise_pdf_path()):
                raise CustomError(
                    _("the scanned-pdf-restore file is not ready"), resp_status_code=http.HTTPStatus.NOT_FOUND
                )
            return await self.export(localstorage.mount(file.revise_pdf_path()), file.name)

        path = file.pdfinsight_path()
        if not path or not localstorage.exists(path):
            raise CustomError(_("interdoc data not ready"), resp_status_code=http.HTTPStatus.NOT_FOUND)
        return await self.export(localstorage.mount(path), f"{file.pdfinsight}.zip")


@plugin.route(r"/question/(\d+)/run")
class QuestionRunTaskHandler(BaseHandler):
    task_schema = {"task": fields.Str(required=True, validate=field_validate.OneOf(["preset"]))}

    @Auth("browse")
    @use_kwargs(task_schema, location="query")
    async def get(self, *args, **kwargs):
        """重跑预测任务"""
        qid = int(args[0])
        if kwargs["task"] == "preset":
            preset_answer_by_qid.delay(qid, force_predict=True)
        return self.data("task queued!")


class HtAnswerFormatter:
    def __init__(self):
        pass

    def dumps(self, answer, rule_results):
        return {"answer": self.dump_schema_answer(answer), "rule": self.dump_rule_results(rule_results)}

    @staticmethod
    def dump_schema_answer(answer):
        res = {}
        for item in answer["userAnswer"]["items"]:
            key_path = [c.split(":") for c in json.loads(item["key"])]
            col = key_path[-1][0]
            res[col] = "\n".join(["".join([box["text"] for box in data["boxes"]]) for data in item["data"]])
        return res

    @staticmethod
    def dump_rule_results(rule_results):
        groups = {}
        for result in rule_results:
            group = groups.setdefault(result.rule, {})
            group[result.second_rule] = not bool(result.result)
        return groups


async def login_by_token(request: HTTPServerRequest) -> NewAdminUser | None:
    token = request.headers.get("access-token")
    if not token:
        logging.debug("can't find access token in request header")
        return None
    password = gen_password(token, "")

    access_token = await NewAccessToken.find_by_kwargs(password=password)
    if not access_token:
        logging.debug(f"can't find available access token by password: {password}")
        return None

    user = await NewAdminUser.find_by_id(access_token.user_id)
    if not user:
        logging.error(f"can't find user from access token {access_token.id}")
        return None
    user.permission.append({"perm": "extapi"})
    return user


@plugin.route(r"/file/(?P<file_id>\d+)/result")
class GetResultHandlerForHT(PermCheckHandler):
    formatter = HtAnswerFormatter()

    async def get(self, file_id):
        """获取文档分析结果接口"""
        self.current_user = await login_by_token(self.request)
        if not self.current_user:
            return self.error("Invalid access-token")
        await self.check_file_permission(file_id)

        _file = await NewFile.find_by_id(file_id)
        if not _file:
            return self.error(_("Invalid file_id"))

        answer_data = None
        questions = await NewQuestion.find_by_fid(_file.id)
        if questions:
            question = questions[0]
            answer_data = question.answer if question.answer else question.preset_answer
        if not answer_data:
            return self.error(_("Answer not ready yet"))
        rule_results = await NewRuleResult.get_by_fid(file_id)

        data = self.formatter.dumps(answer_data, rule_results)
        return self.data(data)


@plugin.route(r"/tree/(\d+)/file")
class ExtUploadFileHandler(PermCheckHandler):
    user_args = {
        "mold": fields.Integer(load_default=None),
    }
    file_args = {
        "files": fields.List(
            fields.Raw(),
            data_key="file",
            required=True,
            error_messages={"required": "not found upload document"},
        ),
    }

    @use_kwargs(user_args, location="form")
    @use_kwargs(file_args, location="files")
    async def post(self, tid, files: list[HTTPFile], mold):
        # TODO: 可能的两个问题
        # 1. Tornado默认文件上传是写到内存里的，这里如果传大文件/多文件内存不友好
        # 2. 一次性上传多份文档，会影响其他用户文档处理等待时间
        self.current_user = await login_by_token(self.request)
        if not self.current_user:
            return self.error("Invalid access-token")
        await self.check_tree_permission(tid)

        tree = await NewFileTree.find_by_id(tid)
        if not tree:
            raise CustomError(_("can't find the tree"))

        project = await NewFileProject.find_by_id(tree.pid)
        if not project:
            raise CustomError(_("can't find the project"))

        if not mold:
            molds = await NewFileTree.find_default_molds(tid)
        else:
            molds = [mold]

        ids = []
        for file in files:
            newfile = await NewFileService.create_file(
                file.filename,
                file.body,
                molds,
                project.id,
                tree.id,
                self.current_user.id,
            )
            await process_file(newfile)
            ids.append(newfile.id)
        return self.data({"id": ids[0], "ids": ids})


@plugin.route(r"/gffund/export")
class GfExportHandler(DbQueryHandler):
    """广发基金导出"""

    get_args = {
        "project_id": fields.Int(load_default=1),
        "schema_id": fields.Int(load_default=None),
    }

    # @Auth("browse")
    @use_kwargs(get_args, location="query")
    async def get(self, **kwargs):
        project_id = kwargs["project_id"]
        schema_id = kwargs["schema_id"]
        project = await NewFileProject.find_by_id(project_id)
        if not project:
            return self.error("project not exists")
        if not schema_id:
            if not project.default_molds:
                return self.error("project schema unspecified")
            schema_id = project.default_molds[0]

        files = await NewFile.find_by_kwargs(pid=project_id, delegate="all")
        if not files:
            return self.error("project is empty")

        workbook = openpyxl.Workbook()
        headers = [
            "基金名称",
            "基金代码",
            "报告名称",
            "份额名称",
            "期初时间",
            "期末时间",
        ]
        data = await self.get_data(schema_id, files)
        dump_data_to_worksheet(workbook, headers, data)
        with io.BytesIO() as bytes_io:
            workbook.save(bytes_io)
            return await self.export(bytes_io.getvalue(), f"{project.name}.xlsx")

    async def get_data(self, mid, files):
        tasks = set()
        results = {}
        for file in files:
            question = await NewQuestion.find_by_fid_mid(file.id, mid)
            if not question:
                continue
            results[file.id] = {}
            task = asyncio.create_task(self.get_data_for_file(question))
            tasks.add(task)
            task.add_done_callback(lambda t: self._task_callback(results, tasks, t))

        await asyncio.gather(*tasks)
        data = []
        for result in results.values():
            data.extend(result)
        return data

    async def get_data_for_file(self, question):
        data = []
        answer_reader = CommonAnswerReader(question.answer)
        fund_name = self.get_text_from_answer_node(answer_reader, ["基金名称"])
        fund_code = self.get_text_from_answer_node(answer_reader, ["基金代码"])
        report_name = self.get_text_from_answer_node(answer_reader, ["报告名称"])
        shares = self.get_text_from_answer_node(answer_reader, ["报告期时间"])
        for share in shares:
            data.append(
                [
                    fund_name,
                    fund_code,
                    report_name,
                    share["份额名称"],
                    share["期初时间"],
                    share["期末时间"],
                ]
            )

        return {
            "file_id": question.fid,
            "data": data,
        }

    @staticmethod
    def get_text_from_answer_node(answer_reader, path):
        answer_node = answer_reader.find_nodes(path)
        answers = []
        for node in answer_node:
            if node.isleaf():
                return node.data.plain_text
            answer_dict = node.to_formatter_dict()
            answer = {}
            for key, answer_item in answer_dict.items():
                answer[key] = answer_item.plain_text
            answers.append(answer)
        return answers

    @staticmethod
    def _task_callback(results: dict[str, dict], tasks: set[asyncio.Task], task: asyncio.Task):
        ret = task.result()
        results[ret["file_id"]] = ret["data"]
        tasks.discard(task)


@plugin.route(r"/gffund/upload")
class GFFundsUploadHandler(BaseHandler):
    """
    广发基金 申请表上传接口
    """

    args_schema = {
        "fax_number": fields.Str(load_default=None),
        "fax_subject": fields.Str(load_default=None),
        "tree_id": fields.Integer(load_default=0),
        "file_id": fields.Str(required=True),
    }

    @Auth("browse")
    @use_kwargs({**args_schema}, location="form")
    @use_kwargs(
        {
            "post_file": fields.Raw(
                data_key="file",
                required=True,
            ),
        },
        location="files",
    )
    async def post(self, fax_number: str, fax_subject: str, tree_id: int, file_id: str, post_file: HTTPFile):
        gffund_file = GFFundUploadFile(fax_number, fax_subject, tree_id, file_id, post_file)
        mold_id = await gffund_file.get_mold_id()
        files = gffund_file.process_file()
        if not files:
            return self.error(_("Invalid file"))
        ret = []
        uid = ADMIN.id
        project = await gffund_file.get_file_project(uid)
        for doc_name, doc_raw in files:
            # 创建文档记录/保存上传文件
            file = await NewFileService.create_file(
                doc_name, doc_raw, [mold_id], project.id, project.rtree_id, uid, meta_info={"gffund_file_id": file_id}
            )
            await NewTimeRecord.update_record(file.id, "upload_stamp")
            await process_file(file, force_predict=True)
            ret.append({"id": str(file.id), "gffund_file_id": file_id, "filename": file.name})
        return self.data(data=ret)


@plugin.route(r"/gffund/fax")
class GFFundsFaxHandler(BaseHandler):
    """
    广发基金 传真号上传接口
    """

    @Auth("browse")
    @use_kwargs(
        {
            "fax_file": fields.Raw(
                data_key="fax_file",
                required=True,
            ),
        },
        location="files",
    )
    async def post(self, fax_file: HTTPFile):
        df = pd.read_excel(fax_file.body, dtype=str)
        query = process_df_fax(df)
        await pw_db.execute(query)
        return self.data(None)


class AuditItem(MMSchema):
    name = fields.Str(
        required=True,
        validate=field_validate.Length(min=1),
    )
    schema_field = fields.List(
        fields.Str(
            required=True,
            validate=field_validate.Length(min=1),
        ),
        required=True,
    )
    is_compliance = fields.Bool(required=True)
    suggestion = fields.Str(required=False)
    reasons = fields.List(fields.Dict(), required=False)
    fid = fields.Int(required=True)
    qid = fields.Int(required=True)
    schema_id = fields.Int(required=True)


@plugin.route(r"/audit/results")
@plugin.route(r"/gffund/audit")
class GFFundsAuditHandler(BaseHandler):
    @Auth("browse")
    @use_kwargs(
        {
            "audit_items": fields.List(fields.Nested(AuditItem), required=True),
            "fid": fields.Int(required=True),
            "schema_id": fields.Int(required=True),
            "answer_type": fields.Int(load_default=AuditAnswerType.final_answer.value),
        },
        location="json",
    )
    async def post(self, fid, schema_id, audit_items: list[dict], answer_type: int):
        file = await NewFile.find_by_id(fid)
        if not file:
            return self.error(_("Not all ids valid."), status_code=http.HTTPStatus.BAD_REQUEST)
        if get_config("client.name") == ClientName.cmfchina:
            mold = await NewMold.find_by_id(schema_id)
            if not mold:
                return self.error(_("Not all ids valid."), status_code=http.HTTPStatus.BAD_REQUEST)
            question = await NewQuestion.find_by_kwargs(mold=mold.id, fid=file.id)
            if not question:
                return self.error(_("Not all ids valid."), status_code=http.HTTPStatus.BAD_REQUEST)
        else:
            question = await NewQuestion.get_master_question(file.id)
            if not question:
                return self.error(_("Not all ids valid."), status_code=http.HTTPStatus.BAD_REQUEST)
            mold = await NewMold.find_by_id(question.mold)
            if not mold:
                return self.error(_("Not all ids valid."), status_code=http.HTTPStatus.BAD_REQUEST)
        # 1. 插入新审核状态
        audit_status: NewAuditStatus = await pw_db.create(
            NewAuditStatus,
            fid=fid,
            schema_id=question.mold,
            status=AuditStatusType.CALLBACK_PROCESSING.value,
            answer_type=answer_type,
        )
        inspector = create_inspector(file, mold, question)
        if answer_type == AuditAnswerType.final_answer.value:
            context = await inspector.build_context()
        else:
            context = await inspector.build_context_for_preset_answer()
        await inspector.prepare_data(context)
        try:
            # 2.插入新审核数据
            await self.update_inspect_results(fid, schema_id, audit_items, inspector, answer_type)
            # 3.修改审核状态
            await audit_status.set_status(AuditStatusType.CALLBACK_PROCESSING_DONE.value)
        except Exception as e:
            print_exc(e, file_=LoggerAsFile(logger))
            await audit_status.set_status(AuditStatusType.CALLBACK_PROCESSING_FAILED.value)
            return self.error(str(e), status_code=400)
        return self.data(None)

    async def update_inspect_results(self, fid, schema_id, audit_items, inspector, answer_type):
        async with pw_db.atomic():
            # 1. 删除老数据
            await pw_db.execute(
                NewAuditResult.delete().where(
                    NewAuditResult.fid == fid,
                    NewAuditResult.schema_id == schema_id,
                    NewAuditResult.rule_type == RuleType.EXTERNAL.value,
                    NewAuditResult.answer_type == answer_type,
                )
            )
            # 2.插入新审核数据
            await NewAuditResult.bulk_insert(
                [
                    item.to_dict(exclude=[NewAuditResult.id])
                    for item in self.gen_schema_results(audit_items, inspector, answer_type)
                ]
            )

    @staticmethod
    def gen_schema_results(audit_items: list[dict], inspector, answer_type) -> Iterator[NewAuditResult]:
        for audit_item in audit_items:
            schema_results = inspector.manager.build_schema_results(audit_item.pop("schema_field"))
            yield NewAuditResult(
                **audit_item,
                is_compliance_ai=audit_item.get("is_compliance"),
                rule_type=RuleType.EXTERNAL.value,
                rule_id=RuleID.EXTERNAL_ID,
                schema_results=schema_results,
                answer_type=answer_type,
                order_key=NewAuditResult.get_first_position(schema_results, None),
            )


@plugin.route(r"/gtja/checklist")
class GTJACheckListHandler(BaseHandler):
    @use_kwargs(
        {"file": fields.Raw(required=True, validate=field_validate.Length(max=100 * 1024 * 1024))}, location="files"
    )
    async def post(self, file: HTTPFile):
        if file.content_type != "text/plain":
            return self.ext_error(_("Only text file are supported"))
        try:
            res_data = parse(file.body)
        except Exception as exp:
            logging.error(f"Parse check list file failed: {exp}")
            return self.ext_error(_("Parse check list file failed"))
        return self.data(res_data)


@plugin.route(r"/scanned_pdf/convert")
class ScannedPDFConverterHandler(BaseHandler):
    @Auth("browse")
    @use_kwargs(
        {"file": fields.Raw(required=True)},
        location="files",
    )
    async def post(self, file: HTTPFile):
        project_name = get_config("feature.scanned_pdf_project") or "scanned_pdf"
        project = await NewFileProjectService.create(name=project_name, visible=False)

        new_file = await NewFileService.create_file(
            file.filename,
            file.body,
            molds=[],
            pid=project.id,
            tree_id=project.rtree_id,
            uid=self.current_user.id,
            task_type=TaskType.SCANNED_PDF_RESTORE.value,
        )
        await process_file(new_file)
        return self.data({"file_id": new_file.id})


class FileSchema(MMSchema):
    url = fields.URL(required=True)
    tree_id = fields.Int(required=True)
    citics_id = fields.Str(required=True)
    meta = fields.Dict(load_default=dict)


class FilesSchema(MMSchema):
    files = fields.List(fields.Nested(FileSchema), load_default=list)


@plugin.route(r"/file_links")
class FileLinksHandler(BaseHandler):
    @Auth("browse")
    @use_kwargs(FilesSchema, location="json")
    async def post(self, files):
        tree_ids = set()
        for file_record in files:
            tree_ids.add(file_record["tree_id"])

        trees = await NewFileTree.find_by_ids(list(tree_ids))
        if len(trees) != len(tree_ids):
            invalid_ids = tree_ids - {i.id for i in trees}
            raise CustomError(
                _(f"列表中包含无效的 tree_id，请检查列表中包含下面 tree_id 的数据：{invalid_ids}"),
                resp_status_code=http.HTTPStatus.BAD_REQUEST,
            )
        projects = await NewFileProject.find_by_ids([i.pid for i in trees])
        projects_map = {i.id: i for i in projects}
        trees = {i.id: i for i in trees}

        result = []
        async with pw_db.atomic():
            for file_record in files:
                tree = trees[file_record["tree_id"]]
                project = projects_map.get(tree.pid)
                if not project:
                    msg = _(f"找不到对应的项目，请检查列表中包含下面 tree_id 的数据：{file_record['tree_id']}")
                    logger.error(msg)
                    raise CustomError(msg, resp_status_code=http.HTTPStatus.BAD_REQUEST)
                mold_ids = file_record["meta"].get("schema_ids", [])
                file = await NewFileService.create_file_from_link(
                    file_record["url"], uid=project.uid, tree=tree, mold_ids=mold_ids
                )
                result.append(
                    {
                        "id": file.id,
                        "citics_id": file_record["citics_id"],
                        "url": file_record["url"],
                    }
                )

        download_file.delay(result)

        return self.data(result)
