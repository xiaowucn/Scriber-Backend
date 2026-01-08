import hashlib
import http
import json
import logging
import os
from dataclasses import asdict

from webargs import ValidationError, fields

from remarkable.common import field_validate
from remarkable.common.apispec_decorators import use_kwargs
from remarkable.common.constants import PDFParseStatus
from remarkable.common.enums import TaskType
from remarkable.common.exceptions import CustomError
from remarkable.common.storage import localstorage
from remarkable.config import get_config
from remarkable.db import pw_db
from remarkable.models.new_file import NewFile
from remarkable.models.new_user import ADMIN
from remarkable.plugins.cgs import CGSHandler, plugin
from remarkable.plugins.cgs.auth import CgsTokenValidator
from remarkable.plugins.cgs.globals import CLEAN_FILE_TYPE, TITLE_FILE_TYPE
from remarkable.plugins.cgs.services.comment import remove_doc_title
from remarkable.pw_models.model import NewFileTree
from remarkable.service.new_file import NewFileService
from remarkable.service.new_file_project import NewFileProjectService
from remarkable.value_obj import CGSFileMeta
from remarkable.worker.tasks import process_file

logger = logging.getLogger(__name__)

MAX_FILE_SIZE = 100 * 1024 * 1024  # 100M


def _validate_file_size(post_files):
    for file in post_files:
        if len(file["body"]) > MAX_FILE_SIZE:
            raise ValidationError("仅支持上传 100MB 以内的文件，请确认后重新上传")


def _validate_file(post_files):
    if len(post_files) != 1:
        raise ValidationError("only support one file")
    _validate_file_size(post_files)


@plugin.route(r"/clean-files/upload")
class UploadHandlerForCGS(CGSHandler):
    form_args = {
        "sysfrom": fields.Str(load_default="-", validate=field_validate.OneOf(["PIF", "OAS", "FMP"])),
    }

    @CgsTokenValidator()
    @use_kwargs(form_args, location="form")
    @use_kwargs(
        {"post_files": fields.List(fields.Raw(), required=True, data_key="file", validate=_validate_file_size)},
        location="files",
    )
    async def post(self, post_files, sysfrom):
        default_project_name = get_config("cgs.default.clean_file_project")
        project = await NewFileProjectService.create(name=default_project_name)
        file_tree = await NewFileTree.find_by_id(project.rtree_id)
        data = []
        for file in post_files:
            suffix = os.path.splitext(file.filename)[1].lower()
            if suffix in CLEAN_FILE_TYPE:
                _data = await self.upload_for_single_file(
                    file,
                    project.id,
                    file_tree.id,
                    sysfrom,
                )
                data.extend(_data)
            else:
                return self.error(message="判断清稿的文件格式仅支持doc和docx", status_code=404)

        return self.data(data)

    @staticmethod
    async def upload_for_single_file(post_file, pid, tree_id, sysfrom):
        doc_name = post_file.filename
        doc_raw = post_file.body
        file = await NewFileService.create_file(
            name=doc_name,
            body=doc_raw,
            molds=[],
            pid=pid,
            tree_id=tree_id,
            uid=ADMIN.id,
            task_type=TaskType.CLEAN_FILE.value,
            sysfrom=sysfrom,
            meta_info={"as_docx": True},
        )
        await process_file(file, force_predict=True)
        return [{"id": file.id, "filename": doc_name}]


@plugin.route(r"/clean-files/(\d+)/info")
class GetCleanInfoHandlerForCGS(CGSHandler):
    @CgsTokenValidator()
    async def get(self, fid):
        file = await NewFile.find_by_id(fid)
        if not file:
            raise CustomError(_("not found file"))
        if file.pdf_parse_status == PDFParseStatus.FAIL:
            return self.error(message="清稿文档处理失败", status_code=http.HTTPStatus.NOT_FOUND)
        if file.pdf_parse_status != PDFParseStatus.COMPLETE:
            return self.error(message="清稿文档处理中", status_code=http.HTTPStatus.ACCEPTED)
        meta_info = CGSFileMeta(**(file.meta_info or {}))
        return self.data(asdict(meta_info.clean_file))


@plugin.route(r"/clean-files/remove-title")
class RemoveTitleHandlerForCGS(CGSHandler):
    @CgsTokenValidator()
    @use_kwargs(
        {
            "post_files": fields.List(
                fields.Raw(),
                data_key="file",
                required=True,
                error_messages={"required": "not found upload document"},
                validate=_validate_file,
            )
        },
        location="files",
    )
    async def post(self, post_files):
        post_file = post_files[0]
        doc_type = os.path.splitext(post_file.filename)[1].lower()
        if doc_type in TITLE_FILE_TYPE:
            data = remove_doc_title(post_file.filename, post_file.body, doc_type)
            return await self.export(data, post_file.filename)
        elif doc_type == ".doc":
            return self.error(message="请先转换为docx文件", status_code=http.HTTPStatus.NOT_FOUND)
        return self.error(message="删除文档属性的文件格式仅支持pdf和docx", status_code=http.HTTPStatus.NOT_FOUND)


@plugin.route(r"/clean-files/(\d+)")
class DownloadHandlerForCGS(CGSHandler):
    args = {
        "doc_type": fields.String(
            required=True, validate=field_validate.OneOf(["word", "pdf"], error="仅支持word和pdf文件")
        ),
    }

    @CgsTokenValidator()
    @use_kwargs(args, location="query")
    async def get(self, fid, doc_type):
        file = await NewFile.find_by_id(fid)
        if not file:
            raise CustomError(_("not found file"), resp_status_code=http.HTTPStatus.NOT_FOUND)
        meta_info = CGSFileMeta(**(file.meta_info or {}))
        path = meta_info.clean_file.pdf_path if doc_type == "pdf" else meta_info.clean_file.docx_path
        if not path.exists() or not path.is_file():
            return self.error(message=f"{doc_type}类型清稿文件不存在", status_code=http.HTTPStatus.NOT_FOUND)

        return await self.export(
            path, f"{os.path.splitext(file.name)[0]}_清稿文件.{'pdf' if doc_type == 'pdf' else 'docx'}"
        )


@plugin.route(r"/clean-files/(\d+)/callback")
class ConvertCallback(CGSHandler):
    args = {
        "state": fields.String(required=True),
    }

    @CgsTokenValidator()
    @use_kwargs(
        {
            "post_files": fields.List(
                fields.Raw(), required=True, data_key="file", validate=field_validate.Length(min=1, max=1)
            )
        },
        location="files",
    )
    @use_kwargs(args, location="form", unknown="exclude")
    async def post(self, fid, state, post_files):
        async with pw_db.atomic():
            file = await NewFile.get_by_id(int(fid), for_update=True)
            if not file:
                raise CustomError(_("not found file"), resp_status_code=http.HTTPStatus.NOT_FOUND)

            state = json.loads(state)
            if state.get("fid") != int(fid):
                await file.update_(pdf_parse_status=PDFParseStatus.FAIL, only=["pdf_parse_status"])
                return self.error(message="参数错误", status_code=http.HTTPStatus.BAD_REQUEST)

            meta_info = CGSFileMeta(**file.meta_info)
            meta_info.clean_file.pdf = hashlib.md5(post_files[0].body).hexdigest()
            localstorage.write_file(meta_info.clean_file.pdf_path.as_posix(), post_files[0].body)
            file.meta_info = meta_info.to_dict()
            file.pdf_parse_status = PDFParseStatus.COMPLETE
            await file.update_(only=["meta_info", "pdf_parse_status"])
