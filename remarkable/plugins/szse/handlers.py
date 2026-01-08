# import os
# import time
# from datetime import datetime
# from io import BytesIO
#
# from marshmallow import validate
# from sqlalchemy import and_, desc
# from webargs import fields
#
# from remarkable.base_handler import Auth, BaseHandler, DbQueryHandler
# from remarkable.common.apispec_decorators import use_kwargs
# from remarkable.common.constants import (
#     AIStatus,
#     AuditStatusEnum,
#     FillInStatus,
#     ModelType,
#     PredictorTrainingStatus,
#     PrompterTrainingStatus,
#     QuestionStatus,
# )
# from remarkable.common.exceptions import CustomError
# from remarkable.common.util import generate_timestamp
# from remarkable.config import get_config
# from remarkable.converter.szse import SZSEAnswerWorkShop, SZSEConverterMaker
# from remarkable.db import db, peewee_transaction_wrapper
# from remarkable.models.answer import SpecialAnswer
# from remarkable.models.file import FileProject
# from remarkable.models.file_meta import FileMeta
# from remarkable.models.new_file import NewFile
# from remarkable.models.query_helper import Pagination
# from remarkable.models.rule_result import RuleResult
# from remarkable.plugins.fileapi.common import validate_keyword
# from remarkable.plugins.fileapi.PermCheckHandler import PermCheckHandler
# from remarkable.plugins.szse import plugin
# from remarkable.service.new_file import FileMetaService, SZSEFileService
# from remarkable.service.rule import RuleService
# from remarkable.worker.tasks import process_file
#
#
# @plugin.route(r"/json_answer/(?P<question_id>\d+)")
# class SZSEJsonAnswerHandler(DbQueryHandler):
#     json_answer_schema = {
#         "data": fields.Dict(
#             required=True,
#         ),
#     }
#
#     @staticmethod
#     def export_excel(data):
#         workbook = SZSEAnswerWorkShop.export_excel(data)
#         res = BytesIO()
#         workbook.save(res)
#         res.seek(0)
#         return res.read()
#
#     @Auth("browse")
#
#     async def get(self, **kwargs):
#         qid = kwargs["question_id"]
#         export_excel = self.get_query_argument("export_excel", default=0)
#         json_answer = await NewSpecialAnswer.get_answers(qid, NewSpecialAnswer.ANSWER_TYPE_JSON, top=1)
#         if not json_answer:
#             return self.error(_("Answer not ready yet!"))
#         data = json_answer[0].data
#
#         if export_excel:
#             file = await NewFile.find_by_qid(qid)
#             excel = self.export_excel(data)
#             file_name = f"{os.path.splitext(file.name)[0]}.xlsm"
#             return await self.export(excel, file_name, "application/vnd.ms-excel")
#
#         return self.data(data)
#
#     @Auth("browse")
#     @use_kwargs(json_answer_schema, location="json")
#     @peewee_transaction_wrapper
#     async def post(self, **kwargs):
#         qid = kwargs["question_id"]
#         data = kwargs["data"]
#
#         await NewSpecialAnswer.update_or_create(qid, NewSpecialAnswer.ANSWER_TYPE_JSON, data)
#         # 更新question表
#         meta = {
#             "fill_in_status": FillInStatus.FINISH.value,
#             "fill_in_user": self.current_user.name,
#             "data_updated_utc": generate_timestamp(),
#         }
#         question = await NewQuestion.find_by_id(qid)
#         if question:
#             await question.update_(**meta)
#         return self.data({})
#
#
# @plugin.route(r"/json_answer/status/(?P<question_id>\d+)")
# class SZSEJsonAnswerStatusHandler(DbQueryHandler):
#     json_answer_schema = {
#         "field_data": fields.List(
#             fields.Dict(),
#             required=True,
#         ),
#         "field": fields.Str(
#             required=True,
#         ),
#         "status": fields.Int(
#             required=True,
#         ),
#     }
#
#     @Auth("browse")
#     @use_kwargs(json_answer_schema, location="json")
#     @peewee_transaction_wrapper
#     async def post(self, **kwargs):
#         qid = kwargs["question_id"]
#         field_data = kwargs["field_data"]
#         field = kwargs["field"]
#         status = kwargs["status"]
#
#         special_answer = await NewSpecialAnswer.find_by_kwargs(qid=qid, answer_type=NewSpecialAnswer.ANSWER_TYPE_JSON)
#         question = await NewQuestion.find_by_id(qid)
#         all_data = self.fix_answer_status(special_answer.data, question.answer, field, field_data, status)
#         await NewSpecialAnswer.update_or_create(qid, NewSpecialAnswer.ANSWER_TYPE_JSON, all_data)
#         # 更新question表
#         meta = {
#             "fill_in_user": self.current_user.name,
#             "data_updated_utc": generate_timestamp(),
#         }
#         question = await NewQuestion.find_by_id(qid)
#         if question:
#             await question.update_(**meta)
#         return self.data({})
#
#     @staticmethod
#     def fix_answer_status(all_data, question_answer, field, field_data, status):
#         for value in all_data["json_answer"].values():
#             for data_item in value:
#                 for export_field in data_item:
#                     if export_field == field:
#                         data_item[export_field] = field_data
#         answer_status = all_data.get("answer_status")
#         if not answer_status:
#             converter = SZSEConverterMaker.init(question_answer)
#             answer_status = converter.gen_answer_status()
#             all_data["answer_status"] = answer_status
#         for value in all_data.get("answer_status").values():
#             for export_field in value:
#                 if export_field == field:
#                     value[export_field] = status
#         return all_data
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
#         "id": fields.Str(),
#         "ann_id": fields.Int(),
#         "title": fields.Str(),
#         "attach_path": fields.Str(),
#         "attach_format": fields.Str(),
#         "attach_size": fields.Int(),
#         "sec_code": fields.Str(required=True, validate=validate.Regexp(r"^\d{1,6}$")),
#         "sec_name": fields.Str(required=True),
#         "publish_time": fields.Str(validate=validate.Regexp(r"^\d{4}-\d{2}-\d{2}\s\d{2}:\d{2}:\d{2}$")),
#         "doc_type": fields.Str(load_default="年报"),
#         "report_year": fields.Str(load_default="0", validate=validate.Regexp(r"^\d{4}$")),
#     }
#     search_param = {
#         "stock_code": fields.Str(load_default="0", validate=validate.Regexp(r"^\d+$", error="股票代码必须是纯数字")),
#         "stock_name": fields.Str(load_default=""),
#         "report_year": fields.Int(load_default=2019),
#     }
#
#     @use_kwargs(param, location="form")
#     @use_kwargs({"file": fields.Raw(required=True)}, location="files")
#
#     async def post(self, file, **params):
#         # NOTE: 临时方案, 不在缓存中的 stock code 不予支持
#         any_item = await FileMeta.query.where(FileMeta.stock_code == params["sec_code"].rjust(6, "0")).gino.first()
#         if not any_item:
#             return self.error("请输入有效的证券代码")
#
#         name = file["filename"]
#         data = file["body"]
#         params.setdefault("title", os.path.splitext(name)[0])
#         params.setdefault("publish_time", datetime.now().strftime("%Y-%m-%d %H:%M:%S"))
#         _file = await SZSEFileService.create(name, data, self.current_user.id, params)
#         await RuleResult.delete.where(RuleResult.fid == _file.id).gino.status()
#         await process_file(_file)
#         return self.data(_file.to_dict())
#
#     @Auth("browse")
#     @use_kwargs(Pagination.web_args, location="query")
#     @use_kwargs(search_param, location="query")
#
#     async def get(self, page, size, stock_code, stock_name, report_year):
#         cond = (FileMeta.doc_type == "年报") & (FileMeta.deleted_utc == 0)
#         if stock_code and stock_code != "0":
#             cond &= FileMeta.stock_code.like(f"%{stock_code}%")
#         if stock_name:
#             cond &= FileMeta.stock_name.like(f'%{stock_name.replace("%", "")}%')
#         if report_year:
#             cond &= FileMeta.report_year == report_year
#         data = await Pagination(cond, FileMeta, page=page, size=size, packer=self.packer).data(
#             order_by=desc(FileMeta.created_utc)
#         )
#         return self.data(data)
#
#     @staticmethod
#     async def packer(row):
#         audit_summary = await RuleService.calc_audit_summary(row.file_id)
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
# @plugin.route(r"/rule_results/(\d+)")
# class UpdateRuleResultHandler(BaseHandler):
#     put_args = {
#         "audit_status": fields.Int(required=True, validate=validate.OneOf(AuditStatusEnum.member_values())),
#     }
#
#     @Auth("remark")
#     @use_kwargs(put_args, location="json")
#     @peewee_transaction_wrapper
#     async def put(self, rule_result_id, audit_status):
#         rule_result_id = int(rule_result_id)
#         rule_result = await RuleResult.get(rule_result_id)
#         if not rule_result:
#             return self.error(f"Record: {rule_result} Not found")
#
#         await RuleResult.update.values(audit_status=audit_status).where(RuleResult.id == rule_result_id).gino.status()
#         query = RuleResult.query.where(
#             and_(RuleResult.fid == rule_result.fid, RuleResult.rule == rule_result.rule)
#         ).order_by(RuleResult.id)
#
#         summary_item = await query.gino.first()
#         if rule_result.id != summary_item.id:
#             # 子条目状态更新时, 需要同步更新 summary 条目状态
#             async for item in query.gino.iterate():
#                 if item.id == summary_item.id:
#                     continue
#                 # 未披露/延迟披露即视为不合规
#                 if item.audit_status in (AuditStatusEnum.DIS_DELAY, AuditStatusEnum.DIS_NONE):
#                     summary_item.audit_status = AuditStatusEnum.NONCOMPLIANCE
#                     break
#             else:
#                 # 全及时披露才算合规
#                 summary_item.audit_status = AuditStatusEnum.COMPLIANCE
#             await summary_item.update_(audit_status=summary_item.audit_status)
#         return self.data("success")
#
#
# @plugin.route(r"/szse_file", use_common_prefix=True)
# class SzseFileHandler(PermCheckHandler):
#     """
#     深交所定制：标注任务页面
#     """
#
#
#     async def get(self):
#         self.set_header("Content-Type", "application/json")
#         mold = self.get_query_argument("mold")
#         filename = self.get_query_argument("filename", "")
#         sql = """
#                 select {}
#                 from file
#                 left join question on file.id=question.fid
#                 left join mold on mold.id=question.mold
#                 where question.deleted_utc=0 and file.pdfinsight is not null and array_length(file.molds, 1) > 0 and file.pid<>0
#             """
#         if int(mold):
#             sql += f" and question.mold={mold}"
#         elif (get_config("client.support_multiple_molds")):
#             raise CustomError("mold is needed when support_multiple_molds is open")
#
#         if filename:
#             filename = filename.replace("=", "==").replace("%", "=%").replace("_", "=_")
#             sql += f" and file.name ILIKE '%{filename}%' ESCAPE '='"
#         columns = [
#             "file.id",
#             "file.name as file_name",
#             "mold.name as mold_name",
#             "file.created_utc",
#             "question.progress",
#             "question.mark_users",
#             "question.updated_utc",
#             "question.status",
#             "question.id as qid",
#             "question.mold as mold_id",
#             "file.tree_id",
#         ]
#         pagedata = await self.pagedata_from_request(self, sql, columns, orderby="order by file.id desc")
#         for item in pagedata.get("items", []):
#             item["created_utc"] = time.strftime("%Y.%m.%d %H:%M:%S", time.localtime(item["created_utc"]))  # 上传时间
#             item["updated_utc"] = time.strftime(
#                 "%Y.%m.%d %H:%M:%S", time.localtime(item["updated_utc"])
#             )  # 标注更新时间
#             item["progress"] = item["progress"]  # 标注进度
#             item["status"] = QuestionStatus.status_anno_map().get(item["status"], item["status"])  # 标注状态
#         return self.data(pagedata)
#
#
# @plugin.route(r"/szse_model", use_common_prefix=True)
# class SzseModelHandler(PermCheckHandler):
#     """
#     深交所定制：模型信息页面
#     """
#
#
#     async def get(self):
#         self.set_header("Content-Type", "application/json")
#         sql = """
#                 select {}
#                 from model_version
#                 left join mold on mold.id=model_version.mold
#                 WHERE model_version.deleted_utc=0 and mold.deleted_utc=0 and model_version.status<>-1
#             """
#         moldname = self.get_query_argument("moldname", "")
#         if moldname:
#             moldname = moldname.replace("=", "==").replace("%", "=%").replace("_", "=_")
#             sql += f" and mold.name ILIKE '%{moldname}%' ESCAPE '='"
#         columns = [
#             "model_version.id",
#             "model_version.mold as mold_id",
#             "mold.name",
#             "model_version.type",
#             "model_version.enable",
#             "model_version.status",
#             "model_version.created_utc",
#             "model_version.files",
#         ]
#         pagedata = await self.pagedata_from_request(
#             self, sql, columns, orderby="order by mold.id,model_version.id desc"
#         )
#         for item in pagedata.get("items", []):
#             item["id"] = item["id"]  # 模型版本id
#             item["name"] = item["name"]  # 项目/schema名称
#             item["created_utc"] = time.strftime("%Y.%m.%d %H:%M:%S", time.localtime(item["created_utc"]))  # 训练时间
#             item["files"] = len(item["files"])  # 训练文件基数
#             item["model_type"] = ModelType.status_anno_map().get(item["type"], item["type"])  # 模型类型
#             item["enable"] = item["enable"]  # 启用状态
#             # 训练状态
#             if item["type"] == ModelType.PREDICT.value:
#                 item["model_status"] = PredictorTrainingStatus.status_anno_map().get(item["status"], item["status"])
#             elif item["type"] == ModelType.PROMPTER.value:
#                 item["model_status"] = PrompterTrainingStatus.status_anno_map().get(item["status"], item["status"])
#             # 最新准确率
#             sql = (
#                 "select data from accuracy_record where vid=%(vid)s and deleted_utc=0 "
#                 "order by created_utc desc limit 1;"
#             )
#             res = await db.raw_sql(sql, "scalar", vid=item["id"])
#             recent = res if res else {}
#             item["precision"] = "%.2f" % float(recent["total_percent"]) if recent.get("total_percent") else None
#         return self.data(pagedata)
#
#
# @plugin.route(r"/question/search")
# class QuestionSearchHandler(DbQueryHandler):
#     keyword_schema = {
#         "tree_id": fields.Integer(load_default=None),
#         "name": fields.Str(validate=validate_keyword, load_default=""),
#         "id": fields.Str(validate=validate_keyword, load_default=""),
#         "fill_in_status": fields.Str(
#             validate=validate.OneOf([str(i) for i in FillInStatus.member_values()]), load_default=None
#         ),
#     }
#
#     @Auth("browse")
#     @use_kwargs(keyword_schema, location="query")
#
#     async def get(self, **kwargs):
#         tree_id = kwargs["tree_id"]
#         question_name = kwargs["name"]
#         fid = kwargs["id"]
#         fill_in_status = kwargs["fill_in_status"]
#
#         if not tree_id:  # 深交所定制界面的tree_id 为default_tree
#             file_project = await NewFileProject.find_by_kwargs(name="default")
#             tree_id = file_project.rtree_id
#
#         # 深交所填报界面 所有用户只能看到自己上传的文件
#         # https://gitpd.paodingai.com/cheftin/docs_scriber/-/issues/398#note_111799
#         search_sql = """SELECT {} FROM question
#         left join file on question.fid = file.id
#         left join admin_user on file.uid = admin_user.id
#         WHERE question.deleted_utc=0 and file.tree_id=%(tree_id)s and file.uid=%(uid)s """
#         search_condition = "AND question.deleted_utc = 0"
#         if question_name:
#             question_name = question_name.replace("=", "==").replace("%", "=%").replace("_", "=_")
#             search_condition += " AND question.name ILIKE %(question_name)s ESCAPE '='"
#         if fid:
#             search_condition += " AND file.id=%(fid)s"
#         if fill_in_status is not None:
#             search_condition += " AND question.fill_in_status=%(fill_in_status)s"
#
#         columns = [
#             "file.name",
#             "file.id as fid",
#             "admin_user.name as user_name",
#             "question.id as qid",
#             "question.name as question_name",
#             "num as question_num",
#             "ai_status as question_ai_status",
#             "fill_in_status",
#             "fill_in_user",
#             "data_updated_utc",
#             "question.created_utc",
#         ]
#
#         sql = search_sql + search_condition
#         pagedata = await self.pagedata_from_request(
#             self,
#             sql,
#             columns,
#             params={
#                 "tree_id": tree_id,
#                 "question_name": "%" + question_name + "%",
#                 "fid": fid,
#                 "fill_in_status": int(fill_in_status) if fill_in_status else "",
#                 "uid": self.current_user.id,
#             },
#             orderby="ORDER BY question.created_utc DESC",
#         )
#         return self.data(pagedata)
