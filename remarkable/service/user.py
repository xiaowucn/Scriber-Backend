import hashlib
import random
import string

from remarkable.config import get_config
from remarkable.db import pw_db
from remarkable.models.new_group import CMFUserGroupRef


def gen_salt():
    return "".join(random.sample(string.printable, k=16))


def gen_password(plain, salt):
    return hashlib.md5((plain + salt).encode("utf8")).hexdigest()


def validate_password(passwd: str) -> str:
    if len(passwd) < 6 or len(passwd) > 128:
        return "The password length must be between 6-128. Please re-enter"
    has_ascii_letters = False
    has_digits = False
    has_special_notation = False
    for char in passwd:
        if char.isupper() or char.islower():
            has_ascii_letters = True
        elif char.isdigit():
            has_digits = True
        elif char in string.punctuation:
            has_special_notation = True
        if has_ascii_letters and has_digits and has_special_notation:
            return ""

    if not has_ascii_letters:
        return "Your password must contain at least one ASCII letter"
    if not has_digits:
        return "Your password must contain at least one number"
    return "Your Password must contains at least one special notation"


async def get_user_permissions(user_id):
    from remarkable.models.new_permission import Permission
    from remarkable.models.new_role import Role
    from remarkable.models.new_role_permission import RolePermissionRef
    from remarkable.models.new_user import NewAdminUser
    from remarkable.models.new_user_role import UserRoleRef

    query = Permission.select(Permission.name).join(RolePermissionRef).join(Role).join(UserRoleRef).join(NewAdminUser)

    items = await pw_db.execute(query.where(NewAdminUser.id == user_id))
    return [item.name for item in items]


async def update_user_refs(user_id, **kwargs):
    if get_config("feature.enable_user_group"):
        group_ids = kwargs.get("group_ids") or []
        if isinstance(group_ids, str):
            group_ids = [int(x) for x in group_ids.split(",")]
        async with pw_db.atomic():
            await CMFUserGroupRef.update_refs(user_id, group_ids)
