import logging
from datetime import datetime

from remarkable.common.constants import ModelEnableStatus, ModelType, PredictorTrainingStatus
from remarkable.config import get_config
from remarkable.db import pw_db
from remarkable.models.model_version import NewModelVersion
from remarkable.pw_models.model import NewMold
from remarkable.service.predictor import PREDICTOR_MODEL_FILES, predictor_model_path
from remarkable.service.prompter import PROMPTER_MODEL_FILES, deploy_model, model_v2_path


async def deploy_predictor_model(schema_id: str, name: str, vid: int):
    schema_ids = await NewMold.tolerate_schema_ids(schema_id)
    mold = await NewMold.find_by_id(schema_ids[0])
    name = name or (get_config("prophet.config_map") or {}).get(mold.name)
    predictor_model_file = predictor_model_path(name)
    deploy_model(predictor_model_file, PREDICTOR_MODEL_FILES, schema_ids[0], vid)
    logging.info(f"deploy {predictor_model_file} to schema [{schema_id}] vid [{vid}]")


async def deploy_prompter_model(schema_id, name, vid):
    schema_ids = await NewMold.tolerate_schema_ids(schema_id)
    mold = await NewMold.find_by_id(schema_ids[0])
    name = name or (get_config("prophet.config_map") or {}).get(mold.name)
    prompter_model_file = model_v2_path(name)
    deploy_model(prompter_model_file, PROMPTER_MODEL_FILES, schema_ids[0], vid)
    logging.info(f"deploy {prompter_model_file} to schema [{schema_id}] vid [{vid}]")


async def deploy_developer_model_version(mid, name, overwrite, is_enabled=False):
    enable = ModelEnableStatus.ENABLE.value if is_enabled else ModelEnableStatus.DISABLE.value
    mid = (await NewMold.tolerate_schema_ids(mid))[0]
    cond = (NewModelVersion.model_type == ModelType.DEVELOP.value) & (NewModelVersion.mold == mid)
    mold = await NewMold.find_by_id(mid)
    # utils_module, prophet_config = collect_prophet_config([], mold)

    if model_version := await NewModelVersion.get_first_one(cond):
        if overwrite:
            model_version.predictors = []
            model_version.enable = enable
            await pw_db.update(model_version)
            return model_version.id
        else:
            await model_version.soft_delete()
            logging.info(f"{mid}对应的schema已存在定制模型, 已删除")

    new_model_version = await NewModelVersion.create(
        **{
            "mold": mold.id,
            "name": (name or "定制模型") + datetime.now().strftime("%Y%m%d%H%M%S"),
            "model_type": ModelType.DEVELOP.value,
            "status": PredictorTrainingStatus.DONE.value,
            "dirs": [],
            "files": [],
            "enable": enable,
            "predictors": [],
            "predictor_option": mold.predictor_option,
        }
    )
    logging.info("special model version successfully created")
    return new_model_version.id
