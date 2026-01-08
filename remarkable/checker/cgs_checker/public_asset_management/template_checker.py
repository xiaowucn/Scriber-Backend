from remarkable.checker.checkers.conditions_checker import BaseConditionsChecker, BaseSentenceMultipleChecker
from remarkable.plugins.cgs.rules.templates.public_asset_management import (
    PUBLIC_CUSTODY_MULTI_WITH_CONDITIONS,
    PUBLIC_MULTI_SENTENCE_OPTIONAL_TEMPLATES,
    PUBLIC_REPLACE_TEMPLATES,
    PUBLIC_SENTENCE_TEMPLATES,
)


class PublicAssetManagementTemplateChecker(BaseConditionsChecker):
    SCHEMA_NAME = "公募-资产管理合同"
    TEMPLATES = PUBLIC_CUSTODY_MULTI_WITH_CONDITIONS
    IGNORE_EXTRA_PARA = True


class PublicAssetSingleWithRatioChecker(PublicAssetManagementTemplateChecker):
    TEMPLATES = PUBLIC_MULTI_SENTENCE_OPTIONAL_TEMPLATES

    def match_template(self, template, paragraphs=None, required=False, similarity_patterns=None):
        return self.match_template_multi_paragraphs(template, paragraphs, required)


class PublicAssetReplaceTemplateChecker(PublicAssetManagementTemplateChecker):
    TEMPLATES = PUBLIC_REPLACE_TEMPLATES


class PublicAssetSentenceTemplateChecker(BaseSentenceMultipleChecker):
    SCHEMA_NAME = "公募-资产管理合同"
    TEMPLATES = PUBLIC_SENTENCE_TEMPLATES
    IGNORE_EXTRA_PARA = True
