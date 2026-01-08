import re
from importlib import import_module

from remarkable.common.util import clean_txt, import_class_by_path
from remarkable.config import get_config

predictor_package_map = {}


def load_prophet_config(mold):
    schema_alias = clean_txt(mold.name)
    config_map = get_config("prophet.config_map") or {}
    schema_name = None
    for key, value in config_map.items():
        if key.startswith("__regex__"):
            if re.compile(key.split("__regex__")[1]).search(schema_alias):
                schema_name = value
                break
        if clean_txt(key) == schema_alias:
            schema_name = value
            break
    if not schema_name:
        raise ModuleNotFoundError(f"Module {schema_alias} not exists in prophet.config_map: {config_map}")
    module_path = f".{schema_name}_schema"

    predictor_packages = []
    multi_packages = get_config("prophet.multi_packages")
    if multi_packages:
        predictor_packages.extend(multi_packages)
    else:
        predictor_package = get_config("prophet.package_name", "default_predictor")
        predictor_packages.append(predictor_package)

    for predictor_package in predictor_packages:
        if not predictor_package.startswith("remarkable."):
            predictor_package = f"remarkable.predictor.{predictor_package}"
        scheme_package = f"{predictor_package}.schemas"
        try:
            module = import_module(module_path, package=scheme_package)
            predictor_package_map[mold.name] = predictor_package
            return module.prophet_config
        except ModuleNotFoundError:
            pass

    raise ModuleNotFoundError(f"Module {module_path} not exists.")


def make_prophet_instance(prophet_config, mold, version_id):
    predictor_package = predictor_package_map.get(mold.name, "default_predictor")
    clazz = import_class_by_path(f"{predictor_package}.Prophet")
    if clazz:
        return clazz(prophet_config, mold, version_id)
    return None
