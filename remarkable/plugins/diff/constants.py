from enum import IntEnum, unique


@unique
class CompareStatus(IntEnum):
    CREATED = 1
    COMPARING = 2  # 文件已提交, 等待Calliper返回比对结果
    DONE = 3
    FAILED = 4
    REMOTE_ERROR = 5  # 比对失败
    NET_PROBLEM = 6  # 网络问题, 推送失败
    TIMEOUT = 7


@unique
class DocType(IntEnum):
    INNER = 0  # 系统内文档
    OUTER = 1  # 系统外新文档


@unique
class DocStatus(IntEnum):
    CREATED = 0
    CONVERTED = 1
    FAILED_CONVERT = -1
