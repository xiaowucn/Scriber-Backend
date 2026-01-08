import json

from remarkable.converter import BaseConverter
from remarkable.fintable.schema import FintableColumnConfig


def keypath_str(keypath: list[tuple[str, int]]) -> str:
    return json.dumps([f"{p[0]}:{p[1]}" for p in keypath], ensure_ascii=False)


class FinanceTableConverter(BaseConverter):
    def __init__(self, answer, fintable_schema) -> None:
        super(FinanceTableConverter, self).__init__(answer)
        self.config = FintableColumnConfig()
        self.fintable_schema = fintable_schema

    @property
    def all_schema_orders(self):
        all_schema_words = []
        for i in self.fintable_schema["schemas"]:
            all_schema_words.extend(i["orders"])
        return all_schema_words
