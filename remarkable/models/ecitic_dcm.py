from peewee import SQL, CharField, IntegerField

from remarkable.common.constants import DcmStatus
from remarkable.db import pw_db
from remarkable.pw_models.base import BaseModel


class DcmProject(BaseModel):
    project_id = CharField()
    publish_start_date = CharField()
    bond_shortname = CharField()
    product_id = CharField()
    project_name = CharField()
    email_host = CharField()
    email_address = CharField()
    email_password = CharField()
    fill_status = CharField(default=DcmStatus.TODO.value)

    created_utc = IntegerField(constraints=[SQL("DEFAULT (EXTRACT(epoch FROM now()))::integer")])
    updated_utc = IntegerField(constraints=[SQL("DEFAULT (EXTRACT(epoch FROM now()))::integer")])


class DcmBondOrder(BaseModel):
    orderapply_id = CharField(unique=True)
    order_id = CharField()
    project_id = CharField()
    project_name = CharField()
    publish_start_date = CharField()
    product_id = CharField()
    bond_shortname = CharField()
    order_no = CharField()
    investor_name = CharField()
    interest_rate = CharField()
    base_money = CharField()
    apply_scale = CharField()
    base_limit = CharField()
    scale_limit = CharField()
    total_amt = CharField()
    apply_money = CharField()
    limit_id = CharField()

    created_utc = IntegerField()
    updated_utc = IntegerField()


class DcmBondLimit(BaseModel):
    limit_id = CharField(unique=True)
    project_id = CharField()
    project_name = CharField()
    publish_start_date = CharField()
    product_id = CharField()
    bond_shortname = CharField()
    order_no = CharField()
    underwrite_name = CharField()
    base_money = CharField()
    scale = CharField()
    plan_circulation = CharField()
    book_keeper_id = CharField()
    order_id = CharField()
    interest_rate = CharField()

    created_utc = IntegerField()
    updated_utc = IntegerField()


class DcmUnderWriteRate(BaseModel):
    underwritegroup_id = CharField(unique=True)
    order_id = CharField()
    project_id = CharField()
    project_name = CharField()
    publish_start_date = CharField()
    underwrite_name = CharField()
    underwrite_role_code = CharField()
    entr_name = CharField()
    underwrite_balance_ratio = CharField()

    created_utc = IntegerField()
    updated_utc = IntegerField()


class DcmQuestionOrderRef(BaseModel):
    question_id = IntegerField()
    order_id = IntegerField()
    created_utc = IntegerField()


class DcmProjectFileProjectRef(BaseModel):
    dcm_project_id = IntegerField()
    file_project_id = IntegerField()
    created_utc = IntegerField()


class DcmFileInfo(BaseModel):
    file_id = IntegerField()
    email_sent_at = IntegerField()
    email_from = CharField()
    email_to = CharField()
    email_content = CharField()
    email_screenshot = CharField()
    fill_status = CharField(default=DcmStatus.TODO.value)
    browse_status = CharField(default=DcmStatus.TODO.value)
    edit_status = CharField(default=DcmStatus.TODO.value)
    investor_name = CharField()
    created_utc = IntegerField()
    updated_utc = IntegerField()

    @classmethod
    async def get_by_file_id(cls, file_id):
        file_info = await pw_db.first(cls.select().where(cls.file_id == file_id))
        return file_info

    def email_screenshot_path(self, *, abs_path=False):
        return self.path(col="email_screenshot", abs_path=abs_path)
