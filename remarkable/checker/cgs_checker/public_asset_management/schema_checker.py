import re
from collections import defaultdict
from dataclasses import dataclass
from functools import cached_property
from itertools import chain

from remarkable.checker.cgs_checker.base_schema_checker import BaseSchemaChecker, replace_parenthesis
from remarkable.checker.cgs_checker.public_asset_management.template_checker import PublicAssetSingleWithRatioChecker
from remarkable.checker.checkers.conditions_checker import BaseConditionsChecker, BaseSentenceMultipleChecker
from remarkable.common.constants import RuleType
from remarkable.common.convert_number_util import NumberUtil
from remarkable.common.pattern import PatternCollection
from remarkable.common.util import clean_txt
from remarkable.pdfinsight.text_util import clear_syl_title
from remarkable.plugins.cgs.common.chapters_patterns import CatalogsPattern, ChapterPattern, RegularChapter
from remarkable.plugins.cgs.common.enum_utils import TemplateCheckTypeEnum
from remarkable.plugins.cgs.common.para_similarity import (
    DIFF_DELETE,
    DIFF_EQUAL,
    DIFF_INSERT,
    P_SUB_PUNCTUATION,
    PUNCTUATION_CHARS,
    DiffResult,
    ParagraphSimilarity,
    Sentence,
)
from remarkable.plugins.cgs.common.patterns_util import (
    P_CATALOG_TITLE,
    P_NUMBERING,
    P_PUBLIC_SIMILARITY_PATTERNS,
    R_CN_NUMBER,
    R_CONJUNCTION,
    R_FLOAT_NUMBER,
    R_NOT_CONJUNCTION_PUNCTUATION,
    R_PUNCTUATION,
)
from remarkable.plugins.cgs.common.template_condition import (
    AssetTemplateConditional,
    FundTypeRelation,
    TemplateName,
    TemplateRelation,
)
from remarkable.plugins.cgs.common.utils import (
    append_suggestion,
    get_outlines,
    get_paragraphs_by_schema_answers,
    get_paragraphs_by_schema_fields,
    get_xpath_by_outlines,
)
from remarkable.plugins.cgs.schemas.reasons import (
    ConflictReasonItem,
    IgnoreConditionItem,
    MatchFailedItem,
    MatchReasonItem,
    MatchSuccessItem,
    MissContentReasonItem,
    NoMatchReasonItem,
    ResultItem,
    Template,
)
from remarkable.plugins.predict.common import clear_syl_title_num, is_catalog, is_paragraph_elt


@dataclass
class CheckResultRelation:
    name: str
    pattern: PatternCollection
    result: bool = False
    condition: TemplateRelation = None


class AssetSchemaChecker(BaseSchemaChecker):
    SCHEMA_NAME = "公募-资产管理合同"
    NAME = ""
    RELATED_NAME = ""
    LABEL = ""
    SCHEMA_FIELDS = []
    RULE_TYPE = RuleType.SCHEMA.value
    # https://gitpd.paodingai.com/cheftin/docs_scriber/-/issues/2272#note_351380
    SYNONYM_PATTERNS = P_PUBLIC_SIMILARITY_PATTERNS
    P_ITEMS = []
    IS_COMPLETE_MATCH = True
    R_SPLIT = r"，,.．、？?。！!：: ;；及与和"

    def check(self):
        raise NotImplementedError

    @cached_property
    def result(self):
        return ResultItem(
            name=self.NAME,
            related_name=self.RELATED_NAME,
            is_compliance=True,
            reasons=[],
            suggestion=None,
            schema_id=self.schema_id,
            fid=self.file.id,
            schema_results=self.manager.build_schema_results(self.SCHEMA_FIELDS),
            label=self.LABEL,
            rule_type=self.RULE_TYPE,
            origin_contents=self.get_origin_contents(),
            contract_content=self.get_contract_content(),
        )

    def check_syllabuses(
        self, p_chapter: RegularChapter, paragraphs: list = None, exclude_chapter=True, check_paragraphs=True
    ):
        find = False
        chapters = []
        valid_paras, reason = self.get_valid_paras(p_chapter, paragraphs, exclude_chapter, check_paragraphs)
        if not reason:
            if not valid_paras:
                if not chapters:
                    chapters, _ = self.reader.find_paragraphs_by_chapters(
                        [p_chapter.pattern], with_parent_chapters=True
                    )
                for chapter in chapters:
                    _, elt = self.reader.find_element_by_index(chapter["element"])
                    if elt and is_paragraph_elt(elt):
                        valid_paras.append(elt)
            else:
                find = True
            self.result.is_compliance, reason = self.check_templates(valid_paras)
        self.result.reasons.extend(self.filter_same_reason([reason]))
        self.result.suggestion = self.generate_suggestion_by_reasons(self.result.reasons)
        return find

    def get_valid_paras(
        self, p_chapter: RegularChapter, paragraphs: list = None, exclude_chapter=True, check_paragraphs=True
    ):
        chapters, valid_paras, reason = [], [], ""

        if paragraphs is None:
            chapters, paragraphs = self.reader.find_paragraphs_by_chapters(
                [p_chapter.pattern], with_parent_chapters=True
            )
            # https://gitpd.paodingai.com/cheftin/docs_scriber/-/issues/2449
            if exclude_chapter:
                chapter_index = [chapter["element"] for chapter in chapters]
                paragraphs = [para for para in paragraphs if para["index"] not in chapter_index]
        # https://gitpd.paodingai.com/cheftin/docs_scriber/-/issues/2576
        if check_paragraphs and not paragraphs and not chapters:
            self.result.is_compliance = False
            reason = MissContentReasonItem(
                reason_text=f"章节《{p_chapter.name}》不存在",
                miss_content="",
                suggestion=f"请在合同中补充《{p_chapter.name}》章节的内容",
            )

        else:
            for paragraph in paragraphs:
                txt = clean_txt(paragraph["text"])
                if not P_NUMBERING.nexts(txt):
                    continue
                for item in self.P_ITEMS:
                    if item.condition and not self.manager.verify_condition([item.condition]):
                        continue
                    if item.pattern.nexts(txt):
                        valid_paras.append(paragraph)
                        break
        return valid_paras, reason

    @cached_property
    def condition_checker(self):
        condition_checker = BaseConditionsChecker(
            reader=self.reader,
            manager=self.manager,
            file=self.file,
            schema_id=self.schema_id,
            labels=self.labels,
            fund_manager_info=self.fund_manager_info,
        )
        return condition_checker

    def generate_suggestion_by_reasons(self, reasons):
        suggestion = ""
        for item in reasons:
            if hasattr(item, "template") and item.template and item.template.name == "范文" and not item.matched:
                item_suggestion = item.render_suggestion(self.reader, self.RELATED_NAME)
                if not suggestion or item_suggestion not in suggestion:
                    suggestion = append_suggestion(suggestion, item_suggestion)
            elif not item.matched:
                item_suggestion = item.render_suggestion(self.reader, self.RELATED_NAME)
                suggestion = append_suggestion(suggestion, item_suggestion)
        return suggestion

    def check_templates(self, paragraphs):
        match_templates = self.split_paragraphs_by_pattern(paragraphs)
        para_mapping = {para["index"]: para for para in paragraphs}
        match_paras, diff_results = self.diff_templates(match_templates, para_mapping)
        checker = BaseSentenceMultipleChecker(
            reader=self.reader,
            manager=self.manager,
            file=self.file,
            schema_id=self.schema_id,
            labels=self.labels,
            fund_manager_info=self.fund_manager_info,
        )
        content = "\n".join([checker.get_content_by_diff_results([diff]) for diff in diff_results])
        template = Template(name="范文", content_title="合同范文", content=content)
        if not match_paras:
            outlines = get_outlines(paragraphs)
            template.outlines = outlines
            template.page = min(outlines, default=0)
            return False, NoMatchReasonItem(template=template, reason_text="未找到与范文匹配的内容")
        template_item = {"name": "范文", "content_title": "合同范文"}
        if ParagraphSimilarity.judge_is_full_matched(diff_results):
            return True, checker.generate_match_reason(template_item, diff_results, paragraphs=match_paras)
        return False, checker.generate_conflict_reason(template_item, diff_results, paragraphs=match_paras)

    def group_paragraphs_by_patterns(self, paragraphs):
        group_matchs = []
        for relation in self.P_ITEMS:
            relation.name = P_SUB_PUNCTUATION.sub("", relation.name)
            if relation.condition and not self.manager.verify_condition([relation.condition]):
                continue
            match_paras = []
            for para in paragraphs:
                if not is_paragraph_elt(para):
                    continue
                match_content = clean_txt(para["text"])
                if not relation.pattern.nexts(match_content):
                    continue
                diff_results = ParagraphSimilarity.search_sentences([relation.name], [match_content], min_ratio=0.1)
                if diff_results:
                    match_paras.append((diff_results[0], para))
            # 获取最高匹配的位置
            if not match_paras:
                group_matchs.append((relation, None))
            else:
                results = sorted(match_paras, key=lambda x: x[0].ratio, reverse=True)
                group_matchs.append((relation, results[0][-1]))
        return group_matchs

    def split_paragraphs_by_pattern(self, paragraphs) -> dict:
        templates = defaultdict(list)
        # https://gitpd.paodingai.com/cheftin/docs_scriber/-/issues/2558
        group_matchs = self.group_paragraphs_by_patterns(paragraphs)
        for relation, para in group_matchs:
            if not para:
                templates[-1].append((relation.name, None))
                continue
            match_content = clean_txt(para["text"])
            if not (res := relation.pattern.nexts(match_content)):
                continue
            content_start = content_end = None
            prev_start = 0
            # 按符号拆分句子，定位当前句子所在最近的符号，截取完整的子句
            # https://gitpd.paodingai.com/cheftin/docs_scriber/-/issues/2562#note_352695
            # 暂时仅过滤句子中存在、 # add 过滤及与和  # https://gitpd.paodingai.com/cheftin/docs_scriber/-/issues/2571
            split_str = {"、", "及", "和", "与"} & set(relation.name)
            split_val = "".join(val for val in self.R_SPLIT if val not in split_str) if split_str else self.R_SPLIT
            p_split = PatternCollection(rf"[{split_val}]")
            for link_res in p_split.finditer(match_content):
                if content_start is not None and content_end is not None:
                    break
                start, end = link_res.span()
                if content_start is None and start > res.start():
                    content_start = prev_start
                if content_start is not None and not content_end and start >= res.end():
                    content_end = start
                prev_start = end
            else:
                if content_start is None:
                    content_start = prev_start
                if content_end is None:
                    content_end = len(match_content)
            relation.result = True
            templates[para["index"]].append((relation.name, (content_start, content_end)))
        for idx, child in templates.items():
            if idx == -1:
                continue
            templates[idx] = sorted(child, key=lambda x: x[-1][0])
        return dict(sorted(templates.items()))

    def diff_templates(self, match_templates, para_mapping):
        all_diffs = []
        match_paras = []
        unmatch_templates = match_templates.pop(-1, [])
        para_idx = template_idx = 0
        for index, templates in match_templates.items():
            para = para_mapping[index]
            match_paras.append(para)
            all_diffs.append(
                self.generate_diff_result(para, templates, para_index=para_idx, template_index=template_idx)
            )
            para_idx += 1
            template_idx += 1

        for template, *_ in unmatch_templates:
            template += "；"
            pack_data = {"text": template, "chars": [], "para_index": template_idx, "origin": None}
            left = self.mock_sentence(pack_data, total=template_idx)
            all_diffs.append(DiffResult(left=left, right=None, ratio=0, diff=[(DIFF_DELETE, ch) for ch in template]))
        return match_paras, all_diffs

    def generate_diff_result(self, para, templates, para_index=0, template_index=0):
        diffs = []
        clean_content = clean_txt(para["text"])
        prev_start = 0
        template_items = []
        # 完全匹配，无需拆分句子，多余的字符应为DIFF_INSERT, 非完全匹配，则为DIFF_EQUAL
        ratio, diff_type = (0, DIFF_INSERT) if self.IS_COMPLETE_MATCH else (1.0, DIFF_EQUAL)

        # symbol_start, symbol_end: 符号拆分句子的位置
        # p_start, p_end: 正则匹配到关键词的位置
        for template, (symbol_start, symbol_end) in templates:
            template_items.append(template)
            content = clean_content[symbol_start:symbol_end]
            # https://gitpd.paodingai.com/cheftin/docs_scriber/-/issues/2590#note_353933
            if prev_start == 0 and (number_res := P_NUMBERING.nexts(clean_content[prev_start:symbol_start])):
                prev_start = number_res.end()
                diffs.append(
                    DiffResult(
                        left=None,
                        right=None,
                        ratio=1.0,
                        diff=[(DIFF_EQUAL, ch) for ch in clean_content[:prev_start]],
                    )
                )
            if prev_start < symbol_start:
                diffs.append(
                    DiffResult(
                        left=None,
                        right=None,
                        ratio=ratio,
                        diff=[(diff_type, ch) for ch in clean_content[prev_start:symbol_start]],
                    )
                )
            prev_start = symbol_end
            if not self.IS_COMPLETE_MATCH and template in content:
                diffs.append(DiffResult(left=None, right=None, ratio=ratio, diff=[(diff_type, ch) for ch in content]))
                continue
            diff_results = ParagraphSimilarity.search_sentences([template], [content], min_ratio=0.1)
            if not diff_results:
                diffs.append(DiffResult(left=None, right=None, ratio=0, diff=[(DIFF_DELETE, ch) for ch in template]))
                continue
            diff_result = diff_results[0]
            prev_pos = 0
            for idx, diff in enumerate(diff_result.diff):
                if diff[0] != DIFF_INSERT:
                    prev_pos = idx
                    break
            if prev_pos != 0:
                diffs.append(
                    DiffResult(
                        left=None,
                        right=None,
                        ratio=ratio,
                        diff=[(diff_type, ch[-1]) for ch in diff_result.diff[:prev_pos]],
                    )
                )
                diff_result.diff = diff_result.diff[prev_pos:]
            last_diffs = []
            diff_len = len(diff_result.diff)
            for idx, diff in enumerate(reversed(diff_result.diff)):
                if diff[0] != DIFF_INSERT:
                    if idx != 0:
                        last_diffs = diff_result.diff[diff_len - idx :]
                        diff_result.diff = diff_result.diff[: diff_len - idx]
                    break
            diffs.append(diff_result)
            if last_diffs:
                diffs.append(
                    DiffResult(left=None, right=None, ratio=ratio, diff=[(diff_type, ch[-1]) for ch in last_diffs])
                )
        if tail_content := clean_content[prev_start:]:
            diffs.append(DiffResult(left=None, right=None, ratio=ratio, diff=[(diff_type, ch) for ch in tail_content]))
        pack_data = {
            "text": f"{'、'.join(template_items)}；",
            "chars": [],
            "para_index": template_index,
            "origin": None,
        }
        left = self.mock_sentence(pack_data, total=template_index)
        pack_data = {"text": para["text"], "chars": para["chars"], "para_index": para["index"], "origin": para}
        right = self.mock_sentence(pack_data, total=para_index)
        # https://gitpd.paodingai.com/cheftin/docs_scriber/-/issues/2563#note_356004
        if len(diffs) > 1:
            last_diff = diffs[-1]
            if (
                len(last_diff.diff) == 1
                and last_diff.diff[0][0] != DIFF_EQUAL
                and last_diff.diff[0][1] in PUNCTUATION_CHARS
            ):
                if diffs[-2].diff[-1][0] == DIFF_EQUAL and diffs[-2].diff[-1][1] not in PUNCTUATION_CHARS:
                    last_diff.ratio = 1
                    last_diff.diff = [(DIFF_EQUAL, last_diff.diff[0][1])]
        diff = list(chain.from_iterable(item.diff for item in diffs))
        ParagraphSimilarity.fix_abnormal_diff(diff, format_type="tuple")
        return DiffResult(left=left, right=right, ratio=ParagraphSimilarity.calc_weighted_ratio(diffs), diff=diff)

    @staticmethod
    def mock_sentence(pack_data, total=0) -> Sentence:
        text = pack_data["text"]
        para_index = pack_data["para_index"]
        origin = pack_data["origin"]
        chars = pack_data["chars"]
        return Sentence(
            index=total,
            text=text,
            sentence_index=0,
            index_mapping={},
            cleaned_text=text,
            para_index=para_index,
            ends="",
            chars=chars if chars else None,
            origin=origin,
        )


class ConsistencyDirectorySchemaChecker(AssetSchemaChecker):
    NAME = "验证目录准确性"
    RELATED_NAME = "目录"
    LABEL = "schema_1006"
    ORIGIN = "第十二条 资产管理合同目录应当自首页开始排印。目录应当列明各个具体标题及相应的页码。"

    def check(self):
        if not self.manager.verify_condition([AssetTemplateConditional.NAME_SINGLE_POOLED]):
            self.result.reasons.append(IgnoreConditionItem(reason_text="当前基金类型不是单一或集合类型"))
            return self.result

        _, paragraphs = self.reader.find_paragraphs_by_chapters([re.compile(r"目录")], is_continued_chapter=False)

        for paragraph in paragraphs:
            find = False
            paragraph_text = paragraph["text"]
            if is_catalog(paragraph_text.rstrip()):
                text = clear_syl_title(paragraph_text)
                text = clear_syl_title_num(text)  # add by # 2498
                if match := P_CATALOG_TITLE.nexts(paragraph_text):
                    if no := match.group("no"):
                        cover_text, elements = self.join_page_text(int(no) - 1)
                        if text in cover_text:
                            find = True
                else:
                    for item in self.reader.syllabuses:
                        if text == clear_syl_title(item["title"]):
                            find = True
                            break

                if not find:
                    outlines = get_outlines([paragraph])
                    self.result.reasons.append(
                        MatchFailedItem(
                            page=min(outlines, key=int, default=0),
                            outlines=outlines,
                            reason_text=f'目录章节"{text}"未找到',
                        )
                    )
        if self.result.reasons:
            self.result.is_compliance = False
            self.result.suggestion = "建议检查目录章节"
        return self.result


class NamingNotationsSchemaChecker(AssetSchemaChecker):
    NAME = "资管计划的命名要求"
    RELATED_NAME = "封面"
    LABEL = "schema_1005"
    SCHEMA_FIELDS = ["计划名称", "计划管理人-名称"]
    # 获取管理人简称 https://gitpd.paodingai.com/cheftin/docs_scriber/-/issues/1980#note_363334
    P_MGR_ABBREVIATION = PatternCollection(r".*(基金|证券|银行|期货|资本|投资|资产)")
    CONTRACT_CONTENT = [
        "【集合】",
        "第十条",
        "资产管理合同封面应当标有“XX集合资产管理计划资产管理合同”的字样与合同编号，封面下端应当标明管理人及托管人名称的全称。",
        "第十一条",
        "资产管理计划的产品名称应当包括管理人简称，格式为“管理人简称 + XX集合资产管理计划”。资产管理计划存在如下情况的应在名称中加入相应标识：",
        "（一）资产管理计划存在分级结构的，应含“分级”或“结构化”字样；",
        "（二）基金中基金资产管理计划、管理人中管理人资产管理计划，应含“FOF”、“MOM”或者其他能反映该资产管理计划类别的字样；",
        "（三）员工持股计划、以收购上市公司为目的设立的资产管理计划等具有特定投资管理目标的资产管理计划应按照规定在其名称中表明反映该资产管理计划投资管理目标的字样。",
        "资产管理计划的产品名称应保持唯一性，且不得存在可能误导投资者的表述。",
        "【单一】",
        "第十条",
        "资产管理合同封面应当标有“XX单一资产管理计划资产管理合同”的字样与合同编号，封面下端应当标明投资者、管理人及托管人（如有）名称的全称。",
        "第十一条",
        "资产管理计划的产品名称应当包括管理人简称，格式为“管理人简称 + XX单一资产管理计划”。资产管理计划存在如下情况的应在名称中加入相应标识：",
        "（一）基金中基金资产管理计划、管理人中管理人资产管理计划，应含“FOF”、“MOM”或者其他能反映该资产管理计划类别的字样；",
        "（二）员工持股计划、以收购上市公司为目的设立的资产管理计划等具有特定投资管理目标的资产管理计划应按照规定在其名称中表明反映该资产管理计划投资管理目标的字样。",
        "资产管理计划的产品名称应保持唯一性，且不得存在可能误导投资者的表述。",
    ]

    def check(self):
        project_name = self.manager.get(self.SCHEMA_FIELDS[0])
        if not project_name.value:
            suggestion = "请添加计划名称"
            self.result.is_compliance = False
            self.result.reasons = [MatchFailedItem(reason_text="计划名称不能为空")]
            self.result.suggestion = suggestion
            return self.result
        if self.manager.verify_condition([AssetTemplateConditional.NAME_SINGLE_POOLED]):
            manager_name = self.manager.get(self.SCHEMA_FIELDS[1])
            if not manager_name.value:
                suggestion = "请添加管理人名称"
                self.result.is_compliance = False
                self.result.reasons = [MatchFailedItem(reason_text="管理人名称不能为空")]
                self.result.suggestion = suggestion
                return self.result
            if (
                abbreviation := self.P_MGR_ABBREVIATION.nexts(manager_name.value)
            ) and abbreviation.group() not in project_name.value:
                self.result.reasons.append(
                    MatchFailedItem(
                        reason_text=f"计划名称应包含管理人简称“{abbreviation.group()}”",
                    )
                )
                self.result.is_compliance = False
        elif self.manager.verify_condition([AssetTemplateConditional.FOF]):
            if "FOF" not in project_name.value:
                self.result.reasons.append(
                    MatchFailedItem(
                        reason_text="计划名称应包含“FOF”",
                    )
                )
                self.result.is_compliance = False
        if not self.result.is_compliance:
            self.result.suggestion = "检查计划名称"
        return self.result


class InvestmentProportionSchemaChecker(AssetSchemaChecker):
    NAME = "全文投资比例限制内容保持一致"
    RELATED_NAME = ""
    LABEL = "schema_1004"

    CHAPTER_ASSET_BASIC_INFO = "资产管理计划的基本情况"
    CHAPTER_ASSET_INVEST = "资产管理计划的投资"
    CHAPTER_ULTRA_VIRES = "越权交易的界定"

    SCHEMA_FIELDS = []

    P_CHAPTERS = [re.compile(r"越权交易的?(处理|界定)")]

    def check(self):
        # https://gitpd.paodingai.com/cheftin/docs_scriber/-/issues/1980#note_352473
        # 拆分schema前缀，投资比例、投资限制或投资比例及限制
        prefix_schema_fields = (
            ["投资比例", "投资限制"]
            if "投资比例-资产管理计划的基本情况" in self.manager.mapping
            else ["投资比例及限制"]
        )
        self.SCHEMA_FIELDS = []
        for prefix in prefix_schema_fields:
            self.SCHEMA_FIELDS.extend(
                [f"{prefix}-{self.CHAPTER_ASSET_BASIC_INFO}", f"{prefix}-{self.CHAPTER_ASSET_INVEST}"]
            )
        answer_dict = self.check_schema_fields(self.result)
        self.result.is_compliance = False
        # 以基本情况章节提取的要素为基准，与其他内容做比对
        unmatch_fields = []
        for prefix in prefix_schema_fields:
            res, paragraphs = self.get_schema_paragraphs(answer_dict, f"{prefix}-{self.CHAPTER_ASSET_BASIC_INFO}")
            if not res:
                unmatch_fields.append(prefix)
                continue
            if not paragraphs:
                self.add_miss_reason(self.CHAPTER_ASSET_BASIC_INFO, prefix)
                continue
            # 资产管理计划的投资章节
            self.check_asset_invest(self.CHAPTER_ASSET_BASIC_INFO, prefix, paragraphs)
            # 越权交易章节
            self.check_ultra_vires(self.CHAPTER_ASSET_BASIC_INFO, prefix, paragraphs)
        for prefix in unmatch_fields:
            res, paragraphs = self.get_schema_paragraphs(answer_dict, f"{prefix}-{self.CHAPTER_ASSET_INVEST}")
            if not res:
                continue
            if not paragraphs:
                self.add_miss_reason(self.CHAPTER_ASSET_INVEST, prefix)
                continue
            # 越权交易章节
            self.check_ultra_vires(self.CHAPTER_ASSET_INVEST, prefix, paragraphs)
        if all(isinstance(reason, MatchSuccessItem) for reason in self.result.reasons):
            self.result.is_compliance = True

        return self.result

    def add_miss_reason(self, chapter_name, invest_type):
        reason = MissContentReasonItem(
            reason_text=f"章节《{chapter_name}》的“{invest_type}”不存在",
            miss_content="",
            suggestion=f"请在《{chapter_name}》章节内补充{invest_type}的内容",
        )
        self.result.reasons.append(reason)
        self.result.suggestion = append_suggestion(self.result.suggestion, reason.suggestion)

    def get_schema_paragraphs(self, answer_dict, schema_field):
        answer = answer_dict.get(schema_field)
        if not answer or not answer.value:
            return False, []
        chapter, paragraphs = get_paragraphs_by_schema_answers(self.reader, [answer])
        return True, [para for para in paragraphs if para["index"] != chapter["element"]]

    def check_asset_invest(self, base_chapter_name, invest_type, basic_paragraphs):
        answer = self.manager.get(f"{invest_type}-{self.CHAPTER_ASSET_INVEST}")
        chapter, paragraphs = get_paragraphs_by_schema_answers(self.reader, [answer])
        paragraphs = [para for para in paragraphs if para["index"] != chapter["element"]]
        self.compare_paragraphs(basic_paragraphs, paragraphs, self.CHAPTER_ASSET_INVEST, invest_type, base_chapter_name)

    def check_ultra_vires(self, base_chapter_name, invest_type, basic_paragraphs):
        chapters, paragraphs = self.reader.find_paragraphs_by_chapters(self.P_CHAPTERS)
        if not paragraphs:
            self.add_miss_reason(self.CHAPTER_ULTRA_VIRES, invest_type)
            return
        chapter_index = [chapter["element"] for chapter in chapters]
        paragraphs = [para for para in paragraphs if para["index"] not in chapter_index]

        self.compare_paragraphs(basic_paragraphs, paragraphs, self.CHAPTER_ULTRA_VIRES, invest_type, base_chapter_name)

    def compare_paragraphs(self, left_paragraphs, right_paragraphs, chapter_name, invest_type, base_chapter_name):
        similarity = ParagraphSimilarity(
            left_paragraphs,
            right_paragraphs,
            ignore_extra_para=True,
            similarity_patterns=self.SYNONYM_PATTERNS,
        )

        if similarity.is_full_matched_or_contain or similarity.is_full_matched_without_extra_para:
            outlines = similarity.right_outlines
            self.result.reasons.append(
                MatchSuccessItem(
                    page=min(outlines, key=int, default=0),
                    outlines=outlines,
                    reason_text=f"《{base_chapter_name}》章节与《{chapter_name}》章节“{invest_type}”的内容一致",
                )
            )
        elif similarity.is_matched:
            outlines = similarity.right_outlines
            self.result.reasons.append(
                MatchFailedItem(
                    page=min(outlines, key=int, default=0),
                    outlines=outlines,
                    reason_text=f"《{base_chapter_name}》章节与《{chapter_name}》章节“{invest_type}”不一致",
                )
            )
            self.result.suggestion = append_suggestion(
                self.result.suggestion,
                f"请修改《{base_chapter_name}》章节与《{chapter_name}》章节“{invest_type}”的内容保持一致",
            )
        else:
            outlines = get_outlines(right_paragraphs)
            self.result.reasons.append(
                MatchFailedItem(
                    page=min(outlines, key=int, default=0),
                    outlines=outlines,
                    reason_text=f"《{chapter_name}》章节未找到与《{base_chapter_name}》章节“{invest_type}”相似的内容",
                )
            )
            self.result.suggestion = append_suggestion(
                self.result.suggestion,
                f"请在《{chapter_name}》章节中添加《{base_chapter_name}》章节中“{invest_type}”的内容",
            )


class FundNameSchemaChecker(AssetSchemaChecker):
    NAME = "全文基金名称保持一致"
    RELATED_NAME = "基础规则"
    LABEL = "schema_1000"
    SCHEMA_FIELDS = ["计划名称"]
    SUGGESTIONS_ON_REVISION = ["请添加计划名称", "全文计划名称需保持一致"]
    REASON = ["计划名称不能为空", "计划名称不是"]
    P_COVER = PatternCollection([r".*计划"])
    P_MAIN_AFTERWARD_START = PatternCollection([r"(无正文|以下无正文)"])
    P_SIGNATURE_START = PatternCollection([r"签[署字](盖章)?[页]"])
    P_MAIN_AFTERWARD = PatternCollection([r"(参与|认购).+计划.+资金", r"为.+计划.+签[署字](盖章)?[页]"])
    DEFINITION = {
        "释义": PatternCollection([r"签署的.*计划", r"(计划说明书|计划)[:：]指.*计划[,.。 ]$"]),
        "资产管理计划的基本情况": PatternCollection([r".*计划的名称"]),
    }

    def check(self):
        fund_name_mode = self.manager.get(self.SCHEMA_FIELDS[0])
        if not fund_name_mode.value:
            self.result.is_compliance = False
            self.result.reasons = [MatchFailedItem(reason_text=self.REASON[0])]
            self.result.suggestion = self.SUGGESTIONS_ON_REVISION[0]
            return self.result
        fund_name_mode_value = replace_parenthesis(fund_name_mode.value)
        # 检查封面
        self.check_cover(fund_name_mode_value)
        # 根据不同的章节 匹配
        for definition in self.DEFINITION:
            self.check_paragraphs_by_definition(definition, fund_name_mode.value)
        self.check_main_afterward(fund_name_mode_value)
        return self.result

    def check_cover(self, keyword: str):
        cover_text, elements = self.join_page_text(0)
        if (match := self.P_COVER.nexts(cover_text)) and keyword not in match.group():
            if elements:
                self.result.reasons.append(
                    MatchFailedItem(
                        reason_text=f"{self.REASON[1]}“{keyword}”",
                        page=elements[0]["page"],
                        matched=False,
                        outlines=get_outlines(elements),
                    )
                )
                self.result.suggestion = self.SUGGESTIONS_ON_REVISION[1]
                self.result.is_compliance = False

    # 检查指定章节
    def check_paragraphs_by_definition(self, definition, model_value):
        chapters, paragraphs = self.reader.find_paragraphs_by_chapters(
            [re.compile(definition)], is_continued_chapter=False
        )
        if not chapters:
            return

        def is_match_in_next_paragraph(curr_index, target_value):
            next_paragraph = replace_parenthesis(paragraphs[curr_index + 1]["text"])
            return self.DEFINITION[definition].nexts(paragraph_text) and target_value not in next_paragraph

        for index, paragraph in enumerate(paragraphs):
            if index == len(paragraphs) - 1:
                return
            paragraph_text = replace_parenthesis(paragraph["text"])
            if definition == "释义":
                if self.DEFINITION[definition].nexts(paragraph_text) and model_value not in paragraph_text:
                    self._handle_failed_match(paragraph, model_value)
            elif definition == "资产管理计划的基本情况":
                if is_match_in_next_paragraph(index, model_value):
                    self._handle_failed_match(paragraphs[index + 1], model_value)
                    break
            else:
                if is_match_in_next_paragraph(index, model_value):
                    self._handle_failed_match(paragraph, model_value)

    # 检查正文后 和签署页面
    def check_main_afterward(self, model_value):
        paragraphs = self.reader.paragraphs

        signature_start, main_afterward_start = self._find_signature_and_main_afterward(paragraphs)
        if signature_start != 0:
            signature_paragraphs = paragraphs[signature_start:]
            for s_element in signature_paragraphs:
                self._match(s_element, model_value)

        if main_afterward_start != 0:
            main_afterward_paragraphs = paragraphs[main_afterward_start : signature_start if signature_start else None]
            for m_element in main_afterward_paragraphs:
                self._match(m_element, model_value)

    def _find_signature_and_main_afterward(self, paragraphs):
        signature_start, main_afterward_start = 0, 0

        index = len(paragraphs) - 1
        while index >= 0:
            paragraph = paragraphs[index]
            paragraph_text = paragraph["text"].strip()

            if self.P_SIGNATURE_START.nexts(paragraph_text):
                signature_start = index
            elif self.P_MAIN_AFTERWARD_START.nexts(paragraph_text):
                main_afterward_start = index
                break

            index -= 1

        return signature_start, main_afterward_start

    def _match(self, element, model_value):
        if (match := self.P_MAIN_AFTERWARD.nexts(element["text"])) and model_value not in match.group():
            self._handle_failed_match(element, model_value)
            return True

    def _handle_failed_match(self, paragraph, model_value):
        self.result.is_compliance = False
        self.result.reasons.append(
            MatchFailedItem(
                reason_text=f"{self.REASON[1]}“{model_value}”",
                page=paragraph["page"],
                matched=False,
                outlines=get_outlines([paragraph]),
            )
        )
        self.result.suggestion = self.SUGGESTIONS_ON_REVISION[1]


class TrusteeNameSchemaChecker(FundNameSchemaChecker):
    NAME = "全文托管人名称保持一致"
    RELATED_NAME = "基础规则"
    LABEL = "schema_1002"
    SCHEMA_FIELDS = ["计划托管人-名称"]
    SUGGESTIONS_ON_REVISION = ["请添加计划托管人名称", "全文计划托管人名称需保持一致"]
    REASON = ["计划托管人名称不能为空", "计划托管人名称不是"]
    P_COVER = PatternCollection([r"托管人([（(](盖章|签章)[)）] )*[:：].*"])
    P_MAIN_AFTERWARD = P_COVER
    DEFINITION = {
        "释义": PatternCollection([r"托管人[:：].*有限公司"]),
        "资产管理计划的费用与税收": PatternCollection([r"(收取|接收)托管费的?.*账户", r"托管费(收取|接收).*账户"]),
        "当事人及权利义务": PatternCollection([r"托管人的?(基本情况|概况)"]),
    }


class CustodianNameChecker(FundNameSchemaChecker):
    NAME = "全文管理人名称保持一致"
    RELATED_NAME = "基础规则"
    LABEL = "schema_1001"
    SCHEMA_FIELDS = ["计划管理人-名称"]
    SUGGESTIONS_ON_REVISION = ["请添加计划管理人名称", "全文计划管理人名称需保持一致"]
    REASON = ["计划管理人名称不能为空", "计划管理人名称不是"]
    P_COVER = PatternCollection([r"管理人([（(](盖章|签章)[)）] )*[:：].*"])
    P_MAIN_AFTERWARD = P_COVER
    DEFINITION = {
        "释义": PatternCollection([r"管理人[:：].*有限责任公司"]),
        "资产管理计划的费用与税收": PatternCollection([r"(收取|接收)管理费的?.*账户", r"管理费(收取|接收).*账户"]),
        "当事人及权利义务": PatternCollection([r"管理人的?(基本情况|概况)"]),
    }


class InvestmentScopeSchemaChecker(InvestmentProportionSchemaChecker):
    NAME = "全文投资范围内容保持一致"
    RELATED_NAME = "基础规则"
    LABEL = "schema_1003"
    SCHEMA_FIELDS = ["计划投资范围"]

    CHAPTER_ASSET_BASIC_INFO = "资产管理计划的基本情况"
    CHAPTER_ASSET_INVEST = "资产管理计划的投资"
    CHAPTER_ULTRA_VIRES = "越权交易的界定"

    P_CHAPTERS = [
        # 资产管理计划的投资
        CatalogsPattern.ASSET_MANAGEMENT_PLAN_INVEST,
        # 越权交易
        CatalogsPattern.ASSET_DEFINITION_ULTRA_VIRES_TRANSACTION,
    ]

    CONTENT_TITLE = "投资范围"

    def check(self):
        investment_scope_mode = self.manager.get(self.SCHEMA_FIELDS[0])

        if not investment_scope_mode.value:
            suggestion = "请添加计划投资范围"
            self.result.is_compliance = False
            self.result.reasons = [MatchFailedItem(reason_text="计划投资范围不能为空")]
            self.result.suggestion = suggestion
            return self.result
        _, base_paragraphs = get_paragraphs_by_schema_fields(
            self.reader, self.manager, self.SCHEMA_FIELDS, without_chapter=True
        )

        for p_chapter in self.P_CHAPTERS:
            chapters, paragraphs = self.reader.find_paragraphs_by_chapters([p_chapter.pattern])
            if not paragraphs:
                self.add_miss_reason(p_chapter.name, self.CONTENT_TITLE)
                return
            chapter_index = [chapter["element"] for chapter in chapters]
            paragraphs = [para for para in paragraphs if para["index"] not in chapter_index]

            self.compare_paragraphs(
                base_paragraphs, paragraphs, p_chapter.name, self.CONTENT_TITLE, self.CHAPTER_ASSET_BASIC_INFO
            )
        self.result.is_compliance = all(isinstance(reason, MatchSuccessItem) for reason in self.result.reasons)
        return self.result


class FundInvestmentScopeChecker(AssetSchemaChecker):
    LABEL = "schema_1023"
    RELATED_NAME = "资产管理计划的基本情况"
    NAME = "投资非标准化债权/股权类资产应封闭运作"
    FROM = "证券期货经营机构私募资产管理计划运作管理规定（证监会令第203号修订 2023年1月12日）"
    ORIGIN = [
        "第二十六条 资产管理计划直接或者间接投资于非标准化债权类资产的，非标准化债权类资产的终止日不得晚于封闭式资产管理计划的到期日或者开放式资产管理计划的最近一次开放日。",
        "资产管理计划直接或者间接投资于非标准化股权类资产的，应当为封闭式资产管理计划，并明确非标准化股权类资产的退出安排。非标准化股权类资产的退出日不得晚于封闭式资产管理计划的到期日。",
        "非标准化股权类资产无法按照约定退出的，资产管理计划可以延期清算，也可以按照投资者持有份额占总份额的比例或者资产管理合同的约定，将其持有的非标准化股权类资产分配给投资者，但不得违反《证券法》关于公开发行的规定。",
    ]
    SCHEMA_FIELDS = ["计划投资范围", "运作方式"]

    P_VALID_FUND_TYPES = [AssetTemplateConditional.NAME_SINGLE_POOLED]
    P_CLOSE_FUND_TYPES = [AssetTemplateConditional.OPERATE_CLOSE]
    # 有效的投资范围
    VALID_INVESTMENT_SCOPES = [
        "未上市企业股权",
        "股权",
        "收益权",
        "信贷",
        "理财",
        "债权融资计划",
        "债权投资计划",
        "资产支持计划",
        "收益凭证",
    ]

    def check(self):
        if not self.manager.verify_condition(self.P_VALID_FUND_TYPES):
            self.result.reasons.append(IgnoreConditionItem(reason_text="当前基金类型不是单一或集合类型"))
            return self.result
        answers = self.check_schema_fields(self.result)
        if self.result.suggestion:
            return self.result
        scope_answer = answers.get(self.SCHEMA_FIELDS[0]).value or ""
        if (
            scopes := [f"“{_val}”" for _val in self.VALID_INVESTMENT_SCOPES if _val in scope_answer]
        ) and not self.manager.verify_condition(self.P_CLOSE_FUND_TYPES):
            self.result.is_compliance = False
            self.result.reasons.append(
                MatchFailedItem(reason_text=f"当前基金类型投资范围包含{'、'.join(scopes)}时，运作方式应为封闭式")
            )
            self.result.suggestion = "建议检查当前投资范围或修改运作方式"
        else:
            self.result.is_compliance = True
        return self.result


class FundDurationChecker(AssetSchemaChecker):
    LABEL = "schema_1024"
    RELATED_NAME = "资产管理计划的基本情况"
    NAME = "资管计划的存续期限制"
    FROM = "证券期货经营机构私募资产管理计划运作管理规定（证监会令第203号修订 2023年1月12日）"
    ORIGIN = [
        "第二十三条 证券期货经营机构应当加强资产管理计划的久期管理，不得设立不设存续期限的资产管理计划。",
        "封闭式资产管理计划的期限不得低于90天。",
    ]
    SCHEMA_FIELDS = ["存续期"]

    P_VALID_FUND_TYPES = [AssetTemplateConditional.NAME_SINGLE_POOLED]

    P_INVALID_DURATION = PatternCollection(r"无固定期限|永续|长期存续|不定期")

    P_CLOSE_FUND_TYPES = [AssetTemplateConditional.OPERATE_CLOSE]
    P_VALID_CLOSE_DURATION = PatternCollection(
        rf"季度|(?P<date>[{R_CN_NUMBER}]+)[天日]|(?P<month>[{R_CN_NUMBER}]+)个月|(?:半|[{R_CN_NUMBER}]+)年"
    )

    def check(self):
        if not self.manager.verify_condition(self.P_VALID_FUND_TYPES):
            self.result.reasons.append(IgnoreConditionItem(reason_text="当前基金类型不是单一或集合类型"))
            return self.result
        answers = self.check_schema_fields(self.result)
        if self.result.suggestion:
            return self.result
        duration_answer = answers[self.SCHEMA_FIELDS[0]].value
        if match := self.P_INVALID_DURATION.nexts(duration_answer):
            self.result.reasons.append(MatchFailedItem(reason_text=f"存续期限不得为“{match.group()}”"))
            self.result.suggestion = "请检查当前合同的“存续期限”"
            self.result.is_compliance = False
        elif self.manager.verify_condition(self.P_CLOSE_FUND_TYPES):
            if match := self.P_VALID_CLOSE_DURATION.nexts(duration_answer):
                if (match.group("date") and NumberUtil.cn_number_2_digit(match.group("date")) < 90) or (
                    match.group("month") and NumberUtil.cn_number_2_digit(match.group("month")) < 3
                ):
                    self.result.reasons.append(MatchFailedItem(reason_text="“存续期限”不得低于三个月/90天"))
                    self.result.suggestion = "请检查当前合同的“存续期限”"
                    self.result.is_compliance = False
            else:
                self.result.is_compliance = False
                self.result.reasons.append(MatchFailedItem(reason_text="“存续期限”不得为空"))
                self.result.suggestion = "请添加“存续期限”"
        return self.result


class OpenDayChecker(AssetSchemaChecker):
    LABEL = "schema_1035"
    RELATED_NAME = "资产管理计划的参与、退出与转让"
    NAME = "集合计划的开放日及其开放频率"
    FROM = [
        "证券期货经营机构私募资产管理业务管理办法（证监会令第203号修订2023年1月12日）",
        "证券期货经营机构私募资产管理计划运作管理规定（证监会令第203号修订2023年1月12日）",
    ]
    ORIGIN = [
        "第二十二条 根据资产管理计划的类别、投向资产的流动性及期限特点、投资者需求等因素，证券期货经营机构可以设立存续期间办理参与、退出的开放式资产管理计划，或者存续期间不办理参与和退出的封闭式资产管理计划。",
        "开放式资产管理计划应当明确投资者参与、退出的时间、次数、程序及限制事项。开放式集合资产管理计划每三个月至多开放一次计划份额的参与、退出，中国证监会另有规定的除外。",
        "第二十四条 全部资产投资于标准化资产的集合资产管理计划和中国证监会认可的其他资产管理计划，可以按照合同约定每季度多次开放，其主动投资于流动性受限资产的市值在开放退出期内合计不得超过该资产管理计划资产净值的20%。",
        "前款规定的资产管理计划每个交易日开放的，其投资范围、投资比例、投资限制、参与和退出管理应当比照适用公募基金投资运作有关规则。",
    ]
    SCHEMA_FIELDS = ["开放日", "投资限制-资产管理计划的基本情况", "投资限制-资产管理计划的投资", "计划投资范围"]
    TEMPLATES = [
        "本计划主动投资于流动性受限资产的市值在开放退出期内合计不得超过本计划资产净值的20%",
    ]
    R_QUARTER = rf"(?:【?(?P<month>[{R_CN_NUMBER}]+)】?个月|季度)"
    R_DAY = rf"【?(?P<day>[{R_CN_NUMBER}]+)】?个自然日"
    R_ONE = r"[1一]"
    R_LIMIT_PREFIX = r"(?:[至最][多少])?"
    P_QUARTER_OPEN_ONCE = PatternCollection(
        # 开放日关键词的靠前
        [
            # 开放日
            rf"开放日为[^{R_PUNCTUATION}]*?{R_DAY}",
            rf"{R_DAY}[^{R_PUNCTUATION}]*?为开放日",
            rf"每{R_QUARTER}最后{R_ONE}个工作日开放",
            rf"开放日为每{R_QUARTER}第.个?(自然)?月的[{R_CN_NUMBER}]+[号日天]",
            rf"开放日为每{R_QUARTER}第.个?(自然)?月的最后{R_ONE}个工作日",
            # 开放
            rf"每隔?{R_QUARTER}{R_LIMIT_PREFIX}开放{R_ONE}次",
        ]
    )
    P_NO_OPEN_DAY = PatternCollection(r"(?:无|不设[置立]?)开放日")

    def check_open_day(self, content):
        # 每季度最多一次
        if match := self.P_QUARTER_OPEN_ONCE.nexts(content):
            match_dict = match.groupdict()
            if (month := match_dict.get("month")) and int(NumberUtil.cn_number_2_digit(month)) < 3:
                return False
            if (day := match_dict.get("day")) and int(NumberUtil.cn_number_2_digit(day)) < 91:
                return False
            return True
        return False

    def check(self):
        if not self.manager.verify_condition([AssetTemplateConditional.NAME_POOLED]):
            self.result.reasons.append(IgnoreConditionItem(reason_text="当前基金类型不是集合类型"))
            return self.result
        open_day = self.manager.get(self.SCHEMA_FIELDS[0])
        content = clean_txt(open_day.value or "")
        if not content or self.P_NO_OPEN_DAY.nexts(content):
            # 合规：无开放日，且封闭式
            # https://gitpd.paodingai.com/cheftin/docs_scriber/-/issues/2027#note_348573
            if self.manager.verify_condition([AssetTemplateConditional.OPERATE_CLOSE]):
                self.result.is_compliance = True
                return self.result
            self.result.is_compliance = False
            self.result.reasons = [MatchFailedItem(reason_text="开放日不能为空")]
            self.result.suggestion = "请添加开放日"
            return self.result
        # 是否为每季度多次开放
        if not self.check_open_day(content):
            self.result.is_compliance = False
            if self.manager.verify_condition([AssetTemplateConditional.NON_STANDARD_INVESTMENT_YES]):
                scope_investment = self.manager.get(self.SCHEMA_FIELDS[3])
                self.result.reasons = [
                    MatchFailedItem(
                        reason_text="计划投资范围包含非标投资",
                        page=min(scope_investment.outlines, key=int, default=0),
                        outlines=scope_investment.outlines,
                    )
                ]
                self.result.suggestion = "请检查计划投资范围"
                return self.result
            _, paragraphs = get_paragraphs_by_schema_fields(self.reader, self.manager, self.SCHEMA_FIELDS[1:3])
            similarity = ParagraphSimilarity(
                self.TEMPLATES,
                paragraphs,
                similarity_patterns=self.SYNONYM_PATTERNS,
                ignore_extra_para=True,
                convert_types=self.CONVERT_TYPES,
            )

            if similarity.is_full_matched_or_contain or similarity.is_full_matched_without_extra_para:
                outlines = similarity.right_outlines
                self.result.is_compliance = True
                self.result.reasons = [
                    MatchReasonItem(
                        template=Template(content=similarity.left_content, name="范文", content_title="合同范文"),
                        content=similarity.right_content,
                        page=min(outlines, key=int, default=0),
                        content_title="当前合同",
                        outlines=outlines,
                        diff=similarity.simple_results,
                        xpath=get_xpath_by_outlines(self.reader, outlines),
                    )
                ]
                return self.result
            if similarity.is_matched:
                outlines = similarity.right_outlines
                reason = ConflictReasonItem(
                    template=Template(content=similarity.left_content, name="范文", content_title="合同范文"),
                    content=similarity.right_content,
                    page=min(outlines, key=int, default=0),
                    content_title="当前合同",
                    outlines=outlines,
                    diff=similarity.simple_results,
                    xpath=get_xpath_by_outlines(self.reader, outlines),
                )
                self.result.reasons = [reason]
                self.result.suggestion = reason.render_suggestion(self.reader, "投资比例及限制/投资限制")
            else:
                self.result.reasons = [
                    MatchFailedItem(
                        reason_text="投资限制需包含“本计划主动投资于流动性受限资产的市值在开放退出期内合计不得超过本计划资产净值的20%”"
                    )
                ]
                self.result.suggestion = "请检查投资比例及限制/投资限制"
        return self.result


class NonTradingChecker(AssetSchemaChecker):
    LABEL = "schema_1037"
    RELATED_NAME = "资产管理计划的参与、退出与转让"
    NAME = "集合计划的非交易过户"
    CONTRACT_CONTENT = [
        "【集合】",
        "第三十五条 订明资产管理计划份额因继承、捐赠、司法强制执行以及其他符合规定的情况，需非交易过户的受理条件与流程。",
    ]
    SCHEMA_FIELDS = ["非交易过户认定及处理方式"]

    def check(self):
        if not self.manager.verify_condition([AssetTemplateConditional.NAME_POOLED]):
            self.result.reasons.append(IgnoreConditionItem(reason_text="当前基金类型不是集合类型"))
            return self.result
        non_trading = self.manager.get(self.SCHEMA_FIELDS[0])
        if not non_trading.value:
            self.result.is_compliance = False
            self.result.reasons = [MatchFailedItem(reason_text="没有约定非交易过户")]
            self.result.suggestion = "请约定非交易过户"
        return self.result


class MeetingMattersChecker(AssetSchemaChecker):
    LABEL = "schema_1041"
    RELATED_NAME = "份额持有人大会及日常机构"
    NAME = "集合计划份额持有人大会-应在合同中订明的事项"
    CONTRACT_CONTENT = [
        "【集合】",
        "第四十二条根据《基金法》和其他有关规定订明资产管理计划份额持有人大会及/或日常机构的下列事项：",
        "（一）召集人和召集方式；",
        "（二）召开会议的通知时间、通知内容、通知方式；",
        "（三）出席会议的方式（包括但不限于现场会议、视频会议、电话会议等）；",
        "（四）议事内容与程序；",
        "（五）决议形成和生效的条件、表决方式、程序。",
    ]

    P_ITEMS = [
        CheckResultRelation("召集人和召集方式", PatternCollection(r"召集人|召集方式")),
        CheckResultRelation(
            "召开会议的通知时间、通知内容、通知方式",
            PatternCollection(rf"(?:(?:通知时间|通知内容|通知方式)[{R_CONJUNCTION}]?){{3}}"),
        ),
        CheckResultRelation("出席会议的方式", PatternCollection(r"出席会议的?方式")),
        CheckResultRelation("议事内容与程序", PatternCollection(rf"议事内容[{R_CONJUNCTION}]程序")),
        CheckResultRelation(
            "决议形成和生效的条件、表决方式、程序",
            PatternCollection(rf"决议形成[{R_CONJUNCTION}]生效的?(?:(?:条件|表决方式|程序)[{R_CONJUNCTION}]?){{3}}"),
        ),
    ]

    def check(self):
        reasons_text_list = []
        for condition in (AssetTemplateConditional.NAME_POOLED, AssetTemplateConditional.HOLDER_MEETING_YES):
            if not self.manager.verify_condition([condition]):
                if condition == AssetTemplateConditional.NAME_POOLED:
                    reasons_text_list.append("不是集合类型")
                else:
                    reasons_text_list.append("未披露持有人大会")
        if reasons_text_list:
            self.result.reasons.append(IgnoreConditionItem(reason_text=f"当前基金{'、'.join(reasons_text_list)}"))
            return self.result
        self.check_syllabuses(CatalogsPattern.GENERAL_ASSEMBLY_DAILY_INSTITUTIONS)
        return self.result


class ResponsibilityChecker(AssetSchemaChecker):
    LABEL = "schema_1045"
    RELATED_NAME = "资产管理计划份额的登记"
    NAME = "集合计划应订明份额登记机构的职责"
    FROM = "证券期货经营机构私募资产管理业务管理办法（证监会令第203号修订 2023年1月12日）"
    ORIGIN = "第十六条 证券期货经营机构可以自行办理资产管理计划份额的登记、估值、核算，也可以委托中国证监会认可的其他机构代为办理。"
    CONTRACT_CONTENT = [
        "【集合】",
        "第四十五条 订明管理人办理份额登记业务的各项事宜。说明管理人委托其他机构代为办理资产管理计划份额登记业务的，应当与有关机构签订委托代理协议，并列明代为办理资产管理计划份额登记机构的权限和职责。",
    ]

    P_SENTENCE = PatternCollection(
        [
            r"(份额|注册)登记机构的?(职责|义务)",
        ]
    )

    def check(self):
        if not self.manager.verify_condition([AssetTemplateConditional.NAME_POOLED]):
            self.result.reasons.append(IgnoreConditionItem(reason_text="当前基金类型不是集合类型"))
            return self.result
        _, paragraphs = self.reader.find_paragraphs_by_chapters([re.compile(r"资产管理计划(注册|份额)的?登记")])
        for paragraph in paragraphs:
            if self.P_SENTENCE.nexts(clean_txt(paragraph["text"])):
                return self.result
        outlines = get_outlines(paragraphs)
        self.result.is_compliance = False
        self.result.suggestion = (
            "请添加“份额登记机构的职责、份额登记机构的义务、注册登记机构的义务、注册登记机构的职责”"
        )
        self.result.reasons.append(
            MatchFailedItem(
                page=min(outlines, key=int, default=0),
                outlines=outlines,
                reason_text="未找到“份额登记机构的职责、份额登记机构的义务、注册登记机构的义务、注册登记机构的职责”",
            )
        )
        return self.result


class PrescribedItemChecker(AssetSchemaChecker):
    LABEL = "schema_1047"
    RELATED_NAME = "资产管理计划的投资"
    NAME = "投资-应在合同中订明的事项"
    CONTRACT_CONTENT = [
        "【单一&集合】",
        "第四十七条 说明资产管理计划财产投资的有关事项，包括但不限于：",
        "（一）投资目标；",
        "（二）投资范围及比例，说明资产管理计划符合《运作规定》组合投资的要求。存在以下情况的应当在资产管理合同中特别说明：",
        "1.投资非标准化资产的，应当穿透披露具体投资标的，暂未确定具体投资标的的，应当约定披露方式及时限；",
        "2.参与证券回购、融资融券、转融通、场外证券业务的应当进行特别揭示。",
        "（三）说明投资比例超限的处理方式及流程；",
        "【FOF】（四）说明FOF产品（如是）所投资资产管理产品的选择标准；",
        "（五）风险收益特征；",
        "（六）业绩比较基准（如有）及确定依据；业绩比较基准原则上不得为固定数值；",
        "（七）投资策略，说明管理人运作资产管理计划财产的决策依据、决策程序、投资管理的方法和标准等；",
        "（八）投资限制，订明按照《管理办法》、自律规则及其他有关规定和合同约定禁止或限制的投资事项；",
        "（九）订明资产管理计划的建仓期；",
        "【集合】（十）说明固定收益类、权益类、商品及金融衍生品类资产管理计划存续期间，为规避特定风险，经全体投资者同意后，投资于对应类别资产的比例可以低于计划总资产80%，但不得持续6个月低于计划总资产80%。管理人应详细列明上述相关特定风险；",
        "【单一】（十）说明固定收益类、权益类、商品及金融衍生品类资产管理计划存续期间，为规避特定风险，经投资者同意后，投资于对应类别资产的比例可以低于计划总资产80%，但不得持续6个月低于计划总资产80%。管理人应详细列明上述相关特定风险；",
        "【股权】（十一）订明投资非标准化股权类资产的退出安排（如有）；",
        "【集合】（十二）订明投资的资产组合的流动性与参与、退出安排相匹配。",
    ]

    P_ITEMS_GENERAL_CHAPTER = [
        CheckResultRelation("投资目标", PatternCollection(r"投资目标")),
        CheckResultRelation("投资范围", PatternCollection(r"投资范围")),
        CheckResultRelation("投资比例", PatternCollection(r"投资比例")),
        CheckResultRelation("风险收益特征", PatternCollection(r"风险收益特征")),
        CheckResultRelation("业绩比较基准", PatternCollection(r"业绩比较基准")),
        CheckResultRelation("投资策略", PatternCollection(r"投资策略")),
        CheckResultRelation("投资限制", PatternCollection(r"投资限制")),
        CheckResultRelation("投资禁止/禁止投资行为", PatternCollection(r"投资禁止|禁止投资行为")),
        CheckResultRelation("建仓期", PatternCollection(r"建仓期")),
        CheckResultRelation(
            "fof产品所投资资产管理产品的选择标准",
            PatternCollection(r"fof产品所投资资产管理产品的?选择标准", re.I),
            condition=AssetTemplateConditional.FOF,
        ),
        CheckResultRelation(
            "投资非标准化股权类资产的退出安排",
            PatternCollection(r"投资非标准化股权类资产的退出安排"),
            condition=AssetTemplateConditional.STOCK_RIGHT_YES,
        ),
    ]

    P_ITEMS_SPECIAL_CHAPTER = [
        CheckResultRelation("投资比例超限的处理方式", PatternCollection(r"投资比例超限的?处理")),
    ]

    def check(self):
        if not self.manager.verify_condition([AssetTemplateConditional.NAME_SINGLE_POOLED]):
            self.result.reasons.append(IgnoreConditionItem(reason_text="当前基金类型不是单一或集合类型"))
            return self.result

        self.P_ITEMS = self.P_ITEMS_SPECIAL_CHAPTER
        if not self.get_valid_paras(CatalogsPattern.ASSET_MANAGEMENT_PLAN_INVEST)[0]:
            if self.check_syllabuses(CatalogsPattern.ASSET_MANAGEMENT_PLAN_BASIC_INFO, check_paragraphs=False):
                self.P_ITEMS = self.P_ITEMS_GENERAL_CHAPTER
            else:
                self._clean_reason()
                if self.check_syllabuses(
                    CatalogsPattern.ASSET_DEFINITION_ULTRA_VIRES_TRANSACTION, check_paragraphs=False
                ):
                    self.P_ITEMS = self.P_ITEMS_GENERAL_CHAPTER
                else:
                    self._clean_reason()
                    self.P_ITEMS.extend(self.P_ITEMS_GENERAL_CHAPTER)
        else:
            self.P_ITEMS.extend(self.P_ITEMS_GENERAL_CHAPTER)

        # 计划的投资
        self.check_syllabuses(CatalogsPattern.ASSET_MANAGEMENT_PLAN_INVEST)

        return self.result

    def _clean_reason(self):
        self.result.reasons = []
        self.result.suggestion = ""
        self.result.is_compliance = False


class DoubleNestingChecker(AssetSchemaChecker):
    RULE_TYPE = RuleType.TEMPLATE.value

    LABEL = "schema_1055"
    RELATED_NAME = "资产管理计划的投资"
    NAME = "投资-双层嵌套"
    FROM = [
        "证券期货经营机构私募资产管理业务管理办法（证监会令第203号修订 2023年1月12日）",
        "证券期货经营机构私募资产管理计划备案管理办法（试行）中基协发[2019]4号 2019年6月3日",
    ]
    ORIGIN = [
        "第四十五条 资产管理计划接受其他资产管理产品参与的，证券期货经营机构应当切实履行主动管理职责，不得进行转委托，不得再投资除公募基金以外的其他资产管理产品。",
        "第四十六条 资产管理计划投资于其他资产管理产品的，应当明确约定所投资的资产管理产品不再投资除公募基金以外的其他资产管理产品。",
        "中国证监会对创业投资基金、政府出资产业投资基金等另有规定的，不受本条第一款及本办法第四十五条关于再投资其他资产管理产品的限制。",
        "证券期货经营机构不得将其管理的资产管理计划资产投资于该机构管理的其他资产管理计划，依法设立的基金中基金资产管理计划以及中国证监会另有规定的除外。",
        "资产管理计划不得通过投资其他资产管理产品变相扩大投资范围或者规避监管要求。",
        "第二十五条针对嵌套层数，重点核查投资者信息和资产管理合同投资范围是否同时存在除公开募集证券投资基金以外的其他资产管理产品，合规负责人审查意见书是否对产品嵌套符合规定作出说明。",
        "对于无正当事由将资管产品或其收受益权作为底层资产的资产支持证券，或者以资产支持证券形式规避监管要求的情形，应当视为一层嵌套。",
        "对于政府出资产业投资基金，存在向社会募集资金的，应当视为一层嵌套。",
    ]

    TEMPLATES = [
        "【1】本计划接受其他资产管理产品参与的，不得进行转委托，不得再投资除公募基金以外的其他资产管理产品。",
        "【2】本计划投资于其他资产管理产品的，所投资的资产管理产品不得投资除公募基金以外的其他资产管理产品。",
        "【3】管理人不得将本计划资产投资于其管理的其他资产管理计划，依法设立的基金中基金资产管理计划以及中国证监会另有规定的除外。",
        "【4】不得通过投资其他资产管理产品变相扩大投资范围或者规避监管要求。",
    ]

    P_INVESTMENT_SCOPE = PatternCollection([r"资产管理计划|资产管理产品|私募证券投资基金|信托计划"])

    def check(self):
        if not self.manager.verify_condition([AssetTemplateConditional.NAME_SINGLE_POOLED]):
            self.result.reasons.append(IgnoreConditionItem(reason_text="当前基金类型不是单一或集合类型"))
            return self.result

        investment_scope_mode = self.manager.get("计划投资范围")

        if not investment_scope_mode.value:
            suggestion = "请添加计划投资范围"
            self.result.is_compliance = False
            self.result.reasons = [MatchFailedItem(reason_text="计划投资范围不能为空")]
            self.result.suggestion = suggestion
            return self.result

        if not self.P_INVESTMENT_SCOPE.nexts(investment_scope_mode.value):
            self.result.is_compliance = False
            self.result.reasons = [
                IgnoreConditionItem(
                    reason_text="计划投资范围不包含“资产管理计划、资产管理产品、私募证券投资基金或信托计划”"
                )
            ]
            return self.result

        _, paragraphs = self.reader.find_paragraphs_by_chapters([CatalogsPattern.ASSET_MANAGEMENT_PLAN_INVEST.pattern])

        self.paragraph_similarity(
            result=self.result,
            paragraphs_left_list=[self.TEMPLATES],
            paragraphs_right=paragraphs,
            outlines=get_outlines(paragraphs),
            origin_content="\n".join(self.TEMPLATES),
            name=TemplateName.EDITING_NAME,
            content_title=TemplateName.EDITING_TITLE,
        )
        return self.result


class MattersToBeSpecifiedChecker(AssetSchemaChecker):
    LABEL = "schema_1059"
    RELATED_NAME = "投资顾问（如有）"
    NAME = "投顾-合同应订明的事项"
    FROM = "证券期货经营机构私募资产管理业务管理办法（证监会令第203号修订 2023年1月12日）"
    ORIGIN = [
        "第十七条 证券期货经营机构应当立足其专业服务能力开展私募资产管理业务；为更好满足资产管理计划投资配置需求，可以聘请符合中国证监会规定条件并接受国务院金融监督管理机构监管的机构为其提供投资顾问服务。证券期货经营机构依法应当承担的责任不因聘请投资顾问而免除。",
        "证券期货经营机构应当向投资者详细披露所聘请的投资顾问的资质、收费等情况，以及更换、解聘投资顾问的条件和程序，充分揭示聘请投资顾问可能产生的特定风险。",
        "证券期货经营机构不得聘请个人或者不符合条件的机构提供投资顾问服务。",
    ]
    CONTRACT_CONTENT = [
        "【单一&集合】",
        "第四十八条 资产管理计划聘请投资顾问的，应当列明投资顾问有关内容，包括但不限于：",
        "（一）资产管理计划所聘请投资顾问的资质和基本情况；",
        "（二）投资顾问的权利和义务；",
        "（三）资产管理计划更换、解聘投资顾问的条件和程序。",
    ]

    TEMPLATES = [
        {
            "name": TemplateName.EDITING_NAME,
            "content_title": TemplateName.EDITING_TITLE,
            "chapter": ChapterPattern.CHAPTER_ASSET_INVESTMENT_COUNSELOR,
            # https://gitpd.paodingai.com/cheftin/docs_scriber/-/issues/2414
            "items": [
                [
                    "本计划不聘请投资顾问。",
                    "本资产管理计划不聘请投资顾问。",
                ]
            ],
        },
    ]

    P_ITEMS = [
        CheckResultRelation(
            "资产管理计划所聘请投资顾问的资质和基本情况；",
            PatternCollection(r"投资顾问的(资质和)?(基本|基础)?(情况|信息)"),
        ),
        CheckResultRelation("投资顾问的权利和义务；", PatternCollection(r"投资顾问的权利和义务")),
        CheckResultRelation(
            "资产管理计划更换、解聘投资顾问的条件和程序；",
            PatternCollection(r"(资产管理计划)?更换、解聘投资顾问的条件和程序"),
        ),
    ]

    def check(self):
        if not self.manager.verify_condition([AssetTemplateConditional.NAME_SINGLE_POOLED]):
            self.result.reasons.append(IgnoreConditionItem(reason_text="当前基金类型不是单一或集合类型"))
            return self.result

        if self.manager.verify_condition([AssetTemplateConditional.INVESTMENT_ADVISER]):
            # 投顾
            self.check_syllabuses(CatalogsPattern.ASSET_INVESTMENT_COUNSELOR)
            return self.result

        else:
            # 无投顾
            # https://gitpd.paodingai.com/cheftin/docs_scriber/-/issues/2413
            if not self.reader.find_chapter_by_patterns([CatalogsPattern.ASSET_INVESTMENT_COUNSELOR.pattern]):
                self.result.is_compliance = True
                return self.result

            template = {
                "label": self.LABEL,
                "schema_fields": self.SCHEMA_FIELDS,
                "related_name": self.RELATED_NAME,
                "name": self.NAME,
                "from": self.FROM,
                "origin": self.ORIGIN,
                "templates": self.TEMPLATES,
            }
            self.condition_checker.TEMPLATES = [template]
            result = self.condition_checker.check()
            if not result:
                return
            result = result[0]
            result.rule_type = self.RULE_TYPE
            miss_content = not any(reason.matched for reason in result.reasons)
            matched, reasons = self.condition_checker.after_match_template(template, result.reasons, miss_content)
            result.reasons = reasons
            result.is_compliance = matched
            return result


class ConnectedTransactionPrescribedItemChecker(AssetSchemaChecker):
    LABEL = "schema_1063"
    RELATED_NAME = "利益冲突及关联交易"
    NAME = "关联交易-合同应订明的事项"
    CONTRACT_CONTENT = [
        "【单一&集合】",
        "第五十三条 列明资产管理计划存在的或可能存在利益冲突的情形。说明FOF产品（如是）投资管理人及管理人关联方所设立的资产管理产品的情况。",
        "第五十四条 订明资产管理计划存在利益冲突的处理方式、披露方式、披露内容以及披露频率。",
    ]

    P_ITEMS = [
        CheckResultRelation("利益冲突/关联交易的情形", PatternCollection(r"(利益冲突|关联交易)的?情形")),
        CheckResultRelation("利益冲突的处理方式", PatternCollection(r"利益冲突的?(处理|应对)(方式)?")),
        CheckResultRelation("利益冲突的信息披露", PatternCollection(r"利益冲突的信息披露")),
        CheckResultRelation("关联方包括的情形/关联方范围", PatternCollection(r"关联方(包括的情形|范围)")),
    ]

    def check(self):
        if not self.manager.verify_condition([AssetTemplateConditional.NAME_SINGLE_POOLED]):
            self.result.reasons.append(IgnoreConditionItem(reason_text="当前基金类型不是单一或集合类型"))
            return self.result

        self.check_syllabuses(CatalogsPattern.ASSET_CONFLICTS_INTEREST_RELATED_PARTY_TRANSACTIONS)
        return self.result


class IdentificationTreatmentChecker(AssetSchemaChecker):
    RULE_TYPE = RuleType.TEMPLATE.value
    LABEL = "schema_1064"
    RELATED_NAME = "利益冲突及关联交易"
    NAME = "关联交易-认定和处理"
    FROM = [
        "关于规范金融机构资产管理业务的指导意见（银发〔2018〕106号 2018年4月27日）",
        "证券期货经营机构私募资产管理业务管理办法（证监会令第203号修订 2023年1月12日）",
        "证券期货经营机构私募资产管理计划运作管理规定（证监会令第203号修订 2023年1月12日）",
    ]
    ORIGIN = [
        "二十四、金融机构不得以资产管理产品的资金与关联方进行不正当交易、利益输送、内幕交易和操纵市场，包括但不限于投资于关联方虚假项目、与关联方共同收购上市公司、向本机构注资等。",
        "金融机构的资产管理产品投资本机构、托管机构及其控股股东、实际控制人或者与其有其他重大利害关系的公司发行或者承销的证券，或者从事其他重大关联交易的，应当建立健全内部审批机制和评估机制，并向投资者充分披露信息。",
        "第六十六条 证券期货经营机构应当建立健全关联交易管理制度，对关联交易认定标准、交易定价方法、交易审批程序进行规范，不得以资产管理计划的资产与关联方进行不正当交易、利益输送、内幕交易和操纵市场。",
        "证券期货经营机构以资产管理计划资产从事关联交易的，应当遵守法律、行政法规、中国证监会的规定和合同约定，事先取得投资者的同意，事后及时告知投资者和托管人，并向中国证监会相关派出机构报告。",
        "第三十条 证券期货经营机构将资产管理计划资产投资于本机构、托管人及前述机构的控股股东、实际控制人或者其他关联方发行的证券或者承销期内承销的证券，应当建立健全内部审批机制和评估机制，并应当遵循投资者利益优先原则，事先取得投资者的同意，事后告知投资者和托管人，并采取切实有效措施，防范利益冲突，保护投资者合法权益。",
        "除前款规定外，证券期货经营机构不得将其管理的资产管理计划资产，直接或者通过投资其他资产管理计划等间接形式，为本机构、托管人及前述机构的控股股东、实际控制人或者其他关联方提供或者变相提供融资。全部投资者均为符合中国证监会规定的专业投资者且单个投资者投资金额不低于1000万元，并且事先取得投资者同意的资产管理计划除外。",
    ]

    CONTRACT_CONTENT = [
        "【单一&集合】",
        "第五十五条 订明运用受托管理资产从事关联交易的，事后及时、全面、客观的向投资者和托管人进行披露。运用受托管理资产从事重大关联交易的，应事先取得投资者同意，并有充分证据证明未损害投资者利益。",
    ]

    SCHEMA_FIELDS = ["关联交易及利益冲突情形", "关联交易及利益冲突的应对及处理"]
    ITEMS = [
        "管理人、托管人及前述机构的控股股东、实际控制人或者其他关联方发行的证券或者承销期内承销的证券",
        "管理人以本计划资产从事重大关联交易的，应当遵守法律、行政法规、中国证监会的规定和合同约定，按照管理人内部审批机制和评估机制对重大关联交易进行事前审批，并事先以公告形式取得投资者同意，事后及时告知投资者和托管人，并向中国证监会相关派出机构报告。",
    ]

    def check(self):
        if not self.manager.verify_condition([AssetTemplateConditional.NAME_SINGLE_POOLED]):
            self.result.reasons.append(IgnoreConditionItem(reason_text="当前基金类型不是单一或集合类型"))
            return self.result
        suggestions = []
        for idx, field in enumerate(self.SCHEMA_FIELDS):
            _, paras = get_paragraphs_by_schema_fields(self.reader, self.manager, [field])
            if not paras:
                self.result.reasons.append(MatchFailedItem(reason_text=f"要素“{field}”为空"))
                suggestions.append(f"请补充“{field}”")
                continue
            self.paragraph_similarity(
                result=self.result,
                paragraphs_left_list=[[self.ITEMS[idx]]],
                paragraphs_right=paras,
                outlines=get_outlines(paras),
                origin_content=self.ITEMS[idx],
                name=TemplateName.EDITING_NAME,
                content_title=TemplateName.EDITING_TITLE,
            )
            if self.result.suggestion:
                suggestions.append(self.result.suggestion)
        self.result.suggestion = "\n".join(suggestions)
        return self.result


class InvestmentProportionChecker(AssetSchemaChecker):
    RULE_TYPE = RuleType.TEMPLATE.value
    LABEL = "schema_1025"
    RELATED_NAME = "资产管理计划的基本情况"
    NAME = "计划的类别及其投资比例"
    FROM = "证券期货经营机构私募资产管理业务管理办法（证监会令第203号修订 2023年1月12日）"
    ORIGIN = [
        "第三十七条 证券期货经营机构设立集合资产管理计划进行投资，除中国证监会另有规定外，应当采用资产组合的方式。资产组合的具体方式和比例，依照法律、行政法规和中国证监会的规定在资产管理合同中约定。"
        "第二十一条 资产管理计划应当具有明确、合法的投资方向，具备清晰的风险收益特征，并区分最终投向资产类别，按照下列规定确定资产管理计划所属类别：",
        "（一）投资于存款、债券等债权类资产的比例不低于资产管理计划总资产80％的，为固定收益类；",
        "（二）投资于股票、未上市企业股权等股权类资产的比例不低于资产管理计划总资产80％的，为权益类；",
        "（三）投资于期货和衍生品的持仓合约价值的比例不低于资产管理计划总资产80%，且期货和衍生品账户权益超过资产管理计划总资产20%的，为期货和衍生品类；",
        "（四）投资于债权类、股权类、期货和衍生品类资产的比例未达到前三类产品标准的，为混合类。",
    ]

    P_VALID_FUND_TYPES = [AssetTemplateConditional.NAME_SINGLE_POOLED]

    TEMPLATES_ITEMS = [
        {
            "name": TemplateName.EDITING_NAME,
            "content_title": TemplateName.EDITING_TITLE,
            "chapter": ChapterPattern.CHAPTER_ASSET_MANAGEMENT_PLAN_BASIC_INFO,
            "items": [
                {
                    "conditions": [AssetTemplateConditional.FIXED_INCOME_CATEGORY],
                    "items": [
                        "投资于存款、债券等债权类资产的比例不低于资产管理计划总资产80％；",
                    ],
                },
            ],
        },
        {
            "name": TemplateName.EDITING_NAME,
            "content_title": TemplateName.EDITING_TITLE,
            "chapter": ChapterPattern.CHAPTER_ASSET_MANAGEMENT_PLAN_BASIC_INFO,
            "items": [
                {
                    "conditions": [AssetTemplateConditional.EQUITIES],
                    "items": [
                        "投资于股票、未上市企业股权等股权类资产的比例不低于资产管理计划总资产80％；",
                    ],
                },
            ],
        },
        {
            "name": TemplateName.EDITING_NAME,
            "content_title": TemplateName.EDITING_TITLE,
            "chapter": ChapterPattern.CHAPTER_ASSET_MANAGEMENT_PLAN_BASIC_INFO,
            "items": [
                {
                    "conditions": [AssetTemplateConditional.FUTURES_AND_DERIVATIVES],
                    "items": [
                        "投资于期货和衍生品的持仓合约价值的比例不低于资产管理计划总资产80%，且期货和衍生品账户权益超过资产管理计划总资产20%；",
                    ],
                },
            ],
        },
        {
            "name": TemplateName.EDITING_NAME,
            "content_title": TemplateName.EDITING_TITLE,
            "chapter": ChapterPattern.CHAPTER_ASSET_MANAGEMENT_PLAN_BASIC_INFO,
            "items": [
                {
                    "conditions": [AssetTemplateConditional.MIXED_CLASS],
                    "items": [
                        [
                            "投资于存款、债券等债权类资产的比例低于资产管理计划总资产80％；",
                            "投资于存款、债券等债权类资产的比例占资产管理计划总资产0-80%；",
                        ],
                    ],
                },
            ],
        },
        {
            "name": TemplateName.EDITING_NAME,
            "content_title": TemplateName.EDITING_TITLE,
            "chapter": ChapterPattern.CHAPTER_ASSET_MANAGEMENT_PLAN_BASIC_INFO,
            "items": [
                {
                    "conditions": [AssetTemplateConditional.MIXED_CLASS],
                    "items": [
                        [
                            "投资于股票、未上市企业股权等股权类资产的比例低于资产管理计划总资产80％",
                            "投资于股票、未上市企业股权等股权类资产的比例占资产管理计划总资产0-80%；",
                        ],
                    ],
                },
            ],
        },
        {
            "name": TemplateName.EDITING_NAME,
            "content_title": TemplateName.EDITING_TITLE,
            "chapter": ChapterPattern.CHAPTER_ASSET_MANAGEMENT_PLAN_BASIC_INFO,
            "items": [
                {
                    "conditions": [AssetTemplateConditional.MIXED_CLASS],
                    "items": [
                        [
                            "投资于期货和衍生品的持仓合约价值的比例低于资产管理计划总资产80%；且期货和衍生品账户权益不超过资产管理计划总资产20%；",
                            "投资于期货和衍生品的持仓合约价值的比例占资产管理计划总资产0-80%；且期货和衍生品账户权益不超过资产管理计划总资产20%；",
                        ],
                    ],
                },
            ],
        },
    ]

    def check(self):
        if not self.manager.verify_condition(self.P_VALID_FUND_TYPES):
            self.result.reasons.append(IgnoreConditionItem(reason_text="当前基金类型不是单一或集合类型"))
            return self.result
        sentence_checker = BaseSentenceMultipleChecker(
            reader=self.reader,
            manager=self.manager,
            file=self.file,
            schema_id=self.schema_id,
            labels=self.labels,
            fund_manager_info=self.fund_manager_info,
        )
        base_template = {
            "label": self.LABEL,
            "schema_fields": self.SCHEMA_FIELDS,
            "related_name": self.RELATED_NAME,
            "name": self.NAME,
            "from": self.FROM,
            "origin": self.ORIGIN,
            "templates": [],
        }
        reasons = []
        suggestions = []
        for template_item in self.TEMPLATES_ITEMS:
            base_template["templates"] = [template_item]
            sentence_checker.TEMPLATES = [base_template]
            if not (check_res := sentence_checker.check()):
                continue
            check_res = check_res[0]
            # 所有的范文模板均参与检查，忽略不满足条件的模板对象，其余均保留
            # https://gitpd.paodingai.com/cheftin/docs_scriber/-/issues/2022#note_319450
            conditions: list[TemplateRelation]
            if conditions := template_item["items"][0]["conditions"]:
                condition_relation: FundTypeRelation = conditions[0].values[0]
                reason_text = f"未找到“{condition_relation.value.value}”的范文内容"
                for reason in check_res.reasons:
                    # 特殊处理：模板中需要替换的内容如果未找到，不通过原因为“请补充***”,只对该类型进行处理
                    if not isinstance(reason, (MatchReasonItem, ConflictReasonItem)) and reason.reason_text.startswith(
                        "请补充"
                    ):
                        reason.reason_text = reason_text + f"；{reason.reason_text}"
            reasons.extend(check_res.reasons)
            if check_res.suggestion:
                suggestions.append(check_res.suggestion)

        if not reasons:
            return

        if any(not isinstance(reason, IgnoreConditionItem) for reason in reasons):
            reasons = [reason for reason in reasons if not isinstance(reason, IgnoreConditionItem)]
        reasons = self.filter_same_reason(reasons)
        self.result.reasons = reasons
        self.result.suggestion = "\n\n".join(suggestions)
        # https://gitpd.paodingai.com/cheftin/docs_scriber/-/issues/2022#note_323295
        self.result.is_compliance = all(isinstance(reason, MatchReasonItem) for reason in reasons)
        return self.result


class InvestmentManagerDesignationChangeChecker(AssetSchemaChecker):
    RULE_TYPE = RuleType.TEMPLATE.value
    LABEL = "schema_1066"
    SCHEMA_FIELDS = ["投资经理的指定与变更"]
    RELATED_NAME = "投资经理的指定与变更"
    NAME = "投资经理的指定和变更"
    FROM = [
        "证券期货经营机构私募资产管理业务管理办法（证监会令第203号修订2023年1月12日）",
        "证券期货经营机构私募资产管理计划备案管理办法（试行） 中基协发[2019]4号2019年6月3日",
    ]
    ORIGIN = [
        "第十三条 投资经理应当依法取得基金从业资格，具有三年以上投资管理、投资研究、投资咨询等相关业务经验，具备良好的诚信记录和职业操守，且最近三年未被监管机构采取重大行政监管措施、行政处罚。",
        "投资经理应当在证券期货经营机构授权范围内独立、客观地履行职责，重要投资应当有详细的研究报告和风险分析支持。",
        "第八条资产管理人应当为每只资产管理计划配备一名或多名投资经理，投资经理应当取得基金从业资格并在证券投资基金业协会完成注册。",
    ]
    CONTRACT_CONTENT = [
        "【单一&集合】",
        "第五十六条 订明资产管理计划投资经理由管理人负责指定。同时，列明本资产管理计划投资经理的姓名、从业简历、学历及兼职情况等。列明投资经理的投资管理、投资研究、投资咨询等相关业务经验、是否取得基金从业资格，以及最近三年是否被监管机构采取重大行政监管措施、行政处罚。",
        "第五十七条 订明资产管理计划投资经理变更的条件和程序。",
    ]

    P_EXPERIENCE = PatternCollection(rf"(?P<val>[{R_CN_NUMBER}]+)年.*经[验历]")
    P_CHANGE = PatternCollection(r"投资经理的?变更")

    def check(self):
        if not self.manager.verify_condition([AssetTemplateConditional.NAME_SINGLE_POOLED]):
            self.result.reasons.append(IgnoreConditionItem(reason_text="当前基金类型不是单一或集合类型"))
            return self.result
        answers = self.check_schema_fields(self.result)
        if self.result.suggestion:
            return self.result
        answer = answers[self.SCHEMA_FIELDS[0]]
        if match := self.P_EXPERIENCE.nexts(answer.value):
            if int(NumberUtil.cn_number_2_digit(match.group("val"))) < 3:
                self.result.reasons.append(
                    MatchFailedItem(
                        page=min(answer.outlines, key=int, default=0),
                        outlines=answer.outlines,
                        reason_text="投资经理经验年限应大于等于3年",
                    )
                )
                self.result.is_compliance = False
        else:
            self.result.reasons.append(
                MatchFailedItem(
                    page=min(answer.outlines, key=int, default=0),
                    outlines=answer.outlines,
                    reason_text="请补充“投资经理经验年限”",
                )
            )
            self.result.is_compliance = False

        if not self.P_CHANGE.nexts(answer.value):
            self.result.reasons.append(
                MatchFailedItem(
                    page=min(answer.outlines, key=int, default=0),
                    outlines=answer.outlines,
                    reason_text="未包含投资经理变更事项",
                )
            )
            self.result.is_compliance = False

        return self.result


class OrderPactItemsChecker(AssetSchemaChecker):
    LABEL = "schema_1071"
    RELATED_NAME = "投资指令的发送、确认和执行"
    NAME = "指令-合同应订明的事项"
    CONTRACT_CONTENT = [
        "【单一&集合】",
        "第五十九条 具体订明有关管理人在运用资产管理计划财产时向托管人发送资金划拨及其他款项收付的投资指令的事项：",
        "（一）交易清算授权；",
        "（二）投资指令的内容；",
        "（三）投资指令的发送、确认及执行时间与程序；",
        "（四）托管人依法暂缓、拒绝执行指令的情形和处理程序；",
        "（五）管理人发送错误指令的情形和处理程序；",
        "（六）更换投资指令被授权人的程序；",
        "（七）投资指令的保管；",
        "（八）其他相关责任。",
    ]

    P_ITEMS = [
        CheckResultRelation("交易清算授权", PatternCollection(r"交易清算授权")),
        CheckResultRelation("投资指令的内容", PatternCollection(r"指令的?内容")),
        CheckResultRelation(
            "投资指令的发送、确认及执行时间与程序", PatternCollection(r"指令的?(发送|确认|执行时间|程序)")
        ),
        CheckResultRelation(
            "托管人依法暂缓、拒绝执行指令的情形和处理程",
            PatternCollection(r"托管人.*?(?:暂缓|拒绝)执行指令的?(情形|处理程序)"),
        ),
        CheckResultRelation(
            "管理人发送错误指令的情形和处理程序", PatternCollection(r"管理人发送错误指令的?(情形|处理程序)")
        ),
        CheckResultRelation("更换投资指令被授权人的程序", PatternCollection(r"更换投资指令被授权人的?程序")),
        CheckResultRelation("投资指令的保管", PatternCollection(r"指令的?保管")),
        CheckResultRelation("其他相关责任", PatternCollection(r"其他相关责任")),
    ]

    def check(self):
        if not self.manager.verify_condition([AssetTemplateConditional.NAME_SINGLE_POOLED]):
            self.result.reasons.append(IgnoreConditionItem(reason_text="当前基金类型不是单一或集合类型"))
            return self.result

        self.check_syllabuses(CatalogsPattern.ASSET_ORDER_SEND_CONFIRMATION_EXECUTION)
        return self.result


class UltraViresTransactionItemsChecker(AssetSchemaChecker):
    LABEL = "schema_1072"
    RELATED_NAME = "越权交易的界定"
    NAME = "越权交易-合同应订明的事项"
    CONTRACT_CONTENT = [
        "【单一&集合】",
        "第六十条 具体订明下列事项：",
        "（一）越权交易的界定；",
        "（二）越权交易的处理程序；",
        "（三）托管人对管理人投资运作的监督。 ",
    ]

    P_ITEMS = [
        CheckResultRelation("越权交易的界定", PatternCollection(r"越权交易的界定")),
        CheckResultRelation("越权交易的处理程序", PatternCollection(r"越权交易的?处理程序")),
        CheckResultRelation(
            "托管人对管理人投资运作的监督", PatternCollection(r"(资产)?托管人对(资产)?管理人投资运作的?监督")
        ),
    ]

    def check(self):
        if not self.manager.verify_condition([AssetTemplateConditional.NAME_SINGLE_POOLED]):
            self.result.reasons.append(IgnoreConditionItem(reason_text="当前基金类型不是单一或集合类型"))
            return self.result
        self.check_syllabuses(CatalogsPattern.ASSET_DEFINITION_ULTRA_VIRES_TRANSACTION)
        return self.result


class AssessmentValueItemsChecker(AssetSchemaChecker):
    LABEL = "schema_1075"
    RELATED_NAME = "资产管理计划财产的估值和会计核算"
    NAME = "估值-合同应订明的事项"
    CONTRACT_CONTENT = [
        "【单一&集合】",
        "第六十一条 订明资产管理计划财产估值的相关事项，包括但不限于：",
        "（一）估值目的；",
        "（二）估值时间；",
        "（三）按照会计准则订明估值方法，使用侧袋估值等特殊估值方法的，应进行明确约定，并在风险揭示书中进行特别揭示；",
        "（四）估值对象；",
        "（五）估值程序；",
        "（六）估值错误的处理；",
        "（七）估值调整的情形与处理；",
        "（八）暂停估值的情形；",
        "【集合】（九）资产管理计划份额净值的确认；",
        "【单一】（九）资产管理计划资产净值的确认；",
        "（十）特殊情况的处理。",
    ]

    P_ITEMS = [
        CheckResultRelation("估值目的", PatternCollection(r"估值目的")),
        CheckResultRelation("估值时间", PatternCollection(r"估值时间")),
        CheckResultRelation("估值方法", PatternCollection(r"估值方法")),
        CheckResultRelation("估值对象", PatternCollection(r"估值对象")),
        CheckResultRelation("估值程序", PatternCollection(r"估值程序")),
        CheckResultRelation("估值错误的处理", PatternCollection(r"估值错误的?处理")),
        CheckResultRelation("估值调整的情形与处理", PatternCollection(r"估值调整的?(情形|处理)")),
        CheckResultRelation("暂停估值的情形", PatternCollection(r"暂停估值的?情形")),
        CheckResultRelation(
            "资产管理计划份额净值的确认",
            PatternCollection(r"(管理)?计划份额净值的?确认"),
            condition=AssetTemplateConditional.NAME_POOLED,
        ),
        CheckResultRelation(
            "资产管理计划资产净值的确认",
            PatternCollection(r"(管理)?计划资产净值的?确认"),
            condition=AssetTemplateConditional.NAME_SINGLE,
        ),
        CheckResultRelation("特殊情况的处理", PatternCollection(r"特殊情况的?处理")),
    ]

    def check(self):
        if not self.manager.verify_condition([AssetTemplateConditional.NAME_SINGLE_POOLED]):
            self.result.reasons.append(IgnoreConditionItem(reason_text="当前基金类型不是单一或集合类型"))
            return self.result

        self.check_syllabuses(CatalogsPattern.ASSET_MANAGEMENT_PLAN_VALUATION_ACCOUNTING_SETTLEMENT)
        return self.result


class CostItemsChecker(AssetSchemaChecker):
    LABEL = "schema_1078"
    RELATED_NAME = "资产管理计划的费用与税收"
    NAME = "费用-合同应订明的事项"
    CONTRACT_CONTENT = [
        "【单一&集合】",
        "第六十三条 订明资产管理计划费用的有关事项：",
        "（一）订明资产管理计划财产运作过程中，从资产管理计划财产中支付的费用种类、费率、费率的调整、计提标准、计提方式与支付方式等；",
        "【集合】（二）订明可列入资产管理计划财产费用的项目，其中，资产管理计划成立前发生的费用，以及存续期间发生的与募集有关的费用，不得在计划资产中列支；",
        "【单一】（二）订明可列入资产管理计划财产费用的项目，其中，资产管理计划成立前发生的费用不得在计划资产中列支；",
        "（三）订明管理人和托管人因未履行或未完全履行义务导致的费用支出或资产管理计划财产的损失，以及处理与资产管理计划财产运作无关事项或不合理事项所发生的费用等不得列入资产管理计划的费用；",
        "（四）订明资产管理计划的管理费率、托管费率、投资顾问费（如有）及其他服务业务费率。管理人可以与投资者约定，根据资产管理计划的管理情况提取适当的业绩报酬；",
        "（五）订明业绩报酬（如有）的计提原则、计算方法、计提比例和提取频率；",
        "（六）其他费用的计提原则和计算方法。",
        "第六十四条 根据国家有关税收规定，订明资产管理合同各方当事人缴税安排。",
    ]

    P_ITEMS = [
        CheckResultRelation("费用的种类", PatternCollection(r"费用的?种类")),
        CheckResultRelation(
            "费用计提方法、计提标准和支付方式",
            PatternCollection(rf"(?:(?:费用|计提方法|计提标准|支付方式)[{R_CONJUNCTION}]?){{3}}"),
        ),
        CheckResultRelation(
            "不列入资产管理业务费用的项目", PatternCollection(r"不列入[\u4e00-\u9fa5]*?管理业务费用的?项目")
        ),
        CheckResultRelation("费用的调整", PatternCollection(r"费用的?调整")),
        CheckResultRelation("税收", PatternCollection(r"税收")),
    ]

    def check(self):
        if not self.manager.verify_condition([AssetTemplateConditional.NAME_SINGLE_POOLED]):
            self.result.reasons.append(IgnoreConditionItem(reason_text="当前基金类型不是单一或集合类型"))
            return self.result

        self.check_syllabuses(CatalogsPattern.ASSET_MANAGEMENT_PLAN_FEES_TAXES)
        return self.result


class IncomeDistributionChecker(AssetSchemaChecker):
    LABEL = "schema_1082"
    RELATED_NAME = "资产管理计划的收益分配"
    NAME = "收益分配-合同应订明的事项"
    FROM = "证券投资基金托管业务管理办法（证监会令第172号修订 2020年7月10日）"
    ORIGIN = [
        "第二十二条 基金托管人应当对所托管基金履行法律法规、基金合同有关收益分配约定情况进行定期复核，发现基金收益分配有违规失信行为的，应当及时通知基金管理人，并报告中国证监会。",
    ]
    CONTRACT_CONTENT = [
        "【单一&集合】",
        "第六十五条 说明资产管理计划收益分配方案依据现行法律法规以及合同约定执行，并订明有关事项：",
        "（一） 可供分配利润的构成；",
        "（二） 收益分配原则，包括订明收益分配的基准、次数、比例、时间等；",
        "（三） 收益分配方案的确定与通知；",
        "（四） 收益分配的执行方式。 ",
    ]

    # https://gitpd.paodingai.com/cheftin/docs_scriber/-/issues/2447
    P_INVALID_PATTERN = PatternCollection(r"存续期内不进行收益分配")

    P_ITEMS = [
        # https://gitpd.paodingai.com/cheftin/docs_scriber/-/issues/2073#note_347510
        CheckResultRelation("可供分配利润的构成", PatternCollection(r"(?:利润|收益)的?构成")),
        CheckResultRelation("收益分配原则", PatternCollection(r"收益分配原则")),
        CheckResultRelation("收益分配方案的确定与通知", PatternCollection(r"收益分配方案的?(?:确定|通知)")),
        CheckResultRelation("收益分配的执行方式", PatternCollection(r"收益分配(?:方案)?的?执行方式")),
    ]

    def check(self):
        if not self.manager.verify_condition([AssetTemplateConditional.NAME_SINGLE_POOLED]):
            self.result.reasons.append(IgnoreConditionItem(reason_text="当前基金类型不是单一或集合类型"))
            return self.result
        chapter_pattern = CatalogsPattern.ASSET_MANAGEMENT_PLAN_INCOME_DISTRIBUTION
        _, paragraphs = self.reader.find_paragraphs_by_chapters([chapter_pattern.pattern])
        for para in paragraphs:
            if self.P_INVALID_PATTERN.nexts(clean_txt(para["text"])):
                outline = get_outlines([para])
                page = min(outline, key=int, default=0)
                self.result.is_compliance = True
                self.result.reasons.append(
                    MatchSuccessItem(
                        reason_text="本资产管理计划存续期内不进行收益分配", outlines=outline, page=page, matched=True
                    )
                )
                return self.result
        self.check_syllabuses(chapter_pattern, paragraphs=paragraphs)
        return self.result


class QRAndARChecker(AssetSchemaChecker):
    RULE_TYPE = RuleType.TEMPLATE.value
    LABEL = "schema_1084"
    RELATED_NAME = "信息披露与报告"
    NAME = "信息披露-季报和年报"
    FROM = "证券期货经营机构私募资产管理计划运作管理规定（证监会令第203号修订 2023年1月12日）"
    ORIGIN = [
        "第四十二条 证券期货经营机构应当按照资产管理合同的约定向投资者提供资产管理计划年度报告，披露报告期内资产管理计划运作情况，包括但不限于下列信息：",
        "（一）管理人履职报告；",
        "（二）托管人履职报告（如适用）；",
        "（三）资产管理计划投资表现；",
        "（四）资产管理计划投资组合报告；",
        "（五）资产管理计划财务会计报告；",
        "（六）资产管理计划投资收益分配情况；",
        "（七）投资经理变更、重大关联交易等涉及投资者权益的重大事项；",
        "（八）中国证监会规定的其他事项。",
        "资产管理计划季度报告应当披露前款除第（五）项之外的其他信息。",
    ]
    CONTRACT_CONTENT = [
        "【单一&集合】",
        "第六十八条 订明管理人应当向投资者提供资产管理计划季度报告和年度报告，披露报告期内资产管理计划运作情况，年度报告包括但不限于下列信息：",
        "（一）管理人履职报告；",
        "（二）托管人履职报告；",
        "（三）资产管理计划投资表现；",
        "（四）资产管理计划投资组合报告;",
        "（五）资产管理计划运用杠杆情况（如有）；",
        "（六）资产管理计划财务会计报告;",
        "（七）资产管理计划支付的管理费、托管费、业绩报酬（如有）等费用的计提基准、计提方式和支付方式；",
        "【集合】（八）资产管理计划投资收益分配情况；/【单一】无此条；",
        "（九）投资经理变更、重大关联交易等涉及投资者权益的重大事项；",
        "（十）中国证监会规定的其他事项。",
        "产管理计划季度报告应当披露前款除第（六）项之外的其他信息。",
        "明资产管理计划成立不足三个月或者存续期间不足三个月的，管理人可以不编制资产管理计划当期的季度报告和年度报告。",
    ]
    SCHEMA_FIELDS = ["年度报告", "季度报告"]
    P_ITEMS = []
    IS_COMPLETE_MATCH = False

    P_AR_ITEMS = [
        CheckResultRelation("管理人履职报告", PatternCollection(r"管理人履职报告")),
        CheckResultRelation("托管人履职报告", PatternCollection(r"托管人履职报告")),
        CheckResultRelation("资产管理计划投资表现", PatternCollection(r"投资表现")),
        CheckResultRelation("资产管理计划投资组合报告", PatternCollection(r"投资组合报告")),
        CheckResultRelation("资产管理计划财务会计报告", PatternCollection(r"财务会计报告")),
        CheckResultRelation("资产管理计划投资收益分配情况", PatternCollection(r"投资收益分配")),
        CheckResultRelation(
            "投资经理变更、重大关联交易等涉及投资者权益的重大事项",
            PatternCollection(r"(?:经理变更|关联交易).*?投资者权益的?重大事项"),
        ),
        CheckResultRelation("中国证监会规定的其他事项", PatternCollection(rf"证监会[^{R_PUNCTUATION}]+定的?其他事项")),
    ]
    P_QR_ITEMS = [
        CheckResultRelation("管理人履职报告", PatternCollection(r"管理人履职报告")),
        CheckResultRelation("托管人履职报告", PatternCollection(r"托管人履职报告")),
        CheckResultRelation("资产管理计划投资表现", PatternCollection(r"投资表现")),
        CheckResultRelation("资产管理计划投资组合报告", PatternCollection(r"投资组合报告")),
        CheckResultRelation("资产管理计划投资收益分配情况", PatternCollection(r"投资收益分配")),
        CheckResultRelation(
            "投资经理变更、重大关联交易等涉及投资者权益的重大事项",
            PatternCollection(r"(?:经理变更|关联交易).*?投资者权益的?重大事项"),
        ),
        CheckResultRelation("中国证监会规定的其他事项", PatternCollection(rf"证监会[^{R_PUNCTUATION}]+定的?其他事项")),
    ]

    TEMPLATES = {
        "年度报告": P_AR_ITEMS,
        "季度报告": P_QR_ITEMS,
    }

    def check(self):
        if not self.manager.verify_condition([AssetTemplateConditional.NAME_SINGLE_POOLED]):
            self.result.reasons.append(IgnoreConditionItem(reason_text="当前基金类型不是单一或集合类型"))
            return self.result
        # https://gitpd.paodingai.com/cheftin/docs_scriber/-/issues/2479
        reasons = []
        for key, item in self.TEMPLATES.items():
            _, paras = get_paragraphs_by_schema_fields(self.reader, self.manager, [key])
            self.P_ITEMS = item
            is_compliance, reason = self.check_templates(paras)
            reasons.append(reason)
            self.result.is_compliance &= is_compliance
        self.result.reasons = self.filter_same_reason(reasons)
        self.result.suggestion = self.generate_suggestion_by_reasons(self.result.reasons)
        return self.result


class InformationDisclosureChecker(AssetSchemaChecker):
    LABEL = "schema_1085"
    RELATED_NAME = "信息披露与报告"
    NAME = "信息披露-运作期间管理人向投资者提供的报告"
    FROM = "证券期货经营机构私募资产管理业务管理办法（证监会令第203号修订 2023年1月12日）"
    ORIGIN = [
        "第五十一条 资产管理计划运作期间，证券期货经营机构应当按照以下要求向投资者提供相关信息：",
        "（一）投资标准化资产的资产管理计划至少每周披露一次净值，投资非标准化资产的资产管理计划至少每季度披露一次净值；",
        "（二）开放式资产管理计划净值的披露频率不得低于资产管理计划的开放频率，分级资产管理计划应当披露各类别份额净值；",
        "（三）每季度结束之日起一个月内披露季度报告，每年度结束之日起四个月内披露年度报告；",
        "（四）发生资产管理合同约定的或者可能影响投资者利益的重大事项时，在事项发生之日起五日内向投资者披露；",
        "（五）中国证监会规定的其他要求。",
        "资产管理计划成立不足三个月或者存续期间不足三个月的，证券期货经营机构可以不编制资产管理计划当期的季度报告和年度报告。",
    ]
    SCHEMA_FIELDS = ["向资产委托人提供的报告"]

    DEFAULT_TEMPLATES = [
        "本计划成立后，管理人每个交易日向委托人报告一次上一个交易日经托管人复核的计划份额净值。",
        "发生本合同约定的、可能影响投资者利益的重大事项时，管理人应当在事项发生之日起5日内向投资者披露。",
        "资产管理计划成立不足三个月或者存续期间不足三个月的，管理人可以不编制资产管理计划当期的季度报告和年度报告。",
    ]

    P_ITEMS = [
        CheckResultRelation("净值报告", PatternCollection(r"(净值报告|计划资产净值)$")),
        CheckResultRelation("季度报告", PatternCollection(r"季度报告$")),
        CheckResultRelation("年度报告", PatternCollection(r"年度报告$")),
        CheckResultRelation("临时报告", PatternCollection(r"(临时报告|临时披露事项|重大事项临时报告)$")),
    ]
    TEMPLATES = [
        {
            "name": TemplateName.EDITING_NAME,
            "content_title": TemplateName.EDITING_TITLE,
            "items": [
                {
                    "conditions": [AssetTemplateConditional.NAME_SINGLE_POOLED],
                    "items": [
                        [
                            "本计划成立后，管理人每周向资产委托人报告一次当期末经托管人复核的计划份额净值。",
                            "本计划成立后，管理人每个交易日向委托人报告一次上一个交易日经托管人复核的计划份额净值。",
                        ],
                        "发生本合同约定的、可能影响投资者利益的重大事项时，管理人应当在事项发生之日起5日内向投资者披露。",
                        "资产管理计划成立不足三个月或者存续期间不足三个月的，管理人可以不编制资产管理计划当期的季度报告和年度报告。",
                    ],
                },
                {
                    "conditions": [AssetTemplateConditional.NAME_SINGLE_POOLED],
                    "items": [
                        [
                            "本计划成立后，管理人每周向资产委托人报告一次当期末经托管人复核的计划份额净值。",
                            "本计划成立后，管理人每个交易日向委托人报告一次上一个交易日经托管人复核的计划份额净值。",
                        ],
                        "发生本合同约定的、可能影响投资者利益的重大事项时，管理人应当在事项发生之日起5日内向投资者披露。",
                        "资产管理计划成立不足三个月或者存续期间不足三个月的，管理人可以不编制资产管理计划当期的季度报告。",
                        "资产管理计划成立不足三个月或者存续期间不足三个月的，管理人可以不编制资产管理计划当期的年度报告。",
                    ],
                },
            ],
        },
    ]
    P_ASSET_DISCLOSURE_REPORTING = RegularChapter("信息披露与报告", re.compile(r"信息披露[及和与、./\\]?报告$"))

    def check(self):
        if not self.manager.verify_condition([AssetTemplateConditional.NAME_SINGLE_POOLED]):
            self.result.reasons.append(IgnoreConditionItem(reason_text="当前基金类型不是单一或集合类型"))
            return self.result

        _, paragraphs = self.reader.find_paragraphs_by_chapters([self.P_ASSET_DISCLOSURE_REPORTING.pattern])
        unmatch_names = []

        for item in self.P_ITEMS:
            for paragraph in paragraphs:
                if item.pattern.nexts(paragraph["text"]):
                    item.result = True
                    break
            else:
                if item.condition and not self.manager.verify_condition([item.condition]):
                    continue
                unmatch_names.append(item.name)

        outlines = get_outlines(paragraphs)
        suggestions = []
        if unmatch_names:
            self.result.is_compliance = False
            self.result.reasons = [
                MatchFailedItem(
                    page=min(outlines, key=int, default=0),
                    reason_text=f"未找到“{'、'.join(unmatch_names)}”章节目录",
                    outlines=outlines,
                )
            ]
            suggestions.append(f"请在{self.RELATED_NAME}中补充:{'、'.join(unmatch_names)}")

        template = {
            "label": self.LABEL,
            "schema_fields": self.SCHEMA_FIELDS,
            "related_name": self.RELATED_NAME,
            "name": self.NAME,
            "from": "",
            "origin": "",
            "templates": self.TEMPLATES,
        }
        # https://gitpd.paodingai.com/cheftin/docs_scriber/-/issues/2484
        # 多段多种描述
        condition_checker = PublicAssetSingleWithRatioChecker(
            reader=self.reader,
            manager=self.manager,
            file=self.file,
            schema_id=self.schema_id,
            labels=self.labels,
            fund_manager_info=self.fund_manager_info,
        )
        condition_checker.TEMPLATES = [template]
        if not (check_res := condition_checker.check()):
            self.result.is_compliance = False
            origin_content = "\n".join(self.DEFAULT_TEMPLATES)
            reason = NoMatchReasonItem(template=Template(content=origin_content, name="范文"))
            self.result.reasons = [reason]
            suggestions.append(reason.render_suggestion(self.reader, self.RELATED_NAME))
            self.result.suggestion = "\n\n".join(suggestions)
            return self.result
        if check_res[0].suggestion:
            suggestions.append(check_res[0].suggestion)
        reasons = check_res[0].reasons
        if any(not isinstance(reason, IgnoreConditionItem) for reason in reasons):
            reasons = [reason for reason in reasons if not isinstance(reason, IgnoreConditionItem)]
        self.result.reasons.extend(self.filter_same_reason(reasons))
        self.result.suggestion = "\n\n".join(suggestions)
        if self.result.is_compliance:
            self.result.is_compliance = all(isinstance(reason, MatchReasonItem) for reason in reasons)
        return self.result


class InterimReportChecker(AssetSchemaChecker):
    LABEL = "schema_1086"
    RELATED_NAME = "信息披露与报告"
    NAME = "信息披露-临时报告的情形"
    FROM = "证券期货经营机构私募资产管理计划备案管理办法（试行）中基协发[2019]4号 2019年6月3日"
    ORIGIN = [
        "第十七条资产管理人在资产管理计划发生以下情形，对资产管理计划持续运行、投资者利益、资产净值产生重大影响时，应当于五个工作日内向证券投资基金业协会报告：",
        "（一）以资产管理计划资产从事重大关联交易的；",
        "（二）涉及产品重大诉讼、仲裁、财产纠纷的，以及出现延期兑付、负面舆论、群体性事件等重大风险事件的；",
        "（三）资产管理计划因委托财产流动性受限等原因延长清算时间的；",
        "（四）发生其他对持续运行、投资者利益、资产净值产生重大影响事件的。",
    ]
    CONTRACT_CONTENT = [
        "【单一&集合】",
        "第六十九条 订明发生资产管理合同约定或可能影响投资者利益的重大事项时，在事项发生之日起五日内向投资者披露。",
        "第七十条 管理人的董事、监事、从业人员及其配偶、控股股东、实际控制人或者其他关联方参与资产管理计划，应向投资者充分披露。",
    ]
    SCHEMA_FIELDS = ["临时报告"]

    TEMPLATES = [
        {
            "name": TemplateName.EDITING_NAME,
            "content_title": TemplateName.EDITING_TITLE,
            "chapter": ChapterPattern.CHAPTER_ASSET_INVESTMENT_COUNSELOR,
            "items": [
                {
                    "conditions": [AssetTemplateConditional.NAME_POOLED],
                    "items": [
                        "（1）投资经理发生变动；",
                        "（2）涉及资产管理人、计划财产、资产托管业务的诉讼；",
                        [
                            "（3）投资顾问发生变动；",
                            "（3）投资顾问（如有）发生变动；",
                        ],
                        [
                            "（4）资产管理人、资产托管人托管业务部门与本合同项下资产管理计划财产相关的行为受到监管部门的严重行政处罚； ",
                            "（4）管理人、托管人托管业务部门与本合同项下资产管理计划财产相关的行为受到监管部门的严重行政处罚；",
                        ],
                        "（5）资产管理人及其董事、总经理及其他高级管理人员、投资经理受到严重行政处罚，资产托管人的托管业务或托管业务部门负责人受到严重行政处罚；",
                        "（6）资产管理人的董事、监事、从业人员及其配偶、控股股东、实际控制人或者其他关联方参与资产管理计划的；",
                        "（7）管理人根据本合同约定自行或与托管人提请确认后对资产管理合同的变更；",
                        "（8）法律法规、监管机构、自律组织规定的其他事项。",
                        [
                            "（9）发生重大关联交易等涉及投资者权益的重大事项；",
                            "（9）发生一般/重大关联交易等涉及投资者权益的重大事项；",
                            "（9）从事重大关联交易的；",
                            "（9）从事关联交易的；",
                        ],
                        "（10）管理人、托管人因重大违法违规，被监管机构取消或认定不符合相关业务资格；",
                        "（11）管理人、托管人因解散、破产、撤销等原因不能履行相应职责；",
                        "（12）资产计价出现错误；",
                        "（13）管理费、托管费、业绩报酬、税费等计提方式或费率发生变更；",
                        "（14）其他对计划持续运营、客户利益、资产净值产生重大影响的事件；",
                    ],
                }
            ],
        },
    ]

    def check(self):
        if not self.manager.verify_condition([AssetTemplateConditional.NAME_POOLED]):
            self.result.reasons.append(IgnoreConditionItem(reason_text="当前基金类型不是集合类型"))
            return self.result

        answers = self.check_schema_fields(self.result)
        if self.result.suggestion:
            return self.result
        parent_chapter, paras = get_paragraphs_by_schema_answers(self.reader, [answers[self.SCHEMA_FIELDS[0]]])
        count = 0
        # https://gitpd.paodingai.com/cheftin/docs_scriber/-/issues/2485
        for paragraph in paras:
            if paragraph["index"] == parent_chapter["element"]:
                continue
            if P_NUMBERING.nexts(paragraph["text"]):
                count += 1
        if count > 14:
            self.result.is_compliance = False
            self.result.reasons.append(MatchFailedItem(reason_text="临时报告条目超过14条"))
            return self.result

        template = {
            "label": self.LABEL,
            "schema_fields": self.SCHEMA_FIELDS,
            "related_name": self.RELATED_NAME,
            "name": self.NAME,
            "from": "",
            "origin": "",
            "templates": [],
        }
        reasons = []
        template["templates"] = self.TEMPLATES
        self.condition_checker.TEMPLATES = [template]
        if not (check_res := self.condition_checker.check()):
            return self.result
        if check_res[0].suggestion:
            self.result.suggestion = check_res[0].suggestion
        reasons.extend(check_res[0].reasons)
        if any(not isinstance(reason, IgnoreConditionItem) for reason in reasons):
            reasons = [reason for reason in reasons if not isinstance(reason, IgnoreConditionItem)]
        self.result.reasons.extend(self.filter_same_reason(reasons))
        if self.result.is_compliance:
            self.result.is_compliance = all(isinstance(reason, MatchReasonItem) for reason in reasons)
        return self.result


class GeneralRiskChecker(AssetSchemaChecker):
    LABEL = "schema_1089"
    RELATED_NAME = "风险揭示"
    NAME = "风险揭示-一般风险"
    FROM = "证券期货经营机构私募资产管理计划运作管理规定（证监会令第203号修订 2023年1月12日）"
    ORIGIN = [
        "第八条 证券期货经营机构设立资产管理计划，应当制作风险揭示书。风险揭示书的内容应当具有针对性，表述应当清晰、明确、易懂，并以醒目方式充分揭示资产管理计划的市场风险、信用风险、流动性风险、操作风险、关联交易的风险、聘请投资顾问的特定风险等各类风险。",
    ]
    CONTRACT_CONTENT = [
        "【单一&集合】",
        "第七十二条 管理人应当在资产管理合同中向投资者重点揭示管理人在管理、运用或处分财产过程中，资产管理计划可能面临的风险，包括但不限于：",
        "（一）资产管理计划面临的一般风险，如本金损失风险、市场风险、管理风险、流动性风险、信用风险、【集合】募集失败风险/【单一】无此条、投资标的风险、关联交易风险、操作或技术风险、税收风险等；",
        "（二）资产管理计划面临的特定风险，如特定投资方法及资产管理计划所投资的特定投资对象可能引起的特定风险、资产管理计划外包事项所涉风险以及未在证券投资基金业协会完成备案的风险、聘请投资顾问的特定风险等；",
        "（三）其他风险。",
    ]

    P_ITEMS = [
        CheckResultRelation("本金损失风险", PatternCollection(r"本金损失风险")),
        CheckResultRelation("市场风险", PatternCollection(r"市场风险")),
        CheckResultRelation("管理风险", PatternCollection(r"管理风险")),
        CheckResultRelation("流动性风险", PatternCollection(r"流动性风险")),
        CheckResultRelation("信用风险", PatternCollection(r"信用风险")),
        # https://gitpd.paodingai.com/cheftin/docs_scriber/-/issues/2554#note_353595
        CheckResultRelation(
            "募集失败风险", PatternCollection(r"募集失败风险"), condition=AssetTemplateConditional.NAME_POOLED
        ),
        CheckResultRelation(
            "投资标的风险", PatternCollection(r"投资标的风险"), condition=AssetTemplateConditional.NAME_POOLED
        ),
        CheckResultRelation("税收风险", PatternCollection(r"税收风险"), condition=AssetTemplateConditional.NAME_POOLED),
        CheckResultRelation(
            "操作或技术风险", PatternCollection(r"操作或技术风险"), condition=AssetTemplateConditional.NAME_POOLED
        ),
        CheckResultRelation(
            "关联交易风险", PatternCollection(r"关联交易风险"), condition=AssetTemplateConditional.NAME_POOLED
        ),
    ]

    def check(self):
        if not self.manager.verify_condition([AssetTemplateConditional.NAME_SINGLE_POOLED]):
            self.result.reasons.append(IgnoreConditionItem(reason_text="当前基金类型不是单一或集合类型"))
            return self.result
        self.check_syllabuses(CatalogsPattern.ASSET_DISCLOSURE_RISK)
        return self.result


class RaisingPeriodChecker(AssetSchemaChecker):
    """
    【集合-非股权】验证募集期限不超过60天；
    【集合-股权】验证募集期限不超过12个月
    """

    LABEL = "schema_1026"
    RELATED_NAME = "资产管理计划的募集"
    NAME = "集合计划的募集期限"
    FROM = "证券期货经营机构私募资产管理计划运作管理规定（证监会令第203号修订 2023年1月12日）"
    ORIGIN = "第五条 ……集合资产管理计划的初始募集期自资产管理计划份额发售之日起不得超过60天，专门投资于未上市企业股权的集合资产管理计划的初始募集期自资产管理计划份额发售之日起不得超过12个月。"
    CONTRACT_CONTENT = [
        "【集合】",
        "第二十六条 订明资产管理计划募集的有关事项，包括但不限于：",
        "（一）资产管理计划的募集对象、募集方式、募集期限，其中初始募集期自资产管理计划份额发售之日起不超过60天，专门投资于未上市企业股权的资产管理计划初始募集期自资产管理计划份额发售之日起不超过12个月；",
        "（二）资产管理计划的认购事项，包括资产管理计划认购费用、认购申请的确认、认购份额的计算方式、初始认购资金的管理及利息处理方式等；",
        "（三）资产管理计划的最低认购金额、支付方式等；最低认购金额不包含认购费；",
        "（四）其他事项。",
        "二十七条 订明资产管理计划募集结算专用账户和销售机构委托募集账户（如有）的披露渠道和查询方式。",
    ]
    SCHEMA_FIELDS = ["募集期限"]

    P_RATING_PERIOD = PatternCollection(
        [
            rf"募集期[自从](?:(?:资产)?管理)?计划份额发售[^{R_PUNCTUATION}]*?不超过(?P<day>[{R_CN_NUMBER}]+)[天日]",
            rf"募集期[自从](?:(?:资产)?管理)?计划份额发售[^{R_PUNCTUATION}]*?不超过(?P<month>[{R_CN_NUMBER}]+)个月",
            rf"募集期[自从](?:(?:资产)?管理)?计划份额发售[^{R_PUNCTUATION}]*?不超过(?P<year>[{R_CN_NUMBER}]+)年",
            rf"募集期[自从](?:(?:资产)?管理)?计划份额发售[^{R_PUNCTUATION}]*?不超过(?P<quarter>[{R_CN_NUMBER}]+)个季度",
        ]
    )

    @classmethod
    def extract_period_days(cls, content) -> int | None:
        if not (match := cls.P_RATING_PERIOD.nexts(clean_txt(content))):
            return None
        time_dict = match.groupdict()
        if day := time_dict.get("day"):
            return int(NumberUtil.cn_number_2_digit(day))
        if month := time_dict.get("month"):
            return int(NumberUtil.cn_number_2_digit(month)) * 30
        if year := time_dict.get("year"):
            return int(NumberUtil.cn_number_2_digit(year)) * 365
        if quarter := time_dict.get("quarter"):
            return int(NumberUtil.cn_number_2_digit(quarter)) * 90
        return None

    def valid_period(self, period: int, threshold_value: int):
        if period <= threshold_value:
            self.result.is_compliance = True
            self.result.reasons.append(MatchSuccessItem(reason_text=f"募集期限未超过{threshold_value}天"))
        else:
            self.result.is_compliance = False
            self.result.reasons.append(MatchFailedItem(reason_text=f"募集期限不应超过{threshold_value}天"))
            self.result.suggestion = f"请修改募集期限不超过{threshold_value}天"

    def check(self):
        if not self.manager.verify_condition([AssetTemplateConditional.NAME_POOLED]):
            self.result.reasons.append(IgnoreConditionItem(reason_text="当前基金类型不是集合类型"))
            return self.result

        answers = self.check_schema_fields(self.result)
        if self.result.suggestion:
            return self.result

        if (days := self.extract_period_days(answers[self.SCHEMA_FIELDS[0]].value)) is None:
            self.result.is_compliance = False
            self.result.reasons.append(MatchSuccessItem(reason_text="未找到管理计划的募集期限"))
            self.result.suggestion = "请在资产管理计划的募集中补充管理计划的募集期限"
            return self.result

        threshold_value = 365 if self.manager.verify_condition([AssetTemplateConditional.STOCK_RIGHT_YES]) else 60
        self.valid_period(days, threshold_value)
        return self.result


class SubscribeAmountChecker(AssetSchemaChecker):
    """
    【固定收益类】xx≥30；
    【混合类】xx≥40；
    【权益类/期货和衍生品类/非标投资】xx≥100
    """

    LABEL = "schema_1028"
    RELATED_NAME = "资产管理计划的募集"
    NAME = "集合计划投资者初始认购金额"
    FROM = "证券期货经营机构私募资产管理计划运作管理规定（证监会令第203号修订 2023年1月12日）"
    ORIGIN = [
        "第三条……合格投资者投资于单只固定收益类资产管理计划的金额不低于30万元，投资于单只混合类资产管理计划的金额不低于40万元，投资于单只权益类、期货和衍生品类资产管理计划的金额不低于100万元。资产管理计划投资于《管理办法》第三十八条第（五）项规定的非标准化资产的，接受单个合格投资者参与资金的金额不低于100万元。",
        "资产管理计划接受其他资产管理产品参与的，不合并计算其他资产管理产品的投资者人数，但应当有效识别资产管理计划的实际投资者与最终资金来源。",
    ]
    SCHEMA_FIELDS = ["资产管理计划的最低认购金额和支付方式"]

    P_SUBSCRIBE_AMOUNT = PatternCollection(rf"募集期间的?认购金额应?不应?得?[低少]于(?P<number>{R_FLOAT_NUMBER})元")

    P_NUMBER_EXTRA_CHAR = PatternCollection(r"[\[\]【】]")

    # https://gitpd.paodingai.com/cheftin/docs_scriber/-/issues/2012#note_341040
    VALID_AMOUNT_TYPES = (
        ("30万", [AssetTemplateConditional.FIXED_INCOME_CATEGORY, AssetTemplateConditional.NON_STANDARD_INVESTMENT_NO]),
        (
            "100万",
            [AssetTemplateConditional.FIXED_INCOME_CATEGORY, AssetTemplateConditional.NON_STANDARD_INVESTMENT_YES],
        ),
        ("40万", [AssetTemplateConditional.MIXED_CLASS, AssetTemplateConditional.NON_STANDARD_INVESTMENT_NO]),
        ("100万", [AssetTemplateConditional.MIXED_CLASS, AssetTemplateConditional.NON_STANDARD_INVESTMENT_YES]),
        ("100万", [AssetTemplateConditional.EQUITIES_FUTURES_DERIVATIVES]),
    )

    @classmethod
    def extract_subscribe_amount(cls, content) -> int | None:
        if not (match := cls.P_SUBSCRIBE_AMOUNT.nexts(clean_txt(content))):
            return None
        return int(NumberUtil.cn_number_2_digit(match.group("number")))

    def valid_amount(self, period: int, threshold_value: str):
        if period >= NumberUtil.cn_number_2_digit(threshold_value):
            self.result.is_compliance = True
            self.result.reasons.append(MatchSuccessItem(reason_text=f"最低认购金额合规，不低于{threshold_value}元"))
        else:
            self.result.is_compliance = False
            self.result.reasons.append(MatchFailedItem(reason_text=f"最低认购金额不得低于{threshold_value}元"))
            self.result.suggestion = f"请修改最低认购金额不低于{threshold_value}元"

    def check(self):
        if not self.manager.verify_condition([AssetTemplateConditional.NAME_POOLED]):
            self.result.reasons.append(IgnoreConditionItem(reason_text="当前基金类型不是集合类型"))
            return self.result

        answers = self.check_schema_fields(self.result)
        if self.result.suggestion:
            return self.result

        content = self.P_NUMBER_EXTRA_CHAR.sub("", answers[self.SCHEMA_FIELDS[0]].value)
        if (subscribe_amount := self.extract_subscribe_amount(content)) is None:
            self.result.is_compliance = False
            self.result.reasons.append(MatchFailedItem(reason_text="未找到资产管理计划的最低认购金额"))
            self.result.suggestion = "请在资产管理计划的募集中补充最低认购金额"
            return self.result

        for amount, conditionals in self.VALID_AMOUNT_TYPES:
            if self.manager.verify_condition(conditionals):
                self.valid_amount(subscribe_amount, amount)
                return self.result
        self.result.reasons.append(
            IgnoreConditionItem(reason_text="当期基金不是固定收益类、混合类、权益类、期货和衍生品类、非标投资等类型")
        )
        return self.result


class ManagePlansRaiseChecker(AssetSchemaChecker):
    RULE_TYPE = RuleType.TEMPLATE.value
    LABEL = "template_1027"
    RELATED_NAME = "资产管理计划的募集"
    NAME = "计划的募集方式"
    FROM = "证券期货经营机构私募资产管理业务管理办法（证监会令第203号修订 2023年1月12日）"
    ORIGIN = [
        "第十五条 证券期货经营机构可以自行销售资产管理计划，也可以委托具有公开募集证券投资基金（以下简称公募基金）销售资格的机构（以下简称销售机构）销售或者推介资产管理计划。",
        "销售机构应当依法、合规销售或者推介资产管理计划。",
    ]
    SCHEMA_FIELDS = ["募集方式"]

    TEMPLATES = [
        {
            "name": TemplateName.EDITING_NAME,
            "content_title": TemplateName.EDITING_TITLE,
            "chapter": ChapterPattern.CHAPTER_ASSET_MANAGEMENT_PLAN_RAISE,
            "items": [
                {
                    "type": TemplateCheckTypeEnum.SINGLE_SELECT.value,
                    "rules": {
                        "IR_1": {
                            "para_pattern": PatternCollection(
                                rf"有(?P<content>[^{R_NOT_CONJUNCTION_PUNCTUATION}]+)销售资格"
                            ),
                            "default": "公开募集证券投资基金/公募基金",
                            "patterns": [
                                {
                                    "pattern": PatternCollection(r"公募基金"),
                                    "content": "公募基金",
                                },
                                {
                                    "pattern": PatternCollection(r"公开募集证券投资基金"),
                                    "content": "公开募集证券投资基金",
                                },
                            ],
                        },
                        "IR_2": {
                            "para_pattern": PatternCollection(
                                rf"销售资格(?P<content>[^{R_NOT_CONJUNCTION_PUNCTUATION}]+)募集"
                            ),
                            "default": "代理销售机构/机构/代销机构",
                            "patterns": [
                                {
                                    "pattern": PatternCollection(r"代理销售机构"),
                                    "content": "代理销售机构",
                                },
                                {
                                    "pattern": PatternCollection(r"代销机构"),
                                    "content": "代销机构",
                                },
                                {
                                    "pattern": PatternCollection(r"机构"),
                                    "content": "机构",
                                },
                            ],
                        },
                    },
                    "items": [
                        {
                            "single_optional": [
                                {
                                    "conditions": [AssetTemplateConditional.NAME_POOLED],
                                    "items": [
                                        [
                                            "本计划由资产管理人自行销售或通过资产管理人委托的具有{IR_1}销售资格的{IR_2}向投资者募集。",
                                            "本计划由管理人自行销售。",
                                            "本计划由管理人委托的具有{IR_1}销售资格的{IR_2}向投资者募集。",
                                        ]
                                    ],
                                },
                                {
                                    "conditions": [AssetTemplateConditional.NAME_SINGLE],
                                    "items": [
                                        [
                                            "",
                                            "本计划由资产管理人自行销售或通过资产管理人委托的具有{IR_1}销售资格的{IR_2}向投资者募集。",
                                            "本计划由管理人自行销售。",
                                            "本计划由管理人委托的具有{IR_1}销售资格的{IR_2}向投资者募集。",
                                        ]
                                    ],
                                },
                            ]
                        },
                    ],
                },
            ],
        },
    ]

    def check(self):
        _ = self.check_schema_fields(self.result)
        if self.result.suggestion:
            # https://gitpd.paodingai.com/cheftin/docs_scriber/-/issues/2343
            if self.manager.verify_condition([AssetTemplateConditional.NAME_SINGLE]):
                self.result.suggestion = ""
                self.result.reasons = []
                self.result.is_compliance = True
            return self.result

        self.condition_checker.TEMPLATES = [
            {
                "label": self.LABEL,
                "schema_fields": self.SCHEMA_FIELDS,
                "related_name": self.RELATED_NAME,
                "name": self.NAME,
                "from": self.FROM,
                "origin": self.ORIGIN,
                "templates": self.TEMPLATES,
            }
        ]
        if not (check_res := self.condition_checker.check()):
            self.result.is_compliance = True
            return self.result
        return check_res[0]


class LargeDenominationWithdrawalChecker(AssetSchemaChecker):
    """
    【集合】章节检查是否已约定巨额退出、连续巨额退出、大额退出的内容
    巨额退出的内容判断依据：巨额退出的认定、巨额退出的处理方式、巨额退出的通知
    大额退出的内容判断方式：大额推出的通知
    若提取内容为空则提示对应字段为空
    连续巨额推出：章节小标题是否有包含‘连续巨额推出’的小标题，有则合规，反之不合规
    """

    LABEL = "schema_1094"
    RELATED_NAME = "资产管理计划的参与、退出与转让"
    NAME = "集合计划的巨额退出和大额退出机制"
    FROM = "证券期货经营机构私募资产管理计划运作管理规定（证监会令第203号修订 2023年1月12日）"
    ORIGIN = [
        "第二十八条 开放式集合资产管理计划资产管理合同，应当明确约定计划巨额退出和连续巨额退出的认定标准、退出顺序、退出价格确定、退出款项支付、告知客户方式，以及单个客户大额退出的预约申请等事宜，相关约定应当符合公平、合理、公开的原则。",
        "证券期货经营机构经与托管人协商，在确保投资者得到公平对待的前提下，可以依照法律、行政法规、中国证监会规定以及合同约定，延期办理巨额退出申请、暂停接受退出申请、延缓支付退出款项、收取短期赎回费，或者采取中国证监会认可的其他流动性管理措施。",
    ]
    SCHEMA_FIELDS = ["巨额退出的认定", "巨额退出的处理方式", "巨额退出的通知", "大额退出的通知"]

    def check(self):
        if not self.manager.verify_condition([AssetTemplateConditional.NAME_POOLED]):
            self.result.reasons.append(IgnoreConditionItem(reason_text="当前基金类型不是集合类型"))
            return self.result
        self.result.is_compliance = False
        self.check_schema_fields(self.result)
        if self.result.suggestion:
            return self.result
        chapters = self.reader.find_sylls_by_pattern(
            [CatalogsPattern.ASSET_MANAGE_PLAN_PARTICIPATION_WITHDRAWAL_TRANSFER.pattern]
        )
        if chapters:
            for syllabus in self.reader.syllabus_reader.get_child_syllabus(chapters[0]):
                if "连续巨额退出" in clean_txt(syllabus["title"]):
                    self.result.is_compliance = True
                    return self.result
        self.result.reasons.append(MatchFailedItem(reason_text="当前章节的小标题未包含“连续巨额退出”"))
        self.result.suggestion = f"请在《{self.RELATED_NAME}》章节的小标题中补充“连续巨额退出”"
        return self.result
