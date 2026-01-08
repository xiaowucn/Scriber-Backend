from remarkable.common.constants import RuleReviewStatus
from remarkable.pw_models.law import LawCheckType, LawRefreshStatus, LawRuleStatus, LawStatus
from remarkable.routers.schemas import DebugSchema


class DebugLawCheckPointBaseSchema(DebugSchema):
    rule_content: str
    name: str
    alias_name: str | None = None
    subject: str
    check_type: LawCheckType
    core: str
    check_method: str | None
    templates: dict | None
    review_status: RuleReviewStatus
    enable: bool


class DebugLawCheckPointSchema(DebugLawCheckPointBaseSchema):
    draft: DebugLawCheckPointBaseSchema | None


class DebugLawRuleSchema(DebugSchema):
    content: str
    enable: bool
    status: LawRuleStatus
    prompt: str | None
    keywords: list
    match_all: bool = False
    scenario_names: list[str]
    check_points: list[DebugLawCheckPointSchema]


class DebugLawFileSchema(DebugSchema):
    name: str
    is_template: bool
    hash: str | None
    size: int | None
    page: int | None
    chatdoc_unique: str | None
    docx: str | None
    pdf: str | None
    is_current: bool
    status: LawStatus
    pdfinsight: str | None
    law_rules: list[DebugLawRuleSchema]


class DebugLawSchema(DebugSchema):
    name: str
    is_template: bool
    refresh_status: LawRefreshStatus | None
    meta: dict
    laws: list[DebugLawFileSchema]
    scenario_names: list[str]
