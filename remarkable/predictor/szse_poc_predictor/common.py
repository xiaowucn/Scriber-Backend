from collections import defaultdict

from remarkable.common.util import clean_txt


def reorganize_preset_answer(answer_results, sub_schemas):
    """
    重组答案 按照报告期分组和下一级schema字段分组
    原始答案 answer_results
    [
        {
            '报告期': [PredictorResult ],
            '流动资产': [PredictorResult ],
        },
        {
            '报告期': [PredictorResult],
            '非流动资产': [PredictorResult],
        },
        ...
    ]
    --->
    重组后答案 answer
        {
        '2020.09.30': {
            {
                '报告期': [PredictorResult],
                '流动资产': [PredictorResult, ],
                '非流动资产': [PredictorResult, ],
                ...
            },
        },
        '2019.12.31': {
            {
                '报告期': [PredictorResult],
                '流动资产': [PredictorResult, ],
                '非流动资产': [PredictorResult, ],
                ...
            },
        },
        ...
    }
    """
    answers = defaultdict(dict)
    for answer_result in answer_results:
        report_period_answer = answer_result.get("报告期")
        if not report_period_answer:
            continue
        report_period = clean_txt(report_period_answer[0].text)
        answers[report_period] = defaultdict(list)
        answers[report_period]["报告期"] = report_period_answer
    for sub_schema in sub_schemas:
        for answer_result in answer_results:
            report_period_answer = answer_result.get("报告期")
            if not report_period_answer:
                continue
            report_period = clean_txt(report_period_answer[0].text)
            for key, item in answer_result.items():
                if key == sub_schema:
                    answers[report_period][sub_schema].extend(item)
    return answers
