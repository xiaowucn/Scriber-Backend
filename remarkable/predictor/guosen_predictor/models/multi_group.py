import logging
import re
from collections import Counter, defaultdict
from dataclasses import dataclass, field
from functools import cached_property, total_ordering
from operator import attrgetter
from typing import Any, Generator, Iterable, NamedTuple, Self, Sequence

import numpy as np
from pydantic import BaseModel as PydanticModel
from pydantic import Field
from sklearn.cluster import KMeans
from sklearn.metrics import silhouette_score

from remarkable.common.util import clean_txt
from remarkable.predictor.models.base_model import BaseModel
from remarkable.predictor.schema_answer import CharResult

P_CODES = [
    re.compile(r"^(\d{5,6})(?:\.\w{2})?$"),
    re.compile(r"[融创](\d{5,6})"),
    re.compile(r"(\d{5,6})[)\]\[融目日]*$"),
    re.compile(r"(\d{5,6})回封$"),
]

P_NAME_BEFORE_CODE = re.compile(r"(.+)[(]\d{5,6}")

P_NUMBER = re.compile(r"^[+-]?(\d+|\d+\.\d*|\d*\.\d+)[%％]?$")
P_SERIAL = re.compile(r"^\d+$")
P_FLOAT_SUFFIX = re.compile(r"\.\d{1,2}$")
P_ALNUM_CODE = re.compile(r"^[A-Z\d]+$")
P_ALPHA = re.compile(r"^[A-Z]")

logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)


class _Box(NamedTuple):
    left: float
    top: float
    right: float
    bottom: float

    @property
    def height(self):
        return self.bottom - self.top

    def in_same_row(self, other: Self) -> bool:
        return self.bottom > other.top and self.top < other.bottom

    def in_same_col(self, other: Self) -> bool:
        return self.right > other.left and self.left < other.right

    def __bool__(self):
        return self.left > 0 or self.right > 0 or self.top > 0 or self.bottom > 0


class _Char(PydanticModel):
    text: str
    box: _Box = Field(alias="font_box")
    page: int = 0


class _TextBlock(PydanticModel):
    text: str
    chars: list[_Char]
    page: int = Field(default=0)
    index: int
    outline: _Box

    def model_post_init(self, __context: Any) -> None:
        self.text = clean_txt(self.text)
        self.chars = [char for char in self.chars if clean_txt(char.text)]

    def __hash__(self) -> int:
        return hash(self.outline)

    def __repr__(self):
        return self.text

    @cached_property
    def code(self) -> list[_Char]:  # 股票代码
        if P_FLOAT_SUFFIX.search(self.text):
            return []
        for p_code in P_CODES:
            if matched := p_code.search(self.text):
                return self.chars[matched.start(1) : matched.end(1)]
        return []

    def in_same_row(self, other: Self) -> bool:
        return self.outline.in_same_row(other.outline)

    def in_same_col(self, other: Self) -> bool:
        return self.outline.in_same_col(other.outline)


@total_ordering
@dataclass
class _Group:
    blocks: list[_TextBlock]
    _texts: list[str] = field(init=False, default_factory=list)

    def __post_init__(self):
        self.blocks = sorted(self.blocks, key=attrgetter("index"))

    @property
    def texts(self) -> list[str]:
        if not self._texts:
            self._texts = [block.text for block in self.blocks]
        return self._texts

    @texts.setter
    def texts(self, texts: list[str]):
        self._texts = texts

    @cached_property
    def codes(self) -> list[list[_Char]]:
        return [block.code for block in self.blocks if block.code]

    def __eq__(self, other):
        return self.blocks[0].index == other.blocks[0].index

    def __lt__(self, other):
        return self.blocks[0].index < other.blocks[0].index

    def __len__(self):
        return len(self.blocks)

    def __bool__(self):
        return bool(self.blocks)

    def __repr__(self):
        return " ".join(self.texts)


@dataclass
class _GroupCursor:
    elem_by_index: dict[int, _TextBlock]

    def __iter__(self) -> Generator[_Group, None, None]:
        # 根据序号所在文本块是否同一列来去除序号
        serial_blocks = [block for block in self.elem_by_index.values() if block.text in ("序号", "序")]
        remove_block_indices = set()
        serial_count = 0
        if serial_blocks:
            for block in self.elem_by_index.values():
                # 去掉和序号同一行, 左边的文本块
                if (
                    block.outline.bottom < serial_blocks[0].outline.top
                    or (block.outline.in_same_row(serial_blocks[0].outline))
                    or (block.outline.right < serial_blocks[0].outline.left)
                ):
                    remove_block_indices.add(block.index)
                # 去掉和序号同一列的文本块, 并计数
                elif block.in_same_col(serial_blocks[0]):
                    remove_block_indices.add(block.index)
                    serial_count += 1
            for index in remove_block_indices:
                self.elem_by_index.pop(index)

        code_count = sum(bool(elem.code or P_ALNUM_CODE.search(elem.text)) for elem in self.elem_by_index.values())
        # 按照股票代码的数量加一个数, 因为截图中可能会有列名之类的

        asset_count = sum("资产情况" in elem.text for elem in self.elem_by_index.values())
        offset = 10
        if asset_count > 2:
            offset = code_count * 2 + 3

        min_k = 2
        if code_count > 0:  # 如果有股票代码, 则根据股票代码的数量算出来最大分组数
            max_k = code_count + offset
        elif serial_count:  # 如果有序号, 则根据序号的数量算出来最大分组数
            min_k = serial_count
            max_k = serial_count + 2
        else:
            max_k = len(self.elem_by_index)
        groups = list(_XMeansClassfier(self.elem_by_index.values(), min_k=min_k, max_k=max_k))

        # 如果第一列是序号的话, 根据序号是否连续来去掉序号的文本块
        serials = []
        for i, group in enumerate(reversed(groups)):
            if not (matched := P_SERIAL.search(group.texts[0])):
                if i < 2:  # 可能截图底部会有菜单之类的文本影响
                    continue
                else:
                    break
            serial = int(matched.group())
            try:
                prev_group = groups[-(i + 2)]
                if matched := P_SERIAL.search(prev_group.texts[0]):
                    prev_serial = matched.group()
                else:
                    raise IndexError
            except IndexError:
                if serials and serial + 1 == serials[-1]:
                    group.blocks = group.blocks[1:]
                    group.texts = []
                break
            serials.append(serial)
            if len(prev_serial) > 4:  # 避免过滤股票代码格式的数字
                break
            if int(prev_serial) + 1 == serial:
                group.blocks = group.blocks[1:]
                group.texts = []
            else:
                break

        for strategy_factory in [_DivideInHalf, _MergeToPrev, _MergeByAsset]:
            strategy: _Strategy = strategy_factory(groups)  # type: ignore
            groups = list(strategy)

        for group in groups:
            if group.blocks and len(group.blocks[0].text) == 1 and group.blocks[0].text.isdigit():
                group.blocks = group.blocks[1:]
                group.texts = []
            if not group.blocks:
                continue
            yield group


@dataclass
class _Strategy:
    groups: list[_Group]

    def _merge(self) -> Generator[_Group, None, None]:
        raise NotImplementedError

    def __iter__(self):
        yield from sorted(self._merge())


@dataclass
class _DivideInHalf(_Strategy):
    """如果只有两种长度的分组, 且短的是长的一半, 则将长的分组拆分为两个"""

    def _merge(self):
        groups_by_len = defaultdict(list)
        for group in self.groups:
            groups_by_len[len(group.blocks)].append(group)

        if len(groups_by_len) == 2:
            (min_len, short_groups), (max_len, long_groups) = sorted(groups_by_len.items())
            if min_len * 2 != max_len:
                yield from self.groups
                return
            yield from short_groups
            for long_group in long_groups:
                yield _Group(long_group.blocks[:min_len])
                yield _Group(long_group.blocks[min_len:])
        else:
            yield from self.groups


@dataclass
class _MergeToPrev(_Strategy):
    """如果所有分组长度最大的值也是出现最频繁的值,则按照这个长度找到一个区间的开始和结束, 对区间内长度小于标准的进行前后合并"""

    def _merge(self):
        counter = Counter(len(group.blocks) for group in self.groups)
        len_ = counter.most_common()[0][0]
        if len_ != max(map(len, self.groups)):
            yield from self.groups
            return
        i = 0
        for i, group in enumerate(self.groups):  # noqa
            if len(group) == len_:
                break
        yield from self.groups[:i]
        groups = self.groups[i:]
        for cur_group, next_group in zip(groups, groups[1:] + [None]):
            if not cur_group.blocks:
                continue
            elif next_group is None:
                yield cur_group
            elif len(cur_group) + len([block for block in next_group.blocks if block.text != "创"]) == len_:
                yield _Group(cur_group.blocks + next_group.blocks)
                next_group.blocks = []
            else:
                yield cur_group


@dataclass
class _MergeByAsset(_Strategy):
    """根据资产情况分组, 每个分组都应该是股票代码一行,资产情况一行,数值指标一行"""

    def _merge(self):
        count = sum("资产情况" in group.texts for group in self.groups)
        if count < 2:
            yield from self.groups
            return

        for group in self.groups:
            if "资产情况" not in group.texts:
                continue
            if group.codes and group.texts.index("资产情况") < len(group.blocks) - 1:
                continue
            break
        else:
            yield from self.groups
            return
        # 先找到有股票代码的分组, 作为要处理的区间的开始
        i = 0
        for i, group in enumerate(self.groups):  # noqa
            if any(block.code for block in group.blocks):
                break
        yield from self.groups[:i]

        groups = self.groups[i:]
        i = 0
        while i < len(groups):
            first_group = groups[i]
            if not first_group:
                i += 1
                continue
            try:
                first_group_with_code = any(block.code for block in first_group.blocks)
                second_group = groups[i + 1]
                if first_group_with_code and "资产情况" == first_group.texts[-1]:
                    yield _Group(first_group.blocks + second_group.blocks)
                    second_group.blocks = []
                    i += 1
                    continue
                elif first_group_with_code and "资产情况" in first_group.texts:
                    yield first_group
                    i += 1
                    continue

                third_group = groups[i + 2]
                if first_group_with_code and "资产情况" in second_group.texts:
                    new_group = _Group(first_group.blocks + second_group.blocks)
                    second_group.blocks = []
                    if any(block.code for block in third_group.blocks):
                        i += 1
                        yield new_group
                        continue
                    new_group.blocks += third_group.blocks
                    third_group.blocks = []
                    yield new_group
                else:
                    yield first_group
            except IndexError:
                yield first_group
            i += 1


@dataclass
class _XMeansClassfier:
    """使用kmeans来找到一个最适合的分组的数量"""

    blocks: Iterable[_TextBlock]
    max_k: int
    min_k: int = 2

    def classify(self, points: np.ndarray):
        best_score = -1
        best_kmeans = None

        for k in range(self.min_k, min(points.size, self.max_k)):
            kmeans = KMeans(n_clusters=k, random_state=42)
            kmeans.fit(points)

            if k > 1:
                score = silhouette_score(points, kmeans.labels_)
                if score > best_score:
                    best_score = score
                    best_kmeans = kmeans
            else:
                best_kmeans = kmeans
        if best_kmeans is None:
            raise ValueError(f"max_k should be greater than {self.min_k}")

        return best_kmeans.labels_

    def __iter__(self):
        first, *others = self.blocks
        if all(first.in_same_col(other) for other in others):
            for elem in self.blocks:
                yield _Group([elem])
            return

        boxes_array = np.array([(block.index, (block.outline.top + block.outline.bottom) / 2) for block in self.blocks])
        points = np.array([[center] for _, center in boxes_array])
        labels = self.classify(points)

        block_by_index = {block.index: block for block in self.blocks}
        grouped_blocks = defaultdict(list)
        for label, (index, *_) in zip(labels, boxes_array):
            grouped_blocks[label].append(block_by_index[index])

        for blocks in sorted(grouped_blocks.values(), key=lambda x: x[0].index):
            yield _Group(blocks)


class MultiGroup(BaseModel):
    """
    将元素块分组, 然后在每一个组中提取需要的字段,

    一般来说 一个组包含一个段落和一个表格, 表格按照列拆分成段落, 然后统一用正则匹配,
    默认会按照优先级来进行分组, 用户可以自定义使用什么模型来配置
    """

    def predict_schema_answer(self, _):
        element_by_index = {
            para["index"]: _TextBlock.model_validate(para)
            for para in self.pdfinsight.data["paragraphs"]
            if para["outline"][0] > 0 or any(char["box"][3] >= para["outline"][3] for char in para["chars"])
        }
        answers = []
        groups = list(_GroupCursor(element_by_index))
        for group in groups:
            answers.extend(self.predict_group_with_digit(group))
        if not answers:
            for group in groups:
                answers.extend(self.predict_group_with_alnum(group))
        # 截图中一个股票代码都没有的话, 尝试从每一个分组中提取股票名称
        if not answers:
            for group in groups:
                exclude_indices = set()
                for i, block in enumerate(group.blocks):
                    if P_NUMBER.search(block.text):
                        exclude_indices.add(i)
                if not exclude_indices:  # 如果分组中不存在数字, 则认为也不存在股票名称
                    continue
                name_blocks = [block for i, block in enumerate(group.blocks) if i not in exclude_indices]
                if name_blocks:
                    answers.append(self.create_column_result("股票名称", name_blocks[0]))
        return answers

    def predict_group_with_digit(self, group: _Group):
        code_blocks = [block for block in group.blocks if block.code]
        if not code_blocks:
            return
        code_block = code_blocks[0]
        answer = self.create_column_result("股票代码", code_block, code_block.code)
        # 1, 有资产情况
        if "资产情况" in group.texts:
            self.predict_asset_group(answer, code_block, group)
        # 2, 只有一个文本块, 包含了代码和名称
        elif (
            code_block == group.blocks[0]
            and len(group.blocks) == 1
            and (matched := P_NAME_BEFORE_CODE.search(code_block.text))
        ):
            chars = code_block.chars[matched.start(1) : matched.end(1)]
            answer.update(self.create_column_result("股票名称", code_block, chars))
        # 3, 第一个块是代码, 这种一般第二个是股票名称
        elif code_block == group.blocks[0] and len(group.blocks) > 1:
            answer.update(self.create_column_result("股票名称", group.blocks[1]))
        # 4, 股票代码在股票名称下面
        elif name_blocks := [block for block in group.blocks if code_block.in_same_col(block) and code_block != block]:
            answer.update(self.create_column_result("股票名称", name_blocks[0]))
        # 5, 第一列是非数字的代码时跳过
        elif P_ALPHA.search(group.blocks[0].text) and P_ALNUM_CODE.search(group.blocks[0].text):
            return

        yield answer

    def predict_group_with_alnum(self, group: _Group):
        code_blocks = [block for block in group.blocks if P_ALNUM_CODE.search(block.text)]
        if not code_blocks:
            return
        code_block = code_blocks[0]
        answer = self.create_column_result("股票代码", code_block, code_block.code)
        if code_block == group.blocks[0] and len(group.blocks) > 1:
            answer.update(self.create_column_result("股票名称", group.blocks[1]))
        yield answer

    def create_column_result(self, column: str, block: _TextBlock, chars: Sequence[_Char] = ()):
        return {
            column: [
                self.create_result(
                    [
                        CharResult(
                            block.model_dump(),
                            [char.model_dump() for char in chars or block.chars],
                        )
                    ],
                    column=column,
                )
            ]
        }

    def predict_asset_group(self, answer: dict, code_block, group):
        asset_blocks = [block for block in group.blocks if block.text == "资产情况"]
        asset_block = asset_blocks[0]
        for block in group.blocks:
            if block.outline.top > asset_block.outline.bottom and asset_block.in_same_col(block):
                answer.update(self.create_column_result("资产情况", block))
                break
        if code_block == group.blocks[0] and (matched := P_NAME_BEFORE_CODE.search(code_block.text)):
            chars = code_block.chars[matched.start(1) : matched.end(1)]
            answer.update(self.create_column_result("股票名称", code_block, chars))
        else:
            index = group.blocks.index(code_block)
            prev_blocks = [
                block
                for i, block in enumerate(group.blocks)
                if (i < index and code_block.outline.top - block.outline.bottom < code_block.outline.height)
            ] + [code_block]
            virtual_block = _TextBlock(
                page=0,
                text="".join(block.text for block in prev_blocks),
                chars=[char for block in prev_blocks for char in block.chars],
                index=min(map(attrgetter("index"), prev_blocks)),
                outline=_Box(0, 0, 0, 0),
            )
            if matched := P_NAME_BEFORE_CODE.search(virtual_block.text):
                chars = virtual_block.chars[matched.start(1) : matched.end(1)]
                answer.update(self.create_column_result("股票名称", virtual_block, chars))
