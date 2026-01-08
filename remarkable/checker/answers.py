import re
from collections import defaultdict
from functools import cached_property
from re import Pattern

import attrs

from remarkable.common.pattern import PatternCollection
from remarkable.common.schema import Schema
from remarkable.common.util import clean_txt, get_key_path
from remarkable.pdfinsight.reader import PdfinsightReader
from remarkable.plugins.cgs.common.fund_classification import (
    DisclosureEnum,
    RelationEnum,
)
from remarkable.plugins.cgs.common.template_condition import TemplateRelation
from remarkable.plugins.cgs.common.utils import (
    get_chapter_info_by_outline,
    get_chapter_title_text,
    get_xpath_by_outline,
)
from remarkable.pw_models.model import NewMold
from remarkable.pw_models.question import NewQuestion

ANSWER_KEY_CONVERT_MAPPING = {
    "投资比例": "投资比例及限制",
    "投资限制": "投资比例及限制",
}

P_PEER_KEY = re.compile(r',[^:]+:0"]$')


@attrs.define
class Answer:
    answer = attrs.field()
    name = attrs.field()
    reader = attrs.field()

    def is_manual(self):
        return self.answer.get("manual")

    @property
    def is_answer(self):
        return isinstance(self.answer, dict) and "schema" in self.answer

    @property
    def data_items(self):
        if self.is_answer:
            return self.answer.get("data") or []
        return []

    @property
    def value(self):
        if not self.answer:
            return None
        if self.answer.get("value"):
            value = self.answer["value"]
            if isinstance(value, (list, tuple)):
                value = ",".join(self.answer["value"])
            return value

        return self.data_text

    @property
    def data_text(self):
        texts = []
        for data in self.data_items:
            texts.append(data.get("text") or "".join([box["text"] for box in data.get("boxes", [])]))
        return "\n".join(texts)

    @property
    def page(self):
        return min(self.outlines.keys(), key=int, default=0)

    @property
    def outlines(self):
        if self.is_answer:
            mapping = defaultdict(list)

            for data in self.data_items:
                boxes = data.get("boxes")
                if boxes:
                    for item in boxes:
                        box = item["box"]
                        mapping[str(item.get("page"))].append(
                            [box["box_left"], box["box_top"], box["box_right"], box["box_bottom"]]
                        )
            return mapping
        return {}

    @property
    def xpath(self):
        page = self.page
        if self.is_answer and self.reader and self.outlines and page in self.outlines:
            return get_xpath_by_outline(self.reader, page, self.outlines[page][0])
        return None

    @property
    def first_result(self):
        page = self.page
        outlines = self.outlines or None
        return {
            "text": self.value,
            "page": page,
            "outlines": outlines,
            "xpath": self.xpath,
            "chapters": get_chapter_info_by_outline(self.reader, outlines),
        }

    @property
    def chapter_title(self):
        result = self.first_result
        if result and result["chapters"]:
            return get_chapter_title_text(result["chapters"])
        return None

    def get_related_paragraphs(self):
        outlines = self.outlines
        page = self.page
        if outlines:
            return [{"text": self.value, "page": page, "chars": [], "index": 0, "outlines": self.outlines}]
        return []


@attrs.define(slots=False)
class AnswerManager:
    question: NewQuestion | dict
    reader: PdfinsightReader = attrs.field(default=None)
    mold: NewMold = attrs.field(default=None)
    answer: dict = attrs.field(factory=dict)

    @cached_property
    def answer_items(self):
        if isinstance(self.question, (NewQuestion)):
            return self.answer.get("userAnswer", {}).get("items", [])
        return []

    @cached_property
    def mapping(self):
        mapping = {}
        if not self.question:
            return mapping

        if isinstance(self.question, dict):
            mapping = self.question
        else:
            for item in self.answer_items:
                mapping[get_key_path(item["key"])] = item

        return mapping

    def get_key(self, key):
        key = origin_key = key.strip()
        if key in self.mapping:
            return key
        # https://gitpd.paodingai.com/cheftin/docs_scriber/-/issues/2012#note_334246
        for pr_key, convert_val in ANSWER_KEY_CONVERT_MAPPING.items():
            if str(key).startswith(f"{pr_key}-") or key == pr_key:
                key = f"{convert_val}{key[len(pr_key) :]}"
                break
        if key in self.mapping:
            return key
        return origin_key

    def get_answer_by_key(self, key):
        key = self.get_key(key)
        if key in self.mapping:
            return self.mapping[key]
        return None

    def get(self, key):
        return Answer(answer=self.get_answer_by_key(key), reader=self.reader, name=key)

    def get_multi(self, key):
        if isinstance(self.question, dict):
            return []
        convert_key = self.get_key(key)
        res = []
        for item in self.answer_items:
            if get_key_path(item["key"]) == convert_key:
                res.append(Answer(answer=item, reader=self.reader, name=key))
        return res

    def get_peers(self, answer: Answer) -> list[Answer]:
        """
        拿到同级其他节点的答案
        :param answer:
        :return:
        """
        res = []
        if not answer:
            return res

        peer_key = P_PEER_KEY.sub("", answer.answer["key"])
        for item in self.answer_items:
            if item["key"].startswith(peer_key) and item["key"] != answer.answer["key"]:
                res.append(Answer(answer=item, reader=self.reader, name=get_key_path(item["key"])))
        return res

    @cached_property
    def schema_items(self):
        return {"-".join(item[0][1:]) for item in Schema(self.answer["schema"]).iter_schema_attr(True)}

    def is_schema_field(self, name):
        if self.schema_items and name not in self.schema_items:
            return False
        return True

    @cached_property
    def classification_mapping(self):
        raise NotImplementedError

    def check_disclosure_chapter(self, chapter_patterns: list[Pattern], child_patterns: PatternCollection):
        """
        是否披露指定章节
        """
        for chapter in self.reader.find_sylls_by_pattern(chapter_patterns):
            for index in range(*chapter["range"]):
                elt_type, element = self.reader.find_element_by_index(index)
                if (
                    elt_type == "PARAGRAPH"
                    and not element.get("fragment")
                    and child_patterns.nexts(clean_txt(element["text"]))
                ):
                    return [DisclosureEnum.YES]
        return [DisclosureEnum.NO]

    def verify_condition(self, template_conditions: list[TemplateRelation] | None):
        if not template_conditions:
            return True

        # 多个conditions需全部满足条件
        for condition in template_conditions:
            default_values = self.classification_mapping.get(condition.name, [])
            # 同一个条件内的多个值满足一个即可
            for val_condition in condition.values:
                attr_values = (
                    val_condition.name and self.classification_mapping.get(val_condition.name, [])
                ) or default_values
                if val_condition.relation == RelationEnum.EQUAL and val_condition.value in attr_values:
                    break
                if val_condition.relation == RelationEnum.UNEQUAL and val_condition.value not in attr_values:
                    break
            else:
                return False
        return True

    def build_schema_results(self, fields: list[str]):
        schema_results = []
        for name in fields:
            answer = self.get(name)
            if answer and answer.value:
                schema_results.append({"name": name, "matched": True, **answer.first_result})
            else:
                schema_results.append({"name": name, "matched": False})
        return schema_results
