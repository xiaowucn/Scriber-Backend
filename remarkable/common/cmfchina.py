from enum import StrEnum

from remarkable.common.constants import EnumMixin


class CmfChinaSysFromType(EnumMixin, StrEnum):
    LOCAL = "LOCAL"
    API = "API"
    EMAIL = "EMAIL"
    DISK = "DISK"
