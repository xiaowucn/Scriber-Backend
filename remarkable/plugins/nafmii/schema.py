import json

from marshmallow import Schema, ValidationError, fields, validate
from marshmallow.validate import OneOf

from remarkable.common import field_validate
from remarkable.common.enums import NafmiiEventStatus, NafmiiEventType
from remarkable.common.enums import NafmiiTaskType as TaskType
from remarkable.models.query_helper import PaginationSchema
from remarkable.plugins.nafmii.enums import ConfirmStatus, DSFileType, KnowledgeDetailType, KnowledgeType


class _EnumField(fields.Field):
    def __init__(self, enum, **kwargs):
        super().__init__(**kwargs)
        self.enum = enum

    def _deserialize(self, value, attr, data, **kwargs):
        if not isinstance(value, str):
            raise validate.ValidationError("值必须是字符串")
        try:
            return getattr(self.enum, value).value
        except AttributeError:
            raise validate.ValidationError(f"Invalid {self.enum.__name__}: {value}") from None


class _StrListField(fields.Field):
    """支持分隔符分割的列表字段
    :param inner_type: 列表元素的字段类型（如fields.Int）
    :param delimiter: 分割符，默认为逗号
    """

    default_error_messages = {"invalid_format": "不是有效的分割字符串", "element_errors": "元素校验失败：{errors}"}

    def __init__(self, inner_type, delimiter=",", **kwargs):
        super().__init__(**kwargs)
        if not isinstance(inner_type, fields.Field):
            raise ValueError("inner_type必须是字段或验证器实例")
        self.inner_type = inner_type
        self.delimiter = delimiter

    def _deserialize(self, value, attr, data, **kwargs):
        # 反序列化：字符串转列表
        if not isinstance(value, str):
            raise self.make_error("invalid_format")

        elements = [s.strip() for s in value.split(self.delimiter) if s.strip()]
        errors = {}

        # 逐个元素校验
        validated_elements = []
        for idx, elem in enumerate(elements):
            try:
                # 支持字段类型和验证器两种处理方式
                validated = self.inner_type.deserialize(elem)
                validated_elements.append(validated)
            except ValidationError as err:
                errors[idx] = err.messages

        if errors:
            error_msg = self.error_messages["element_errors"].format(
                errors="; ".join([f"第{i}项：{','.join(e)}" for i, e in errors.items()])
            )
            raise ValidationError(error_msg)

        return validated_elements


class _JsonField(fields.Field):
    default_error_messages = {"invalid_format": "不是有效的json字符串"}

    def __init__(self, inner_type, **kwargs):
        super().__init__(**kwargs)
        if not isinstance(inner_type, fields.Field):
            raise ValueError("inner_type必须是字段或验证器实例")
        self.inner_type = inner_type

    def _deserialize(self, value, attr, data, **kwargs):
        try:
            # 尝试将字符串解析为JSON对象
            parsed_obj = json.loads(value)
        except ValueError as e:
            # 如果解析失败，抛出ValidationError，并包含原始异常信息
            raise ValidationError(f"{self.error_messages['invalid_format']}: {str(e)}") from e
        return self.inner_type.deserialize(parsed_obj)


class CreateProjectSchema(Schema):
    name = fields.Str(required=True, validate=field_validate.Length(min=1, max=255))
    comment = fields.Str(load_default="")
    public = fields.Bool(load_default=True, data_key="is_public")
    default_molds = fields.List(fields.Int(), load_default=list)


class SearchProjectSchema(PaginationSchema):
    pid = fields.Int(required=False, load_default=None)
    start = fields.Int(required=False, load_default=0)
    end = fields.Int(required=False, load_default=0)
    name = fields.Str(required=False, validate=field_validate.Length(min=1), load_default="")
    username = fields.Str(required=False, validate=field_validate.Length(min=1), load_default="", data_key="user_name")
    order_by = fields.Str(
        required=False, validate=OneOf(["id", "-id", "-created_utc", "created_utc"]), load_default="-id"
    )


class UpdateProjectSchema(Schema):
    name = fields.Str(required=False, load_default="", validate=field_validate.Length(min=1, max=255))
    is_public = fields.Bool(required=False, load_default=None)
    comment = fields.Str(required=False, load_default="", validate=field_validate.Length(min=1))
    default_molds = fields.List(fields.Int(), required=False, load_default=None)


class UploadFileSchema(Schema):
    mold_id = fields.Int(load_default=None)
    task_types = _StrListField(fields.Str(validate=OneOf(TaskType)), load_default=list)
    keywords = _JsonField(
        fields.List(fields.Str(validate=field_validate.Length(min=1))), required=False, load_default="[]"
    )


ORDER_BY_FIELD = fields.Str(
    required=False,
    validate=OneOf(
        [
            "-created_utc",
            "created_utc",
            "-insight_queue_stamp",
            "insight_queue_stamp",
            "-insight_parse_stamp",
            "insight_parse_stamp",
        ]
    ),
    load_default="-created_utc",
)


class SearchFileSchema(PaginationSchema):
    mold_id = fields.Int(required=False, load_default=None)
    task_id = fields.Int(required=False, load_default=None, data_key="id")
    task_types = _StrListField(fields.Str(validate=OneOf(TaskType)), load_default=list)
    filename = fields.Str(required=False, validate=field_validate.Length(min=1), load_default="", data_key="name")
    username = fields.Str(required=False, validate=field_validate.Length(min=1), load_default="", data_key="user_name")
    confirm_status = fields.Int(required=False, load_default=1, validate=OneOf(ConfirmStatus.members()))
    start = fields.Int(required=False, load_default=0)
    end = fields.Int(required=False, load_default=0)
    answered = fields.Bool(required=False, load_default=None)
    status = fields.Int(required=False, load_default=None)
    order_by = ORDER_BY_FIELD
    file_type = fields.Str(required=False, load_default=None)


class ListFileSchema(PaginationSchema):
    order_by = ORDER_BY_FIELD


class CreateTaskSchema(Schema):
    sys_id = fields.Int(required=True)
    user_id = fields.Str(required=True)
    username = fields.Str(required=True)
    org_code = fields.Str(load_default="")
    org_name = fields.Str(load_default="")
    filename = fields.Str(required=True, validate=field_validate.Length(min=1, max=255))
    file_type = _EnumField(DSFileType, required=False, load_default=DSFileType.DS_D004.value)
    file_path = fields.Str(required=True)
    file_id = fields.Str(required=False, load_default="")
    task_types = _StrListField(_EnumField(TaskType), load_default=list, data_key="task_type")
    keywords = fields.List(fields.Str(), load_default=list, data_key="key_words")


class SearchSensitiveWordSchema(PaginationSchema):
    start = fields.Int(required=False, load_default=0)
    end = fields.Int(required=False, load_default=0)
    word_id = fields.Int(required=False, load_default=None, data_key="id")
    name = fields.Str(required=False, load_default="")
    type_id = fields.Int(required=False, load_default=None)
    sys_id = fields.Int(required=False, load_default=None)
    username = fields.Str(required=False, load_default="", data_key="user_name")
    order_by = fields.Str(
        required=False,
        validate=OneOf(["-created_utc", "created_utc"]),
        load_default="-created_utc",
    )


class CreateSensitiveWordSchema(Schema):
    name = fields.Str(required=True, validate=field_validate.Length(min=1, max=255))
    type_id = fields.Int(required=True)
    sys_id = fields.Int(required=True)
    user_id = fields.Str(required=False, validate=field_validate.Length(min=1, max=255), load_default=None)
    username = fields.Str(required=False, validate=field_validate.Length(min=1, max=255), load_default=None)


class UpdateSensitiveWordSchema(Schema):
    name = fields.Str(required=False, load_default=None, validate=field_validate.Length(min=1, max=255))
    type_id = fields.Int(required=False, load_default=None)
    sys_id = fields.Int(required=False, load_default=None)


class CreateWordTypeSchema(Schema):
    name = fields.Str(required=True, validate=field_validate.Length(min=1, max=255))


class UpdateFileAnswerSchema(Schema):
    field = fields.Str(required=True, validate=OneOf(["sensitive_word", "keyword"]))
    words = fields.List(fields.Dict(), required=True)


class UpdateTaskAnswerSchema(Schema):
    result_info = fields.List(fields.Dict(), required=True)
    check_points = fields.List(fields.Dict(), required=True)
    words_answers = fields.List(fields.Dict(), required=True)


class FileDeleteSchema(Schema):
    file_ids = fields.List(fields.Int(), required=True)
    tree_ids = fields.List(fields.Int(), required=True)


class ListKnowledgeSchema(PaginationSchema):
    id_ = fields.Int(required=False, load_default=None, data_key="id")
    type_ = fields.Int(required=False, load_default=None, validate=OneOf(KnowledgeType.members()), data_key="type")
    start = fields.Int(required=False, load_default=None)
    end = fields.Int(required=False, load_default=None)
    name = fields.Str(required=False, load_default=None)
    username = fields.Str(required=False, load_default=None, data_key="user_name")
    order_by = fields.Str(required=False, validate=OneOf(["-created_utc", "created_utc"]), load_default="-created_utc")


class CreateKnowledgeSchema(Schema):
    name = fields.Str(required=True, validate=field_validate.Length(min=1, max=255))
    type_ = fields.Int(required=True, validate=OneOf(KnowledgeType.members()), data_key="type")


class UpdateKnowledgeSchema(Schema):
    name = fields.Str(required=False, load_default=None, validate=field_validate.Length(min=1, max=255))
    type = fields.Int(required=False, load_default=None, validate=OneOf(KnowledgeType.members()))


class ListKnowledgeDetailSchema(Schema):
    type_ = fields.Int(
        required=False, load_default=None, validate=OneOf(KnowledgeDetailType.members()), data_key="type"
    )
    title = fields.Str(required=False, load_default=None, validate=field_validate.Length(min=1, max=255))


class CreateKnowledgeDetailSchema(Schema):
    type_ = fields.Int(required=True, validate=OneOf(KnowledgeDetailType.members()), data_key="type")
    title = fields.Str(required=True, validate=field_validate.Length(min=1, max=500, error="词条标题不能超过500字"))
    content = fields.Str(validate=field_validate.Length(max=1000, error="词条内容不能超过1000字"), load_default="")


class UpdateKnowledgeDetailSchema(Schema):
    title = fields.Str(
        required=False,
        load_default=None,
        validate=field_validate.Length(min=1, max=500, error="词条标题不能超过500字"),
    )
    content = fields.Str(validate=field_validate.Length(max=1000, error="词条内容不能超过1000字"), load_default=None)
    file_path = fields.Str(required=False, load_default=None, validate=OneOf([""]))


class ListSystemLogSchema(PaginationSchema):
    start = fields.Int(required=False, load_default=None)
    end = fields.Int(required=False, load_default=None)
    username = fields.Str(required=False, load_default=None, data_key="user_name")
    user_id = fields.Str(required=False, load_default=None)
    menu = fields.Str(required=False, load_default=None)
    subject = fields.Str(required=False, load_default=None)
    type = fields.Int(required=False, load_default=NafmiiEventType.ALL.value, validate=OneOf(NafmiiEventType.members()))
    status = fields.Int(
        required=False, load_default=NafmiiEventStatus.ALL.value, validate=OneOf(NafmiiEventStatus.members())
    )


class ExportSystemLogSchema(Schema):
    start = fields.Int(required=True)
    end = fields.Int(required=True)
