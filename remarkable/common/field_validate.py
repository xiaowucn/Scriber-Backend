from webargs import validate


class Length(validate.Length):
    message_min = "长度小于 {min}"
    message_max = "长度大于 {max}"
    message_all = "长度必须在 {min} 和 {max} 之间"
    message_equal = "长度必须为 {equal}"


class OneOf(validate.OneOf):
    default_message = "必须是以下选项之一: {choices}"


class URL(validate.URL):
    default_message = "无效的 URL"


class Range(validate.Range):
    message_min = "必须{min_op} {{min}}"
    message_max = "必须{max_op} {{max}}"
    message_all = "必须{min_op} {{min}} 且 {max_op} {{max}}"

    message_gte = "大于或等于"
    message_gt = "大于"
    message_lte = "小于或等于"
    message_lt = "小于"


class Equal(validate.Equal):
    default_message = "必须等于 {other}"


class Regexp(validate.Regexp):
    default_message = "字符串不符合预期的格式"
