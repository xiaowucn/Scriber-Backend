import json
import logging

from remarkable.predictor.models.chatgpt import ChatGPT
from remarkable.predictor.schema_answer import CharResult

logger = logging.getLogger(__name__)


class ScopeInvestmentGPT(ChatGPT):
    def parse_gpt_result(self, element: dict, gpt_res: str):
        results = []
        data = json.loads(gpt_res)
        for name in data:
            dst_chars = self.get_chars(element["text"], name, element["chars"])
            if name != "".join([i["text"] for i in dst_chars]):
                logger.warning(f"{name=}, {''.join([i['text'] for i in dst_chars])}")
            result = self.create_result([CharResult(element, dst_chars)], column=self.schema.name)
            results.append(result)
        return results
