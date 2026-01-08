import logging
from dataclasses import dataclass
from typing import ClassVar, Type

from typing_extensions import Self

from remarkable.config import get_config
from remarkable.models.new_file import NewFile

__all__ = ("InsightFinishHook", "PredictFinishHook", "InsightStartHook")

from remarkable.pw_models.question import QuestionWithFK

logger = logging.getLogger(__name__)


class _Meta(type):
    name: str
    __impl__: type

    def __new__(mcs, name, bases, attrs):
        cls = super().__new__(mcs, name, bases, attrs)

        if hasattr(cls, "name") and cls.name == get_config("client.name"):
            if hasattr(cls, "__impl__"):
                raise RuntimeError(f"{cls.__name__} has already been registered")
            if bases := cls.__bases__:
                bases[0].__impl__ = cls  # type: ignore

        return cls


@dataclass
class InsightStartHook(metaclass=_Meta):
    __impl__: ClassVar[Type[Self]]  # noqa: UP006

    file: NewFile

    async def __call__(self):
        if not hasattr(self, "__impl__"):
            logger.info("no insight start hook implemented")
            return
        logger.info("begin to invoke hook when insight start using %s", self.__impl__.__name__)
        await self.__impl__(self.file).__call__()
        logger.info("finish to invoke hook when insight start using %s", self.__impl__.__name__)


@dataclass
class InsightFinishHook(metaclass=_Meta):
    __impl__: ClassVar[Type[Self]]  # noqa: UP006

    file: NewFile

    async def __call__(self):
        if not hasattr(self, "__impl__"):
            logger.info("no insight finish hook implemented")
            return
        logger.info("begin to invoke hook when insight finished using %s", self.__impl__.__name__)
        await self.__impl__(self.file).__call__()
        logger.info("finish to invoke hook when insight finished using %s", self.__impl__.__name__)


@dataclass
class PredictFinishHook(metaclass=_Meta):
    __impl__: ClassVar[Type[Self]]  # noqa: UP006

    question: QuestionWithFK

    async def __call__(self):
        if not hasattr(self, "__impl__"):
            logger.info("no predict finish hook implemented")
            return
        logger.info("begin to invoke hook when predict answer finished for %s", self.__impl__.name)
        await self.__impl__(self.question).__call__()
        logger.info("finish to invoke hook when predict answer finished for %s", self.__impl__.name)
