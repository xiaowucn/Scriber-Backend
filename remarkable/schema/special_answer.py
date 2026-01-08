# CYC: build-with-nuitka
from functools import cached_property
from typing import Any

from pydantic import BaseModel, Field


class Box(BaseModel):
    box_top: float
    box_left: float
    box_right: float
    box_bottom: float

    @cached_property
    def outline(self) -> tuple[float, float, float, float]:
        return self.box_left, self.box_top, self.box_right, self.box_bottom


class MultiBox(BaseModel):
    box: Box
    page: int
    text: str


class BoxData(BaseModel):
    boxes: list[MultiBox]
    handleType: str = "wireframe"


class SchemaData(BaseModel):
    type: str
    label: str
    multi: bool
    words: str
    required: bool
    description: str | None = None


class Schema(BaseModel):
    data: SchemaData


class Cell(BaseModel):
    data: list[BoxData]
    text: str | None
    manual: bool | None = False
    key: str | None = None
    meta: Any = None
    score: str | None = "-1.00"
    value: str | None = None
    custom: bool | None = False
    marker: dict[str, Any] | None = None
    schema_: Schema | None = Field(default=None, alias="schema")
    _migrated: bool | None = False


class Pages(BaseModel):
    rows: list[list[Cell]]
    fill_status: int = 0


class SpecialPageAnswer(BaseModel):
    headers: list[str]
    pages: dict[str, Pages]
