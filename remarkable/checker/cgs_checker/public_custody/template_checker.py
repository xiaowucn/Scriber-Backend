from remarkable.checker.checkers.conditions_checker import BaseConditionsChecker
from remarkable.plugins.cgs.rules.templates.public_custody import (
    PUBLIC_CUSTODY_MULTI_WITH_CONDITIONS,
    PUBLIC_MULTI_SENTENCE_OPTIONAL_TEMPLATES,
    PUBLIC_REPLACE_TEMPLATES,
)


class PublicCustodyTemplateChecker(BaseConditionsChecker):
    SCHEMA_NAME = "公募-托管协议"
    TEMPLATES = PUBLIC_CUSTODY_MULTI_WITH_CONDITIONS


class PublicCustodySingleWithRatioChecker(PublicCustodyTemplateChecker):
    TEMPLATES = PUBLIC_MULTI_SENTENCE_OPTIONAL_TEMPLATES

    def match_template(self, template, paragraphs=None, required=False, similarity_patterns=None):
        return self.match_template_multi_paragraphs(template, paragraphs, required)


class PublicCustodyReplaceTemplateChecker(PublicCustodyTemplateChecker):
    TEMPLATES = PUBLIC_REPLACE_TEMPLATES
