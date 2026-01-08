import asyncio
import logging
import os
from pathlib import Path
from urllib.parse import urlparse

import httpx
from webargs import fields

from remarkable.answer.common import get_mold_name
from remarkable.answer.reader import AnswerReader
from remarkable.base_handler import Auth, BaseHandler
from remarkable.common import field_validate
from remarkable.common.apispec_decorators import use_kwargs
from remarkable.common.constants import AIStatus, OctopusFileType
from remarkable.common.util import count_pdf_pages
from remarkable.config import get_config
from remarkable.converter.csc_octopus import OctopusConverter
from remarkable.db import pw_db
from remarkable.models.new_file import NewFile
from remarkable.models.new_user import ADMIN
from remarkable.plugins import Plugin
from remarkable.pw_models.model import NewFileProject, NewFileTree, NewMold
from remarkable.pw_models.question import NewQuestion
from remarkable.service.new_file import NewFileService, octopus_html2pdf
from remarkable.service.new_file_project import NewFileProjectService
from remarkable.worker.tasks import process_file

plugin = Plugin(Path(__file__).parent.name)
mold_map = get_config("octopus.mold_map") or {}
logger = logging.getLogger(__name__)


@plugin.route(r"/upload")
class CscOctopusHandler(BaseHandler):
    args_schema = {
        "url": fields.Str(load_default="", validate=field_validate.URL()),
        "file_type": fields.Str(load_default="1", validate=field_validate.OneOf(mold_map.keys())),
        "confirm_url": fields.Str(load_default=get_config("octopus.confirm_url"), validate=field_validate.URL()),
        "scriber_domain": fields.Str(
            load_default=get_config("octopus.upload.scriber_domain"), validate=field_validate.URL()
        ),
        "csc_project_id": fields.Str(data_key="projectId", load_default=None),
        "csc_bond_id": fields.Str(data_key="bondId", load_default=None),
        "csc_bond_type": fields.Str(data_key="bondType", load_default=None),
        "csc_duration_id": fields.Str(data_key="durationId", load_default=None),
    }

    @Auth("browse")
    @use_kwargs({**args_schema}, location="form")
    @use_kwargs({"post_files": fields.Raw(data_key="file", required=False)}, location="files")
    async def post(self, url, file_type, confirm_url, scriber_domain, post_files=None, **kwargs):
        project_name = get_config("octopus.upload.project_name")
        project = await self.make_sure_project_exist(project_name)
        tree_id = project.rtree_id
        display_mold_id = None
        if file_type == OctopusFileType.REGISTER.value:  # "回售登记"类型的问题 这类文档指定了三个schema
            mold_names = get_config("octopus.register_mold_names")
            mold_ids = await pw_db.scalars(NewMold.select(NewMold.id).where(NewMold.name.in_(mold_names)))
        else:
            mold = await NewMold.find_by_name(mold_map[file_type])
            mold_ids = [mold.id]
            display_mold_id = mold.id

        meta_info = {"confirm_url": confirm_url}
        meta_info.update(kwargs)
        # 界面点击确认按钮的次数  每点击一次+1
        meta_info.update({"csc_click_count": 0})

        # 创建文件+开启预测流程
        if post_files or url:
            fid = await self.create_octopus_file(post_files, url, mold_ids, project, tree_id, meta_info, file_type)
        else:
            return self.error("Url and post_files cannot be both empty!")

        # 轮询预测结果是否OK
        timeout = get_config("octopus.check.timeout.count", default=20)
        step = get_config("octopus.check.timeout.step_second", default=1)
        qid, display_mold_id = await self.poll_preset_result(fid, file_type, display_mold_id, timeout, step)
        if qid:
            queries = {
                "treeId": tree_id,
                "fileId": fid,
                "schemaId": display_mold_id,
                "projectId": project.id,
                "from": "octopus",
            }
            return self.data(
                {
                    "isSuccess": 1,
                    "paitechId": fid,
                    "paitechURL": _build_display_url(f"{scriber_domain}/#/csc-octopus/project/remark/{qid}", queries),
                    "confirmURL": confirm_url,
                }
            )
        logger.error(f"fid={fid}, ai result is not finished in {timeout * step} seconds")
        return self.error(f"fid={fid}, ai result is not finished in {timeout * step} seconds")

    async def poll_preset_result(self, fid, file_type, display_mold_id, timeout, step):
        time_count = 0
        qid = 0
        while time_count < timeout:
            if file_type == OctopusFileType.REGISTER.value:  # "回售登记" 指定了三个schema
                questions = await NewQuestion.find_by_fid(fid)
                for question in questions:
                    if question.ai_status == AIStatus.FINISH and self.has_title(question):
                        qid = question.id
                        display_mold_id = question.mold
                        break
                if display_mold_id:
                    break
            else:
                question = await NewQuestion.find_by_fid_mid(fid, display_mold_id)
                if question.ai_status == AIStatus.FINISH:
                    qid = question.id
                    break
            time_count += step
            await asyncio.sleep(step)
        return qid, display_mold_id

    async def create_octopus_file(self, post_files, url, mold_ids, project, tree_id, meta_info, file_type):
        fid = None
        if post_files:
            # document from upload
            doc_name = post_files.filename
            doc_raw = post_files.body
            # 创建文档记录/保存上传文件
            if os.path.splitext(doc_name)[1].lower() not in [".doc", ".docx", ".pdf"]:
                logger.error(f"{doc_name}, file format not supported")
                return self.error(f"{doc_name}, file format not supported")
            force_ocr_pages = None
            if file_type == OctopusFileType.REGISTER.value:
                # check Whether the number of pdf pages is greater than 5 pages
                pdf_pages = count_pdf_pages(doc_raw)
                logger.info(f"{doc_name}, pdf pages: {pdf_pages}")
                if pdf_pages > 5:
                    force_ocr_pages = "0"

            file = await NewFileService.create_file(
                doc_name,
                doc_raw,
                mold_ids,
                project.id,
                tree_id,
                uid=ADMIN.id,
                meta_info=meta_info,
            )
            await process_file(file, force_predict=True, force_ocr_pages=force_ocr_pages)
            fid = file.id
        elif url != "":
            # document from https://www.chinabond.com.cn url
            try:
                doc_name, doc_raw = await octopus_html2pdf(await _fetch_from(url))
                file = await NewFileService.create_file(
                    doc_name, doc_raw, mold_ids, project.id, tree_id, uid=ADMIN.id, link=url, meta_info=meta_info
                )
                await process_file(file, force_predict=True)
            except AttributeError:
                logger.error(f"Wrong web url, {url}")
                return self.error(f"Wrong web url, {url}")
            fid = file.id

        return fid

    @staticmethod
    def has_title(question):
        if not question or not question.preset_answer:
            return False
        reader = AnswerReader(question.preset_answer)
        mold_name = get_mold_name(question.preset_answer)
        root_node, _ = reader.build_answer_tree()
        answer_items = root_node.to_dict(item_handler=lambda n: n.plain_text)[mold_name]
        if not answer_items:
            return False
        return answer_items[0].get("文档标题")

    @staticmethod
    async def make_sure_project_exist(name):
        file_tree = await NewFileTree.find_by_kwargs(name=name)
        file_project = await NewFileProject.find_by_kwargs(name=name)
        if not file_tree and not file_project:
            file_project = await NewFileProjectService.create(name=name, default_molds=[])
        return file_project


async def _fetch_from(url: str) -> str:
    headers = {"User-Agent": get_config("octopus.scrapy.user_agent") or "PAI", "Accept": "*/*"}
    proxy = get_config("octopus.proxy")
    if proxy:
        url = f"{proxy}{urlparse(url).path}"
    async with httpx.AsyncClient(verify=False, timeout=httpx.Timeout(timeout=30.0)) as client:
        response = await client.get(url, headers=headers)
    assert httpx.codes.is_success(response.status_code)
    return response.text


def _build_display_url(base_url, queries):
    query = ""
    for key, value in queries.items():
        query += f"&{key}={value}"

    return f"{base_url}?{query[1:]}"


@plugin.route(r"/files/confirm")
class CscOctopusSaveHandler(BaseHandler):
    args_schema = {
        "data": fields.Nested(
            {
                "fid": fields.Int(required=True),
                "userAnswer": fields.Dict(required=True),
                "schema": fields.Dict(required=True),
            },
            required=True,
        ),
    }

    @use_kwargs(args_schema, location="json")
    async def post(self, data):
        # only for debug
        # question = await NewQuestion.find_by_fid_mid(data['fid'], 10)
        # data.update(question.answer)
        file = await NewFile.find_by_id(data["fid"])
        meta_info = file.meta_info or {}
        csc_click_count = meta_info.get("csc_click_count", 0)
        if csc_click_count is not None:
            csc_click_count += 1
            meta_info["csc_click_count"] = csc_click_count
            await file.update_(meta_info=meta_info)
        converter = OctopusConverter(data)
        converted_answer = converter.convert()
        additional_data = {
            "paitechId": data["fid"],
            "projectId": meta_info.get("csc_project_id") or "",
            # 'csc_bond_id': meta_info.get('csc_bond_id') or '',
            "bondId": meta_info.get("csc_bond_id") or "",
            # 'csc_bond_type': meta_info.get('csc_bond_type') or '',
            "bondType": meta_info.get("csc_bond_type") or "",
            "durationId": meta_info.get("csc_duration_id") or "",
            "paitechBatchNo": csc_click_count,
        }
        if isinstance(converted_answer, list):
            for item in converted_answer:
                item.update(additional_data)
        else:
            converted_answer.update(additional_data)
        confirm_url = meta_info.get("confirm_url")
        if not confirm_url:
            return self.error("confirm_url not exists")
        result = await self.call_octopus(converted_answer, confirm_url)
        if result != "OK":
            return self.error(result)
        return self.data({})

    @staticmethod
    async def call_octopus(data, confirm_url):
        timeout = get_config("octopus.call_timeout", 5)
        try:
            logger.info(f"{data=}")
            async with httpx.AsyncClient(verify=False, timeout=httpx.Timeout(timeout=timeout)) as client:
                response = await client.post(url=confirm_url, json=data)
            if not httpx.codes.is_success(response.status_code):
                logger.error(f"call {confirm_url} failed")
                return "call octopus failed"
        except Exception:
            logger.error(f"call {confirm_url} timeout failed")
            return "call octopus timeout"
        return "OK"
