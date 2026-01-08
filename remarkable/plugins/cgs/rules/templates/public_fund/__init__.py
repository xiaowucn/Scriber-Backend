from remarkable.plugins.cgs.rules.templates.public_fund.public_normal import TEMPLATE_MATCH_ANY
from remarkable.plugins.cgs.rules.templates.public_fund.template_with_multi_expression import (
    TEMPLATE_WITH_MULTI_EXPRESSION,
)
from remarkable.plugins.cgs.rules.templates.public_fund.template_with_multi_sentence_optional import (
    TEMPLATE_WITH_MULTI_SENTENCE_OPTIONALS,
)
from remarkable.plugins.cgs.rules.templates.public_fund.template_with_normal_condition import (
    TEMPLATE_WITH_NORMAL_CONDITIONS,
)
from remarkable.plugins.cgs.rules.templates.public_fund.template_with_normal_condition_u1 import (
    TEMPLATE_WITH_MULTI_EXPRESSION_U1,
)
from remarkable.plugins.cgs.rules.templates.public_fund.template_with_normal_condition_u2 import (
    TEMPLATE_WITH_NORMAL_CONDITION_U2,
)
from remarkable.plugins.cgs.rules.templates.public_fund.template_with_replace_condition import (
    TEMPLATE_WITH_REPLACE_CONDITIONS,
)
from remarkable.plugins.cgs.rules.templates.public_fund.template_with_value_condition import (
    TEMPLATE_WITH_VALUE_CONDITIONS,
)

# 无条件类型
PUBLIC_TEMPLATE_MATCH_ANY = TEMPLATE_MATCH_ANY

# 多段同时拆分为多种表述
PUBLIC_MULTI_SENTENCE_OPTIONAL_TEMPLATES = TEMPLATE_WITH_MULTI_SENTENCE_OPTIONALS

# 根据条件替换模板
PUBLIC_REPLACE_TEMPLATES = TEMPLATE_WITH_REPLACE_CONDITIONS

# 单独段落存在多种表述或存在条件判断
PUBLIC_MULTI_WITH_CONDITIONS = (
    TEMPLATE_WITH_NORMAL_CONDITIONS
    + TEMPLATE_WITH_VALUE_CONDITIONS
    + TEMPLATE_WITH_MULTI_EXPRESSION
    + TEMPLATE_WITH_MULTI_EXPRESSION_U1
    + TEMPLATE_WITH_NORMAL_CONDITION_U2
)

PUBLIC_LAW_SOURCE = "法规来源：《证券投资基金基金合同填报指引第1、2、3号》（证监会201104）"
