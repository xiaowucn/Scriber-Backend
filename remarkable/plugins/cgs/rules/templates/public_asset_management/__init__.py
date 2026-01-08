from remarkable.plugins.cgs.rules.templates.public_asset_management.template_with_multi_sentence_optional import (
    TEMPLATE_WITH_MULTI_SENTENCE_OPTIONALS,
)
from remarkable.plugins.cgs.rules.templates.public_asset_management.template_with_normal_condition import (
    TEMPLATE_WITH_MULTI_EXPRESSION,
)
from remarkable.plugins.cgs.rules.templates.public_asset_management.template_with_replace_condition import (
    TEMPLATE_WITH_REPLACE_CONDITIONS,
)
from remarkable.plugins.cgs.rules.templates.public_asset_management.template_with_sentence_multiple_compare import (
    TEMPLATE_WITH_SENTENCE_MULTIPLE_COMPARE,
)

PUBLIC_CUSTODY_MULTI_WITH_CONDITIONS = TEMPLATE_WITH_MULTI_EXPRESSION


# 多段同时拆分为多种表述
PUBLIC_MULTI_SENTENCE_OPTIONAL_TEMPLATES = TEMPLATE_WITH_MULTI_SENTENCE_OPTIONALS

# 根据条件替换模板
PUBLIC_REPLACE_TEMPLATES = TEMPLATE_WITH_REPLACE_CONDITIONS

# 段落至少匹配一次
PUBLIC_SENTENCE_TEMPLATES = TEMPLATE_WITH_SENTENCE_MULTIPLE_COMPARE
