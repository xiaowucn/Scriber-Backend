from remarkable.checker.checkers.conditions_checker import BaseConditionsChecker
from remarkable.plugins.cgs.common.enum_utils import ConvertContentEnum
from remarkable.plugins.cgs.rules.templates.public_fund import (
    PUBLIC_LAW_SOURCE,
    PUBLIC_MULTI_SENTENCE_OPTIONAL_TEMPLATES,
    PUBLIC_MULTI_WITH_CONDITIONS,
    PUBLIC_REPLACE_TEMPLATES,
    PUBLIC_TEMPLATE_MATCH_ANY,
)


class PublicMultiWithConditionsChecker(BaseConditionsChecker):
    SCHEMA_NAME = "公募-基金合同"
    TEMPLATES = PUBLIC_MULTI_WITH_CONDITIONS
    IGNORE_EXTRA_PARA = True
    CONVERT_TYPES = ConvertContentEnum.member_values()
    SOURCE = PUBLIC_LAW_SOURCE


class PublicNormalTemplateChecker(PublicMultiWithConditionsChecker):
    TEMPLATES = PUBLIC_TEMPLATE_MATCH_ANY


class PublicSingleWithRatioChecker(PublicMultiWithConditionsChecker):
    """仅针对最外层多段同时存在多种表述模式，
    example：
        表述1：段1、段2、段3
        表述2：段1、段2、段3
    如某段存在多种表述，则按父类逻辑处理
    """

    TEMPLATES = PUBLIC_MULTI_SENTENCE_OPTIONAL_TEMPLATES

    def match_template(self, template, paragraphs=None, required=False, similarity_patterns=None):
        return self.match_template_multi_paragraphs(template, paragraphs, required, similarity_patterns)


class PublicReplaceTemplateChecker(PublicMultiWithConditionsChecker):
    TEMPLATES = PUBLIC_REPLACE_TEMPLATES
