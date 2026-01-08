from contextlib import asynccontextmanager
from dataclasses import dataclass, field
from typing import AsyncGenerator, Generic, Type, TypeVar

import peewee
from peewee import DoesNotExist, fn

from remarkable.common.constants import AIStatus, FillInStatus, LLMStatus, MoldType, QuestionStatus
from remarkable.config import get_config
from remarkable.db import pw_db
from remarkable.models.new_file import NewFile
from remarkable.models.new_user import NewAdminUser
from remarkable.pw_models.model import NewFileProject, NewFileTree, NewMold, NewTimeRecord
from remarkable.pw_models.question import NewQuestion
from remarkable.pw_orm import func

ModelT = TypeVar("ModelT")


class PeeweeReadService(Generic[ModelT]):
    model_type: Type[ModelT]  # noqa: UP006

    async def get_one_or_none(self, *filters, **kwargs) -> ModelT:
        try:
            return await pw_db.get(self.model_type, *filters, **kwargs)
        except DoesNotExist:
            return None

    async def get_one(self, *filters, **kwargs) -> ModelT:
        return await pw_db.get(self.model_type, *filters, **kwargs)

    async def list(self, *filters, include_deleted: bool = False, **kwargs) -> list[ModelT]:
        statement = self.model_type.select(include_deleted=include_deleted)
        if filters:
            statement = statement.where(*filters)

        for name, value in kwargs.items():
            statement = statement.where(getattr(self.model_type, name) == value)

        return await pw_db.execute(statement)


class PeeweeReadWriteService(PeeweeReadService[ModelT]):
    async def create(self, data: dict) -> ModelT:
        return await pw_db.create(self.model_type, **data)

    async def create_many(self, data: list[dict]) -> ModelT:
        return await self.model_type.insert().gino.all(data)

    async def update(self, item: int | ModelT, data: dict, update_timestamp: bool = True):
        instance = item
        if isinstance(item, int):
            instance: ModelT = await self.get_one(id=item)

        assert instance is not None, f"Can't update model<{self.model_type.__class__.__name__}>"

        await pw_db.update(instance, update_timestamp=update_timestamp, **data)


class UserDbService(PeeweeReadWriteService[NewAdminUser]):
    model_type = NewAdminUser


class FileDbService(PeeweeReadWriteService[NewFile]):
    model_type = NewFile

    @staticmethod
    async def get_same_file(file_hash: str):
        same_file = await pw_db.first(
            NewFile.select()
            .where(
                NewFile.hash == file_hash,
                NewFile.pdfinsight.is_null(False),
            )
            .order_by(NewFile.id.desc())
        )

        return same_file


class ProjectDbService(PeeweeReadWriteService[NewFileProject]):
    model_type = NewFileProject


class MoldDbService(PeeweeReadWriteService[NewMold]):
    model_type = NewMold

    async def verify_enable_ocr(self, mold_ids: list[int], force_ocr_mold_items: list[int | str]):
        force_ocr = False
        molds = await self.list(self.model_type.id.in_(mold_ids))
        for mold in molds:
            if mold.id in [i for i in force_ocr_mold_items if isinstance(i, int)] or mold.name in [
                i for i in force_ocr_mold_items if isinstance(i, str)
            ]:
                force_ocr = True
                break

        return force_ocr

    async def get_related_molds(self, fid, master_question_mid):
        if get_config("data_flow.file_answer.with_all_molds"):
            file = await NewFile.find_by_id(fid)
            molds = await pw_db.execute(NewMold.select().where(NewMold.id.in_(file.molds)).order_by(NewMold.id))
        else:
            molds = await NewMold.get_related_molds(master_question_mid)
        return molds


class FileTreeDbService(PeeweeReadWriteService[NewFileTree]):
    model_type = NewFileTree

    async def delete_by_tree(self, tree: NewFileTree):
        files = await pw_db.execute(NewFile.select().where(NewFile.tree_id == tree.id))
        for file in files:
            await file.soft_delete()
        await tree.soft_delete()
        sub_trees = await self.list(NewFileTree.ptree_id == tree.id)
        for tree in sub_trees:
            await self.delete_by_tree(tree)


class QuestionDbService(PeeweeReadWriteService[NewQuestion]):
    model_type = NewQuestion

    async def create_for_file(
        self, file: NewFile, name: str | None = None, num: str | None = None, default_health: int = 1
    ):
        question_ids = await pw_db.scalars(
            self.model_type.select(self.model_type.id).where(self.model_type.fid == file.id)
        )

        items = []
        for mold_id in file.molds:
            if mold_id not in question_ids:
                mold_ins = await NewMold.find_by_id(mold_id)
                exclusive_status = await self.model_type._initialize_ai_status(mold_ins)
                if mold_ins.mold_type == MoldType.COMPLEX.value or exclusive_status != AIStatus.TODO:
                    llm_status = LLMStatus.SKIP_PREDICT
                else:
                    llm_status = LLMStatus.TODO
                data = {
                    "data": {"file_id": file.id},
                    "checksum": self.model_type.gen_checksum(file.id, mold_id),
                    "fid": file.id,
                    "health": default_health,
                    "origin_health": default_health,
                    "status": QuestionStatus.TODO.value,
                    "ai_status": exclusive_status,
                    "exclusive_status": exclusive_status,
                    "llm_status": llm_status,
                    "name": name,
                    "num": num,
                    "fill_in_status": FillInStatus.TODO.value,
                    "mold": mold_id,
                }
                items.append(data)

        for item in items:
            await self.create(item)

    def group_by_fid(self, *conditions) -> peewee.CTE:
        default_health = get_config("web.default_question_health", 2)
        return (
            NewQuestion.select(
                func.ARRAY_AGG(
                    NewQuestion.jsonb_build_object(
                        "id",
                        "mold",
                        "ai_status",
                        "health",
                        "fill_in_user",
                        "data_updated_utc",
                        "updated_utc",
                        "fill_in_status",
                        "progress",
                        "status",
                        "name",
                        "num",
                        "mark_uids",
                        "mark_users",
                        origin_health=fn.COALESCE(NewQuestion.origin_health, default_health),
                        mold_name=NewMold.name,
                    )
                ).alias("questions"),
                NewQuestion.fid,
            )
            .join(NewMold, on=(NewQuestion.mold == NewMold.id))
            .where(*conditions)
            .group_by(NewQuestion.fid)
            .cte("question_cte")
        )


class TimeRecordDbService(PeeweeReadWriteService[NewTimeRecord]):
    model_type = NewTimeRecord


@dataclass
class PeeweeService:
    projects: ProjectDbService = field(default_factory=ProjectDbService)
    files: FileDbService = field(default_factory=FileDbService)
    questions: QuestionDbService = field(default_factory=QuestionDbService)
    users: UserDbService = field(default_factory=UserDbService)

    trees: FileTreeDbService = field(default_factory=FileTreeDbService)
    time_records: TimeRecordDbService = field(default_factory=TimeRecordDbService)

    molds: MoldDbService = field(default_factory=MoldDbService)
    # audit_statuses: AuditStatusDbService

    @classmethod
    def create(cls):
        return cls(
            # projects=ProjectDbService(),
            # molds=MoldDbService(),
            # audit_statuses=AuditStatusDbService(),
        )

    @classmethod
    @asynccontextmanager
    async def get_service(cls, with_tx: bool = False) -> AsyncGenerator["PeeweeService", None]:
        service = cls.create()
        if not with_tx:
            yield service
        else:
            async with pw_db.atomic():
                yield service


if __name__ == "__main__":
    import asyncio

    # logger = logging.getLogger("peewee")
    # logger.addHandler(logging.StreamHandler())
    # logger.setLevel(logging.DEBUG)

    async def run():
        async with PeeweeService.get_service(with_tx=True) as db_service:
            user = await db_service.users.get_one_or_none(NewAdminUser.id == 1, login_count=290)
            if user:
                print(user, user.is_admin, user.login_count)
                await db_service.users.update(user, {"login_count": 291})
                await db_service.users.update(user.id, {"login_count": 290})

            files = await db_service.users.list(NewAdminUser.id < 10, name="admin")
            print(len(files))

    asyncio.run(run())
