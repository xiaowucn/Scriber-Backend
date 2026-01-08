# from collections import Counter
# from collections.abc import AsyncGenerator
# from contextlib import asynccontextmanager
# from dataclasses import dataclass
# from typing import Generic, Optional, TypeVar
#
# from sqlalchemy import and_, desc
#
# from remarkable.common.constants import FillInStatus, QuestionStatus
# from remarkable.common.util import generate_timestamp
# from remarkable.db import db
# from remarkable.models.file import File, FileProject
# from remarkable.models.mold import Mold
# from remarkable.models.time_record import TimeRecord
# from remarkable.models.user import User
#
# # from remarkable.plugins.cgs.models import AuditStatus
#
# ModelT = TypeVar("ModelT")
#
#
# class GinoReadService(Generic[ModelT]):
#     model_type
#
#     async def get_one_or_none(self, *filters, load=dict | None, **kwargs) -> ModelT:
#         statement = self.model_type.query
#         if filters:
#             statement = statement.where(*filters)
#
#         for name, value in kwargs.items():
#             statement = statement.where(getattr(self.model_type, name) == value)
#
#         return await statement.gino.one_or_none()
#
#     async def get_one(self, *filters, **kwargs) -> ModelT:
#         statement = self.model_type.query
#         if filters:
#             statement = statement.where(*filters)
#
#         for name, value in kwargs.items():
#             statement = statement.where(getattr(self.model_type, name) == value)
#
#         return await statement.gino.one()
#
#     async def list(self, *filters, include_deleted: bool = False, **kwargs) -> list[ModelT]:
#         statement = self.model_type.query
#         if filters:
#             statement = statement.where(*filters)
#
#         if hasattr(self.model_type, "deleted_utc"):
#             if include_deleted:
#                 statement = statement.where(self.model_type.deleted_utc > 0)
#             else:
#                 statement = statement.where(self.model_type.deleted_utc == 0)
#
#         for name, value in kwargs.items():
#             statement = statement.where(getattr(self.model_type, name) == value)
#
#         return await statement.gino.all()
#
#     async def list_and_count(self, *filters, include_deleted: bool = False, **kwargs):
#         pass
#
#
# class GinoReadWriteService(GinoReadService[ModelT]):
#     async def create(self, data: dict) -> ModelT:
#         return await self.model_type(**data).create()
#
#     async def create_many(self, data: list[dict]) -> ModelT:
#         return await self.model_type.insert().gino.all(data)
#
#     async def update(self, item: int | ModelT, data: dict, update_timestamp: bool = True):
#         instance = item
#         if isinstance(item, int):
#             instance: ModelT = await self.model_type.get(item)
#
#         if update_timestamp and hasattr(self.model_type, "updated_utc"):
#             data["updated_utc"] = generate_timestamp()
#
#         assert instance is not None, f"Can't update model<{self.model_type.__class__.__name__}>"
#
#         await instance.update(**data).apply()
#
#
# class UserDbService(GinoReadWriteService[User]):
#     model_type = User
#
#
# class FileDbService(GinoReadWriteService[File]):
#     model_type = File
#
#     @staticmethod
#     async def get_same_file(file_hash: str):
#         same_file = (
#             await File.query.where(and_(File.hash == file_hash, File.pdfinsight.isnot(None)))
#             .order_by(desc(File.id))
#             .gino.first()
#         )
#
#         return same_file
#
#     @staticmethod
#     async def get_sibling_molds(file: File):
#         mold_counter = Counter()
#         peer_files = (
#             await File.select("molds")
#             .where(and_(File.deleted_utc == 0, File.tree_id == file.tree_id, File.id != file.id))
#             .gino.all()
#         )
#         for (molds,) in peer_files:
#             mold_counter.update(molds)
#
#         return mold_counter
#
#
# class ProjectDbService(GinoReadWriteService[FileProject]):
#     model_type = FileProject
#
#
# # class AuditStatusDbService(GinoReadWriteService[AuditStatus]):
# #     model_type = AuditStatus
#
#
# class MoldDbService(GinoReadWriteService[Mold]):
#     model_type = Mold
#
#     async def verify_enable_ocr(self, mold_ids: list[int], force_ocr_mold_items: list[int | str]):
#         force_ocr = False
#         molds = await self.list(self.model_type.id.in_(mold_ids))
#         for mold in molds:
#             if mold.id in [i for i in force_ocr_mold_items if isinstance(i, int)] or mold.name in [
#                 i for i in force_ocr_mold_items if isinstance(i, str)
#             ]:
#                 force_ocr = True
#                 break
#
#         return force_ocr
#
#
# class QuestionDbService(GinoReadWriteService[Question]):
#     model_type = Question
#
#     @staticmethod
#     async def get_master_question(fid: int):
#         """
#         当前一个file只会有一个master_question
#         :param fid:
#         :return:
#         """
#         cond = Mold.master.is_(None)
#         cond &= Question.fid == fid
#         cond &= Question.deleted_utc == 0
#         return (
#             await Question.load(_mold=Mold.on(Question.mold == Mold.id))
#             .query.where(cond)
#             .order_by(Mold.id)
#             .gino.first()
#         )
#
#     async def create_for_file(
#         self, file: File, name: Optional[str] = None, num: Optional[str] = None, default_health: int = 1
#     ):
#         rows = await self.model_type.select("id").where(self.model_type.fid == file.id).gino.all()
#         question_ids = {r.id for r in rows}
#
#         items = []
#         for mold_id in file.molds:
#             if mold_id not in question_ids:
#                 data = {
#                     "data": {"file_id": file.id},
#                     "checksum": self.model_type.gen_checksum(file.id, mold_id),
#                     "fid": file.id,
#                     "health": default_health,
#                     "origin_health": default_health,
#                     "status": QuestionStatus.TODO.value,
#                     "ai_status": await self.model_type._initialize_ai_status(mold_id),
#                     "name": name,
#                     "num": num,
#                     "fill_in_status": FillInStatus.TODO.value,
#                     "mold": mold_id,
#                 }
#                 items.append(data)
#
#         for item in items:
#             await self.create(item)
#
#
# class TimeRecordDbService(GinoReadWriteService[TimeRecord]):
#     model_type = TimeRecord
#
#
# @dataclass
# class GinoService:
#     projects: ProjectDbService
#     files: FileDbService
#     questions: QuestionDbService
#     users: UserDbService
#     molds: MoldDbService
#     time_records: TimeRecordDbService
#     # audit_statuses: AuditStatusDbService
#
#     @classmethod
#     def create(cls):
#         return GinoService(
#             projects=ProjectDbService(),
#             questions=QuestionDbService(),
#             users=UserDbService(),
#             files=FileDbService(),
#             molds=MoldDbService(),
#             time_records=TimeRecordDbService(),
#             # audit_statuses=AuditStatusDbService(),
#         )
#
#     @classmethod
#     @asynccontextmanager
#     async def get_service(cls, with_tx: bool = False) -> AsyncGenerator["GinoService", None]:
#         async with db.with_bind(echo=True):
#             if not with_tx:
#                 yield GinoService(
#                     projects=ProjectDbService(),
#                     questions=QuestionDbService(),
#                     users=UserDbService(),
#                     files=FileDbService(),
#                     molds=MoldDbService(),
#                     time_records=TimeRecordDbService(),
#                     # audit_statuses=AuditStatusDbService(),
#                 )
#             else:
#                 async with db.transaction():
#                     yield GinoService(
#                         projects=ProjectDbService(),
#                         questions=QuestionDbService(),
#                         users=UserDbService(),
#                         files=FileDbService(),
#                         molds=MoldDbService(),
#                         time_records=TimeRecordDbService(),
#                         # audit_statuses=AuditStatusDbService(),
#                     )
#
#
# if __name__ == "__main__":
#     import asyncio
#
#     async def run():
#         async with GinoService.get_service(with_tx=True) as db_service:
#             user = await db_service.users.get_one_or_none(User.id == 1, login_count=290)
#             if user:
#                 print(user, user.is_admin, user.login_count)
#                 await db_service.users.update(user, {"login_count": 291})
#                 await db_service.users.update(user.id, {"login_count": 290})
#
#     asyncio.run(run())
