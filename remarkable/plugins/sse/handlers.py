# import os
# from datetime import datetime
#
# from marshmallow import validate
# from sqlalchemy import and_, desc, or_
# from webargs import fields
#
# from remarkable.base_handler import Auth, BaseHandler
# from remarkable.common.apispec_decorators import use_kwargs
# from remarkable.common.constants import AIStatus, ComplianceStatus, SSEAuditStatus
# from remarkable.db import peewee_transaction_wrapper
# from remarkable.models.file_meta import FileMeta
# from remarkable.models.query_helper import Pagination
# from remarkable.models.rule_result import RuleResult
# from remarkable.plugins.sse import plugin
# from remarkable.service.new_file import FileMetaService, SZSEFileService
# from remarkable.service.rule import RuleService
# from remarkable.worker.tasks import process_file
#
#
# @plugin.route(r"/files/(\d+)")
# class FileHandler(BaseHandler):
#     @Auth("browse")
#
#     async def delete(self, file_id):
#         await FileMetaService.remove_by_fid(int(file_id))
#         return self.data("deleted")
#
#
# @plugin.route(r"/files")
# class ReceiveFileHandler(BaseHandler):
#     param = {
#         "sec_code": fields.Str(required=True, validate=validate.Regexp(r"^\d{1,6}$")),
#         "sec_name": fields.Str(required=True),
#         "publish_time": fields.Str(validate=validate.Regexp(r"^\d{4}-\d{2}-\d{2}\s\d{2}:\d{2}:\d{2}$")),
#         "doc_type": fields.Str(load_default="年报"),
#         "report_year": fields.Str(load_default="0", validate=validate.Regexp(r"^\d{4}$")),
#     }
#     search_param = {
#         "stock_code": fields.Str(validate=validate.Regexp(r"^\d+$", error="股票代码必须是纯数字")),
#         "stock_name": fields.Str(),
#         "report_year": fields.Int(),
#     }
#
#     @Auth("browse")
#     @use_kwargs(param, location="form")
#     @use_kwargs({"file": fields.Raw(required=True)}, location="files")
#
#     async def post(self, file, **params):
#         name = file["filename"]
#         data = file["body"]
#         params.setdefault("title", os.path.splitext(name)[0])
#         params.setdefault("publish_time", datetime.now().strftime("%Y-%m-%d %H:%M:%S"))
#         _file = await SZSEFileService.create(name, data, self.current_user.id, params)
#         await process_file(_file)
#         await RuleResult.delete.where(RuleResult.fid == _file.id).gino.status()
#         return self.data(_file.to_dict())
#
#     @Auth("browse")
#     @use_kwargs(Pagination.web_args, location="query")
#     @use_kwargs(search_param, location="query")
#
#     async def get(self, page, size, **params):
#         cond = and_(FileMeta.doc_type == "年报", FileMeta.deleted_utc == 0)
#         if "stock_code" in params:
#             cond &= FileMeta.stock_code.like(f'%{params["stock_code"]}%')
#         if "stock_name" in params:
#             cond &= FileMeta.stock_name.like(f'%{params["stock_name"].replace("%", "")}%')
#         if "report_year" in params:
#             cond &= FileMeta.report_year == params["report_year"]
#         data = await Pagination(cond, FileMeta, page=page, size=size, packer=self.packer).data(
#             order_by=desc(FileMeta.created_utc)
#         )
#         return self.data(data)
#
#     @staticmethod
#     async def packer(row):
#         audit_summary = await RuleService.calc_sse_summary(row.file_id)
#         ret = row.to_dict()
#         # 合规结果为空, 算"预测中"状态, 不允许跳转查看合规审核界面
#         ret["ai_status"] = AIStatus.DOING if all(i == 0 for i in audit_summary.values()) else AIStatus.FINISH
#
#         for col in ("file",):
#             sub_row = getattr(row, col, None)
#             ret[col] = sub_row.to_dict() if sub_row else None
#         ret.update(audit_summary)
#         return ret
#
#
# @plugin.route(r"/rule_summary")
# class RuleSummaryHandler(BaseHandler):
#     @Auth("remark")
#     @use_kwargs({"report_year": fields.Int(required=True)}, location="query")
#     async def get(self, report_year):
#         """合规审核结果统计(按rule分组)"""
#         return self.data(await RuleService.gen_sse_rule_summary(report_year))
#
#
# @plugin.route(r"/rule_detail")
# class RuleDetailHandler(BaseHandler):
#     query_param = {
#         "report_year": fields.Int(required=True),
#         "rule": fields.Str(required=True),
#         "rule_result": fields.Int(
#             required=True,
#             validate=validate.OneOf(SSEAuditStatus.member_values()),
#         ),
#     }
#
#     @Auth("remark")
#     @use_kwargs(Pagination.web_args, location="query")
#     @use_kwargs(query_param, location="query")
#
#     async def get(self, page, size, report_year, rule, rule_result):
#         if rule_result == SSEAuditStatus.TODO:
#             cond = and_(RuleResult.result == SSEAuditStatus.UNCERTAIN, RuleResult.audit_status == SSEAuditStatus.TODO)
#         else:
#             cond = or_(
#                 RuleResult.audit_status == rule_result,
#                 and_(RuleResult.result == rule_result, RuleResult.audit_status == SSEAuditStatus.TODO),
#             )
#         cond &= and_(
#             FileMeta.doc_type == "年报",
#             FileMeta.report_year == report_year,
#             FileMeta.deleted_utc == 0,
#             RuleResult.rule == rule,
#         )
#         data = await Pagination(cond, RuleResult, page=page, size=size, packer=self.packer).data(
#             order_by=desc(FileMeta.created_utc)
#         )
#         return self.data(data)
#
#     @staticmethod
#     def packer(row):
#         ret = {"rule_result": row.to_dict()}
#         for col in "file", "file_meta":
#             sub_row = getattr(row, col, None)
#             ret[col] = sub_row.to_dict() if sub_row else None
#         if row.audit_status != SSEAuditStatus.TODO:
#             # 有人工审核介入, 覆盖AI判断信息
#             ret["rule_result"].update(
#                 {
#                     "comment": "合规"
#                     if SSEAuditStatus.COMP_0 <= row.audit_status < SSEAuditStatus.NON_COMP_0
#                     else "不合规",
#                     "second_rule": SSEAuditStatus.status_anno_map()[row.audit_status],
#                 }
#             )
#         return ret
#
#
# @plugin.route(r"/rule_results/(\d+)")
# class UpdateRuleResultHandler(BaseHandler):
#     put_args = {
#         "audit_status": fields.Int(required=True, validate=validate.OneOf(SSEAuditStatus.member_values())),
#     }
#
#     @Auth("remark")
#     @use_kwargs(put_args, location="json")
#
#     async def put(self, rule_result_id, audit_status):
#         rule_result_id = int(rule_result_id)
#         rule_result = await RuleResult.get(rule_result_id)
#         if not rule_result:
#             return self.error(f"Record: {rule_result} Not found")
#         if rule_result.result != ComplianceStatus.IGNORE:
#             await (
#                 RuleResult.update.values(audit_status=audit_status).where(RuleResult.id == rule_result_id).gino.status()
#             )
#         return self.data("success")
#
#
# @plugin.route(r"/audit_status_map")
# class AuditStatusHandler(BaseHandler):
#     @Auth("remark")
#
#     async def get(self, *args, **kwargs):
#         return self.data(
#             [
#                 {"key": SSEAuditStatus.value2member_map()[k].name, "label": v, "value": k}
#                 for k, v in SSEAuditStatus.status_anno_map().items()
#                 if SSEAuditStatus.TODO < k
#             ]
#         )
