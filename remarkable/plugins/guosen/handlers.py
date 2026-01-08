import base64
import http
import json
import logging
import os
import uuid
from collections import defaultdict
from functools import cached_property
from operator import attrgetter
from pathlib import Path

import numpy as np
from marshmallow import Schema, fields
from peewee import fn
from sklearn.cluster import KMeans
from sqlalchemy import and_, or_
from sqlalchemy.orm import Query
from tornado.httputil import HTTPFile

from remarkable.answer.common import is_empty_answer
from remarkable.answer.reader import AnswerReader
from remarkable.base_handler import Auth, BaseHandler
from remarkable.common.apispec_decorators import use_kwargs
from remarkable.common.constants import JSONConverterStyle, PDFParseStatus
from remarkable.common.diff.para_similarity import SimilarPara
from remarkable.converter import SimpleJSONConverter
from remarkable.db import pw_db
from remarkable.models.new_file import NewFile
from remarkable.plugins import Plugin, PostFileValidator
from remarkable.plugins.guosen.db import session_scope
from remarkable.plugins.guosen.models.external import DWDSecuInfo
from remarkable.plugins.guosen.service import GuosenFileService
from remarkable.pw_models.model import NewAnswer, NewMold
from remarkable.pw_models.question import NewQuestion

plugin = Plugin(Path(__file__).parent.name)

logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)


class ImageFileValidator(PostFileValidator):
    valid_suffixes = (".png", ".jpg", ".jpeg")


class UploadImageSchema(Schema):
    body: str = fields.String(data_key="image", load_default="")
    debug: bool = fields.Bool(load_default=False)
    match: bool = fields.Bool(load_default=True)
    use_kmeans: bool = fields.Bool(load_default=False)


@plugin.route(r"/images")
class ProjectFilesHandler(BaseHandler):
    @cached_property
    def detail(self) -> list:
        return []

    @cached_property
    def kmeans(self) -> KMeans:
        return KMeans(n_clusters=2, random_state=42)

    @Auth("browse")
    @use_kwargs(UploadImageSchema, location="form")
    @use_kwargs(
        {
            "post_files": fields.List(
                fields.Raw(validate=ImageFileValidator.check), data_key="file", load_default=list
            ),  # 用于测试使用
        },
        location="files",
    )
    async def post(self, body: str, debug: bool, match: bool, use_kmeans: bool, post_files: list[HTTPFile]):
        """
        g007001000: 股票
        g007009000: 指数
        g007002000: 基金
        g007003000: 债券
        """
        if post_files:
            post_file = post_files[0]
        else:
            post_file = HTTPFile(
                filename=uuid.uuid4().hex, body=base64.b64decode(body), content_type="application/octet-stream"
            )
        file = await GuosenFileService.create(post_file)
        pred_answer = await pw_db.scalar(
            NewQuestion.select(NewQuestion.answer).where(
                NewQuestion.fid == file.id,
                fn.EXISTS(NewMold.select(1).where(NewMold.name == "自选股", NewMold.id == NewQuestion.mold)),
            )
        )
        if pred_answer is None:
            return self.error("预测答案不存在", status_code=400)

        if pred_answer["userAnswer"]["items"]:
            pred_answer = SimpleJSONConverter(pred_answer).convert()
        else:
            pred_answer = {"日期": None, "详情": []}
        if match:
            stock, index, fund, bond = "g007001000", "g007009000", "g007002000", "g007003000"
            with session_scope() as session:
                logger.info("start to match for fixed code")
                query = session.query(DWDSecuInfo).filter(DWDSecuInfo.is_delete == "0")
                unmatched = list(self.match_for_fixed_code(query, pred_answer["详情"]))
                logger.info("finish to match for fixed code")
                query = query.filter(
                    or_(
                        DWDSecuInfo.sf_type_code.in_([stock, fund, bond]),
                        and_(
                            DWDSecuInfo.sf_type_code == index,
                            or_(
                                DWDSecuInfo.country_code.in_(["CN", "HK", "US", ""]),
                                DWDSecuInfo.country_code.is_(None),
                            ),
                        ),
                    ),
                )

                logger.info("start to match by code")
                unmatched = list(self.match_by_code(query, unmatched, use_kmeans))
                logger.info("finish to match by code")

                if unmatched:
                    logger.info("start to match by name")
                    unmatched = list(self.match_by_name(query, unmatched))
                    logger.info("finish to match by name")
        else:
            unmatched = pred_answer["详情"]

        # 如果都没有, 只返回提取答案中的资产情况
        for answer in unmatched:
            self.detail.append(
                {
                    "combCode": None,
                    "secuAbbr": None,
                    "exchangeCode": None,
                    "exchange": None,
                    "assetSituation": answer["资产情况"],
                    "answer": answer,
                }
            )

        if not debug:
            for answer in self.detail:
                answer.pop("answer")

        return self.data(
            {
                "file_id": file.id,
                "answer": [{"name": "日期", "item": pred_answer["日期"]}, {"name": "详情", "items": self.detail}],
            }
        )

    def match_for_fixed_code(self, query: Query, answers: list):
        """
        对这几个特殊的股票代码进行匹配时,取更新时间最新的第一条
        000510	中证A500
        000188	中国波指
        000929	800材料
        SPHKL	标普香港大型股
        000930	800工业
        SXXP	欧洲STOXX600(欧元)
        """
        dwd_records = query.filter(
            DWDSecuInfo.trading_code.in_(("000930", "SXXP", "000929", "000188", "000510", "SPHKL"))
        )

        dwd_record_by_code = defaultdict(list)
        for record in dwd_records:
            dwd_record_by_code[record.trading_code].append(record)
        for records in dwd_record_by_code.values():
            records.sort(key=attrgetter("u_time"), reverse=True)

        for answer in answers:
            records = dwd_record_by_code.get(answer["股票代码"], [])
            if not records:
                matched = []
            else:
                record = records[0]
                matched = [
                    {
                        "combCode": record.stock_code,
                        "secuAbbr": record.stock_abbr,
                        "exchangeCode": record.exchange_code,
                        "exchange": record.exchange,
                        "assetSituation": answer["资产情况"],
                        "answer": answer,
                    }
                ]
            if matched:
                self.detail.extend(matched)
            else:
                yield answer

    def match_by_code(self, query: Query, answers: list, use_kmeans: bool):
        """按照股票代码匹配, 精确匹配, 可能会匹配到多条, 按照股票名称或者股票简称相似度75%找到最相似的, 找不到则返回全部"""
        dwd_records = query.filter(
            DWDSecuInfo.trading_code.in_([answer["股票代码"] for answer in answers if answer["股票代码"] is not None]),
        )

        for answer in answers:
            records = [record for record in dwd_records if record.trading_code == answer["股票代码"]]
            matched = []
            logger.debug(f"{answer['股票代码']} -> {[(record.stock_abbr, record.stock_name) for record in records]}")
            scores = []
            for record in records:
                if not (stock_name := answer["股票名称"]):
                    score = 0
                elif record.stock_abbr and record.stock_name:
                    score = max(
                        SimilarPara.get_para_similarity(stock_name, record.stock_abbr),
                        SimilarPara.get_para_similarity(stock_name, record.stock_name),
                    )
                elif record.stock_abbr:
                    score = SimilarPara.get_para_similarity(stock_name, record.stock_abbr)
                elif record.stock_name:
                    score = SimilarPara.get_para_similarity(stock_name, record.stock_name)
                else:
                    score = 0
                scores.append(score)
                if score >= 0.75:
                    matched.append(
                        {
                            "combCode": record.stock_code,
                            "secuAbbr": record.stock_abbr,
                            "exchangeCode": record.exchange_code,
                            "exchange": record.exchange,
                            "assetSituation": answer["资产情况"],
                            "answer": answer,
                        }
                    )
                    break
            if not matched and use_kmeans and len(records) > 1:
                matched.extend(self.match_by_kmeans(answer, records, scores))
            # 如果匹配到名称和代码, 只返回一条
            if matched:
                self.detail.extend(matched)
                continue
            # 如果只匹配到代码, 返回所有数据库查到的数据
            if records:
                for record in records:
                    self.detail.append(
                        {
                            "combCode": record.stock_code,
                            "secuAbbr": record.stock_abbr,
                            "exchangeCode": record.exchange_code,
                            "exchange": record.exchange,
                            "assetSituation": answer["资产情况"],
                            "answer": answer,
                        }
                    )
            else:
                yield answer

    def match_by_kmeans(self, answer: dict, records: list[DWDSecuInfo], scores: list[float]):
        # 通过kmeans用分数来将匹配到的记录分成两组, 如果分数高的组中只有一条记录, 就返回这条记录
        points = np.array([[score] for score in scores])
        self.kmeans.fit(points)
        record_by_label = defaultdict(list)
        for index, label in enumerate(self.kmeans.labels_):
            record_by_label[label].append(index)
        for indices in record_by_label.values():
            if len(indices) == 1 and scores[indices[0]] == np.max(points):
                record = records[indices[0]]
                yield {
                    "combCode": record.stock_code,
                    "secuAbbr": record.stock_abbr,
                    "exchangeCode": record.exchange_code,
                    "exchange": record.exchange,
                    "assetSituation": answer["资产情况"],
                    "answer": answer,
                }
                return

    def match_by_name(self, query: Query, answers: list):
        names = [answer["股票名称"] for answer in answers if answer["股票名称"] is not None]
        dwd_records = query.filter(or_(DWDSecuInfo.stock_abbr.in_(names), DWDSecuInfo.stock_name.in_(names)))
        for answer in answers:
            matched = []
            for record in dwd_records:
                if answer["股票名称"] in (record.stock_abbr, record.stock_name):
                    logger.debug(f"{answer['股票名称']} -> {record.stock_abbr, record.stock_name}")
                    matched.append(
                        {
                            "combCode": record.stock_code,
                            "secuAbbr": record.stock_abbr,
                            "exchangeCode": record.exchange_code,
                            "exchange": record.exchange,
                            "assetSituation": answer["资产情况"],
                            "answer": answer,
                        }
                    )

            if matched:
                self.detail.extend(matched)
            else:
                yield answer

    def match_by_similarity(self, query: Query, answers: list):
        dwd_records = query.all()
        # 遍历所有数据库数据, 匹配名称
        for answer in answers:
            matched = []
            for record in dwd_records:
                if not (stock_name := answer.get("股票名称")):
                    continue
                if (record.stock_abbr and SimilarPara.get_para_similarity(stock_name, record.stock_abbr) >= 0.75) or (
                    record.stock_name and SimilarPara.get_para_similarity(stock_name, record.stock_name) >= 0.75
                ):
                    matched.append(
                        {
                            "combCode": record.stock_code,
                            "secuAbbr": record.stock_abbr,
                            "exchangeCode": record.exchange_code,
                            "exchange": record.exchange,
                            "assetSituation": answer["资产情况"],
                            "answer": answer,
                        }
                    )
            if matched:
                self.detail.extend(matched)
            else:
                yield answer


class GetResultSchema(Schema):
    mold: int = fields.Int(load_default=0)


@plugin.route(r"/files/(?P<file_id>\d+)/result/json")
class ExportAnswerHandler(BaseHandler):
    @Auth("browse")
    @use_kwargs(GetResultSchema, location="query")
    async def get(self, file_id: int, mold: int):
        if not (file := await NewFile.find_by_id(file_id)):
            return self.error(_("Item Not Found"), http.HTTPStatus.NOT_FOUND)
        if file.pdf_parse_status != PDFParseStatus.COMPLETE:
            return self.error(_("The file is being processed, please try again later"), http.HTTPStatus.ACCEPTED)

        questions = []
        if mold:
            if question := await NewQuestion.find_by_fid_mid(file.id, mold):
                questions.append(question)
        else:
            questions = await NewQuestion.find_by_fid(file.id)
        if not questions:
            return self.error(_("Item Not Found"), http.HTTPStatus.NOT_FOUND)

        answers = await self.get_result(questions)
        file_name = f"{os.path.splitext(file.name)[0]}.json"
        data = json.dumps(answers, ensure_ascii=False, indent=4)
        data = bytes(data, "utf-8")
        if not data:
            return self.error(_("data not ready"), http.HTTPStatus.ACCEPTED)

        return await self.export(data, file_name)

    async def get_result(self, questions: list[NewQuestion]):
        answers = {}
        users = []
        updated_time = await pw_db.scalar(
            NewAnswer.select(
                fn.MAX(NewAnswer.updated_utc),
            ).where(NewAnswer.qid.in_([question.id for question in questions]))
        )
        for question in questions:
            if is_empty_answer(question.answer):
                continue
            users.extend(question.mark_users)
            answer_reader = AnswerReader(question.answer)
            answers[answer_reader.mold_name] = answer_reader.to_json(
                JSONConverterStyle.PLAIN_TEXT, item_handler=lambda x: x.origin_text
            )
        return {
            "answers": answers,
            "user": users[-1] if users else None,
            "updated_time": updated_time,
        }
