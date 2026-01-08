import collections
import hashlib
import json
import os
import shutil

from peewee import JOIN
from webargs import fields

from remarkable import config
from remarkable.base_handler import Auth, BaseHandler, DbQueryHandler, PermCheckHandler
from remarkable.common import field_validate
from remarkable.common.apispec_decorators import use_args, use_kwargs
from remarkable.common.constants import (
    AuditStatusEnum,
    AutoDocStatus,
    ComplianceStatus,
    ErrorStatus,
    PDFParseStatus,
)
from remarkable.common.exceptions import CustomError
from remarkable.common.storage import localstorage, tmp_storage
from remarkable.common.util import md5sum, subprocess_exec
from remarkable.db import db, peewee_transaction_wrapper, pw_db
from remarkable.models.new_file import NewFile
from remarkable.models.new_user import ADMIN, NewAdminUser
from remarkable.plugins.fileapi.common import clear_tmp_files
from remarkable.plugins.rule import plugin
from remarkable.pw_models.model import NewErrorContent, NewMold, NewRuleDoc, NewRuleResult
from remarkable.pw_models.question import NewQuestion
from remarkable.rule.inspector import AnswerInspectorFactory, Inspector, LegacyInspector
from remarkable.service.new_file import NewFileService
from remarkable.service.new_file_project import NewFileProjectService
from remarkable.service.rule import RuleService
from remarkable.worker.tasks import cache_pdf_file, inspect_rule_task, process_file

annotation_storage = tmp_storage.mount("annotation")


@plugin.route(r"/rule_results")
class RuleResultHandler(DbQueryHandler):
    @Auth("remark")
    @use_kwargs({"fid": fields.Int(required=True)}, location="query")
    async def get(self, fid):
        file = await NewFile.find_by_id(fid)
        if not file:
            raise CustomError(_("not found file"))
        inspector = None
        for mold_id in file.molds:
            mold = await NewMold.find_by_id(mold_id)
            if not mold:
                continue
            inspector = await AnswerInspectorFactory.create(mold)
            if inspector:
                break

        if isinstance(inspector, Inspector):
            # Rule
            rules_order = [rule.name for rule in inspector.rules if rule.name]
        elif isinstance(inspector, LegacyInspector):
            # LegacyRule
            rules_order = [rule.name for rule in inspector.rules.get(mold.name, []) if rule.name]
        else:
            rules_order = []
        rule_results = await pw_db.execute(
            NewRuleResult.select(NewRuleResult, NewErrorContent.content.alias("error_content"))
            .join(NewErrorContent, join_type=JOIN.LEFT_OUTER, on=(NewErrorContent.rule_result_id == NewRuleResult.id))
            .where(NewRuleResult.fid == file.id)
            .order_by(NewRuleResult.id)
            .dicts()
        )
        rule_res = collections.defaultdict(list)
        for rule_result in rule_results:
            rule_res[rule_result["rule"]].append(rule_result)
        ret = {
            "rule_res": rule_res,
            "rules_order": rules_order,
        }
        return self.data(ret)


@plugin.route(r"/rule_results/(\d+)")
class UpdateRuleResultHandler(BaseHandler):
    put_args = {
        "index": fields.Int(validate=field_validate.Range(0)),
        "audit_status": fields.Int(required=True, validate=field_validate.OneOf(AuditStatusEnum.member_values())),
    }

    @Auth("remark")
    @use_args(put_args, location="json")
    async def put(self, rule_result_id, param):
        rule_result_id = int(rule_result_id)
        index = param.pop("index", None)
        if not index:
            await NewRuleResult.update_by_pk(rule_result_id, audit_status=param["audit_status"])
        else:
            rule_result = await NewRuleResult.get_by_id(rule_result_id)
            if not rule_result:
                return self.error(f"Record: {rule_result} Not found")
            try:
                rule_result.detail["sub_cols"][index]["audit_status"] = param["audit_status"]
            except IndexError as exp:
                return self.error(f"{exp}")
            await rule_result.update_()
        return self.data("success")


@plugin.route(r"/rule_summary")
class RuleSummaryHandler(BaseHandler):
    @Auth("remark")
    @use_kwargs({"report_year": fields.Int(required=True)}, location="query")
    async def get(self, report_year):
        return self.data(await RuleService.gen_rule_summary(report_year))


@plugin.route(r"/audit_summary")
class AuditSummaryHandler(BaseHandler):
    @Auth("remark")
    @use_kwargs({"file_id": fields.Int(required=True, validate=field_validate.Range(0))}, location="query")
    async def get(self, file_id):
        return self.data(await RuleService.calc_audit_summary(file_id))


@plugin.route(r"/errors")
class ErrorHandler(DbQueryHandler):
    @Auth("remark")
    @peewee_transaction_wrapper
    async def post(self):
        form = self.get_json_body()
        fid = form.get("fid", None)
        content = form.get("content", None)
        rule_result_id = form.get("rule_result_id", None)
        params = {
            "uid": self.current_user.id,
            "fid": fid,
            "rule_result_id": rule_result_id,
            "content": content,
            "error_status": ErrorStatus.UNAMEND.value,
        }

        await NewErrorContent.create(**params)
        await NewRuleResult.update_by_pk(rule_result_id, audit_status=AuditStatusEnum.REFUSE.value)
        return self.data("success")

    @Auth("browse")
    async def get(self):
        fid = self.get_query_argument("fid", "")
        username = self.get_query_argument("username", "")

        search_condition = ""
        search_sql = """SELECT {}
                        FROM error_content err
                        JOIN file f ON err.fid = f.id
                        JOIN admin_user u ON err.uid = u.id"""
        if fid:
            search_condition = " WHERE err.fid=%(fid)s"
        elif username:
            user = await NewAdminUser.find_by_kwargs(name=username)
            if not user:
                return self.data({"page": 1, "size": 20, "total": 0, "items": []})
            search_condition = f" WHERE err.uid={user.id}"

        columns = [
            "err.id AS id",
            "f.name AS file_name",
            "err.fid AS fid",
            "err.content AS content",
            "to_char(to_timestamp(err.created_utc), 'YYYY/MM/DD HH24:MI:SS') AS error_date",
            "err.uid AS user_id",
            "u.name AS user_name",
            "err.error_status AS error_status",
        ]

        sql = search_sql + search_condition + " AND err.deleted_utc = 0;"
        pagedata = await self.pagedata_from_request(self, sql, columns, params={"fid": fid}, orderby="ORDER BY id DESC")
        return self.data(pagedata)


@plugin.route(r"/errors/(?P<error_id>\d+)")
class UpdateErrorStatusHandler(DbQueryHandler):
    @Auth("remark")
    @peewee_transaction_wrapper
    async def put(self, **kwargs):
        error_id = kwargs["error_id"]
        error_content = await NewErrorContent.find_by_id(error_id)
        if not error_content:
            return self.data("error content not exist")
        form = self.get_json_body()
        error_status = form.get("status", None)
        if error_status not in (0, 1):
            return self.data("status error")
        updates = {"error_status": error_status}
        await error_content.update(**updates)
        if error_status == ErrorStatus.AMEND.value:
            updates = {"audit_status": AuditStatusEnum.ACCEPT.value}
            await NewRuleResult.update_by_pk(error_content.rule_result_id, **updates)
        return self.data("success")


@plugin.route(r"/annotated_document")
class AnnotateDocumentHandler(DbQueryHandler):
    @Auth("remark")
    async def get(self):
        fid = self.get_query_argument("fid", "")
        _file = await NewFile.find_by_id(fid)
        file_hash = _file.hash
        file_path = _file.docx_path()
        if not file_path:
            raise CustomError(_("doc file is not ready"))
        tmp_dir = annotation_storage.mount(file_hash[:2])
        if not os.path.exists(tmp_dir):
            os.makedirs(tmp_dir)
        tmp_json_path = os.path.join(tmp_dir, os.path.splitext(_file.name)[0] + ".json")

        # dump json
        rule_results = await NewRuleResult.get_by_fid(fid)
        annotation_json = []
        for rule_result in rule_results:
            if (
                rule_result.result == ComplianceStatus.NONCOMPLIANCE.value
                and rule_result.audit_status == AuditStatusEnum.ACCEPT.value
            ):
                annotation = {"comment": rule_result.comment, "type": "error"}
                annotation.update(rule_result.comment_pos)
                annotation_json.append(annotation)
        with open(tmp_json_path, "w") as tmp:
            json.dump(annotation_json, tmp)

        tmp_docx_path = os.path.join(tmp_dir, _file.name)
        shutil.copy(localstorage.mount(file_path), tmp_docx_path)

        word_insight_dll = config.get_config("web.revision_tools")
        try:
            subprocess_exec("%s -d %s --json %s" % (word_insight_dll, tmp_docx_path, tmp_json_path))
        except Exception as e:
            return self.data("add annotation failed, error_info {}".format(str(e)))
        annotation_path = md5sum(tmp_docx_path)
        # copy tmp to data/files
        annotation_dir = localstorage.mount(annotation_path[:2])
        if not os.path.exists(annotation_dir):
            os.makedirs(annotation_dir)
        new_docx_path = os.path.join(annotation_dir, annotation_path[2:])
        shutil.copy(tmp_docx_path, new_docx_path)
        # update annotation_path to file
        updates = {"annotation_path": annotation_path}
        await _file.update_(**updates)
        # clean tmp file
        clear_tmp_files(tmp_docx_path, tmp_json_path)
        return self.data("success")


@plugin.route(r"/file/(\d+)/annotated")
class FileHandler(PermCheckHandler):
    @Auth("browse")
    async def get(self, *args):
        """批注文件下载"""

        (fid,) = args
        file = await NewFile.find_by_id(fid)
        if not file or not file.annotation_path:
            raise CustomError(_("not found file"))

        await self.check_file_permission(fid, file=file)

        return await self.export(localstorage.mount(file.annotation_pdf_path()), file.name)


@plugin.route(r"/export_error")
class ExportErrorHandler(PermCheckHandler):
    args_schema = {
        "s_time": fields.String(required=True),
        "e_time": fields.String(required=True),
    }

    @Auth("browse")
    @use_kwargs(args_schema, location="query")
    @peewee_transaction_wrapper
    async def get(self, s_time, e_time):
        """导出报错信息"""
        time_cond = """
            and to_char(TO_TIMESTAMP(f.created_utc), 'YYYY-MM-DD')>='%s '
            and to_char(TO_TIMESTAMP(f.created_utc), 'YYYY-MM-DD')<='%s '
        """ % (
            s_time,
            e_time,
        )

        _sql = f"""
                SELECT err.id AS id, f.name AS file_name, err.fid AS fid, err.content AS content,
                   to_char(to_timestamp(err.created_utc) AT TIME ZONE 'PRC', 'YYYY/MM/DD HH24:MI:SS') AS error_date,
                   err.uid AS user_id, u.name AS user_name, err.error_status AS error_status
                FROM error_content err
                JOIN file f ON err.fid = f.id
                JOIN admin_user u ON err.uid = u.id
                WHERE err.deleted_utc = 0
                AND f.deleted_utc = 0
                {time_cond}
                ORDER BY id DESC"""

        data = await db.raw_sql(_sql)
        data = json.dumps([dict(item) for item in data]).encode()
        return await self.export(data, "报错信息.json")


@plugin.route(r"/file/(?P<fid>\d+)/recheck")
class ReCheckHandler(PermCheckHandler):
    @Auth("browse")
    async def put(self, **kwargs):
        """规则的重新审核"""
        fid = kwargs["fid"]
        answer = self.get_json_body()
        _file = await NewFile.find_by_id(fid)
        if not _file:
            raise CustomError(_("not found file"))
        for item in answer["userAnswer"]["items"]:
            item["key"] = json.dumps(json.loads(item["key"]))
        await NewQuestion.update_by_pk(_file.qid, preset_answer=json.dumps(answer))  # 接口已废弃,用时再调整
        await RuleService.inspect_rules(_file)
        return self.data({})


@plugin.route(r"/doc")
class ReceiveDocHandler(PermCheckHandler):
    @Auth("browse")
    async def post(self):
        doc_id = self.get_argument("doc_id")
        doclet_id = self.get_argument("doclet_id")
        mold_id = self.get_argument("mold_id")
        callback = self.get_argument("callback")
        mold_type = self.get_argument("mold_type", None)
        mold_dict = {
            "ipo": 1,  # 科创
            "zjs": 4,  # 中信建投
        }
        # 有传schema类别则用对应的id, 没有就继续用传过来的mold_id
        # TODO: schema类别id对应关系写到配置文件里
        mold_id = mold_dict[mold_type] if mold_type in mold_dict else mold_id

        doc_meta = self.request.files["pdf_file"][0]
        doc_name = self.get_argument("filename", doc_meta["filename"])
        doc_raw = doc_meta["body"]

        inter_meta = self.request.files.get("interdoc_file", [None])[0]
        mold = await NewMold.find_by_id(mold_id)

        # 1. 按schema名新建项目(同类文档会被归到同一项目/文件夹下)
        project = await NewFileProjectService.create(mold.name)
        # 2. 创建文档记录/保存上传文件/出题
        _file = await self._create_file(doc_name, doc_raw, inter_meta, mold_id, project, doclet_id, callback)
        # 3. 保留doclet记录
        record = await self._create_record(_file.id, doc_id, doclet_id, callback)
        # 4. 预测
        if record.status != AutoDocStatus.DOING.value:
            if inter_meta:
                # 第二次推送会带interdoc内容,首次推送不会带interdoc内容
                await record.update(status=AutoDocStatus.DOING.value)
            await process_file(_file)

        return self.data(record.to_dict())

    async def _create_file(self, doc_name, doc_raw, inter_meta, mold, project, doclet_id, callback):
        record = await NewRuleDoc.find_by_kwargs(doclet_id=doclet_id, callback=callback)
        if record:
            _file = await NewFile.find_by_id(record.fid)
            if _file:
                if inter_meta:
                    await self._update_pdfinsight(inter_meta, _file.id)
                    cache_pdf_file.delay(_file.id)
                return _file
            await record.delete()  # 删除孤立记录

        _file = await NewFileService.create_file(
            **{
                "name": doc_name,
                "body": doc_raw,
                "molds": [mold],
                "pid": project.id,
                "tree_id": project.rtree_id,
                "uid": ADMIN.id,
            },
        )
        if inter_meta:
            await self._update_pdfinsight(inter_meta, _file.id)
            cache_pdf_file.delay(_file.id)
        return _file

    async def _update_pdfinsight(self, inter_meta, file_id):
        inter_raw = inter_meta["body"]
        pdfinsight = hashlib.md5(inter_raw).hexdigest()
        await NewFile.update_by_pk(file_id, pdfinsight=pdfinsight, pdf_parse_status=PDFParseStatus.CACHING)
        localstorage.write_file(os.path.join(pdfinsight[:2], pdfinsight[2:]), inter_raw)

    async def _create_record(self, fid, doc_id, doclet_id, callback):
        record = await NewRuleDoc.find_by_kwargs(fid=fid, doclet_id=doclet_id, callback=callback)
        if not record:
            record = await NewRuleDoc.create(
                **{
                    "fid": fid,
                    "aid": doc_id,
                    "doclet_id": doclet_id,
                    "callback": callback,
                    "status": AutoDocStatus.CREATED.value,
                },
            )
        return record


@plugin.route(r"/doc/(?P<doclet_id>\d+)")
class RuleDocHandler(PermCheckHandler):
    @Auth("browse")
    async def get(self, **kwargs):
        doclet_id = kwargs.get("doclet_id")
        doc = await NewRuleDoc.find_by_kwargs(doclet_id=doclet_id, status=AutoDocStatus.DONE.value)
        if not doc:
            return self.error(_("Nothing found"))
        ret = await NewRuleResult.find_by_kwargs("all", fid=doc.fid)
        if not ret:
            return self.error(_("Nothing found"))
        file = await NewFile.find_by_id(doc.fid)
        if not file:
            return self.error(_("Nothing found"))
        if not file.molds or len(file.molds) > 1:
            return self.error(_("Multi mold error"))
        schema = await NewMold.find_by_id(file.molds[0])
        if not schema:
            return self.error(_("Nothing found"))
        return self.data({"schema": schema.data, "records": ret})


@plugin.route(r"/doc/(?P<fid>\d+)/recheck")
class RecheckDocHandler(PermCheckHandler):
    @Auth("remark")
    async def post(self, **kwargs):
        """重新进行规则审核"""
        fid = int(kwargs.get("fid"))
        doc = await NewRuleDoc.find_by_kwargs(fid=fid)
        if not doc:
            return self.error(_("No doclet found"))
        if doc.status != AutoDocStatus.DOING.value:
            inspect_rule_task.delay(doc.fid)
            await doc.update(status=AutoDocStatus.DOING.value)
            return self.data(doc.to_dict())
        return self.error(_("Task is running."))
