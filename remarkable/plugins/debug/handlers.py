import io
import json
import os
from http import HTTPStatus
from pathlib import Path
from zipfile import ZipFile

from webargs import fields

from remarkable.base_handler import Auth, BaseHandler, route
from remarkable.common import field_validate
from remarkable.common.apispec_decorators import doc, use_kwargs
from remarkable.common.constants import AutoDocStatus, TableType
from remarkable.common.enums import TaskType
from remarkable.common.storage import localstorage
from remarkable.common.util import add_time_hierarchy, release_lock_keys
from remarkable.config import get_config, project_root
from remarkable.converter.utils import generate_customer_answer
from remarkable.db import pw_db
from remarkable.models.cmf_china import CmfModelAuditAccuracy, CmfMoldModelRef
from remarkable.models.model_version import NewModelVersion
from remarkable.models.new_file import NewFile
from remarkable.pdfinsight.parser import parse_table
from remarkable.pdfinsight.reader import PdfinsightReader
from remarkable.plugins import Plugin
from remarkable.plugins.debug.docs import generate_spec, generate_template
from remarkable.plugins.ext_api.common import is_table_elt
from remarkable.pw_models.answer_data import NewAnswerData
from remarkable.pw_models.audit_rule import NewAuditResult, NewAuditRule
from remarkable.pw_models.law import LawCheckPoint
from remarkable.pw_models.law_judge import LawJudgeResult
from remarkable.pw_models.model import (
    NewAnswer,
    NewFileMeta,
    NewFileProject,
    NewFileTree,
    NewMold,
    NewRuleDoc,
    NewTrainingData,
)
from remarkable.pw_models.question import NewQuestion
from remarkable.routers.schemas.law import LawCheckPointSyncSchema
from remarkable.routers.schemas.law_judge import LawJudgeResultSyncSchema
from remarkable.service.deploy import (
    deploy_developer_model_version,
    deploy_predictor_model,
    deploy_prompter_model,
)
from remarkable.service.new_mold import NewMoldService
from remarkable.service.predictor import is_paragraph_elt
from remarkable.worker.tasks import (
    inspect_rule_task,
    preset_answer_by_fid_task,
    process_file,
)

plugin = Plugin(Path(__file__).parent.name)


@plugin.route(r"/file/(?P<file_id>\d+)/export/(?P<pdf_cache>\d+)")
class FileExportHandler(BaseHandler):
    query_args = {
        "key": fields.Str(required=True, validate=field_validate.Equal("u-never-know", error="Key error.")),
        "mold_id": fields.Int(data_key="mold", load_default=0),
        "contain_model_version": fields.Int(data_key="model_version", load_default=0),
    }

    @use_kwargs(query_args, location="query")
    async def get(self, file_id, pdf_cache, mold_id, key, contain_model_version):
        file_id = int(file_id)
        file: NewFile | None = await NewFile.find_by_id(file_id)
        if not file:
            return self.error("not found file", status_code=404)
        molds = []
        if file.task_type != TaskType.CLEAN_FILE.value:
            if mold_id:
                molds = await NewMold.get_related_molds(mold_id)
            else:
                molds = [await NewMold.get_by_id(m) for m in file.molds]

        # TODO: special answer改造
        # special_answers = await NewSpecialAnswer.get_answers(file.qid, NewSpecialAnswer.ANSWER_TYPE_EXPORT, top=1)
        questions = []
        answers = []
        model_versions = []
        training_datas = []
        cgs_rule = []
        cmf_model_audit_accuracy = []
        answer_data = []
        cgs_result = []
        for mold in molds:
            question = await NewQuestion.find_by_fid_mid(file.id, mold.id)
            if not question:
                continue
            questions.append(question)
            answers.extend(await NewAnswer.find_by_kwargs("all", qid=question.id))
            if contain_model_version:
                model_versions.extend(await NewModelVersion.find_by_kwargs("all", mold=mold.id))
            training_datas.extend(await NewTrainingData.find_by_kwargs("all", mold=mold.id))
            cgs_rule.extend(await NewAuditRule.find_by_kwargs(delegate="all", schema_id=mold.id))
            if cmf_model := await CmfMoldModelRef.get_enabled_model(mold.id):
                cmf_model_audit_accuracy.extend(
                    await CmfModelAuditAccuracy.find_by_kwargs(delegate="all", model_id=cmf_model.id)
                )

            answer_data.extend(await NewAnswerData.find_by_kwargs(delegate="all", qid=question.id))
            cgs_result.extend(await NewAuditResult.find_by_kwargs(delegate="all", qid=question.id))
        law_judge_result = await LawJudgeResult.find_by_kwargs(delegate="all", file_id=file.id)
        law_check_point_ids = {r.cp_id for r in law_judge_result if r.cp_id}
        if law_check_point_ids:
            law_check_point = await pw_db.execute(
                LawCheckPoint.select().where(LawCheckPoint.id.in_(law_check_point_ids))
            )
        else:
            law_check_point = []

        file_meta = await NewFileMeta.find_by_kwargs(file_id=file_id)
        docx_file = localstorage.read_file(file.docx_path()) if file.docx else None
        origin_file = localstorage.read_file(file.path()) if file.path else None
        pdf_file = localstorage.read_file(file.pdf_path()) if file.pdf else None
        pdfinsight_file = localstorage.read_file(file.pdfinsight_path()) if file.pdfinsight else None
        raw_pdf_file = localstorage.read_file(file.raw_pdf_path()) if file.raw_pdf_path() else None
        revise_docx = localstorage.read_file(file.revise_docx_path()) if file.revise_docx_path() else None

        cgs_rules = []
        for i in cgs_rule:
            data = i.to_dict()
            data.pop("rule_content")
            cgs_rules.append(data)

        meta = {
            # 'admin_user': [u.to_dict(True) for u in users],
            "file": file.to_dict(),
            "question": [q.to_dict() for q in questions],
            "mold": [m.to_dict() for m in molds],
            "model_version": [i.to_dict() for i in model_versions],
            "training_data": [i.to_dict() for i in training_datas],
            "answer": [i.to_dict() for i in answers],
            # 'special_answer': [i.to_dict(True) for i in special_answers],
            "tree": await self._get_file_trees(file),
            "project": (await NewFileProject.find_by_id(file.pid)).to_dict(),
            "file_meta": file_meta.to_dict() if file_meta else None,
            "extract_methods": (await NewMoldService.get_extract_methods(molds)),
            "rule_classes": (await NewMoldService.get_rule_classes(molds)),
            "rule_items": (await NewMoldService.get_rule_items(molds)),
            "rule_results": (await NewMoldService.get_rule_results(file.id)),
            "answer_data": [i.to_dict() for i in answer_data],
            "cgs_result": [i.to_dict() for i in cgs_result],
            "cgs_rule": cgs_rules,
            "law_judge_result": [LawJudgeResultSyncSchema.model_validate(i).model_dump() for i in law_judge_result],
            "law_check_point": [
                LawCheckPointSyncSchema.model_validate(i).model_dump(by_alias=True) for i in law_check_point
            ],
            "cmf_model_audit_accuracy": [i.to_dict() for i in cmf_model_audit_accuracy],
        }
        add_prefix = get_config("client.add_time_hierarchy", False)
        res = io.BytesIO()
        with ZipFile(res, "w") as res_fp:
            # 先写db到json
            res_fp.writestr("meta.json", json.dumps(meta).encode("utf-8"))
            # 再写文件
            if origin_file:
                arcname = add_time_hierarchy(file.created_utc, file.hash) if add_prefix else file.hash
                res_fp.writestr(arcname, origin_file)
            if docx_file:
                arcname = add_time_hierarchy(file.created_utc, file.docx) if add_prefix else file.docx
                res_fp.writestr(arcname, docx_file)
            if pdf_file:
                arcname = add_time_hierarchy(file.created_utc, file.pdf) if add_prefix else file.pdf
                res_fp.writestr(arcname, pdf_file)
            if pdfinsight_file:
                arcname = add_time_hierarchy(file.created_utc, file.pdfinsight) if add_prefix else file.pdfinsight
                res_fp.writestr(arcname, pdfinsight_file)
            if revise_docx:
                arcname = add_time_hierarchy(file.created_utc, file.revise_docx) if add_prefix else file.revise_docx
                res_fp.writestr(arcname, revise_docx)
            if raw_pdf_file:
                arcname = (
                    add_time_hierarchy(file.created_utc, file.meta_info.get("raw_pdf"))
                    if add_prefix
                    else file.meta_info.get("raw_pdf")
                )
                res_fp.writestr(arcname, raw_pdf_file)
            # 同步pdf_cache
            pdf_cache = int(pdf_cache)
            if pdf_cache:
                pdf_cache_path = file.pdf_cache_path()
                if pdf_cache_path:
                    for root, _, names in os.walk(localstorage.mount(pdf_cache_path)):
                        for _name in names:
                            pdf_cache_file = localstorage.read_file(os.path.join(root, _name))
                            res_fp.writestr(os.path.join(pdf_cache_path, _name), pdf_cache_file)

        return await self.export(res.getvalue(), f"{file.name}.zip")

    @staticmethod
    async def _get_file_trees(file):
        trees = []
        tree_id = file.tree_id
        tree = await NewFileTree.find_by_id(tree_id)
        if tree is None:
            return []
        trees.append(tree.to_dict())
        while tree.ptree_id:
            ptree = await NewFileTree.find_by_id(tree.ptree_id)
            trees.append(ptree.to_dict())
            tree = ptree

        return trees


@plugin.route(r"/rule/(?P<fid>\d+)/recheck")
class DebugRecheckHandler(BaseHandler):
    async def get(self, fid):
        """重跑指定fid的完备性审核任务"""
        fid = int(fid)
        key = self.get_query_argument("key")
        force = int(self.get_query_argument("force", "0"))
        if key != "u-never-known":
            return self.error("", status_code=403)
        doc = await NewRuleDoc.find_by_kwargs(fid=fid)
        if doc and (force or doc.status != AutoDocStatus.DOING.value):
            # 重跑没有在跑的任务
            preset_answer_by_fid_task.delay(doc.fid)
            await doc.update(status=AutoDocStatus.DOING.value)
            return self.data(doc.to_dict())

        return self.error("No related doclet id found", status_code=403)


@plugin.route(r"/(?:project|file)s/(\d+)/run")
class RunTaskHandler(BaseHandler):
    task_schema = {
        "task": fields.Str(required=True, validate=field_validate.OneOf(["preset", "inspect", "pdfinsight"]))
    }

    @Auth("browse")
    @use_kwargs(task_schema, location="query")
    async def get(self, *args, **kwargs):
        """重跑预测/合规任务"""
        if self.request.path.split(f"/{plugin.name}", maxsplit=1)[-1].startswith("/projects/"):
            files = await NewFile.find_by_kwargs(delegate="all", pid=int(args[0]))
        else:
            files = [NewFile(id=int(args[0]))]
        release_lock_keys()
        for file in files:
            if kwargs["task"] == "preset":
                preset_answer_by_fid_task.delay(file.id, force_predict=True)
            if kwargs["task"] == "inspect":
                inspect_rule_task.delay(file.id)
            if kwargs["task"] == "pdfinsight":
                file = await NewFile.find_by_id(file.id)
                await process_file(file, force_parse_file=True)
        return self.data("task queued!")


@plugin.route(r"/files/(\d+)/related_fids")
class RelatedFilesHandler(BaseHandler):
    @Auth("browse")
    async def get(self, fid):
        # 获取指定年报关联的文档id(包括年报文档本身)
        file_meta = await NewFileMeta.find_by_kwargs(file_id=int(fid))
        if not file_meta or file_meta.doc_type != "年报":
            return self.data([int(fid)])
        fids = []
        query = (
            NewFileMeta.select(NewFileMeta.file_id)
            .where(NewFileMeta.stock_code == file_meta.stock_code)
            .order_by(NewFileMeta.file_id)
        )
        data = await pw_db.execute(query)
        for item in data:
            fids.append(item.file_id)
        return self.data(fids)


@plugin.route(r"/tree/(?P<tree_id>\d+)/file_ids")
class TreeFilesHandler(BaseHandler):
    @Auth("browse")
    async def get(self, tree_id):
        """获取指定 tree_id 下所有文件 id"""
        return self.data(await NewFileTree.get_fids(int(tree_id)))


@plugin.route(r"/mold/(?P<mold_id>\d+)/files")
class MoldFilesHandler(BaseHandler):
    async def get(self, mold_id):
        """获取指定schema id下所有文件id"""
        mold_id = int(mold_id)
        key = self.get_argument("key")
        if key != "u-never-known":
            return self.error("", status_code=403)
        # start_time = self.get_query_argument('start_time', int(time.time() - 3600 * 24 * 7))
        questions = await NewQuestion.list_by_range(mold=mold_id, special_cols=["fid"])
        file_ids = [q.fid for q in questions]
        return self.data(file_ids)


@plugin.route(r"/questions/(?P<qid>\d+)/file")
class QuestionToFileHandler(BaseHandler):
    @Auth("browse")
    async def get(self, qid):
        question = await NewQuestion.find_by_id(qid)
        fid = question.fid if question else None
        return self.data({"fid": fid})


@route("/docs")
class DocsHandler(BaseHandler):
    @Auth("browse")
    async def get(self):
        return await self.export(generate_template(), content_type="text/html")


@route("/__docs/(?P<filename>.*)")
class DocsStaticHandler(BaseHandler):
    @Auth("browse")
    async def get(self, filename):
        if self.request.uri.endswith(".map"):
            return self.write("")

        if filename == "json":
            return self.send_json(generate_spec(route.HANDLERS.items()).to_dict())

        return await self.export(Path(project_root) / f"data/swagger/{filename}", content_type="")


@plugin.route(r"/gen-customer-answer")
class GenCustomerAnswer(BaseHandler):
    get_args = {
        "mid": fields.Int(required=True),
        "fid": fields.Int(required=True),
    }

    @Auth("browse")
    @use_kwargs(get_args, location="query")
    async def get(self, mid, fid):
        if not (question := await NewQuestion.find_by_fid_mid(fid, mid)):
            return self.error(message="文件不存在")
        await question.set_answer()
        await generate_customer_answer(question.id)
        return self.data(None)


@plugin.route("/molds/(?P<mold>.*)/deploy")
class DeployMoldHandler(BaseHandler):
    args = {
        "name": fields.Str(load_default=""),
        "ver_name": fields.Str(load_default=""),
    }

    @Auth("browse")
    @doc(tags=["debug"], summary="部署开发模型")
    @use_kwargs(args, location="query")
    async def get(self, mold: str, name, ver_name: str):
        molds = await NewMold.tolerate_schema_ids(mold)
        mold = await NewMold.get_by_id(molds[0])
        if not mold:
            return self.error("mold not found", status_code=404)
        name = name or (get_config("prophet.config_map") or {}).get(mold.name)
        if not name:
            return self.error("predictor package name is missing")

        vid = await deploy_developer_model_version(mold.id, ver_name, False, is_enabled=True)
        await deploy_predictor_model(mold.id, name, vid)
        await deploy_prompter_model(mold.id, name, vid)

        return self.data(f"成功部署schema:{mold.id} vid:{vid}的模型版本, 已启用")


@plugin.route(r"/files/(?P<fid>\d+)/elements/(?P<index>\d+)")
class ElementsInfoHandler(BaseHandler):
    @Auth("browse")
    async def get(self, fid, index):
        file = await NewFile.find_by_id(int(fid))
        if not file:
            return self.error("File not found", status_code=HTTPStatus.NOT_FOUND)
        pdfinsight_path = localstorage.mount(file.pdfinsight_path())
        if not os.path.exists(pdfinsight_path):
            return self.error("Pdfinsight not found", status_code=HTTPStatus.NOT_FOUND)
        reader = PdfinsightReader(pdfinsight_path)
        ele_type, element = reader.find_element_by_index(int(index))
        if not element:
            return self.error("Element not found", status_code=HTTPStatus.NOT_FOUND)
        if is_paragraph_elt(element):
            return self.data(element)
        if is_table_elt(element):
            parsed_table = parse_table(element, pdfinsight_reader=reader, tabletype=TableType.TUPLE.value)
            parsed_table_data = {
                "col_headers": [
                    {"rowidx": cell.rowidx, "colidx": cell.colidx, "text": cell.text}
                    for cell in parsed_table.header
                    if cell.is_col_header
                ],
                "row_headers": [
                    {"rowidx": cell.rowidx, "colidx": cell.colidx, "text": cell.text}
                    for cell in parsed_table.header
                    if cell.is_row_header
                ],
            }
            return self.data(parsed_table_data)
        return self.data("element type not supported")
