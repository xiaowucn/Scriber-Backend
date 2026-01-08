from remarkable.common.util import clean_txt
from remarkable.predictor.base_prophet import BaseProphet
from remarkable.predictor.predictor import JudgeByRegex


class PrivateFundContract(JudgeByRegex):
    col_patterns = {}

    multi_answer_col_patterns = {}


class Prophet(BaseProphet):
    def parse_enum_value(self, predictor_result, schema):
        if self.enum_predictor:
            return self.enum_predictor.predict(predictor_result, schema)
        return None

    def get_enum_predictor(self):
        enum_classes = {}
        if predictor := (enum_classes.get(self._mold.name) or enum_classes.get(clean_txt(self._mold.name))):
            return predictor()
