from typing import Any, Literal

from pydantic import BaseModel, Field, model_validator
from pydantic.functional_serializers import field_serializer

from remarkable.common.constants import MoldType
from remarkable.common.enums import ExtractType
from remarkable.common.exceptions import InvalidMoldError
from remarkable.common.schema import Schema
from remarkable.schema import PaginateSchema


class SearchUsableFilesSchema(PaginateSchema):
    pass


class LLMTestSchema(BaseModel):
    fid: int


class SchemaField(BaseModel):
    type: str
    required: bool
    multi: bool
    description: str = ""
    regex: str | None = None
    extract_type: ExtractType | None = ExtractType.EXCLUSIVE

    @field_serializer("extract_type")
    def serialize_extract_type(self, extract_type: ExtractType | None) -> str | None:
        if extract_type is None:
            return None
        return extract_type.value


class SchemaItem(BaseModel):
    name: str = Field(..., min_length=1)
    orders: list[str] | None = Field(default_factory=list)
    schema: dict[str, SchemaField]

    @model_validator(mode="after")
    def validate_schema_keys_in_orders(self):
        schema_keys = set(self.schema.keys())
        for name in schema_keys:
            Schema.is_valid_filed_name(name)
        orders_set = set(self.orders)
        if orders_set and (len(schema_keys - orders_set) or len(orders_set - schema_keys)):
            raise InvalidMoldError(f"{self.name}的orders和schema不匹配")
        return self


class SchemaTypeValue(BaseModel):
    name: str
    is_default: bool = Field(default=False, validation_alias="isDefault")


class SchemaType(BaseModel):
    label: str = Field(..., min_length=1)
    values: list[SchemaTypeValue] = Field(min_length=1)
    type: Literal["enum"]
    is_multi_select: bool = Field(default=True, validation_alias="isMultiSelect")

    @model_validator(mode="after")
    def validate_schema_type(self):
        if not self.is_multi_select and sum(1 for v in self.values if v.is_default) > 1:
            raise InvalidMoldError(f"枚举类型:{self.label}存在多个默认值")
        return self


class MoldDataSchema(BaseModel):
    schemas: list[SchemaItem] = Field(min_length=1)
    schema_types: list[SchemaType]

    @property
    def need_llm_extract(self):
        for schema in self.schemas:
            for field in schema.schema.values():
                if field.extract_type == ExtractType.LLM:
                    return True
        return False

    @property
    def mold_type(self):
        has_llm = False
        has_exclusive = False
        for schema in self.schemas:
            for field in schema.schema.values():
                if field.extract_type == ExtractType.LLM:
                    has_llm = True
                else:
                    has_exclusive = True
        if has_llm and has_exclusive:
            return MoldType.HYBRID
        if has_llm:
            return MoldType.LLM
        return MoldType.COMPLEX


class MoldDataWithModelNameSchema(MoldDataSchema):
    model_name: str | None = None

    @model_validator(mode="after")
    def validate_model_name(self):
        if self.need_llm_extract and not self.model_name:
            raise InvalidMoldError("model_name不能为空")
        return self


class StudioSchemaProperty(BaseModel):
    type: str | None = None
    description: str | None = None
    enum: list[str] = None
    property_order: int | None = Field(serialization_alias="propertyOrder")
    properties: dict[str, "StudioSchemaProperty"] | None = None
    items: dict[str, Any] | None = None


class StudioSchemaSchemas(BaseModel):
    type: str
    properties: dict[str, StudioSchemaProperty]


class StudioSchema(BaseModel):
    schemas: StudioSchemaSchemas
