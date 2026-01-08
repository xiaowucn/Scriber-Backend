from typing import Generic, TypeAlias

from json_repair import repair_json
from pydantic import BaseModel, ConfigDict, ValidationError
from speedy.schemas import GenericModel, T

Box: TypeAlias = tuple[int | float, int | float, int | float, int | float]
PageBoxes: TypeAlias = dict[int, list[Box]]
PagesBoxes: TypeAlias = list[PageBoxes]

ContractRects: TypeAlias = list[tuple[str, PagesBoxes]]


class DebugSchema(BaseModel):
    model_config = ConfigDict(from_attributes=True)


class IDSchema(BaseModel):
    id: int
    model_config = ConfigDict(from_attributes=True)


class PaginateResSchema(GenericModel, Generic[T]):
    page: int
    size: int
    total: int
    items: list[T]


class PaginateResWithScenarioIdsSchema(PaginateResSchema, Generic[T]):
    scenario_ids: list[int]


class RepairLLMSchem(BaseModel):
    @classmethod
    def model_validate_json(cls, json_data, **kwargs):
        try:
            return super().model_validate_json(json_data, **kwargs)
        except ValidationError:
            json_data = repair_json(json_data)
            return super().model_validate_json(json_data, **kwargs)


class RepairCPsLLMSchem(BaseModel):
    @classmethod
    def model_validate_json(cls, json_data, **kwargs):
        try:
            return super().model_validate_json(json_data, **kwargs)
        except ValidationError:
            data = repair_json(json_data, return_objects=True)
            if len(data["check_points"]) > 1:
                data["check_points"][-1:] = []
            return cls.model_validate(data)
