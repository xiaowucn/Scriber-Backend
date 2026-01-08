import http
import logging
import os

import speedy.peewee_plus.orm
from marshmallow import fields
from marshmallow.validate import OneOf
from peewee import JOIN, fn
from speedy.peewee_plus import orm

from remarkable.base_handler import Auth
from remarkable.checker.cgs_checker import CGSAnswerManager
from remarkable.checker.cgs_checker.checker import get_updated_rule_labels
from remarkable.checker.helpers import audit_file_rules
from remarkable.common import field_validate
from remarkable.common.apispec_decorators import doc, use_kwargs
from remarkable.common.constants import FAKE_DATA, HistoryAction, RuleReviewStatus, TagType
from remarkable.common.enums import NafmiiEventStatus, NafmiiEventType, TaskType
from remarkable.common.exceptions import CustomError, ItemNotFound
from remarkable.common.schema import Schema
from remarkable.config import get_config
from remarkable.db import pw_db
from remarkable.models.new_file import NewFile
from remarkable.models.new_user import NewAdminUser
from remarkable.models.query_helper import AsyncPagination
from remarkable.plugins.cgs import CGSHandler, plugin
from remarkable.plugins.cgs.common.utils import get_review_fields
from remarkable.plugins.cgs.rules.rules import ConditionRule, ExprRule
from remarkable.plugins.cgs.services.comment import edit_answer_data, export_result_comment
from remarkable.plugins.cgs.services.export_word import export_docx
from remarkable.plugins.inspector import plugin as inspector_plugin
from remarkable.pw_db_services import PeeweeService
from remarkable.pw_models.audit_rule import NewAuditResult, NewAuditRule
from remarkable.pw_models.law import LawScenario
from remarkable.pw_models.law_judge import LawJudgeResult
from remarkable.pw_models.model import (
    NewAuditDevRule,
    NewAuditResultRecord,
    NewChinaStockAnswer,
    NewFileProject,
    NewFileTree,
    NewHistory,
    NewMold,
    NewTag,
    NewTagRelation,
)
from remarkable.pw_models.question import NewQuestion
from remarkable.pw_orm import func
from remarkable.schema.cgs.rules import (
    RuleSchema,
    RulesSchema,
    RuleStatusSchema,
    mapping_schema,
    pagination_schema,
    rules_schema,
)
from remarkable.service.answer import SimpleQuestion, get_master_question_answer
from remarkable.service.file_list_status import fill_files_status
from remarkable.service.new_file_project import NewFileProjectService
from remarkable.service.new_file_tree import get_crumbs

logger = logging.getLogger(__name__)


@inspector_plugin.route(r"/rules")
@plugin.route(r"/rules")
class RulesHandler(CGSHandler):
    @Auth("customer_rule_participate")
    @use_kwargs(RulesSchema, location="query")
    async def get(self, page, size, mold_id, name, rule_type, review_status):
        cond = NewAuditRule.deleted_utc == 0
        if name:
            cond &= NewAuditRule.name.contains(name)
        if rule_type:
            cond &= NewAuditRule.rule_type == rule_type
        if mold_id:
            cond &= NewAuditRule.schema_id == mold_id
        if review_status:
            cond &= NewAuditRule.review_status == review_status
        if not self.current_user.is_admin:
            cond &= NewAuditRule.public | (NewAuditRule.uid == self.current_user.id)
        query = NewAuditRule.select().where(cond).order_by(NewAuditRule.id.desc())
        data = await AsyncPagination(query, page=page, size=size).data()

        return self.data(data)

    @Auth("customer_rule_participate")
    @use_kwargs(rules_schema, location="json")
    async def post(self, rules):
        public = get_config("feature.default_audit_rule_public")
        res = []
        async with pw_db.atomic():
            for rule_item in rules:
                rule_item["uid"] = self.current_user.id
                rule_item["user"] = self.current_user.name
                rule_item["handle_uid"] = self.current_user.id
                rule_item["handle_user"] = self.current_user.name
                rule_item["public"] = public
                rule = await pw_db.create(NewAuditRule, **rule_item)
                res.append(rule)
        return self.data([item.to_dict() for item in res])


@inspector_plugin.route(r"/rules/(\d+)")
@plugin.route(r"/rules/(\d+)")
class RuleHandler(CGSHandler):
    @Auth("customer_rule_participate")
    async def get(self, rule_id):
        rule = await NewAuditRule.get_by_id_and_user(int(rule_id), self.current_user.is_admin, self.current_user.id)
        if not rule:
            return self.error("未找到对应规则", status_code=404)
        return self.data(rule.to_dict())

    @Auth("customer_rule_participate")
    async def delete(self, rule_id):
        rule = await NewAuditRule.get_by_id_and_user(int(rule_id), self.current_user.is_admin, self.current_user.id)
        if not rule:
            return self.error("未找到对应规则", status_code=404)
        await rule.soft_delete()
        return self.data(rule.to_dict())

    @Auth("customer_rule_participate")
    @use_kwargs(RuleSchema, location="json")
    async def post(self, rule_id, **kwargs):
        rule = await NewAuditRule.get_by_id_and_user(int(rule_id), self.current_user.is_admin, self.current_user.id)
        if not rule:
            return self.error("未找到对应规则", status_code=404)

        kwargs["review_status"] = RuleReviewStatus.NOT_REVIEWED
        kwargs["handle_uid"] = self.current_user.id
        kwargs["handle_user"] = self.current_user.name

        await rule.update_rule(**kwargs)

        return self.data(rule.to_dict())

    @Auth("customer_rule_participate")
    @use_kwargs(RuleStatusSchema, location="json")
    async def put(self, rule_id, **kwargs):
        rule = await NewAuditRule.get_by_id_and_user(int(rule_id), self.current_user.is_admin, self.current_user.id)
        if not rule:
            return self.error("未找到对应规则", status_code=404)
        if rule.review_status == kwargs["review_status"]:
            return self.data(rule.to_dict())

        kwargs["handle_uid"] = self.current_user.id
        kwargs["handle_user"] = self.current_user.name
        if not rule.is_valid:
            return self.error("不合法的规则，请检查后再试")
        await rule.update_(**kwargs)
        return self.data(rule.to_dict())


@plugin.route(r"/dev-rules")
class DevRulesHandler(CGSHandler):
    @Auth("developed_rule_browse")
    @use_kwargs(pagination_schema, location="query")
    async def get(self, page, size, field, keyword):
        cond = speedy.peewee_plus.orm.TRUE

        if keyword:
            if field == "name":
                cond &= NewAuditDevRule.name.contains(keyword)
            elif field == "rule_type":
                cond &= NewAuditDevRule.rule_type.contains(keyword)

        query = NewAuditDevRule.select().where(cond).order_by(NewAuditDevRule.id)
        data = await AsyncPagination(query, page=page, size=size).data()

        return self.data(data)


@inspector_plugin.route(r"/rules/(\d+)/review")
@plugin.route(r"/rules/(\d+)/review")
class RuleReviewHandler(CGSHandler):
    args = {
        "review_status": fields.Int(validate=OneOf(RuleReviewStatus.member_values())),
        "not_pass_reason": fields.Str(load_default=None),
    }

    @Auth("customer_rule_review")
    @doc(summary="审核规则复核", description="review_status: 待复核[1],复核不通过[2],复核通过[3]", tags=["cgs"])
    @use_kwargs(args, location="json")
    async def put(self, rule_id, review_status, not_pass_reason):
        rule = await NewAuditRule.find_by_id(rule_id)
        if not rule:
            return self.error("未找到对应规则", status_code=404)
        if rule.handle_uid == self.current_user.id:
            return self.error("规则不能由经办人复核", status_code=400)
        if rule.review_status != RuleReviewStatus.NOT_REVIEWED:
            return self.error("当前已是最终态,无法复核", status_code=400)

        review_uids = rule.review_uids
        if self.current_user.id not in review_uids:
            review_uids.append(self.current_user.id)
        review_users = rule.review_users
        if self.current_user.name not in review_users:
            rule.review_users.append(self.current_user.name)

        params = {
            "review_status": review_status,
            "not_pass_reason": not_pass_reason,
            "review_uids": review_uids,
            "review_users": review_users,
        }
        await rule.update_(**params)
        return self.data(rule.to_dict())


@inspector_plugin.route(r"/expr-operators")
@plugin.route(r"/expr-operators")
class ExprOperationHandler(CGSHandler):
    @Auth("customer_rule_participate")
    async def get(self):
        return self.data(ExprRule.operators())


@inspector_plugin.route(r"/condition-operators")
@plugin.route(r"/condition-operators")
class ConditionOperationHandler(CGSHandler):
    @Auth("customer_rule_participate")
    async def get(self):
        return self.data(ConditionRule.operators())


@inspector_plugin.route(r"/schemas/(\d+)/schema-items")
@plugin.route(r"/schemas/(\d+)/schema-items")
class SchemaItemsHandler(CGSHandler):
    @Auth("customer_rule_participate")
    async def get(self, schema_id):
        schemas = await NewMold.get_related_molds(int(schema_id))
        if not schemas:
            return self.error("错误，模型不存在", status_code=404)

        mapping = {}
        for schema in schemas:
            for schema_path, detail in Schema(schema.data).iter_schema_attr(True):
                mapping["-".join(schema_path[1:])] = detail
        return self.data(mapping)


@inspector_plugin.route(r"/files/(\d+)/schemas/(\d+)/results")
@plugin.route(r"/files/(\d+)/schemas/(\d+)/results")
class ResultHandler(CGSHandler):
    @Auth("inspect")
    async def get(self, fid, schema_id):
        results = await NewAuditResult.get_results(fid, [schema_id], self.current_user.is_admin, self.current_user.id)
        return self.data([item.to_dict() for item in results])

    @Auth("inspect")
    @use_kwargs({"results": fields.List(fields.Dict())}, location="json")
    async def put(self, fid, schema_id, results):
        if not results:
            return self.error("审核结果未做任何修改，已保存答案")
        await NewAuditResult.batch_update_user_result(results, self.current_user)
        return self.data({})


@inspector_plugin.route(r"/rules/(\d+)/validate")
@plugin.route(r"/rules/(\d+)/validate")
class RuleValidateHandler(CGSHandler):
    @Auth("browse")
    @use_kwargs(mapping_schema, location="json")
    async def post(self, rule_id, mapping):
        rule = await NewAuditRule.find_by_id(int(rule_id))
        if not rule:
            return self.error("未找到对应规则", status_code=404)

        return self.data(rule.validate(CGSAnswerManager(mapping)))


@plugin.route(r"/files/(\d+)/schemas/(\d+)/export-comment")
class ExportCommentHandler(CGSHandler):
    args = {"export_type": fields.Str(validate=OneOf(["docx", "pdf"]), load_default="pdf")}

    @Auth("browse")
    @use_kwargs(args, location="query")
    async def get(self, fid, schema_id, export_type):
        try:
            path = await export_result_comment(
                export_type, fid, schema_id, self.current_user.is_admin, self.current_user.id
            )
        except ItemNotFound:
            return self.error(_("Item not found"), status_code=http.HTTPStatus.NOT_FOUND)

        if not path:
            return self.error(_("data not ready"), status_code=http.HTTPStatus.BAD_REQUEST)
        return await self.export(path)


@inspector_plugin.route(r"/files/(\d+)/schemas/(\d+)/export-result")
@plugin.route(r"/files/(\d+)/schemas/(\d+)/export-result")
class ExportResultHandler(CGSHandler):
    @Auth("browse")
    async def get(self, file_id, schema_id):
        file = await NewFile.find_by_id(file_id)
        name = os.path.splitext(file.name)[0]
        head_results = []
        results = await NewAuditResult.get_results(
            file_id, [schema_id], self.current_user.is_admin, self.current_user.id, only_incompliance=True
        )
        if results:
            head_results.append(("规则审核", results))
        law_results = await LawJudgeResult.get_judge_results(file_id)
        if law_results:
            head_results.append(("大模型审核", law_results))
        return await self.export(export_docx(head_results).read(), file_name=f"{name}-修改意见.docx")


@plugin.route(r"/project/(?P<project_id>\d+)/file")
class ChinaStockFileListHandler(CGSHandler):
    args = {
        "mold_id": fields.Int(load_default=-1),
        "answered": fields.Bool(load_default=0),
        "status": fields.Int(load_default=None),
        "product_name": fields.Str(load_default=None),
        "manager_name": fields.Str(load_default=None),
        "fileid": fields.Int(load_default=0),
        "filename": fields.Str(load_default=""),
        "username": fields.Str(load_default=""),
        "sysfrom": fields.Str(load_default="", validate=field_validate.OneOf(["local", "PIF", "OAS", "FMP"])),
        "source": fields.Str(load_default="", validate=field_validate.OneOf(["Glazer"])),
    }

    @Auth("browse")
    @doc(tags=["cgs"])
    @use_kwargs(AsyncPagination.web_args, location="query")
    @use_kwargs(args, location="query")
    async def get(
        self,
        project_id,
        mold_id,
        answered,
        status,
        product_name,
        manager_name,
        fileid,
        filename,
        username,
        sysfrom,
        source,
        page,
        size,
    ):
        project_id = -1 if project_id == "0" else project_id
        if project_id != -1:
            await self.check_project_permission(project_id)

        file_tag_cte = (
            NewTagRelation.select(
                NewTagRelation.relational_id.alias("file_id"),
                func.ARRAY_AGG(NewTag.id).alias("tags"),
            )
            .join(NewTag, on=(NewTagRelation.tag_id == NewTag.id))
            .where(NewTag.tag_type == TagType.FILE.value)
            .group_by(NewTagRelation.relational_id)
            .cte("file_tag")
        )

        user = self.current_user
        if username:
            user = await NewAdminUser.find_by_kwargs(name=username)
            if not user:
                return self.data({"page": 1, "size": 20, "total": 0, "items": []})
            answered = True

        origin_query = q_subquery = NewQuestion.select().where(NewQuestion.fid == NewFile.id)
        question_filter = orm.TRUE
        if answered:
            question_filter = NewQuestion.mark_uids.contains([user.id])
            q_subquery = q_subquery.where(question_filter)
        question_cte = PeeweeService.create().questions.group_by_fid(question_filter)
        query = (
            NewFile.select(
                NewFile,
                NewAdminUser.name.alias("user_name"),
                fn.COALESCE(question_cte.c.questions, func.build_array()).alias("questions"),
                fn.COALESCE(file_tag_cte.c.tags, func.build_array()).alias("tags"),
                NewChinaStockAnswer.id.alias("china_stock_id"),
                NewChinaStockAnswer.product_name,
                NewChinaStockAnswer.manager_name,
            )
            .join(NewAdminUser, JOIN.LEFT_OUTER, on=(NewFile.uid == NewAdminUser.id), include_deleted=True)
            .join(NewFileProject, JOIN.LEFT_OUTER, on=(NewFile.pid == NewFileProject.id))
            .join(NewChinaStockAnswer, JOIN.LEFT_OUTER, on=(NewFile.id == NewChinaStockAnswer.fid))
            .join(file_tag_cte, JOIN.LEFT_OUTER, on=(NewFile.id == file_tag_cte.c.file_id))
            .join(question_cte, JOIN.LEFT_OUTER, on=(NewFile.id == question_cte.c.fid))
        ).where(NewFile.name.contains(filename))

        if project_id != -1:
            query = query.where(NewFile.pid == project_id)
        else:
            query = query.where(NewFileProject.visible)
        if product_name:
            query = query.where(NewChinaStockAnswer.product_name.contains(product_name))
        if manager_name:
            query = query.where(NewChinaStockAnswer.manager_name.contains(manager_name))
        if sysfrom:
            if sysfrom == "local":  # 本地上传
                query = query.where(NewFile.sysfrom.is_null())
            else:
                query = query.where(NewFile.sysfrom == sysfrom)
        if source:
            query = query.where(NewFile.source == source)
        if fileid:
            query = query.where(NewFile.id == fileid)

        if len([x for x in (filename, fileid, username) if x]) > 1:
            raise CustomError(_("The input search criteria is invalid"))

        if status is not None:
            q_subquery = q_subquery.where(NewQuestion.status == status)
        if mold_id != -1:
            q_subquery = q_subquery.where(NewQuestion.mold == mold_id)
        if origin_query is not q_subquery:
            query = query.where(fn.EXISTS(q_subquery))
        data = await AsyncPagination(
            query.order_by(NewFile.id.desc()).dicts().with_cte(file_tag_cte, question_cte), page, size
        ).data()
        await fill_files_status(data["items"])
        return self.data(data)


@plugin.route(r"/tree/(\d+)")
class ChinaStockTreeHandler(CGSHandler):
    args = {
        "sysfrom": fields.Str(load_default="", validate=field_validate.OneOf(["local", "PIF", "OAS", "FMP"])),
        "source": fields.Str(load_default="", validate=field_validate.OneOf(["Glazer"])),
    }

    @Auth("browse")
    @use_kwargs(AsyncPagination.web_args, location="query")
    @use_kwargs(args, location="query")
    async def get(self, tid, sysfrom, source, page, size):
        tree = await NewFileTree.find_by_id(tid)
        if not tree:
            return self.error(_("not found tree"))
        await self.check_tree_permission(tid, tree=tree)

        res = tree.to_dict()

        trees = await NewFileTree.list_by_tree(tree.id)
        start = (page - 1) * size
        end = page * size
        res["trees"] = trees[start:end]

        question_cte = PeeweeService.create().questions.group_by_fid()
        query = (
            NewFile.select(
                NewFile,
                NewAdminUser.name.alias("user_name"),
                fn.COALESCE(question_cte.c.questions, func.build_array()).alias("questions"),
                NewChinaStockAnswer.id.alias("china_stock_id"),
                NewChinaStockAnswer.product_name,
                NewChinaStockAnswer.manager_name,
                LawScenario.name.alias("scenario_name"),
            )
            .join(NewAdminUser, JOIN.LEFT_OUTER, on=(NewFile.uid == NewAdminUser.id), include_deleted=True)
            .join(LawScenario, JOIN.LEFT_OUTER, on=(LawScenario.id == NewFile.scenario_id), include_deleted=True)
            .join(NewChinaStockAnswer, JOIN.LEFT_OUTER, on=(NewFile.id == NewChinaStockAnswer.fid))
            .join(question_cte, JOIN.LEFT_OUTER, on=(NewFile.id == question_cte.c.fid))
        ).where(NewFile.tree_id == tid)

        if sysfrom:
            if sysfrom == "local":  # 本地上传
                query = query.where(NewFile.sysfrom.is_null())
            else:
                query = query.where(NewFile.sysfrom == sysfrom)

        if source:
            query = query.where(NewFile.source == source)

        query = query.with_cte(question_cte).order_by(NewFile.id.desc())
        file_count = await pw_db.count(query)

        if len(res["trees"]) < size:
            offset = max((page - 1) * size - len(trees), 0)
            query = query.limit(size - len(res["trees"])).offset(offset)
            res["files"] = list(await pw_db.execute(query.order_by(NewFile.id.desc()).dicts()))
            await fill_files_status(res["files"])
        else:
            res["files"] = []
        res["page"] = page
        res["total"] = file_count + len(trees)
        res["crumbs"] = await get_crumbs(tree.id)

        project = await NewFileProject.find_by_id(res["pid"])
        res["project_public"] = project.public

        return self.data(res)


@plugin.route(r"/result/(?P<result_id>\d+)/records")
class CgsResultRecordsHandler(CGSHandler):
    @Auth("browse")
    @doc(tags=["cgs"])
    async def get(self, result_id):
        data = await NewAuditResultRecord.find_by_kwargs(result_id=result_id, delegate="all")
        return self.data([x.to_dict() for x in data])


@inspector_plugin.route(r"/files/(\d+)/answer_data")
@plugin.route(r"/files/(\d+)/answer_data")
class CgsAnswerDataHandler(CGSHandler):
    post_args = {
        "add": fields.List(
            fields.Dict(validate=lambda x: set(x.keys()) == {"key", "data", "value", "schema", "revise_suggestion"})
        ),
        "update": fields.List(
            fields.Dict(validate=lambda x: set(x.keys()) == {"id", "key", "data", "value", "revise_suggestion"})
        ),
        "delete": fields.List(fields.Dict(validate=lambda x: set(x.keys()) == {"id", "key"})),
    }

    @Auth("inspect")
    @doc(tags=["cgs"])
    async def get(self, fid):
        fid = int(fid)
        question = await NewQuestion.get_master_question(fid, NewQuestion.id, NewQuestion.mold, NewQuestion.fid)
        if not question:
            return self.error(f"can't find master_question for {fid}")
        answer, master_mold = await get_master_question_answer(question)
        return self.data(
            {
                "answer_data": answer["userAnswer"]["items"],
                "mold": master_mold.to_dict(),
            }
        )

    @Auth("inspect")
    @use_kwargs(post_args, location="json")
    @doc(tags=["cgs"])
    async def post(self, fid, add, update, delete):
        fid = int(fid)
        file = await NewFile.find_by_id(fid)
        question: SimpleQuestion = await NewQuestion.get_master_question(
            fid, NewQuestion.id, NewQuestion.mold, NewQuestion.fid
        )
        if not question:
            return self.error(f"can't find question for {fid}")
        async with pw_db.atomic():
            data = await edit_answer_data(question.id, add, update, delete, self.current_user.id)
            await self.update_inspector_results(file, question, [delete, add, update])

        if get_config("client.name") == "nafmii":
            await NewHistory.save_operation_history(
                None,
                action=HistoryAction.NAFMII_DEFAULT,
                user_name=self.current_user.name,
                meta=None,
                uid=self.current_user.id,
                nafmii=self.get_nafmii_event(
                    status=NafmiiEventStatus.SUCCEED.value,
                    type=NafmiiEventType.MODIFY.value,
                    menu=self.record_menu,
                    subject="要素答案",
                    content=f"修改{fid}要素答案成功",
                ),
            )

        return self.data(data)

    @classmethod
    async def update_inspector_results(cls, _file, question: SimpleQuestion, updated):
        updated_key = [x["key"] for item in updated for x in item]
        if _file.task_type == TaskType.AUDIT.value:
            labels = await get_updated_rule_labels(_file.id, question.mold, updated_key)
            if labels:
                await audit_file_rules(fid=question.fid, labels=labels)


@plugin.route(r"/projects/(\d+)/trash")
class CgsAbandonedFileHandler(CGSHandler):
    args = {
        "file_id": fields.Int(load_default=None),
        "tree_id": fields.Int(load_default=None),
        "abandon": fields.Bool(load_default=False),
        "restore": fields.Bool(load_default=False),
    }

    @Auth("browse")
    @doc(tags=["cgs"])
    async def get(self, pid):
        project = await NewFileProject.find_by_id(pid)
        if not project:
            return self.error(_("not found project"))
        await self.check_project_permission(pid, project=project)
        project_trash = await NewFileProjectService.get_project_trash(project)
        return self.data(project_trash.to_dict(only=[NewFileProject.id, NewFileProject.rtree_id]))

    @Auth("browse")
    @use_kwargs(args, location="json")
    @doc(tags=["cgs"])
    async def put(self, pid, file_id, tree_id, abandon, restore):
        pid = int(pid)
        project = await NewFileProject.find_by_id(pid)
        if not project:
            return self.error(_("not found project"))
        await self.check_project_permission(pid, project=project)
        project_trash = await NewFileProjectService.get_project_trash(project)

        update_params = {}
        if abandon:
            update_params["pid"] = project_trash.id
        elif restore:
            update_params["pid"] = project.id
        else:
            return self.error(_("Invalid input parameters."))

        if file_id:
            file = await NewFile.find_by_id(file_id)
            if not file:
                return self.error(_("not found file"))
            await self.check_file_permission(file_id, file=file, mode="write")
            if abandon:
                update_params["tree_id"] = project_trash.rtree_id
                update_params["origin_tree_id"] = file.tree_id
            else:
                origin_tree = await NewFileTree.find_by_id(file.origin_tree_id)
                if not origin_tree or origin_tree.pid != pid:
                    return self.error(f"无法恢复，文件夹{origin_tree.name}不存在")
                update_params["tree_id"] = file.origin_tree_id
            await file.update_(**update_params)

        if tree_id:
            tree = await NewFileTree.find_by_id(tree_id)
            if not tree:
                return self.error(_("not found tree"))
            await self.check_tree_permission(tree_id, tree=tree)
            if abandon:
                update_params["ptree_id"] = project_trash.rtree_id
                update_params["origin_ptree_id"] = tree.ptree_id
            else:
                origin_tree = await NewFileTree.find_by_id(tree.origin_ptree_id)
                if not origin_tree or origin_tree.pid != pid:
                    return self.error(f"无法恢复，文件夹{origin_tree.name}不存在")
                update_params["ptree_id"] = tree.origin_ptree_id

            await tree.update_(**update_params)

        return self.data({})


@plugin.route(r"/files/(\d+)/review_fields")
class CgsReviewFieldsHandler(CGSHandler):
    @Auth("browse")
    @doc(tags=["cgs"])
    async def get(self, fid):
        file = await NewFile.find_by_id(fid)
        if not file:
            return self.error(_("not found file"))
        glazer_id = (file.meta_info or {}).get("glazer_project_id")
        if not glazer_id:
            return self.error("review_fields_url not found")
        try:
            review_fields = await get_review_fields(glazer_id)
        except CustomError as err:
            return self.error(str(err))
        return self.data({"review_fields": review_fields})


@plugin.route(r"/files/(\d+)/bid-matches/download")
class CgsBidsMatchesDownloadHandler(CGSHandler):
    @Auth("browse")
    @doc(tags=["cgs"])
    async def get(self, fid):
        file = await NewFile.find_by_id(fid)
        if not file:
            return self.error(_("not found file"))
        fake_data = FAKE_DATA.get(file.hash)
        if not fake_data:
            return self.error(_("not found json data"))
        json_path = fake_data["json_path"]
        return await self.export(json_path, json_path.rsplit("/")[-1])
