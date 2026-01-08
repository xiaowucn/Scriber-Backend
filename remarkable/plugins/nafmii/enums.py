from enum import Enum, IntEnum

from remarkable.common.constants import MultiValueEnumBase


class ConfirmStatus(MultiValueEnumBase):
    all = (1, "全部")
    pending = (2, "未确认")
    confirmed = (3, "已确认")


class DSFileType(str, Enum):
    DS_D001 = "付息兑付安排公告"
    DS_D002 = "行权公告"
    DS_D003 = "行权结果公告"
    DS_D004 = "敏感词/关键词识别"


class TaskStatus(str, Enum):
    TODO = "S000"
    DOING = "S001"
    DONE = "S002"
    FAIL = "S003"


class ErrorType(str, Enum):
    PARSE = "E001"
    PREDICT = "E002"
    MODEL = "E003"
    COMPARE = "E004"


class OperationType(IntEnum):
    add = 1
    undo = 2


class KnowledgeType(MultiValueEnumBase):
    finance = (1, "金融")
    account = (2, "会计")
    law = (3, "法律法规")
    service = (4, "存续期服务")

    def dict(self):
        return {"id": self.value, "name": self.values[1]}


class KnowledgeDetailType(MultiValueEnumBase):
    file = (1, "文件")
    word = (2, "词条")
