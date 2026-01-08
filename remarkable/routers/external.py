from fastapi import APIRouter, Depends, HTTPException, status

from remarkable.dependencies import check_user_permission
from remarkable.pw_models.model import NewMold

external_router = APIRouter(prefix="/external", tags=["external"])


@external_router.get(r"/molds", dependencies=[Depends(check_user_permission("browse"))])
async def get_mold(name: str):
    mold = await NewMold.find_by_name(name)
    if not mold:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Item Not Found")

    return mold.to_dict()
