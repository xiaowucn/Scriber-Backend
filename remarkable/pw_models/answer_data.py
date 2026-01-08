from peewee import SQL, BooleanField, CharField, DecimalField, ForeignKeyField, IntegerField

from remarkable.answer.node import AnswerItem
from remarkable.common.constants import FileAnswerMergeStrategy
from remarkable.common.enums import ExportStatus
from remarkable.common.exceptions import CustomError
from remarkable.common.util import generate_timestamp
from remarkable.config import get_config
from remarkable.db import pw_db
from remarkable.pw_models.base import BaseModel
from remarkable.pw_orm import field
from remarkable.pw_orm.field import ArrayField
from remarkable.service.new_mold import NewMoldService

DEFAULT_FILE_ANSWER_MERGE_STRATEGY = (
    get_config("data_flow.file_answer.merge_strategy") or FileAnswerMergeStrategy.ONLY_LATEST.value
)


class NewAnswerData(BaseModel):
    created_utc = IntegerField(constraints=[SQL("DEFAULT (EXTRACT(epoch FROM now()))::integer")], index=True, null=True)
    deleted_utc = IntegerField(constraints=[SQL("DEFAULT 0")], null=True)
    data = field.JSONField(null=True)
    key = CharField(null=True)
    mold_field_id = IntegerField()
    qid = IntegerField(index=True, null=True)
    record = field.JSONField(null=True)
    schema = field.JSONField(null=True)
    score = CharField(null=True)
    uid = IntegerField(null=True)
    updated_utc = IntegerField(constraints=[SQL("DEFAULT (EXTRACT(epoch FROM now()))::integer")], null=True)
    value = field.ArrayField(field_class=CharField, null=True)
    revise_suggestion = BooleanField(null=True)

    class Meta:
        table_name = "answer_data"
        indexes = ((("qid", "key"), True),)

    fields_in_record = ["key", "data", "value", "score", "uid", "schema", "revise_suggestion", "updated_utc"]

    @classmethod
    def merge_groups(cls, old_groups, new_groups, merge_strategy):
        if merge_strategy == FileAnswerMergeStrategy.ONLY_LATEST:
            merged_groups = new_groups
        elif merge_strategy == FileAnswerMergeStrategy.OLD_FIRST:
            merged_groups = old_groups
            for key, answer_group in new_groups.items():
                if key not in merged_groups:
                    merged_groups[key] = answer_group
        elif merge_strategy == FileAnswerMergeStrategy.EDITED_FIRST:
            merged_groups = new_groups
            for key, answer_group in old_groups.items():
                if answer_group.manual or key not in merged_groups:
                    merged_groups[key] = answer_group
        else:
            raise ValueError("Invalid merge strategy")

        answer_datas = []
        for answer_group in merged_groups.values():
            answer_datas.extend(answer_group.items)
        return answer_datas

    @classmethod
    def gen_empty_record(cls):
        return {k: None for k in ["key", "data", "value", "score", "uid", "schema", "revise_suggestion", "updated_utc"]}

    @staticmethod
    def is_changed(last_item, item):
        last_answer_item = AnswerItem(**last_item)
        answer_item = AnswerItem(**item)
        return last_answer_item.origin_text != answer_item.origin_text

    @classmethod
    async def batch_update(cls, items, uid, qid: int = None):
        items_map = {item["id"]: item for item in items}
        old_answer_datas = list(await pw_db.execute(cls.select().where(cls.id.in_(tuple(items_map)))))
        if len(old_answer_datas) != len(items):
            raise CustomError("Item Not Found")

        for old_answer_data in old_answer_datas:
            item_id = old_answer_data.id
            item = items_map[item_id]
            record = old_answer_data.record or []
            new_record = old_answer_data.to_dict(
                show_cols=["key", "data", "value", "score", "uid", "schema", "revise_suggestion", "updated_utc"]
            )
            if cls.is_changed(new_record, item):
                record.append(new_record)
            item["uid"] = uid
            if qid:
                item["qid"] = qid
            item["record"] = record
            await pw_db.execute(cls.update(**item).where(cls.id == item_id))

    def to_dict(
        self,
        show_all=False,
        hide_cols=None,
        show_cols=None,
        master_mold=None,
        p_molds_name=None,
        user_map=None,
        exclude=None,
    ):
        only = [getattr(self.__class__, col) for col in show_cols or ()]
        data = super().to_dict(only=only, exclude=exclude or hide_cols)
        if user_map:
            data["username"] = user_map.get(self.uid)
            for item in self.record or []:
                item["username"] = user_map.get(item["uid"])
        data["master_key"] = NewMoldService.update_merged_answer_key_path(p_molds_name, master_mold, data["key"])
        return data

    @classmethod
    def get_empty_record(cls):
        return {k: None for k in cls.fields_in_record}


class NewAnswerDataStat(BaseModel):
    answer_data = ForeignKeyField(NewAnswerData, column_name="answer_data_id")
    key = CharField(null=False)
    qid = IntegerField(null=False)
    uid = IntegerField(null=False)
    record = BooleanField(default=False)
    score = DecimalField(null=True)
    mold_field_id = IntegerField()
    content = CharField()
    created_utc = IntegerField()
    updated_utc = IntegerField()

    class Meta:
        table_name = "answer_data_stat"


class AnswerDataExport(BaseModel):
    created_utc = IntegerField(default=generate_timestamp)
    deleted_utc = IntegerField(default=0, null=True)
    pid = IntegerField()
    task_done = IntegerField(default=0, null=True)
    task_total = IntegerField(default=0, null=True)
    zip_path = CharField(null=True)
    files_ids = ArrayField(field_class=IntegerField, default=list)
    status = IntegerField(default=ExportStatus.DOING, null=False)

    class Meta:
        table_name = "answer_data_export"
