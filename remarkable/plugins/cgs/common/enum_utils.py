from enum import Enum

from remarkable.common.constants import EnumMixin


class TemplateCheckTypeEnum(EnumMixin, Enum):
    # 段内替换
    INNER_REPLACE = "inner_replace"
    # 段内重组
    INNER_RECOMBINATION = "inner_recombination"
    # 多段重组
    RECOMBINATION = "recombination"
    # 段内引用
    INNER_REFER = "inner_refer"
    # single select
    SINGLE_SELECT = "single_select"
    # 小标题忽略顺序
    CHAPTER_COMBINATION = "chapter_recombination"


class ConvertContentEnum(EnumMixin, Enum):
    DATE = "date"
    PERCENTAGE = "percentage"
    NUMBER = "number"
