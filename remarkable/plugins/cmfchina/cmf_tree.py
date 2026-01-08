from collections import defaultdict

import peewee
from peewee import JOIN, fn
from speedy.peewee_plus import orm

from remarkable.db import pw_db
from remarkable.models.cmf_china import CmfFileReviewed
from remarkable.models.new_file import NewFile
from remarkable.models.new_user import NewAdminUser
from remarkable.pw_models.model import NewFileProject, NewFileTree, NewMold
from remarkable.pw_models.question import NewQuestion
from remarkable.service.new_file_tree import NewFileTreeService, get_crumbs


def filter_file_by_mold(search_mid: int = None, permissions_mold_ids: list[int] = None) -> peewee.Expression:
    cond = orm.TRUE
    if search_mid:
        # 按场景搜索条件
        cond &= NewFile.molds.contains(search_mid)
    if permissions_mold_ids is not None:
        # 按权限过滤
        # mold_ids和search_mid不一定重叠，含义不同
        cond &= NewFile.molds.contains_any(permissions_mold_ids) | (NewFile.molds == [])
    return cond


class CmfFileTreeService:
    @classmethod
    async def get_trees(
        cls,
        tree: NewFileTree,
        order_by: str,
        page: int,
        size: int,
        permissions_tree_ids: list[int] = None,
        permissions_mold_ids: list[int] = None,
        search_fid: int = None,
        search_mid: int = None,
    ):
        res = tree.to_dict()
        visible_tree_ids = None
        if permissions_tree_ids is not None:
            items = await NewFileTreeService.get_all_parent_trees(permissions_tree_ids)
            visible_tree_ids = [item.id for item in items]
        if search_mid:
            file_cond = NewFile.molds.contains(search_mid)
            file_tree_cond = NewFileTree.default_molds.contains(search_mid)
            if visible_tree_ids is not None:
                file_cond &= NewFile.tree_id.in_(visible_tree_ids)
                file_tree_cond &= NewFileTree.id.in_(visible_tree_ids)
            visible_tree_ids = await pw_db.scalars(
                NewFileTree.select(NewFileTree.id)
                .where(file_tree_cond)
                .union(NewFile.select(NewFile.tree_id).where(file_cond))
            )
            parents = await NewFileTreeService.get_all_parent_trees(visible_tree_ids)
            visible_tree_ids.extend([item.id for item in parents])
        trees = await NewFileTree.list_by_tree(int(tree.id), order_by, tree_ids=visible_tree_ids)

        if permissions_tree_ids is not None and tree.id not in permissions_tree_ids:
            all_files_count = 0
        else:
            files_cont_cond = NewFile.tree_id == tree.id
            files_cont_cond &= filter_file_by_mold(search_mid, permissions_mold_ids)
            all_files_count = await pw_db.count(NewFile.select().where(files_cont_cond))

        async def gen_files():
            start = (page - 1) * size
            end = page * size
            res["trees"] = trees[start:end]
            if permissions_tree_ids is not None and tree.id not in permissions_tree_ids:
                need_file_count = 0
            else:
                need_file_count = size - len(res["trees"])
            if need_file_count:
                file_end = end - len(trees)
                file_offset = max(file_end - size + len(res["trees"]), 0)
                res["files"] = await cls.get_files_and_questions_by_tree(
                    tree.id,
                    file_offset,
                    need_file_count,
                    order_by,
                    mold_ids=permissions_mold_ids,
                    search_mid=search_mid,
                )
            else:
                res["files"] = []

        if search_fid:
            search_file_tree_id = await pw_db.scalar(NewFile.select(NewFile.tree_id).where(NewFile.id == search_fid))
            if search_file_tree_id != tree.id:
                search_fid = None

        while True:
            await gen_files()
            if search_fid is None:
                break
            if not res.get("files"):
                break
            if search_fid in [file["id"] for file in res["files"]]:
                break
            page += 1

        res["page"] = page
        res["total"] = all_files_count + len(trees)
        res["crumbs"] = await get_crumbs(tree.id)

        project = await NewFileProject.find_by_id(res["pid"])
        res["project_public"] = project.public
        return res

    @staticmethod
    async def get_files_and_questions_by_tree(
        tid, offset, need_file_count, order_by: str, mold_ids: list[int] = None, search_mid: int = None
    ):
        file_cond = NewFile.tree_id == tid
        file_cond &= filter_file_by_mold(search_mid, mold_ids)
        query = (
            NewFile.select(
                NewFile,
                NewAdminUser.name.alias("user_name"),
                peewee.Case(
                    None,
                    [
                        (CmfFileReviewed.id.is_null(False), orm.TRUE),
                    ],
                    orm.FALSE,
                ).alias("reviewed"),
            )
            .join(NewAdminUser, on=(NewFile.uid == NewAdminUser.id), join_type=JOIN.LEFT_OUTER, include_deleted=True)
            .join(CmfFileReviewed, on=(NewFile.id == CmfFileReviewed.file_id), join_type=JOIN.LEFT_OUTER)
            .where(file_cond)
            .group_by(NewFile.id, NewAdminUser.name, CmfFileReviewed.id)
            .order_by(getattr(NewFile, order_by))
        )

        query = query.offset(offset).limit(need_file_count)
        files = list(await pw_db.execute(query.dicts()))
        file_ids = [file["id"] for file in files]
        question_cond = NewQuestion.fid.in_(file_ids)
        if mold_ids is not None:
            question_cond &= NewQuestion.mold.in_(mold_ids)
        if search_mid:
            question_cond &= NewQuestion.mold == search_mid
        question_query = (
            NewQuestion.select(
                NewQuestion.id,
                NewQuestion.fid,
                NewQuestion.mold,
                NewQuestion.ai_status,
                NewQuestion.health,
                NewQuestion.fill_in_user,
                NewQuestion.data_updated_utc,
                NewQuestion.updated_utc,
                NewQuestion.fill_in_status,
                NewQuestion.progress,
                NewQuestion.status,
                NewQuestion.name,
                NewQuestion.num,
                NewQuestion.mark_uids,
                NewQuestion.mark_users,
                fn.COALESCE(NewQuestion.origin_health, 1).alias("origin_health"),
                NewMold.name.alias("mold_name"),
            )
            .join(NewMold, on=(NewQuestion.mold == NewMold.id))
            .where(question_cond)
            .order_by(NewQuestion.fid.desc(), NewQuestion.mold)
            .dicts()
        )
        question_by_fid = defaultdict(list)
        for question in await pw_db.execute(question_query):
            question_by_fid[question["fid"]].append(question)

        for file in files:
            file["questions"] = question_by_fid[file["id"]]
            file["pid"] = file.pop("project")

        return files
