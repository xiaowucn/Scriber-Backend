from remarkable.models.new_file import NewFile
from remarkable.plugins.chinaamc_yx.schemas import I_SELF_CONFIG
from remarkable.pw_models.model import NewMold
from remarkable.service.new_file import NewFileService


class ChinaAmcYxFileService(NewFileService):
    @classmethod
    async def get_mids(cls, file_type: str) -> list[int]:
        return await NewMold.tolerate_schema_ids(*I_SELF_CONFIG.mold_names(file_type))

    @classmethod
    async def create(cls, project, file_name, body, file_type, uid):
        mids = await cls.get_mids(file_type)
        return await cls.create_file(
            file_name,
            body,
            mids,
            project.id,
            project.rtree_id,
            uid=uid,
            source=file_type,
        )

    @classmethod
    async def update_molds(
        cls,
        file: NewFile,
        mold_ids: list[int],
        question_name: str | None = None,
        question_num: str | None = None,
    ):
        await super().update_molds(file, mold_ids, question_name, question_num)
