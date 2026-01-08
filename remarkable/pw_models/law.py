import os
from functools import cached_property

from fastapi_permissions import All, Allow, Everyone
from peewee import BooleanField, CharField, ForeignKeyField, IntegerField, TextField, Value, fn
from speedy.peewee_plus.field import EnumField

from remarkable.common.constants import IntEnumBase, RuleReviewStatus
from remarkable.common.util import generate_timestamp, simple_match_ext
from remarkable.db import IS_MYSQL, pw_db
from remarkable.models.new_user import NewAdminUser
from remarkable.pw_models.base import BaseUTCModel, ReadOnlyForeignKeyField
from remarkable.pw_orm.field import ArrayField, JSONField

LAW_FILE_PARENT = "law"


class LawStatus(IntEnumBase):
    # 状态转换必须是有序的
    INIT = 0, ""
    PENDING = 5, "排队中"
    PARSING = 15, "解析中"
    PARSE_FAIL = -15, "解析失败"

    FETCHING = 25, "获取中"
    FETCH_FAIL = -25, "获取失败"

    PARSED = 30, "解析完成"

    SPLITTING = 35, "拆分中"
    SPLIT_FAIL = -35, "拆分失败"
    SPLIT = 50, "拆分完成"


class LawRefreshStatus(IntEnumBase):
    INIT = 0, ""
    REFRESHING = 5, "更新中"
    SUCCESS = 10, "有更新"
    FAILED = -10, "更新失败"


def bind_law_path(col, abs_path=True):
    def _path_method(self):
        return self.path(col=col, abs_path=abs_path)

    return _path_method


class LawScenario(BaseUTCModel):
    class Meta:
        table_name = "law_scenario"

    name = CharField(max_length=30, unique=True)
    user = ForeignKeyField(NewAdminUser)
    updated_by_id = IntegerField(null=True)

    def __acl__(self):
        return [
            (Allow, "perm:manage_law", All),
            (Allow, Everyone, "view"),
        ]


class LawOrder(BaseUTCModel):
    class Meta:
        table_name = "law_order"

    rank = IntegerField(index=True, unique=True)
    name = CharField()
    is_template = BooleanField(default=False)
    refresh_status = EnumField(LawRefreshStatus, default=LawRefreshStatus.INIT)
    meta = JSONField(default=dict)
    user = ForeignKeyField(NewAdminUser)
    updated_by_id = IntegerField(null=True)

    @classmethod
    async def max_rank_with_lock(cls):
        query = (
            cls.select(cls.rank, include_deleted=True, for_update=True)
            .order_by(cls.deleted_utc, cls.rank.desc())
            .limit(1)
        )
        last = await pw_db.scalar(query)
        return last

    @property
    def scenarios(self):
        if isinstance(self.law_scenarios, list):
            return [law_scenario.scenario for law_scenario in self.law_scenarios]
        return []

    @property
    def scenario_names(self):
        if isinstance(self.law_scenarios, list):
            return [law_scenario.scenario.name for law_scenario in self.law_scenarios]
        return []

    @property
    def status(self):
        return (
            min(self.laws, key=lambda law: (not law.is_current, law.status >= 0, abs(law.status))).status
            if self.laws
            else LawStatus.INIT
        )

    def __acl__(self):
        return [
            (Allow, "perm:manage_law", All),
        ]

    @classmethod
    def refresh_err(cls, pk, msg):
        update = {
            cls.refresh_status: LawRefreshStatus.FAILED,
            cls.meta: {"error_msg": msg},
            cls.updated_utc: generate_timestamp(),
        }
        return cls.update(update).where(cls.id == pk)

    async def refresh(self, updated_by_id, outdate_laws):
        for law in outdate_laws:
            await law.soft_delete()
        await pw_db.update(self, refresh_status=LawRefreshStatus.REFRESHING, updated_by_id=updated_by_id, meta={})

    async def soft_delete(self):
        await pw_db.execute(
            LawCheckPoint.update(
                {
                    LawCheckPoint.abandoned: True,
                    LawCheckPoint.updated_utc: generate_timestamp(),
                    LawCheckPoint.abandoned_reason: "原始法规被删除",
                }
            ).where(LawCheckPoint.order_id == self.id)
        )

        await pw_db.execute(
            LawRule.update({LawRule.deleted_utc: generate_timestamp()}).where(LawRule.order_id == self.id)
        )
        await pw_db.execute(
            LawRulesScenarios.update({LawRulesScenarios.deleted_utc: generate_timestamp()}).where(
                LawRulesScenarios.order_id == self.id
            )
        )

        await pw_db.execute(Law.update({Law.deleted_utc: generate_timestamp()}).where(Law.order_id == self.id))

        await pw_db.execute(
            LawsScenarios.update({LawsScenarios.deleted_utc: generate_timestamp()}).where(
                LawsScenarios.law_id == self.id
            )
        )
        self.deleted_utc = generate_timestamp()
        await pw_db.update(self)


class Law(BaseUTCModel):
    class Meta:
        table_name = "law"

    order = ForeignKeyField(LawOrder, backref="laws")
    name = CharField()
    is_template = BooleanField(default=False)
    hash = CharField()
    size = IntegerField(null=True)
    page = IntegerField(null=True)
    docx = CharField(null=True)
    pdf = CharField(null=True)
    pdfinsight = CharField(null=True)
    chatdoc_unique = CharField(null=True)
    is_current = BooleanField()
    status = EnumField(LawStatus, null=False, default=LawStatus.INIT)

    pdf_path = bind_law_path("pdf")
    docx_path = bind_law_path("docx")
    file_path = bind_law_path("hash")
    pdfinsight_path = bind_law_path("pdfinsight")

    LAW_FILE_EXTENSIONS = (".pdf", ".doc", ".docx")

    def path(self, col="hash", *, parent=LAW_FILE_PARENT, abs_path=False):
        return super().path(col, parent=parent, abs_path=abs_path)

    def parse_path(self):
        if self.pdf:
            return self.pdf_path()
        return self.path()

    def parse_name(self):
        if self.pdf:
            return f"{self.filename}.pdf"
        return self.name

    @property
    def filename(self):
        return os.path.splitext(self.name)[0]

    @property
    def ext(self):
        return os.path.splitext(self.name)[-1].lower()

    @cached_property
    def is_pdf(self):
        return simple_match_ext(self.ext, self.path(abs_path=True), ".pdf")

    @cached_property
    def is_word(self):
        return simple_match_ext(self.ext, self.path(abs_path=True), ".doc", ".docx")

    @classmethod
    def split_ids(cls):
        return cls.select(cls.id, cls.order_id).where(cls.is_current, cls.status == LawStatus.SPLIT)

    async def soft_delete(self):
        await pw_db.execute(
            LawCheckPoint.update(
                {
                    LawCheckPoint.abandoned: True,
                    LawCheckPoint.updated_utc: generate_timestamp(),
                    LawCheckPoint.abandoned_reason: "原始法规被删除",
                }
            ).where(LawCheckPoint.law_id == self.id, ~LawCheckPoint.abandoned)
        )

        await pw_db.execute(
            LawRule.update({LawRule.deleted_utc: generate_timestamp()}).where(LawRule.law_id == self.id)
        )
        await pw_db.execute(
            LawRulesScenarios.update({LawRulesScenarios.deleted_utc: generate_timestamp()}).where(
                LawRulesScenarios.law_id == self.id
            )
        )
        self.deleted_utc = generate_timestamp()
        await pw_db.update(self)


class LawsScenarios(BaseUTCModel):
    class Meta:
        table_name = "laws_scenarios"

    law = ForeignKeyField(LawOrder, backref="law_scenarios")
    scenario = ForeignKeyField(LawScenario)
    user = ForeignKeyField(NewAdminUser)
    updated_by_id = IntegerField(null=True)


class LawRuleStatus(IntEnumBase):
    DISABLED = 0, "不适用"
    INIT = 1, "未转换"
    WAITING = 3, "排队中"
    CONVERTING = 5, "转换中"
    CONVERTED = 10, "转换成功"
    CONVERT_FAILED = -10, "转换失败"


class LawRule(BaseUTCModel):
    class Meta:
        table_name = "law_rule"

    law = ForeignKeyField(Law, backref="law_rules")
    order = ForeignKeyField(LawOrder, backref="law_rules")
    content = TextField(null=False)
    enable = BooleanField(default=False)
    status = EnumField(LawRuleStatus, default=LawRuleStatus.DISABLED)
    prompt = TextField()
    keywords = ArrayField(TextField, default=list)
    match_all = BooleanField(default=False)
    updated_by_id = IntegerField(null=True)

    @classmethod
    def _normalize_content_expr(cls, content_field):
        """统一的内容规范化表达式，兼容 MySQL 和 PostgreSQL"""
        if IS_MYSQL:
            return fn.REGEXP_REPLACE(content_field, "[^\\\\u4e00-\\\\u9fa5a-zA-Z0-9]", "", "g")
        else:
            return fn.REGEXP_REPLACE(content_field, "[^\\u4e00-\\u9fa5a-zA-Z0-9]", "", "g")

    @classmethod
    async def check_duplicate_content(cls, content, order_id, exclude_id=None):
        """检查在同一order_id下是否存在重复的规范化内容，仅检查当前有效的法规"""
        # 使用相同的规范化表达式确保命中索引
        db_normalized = cls._normalize_content_expr(cls.content)
        target_normalized = cls._normalize_content_expr(Value(content))

        query = (
            cls.select().join(Law).where(db_normalized == target_normalized, cls.order_id == order_id, Law.is_current)
        )
        if exclude_id:
            query = query.where(cls.id != exclude_id)
        return await pw_db.exists(query)

    def add_ranges(self, value):
        self.ranges.append(value)

    @cached_property
    def ranges(self):
        return []

    @property
    def scenarios(self):
        if isinstance(self.rule_scenarios, list):
            return [rule_scenario.scenario for rule_scenario in self.rule_scenarios]
        return []

    @property
    def scenario_names(self):
        if isinstance(self.rule_scenarios, list):
            return [rule_scenario.scenario.name for rule_scenario in self.rule_scenarios]
        return []

    def __acl__(self):
        return [
            (Allow, "perm:manage_law", All),
            (Allow, "perm:customer_rule_participate", "view"),
            (Allow, "perm:customer_rule_review", "view"),
        ]

    def __repr__(self):
        return f"LawRule(id={self.id}, utc={self.updated_utc})"

    def __str__(self):
        return f"LawRule(id={self.id}, utc={self.updated_utc})"

    def filter_by_keywords(self, contents):
        if not self.keywords:
            return contents
        if self.match_all:
            return [content for content in contents if all(keyword in content["text"] for keyword in self.keywords)]
        return [content for content in contents if any(keyword in content["text"] for keyword in self.keywords)]

    def template_cp(self):
        return {
            "order_id": self.order_id,
            "law_id": self.law_id,
            "rule_id": self.id,
            "rule_content": self.content,
            "core": "检查合同中的内容，需与范文/法规保持一致",
            "check_method": None,
            "templates": {
                "groups": [
                    {
                        "label": "范文",
                        "contents": [{"chapters": [], "diff_context": False, "content": self.content}],
                    }
                ]
            },
            "meta": {},
        }

    async def soft_delete(self):
        await pw_db.execute(
            LawCheckPoint.update(
                {
                    LawCheckPoint.abandoned: True,
                    LawCheckPoint.updated_utc: generate_timestamp(),
                    LawCheckPoint.abandoned_reason: "原始法规被删除",
                }
            ).where(LawCheckPoint.rule_id == self.id)
        )
        await super().soft_delete()


class LawRulesScenarios(BaseUTCModel):
    class Meta:
        table_name = "law_rules_scenarios"

    rule = ReadOnlyForeignKeyField(LawRule, backref="rule_scenarios")
    scenario = ReadOnlyForeignKeyField(LawScenario)
    updated_by_id = IntegerField(null=True)
    order_id = IntegerField()
    law_id = IntegerField()


class LawCheckType(IntEnumBase):
    FORBIDDEN = -1, "禁止性"
    PROCEDURAL = 0, "程序性"
    REQUIRED = 1, "义务性"


class LawCheckPoint(BaseUTCModel):
    order = ReadOnlyForeignKeyField(LawOrder)
    law_id = IntegerField()
    rule = ReadOnlyForeignKeyField(LawRule, lazy_load=False, backref="check_points")
    rule_content = TextField(null=False)
    name = TextField(null=False)
    alias_name = TextField(null=True)
    subject = TextField(null=False)
    check_type = EnumField(LawCheckType, null=False)
    core = TextField(null=False)
    check_method = TextField(null=True)
    templates = JSONField(null=True)
    meta = JSONField(default=dict)
    review_status = EnumField(RuleReviewStatus, null=False, default=RuleReviewStatus.NOT_REVIEWED)
    enable = BooleanField(default=False)
    parent = ForeignKeyField("self", backref="children", null=True)
    updated_by_id = IntegerField(null=True)
    reviewer_id = IntegerField(null=True)
    enable_switcher_id = IntegerField(null=True)
    abandoned = BooleanField(default=False)
    abandoned_reason = TextField()
    alias_by_id = IntegerField(null=True)

    @classmethod
    def active_cond(cls):
        return cls.enable & (~cls.abandoned) & cls.parent_id.is_null()

    @staticmethod
    def displaying(draft):
        return draft.review_status.in_([RuleReviewStatus.NOT_REVIEWED, RuleReviewStatus.DEL_NOT_REVIEWED])

    @classmethod
    def active_by_scenario(cls, scenario_id):
        return (
            cls.select(
                cls.id,
                cls.rule_id,
                cls.order_id,
                cls.alias_name,
                cls.name,
            )
            .join(LawCPsScenarios)
            .where(cls.active_cond(), LawCPsScenarios.scenario_id == scenario_id)
        )

    @classmethod
    def children_with_scenario(cls):
        # 使用别名 prefetch draft with scenarios
        cp_draft = cls.alias()
        draft_scenarios = LawCPsScenarios.alias()

        return [
            (cp_draft.select().where(cp_draft.parent_id.is_null(False), cp_draft.deleted_utc == 0), cls),
            (draft_scenarios.select().where(draft_scenarios.deleted_utc == 0), cp_draft),
            (LawScenario.select(), draft_scenarios),
        ]

    def cp_dict(self, *, new_rule=None):
        return {
            "created_utc": self.created_utc,
            "updated_utc": self.updated_utc,
            "order_id": self.order_id,
            "law_id": new_rule.law_id if new_rule else self.law_id,
            "rule_id": new_rule.id if new_rule else self.rule_id,
            "rule_content": self.rule_content,
            "name": self.name,
            "subject": self.subject,
            "check_type": self.check_type,
            "core": self.core,
            "check_method": self.check_method,
            "templates": self.templates,
            "meta": self.meta,
            "review_status": self.review_status,
            "enable": self.enable,
            "updated_by_id": self.updated_by_id,
            "reviewer_id": self.reviewer_id,
            "enable_switcher_id": self.enable_switcher_id,
            "abandoned": self.abandoned,
            # "abandoned_reason": self.abandoned_reason,
        }

    async def create_draft(self, form, user, review_status=RuleReviewStatus.NOT_REVIEWED):
        draft = await pw_db.create(
            self.__class__,
            order_id=self.order_id,
            rule_id=self.rule_id,
            name=self.name,
            **form.model_dump(exclude={"id", "scenario_ids"}),
            meta=self.meta,
            review_status=review_status,
            parent_id=self.id,
            updated_by_id=user.id,
            alias_by_id=self.alias_by_id,
        )
        if scenario_ids := getattr(form, "scenario_ids", None):
            await LawCPsScenarios.bulk_insert(
                [{"cp_id": draft.id, "scenario_id": _id, "updated_by_id": user.id} for _id in scenario_ids]
            )
            draft.cp_scenarios = await draft.get_related_objects(
                LawCPsScenarios, LawCPsScenarios.cp_id, subqueries=(LawScenario.select(),)
            )
        else:
            draft.cp_scenarios = []
        self.children = [draft]
        return draft

    async def update_draft(self, form, user):
        await pw_db.update(
            self,
            **form.model_dump(exclude={"id", "scenario_ids"}),
            review_status=RuleReviewStatus.NOT_REVIEWED,
            updated_by_id=user.id,
        )
        if form.scenario_ids:
            for cp_scenario in self.cp_scenarios:
                if cp_scenario.scenario_id in form.scenario_ids:
                    form.scenario_ids.remove(cp_scenario.scenario_id)
                    continue
                cp_scenario.updated_by_id = user.id
                await cp_scenario.soft_delete()
            if form.scenario_ids:
                await LawCPsScenarios.bulk_insert(
                    [{"cp_id": self.id, "scenario_id": _id, "updated_by_id": user.id} for _id in form.scenario_ids]
                )
            self.cp_scenarios = await self.get_related_objects(
                LawCPsScenarios, LawCPsScenarios.cp_id, subqueries=(LawScenario.select(),)
            )

    @property
    def draft(self):
        if isinstance(self.children, list) and self.children:
            return self.children[0]
        return None

    @property
    def full_user_ids(self):
        draft_user = []
        if draft := self.draft:
            draft_user = [draft.updated_by_id, draft.reviewer_id]
        return [self.updated_by_id, self.reviewer_id, self.enable_switcher_id, *draft_user]

    @property
    def scenarios(self):
        if isinstance(self.cp_scenarios, list):
            return [cp_scenario.scenario for cp_scenario in self.cp_scenarios]
        return []

    @property
    def scenario_names(self):
        if isinstance(self.cp_scenarios, list):
            return [rule_scenario.scenario.name for rule_scenario in self.cp_scenarios]
        return []

    def __acl__(self):
        return [
            (Allow, "perm:customer_rule_participate", All),
            (Allow, "perm:customer_rule_review", All),
        ]


class LawCPsScenarios(BaseUTCModel):
    class Meta:
        table_name = "law_check_points_scenarios"

    cp = ReadOnlyForeignKeyField(LawCheckPoint, backref="cp_scenarios")
    scenario = ReadOnlyForeignKeyField(LawScenario)
    updated_by_id = IntegerField(null=True)
