import logging
from collections import ChainMap
from enum import Enum, EnumMeta, IntEnum, StrEnum, auto, unique
from functools import cached_property, lru_cache
from pathlib import Path
from typing import Any, Iterable, Literal

from aenum import MultiValueEnum
from pydantic import BaseModel, ConfigDict, Field, model_validator
from typing_extensions import Self, TypeAlias

from remarkable.config import get_config, project_root

BASIC_SUPPORTED_SUFFIXES = [".zip", ".doc", ".docx", ".jpeg", ".jpg", ".pdf", ".png", ".txt"]
SUPPORTED_SUFFIXES = BASIC_SUPPORTED_SUFFIXES + [".tif", ".tiff", ".xls", ".xlsx"]
ADMIN_ID = 1
API_PREFIX_V1 = "/api/v1"
API_PREFIX_V2 = "/api/v2"
ADMIN_NAME = "admin"

CCXI_CACHE_PATH = Path(project_root) / "data" / "ccxi_cache"

logger = logging.getLogger(__name__)


class _EnumMeta(EnumMeta):
    def __new__(metacls, cls, bases, classdict, **kwds):
        enum_cls = super().__new__(metacls, cls, bases, classdict, **kwds)
        enum_cls._phrase2enum_map_ = {}
        enum_cls._label2enum_map_ = {}
        enum_cls._abbr_map_ = {}
        for enum in enum_cls:
            enum_cls._phrase2enum_map_[enum.phrase.lower()] = enum
            enum_cls._label2enum_map_[enum.label.lower()] = enum
            enum_cls._abbr_map_[enum.abbr.lower()] = enum
        return enum_cls

    def __contains__(self, item):
        if item in self._value2member_map_:
            return True
        if not isinstance(item, str):
            return False
        item = item.lower()
        return item in self._phrase2enum_map_ or item in self._label2enum_map_ or item in self._abbr_map_

    def __getitem__(cls, name):
        return ChainMap(cls._member_map_, cls._phrase2enum_map_, cls._label2enum_map_, cls._abbr_map_)[name]


class EnumMixin:
    _phrase2enum_map_ = None
    _value2member_map_ = None

    @classmethod
    def value2member_map(cls) -> dict[int, Enum]:
        return cls._value2member_map_

    @classmethod
    def member_values(cls) -> list[int]:
        return [i.value for i in cls.__members__.values()]

    @classmethod
    def phrase_to_enum(cls, phrase: str) -> Self | None:
        phrase = (phrase or "").strip().lower()
        if phrase not in cls._phrase2enum_map_:
            raise ValueError(f'No such phrase: "{phrase}"')
        return cls._phrase2enum_map_[phrase]

    @classmethod
    def phrase_to_enums(cls, phrase: str | None | list[str]) -> list[Self]:
        if not phrase:
            return []
        if isinstance(phrase, str):
            phrase = [phrase]

        enums = []
        for p in phrase:
            if enum := cls.phrase_to_enum(p):
                enums.append(enum)
            else:
                logger.warning(f'Invalid phrase: "{p}"')
        return enums

    @classmethod
    def _attrs(cls, name: str) -> tuple[str, ...]:
        return tuple(getattr(i, name) for i in cls)

    @classmethod
    def labels(cls) -> tuple[str, ...]:
        return cls._attrs("label")

    @classmethod
    def phrases(cls) -> tuple[str, ...]:
        return cls._attrs("phrase")

    @classmethod
    def abbrs(cls) -> tuple[str, ...]:
        return cls._attrs("abbr")


class IntEnumMixin(IntEnum):
    def __new__(cls, value: int, phrase: str = "", label: str = "", abbr: str = ""):
        obj = int.__new__(cls, value)
        obj._value_ = value
        obj.phrase = phrase
        obj.label = label or phrase
        obj.abbr = abbr or phrase
        return obj


class MultiValueEnumBase(MultiValueEnum):
    @classmethod
    def members(cls):
        return [k.value for k in cls]


class IntEnumBase(EnumMixin, IntEnumMixin, metaclass=_EnumMeta):
    pass


@unique
class CommonStatus(EnumMixin, IntEnum):
    """
    通用的"有效/无效"状态
    """

    INVALID = 0  # 无效
    VALID = 1  # 有效


@unique
class AccuracyType(EnumMixin, IntEnum):
    PROMPT = 1  # 默认，最终提取答案的正确率
    CRUDE = 2  # 位置推荐的正确率


@unique
class AccuracyTest(EnumMixin, IntEnum):
    # TRAIN = 1  # 默认，训练集正确率
    TEST = 2  # 测试集正确率
    DIFF_MODEL = 3  # 对比版本差异


@unique
class AnswerStatus(EnumMixin, IntEnum):
    INVALID = 0
    VALID = 1

    # 用户答题过程中暂存在服务器上的答案，在正式确认前该答案不算作答案。
    # PDF表格标注要求客户端每20s自动提交一次暂存答案给服务端，最后用户手动确认。
    UNFINISHED = 2


@unique
class FillInStatus(EnumMixin, IntEnum):
    TODO = 0  # 待填报
    DOING = 1  # 填报中
    FINISH = 2  # 已提交


@unique
class QuestionStatus(EnumMixin, IntEnum):
    TODO = 0  # 待做
    DOING = 1  # 正在答题
    FINISH = 2  # 答题完毕
    VERIFY = 3  # 已反馈
    DISACCORD = 4  # 答案不一致
    ACCORDANCE = 5  # 答案一致
    VERIFY_CONFIRMED = 6  # 管理员确认了反馈
    STANDARD_CONFIRMED = 10  # 正确答案已确定/冲突已处理

    @classmethod
    def status_anno_map(cls):
        return {
            0: "待做",
            1: "正在答题",
            2: "答题完毕",
            3: "已反馈",
            4: "答案不一致",
            5: "答案一致",
            6: "管理员确认了反馈",
            10: "正确答案已确定/冲突已处理",
        }


class AIStatus(EnumMixin, IntEnum):
    SKIP_PREDICT = -1  # 不需要预测
    TODO = 0  # 待预测
    DOING = 1  # 预测中
    FAILED = 2  # 失败
    FINISH = 3  # 完成
    DISABLE = 4  # 模型未启用
    UNCORRELATED = 5  # 模型未关联


class LLMStatus(EnumMixin, IntEnum):
    SKIP_PREDICT = -1  # 不需要预测
    TODO = 0  # 待预测
    DOING = 1  # 预测中
    FAILED = 2  # 失败
    FINISH = 3  # 完成


class SearchAIStatus(EnumMixin, IntEnum):
    TODO = AIStatus.TODO  # 待预测
    DOING = AIStatus.DOING  # 预测中
    FAILED = AIStatus.FAILED  # 失败
    FINISH = AIStatus.FINISH  # 完成
    DISABLE = AIStatus.DISABLE  # 模型未启用


@unique
class AnswerResult(EnumMixin, IntEnum):
    NONE = -1
    NOT_REACH_THRESHOLD = 0  # 等待凑足答题人数
    CORRECT = 1  # 正确
    INCORRECT = 2  # 错误
    TOBE_JUDGED = 3  # 自动比较无法判断, 等待管理员判断


@unique
class AnswerType(EnumMixin, IntEnum):
    USER_DO = 1  # 用户创建的普通答案
    ADMIN_DO_1 = 2  # 普通用户答题完毕, 比较答案前, 管理员答题
    ADMIN_VERIFY = 3  # 管理员处理反馈增加的答案
    ADMIN_JUDGE = 4  # 管理员处理冲突增加的答案
    ADMIN_DO_2 = 5  # 题目已经处理完毕(一致或者已经设定标准答案)的情况下, 管理员答题


class HistoryAction(EnumMixin, IntEnum):
    LOGIN = 1
    OPEN_PDF = 2
    SUBMIT_ANSWER = 3
    ADMIN_VERIFY = 4
    ADMIN_JUDGE = 5
    CREATE_USER = 6
    MODIFY_USER = 7
    DELETE_USER = 8
    CREATE_MOLD = 9
    MODIFY_MOLD = 10
    DELETE_MOLD = 11
    CREATE_PROJECT = 12
    MODIFY_PROJECT = 13
    DELETE_PROJECT = 14
    CREATE_TREE = 15
    MODIFY_TREE = 16
    DELETE_TREE = 17
    CREATE_FILE = 18
    MODIFY_FILE = 19
    DELETE_FILE = 20
    CREATE_TAG = 21
    MODIFY_TAG = 22
    DELETE_TAG = 23
    UPLOAD_ZIP = 24
    CREATE_TRAINING_DATA = 25  # 新建`导出训练数据`任务
    EXPORT_TRAINING_DATA = 26  # 导出训练数据
    DELETE_TRAINING_DATA = 27  # 删除`导出训练数据`任务
    TRAINING_SCHEMA = 28  # 训练模型
    ENABLE_MODEL = 29  # 启用模型
    TESTING_SCHEMA = 30  # 测试模型
    DELETE_CUSTOM_FIELD = 31  # 删除自定义字段
    CREATE_MODEL_VERSION = 32  # 新建模型版本
    UPDATE_MODEL_PREDICTOR = 33  # 更新提取模型
    DELETE_MODEL_PREDICTOR = 34  # 删除模型版本
    DISABLE_MODEL = 35  # 停用模型
    CREATE_TABLE_OF_CONTENT = 36  # 新建导出目录结构任务
    EXPORT_TABLE_OF_CONTENT = 37  # 导出目录结构
    DELETE_TABLE_OF_CONTENT = 38  # 删除导出目录结构
    CREATE_INSPECT_RESULT = 39  # 新建`导出审核结果`任务
    EXPORT_INSPECT_RESULT = 40  # 导出审核结果
    DELETE_INSPECT_RESULT = 41  # 删除`导出审核结果`任务
    DIFF_MODEL = 42  # 比较模型差异
    ORIGINAL_FILE = 43  # 导出原文件
    LOGOUT = 100

    ECITIC_TG_PUSH = 1000  # 中信托管部推送
    DCM_ORDER_REF_MODIFY = 2000  # 中信dcm簿记信息关联关系修改

    NAFMII_DEFAULT = 3000  # 交易商协会默认的action, 其他的都在nafmii_event表中


Permission: TypeAlias = dict[Literal["name", "definition"], str]


class FeatureSchema(BaseModel):
    model_config = ConfigDict(from_attributes=True, str_strip_whitespace=True, extra="allow")

    common_permissions: dict[str, Permission]
    basic_permissions: list[str] = Field(default_factory=list)
    additional_permissions: dict[str, Permission] = Field(default_factory=dict)
    supported_suffixes: list[str] = SUPPORTED_SUFFIXES
    supported_zip_suffixes: list[str] = [".zip"]

    @classmethod
    def from_config(cls, cfg: dict | None = None) -> Self:
        return cls(**(cfg or get_config("feature")))

    def model_post_init(self, __context: Any) -> None:
        # stronghold 环境移除 manage_prj 项目管理权限
        if "stronghold" in (get_config("web.plugins") or []):
            self.common_permissions.pop("manage_prj", None)

        if not get_config("web.model_manage"):
            self.common_permissions.pop("manage_model", None)

        if not self.basic_permissions:
            logger.warning("No basic permissions found in config file, use default value.")
            self.basic_permissions = ["browse", "remark"]

    @model_validator(mode="after")
    def check(self):
        # TODO: We should validate all the possible essential features here.
        assert self.common_permissions, "No common permissions found in config file."
        if any(k for k in self.additional_permissions if k in self.common_permissions):
            raise ValueError(f"{self.additional_permissions=} conflicts with {self.common_permissions=}")

        if any(not s.startswith(".") for s in self.supported_suffixes):
            raise ValueError(f"{self.supported_suffixes=} should start with '.'")

        if not self.basic_permissions:
            raise ValueError("No basic permissions found in config file.")

        if not self.supported_suffixes:
            raise ValueError("No supported suffixes found in config file.")

        assert set(self.basic_permissions) <= set(self.common_permissions), ValueError(
            "Basic permissions should be subset of common permissions."
        )

    @cached_property
    def all_perms(self) -> dict[str, Permission]:
        return self.common_permissions | self.additional_permissions

    def filter_perms_to_db(self, perms: Iterable[str] | None = None) -> list[dict[str, str]]:
        # 确保有基本权限
        perms = set(perms or set()) | set(self.basic_permissions)
        return [{"perm": p} for p in self.all_perms if p in perms]

    @staticmethod
    def base_perms_to_db() -> list[dict[str, str]]:
        return FeatureSchema.from_config().filter_perms_to_db()

    @staticmethod
    def all_perms_to_db() -> list[dict[str, str]]:
        feature = FeatureSchema.from_config()
        return feature.filter_perms_to_db(feature.all_perms)


@lru_cache(maxsize=1)
def get_perms(feature: FeatureSchema | None = None) -> list[str]:
    return list((feature or FeatureSchema.from_config()).all_perms)


class PDFParseStatus(EnumMixin, IntEnum):
    PENDING = 1  # 排队中
    UNSUPPORTED_FILE = 9  # 不支持的文件
    PDFINSIGHT_PARSING = 10  # pdfinsight 解析中，pdfinsight真正开始解析文件，收到解析回调通知的状态
    PARSING = 2  # 解析中（pdfinsight,文件发送到pdfinsight了，可能还在pdfinsight队列中等待）
    PARSED = 21  # 解析中 pdfinsight回调完成
    CACHING = 7  # 缓存中（png or svg + pageinfo）
    OCR_EXPIRED = 8  # ocr过期
    PAGE_CACHED = 6
    COMPLETE = 4
    FAIL = 5
    CANCELLED = 3
    UN_CONFIRMED = 51  # pdfinsight 解析流程无误 但是结果有问题 包括但不限于 返回的元素块为空

    EXCEL_INSERT_DB_SUCCESS = 100  # EXCEL入库成功
    EXCEL_INSERT_DB_FAILED = 101  # EXCEL入库失败

    CLEAN_FILE_PARSING = 200  # 清稿文件处理中


class SearchPDFParseStatus(EnumMixin, IntEnum):
    PENDING = PDFParseStatus.PENDING  # 排队中
    PARSING = PDFParseStatus.PARSING  # 解析中
    COMPLETE = PDFParseStatus.COMPLETE  # 完成
    FAIL = PDFParseStatus.FAIL  # 解析失败
    UN_CONFIRMED = PDFParseStatus.UN_CONFIRMED  # 解析异常


@unique
class PDFFlag(EnumMixin, IntEnum):
    NEED_CONVERT = 1
    CONVERTED = 0
    FAILED_CONVERT = -1


@unique
class ConflictTreatmentType(EnumMixin, IntEnum):
    MANUAL = 1  # 人工处理
    LATEST = 2  # 以最新为准
    MERGED = 3  # 合并答案


class FileAnswerMergeStrategy(EnumMixin, StrEnum):
    ONLY_LATEST = auto()  # 仅采用新的
    OLD_FIRST = auto()  # 合并答案, 旧答案优先, 其次新答案
    EDITED_FIRST = auto()  # 合并答案, 用户编辑过的的答案优先, 其次新答案, 再次旧答案


@unique
class PublicStatus(EnumMixin, IntEnum):
    PUBLIC = 1
    PRIVATE = 0


@unique
class PrompterTrainingStatus(EnumMixin, IntEnum):
    """
    模型训练状态（初步定位）
    """

    ERROR = -1  # 训练异常
    CREATE = 0  # 新建
    UPDATE = 1  # 读取文档数据和答案
    EXTRACT = 2  # 生成训练数据
    TRAIN = 3  # 训练完毕

    @classmethod
    def status_anno_map(cls):
        return {
            0: "模型训练中 10%",
            1: "模型训练中 30%",
            2: "模型训练中 60%",
            3: "训练完毕",
            -1: "预处理中，请稍后重试",
        }


@unique
class PredictorTrainingStatus(EnumMixin, IntEnum):
    """
    模型训练状态（精确提取）
    """

    ERROR = -1  # 训练异常
    CREATE = 0  # 新建 待训练
    PREPARE = 1  # 读取文档数据和答案
    TRAINING = 2  # 训练中
    DONE = 3  # 训练完毕
    NEED_TRAIN_AGAIN = 4  # 需要重新训练

    @classmethod
    def status_anno_map(cls):
        return {
            0: "新建模型",
            1: "模型训练中 30%",
            3: "训练完毕",
            -1: "预处理中，请稍后重试",
        }


@unique
class ModelEnableStatus(EnumMixin, IntEnum):
    """
    模型启用状态
    """

    DISABLE = 0  # 未启用
    ENABLE = 1  # 启用


@unique
class ModelType(EnumMixin, IntEnum):
    """
    模型类型
    """

    PREDICT = 1  # 精确提取  # 在界面配置的模型 默认会进行初步定位 所有的状态判断均使用PREDICT   PROMPTER将会被丢弃
    PROMPTER = 2  # 初步定位

    DEVELOP = 20  # 开发定制的模型

    @classmethod
    def status_anno_map(cls):
        return {
            1: "精确提取",
            2: "初步定位",
        }


@unique
class MoldType(EnumMixin, IntEnum):
    COMPLEX = 0  # 复杂长文档信息抽取
    LLM = 10  # 大模型提取（调用chatdoc studio）
    HYBRID = 11  # 混合形式（COMPLEX + LLM）


@unique
class AuditStatusEnum(EnumMixin, IntEnum):
    UNAUDITED = 0  # 未审核
    ACCEPT = 1  # 接受
    REFUSE = 2  # 拒绝
    SKIP = 3  # 无需审核

    # 深交所POC合规判断用 EOF
    COMPLIANCE = 10  # 合规
    NONCOMPLIANCE = 11  # 不合规
    DIS_IN_TIME = 20  # 及时披露
    DIS_DELAY = 21  # 未及时披露
    DIS_NONE = 22  # 未披露

    # EOF

    @classmethod
    def status_anno_map(cls):
        return {
            0: "未审核",
            1: "接受",
            2: "拒绝",
            3: "无需审核",
            10: "合规",
            11: "不合规",
            20: "及时披露",
            21: "未及时披露",
            22: "未披露",
        }


@unique
class SSEAuditStatus(EnumMixin, IntEnum):
    TODO = AuditStatusEnum.UNAUDITED.value
    COMP_0 = 10
    COMP_1 = 11
    NON_COMP_0 = 20
    NON_COMP_1 = 21
    NON_COMP_2 = 22
    UNCERTAIN = 30

    @classmethod
    def status_anno_map(cls):
        return {
            AuditStatusEnum.UNAUDITED.value: "待审核",
            10: "合规(经营情况与财务报告披露一致)",
            11: "合规(经营情况与分部信息披露一致)",
            20: "不合规(经营情况与财务报告披露不一致)",
            21: "不合规(经营情况与分部信息披露不一致)",
            22: "不合规(财务注释与分部均未详细披露)",
            30: "待分析(披露分部财务信息，需进一步分析)",
        }


@unique
class ComplianceStatus(EnumMixin, IntEnum):
    COMPLIANCE = 0  # 合规
    NONCOMPLIANCE = 1  # 不合规
    NONCONTAIN = 2  # 未出现
    UNCERTAIN = 3  # 待定，需人工审核
    IGNORE = 4  # 忽略, 不做处理

    # 深交所POC合规判断用 EOF
    DIS_IN_TIME = 20  # 及时披露
    DIS_DELAY = 21  # 未及时披露
    DIS_NONE = 22  # 未披露

    # EOF

    @classmethod
    def status_anno_map(cls):
        return {
            0: "合规",
            1: "不合规",
            2: "未披露",
            3: "需人工审核",
            4: "忽略",
            20: "及时披露",
            21: "未及时披露",
            22: "未披露",
        }


@unique
class ErrorStatus(EnumMixin, IntEnum):
    UNAMEND = 0  # 未修改
    AMEND = 1  # 修改


@unique
class AutoDocStatus(EnumMixin, IntEnum):
    CREATED = 0
    DONE = 1
    FAILED = 2
    DOING = 3


@unique
class RPCTaskType(EnumMixin, IntEnum):
    PROMPTER = 1  # 定位
    PREDICTOR = 2  # 提取
    INSPECTOR = 3  # 合规


@unique
class SZSETableAnswerStatus(EnumMixin, IntEnum):
    UNCONFIRMED = 0  # 待确认
    CONFIRMED = 1  # 已确认


class TagType(EnumMixin, IntEnum):
    FILE = 1  # 约定变量名为对应model类名的大写, TagRelation.update_tag_relation会基于此做判断
    NEWFILE = 1
    MOLD = 2
    NEWMOLD = 2

    @classmethod
    def status_anno_map(cls):
        return {
            1: "文件",
            2: "Schema",
        }


class TableType(EnumMixin, IntEnum):
    TUPLE = 1
    ROW = 2
    KV = 3
    COL = 4  # 按列解析

    @classmethod
    def status_anno_map(cls):
        return {
            1: "table_tuple",
            2: "table_row",
            3: "table_kv",
            4: "table_col",
        }


class TokenStatus(EnumMixin, Enum):
    EXPIRED = "Token expired."
    INVALID = "Token invalid."
    MISSED = "Token or timestamp missed."
    PASSED = "Token check passed."


@unique
class ExtractMethodType(EnumMixin, IntEnum):
    FIRGUE = 0  # 数值, 提取段落里的内容
    TERM = 1  # 条款, 提取整个段落


@unique
class RuleMethodType(EnumMixin, IntEnum):
    PROGRAM = 0  # 程序
    TERM = 1  # 固定条款
    FORMULA = 2  # 计算公式


@unique
class TaxRate(EnumMixin, IntEnum):
    GENERAL = 6
    SPECIAL = 13


@unique
class OctopusFileType(EnumMixin, Enum):
    """
    '1': "国债发行公告"
    '2': "发行情况公告"
    '3': "回售登记"
    """

    TREASURY = "1"
    ISSUANCE = "2"
    REGISTER = "3"


@unique
class OctopusUnit(EnumMixin, IntEnum):
    """
    持有金额单位(1, "亿元")(2, "元")(3, "万元")(4L, "其他")
    """

    YI_YUAN = 1
    YUAN = 2
    WAN_YUAN = 3
    OTHER = 4


@unique
class Language(EnumMixin, Enum):
    """
    语言类型
    """

    ZH_CN = "zh_CN"
    EN_US = "en_US"


@unique
class RuleReviewStatus(EnumMixin, IntEnum):
    """
    审核规则复核状态
    """

    NOT_REVIEWED = 1  # 待复核
    NOT_PASS = 2  # 复核不通过
    PASS = 3  # 复核通过
    DEL_NOT_REVIEWED = 4  # 删除后待复核
    DEL_NOT_PASS = 5  # 删除后复核不通过


class SpecialAnswerType(EnumMixin, IntEnum):
    EXPORT_ANSWER = 10
    PREDICT_ANSWER = 20
    JSON_ANSWER = 30
    ORIGIN_ANSWER = 40
    TEST_ACCURACY_PRESET = 50
    TEST_ACCURACY_CRUDE = 51


@unique
class AccuracyRecordStatus(EnumMixin, Enum):
    DOING = "doing"
    DONE = "done"
    FAILED = "failed"


@unique
class PdfinsightRetCode(EnumMixin, IntEnum):
    COLORING_FAILED = 30


@unique
class ChinaAmcProjectSource(EnumMixin, IntEnum):
    LOCAL = 0  # 本地上传
    XINGYUN = 1  # 星云系统


class ChinaAmcProjectStatus(EnumMixin, IntEnum):
    TO_BE_UPLOADED = 1000  # 文档待上传
    PARSING = 1100  # 文档解析中
    PARSED = 1110  # 文档解析完成
    AI_FAILED = 1111  # 文档预测失败
    AI_DISABLE = 1112  # 模型未启用
    AI_DOING = 1113  # 文档预测中
    DIFF_FAILED = 1114  # 文档对比失败
    DIFF_DONE = 1115  # 文档对比成功
    DIFF_DOING = 1116  # 文档对比中
    PARSE_FAILED = 1117  # 文档解析失败


class ChinaAmcFileStatus(IntEnum):
    PDF_PARSING = 0  # 解析中
    PDF_FAILED = 1  # 解析失败
    AI_DISABLE = 2  # 模型未启动
    AI_FAILED = 3  # 预测失败
    AI_TODO = 4  # 待预测
    AI_DOING = 5  # 预测中
    AI_FINISH = 6  # 预测成功
    CMP_FAILED = 7  # 文档内比对失败
    CMP_DOING = 8  # 文档内比对进行中
    CMP_FINISH = 9  # 文档内比对成功


class ChinaAmcCompareStatus(EnumMixin, IntEnum):
    DEFAULT = 0  # 比对未开始
    FAILED = -2  # 文档对比失败
    DOING = 1  # 文档对比中
    DONE = 2  # 文档对比成功


class ChinaAMCChapterDiffStatus(IntEnumBase):
    DEFAULT = (0, "default", "章节对比未开始")
    FAILED = (-2, "failed", "章节对比失败")
    DOING = (1, "doing", "章节对比中")
    DONE = (2, "done", "章节对比成功")


class EciticTgTaskType(EnumMixin, IntEnum):
    SINGLE = 1  # 单文档参数提取
    COMPARE = 2  # 两文档对比
    TO_COUNT = 3  # 参与统计


class EciticTgTriggerType(EnumMixin, IntEnum):
    AUTO = 1  # 自动
    MANUAL = 2  # 人工


class UNZipStage(IntEnumBase):
    START = (1, "start", "开始")
    UNPACK = (2, "unpack", "解压中")
    IMPORT = (3, "import", "导入中")
    FINISHED = (4, "finished", "完成")
    ERROR = (-1, "error", "失败")


class JSONConverterStyle(IntEnumBase):
    ORIGIN = (0, "origin", "原始数据")
    PLAIN_TEXT = (1, "plain_text", "文本数据")
    ENUM = (2, "enum", "枚举字段保留文本和枚举值")


class RuleType(EnumMixin, StrEnum):
    EXPR = "expr"
    EMPTY = "empty"
    REGEX = "regex"
    CONDITION = "condition"
    TEMPLATE = "template"
    SCHEMA = "schema"
    EXTERNAL = "external"


class RuleID(IntEnum):
    EXTERNAL_ID = -1


class EciticExternalSource(StrEnum):
    GANYI = "感易"


class DcmStatus(EnumMixin, StrEnum):
    TODO = "1"
    READY = "2"
    DOING = "3"
    DONE = "4"
    FAILED = "5"


class ZTSProjectStatus(EnumMixin, StrEnum):
    TODO = "1"
    DOING = "2"
    DONE = "3"
    FAILED = "4"


class ZTSDocType(EnumMixin, StrEnum):
    ANNUAL = "本期年报"
    SEMI = "本期半年报"
    PREVIOUS_ANNUAL = "往期年报"


ZTS_DOC_TYPES_ANNUAL = {ZTSDocType.ANNUAL.value, ZTSDocType.PREVIOUS_ANNUAL.value}
ZTS_DOC_TYPES_SEMI = {ZTSDocType.SEMI.value, ZTSDocType.PREVIOUS_ANNUAL.value}


class TimeType(EnumMixin, IntEnum):
    CREATE = 1  # 创建/上传 时间
    UPDATE = 2  # 修改/更新 时间


class OrderByType(EnumMixin, IntEnum):
    DESC = 1  # 降序
    ASC = 2  # 升序


class CmfFiledStatus(EnumMixin, IntEnum):
    WAIT = 0  # 待分类
    DOING = 1  # 分类中
    DONE = 2  # 分类完成
    FAIL = 3  # 分类失败


class CmfInterfacePresetStatus(EnumMixin, IntEnum):
    WAIT = 0  # 待预测
    DOING = 1  # 预测中
    DONE = 2  # 预测完成
    FAIL = 3  # 预测失败


SZSE_RULE_MAP = {
    "AR": "年报",
    "rule1": "重大交易",
    "rule2": "担保",
    "rule3": "关联交易",
    "rule4": "业绩预告",
    "rule5": "会计变更",
    "rule6": "会计事务所变更",
}

abs_path = f"{project_root}/data/cgs"
FAKE_DATA = {
    "c819a6c85c2c9594d09ed5b0337a50e8": {
        "fid": 2526,
        "qid": 11983,
        "json_path": f"{abs_path}/误入藕花深处私募证券投资基金.json",
    },
    "7e4500464171862686a7cd3a3acaede1": {
        "fid": 2527,
        "qid": 11984,
        "json_path": f"{abs_path}/昨夜星辰昨夜2风私募证券投资基金.json",
    },
    "e2b8e962dfa16a4431e9f56aa90630f6": {
        "fid": 2528,
        "qid": 11985,
        "json_path": f"{abs_path}/上海盈象大象收益_1_号私募证券投资基金.json",
    },
}


SAFE_SEPARATOR = "|$|"

# 文件页解析时间乘数
TIME_MULTIPLIER = 3
SCANNED_PDF_MULTIPLIER = 7
INTERACTION_COST = get_config("nafmii.time.pdf_page") or 50
