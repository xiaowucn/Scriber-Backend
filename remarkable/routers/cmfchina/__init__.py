from fastapi import APIRouter

from remarkable.routers.cmfchina import handlers

router = APIRouter(prefix="/cmfchina", tags=["招商基金"])

router.include_router(handlers.router)
