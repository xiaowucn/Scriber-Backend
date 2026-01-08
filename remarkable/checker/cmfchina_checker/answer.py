import json
import re
from collections import defaultdict
from functools import cached_property

from remarkable.checker.answers import Answer, AnswerManager
from remarkable.common.util import get_key_path
from remarkable.plugins.cgs.common.utils import get_chapter_info_by_outline

P_INDEX = re.compile(r":\d+")


class CmfChinaAnswer(Answer):
    @property
    def cells(self):
        if self.is_answer:
            cells = []
            for data in self.data_items:
                if data.get("cell"):
                    cells.append({"cell": data.get("cell"), "sheet_name": data.get("sheet_name")})
            return cells
        return []

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
            "cells": self.cells if self.cells else [],
            "path": self.master_key,
        }

    @property
    def master_key(self):
        return self.answer.get("master_key") or ""


class CmfChinaAnswerManager(AnswerManager):
    def get(self, key):
        res = []
        for answer in self.get_answer_by_key(key) or []:
            res.append(CmfChinaAnswer(answer=answer, reader=self.reader, name=key))
        return res

    @cached_property
    def mapping(self):
        mapping = defaultdict(list)
        if not self.question:
            return mapping

        if isinstance(self.question, dict):
            mapping = self.question
        else:
            for item in self.answer_items:
                mapping[get_key_path(item["key"])].append(item)

        return mapping

    def build_schema_results(self, fields: list[str]):
        schema_results = []
        for name in fields:
            fix_name = P_INDEX.sub("", name)
            search_result = P_INDEX.search(name)
            for answer in self.get(fix_name):
                if not search_result or (search_result and "-".join(json.loads(answer.master_key)[1:]) == name):
                    if answer and answer.value:
                        schema_results.append({"name": fix_name, "matched": True, **answer.first_result})
                    else:
                        schema_results.append({"name": fix_name, "matched": False})
        return schema_results
