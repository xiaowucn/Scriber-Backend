import sys

from remarkable.common.util import loop_wrapper
from remarkable.db import pw_db
from remarkable.models.new_file import NewFile
from remarkable.pw_models.model import NewFileMeta, NewFileProject, NewFileTree
from remarkable.pw_models.question import NewQuestion


@loop_wrapper
async def recovery_project(pid=None):
    async with pw_db.atomic():
        await pw_db.execute(NewFileProject.update(deleted_utc=0).where(NewFileProject.id == pid))
        await pw_db.execute(NewFileTree.update(deleted_utc=0).where(NewFileTree.pid == pid))
        await pw_db.execute(NewFile.update(deleted_utc=0).where(NewFile.pid == pid))

        files = await pw_db.execute(NewFile.select(NewFile.id).where(NewFile.pid == pid))
        file_ids = [file.id for file in files]
        await pw_db.execute(NewQuestion.update(deleted_utc=0).where(NewQuestion.fid.in_(file_ids)))
        await pw_db.execute(NewFileMeta.update(deleted_utc=0).where(NewFileMeta.file_id.in_(file_ids)))


if __name__ == "__main__":
    PID = sys.argv[1] if len(sys.argv) > 1 else None
    recovery_project(PID)
