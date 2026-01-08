from enum import Enum, IntEnum, StrEnum

from remarkable.common.constants import EnumMixin, MultiValueEnumBase


class TaskType(Enum):
    EXTRACT = "extract"
    AUDIT = "audit"
    JUDGE = "judge"  # 业务上使用`file.scenario_id`判断
    PDF2WORD = "pdf2word"
    CLEAN_FILE = "clean_file"
    SCANNED_PDF_RESTORE = "scanned_pdf_restore"


class FileTask(EnumMixin, StrEnum):
    JUDGE = TaskType.JUDGE.value
    AUDIT = TaskType.AUDIT.value
    INSPECT = "inspect"
    PREDICT = "predict"
    PARSE = "parse"


class NafmiiTaskType(str, Enum):
    T001 = "文本识别"
    T002 = "关键字识别"
    T003 = "敏感词识别"


class AuditAnswerType(IntEnum):
    final_answer = 1
    preset_answer = 2


class CountType(EnumMixin, IntEnum):
    DAY = 0  # 按日统计
    MONTH = 1  # 按月统计


class FieldStatus(EnumMixin, IntEnum):
    ALL = 0  # 全部
    AUDIT = 1  # 审核通过
    FAIL_AUDIT = 2  # 审核不通过
    UN_AUDIT = 3  # 未审核字段
    MODIFIED = 4  # 用户修改过
    NA = 5  # 不适用
    PROBABILITY = 6  # 评分


class ReviewedType(EnumMixin, IntEnum):
    ALL = 0  # 全部
    REVIEWED = 1  # 已复核
    UNREVIEWED = 2  # 未复核


class ExportStatus(EnumMixin, IntEnum):
    DOING = 1  # 进行中
    FAILED = 2  # 失败
    FINISH = 3  # 完成


class NafmiiEventStatus(MultiValueEnumBase, IntEnum):
    ALL = (1, "全部")
    SUCCEED = (2, "成功")
    FAILED = (3, "失败")


class NafmiiEventType(MultiValueEnumBase, IntEnum):
    ALL = (1, "全部")
    VIEW = (2, "查看")
    ADD = (3, "新增")
    MODIFY = (4, "修改")
    DELETE = (5, "删除")
    EXPORT = (6, "导出")
    LOGIN = (7, "登录")
    LOGOUT = (8, "退出登录")


class ClientName(StrEnum):
    cmfchina = "cmfchina"  # 招商基金
    cmbchina = "cmbchina"  # 招商银行
    gjzq = "gjzq"  # 国金证券
    nafmii = "nafmii"  # 交易商协会


class ExtractType(Enum):
    EXCLUSIVE = "exclusive"
    LLM = "llm"
