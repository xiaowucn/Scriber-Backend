from fastapi import HTTPException
from pydantic import BaseModel, Field, field_validator, model_validator
from starlette.status import HTTP_400_BAD_REQUEST

from remarkable.routers.schemas import IDSchema
from remarkable.schema import PaginateSchema


class BoxSchema(BaseModel):
    box_top: float
    box_left: float
    box_right: float
    box_bottom: float


class BoxesSchema(BaseModel):
    box: BoxSchema | None = None
    page: int | None = None
    text: str


class BoxesDataItemSchema(BaseModel):
    boxes: list[BoxesSchema]


class BoxesDataSchema(BaseModel):
    text: str
    items: list[BoxesDataItemSchema] | None = None
    boxes: list[BoxesSchema] | None = None
    handleType: str | None = None


class CellSchema(BaseModel):
    row: int
    col: int


class ExcelDataSchema(BaseModel):
    text: str
    cell: CellSchema
    sheet_name: str


class AnswerDataBase(BaseModel):
    key: str = Field(default="")
    data: list[BoxesDataSchema | ExcelDataSchema] = Field(default_factory=list)
    value: list[str] = Field(default_factory=list)
    revise_suggestion: bool | None = Field(default=None)


class AnswerDataAdd(AnswerDataBase):
    schema_: dict = Field(default_factory=dict, alias="schema")
    mold_id: int


class AnswerDataUpdate(AnswerDataBase):
    id: int
    qid: int


class AnswerDataDelete(BaseModel):
    id: int
    key: str


class AnswerData(BaseModel):
    add: list[AnswerDataAdd] = Field(default_factory=list, description="新增数据")
    update: list[AnswerDataUpdate] = Field(default_factory=list, description="更新数据")
    delete: list[AnswerDataDelete] = Field(default_factory=list, description="删除数据")


class AnswerDataRes(BaseModel):
    add: list[AnswerDataDelete] = Field(default_factory=list)


class ExtractStatusPayload(BaseModel):
    app_id: str
    doc_id: str
    success: bool


class ExtractStatusSchema(BaseModel):
    event_name: str
    payload: ExtractStatusPayload

    @field_validator("event_name")
    @classmethod
    def validate_event_name(cls, v):
        if v != "extract_done":
            raise HTTPException(HTTP_400_BAD_REQUEST, "event_name must be extract_done")
        return v


class BatchExportAnswerSchema(BaseModel):
    tree_ids: list[int]
    file_ids: list[int]

    @model_validator(mode="after")
    def validate_tree_ids(self):
        if not self.tree_ids and not self.file_ids:
            raise HTTPException(HTTP_400_BAD_REQUEST, "tree_ids or file_ids is required")
        return self


class AnswerDataExportDbSchema(IDSchema):
    pid: int
    task_done: int
    task_total: int
    files_ids: list[int]
    status: int
    zip_path: str | None = None
    created_utc: int


class SearchAnswerDataExportSchema(PaginateSchema):
    status: int | None = None
