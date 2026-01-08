from tornado.httputil import HTTPFile
from webargs import ValidationError

from remarkable.common.constants import FeatureSchema
from remarkable.common.exceptions import CustomError
from remarkable.plugins import PostFileValidator


class CmfPostFileValidator(PostFileValidator):
    valid_suffixes = FeatureSchema.from_config().supported_suffixes
    size_limit = 50  # 50M


class CmfZipFileValidator(PostFileValidator):
    valid_suffixes = FeatureSchema.from_config().supported_zip_suffixes

    @classmethod
    def check(cls, file: HTTPFile):
        cls.check_suffix(file)


def validate_zip_file_length(files: list[HTTPFile]):
    if len(files) > 1:
        raise ValidationError("每次仅支持上传一个压缩包，请依次上传。")


def validate_file_length(files: list[HTTPFile]):
    if len(files) > 1:
        raise ValidationError("每次仅支持上传一个文档，请依次上传。")


class CmfSharedDiskFileValidator(PostFileValidator):
    valid_suffixes = FeatureSchema.from_config().supported_suffixes
    size_limit_range = (0.001, 50)  # 0.001M(1KB) ~ 50M

    @classmethod
    def check_size(cls, file: HTTPFile):
        if len(file.body) < cls.size_limit_range[0] * 1024 * 1024:
            raise CustomError(f"{file.filename}:文件大小小于{cls.size_limit_range[0]}M", resp_status_code=400)
        if len(file.body) > cls.size_limit_range[1] * 1024 * 1024:
            raise CustomError(f"{file.filename}:文件大小超过{cls.size_limit_range[1]}M", resp_status_code=400)
