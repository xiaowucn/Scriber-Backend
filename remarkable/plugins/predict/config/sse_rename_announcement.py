from remarkable.plugins.predict.predictor import AIAnswerPredictor

# from remarkable.plugins.predict.models.model_base import SPECIAL_ATTR_PATTERNS

predictors = [
    # {
    #     "path": ["证券代码"],
    #     "model": "partial_text",
    #     "regs": [r"\d+"]
    # },
    # {
    #     "path": ["证券简称"],
    #     "model": "partial_text",
    # },
    # {
    #     "path": ["公告编号"],
    #     "model": "partial_text",
    #     "regs": [r"临[\d-]+号"]
    # },
    # {
    #     "path": ["变更后的证券简称"],
    #     "model": "partial_text",
    # },
    # {
    #     "path": ["变更日期"],
    #     "model": "partial_text",
    #     "regs": SPECIAL_ATTR_PATTERNS['date']
    # },
    # {
    #     "path": ["公告日"],
    #     "model": "partial_text",
    #     "regs": SPECIAL_ATTR_PATTERNS['date']
    # },
    # {
    #     "path": ["产品基本信息", "风险等级"],
    #     "model": "partial_text",
    #     "regs": [r"【(?P<dst>R\d+)】"]
    # },
]


class SSERemaneAnnouncementPredictor(AIAnswerPredictor):
    """上交所 变更证券简称公告信息抽取POC"""

    def __init__(self, *args, **kwargs):
        kwargs["predictors"] = predictors
        kwargs["default_model"] = "partial_text"
        super(SSERemaneAnnouncementPredictor, self).__init__(*args, **kwargs)
