import logging
import tempfile

from aipod.rpc.client import AIClient
from grpc.aio import AioRpcError

from remarkable.common.constants import CmfFiledStatus
from remarkable.common.storage import localstorage
from remarkable.config import get_config
from remarkable.db import pw_db
from remarkable.models.cmf_china import CmfChinaEmailFileInfo, CmfFiledFileInfo, CmfFiledScript
from remarkable.models.new_file import NewFile
from remarkable.models.new_user import ADMIN
from remarkable.pdfinsight.reader import PdfinsightReader
from remarkable.pw_models.model import NewFileProject, NewMold
from remarkable.service.cmfchina.common import SAMPLE_CODE_FILE_NAME
from remarkable.service.cmfchina.filed_file_service import CmfFiledFileService
from remarkable.service.new_file import NewFileService
from remarkable.service.new_file_project import NewFileProjectService

logger = logging.getLogger(__name__)


class GJZQFiledFileService(CmfFiledFileService):
    @classmethod
    def ensure_mold(cls, data: dict):
        file_name = data["file_name"]
        top_elements = data["top_elements"]
        filed_map = {
            "私募证券投资基金基金合同": "私募-基金合同",
            "证券投资基金基金合同": "公募-基金合同",
            "资产管理计划资产管理合同": "公募-资产管理合同",
            "招募说明书": "公募-招募说明书",
        }
        mold_name = None
        for key in filed_map:
            if key in file_name:
                mold_name = filed_map[key]
                return mold_name

        if not mold_name:
            for elt in top_elements:
                if text := elt.get("text"):
                    for key in filed_map:
                        if key in text:
                            mold_name = filed_map[key]
                            return mold_name

        return mold_name

    @classmethod
    async def exec_python(cls, file: NewFile):
        logger.info(f"start GJZQ filed file<{file.id}> with python")
        mold_name = None
        try:
            _, script = await cls.get_filed_code(sample=False)
        except FileNotFoundError:
            return mold_name, "未找到分类代码文件"

        reader = PdfinsightReader(localstorage.mount(file.pdfinsight_path()))
        top_elements = reader.find_elements_near_by(index=0, amount=3, include=True)
        ctx = {
            "file_name": file.name,
            "top_elements": top_elements,
        }

        if email_file := await pw_db.first(CmfChinaEmailFileInfo.select().where(CmfChinaEmailFileInfo.fid == file.id)):
            ctx["email"] = {
                "from": email_file.from_,
                "to": email_file.to,
                "cc": email_file.cc,
                "subject": email_file.subject,
                "sent_at": email_file.sent_at,
            }

        metadata = [("x-func-name", "exec"), ("x-upstream", "scriber-cmf-china")]
        with tempfile.TemporaryDirectory() as tmpdir:
            client = AIClient(
                version="python-runner",
                address=get_config("ai.py_runner_addr"),
                datapath=tmpdir,
            )
            try:
                mold_name = await client.chaos(script, ctx=ctx, metadata=metadata)
                logger.info(f"end CmfChina filed file<{file.id}> with python")
            except AioRpcError as exp:
                logger.exception(exp)
                return mold_name, exp.details()
            except Exception as exp:
                logger.exception(exp)
                return mold_name, str(exp)

        if not mold_name:
            return mold_name, "分类失败"

        return mold_name, None

    @classmethod
    async def filed_file(cls, file):
        # 根据分类代码返回的数据，刷新文件的工程和场景
        cmf_china_file_info = await pw_db.first(CmfFiledFileInfo.select().where(CmfFiledFileInfo.fid == file.id))
        if not cmf_china_file_info:
            logger.info(f"file:{file.id} not uploaded by the filed system")
            return
        if cmf_china_file_info.status != CmfFiledStatus.WAIT:
            logger.info(f"file:{file.id} filed in progress")
            return
        cmf_china_file_info.status = CmfFiledStatus.DOING
        await pw_db.update(cmf_china_file_info, only=["status"])

        mold_name, error_info = await cls.exec_python(file)

        if error_info:
            cmf_china_file_info.status = CmfFiledStatus.FAIL
            cmf_china_file_info.fail_info = error_info
            await pw_db.update(cmf_china_file_info, only=["status", "fail_info"])
            return

        project = await NewFileProject.find_by_kwargs(name=mold_name)
        if not project:
            project = await NewFileProjectService.create(mold_name, uid=ADMIN.id)

        mold = await NewMold.find_by_name(name=mold_name)
        async with pw_db.atomic():
            file.pid = project.id
            file.tree_id = project.rtree_id
            await pw_db.update(file, only=["pid", "tree_id"])
            await NewFileService.update_molds(file, [mold.id])

    @staticmethod
    async def get_filed_code(sample: bool):
        if sample:
            sample_code = """
def main(data: dict):
    file_name = data["file_name"]
    top_elements = data["top_elements"]
    filed_map = {
        "私募证券投资基金基金合同": "私募-基金合同",
        "证券投资基金基金合同": "公募-基金合同",
        "资产管理计划资产管理合同": "公募-资产管理合同",
        "招募说明书": "公募-招募说明书",
    }
    mold_name = None
    for key in filed_map:
        if key in file_name:
            mold_name = filed_map[key]
    if not mold_name:
        for elt in top_elements:
            if text := elt.get("text"):
                for key in filed_map:
                    if key in text:
                        mold_name = filed_map[key]
    return mold_name

                """
            return SAMPLE_CODE_FILE_NAME, sample_code.encode("utf-8")
        filed_script = await pw_db.first(CmfFiledScript.select())
        if not filed_script:
            raise FileNotFoundError
        return filed_script.filename, filed_script.context.encode("utf-8")


async def main():
    file = await NewFile.get_by_id(6030)
    await GJZQFiledFileService.filed_file(file)


if __name__ == "__main__":
    import asyncio

    asyncio.run(main())
