import json
import logging

from remarkable.common.util import clean_txt
from remarkable.predictor.models.chatgpt import ChatGPT
from remarkable.predictor.schema_answer import CharResult

logger = logging.getLogger(__name__)


class DraftsManGPT(ChatGPT):
    def parse_gpt_result(self, element: dict, gpt_res: str):
        results = []
        data = json.loads(gpt_res)
        for name, span in data.items():
            dst_chars = self.get_chars(element["text"], name, element["chars"], span)
            if name != "".join([i["text"] for i in dst_chars]):
                logger.warning(f"{name=}, {''.join([i['text'] for i in dst_chars])}")
            result = self.create_result([CharResult(element, dst_chars)], column=self.schema.name)
            results.append(result)
        return results


class DraftsCompanyGPT(ChatGPT):
    def parse_gpt_result(self, element: dict, gpt_res: str):
        results = []
        clean_text = clean_txt(element["text"])
        data = json.loads(gpt_res)
        for unit in data:
            start = clean_text.index(unit)
            end = start + len(unit)
            dst_chars = self.get_chars(element["text"], unit, element["chars"], (start, end))
            result = self.create_result([CharResult(element, dst_chars)], column=self.schema.name)
            results.append(result)
        return results
