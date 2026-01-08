from peewee import SQL, ForeignKeyField, IntegerField

from remarkable.models.new_role import Role
from remarkable.models.new_user import NewAdminUser
from remarkable.pw_models.base import BaseModel


class UserRoleRef(BaseModel):
    user = ForeignKeyField(NewAdminUser, backref="user_role_refs")
    role = ForeignKeyField(Role)
    created_utc = IntegerField(constraints=[SQL("DEFAULT (EXTRACT(epoch FROM now()))::integer")])

    def to_dict(self, exclude=(user, role), extra_attrs=("user_id", "role_id"), **kwargs):
        return super().to_dict(exclude=exclude, extra_attrs=extra_attrs, **kwargs)
