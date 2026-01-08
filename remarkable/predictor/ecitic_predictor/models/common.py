from remarkable.common.pattern import PatternCollection
from remarkable.predictor.common_pattern import R_COLON

R_SPECIAL_TIPS = PatternCollection(rf"^特别(.示|说明)([{R_COLON}]|$)")
