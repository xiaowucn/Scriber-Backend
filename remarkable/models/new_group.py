from peewee import CharField, ForeignKeyField, IntegerField

from remarkable.db import pw_db
from remarkable.models.new_user import NewAdminUser
from remarkable.pw_models.base import BaseModel
from remarkable.pw_models.model import NewFileTree, NewMold


class CMFGroup(BaseModel):
    name = CharField(unique=True)
    description = CharField()
    created_utc = IntegerField()
    updated_utc = IntegerField()

    class Meta:
        table_name = "cmf_group"


class CMFUserGroupRef(BaseModel):
    user = ForeignKeyField(NewAdminUser, backref="user_group_refs")
    cmf_group = ForeignKeyField(CMFGroup)
    created_utc = IntegerField()

    class Meta:
        table_name = "cmf_user_group_ref"

    def to_dict(self, exclude=(user, cmf_group), extra_attrs=("user_id", "cmf_group_id"), **kwargs):
        return super().to_dict(exclude=exclude, extra_attrs=extra_attrs, **kwargs)

    @classmethod
    async def get_user_group_ids(cls, user_id):
        query = cls.select(cls.cmf_group_id).where(cls.user_id == user_id)
        return await pw_db.scalars(query)

    @classmethod
    async def update_refs(cls, user_id: int, group_ids: list[int]):
        query = cls.select(cls.cmf_group_id).where(cls.user_id == user_id)
        exist_group_ids = await pw_db.scalars(query)
        group_ids_to_add = set(group_ids) - set(exist_group_ids)
        group_ids_to_delete = set(exist_group_ids) - set(group_ids)
        group_ids_infos = [
            {
                "user_id": user_id,
                "cmf_group_id": group_id,
            }
            for group_id in group_ids_to_add
        ]

        await pw_db.execute(cls.delete().where(cls.user_id == user_id, cls.cmf_group_id.in_(group_ids_to_delete)))
        await cls.bulk_insert(group_ids_infos)


class CMFGroupRef(BaseModel):
    cmf_group = ForeignKeyField(CMFGroup, backref="group_file_tree_refs")
    file_tree = ForeignKeyField(NewFileTree)
    mold = ForeignKeyField(NewMold)
    created_utc = IntegerField()

    class Meta:
        table_name = "cmf_group_ref"

    def to_dict(
        self, exclude=(cmf_group, file_tree), extra_attrs=("cmf_group_id", "file_tree_id", "mold_id"), **kwargs
    ):
        return super().to_dict(exclude=exclude, extra_attrs=extra_attrs, **kwargs)

    @classmethod
    async def update_refs_for_file_tree(cls, cmf_group_id, file_tree_ids):
        query = cls.select(cls.file_tree_id).where(cls.cmf_group_id == cmf_group_id, ~cls.file_tree.is_null())
        exist_file_tree_ids = await pw_db.scalars(query)
        file_tree_to_add = set(file_tree_ids) - set(exist_file_tree_ids)
        file_tree_to_delete = set(exist_file_tree_ids) - set(file_tree_ids)
        file_tree_infos = [
            {
                "cmf_group_id": cmf_group_id,
                "file_tree_id": file_tree_id,
            }
            for file_tree_id in file_tree_to_add
        ]

        await pw_db.execute(
            cls.delete().where(cls.cmf_group_id == cmf_group_id, cls.file_tree_id.in_(file_tree_to_delete))
        )
        await cls.bulk_insert(file_tree_infos)

    @classmethod
    async def update_refs_for_mold(cls, cmf_group_id, mold_ids):
        query = cls.select(cls.mold_id).where(cls.cmf_group_id == cmf_group_id, ~cls.mold.is_null())
        exist_mold_ids = await pw_db.scalars(query)
        mold_to_add = set(mold_ids) - set(exist_mold_ids)
        mold_to_delete = set(exist_mold_ids) - set(mold_ids)
        mold_infos = [
            {
                "cmf_group_id": cmf_group_id,
                "mold_id": mold_id,
            }
            for mold_id in mold_to_add
        ]

        await pw_db.execute(cls.delete().where(cls.cmf_group_id == cmf_group_id, cls.mold_id.in_(mold_to_delete)))
        await cls.bulk_insert(mold_infos)

    @classmethod
    async def update_refs_for_group(
        cls, old_group_ids: list[int], new_group_ids: list[int], mold_id: int = None, file_tree_id: int = None
    ):
        group_to_add = set(new_group_ids) - set(old_group_ids)
        group_to_delete = set(old_group_ids) - set(new_group_ids)
        if mold_id:
            group_infos = [
                {
                    "cmf_group_id": group_id,
                    "mold_id": mold_id,
                }
                for group_id in group_to_add
            ]
            await pw_db.execute(cls.delete().where(cls.mold == mold_id, cls.cmf_group.in_(group_to_delete)))
            await cls.bulk_insert(group_infos)

        if file_tree_id:
            group_infos = [
                {
                    "cmf_group_id": group_id,
                    "file_tree_id": file_tree_id,
                }
                for group_id in group_to_add
            ]
            await pw_db.execute(cls.delete().where(cls.file_tree == file_tree_id, cls.cmf_group.in_(group_to_delete)))
            await cls.bulk_insert(group_infos)
