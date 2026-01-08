import logging
import math
import re
from collections import defaultdict

import attr

from remarkable.checker.base import BaseChecker
from remarkable.common.pattern import PatternCollection
from remarkable.plugins.cgs.common.enum_utils import TemplateCheckTypeEnum
from remarkable.plugins.cgs.common.para_similarity import DiffResult
from remarkable.plugins.cgs.common.template_condition import TemplateName
from remarkable.plugins.cgs.common.utils import append_suggestion, number2chinese
from remarkable.plugins.cgs.schemas.reasons import (
    ConflictReasonItem,
    DiffLike,
    IgnoreConditionItem,
    MatchFailedItem,
    MissContentReasonItem,
    NoMatchReasonItem,
    SchemaFailedItem,
)

P_CHAPTER_NUMBERING = re.compile(r"^\s*第?\s*([一二三四五六七八九十零〇0-9]+)\s*[章节.\s、，,]+")

P_TOP_CHAPTER_NUMBERING = re.compile(r"^\s*第?\s*([一二三四五六七八九十零〇]+)\s*[章节.\s、，,]+")


class BaseTemplateChecker(BaseChecker):
    SYNONYM_PATTERNS = []
    TEMPLATES = []
    MIN_RATIO_THRESHOLD_VALUE = 0.2
    THRESHOLD_VALUE = 0.8
    DIFFERENCE_VALUE = 0.2

    def render_text(self, text):
        return text

    def get_templates(self):
        return [template for template in self.TEMPLATES if self.is_updated_template(template)]

    @classmethod
    def get_origin_contents(cls, template):
        template_origin = template["origin"]
        if isinstance(template["origin"], list):
            template_origin = "\n".join(template["origin"])
        template_from = template["from"]
        if not isinstance(template_from, list):
            template_from = [template["from"]]
        template_from = [
            item if item.startswith("《") and item.endswith("》") else f"《{item}》" for item in template_from
        ]
        return ["\n".join(template_from), template_origin]

    @staticmethod
    def get_contract_content(template):
        contract_content = template.get("contract_content") or ""
        if isinstance(contract_content, list):
            return "\n".join(contract_content)
        return contract_content

    def find_paragraphs_by_range(self, chapters, start, end):
        chapters, paragraphs = self.reader.find_paragraphs_by_chapters(chapters)
        start = PatternCollection(start)
        end = PatternCollection(end)

        res = []
        find_start = False
        for paragraph in paragraphs:
            if paragraph.get("fragment"):
                continue
            if start.nexts(paragraph["text"]):
                find_start = True
                continue
            if find_start:
                if end.nexts(paragraph["text"]):
                    break
                res.append(paragraph)
        return chapters, res

    @classmethod
    def ignore_chapters(cls, chapters, elements, chapter_rule):
        indexes = chapter_rule.get("indexes")
        if indexes:
            remove_indexes = set()
            count = len(elements)
            for index in indexes:
                if count > index:
                    if chapters and any(item["element"] == elements[index]["index"] for item in chapters):
                        remove_indexes.add(index)
            if remove_indexes:
                for index in sorted(remove_indexes, reverse=True):
                    elements.pop(index)
        return elements

    def ignore_elements(self, chapters, elements, rules):
        if not rules:
            return elements

        if "chapter" in rules:
            elements = self.ignore_chapters(chapters, elements, rules["chapter"])

        return elements

    def get_paragraphs(self, template):
        element_from = template.get("element_from")
        chapters = None
        paragraphs = []

        if element_from:
            if element_from.get("type") == "field":
                paragraphs = self.manager.get(element_from["field"]).get_related_paragraphs()
        elif not template.get("chapter"):
            paragraphs = self.reader.paragraphs
        else:
            # 根据章节正则获取段落，不需要严格层级关系
            is_continued_chapter = template["chapter"].get("is_continued_chapter", True)
            chapters, paragraphs = self.reader.find_paragraphs_by_chapters(
                template["chapter"]["chapters"], is_continued_chapter=is_continued_chapter
            )
            if not paragraphs and template["chapter"].get("range"):
                chapters, paragraphs = self.find_paragraphs_by_range(
                    template["chapter"]["range"]["chapters"],
                    template["chapter"]["range"]["start"],
                    template["chapter"]["range"]["end"],
                )

        return chapters, [paragraph for paragraph in paragraphs if not paragraph.get("fragment")]

    @classmethod
    def get_chapter_numbering(cls, chapters, reader):
        from remarkable.converter.utils import (
            cn2digit,
        )

        if chapters:
            chapters = reader.find_syllabuses_by_index(chapters[-1]["element"])
            if chapters:
                if "目录" in chapters[0]["title"]:
                    chapters = chapters[1:]
            if chapters:
                chapter = chapters[0]
                for item in chapters:
                    if P_TOP_CHAPTER_NUMBERING.search(item["title"]):
                        chapter = item
                        break

                numbering = P_CHAPTER_NUMBERING.search(chapter["title"])
                if numbering:
                    numbering_text = numbering.group(1)
                    level_text = numbering_text
                    if not numbering_text.isdigit():
                        try:
                            level_text = cn2digit(numbering_text)
                        except Exception as e:
                            logging.exception(e)
                            return ""
                    text = "第{}章".format(number2chinese(level_text))
                    return text
        return ""

    def check(self):
        raise NotImplementedError

    def is_updated_template(self, template):
        if not self.labels:
            return True
        return template["label"] in self.labels

    def check_field(self, template):
        checkers = template.get("field_checker") or []
        for checker in checkers:
            if checker.get("type") == "empty":  # names里的字段不能全为空
                names = checker["name"]
                if isinstance(checker["name"], str):
                    names = [checker["name"]]
                if all(not self.manager.get(name).value for name in names):
                    return SchemaFailedItem(
                        reason_text=self.render_text(checker["reason_text"]),
                        suggestion=self.render_text(checker["suggestion"]),
                    )
        return None

    @classmethod
    def after_match_template(cls, template, reasons, miss_content):
        matched = False

        if reasons and all(isinstance(reason, IgnoreConditionItem) for reason in reasons):
            matched = True
        else:
            for reason in reasons:
                if isinstance(reason, IgnoreConditionItem):
                    continue
                matched |= reason.matched

        # 处理对不同分组匹配数量的限制
        if template.get("group_count"):
            counts = defaultdict(int)
            for reason in reasons:
                if reason.template and reason.matched:
                    counts[reason.template.name] += 1

            temp_reasons = []
            find_matched = False
            for key, count in template["group_count"]:
                if key not in counts or counts[key] < count:
                    temp_reasons.append(
                        MissContentReasonItem(
                            miss_content=cls.get_template_text(template, key), reason_text=f"缺少部分{key}内容"
                        )
                    )
                else:
                    find_matched = True
            if template.get("group_count_or"):
                if not find_matched:
                    matched = False
                    reasons.extend(temp_reasons)
            else:
                if temp_reasons:
                    matched = False
                    reasons.extend(temp_reasons)
        else:
            # https://gitpd.paodingai.com/cheftin/docs_scriber/-/issues/3225#note_402946
            # 需要加个逻辑：同时对比法规和范文的 有一个对就算对 算合规 举例：如与法规比对后 只有16不合规 而检查到了16的范文 则算合规
            temp_reasons = []
            for reason in reasons:
                if isinstance(reason, DiffLike):
                    temp_reasons.append(reason)
            if len(temp_reasons) == 2:
                equal_list = []
                no_equal_list = []
                for item in temp_reasons:
                    equal_left_list = set()
                    no_equal_left_list = set()
                    for diff in item.diff:
                        if diff["type"] == "equal":
                            equal_left_list.add(diff["left"])
                        else:
                            no_equal_left_list.add(diff["left"])
                    equal_list.append(equal_left_list)
                    no_equal_list.append(no_equal_left_list)
                if no_equal_list[1] < equal_list[0] or no_equal_list[0] < equal_list[1]:
                    matched = True

        if template.get("check_reasons"):
            matched = template["check_reasons"](reasons)
            if not matched:
                reasons.append(MatchFailedItem(reason_text=template["check_failed_text"]))

        if miss_content:
            matched = False

        return matched, reasons

    def render_suggestion_by_reasons(self, template, reasons):
        # 如果有不合规原因：1.只有不一致和不匹配的，优先去取范文的 2.否则取最后一个不合规的原因
        # 如果不合规原因为schema缺失，则保留
        suggestions = []

        def add_suggestion(reason):
            suggestion = reason.render_suggestion(self.reader, template["related_name"])
            if suggestion and suggestion not in suggestions:
                suggestions.append(suggestion)

        if reasons:
            reasons = [reason for reason in reasons if not reason.matched]
            _reasons = [reason for reason in reasons if isinstance(reason, (NoMatchReasonItem, ConflictReasonItem))]
            schema_reasons = [reason for reason in reasons if isinstance(reason, SchemaFailedItem)]
            # https://gitpd.paodingai.com/cheftin/docs_scriber/-/issues/2455#note_347718
            for reason in schema_reasons:
                add_suggestion(reason)
            if _reasons and len(_reasons) == len(reasons):
                editing_reasons, law_reasons = [], []
                # 范文的修改建议全部保留
                for reason in reasons:
                    if reason.template.name == TemplateName.EDITING_NAME:
                        editing_reasons.append(reason)
                    elif reason.template.name == TemplateName.LAW_NAME:
                        law_reasons.append(reason)
                if editing_reasons:
                    for reason in editing_reasons:
                        add_suggestion(reason)
                elif law_reasons:
                    for reason in law_reasons:
                        add_suggestion(reason)
                else:
                    add_suggestion(_reasons[0])
            else:
                add_suggestion(reasons[-1])

        return "\n".join(suggestions)

    @classmethod
    def get_template_text(cls, template, name):
        res = []
        for item in template["templates"]:
            if item["name"] == name:
                res.append("\n".join(item["items"]))
        return "\n".join(res)

    def filter_result(self, result, template):
        result.reasons = self.filter_same_reason(result.reasons)
        if not result.is_compliance:
            result.suggestion = self.render_suggestion_by_reasons(template, result.reasons)

    @staticmethod
    def mock_diff_html_by_diff_content(diff_results: list[DiffResult]):
        _type = "equal" if all(math.isclose(result.ratio, 1, abs_tol=1e-06) for result in diff_results) else "match"
        diffs = []
        for result in diff_results:
            diffs.append(
                {
                    "html": result.html_diff_content,
                    "type": _type,
                    "left": result.left.origin_text,
                    "right": result.right.origin_text if _type != "equal" and result.right else None,
                }
            )
        return diffs

    def generate_suggestion_by_reasons(self, template, reasons):
        suggestion = ""
        for item in reasons:
            if hasattr(item, "template") and item.template.name == "范文" and not item.matched:
                item_suggestion = item.render_suggestion(self.reader, template["related_name"])
                if not suggestion or item_suggestion not in suggestion:
                    suggestion = append_suggestion(suggestion, item_suggestion)
        return suggestion

    @classmethod
    def recombined_template(cls, source_templates):
        """
        example:
            input: [[para_1_1, para_1_2], [para_2_1, para_2_2]]
            output: [
                [para_1_1, para_2_1],
                [para_1_1, para_2_2],
                [para_1_2, para_2_1],
                [para_1_2, para_2_2]
            ]
        """
        new_templates = []
        if not source_templates or any(isinstance(item, str) for item in source_templates):
            return new_templates
        for item in source_templates[0]:
            for child_template in cls.recombined_template(source_templates[1:]):
                if not child_template:
                    continue
                if isinstance(child_template, str):
                    new_templates.append([item, child_template])
                    continue
                child_template.insert(0, item)
                new_templates.append(child_template)

        if len(source_templates) == 1:
            return [[item] for item in source_templates[0]]
        return new_templates

    def split_templates_by_conditions(self, template_paragraphs, paragraphs=None):
        # 根据templates中各段落配置的规则筛选合规的数据，组合为二维数组
        match_templates = []
        for item in template_paragraphs:
            templates = self.get_split_templates(item, paragraphs=paragraphs)
            if templates:
                match_templates.extend(templates)

        return match_templates

    def get_split_templates(self, templates, paragraphs=None) -> list:
        if isinstance(templates, str):
            return [[templates]]
        if isinstance(templates, list):
            if any(isinstance(item, list) for item in templates) or len(templates) == 1:
                logging.error("Template rules are incorrectly configured")
                logging.error(templates)
                return []
            return [templates]

        if templates.get("conditions") and not self.manager.verify_condition(templates["conditions"]):
            return []

        for item in templates.get("single_optional", []):
            # templates内为dict，则默认为并列单选，任意一个匹配到即可
            if item.get("conditions") and not self.manager.verify_condition(item["conditions"]):
                continue
            return self.get_split_templates(item, paragraphs=paragraphs)
        # TODO 暂时不用，后续再删与multi_optional相关代码
        # if multi_optional := templates.get('multi_optional', []):
        #     match_templates = []
        #     for item in multi_optional:
        #         # templates内为dict，并列多选
        #         if item.get("conditions") and not self.manager.verify_condition(item["conditions"]):
        #             continue
        #         child_templates = self.get_split_templates(item, paragraphs=paragraphs)
        #         if child_templates:
        #             match_templates.extend(child_templates[0])
        #     return [match_templates] if match_templates else []

        # 处理需要替换、转换的场景
        if templates.get("type") in TemplateCheckTypeEnum.member_values():
            replace_templates = self.replace_template_with_paragraphs(templates, paragraphs)
            if replace_templates:
                return replace_templates

        if not templates.get("items"):
            return []
        match_templates = []

        for item in templates["items"]:
            # 遍历templates，为str则转为list插入，为list则直接插入，为dict则可能存在内嵌类型，继续判断，
            if isinstance(item, str):
                match_templates.append([item])
                continue
            if isinstance(item, list):
                if any(isinstance(val, list) for val in item) or len(item) == 1:
                    logging.error("Template rules are incorrectly configured")
                    logging.error(templates)
                    return []
                match_templates.append(item)
                continue
            if isinstance(item, dict):
                split_templates = self.get_split_templates(item, paragraphs=paragraphs)
                if split_templates:
                    match_templates.extend(split_templates)

        return match_templates

    def replace_template_with_paragraphs(self, template: dict, paragraphs=None):
        if paragraphs is None:
            paragraphs = []
        if not hasattr(self, f"extract_template_by_{template.get('type', '')}"):
            logging.error(f"Class {self.__class__.__name__} has no attribute extract_template_by_{template['type']}")
            return []
        return getattr(self, f"extract_template_by_{template['type']}")(template, paragraphs)

    def check_schema_fields(self, schema_fields):
        reasons = []
        for field in schema_fields:
            answer = self.manager.get(field)
            if not answer or not answer.value:
                reasons.append(SchemaFailedItem(reason_text=f"要素“{field}”为空", suggestion=f"请补充“{field}”"))
        return reasons


@attr.s
class ChapterBlock:
    indexes = attr.ib()
    paragraphs = attr.ib()
    chapters = attr.ib()
    chapter = attr.ib()

    mapping = {}
    start = None
    end = None
    _blocks = None

    def __attrs_post_init__(self):
        self.mapping = {paragraph["index"]: paragraph for paragraph in self.paragraphs}
        self.start = None
        self.end = None
        if self.paragraphs:
            self.start = self.paragraphs[0]["index"]
            self.end = self.paragraphs[-1]["index"]

    def get_paragraphs_by_start_end(self, start, end):
        return [self.mapping[index] for index in range(start, end) if index in self.mapping]

    def blocks(self):
        if self._blocks is None:
            res = []
            prev_index = self.start
            for start, end in self.indexes:
                if start != prev_index:
                    res.append([self.get_paragraphs_by_start_end(prev_index, start - 1), False])
                res.append([self.get_paragraphs_by_start_end(start, end), True])
                prev_index = self.end + 1
            self._blocks = res
        return self._blocks


@attr.s
class BlockResult:
    ratio = attr.ib()
    similarity = attr.ib()
    left = attr.ib()
    right = attr.ib()
