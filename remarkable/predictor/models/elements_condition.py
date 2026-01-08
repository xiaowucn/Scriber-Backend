from remarkable.predictor.models.syllabus_based import SyllabusBased
from remarkable.predictor.mold_schema import SchemaItem
from remarkable.predictor.schema_answer import PredictorResult


class ElementsCondition(SyllabusBased):
    # 通过条件模型判断是否继续用提取模型提取

    def __init__(self, options: dict, schema: SchemaItem, predictor):
        super().__init__(options, schema, predictor=predictor)
        # 条件模型
        self.elements_condition_name = self.get_config("elements_condition_model", "syllabus_elt_v2")
        self.elements_condition_config = self.get_config("elements_condition_config", {})
        self.elements_condition_model = self.gen_model(self.elements_condition_name, self.elements_condition_config)
        # 提取模型 目前只支持段落
        self.elements_extract_name = self.get_config("elements_extract_model", "partial_text")
        self.elements_extract_config = self.get_config("elements_extract_config", {})
        self.elements_extract_model = self.gen_model(self.elements_extract_name, self.elements_extract_config)

    def train(self, dataset, **kwargs):
        self.elements_condition_model.train(dataset, **kwargs)
        self.model_data["elements_condition"] = self.elements_condition_model.model_data
        self.elements_extract_model.train(dataset, **kwargs)
        self.model_data["extract"] = self.elements_extract_model.model_data

    def load_model_data(self):
        self.model_data = self.predictor.model_data.get(self.name, {})
        self.elements_condition_model.model_data = self.model_data["elements_condition"]
        self.elements_extract_model.model_datam = self.model_data["extract"]

    def predict_schema_answer(self, elements) -> list[dict[str, list[PredictorResult]]]:
        self.load_model_data()
        answer_results = []
        if self.elements_condition_model.is_meet_condition(elements):
            answer_results = self.elements_extract_model.predict_schema_answer(elements)
        return answer_results
