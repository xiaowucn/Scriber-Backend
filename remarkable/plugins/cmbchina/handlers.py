# CYC: build-with-nuitka
import http
import logging
from pathlib import PurePath

import httpx
from marshmallow import fields
from speedy.peewee_plus import orm

from remarkable.base_handler import Auth, BaseHandler
from remarkable.common.apispec_decorators import use_kwargs
from remarkable.common.exceptions import CustomError
from remarkable.common.redis_cache import QUESTION_POST_PIPE_KEY
from remarkable.config import get_config
from remarkable.converter.cmbchina import CMBChinaConverter
from remarkable.db import init_rdb, pw_db
from remarkable.models.cmbchina import AuditAnswer
from remarkable.models.new_file import NewFile
from remarkable.plugins import Plugin
from remarkable.pw_models.model import MoldWithFK
from remarkable.pw_models.question import QuestionWithFK

plugin = Plugin(PurePath(__file__).parent.name)
logger = logging.getLogger(__name__)


@plugin.route(r"/files/(\d+)/answer")
class FileAnswerHandler(BaseHandler):
    get_args = {"mold": fields.Int(load_default=0)}

    @Auth("browse")
    @use_kwargs(get_args, location="query")
    async def get(self, fid: str, mold: int):
        questions = await pw_db.prefetch(
            QuestionWithFK.select(QuestionWithFK.answer, QuestionWithFK.fid, QuestionWithFK.mold)
            .where(
                QuestionWithFK.fid == fid,
                QuestionWithFK.mold == mold if mold > 0 else orm.TRUE,
            )
            .order_by(QuestionWithFK.id),
            MoldWithFK.select(),
        )
        file = await NewFile.get_by_id(fid)
        answers = []
        for question in questions:
            converter = CMBChinaConverter(question)
            answer = converter.convert()
            answer["schema_id"] = question.mold.id
            answers.append(answer)
        return self.data(
            {
                "answers": answers,
                "user": {"id": self.current_user.id, "name": self.current_user.name},
                "file_id": str(fid),
                "tree_id": str(file.tree_id),
                "schema_ids": [q.mold.id for q in questions],
            }
        )


def sort_field(product_info: dict):
    info_type = product_info["infoType"]
    if info_type == "basic":
        return 0, product_info.get("fieldOrder", 0)
    elif info_type == "limit":
        return 1, product_info.get("fieldOrder", 0)
    elif info_type == "fee":
        return 2, product_info.get("fieldOrder", 0)
    else:
        return 3, product_info.get("fieldOrder", 0)


@plugin.route(r"/files/(\d+)/audit-answer")
class AuditAnswerHandler(BaseHandler):
    get_args = {
        "product_code": fields.Str(data_key="productCode", allow_none=True),
    }

    @Auth("browse")
    @use_kwargs(get_args, location="query")
    async def get(self, fid: str, product_code: str):
        qid = await pw_db.scalar(QuestionWithFK.select(QuestionWithFK.id).where(QuestionWithFK.fid == fid))
        async with httpx.AsyncClient(transport=httpx.AsyncHTTPTransport(retries=3)) as client:
            rsp = await client.post(
                get_config("cmbchina.answer_pull_api"),
                headers={"Authorization": f"Basic {get_config('cmbchina.basic_auth')}"},
                json={
                    "productCode": product_code,
                    "optType": "detail",
                    "fileId": str(fid),
                },
            )
            answer = rsp.json()
        answer["data"]["productInfo"].sort(key=sort_field)
        await AuditAnswer().insert_or_update(
            conflict_target=[AuditAnswer.fid, AuditAnswer.product_code],
            **{"fid": fid, "product_code": product_code, "answer": answer["data"]},
        )
        return self.data({"qid": qid, **answer["data"]})


@plugin.route(r"/questions/(\d+)/submit")
class QuestionAnswerHandler(BaseHandler):
    put_args = {
        "product_code": fields.Str(),
        "zyt_answer": fields.Dict(),
        "answer": fields.Dict(),
    }

    @Auth("browse")
    @use_kwargs(put_args, location="json")
    async def post(self, qid: str, product_code: str, zyt_answer: dict, answer: dict):
        question = await QuestionWithFK.find_by_id(int(qid), prefetch_queries=[NewFile.select()])
        if not question:
            return self.error("question not found", status_code=http.HTTPStatus.NOT_FOUND)
        if init_rdb().exists(f"lock:{QUESTION_POST_PIPE_KEY.format(qid=qid)}"):
            return self.error("提交答案过于频繁, 请稍后重试", status_code=http.HTTPStatus.BAD_REQUEST)
        file = question.file
        zyt_answer.pop("qid", None)

        async with pw_db.atomic():
            await pw_db.execute(
                AuditAnswer.delete().where(AuditAnswer.fid == file.id, AuditAnswer.product_code == product_code)
            )
            await pw_db.create(AuditAnswer, **{"fid": file.id, "product_code": product_code, "answer": zyt_answer})

            push_api = get_config("cmbchina.answer_update_api")
            async with httpx.AsyncClient(timeout=get_config("cmbchina.submit_timeout")) as client:
                logger.info("start to commit answer to cmbchina")
                try:
                    rsp = await client.post(
                        push_api,
                        headers={"Authorization": f"Basic {get_config('cmbchina.basic_auth')}"},
                        json=zyt_answer,
                    )
                    body = rsp.json()
                except Exception as e:
                    raise Exception("fail to commit answer to cmbchina") from e
                finally:
                    logger.info("end to commit answer to cmbchina")
            if body["returnCode"].upper() != "SUC0000":
                raise CustomError(body["message"], resp_status_code=http.HTTPStatus.BAD_REQUEST)
        return self.data(None)
