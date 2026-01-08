# CYC: skip-file
import hashlib
import logging

from remarkable.answer.node import AnswerItem
from remarkable.common.util import compact_dumps
from remarkable.converter import BaseConverter
from remarkable.predictor.mold_schema import MoldSchema, SchemaItem
from remarkable.pw_models.question import QuestionWithFK

logger = logging.getLogger(__name__)


class CMBChinaConverter(BaseConverter):
    def __init__(self, question: QuestionWithFK):
        super().__init__(question.answer)
        self.schema = MoldSchema(question.mold.data)

    def func(self, item: AnswerItem):
        md5 = hashlib.md5(item["key"].encode()).hexdigest()
        if not item["data"]:
            value = None
        elif "zyt_value" in item["kwargs"]:
            value = item["kwargs"]["zyt_value"]
        else:
            value = item.plain_text

        if item.namepath.endswith("区间起始值") and value is None:
            value = "0"
        return {"value": value, "md5": md5}

    def match_schema(self, schemas: list[SchemaItem], answer: dict) -> list:
        items = []
        for schema in schemas:
            item = {"name": schema.name, "alias": schema.alias}
            checksum = hashlib.md5(compact_dumps([f"{p}:0" for p in schema.path]).encode()).hexdigest()
            if schema.children:
                item["md5"] = checksum
                detail = answer.get(schema.name) or ()
                item["items"] = [self.match_schema(schema.children, ans) for ans in detail]
            elif detail := answer.get(schema.name):
                item.update(detail)
            else:
                item["value"] = None
            if "md5" not in item:
                logger.error(f"{schema.path_key} md5 does not exist")
                item["md5"] = checksum
            item.setdefault("value", None)
            items.append(item)
        return items

    def convert(self, *args, item_handler=None):
        answer = self.answer_node.to_dict(item_handler=self.func)
        return {
            "name": self.schema.root_schema.name,
            "alias": self.schema.root_schema.alias,
            "items": self.match_schema(self.schema.root_schema.children, answer),
        }
