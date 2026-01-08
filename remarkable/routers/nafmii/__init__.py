from fastapi import APIRouter

from remarkable.routers.nafmii import task

router = APIRouter(prefix="/nafmii", tags=["交易商协会"])

router.include_router(task.router)
