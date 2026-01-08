import asyncio
import logging
from typing import TypedDict

import httpx

from remarkable.common.util import loop_wrapper
from remarkable.db import pw_db
from remarkable.models.new_file import NewFile
from remarkable.service.new_file import NewFileService
from remarkable.worker.app import app
from remarkable.worker.tasks import process_file

logger = logging.getLogger(__name__)


class FileLink(TypedDict):
    url: str
    id: int


def parse_filename(response: httpx.Response) -> str:
    return response.headers.get("Content-Disposition", "").split("filename=")[-1].strip('"')


@app.task
def download_file(links: list[FileLink]):
    semaphore = asyncio.Semaphore(5)

    async def _download(link: FileLink, sem: asyncio.Semaphore, client: httpx.AsyncClient):
        async with sem:
            try:
                response = await client.get(link["url"])
                response.raise_for_status()

                content = response.content
                filename = parse_filename(response)
                file = await NewFileService.update_file_body(
                    link["id"],
                    {
                        "filename": filename,
                        "body": content,
                    },
                )

                if file:
                    await process_file(file)
            except (httpx.RequestError, httpx.HTTPStatusError) as exc:
                file = await NewFile.find_by_id(link["id"])
                if file:
                    file.meta_info = file.meta_info | {"failed_reason": "文件下载失败"}
                    await pw_db.update(
                        file,
                        only=["meta_info"],
                    )
                logger.exception(exc)
                return

    async def run():
        transport = httpx.AsyncHTTPTransport(retries=2)
        async with httpx.AsyncClient(transport=transport) as client:
            tasks = [asyncio.create_task(_download(link, semaphore, client)) for link in links]
            await asyncio.gather(*tasks)

    asyncio.run(run())


@app.task
@loop_wrapper
async def file_post_pipe_task(fid):
    await NewFileService.post_pipe(fid, triggered_by_predict=False)
