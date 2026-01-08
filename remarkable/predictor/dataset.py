from remarkable.plugins.predict.answer import AnswerReader


class DatasetItem:
    def __init__(self, path: list[str], data: dict, answer: AnswerReader, fid: int, predict_answer=None):
        self.path = path
        self.data = data
        self.answer = answer
        self.fid = fid
        self.predict = predict_answer
