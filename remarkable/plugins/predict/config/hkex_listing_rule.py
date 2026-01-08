# pylint: skip-file
import os
import re

import pandas as pd

from remarkable.config import project_root
from remarkable.plugins.predict.models.regex_pattern import PartialRegPredictor, RegPredictor, ScorePredictor
from remarkable.plugins.predict.predictor import AIAnswerPredictor

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

predictors = [
    {
        "path": ["B1", "Issue reason"],
        "model": "partial_text",
    },
    {
        "path": ["B2", "Class of equity securities"],
        "model": "partial_text",
    },
    {
        "path": ["B3", "Number of issued"],
        "model": "partial_text",
    },
    {
        "path": ["B4", "Issue price"],
        "model": "partial_text",
    },
    {
        "path": ["B5", "Net price"],
        "model": "partial_text",
    },
    {
        "path": ["B6", "Names of allottes"],
        "model": "partial_text",
    },
    {
        "path": ["B7", "Market price"],
        "model": "partial_text",
    },
    {
        "path": ["B8", "Detailed breakdown and description"],
        "model": "partial_text",
    },
    {
        "path": ["B9", "Detailed breakdown and description of utilized amount"],
        "model": "partial_text",
    },
    {
        "path": ["B10", "Use of proceeds"],
        "model": "partial_text",
    },
    {
        "path": ["B11", "Content"],
        "model": "regex_pattern",
        "patterns": [ScorePredictor({"table": 1, "paragraph": 1}, 2), RegPredictor(deny_regs, 1, is_positive=False)],
        "passed_result": 0,
    },
    {
        "path": ["B12", "Name"],
        "model": ["partial_text", "table_tuple_select"],
    },
    {
        "path": ["B12", "Interest or short position"],
        "model": ["partial_text", "table_tuple_select"],
    },
    {"path": ["B12", "Class"], "model": ["partial_text", "b12_class"], "dump_filename": "B12_Number of securities"},
    {
        "path": ["B12", "Number of securities"],
        "model": ["table_tuple_select"],
        "select_by": "column",
        "multi_elements": True,
    },
    {
        "path": ["B13", "Content"],
        "model": "regex_pattern",
        "patterns": [
            ScorePredictor({"table": 1, "paragraph": 1}, 2),
            RegPredictor(deny_regs, 1, is_positive=False),
        ],
        "passed_result": 0,
    },
    {
        "path": ["B14", "Pre-emptive right"],
        "model": "regex_pattern",
        "patterns": [
            ScorePredictor({"table": 1, "paragraph": 1}, 2),
            RegPredictor(deny_regs, 1, is_positive=False),
        ],
        "passed_result": 0,
    },
    {
        "path": ["B14", "Incorporated place"],
        "model": "partial_text",
    },
    {
        "path": ["B15", "Bank loans and overdrafts"],
        "model": ["table_tuple_select", "regex_pattern"],
        "patterns": [
            ScorePredictor({"table": 1, "paragraph": 1}, 2),
            RegPredictor(b15_neg_pattern, 2, include_non_paragraph=False),
        ],
        "passed_result": 1,
        "select_by": "both",
    },
    {
        "path": ["B15", "Other borrowings"],
        "model": ["table_tuple_select", "regex_pattern"],
        "patterns": [
            ScorePredictor({"table": 1, "paragraph": 1}, 2),
            RegPredictor(b15_neg_pattern, 2, include_non_paragraph=False),
        ],
        "passed_result": 1,
        "select_by": "both",
        "cell_neg_pattern": cell_neg_pattern,
    },
    {
        "path": ["B15", "Aggregate amount"],
        "model": ["table_tuple_select", "regex_pattern"],
        "patterns": [
            ScorePredictor({"table": 1, "paragraph": 1}, 2),
            RegPredictor(b15_neg_pattern, 2, include_non_paragraph=False),
        ],
        "passed_result": 1,
        "select_by": "both",
        "location_threshold": {
            "table": 0.1,
            "paragraph": 0.1,
        },
    },
    {
        "path": ["B16", "Content"],
        "model": "regex_pattern",
        "patterns": [
            ScorePredictor({"table": 1, "paragraph": 1}, 2),
            RegPredictor(deny_reg_with_not, 1, is_positive=False),
        ],
        "passed_result": 0,
    },
    {
        "path": ["B17", "Amount"],
        "model": ["table_tuple_select"],
        "select_by": "column",
        "multi_elements": True,
    },
    {
        "path": ["B18", "Amount"],
        "model": ["table_tuple_select"],
        "select_by": "column",
        "multi_elements": True,
    },
    {
        "path": ["B19", "Amount"],
        "model": ["table_tuple_select"],
        "select_by": "both",
        "multi_elements": True,
        "cell_neg_pattern": cell_neg_pattern,
        "header_pattern": re.compile(r"bonus|bonuses"),
    },
    {
        "path": ["B20", "Content"],
        "model": "regex_pattern",
        "patterns": [
            ScorePredictor({"table": 1, "paragraph": 1}, 2),
            RegPredictor(deny_reg_with_not, 1, is_positive=False),
        ],
        "passed_result": 0,
    },
    {
        "path": ["B21", "Content"],
        "model": "regex_pattern",
        "patterns": [
            ScorePredictor({"table": 1, "paragraph": 1}, 2),
            RegPredictor(deny_reg_with_not, 1, is_positive=False),
        ],
        "passed_result": 0,
    },
    {
        "path": ["B22", "Table"],
        "model": "score_filter",
        "threshold": 0.012,
    },
    {
        "path": ["B22", "Upper limit"],
        "model": "table_column_content",
    },
    {
        "path": ["B23", "Brief outline"],
        "model": "partial_text",
    },
    {"path": ["B23", "Pension scheme elsewhere"], "model": "table_tuple_select", "select_by": "both"},
    {
        "path": ["B24", "Detail of forfeited contributions"],
        "model": "regex_pattern",
        "patterns": [ScorePredictor({"table": 1, "paragraph": 1}, 2), RegPredictor(deny_regs, 1, is_positive=False)],
        "passed_result": 0,
    },
    {
        "path": ["B25", "Name of actuary"],
        "model": "partial_text",
    },
    {
        "path": ["B26", "Qualification of actuary"],
        "model": "partial_text",
    },
    {
        "path": ["B27", "Actuarial method "],
        "model": "partial_text",
    },  # NOTE: 注意此处应多个空格
    {
        "path": ["B28", "Description of actuarial assumptions"],
        "model": "regex_pattern",
        "patterns": [ScorePredictor({"table": 1, "paragraph": 1}, 2), RegPredictor(deny_regs, 1, is_positive=False)],
        "passed_result": 0,
    },
    {
        "path": ["B29", "Market value "],
        "model": ["table_tuple_select", "partial_text"],
        "select_by": "both",
    },  # NOTE: 注意此处应多个空格
    {"path": ["B30", "Level of funding"], "model": ["table_tuple_select", "partial_text"], "select_by": "both"},
    {
        "path": ["B31", "Comments"],
        "model": "regex_pattern",
        "patterns": [ScorePredictor({"table": 1, "paragraph": 1}, 2), RegPredictor(deny_regs, 1, is_positive=False)],
        "passed_result": 0,
    },
    {
        "path": ["B32", "Content"],
        "model": "regex_pattern",
        "patterns": [ScorePredictor({"table": 1, "paragraph": 1}, 2), RegPredictor(deny_regs, 1, is_positive=False)],
        "passed_result": 0,
    },
    {
        "path": ["B33", "Content"],
        "model": "regex_pattern",
        "patterns": [ScorePredictor({"table": 1, "paragraph": 1}, 2), RegPredictor(deny_regs, 1, is_positive=False)],
        "passed_result": 0,
    },
    {
        "path": ["B34", "Table"],
        "model": "score_filter",
        "threshold": 0.025,
    },
    {
        "path": ["B35", "Content"],
        "model": "regex_pattern",
        "patterns": [
            ScorePredictor({"table": 1, "paragraph": 1}, 2),
            RegPredictor(deny_regs, 1, is_positive=False),
            RegPredictor(b35_keyword_pattern, 2),
        ],
        "passed_result": 0,
    },
    {
        "path": ["B35", "Controlling interest"],
        "model": "table_tuple_select",
        "select_by": "column",
    },  # TODO: 还要筛选最大的那个
    {
        "path": ["B36", "Content"],
        "model": "regex_pattern",
        "patterns": [ScorePredictor({"table": 1, "paragraph": 1}, 2), RegPredictor(deny_regs, 1, is_positive=False)],
        "passed_result": 0,
    },
    {
        "path": ["B37", "Content"],
        "model": "regex_pattern",
        "patterns": [ScorePredictor({"table": 1, "paragraph": 1}, 2), RegPredictor(deny_regs, 1, is_positive=False)],
        "passed_result": 0,
    },
    {
        "path": ["B38", "Content"],
        "model": "regex_pattern",
        "patterns": [
            ScorePredictor({"table": 1, "paragraph": 1}, 2),
            PartialRegPredictor(deny_regs, 1, is_positive=False),
        ],
        "passed_result": 0,
    },
    {
        "path": ["B41", "Content"],
        "model": "regex_pattern",
        "patterns": [ScorePredictor({"table": 1, "paragraph": 1}, 2), RegPredictor(deny_regs, 1, is_positive=False)],
        "passed_result": 0,
    },
    {
        "path": ["B42", "Content"],
        "model": "regex_pattern",
        "patterns": [ScorePredictor({"table": 1, "paragraph": 1}, 2), RegPredictor(deny_regs, 1, is_positive=False)],
        "passed_result": 0,
    },
    {
        "path": ["B43", "Management contract"],  # TODO: 效果不好
        "model": "regex_pattern",
        "patterns": [
            ScorePredictor({"table": 1, "paragraph": 1}, 2),
            RegPredictor(deny_reg_with_not, 1, is_positive=False),
        ],
        "passed_result": 0,
    },
    {
        "path": ["B43", "Service contract"],
        "model": "regex_pattern",
        "patterns": [ScorePredictor({"table": 1, "paragraph": 1}, 2), RegPredictor(deny_regs, 1, is_positive=False)],
        "passed_result": 0,
    },
    {
        "path": ["B43", "Director list"],
        "model": "regex_pattern",
        "patterns": [ScorePredictor({"table": 1, "paragraph": 1}, 2), RegPredictor(deny_regs, 1, is_positive=False)],
        "passed_result": 0,
    },
    {
        "path": ["B44", "Content"],
        "model": "regex_pattern",
        "patterns": [ScorePredictor({"table": 1, "paragraph": 1}, 2), RegPredictor(deny_regs, 1, is_positive=False)],
        "passed_result": 0,
    },
    {
        "path": ["B45", "Percentage"],
        "model": ["partial_text", "table_tuple_select"],
        "neg_pattern": deny_reg_with_not,
    },
    {
        "path": ["B46", "Percentage"],
        "model": ["partial_text", "table_tuple_select"],
        "neg_pattern": deny_reg_with_not,
    },
    {
        "path": ["B47", "Percentage"],
        "model": ["partial_text", "table_tuple_select"],
        "neg_pattern": deny_reg_with_not,
    },
    {
        "path": ["B48", "Percentage"],
        "model": ["partial_text", "table_tuple_select"],
        "neg_pattern": deny_reg_with_not,
    },
    {
        "path": ["B49", "Content"],
        "model": "regex_pattern",
        "patterns": [ScorePredictor({"table": 1, "paragraph": 1}, 2), RegPredictor(deny_regs, 1, is_positive=False)],
        "passed_result": 0,
    },
    {
        "path": ["B50", "Content"],
        "model": "regex_pattern",
        "patterns": [
            ScorePredictor({"table": 1, "paragraph": 1}, 2),
            RegPredictor(deny_reg_with_less_than, 1, is_positive=False),
        ],
        "passed_result": 0,
    },
    {
        "path": ["B51", "Content"],
        "model": "regex_pattern",
        "patterns": [
            ScorePredictor({"table": 1, "paragraph": 1}, 2),
            RegPredictor(deny_reg_with_less_than, 1, is_positive=False),
        ],
        "passed_result": 0,
    },
    {
        "path": ["B52", "Ratio"],
        "model": ["partial_text", "table_tuple_select"],
        "cell_neg_pattern": cell_neg_pattern,
        "neg_pattern": re.compile(r"not|^0%"),
    },
    {
        "path": ["B53", "Content"],
        "model": "regex_pattern",
        "patterns": [
            ScorePredictor({"table": 1, "paragraph": 1}, 2),
            RegPredictor(b53_neg_pattern, 1, is_positive=False),
        ],
        "passed_result": 0,
    },
    {
        "path": ["B54", "Content"],
        "model": "regex_pattern",
        "patterns": [ScorePredictor({"table": 1, "paragraph": 1}, 2), RegPredictor(deny_regs, 1, is_positive=False)],
        "passed_result": 0,
    },
    {
        "path": ["B55", "Content"],
        "model": "regex_pattern",
        "patterns": [
            ScorePredictor({"table": 1, "paragraph": 1}, 2),
            RegPredictor(b55_neg_pattern, 1, is_positive=False),
        ],
        "passed_result": 0,
    },
    {
        "path": ["B56", "Content"],
        "model": "regex_pattern",
        "patterns": [ScorePredictor({"table": 1, "paragraph": 1}, 2), RegPredictor(deny_regs, 1, is_positive=False)],
        "passed_result": 0,
    },
    # {
    #     "path": ["B57", "Significant investments"],
    #     "model": "partial_text",
    #     "neg_pattern": b57_neg_pattern,
    #     "location_threshold": {
    #         "table": 0.05,
    #         "paragraph": 0.05,
    #     }
    # },
    {
        "path": ["B57", "Significant investments"],
        "model": "regex_pattern",
        "patterns": [
            ScorePredictor({"table": 1, "paragraph": 1}, 2),
            RegPredictor(b57_neg_pattern, 1, is_positive=False),
        ],
        "passed_result": 0,
        "location_threshold": {
            "table": 0.05,
            "paragraph": 0.05,
        },
    },
    # {"path": ["B58", "Summary of segmental information"], "model": "partial_text",},  # TODO: 取表头单元格，没有合适的模型
    {"path": ["B58", "Summary of segmental information"], "model": "segment_info"},
    {
        "path": ["B58", "Detail of segmental information"],
        "model": "regex_pattern",
        "patterns": [
            ScorePredictor({"table": 1, "paragraph": 1}, 2),
            RegPredictor(deny_regs, 1, is_positive=False),
        ],
        "passed_result": 0,
        "location_threshold": {
            "table": 0.3,
            "paragraph": 0.3,
        },
    },
    {
        "path": ["B59", "Content"],
        "model": "regex_pattern",
        "patterns": [
            ScorePredictor({"table": 1, "paragraph": 1}, 2),
            RegPredictor(deny_regs, 1, is_positive=False),
        ],
        "passed_result": 0,
    },
    {
        "path": ["B60", "Content"],
        "model": "regex_pattern",
        "patterns": [
            ScorePredictor({"table": 1, "paragraph": 1}, 2),
            RegPredictor(deny_reg_with_not, 1, is_positive=False),
        ],
        "passed_result": 0,
    },
    {
        "path": ["B61", "Content"],
        "model": "regex_pattern",
        "patterns": [
            ScorePredictor({"table": 1, "paragraph": 1}, 2),
            RegPredictor(deny_reg_with_not, 1, is_positive=False),
        ],
        "passed_result": 0,
    },
    {
        "path": ["B62", "Content"],
        "model": ["regex_pattern", "table_tuple_select"],
        "patterns": [
            ScorePredictor({"table": 1, "paragraph": 1}, 2),
            RegPredictor(deny_regs, 1, is_positive=False),
        ],
        "passed_result": 0,
        "select_by": "both",
        "multi_elements": True,
    },
    {
        "path": ["B63", "Number of options"],
        "model": ["table_tuple_select", "regex_pattern"],
        "patterns": [ScorePredictor({"table": 1, "paragraph": 1}, 2), RegPredictor(deny_reg_with_not, 0)],
        "passed_result": 1,
        "select_by": "column",
        "multi_elements": True,
    },
    {
        "path": ["B63", "Date of grant"],
        "model": ["table_tuple_select"],
        "select_by": "column",
        "multi_elements": True,
    },
    {
        "path": ["B63", "Vesting period"],
        "model": "regex_pattern",
        "patterns": [
            ScorePredictor({"table": 1, "paragraph": 1}, 2),
            RegPredictor(deny_regs, 1, is_positive=False),
        ],
        "passed_result": 0,
    },
    {
        "path": ["B63", "Exercise period"],
        "model": "regex_pattern",
        "patterns": [
            ScorePredictor({"table": 1, "paragraph": 1}, 2),
            RegPredictor(deny_regs, 1, is_positive=False),
        ],
        "passed_result": 0,
    },
    {
        "path": ["B63", "Exercise price"],
        "model": ["table_tuple_select"],
        "select_by": "column",
        "multi_elements": True,
    },
    {
        "path": ["B64", "Number of options"],
        "model": ["table_tuple_select", "regex_pattern"],
        "patterns": [
            ScorePredictor({"table": 1, "paragraph": 1}, 2),
            RegPredictor(deny_regs, 2, include_non_paragraph=False),
        ],
        "passed_result": 1,
        "select_by": "column",
        "multi_elements": True,
    },
    {
        "path": ["B64", "Date of grant"],
        "model": ["table_tuple_select"],
        "select_by": "column",
        "multi_elements": True,
    },
    {
        "path": ["B64", "Vesting period"],
        "model": "regex_pattern",
        "patterns": [
            ScorePredictor({"table": 1, "paragraph": 1}, 2),
            RegPredictor(deny_regs, 1, is_positive=False),
        ],
        "passed_result": 0,
    },
    {
        "path": ["B64", "Exercise period"],
        "model": "regex_pattern",
        "patterns": [
            ScorePredictor({"table": 1, "paragraph": 1}, 2),
            RegPredictor(deny_regs, 1, is_positive=False),
        ],
        "passed_result": 0,
    },
    {
        "path": ["B64", "Exercise price"],
        "model": ["table_tuple_select"],
        "select_by": "column",
        "multi_elements": True,
    },
    {
        "path": ["B64", "Closing price"],
        "model": ["table_tuple_select", "partial_text"],
        "select_by": "column",
        "multi_elements": True,
    },
    {
        "path": ["B64", "Beginning amount"],
        "model": ["table_tuple_select"],
        "select_by": "column",
        "cell_neg_pattern": cell_neg_pattern,
        "multi_elements": True,
    },
    {
        "path": ["B64", "Ending amount"],
        "model": ["table_tuple_select"],
        "select_by": "both",
        "multi_elements": True,
    },
    {
        "path": ["B65", "Number of options"],
        "model": ["table_tuple_select", "regex_pattern"],
        "patterns": [ScorePredictor({"table": 1, "paragraph": 1}, 2), RegPredictor(deny_regs, 0)],
        "passed_result": 1,
        "select_by": "column",
        "multi_elements": True,
        "cell_neg_pattern": cell_neg_pattern,
    },
    {
        "path": ["B65", "Exercise price"],
        "model": ["table_tuple_select"],
        "select_by": "column",
        "multi_elements": True,
    },
    {
        "path": ["B65", "Closing price"],
        "model": ["table_tuple_select", "partial_text"],
        "select_by": "column",
        "multi_elements": True,
    },
    {
        "path": ["B66", "Number of options"],
        "model": ["table_tuple_select", "regex_pattern"],
        "patterns": [
            ScorePredictor({"table": 1, "paragraph": 1}, 2),
            RegPredictor(deny_regs, 2, include_non_paragraph=False),
        ],
        "passed_result": 1,
        "cell_neg_pattern": cell_neg_pattern,
        "select_by": "column",
        "multi_elements": True,
    },
    {
        "path": ["B66", "Exercise price"],
        "model": ["table_tuple_select"],
        "select_by": "column",
        "multi_elements": True,
    },
    {
        "path": ["B67", "Number of options"],
        "model": ["table_tuple_select", "regex_pattern"],
        "patterns": [
            ScorePredictor({"table": 1, "paragraph": 1}, 2),
            RegPredictor(deny_regs, 2, include_non_paragraph=False),
        ],
        "passed_result": 1,
        "cell_neg_pattern": cell_neg_pattern,
        "select_by": "column",
        "multi_elements": True,
    },
    {
        "path": ["B68", "Content"],
        "model": "regex_pattern",
        "patterns": [ScorePredictor({"table": 1, "paragraph": 1}, 2), RegPredictor(deny_regs, 0, is_positive=False)],
        "passed_result": 0,
    },
    {
        "path": ["B69", "Content"],
        "model": "partial_text",
    },
    {
        "path": ["B70", "Amount"],
        "model": ["partial_text", "table_tuple_select"],
    },
    {
        "path": ["B70", "Period"],
        "model": ["partial_text", "table_tuple_select"],
    },
    {
        "path": ["B71", "Content"],
        "model": "regex_pattern",
        "patterns": [ScorePredictor({"table": 1, "paragraph": 1}, 2), RegPredictor(deny_regs, 0, is_positive=False)],
        "passed_result": 0,
    },
    {
        "path": ["B72", "Content"],
        "model": "regex_pattern",
        "patterns": [ScorePredictor({"table": 1, "paragraph": 1}, 2), RegPredictor(deny_regs, 0, is_positive=False)],
        "passed_result": 0,
    },
]

"""
阈值优先级：
1. predictor["location_threshold"]
2. rule_thd.json
3. ScorePredictor 初始化参数
"""


def update_threshold(predictors_config):
    rule_threshold_path = os.path.join(project_root, "data/mold_element_threshold/rule_thd.json")
    if not os.path.exists(rule_threshold_path):
        return predictors_config
    threshold_df = pd.read_json(rule_threshold_path)
    for index, predictor in enumerate(predictors_config):
        rule_name = "-".join(predictor["path"])
        current_rule_row = threshold_df[threshold_df["rule_name"] == rule_name]
        if current_rule_row.empty:
            stat_threshold = {}
        else:
            stat_threshold = {
                "table": max(current_rule_row["table"].iloc[0], 0.01),
                "paragraph": max(current_rule_row["paragraph"].iloc[0], 0.01),
            }
        if predictor.get("patterns") and isinstance(predictor["patterns"][0], ScorePredictor):
            if "location_threshold" in predictor:
                threshold = predictor["location_threshold"]
            elif stat_threshold:
                threshold = stat_threshold
            else:
                continue
            score_predictor = predictors_config[index]["patterns"][0]
            score_predictor.update_threshold(threshold)
            # print(f"load rule({rule_name}) threshold from {rule_threshold_path}")
        else:
            if "location_threshold" not in predictor and stat_threshold:
                predictor["location_threshold"] = stat_threshold
    return predictors_config


predictors = update_threshold(predictors)


class HKEXListingRulePredictor(AIAnswerPredictor):
    """港交所上市规则预测"""

    PREDICTORS = predictors

    def __init__(self, *args, **kwargs):
        kwargs["predictors"] = self.PREDICTORS
        kwargs["default_model"] = "empty"
        super(HKEXListingRulePredictor, self).__init__(*args, **kwargs)
