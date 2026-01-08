import logging

import httpx
from pdfparser.imgtools.ocraug.faded_h_stroke import defaultdict

from remarkable.common.enums import TaskType
from remarkable.common.util import generate_timestamp
from remarkable.config import get_config
from remarkable.db import pw_db
from remarkable.models.new_file import NewFile
from remarkable.models.new_user import ADMIN
from remarkable.models.zts import ZTSProjectInfo
from remarkable.pw_models.audit_rule import NewAuditResult
from remarkable.pw_models.model import NewFileMeta, NewFileProject, NewMold
from remarkable.service.new_file import NewFileService
from remarkable.service.new_file_project import NewFileProjectService

logger = logging.getLogger(__name__)


class ZTSFileService(NewFileService):
    @classmethod
    async def create(
        cls,
        name: str,
        body: bytes,
        molds: list[int],
        pid: int,
        tree_id: int,
        uid: int,
        doc_type: str,
        report_year: str,
    ):
        async with pw_db.atomic():
            file = await cls.create_file(
                name=name, body=body, molds=molds, pid=pid, tree_id=tree_id, uid=uid, task_type=TaskType.AUDIT.value
            )

            await NewFileMeta.create(
                file_id=file.id,
                doc_type=doc_type,
                report_year=report_year,
                hash=file.id,
                title="",
                stock_code="",
                stock_name="",
                publish_time=0,
                raw_data={},
            )
            return file

    @staticmethod
    async def get_files_by_project_id(project_id: int):
        query = (
            NewFile.select(
                NewFile.id,
                NewFile.name,
                NewFile.created_utc,
                NewFile.pdf_parse_status,
                NewFileMeta.report_year,
                NewFileMeta.doc_type,
            )
            .join(NewFileMeta, on=(NewFile.id == NewFileMeta.file_id))
            .where(NewFile.pid == project_id)
            .order_by(NewFileMeta.report_year.desc())
        )

        data = await pw_db.execute(query.dicts())
        return list(data)

    @staticmethod
    async def get_files_by_project_ids(project_ids: list[int]):
        query = (
            NewFile.select(
                NewFile.id,
                NewFile.pid,
                NewFile.name,
                NewFile.created_utc,
                NewFile.pdf_parse_status,
                NewFileMeta.report_year,
                NewFileMeta.doc_type,
            )
            .join(NewFileMeta, on=(NewFile.id == NewFileMeta.file_id))
            .where(NewFile.pid.in_(project_ids))
            .order_by(NewFileMeta.report_year.desc())
        )

        data = await pw_db.execute(query.dicts())
        return list(data)


class ZTSProjectService(NewFileProjectService):
    @classmethod
    async def create(
        cls,
        name: str,
        default_molds=None,
        uid: int = ADMIN.id,
        rtree_id: int = 0,
        exchange: str = None,
        record_id: str = None,
        **kwargs,
    ) -> NewFileProject:
        if exchange == "上交所":
            default_molds = await NewMold.tolerate_schema_ids("上交所企业债")
        elif exchange == "深交所":
            default_molds = await NewMold.tolerate_schema_ids("深交所企业债")

        async with pw_db.atomic():
            project = await super().create(name, default_molds, uid, rtree_id, **kwargs)
            await ZTSProjectInfo.create(project_id=project.id, exchange=exchange, record_id=record_id)
        return project

    @classmethod
    async def update_inspect_info(cls, pid: int, conclusion: dict):
        await pw_db.execute(
            ZTSProjectInfo.update(
                consistency=conclusion["一致性比对"]["disclosure"],
                restricted_funds=conclusion["资产受限"]["disclosure"],
                borrowing=conclusion["新增借款"]["disclosure"],
                guarantee=conclusion["对外担保"]["disclosure"],
                inspected_utc=generate_timestamp(),
            ).where(ZTSProjectInfo.project == pid)
        )

    @classmethod
    async def get_inspect_conclusion(cls, results: list[NewAuditResult]):
        data = defaultdict(lambda: {"name": "", "disclosure": False, "data": []})

        for result in results:
            if result.name == "一致性比对":
                data[result.name]["data"].append(
                    {
                        "label": result.label,
                        "is_compliance": result.is_compliance,
                    }
                )

            else:
                data[result.name]["data"].append(
                    {
                        "label": result.label,
                        "is_compliance": result.is_compliance,
                        "formula_ret": result.reasons["formula_ret"],
                        "schema_results": [
                            {
                                "doc_type": x["doc_type"],
                                "name": x["name"],
                                "text": x.get("text"),
                            }
                            for x in result.schema_results
                        ],
                    }
                )

            data[result.name]["name"] = result.name

            if not result.is_compliance:
                data[result.name]["disclosure"] = True

        return data

    @classmethod
    async def push_inspect_result(cls, pid: int, data: dict, status: str, msg: str = None):
        url = get_config("zts.push_api")
        if not url:
            return

        project_info = await pw_db.first(ZTSProjectInfo.select().where(ZTSProjectInfo.project == pid))
        if not project_info:
            logger.error(f"zts_project_info not found for {pid=}")
            return

        body = {
            "recordId": project_info.record_id,
            "status": status,
            "msg": msg,
            "bondReportCompareList": list(data.values()),
        }
        async with httpx.AsyncClient(verify=False, timeout=5, transport=httpx.AsyncHTTPTransport(retries=3)) as client:
            try:
                resp = await client.post(url=url, json=body)
                logger.info(f"push_inspect_result {url=} {body=} {resp.content=}")
            except Exception as exp:
                logger.exception(exp)
