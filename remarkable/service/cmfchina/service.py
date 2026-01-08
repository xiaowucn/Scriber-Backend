import datetime
import json
import logging
from collections import defaultdict
from copy import deepcopy
from dataclasses import asdict, dataclass, field
from itertools import groupby

import peewee
import speedy
from peewee import JOIN, fn
from speedy.peewee_plus.orm import and_, or_
from tornado.httputil import HTTPFile

from remarkable.checker.cgs_checker.checker import get_updated_rule_labels
from remarkable.checker.helpers import audit_file_rules_by_mold
from remarkable.common.constants import (
    CmfFiledStatus,
    CommonStatus,
    PDFParseStatus,
    RuleID,
    RuleType,
    TimeType,
)
from remarkable.common.datetime_util import gen_day_ranges, gen_month_ranges_data, group_by_date
from remarkable.common.enums import AuditAnswerType, CountType, FieldStatus, ReviewedType, TaskType
from remarkable.common.util import compact_dumps, run_singleton_task
from remarkable.db import pw_db
from remarkable.models.cmf_china import (
    CmfChinaEmail,
    CmfFiledFileInfo,
    CmfFileReviewed,
    CmfModel,
    CmfModelAuditAccuracy,
    CmfModelUsageCount,
    CmfMoldFieldRef,
    CmfMoldModelRef,
    CmfUserCheckFields,
)
from remarkable.models.new_file import NewFile
from remarkable.models.new_user import NewAdminUser
from remarkable.models.query_helper import AsyncPagination
from remarkable.predictor.mold_schema import MoldSchema
from remarkable.pw_models.answer_data import NewAnswerData, NewAnswerDataStat
from remarkable.pw_models.audit_rule import NewAuditResult, NewAuditRule
from remarkable.pw_models.base import ScriberModelSelect, to_sql
from remarkable.pw_models.model import (
    MoldWithFK,
    NewFileProject,
    NewFileTree,
    NewMold,
    NewMoldField,
)
from remarkable.pw_models.question import NewQuestion
from remarkable.schema.cmfchina.schema import CmfAnswerDataAdd, CmfAnswerDataDelete, CmfAnswerDataUpdate
from remarkable.service.cmfchina.cmf_file import CmfFileService
from remarkable.service.cmfchina.common import (
    CMF_CHINA_FILED_FILE_PROJECT_NAME,
    CMF_CHINA_VERIFY_FILED_PROJECT_NAME,
)
from remarkable.service.mold_field import MoldFieldService
from remarkable.service.new_file import NewFileService
from remarkable.service.new_file_project import NewFileProjectService
from remarkable.service.new_question import NewQuestionService
from remarkable.worker.tasks import preset_answers_for_mold_online

logger = logging.getLogger(__name__)


@dataclass
class AuditStatisticRecord:
    total: int = 0
    compliance_count: int = 0
    rules: dict = field(default_factory=dict)

    def add_up(self, record: dict):
        self.total += record["total"]
        self.compliance_count += record["compliance_count"]

        original_data = self.rules
        new_data = record["rules"]

        for rule_name in new_data:
            if rule_name in original_data:
                original_data[rule_name]["total"] += new_data[rule_name]["total"]
                original_data[rule_name]["compliance_count"] += new_data[rule_name]["compliance_count"]
                if "rule_total" in original_data[rule_name] or "rule_total" in new_data[rule_name]:
                    original_rule_total = original_data[rule_name].get("rule_total", 0)
                    new_rule_total = new_data[rule_name].get("rule_total", 0)
                    original_data[rule_name]["rule_total"] = original_rule_total + new_rule_total
            else:
                original_data[rule_name] = new_data[rule_name]

    @staticmethod
    def _merge_new_rules(original_data, new_data):
        for rule_name in new_data:
            if rule_name in original_data:
                original_data[rule_name]["total"] += new_data[rule_name]["total"]
                original_data[rule_name]["compliance_count"] += new_data[rule_name]["compliance_count"]
            else:
                original_data[rule_name] = {
                    "total": new_data[rule_name]["total"],
                    "compliance_count": new_data[rule_name]["compliance_count"],
                }

    def __add__(self, other):
        record = AuditStatisticRecord(total=0, compliance_count=0, rules={})
        record.total = self.total + other.total
        record.compliance_count = self.compliance_count + other.compliance_count
        copied_rules = deepcopy(self.rules)
        self._merge_new_rules(copied_rules, other.rules)
        record.rules = copied_rules

        return record


@dataclass
class DayAuditStatistic:
    internal: AuditStatisticRecord
    external: AuditStatisticRecord
    preset_answer: AuditStatisticRecord
    answer: AuditStatisticRecord

    @classmethod
    def default(cls):
        return cls(
            internal=AuditStatisticRecord(),
            external=AuditStatisticRecord(),
            preset_answer=AuditStatisticRecord(),
            answer=AuditStatisticRecord(),
        )

    @classmethod
    def aggregate(cls, audit_results):
        statistical_record = AuditStatisticRecord(total=0, compliance_count=0, rules=defaultdict(dict))
        for audit_result in audit_results:
            for rule in audit_result.schema_results:
                statistical_record.total += 1
                if audit_result.is_compliance:
                    statistical_record.compliance_count += 1

                rule = statistical_record.rules[rule["name"]]
                total = rule.setdefault("total", 0)
                compliance_count = rule.setdefault("compliance_count", 0)
                if audit_result.is_compliance:
                    compliance_count += 1
                total += 1

                rule["total"] = total
                rule["compliance_count"] = compliance_count

        return statistical_record

    @classmethod
    def from_audit_results(cls, audit_results):
        internal_record = AuditStatisticRecord(total=0, compliance_count=0, rules={})
        external_record = AuditStatisticRecord(total=0, compliance_count=0, rules={})
        preset_answer_record = AuditStatisticRecord(total=0, compliance_count=0, rules={})

        sorted_items = sorted(audit_results, key=lambda x: x.answer_type)
        for answer_type, group_items in groupby(sorted_items, lambda x: x.answer_type):
            if answer_type == AuditAnswerType.preset_answer:
                preset_answer_record = cls.aggregate(group_items)
            else:
                group_items = [i for i in group_items if i.reviewed]
                group_items.sort(key=lambda x: x.rule_type == RuleType.EXTERNAL.value)
                for is_external, rule_audit_results in groupby(
                    group_items, lambda x: x.rule_type == RuleType.EXTERNAL.value
                ):
                    if is_external:
                        external_record = cls.aggregate(rule_audit_results)
                    else:
                        internal_record = cls.aggregate(rule_audit_results)

        answer_record = internal_record + external_record
        for record in [internal_record, external_record]:
            for rule_name, data in record.rules.items():
                data["rule_total"] = data["total"]
                data["total"] = answer_record.rules[rule_name]["total"]
        return cls(
            internal=internal_record,
            external=external_record,
            preset_answer=preset_answer_record,
            answer=answer_record,
        )


class CmfChinaService:
    BASIC_TYPES = ["文本", "数字", "日期"]

    @classmethod
    async def get_pagination_projects(
        cls,
        name: str,
        iid: int,
        user_name: str,
        mid: int | None,
        start_at: int,
        end_at: int,
        order_by: str,
        page: int,
        size: int,
        file_tree_ids: list[int] = None,
    ):
        cond = NewFileProject.visible
        query = NewFileProject.select(NewFileProject, NewAdminUser.name.alias("user_name"))
        if user_name:
            query = query.join(
                NewAdminUser,
                on=and_(NewAdminUser.id == NewFileProject.uid, NewAdminUser.name.contains(user_name)),
                include_deleted=True,
            )
        else:
            query = query.join(
                NewAdminUser,
                peewee.JOIN.LEFT_OUTER,
                on=(NewAdminUser.id == NewFileProject.uid),
                include_deleted=True,
            )
        if mid is not None:
            query = query.join(
                NewFile, join_type=JOIN.LEFT_OUTER, on=(NewFile.pid == NewFileProject.id), include_deleted=True
            ).join(
                NewFileTree, join_type=JOIN.LEFT_OUTER, on=(NewFileTree.pid == NewFileProject.id), include_deleted=True
            )
            cond &= or_(
                NewFile.molds.contains(mid),
                NewFileTree.default_molds.contains(mid),
                NewFileProject.default_molds.contains(mid),
            )

        if file_tree_ids is not None:
            cond &= NewFileProject.rtree_id.in_(file_tree_ids)

        query = (
            query.where(cond).order_by(getattr(NewFileProject, order_by)).group_by(NewFileProject.id, NewAdminUser.name)
        )

        query = CmfChinaService.gen_pagination_query(
            query, name, [iid] if iid else [], [], TimeType.CREATE, start_at, end_at, page, size
        )
        data = await AsyncPagination(query.dicts(), page=page, size=size).data()
        return data

    @classmethod
    async def get_pagination_models(
        cls,
        name: str,
        iid: int,
        user_name: str,
        start_at: int,
        end_at: int,
        order_by: str,
        page: int,
        size: int,
    ):
        subquery = (
            CmfMoldModelRef.select(
                CmfMoldModelRef.model_id,
                fn.JSONB_AGG(
                    fn.JSONB_BUILD_OBJECT(
                        "mold_id",
                        MoldWithFK.id,
                        "mold_name",
                        MoldWithFK.name,
                    )
                ).alias("molds"),
            )
            .join(MoldWithFK, on=(CmfMoldModelRef.mold == MoldWithFK.id))
            .group_by(CmfMoldModelRef.model_id)
            .order_by(CmfMoldModelRef.model_id)
            .alias("subquery")
        )
        query = (
            CmfModel.select(
                CmfModel.id,
                CmfModel.name,
                CmfModel.address,
                CmfModel.intro,
                CmfModel.usage,
                CmfModel.created_utc,
                peewee.Case(
                    None,
                    [
                        (subquery.c.molds.is_null(True), peewee.SQL("'[]'::jsonb")),
                    ],
                    default=subquery.c.molds,
                ).alias("molds"),
                NewAdminUser.name.alias("user_name"),
            )
            .join(subquery, join_type=JOIN.LEFT_OUTER, on=(CmfModel.id == subquery.c.model_id))
            .order_by(getattr(CmfModel, order_by))
        )
        if user_name:
            query = query.join(
                NewAdminUser,
                on=and_(NewAdminUser.id == CmfModel.uid, NewAdminUser.name.contains(user_name)),
                include_deleted=True,
            )
        else:
            query = query.join(
                NewAdminUser, join_type=JOIN.LEFT_OUTER, on=(NewAdminUser.id == CmfModel.uid), include_deleted=True
            )
        query = CmfChinaService.gen_pagination_query(
            query, name, [iid] if iid else [], [], TimeType.CREATE, start_at, end_at, page, size
        )
        data = await AsyncPagination(query.dicts(), page=page, size=size).data()
        return data

    @classmethod
    async def get_pagination_pro_files(
        cls,
        name: str,
        iid: int,
        user_name: str,
        start_at: int,
        end_at: int,
        order_by: str,
        _type: TimeType,
        pdf_parse_status: int,
        ai_status: int,
        pid: int,
        page: int,
        size: int,
        tree_ids: list[int] = None,
        mold_ids: list[int] = None,
        search_mid: int = None,
    ):
        query = CmfFileService.file_query(
            pid=pid,
            filename=name,
            user_name=user_name,
            fileid=iid,
            time_type=_type,
            start_at=start_at,
            end_at=end_at,
            order_by=order_by,
            pdf_parse_status=pdf_parse_status,
            ai_status=ai_status,
            tree_ids=tree_ids,
            mold_ids=mold_ids,
            search_mid=search_mid,
        )
        res = await AsyncPagination(query.dicts(), page=page, size=size).data(
            dump_func=cls.packer,
        )
        res = await cls.append_questions(res)
        return res

    @staticmethod
    def packer(row, fields):
        row["pid"] = row.pop("project")
        return row

    @staticmethod
    async def get_pagination_mold_pro_files(name, page: int, size: int):
        # TODO 后续添加权限
        # 获取关联场景和工程的文件
        query = (
            NewFile.select()
            .join(
                NewFileProject,
                on=and_(
                    NewFileProject.id == NewFile.pid,
                    NewFileProject.visible,
                ),
            )
            .where(
                fn.ARRAY_LENGTH(NewFile.molds, 1) > 0,
                NewFile.pid.is_null(False),
                NewFile.pdf_parse_status == PDFParseStatus.COMPLETE,
            )
            .order_by(NewFile.id.desc())
        )
        if name:
            query = query.where(NewFile.name.contains(name))
        data = await AsyncPagination(query.dicts(), page=page, size=size).data()
        return data

    @classmethod
    async def get_pagination_schema(
        cls,
        name: str,
        iid: int,
        user_name: str,
        start_at: int,
        end_at: int,
        order_by: str,
        _type: TimeType,
        alias: str,
        page: int,
        size: int,
        mold_ids: list[int] = None,
    ):
        query = (
            MoldWithFK.select(MoldWithFK, NewAdminUser.name.alias("user_name"))
            .order_by(getattr(MoldWithFK, order_by))
            .dicts()
        )
        if user_name:
            query = query.join(
                NewAdminUser,
                on=and_(NewAdminUser.id == MoldWithFK.uid, NewAdminUser.name.contains(user_name)),
                include_deleted=True,
            )
        else:
            query = query.join(
                NewAdminUser, join_type=JOIN.LEFT_OUTER, on=(NewAdminUser.id == MoldWithFK.uid), include_deleted=True
            )

        cond = speedy.peewee_plus.orm.TRUE
        if alias:
            cond &= fn.json_extract_path_text(MoldWithFK.data, "schemas", "0", "alias").contains(alias)
        if mold_ids is not None:
            cond &= MoldWithFK.id.in_(mold_ids)
        query = query.where(cond)
        query = CmfChinaService.gen_pagination_query(
            query, name, [iid] if iid else [], [], _type, start_at, end_at, page, size
        )
        data = await AsyncPagination(query.dicts(), page=page, size=size).data()
        return data

    @staticmethod
    def gen_pagination_query(
        query: peewee.ModelSelect,
        name: str | None,
        in_ids: list,
        not_ids: list,
        _type: TimeType,
        start_at: int,
        end_at: int,
        page: int,
        size: int,
    ):
        if name:
            query = query.where(query.model.name.contains(name))
        if in_ids:
            query = query.where(query.model.id.in_(in_ids))
        if not_ids:
            query = query.where(query.model.id.not_in(not_ids))
        if _type == TimeType.CREATE:
            if start_at:
                query = query.where(query.model.created_utc >= start_at)
            if end_at:
                query = query.where(query.model.created_utc < end_at)
        else:
            if start_at:
                query = query.where(query.model.updated_utc >= start_at)
            if end_at:
                query = query.where(query.model.updated_utc < end_at)
        logger.debug(f"query: {to_sql(query)}")
        return query

    @classmethod
    async def get_pagination_models_files(cls, model_id: int, mold_id: int, pid: int, page: int, size: int):
        query = CmfFileService.model_file_query(mold=mold_id, pid=pid, model_id=model_id)
        res = await AsyncPagination(query.dicts(), page=page, size=size).data(
            dump_func=cls.packer,
        )
        res = await cls.append_questions(res)
        return res

    @classmethod
    async def get_pagination_filed_files(
        cls,
        filename: str,
        projectname: str,
        fid: int,
        user_name: str,
        pdf_parse_status: int,
        sysfrom: str | None,
        ai_status: int,
        start_at: str,
        end_at: str,
        order_by: str,
        page: int,
        size: int,
    ):
        query = CmfFileService.filed_file_query(
            filename=filename,
            projectname=projectname,
            fid=fid,
            user_name=user_name,
            pdf_parse_status=pdf_parse_status,
            ai_status=ai_status,
            start_at=start_at,
            end_at=end_at,
            order_by=order_by,
            sysfrom=sysfrom,
        )
        res = await AsyncPagination(query.dicts(), page=page, size=size).data()
        res = await cls.append_questions(res)
        return res

    @staticmethod
    async def get_verify_filed_file(fid: int):
        query = (
            NewFile.select()
            .join(
                NewFileProject,
                on=and_(
                    NewFileProject.id == NewFile.pid,
                    NewFileProject.name == CMF_CHINA_VERIFY_FILED_PROJECT_NAME,
                    ~NewFileProject.visible,
                ),
            )
            .where(NewFile.id == fid)
        )
        return await pw_db.first(query)

    @staticmethod
    async def get_pagination_mold_models(mold: MoldWithFK, page, size):
        query = (
            CmfModel.select(
                CmfModel.id,
                CmfModel.name,
                CmfModel.address,
                CmfModel.intro,
                CmfModel.usage,
                CmfModel.created_utc,
                NewAdminUser.name.alias("user_name"),
                CmfMoldModelRef.enable.alias("enable"),
            )
            .join(CmfMoldModelRef, on=and_(CmfMoldModelRef.mold_id == mold.id, CmfMoldModelRef.model_id == CmfModel.id))
            .join(NewAdminUser, join_type=JOIN.LEFT_OUTER, on=(NewAdminUser.id == CmfModel.uid), include_deleted=True)
            .order_by(CmfModel.id.desc())
        )
        data = await AsyncPagination(query.dicts(), page=page, size=size).data()
        return data

    @staticmethod
    async def append_questions(res):
        file_ids = [item["id"] for item in res["items"]]
        question_query = NewQuestionService.question_query_without_answer(
            file_ids=file_ids,
        )
        questions_by_fid = defaultdict(list)
        for question in await pw_db.execute(question_query.dicts()):
            questions_by_fid[question["fid"]].append(question)

        for item in res["items"]:
            item["questions"] = questions_by_fid[item["id"]]
        return res

    @staticmethod
    async def get_mold_id_from_model(model: CmfModel) -> list[int]:
        return await pw_db.scalars(
            MoldWithFK.select(MoldWithFK.id)
            .join(CmfMoldModelRef, on=and_(CmfMoldModelRef.mold_id == MoldWithFK.id, CmfMoldModelRef.model == model))
            .order_by(MoldWithFK.id)
        )

    @staticmethod
    async def upload_filed_file(file: HTTPFile, uid: int, sysfrom: str):
        project = await NewFileProjectService.create(name=CMF_CHINA_FILED_FILE_PROJECT_NAME, uid=uid, visible=False)
        file_tree = await NewFileTree.find_by_id(project.rtree_id)
        new_file = await NewFileService.create_file(
            name=file.filename,
            body=file.body,
            pid=project.id,
            tree_id=file_tree.id,
            uid=uid,
            task_type=TaskType.AUDIT.value,
            sysfrom=sysfrom,
            molds=[],
            priority=2,
        )
        cmf_file_info = await pw_db.create(CmfFiledFileInfo, fid=new_file.id, status=CmfFiledStatus.WAIT)

        return new_file, cmf_file_info

    @classmethod
    async def get_check_fields(cls, uid, mold_id):
        if not (mold := await pw_db.first(NewMold.select().where(NewMold.id == mold_id))):
            return []
        query = (
            CmfUserCheckFields.select()
            .join(NewMoldField, on=and_(NewMoldField.id == CmfUserCheckFields.mold_field, NewMoldField.mid == mold_id))
            .where(CmfUserCheckFields.uid == uid)
            .order_by(CmfUserCheckFields.mold_field)
        )
        check_items = list(await pw_db.execute(query.dicts()))
        if not check_items:
            # 没有查找到，插入默认值
            mold_field_ids = await pw_db.scalars(
                NewMoldField.select(NewMoldField.id)
                .where(NewMoldField.mid == mold_id, NewMoldField.is_leaf)
                .order_by(NewMoldField.id)
            )
            check_items = [{"mold_field": _id, "check": True, "uid": uid} for _id in mold_field_ids]
            await CmfUserCheckFields.bulk_insert(check_items)

        key_uuid_path_mapping = MoldSchema(mold.data).get_path_mapping()
        uuid_key_path_mapping = {compact_dumps(v): k for k, v in key_uuid_path_mapping.items()}
        mold_field_mapping = await MoldFieldService.get_mold_field_uuid_path(mold.id)
        mold_field_uuid_path = {row.id: compact_dumps(row.path) for row in mold_field_mapping}

        res = []
        for item in check_items:
            uuid_path = mold_field_uuid_path.get(item["mold_field"])
            key_path = uuid_key_path_mapping.get(uuid_path)
            res.append(
                {
                    "mold_field_id": item["mold_field"],
                    "check": item["check"],
                    "uuid_path": uuid_path,
                    "key_path": key_path,
                }
            )
        return res

    @staticmethod
    async def set_check_fields(uid: int, mold_id: int, check_fields: list[dict[str, bool]]):
        await pw_db.execute(
            CmfUserCheckFields.update(check_fields=check_fields).where(
                CmfUserCheckFields.uid == uid, CmfUserCheckFields.mold_id == mold_id
            )
        )

    @staticmethod
    async def get_qid_from_conditions(
        mold_id,
        fids,
        not_fids,
        key_keywords_dict,
        key_modified_list,
        no_key_modified_list,
        no_audit_and_no_key_modified_list,
        probability_list,
    ):
        question_conditions = [NewQuestion.mold == mold_id]
        if fids:
            question_conditions.append(NewQuestion.fid.in_(fids))
        if not_fids:
            question_conditions.append(NewQuestion.fid.not_in(not_fids))
        question_query = NewQuestion.select(NewQuestion.id).where(*question_conditions)
        all_qid = await pw_db.scalars(question_query)
        # 1, 创建查询条件
        answer_conditions = []
        for key, keywords in key_keywords_dict.items():
            condition = and_(NewAnswerDataStat.key == key, NewAnswerDataStat.content.contains(keywords))
            answer_conditions.append(fn.SUM(peewee.Case(None, [(condition, 1)], default=0)) > 0)
        for key in key_modified_list:
            condition = and_(NewAnswerDataStat.key == key, NewAnswerDataStat.record)
            answer_conditions.append(fn.SUM(peewee.Case(None, [(condition, 1)], default=0)) > 0)
        for key in no_key_modified_list:
            null_condition = and_(NewAnswerDataStat.key == key, ~NewAnswerDataStat.record)
            not_null_condition = and_(NewAnswerDataStat.key == key, NewAnswerDataStat.record)
            answer_conditions.append(fn.SUM(peewee.Case(None, [(null_condition, 1)], default=0)) > 0)
            answer_conditions.append(fn.SUM(peewee.Case(None, [(not_null_condition, 1)], default=0)) == 0)
        if probability_list:
            mold_field_probability_mapping = list(
                await pw_db.execute(
                    CmfMoldFieldRef.select(CmfMoldFieldRef.mold_field_id, CmfMoldFieldRef.probability).where(
                        CmfMoldFieldRef.mold_field_id.in_(probability_list)
                    )
                )
            )
            for item in mold_field_probability_mapping:
                condition = and_(
                    NewAnswerDataStat.mold_field_id == item.mold_field_id,
                    NewAnswerDataStat.score < item.probability,
                )
                answer_conditions.append(fn.SUM(peewee.Case(None, [(condition, 1)], default=0)) > 0)
        no_audit_and_key_modified_qids = []
        if no_audit_and_no_key_modified_list:
            # 查询被修改过的字段的qid
            no_audit_and_key_modified_qids = await pw_db.scalars(
                question_query.join(
                    NewAnswerDataStat,
                    on=and_(
                        NewAnswerDataStat.qid == NewQuestion.id,
                        NewAnswerDataStat.key.in_(no_audit_and_no_key_modified_list),
                        NewAnswerDataStat.record,
                    ),
                )
            )
        # 2、获取满足条件的qid
        qids = []
        if answer_conditions:
            answer_sub_query = (
                NewAnswerDataStat.select(NewAnswerDataStat.qid)
                .where(NewAnswerDataStat.qid.in_(all_qid))
                .group_by(NewAnswerDataStat.qid)
                .having(*answer_conditions)
            )
            logger.debug(f"answer:{to_sql(answer_sub_query)}")
            qids = await pw_db.scalars(answer_sub_query)
        return qids, no_audit_and_key_modified_qids

    @classmethod
    async def get_audit_fids(
        cls,
        fid: int,
        mold_id: int,
        audit_compliance_conditions: list[dict[str, str]],
        audit_no_compliance_conditions: list[dict[str, str]],
        audit_na_compliance_conditions: list[dict[str, str]],
    ) -> list[int]:
        def get_cond_temp(compliance_conditions: list[dict[str, str]]) -> list[peewee.Expression]:
            cond_temp = []
            for item in compliance_conditions:
                cond_temp.append(
                    NewAuditResult.schema_results.contains([item]),
                )
            return cond_temp

        def get_sub_query(
            query: ScriberModelSelect, cond_temp: list[peewee.Expression], *expressions
        ) -> ScriberModelSelect:
            sub_query = (
                query.where(or_(*cond_temp), expressions)
                .group_by(NewAuditResult.fid)
                .having(
                    fn.COUNT(fn.DISTINCT(peewee.Case(None, [(item, i) for i, item in enumerate(cond_temp)], None)))
                    == len(cond_temp)
                )
            )
            return sub_query

        def get_in_cond(
            query: ScriberModelSelect, compliance_conditions: list[dict[str, str]], *expressions
        ) -> peewee.Expression:
            cond_temp = get_cond_temp(compliance_conditions)
            sub_query = get_sub_query(query, cond_temp, expressions)
            return NewAuditResult.fid.in_(sub_query)

        # 查找满足审核结果的fids
        query = NewAuditResult.select(NewAuditResult.fid.distinct()).where(
            NewAuditResult.schema_id == mold_id,
            NewAuditResult.answer_type == AuditAnswerType.final_answer,
            or_(
                fn.EXISTS(
                    NewAuditRule.select().where(
                        NewAuditResult.rule_id == NewAuditRule.id,
                    )
                ),
                NewAuditResult.rule_id == RuleID.EXTERNAL_ID,
                NewAuditResult.rule_id.is_null(),
            ),
        )
        cond = []
        if audit_compliance_conditions:
            # 审核通过
            # 一个字段有多少个审核结果，有一个审核不通过/审核不适用，则该fid不通过
            cond_temp = get_cond_temp(audit_compliance_conditions)
            not_compliance_query = query.where(
                or_(*cond_temp),
                or_(~NewAuditResult.is_compliance, NewAuditResult.is_compliance.is_null(True)),
            )
            cond.extend(
                [
                    get_in_cond(query, audit_compliance_conditions, NewAuditResult.is_compliance),
                    NewAuditResult.fid.not_in(not_compliance_query),
                ]
            )
        if audit_no_compliance_conditions:
            # 审核不通过
            cond.append(get_in_cond(query, audit_no_compliance_conditions, ~NewAuditResult.is_compliance))
        if audit_na_compliance_conditions:
            # 审核不适用
            cond.append(get_in_cond(query, audit_na_compliance_conditions, NewAuditResult.is_compliance.is_null(True)))
        if fid:
            cond.append(NewAuditResult.fid == fid)

        return await pw_db.scalars(query.where(*cond))

    @classmethod
    def gen_question_query(cls, mold: NewMold, qids: list[int], not_qids: list[int]) -> ScriberModelSelect:
        sub_question_query = (
            NewQuestion.select(
                NewQuestion.id.alias("qid"),
                NewQuestion.fid.alias("fid"),
                fn.json_agg(
                    fn.json_build_object(
                        "key",
                        NewAnswerData.key,
                        "data",
                        NewAnswerData.data,
                        "value",
                        NewAnswerData.value,
                        "record",
                        NewAnswerData.record,
                        "score",
                        NewAnswerData.score,
                    )
                ).alias("answer_data"),
            )
            .group_by(NewQuestion.id, NewQuestion.fid)
            .where(NewQuestion.mold == mold.id, NewQuestion.id.not_in(not_qids))
            .alias("sub_question_query")
        )
        if qids:
            sub_question_query = sub_question_query.join(
                NewAnswerData,
                join_type=JOIN.INNER,
                on=and_(NewAnswerData.qid == NewQuestion.id, NewAnswerData.qid.in_(qids)),
                include_deleted=True,
            )
        else:
            sub_question_query = sub_question_query.join(
                NewAnswerData,
                join_type=JOIN.LEFT_OUTER,
                on=(NewAnswerData.qid == NewQuestion.id),
                include_deleted=True,
            )
        return sub_question_query

    @classmethod
    async def get_panorama(
        cls,
        mold: NewMold,
        pid: int,
        fid: int | None,
        file_name: str | None,
        start_at: int | None,
        end_at: int | None,
        reviewed: ReviewedType,
        filter_dict: dict,
        order_by: str = "-id",
        _type: TimeType = TimeType.CREATE,
        page: int = 1,
        size: int = 20,
        tree_ids: list[int] = None,
        export: bool = False,
    ):
        uuid_path_mapping = MoldSchema(mold.data).get_path_mapping()
        mold_field_mapping = await MoldFieldService.get_mold_field_uuid_path(mold.id)
        mold_field_uuid_path = {compact_dumps(row.path): row.id for row in mold_field_mapping}
        audit_compliance_conditions = []
        audit_no_compliance_conditions = []
        audit_na_compliance_conditions = []
        audit_no_contain_conditions = []
        no_key_modified_list = []  # 没有修改过的字段
        key_keywords_dict = {}  # 存储关键字
        key_modified_list = []  # 存储修改过的字段
        no_audit_and_no_key_modified_list = []  # 未审核，未修改过的字段
        probability_list = []  # 评分小于阈值的字段
        for key, value in filter_dict.items():
            keys = json.loads(key)
            key_temp = "-".join(keys)
            full_path = [mold.name, *keys]
            full_path = compact_dumps(full_path)
            if value["status"] == FieldStatus.AUDIT:
                # 审核通过
                audit_compliance_conditions.append({"name": key_temp})
                no_key_modified_list.append(full_path)
            elif value["status"] == FieldStatus.FAIL_AUDIT:
                # 审核不通过
                audit_no_compliance_conditions.append({"name": key_temp})
                no_key_modified_list.append(full_path)
            elif value["status"] == FieldStatus.NA:
                # 不适用
                audit_na_compliance_conditions.append({"name": key_temp})
                no_key_modified_list.append(full_path)
            elif value["status"] == FieldStatus.UN_AUDIT:
                # 未审核
                audit_no_contain_conditions.append({"name": key_temp})
                no_audit_and_no_key_modified_list.append(full_path)
            elif value["status"] == FieldStatus.MODIFIED:
                # 用户修改过
                key_modified_list.append(full_path)
            elif value["status"] == FieldStatus.PROBABILITY:
                # 评分过滤
                probability_list.append(mold_field_uuid_path[compact_dumps(uuid_path_mapping[full_path])])
            if value["keywords"]:
                # 查找内容
                key_keywords_dict.update({full_path: value["keywords"]})
        # 1、在AuditResult 中查询出所有符合审核条件的fid
        if audit_compliance_conditions or audit_no_compliance_conditions or audit_na_compliance_conditions:
            fids = await cls.get_audit_fids(
                fid,
                mold.id,
                audit_compliance_conditions,
                audit_no_compliance_conditions,
                audit_na_compliance_conditions,
            )
            if not fids:
                return {"page": page, "size": size, "total": 0, "items": []}
        else:
            fids = [fid] if fid else []
        # 2、未审核： 反向查询，获取所有已经审核的fid，后面查询文件时排除
        not_fids = []
        if audit_no_contain_conditions:
            conditions = []
            for item in audit_no_contain_conditions:
                conditions.append(NewAuditResult.schema_results.contains([item]))
            no_audit_query = NewAuditResult.select(NewAuditResult.fid.distinct()).where(
                NewAuditResult.schema_id == mold.id,
                NewAuditResult.answer_type == AuditAnswerType.final_answer,
                or_(*conditions),
                or_(
                    fn.EXISTS(
                        NewAuditRule.select().where(
                            NewAuditResult.rule_id == NewAuditRule.id,
                        )
                    ),
                    NewAuditResult.rule_id == RuleID.EXTERNAL_ID,
                    NewAuditResult.rule_id.is_null(),
                ),
            )
            not_fids = await pw_db.scalars(no_audit_query)

        # 3、获取符合的qid
        qids, not_qids = await cls.get_qid_from_conditions(
            mold.id,
            fids,
            not_fids,
            key_keywords_dict,
            key_modified_list,
            no_key_modified_list,
            no_audit_and_no_key_modified_list,
            probability_list,
        )
        if (key_keywords_dict or key_modified_list or no_key_modified_list) and not qids:
            return {"page": page, "size": size, "total": 0, "items": []}

        # 4、构建question子查询
        sub_question_query = cls.gen_question_query(mold, qids, not_qids)
        # 5、构建audit_result子查询
        sub_audit_result_query = (
            NewAuditResult.select(
                NewAuditResult.fid.alias("fid"),
                fn.json_agg(
                    fn.json_build_object(
                        "schema_results",
                        NewAuditResult.schema_results,
                        "is_compliance",
                        NewAuditResult.is_compliance,
                    )
                ).alias("audit_results"),
            )
            .where(
                NewAuditResult.answer_type == AuditAnswerType.final_answer,
                or_(
                    fn.EXISTS(
                        NewAuditRule.select().where(
                            NewAuditResult.rule_id == NewAuditRule.id,
                        )
                    ),
                    NewAuditResult.rule_id == RuleID.EXTERNAL_ID,
                    NewAuditResult.rule_id.is_null(),
                ),
            )
            .group_by(NewAuditResult.fid)
            .alias("sub_audit_result_query")
        )

        # 6、文件过滤条件
        file_query = (
            NewFile.select(
                NewFile.id,
                NewFile.name,
                NewFile.pid.alias("pid"),
                NewFile.tree_id,
                NewFile.pdf_parse_status,
                sub_question_query.c.qid,
                sub_question_query.c.answer_data,
                sub_audit_result_query.c.audit_results,
                peewee.Case(
                    None,
                    [
                        (CmfFileReviewed.id.is_null(False), speedy.peewee_plus.orm.TRUE),
                    ],
                    default=speedy.peewee_plus.orm.FALSE,
                ).alias("reviewed"),
                NewAdminUser.name.alias("review_user"),
                NewFile.created_utc,
                NewFile.updated_utc,
            )
            .join(NewFileProject, on=and_(NewFileProject.id == NewFile.pid, NewFileProject.visible))
            .join(sub_question_query, on=(sub_question_query.c.fid == NewFile.id))
            .join(sub_audit_result_query, join_type=JOIN.LEFT_OUTER, on=(sub_audit_result_query.c.fid == NewFile.id))
            .order_by(getattr(NewFile, order_by))
        )

        if reviewed == ReviewedType.REVIEWED:
            # 已复核
            file_query = file_query.join(CmfFileReviewed, on=(CmfFileReviewed.file_id == NewFile.id))
        elif reviewed == ReviewedType.UNREVIEWED:
            # 未复核
            file_query = file_query.join(
                CmfFileReviewed, join_type=JOIN.LEFT_OUTER, on=(CmfFileReviewed.file_id == NewFile.id)
            )
            file_query = file_query.where(CmfFileReviewed.id.is_null(True))
        else:
            # 全部
            file_query = file_query.join(
                CmfFileReviewed, join_type=JOIN.LEFT_OUTER, on=(CmfFileReviewed.file_id == NewFile.id)
            )
        file_query = file_query.join(
            NewAdminUser, join_type=JOIN.LEFT_OUTER, on=(NewAdminUser.id == CmfFileReviewed.uid), include_deleted=True
        )
        cond = NewFile.molds.contains(mold.id)
        if tree_ids is not None:
            cond &= NewFile.tree_id.in_(tree_ids)
        if pid:
            cond &= NewFile.pid == pid
        file_query = file_query.where(cond)
        query = cls.gen_pagination_query(
            query=file_query,
            name=file_name,
            in_ids=fids,
            not_ids=not_fids,
            _type=_type,
            start_at=start_at,
            end_at=end_at,
            page=page,
            size=size,
        )
        if export:
            res = list(await pw_db.execute(query.dicts()))
        else:
            res = await AsyncPagination(query.dicts(), page=page, size=size).data()
        return res

    @staticmethod
    async def get_model_usage_count(model_ids, count_type, start_at, end_at):
        sub_query = (
            CmfModelUsageCount.select(
                CmfModelUsageCount.model_id.alias("model_id"),
                fn.JSONB_AGG(
                    fn.json_build_object(
                        "date",
                        CmfModelUsageCount.date,
                        "success_count",
                        CmfModelUsageCount.success_count,
                        "failure_count",
                        CmfModelUsageCount.failure_count,
                    )
                ).alias("items"),
            )
            .where(
                CmfModelUsageCount.model_id.in_(model_ids),
                CmfModelUsageCount.date >= start_at,
                CmfModelUsageCount.date <= end_at,
            )
            .group_by(CmfModelUsageCount.model_id)
        )
        query = (
            CmfModel.select(
                CmfModel.id,
                CmfModel.name,
                CmfModel.address,
                peewee.Case(
                    None,
                    [(sub_query.c.model_id.is_null(False), sub_query.c.items)],
                    default=peewee.SQL("'[]'::jsonb"),
                ).alias("items"),
            )
            .join(sub_query, join_type=JOIN.LEFT_OUTER, on=(sub_query.c.model_id == CmfModel.id))
            .where(CmfModel.id.in_(model_ids))
            .order_by(CmfModel.id.desc())
        )
        model_usages = list(await pw_db.execute(query.dicts()))
        if count_type == CountType.DAY:
            # 按天统计
            time_range = gen_day_ranges(start_at, end_at)
        else:
            # 按月统计
            time_range = gen_month_ranges_data(start_at, end_at)
        for model_usage in model_usages:
            items = []
            model_usage["success_total"], model_usage["failure_total"] = 0, 0
            for start_timestamp, end_timestamp in time_range:
                temp_data = {"date": start_timestamp, "success_count": 0, "failure_count": 0}
                for item in model_usage["items"]:
                    if start_timestamp <= item["date"] < end_timestamp:
                        temp_data["success_count"] += item["success_count"]
                        temp_data["failure_count"] += item["failure_count"]
                model_usage["success_total"] += temp_data["success_count"]
                model_usage["failure_total"] += temp_data["failure_count"]
                items.append(temp_data)
            model_usage["items"] = items

        return model_usages

    @classmethod
    async def get_model_review_count(cls, model_ids, count_type, start_at, end_at):
        file_cte = (
            NewFile.select(
                NewFile.id,
                NewFile.name,
                NewFile.created_utc,
                NewFile.molds,
                CmfFileReviewed.id.is_null(False).alias("reviewed"),
            )
            .join(CmfFileReviewed, join_type=JOIN.LEFT_OUTER, on=(NewFile.id == CmfFileReviewed.file_id))
            .join(NewFileProject, on=and_(NewFileProject.id == NewFile.pid, NewFileProject.visible))
            .where(NewFile.created_utc >= start_at, NewFile.created_utc <= end_at)
            .cte("file_cte")
        )

        mold_cte = (
            NewMold.select(
                NewMold.id,
                file_cte.c.id.alias("fid"),
                file_cte.c.name.alias("file_name"),
                file_cte.c.created_utc.alias("created_utc"),
                file_cte.c.reviewed,
            )
            .join(file_cte, on=(NewMold.id == fn.ANY(file_cte.c.molds)))
            .cte("mold_cte")
        )

        # 文件复核次数查询
        query = (
            CmfModel.select(
                CmfModel.id,
                CmfModel.name,
                fn.JSONB_AGG(
                    peewee.Case(
                        None,
                        (
                            (
                                mold_cte.c.fid.is_null(False),
                                fn.jsonb_build_object(
                                    "id",
                                    mold_cte.c.fid,
                                    "name",
                                    mold_cte.c.file_name,
                                    "created_utc",
                                    mold_cte.c.created_utc,
                                    "reviewed",
                                    mold_cte.c.reviewed,
                                ),
                            ),
                        ),
                        default=peewee.Value(None),
                    )
                ).alias("files"),
            )
            .join(
                CmfMoldModelRef,
                join_type=JOIN.LEFT_OUTER,
                on=and_(CmfMoldModelRef.model_id == CmfModel.id, CmfMoldModelRef.enable),
            )
            .join(mold_cte, join_type=JOIN.LEFT_OUTER, on=(mold_cte.c.id == CmfMoldModelRef.mold_id))
            .where(CmfModel.id.in_(model_ids))
            .with_cte(file_cte, mold_cte)
            .group_by(CmfModel.id)
            .order_by(CmfModel.id.desc())
        )
        data_list = list(await pw_db.execute(query.dicts()))

        # 统计
        if count_type == CountType.MONTH:
            time_range = gen_month_ranges_data(start_at, end_at)
        else:
            time_range = gen_day_ranges(start_at, end_at)
        for item in data_list:
            reviewed_total = 0
            not_reviewed_total = 0
            items = []
            for start_timestamp, end_timestamp in time_range:
                reviewed_count = 0
                not_reviewed_count = 0
                for file in item["files"]:
                    if not file:
                        continue
                    if start_timestamp <= file["created_utc"] < end_timestamp:
                        if file["reviewed"]:
                            reviewed_total += 1
                            reviewed_count += 1
                        else:
                            not_reviewed_count += 1
                            not_reviewed_total += 1
                items.append(
                    {
                        "date": start_timestamp,
                        "reviewed_count": reviewed_count,
                        "not_reviewed_count": not_reviewed_count,
                    }
                )

            item.update({"reviewed_total": reviewed_total, "not_reviewed_total": not_reviewed_total, "items": items})
            item.pop("files")
        return data_list

    @classmethod
    async def get_model_accuracy(cls, models: list[CmfModel], count_type: int, start_at: int, end_at: int):
        model_ids = [i.id for i in models]
        if count_type == CountType.MONTH:
            time_ranges = gen_month_ranges_data(start_at, end_at)
        else:
            time_ranges = gen_day_ranges(start_at, end_at)
        if not time_ranges:
            return {}

        query = (
            CmfModelAuditAccuracy.select()
            .where(
                CmfModelAuditAccuracy.model_id.in_(model_ids),
                CmfModelAuditAccuracy.date >= time_ranges[0][0],
                CmfModelAuditAccuracy.date < time_ranges[-1][1],
            )
            .order_by(CmfModelAuditAccuracy.model_id.desc(), CmfModelAuditAccuracy.date)
        )
        accuracy_items = await pw_db.execute(query)
        refs = await pw_db.prefetch(
            CmfMoldModelRef.select().where(CmfMoldModelRef.enable == CommonStatus.VALID.value), MoldWithFK.select()
        )
        enabled_molds = defaultdict(set)
        model_molds = defaultdict(list)
        for ref in refs:
            enabled_molds[ref.model_id].add(ref.mold_id)
            model_molds[ref.model_id].append(ref.mold)

        model_accuracy = defaultdict(list)
        model_aliases = {i.id: i.schema_aliases for i in models}
        for model_id, model_accuracy_items in groupby(accuracy_items, lambda x: x.model_id):
            enabled_mold_ids = enabled_molds[model_id]
            for accuracy_item in model_accuracy_items:
                schema_ids = {k for k in accuracy_item.molds_rate if int(k) not in enabled_mold_ids}
                for schema_id in schema_ids:
                    del accuracy_item.molds_rate[schema_id]

                internal_record = AuditStatisticRecord(total=0, compliance_count=0, rules={})
                external_record = AuditStatisticRecord(total=0, compliance_count=0, rules={})
                preset_record = AuditStatisticRecord(total=0, compliance_count=0, rules={})
                answer_record = AuditStatisticRecord(total=0, compliance_count=0, rules={})
                for accuracy_data in accuracy_item.molds_rate.values():
                    # key of accuracy_data endswith '_record' only exists in history audit accuracy.
                    internal_record.add_up(accuracy_data.get("internal", accuracy_data.get("internal_record")))
                    external_record.add_up(accuracy_data.get("external", accuracy_data.get("external_record")))
                    preset_record.add_up(accuracy_data.get("preset_answer", accuracy_data.get("preset_answer_record")))
                    answer_record.add_up(accuracy_data.get("answer", accuracy_data.get("answer_record")))
                model_accuracy[accuracy_item.model_id].append(
                    {
                        "date": accuracy_item.date,
                        "internal": asdict(internal_record),
                        "external": asdict(external_record),
                        "preset_answer": asdict(preset_record),
                        "answer": asdict(answer_record),
                    }
                )

        if count_type == CountType.DAY:
            return [
                {
                    "id": model.id,
                    "name": model.name,
                    "accuracy_items": cls._expand_accuracy_items(
                        cls._gen_path_name_alias(model_molds[model.id]),
                        set(model_aliases[model.id]),
                        model_accuracy[model.id],
                        time_ranges,
                    ),
                }
                for model in models
            ]

        return [
            {
                "id": model.id,
                "name": model.name,
                "accuracy_items": cls._expand_accuracy_items(
                    cls._gen_path_name_alias(model_molds[model.id]),
                    set(model_aliases[model.id]),
                    cls._aggregate_accuracy_items_by_month(model_accuracy[model.id]),
                    time_ranges,
                ),
            }
            for model in models
        ]

    @classmethod
    def _gen_path_name_alias(cls, molds: list[MoldWithFK]) -> dict | None:
        result = {}
        for mold in molds:
            mold_schema = MoldSchema(mold.data)
            result |= mold_schema.gen_path_name_alias()

        return result

    @classmethod
    def _expand_accuracy_items(
        cls, name_aliases, model_aliases: set, accuracy_items: list[dict], time_ranges: list[tuple[int, int]]
    ):
        dates = {item["date"]: item for item in accuracy_items}
        result = []
        alias_names = {v: k for k, v in name_aliases.items()}
        empty_statistic = DayAuditStatistic.default()
        for start, _ in time_ranges:
            if start not in dates:
                result.append({"date": start} | asdict(empty_statistic))
            else:
                accuracy_data = dates[start]
                if name_aliases:
                    for name, data in accuracy_data.items():
                        if name == "date":
                            continue
                        exists_aliases = {name_aliases[name] for name in data["rules"] if name in name_aliases}
                        for alias in model_aliases.difference(exists_aliases):
                            schema_name = alias_names.get(alias)
                            if schema_name:
                                data["rules"][schema_name] = asdict(AuditStatisticRecord())
                result.append(accuracy_data)

        return result

    @classmethod
    def _aggregate_accuracy_items_by_month(cls, accuracy_items: list[dict]):
        def _sort(row: dict):
            dt = datetime.datetime.fromtimestamp(row["date"])
            return dt.year, dt.month

        result = []
        for _, items in groupby(accuracy_items, key=_sort):
            internal_record = AuditStatisticRecord(total=0, compliance_count=0, rules={})
            external_record = AuditStatisticRecord(total=0, compliance_count=0, rules={})
            preset_record = AuditStatisticRecord(total=0, compliance_count=0, rules={})
            answer_record = AuditStatisticRecord(total=0, compliance_count=0, rules={})
            for item in items:
                internal_record.add_up(item["internal"])
                external_record.add_up(item["external"])
                preset_record.add_up(item["preset_answer"])
                answer_record.add_up(item["answer"])

            month_start = datetime.datetime.fromtimestamp(item["date"]).replace(day=1)
            result.append(
                {
                    "date": int(month_start.timestamp()),
                    "internal": asdict(internal_record),
                    "external": asdict(external_record),
                    "preset_answer": asdict(preset_record),
                    "answer": asdict(answer_record),
                }
            )

        return result

    @classmethod
    async def aggregate_audit_accuracy(
        cls, files: list[NewFile], mold_models: dict[int, CmfModel], molds: dict[int, NewMold]
    ):
        mold_ids = list(mold_models.keys())
        for day_start_at, group_files in group_by_date(files):
            file_ids = {i.id for i in group_files}
            query = (
                NewAuditResult.select(NewAuditResult, CmfFileReviewed.id.is_null(False).alias("reviewed"))
                .join(CmfFileReviewed, on=(CmfFileReviewed.file_id == NewAuditResult.fid), join_type=JOIN.LEFT_OUTER)
                .where(
                    NewAuditResult.schema_id.in_(mold_ids),
                    NewAuditResult.fid.in_(file_ids),
                    or_(
                        fn.EXISTS(
                            NewAuditRule.select().where(
                                NewAuditResult.rule_id == NewAuditRule.id,
                            )
                        ),
                        NewAuditResult.rule_id == RuleID.EXTERNAL_ID,
                        NewAuditResult.rule_id.is_null(),
                    ),
                )
            )
            audit_results = list(await pw_db.execute(query.namedtuples()))
            audit_results.sort(key=lambda x: mold_models.get(x.schema_id).id)
            for model_id, model_audit_results in groupby(audit_results, lambda x: mold_models.get(x.schema_id).id):
                if model_id is None:
                    continue

                molds_rate = {}
                model_audit_results = list(model_audit_results)
                model_audit_results.sort(key=lambda x: x.schema_id)
                for schema_id, schema_audit_results in groupby(model_audit_results, lambda x: x.schema_id):
                    mold_schema = MoldSchema(molds[schema_id].data)
                    model = mold_models[schema_id]
                    valid_audit_results = [
                        i
                        for i in schema_audit_results
                        if all(cls._is_valid_schema_rule(r["name"], model, mold_schema) for r in i.schema_results)
                    ]
                    day_statistic = DayAuditStatistic.from_audit_results(valid_audit_results)
                    molds_rate[schema_id] = asdict(day_statistic)

                yield model_id, day_start_at, molds_rate

    @classmethod
    def _is_valid_schema_rule(cls, schema_joined_name: str, model, mold_schema):
        joined_alias = mold_schema.get_alias_by_name(schema_joined_name)
        return joined_alias and model.can_predict(joined_alias)

    @classmethod
    async def get_rules(cls, page, size, mold_id, name, rule_type, rule_id, user, field, group_molds=None):
        query = NewAuditRule.select()
        cond = NewAuditRule.deleted_utc == 0
        if name:
            cond &= NewAuditRule.name.contains(name)
        if rule_type:
            cond &= NewAuditRule.rule_type == rule_type
        if rule_id:
            cond &= NewAuditRule.id == rule_id
        if user:
            cond &= NewAuditRule.user.contains(user)
        if mold_id is not None:
            cond &= NewAuditRule.schema_id == mold_id
        if field:
            cond &= NewAuditRule.fields.contains(field)

        order_by = [NewAuditRule.updated_utc.desc()]
        if group_molds:
            order_by = [NewAuditRule.schema_id.in_(group_molds).desc(), NewAuditRule.updated_utc.desc()]
        query = query.where(cond).order_by(*order_by)

        data = await AsyncPagination(query, page=page, size=size).data()
        return data

    @staticmethod
    async def edit_email(email: CmfChinaEmail, host: str, account: str, password: str, mold_id: int, pid: int):
        email.host = host
        email.account = account
        email.password = password
        email.mold_id = mold_id
        email.pid = pid
        await pw_db.update(email, only=["host", "account", "password", "mold_id", "pid"])

    @staticmethod
    async def get_emails(start_at, end_at, order_by, _type, page, size):
        query = (
            CmfChinaEmail.select(
                CmfChinaEmail.id,
                CmfChinaEmail.account,
                CmfChinaEmail.host,
                CmfChinaEmail.created_utc,
                CmfChinaEmail.updated_utc,
                NewAdminUser.name.alias("user_name"),
                NewFileProject.id.alias("pid"),
                NewFileProject.name.alias("project_name"),
                NewMold.id.alias("mold_id"),
                NewMold.name.alias("mold_name"),
            )
            .join(
                NewAdminUser,
                on=(NewAdminUser.id == CmfChinaEmail.uid),
                join_type=JOIN.LEFT_OUTER,
                include_deleted=True,
            )
            .join(
                NewFileProject,
                on=and_(
                    NewFileProject.id == CmfChinaEmail.pid, NewFileProject.visible, NewFileProject.deleted_utc == 0
                ),
                join_type=JOIN.LEFT_OUTER,
                include_deleted=True,
            )
            .join(
                NewMold,
                on=and_(NewMold.id == CmfChinaEmail.mold_id, NewMold.deleted_utc == 0),
                join_type=JOIN.LEFT_OUTER,
                include_deleted=True,
            )
            .order_by(getattr(CmfChinaEmail, order_by))
        )

        query = CmfChinaService.gen_pagination_query(query, None, [], [], _type, start_at, end_at, page, size)
        data = await AsyncPagination(query.dicts(), page=page, size=size).data()
        return data

    @staticmethod
    async def rerun_preset_answers(mold_id: int, model_id: int):
        fids = await pw_db.scalars(
            NewFile.select(NewFile.id)
            .join(CmfFileReviewed, on=(NewFile.id == CmfFileReviewed.file_id))
            .where(NewFile.molds.contains(mold_id))
        )
        get_lock, lock = run_singleton_task(
            preset_answers_for_mold_online,
            mold_id,
            not_in_fids=fids,
            lock_key=f"preset_answers_for_mold_online_{mold_id}_{model_id}",
            lock_expired=60,
        )
        return get_lock, lock

    @staticmethod
    async def get_answer_data(file: NewFile, group_mold_ids: list[int] = None):
        """
        将answer_data表中的数据组装成普通answer格式
        [
            {
                "answer_data": {},
                "mold: {}
            }
        ]
        :return:
        """
        user_map = await NewAdminUser.get_user_name_map()
        query = (
            NewMold.select(
                NewMold,
                NewQuestion.id.alias("qid"),
            )
            .join(NewQuestion, on=and_(NewMold.id == NewQuestion.mold, NewQuestion.fid == file.id))
            .group_by(NewMold.id, NewQuestion.id)
            .objects()
        )
        if group_mold_ids:
            query = query.where(NewMold.id.in_(group_mold_ids))
        mold_list = list(await pw_db.execute(query))
        qid_list = [item.qid for item in mold_list]
        answer_data_list = list(await pw_db.execute(NewAnswerData.select().where(NewAnswerData.qid.in_(qid_list))))
        answer_data_dict = defaultdict(list)
        for item in answer_data_list:
            answer_data_dict[item.qid].append(item.to_dict(user_map=user_map))
        res = []
        for item in mold_list:
            res.append(
                {
                    "answer_data": answer_data_dict.get(item.qid, []),
                    "mold": item.to_dict(),
                }
            )
        return res

    @staticmethod
    async def edit_answer_data(
        file,
        add: list[CmfAnswerDataAdd],
        update: list[CmfAnswerDataUpdate],
        delete: list[CmfAnswerDataDelete],
        uid: int,
    ):
        data = {}
        if delete:
            cond = NewAnswerData.id.in_([x.id for x in delete])
            await pw_db.execute(NewAnswerData.delete().where(cond))
        if add:
            molds = [item.mold_id for item in add]
            qid_mold_dict = dict(
                await pw_db.execute(
                    NewQuestion.select(NewQuestion.mold, NewQuestion.id)
                    .where(NewQuestion.mold.in_(molds), NewQuestion.fid == file.id)
                    .tuples()
                )
            )
            fix_add = []
            for item in add:
                if not (qid := qid_mold_dict.get(item.mold_id)):
                    continue
                fix_ = item.model_dump(by_alias=True)
                fix_.pop("mold_id")
                fix_["qid"] = qid
                fix_["uid"] = uid
                fix_["record"] = [NewAnswerData.gen_empty_record()]
                fix_add.append(fix_)
            if fix_add:
                added = await NewAnswerData.insert_and_returning(
                    fix_add, returning=[NewAnswerData.id, NewAnswerData.key]
                )
            data["add"] = added
        if update:
            await NewAnswerData.batch_update([item.model_dump(by_alias=True) for item in update], uid)

        return data

    @staticmethod
    async def update_inspector_results(file, delete, add, update):
        mold_key_dict = defaultdict(list)
        for item in add:
            mold_key_dict[item.mold_id].append(item.key)
        delete_ids = [item.id for item in delete]
        query = NewQuestion.select(NewQuestion.mold, NewAnswerData.key).join(
            NewAnswerData, on=and_(NewQuestion.id == NewAnswerData.qid, NewAnswerData.id.in_(delete_ids))
        )
        mold_ids = list(await pw_db.execute(query.dicts()))
        for mold_key in mold_ids:
            mold_key_dict[mold_key["mold"]].append(mold_key["key"])
        if file.task_type == TaskType.AUDIT.value:
            for mold_id, keys in mold_key_dict.items():
                labels = await get_updated_rule_labels(file.id, mold_id, keys)
                if labels:
                    await audit_file_rules_by_mold(fid=file.id, schema_id=mold_id, labels=labels)

    @staticmethod
    async def get_probabilities(mid: int):
        rows = await MoldFieldService.get_mold_field_uuid_path(mid)
        mold_field_mapping = {item.id: compact_dumps(item.path) for item in rows}
        datas = list(
            await pw_db.execute(
                CmfMoldFieldRef.select()
                .where(CmfMoldFieldRef.mold_field_id.in_(list(mold_field_mapping.keys())))
                .order_by(CmfMoldFieldRef.mold_field_id)
            )
        )
        datas = [
            {
                "field_id": item.mold_field_id,
                "probability": item.probability * 100,
                "uuid_path": mold_field_mapping[item.mold_field_id],
            }
            for item in datas
        ]
        return datas

    @staticmethod
    async def set_probability(field_id: int, probability: int):
        query = CmfMoldFieldRef.update(probability=probability / 100).where((CmfMoldFieldRef.mold_field == field_id))

        await pw_db.execute(query)


async def main():
    mold = await pw_db.first(NewMold.select().where(NewMold.id == 168))
    await CmfChinaService.get_panorama(
        mold=mold,
        pid=146,
        fid=1931,
        file_name=None,
        start_at=None,
        end_at=None,
        reviewed=ReviewedType.ALL,
        filter_dict={
            '["file","字段a"]': {"keywords": "", "status": 6},
            '["file","字段b"]': {"keywords": "", "status": 0},
            '["file","字段c"]': {"keywords": "", "status": 0},
        },
    )

    # mold = await pw_db.first(NewMold.select().where(NewMold.id == 96))
    # await CmfChinaService.get_panorama(
    #     mold=mold,
    #     fid=1451,
    #     file_name=None,
    #     start_at=None,
    #     end_at=None,
    #     reviewed=ReviewedType.ALL,
    #     filter_dict={
    #         '["文件组","字段1"]': {"keywords": "", "status": 3},
    #         '["文件组","字段2"]': {"keywords": "", "status": 0},
    #         '["文件组","字段3"]': {"keywords": "", "status": 0},
    #         '["文件组","字段4"]': {"keywords": "", "status": 0},
    #         '["文件组","字段5"]': {"keywords": "", "status": 0},
    #         '["文件组","数据列表","多层字段1"]': {"keywords": "", "status": 0},
    #         '["文件组","数据列表","多层字段2"]': {"keywords": "", "status": 0},
    #     },
    # )


if __name__ == "__main__":
    import asyncio

    asyncio.run(main())
