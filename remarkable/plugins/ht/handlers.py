# import collections
# import hashlib
# import html
# import io
# import json
# import logging
# import os
# import re
# import shutil
# from copy import deepcopy
# from decimal import Decimal
# from json.decoder import JSONDecodeError
#
# import xlwt
# from marshmallow import fields, validate
# from sqlalchemy import asc
# from wordinsight import revise_docx
#
# from remarkable import config
# from remarkable.base_handler import Auth, BaseHandler, DbQueryHandler
# from remarkable.common.apispec_decorators import use_kwargs
# from remarkable.common.constants import AuditStatusEnum, ErrorStatus, RuleMethodType
# from remarkable.common.exceptions import CustomError
# from remarkable.common.storage import LocalStorage, localstorage
# from remarkable.common.util import md5sum, subprocess_exec
# from remarkable.db import db, peewee_transaction_wrapper, init_rdb
# from remarkable.models.answer import SpecialAnswer
# from remarkable.models.error_content import ErrorContent
# from remarkable.models.extract_method import ExtractMethod
# from remarkable.models.file import File
# from remarkable.models.file_template import FileTemplate
# from remarkable.models.mold import Mold
# from remarkable.models.query_helper import Pagination
# from remarkable.models.rule_class import RuleClass
# from remarkable.models.rule_item import RuleItem
# from remarkable.models.rule_result import RuleResult
# from remarkable.models.user import User
# from remarkable.plugins.fileapi.common import clear_tmp_files
# from remarkable.plugins.fileapi.PermCheckHandler import PermCheckHandler
# from remarkable.plugins.ht import plugin
# from remarkable.rule.common import lower2upper, upper2lower
# from remarkable.rule.ht.ht_business_rules.patterns import HT_PATTERNS
# from remarkable.rule.inspector import AnswerInspectorFactory, Inspector
# from remarkable.service.mold import MoldService
# from remarkable.service.rule import RuleService
#
# logger = logging.getLogger(__name__)
#
# tmp_storage = LocalStorage(os.path.join(config.get_config("web.tmp_dir"), "annotation"))
#
# fid_args_schema = {
#     "fid": fields.Int(required=True),
# }
#
# FILE_FORMAT = re.compile(r"docx?$", re.IGNORECASE)
#
#
# @plugin.route(r"/rule_results")
# class RuleResultHandler(DbQueryHandler):
#     args_schema = {
#         "fid": fields.Int(required=True),
#         "mid": fields.Int(required=True),
#     }
#
#     @Auth("remark")
#     @use_kwargs(args_schema, location="query")
#     @peewee_transaction_wrapper
#     async def get(self, fid, mid):
#         file = await NewFile.find_by_id(fid)
#         if not file:
#             raise CustomError("not found file")
#         inspector = None
#         for mold_id in file.molds:
#             mold = await NewMold.find_by_id(mold_id)
#             if not mold:
#                 continue
#             inspector = await AnswerInspectorFactory.create(mold)
#             if inspector:
#                 break
#         rules_order = await self.gen_rules_order(mid, inspector)
#         rule_results = (
#             await RuleResult.load(error=ErrorContent.on(ErrorContent.rule_result_id == RuleResult.id))
#             .query.where(RuleResult.fid == file.id)
#             .order_by(RuleResult.id)
#             .gino.all()
#         )
#         rule_res = collections.defaultdict(list)
#         for rule_result in rule_results:
#             res = rule_result.to_dict()
#             res["error_content"] = rule_result.error.content if hasattr(rule_result, "error") else None
#             rule_res[rule_result.rule].append(res)
#         ret = {
#             "rule_res": rule_res,
#             "rules_order": rules_order,
#         }
#         return self.data(ret)
#
#     async def gen_rules_order(self, mid, inspector):
#         mold_name = await Mold.get_name_by_id(mid)
#         if mold_name in ("软件开发外包合同", "软件使用许可合同", "硬件采购合同"):
#             # 预设 schema 固定顺序
#             rules_order = [
#                 "大小写校验",
#                 "分笔付款比例校验",
#                 "合同总金额校验",
#                 "税款校验",
#                 "增值税税率校验",
#                 "最后一笔付款条件校验",
#                 "固定条款对比",
#                 "项目负责人",
#                 "附件检查",
#             ]
#             if mold_name == "硬件采购合同":
#                 rules_order.remove("最后一笔付款条件校验")
#         elif inspector and isinstance(inspector, Inspector):
#             rules_order = list({rule.name: 1 for rule in inspector.rules if rule.name}.keys())
#         else:
#             rules_order = []
#
#         # 补充自定义 rule_class
#         rule_classes = await RuleClass.list_by_mold(mid)
#         for rule_class in rule_classes:
#             if rule_class.name not in rules_order:
#                 rules_order.append(rule_class.name)
#         return rules_order
#
#
# @plugin.route(r"/rule_results/(?P<rule_result_id>\d+)")
# class UpdateRuleResultHandler(DbQueryHandler):
#     user_args = {
#         "status": fields.Integer(
#             required=True,
#             validate=validate.OneOf(
#                 [AuditStatusEnum.UNAUDITED.value, AuditStatusEnum.ACCEPT.value, AuditStatusEnum.REFUSE.value]
#             ),
#         ),
#     }
#
#     @Auth("remark")
#     @use_kwargs(user_args, location="json")
#     @peewee_transaction_wrapper
#     async def put(self, rule_result_id, status):
#         await RuleResult.update_audit_status(rule_result_id, status)
#         return self.data("success")
#
#
# @plugin.route(r"/errors")
# class ErrorHandler(DbQueryHandler):
#     user_args = {
#         "fid": fields.Integer(required=True),
#         "rule_result_id": fields.Integer(required=True),
#         "content": fields.String(required=True),
#     }
#
#     args_schema = {
#         "fid": fields.Integer(required=True),
#         "username": fields.String(),
#     }
#
#     @Auth("remark")
#     @use_kwargs(user_args, location="json")
#     @peewee_transaction_wrapper
#     async def post(self, fid, rule_result_id, content):
#         params = {
#             "uid": self.current_user.id,
#             "fid": fid,
#             "rule_result_id": rule_result_id,
#             "content": content,
#             "error_status": ErrorStatus.UNAMEND.value,
#         }
#         sql = """
#         INSERT INTO error_content (uid, fid, rule_result_id, content, error_status)
#         VALUES (%(uid)s, %(fid)s, %(rule_result_id)s, %(content)s, %(error_status)s)
#         ON conflict (uid, fid,rule_result_id) do UPDATE
#         SET content = excluded.content,
#            updated_utc=extract(epoch from now())::int
#         """
#         await db.raw_sql(sql, **params)
#         await RuleResult.update_audit_status(rule_result_id, AuditStatusEnum.REFUSE.value)
#         return self.data("success")
#
#     @Auth("browse")
#     @use_kwargs(args_schema, location="query")
#     @peewee_transaction_wrapper
#     async def get(self, fid, username):
#         search_condition = ""
#         search_sql = """SELECT {}
#                         FROM error_content err
#                         JOIN file f ON err.fid = f.id
#                         JOIN admin_user u ON err.uid = u.id"""
#         if fid:
#             search_condition = " WHERE err.fid=%(fid)s"
#         elif username:
#             user = await User.find_by_kwargs(name=username)
#             if not user:
#                 return self.data({"page": 1, "size": 20, "total": 0, "items": []})
#             search_condition = " WHERE err.uid=%s" % user.id
#
#         columns = [
#             "err.id AS id",
#             "f.name AS file_name",
#             "err.fid AS fid",
#             "err.content AS content",
#             "to_char(to_timestamp(err.created_utc) AT TIME ZONE 'PRC', 'YYYY/MM/DD HH24:MI:SS') AS error_date",
#             "err.uid AS user_id",
#             "u.name AS user_name",
#             "err.error_status AS error_status",
#         ]
#
#         sql = search_sql + search_condition + " AND err.deleted_utc = 0;"
#         pagedata = await self.pagedata_from_request(self, sql, columns, params={"fid": fid}, orderby="ORDER BY id DESC")
#         return self.data(pagedata)
#
#
# @plugin.route(r"/errors/(?P<error_id>\d+)")
# class UpdateErrorStatusHandler(DbQueryHandler):
#     user_args = {
#         "status": fields.Integer(required=True),
#     }
#
#     @Auth("remark")
#     @use_kwargs(user_args, location="form")
#     @peewee_transaction_wrapper
#     async def put(self, error_id, error_status):
#         error_content = await ErrorContent.find_by_id(error_id)
#         if not error_content:
#             return self.data("error content not exist")
#         if error_status not in (ErrorStatus.AMEND.value, ErrorStatus.UNAMEND.value):
#             return self.data("status error")
#         await error_content.update_(error_status=error_status)
#         if error_status == ErrorStatus.AMEND.value:
#             await RuleResult.update_audit_status(error_content.rule_result_id, AuditStatusEnum.ACCEPT.value)
#         return self.data("success")
#
#
# @plugin.route(r"/annotated_document")
# class AnnotateDocumentHandler(DbQueryHandler):
#     @Auth("browse")
#     @use_kwargs(fid_args_schema, location="query")
#     @peewee_transaction_wrapper
#     async def get(self, fid):
#         file = await NewFile.find_by_id(fid)
#         file_hash = file.hash
#         file_path = file.docx_path()
#         if not file_path:
#             raise CustomError("仅支持对docx格式文档生成批注")
#         tmp_dir = tmp_storage.mount(file_hash[:2])
#         if not os.path.exists(tmp_dir):
#             os.makedirs(tmp_dir)
#         tmp_json_path = os.path.join(tmp_dir, os.path.splitext(file.name)[0] + ".json")
#
#         # dump json
#         await self.gen_annotate_json(fid, tmp_json_path)
#
#         tmp_docx_path = os.path.join(tmp_dir, file.name)
#         tmp_revised_docx_path = tmp_docx_path + ".revised"
#         data = localstorage.read_file(file_path, decrypt=True)
#         localstorage.write_file(tmp_docx_path, data, encrypt=False)
#
#         revision_dll = config.get_config("web.revision_tools")
#         try:
#             revise_docx(tmp_docx_path, tmp_revised_docx_path)
#             subprocess_exec("{} -d '{}' --json '{}'".format(revision_dll, tmp_revised_docx_path, tmp_json_path))
#             docx_with_revision_path = tmp_revised_docx_path
#         except Exception as e:
#             return self.error("add annotation failed, error_info {}".format(str(e)))
#         annotation_path = md5sum(docx_with_revision_path)
#         # copy tmp to data/files
#         annotation_dir = localstorage.mount(annotation_path[:2])
#         if not os.path.exists(annotation_dir):
#             os.makedirs(annotation_dir)
#         new_docx_path = os.path.join(annotation_dir, annotation_path[2:])
#         shutil.copy(docx_with_revision_path, new_docx_path)
#         # update annotation_path to file
#         await file.update_(annotation_path=annotation_path)
#         # clean tmp file
#         clear_tmp_files(docx_with_revision_path, tmp_json_path)
#         return self.data("success")
#
#     async def gen_annotate_json(self, fid, tmp_json_path):
#         annotation_json = []
#         rule_results = await RuleResult.get_by_fid(fid)
#         for rule_result in rule_results:
#             if rule_result.audit_status == AuditStatusEnum.ACCEPT.value:
#                 label_info = rule_result.detail.get("label_info")
#                 if label_info:
#                     annotation = {"comment": self.label_info_text(label_info), "type": "error"}
#                 else:
#                     annotation = {"comment": rule_result.comment, "type": "error"}
#                 x_paths = rule_result.comment_pos.get("xpath", [])
#                 if not isinstance(x_paths, list):  # 兼容海通业务合同数据
#                     x_paths = [x_paths]
#                 for x_path in x_paths:
#                     annotation_res = deepcopy(annotation)
#                     annotation_res["xpath"] = x_path
#                     annotation_json.append(annotation_res)
#         with open(tmp_json_path, "w") as tmp:
#             json.dump(annotation_json, tmp)
#         return annotation_json
#
#     @staticmethod
#     def label_info_text(label_info):
#         try:
#             label_info_obj = json.loads(label_info)
#             return "\n".join(line.replace("<em>", "").replace("</em>", "") for line in label_info_obj)
#         except Exception as exp:
#             logger.exception(exp)
#             return label_info
#
#
# @plugin.route(r"/file/(\d+)/annotated")
# class FileHandler(PermCheckHandler):
#     @Auth("browse")
#     @peewee_transaction_wrapper
#     async def get(self, fid):
#         """批注文件下载"""
#         file = await NewFile.find_by_id(fid)
#         if not file or not file.annotation_path:
#             raise CustomError(_("not found file"))
#         await self.check_file_permission(file.id)
#         name_char = os.path.splitext(file.name)
#         _file_name = name_char[0] + "_已批注" + name_char[1]
#         return await self.export(localstorage.mount(file.annotation_pdf_path()), _file_name)
#
#
# @plugin.route(r"/export_error")
# class ExportErrorHandler(PermCheckHandler):
#     args_schema = {
#         "s_time": fields.String(required=True),
#         "e_time": fields.String(required=True),
#     }
#
#     @Auth("browse")
#     @use_kwargs(args_schema, location="query")
#     @peewee_transaction_wrapper
#     async def get(self, s_time, e_time):
#         """导出报错信息"""
#         time_cond = """
#             and to_char(TO_TIMESTAMP(f.created_utc), 'YYYY-MM-DD')>='%s '
#             and to_char(TO_TIMESTAMP(f.created_utc), 'YYYY-MM-DD')<='%s '
#         """ % (
#             s_time,
#             e_time,
#         )
#
#         _sql = f"""
#                 SELECT err.id AS id, f.name AS file_name, err.fid AS fid, err.content AS content,
#                    to_char(to_timestamp(err.created_utc) AT TIME ZONE 'PRC', 'YYYY/MM/DD HH24:MI:SS') AS error_date,
#                    err.uid AS user_id, u.name AS user_name, err.error_status AS error_status
#                 FROM error_content err
#                 JOIN file f ON err.fid = f.id
#                 JOIN admin_user u ON err.uid = u.id
#                 WHERE err.deleted_utc = 0
#                 AND f.deleted_utc = 0
#                 {time_cond}
#                 ORDER BY id DESC"""
#
#         data = await db.raw_sql(_sql)
#         data = json.dumps([dict(item) for item in data]).encode()
#         return await self.export(data, "报错信息.json")
#
#
# @plugin.route(r"/file/(?P<fid>\d+)/recheck")
# class ReCheckHandler(PermCheckHandler):
#     @Auth("browse")
#     @use_kwargs({"answer": fields.Dict(load_default=None, data_key="data")}, location="json")
#     @use_kwargs(
#         {
#             "mid": fields.Integer(required=True),
#         },
#         location="query",
#     )
#     @peewee_transaction_wrapper
#     async def put(self, fid, mid, answer):
#         """规则的重新审核"""
#         _file = await NewFile.find_by_id(fid)
#         if not _file:
#             raise CustomError(_("not found file"))
#         question = await NewQuestion.find_by_fid_mid(_file.id, mid)
#         await question.update_(preset_answer=answer)
#         await question.set_answer()
#         await RuleService.inspect_rules(_file)
#         return self.data({})
#
#
# @plugin.route(r"/convert-amount")
# class ConvertAmountHandler(PermCheckHandler):
#     args_schema = {
#         "amount": fields.String(required=True),
#         "schema_col": fields.String(required=True),
#         "qid": fields.Integer(required=True),
#     }
#
#     @Auth("browse")
#     @use_kwargs(args_schema, location="query")
#
#     async def get(self, amount, schema_col, qid):
#         question = await NewQuestion.find_by_id(qid)
#         if not question:
#             return self.error(_("Question not exists."))
#         ratio_pattern = HT_PATTERNS["ratio_pattern"]
#         lower_sub_pattern = HT_PATTERNS["lower_sub_pattern"]
#         upper_sub_pattern = HT_PATTERNS["upper_sub_pattern"]
#         converted_value = ""
#         if "维护费用" in schema_col and ratio_pattern.search(amount):
#             try:
#                 con_amount = self.get_con_amount(question.preset_answer, lower_sub_pattern)
#                 con_amount = Decimal(con_amount)
#                 matcher = ratio_pattern.search(amount)
#                 ratio = int(matcher.group(1).strip())
#                 ops_amount = str(con_amount * ratio / 100)
#                 if "大" in schema_col:
#                     ops_amount = "人民币" + lower2upper(ops_amount)
#                 else:
#                     ops_amount = "￥" + ops_amount
#             except Exception as e:
#                 print(e)
#                 return self.error(_("Ops amount has error."))
#
#             return self.data(ops_amount)
#         if "小" in schema_col:
#             texts = lower_sub_pattern.sub("", amount)
#             if texts.strip():
#                 converted_value = "人民币" + lower2upper(texts.strip())
#         elif "大" in schema_col:
#             amount = re.sub(r"\s", "", amount)
#             texts = upper_sub_pattern.sub("", amount)
#             texts = Decimal(upper2lower(texts.strip())).quantize(Decimal("0.00"))
#             converted_value = "￥" + format(texts, ",")
#         return self.data(converted_value)
#
#     @staticmethod
#     def get_con_amount(answer, lower_sub_pattern):
#         con_amount = ""
#         for item in answer["userAnswer"]["items"]:
#             if item["schema"]["data"]["label"] == "合同总金额小写":
#                 con_amount = item["data"][0]["boxes"][0]["text"]
#                 break
#         amount = lower_sub_pattern.sub("", con_amount)
#         return amount
#
#
# @plugin.route(r"/template/(\d+)")
# class TemplateHandler(PermCheckHandler):
#     @Auth("browse")
#
#     async def get(self, file_template_id):
#         file_template = await FileTemplate.find_by_id(file_template_id)
#         if not file_template:
#             raise CustomError(_("template file not found"))
#         return await self.export(localstorage.mount(file_template.path()), file_template.name)
#
#     @Auth("manage_prj")
#     @peewee_transaction_wrapper
#     async def delete(self, file_template_id):
#         file_template = await FileTemplate.find_by_id(file_template_id)
#         if not file_template:
#             raise CustomError(_("template file not found"))
#         res = await FileTemplate.find_by_hash(file_template.hash_name)
#         if len(res) == 1:
#             localstorage.delete_file(file_template.path())
#         await file_template.delete()
#         return self.data({})
#
#
# @plugin.route(r"/template")
# class TemplateUpload(PermCheckHandler):
#     @Auth("manage_prj")
#     @use_kwargs({"file": fields.Raw(required=True)}, location="files")
#     @peewee_transaction_wrapper
#     async def post(self, file):
#         file_hash = hashlib.md5(file["body"]).hexdigest()
#         file_name = file["filename"]
#         if not self.is_valid_ht_file_format(file_name):
#             return self.error(_("Invalid file format"))
#         same_file = await FileTemplate.find_by_name(file_name)
#         if same_file:
#             return self.error(_("template file already exists"))
#         params = {
#             "name": file_name,
#             "hash_name": file_hash,
#         }
#         file_template = await FileTemplate.create(**params)
#         localstorage.write_file(file_template.path(), file["body"])
#         return self.data(file_template.to_dict())
#
#     @Auth("browse")
#     @use_kwargs(Pagination.web_args, location="query")
#     @use_kwargs({"filename": fields.Str()}, location="query")
#     async def get(self, page, size, **params):
#         cond = FileTemplate.deleted_utc == 0
#         if "filename" in params:
#             cond &= FileTemplate.name == params["filename"]
#         data = await Pagination(cond, cls=FileTemplate, page=page, size=size).data()
#
#         return self.data(data)
#
#     @staticmethod
#     def is_valid_ht_file_format(filename):
#         return FILE_FORMAT.search(filename)
#
#
# @plugin.route(r"/extract_method")
# class ExtractMethodHandler(PermCheckHandler):
#     query_params = {
#         "mold": fields.Str(required=True),
#         "path": fields.Str(required=True),
#     }
#
#     @Auth("browse")
#     @use_kwargs(query_params, location="query")
#
#     async def get(self, mold, path):
#         extract_method = await ExtractMethod.find_by_path_and_mold(path, mold)
#         data = extract_method.to_dict() if extract_method else {}
#         return self.data(data)
#
#     json_args_schema = {
#         "mold": fields.Int(required=True),
#         "path": fields.Str(required=True),
#         "data": fields.Dict(required=True),
#         "method_type": fields.Int(required=True),
#     }
#
#     @Auth("browse")
#     @use_kwargs(json_args_schema, location="json")
#     @peewee_transaction_wrapper
#     async def post(self, mold, path, data, method_type):
#         mold_obj = await NewMold.find_by_id(mold)
#         if not mold_obj:
#             return self.error(message=_("can't find the mold"), status_code=400)
#         extract_method = await ExtractMethod.find_by_path_and_mold(path, mold)
#         regs = data.get("regs", [])
#         if regs:
#             regs = [html.unescape(reg) for reg in regs if reg]  # 去掉类似于''的正则表达式
#             data["regs"] = regs
#         if extract_method:
#             updates = {
#                 "data": data,
#                 "method_type": method_type,
#             }
#             await extract_method.update_(**updates)
#             await self.update_framework_version(mold_obj)
#             return self.data("success")
#
#         item = {
#             "path": path,
#             "mold": mold,
#             "data": data,
#             "method_type": method_type,
#         }
#         extract_method = await ExtractMethod.create(**item)
#         await self.update_framework_version(mold_obj)
#         return self.data(extract_method.to_dict())
#
#     async def update_framework_version(self, mold_obj):
#         # todo 迁移界面配置的提取方法到2.0的提取框架
#         if mold_obj.predictor_option and mold_obj.predictor_option["framework_version"] == "2.0":
#             await mold_obj.update_(**{"predictor_option": {"framework_version": "1.0"}})
#             logger.info(f"mold：{mold_obj.id} update framework_version to 1.0")
#
#
# @plugin.route(r"/class/mold/(\d+)")
# class RuleClassHandler(PermCheckHandler):
#     @Auth("browse")
#
#     async def get(self, mold):
#         classes = await RuleClass.list_by_mold(mold)
#         classes = [item.to_dict() for item in classes]
#         return self.data(classes)
#
#     json_args_schema = {
#         "method_type": fields.Int(required=True),
#         "name": fields.Str(required=True),
#     }
#
#     @Auth("manage_prj")
#     @use_kwargs(json_args_schema, location="json")
#     @peewee_transaction_wrapper
#     async def post(self, mold, name, method_type):
#         if not method_type:
#             return self.error(message="miss column `method_type`", status_code=400)
#         if method_type not in (RuleMethodType.TERM, RuleMethodType.FORMULA):
#             return self.error(message=f"undefined method_type value `{method_type}`", status_code=400)
#
#         rule_class = await RuleClass.create_(
#             **{
#                 "name": name,
#                 "mold": mold,
#                 "method_type": method_type,
#             }
#         )
#         return self.data(rule_class.to_dict())
#
#
# @plugin.route(r"/class/(\d+)")
# class RuleClassModifyHandler(PermCheckHandler):
#     @Auth("manage_prj")
#
#     async def delete(self, cid):
#         rule_class = await RuleClass.find_by_id(cid)
#         if not rule_class:
#             return self.error(message=f"can't find rule class `{cid}`", status_code=400)
#         rule_items = await RuleItem.list_by_rule_class(cid)
#         if rule_items:
#             await RuleItem.clear_by_rule_class(cid)
#         await rule_class.delete_()
#         return self.data({})
#
#     json_args_schema = {
#         "method_type": fields.Int(required=True),
#         "name": fields.Str(required=True),
#     }
#
#     @Auth("manage_prj")
#     @use_kwargs(json_args_schema, location="json")
#     @peewee_transaction_wrapper
#     async def put(self, cid, name, method_type):
#         rule_class = await RuleClass.find_by_id(cid)
#         if not rule_class:
#             return self.error(message=f"can't find rule class `{cid}`", status_code=400)
#
#         columns = {}
#         if name:
#             columns["name"] = name
#         if method_type is not None and method_type not in (RuleMethodType.TERM, RuleMethodType.FORMULA):
#             return self.error(message=f"undefined method_type value `{method_type}`", status_code=400)
#         if method_type is not None:
#             columns["method_type"] = method_type
#
#         if not columns:
#             return self.error(message="nothing to update", status_code=400)
#         await rule_class.update_(**columns)
#
#
# @plugin.route(r"/item/class/(\d+)")
# class RuleItemHandler(PermCheckHandler):
#     @Auth("browse")
#     @use_kwargs(Pagination.web_args, location="query")
#
#     async def get(self, cid, page, size):
#         cond = RuleItem.class_name == int(cid)
#
#         data = await Pagination(cond, RuleItem, page=page, size=size).data(
#             query=RuleItem.loader(), order_by=asc(RuleItem.id)
#         )
#         return self.data(data)
#
#     json_args_schema = {
#         "name": fields.Str(required=True),
#         "data": fields.Dict(required=True),
#     }
#
#     @Auth("browse")
#     @use_kwargs(json_args_schema, location="json")
#     @peewee_transaction_wrapper
#     async def post(self, cid, name, data):
#         rule_class = await RuleClass.find_by_id(cid)
#         if not rule_class:
#             return self.error(message=f"can't find rule class `{cid}`", status_code=400)
#
#         item = await NewRuleItem.create(
#             **{
#                 "name": name,
#                 "class_name": rule_class.id,
#                 "mold": rule_class.mold,
#                 "method_type": rule_class.method_type,
#                 "data": data,
#             }
#         )
#         return self.data(item.to_dict())
#
#
# @plugin.route(r"/item/(\d+)")
# class RuleItemModifyHandler(PermCheckHandler):
#     @Auth("manage_prj")
#
#     async def delete(self, rid):
#         rule_item = await RuleItem.find_by_id(rid)
#         if not rule_item:
#             return self.error(message=f"can't find rule `{rid}`", status_code=400)
#         await rule_item.delete_()
#         return self.data({})
#
#     json_args_schema = {
#         "name": fields.Str(required=True),
#         "data": fields.Dict(required=True),
#     }
#
#     @Auth("manage_prj")
#     @use_kwargs(json_args_schema, location="json")
#     @peewee_transaction_wrapper
#     async def put(self, rid, name, data):
#         rule_item = await RuleItem.find_by_id(rid)
#         if not rule_item:
#             return self.error(message=f"can't find rule `{rid}`", status_code=400)
#         columns = {
#             "name": name,
#             "data": data,
#         }
#         await rule_item.update_(**columns)
#
#
# @plugin.route(r"/schema/sync")
# class SchemaRuleSyncHandler(PermCheckHandler):
#     @Auth("manage_prj")
#     @use_kwargs({"mold": fields.Int(required=True)}, location="query")
#
#     async def get(self, mold):
#         mold_obj = await NewMold.find_by_id(mold)
#         if not mold_obj:
#             return self.error(message=_("can't find the mold"), status_code=400)
#
#         data = await NewMoldService.export_schema(mold_obj)
#         return await self.export(json.dumps(data, ensure_ascii=False).encode(), f"{mold_obj.name}.json")
#
#     user_args = {
#         "rewrite": fields.String(required=False, load_default=""),
#         "rename": fields.String(required=False, load_default=""),
#     }
#
#     @Auth("manage_prj")
#     @use_kwargs({"file": fields.Raw(required=True)}, location="files")
#     @use_kwargs(user_args, location="form")
#     @peewee_transaction_wrapper
#     async def post(self, file, rewrite, rename):
#         status, info = self.check_json_file(file)
#         if not status:
#             return info
#
#         meta = json.loads(file["body"])
#         success, msg = await NewMoldService.sync_mold_and_rule(meta, rewrite, rename)
#         if not success:
#             return self.error(_(msg))
#         return self.data({})
#
#     def check_json_file(self, file):
#         try:
#             params = json.loads(file["body"])
#         except JSONDecodeError:
#             return False, self.error(message=_("Payload is not dict"), status_code=400)
#
#         if not isinstance(params, dict):
#             return False, self.error(message=_("Payload is not dict"), status_code=400)
#         columns = ("mold", "extract_method", "rule_class", "rule_item")
#         for column in columns:
#             if column not in params:
#                 return False, self.error(message="{}".format(column) + _(" is required"), status_code=400)
#         return True, None
#
#
# @plugin.route(r"/ht_stat")
# class StatHandler(DbQueryHandler):
#     query_params = {
#         "group_by": fields.Str(
#             validate=validate.OneOf(
#                 [
#                     "month",
#                     "day",
#                     "mold",
#                     "user",
#                 ]
#             )
#         ),
#         "department_id": fields.Str(required=False, load_default=""),
#         "s_time": fields.Str(required=True),
#         "e_time": fields.Str(required=True),
#         "is_export": fields.Boolean(required=False, load_default=False),
#     }
#
#     @Auth("manage_user")
#     @use_kwargs(query_params, location="query")
#
#     async def get(self, group_by, department_id, s_time, e_time, is_export):
#         col_map = {
#             "month": [
#                 "to_char(TO_TIMESTAMP(f.created_utc),'YYYY-MM') as g",  # 按月汇总
#                 "count(distinct f.id) as file_cnt",  # 文档数
#                 "count(distinct q.id) as ai_finish_cnt",  # 分析完成数
#                 "count(distinct res.fid) as err_file_cnt",  # 问题文档数
#                 "count(distinct res.id) as err_rule_cnt",  # 不符合规则数
#                 "count(distinct war.id) as warning_cnt",  # 报错数
#                 "count(distinct f.uid) as user_cnt",  # 用户数
#             ],
#             "day": [
#                 "to_char(TO_TIMESTAMP(f.created_utc), 'YYYY-MM-DD') as g",  # 按天汇总
#                 "count(distinct f.id) as file_cnt",
#                 "count(distinct q.id) as ai_finish_cnt",
#                 "count(distinct res.fid) as err_file_cnt",
#                 "count(distinct res.id) as err_rule_cnt",
#                 "count(distinct war.id) as warning_cnt",
#                 "count(distinct f.uid) as user_cnt",
#             ],
#             "mold": [
#                 "coalesce(m.name,'未指定合同类型') as g",  # 按合同类型汇总
#                 "count(distinct f.id) as file_cnt",
#                 "count(distinct q.id) as ai_finish_cnt",
#                 "count(distinct res.fid) as err_file_cnt",
#                 "count(distinct res.id) as err_rule_cnt",
#                 "count(distinct war.id) as warning_cnt",
#                 "count(distinct f.uid) as user_cnt",
#             ],
#             "user": [
#                 "coalesce(u.name,'未指定用户') as g",  # 按用户汇总
#                 "department_id as department_id",
#                 "department as department",
#                 "count(distinct f.id) as file_cnt",
#                 "count(distinct q.id) as ai_finish_cnt",
#                 "count(distinct res.fid) as err_file_cnt",
#                 "count(distinct res.id) as err_rule_cnt",
#                 "count(distinct war.id) as warning_cnt",
#                 # "count(distinct f.uid) as user_cnt",
#             ],
#         }
#         department_sql = "AND u.department_id=%(department_id)s" if department_id else ""
#         group_by_department = ",department, department_id" if group_by == "user" else ""
#         # if group_by not in col_map:
#         #     raise CustomError(_("group by unknown column"))
#
#         columns = col_map[group_by]
#         time_cond = """
#             and to_char(TO_TIMESTAMP(f.created_utc), 'YYYY-MM-DD')>=%(s_time)s
#             and to_char(TO_TIMESTAMP(f.created_utc), 'YYYY-MM-DD')<=%(e_time)s
#         """
#
#         sql = """
#         WITH f AS(
#             SELECT {cols}
#                 FROM file as f
#                 left join question as q on f.id=q.fid and q.ai_status=3
#                 left join rule_result as res on res.fid=f.id and res.result=1
#                 left join mold as m on m.id=q.mold
#                 left join admin_user as u on u.id=f.uid
#                 left join error_content as war on war.fid=f.id and war.deleted_utc=0
#                 WHERE True {department_sql}
#                 {time_cond}
#                 group by g {group_by_department}
#         ),d_f AS(
#             SELECT {g}
#                 ,count(distinct f.id) as file_del_cnt
#                 FROM file as f
#                 left join question as q on f.id=q.fid and q.ai_status=3
#                 left join rule_result as res on res.fid=f.id and res.result=1
#                 left join mold as m on m.id=q.mold
#                 left join admin_user as u on u.id=f.uid
#                 left join error_content as war on war.fid=f.id and war.deleted_utc=0
#                 WHERE f.deleted_utc!=0 {department_sql}
#                 {time_cond}
#                 group by g
#         )
#         select {query_cols}
#           from f
#           left join d_f on d_f.g=f.g
#           order by f.g desc
#         """.format(
#             cols=",".join(columns),
#             g=columns[0],
#             time_cond=time_cond,
#             department_sql=department_sql,
#             group_by_department=group_by_department,
#             query_cols=",".join(
#                 ["f." + re.split(r"\bas\b\s*", col)[-1] for col in columns]
#                 + [
#                     "file_del_cnt",
#                 ]
#             ),
#         )
#         params = {
#             "department_id": department_id,
#             "s_time": s_time,
#             "e_time": e_time,
#         }
#
#         # columns = ['f.' + re.split(r'\bas\b\s*', col)[-1] for col in columns] + ['file_del_cnt', ]
#         pagedata = await Pagination().data(sql, **params)
#         summary = {}  # 汇总数据
#         for item in pagedata.get("items", []):
#             for k, sub_item in item.items():
#                 if k == "g":
#                     continue
#                 summary.setdefault(k, 0)
#                 if sub_item and isinstance(sub_item, int):
#                     summary[k] += sub_item
#         # 用户总数单独统计
#         (user_cnt,) = await self.get_user_cnt(time_cond, params=params)
#         summary["user_cnt"] = user_cnt.user_cnt
#         pagedata["sum"] = summary
#         if is_export:
#             excel_name_map = {
#                 "month": "按月统计",
#                 "day": "按天统计",
#                 "mold": "分类统计",
#                 "user": "用户使用统计",
#             }
#             excel_title_map = {
#                 "month": ["日期", "文档数", "分析完成", "问题文档数", "不符合规则数", "报错数", "用户数", "用户删除"],
#                 "day": ["日期", "文档数", "分析完成", "问题文档数", "不符合规则数", "报错数", "用户数", "用户删除"],
#                 "mold": [
#                     "合同类型",
#                     "文档数",
#                     "分析完成",
#                     "问题文档数",
#                     "不符合规则数",
#                     "报错数",
#                     "用户数",
#                     "用户删除",
#                 ],
#                 "user": ["用户", "部门ID", "部门", "文档数", "分析完成", "问题文档数", "不符合规则数", "报错数"],
#             }
#             data = self.gen_excel(
#                 pagedata, group_by, header=excel_title_map[group_by], sheet_name=excel_name_map[group_by]
#             )
#             return await self.export(data, f"{excel_name_map[group_by]}.xls")
#         return self.data(pagedata)
#
#     async def get_user_cnt(self, time_cond, params):
#         sql = """
#         SELECT count(distinct f.uid) as user_cnt
#             FROM file as f
#             WHERE 1=1
#             {time_cond}
#         """.format(time_cond=time_cond)
#         return await db.raw_sql(sql, **params)
#
#     @staticmethod
#     def gen_excel(data, group_by, header, sheet_name):
#         excel_io = io.BytesIO()
#         workbook = xlwt.Workbook(encoding="utf-8")
#         worksheet = workbook.add_sheet(sheet_name)
#         for index, value in enumerate(header):
#             worksheet.write(0, index, value)
#
#         for row_index, row_data in enumerate(data["items"], start=1):
#             for index, (key, value) in enumerate(row_data.items()):
#                 # 用户使用统计导出时需要过滤文件删除数
#                 if group_by == "user" and key == "file_del_cnt":
#                     continue
#                 worksheet.write(row_index, index, value)
#         workbook.save(excel_io)
#         return excel_io.getvalue()
#
#
# @plugin.route(r"/mock-htesb")
# class MockHandler(BaseHandler):
#     user_args = {
#         "file_id": fields.Str(required=True, data_key="ID"),
#         "code": fields.Str(required=True, data_key="CODE"),
#         "note": fields.Str(required=True, data_key="NOTE"),
#         "answer": fields.Str(required=True, data_key="RESULT"),
#     }
#     redis_key = "mock_htesb"
#
#     @use_kwargs(user_args, location="json")
#     async def post(self, file_id, answer, code, note):
#         status = self.check_header()
#         if not status:
#             return self.error("request header error", status_code=400)
#
#         rdb = init_rdb()
#         rdb.hset(self.redis_key, file_id, answer)
#         rdb.expire(self.redis_key, 60 * 60)
#         ret = {
#             "returnCode": 0,
#             "returnMsg": "success",
#             "code": code,
#             "note": note,
#         }
#         return self.data(ret)
#
#     def check_header(self):
#         header_info = self.request.headers
#         return "interfaceCode" in header_info and "consumerCode" in header_info
#
#     @use_kwargs({"file_id": fields.Str(required=True)}, location="query")
#     async def get(self, file_id):
#         rdb = init_rdb()
#         answer = rdb.hget(self.redis_key, file_id)
#         if not answer:
#             return self.error("file_id not found", status_code=400)
#         ret = {
#             "ID": file_id,
#             "RESULT": json.loads(answer),
#             "returnCode": 0,
#             "returnMsg": "success",
#         }
#         return self.data(ret)
#
#     @plugin.route(r"/json_answer/(?P<fid>\d+)")
#     class HtJsonAnswerHandler(DbQueryHandler):
#         @Auth("browse")
#
#         async def get(self, **kwargs):
#             fid = kwargs["fid"]
#             if int(fid) > 8888:
#                 # maybe this is a question id
#                 question = await NewQuestion.find_by_id(fid)
#             else:
#                 mold = await NewMold.find_by_name("私募类基金合同")
#                 question = await NewQuestion.find_by_fid_mid(fid, mold_id=mold.id)
#             if not question:
#                 return self.error(_("Answer not ready yet!"))
#             json_answer = await NewSpecialAnswer.get_answers(question.id, NewSpecialAnswer.ANSWER_TYPE_JSON, top=1)
#             if not json_answer:
#                 return self.error(_("Answer not ready yet!"))
#             data = json_answer[0].data
#             return self.data(data)
