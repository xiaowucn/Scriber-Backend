from pydantic import BaseModel, Field


class CmfABCompareSchema(BaseModel):
    url: str
    use_llm: bool
    prompt: str | None


class BoxSchema(BaseModel):
    box_top: float
    box_left: float
    box_right: float
    box_bottom: float


class BoxesSchema(BaseModel):
    box: BoxSchema
    page: int
    text: str


class BoxesDataSchema(BaseModel):
    text: str
    boxes: list[BoxesSchema]
    handleType: str


class CellSchema(BaseModel):
    row: int
    col: int


class ExcelDataSchema(BaseModel):
    text: str
    cell: CellSchema
    sheet_name: str


class CmfAnswerDataBase(BaseModel):
    key: str = Field(default="")
    data: list[BoxesDataSchema | ExcelDataSchema] = Field(default_factory=list)
    value: list[str] = Field(default_factory=list)
    revise_suggestion: bool | None = Field(default=None)


class CmfAnswerDataAdd(CmfAnswerDataBase):
    schema_: dict = Field(default_factory=dict, alias="schema")
    mold_id: int


class CmfAnswerDataUpdate(CmfAnswerDataBase):
    id: int
    qid: int


class CmfAnswerDataDelete(BaseModel):
    id: int
    key: str


class CmfAnswerData(BaseModel):
    add: list[CmfAnswerDataAdd] = Field(default_factory=list, description="新增数据")
    update: list[CmfAnswerDataUpdate] = Field(default_factory=list, description="更新数据")
    delete: list[CmfAnswerDataDelete] = Field(default_factory=list, description="删除数据")


class CmfAnswerDataRes(BaseModel):
    add: list[CmfAnswerDataDelete] = Field(default_factory=list)


class CmfMoldFieldSchema(BaseModel):
    field_id: int
    probability: float
    uuid_path: str


class CmfProbabilitySchema(BaseModel):
    probability: int
