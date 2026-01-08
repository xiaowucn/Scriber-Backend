import json
import logging
import re
from json import JSONDecodeError
from typing import Literal, Self

from openai import AsyncOpenAI, OpenAI
from pydantic import BaseModel
from typing_extensions import Iterator

from remarkable.config import get_config
from remarkable.service.embedding import TOKEN_ENCODER

logger = logging.getLogger(__name__)

P_MD_PREFIX = re.compile(r"^.{,50}?```json\s*|\s*```$", re.S)
P_JSON_BOUNDARY = re.compile(r"\{.*}|\[.*]", re.DOTALL)
P_JSON_BOUNDARY_MINI = re.compile(r"\{.*?}|\[.*?]", re.DOTALL)


class OpenAIClient:
    def __init__(self):
        self.api_key = get_config("ai.openai.api_key")
        assert self.api_key, "OpenAI API key or PAI proxy URL must be provided"
        self._client = None

    @property
    def client(self) -> OpenAI:
        if not self._client:
            self._client = OpenAI(api_key=self.api_key, base_url=get_config("ai.openai.base_url"))
        return self._client

    def send_message(
        self,
        messages: list[dict[Literal["role", "content"], str]],
        options: dict | None = None,
        response_format=None,
    ) -> str:
        options = options or {}
        if response_format:
            response = self.client.beta.chat.completions.parse(
                model=options.get("model") or get_config("ai.openai.model"),
                messages=messages,
                temperature=options.get("temperature")
                or get_config("ai.openai.temperature"),  # o3-mini is not support temperature
                timeout=options.get("timeout") or get_config("ai.openai.timeout") or 10,
                response_format=response_format,
            )
            return response.choices[0].message

        response = self.client.chat.completions.create(
            model=options.get("model") or get_config("ai.openai.model"),
            messages=messages,
            temperature=options.get("temperature") or get_config("ai.openai.temperature"),
            stream=True,
            timeout=options.get("timeout") or get_config("ai.openai.timeout") or 10,
            max_tokens=options.get("max_tokens") or get_config("ai.openai.max_tokens"),
        )
        texts = []
        for chunk in response:
            if chunk.choices and (content := chunk.choices[0].delta.content):
                texts.append(content)
        return "".join(texts).strip()

    def get_embddings(self, texts: list[str], **options) -> Iterator[list[float]]:
        for group in TOKEN_ENCODER.split_by_length(texts):
            response = self.client.embeddings.create(
                input=group,
                model=options.get("embedding_model") or get_config("ai.openai.embedding_model"),
            )
            for item in response.data:
                yield item.embedding


class AsyncOpenAIClient:
    def __init__(self):
        self.api_key = get_config("ai.openai.api_key")
        assert self.api_key, "OpenAI API key or PAI proxy URL must be provided"
        self._async_client = None

    @property
    def async_client(self) -> AsyncOpenAI:
        if not self._async_client:
            self._async_client = AsyncOpenAI(api_key=self.api_key, base_url=get_config("ai.openai.base_url"))
        return self._async_client

    async def send_message(
        self,
        messages: list[dict[Literal["role", "content"], str]],
        options: dict | None = None,
        response_format=None,
        response_format_type: str = "text",
    ):
        options = options or {}
        if response_format:
            response = await self.async_client.beta.chat.completions.parse(
                model=options.get("model") or get_config("ai.openai.model"),
                messages=messages,
                temperature=options.get("temperature") or get_config("ai.openai.temperature", 0),
                timeout=options.get("timeout") or get_config("ai.openai.timeout") or 30,
                response_format=response_format,
            )
            return response.choices[0].message

        stream = response_format_type == "text"
        response = await self.async_client.chat.completions.create(
            model=options.get("model") or get_config("ai.openai.model"),
            messages=messages,
            temperature=options.get("temperature")
            or get_config("ai.openai.temperature", 0),  # o3-mini is not support temperature
            response_format={"type": response_format_type},
            stream=stream,
            timeout=options.get("timeout") or get_config("ai.openai.timeout") or 30,
            max_tokens=options.get("max_tokens") or get_config("ai.openai.max_tokens"),
        )
        if not stream:
            return P_MD_PREFIX.sub("", response.choices[0].message.content)

        texts = []
        async for chunk in response:
            if chunk.choices and (content := chunk.choices[0].delta.content):
                texts.append(content)

        return "".join(texts).strip()

    async def get_embeddings(self, texts: list[str], **options) -> list[list[float]]:
        """异步获取文本嵌入向量"""
        async with self.async_client:
            response = await self.async_client.embeddings.create(
                input=texts,
                model=options.get("embedding_model") or get_config("ai.openai.embedding_model"),
            )
            return [item.embedding for item in response.data]


def safe_load(answer: str, default: list[dict] = ()) -> list[dict]:
    try:
        return json.loads(answer)
    except JSONDecodeError:
        try:
            return json.loads(P_MD_PREFIX.sub("", answer))
        except JSONDecodeError:
            match = P_JSON_BOUNDARY.search(answer.strip())
            if match:
                try:
                    return json.loads(match.group())
                except JSONDecodeError:
                    match = P_JSON_BOUNDARY_MINI.search(answer.strip())
                    if match:
                        try:
                            return json.loads(match.group())
                        except JSONDecodeError:
                            return default
                    return default
            return default


class LLMSchema(BaseModel):
    @classmethod
    def from_llm(cls, json_str: str) -> Self:
        return cls.model_validate(safe_load(json_str))
