import json
import re
from typing import Literal

from pydantic import BaseModel, Field, PrivateAttr, computed_field, field_validator, model_validator

from remarkable.common.constants import RuleReviewStatus
from remarkable.pw_models.law import LawCheckType, LawRefreshStatus, LawRuleStatus, LawStatus
from remarkable.routers.schemas import (
    ContractRects,
    DebugSchema,
    IDSchema,
    PaginateResSchema,
    RepairCPsLLMSchem,
    RepairLLMSchem,
)
from remarkable.routers.schemas.law_template import LawTemplatesSchema
from remarkable.schema import PaginateSchema

P_QUOTES = re.compile(r"(['\"‘“’”])(.*?)(['\"‘“’”])", re.DOTALL)


class JsonModel(BaseModel):
    @model_validator(mode="before")
    def jsonfy(cls, value):
        if isinstance(value, str):
            return json.loads(value)
        return value


class ScenarioSchema(BaseModel):
    name: str = Field(..., min_length=1, max_length=30)


class ScenarioDBSchema(IDSchema):
    name: str


class ScenarioIdsSchema(BaseModel):
    scenario_ids: list[int] | None = None


class ChatDocMaxmin(BaseModel):
    chatdoc_unique: str
    name: str = ""


class ChatDocLawSchema(ChatDocMaxmin):
    is_empty: bool = False
    children: list[ChatDocMaxmin] = Field(..., default_factory=list)

    @model_validator(mode="after")
    @classmethod
    def validate_root(cls, ins):
        if ins.is_empty and not ins.children:
            raise ValueError("文档内容不可为空")
        return ins


class CreateLawSchema(JsonModel):
    chatdocs: list[ChatDocLawSchema] = Field(default_factory=list)
    is_template: bool = False
    scenario_ids: list[int]


class EditLawSchema(BaseModel):
    name: str
    scenario_ids: list[int]


class RefreshLawSchema(JsonModel):
    chatdoc: ChatDocLawSchema | None = None


class LawFileDBSchema(IDSchema):
    name: str
    is_template: bool
    size: int | None
    page: int | None
    chatdoc_unique: str | None
    is_current: bool
    status: LawStatus


class LawOrderNameDBSchema(IDSchema):
    name: str
    rank: int | None = None
    is_template: bool


class LawOrderNameWithScenariosDBSchema(LawOrderNameDBSchema):
    scenarios: list[ScenarioDBSchema]


class LawOrderDBSchema(LawOrderNameWithScenariosDBSchema):
    rank: int
    refresh_status: LawRefreshStatus | None
    laws: list[LawFileDBSchema]
    status: LawStatus
    refresh_msg: str | None = None


class CreatedLawsSchema(BaseModel):
    laws: list[LawOrderDBSchema]
    duplicates: list[str]


class SearchLawOrderSchema(PaginateSchema):
    rank: int | None = None
    name: str | None = None
    scenario_ids: list[int] | None = None
    from_chatdoc: bool | None = None
    status: list[LawStatus] | None = None
    is_template: bool | None = None


class LawRuleDBSchema(IDSchema):
    content: str
    enable: bool
    status: LawRuleStatus
    prompt: str | None
    keywords: list
    match_all: bool
    scenarios: list[ScenarioDBSchema]


class SearchLawRuleSchema(PaginateSchema):
    keywords: str | None = None
    status: list[LawRuleStatus] | None = None
    scenario_ids: list[int] | None = None
    enable: bool | None = None
    desc: bool = False


class ExtractRuleKeywordsSchema(BaseModel):
    content: str = ""
    id: int | None = None


class RuleKeywordsSchema(RepairLLMSchem):
    keywords: list[str]


class EditLawRule(RuleKeywordsSchema):
    content: str
    prompt: str | None
    match_all: bool = True
    scenario_ids: list[int]
    update_check_points: bool = False


class RuleDiffRangeSchema(IDSchema):
    law_id: int
    content: str
    ranges: list


class DiffItemSchema(BaseModel):
    type: str
    left: list[RuleDiffRangeSchema]
    right: list[RuleDiffRangeSchema]


class DiffLawRuleSchema(BaseModel):
    ratio: int
    diff: list[DiffItemSchema]
    equal_pairs: list[tuple[int, int]]


class ApplyLawRulesSchema(BaseModel):
    pairs: list[tuple[int, int]]


class RuleFocusPointLLMS(BaseModel):
    focus_name: str = Field(description="领域名称，如‘基金规模合规’")
    focus_core: str = Field(description="核心要求，条款中的核心约束内容，如‘初始实缴规模≥1000万元；不得短期赎回规避’")
    focus_risk: str = Field(
        description="风险关联，说明该条款对应的行业风险，如‘初始实缴规模要求直接关联‘规模不足导致清盘’风险’"
    )


class RuleFocusLLMS(RepairLLMSchem):
    law_name: str = Field(description="法规名称，法规名称")
    rule_content: str = Field(description="条款原文，用户输入的单条法规原文")
    scenario: str = Field(description="法规场景，用户输入的法规场景")
    focus_area: list[RuleFocusPointLLMS]


class RuleCheckPointBaseLLMS(RepairLLMSchem):
    focus_name: str = Field(description="关注领域，传入关注领域，必须唯一")
    check_type: str = Field(description="类型，禁止性/义务性/程序性")
    subject: str = Field(description="行为主体，约束对象，如“私募基金管理人、投资者”")

    def row_data(self, *args):
        return {
            "name": self.focus_name,
            "subject": self.subject,
            "check_type": LawCheckType[self.check_type],
        }


class RuleCheckPointLLMS(RuleCheckPointBaseLLMS):
    law_name: str = Field(description="法规名称，法规全称")
    rule_content: str = Field(description="法规条款原文，法规中关联的条款原文")
    focus_core: str = Field(description="核心要求，需遵守的具体行为，与输入的‘核心要求’绑定")
    check_method: str = Field(description="验证方式，审核时如何检查合规，与‘风险关联’绑定")
    exclude_reason: str = Field(description="排除原因，若拆分，填“无”；若不拆分，填原因")

    @staticmethod
    def fix_quotes(content):
        return P_QUOTES.sub(r"“\2”", content)

    def row_data(self, rule):
        return {
            "order_id": rule.order_id,
            "law_id": rule.law_id,
            "rule_id": rule.id,
            "rule_content": self.fix_quotes(self.rule_content),
            "name": self.focus_name,
            "subject": self.subject,
            "check_type": LawCheckType[self.check_type],
            "core": self.focus_core,
            "check_method": self.check_method,
            "meta": {"exclude_reason": self.exclude_reason},
        }


class RuleCheckPointsLLMS(RepairCPsLLMSchem):
    check_points: list[RuleCheckPointLLMS]


class TuningLawRuleResLLMS(RuleCheckPointsLLMS):
    area: RuleFocusLLMS


class SearchLawCheckPointSchema(PaginateSchema):
    # 直接过滤
    order_ids: list[int] = Field(default_factory=list)
    law_name: str | None = None
    abandoned: bool | None = None
    parent_name: str | None = None
    parent_rule_content: str | None = None
    # 草稿优先
    review_status: RuleReviewStatus | None = None
    # 待审核则使用草稿
    name: str | None = None
    rule_content: str | None = None
    is_consistency: bool | None = None
    scenario_ids: list[int] | None = None


class LawCheckPointBaseSchema(BaseModel):
    rule_content: str
    name: str = Field(exclude=True)
    alias_name: str | None = Field(None, serialization_alias="name")
    subject: str
    check_type: LawCheckType
    core: str
    check_method: str | None = None
    templates: LawTemplatesSchema | None = None

    @model_validator(mode="after")
    def validate_check_point(self):
        if not (bool(self.check_method) ^ bool(self.templates)):
            raise ValueError("验证方式有问题")
        if self.templates:
            self.check_method = None
        if not self.alias_name:
            self.alias_name = self.name
        return self


class EditLawCheckPointSchema(LawCheckPointBaseSchema):
    scenario_ids: set[int] | None = Field(None, description="没有修改时不传更好")


class LawCheckPointBaseDBSchema(IDSchema, LawCheckPointBaseSchema):
    meta: dict
    review_status: RuleReviewStatus
    updated_by_id: int | None


class AnalysisLawCheckPointSchema(LawCheckPointBaseSchema):
    chatdoc_unique: str | None = None
    snippet: str | None = None
    _id: int | None = PrivateAttr(None)

    @computed_field
    def id(self) -> int:
        return self._id

    @model_validator(mode="after")
    def validate_document(self):
        if self.chatdoc_unique is None and self.snippet is None:
            raise ValueError("文档信息缺失")
        return self


class SaveLawCheckPointSchema(EditLawCheckPointSchema):
    id: int | None


class SaveAllLawCheckPointSchema(BaseModel):
    check_points: list[SaveLawCheckPointSchema]


class LawCheckPointBaseWithScenariosDBSchema(LawCheckPointBaseDBSchema):
    scenarios: list[ScenarioDBSchema]
    reviewer_id: int | None


class LawCheckPointSimpleDBSchema(LawCheckPointBaseWithScenariosDBSchema):
    rule_id: int
    enable: bool
    enable_switcher_id: int | None
    abandoned: bool
    abandoned_reason: str | None
    draft: LawCheckPointBaseWithScenariosDBSchema | None


class LawCheckPointDBSchema(LawCheckPointSimpleDBSchema):
    order: LawOrderNameWithScenariosDBSchema | int


class LawCheckPointPaginateResSchema(PaginateResSchema):
    items: list[LawCheckPointDBSchema]
    user_map: dict[int, str]
    all_scenario_ids: list[int]


class LawCheckPointReviewSchema(BaseModel):
    review_status: Literal[RuleReviewStatus.NOT_PASS, RuleReviewStatus.PASS, RuleReviewStatus.DEL_NOT_PASS]
    review_reason: str = ""


class LawCheckPointsAliasSchema(BaseModel):
    alias_name: str = Field(..., min_length=1, max_length=255)
    cp_ids: list[int] = Field(..., min_length=1)


class LawCheckPointSyncSchema(LawCheckPointBaseSchema, DebugSchema):
    id: int
    meta: dict
    review_status: RuleReviewStatus
    enable: bool
    abandoned: bool
    abandoned_reason: str | None

    @field_validator("id", mode="after")
    @classmethod
    def format_sync_id(cls, value):
        return -abs(value)


class ContractComplianceCheckPointLLMS(BaseModel):
    id: int = Field(description="审核点ID")
    check_type: str = Field(description="类型，禁止性/程序性/义务性")
    judgment_basis: str = Field(
        description="判断依据，结合类型说明内容合规/不合规原因(使用“合同中……”来阐述依据，`片段`和`序号`无实际意义，不要使用)"
    )
    compliance_status: str = Field(description="合规状态，合规/不合规/不适用")
    suggestion: str = Field("", description="修改意见，当不合规时，给出建议的修改意见；合规时无需修改意见")
    # contract_ids: list[int] = Field(
    #     default_factory=list, description="合同片段序号, 必须为片段的序号, 否则后续会KeyError"
    # )


class ContractComplianceResultLLMS(RepairCPsLLMSchem):
    check_points: list[ContractComplianceCheckPointLLMS] = Field(description="依据审核点")


class ContractComplianceCheckPointWithRectsLLMS(BaseModel):
    check_type: str
    judgment_basis: str
    compliance_status: str
    suggestion: str
    contract_rects: ContractRects
