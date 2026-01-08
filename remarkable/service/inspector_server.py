import logging

import httpx

logger = logging.getLogger(__name__)


class InspectorServer:
    server_url: str
    timeout: int = 5

    def __init__(self, server_url: str):
        self.server_url = server_url

    async def send(self, data):
        logger.debug(f"Sending inspect answer to: {self.server_url}")

        is_success = True

        async with httpx.AsyncClient(
            verify=False, timeout=self.timeout, transport=httpx.AsyncHTTPTransport(retries=3)
        ) as client:
            try:
                resp = await client.post(url=self.server_url, json=data)
                assert httpx.codes.is_success(resp.status_code), resp.text
            except Exception as exp:
                is_success = False
                logger.exception(exp)

        return is_success
