import asyncio
import http
import json
import logging
import os
import shutil
import tempfile

from tornado.httputil import HTTPFile
from tornado.iostream import StreamClosedError

from remarkable import config
from remarkable.base_handler import BaseHandler
from remarkable.common.constants import SUPPORTED_SUFFIXES, FeatureSchema, UNZipStage
from remarkable.common.enums import ClientName
from remarkable.common.exceptions import CustomError
from remarkable.common.util import custom_async_open, generate_timestamp
from remarkable.db import init_rdb
from remarkable.worker.tasks import process_compressed_file

logger = logging.getLogger(__name__)


def zip_task_id(tid, event_id):
    return f"upload-zip:{tid}:{event_id}"


class UploadZipFileBaseHandler(BaseHandler):
    async def upload_compressed_file(
        self,
        tid: int,
        task_type: str,
        event_id: str | None,
        file: HTTPFile | None,
        need_create_folder: bool = True,
        scenario_id: int | None = None,
        sysfrom: str | None = None,
        molds: list[int] | None = None,
    ):
        rdb = init_rdb()
        work_dir = None
        if not event_id:
            assert file, CustomError(_("not found upload document"), resp_status_code=http.HTTPStatus.BAD_REQUEST)

            event_id = str(generate_timestamp())
            task_id = zip_task_id(tid, event_id)
            work_dir = tempfile.mkdtemp(prefix="zip_work_dir_", dir=config.get_config("web.tmp_dir"))

            compressed_suffix = os.path.splitext(file.filename)[1].lower()

            async with custom_async_open(os.path.join(work_dir, f"{task_id}{compressed_suffix}"), "wb") as afp:
                await afp.write(file.body)
            rdb.setex(task_id, 7200, f"{UNZipStage.START}:10:")
            if ClientName.cmfchina == config.get_config("client.name"):
                suffixes = FeatureSchema.from_config().supported_suffixes
            else:
                suffixes = SUPPORTED_SUFFIXES
            process_compressed_file.delay(
                self.current_user.id,
                tid,
                work_dir,
                task_id,
                compressed_suffix,
                suffixes,
                task_type,
                need_create_folder,
                scenario_id,
                sysfrom,
                molds,
            )

        task_id = zip_task_id(tid, event_id)
        if not rdb.get(task_id):
            raise CustomError(_("No unzip process task found."), resp_status_code=http.HTTPStatus.NOT_FOUND)

        while data := rdb.get(task_id):
            stage, percent, message = (int(x) if x.isdigit() else x for x in data.split(":"))
            msg = json.dumps({"stage": UNZipStage(stage).name, "percent": percent, "message": message})
            try:
                self.write(f"data: {msg}\n\nevent: message\n\nid: {event_id}\n\nretry: 5000\n\n")
                await self.flush()
            except StreamClosedError:
                break
            if stage in {UNZipStage.ERROR, UNZipStage.FINISHED}:
                logger.info(f"{task_id=}, stage={UNZipStage(stage).name}")
                rdb.delete(task_id)
                if work_dir:
                    shutil.rmtree(work_dir, ignore_errors=True)
                break
            await asyncio.sleep(0.8)
