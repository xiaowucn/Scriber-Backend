import json
import logging
from urllib.parse import quote

import httpx

from remarkable.common.storage import localstorage
from remarkable.config import get_config

logger = logging.getLogger(__name__)


async def convert_by_office(url: str, fid: int, src_path: str):
    logger.info(f"make convert request for file {fid=}, {src_path=}")
    data = {
        "app": get_config("converter.app_name"),
        "callback_type": "http",
        "callback": url,
        "key": str(fid),
        "state": json.dumps({"fid": fid}),
    }
    api = get_config("converter.pdf_api")
    docx_data = localstorage.read_file(src_path, decrypt=bool(get_config("app.file_encrypt_key")))
    async with httpx.AsyncClient(verify=False, timeout=5, transport=httpx.AsyncHTTPTransport(retries=3)) as client:
        try:
            response = await client.post(url=api, data=data, files={"file": (quote(f"{fid}.docx"), docx_data)})
            response.raise_for_status()
            logger.info("convert request success")
        except Exception as exp:
            logger.exception(f"convert request failed: {exp}, {url=}")
