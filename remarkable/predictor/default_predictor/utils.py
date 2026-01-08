from remarkable.common.exceptions import ConfigurationError
from remarkable.predictor.base_prophet import BaseProphet
from remarkable.predictor.mold_schema import MoldSchema
from remarkable.predictor.predictor import JudgeByRegex


def collect_predictable_items(schema_item):
    def _collect(item, result):
        if item.is_leaf:
            result.append(item)
        else:
            for child in item.children:
                _collect(child, result)

    predictable_items = []
    _collect(schema_item, predictable_items)

    return predictable_items


def choose_model(schema_item, predictors):
    default_model = {"name": "score_filter"}
    config = next((i for i in predictors if i["path"] == schema_item.path[1:]), None)
    if config:
        return {"name": config["model"]}
    return default_model


def create_predictor_options(mold, predictors):
    predictor_options = []
    predictors = predictors or mold.predictors or []
    mold_schema = MoldSchema(mold.data)
    is_leaf_map = get_child_schema(mold_schema.root_schema)
    for item in predictors:
        model_option = item.get("model", None) or item.get("models", None)
        item_models = []
        if model_option:
            if isinstance(model_option, str):
                item_models.append({"name": model_option})
            elif isinstance(model_option, list):
                item_models = model_option[:]
            else:
                raise ConfigurationError("Predictor config should be instance of str or list")

        item_config = {"path": item["path"], "models": item_models}
        item_info = is_leaf_map.get("_".join(item["path"]), {})
        if sub_primary_key := item.get("sub_primary_key"):
            item_config["sub_primary_key"] = sub_primary_key
            item_config["group"] = item.get("group", {})
        else:
            if not item_info.get("is_leaf", True) and "table_row" in [i["name"] for i in item_models]:
                item_config["sub_primary_key"] = item_info["children"]
        item_config.update({"enum_config": item.get("enum_config", {})})
        predictor_options.append(item_config)

    return predictor_options


def get_child_schema(schema_item):
    def _get_child_schema(_schema_item, result):
        if _schema_item.children:
            for children in _schema_item.children:
                if children.is_leaf:
                    result["_".join(children.path[1:])] = {"is_leaf": True}
                else:
                    result["_".join(children.path[1:])] = {"is_leaf": False, "children": list(children.schema.keys())}

                _get_child_schema(children, result)

    ret = {}
    if schema_item.is_leaf:
        ret["_".join(schema_item.path[1:])] = {"is_leaf": True}
        return ret
    _get_child_schema(schema_item, ret)
    return ret


def load_prophet_config(mold, predictors=None):
    predictor_options = create_predictor_options(mold, predictors)

    return {
        "depends": {},
        "predictor_options": predictor_options,
    }


class DefaultProphet(BaseProphet):
    def parse_enum_value(self, predictor_result, schema):
        if self.enum_predictor:
            return self.enum_predictor.predict(predictor_result, schema)
        return None

    def get_enum_predictor(self):
        enum_predictor = JudgeByRegex()
        col_patterns = {}
        multi_answer_col_patterns = {}
        for item in self.predictor_options:
            enum_config = item.get("enum_config")
            if enum_config:
                # todo 正则转义处理 enum_config = {k: [rf'{i}' for i in v] for k, v in enum_config.items()}
                schema_item = self.mold_schema.find_schema_by_path(item["path"])
                enum_type_info = schema_item.mold_schema.get_enum_type(schema_item.type)
                if item.get("multi_enum") or enum_type_info.get("isMultiSelect"):
                    multi_answer_col_patterns[item["path"][-1]] = self.gen_multi_patterns(enum_type_info, enum_config)
                else:
                    col_patterns[item["path"][-1]] = enum_config
        enum_predictor.col_patterns = col_patterns
        enum_predictor.multi_answer_col_patterns = multi_answer_col_patterns
        return enum_predictor

    @staticmethod
    def gen_multi_patterns(enum_type_info, enum_config):
        # 兼容 JudgeByRegex multi_answer_col_patterns配置的格式
        ret = {
            "values": enum_config,
        }
        for item in enum_type_info["values"]:
            if item["isDefault"]:
                ret["default"] = item["name"]
        return ret


def make_prophet_instance(prophet_config, mold, version_id):
    return DefaultProphet(prophet_config, mold, version_id)
