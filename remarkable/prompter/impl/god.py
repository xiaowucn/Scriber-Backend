import json

from remarkable.common.schema import Schema, attribute_id
from remarkable.pdfinsight.reader import PdfinsightReader


class GodAnswerPrompter:
    def __init__(self, schema_id):
        self.files = []
        self.attributes = {}
        self.schema_id = schema_id
        self.timestamp = 0

    @staticmethod
    def _clear_path_index(path):
        return [p.split(":")[0] for p in path]

    def find_items_from_known_answer(self, answer, key_path):
        items = []
        for item in answer.get("userAnswer", {}).get("items", []):
            item_path = self._clear_path_index(json.loads(item["key"]))
            if item_path == key_path:
                items.append(item)
        return items

    def prompt_all(self, pdfinsight_path, **kwargs):
        answer = kwargs.get("known_answer")
        if not answer:
            return {}
        mold = kwargs.get("mold_data")
        if not mold:
            raise Exception("mold_data is needed")
        reader = PdfinsightReader(pdfinsight_path, data=kwargs.get("pdfinsight_data"))

        res = {}
        schema = Schema(mold)
        for key_path in schema.iter_schema_attr():
            items = []
            aid = attribute_id(key_path)
            known_answer_items = self.find_items_from_known_answer(answer, key_path)
            for item in known_answer_items:
                for data in item["data"]:
                    for box in data["boxes"]:
                        page = box["page"]
                        outline = (
                            box["box"]["box_left"],
                            box["box"]["box_top"],
                            box["box"]["box_right"],
                            box["box"]["box_bottom"],
                        )
                        for etype, element in reader.find_elements_by_outline(page, outline):
                            if element["index"] not in [item[1]["index"] for item in items]:
                                items.append((1, element, [], etype))
            res[aid] = items
        return res
