from pydantic import BaseModel


class QuestionStatusSchema(BaseModel):
    id: int
    ai_status: int
    updated_utc: int


class FileAuditStatusSchema(BaseModel):
    questions: list[QuestionStatusSchema]
    audit_status: int | None = None
    judge_status: int | None = None
    judge_status_count: dict | None = None
