from email_validator import EmailNotValidError, validate_email
from marshmallow import Schema, fields, pre_load
from webargs import ValidationError

from remarkable.common import field_validate
from remarkable.common.cmfchina import CmfChinaSysFromType
from remarkable.common.constants import HistoryAction, RuleType, SearchAIStatus, SearchPDFParseStatus, TimeType
from remarkable.common.datetime_util import TIME_STAMP_MAX
from remarkable.common.enums import CountType, FieldStatus, ReviewedType
from remarkable.data.handlers import _validate_export_type
from remarkable.models.query_helper import PaginationSchema


def is_valid_email(email):
    try:
        validate_email(email, check_deliverability=False)
    except EmailNotValidError as e:
        raise ValidationError("账户地址格式错误") from e


class OrderBySchema(PaginationSchema):
    order_by = fields.Str(
        load_default="-id",
        validate=field_validate.OneOf(["id", "-id", "updated_utc", "-updated_utc", "created_utc", "-created_utc"]),
    )

    @pre_load
    def fomart_order_by(self, data, **kwargs):
        if "created_utc" in (data.get("order_by") or ""):
            data["order_by"] = data["order_by"].replace("created_utc", "id")
        return data


class SearchSchema(OrderBySchema):
    name = fields.Str(load_default="")
    iid = fields.Str(load_default="", data_key="id")
    user_name = fields.Str(load_default="")
    start_at = fields.Int(load_default=0, validate=field_validate.Range(max=TIME_STAMP_MAX, min=0))
    end_at = fields.Int(load_default=0, validate=field_validate.Range(max=TIME_STAMP_MAX, min=0))


class ProjectSearch(SearchSchema):
    mid = fields.Int(load_default=None)


class SchemaSearchSchema(SearchSchema):
    # 1: 上传/创建时间 2:修改时间
    _type = fields.Int(load_default=TimeType.CREATE, data_key="type")
    alias = fields.Str(load_default="")


class FileSearchSchema(SearchSchema):
    # 1: 上传/创建时间 2:修改时间
    _type = fields.Int(load_default=TimeType.CREATE, data_key="type")
    pdf_parse_status = fields.Int(
        load_default=None, validate=field_validate.OneOf(SearchPDFParseStatus.member_values())
    )
    ai_status = fields.Int(load_default=None, validate=field_validate.OneOf(SearchAIStatus.member_values()))
    search_mid = fields.Int(load_default=None, data_key="mid")


class ModelBaseSchema(Schema):
    intro = fields.Str(load_default="")
    usage = fields.Str(load_default="")


class ModelPostSchema(ModelBaseSchema):
    name = fields.Str(required=True)
    address = fields.Str(required=True, validate=field_validate.Regexp(r"^https?://"))


class ModelManSchema(Schema):
    enable = fields.Bool(load_default=True)
    preset = fields.Bool(load_default=True)


class FiledVerifySchema(Schema):
    fid = fields.Int(required=True)
    pid = fields.Int(required=True)
    mid = fields.Int(required=True)


class SortFieldSchema(Schema):
    field = fields.Str(required=True)
    direction = fields.Str(required=True)


class OrderSchema(Schema):
    orders = fields.List(fields.Nested(SortFieldSchema), load_default=[])


class NameSearchSchema(PaginationSchema):
    name = fields.Str(load_default="")


class FiledFileSearchSchema(OrderBySchema):
    filename = fields.Str(load_default="")
    projectname = fields.Str(load_default="")
    fid = fields.Int(load_default=None)
    user_name = fields.Str(load_default="")
    pdf_parse_status = fields.Int(
        load_default=None, validate=field_validate.OneOf(SearchPDFParseStatus.member_values())
    )
    sysfrom = fields.Str(load_default=None, validate=field_validate.OneOf(CmfChinaSysFromType.member_values()))
    ai_status = fields.Int(load_default=None, validate=field_validate.OneOf(SearchAIStatus.member_values()))
    start_at = fields.Int(load_default=0, validate=field_validate.Range(max=TIME_STAMP_MAX, min=0))
    end_at = fields.Int(load_default=0, validate=field_validate.Range(max=TIME_STAMP_MAX, min=0))


class ModelFileSearchSchema(PaginationSchema):
    mold_id = fields.Int(load_default=None)


class FilterSchema(Schema):
    keywords = fields.Str(load_default="")
    status = fields.Int(load_default=FieldStatus.ALL, validate=field_validate.OneOf(FieldStatus.member_values()))


class PanoramaSchema(Schema):
    mid = fields.Int(required=True)
    pid = fields.Int(required=False, load_default=None)
    fid = fields.Int(required=False, load_default=None)
    file_name = fields.Str(required=False, load_default=None)
    start_at = fields.Int(required=False, validate=field_validate.Range(max=TIME_STAMP_MAX, min=0))
    end_at = fields.Int(required=False, validate=field_validate.Range(max=TIME_STAMP_MAX, min=0))
    reviewed = fields.Int(required=False, load_default=ReviewedType.ALL)
    filter_dict = fields.Dict(
        keys=fields.Str(),
        values=fields.Nested(FilterSchema),
        load_default=dict,
        required=False,
    )
    # 1: 上传/创建时间 2:修改时间
    _type = fields.Int(load_default=TimeType.CREATE, data_key="type")


class PanoramaSearchSchema(PanoramaSchema, OrderBySchema):
    pass


class ExportSchema(PanoramaSchema):
    files_ids = fields.List(fields.Int(), load_default=[])
    export_type = fields.Str(load_default="json", validate=_validate_export_type)
    export_action = fields.Int(
        load_default=HistoryAction.CREATE_TRAINING_DATA, validate=field_validate.OneOf(HistoryAction.member_values())
    )


class ModelStatisticalSchema(Schema):
    model_ids = fields.List(fields.Int(), required=True, data_key="ids")
    count_type = fields.Int(
        load_default=CountType.DAY, validate=field_validate.OneOf(CountType.member_values()), data_key="type"
    )
    start_at = fields.Int(required=True, validate=field_validate.Range(max=TIME_STAMP_MAX, min=0))
    end_at = fields.Int(required=True, validate=field_validate.Range(max=TIME_STAMP_MAX, min=0))


class ModelCallSchema(ModelStatisticalSchema):
    pass


class ModelAccuracySchema(ModelStatisticalSchema):
    run_statistical_task = fields.Bool(required=False, load_default=False)


class RulesSchema(PaginationSchema):
    mold_id = fields.Int(load_default=None)
    name = fields.Str(load_default="")
    rule_type = fields.Str(load_default=None, validate=field_validate.OneOf(RuleType.member_values()))
    rule_id = fields.Int(load_default=None, data_key="id")
    user = fields.Str(load_default=None)
    field = fields.Str(load_default=None)


class GroupSchema(Schema):
    name = fields.Str(required=True)
    file_tree_ids = fields.List(fields.Int(), required=True)
    mold_ids = fields.List(fields.Int(), required=True)


class EditGroupSchema(Schema):
    name = fields.Str(load_default=None)
    file_tree_ids = fields.List(fields.Int(), load_default=None)
    mold_ids = fields.List(fields.Int(), load_default=None)


class SearchEmailSchema(OrderBySchema):
    # 1: 上传/创建时间 2:修改时间
    _type = fields.Int(load_default=TimeType.CREATE, data_key="type")
    start_at = fields.Int(load_default=0, validate=field_validate.Range(max=TIME_STAMP_MAX, min=0))
    end_at = fields.Int(load_default=0, validate=field_validate.Range(max=TIME_STAMP_MAX, min=0))


class EmailSchema(Schema):
    host = fields.Str(required=True)
    account = fields.Str(required=True, validate=is_valid_email)
    password = fields.Str(required=True)
    mold_id = fields.Int(required=False, load_default=None)
    pid = fields.Int(required=False, load_default=None)


class EditEmailSchema(Schema):
    host = fields.Str(required=True)
    account = fields.Str(required=True, validate=is_valid_email)
    password = fields.Str(required=False, load_default=None)
    mold_id = fields.Int(required=False, load_default=None)
    pid = fields.Int(required=False, load_default=None)


class TreeSchema(OrderBySchema):
    search_fid = fields.Int(load_default=None)
    search_mid = fields.Int(load_default=None, data_key="mid")
