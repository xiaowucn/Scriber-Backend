from fastapi import APIRouter

from remarkable import config

DEBUG_WEBIF = "debug" in config.get_config("web.plugins", [])

debug_route = APIRouter(prefix="/debug", tags=["debug"])
