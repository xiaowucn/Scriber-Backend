# CYC: build-with-nuitka
import logging
from functools import cached_property
from typing import Literal

from pydantic import BaseModel, Field, model_validator
from webargs import fields

from remarkable.common import field_validate
from remarkable.config import get_config

logger = logging.getLogger(__name__)


class Mold(BaseModel):
    name: str


class FileType(BaseModel):
    name: Literal[
        "基金合同",
        "招募说明书",
        "托管协议",
        "风险评估报告",
        "核心要素表",
        "请示函",
        "港股人员说明",
        "承诺函",
    ]
    serial: int
    require: bool
    quantity_limit: int
    molds: list[Mold]


class CheckPoint(BaseModel):
    """
    name: "基金份额持有人、基金管理人和基金托管人的权利、义务"
    left_mold: "标注章节比对 招募说明书V1"
    left_key: "001基金份额持有人、基金管理人和基金托管人的权利、义务"
    right_mold: "标注章节对比 基金合同V1"
    right_key: "001基金合同当事人及权利义务"
    """

    name: str = Field(description="审核点名称")
    left_mold: Literal["标注章节比对 招募说明书V1"]
    left_key: str
    right_mold: Literal["标注章节对比 基金合同V1", "标注章节比对 托管协议V1"]
    right_key: str


class SelfConfig(BaseModel):
    file_types: list[FileType] = []
    # sync: dict
    check_points: list[CheckPoint] = Field(default_factory=list, description="章节比对审核点")

    @model_validator(mode="after")
    def check(self):
        for idx, file_type in enumerate(self.file_types, 1):
            if file_type.serial != idx:
                logger.warning(f"wrong serial: {file_type.serial}, should be {idx}")
                file_type.serial = idx
        return self

    @cached_property
    def required_types(self) -> set[str]:
        return {file_type.name for file_type in self.file_types if file_type.require}

    @cached_property
    def valid_types(self) -> list[str]:
        return [file_type.name for file_type in self.file_types]

    @cached_property
    def check_points_molds(self) -> dict[str, list[str]]:
        """章节比对审核点涉及的 Schema 名称: Keys 列表"""
        molds = {}
        for check_point in self.check_points:
            molds.setdefault(check_point.left_mold, []).append(check_point.left_key)
            molds.setdefault(check_point.right_mold, []).append(check_point.right_key)
        return molds

    def mold_names(self, type_name: str) -> set[str]:
        file_type = next((ft for ft in self.file_types if ft.name == type_name), None)
        assert file_type, ValueError(f"Not a valid file type: {type_name}")
        return {mold.name for mold in file_type.molds}


I_SELF_CONFIG = SelfConfig.model_validate(get_config("chinaamc_yx") or {})


file_type_kwargs = {"file_type": fields.Str(required=True, validate=field_validate.OneOf(I_SELF_CONFIG.valid_types))}
