from peewee import SQL, ForeignKeyField, IntegerField

from remarkable.models.new_permission import Permission
from remarkable.models.new_role import Role
from remarkable.pw_models.base import BaseModel


class RolePermissionRef(BaseModel):
    role = ForeignKeyField(Role, backref="role_permission_refs")
    permission = ForeignKeyField(Permission)
    created_utc = IntegerField(constraints=[SQL("DEFAULT (EXTRACT(epoch FROM now()))::integer")])

    def to_dict(self, exclude=(role, permission), extra_attrs=("role_id", "permission_id"), **kwargs):
        return super().to_dict(exclude=exclude, extra_attrs=extra_attrs, **kwargs)
