from typing import NamedTuple

import attr


class UserAnswer(NamedTuple):
    uid: int
    name: str
    data: dict


@attr.s
class AnswerGroup:
    items: list = attr.ib(default=attr.Factory(list))
    manual: bool = attr.ib(default=False)
