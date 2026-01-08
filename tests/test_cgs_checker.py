from unittest import TestCase

import attr

from remarkable.checker.cgs_checker.rule_checker import FundManagerInfoChecker
from remarkable.plugins.cgs.common.para_similarity import ParagraphSimilarity


@attr.s
class Answer:
    name = attr.ib()
    value = attr.ib()

    def get_related_paragraphs(self):
        return [{"text": self.value, "page": self.page, "chars": [], "index": 0, "outlines": self.outlines}]

    @property
    def page(self):
        return 1

    @property
    def outlines(self):
        return {1: [[0, 1, 0, 1]]}


class TestChecker(TestCase):
    def test_validate_field_only_by_company_info(self):
        name = "基金管理人概况-名称"
        answer = Answer(name, "test")
        text = "test"
        company_info = {
            "基金管理人概况-名称": {
                "matched": False,
                "text": "test1",
                "answer": answer,
                "ignore_check": False,
                "diff": ParagraphSimilarity(
                    paragraphs_left=answer.get_related_paragraphs(), paragraphs_right=[text], fill_paragraph=False
                ),
            }
        }
        checker = FundManagerInfoChecker({}, company_info)
        matched, reasons, suggestion = checker.check([name], validate_bond_info=True, validate_company_info=True)
        self.assertFalse(matched)
        self.assertEqual(1, len(reasons))
        self.assertEqual("请修改 test。", suggestion)

    def test_validate_field_by_all(self):
        name = "基金管理人概况-名称"
        address = "基金管理人概况-地址"
        name_answer = Answer(name, "test名称")
        address_answer = Answer(address, "test地址")
        test_name = "test"
        test_address = "test"
        company_info = {
            "基金管理人概况-名称": {
                "matched": False,
                "text": test_name,
                "answer": name_answer,
                "ignore_check": False,
                "diff": ParagraphSimilarity(
                    paragraphs_left=name_answer.get_related_paragraphs(),
                    paragraphs_right=[test_name],
                    fill_paragraph=False,
                ),
            },
        }
        bond_info = {
            "基金管理人概况-名称": {
                "matched": False,
                "text": test_name,
                "answer": name_answer,
                "ignore_check": False,
                "diff": ParagraphSimilarity(
                    paragraphs_left=name_answer.get_related_paragraphs(),
                    paragraphs_right=[test_name],
                    fill_paragraph=False,
                ),
            },
            "基金管理人概况-地址": {
                "matched": False,
                "text": test_address,
                "answer": address_answer,
                "ignore_check": False,
                "diff": ParagraphSimilarity(
                    paragraphs_left=address_answer.get_related_paragraphs(),
                    paragraphs_right=[test_address],
                    fill_paragraph=False,
                ),
            },
        }
        checker = FundManagerInfoChecker(bond_info, company_info)
        matched, reasons, suggestion = checker.check(
            [name, address], validate_bond_info=True, validate_company_info=True
        )
        self.assertFalse(matched)
        self.assertEqual(2, len(reasons))
        self.assertEqual("请修改 test名称。\n请修改 test地址。", suggestion)

    def test_validate_empty_field_by_all(self):
        name = "基金管理人概况-名称"
        company_info = {
            "基金管理人概况-名称": {
                "matched": False,
                "text": "test",
                "answer": None,
                "ignore_check": False,
                "diff": None,
            }
        }
        bond_info = {}
        checker = FundManagerInfoChecker(bond_info, company_info)
        matched, reasons, suggestion = checker.check([name], validate_bond_info=True, validate_company_info=True)
        self.assertFalse(matched)
        self.assertEqual(1, len(reasons))
        self.assertEqual(f"请补充{name}", suggestion)
