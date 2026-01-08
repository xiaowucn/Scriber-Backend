import collections
import hashlib
import logging
import os
from copy import deepcopy

import asyncpg
import httpx
from marshmallow import fields
from utensils.auth.token import encode_url

from remarkable.answer.reader import AnswerReader
from remarkable.base_handler import Auth, DbQueryHandler
from remarkable.common.apispec_decorators import use_kwargs
from remarkable.common.diff import calliper_diff
from remarkable.common.exceptions import CustomError
from remarkable.common.storage import localstorage
from remarkable.common.util import run_singleton_task
from remarkable.config import get_config
from remarkable.models.new_file import NewFile
from remarkable.plugins.diff import plugin
from remarkable.plugins.diff.common import add_url, get_cache_for_diff, utc_now
from remarkable.plugins.diff.constants import CompareStatus, DocStatus, DocType
from remarkable.plugins.diff.tasks import clean_up, doc2pdf, push2calliper
from remarkable.pw_models.model import NewAnswer, NewDiffFile, NewDiffRecord
from remarkable.pw_models.question import NewQuestion
from remarkable.worker.tasks import gen_cache_for_diff_task

logger = logging.getLogger(__name__)


@plugin.route(r"/doc/(?P<fid>\d+)")
class DocDiffHandler(DbQueryHandler):
    @Auth("remark")
    async def post(self, **kwargs):
        """接收文件上传或内部文件id, 后台执行转换,推送,刷新diff状态等"""
        uid = self.current_user.id
        fid1 = int(kwargs["fid"])
        file_metas = self.request.files.get("file")
        cookies = {key: self.cookies[key].value for key in self.cookies}
        if file_metas:
            # 上传新文档进行对比
            _hash = hashlib.md5(file_metas[0]["body"]).hexdigest()
            file_name = file_metas[0]["filename"]
            file_path = localstorage.mount(os.path.join(_hash[:2], _hash[2:]))
            if not localstorage.exists(file_path):
                localstorage.write_file(file_path, file_metas[0]["body"])

            try:
                file2 = await NewDiffFile.create(
                    **{
                        "uid": uid,
                        "name": file_name,
                        "hash": _hash,
                        "pdf_hash": _hash if file_name.split(".")[-1].lower() == "pdf" else "",
                        "status": DocStatus.CREATED.value,
                    },
                )
            except asyncpg.UniqueViolationError:
                # 返回重复文件
                file2 = await NewDiffFile.find_by_kwargs(uid=uid, hash=_hash)

            try:
                diff_record = await NewDiffRecord.create(
                    **{
                        "uid": uid,
                        "fid1": fid1,
                        "fid2": file2.id,
                        "name2": file_name,
                        "type": DocType.OUTER.value,
                        "status": CompareStatus.CREATED.value,
                    },
                )
            except asyncpg.UniqueViolationError:
                # 返回重复比对记录
                diff_record = await NewDiffRecord.find_by_kwargs(uid=uid, fid1=fid1, fid2=file2.id)

            if file2.status != DocStatus.CONVERTED.value:
                _file = file2.to_dict()
                _file["path"] = file2.path()
                doc2pdf.apply_async(
                    (_file,),
                    link=[push2calliper.si(diff_record.to_dict(), cookies), clean_up.si(diff_record.to_dict())],
                )
        else:
            # 选择系统内已上传文件进行对比
            try:
                fid2 = int(self.get_argument("fid"))
            except (TypeError, ValueError):
                raise CustomError(_("Invalid file id detected")) from Exception

            try:
                diff_record = await NewDiffRecord.create(
                    **{
                        "uid": uid,
                        "fid1": fid1,
                        "fid2": fid2,
                        "type": DocType.INNER.value,
                        "status": CompareStatus.CREATED.value,
                    },
                )
            except asyncpg.UniqueViolationError:
                # 返回重复比对记录
                diff_record = await NewDiffRecord.find_by_kwargs(uid=uid, fid1=fid1, fid2=fid2)

            if diff_record.status not in (CompareStatus.COMPARING.value, CompareStatus.DONE.value):
                push2calliper.apply_async(
                    (diff_record.to_dict(), cookies, True), link=clean_up.si(diff_record.to_dict())
                )

        return self.data(diff_record.to_dict())

    @Auth("remark")
    async def get(self, **kwargs):
        """获取文档对比记录"""
        # manage_user权限用户可以获取该文档所有用户比对记录
        uid = None if any(i["perm"] == "manage_user" for i in self.current_user.permission) else self.current_user.id
        fid1 = int(kwargs["fid"])
        _type = self.get_argument("type", default="outer")
        if _type == "outer":
            diff_records = await NewDiffRecord.find_by_kwargs("all", uid=uid, fid1=fid1, type=DocType.OUTER.value)
        elif _type == "inner":
            diff_records = await NewDiffRecord.find_by_kwargs("all", uid=uid, fid1=fid1, type=DocType.INNER.value)
        else:
            return self.error(_("Unsupported doc type, valid value: outer or inner"))

        return self.data(add_url(diff_records))


@plugin.route(r"/(?P<cmp_id>\d+)/status")
class CheckStatusHandler(DbQueryHandler):
    @Auth("browse")
    async def post(self, **kwargs):
        """接收callback通知, 更新比对任务状态"""
        cmp_id = int(kwargs["cmp_id"])
        status = int(self.get_argument("compare_status"))
        total_diff = int(self.get_argument("total_diff", default=-1))
        if status in (CompareStatus.DONE.value, CompareStatus.FAILED.value):
            await NewDiffRecord.update_by_pk(cmp_id, total_diff=total_diff, status=status, updated_utc=utc_now())
        return self.data({})

    @Auth("remark")
    async def get(self, **kwargs):
        """查询比对任务状态"""
        cmp_id = int(kwargs["cmp_id"])

        ret = await NewDiffRecord.find_by_kwargs(id=cmp_id, status=CompareStatus.DONE.value)
        if ret:
            return self.data(add_url([ret.to_dict()])[0])
        return self.error(_("Compare task not complete yet"))


@plugin.route(r"/question/(?P<question_id>\d+)/diff")
class ModelStatHandler(DbQueryHandler):
    @Auth("browse")
    @use_kwargs({"standard_qid": fields.Int(required=True)}, location="query")
    async def get(self, **kwargs):
        question_id = int(kwargs["question_id"])
        answers = await NewAnswer.get_answers_by_qid_uid(question_id, self.current_user.id)
        diff_question = await NewQuestion.find_by_id(question_id)
        standard_question = await NewQuestion.find_by_id(kwargs["standard_qid"])
        if not diff_question or not standard_question:
            raise CustomError(_("not found file"))
        if diff_question.mold != standard_question.mold:
            raise CustomError(_("Mold is not the same"))
        diff_answer = diff_question.answer
        standard_answer = standard_question.answer
        if answers:  # 优先用当前用户的答案,但自定义字段用合并答案里的
            label_answer = answers.data
            label_answer["custom_field"] = diff_answer.get("custom_field", {})
            diff_answer = label_answer
        if not diff_answer or not standard_answer:
            raise CustomError(_("Answer not ready yet!"))

        diff_answer_dict = AnswerReader(diff_answer).to_tile_dict(include_custom=True)
        standard_answer_dict = AnswerReader(standard_answer).to_tile_dict(include_custom=True)

        diff_file = await NewFile.find_by_qid(question_id)
        standard_file = await NewFile.find_by_qid(kwargs["standard_qid"])

        diff_pdfinsight = get_cache_for_diff(diff_file)
        standard_pdfinsight = get_cache_for_diff(standard_file)

        if not diff_pdfinsight:
            run_singleton_task(gen_cache_for_diff_task, diff_question.id, lock_key=f"gen_ccxi_cache_{diff_question.id}")
        if not standard_pdfinsight:
            run_singleton_task(
                gen_cache_for_diff_task, standard_question.id, lock_key=f"gen_ccxi_cache_{standard_question.id}"
            )

        if not diff_pdfinsight or not standard_pdfinsight:
            raise CustomError("文件对比缓存正在生成，请稍后再试")

        await self.run_in_executor(
            self.find_diff_result, diff_answer_dict, standard_answer_dict, diff_pdfinsight, standard_pdfinsight
        )

        return self.data(
            {
                "standard_answer": list(standard_answer_dict.values()),
                "diff_answer": list(diff_answer_dict.values()),
            }
        )

    def find_diff_result(self, diff_answer_dict, standard_answer_dict, diff_pdfinsight, standard_pdfinsight):
        fake_template = {"data": [], "value": "", "marker": {}, "detail": {}, "diff_result": False, "is_fake": True}
        diff_detail_map = {}

        for key, item in diff_answer_dict.items():
            if key in standard_answer_dict:
                result, left_res, right_res = self.diff_two_items(key, diff_pdfinsight, standard_pdfinsight)
                diff_detail_map[key] = right_res
                item["diff_result"] = not result
                item["detail"] = left_res
            else:
                item["diff_result"] = False
                fake_item = deepcopy(item)
                fake_item.update(fake_template)
                fake_item["detail"] = [f"缺少{item['schema']['data']['label']}字段"]
                standard_answer_dict.setdefault(key, fake_item)

        for key, item in standard_answer_dict.items():
            if key in diff_answer_dict:
                diff_result = diff_answer_dict[key]["diff_result"]
                item["diff_result"] = diff_answer_dict[key]["diff_result"]
                if not diff_result and diff_detail_map.get(key):
                    item["detail"] = diff_detail_map[key]
            else:
                item["diff_result"] = False
                fake_item = deepcopy(item)
                fake_item.update(fake_template)
                fake_item["detail"] = [f"缺少{item['schema']['data']['label']}字段"]
                diff_answer_dict.setdefault(key, fake_item)

    @staticmethod
    def diff_two_items(key, diff_pdfinsight, standard_pdfinsight):
        # TODO: Calliper SDK 有变更，此方法可用性待确认，需要增加单元测试。
        diff_interdoc = diff_pdfinsight.get(key)
        standard_interdoc = standard_pdfinsight.get(key)
        if not diff_interdoc or not standard_interdoc:
            return False, {}, {}
        diff_res = calliper_diff(diff_interdoc, standard_interdoc)
        left_res = collections.defaultdict(list)
        right_res = collections.defaultdict(list)
        for item in diff_res:
            for page, value in item["left_box"].items():
                left_res[page].extend(value)
            for page, value in item["right_box"].items():
                right_res[page].extend(value)
        return bool(diff_res), left_res, right_res


@plugin.route(r"/calliper/diff/upload")
class CalliperDiffHandler(DbQueryHandler):
    args_schema = {
        "file_id_1": fields.Int(required=True),
        "file_id_2": fields.Int(required=True),
    }

    @use_kwargs(args_schema, location="json")
    async def post(self, file_id_1, file_id_2):
        file_1 = await NewFile.find_by_id(file_id_1)
        file_2 = await NewFile.find_by_id(file_id_2)
        if not (file_1 and file_2):
            return self.error("not found file", status_code=404)
        success, cmp_id = await self.compare_docs(file_1, file_2)
        if not success:
            return self.error(f"compare doc error, doc_ids: {file_id_1} with {file_id_2}")
        calliper_url = f"/api/v1/get-off?sys=calliper&origin=/#/projectList?cmp_id={cmp_id}"
        return self.data({"calliper_url": calliper_url})

    @classmethod
    async def compare_docs(cls, left, right):
        left_file = localstorage.read_file(left.pdf_path())
        right_file = localstorage.read_file(right.pdf_path())
        files = {"file1": (left.name, left_file), "file2": (right.name, right_file)}
        url = (get_config("app.auth.calliper.url") or "") + (get_config("app.auth.calliper.compare_api") or "")
        async with httpx.AsyncClient(verify=False, timeout=30) as client:
            try:
                response = await client.post(cls.auth_compare(url), files=files)
                if response.status_code // 200 != 1:
                    logger.error(f"compare doc error, doc_ids: {left.id} with {right.id}")
                    logger.error(response.text)
                    return False, None
                cmp_id = response.json()["data"]["cmp_id"]
                return True, cmp_id
            except Exception as exp:
                logger.exception(exp)

            return False, None

    @staticmethod
    def auth_compare(api, params=None):
        app_id = get_config("app.auth.calliper.app_id")
        secret_key = get_config("app.auth.calliper.secret_key")
        exclude_domain = get_config("app.auth.calliper.exclude_domain") or False
        return encode_url(api, app_id, secret_key, params, exclude_domain=exclude_domain)
