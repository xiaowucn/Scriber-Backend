from __future__ import annotations

import sys
from typing import Any, Match, Protocol, TypeVar, runtime_checkable

T = TypeVar("T", covariant=True)


@runtime_checkable
class SearchPatternLike(Protocol):
    def search(self, string: str, pos: int = 0, endpos: int = sys.maxsize) -> Any: ...


@runtime_checkable
class CompleteSearchPattern(Protocol):
    def search(self, string: str, pos: int = 0, endpos: int = sys.maxsize) -> Match | None: ...
