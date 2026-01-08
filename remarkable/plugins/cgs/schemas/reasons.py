from copy import copy
from typing import Any, Protocol, runtime_checkable

import attr

from remarkable.plugins.cgs.common.utils import (
    append_suggestion,
    combine_line_no,
    generate_suggestion,
    get_chapter_info_by_outline,
    get_chapter_title_text,
    render_suggestion,
)


@attr.s
class Template:
    content = attr.ib("")
    content_title = attr.ib(default="")
    name = attr.ib(default="模板")
    page = attr.ib(default=None)
    outlines = attr.ib(default=None)


class BaseReasonItem:
    def render_suggestion(self, reader, rule_name):
        return ""


@attr.s
class NoMatchReasonItem(BaseReasonItem):
    template = attr.ib()
    matched = attr.ib(default=False)
    type = attr.ib(default="tpl_no_match")
    reason_text = attr.ib(default="")
    suggestion = attr.ib(default="")

    def __attrs_post_init__(self):
        if not self.reason_text:
            self.reason_text = self.default_reason_text

    @property
    def default_reason_text(self):
        name = self.template.name if self.template and self.template.name else "范文与法规"
        return f"未找到与{name}匹配的内容"

    def render_suggestion(self, reader, rule_name):
        if self.suggestion:
            return self.suggestion
        return f"请在{rule_name or '合同'}中补充“{self.template.content}”"


@attr.s
class ConflictReasonItem(BaseReasonItem):
    template = attr.ib()
    content = attr.ib()
    page = attr.ib()
    outlines = attr.ib()
    diff = attr.ib()
    content_title = attr.ib()
    xpath = attr.ib(default=None)
    type = attr.ib(default="tpl_conflict")
    matched = attr.ib(default=False)
    reason_text = attr.ib(default="")
    source = attr.ib(default="")

    def __attrs_post_init__(self):
        if not self.reason_text:
            self.reason_text = self.default_reason_text

    @property
    def default_reason_text(self):
        name = self.template.name if self.template and self.template.name else "范文与法规"
        return f"与{name}不一致"

    def render_suggestion(self, reader, rule_name):
        chapters = get_chapter_info_by_outline(reader, self.outlines)
        if not chapters:
            return f"请在{rule_name or '合同'}中补充“{self.template.content}”"

        title = get_chapter_title_text(chapters)
        if "\n" not in self.content:
            suggestion = combine_line_no(self.content, self.template.content)
            return render_suggestion(title, rule_name, self.content, suggestion)
        return self.render_multi_suggestion(reader, rule_name)

    def render_multi_suggestion(self, reader, rule_name):
        chapters = get_chapter_info_by_outline(reader, self.outlines)
        if not chapters:
            suggestion = None
            for item in self.template.content.split("\n"):
                suggestion = append_suggestion(suggestion, f"请在{rule_name}中补充“{item}”")
            return suggestion

        title = get_chapter_title_text(chapters)

        suggestion = ""
        prev_item = None
        for item in self.diff:
            if not prev_item:
                prev_item = copy(item)
                continue
            if prev_item["type"] != "add":
                if item["type"] != "add":
                    suggestion = generate_suggestion(prev_item, suggestion, title, rule_name)
                    prev_item = copy(item)
                    continue
            # 上一个为add，则直接跟当前合并
            # 上一个为equal，则该合并以当前类型为主，且调整right文本
            prev_item["right"] = (
                prev_item["left"] if prev_item["type"] == "equal" and not prev_item["right"] else prev_item["right"]
            )
            prev_item["type"] = item["type"] if prev_item["type"] != "equal" else "match"
            prev_item["left"] = append_suggestion(prev_item["left"], item["left"], separator="\n")
            prev_item["right"] = append_suggestion(prev_item["right"], item["right"], separator="\n")
        suggestion = generate_suggestion(prev_item, suggestion, title, rule_name)

        return suggestion


@attr.s
class MissContentReasonItem(BaseReasonItem):
    miss_content = attr.ib()
    template = attr.ib(default=None)
    type = attr.ib(default="tpl_miss_content")
    matched = attr.ib(default=False)
    reason_text = attr.ib(default="")
    suggestion = attr.ib(default="")

    def __attrs_post_init__(self):
        if not self.reason_text:
            self.reason_text = self.default_reason_text
        if not self.miss_content:
            if self.template:
                self.miss_content = self.template.content

    @property
    def default_reason_text(self):
        return f"{self.miss_content} 缺失"

    def render_suggestion(self, reader, rule_name):
        if self.suggestion:
            return self.suggestion
        suggestion = None
        for item in self.miss_content.split("\n"):
            suggestion = append_suggestion(suggestion, f"请在{rule_name}中补充{item}")
        return suggestion


@attr.s
class AdditionContentReasonItem(BaseReasonItem):
    template = attr.ib()
    content = attr.ib()
    page = attr.ib()
    outlines = attr.ib()
    addition_content = attr.ib()
    content_title = attr.ib()
    type = attr.ib(default="tpl_addition_content")
    matched = attr.ib(default=False)
    reason_text = attr.ib(default="")

    def __attrs_post_init__(self):
        if not self.reason_text:
            self.reason_text = self.default_reason_text

    @property
    def default_reason_text(self):
        return self.addition_content


@attr.s
class MatchReasonItem(BaseReasonItem):
    template = attr.ib()
    content = attr.ib()
    page = attr.ib()
    outlines = attr.ib()
    diff = attr.ib()
    content_title = attr.ib()
    xpath = attr.ib(default=None)
    type = attr.ib(default="tpl_match")
    matched = attr.ib(default=True)
    reason_text = attr.ib(default="")
    source = attr.ib(default="")

    def __attrs_post_init__(self):
        if not self.reason_text:
            self.reason_text = self.default_reason_text

    @property
    def default_reason_text(self):
        name = self.template.name if self.template and self.template.name else "范文与法规"
        return f"匹配到{name}的内容"


@attr.s
class MatchChaptersReasonItem(BaseReasonItem):
    template = attr.ib()
    page = attr.ib()
    outlines = attr.ib()
    diff = attr.ib()
    right = attr.ib()
    content_title = attr.ib()
    xpath = attr.ib(default=None)
    type = attr.ib(default="tpl_match_chapters")
    matched = attr.ib(default=True)
    reason_text = attr.ib(default="")

    def __attrs_post_init__(self):
        if not self.reason_text:
            self.reason_text = self.default_reason_text

    @property
    def default_reason_text(self):
        return "章节匹配"


@attr.s
class IgnoreConditionItem(BaseReasonItem):
    type = attr.ib(default="tpl_ignore_condition")
    matched = attr.ib(default=True)
    reason_text = attr.ib(default="")


@attr.s
class SchemaFailedItem(BaseReasonItem):
    type = attr.ib(default="schema_failed")
    matched = attr.ib(default=False)
    reason_text = attr.ib(default="")
    suggestion = attr.ib(default="")

    def render_suggestion(self, reader, rule_name):
        return self.suggestion


@attr.s
class MatchFailedItem(BaseReasonItem):
    page = attr.ib(default=None)
    outlines = attr.ib(default=None)
    type = attr.ib(default="tpl_failed")
    matched = attr.ib(default=False)
    reason_text = attr.ib(default="")


@attr.s
class MatchSuccessItem(BaseReasonItem):
    page = attr.ib(default=None)
    outlines = attr.ib(default=None)
    content = attr.ib(default="")
    type = attr.ib(default="matched_success")
    matched = attr.ib(default=False)
    reason_text = attr.ib(default="")


@attr.s
class CustomRuleNoMatchItem(BaseReasonItem):
    matched = attr.ib(default=False)
    type = attr.ib(default="rule_no_match")
    reason_text = attr.ib(default="")


@attr.s
class FieldNoMatchItem(BaseReasonItem):
    template = attr.ib()
    name = attr.ib()
    page = attr.ib()
    outlines = attr.ib()
    content = attr.ib()
    diff = attr.ib()
    matched = attr.ib(default=False)
    type = attr.ib(default="field_no_match")
    reason_text = attr.ib(default="")

    def __attrs_post_init__(self):
        if not self.reason_text:
            self.reason_text = self.default_reason_text

    @property
    def default_reason_text(self):
        return f"{self.content}与{self.name}不匹配。"

    def render_suggestion(self, reader, rule_name):
        return f"请修改 {self.content}。"


@attr.s
class ResultItem(BaseReasonItem):
    is_compliance = attr.ib()
    fid = attr.ib()
    schema_id = attr.ib()
    reasons = attr.ib()
    label = attr.ib()
    suggestion = attr.ib(default=None)
    schema_results = attr.ib(default=None)
    name = attr.ib(default=None)
    origin_contents = attr.ib(default=None)
    tip = attr.ib(default=None)
    related_name = attr.ib(default=None)
    rule_type = attr.ib(default=None)
    contract_content = attr.ib(default=None)

    @property
    def is_compliance_real(self):
        if self.reasons and all(isinstance(reason, IgnoreConditionItem) for reason in self.reasons):
            return None
        return self.is_compliance

    @property
    def schema_fields(self):
        res = []
        for item in self.schema_results or []:
            if item.get("name"):
                res.append(item["name"])
        return res


@runtime_checkable
class DiffLike(Protocol):
    diff: list[Any]
