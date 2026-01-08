import re

from remarkable.common.pattern import PatternCollection
from remarkable.common.util import index_in_space_string
from remarkable.pdfinsight.text_util import clear_syl_title
from remarkable.predictor.models.auto import AutoModel
from remarkable.predictor.schema_answer import PredictorResult

P_SEP = re.compile(r"\s*?[:：]\s*?")


def fake_kv_elt(elements):
    """将类似kv的连续段落转换成表格"""
    if len(elements) < 2 or any(len(P_SEP.split(e["text"])) > 2 for e in elements[1:]):
        return None
    element = {
        "class": "TABLE",
        "type": "TABLE",
        "page": elements[0]["page"],
        "index": elements[1]["index"],
        "merged": [],
        "title": elements[0]["text"],
        "cells": {},
        "outline": [*elements[1]["outline"][:2], *elements[-1]["outline"][2:]],
        "__indexes": set(),
    }
    for idx, elt in enumerate(elements[1:]):
        if match := P_SEP.search(elt["text"]):
            _, to_idx = index_in_space_string(elt["text"], match.span())
            element["cells"][f"{idx}_0"] = {
                "text": elt["text"][:to_idx],
                "chars": elt["chars"][:to_idx],
                "page": elt["page"],
                "box": [],
                "docx_meta": {},
                "left": 0,
                "right": 1,
                "top": idx,
                "bottom": idx + 1,
                "row": idx,
                "col": 0,
            }
            element["cells"][f"{idx}_1"] = {
                "text": elt["text"][to_idx:],
                "chars": elt["chars"][to_idx:],
                "page": elt["page"],
                "box": [],
                "docx_meta": {},
                "left": 1,
                "right": 2,
                "top": idx,
                "bottom": idx + 1,
                "row": idx,
                "col": 1,
            }
        else:
            element["cells"][f"{idx}_0"] = {
                "text": elt["text"],
                "chars": elt["chars"],
                "page": elt["page"],
                "box": [],
                "docx_meta": {},
                "left": 0,
                "right": 2,
                "top": idx,
                "bottom": idx + 1,
                "row": idx,
                "col": 0,
                "dummy": True,
            }
            element["cells"][f"{idx}_1"] = {
                "text": elt["text"],
                "chars": elt["chars"],
                "page": elt["page"],
                "box": [],
                "docx_meta": {},
                "left": 0,
                "right": 2,
                "top": idx,
                "bottom": idx + 1,
                "row": idx,
                "col": 1,
            }
        element["__indexes"].add(elt["index"])
    return element


class FakeKV(AutoModel):
    @property
    def closest_syllabus_pattern(self):
        return PatternCollection(self.get_config("closest_syllabus_pattern"))

    def predict_schema_answer(self, elements) -> list[dict[str, list[PredictorResult]]]:
        if not self.closest_syllabus_pattern:
            return super().predict_schema_answer(elements)
        matched_closest_syllabus_pattern = False
        new_elements = []
        indexes = set()
        for elt in elements:
            syllables = self.pdfinsight_syllabus.find_by_elt_index(elt["index"])
            if syllables and self.closest_syllabus_pattern.nexts(syllables[-1]["title"]):
                if (fake_elt := fake_kv_elt(self.pdfinsight.get_elements_by_syllabus(syllables[-1]))) and elt[
                    "index"
                ] not in indexes:
                    new_elements.append(fake_elt)
                    indexes.update(fake_elt.pop("__indexes"))
                    matched_closest_syllabus_pattern = True
            if elt["index"] not in indexes:
                new_elements.append(elt)

        if not matched_closest_syllabus_pattern:
            for pattern in self.closest_syllabus_pattern.patterns:
                for syllabuse in self.pdfinsight.find_sylls_by_pattern([pattern], clean_func=clear_syl_title):
                    if fake_elt := fake_kv_elt(self.pdfinsight.get_elements_by_syllabus(syllabuse)):
                        new_elements.append(fake_elt)
                        break

        return super().predict_schema_answer(new_elements)
