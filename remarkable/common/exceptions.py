import logging
from sre_constants import error as ReError


class CustomError(Exception):
    def __init__(self, msg, log_level=logging.ERROR, resp_status_code=200, logger=None, errors=None):
        (logger or logging).log(log_level, msg)
        self.msg = msg
        self.resp_status_code = resp_status_code
        self.errors = errors
        Exception.__init__(self, msg)


class NoFileError(CustomError):
    pass


class NoModelFoundError(CustomError):
    pass


class InvalidAnswerError(CustomError):
    pass


class ConfigError(CustomError):
    pass


class BasePredictError(Exception):
    pass


class ConfigurationError(BasePredictError):
    """The ConfigurationError exception is raised when the configuration of prophet is invalid."""


class PushError(Exception):
    pass


class DownloadError(Exception):
    pass


class ShellCmdError(Exception):
    pass


class NotSupportConvertError(Exception):
    pass


class InvalidMoldError(CustomError):
    pass


class NoEnabledModelError(Exception):
    pass


class PDFInsightNotFound(Exception):
    pass


class InvalidInterdocError(Exception):
    pass


class CustomReError(ReError):
    pass


class PdfinsightError(Exception):
    pass


class ModelDataNotFound(Exception):
    pass


class ItemNotFound(Exception):
    pass


class CmfChinaAPIError(Exception):
    pass


class NonAuditableError(Exception):
    pass


class IMAPLoginException(Exception):
    pass


class CGSException(Exception):
    @property
    def message(self):
        return self.args

    def to_dict(self):
        return None


class FormException(CGSException):
    def __init__(self, errors, content):
        super().__init__(self)
        self.errors = errors
        self.content = content

    @property
    def message(self):
        return self.content

    def to_dict(self):
        return self.errors
