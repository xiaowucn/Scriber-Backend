# -*- coding: utf-8 -*-
import re

common_deny_pattern = r"no(?! doubt)|neither|nor|none|nil(?!\))|N\.M\."

deny_regs = re.compile(rf"\b(?P<dst>({common_deny_pattern}))\b", re.I)
deny_reg_with_not = re.compile(rf"\b(?P<dst>(insufficient|not|{common_deny_pattern}))\b", re.I)
deny_reg_with_less_than = re.compile(rf"\b(?P<dst>({common_deny_pattern}|less than))\b", re.I)
b35_keyword_pattern = re.compile(r"\b(?P<dst>(ultimate?\s+(parent|hold(ing)?)|controll?(ing)?\s+shareholder))\b")
b57_neg_pattern = re.compile(r"(no|not).*? (significant )?(investments?|events|material acquisitions)")

b15_neg_pattern = re.compile(r"(?:no|not)[\w\s]*? (borrowings|bank loans?)")
b55_neg_pattern = re.compile(r"not?[\w\s]* contingent liabilities(?![\w\s]*not[\w\s]*\.)")
b53_neg_pattern = re.compile(r"\b(?P<dst>(no|neither|nor|none|N\.M\.))\b", re.I)
cell_neg_pattern = re.compile(r"—|–|N/A|^0(?!.)|^0%|not applicable|nil", re.I)


predictor_options = [
    {"path": ["B1", "Issue reason"], "models": [{"name": "partial_text"}]},
    {
        "path": ["B11", "Content"],
        "models": [
            {
                "name": "regex_pattern",
                "matchers": [{"is_positive": False, "stop_value": 1, "pattern": deny_regs}],
                "predict_result": 2,
                "passed_result": 0,
            }
        ],
    },
    {"path": ["B12", "Name"], "models": [{"name": "partial_text"}, {"name": "table_tuple_select"}]},
    {
        "path": ["B12", "Class"],
        "models": [{"name": "partial_text"}, {"name": "b12_class"}],
        "depends": ["Number of securities"],
    },
    {"path": ["B12", "Number of securities"], "models": [{"name": "table_tuple_select", "select_by": "column"}]},
    {
        "path": ["B13", "Content"],
        "models": [
            {
                "name": "regex_pattern",
                "matchers": [{"is_positive": False, "stop_value": 1, "pattern": deny_regs}],
                "predict_result": 2,
                "passed_result": 0,
            },
        ],
    },
]


prophet_config = {"depends": {"B1": ["B12"]}, "merge_schema_answers": True, "predictor_options": predictor_options}
