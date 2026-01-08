from collections import defaultdict

from remarkable.checker.base import BaseChecker
from remarkable.common.pattern import PatternCollection
from remarkable.common.util import clean_txt
from remarkable.plugins.cgs.common.para_similarity import ParagraphSimilarity
from remarkable.plugins.cgs.common.utils import get_xpath_by_outlines, group_table_cells_by_row
from remarkable.plugins.cgs.schemas.reasons import (
    ConflictReasonItem,
    MatchFailedItem,
    MatchReasonItem,
    NoMatchReasonItem,
    Template,
)
from remarkable.plugins.ext_api.common import is_table_elt
from remarkable.service.predictor import is_paragraph_elt


def replace_parenthesis(word):
    word = clean_txt(word)
    word = word.replace("(", "（")
    word = word.replace(")", "）")
    return word


class BaseSchemaChecker(BaseChecker):
    FROM = ""
    ORIGIN = ""
    CONVERT_TYPES = None
    RELATED_NAME = None
    SCHEMA_FIELDS = []
    CONTRACT_CONTENT = ""

    def prev_check(self):
        return None

    def check(self):
        raise NotImplementedError

    def __init__(self, reader, file, manager, schema_id=None, labels=None, fund_manager_info=None):
        super().__init__(reader, file, manager, schema_id, labels)
        self.fund_manager_info = fund_manager_info or {}
        fun_manager_type = self.fund_manager_info.get("基金管理人概况-类型")
        self.fun_manager_type = None
        if fun_manager_type:
            self.fun_manager_type = fun_manager_type.get("text") or ""

    @classmethod
    def get_fun_manager_type(cls, fund_manager_type):
        fund_manager_type = fund_manager_type or ""
        if "股权" in fund_manager_type:
            return "股权投资"
        for item in ["证券投资", "创业投资", "股权投资", "资产配置"]:
            if item in fund_manager_type:
                return item
        return None

    def get_origin_contents(self):
        template_origin = self.ORIGIN
        if isinstance(template_origin, list):
            template_origin = "\n".join(template_origin)
        template_from = self.FROM
        if not isinstance(template_from, list):
            template_from = [template_from]
        template_from = [
            item if item.startswith("《") and item.endswith("》") else f"《{item}》" for item in template_from
        ]
        return ["\n".join(template_from), template_origin]

    def get_contract_content(self):
        if isinstance(self.CONTRACT_CONTENT, list):
            return "\n".join(self.CONTRACT_CONTENT)
        return self.CONTRACT_CONTENT

    def check_schema_fields(self, result):
        suggestions = []
        answers = {}
        for field in self.SCHEMA_FIELDS:
            answer = self.manager.get(field)
            if not answer or not answer.value:
                result.reasons.append(MatchFailedItem(reason_text=f"要素“{field}”为空"))
                suggestions.append(f"请补充要素：“{field}”")
            else:
                answers[field] = answer
        if suggestions:
            result.is_compliance = False
        result.suggestion = "\n".join(suggestions)
        return answers

    def paragraph_similarity(
        self,
        result,
        paragraphs_left_list,
        paragraphs_right,
        outlines,
        origin_content,
        name,
        content_title,
        source="",
    ):
        group_similarity = defaultdict(list)
        current_similarities = []
        result.is_compliance = False
        for paragraphs_left in paragraphs_left_list:
            current_similarity = ParagraphSimilarity(
                paragraphs_left,
                paragraphs_right,
                convert_types=self.CONVERT_TYPES,
            )
            group_similarity[current_similarity.valid_sentences_count].append(current_similarity)
            current_similarities.append(current_similarity)

        similarities = group_similarity[max(group_similarity.keys())]
        similarity = sorted(similarities, key=lambda x: x.max_ratio)[-1]
        if similarity.is_matched:
            outlines = similarity.right_outlines
        page = min(outlines, key=int, default=0)
        if similarity.is_full_matched_or_contain or similarity.is_full_matched_without_extra_para:
            result.reasons.append(
                MatchReasonItem(
                    template=Template(content=origin_content, name=name, content_title=content_title),
                    content=similarity.right_content,
                    content_title="当前合同",
                    page=page,
                    outlines=outlines,
                    diff=similarity.simple_results,
                    source=source,
                )
            )
            result.is_compliance = True
        elif similarity.is_matched:
            result.reasons.append(
                ConflictReasonItem(
                    template=Template(content=origin_content, name=name, content_title=content_title),
                    content=similarity.right_content,
                    page=page,
                    content_title="当前合同",
                    outlines=outlines,
                    diff=similarity.simple_results,
                    xpath=get_xpath_by_outlines(self.reader, outlines),
                    source=source,
                )
            )
        else:
            result.reasons.append(
                NoMatchReasonItem(template=Template(content=origin_content, name=name), matched=False)
            )
        for reason in result.reasons:
            if isinstance(reason, (NoMatchReasonItem, ConflictReasonItem)):
                result.suggestion = reason.render_suggestion(self.reader, self.RELATED_NAME or "")

    def check_cover(self, keyword: str) -> list:
        """
        检查封面
        """
        cover_text, elements = self.join_page_text(0)
        if keyword not in replace_parenthesis(cover_text):
            return elements
        return []

    def check_signature_page(self, keyword: str, pattern: PatternCollection) -> list:
        """
        检查签署页
        """
        if not pattern:
            return []
        pages = list(self.reader.data["pages"].keys())
        cover_text, elements = self.join_page_text(int(pages[-1]))
        # 1、首先判断是否为签署页
        is_signature_page = False
        if "本页无正文" in cover_text:
            is_signature_page = True
        # 2、匹配内容
        if is_signature_page:
            if pattern.nexts(cover_text):
                if keyword not in replace_parenthesis(cover_text):
                    return elements
        return []

    def join_page_text(self, page: int):
        elements = self.reader.find_elements_by_page(page)
        cover_text = ""
        for element in elements:
            if is_table_elt(element):
                cover_text += "".join(
                    cell["text"] for item in group_table_cells_by_row(element).values() for cell in item
                )
            elif is_paragraph_elt(element):
                cover_text += element["text"]
        return cover_text, elements
