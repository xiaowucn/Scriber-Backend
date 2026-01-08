import logging

from remarkable.common.pattern import MatchMulti, NeglectPattern
from remarkable.common.util import clean_txt
from remarkable.predictor.common_pattern import R_CONJUNCTION, R_LEFT_BRACKET, R_RIGHT_BRACKET
from remarkable.predictor.schema_answer import PredictorResult

logger = logging.getLogger(__name__)

PLATFORM_NEGLECT_PATTERN = NeglectPattern(
    match=MatchMulti.compile(
        r"直销",
        r"场内",
        operator=any,
    ),
    unmatch=MatchMulti.compile(
        r"非直销",
        rf"[{R_CONJUNCTION}](基金管理人)?(网上|官网|电子)?直销",
        rf"[{R_CONJUNCTION}]场内",
        rf"直销.{{1,2}}({R_LEFT_BRACKET}.*{R_RIGHT_BRACKET})?[{R_CONJUNCTION}]",
        rf"({R_LEFT_BRACKET}含.*直销.*{R_RIGHT_BRACKET})",
        operator=any,
    ),
)


def post_process_sale_platform(answers: list[dict[str, list[PredictorResult]]], **kwargs) -> list[dict]:
    """
    过滤销售平台
    """
    ret = []
    for answer in answers:
        sale_platform = answer.get("销售平台", [])
        for predictor_result in sale_platform:
            if PLATFORM_NEGLECT_PATTERN.search(clean_txt(predictor_result.text)):
                logger.debug(f"Neglect main column: {predictor_result.text}")
                break
        else:
            ret.append(answer)
    return ret
