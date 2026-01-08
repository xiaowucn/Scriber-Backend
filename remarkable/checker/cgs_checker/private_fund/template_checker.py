import copy
import itertools
import math
from collections import defaultdict

from remarkable.checker.checkers.template_checker import (
    BaseTemplateChecker,
    BlockResult,
    ChapterBlock,
)
from remarkable.pdfinsight.reader import PdfinsightReader
from remarkable.plugins.cgs.common.para_similarity import ParagraphSimilarity
from remarkable.plugins.cgs.common.patterns_util import P_PRIVATE_SIMILARITY_PATTERNS
from remarkable.plugins.cgs.common.utils import (
    get_outlines,
    get_paragraphs_by_schema_fields,
    get_xpath_by_outlines,
    number2chinese,
)
from remarkable.plugins.cgs.rules.templates.chapter_with_template import (
    CHAPTERS_WITH_TEMPLATES,
)
from remarkable.plugins.cgs.rules.templates.chapters import CHAPTERS_TEMPLATES
from remarkable.plugins.cgs.rules.templates.normal import TEMPLATE_MATCH_ANY
from remarkable.plugins.cgs.rules.templates.setenecs import SENTENCE_TEMPLATES
from remarkable.plugins.cgs.rules.templates.single_chapter import (
    INTERDOC_PATH,
    SINGLE_CHAPTER_TEMPLATES,
)
from remarkable.plugins.cgs.schemas.reasons import (
    ConflictReasonItem,
    IgnoreConditionItem,
    MatchFailedItem,
    MatchReasonItem,
    MissContentReasonItem,
    NoMatchReasonItem,
    ResultItem,
    Template,
)


class PrivateTemplateChecker(BaseTemplateChecker):
    SCHEMA_NAME = "私募-基金合同"
    SYNONYM_PATTERNS = P_PRIVATE_SIMILARITY_PATTERNS
    IGNORE_EXTRA_PARA = False
    CONVERT_TYPES = None

    def __init__(self, reader, file, manager, schema_id=None, labels=None, fund_manager_info=None):
        super().__init__(reader, file, manager, schema_id=schema_id, labels=labels)
        self.fund_manager_info = fund_manager_info
        self.fund_manager_type = self.fund_manager_info.get("基金管理人概况-类型") and self.fund_manager_info.get(
            "基金管理人概况-类型"
        ).get("text")
        if not self.fund_manager_type:
            self.fund_manager_type = "空"

    def render_text(self, text):
        if not text:
            return text

        if "{fund_manager_type}" in text:
            text = text.format(fund_manager_type=self.fund_manager_type)
        return text

    def check(self):
        raise NotImplementedError


class NormalTemplateChecker(PrivateTemplateChecker):
    TEMPLATES = TEMPLATE_MATCH_ANY + SINGLE_CHAPTER_TEMPLATES  # 匹配任一即为合规 + 指定章节与模版文件一致为合规
    _template_reader = None

    @classmethod
    def get_sub_chapters(cls, reader, chapter_patterns):
        chapters = reader.find_sylls_by_pattern(
            chapter_patterns,
            order="index",
            reverse=False,
        )
        res = []
        current = None
        if chapters:
            current = chapters[0]
            for _, item in reader.syllabus_dict.items():
                if current["range"][0] <= item["range"][0] <= current["range"][1]:
                    res.append(item)
        return current, res

    def get_chapter_blocks(self, chapter_patterns, level, reader):
        current_chapter, child_chapters = self.get_sub_chapters(reader=reader, chapter_patterns=chapter_patterns)
        if not current_chapter:
            return None

        parent_level = level - 2
        indexes = []
        for chapter in child_chapters:
            if chapter["level"] - current_chapter["level"] == parent_level:
                element_indexes = []
                if chapter["children"]:
                    for item in chapter["children"]:
                        _range = reader.syllabus_dict.get(item)["range"]
                        if _range:
                            element_indexes.append(_range)
                    if element_indexes[0][0] - chapter["range"][0] > 1:
                        element_indexes.append([chapter["range"][0], element_indexes[0][0]])
                indexes.extend(element_indexes)

        return ChapterBlock(
            chapters=child_chapters,
            chapter=current_chapter,
            indexes=indexes,
            paragraphs=self.reader.find_paragraphs_by_chapters(chapter_patterns)[1],
        )

    @classmethod
    def get_origin_detail(cls, blocks):
        res = []
        for paragraphs, _ in blocks:
            for paragraph in paragraphs:
                res.append(paragraph)
        outlines = get_outlines(res)
        return "\n".join((item["text"] for item in res)), outlines

    @classmethod
    def render_diff_results(cls, results, right_blocks):
        mapping = {item.right[0]["index"]: item for item in results if item.right}
        res = []
        for paragraphs, effective in right_blocks:
            if not effective:
                for item in paragraphs:
                    res.append({"html": item["text"]})
                continue
            if paragraphs:
                result = mapping.get(paragraphs[0]["index"])
                if not result:
                    for item in paragraphs:
                        res.append({"html": f"<u>{item['text']}</u>"})
                else:
                    res.extend(result.similarity.simple_results)
        return res

    def match_template_by_blocks(self, template):
        level = template.get("level")
        left_block = self.get_chapter_blocks(template["template_chapter"], level, self.reader)
        right_block = self.get_chapter_blocks(template["template_chapter"], level, self.get_template_reader())

        if not left_block or not right_block:
            return None

        effective_left_items = [item for item, effective in left_block.blocks() if effective]
        effective_right_items = [item for item, effective in right_block.blocks() if effective]
        if not effective_right_items:
            return None

        res = []
        for left_paragraphs in effective_left_items:
            max_ratio = 0
            max_block = (None, None)
            for right_paragraphs in effective_right_items:
                similarity = ParagraphSimilarity(
                    left_paragraphs, right_paragraphs, fill_paragraph=False, ignore_extra_para=self.IGNORE_EXTRA_PARA
                )
                ratios = [item.ratio for item in similarity.results]
                ratio = 0
                if ratios:
                    ratio = sum(ratios) / len(ratios)
                if ratio >= max_ratio:
                    max_ratio = ratio
                    max_block = (similarity, right_paragraphs)

            res.append(BlockResult(ratio=max_ratio, left=left_paragraphs, right=max_block[1], similarity=max_block[0]))

        return self.render_results(res, left_block, right_block, template["related_name"])

    def render_results(self, res, left_block, right_block, name):
        diff = self.render_diff_results(res, right_block.blocks())
        left_content, _ = self.get_origin_detail(left_block.blocks())
        right_content, outlines = self.get_origin_detail(right_block.blocks())
        page = min(outlines.keys(), default=0)
        if all(math.isclose(item.ratio, 1, abs_tol=10e-6) for item in res) and len(
            left_block.chapter["children"]
        ) == len(right_block.chapter["children"]):
            return MatchReasonItem(
                content=right_content,
                content_title="当前合同",
                page=page,
                outlines=outlines,
                template=Template(content=left_content, name=name),
                diff=diff,
                xpath=get_xpath_by_outlines(self.reader, outlines),
            )

        return ConflictReasonItem(
            content_title="当前合同",
            content=right_content,
            page=page,
            outlines=outlines,
            template=Template(
                content=left_content,
                name=name,
            ),
            diff=diff,
            xpath=get_xpath_by_outlines(self.reader, outlines),
        )

    def get_template_reader(self):
        if not self._template_reader:
            self._template_reader = PdfinsightReader(INTERDOC_PATH)
        return self._template_reader

    @classmethod
    def validate_by_regex(cls, regex_info, paragraph_groups):
        regex = regex_info["regex"]
        func = regex_info["func"]
        formatter = regex_info["format"]
        for paragraphs in paragraph_groups:
            for paragraph in paragraphs:
                text = paragraph["text"]
                matched = regex.search(text)
                if not matched:
                    continue

                paragraph = {
                    "text": matched.group(0),
                    "chars": paragraph["chars"][slice(*matched.span(0))] if paragraph["chars"] else [],
                    "outlines": paragraph["outlines"],
                    "page": paragraph["page"],
                    "index": 1,
                }

                if func(**matched.groupdict()):
                    return ParagraphSimilarity(
                        [matched.group(0)], [paragraph], fill_paragraph=False, ignore_extra_para=cls.IGNORE_EXTRA_PARA
                    )
                return ParagraphSimilarity(
                    [regex.sub(formatter, matched.group(0))],
                    [paragraph],
                    fill_paragraph=False,
                    ignore_extra_para=cls.IGNORE_EXTRA_PARA,
                )
        return None

    def match_template(self, template, paragraphs=None, required=False, similarity_patterns=None):
        items = template.get("items")
        name = template.get("name")
        content_title = template.get("content_title")
        if not items:
            reader = self.get_template_reader()
            _, paragraphs = reader.find_paragraphs_by_chapters(template["template_chapter"])
            items = [item["text"] for item in paragraphs]
        match_templates = self.split_templates_by_conditions(items, paragraphs)
        match_templates = self.recombined_template(match_templates)
        origin_content = "\n".join(match_templates[0])

        # 从全文里取数据
        if not paragraphs:
            _, paragraphs = self.get_paragraphs(template)
        if not paragraphs:
            if template.get("chapter"):
                return MissContentReasonItem(
                    reason_text=self.render_text(template["chapter"]["miss_detail"]["reason_text"]),
                    miss_content=template["chapter"]["miss_detail"].get("miss_content"),
                    template=Template(content=origin_content, name=name),
                )
            return NoMatchReasonItem(template=Template(content=origin_content, name=name))
        group_similarity = defaultdict(list)
        current_similarities = []
        for items in match_templates:
            similarity = ParagraphSimilarity(
                items,
                paragraphs,
                fill_paragraph=False,
                similarity_patterns=similarity_patterns,
                ignore_extra_para=self.IGNORE_EXTRA_PARA,
                convert_types=self.CONVERT_TYPES,
            )
            if similarity.max_ratio > self.MIN_RATIO_THRESHOLD_VALUE:
                group_similarity[similarity.valid_sentences_count].append(similarity)
                current_similarities.append(similarity)
        similarity = None
        if group_similarity:
            # 1、取匹配到段落数最多，相似度最高的模版
            similarities = group_similarity[max(group_similarity)]
            similarity = max(similarities, key=lambda x: x.max_ratio)

            # 2、取相似度最高的模版
            similarities = list(itertools.chain.from_iterable(group_similarity.values()))
            similarity_temp = max(similarities, key=lambda x: x.max_ratio)

            # 3、如果相差大于阈值，且匹配到段落的最大比例小于0.8的时候，取相似度最高的模版
            if similarity_temp != similarity:
                if (
                    similarity_temp.max_ratio - similarity.max_ratio > self.DIFFERENCE_VALUE
                    and similarity.max_ratio < self.THRESHOLD_VALUE
                ):
                    similarity = similarity_temp
        if not similarity:
            return NoMatchReasonItem(
                template=Template(content=origin_content, name=name),
                reason_text=self.render_text(template.get("miss_detail", {}).get("reason_text")),
                suggestion=self.render_text(template.get("miss_detail", {}).get("suggestion")),
            )

        # 指定模板 和 全文内容必须是第一个
        paragraph_groups = [paragraphs]
        items_groups = [items, *template.get("other_items", [])]

        # 从提取结果里取数据
        addition_element_from = template.get("addition_element_from")
        if addition_element_from:
            for element_from in addition_element_from:
                if element_from.get("type") == "field":
                    paragraph_groups.append(self.manager.get(element_from["field"]).get_related_paragraphs())

        for para_index, _paragraphs in enumerate(paragraph_groups):
            if not _paragraphs:
                continue
            for item_index, items in enumerate(items_groups):
                # 跳过 指定模板在全文里的结果，因为已经有了
                if not items or (para_index == 0 and item_index == 0):
                    continue
                similarity_other = ParagraphSimilarity(
                    items,
                    _paragraphs,
                    fill_paragraph=False,
                    ignore_extra_para=self.IGNORE_EXTRA_PARA,
                    convert_types=self.CONVERT_TYPES,
                )
                if similarity_other.max_ratio > similarity.max_ratio:
                    similarity = similarity_other
                    origin_content = "\n".join(items)
                    if similarity.is_full_matched:
                        break

            if similarity.is_full_matched:
                break

        if template.get("regex") and not similarity.is_full_matched:
            regex_similarity = self.validate_by_regex(template["regex"], paragraph_groups)
            if regex_similarity:
                similarity = regex_similarity
                origin_content = similarity.left_content

        outlines = similarity.right_outlines

        if similarity.is_full_matched_or_contain:
            return MatchReasonItem(
                template=Template(content=origin_content, name=name, content_title=content_title),
                content=similarity.right_content,
                content_title="当前合同",
                page=min(outlines, key=int, default=0),
                outlines=outlines,
                diff=similarity.simple_results,
            )

        if similarity.is_matched:
            page = min(outlines.keys(), key=int, default=0)
            return ConflictReasonItem(
                template=Template(content=origin_content, name=name, content_title=content_title),
                content=similarity.right_content,
                page=page,
                content_title="当前合同",
                outlines=outlines,
                diff=similarity.simple_results,
                reason_text=self.render_text(template.get("diff_text")),
                xpath=get_xpath_by_outlines(self.reader, outlines),
            )

        if required:
            return MissContentReasonItem(
                miss_content=template["miss_detail"].get("miss_content"),
                template=Template(content=origin_content, name=name),
                reason_text=self.render_text(template["miss_detail"]["reason_text"]),
                suggestion=self.render_text(template["miss_detail"].get("suggestion")),
            )

    @classmethod
    def check_chapter(cls, reader, chapters):
        chapters = reader.find_sylls_by_pattern(
            chapters,
            order="index",
            reverse=False,
        )
        return bool(chapters)

    @classmethod
    def get_template_items_text(cls, template):
        return "\n".join(template["items"])

    def check(self):
        results = []
        templates = copy.deepcopy(self.get_templates())
        for template in templates:
            if result := self.generate_result_by_templates(template):
                # 过滤相同原因的错误
                self.filter_result(result, template)
                results.append(result)

        return results

    def generate_result_by_templates(self, template, templates=None):
        valid_types = ["PARAGRAPH", "TABLE"]
        reasons = []
        miss_content = False
        for template_item in templates or template["templates"]:
            required = bool(template_item.get("required"))

            flag = False
            reason = self.check_field(template_item)
            if not reason:
                condition = template_item.get("ignore")
                condition_result = False
                ignore_text = ""
                if condition:  # 不适用的情形
                    if isinstance(condition, (list, tuple)):
                        flags = [func(self.manager, self.fund_manager_type) for func in condition]
                        if any(flags):
                            condition_result = True
                        for ignore_index, ignore_text_item in enumerate(template_item.get("ignore_text") or []):
                            if isinstance(ignore_text_item, str):
                                ignore_text += ignore_text_item
                            else:
                                ignore_text += ignore_text_item[0] if flags[ignore_index] else ignore_text_item[1]

                    else:
                        ignore_text = template_item.get("ignore_text")
                        condition_result = condition(self.manager, self.fund_manager_type)

                if condition_result:
                    flag = True
                    reason = IgnoreConditionItem(reason_text=self.render_text(ignore_text))
                else:
                    # 规则条款内的schema_fields独立检查，全部没有答案不进行一致性检查
                    paragraphs = None
                    child_schema_fields = template_item.get("schema_fields", [])
                    if child_schema_fields:
                        child_reasons = self.check_schema_fields(child_schema_fields)
                        reasons.extend(child_reasons)
                        if len(child_reasons) == len(child_schema_fields):
                            continue
                        # 根据当前答案，取合并
                        answer_chapter, paragraphs = get_paragraphs_by_schema_fields(
                            self.reader, self.manager, child_schema_fields, valid_types=valid_types
                        )
                        if not paragraphs:
                            reasons.append(MatchFailedItem(reason_text="当前规则对应的要素答案未找到对应内容"))
                            continue
                        template_item["chapter"] = None
                    reason = self.match_template(template_item, paragraphs, required, self.SYNONYM_PATTERNS)
                    flag = reason.matched

                if not flag and required:
                    miss_content = True

            if flag and template.get("check_chapter"):
                flag = self.check_chapter(self.reader, template["check_chapter"]["chapters"])
                if not flag:
                    reason.matched = False
                    reasons.append(
                        MissContentReasonItem(
                            reason_text=self.render_text(template["check_chapter"]["miss_detail"]["reason_text"]),
                            miss_content=template["check_chapter"]["miss_detail"]["miss_content"],
                            template=None,
                        )
                    )
            reasons.append(reason)

        matched, reasons = self.after_match_template(template, reasons, miss_content)
        suggestion = None
        if not matched:
            suggestion = self.render_suggestion_by_reasons(template, reasons)

        return ResultItem(
            name=template["name"],
            related_name=template["related_name"],
            is_compliance=matched,
            reasons=reasons,
            schema_id=self.schema_id,
            fid=self.file.id,
            suggestion=suggestion,
            label=template["label"],
            origin_contents=self.get_origin_contents(template),
            schema_results=self.manager.build_schema_results(template.get("schema_fields") or []),
            tip=template.get("tip"),
        )


class ChaptersTemplateChecker(PrivateTemplateChecker):
    # left与right均为当前范文中段落，相互比对
    TEMPLATES = CHAPTERS_TEMPLATES

    def match_template(self, template):
        left_chapters, left_paragraphs = self.reader.find_paragraphs_by_chapters(template["left"]["chapter"])
        right_chapters, right_paragraphs = self.reader.find_paragraphs_by_chapters(template["right"]["chapter"])

        if not left_paragraphs:
            return MissContentReasonItem(
                miss_content=template["left"]["miss_detail"].get("miss_content"),
                reason_text=template["left"]["miss_detail"]["reason_text"],
            )

        if not right_paragraphs:
            return MissContentReasonItem(
                miss_content=template["right"]["miss_detail"].get("miss_content"),
                reason_text=template["right"]["miss_detail"]["reason_text"],
            )

        left_paragraphs = self.ignore_elements(left_chapters, left_paragraphs, template["left"].get("ignore_elements"))
        right_paragraphs = self.ignore_elements(
            right_chapters, right_paragraphs, template["left"].get("ignore_elements")
        )

        similarity = ParagraphSimilarity(
            left_paragraphs, right_paragraphs, fill_paragraph=False, ignore_extra_para=self.IGNORE_EXTRA_PARA
        )
        left_outlines = similarity.left_outlines
        right_outlines = similarity.right_outlines
        name = "章节"

        left_origin_content = "\n".join([item["text"] for item in left_paragraphs])
        left_page = min(left_outlines.keys(), key=int, default=0)
        right_page = min(right_outlines.keys(), key=int, default=0)

        if similarity.is_full_matched_or_contain:
            return MatchReasonItem(
                template=Template(
                    content_title=self.get_chapter_numbering(left_chapters, self.reader),
                    content=left_origin_content,
                    name=name,
                    page=left_page,
                    outlines=left_outlines,
                ),
                content=similarity.right_content,
                page=right_page,
                content_title=self.get_chapter_numbering(right_chapters, self.reader),
                outlines=right_outlines,
                diff=similarity.simple_results,
                xpath=get_xpath_by_outlines(self.reader, right_outlines),
            )

        if similarity.is_matched:
            return ConflictReasonItem(
                template=Template(
                    content_title=self.get_chapter_numbering(left_chapters, self.reader),
                    content=left_origin_content,
                    name=name,
                    page=left_page,
                    outlines=left_outlines,
                ),
                content=similarity.right_content,
                page=right_page,
                content_title=self.get_chapter_numbering(right_chapters, self.reader),
                outlines=right_outlines,
                diff=similarity.simple_results,
                reason_text=template.get("diff_text"),
                xpath=get_xpath_by_outlines(self.reader, right_outlines),
            )
        return NoMatchReasonItem(
            template=Template(
                content_title=self.get_chapter_numbering(left_chapters, self.reader),
                name=name,
                content=left_origin_content,
                page=left_page,
                outlines=left_outlines,
            ),
            reason_text=template.get("miss_detail", {}).get("reason_text"),
        )

    def check(self):
        results = []
        for template in self.get_templates():
            reason = self.match_template(template)
            suggestion = None
            if not reason.matched:
                suggestion = reason.render_suggestion(self.reader, template["related_name"])
                if isinstance(reason, ConflictReasonItem):
                    suggestion = template.get("diff_suggestion")
            results.append(
                ResultItem(
                    name=template["name"],
                    related_name=template["related_name"],
                    is_compliance=reason.matched,
                    reasons=[reason],
                    fid=self.file.id,
                    origin_contents=self.get_origin_contents(template),
                    schema_id=self.schema_id,
                    suggestion=suggestion,
                    label=template["label"],
                    tip=template.get("tip"),
                )
            )
        return results


class ChapterWithTemplateChecker(PrivateTemplateChecker):
    TEMPLATES = CHAPTERS_WITH_TEMPLATES

    def match_one_template(self, name, left_paragraphs, paragraphs, diff_text, miss_detail, left_title, right_title):
        similarity = ParagraphSimilarity(
            left_paragraphs, paragraphs, fill_paragraph=False, ignore_extra_para=self.IGNORE_EXTRA_PARA
        )
        right_outlines = similarity.right_outlines
        left_origin_content = "\n".join(item["text"] if isinstance(item, dict) else item for item in left_paragraphs)
        right_page = min(right_outlines.keys(), key=int, default=0)
        if similarity.is_full_matched_or_contain:
            return MatchReasonItem(
                template=Template(content=left_origin_content, name=name, content_title=left_title),
                content=similarity.right_content,
                page=right_page,
                content_title=right_title,
                outlines=right_outlines,
                diff=similarity.simple_results,
                xpath=get_xpath_by_outlines(self.reader, right_outlines),
            )

        if similarity.is_matched:
            return ConflictReasonItem(
                template=Template(content=left_origin_content, name=name, content_title=left_title),
                content=similarity.right_content,
                page=right_page,
                content_title=right_title,
                outlines=right_outlines,
                diff=similarity.simple_results,
                reason_text=diff_text,
                xpath=get_xpath_by_outlines(self.reader, right_outlines),
            )

        return NoMatchReasonItem(
            template=Template(name=name, content=left_origin_content),
            reason_text=miss_detail.get("reason_text"),
        )

    def match_template(self, template):
        _, left_paragraphs = self.get_paragraphs(template["left"])
        _, right_paragraphs = self.get_paragraphs(template["right"])

        reasons = []
        if not left_paragraphs:
            reasons.append(
                MissContentReasonItem(
                    miss_content=template["left"].get("miss_detail", {}).get("miss_content"),
                    reason_text=template["left"].get("miss_detail", {}).get("miss_text"),
                )
            )
        else:
            reasons.extend(list(self.match_sub_template(left_paragraphs, template["left"])))

        if not right_paragraphs:
            reasons.append(
                MissContentReasonItem(
                    miss_content=template["right"].get("miss_detail", {}).get("miss_content"),
                    reason_text=template["right"].get("miss_detail", {}).get("miss_text"),
                )
            )
        else:
            reasons.extend(list(self.match_sub_template(right_paragraphs, template["right"])))

        return reasons

    def match_sub_template(self, paragraphs, template):
        for sub_template in template["templates"]:
            yield self.match_one_template(
                sub_template["name"],
                sub_template["items"],
                paragraphs,
                diff_text=sub_template.get("diff_text"),
                miss_detail=sub_template.get("miss_detail") or {},
                left_title=sub_template["content_title"],
                right_title="当前合同",
            )

    def render_suggestion_by_reasons(self, template, reasons):
        res = []
        for item in reasons:
            if not item.matched:
                res.append(item.render_suggestion(self.reader, template["related_name"]))
        return "\n".join(x for x in res if x)

    def check(self):
        results = []
        for template in self.get_templates():
            reasons = self.match_template(template)
            matched = all(item.matched for item in reasons)

            suggestion = self.render_suggestion_by_reasons(template, reasons)
            results.append(
                ResultItem(
                    name=template["name"],
                    related_name=template["related_name"],
                    is_compliance=matched,
                    reasons=reasons,
                    fid=self.file.id,
                    origin_contents=self.get_origin_contents(template),
                    schema_id=self.schema_id,
                    suggestion=suggestion,
                    label=template["label"],
                    schema_results=self.manager.build_schema_results(template.get("schema_fields") or []),
                    tip=template.get("tip"),
                )
            )
        return results


class SentenceSearcher(PrivateTemplateChecker):
    TEMPLATES = SENTENCE_TEMPLATES

    def match_template(self, template):
        res = []
        for template_item in template["templates"]:
            _, right_paragraphs = self.get_paragraphs(template_item)
            results = ParagraphSimilarity.search_sentences(template_item["items"], right_paragraphs)
            res.append((template_item, results))

        for template_item, results in res:
            if len(results) >= template_item["sentence_count"] and all(item.is_full_matched for item in results):
                left_content = "\n".join(template_item["items"])
                reasons = []
                for result in results:
                    page = None
                    outlines = {}
                    if result.right:
                        outlines = get_outlines([result.right.origin])
                        page = min(outlines.keys(), default=0)
                    reasons.append(
                        MatchReasonItem(
                            template=Template(
                                content_title=template_item["content_title"],
                                content=left_content,
                                name=template_item["name"],
                            ),
                            content=result.right_content,
                            page=page,
                            content_title="当前合同",
                            outlines=outlines,
                            diff=self.mock_diff_html_by_diff_content([result]),
                            xpath=get_xpath_by_outlines(self.reader, outlines),
                        )
                    )
                return True, None, reasons

        reasons = []
        for template_item, results in res:
            left_content = "\n".join(template_item["items"])
            if not results:
                reasons.append(
                    NoMatchReasonItem(
                        template=Template(name=template_item["name"], content=left_content),
                        reason_text=f"未找到与{template_item['name']}匹配的内容",
                    )
                )
                continue

            matched_count = 0
            for result in results:
                page = None
                outlines = {}
                if result.right:
                    outlines = get_outlines([result.right.origin])
                    page = min(outlines.keys(), default=0)
                if result.is_full_matched:
                    reasons.append(
                        MatchReasonItem(
                            template=Template(
                                content_title=template_item["content_title"],
                                content=left_content,
                                name=template_item["name"],
                            ),
                            content=result.right_content,
                            page=page,
                            content_title="当前合同",
                            outlines=outlines,
                            diff=self.mock_diff_html_by_diff_content([result]),
                            xpath=get_xpath_by_outlines(self.reader, outlines),
                        )
                    )
                    matched_count += 1

                elif result.is_matched:
                    reasons.append(
                        ConflictReasonItem(
                            template=Template(
                                content_title=template_item["content_title"],
                                content=left_content,
                                name=template_item["name"],
                            ),
                            content=result.right_content,
                            page=page,
                            content_title="当前合同",
                            outlines=outlines,
                            diff=self.mock_diff_html_by_diff_content([result]),
                            reason_text=template_item.get("diff_text"),
                            xpath=get_xpath_by_outlines(self.reader, outlines),
                        )
                    )
                    matched_count += 1
            if matched_count < template_item["sentence_count"]:
                count = number2chinese(matched_count)
                reasons.append(
                    NoMatchReasonItem(
                        template=Template(name=template_item["name"], content=left_content),
                        reason_text=f"仅匹配到{count}条{template_item['name']}",
                    )
                )

        return False, self.generate_suggestion_by_reasons(template, reasons), reasons

    def check(self):
        results = []
        for template in self.get_templates():
            matched, suggestion, reasons = self.match_template(template)
            results.append(
                ResultItem(
                    name=template["name"],
                    related_name=template["related_name"],
                    is_compliance=matched,
                    reasons=reasons,
                    fid=self.file.id,
                    origin_contents=self.get_origin_contents(template),
                    schema_id=self.schema_id,
                    suggestion=suggestion,
                    label=template["label"],
                    schema_results=self.manager.build_schema_results(template.get("schema_fields") or []),
                    tip=template.get("tip"),
                )
            )
        return results
