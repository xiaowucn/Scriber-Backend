import json
from typing import Literal, TypedDict

from pydantic import BaseModel, Field, model_validator

from remarkable.common.constants import FileAnswerMergeStrategy
from remarkable.common.enums import NafmiiTaskType
from remarkable.models.nafmii import TaskFlag
from remarkable.plugins.nafmii.enums import DSFileType
from remarkable.pw_models.answer_data import DEFAULT_FILE_ANSWER_MERGE_STRATEGY


class JsonModel(BaseModel):
    @model_validator(mode="before")
    def jsonfy(cls, value):
        if isinstance(value, str):
            return json.loads(value)
        return value


class CreateTaskSchema(JsonModel):
    file_type: DSFileType = Field(description="file type", default=DSFileType.DS_D004)
    task_types: list[NafmiiTaskType] = Field(description="task type list")
    keywords: list[str] = Field(description="keywords", default_factory=list)


class PredictFileSchema(BaseModel):
    task: Literal["predict"] = Field(description="任务类型，目前只支持 'predict'")
    dirs: list[int] = Field(description="目录ID列表", default_factory=list)
    fids: list[int] = Field(description="文件ID列表", default_factory=list)
    merge_strategy: FileAnswerMergeStrategy = Field(description="合并策略", default=DEFAULT_FILE_ANSWER_MERGE_STRATEGY)
    flag: TaskFlag = Field(
        description="任务标记",
        default=TaskFlag.skip_push,
        examples=["重新识别并推送: 0", "重新识别: 1", "推送识别结果: 2"],
    )


class SummarySchema(TypedDict):
    total_file: int
    predicting: int
    predicted: int
