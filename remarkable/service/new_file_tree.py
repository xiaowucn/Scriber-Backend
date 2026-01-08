import logging
from collections import defaultdict

import peewee
from peewee import JOIN, Case, fn

from remarkable.common.constants import AIStatus, QuestionStatus, TagType
from remarkable.common.exceptions import CustomError
from remarkable.db import pw_db
from remarkable.models.new_file import NewFile
from remarkable.models.new_user import NewAdminUser
from remarkable.pw_models.model import NewFileTree, NewMold, NewTag, NewTagRelation
from remarkable.pw_models.question import NewQuestion
from remarkable.pw_orm import func


class NewFileTreeService:
    @staticmethod
    async def exist(tid, name):
        tree = await NewFileTree.find_by_kwargs(ptree_id=tid, name=name)
        if not tree:
            tree = await NewFile.find_by_kwargs(tree_id=tid, name=name)
        return bool(tree)

    @staticmethod
    async def find_by_id_name(tid, name):
        tree = await NewFileTree.find_by_kwargs(ptree_id=tid, name=name)
        if not tree:
            tree = await NewFile.find_by_kwargs(tree_id=tid, name=name)
        return tree

    @classmethod
    async def create(cls, tid, uid, pid, name, default_molds=None, inherit_parent_molds=True, **kwargs):
        """创建目录"""
        exists = await NewFileTreeService.exist(tid, name)
        if exists:
            raise CustomError(_("Tree name is existed"))
        if not default_molds and inherit_parent_molds:
            default_molds = await NewFileTree.find_default_molds(tid)
        new_tree = await pw_db.create(
            NewFileTree,
            ptree_id=tid,
            pid=pid,
            name=name,
            uid=uid,
            default_molds=default_molds,
            **kwargs,
        )
        return new_tree

    @classmethod
    async def get_or_create(cls, tid, uid, pid, name, default_molds=None):
        """查找目录，不存在则创建"""
        tree = await NewFileTree.find_by_kwargs(ptree_id=tid, name=name)
        if tree:
            return tree
        if not default_molds:
            default_molds = await NewFileTree.find_default_molds(tid)
        new_tree = await pw_db.create(
            NewFileTree,
            ptree_id=tid,
            pid=pid,
            name=name,
            uid=uid,
            default_molds=default_molds,
        )
        return new_tree

    @classmethod
    async def update(cls, tree, param):
        name = param.get("name")
        if name and tree.name != name:
            exists = await NewFileTreeService.exist(tree.ptree_id, param.get("name"))
            if exists:
                raise CustomError(_("Tree name is existed"))

        async with pw_db.atomic():
            await tree.update_(**param)

            molds = param.get("default_molds")
            if molds is not None:
                await NewFileTreeService.update_child_molds(tree, molds)

            return tree

    @staticmethod
    async def get_by_default_molds(molds: list[int]):
        query = NewFileTree.select().where(NewFileTree.default_molds.contains_any(molds))
        trees = await pw_db.execute(query)
        return list(trees)

    @classmethod
    async def update_child_molds(cls, tree: NewFileTree, molds: list[int]) -> list[NewFile]:
        """更新文件夹内所有未关联schema的子节点"""
        files = []
        await tree.update_(default_molds=molds)
        files.extend(await cls.update_child_files_mold(tree, molds))
        child_trees = await NewFileTree.find_by_kwargs(delegate="all", ptree_id=tree.id, default_molds=[])
        for child_tree in child_trees:
            logging.info("update tree %s, form mold: %s", child_tree.id, molds)
            files.extend(await cls.update_child_molds(child_tree, molds))
        return files

    @staticmethod
    async def update_child_files_mold(tree: NewFileTree, molds: list[int]):
        """更新文件夹内所有未关联schema的文件"""
        from remarkable.service.new_file import NewFileService

        files = await NewFile.find_by_kwargs(delegate="all", tree_id=tree.id, molds=[])
        for file in files:
            await NewFileService.update_molds(file, molds)
        return files

    @staticmethod
    async def get_related_tree_ids(tree_id: int) -> list[int]:
        tree_ids = []

        async def find_sub_dir(dir_id):
            file_trees = await NewFileTree.find_by_kwargs(ptree_id=dir_id, delegate="all")
            if file_trees:
                for file_tree in file_trees:
                    tree_ids.append(file_tree.id)
                    await find_sub_dir(file_tree.id)

        tree_ids.append(tree_id)
        await find_sub_dir(tree_id)

        return tree_ids

    @staticmethod
    async def get_all_parent_trees(tree_ids: list[int]):
        own = NewFileTree.select().where(NewFileTree.id.in_(tree_ids)).cte("base", recursive=True)
        parent = NewFileTree.alias("parent")
        recursive = parent.select().join(own, on=(own.c.ptree_id == parent.id))
        cte = own.union_all(recursive)
        subquery = cte.select_from(cte.c.id, cte.c.name, cte.c.ptree_id, cte.c.meta)
        exist_query = fn.EXISTS(subquery.where(cte.c.id == NewFileTree.id))
        return await pw_db.prefetch(NewFileTree.select().where(exist_query).order_by(NewFileTree.id))

    @staticmethod
    async def get_all_child_trees(rtree_ids: list[int]):
        parent = NewFileTree.select().where(NewFileTree.ptree_id.in_(rtree_ids)).cte("base", recursive=True)
        child = NewFileTree.alias("child")
        recursive = child.select().join(parent, on=(child.ptree_id == parent.c.id))
        cte = parent.union_all(recursive)
        subquery = cte.select_from(cte.c.id, cte.c.name, cte.c.ptree_id, cte.c.meta)
        exist_query = peewee.fn.EXISTS(subquery.select().where(cte.c.id == NewFileTree.id))
        return await pw_db.prefetch(NewFileTree.select().where(exist_query).order_by(NewFileTree.id))

    @staticmethod
    async def get_ai_status_summary(prj_id, tree_ids=None, mold_ids=None):
        cond = NewFile.pid == int(prj_id)
        question_cond = NewQuestion.fid == NewFile.id
        question_cond &= NewQuestion.deleted_utc == 0
        if tree_ids is not None:
            cond &= NewFile.tree_id.in_(tree_ids)
        if mold_ids is not None:
            cond &= NewFile.molds.contains_any(mold_ids) | (NewFile.molds == [])
            question_cond &= NewQuestion.mold.in_(mold_ids)

        query = (
            NewFile.select(
                fn.COUNT(NewFile.id).alias("total_file"),
                fn.COUNT(NewQuestion.id).alias("total_question"),
                func._sum(Case(None, [(NewQuestion.ai_status == AIStatus.DOING, 1)], 0)).alias("predicting"),
                func._sum(Case(None, [(NewQuestion.ai_status == AIStatus.FINISH, 1)], 0)).alias("predicted"),
                func._sum(Case(None, [(NewQuestion.status == QuestionStatus.FINISH, 1)], 0)).alias("marked"),
                func._sum(Case(None, [(NewQuestion.status == QuestionStatus.DISACCORD, 1)], 0)).alias("conflicted"),
                func._sum(
                    Case(
                        None,
                        [(NewQuestion.status.in_([QuestionStatus.ACCORDANCE, QuestionStatus.STANDARD_CONFIRMED]), 1)],
                        0,
                    )
                ).alias("finished"),
                func._sum(NewFile.page).alias("total_page"),
            )
            .join(NewQuestion, join_type=peewee.JOIN.LEFT_OUTER, on=question_cond, include_deleted=True)
            .where(cond)
        )
        count_obj = await pw_db.first(query)
        return count_obj

    @staticmethod
    async def get_files_and_questions_by_tree(tid, offset, need_file_count):
        file_tag = (
            NewTagRelation.select(
                NewTagRelation.relational_id.alias("file_id"),
                NewTag.id,
            )
            .join(NewTag, on=(NewTagRelation.tag_id == NewTag.id))
            .where(NewTag.tag_type == TagType.FILE.value)
            .alias("file_tag")
        )
        query = (
            NewFile.select(
                NewFile,
                NewAdminUser.name.alias("user_name"),
                fn.array_remove(fn.array_agg(file_tag.c.id.distinct()), None).alias("tags"),
            )
            .join(NewAdminUser, on=(NewFile.uid == NewAdminUser.id), join_type=JOIN.LEFT_OUTER)
            .join(file_tag, on=(NewFile.id == file_tag.c.file_id), join_type=JOIN.LEFT_OUTER)
            .where(NewFile.tree_id == tid)
            .group_by(NewFile.id, NewAdminUser.name)
            .order_by(NewFile.id.desc())
            .dicts()
        )
        query = query.offset(offset).limit(need_file_count)
        files = list(await pw_db.execute(query))
        file_ids = [file["id"] for file in files]
        question_query = (
            NewQuestion.select(
                NewQuestion.id,
                NewQuestion.fid,
                NewQuestion.mold,
                NewQuestion.ai_status,
                NewQuestion.health,
                NewQuestion.updated_utc,
                NewQuestion.fill_in_user,
                NewQuestion.data_updated_utc,
                NewQuestion.fill_in_status,
                NewQuestion.progress,
                NewQuestion.status,
                NewQuestion.name,
                NewQuestion.num,
                NewQuestion.mark_uids,
                NewQuestion.mark_users,
                fn.COALESCE(NewQuestion.origin_health, 1).alias("origin_health"),
                NewMold.name.alias("mold_name"),
                NewMold.mold_type,
            )
            .join(NewMold, on=(NewQuestion.mold == NewMold.id))
            .where(NewQuestion.fid.in_(file_ids), NewQuestion.deleted_utc == 0)
            .order_by(NewQuestion.fid.desc(), NewQuestion.mold)
            .dicts()
        )
        question_by_fid = defaultdict(list)
        for question in await pw_db.execute(question_query):
            question_by_fid[question["fid"]].append(question)

        for file in files:
            file["questions"] = question_by_fid[file["id"]]
            file["pid"] = file.pop("project")  # 保持与接口文档一致

        return files


async def get_crumbs(tree_id: int) -> list[dict]:
    from remarkable.pw_models.model import NewFileTree

    own = NewFileTree.select().where(NewFileTree.id == tree_id).cte("base", recursive=True)
    parent = NewFileTree.alias("parent")
    recursive = parent.select().join(own, on=(own.c.ptree_id == parent.id))
    cte = own.union_all(recursive)
    subquery = cte.select_from(cte.c.id, cte.c.name, cte.c.ptree_id, cte.c.meta)
    exist_query = fn.EXISTS(subquery.where(cte.c.id == NewFileTree.id))
    trees = await pw_db.prefetch(NewFileTree.select().where(exist_query).order_by(NewFileTree.id))
    return [
        {
            "id": tree.id,
            "name": tree.name,
            "meta": tree.meta,
            "default_molds": tree.default_molds,
            "default_scenario_id": tree.default_scenario_id,
            "default_task_type": tree.default_task_type,
        }
        for tree in trees
    ]
