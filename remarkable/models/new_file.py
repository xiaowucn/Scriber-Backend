import logging
import os
from datetime import datetime
from functools import cached_property

from peewee import SQL, CharField, ForeignKeyField, IntegerField, fn

from remarkable.common.constants import CCXI_CACHE_PATH, AnswerStatus
from remarkable.common.enums import TaskType
from remarkable.common.storage import localstorage
from remarkable.common.util import generate_timestamp, simple_match_ext
from remarkable.config import get_config
from remarkable.db import pw_db
from remarkable.pw_models.base import BaseModel, ReadOnlyForeignKeyField
from remarkable.pw_models.law import LawScenario
from remarkable.pw_models.model import NewFileProject
from remarkable.pw_orm import field

logger = logging.getLogger(__name__)


class NewFile(BaseModel):
    class Meta:
        table_name = "file"

    pid: int | IntegerField

    annotation_path = CharField(null=True)
    created_utc = IntegerField(default=generate_timestamp)
    updated_utc = IntegerField(default=generate_timestamp)
    # created_utc = IntegerField(constraints=[SQL("DEFAULT (EXTRACT(epoch FROM now()))::integer")], index=True, null=True)
    deleted_utc = IntegerField(default=0)
    docx = CharField(null=True)
    farm_id = IntegerField(null=True)
    hash = CharField()
    link = CharField(constraints=[SQL("DEFAULT ''::character varying")], null=True)
    meta_info = field.JSONField(null=True)
    molds = field.ArrayField(field_class=IntegerField)
    name = CharField()
    origin_tree_id = IntegerField(null=True)
    page = IntegerField(null=True)
    pdf = CharField(null=True)
    pdf_flag = IntegerField(null=True)
    pdf_parse_status = IntegerField(null=True)
    pdfinsight = CharField(null=True)
    project = ForeignKeyField(NewFileProject, column_name="pid", backref="files")
    revise_docx = CharField(null=True)
    revise_pdf = CharField(null=True)
    size = IntegerField(null=True)
    sysfrom = CharField(index=True, null=True)
    source = CharField(index=True, null=True)
    task_type = CharField(constraints=[SQL("DEFAULT 'extract'::character varying")], null=True)
    tree_id = IntegerField()
    uid = IntegerField(index=True, null=True)
    rank = IntegerField(default=0)
    priority = IntegerField(default=9)
    scenario = ReadOnlyForeignKeyField(LawScenario, null=True)
    chatdoc_unique = CharField(null=True)
    studio_upload_id = CharField(null=True)

    def to_dict(self, exclude=(project, scenario), extra_attrs=("pid", "scenario_id"), **kwargs):
        return super().to_dict(exclude=exclude, extra_attrs=extra_attrs, **kwargs)

    def pdf_path(self, *, abs_path=False):
        return self.path(col="pdf", abs_path=abs_path)

    def pdfinsight_path(self, *, abs_path=False):
        return self.path(col="pdfinsight", abs_path=abs_path)

    def revise_docx_path(self):
        return self.path(col="revise_docx")

    def revise_pdf_path(self, *, abs_path=False):
        return self.path(col="revise_pdf", abs_path=abs_path)

    def docx_path(self):
        return self.path(col="docx")

    async def soft_delete(self):
        from remarkable.pw_models.model import NewCCXIContract, NewChinaStockAnswer, NewFileMeta, NewRuleResult

        await pw_db.execute(NewFileMeta.delete().where(NewFileMeta.file_id == self.id))
        await pw_db.execute(NewRuleResult.delete().where(NewRuleResult.fid == self.id))
        await pw_db.execute(NewCCXIContract.delete().where(NewCCXIContract.fid == self.id))
        await pw_db.execute(NewChinaStockAnswer.delete().where(NewChinaStockAnswer.fid == self.id))
        await super().soft_delete()

        if self.meta_info and self.task_type == TaskType.CLEAN_FILE.value:
            from remarkable.value_obj import CGSFileMeta

            CGSFileMeta(**self.meta_info).clean_file.delete()

        if await NewFile.find_by_kwargs(hash=self.hash):
            return None
        if self.pdf_path():
            localstorage.delete_file(self.pdf_path())
        if self.pdfinsight_path():
            localstorage.delete_file(self.pdfinsight_path())
            # remove ccxi pdfinsight cache
            ccxi_path = os.path.join(CCXI_CACHE_PATH, self.pdfinsight[:2], self.pdfinsight[2:])
            localstorage.delete_file(ccxi_path)
        if self.pdf_cache_path():
            localstorage.delete_dir(self.pdf_cache_path())
        # 如果没有相同文件, 则删除db关联的PDFinsight hash记录
        await self.update_(pdfinsight=None)

    @property
    def is_auditable(self):
        return self.task_type == TaskType.AUDIT.value

    @property
    def pdf_name(self):
        return f"{os.path.splitext(self.name)[0]}.pdf"

    @property
    def ext(self):
        return os.path.splitext(self.name)[-1].lower()

    @property
    def deleted(self) -> bool:
        return bool(self.deleted_utc != 0)

    @property
    def created_from_link(self) -> bool:
        return (self.meta_info or {}).get("created_from_link", False)

    @property
    def inspect_fields(self):
        return (self.meta_info or {}).get("inspect_fields")

    @property
    def failed_reason(self) -> str:
        return (self.meta_info or {}).get("failed_reason", "")

    @cached_property
    def is_pdf(self):
        return simple_match_ext(self.ext, self.path(abs_path=True), ".pdf")

    @cached_property
    def is_image(self):
        return simple_match_ext(self.ext, self.path(abs_path=True), ".jpg", ".jpeg", ".png", ".tif")

    @cached_property
    def is_ppt(self):
        return simple_match_ext(self.ext, self.path(abs_path=True), ".ppt", ".pptx")

    @cached_property
    def is_word(self):
        return simple_match_ext(self.ext, self.path(abs_path=True), ".doc", ".docx")

    @cached_property
    def is_docx(self):
        return simple_match_ext(self.ext, self.path(abs_path=True), ".docx")

    @cached_property
    def is_doc(self):
        return simple_match_ext(self.ext, self.path(abs_path=True), ".doc")

    @cached_property
    def is_excel(self):
        return simple_match_ext(self.ext, self.path(abs_path=True), ".xls", ".xlsx")

    @cached_property
    def is_txt(self):
        return simple_match_ext(self.ext, self.path(abs_path=True), ".txt")

    @classmethod
    async def find_by_qid(cls, qid):
        from remarkable.pw_models.question import NewQuestion

        query = cls.select().join(NewQuestion, on=(cls.id == NewQuestion.fid)).where(NewQuestion.id == qid)
        ret = await pw_db.first(query)
        return ret

    @classmethod
    async def find_by_hash(cls, hash_val):
        return await cls.find_by_kwargs(hash=hash_val)

    @classmethod
    async def find_by_pid(cls, pid):
        query = cls.select().where(cls.pid == pid)
        return await pw_db.execute(query)

    @classmethod
    async def find_by_tree_id(cls, tree_id):
        query = cls.select().where(cls.tree_id == tree_id)
        return await pw_db.execute(query)

    @classmethod
    async def list_by_range(cls, mold=None, start=None, end=None, tree_l=None, created_from=None, created_to=None):
        cond = []
        if mold:
            cond.append(cls.molds.contains(mold))
        if start:
            cond.append(cls.id >= start)
        if end:
            cond.append(cls.id <= end)
        if tree_l:
            cond.append(cls.tree_id.in_(tree_l))
        if created_from:
            cond.append(cls.created_utc >= created_from)
        if created_to:
            cond.append(cls.created_utc < created_to)

        query = cls.select().where(*cond).order_by(cls.id)
        return await pw_db.execute(query)

    @classmethod
    async def find_by_mold_parsed(cls, mold_id):
        query = cls.select().where(cls.molds.contains(mold_id), cls.pdfinsight.is_null(False))
        return await pw_db.execute(query)

    @classmethod
    async def find_by_mold_inspected(cls, mold_id):
        from remarkable.pw_models.audit_rule import NewAuditResult
        from remarkable.pw_models.question import NewQuestion

        query = (
            cls.select()
            .distinct(cls.id)
            .join(
                NewAuditResult,
                on=((cls.id == NewAuditResult.fid) & (NewAuditResult.answer_type == AnswerStatus.final_answer)),
            )
            .join(NewQuestion, on=(cls.id == NewQuestion.fid))
        )
        cond = (NewAuditResult.schema_id == mold_id, NewQuestion.mold == mold_id)
        return await pw_db.execute(query.where(*cond))

    @classmethod
    async def find_by_mold_with_model_answer(cls, mold_id, enable_vid):
        from remarkable.models.model_version import NewModelVersion
        from remarkable.models.new_model_answer import ModelAnswer
        from remarkable.pw_models.question import NewQuestion

        version = await NewModelVersion.get_last_with_model_answer(mold_id, enable_vid)
        if not version:
            logger.info(f"not last version for {mold_id=}, {enable_vid=}")
            return []

        query = cls.select().distinct(cls.id).join(NewQuestion, on=(cls.id == NewQuestion.fid))
        query = query.join(ModelAnswer, on=(NewQuestion.id == ModelAnswer.qid))
        cond = ModelAnswer.vid == version.id

        return await pw_db.execute(query.where(cond))

    @classmethod
    async def find_by_mold_labeled(cls, mold_id: int, tree_l: list[int] = None, fids: list[int] = None):
        """
        已标注的文档
        """
        from remarkable.pw_models.model import NewAnswer
        from remarkable.pw_models.question import NewQuestion

        train_status = get_config("prompter.training_data_status", "2, 5, 10, 100")
        train_status = [int(x.strip()) for x in train_status.split(",")]

        query = (
            cls.select()
            .distinct()
            .join(NewQuestion, on=(cls.id == NewQuestion.fid))
            .join(NewAnswer, on=(NewQuestion.id == NewAnswer.qid))
        )

        cond = cls.pdfinsight.is_null(False)
        cond &= (
            (NewQuestion.mold == mold_id) & (NewQuestion.answer.is_null(False)) & (NewQuestion.status.in_(train_status))
        )
        cond &= NewAnswer.data.is_null(False) & (NewAnswer.status == AnswerStatus.VALID)

        if tree_l:
            cond &= cls.tree_id.in_(tree_l)
        if fids:
            cond &= cls.id.in_(fids)

        files = await pw_db.execute(query.where(cond).order_by(cls.id))
        return files

    @classmethod
    async def find_by_mold_answered(cls, mold_id: int, tree_l: list[int] = None, fids: list[int] = None):
        """
        有答案的文档(标注过 or 预测过)
        """
        from remarkable.pw_models.question import NewQuestion

        query = cls.select().distinct(cls.id).join(NewQuestion, on=(cls.id == NewQuestion.fid))

        cond = (NewQuestion.mold == mold_id) & (NewQuestion.answer.is_null(False))
        cond &= (fn.json_array_length(fn.json_extract_path(NewQuestion.answer, "userAnswer", "items")) != 0) | (
            fn.json_array_length(fn.json_extract_path(NewQuestion.answer, "custom_field", "items")) != 0
        )

        if tree_l:
            cond &= cls.tree_id.in_(tree_l)
        if fids:
            cond &= cls.id.in_(fids)

        files = await pw_db.execute(query.where(cond).order_by(cls.id))
        return files

    @staticmethod
    def get_path(col_val):
        return os.path.join(col_val[:2], col_val[2:]) if col_val else None

    @property
    def label_cache_dir(self):
        """PDFinsight相关数据缓存
        TODO: 迁移文档svg/搜索缓存到这里
        """
        if not self.pdfinsight_path():
            raise FileNotFoundError(f"file: {self.id} missing pdfinsight data")
        cache_dir = localstorage.mount(os.path.join(localstorage.label_cache_dir, self.pdfinsight_path()))
        localstorage.create_dir(cache_dir)
        return cache_dir

    def pdf_cache_path(self):
        return os.path.join(localstorage.cache_root, self.path("pdf")) if self.pdf else None

    def raw_pdf_path(self):
        # convert_to_pdf 处理图片转pdf的流早前存在问题（我们会将图片转换成pdf后进行处理，然后再将pdf传送到pdfinsight解析,
        # 但pdfinsight需要的是原始的pdf，不然会产生其他不可预知的问题）
        # 现在修正流程，保存了原始的pdf发送给pdfinsight,并且如果是图片的情况下应该也将pdf的path置为原始的文件路径
        if self.is_image and self.meta_info:
            if raw_pdf := self.meta_info.get("raw_pdf"):
                if get_config("client.add_time_hierarchy", False):
                    upload_date = datetime.fromtimestamp(self.created_utc)
                    return os.path.join(
                        str(upload_date.year), str(upload_date.month), str(upload_date.day), raw_pdf[:2], raw_pdf[2:]
                    )
                else:
                    return os.path.join(raw_pdf[:2], raw_pdf[2:])
        return None
