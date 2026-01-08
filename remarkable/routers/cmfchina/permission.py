import http
from typing import Type

from fastapi import HTTPException, Path
from peewee import Select

from remarkable.pw_models.base import TModel


def get_model(clz: Type[TModel], *prefetch: Select, alias="mold_id", lock=False, detail="操作对象不存在") -> TModel:  # noqa: UP006
    async def get_record(model_id: int = Path(..., alias=alias)) -> TModel:
        record = await clz.get_by_id(model_id, *prefetch, lock=lock)
        if record is None:
            raise HTTPException(status_code=http.HTTPStatus.NOT_FOUND, detail=detail)
        return record

    return get_record
