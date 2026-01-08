from unittest import TestCase

from remarkable.checker.checkers.conditions_checker import BaseConditionsChecker
from remarkable.plugins.cgs.common.enum_utils import TemplateCheckTypeEnum
from remarkable.plugins.cgs.common.template_condition import TemplateName
from remarkable.plugins.cgs.rules.templates import public_asset_management, public_custody, public_fund

NORMAL_CONDITION_TEMPLATES = (
    public_asset_management.PUBLIC_CUSTODY_MULTI_WITH_CONDITIONS
    + public_custody.PUBLIC_CUSTODY_MULTI_WITH_CONDITIONS
    + public_fund.PUBLIC_TEMPLATE_MATCH_ANY
    + public_fund.PUBLIC_MULTI_WITH_CONDITIONS
)
# 模板内需要替换内容或调整顺序
REPLACE_CONDITION_TEMPLATES = (
    public_asset_management.PUBLIC_REPLACE_TEMPLATES
    + public_custody.PUBLIC_REPLACE_TEMPLATES
    + public_fund.PUBLIC_REPLACE_TEMPLATES
)
# 多个句子存在多种表述
MULTIPLE_SENTENCES_WITH_CONDITION_TEMPLATES = (
    public_asset_management.PUBLIC_MULTI_SENTENCE_OPTIONAL_TEMPLATES
    + public_custody.PUBLIC_MULTI_SENTENCE_OPTIONAL_TEMPLATES
    + public_fund.PUBLIC_MULTI_SENTENCE_OPTIONAL_TEMPLATES
)
# 单个句子匹配多次
SINGLE_SENTENCE_MULTIPLE_COMPARE_TEMPLATES = public_asset_management.PUBLIC_SENTENCE_TEMPLATES


class TestRuleStructure(TestCase):
    @classmethod
    def check_error_conditions_name(cls, template_item):
        if "condition" in template_item:
            print("Error: The condition key of the template should be written as conditions")
            return False
        return True

    @classmethod
    def check_template_name(cls, template):
        if template["name"] not in (TemplateName.EDITING_NAME, TemplateName.LAW_NAME) or template[
            "content_title"
        ] not in (TemplateName.EDITING_TITLE, TemplateName.LAW_TITLE):
            print("Error: Template name error")
            return False
        return True

    @classmethod
    def check_replace_template_structure(cls, template_item):
        check_type = template_item["type"]
        if not hasattr(BaseConditionsChecker, f"extract_template_by_{check_type}"):
            print(f"Error: Class BaseConditionsChecker has no extract_template_by_{check_type} method")
            return False
        if check_type == TemplateCheckTypeEnum.INNER_RECOMBINATION:
            for condition in template_item["rules"].values():
                for check_pattern in condition["patterns"]:
                    if not isinstance(check_pattern, dict):
                        print("Error: Check inner_recombination structure, patterns should be configured as dict")
                        return False
        elif check_type == TemplateCheckTypeEnum.RECOMBINATION:
            if len(template_item["patterns"]) != len(template_item["items"]):
                print("Error: Check recombination structure, check template patterns or items")
                return False
        elif check_type == TemplateCheckTypeEnum.INNER_REFER:
            for condition in template_item["rules"].values:
                if (
                    "refer_chapters" in condition and not condition["refer_chapters"]["chapters"]
                ) or "default" not in condition:
                    print("Error: Check inner_refer structure, check template patterns or items")
                    return False
        elif check_type == TemplateCheckTypeEnum.SINGLE_SELECT:
            for condition in template_item["rules"].values:
                if "para_pattern" not in condition or "default" not in condition:
                    print("Error: Check inner_refer structure, check template patterns or items")
                    return False
        elif check_type == TemplateCheckTypeEnum.CHAPTER_COMBINATION:
            if len(template_item["patterns"]) != len(template_item["items"]) != len(template_item["child_items"]):
                print("Error: Check chapter_recombination structure, check template patterns or items")
                return False

        return cls.check_common_structure(template_item["items"])

    @classmethod
    def check_single_optional_structure(cls, template_item):
        # single_optional内最多一个无条件的模板对象，且必须在最后
        without_condition_item = 0
        if len(template_item["single_optional"]) == 1:
            print("Error: The number of unconditional templates should be greater than 1")
            return False
        for child_item in template_item["single_optional"]:
            if not cls.check_error_conditions_name(child_item):
                return False
            if not child_item.get("conditions"):
                without_condition_item += 1
            if without_condition_item > 1:
                print("Error: Only one unconditional template can be configured")
                return False
            assert cls.check_common_structure(child_item)
        if without_condition_item == 1 and template_item["single_optional"][-1].get("conditions"):
            print("Error: Unconditional templates should be at the end")
            return False

        return True

    @classmethod
    def check_common_structure(cls, template_items, ignore_unconditional=False):
        # 通用检查
        # items内子项可为str、list、dict
        result = True
        if not template_items:
            print("Error: The content cannot be empty")
            return False
        for item in template_items:
            if isinstance(item, str):
                pass
            elif isinstance(item, list):
                if any(not isinstance(val, str) for val in item) or len(item) <= 1:
                    print("Error: At least two templates with multiple expressions")
                    return False
            elif isinstance(item, dict):
                assert cls.check_error_conditions_name(item)
                if item.get("type") in TemplateCheckTypeEnum.member_values():
                    assert cls.check_replace_template_structure(item)
                elif "single_optional" in item:
                    assert cls.check_single_optional_structure(item)
                elif "conditions" in item:
                    result &= cls.check_common_structure(item["items"])
                else:
                    if ignore_unconditional:
                        continue
                    print("Error: If the template is unconditional, it should be set to string or list")
                    return False
            else:
                print("Error: The template structure supports only string、list、dict")
                return False
        return result

    def test_normal_condition_template(self):
        # 普通条件
        for base_template in NORMAL_CONDITION_TEMPLATES + REPLACE_CONDITION_TEMPLATES:
            for template in base_template["templates"]:
                assert self.check_template_name(template)
                assert self.check_common_structure(template["items"]), base_template["label"]

    def test_multiple_sentence_template(self):
        # 多个句子存在多种表述
        for base_template in MULTIPLE_SENTENCES_WITH_CONDITION_TEMPLATES:
            assert any(len(template["items"]) > 1 for template in base_template["templates"]), base_template["label"]
            for template in base_template["templates"]:
                assert self.check_template_name(template)
                assert self.check_common_structure(template["items"], ignore_unconditional=True), base_template["label"]

    @classmethod
    def check_single_sentence_structure(cls, template_items):
        if len(template_items) != 1:
            return False
        if not cls.check_common_structure(template_items):
            return False
        item = template_items[0]
        if not isinstance(item, dict):
            return True
        if "single_optional" in item:
            for child_item in item["single_optional"]:
                if cls.check_single_sentence_structure([child_item]):
                    continue
                return False
            return True
        return cls.check_single_sentence_structure(item["items"])

    def test_single_sentence_multiple_compare_template(self):
        # 单个句子匹配多次
        for base_template in SINGLE_SENTENCE_MULTIPLE_COMPARE_TEMPLATES:
            for template in base_template["templates"]:
                assert self.check_template_name(template)
                assert self.check_single_sentence_structure(template["items"]), base_template["label"]
