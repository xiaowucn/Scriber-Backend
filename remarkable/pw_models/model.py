import json
import logging
import shutil
from pathlib import Path
from typing import Self

import peewee
import speedy
from peewee import (
    SQL,
    BigIntegerField,
    BooleanField,
    CharField,
    DoubleField,
    ForeignKeyField,
    IntegerField,
    SmallIntegerField,
    TextField,
    fn,
)
from speedy.peewee_plus.orm import or_

from remarkable.common.constants import (
    AccuracyRecordStatus,
    AnswerStatus,
    HistoryAction,
    PDFFlag,
    PDFParseStatus,
    TagType,
)
from remarkable.common.enums import AuditAnswerType, ExportStatus, TaskType
from remarkable.common.exceptions import CustomError
from remarkable.common.util import generate_timestamp
from remarkable.config import get_config
from remarkable.db import pw_db
from remarkable.file_flow.uploaded_file import UploadedFile
from remarkable.models.new_user import NewAdminUser
from remarkable.pw_models.base import BaseModel
from remarkable.pw_orm import field

logger = logging.getLogger(__name__)


def is_empty(field_):
    from playhouse.postgres_ext import BinaryJSONField, JSONField  # noqa

    cond = field_.is_null()
    if isinstance(field_, (JSONField, BinaryJSONField)):
        cond |= SQL(f"{field_.name}::text = '{{}}'") | SQL(f"{field_.name}::text = 'null'")
    else:
        cond |= fn.TRIM(field_) == ""
    return cond


class NewAccessToken(BaseModel):
    created_utc = IntegerField(constraints=[SQL("DEFAULT (EXTRACT(epoch FROM now()))::integer")], null=True)
    deleted_utc = IntegerField(constraints=[SQL("DEFAULT 0")], null=True)
    password = CharField(unique=True)
    updated_utc = IntegerField(constraints=[SQL("DEFAULT (EXTRACT(epoch FROM now()))::integer")], null=True)
    user_id = IntegerField()

    class Meta:
        table_name = "access_token"


class NewAccuracyRecord(BaseModel):
    created_utc = IntegerField(default=generate_timestamp, index=True, null=True)
    data = field.JSONField(json_type="json")
    deleted_utc = IntegerField(default=0, null=True)
    dirs = field.ArrayField(field_class=IntegerField, null=True)
    file_count = IntegerField(null=True)
    files = field.ArrayField(field_class=IntegerField, null=True)
    mold = IntegerField()
    test = IntegerField()
    type = IntegerField()
    vid = IntegerField(null=True)
    export_path = CharField(null=True)
    status = CharField(default=AccuracyRecordStatus.DOING.value)

    class Meta:
        table_name = "accuracy_record"


class NewAdminOp(BaseModel):
    answer = IntegerField(null=True)
    created_utc = IntegerField(default=generate_timestamp, index=True, null=True)
    qid = IntegerField()
    type = SmallIntegerField()
    uid = IntegerField()
    updated_utc = IntegerField(default=generate_timestamp, index=True, null=True)

    class Meta:
        table_name = "admin_op"


class AlembicVersion(BaseModel):
    version_num = CharField(primary_key=True)

    class Meta:
        table_name = "alembic_version"


class NewAnswer(BaseModel):
    created_utc = BigIntegerField(constraints=[SQL("DEFAULT (EXTRACT(epoch FROM now()))::integer")])
    data = field.JSONField(json_type="json")
    qid = IntegerField()
    result = IntegerField(constraints=[SQL("DEFAULT 0")])
    standard = IntegerField(constraints=[SQL("DEFAULT 0")])
    status = IntegerField(constraints=[SQL("DEFAULT 1")])
    type = SmallIntegerField(constraints=[SQL("DEFAULT '1'::smallint")])
    uid = IntegerField()
    updated_utc = BigIntegerField(constraints=[SQL("DEFAULT (EXTRACT(epoch FROM now()))::integer")])

    class Meta:
        table_name = "answer"
        indexes = ((("qid", "uid"), True),)

    @classmethod
    async def get_answers_by_qid(cls, qid):
        answers = await pw_db.execute(
            cls.select().where(
                cls.qid == qid,
                cls.status.in_([AnswerStatus.VALID.value, AnswerStatus.UNFINISHED.value]),
            )
        )
        for answer in answers:
            if answer.status == AnswerStatus.UNFINISHED:
                # 对于仅保存草稿的答案, 只保留自定义字段
                answer.data["userAnswer"] = {"version": "2.2", "items": []}
        return answers

    @classmethod
    async def find_standard(cls, qid):
        return await pw_db.first(cls.select().where(cls.qid == qid, cls.standard == 1).order_by(cls.updated_utc.desc()))


class NewAnswerDmLog(BaseModel):
    aid = IntegerField(index=True)
    created_utc = IntegerField()
    data = field.JSONField(json_type="json")
    dm_utc = IntegerField(constraints=[SQL("DEFAULT (EXTRACT(epoch FROM now()))::integer")], null=True)
    qid = IntegerField(index=True)
    result = IntegerField()
    standard = IntegerField()
    status = IntegerField()
    type = CharField(constraints=[SQL("DEFAULT 'DELETE'::character varying")])
    uid = IntegerField(index=True)
    updated_utc = IntegerField()

    class Meta:
        table_name = "answer_dm_log"
        indexes = ((("type", "qid", "uid", "aid"), True),)


class NewCCXIContract(BaseModel):
    area = CharField(null=True)
    company_name = CharField(null=True)
    contract_no = CharField(null=True)
    created_utc = IntegerField(constraints=[SQL("DEFAULT (EXTRACT(epoch FROM now()))::integer")], null=True)
    date_signed = IntegerField(null=True)
    fid = IntegerField(null=True)
    meta = field.JSONField(null=True)
    project_name = CharField(null=True)
    qid = IntegerField()
    third_party_name = CharField(null=True)
    tree_id = IntegerField(null=True)
    updated_utc = IntegerField(constraints=[SQL("DEFAULT (EXTRACT(epoch FROM now()))::integer")], null=True)
    variety = CharField(null=True)

    class Meta:
        table_name = "ccxi_contract"
        indexes = (
            (
                ("contract_no", "company_name", "project_name", "third_party_name", "area", "variety", "date_signed"),
                False,
            ),
        )


class NewAuditStatus(BaseModel):
    created_utc = IntegerField(constraints=[SQL("DEFAULT (EXTRACT(epoch FROM now()))::integer")], index=True, null=True)
    deleted_utc = IntegerField(constraints=[SQL("DEFAULT 0")], null=True)
    fid = IntegerField(null=True)
    schema_id = IntegerField(null=True)
    status = IntegerField(null=True)
    updated_utc = IntegerField(constraints=[SQL("DEFAULT (EXTRACT(epoch FROM now()))::integer")], null=True)
    answer_type = IntegerField(null=True, default=AuditAnswerType.final_answer)

    class Meta:
        table_name = "cgs_audit_status"

    async def set_status(self, status):
        await self.update_(status=status)

    @classmethod
    async def find_latest_status(cls, fid, schema_id=None) -> Self | None:
        cond = (cls.fid == fid) & (cls.answer_type == AuditAnswerType.final_answer)
        if schema_id:
            cond &= cls.schema_id == schema_id
        return await pw_db.first(cls.select().where(cond).order_by(cls.id.desc()))

    @classmethod
    async def reset(cls, fid):
        return await pw_db.execute(cls.update({cls.deleted_utc: generate_timestamp()}).where(cls.fid == fid))


class NewAuditDevRule(BaseModel):
    content = TextField()
    created_utc = IntegerField(constraints=[SQL("DEFAULT (EXTRACT(epoch FROM now()))::integer")], index=True, null=True)
    deleted_utc = IntegerField(constraints=[SQL("DEFAULT 0")], null=True)
    law = CharField(null=True)
    law_id = CharField(index=True, null=True)
    name = CharField(index=True)
    rule_type = CharField(index=True)
    updated_utc = IntegerField(constraints=[SQL("DEFAULT (EXTRACT(epoch FROM now()))::integer")], null=True)

    class Meta:
        table_name = "cgs_dev_rule"


class NewAuditResultRecord(BaseModel):
    created_utc = IntegerField(constraints=[SQL("DEFAULT (EXTRACT(epoch FROM now()))::integer")], index=True, null=True)
    deleted_utc = IntegerField(constraints=[SQL("DEFAULT 0")], null=True)
    is_compliance_from = BooleanField(null=True)
    is_compliance_to = BooleanField(null=True)
    result_id = IntegerField(index=True)
    suggestion = TextField(null=True)
    updated_utc = IntegerField(constraints=[SQL("DEFAULT (EXTRACT(epoch FROM now()))::integer")], null=True)
    user_id = IntegerField(index=True)
    user_name = CharField(index=True)
    user_reason = TextField(null=True)

    class Meta:
        table_name = "cgs_result_record"

    @classmethod
    async def get_last_modified_users(cls, result_ids: list[int]):
        if not result_ids:
            return {}
        cte = (
            cls.select(
                cls.result_id,
                cls.user_name,
                fn.ROW_NUMBER().over(partition_by=[cls.result_id], order_by=[cls.id.desc()]).alias("rnk"),
            )
            .where(cls.result_id.in_(result_ids))
            .cte("subq")
        )
        query = cte.select_from(cte.c.result_id, cte.c.user_name).where(cte.c.rnk == 1).with_cte(cte).tuples()
        ret = dict(await pw_db.execute(query))
        return ret


class NewChinaStockAnswer(BaseModel):
    created_utc = IntegerField(constraints=[SQL("DEFAULT (EXTRACT(epoch FROM now()))::integer")], null=True)
    fid = IntegerField()
    file_source = CharField(null=True)
    manager_name = CharField(null=True)
    meta = field.JSONField(null=True)
    product_name = CharField(null=True)
    qid = IntegerField(unique=True)
    tree_id = IntegerField()
    updated_utc = IntegerField(constraints=[SQL("DEFAULT (EXTRACT(epoch FROM now()))::integer")], null=True)

    class Meta:
        table_name = "china_stock_answer"


class NewDiffCmp(BaseModel):
    created_utc = IntegerField(constraints=[SQL("DEFAULT (EXTRACT(epoch FROM now()))::integer")], index=True, null=True)
    deleted_utc = IntegerField(constraints=[SQL("DEFAULT 0")], null=True)
    f1_hash = CharField(index=True, null=True)
    f1_name = CharField(null=True)
    f1_pdf_hash = CharField(null=True)
    f1_pdfinsight = CharField(null=True)
    f1_size = IntegerField(null=True)
    f2_hash = CharField(index=True, null=True)
    f2_name = CharField(null=True)
    f2_pdf_hash = CharField(null=True)
    f2_pdfinsight = CharField(null=True)
    f2_size = IntegerField(null=True)
    result_hash = CharField(null=True)
    status = IntegerField(null=True)
    total_diff = IntegerField(null=True)
    uid = IntegerField(index=True)
    updated_utc = IntegerField(constraints=[SQL("DEFAULT (EXTRACT(epoch FROM now()))::integer")], index=True, null=True)

    class Meta:
        table_name = "diff_cmp"


class NewDiffFile(BaseModel):
    created_utc = IntegerField(constraints=[SQL("DEFAULT (EXTRACT(epoch FROM now()))::integer")], null=True)
    hash = CharField()
    name = CharField()
    pdf_hash = CharField(null=True)
    status = IntegerField(null=True)
    uid = IntegerField(index=True)
    updated_utc = IntegerField(constraints=[SQL("DEFAULT (EXTRACT(epoch FROM now()))::integer")], index=True, null=True)

    class Meta:
        table_name = "diff_file"
        indexes = ((("uid", "hash"), True),)


class NewDiffRecord(BaseModel):
    cmp_id = IntegerField(null=True)
    created_utc = IntegerField(constraints=[SQL("DEFAULT (EXTRACT(epoch FROM now()))::integer")], null=True)
    dst_fid1 = IntegerField(null=True)
    dst_fid2 = IntegerField(null=True)
    fid1 = IntegerField(index=True)
    fid2 = IntegerField(index=True)
    name1 = CharField(null=True)
    name2 = CharField(null=True)
    status = IntegerField()
    total_diff = IntegerField(null=True)
    type = IntegerField()
    uid = IntegerField(index=True)
    updated_utc = IntegerField(constraints=[SQL("DEFAULT (EXTRACT(epoch FROM now()))::integer")], index=True, null=True)

    class Meta:
        table_name = "diff_record"
        indexes = ((("uid", "fid1", "fid2"), True),)


class NewDocument(BaseModel):
    checksum = CharField(unique=True)
    created_utc = BigIntegerField(constraints=[SQL("DEFAULT (EXTRACT(epoch FROM now()))::integer")])
    data = field.JSONField(json_type="json")
    updated_utc = BigIntegerField(constraints=[SQL("DEFAULT (EXTRACT(epoch FROM now()))::integer")])

    class Meta:
        table_name = "document"


class NewErrorContent(BaseModel):
    content = CharField(null=True)
    created_utc = IntegerField(constraints=[SQL("DEFAULT (EXTRACT(epoch FROM now()))::integer")], null=True)
    deleted_utc = IntegerField(constraints=[SQL("DEFAULT 0")], null=True)
    error_status = IntegerField(null=True)
    fid = IntegerField(null=True)
    rule_result_id = IntegerField(null=True)
    uid = IntegerField(null=True)
    updated_utc = IntegerField(constraints=[SQL("DEFAULT (EXTRACT(epoch FROM now()))::integer")], null=True)

    class Meta:
        table_name = "error_content"
        indexes = ((("uid", "fid", "rule_result_id"), True),)


class NewExtractMethod(BaseModel):
    created_utc = IntegerField(constraints=[SQL("DEFAULT (EXTRACT(epoch FROM now()))::integer")], null=True)
    data = field.JSONField(json_type="json")
    deleted_utc = IntegerField(constraints=[SQL("DEFAULT 0")], null=True)
    method_type = IntegerField()
    mold = IntegerField()
    path = CharField()
    updated_utc = IntegerField(constraints=[SQL("DEFAULT (EXTRACT(epoch FROM now()))::integer")], null=True)

    class Meta:
        table_name = "extract_method"

    @classmethod
    async def clear_by_mold(cls, mold):
        await pw_db.execute(cls.delete().where(cls.mold == mold))

    @classmethod
    async def find_by_mold(cls, mold):
        return await cls.find_by_kwargs(mold=mold, delegate="all")


class NewFileMeta(BaseModel):
    created_utc = IntegerField(constraints=[SQL("DEFAULT (EXTRACT(epoch FROM now()))::integer")], null=True)
    deleted_utc = IntegerField(constraints=[SQL("DEFAULT 0")], null=True)
    doc_type = CharField(index=True)
    file_id = IntegerField(null=True, unique=True)
    hash = CharField()
    publish_time = IntegerField()
    raw_data = field.JSONField(json_type="json")
    report_year = IntegerField(null=True)
    stock_code = CharField()
    stock_name = CharField()
    title = CharField()
    updated_utc = IntegerField(constraints=[SQL("DEFAULT (EXTRACT(epoch FROM now()))::integer")], null=True)

    class Meta:
        table_name = "file_meta"
        indexes = (
            (("doc_type", "hash"), True),
            (("title", "stock_name", "stock_code", "report_year"), False),
        )


class NewFileProject(BaseModel):
    class Meta:
        table_name = "file_project"

    created_utc = IntegerField(constraints=[SQL("DEFAULT (EXTRACT(epoch FROM now()))::integer")], index=True, null=True)
    default_molds = field.ArrayField(field_class=IntegerField)
    default_scenario_id = IntegerField(null=True)
    default_task_type = CharField(null=True)
    deleted_utc = IntegerField(constraints=[SQL("DEFAULT 0")], null=True)
    meta = field.JSONField(null=True)
    name = CharField()
    preset_answer_model = CharField(null=True)
    public = BooleanField(constraints=[SQL("DEFAULT true")], null=True)
    rtree_id = IntegerField()
    uid = IntegerField(constraints=[SQL("DEFAULT 1")], null=True)
    updated_utc = IntegerField(constraints=[SQL("DEFAULT (EXTRACT(epoch FROM now()))::integer")], null=True)
    visible = BooleanField(constraints=[SQL("DEFAULT true")], null=True)
    status = CharField()

    async def create_root_tree(self):
        if self.rtree_id:
            raise Exception("the project already have root filetree")
        tree = await pw_db.create(
            NewFileTree,
            **{
                "name": self.name,
                "ptree_id": 0,
                "default_molds": self.default_molds,
                "default_scenario_id": self.default_scenario_id,
                "default_task_type": self.default_task_type,
                "uid": self.uid,
                "pid": self.id,
                "meta": self.meta,
            },
        )
        await pw_db.update(self, rtree_id=tree.id)
        return tree

    def build_file_data(
        self, upload_file: UploadedFile, tree_id: int, uid: int | None = None, data: None | dict = None
    ):
        pdf_hash = upload_file.md5 if upload_file.is_pdf else None
        file_data = {
            "tree_id": tree_id,
            "pid": self.id,
            "name": upload_file.filename,
            "hash": upload_file.md5,
            "size": upload_file.length,
            "page": None,
            "molds": [],
            "pdf": pdf_hash,
            "docx": upload_file.md5 if upload_file.is_docx else None,
            "uid": uid if uid else self.uid,
            "pdfinsight": None,
            "pdf_flag": PDFFlag.CONVERTED.value if pdf_hash else PDFFlag.NEED_CONVERT.value,
            "pdf_parse_status": PDFParseStatus.PENDING.value,
            "meta_info": None,
            "link": None,
            "task_type": TaskType.EXTRACT.value,
            "sysfrom": None,
            "source": None,
            "rank": 0,
            "priority": 9,
        }
        if data:
            return file_data | data

        return file_data

    async def soft_delete(self):
        await super().soft_delete()
        await pw_db.execute(NewFileTree.update(deleted_utc=generate_timestamp()).where(NewFileTree.pid == self.id))


class NewFileTree(BaseModel):
    name = CharField()
    pid = IntegerField()
    uid = IntegerField(constraints=[SQL("DEFAULT '-1'::integer")], null=True)
    origin_ptree_id = IntegerField(null=True)
    ptree_id: int = IntegerField()
    meta = field.JSONField(null=True)
    default_molds: list[int] = field.ArrayField(field_class=IntegerField)
    default_scenario_id = IntegerField(null=True)
    default_task_type = CharField(null=True)
    created_utc = IntegerField(constraints=[SQL("DEFAULT (EXTRACT(epoch FROM now()))::integer")], index=True, null=True)
    updated_utc = IntegerField(constraints=[SQL("DEFAULT (EXTRACT(epoch FROM now()))::integer")], null=True)
    deleted_utc = IntegerField(constraints=[SQL("DEFAULT 0")], null=True)

    class Meta:
        table_name = "file_tree"

    async def soft_delete(self):
        from remarkable.models.new_group import CMFGroupRef

        await pw_db.execute(CMFGroupRef.delete().where(CMFGroupRef.file_tree == self.id))
        await super().soft_delete()

    @classmethod
    async def list_by_tree(cls, ptree_id, order_by=None, tree_ids=None):
        query = cls.select(
            cls.id,
            cls.name,
            cls.origin_ptree_id,
            cls.pid,
            cls.ptree_id,
            cls.meta,
            cls.default_molds,
            cls.default_scenario_id,
            cls.default_task_type,
            cls.created_utc,
            cls.updated_utc,
            NewAdminUser.name.alias("user_name"),
        ).join(NewAdminUser, join_type=peewee.JOIN.LEFT_OUTER, on=(NewAdminUser.id == cls.uid))

        cond = cls.ptree_id == ptree_id
        if tree_ids is not None:
            cond &= cls.id.in_(tree_ids)

        query = query.where(cond).dicts()

        if order_by:
            query = query.order_by(getattr(cls, order_by))
        else:
            query = query.order_by(cls.id.desc())
        return await pw_db.execute(query)

    @classmethod
    async def get_fids(cls, *tree_id: int) -> list[int]:
        from remarkable.models.new_file import NewFile

        own = NewFileTree.select().where(NewFileTree.id.in_(tree_id)).cte("base", recursive=True)
        child = NewFileTree.alias("child")
        recursive = child.select().join(own, on=(own.c.id == child.ptree_id))
        cte = own.union_all(recursive)
        subquery = cte.select_from(cte.c.id, cte.c.ptree_id)
        exist_query = peewee.fn.EXISTS(subquery.where(cte.c.id == NewFileTree.id))
        tree_ids = [
            tree.id for tree in await pw_db.prefetch(NewFileTree.select().where(exist_query).order_by(NewFileTree.id))
        ]
        return [file.id for file in await pw_db.prefetch(NewFile.select().where(NewFile.tree_id.in_(tree_ids)))]

    @classmethod
    async def find_default_molds(cls, tree_id: int) -> list[int]:
        own = NewFileTree.select().where(NewFileTree.id == tree_id).cte("base", recursive=True)
        parent = NewFileTree.alias("parent")
        recursive = parent.select().join(own, on=(own.c.ptree_id == parent.id))
        cte = own.union_all(recursive)
        subquery = cte.select_from(cte.c.id, cte.c.ptree_id)
        exist_query = peewee.fn.EXISTS(subquery.where(cte.c.id == NewFileTree.id))
        for tree in await pw_db.prefetch(
            NewFileTree.select(NewFileTree.default_molds).where(exist_query).order_by(NewFileTree.id.desc())
        ):
            if tree.default_molds:
                return tree.default_molds
        return []

    @classmethod
    async def find_default(cls, tree_id: int) -> Self:
        own = cls.select().where(cls.id == tree_id).cte("base", recursive=True)
        parent = cls.alias("parent")
        recursive = parent.select().join(own, on=(own.c.ptree_id == parent.id))
        cte = own.union_all(recursive)
        subquery = cte.select_from(cte.c.id, cte.c.ptree_id)
        exist_query = peewee.fn.EXISTS(subquery.where(cte.c.id == cls.id))
        for tree in await pw_db.prefetch(
            cls.select(cls.id, cls.default_molds, cls.default_scenario_id, cls.default_task_type)
            .where(exist_query)
            .order_by(cls.id.desc())
        ):
            if tree.default_task_type is not None:
                return tree
        return None

    @classmethod
    async def get_all_trees(cls, current_user: NewAdminUser | None = None) -> list[dict]:
        cond = NewFileProject.visible
        if current_user and not current_user.is_admin:
            cond &= or_(NewFileProject.public, cls.uid == current_user.id)
        fields = (cls.id, cls.name, cls.ptree_id, cls.pid)
        query = cls.select(*fields).left_outer_join(NewFileProject, on=(cls.pid == NewFileProject.id))
        data = list(await pw_db.execute(query.where(cond).order_by(cls.id.desc()).dicts()))

        data.insert(0, {"id": 0, "name": "root"})  # 插入根节点
        for each in data:
            each["children"] = []

        # 建立索引
        index = {data[i]["id"]: i for i in range(len(data))}
        for i in range(1, len(data)):
            if data[i]["ptree_id"] not in index:
                continue
            if index[data[i]["ptree_id"]] not in range(len(data)):
                continue
            data[index[data[i]["ptree_id"]]]["children"].append(data[i])
        return data

    @classmethod
    async def find_all_sub_tree(cls, tree_id, include_self=False):
        async def recursive_find(_tree_id):
            trees = await cls.find_by_kwargs(ptree_id=_tree_id, delegate="all")
            if trees:
                for tree in trees:
                    tree_ids.append(tree.id)
                    await recursive_find(tree.id)

        tree_ids = []
        if include_self:
            tree_ids.append(tree_id)
        await recursive_find(tree_id)
        return tree_ids


class NewHistory(BaseModel):
    action = IntegerField()
    action_time = IntegerField(constraints=[SQL("DEFAULT (EXTRACT(epoch FROM now()))::integer")], index=True, null=True)
    meta = field.JSONField(json_type="json", null=True)
    qid = IntegerField(index=True, null=True)
    uid = IntegerField(index=True)
    user_name = CharField(null=True)
    visible = BooleanField(default=True)
    nafmii_misc = field.JSONField(json_type="jsonb", null=True)

    class Meta:
        table_name = "history"

    @classmethod
    async def save_operation_history(
        cls, qid: int | None, uid: int, action: int, user_name: str, meta: dict | None, **kwargs
    ):
        history = await pw_db.create(
            cls, **{"uid": uid, "qid": qid, "action": action, "user_name": user_name, "meta": meta, **kwargs}
        )
        if "nafmii" in kwargs:
            await pw_db.create(
                NafmiiEvent,
                history_id=history.id,
                user_id=uid,
                **kwargs["nafmii"],
            )


class _NewMold(BaseModel):
    b_training = IntegerField(constraints=[SQL("DEFAULT 0")], null=True)
    checksum = CharField()
    comment = CharField(null=True)
    created_utc = IntegerField(constraints=[SQL("DEFAULT (EXTRACT(epoch FROM now()))::integer")])
    data = field.JSONField(json_type="json", null=True)
    deleted_utc = IntegerField(constraints=[SQL("DEFAULT 0")], null=True)
    group_tags = field.ArrayField(field_class=CharField, null=True)
    last_training_utc = IntegerField(constraints=[SQL("DEFAULT 0")], null=True)
    master = IntegerField(null=True)
    meta = field.JSONField(null=True)
    mold_type = IntegerField(null=True)
    name = CharField()
    predictor_option = field.JSONField(json_type="json", null=True)
    predictors = field.JSONField(json_type="json", null=True)
    progress = DoubleField(constraints=[SQL("DEFAULT 0")], null=True)
    public = BooleanField(constraints=[SQL("DEFAULT true")], null=True)
    updated_utc = IntegerField(constraints=[SQL("DEFAULT (EXTRACT(epoch FROM now()))::integer")])
    studio_app_id = CharField(null=True)
    model_name = CharField(null=True)

    class Meta:
        table_name = "mold"

    @classmethod
    async def find_by_name(cls, name):
        return await cls.find_by_kwargs(name=name)

    @classmethod
    async def list_by_range(cls, start=None, end=None, include_deleted=False):
        cond = speedy.peewee_plus.orm.TRUE

        if start:
            cond &= cls.id >= start
        if end:
            cond &= cls.id <= end
        return await pw_db.execute(cls.select(include_deleted=include_deleted).where(cond).order_by(cls.id.desc()))

    @classmethod
    async def get_related_molds(cls, pk_id: int):
        mold = await cls.find_by_id(pk_id)

        cond = NewMold.deleted_utc == 0
        if not mold.master:
            cond &= (cls.id == pk_id) | (cls.master == pk_id)
        else:
            cond &= (cls.id == pk_id) | (cls.id == mold.master) | (cls.master == mold.master)
        molds = await pw_db.execute(cls.select().where(cond).order_by(cls.master.desc()))
        return molds

    @classmethod
    async def tolerate_schema_ids(cls, *schema_id: str | int) -> list[int]:
        names = []
        ids = []
        for sid in schema_id:
            if isinstance(sid, str) and not sid.isdigit():
                names.append(sid)
            else:
                ids.append(sid)
        if ids:
            ids = await pw_db.scalars(cls.select(cls.id).where(cls.id.in_(ids)))
        if names:
            ids.extend(await pw_db.scalars(cls.select(cls.id).where(cls.name.in_(names))))
        assert ids, f"{schema_id=} not found"
        return ids

    @classmethod
    async def get_name_by_id(cls, pk_id) -> str | None:
        mold = await pw_db.first(cls.select(cls.name).where(cls.id == pk_id))
        return mold.name if mold else None

    async def soft_delete(self):
        cache_dir = Path(get_config("training_cache_dir")) / str(self.id)
        if cache_dir.is_dir():
            shutil.rmtree(cache_dir)
        await super().soft_delete()


class NewMold(_NewMold):
    class Meta:
        table_name = "mold"

    uid = IntegerField(null=True)


class MoldWithFK(_NewMold):
    class Meta:
        table_name = "mold"

    user: NewAdminUser | None = ForeignKeyField(NewAdminUser, column_name="uid", backref="molds")


class NewRuleClass(BaseModel):
    created_utc = IntegerField(constraints=[SQL("DEFAULT (EXTRACT(epoch FROM now()))::integer")], null=True)
    deleted_utc = IntegerField(constraints=[SQL("DEFAULT 0")], null=True)
    method_type = IntegerField()
    mold = IntegerField()
    name = CharField()
    updated_utc = IntegerField(constraints=[SQL("DEFAULT (EXTRACT(epoch FROM now()))::integer")], null=True)

    class Meta:
        table_name = "rule_class"

    @classmethod
    async def list_by_mold(cls, mold: int):
        return await cls.find_by_kwargs("all", mold=mold)

    @classmethod
    async def clear_by_mold(cls, mold):
        await pw_db.execute(cls.delete().where(cls.mold == mold))


class NewRuleDoc(BaseModel):
    aid = IntegerField()
    callback = TextField(null=True)
    created_utc = IntegerField(constraints=[SQL("DEFAULT (EXTRACT(epoch FROM now()))::integer")], null=True)
    deleted_utc = IntegerField(constraints=[SQL("DEFAULT 0")], null=True)
    doclet_id = IntegerField(index=True, null=True)
    fid = IntegerField(index=True)
    status = IntegerField(constraints=[SQL("DEFAULT 0")], null=True)
    updated_utc = IntegerField(constraints=[SQL("DEFAULT (EXTRACT(epoch FROM now()))::integer")], null=True)

    class Meta:
        table_name = "rule_doc"
        indexes = ((("fid", "doclet_id", "callback"), True),)


class NewRuleItem(BaseModel):
    class_ = IntegerField(column_name="class")
    created_utc = IntegerField(constraints=[SQL("DEFAULT (EXTRACT(epoch FROM now()))::integer")], null=True)
    data = field.JSONField(json_type="json")
    deleted_utc = IntegerField(constraints=[SQL("DEFAULT 0")], null=True)
    method_type = IntegerField()
    mold = IntegerField()
    name = CharField()
    updated_utc = IntegerField(constraints=[SQL("DEFAULT (EXTRACT(epoch FROM now()))::integer")], null=True)

    class Meta:
        table_name = "rule_item"

    @classmethod
    async def list_by_mold(cls, mold):
        return await cls.find_by_kwargs("all", mold=mold)

    @classmethod
    async def list_by_rule_class(cls, cid):
        return await cls.find_by_kwargs("all", **{"class": cid, "desc": False})

    @classmethod
    async def clear_by_mold(cls, mold):
        await pw_db.execute(cls.delete().where(cls.mold == mold))

    @classmethod
    async def clear_by_rule_class(cls, cid):
        await pw_db.execute(cls.delete().where(cls.class_ == cid))


class NewRuleResult(BaseModel):
    audit_status = IntegerField()
    comment = CharField(null=True)
    comment_pos = field.JSONField(json_type="json", null=True)
    created_utc = IntegerField(default=generate_timestamp, null=True)
    detail = field.JSONField(json_type="json", null=True)
    fid = IntegerField()
    result = IntegerField(constraints=[SQL("DEFAULT 0")])
    rule = CharField()
    schema_cols = field.ArrayField(field_class=CharField, null=True)
    second_rule = CharField(null=True)
    updated_utc = IntegerField(default=generate_timestamp, null=True)

    class Meta:
        table_name = "rule_result"

    @classmethod
    async def get_by_fid(cls, fid):
        return await cls.find_by_kwargs("all", fid=fid)


class NewSpecialAnswer(BaseModel):
    ANSWER_TYPE_EXPORT = "export_answer"
    ANSWER_TYPE_PREDICT = "predict_answer"
    ANSWER_TYPE_JSON = "json_answer"  # json格式导出答案
    ANSWER_TYPE_ORIGIN = "origin_answer"  # 转换前原答案
    ANSWER_TYPE_NAFMII = "nafmii_answer"

    qid = IntegerField(null=True)
    answer_type = CharField(null=True)
    data = field.JSONField(null=True)

    created_utc = IntegerField(constraints=[SQL("DEFAULT (EXTRACT(epoch FROM now()))::integer")], null=True)
    deleted_utc = IntegerField(constraints=[SQL("DEFAULT 0")], null=True)
    updated_utc = IntegerField(constraints=[SQL("DEFAULT (EXTRACT(epoch FROM now()))::integer")], null=True)

    class Meta:
        table_name = "special_answer"

    @classmethod
    async def get_answers(cls, qid: int, answer_type: str, top=1):
        cond = (cls.qid == qid) & (cls.answer_type == answer_type) & (cls.deleted_utc == 0)
        return await pw_db.execute(cls.select().where(cond).order_by(cls.updated_utc.desc()).limit(top))

    @classmethod
    async def get_answers_by_page(cls, qid: int, answer_type: str, top=1, page: int | None = None) -> list[dict]:
        cond = (cls.qid == qid) & (cls.answer_type == answer_type) & (cls.deleted_utc == 0)
        # NOTE: 中信的表单可能有上千页，如果传page，就按页返回，优化查询速度
        query = (
            cls.select(cls.data["headers"].as_json(), cls.data["pages"][str(page)].as_json())
            .where(cond)
            .order_by(cls.updated_utc.desc())
            .limit(top)
            .tuples()
        )
        return [{"headers": headers, "pages": {str(page): pages}} for headers, pages in await pw_db.execute(query)]

    @classmethod
    async def update_or_create(cls, qid: int, answer_type: str, data: dict | list):
        if isinstance(data, list):
            return await pw_db.execute(cls.update(data=data).where((cls.qid == qid) & (cls.answer_type == answer_type)))

        if isinstance(data, dict) and "pages" in data:
            # 这里只可能传一页，所以直接取第一个
            page, value = list(data["pages"].items())[0]
            return await pw_db.execute(
                cls.update(data=SQL("jsonb_set(data, %s, %s)", ("{{pages,{}}}".format(page), json.dumps(value)))).where(
                    (cls.qid == qid) & (cls.answer_type == answer_type)
                )
            )
        raise CustomError("Invalid data type")

    @classmethod
    async def update_or_create_crude(cls, qid, answer_type, data):
        """for test accuracy only"""
        answers = await pw_db.execute(
            cls.select().where(cls.qid == qid, cls.answer_type == answer_type).order_by(cls.updated_utc.desc()).limit(2)
        )
        if len(answers) > 1:  # 正常情况应该只有一个special_answer
            raise CustomError("Unknown situation: more than one special_answer!")

        if answers:
            await answers[0].update_(data=data)
        else:
            await cls.create(qid=qid, answer_type=answer_type, data=data)


class NewSystemConfig(BaseModel):
    created_utc = IntegerField(default=generate_timestamp, null=True)
    data = field.JSONField(json_type="json", null=True)
    enable = IntegerField(constraints=[SQL("DEFAULT 1")])
    index = CharField(constraints=[SQL("DEFAULT ''::character varying")])
    name = CharField()
    updated_utc = IntegerField(default=generate_timestamp, null=True)

    class Meta:
        table_name = "system_config"

    def index_str(cls, **kwargs):
        _parts = ["%s:%s" % (k, v) for k, v in kwargs.items() if v is not None]
        return "_".join(sorted(_parts))

    @classmethod
    async def find_by_name(cls, name, index=""):
        return await cls.find_by_kwargs(name=name, index=index)

    @classmethod
    async def list_by_name(cls, name):
        return await cls.find_by_kwargs("all", name=name)


class NewTag(BaseModel):
    created_utc = BigIntegerField(constraints=[SQL("DEFAULT (EXTRACT(epoch FROM now()))::integer")])
    name = CharField()
    status = IntegerField(constraints=[SQL("DEFAULT 1")])
    tag_type = IntegerField()
    updated_utc = BigIntegerField(constraints=[SQL("DEFAULT (EXTRACT(epoch FROM now()))::integer")])

    class Meta:
        table_name = "tag"
        indexes = ((("name", "tag_type"), False),)


class NewTagRelation(BaseModel):
    relational_id = IntegerField()
    tag_id = IntegerField()

    class Meta:
        table_name = "tag_relation"
        indexes = ((("tag_id", "relational_id"), False),)

    @classmethod
    async def update_tag_relation(cls, tag_ids, relational_obj, tag_type: TagType):
        tags = await NewTag.find_by_ids(tag_ids)
        for tag in tags:
            if tag.tag_type != tag_type:
                raise CustomError(_("Tag_type is not correct!"))  # noqa

        tag_relations = await pw_db.execute(
            cls.select().where(
                cls.relational_id == relational_obj.id,
                fn.EXISTS(NewTag.select().where(NewTag.id == cls.tag_id, NewTag.tag_type == tag_type)),
            )
        )

        exists_tag_ids = []
        for tag_relation in tag_relations:
            exists_tag_ids.append(tag_relation.tag_id)
            if tag_relation.tag_id not in tag_ids:
                await tag_relation.soft_delete()

        for tag_id in set(tag_ids) - set(exists_tag_ids):
            await pw_db.create(cls, tag_id=tag_id, relational_id=relational_obj.id)


class NewTimeRecord(BaseModel):
    created_utc = IntegerField(constraints=[SQL("DEFAULT (EXTRACT(epoch FROM now()))::integer")], null=True)
    deleted_utc = IntegerField(constraints=[SQL("DEFAULT 0")], null=True)
    fid = IntegerField(index=True)
    insight_parse_stamp = IntegerField(null=True)
    insight_queue_stamp = IntegerField(null=True)
    pdf_parse_stamp = IntegerField(null=True)
    preset_stamp = IntegerField(null=True)
    prompt_stamp = IntegerField(null=True)
    updated_utc = IntegerField(constraints=[SQL("DEFAULT (EXTRACT(epoch FROM now()))::integer")], null=True)
    upload_stamp = IntegerField(null=True)

    class Meta:
        table_name = "time_record"

    @classmethod
    async def update_record(cls, fid: int, record_col: str):
        assert record_col in cls._meta.fields, f"{record_col=} not in {cls._meta.fields}"
        record = await pw_db.first(cls.select().where(cls.fid == fid))
        if record:
            setattr(record, record_col, generate_timestamp())
            return await pw_db.update(record, only=[record_col])
        await cls.create(fid=fid, **{record_col: generate_timestamp()})

    @classmethod
    async def find_by_fid(cls, fid: int):
        time_record = await pw_db.first(cls.select().where(NewTimeRecord.fid == fid))
        return time_record


class NewTrainingData(BaseModel):
    created_utc = IntegerField(constraints=[SQL("DEFAULT (EXTRACT(epoch FROM now()))::integer")], index=True, null=True)
    deleted_utc = IntegerField(constraints=[SQL("DEFAULT 0")], null=True)
    dirs = field.ArrayField(field_class=IntegerField, null=True)
    export_type = CharField(constraints=[SQL("DEFAULT 'json'::character varying")], null=True)
    files_ids = field.ArrayField(field_class=IntegerField, null=True)
    mold = IntegerField()
    task_done = IntegerField(constraints=[SQL("DEFAULT 0")], null=True)
    task_total = IntegerField(constraints=[SQL("DEFAULT 0")], null=True)
    zip_path = CharField(null=True)
    task_action = IntegerField(default=HistoryAction.CREATE_TRAINING_DATA)
    status = IntegerField(default=ExportStatus.DOING, null=False)

    class Meta:
        table_name = "training_data"


class NafmiiUser(NewAdminUser):
    class Meta:
        table_name = "admin_user"


class NafmiiEvent(BaseModel):
    history = ForeignKeyField(NewHistory)
    user = ForeignKeyField(NafmiiUser)
    type = IntegerField()
    status = IntegerField()
    ip = CharField()
    client = CharField()
    menu = CharField()
    subject = CharField()
    content = CharField()
    created_utc = IntegerField(null=True)

    class Meta:
        table_name = "nafmii_event"


class NewMoldField(BaseModel):
    mid = IntegerField()
    uuid = CharField()
    parent = CharField(default=None)
    type = CharField()
    alias = CharField()
    required = BooleanField(default=False)
    multi = BooleanField(default=True)
    words = CharField(default=None)
    description = CharField(default=None)
    is_leaf = BooleanField(default=False)
    created_utc = IntegerField(default=generate_timestamp)
    updated_utc = IntegerField(default=generate_timestamp)

    class Meta:
        table_name = "mold_field"
