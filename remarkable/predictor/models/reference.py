from copy import copy
from typing import Any, Callable

from remarkable.predictor.dataset import DatasetItem
from remarkable.predictor.models.base_model import BaseModel
from remarkable.predictor.mold_schema import SchemaItem


def get_first_value(data: dict):
    """
    取字典的第一个value
    """
    for value in data.values():
        return value


class Reference(BaseModel):
    def __init__(self, options: dict, schema: SchemaItem, predictor=None):
        super().__init__(options, schema, predictor=predictor)
        assert self.from_paths

    @property
    def predictors(self) -> dict[str, Any]:
        return {predictor.schema_name: predictor for predictor in self.predictor.prophet.predictors}

    @property
    def from_paths(self) -> list[str]:
        from_path = self.get_config("from_path")
        if isinstance(from_path, str):
            return [from_path]
        return from_path

    @property
    def model_ids(self) -> list[str] | None:
        """
        只要指定index的model的结果
        """
        return self.get_config("model_ids")

    @property
    def share_type(self):
        """无需配置，由`GroupBased`动态设置"""
        share_type = self.config["share_type"]
        if share_type not in ["option", "award"]:
            raise ValueError(f"share_type should be option or award, but got {share_type}")
        return share_type

    @property
    def share_group(self):
        """无需配置，由`GroupBased`动态设置"""
        return self.get_config("share_group")

    @property
    def correct_group_keys(self) -> set[str]:
        """无需配置，由`GroupBased`动态设置"""
        return self.get_config("correct_group_keys")

    @property
    def incorrect_group_keys(self) -> set[str]:
        """无需配置，由`GroupBased`动态设置"""
        return self.get_config("incorrect_group_keys")

    @property
    def only_reference_crude_elements(self):
        return self.get_config("only_reference_crude_elements", False)

    @property
    def filter_results_function(self) -> Callable | None:  # noqa: UP006
        """
        基于关联规则的结果元素块， 用函数filter_results_function对元素块结果做二次处理
        """
        return self.get_config("filter_results_function")

    def train(self, dataset: list[DatasetItem], **kwargs):
        pass

    def extract_feature(self, elements, answer):
        pass

    def predict_schema_answer(self, elements):
        predictor = self.predictors.get(self.from_paths[0])
        if not predictor:
            return []

        models = self.get_models(predictor)
        if not models:
            return []

        results = []
        # TODO 考虑关联顺序，如果被关联的字段后执行，就不能直接取已有答案
        if not self.model_ids and not self.correct_group_keys and len(predictor.answer_groups) == 1:
            # 未配置model_ids时，直接从answer_groups中取答案
            for predictor_result in self.get_common_predictor_results(get_first_value(predictor.answer_groups)):
                new_result = copy(predictor_result)
                new_result.schema = self.schema
                results.append(new_result)
        else:
            crude_elements = predictor.get_candidate_elements(self.from_paths)
            # 考虑非初步定位的元素
            if not self.only_reference_crude_elements:
                crude_elements += [
                    elem for elem in elements if elem["index"] not in (e["index"] for e in crude_elements)
                ]
            for model in models:
                res_list = model.predict(crude_elements)
                if not res_list:
                    continue
                results.extend([copy(res) for res in self.get_common_predictor_results(res_list)])
                # 如果基准规则的答案不在指定的model_ids中，直接返回空
                if self.model_ids and (not model.model_id or model.model_id not in self.model_ids):
                    return []
                if self.predictor.pick_answer_strategy == "single":
                    break
        return results

    def get_models(self, predictor):
        models = predictor.models
        # 校验model_id配置
        if self.model_ids:
            has_id_models = [model for model in models if model.model_id and model.model_id in self.model_ids]
            ref_model_ids = {model.model_id for model in has_id_models}
            if not set(self.model_ids).issubset(ref_model_ids):
                raise Exception(
                    f"{self.from_paths} lack models whose `model_id` are: {set(self.model_ids) - ref_model_ids}"
                )
            if len(self.model_ids) != len(has_id_models):
                raise Exception(f"{self.from_paths} has duplicate `model_id` in models!")
        return models
