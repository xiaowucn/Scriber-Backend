import functools
import logging
import os
import traceback
from typing import Any

import httpx

from remarkable.config import get_config

logger = logging.getLogger(__name__)


class MMPoster:
    NAME = "scriber"
    HOOK_URL = get_config("notification.mattermost", "https://mm.paodingai.com/hooks/zxg3ncokc3yuxfymyrco7zctta")
    TIMEOUT = 10
    RETRIES = 3

    @classmethod
    def _enabled(cls, force=False) -> bool:
        enabled = bool(force or get_config("notification.switch"))
        if not enabled:
            logger.warning('MM notification not enabled, update your config or pass "force=True" to enable it.')
        return enabled

    @classmethod
    def _generate_payload(
        cls, msg: str, error=False, attachments: list[dict[str, Any]] | None = None
    ) -> dict[str, Any]:
        return {
            "text": f"{':x: :x: :x:' if error else ':white_check_mark:'} "
            f"[{cls.NAME}-{os.environ.get('ENV', 'dev')}@{os.uname().nodename}]\n"  # Scriber-dev-hello-world-xxxx
            f"{msg}\n"
            f"{(get_config('notification.tail') or '')}\n",
            "channel": get_config("notification.channel", "test-exception"),
            "username": cls.NAME,
            "icon_url": "http://res.cloudinary.com/kdr2/image/upload"
            "/c_crop,g_faces,h_240,w_240/v1454772214/misc/c3p0-001.jpg",
            "attachments": attachments,
        }

    @classmethod
    async def send(cls, msg: str, error=False, force=False, attachments: list[dict[str, Any]] | None = None) -> bool:
        if not cls._enabled(force):
            return False
        async with httpx.AsyncClient(
            timeout=cls.TIMEOUT, transport=httpx.AsyncHTTPTransport(verify=False, retries=cls.RETRIES)
        ) as client:
            try:
                resp = await client.post(cls.HOOK_URL, json=cls._generate_payload(msg, error, attachments))
                return resp.status_code // 200 == 1
            except Exception:
                logger.exception(f"MM消息发送失败：msg: {msg} attachments: {attachments}")
                return False


def fail2mm(func):
    @functools.wraps(func)
    async def wrapper(*args, **kwargs):
        res = []
        try:
            ret = await func(*args, **kwargs)
        except Exception:
            for arg in args:
                if hasattr(arg, "to_dict"):
                    run = arg.to_dict  # ruff: noqa:B009
                    res.append(run())
                else:
                    res.append(arg)
            msg = "- func name: {}\n- args: {}\n- kwargs: {}\n- error info: \n```shell\n{}```".format(
                func.__name__, res, kwargs, traceback.format_exc()
            )
            logger.error(traceback.format_exc())
            await MMPoster.send(msg, error=True)
            raise
        return ret

    return wrapper
