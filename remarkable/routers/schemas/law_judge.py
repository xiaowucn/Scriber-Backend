from pydantic import BaseModel, field_validator

from remarkable.routers.schemas import DebugSchema, IDSchema


class LawJudgeLLMResultSchema(BaseModel):
    is_compliance: bool | None
    reasons: list | None
    rule_type: str | None
    schema_results: list | None
    suggestion: str | None


class LawJudgeResultBaseSchema(LawJudgeLLMResultSchema):
    file_id: int
    judge_status: int
    is_compliance_ai: bool | None
    is_compliance_tip: bool | None
    is_compliance_user: bool | None
    is_edited: bool | None
    is_noncompliance_tip: bool | None
    name: str | None
    order_key: str | None
    origin_contents: list[str] | None
    contract_content: str | None
    related_name: str | None
    suggestion_ai: str | None
    suggestion_user: str | None
    tip_content: str | None
    user_reason: str | None


class LawJudgeResultDBSchema(LawJudgeResultBaseSchema, IDSchema):
    law_order_id: int
    rule_id: int
    cp_id: int


class LawJudgeResultSyncSchema(LawJudgeResultBaseSchema, DebugSchema):
    cp_id: int | None

    @field_validator("cp_id", mode="after")
    @classmethod
    def format_sync_cp_id(cls, value):
        return -abs(value) if value else None


class LawJudgeResultWithNameDBSchema(LawJudgeResultDBSchema):
    law_order_name: str
    is_template: bool
    cp_name: str


class SetLawJudgeResultsSchema(BaseModel):
    results: list[dict]


class LawJudgeResultRecordsDBSchema(IDSchema):
    created_utc: int
    is_compliance_from: bool | None
    is_compliance_to: bool | None
    result_id: int
    suggestion: str | None
    user_id: int
    user_name: str
    user_reason: str | None
