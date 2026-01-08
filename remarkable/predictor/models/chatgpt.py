import logging

from remarkable.common.util import clean_txt
from remarkable.predictor.eltype import ElementClassifier
from remarkable.predictor.models.base_model import BaseModel
from remarkable.predictor.schema_answer import PredictorResult
from remarkable.service.chatgpt import OpenAIClient

logger = logging.getLogger(__name__)

DEFAULT_SYSTEM_PROMPT = (
    # 'You are a helpful AI document extraction assistant. '
    # 'The following are the relevant article content fragments found from the article.'
    # 'The relevance is sorted from high to low. '
    # 'You can only extract answer according to the following content'
    "你是一个有用的AI文档提取小助手"
    "我会给你发送一段话 你需要从中提取出对应的答案，我会告诉你这段话和需要返回的格式。下面是一个例子"
)

# todo
# 1. 缓存 chatgpt 的结果
# 2. 多段答案时组织文本 初步定位  章节元素块 页码元素块


class ChatGPT(BaseModel):
    base_all_elements = True

    def __init__(self, options, schema, predictor=None):
        super().__init__(options, schema, predictor=predictor)
        self.prompt = self.get_config("prompt")
        assert self.prompt, "prompt is required"
        self.system_prompt = self.get_config("system_prompt")
        self.assistant = self.get_config("assistant", [])  #

    def train(self, dataset, **kwargs):
        pass

    def extract_answer(self, text):
        system_prompt = self.system_prompt or DEFAULT_SYSTEM_PROMPT
        messages = [{"role": "system", "content": f"{system_prompt}\n{self.prompt}"}]
        messages.extend(self.assistant)
        messages.append({"role": "user", "content": text})
        openai_client = OpenAIClient()
        try:
            gpt_res = openai_client.send_message(messages)
        except Exception as e:
            logger.exception(e)
            gpt_res = ""
        return gpt_res

    def predict_schema_answer(self, elements) -> list[dict[str, list[PredictorResult]]]:
        result = []
        for element in elements:
            if ElementClassifier.like_paragraph(element):
                clean_text = clean_txt(element.get("text"))
            elif ElementClassifier.is_table(element):
                continue
                # todo process table
                # clean_text = PdfinsightTable(element).markdown
            else:
                logger.error(f"Not supported element class: {element['class']}")
                continue
            gpt_res = self.extract_answer(clean_text)
            try:
                res = self.parse_gpt_result(element, gpt_res)
            except Exception as e:
                logger.exception(e)
                res = []
            result.extend(res)
            if result and not self.multi_elements:
                break
        return result

    def parse_gpt_result(self, element, gpt_res):
        raise NotImplementedError
