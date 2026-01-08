from typing import TypeVar

from pydantic import BaseModel, ConfigDict, Field

T = TypeVar("T")
TSchema = TypeVar("TSchema", bound=BaseModel)


class BaseORM(BaseModel):
    model_config = ConfigDict(from_attributes=True, str_strip_whitespace=True)

    id: int | None = None
    created_utc: int | None = None
    updated_utc: int | None = None
    deleted_utc: int = 0


class PaginateSchema(BaseModel):
    page: int = Field(1, ge=1)
    size: int = Field(20, ge=1, le=1000)
