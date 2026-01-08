import speedy.peewee_plus.orm
from peewee import JOIN, fn

from remarkable.common.exceptions import CustomError
from remarkable.db import pw_db
from remarkable.models.new_group import CMFGroup, CMFGroupRef, CMFUserGroupRef
from remarkable.models.query_helper import AsyncPagination
from remarkable.pw_models.model import NewFileTree, NewMold
from remarkable.pw_orm import func


class CMFGroupService:
    @staticmethod
    def get_groups_query(group_ids=None):
        file_tree_cte = (
            CMFGroupRef.select(
                CMFGroupRef.cmf_group_id, func.ARRAY_AGG(CMFGroupRef.file_tree_id).alias("file_tree_ids")
            )
            .join(NewFileTree)  # 排除掉已被删除的file_tree
            .where(CMFGroupRef.file_tree_id.is_null(False))
            .group_by(CMFGroupRef.cmf_group_id)
            .cte("file_tree_cte")
        )

        mold_cte = (
            CMFGroupRef.select(CMFGroupRef.cmf_group_id, func.ARRAY_AGG(CMFGroupRef.mold_id).alias("mold_ids"))
            .join(NewMold)  # 排除掉已被删除的mold
            .where(CMFGroupRef.mold_id.is_null(False))
            .group_by(CMFGroupRef.cmf_group_id)
            .cte("mold_cte")
        )

        cond = speedy.peewee_plus.orm.TRUE
        query = (
            CMFGroup.select(
                CMFGroup.id,
                CMFGroup.name,
                fn.COALESCE(file_tree_cte.c.file_tree_ids, func.build_array()).alias("file_tree_ids"),
                fn.COALESCE(mold_cte.c.mold_ids, func.build_array()).alias("mold_ids"),
            )
            .join(file_tree_cte, JOIN.LEFT_OUTER, on=(CMFGroup.id == file_tree_cte.c.cmf_group_id))
            .join(mold_cte, JOIN.LEFT_OUTER, on=(CMFGroup.id == mold_cte.c.cmf_group_id))
        )

        if group_ids is not None:
            cond &= CMFGroup.id.in_(group_ids)

        query = query.where(cond)
        query = query.with_cte(file_tree_cte, mold_cte).order_by(CMFGroup.id.desc()).dicts()
        return query

    @classmethod
    async def get_pagination_groups(cls, page: int, size: int, group_ids: list[int] = None):
        query = CMFGroupService.get_groups_query(group_ids)
        data = await AsyncPagination(query, page=page, size=size).data()
        return data

    @classmethod
    async def get_user_groups(cls, user_id):
        group_ids = await CMFUserGroupRef.get_user_group_ids(user_id)
        query = CMFGroupService.get_groups_query(group_ids)
        groups = await pw_db.execute(query)
        return list(groups)

    @classmethod
    async def get_groups(cls, group_ids: list[int]):
        query = CMFGroupService.get_groups_query(group_ids)
        groups = await pw_db.execute(query)
        return list(groups)

    @classmethod
    async def get_user_group_molds(cls, user_id):
        groups = await cls.get_user_groups(user_id)
        mold_ids = []
        for group in groups:
            mold_ids.extend(group["mold_ids"])
        return mold_ids

    @classmethod
    async def get_user_group_file_trees(cls, user_id) -> list[int]:
        groups = await cls.get_user_groups(user_id)
        file_tree_ids = []
        for group in groups:
            file_tree_ids.extend(group["file_tree_ids"])
        return file_tree_ids

    @staticmethod
    async def get_mold_groups(mold_id, group_ids=None):
        cond = CMFGroupRef.mold == mold_id
        if group_ids is not None:
            cond &= CMFGroup.id.in_(group_ids)

        query = CMFGroup.select(CMFGroup.id, CMFGroup.name).where(cond).join(CMFGroupRef)
        return await pw_db.execute(query)

    @staticmethod
    async def get_file_tree_groups(file_tree_id, group_ids=None):
        cond = CMFGroupRef.file_tree == file_tree_id
        if group_ids is not None:
            cond &= CMFGroup.id.in_(group_ids)
        query = CMFGroup.select(CMFGroup.id, CMFGroup.name).where(cond).join(CMFGroupRef)
        return await pw_db.execute(query)

    @staticmethod
    async def create(name: str, file_tree_ids: list[int], mold_ids: list[int]):
        if not await NewMold.all_ids_exists(mold_ids):
            raise CustomError(_("Not all ids valid."))
        if not await NewFileTree.all_ids_exists(file_tree_ids):
            raise CustomError(_("Not all ids valid."))

        async with pw_db.atomic():
            group = await CMFGroup.create(name=name)
            await CMFGroupRef.update_refs_for_file_tree(group.id, file_tree_ids)
            await CMFGroupRef.update_refs_for_mold(group.id, mold_ids)

    @staticmethod
    async def update(group_id: int, name: str = None, file_tree_ids: list[int] = None, mold_ids: list[int] = None):
        if mold_ids and not await NewMold.all_ids_exists(mold_ids):
            raise CustomError(_("Not all ids valid."))
        if file_tree_ids and not await NewFileTree.all_ids_exists(file_tree_ids):
            raise CustomError(_("Not all ids valid."))
        async with pw_db.atomic():
            if name:
                await CMFGroup.update_by_pk(group_id, name=name)
            if file_tree_ids is not None:
                await CMFGroupRef.update_refs_for_file_tree(group_id, file_tree_ids)
            if mold_ids is not None:
                await CMFGroupRef.update_refs_for_mold(group_id, mold_ids)

    @staticmethod
    async def delete(group):
        if await pw_db.exists(
            CMFUserGroupRef.select(CMFUserGroupRef.id).where(CMFUserGroupRef.cmf_group_id == group.id)
        ):
            raise CustomError("业务组正在被用户使用")
        if await pw_db.exists(CMFGroupRef.select(CMFGroupRef.id).where(CMFGroupRef.cmf_group_id == group.id)):
            raise CustomError("业务组正在被项目或场景使用")

        await pw_db.delete(group)

    @classmethod
    async def add_group_to_tree_from_rtree(cls, tree_id, rtree_id):
        if groups := await cls.get_file_tree_groups(rtree_id):
            groups = await cls.get_groups([group.id for group in groups])
            for group in groups:
                file_tree_ids = set(group["file_tree_ids"] + [tree_id])
                await cls.update(group["id"], file_tree_ids=list(file_tree_ids))
