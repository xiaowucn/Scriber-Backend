from remarkable import config
from remarkable.common.enums import ClientName
from remarkable.models.cmf_china import CmfMoldModelRef
from remarkable.models.model_version import NewModelVersion


class ModelVersionService:
    @staticmethod
    async def get_enabled_version(mold: int, only_developed=False):
        client_name = config.get_config("client.name")
        if client_name == ClientName.cmfchina:
            cmf_model = await CmfMoldModelRef.get_enabled_model(mold)
            return cmf_model.id if cmf_model else None
        else:
            return await NewModelVersion.get_enabled_version(mold, only_developed)
