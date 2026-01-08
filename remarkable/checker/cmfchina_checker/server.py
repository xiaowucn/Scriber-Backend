import logging
import time

import httpx

from remarkable.config import get_config
from remarkable.security.crypto_util import encode_jwt, make_bearer_header
from remarkable.service.inspector_server import InspectorServer

logger = logging.getLogger(__name__)


class CmfChinaInspectorServer(InspectorServer):
    async def send(self, data):
        logger.debug(f"Sending inspect answer to: {self.server_url}")

        is_success = True
        jwt_secret_key = get_config("app.jwt_secret_key")

        async with httpx.AsyncClient(
            verify=False,
            timeout=self.timeout,
            transport=httpx.AsyncHTTPTransport(retries=3),
            headers=make_bearer_header(
                encode_jwt(
                    {"sub": "admin", "exp": time.time() + 43200, "path": "/external_api/v1/audit/results"},
                    jwt_secret_key,
                )
            ),
        ) as client:
            try:
                resp = await client.post(url=self.server_url, json=data)
                assert httpx.codes.is_success(resp.status_code), resp.text
            except Exception as exp:
                is_success = False
                logger.exception(exp)

        return is_success
