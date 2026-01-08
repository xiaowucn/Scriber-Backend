from remarkable.predictor.models.syllabus_based import SyllabusBased
from remarkable.predictor.mold_schema import SchemaItem
from remarkable.predictor.schema_answer import PredictorResult


class ElementsCollectorBased(SyllabusBased):
    """
    确定elements范围的模型 与 提取模型,可分别配置
    elements_collect_model需实现.collect_elements() -> List[List[dict]] 方法
    SyllabusBased的抽象, 考虑将SyllabusBased重构为CollectElementsBased的子类
    """

    def __init__(self, options: dict, schema: SchemaItem, predictor):
        super().__init__(options, schema, predictor=predictor)
        self.elements_collect_name = self.get_config("elements_collect_model", "syllabus_elt_v2")  # 元素块定位模型
        self.elements_collect_config = self.get_config("elements_collect_config", {})  # 元素块定位模型的配置
        self.elements_collect_model = self.gen_model(self.elements_collect_name, self.elements_collect_config)
        self.is_table_model_assigned = bool(self.get_config("table_model"))  # 是否指定了表格模型

        # {'match_all_fields':  False}  当满足条件时才激活模型, match_all_fields 所有字段都匹配上
        self.active_model = self.get_config("active_model", {})

    def train(self, dataset, **kwargs):
        self.elements_collect_model.train(dataset, **kwargs)
        self.model_data["elements_collect"] = self.elements_collect_model.model_data
        self.para_model.train(dataset, **kwargs)
        self.model_data["paragraph"] = self.para_model.model_data
        self.table_model.train(dataset, **kwargs)
        self.model_data["table"] = self.table_model.model_data
        self.general_model.train(dataset, **kwargs)
        self.model_data["general"] = self.general_model.model_data

    def load_model_data(self):
        self.model_data = self.predictor.model_data.get(self.name, {})
        self.elements_collect_model.model_data = self.model_data.get("elements_collect", {})
        self.para_model.model_data = self.model_data.get("paragraph", {})
        self.table_model.model_data = self.model_data.get("table", {})
        self.general_model.model_data = self.model_data.get("general", {})

    def after_predict(self, answer_results):
        if not (self.active_model and self.active_model.get("match_all_fields")):
            return answer_results

        columns = set()
        for item in answer_results:
            columns.update(item.keys())

        if columns != set(self.columns):
            return []

        return answer_results

    def predict_schema_answer(self, elements) -> list[dict[str, list[PredictorResult]]]:
        self.load_model_data()

        answer_results = []
        for elements_block in self.elements_collect_model.collect_elements(elements):  # 确定元素块范围
            if self.general_config:
                answer_results.extend(self.general_model.predict(elements_block))
                continue

            same_type_elements = []
            pre_elt_type = None
            for element in elements_block:
                ele_type = element["class"]
                if ele_type not in ["PARAGRAPH", "TABLE"]:
                    continue

                if ele_type == "TABLE" and not self.is_table_model_assigned:  # 没有指定表格模型时,将表格按段落处理
                    paragraphs = self.get_paragraphs_from_table(element)
                    same_type_elements.extend(paragraphs)
                    ele_type = "PARAGRAPH"
                    pre_elt_type = ele_type
                    continue

                if pre_elt_type and pre_elt_type != ele_type:
                    if pre_elt_type == "PARAGRAPH":
                        answer_results.extend(self.para_model.predict(same_type_elements))
                    elif pre_elt_type == "TABLE":
                        answer_results.extend(self.table_model.predict(same_type_elements))
                    same_type_elements = []
                same_type_elements.append(element)
                pre_elt_type = ele_type

            if pre_elt_type == "PARAGRAPH":
                answer_results.extend(self.para_model.predict(same_type_elements))
            elif pre_elt_type == "TABLE":
                answer_results.extend(self.table_model.predict(same_type_elements))

        answer_results = self.after_predict(answer_results)

        return answer_results
