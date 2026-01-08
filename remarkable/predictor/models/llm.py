import logging
from functools import cached_property
from typing import Generic, Iterator, Literal, Type

from pdfparser.utils.autodoc.itable_util import deepcopy
from pydantic import Field, create_model

from remarkable.common.util import T, clean_txt
from remarkable.db import pw_db
from remarkable.predictor.eltype import ElementClassifier
from remarkable.predictor.models.base_model import BaseModel
from remarkable.predictor.schema_answer import (
    LLMTableResult,
    ParagraphResult,
    PredictorResult,
)
from remarkable.pw_models.embedding import Embedding
from remarkable.service.chatgpt import LLMSchema, OpenAIClient
from remarkable.service.embedding import Document

logger = logging.getLogger(__name__)


class LLMAnswerSchema(LLMSchema, Generic[T]):
    answer: T = Field(description="提取的答案, 如果提取不到答案, 请返回空字符串")
    reason: str = Field(default="")


DEFAULT_SYSTEM_PROMPT = """
你是一个有用的文档信息提取智能助手
我会给你发送一段文本, 你需要从中提取出 `{field}` 对应的答案。

如果answer的类型是列表, 那么`{field}`需要提取多组答案, 每一组答案放在一个列表中, 每个组会有多个字段需要提取, 具体提取的内容需要按照answer的schema来确定

严格按照定义的pydantic schema来返回答案, 不要返回其他内容。

{schema}
    """


class LLModel(BaseModel):
    def __init__(self, options, schema, predictor=None):
        super().__init__(options, schema, predictor=predictor)
        self.prompt = self.get_config("prompt")
        self.system_prompt = self.get_config("system_prompt") or DEFAULT_SYSTEM_PROMPT.format(
            field=self.field, schema=self.model.model_json_schema()
        )
        self.assistant = self.get_config("assistant", [])  #

    @cached_property
    def llm_client(self):
        return OpenAIClient()

    @cached_property
    def field(self):
        if len(self.schema.path) > 2:
            return self.schema.parent.name
        return self.schema.name

    @cached_property
    def model(self) -> Type[LLMAnswerSchema]:  # noqa: UP006
        if len(self.schema.path) <= 2:
            return LLMAnswerSchema[str]
        models = []
        for i, name in enumerate(self.schema.parent.orders):
            models.append(
                create_model(
                    f"AnswerModel{i}",
                    name=(Literal[name], Field(default=name, description="字段名称, 无需提取")),
                    answer=(str, Field(description=f"需要提取{self.schema.parent.name}下的{name}", min_length=1)),
                )
            )
        return LLMAnswerSchema[list[list[*models]]]

    def train(self, dataset, **kwargs):
        pass

    def extract_answer(self, text: str) -> LLMAnswerSchema:
        messages = [{"role": "system", "content": f"{self.system_prompt}\n{self.prompt}"}]
        messages.extend(self.assistant)
        messages.append({"role": "user", "content": text})
        answer = self.model.from_llm(self.llm_client.send_message(messages))
        if not answer.answer:
            raise ValueError(f"No answer found, reason={answer.reason}")
        return answer

    def get_next_element(self, elements: list[dict]) -> Iterator[dict]:
        """优先用初步定位的答案, 没有的话用向量搜索的答案"""
        if elements:
            for element in elements:
                yield element
        else:
            with pw_db.allow_sync():
                records = list(
                    Embedding.semantic_search_query(
                        self.predictor.prophet.metadata["fid"], self.field, limit=20
                    ).execute()
                )

            for record in records:
                _, element = self.pdfinsight.find_element_by_index(record["index"])
                yield element

    def predict_schema_answer(self, elements) -> list[dict[str, list[PredictorResult]]]:
        result = []
        for element in self.get_next_element(elements):
            if ElementClassifier.like_paragraph(element):
                clean_text = clean_txt(element.get("text"))
                predict_result = ParagraphResult(element, element["chars"])
            elif ElementClassifier.is_table(element):
                clean_text = Document.get_table_markdown(element, remove_num=False)
                predict_result = LLMTableResult(element, [])
            else:
                logger.error(f"Not supported element class: {element['class']}")
                continue
            try:
                answer = self.extract_answer(clean_text)
                if isinstance(answer.answer, list):
                    res = []
                    for records in answer.answer:
                        ans = {}
                        for record in records:
                            if ElementClassifier.is_table(element):
                                predict_result = deepcopy(predict_result)
                                predict_result.text = record.answer
                            ans[record.name] = [
                                self.create_result(
                                    element_results=[predict_result], text=record.answer, column=record.name
                                )
                            ]
                        res.append(ans)
                else:
                    if ElementClassifier.is_table(element):
                        predict_result.text = answer.answer
                    res = [self.create_result(element_results=[predict_result], text=answer.answer)]
            except Exception as e:
                logger.exception(e)
                res = []
            result.extend(res)
            if result and not self.multi_elements:
                break
        return result
