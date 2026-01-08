import httpx

from remarkable.infrastructure.mattermost import MMPoster


async def http_post_callback(url, data=None, json=None):
    success = False
    resp = None
    async with httpx.AsyncClient(timeout=10, transport=httpx.AsyncHTTPTransport(verify=False, retries=3)) as client:
        try:
            resp = await client.post(url, data=data, json=json)
            if resp.status_code // 200 == 1:
                success = True
        except Exception:
            pass
    if not success:
        await MMPoster.send(
            f"callback {url} error with code: {resp.status_code if resp else ''}, detail:\n{resp.text if resp else ''}",
            error=True,
        )
