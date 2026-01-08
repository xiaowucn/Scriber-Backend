from peewee import BooleanField, ForeignKeyField, IntegerField, TextField
from playhouse.postgres_ext import ArrayField, BinaryJSONField

from remarkable.models.new_file import NewFile
from remarkable.models.new_user import NewAdminUser
from remarkable.pw_models.model import BaseModel, NewFileProject


class ChinaamcProject(NewFileProject):
    compare_tasks: list["CompareTask"]

    class Meta:
        table_name = "file_project"


class ProjectInfo(BaseModel):
    source = IntegerField(null=False)
    project = ForeignKeyField(ChinaamcProject, null=False, column_name="pid")
    dept_ids = ArrayField(TextField, default=list)

    class Meta:
        table_name = "chinaamc_project_info"


class UserInfo(BaseModel):
    user = ForeignKeyField(NewAdminUser, null=False, column_name="uid")
    dept_ids = ArrayField(TextField, default=list)

    class Meta:
        table_name = "chinaamc_user_info"


class CompareTask(BaseModel):
    name = TextField()
    status = IntegerField(default=0)
    started = BooleanField(default=False)
    fids = ArrayField(IntegerField, default=list, null=False)

    consistency_status = IntegerField(default=0)
    consistency_answer = BinaryJSONField(default=list)
    chapter_status = IntegerField(default=0)
    chapter_answer = BinaryJSONField(default=dict)

    created_utc = IntegerField(null=False)
    updated_utc = IntegerField(null=False)
    deleted_utc = IntegerField(null=False)

    user = ForeignKeyField(NewAdminUser, null=False, column_name="uid")
    project = ForeignKeyField(ChinaamcProject, null=False, column_name="pid", backref="compare_tasks")

    class Meta:
        table_name = "chinaamc_compare_task"


class FileAnswer(BaseModel):
    task = ForeignKeyField(CompareTask, null=False, column_name="task_id")
    file = ForeignKeyField(NewFile, null=False, column_name="fid")
    status = IntegerField(default=0)
    schema = BinaryJSONField(default=list)
    answer = BinaryJSONField(default=list)

    created_utc = IntegerField(null=False)
    updated_utc = IntegerField(null=False)

    class Meta:
        table_name = "chinaamc_file_answer"
