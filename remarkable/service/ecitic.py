from remarkable.db import pw_db
from remarkable.models.ecitic import EciticFileInfo
from remarkable.models.new_file import NewFile
from remarkable.service.new_file import NewFileService


class EciticTGFileService(NewFileService):
    @classmethod
    async def create_file(
        cls,
        name: str,
        body: bytes,
        molds: list[int],
        pid: int,
        tree_id: int,
        uid: int,
        task_type: int,
        templates: list[int],
        version: str,
        group_name: str,
        stat_after_push: bool,
    ) -> NewFile:
        file = await super().create_file(name, body, molds, pid, tree_id, uid, task_type=task_type)
        await pw_db.create(
            EciticFileInfo,
            file_id=file.id,
            templates=templates,
            version=version,
            group_name=group_name,
            stat_after_push=stat_after_push,
        )
        return file
