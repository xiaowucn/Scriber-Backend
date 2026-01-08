import json
import logging
from collections import defaultdict
from copy import copy, deepcopy

from networkx.utils.misc import groups

from remarkable.common.util import clean_txt
from remarkable.plugins.predict.common import get_element_candidates
from remarkable.predictor.base_prophet import BaseProphet, PredictorContext
from remarkable.predictor.predictor import SchemaPredictor
from remarkable.predictor.schema_answer import PredictorResult, PredictorResultGroup

logger = logging.getLogger(__name__)


class CmfSchemaPredictor(SchemaPredictor):
    def create_sub_predictors(self):
        path_key = json.dumps(self.schema.path + ["interface_model"], ensure_ascii=False)
        predictor_config = self.root_config.get(path_key, {"path": self.schema.path[:]})
        sub_predictors = [SchemaPredictor(self.schema, predictor_config, prophet=self.prophet)]
        return sub_predictors


class Prophet(BaseProphet):
    depends_root_predictor = False

    def __init__(self, prophet_config, mold, version_id=0, **kwargs):
        super().__init__(prophet_config, mold, version_id=version_id)
        self.root_predictor = CmfSchemaPredictor(self.root_schema, {"path": self.root_schema.path}, prophet=self)

    def parse_enum_value(self, predictor_result, schema):
        if self.enum_predictor:
            return self.enum_predictor.predict(predictor_result, schema)
        return None

    def get_enum_predictor(self):
        enum_classes = {}
        if predictor := (enum_classes.get(self._mold.name) or enum_classes.get(clean_txt(self._mold.name))):
            return predictor()

    def run_predict(self, **kwargs):
        crude_answer = kwargs["crude_answer"]
        pdfinsight_path = kwargs["pdfinsight_path"]
        pdfinsight_data = kwargs.get("pdfinsight_data")
        if kwargs.get("predict_excel"):
            self.predictor_context = PredictorContext(crude_answer, None, metadata=kwargs.get("metadata"))
        else:
            self.predictor_context = self._bind_context(
                crude_answer, pdfinsight_path, pdfinsight_data=pdfinsight_data, metadata=kwargs.get("metadata")
            )
        self.predict_answer()
        answer_items = self.collect_answer_items()

        return self.build_question_answer(answer_items)
