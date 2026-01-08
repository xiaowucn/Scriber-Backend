from functools import cached_property

from peewee import SQL, CharField, IntegerField

from remarkable.common.constants import ADMIN_ID, ADMIN_NAME, FeatureSchema
from remarkable.config import get_config
from remarkable.db import pw_db
from remarkable.pw_models.base import BaseModel
from remarkable.pw_orm import field


class NewAdminUser(BaseModel):
    created_utc = IntegerField(constraints=[SQL("DEFAULT (EXTRACT(epoch FROM now()))::integer")], null=True)
    data: dict = field.JSONField(null=True, default=dict)
    deleted_utc = IntegerField(constraints=[SQL("DEFAULT 0")], null=True)
    department = CharField(null=True)
    department_id = CharField(null=True)
    ext_from = CharField(null=True)
    ext_id = CharField(null=True)
    login_count = IntegerField(constraints=[SQL("DEFAULT 0")], null=True)
    login_utc = IntegerField(constraints=[SQL("DEFAULT 0")], null=True)
    name = CharField()
    password = CharField()
    permission = field.JSONField(null=True, json_type="json")
    salt = CharField()
    updated_utc = IntegerField(constraints=[SQL("DEFAULT (EXTRACT(epoch FROM now()))::integer")], null=True)
    note = CharField(null=True)
    expired_utc = IntegerField(default=0)

    class Meta:
        table_name = "admin_user"

    @property
    def is_admin(self):
        return self.id == ADMIN_ID or self.name in ("admin", "token|nekot")

    @cached_property
    def all_perms(self) -> set[str]:
        return {item["perm"] for item in self.permission if "perm" in item} | {
            p.rsplit("_", maxsplit=1)[-1] for p in (self.data or {}).get("param_perms", [])
        }

    async def has_perms(self, *required_perms: str, strategy: str = "any"):
        from remarkable.service.user import get_user_permissions

        if get_config("feature.role_based_permission"):
            user_permissions = await get_user_permissions(self.id)
            user_permissions = set(user_permissions)
        else:
            user_permissions = self.all_perms

        return (
            self.has_all_perms(*required_perms, user_permissions=user_permissions)
            if strategy == "all"
            else self.has_any_perms(*required_perms, user_permissions=user_permissions)
        )

    def has_any_perms(self, *required_perms: str, user_permissions: set[str]):
        ro_perms = {
            "prj",
            "search",
            "detail",
            "template",
            "para",
            "upload",
            "compare",
            "predict",
            "audit",
            "file",
        }
        required_perms = set(required_perms)
        rw_perms = {"add", "del", "edit", "push", "batchdel", "submit"}
        if "browse" in required_perms:
            required_perms = required_perms | ro_perms
        if any(p.startswith("manage_") for p in required_perms):
            required_perms = required_perms | rw_perms
        return self.is_admin or bool(required_perms & user_permissions)

    def has_all_perms(self, *required_perms: str, user_permissions: set[str]):
        return self.is_admin or set(required_perms) <= user_permissions

    async def principals(self) -> list[str]:
        if get_config("feature.role_based_permission"):
            from remarkable.service.user import get_user_permissions

            user_permissions = await get_user_permissions(self.id)
            user_permissions = set(user_permissions)
        else:
            user_permissions = self.all_perms
        return [f"user:{self.id}"] + [f"perm:{p}" for p in user_permissions]

    @classmethod
    def sync_get_or_create_default_user(cls, user_name: str) -> "NewAdminUser":
        from remarkable.service.user import gen_password, gen_salt

        if user := cls.get_or_none(cls.name == user_name):
            return user

        salt = gen_salt()
        password = gen_password(user_name, salt)
        user_info = {
            "name": user_name,
            "permission": FeatureSchema.base_perms_to_db(),
            "ext_id": "",
            "password": password,
            "salt": salt,
        }
        default_user = cls(**user_info)
        default_user.save()

        return default_user

    @classmethod
    async def get_user_name_map(cls):
        user_map = dict(await pw_db.execute(cls.select(cls.id, cls.name).tuples()))
        return user_map

    @property
    def is_gf_oa_user(self):
        return get_config("client.name") == "gffund" and self.data.get("oa_user")


class MockTokenUser(NewAdminUser):
    async def has_perms(self, *required_perms: str, strategy: str = "any"):
        return True


ADMIN = NewAdminUser(id=ADMIN_ID, name=ADMIN_NAME)
TokenUser = MockTokenUser(id=-2, name="token|nekot")
