import logging
import os
import pickle
from pathlib import Path

from invoke import task

from remarkable.db import peewee_transaction_wrapper
from remarkable.devtools import InvokeWrapper, int_or_none


@task
def prepare_dataset(ctx, schema_id, start=None, end=None, vid=0):
    from remarkable.common.util import loop_wrapper
    from remarkable.models.model_version import NewModelVersion
    from remarkable.predictor.helpers import create_predictor_prophet
    from remarkable.pw_models.model import NewMold

    @loop_wrapper
    @peewee_transaction_wrapper
    async def _run():
        mold = await NewMold.find_by_id(schema_id)
        model_version = await NewModelVersion.find_by_id(vid)
        prophet = create_predictor_prophet(mold, model_version=model_version)
        await prophet.run_dump_dataset(start, end)

    _run()


@task
def train(ctx, schema_id, vid=0):
    from remarkable.common.util import loop_wrapper
    from remarkable.models.model_version import NewModelVersion
    from remarkable.predictor.helpers import create_predictor_prophet
    from remarkable.pw_models.model import NewMold

    @loop_wrapper
    @peewee_transaction_wrapper
    async def _run():
        mold = await NewMold.find_by_id(schema_id)
        model_version = await NewModelVersion.find_by_id(vid)
        prophet = create_predictor_prophet(mold, model_version=model_version)
        prophet.run_train()

    _run()


@task
def archive_model_for(ctx, schema_id, vid=0, name="predictor"):
    from remarkable.service.predictor import PREDICTOR_MODEL_FILES, predictor_model_path
    from remarkable.service.prompter import archive_model

    archive_path = predictor_model_path(name)
    archive_model(os.path.splitext(archive_path)[0], PREDICTOR_MODEL_FILES, schema_id, vid)


@task(klass=InvokeWrapper)
async def deploy_model_for(ctx, schema_id, vid=0, name="predictor"):
    from remarkable.service.deploy import deploy_predictor_model

    await deploy_predictor_model(schema_id, name, vid)


@task(klass=InvokeWrapper, iterable=["special_rules"])
async def preset_answer(
    ctx,
    start=None,
    end=None,
    project=None,
    mold=None,
    vid=None,
    overwrite=False,
    workers=0,
    save=None,
    parallel=True,
    special_rules=None,
    from_file=None,
):
    """预测答案（内容提取）"""
    from remarkable.pw_models.question import NewQuestion
    from remarkable.service.new_question import batch_preset, run_preset_answer

    files_ids = []
    if from_file:
        with open(from_file, "r", encoding="utf-8") as f:
            files_ids = [int(i.strip()) for i in f if i.strip().isdigit()]

    if parallel:
        await batch_preset(
            int_or_none(start),
            int_or_none(end),
            project=int_or_none(project),
            mold=int_or_none(mold),
            vid=int_or_none(vid),
            overwrite=overwrite,
            workers=workers,
            save=save,
            ctx_method="spawn",
            special_rules=special_rules,
            files_ids=files_ids,
        )
    else:
        questions = await NewQuestion.list_by_range(
            start=start,
            end=end,
            project=project,
            mold=mold,
            have_preset_answer=None if overwrite else False,
            special_cols=["id", "fid"],
            files_ids=files_ids,
        )
        for question in questions:
            args = (question.fid, question.id, vid, None, special_rules)
            await run_preset_answer(args)


@task(klass=InvokeWrapper)
async def stat(ctx, mold=None, start=None, end=None, headnum=10, save=0, host=None, strict=False):
    from remarkable.optools.stat_scriber_answer import StatScriberAnswer

    await StatScriberAnswer(
        headnum=headnum,
        from_id=start,
        to_id=end,
        mold=mold,
        save=save,
        host=host,
        strict=strict,
    ).stat_preset_answer()


@task
def preset_answer_async(ctx, mold, start=0, end=0, overwrite=False):
    """
    异步预测答案（上传文件撞缓存）
    """
    from remarkable.common.util import loop_wrapper
    from remarkable.pw_models.question import NewQuestion
    from remarkable.worker.tasks import preset_answer_by_qid

    @loop_wrapper
    @peewee_transaction_wrapper
    async def _run(mold, start, end, overwrite):
        questions = await NewQuestion.list_by_range(
            mold=mold,
            start=start,
            end=end,
            have_preset_answer=None if overwrite else False,
            special_cols=["id"],
        )
        for question in questions:
            preset_answer_by_qid.delay(question.id)

    _run(mold, start, end, overwrite)


@task()
def modify_model_name(ctx, mold_id, path_config, old_model_name, new_model_name, vid=0, test=False):
    """
    指定字段修改配置的模型之后，对应模型中的key也需要改变，这时若不想重新训练，直接修改pickle中的对应key就可以
    note：
        修改之后确认无误后，需要打包模型并提交到仓库
        测试环境需要手动部署模型
    ex:
        inv predictor.modify-model-name -m 24 -o cash_bank_balances -n add_subtotal -p 'Cash and Bank Balances'
        对于字段`Cash and Bank Balances` 配置的模型是cash_bank_balances 修改为add_subtotal
        执行前可以加-t参数， 打印出对应的模型信息，检查无误后再执行
    PS: 涉及到三级字段配置的字段， 对应的模型文件不仅仅是paths中的两个文件，需要根据具体的模型文件修改paths的内容
        可以调试下 SchemaPredictor.model_data_path()方法 查看具体的文件路径
    """
    from remarkable.config import get_config
    from remarkable.predictor.utils import SafeFileName

    bash_path = Path(get_config("training_cache_dir")) / str(mold_id) / str(vid) / "predictors"
    paths = [
        [path_config],
        [path_config, "PARENT_SUBSTITUE"],
    ]
    model_paths = []
    for path in paths:
        filename = SafeFileName.escape("_".join(path))
        model_paths.append(bash_path / f"{filename}.pkl")
    for model_path in model_paths:
        if not Path(model_path).exists():
            logging.info(f"{model_path} not exists, skip")
            continue
        model_path = model_path.as_posix()
        if test:
            logging.info("Please check if the model file is correct")
            logging.info(model_path)
            with open(model_path, "rb") as file_obj:
                logging.info(pickle.load(file_obj))
            continue
        with open(model_path, "rb") as model_fp:
            model_info = pickle.load(model_fp)
        if not model_info:
            logging.info("empty model, do nothing, please check...")

        model_data = model_info.pop(old_model_name, None)
        if not model_data:
            logging.info("empty model_data, do nothing, please check...")

        model_info[new_model_name] = model_data

        with open(model_path, "wb") as model_fp:
            pickle.dump(model_info, model_fp)

        logging.info(f"modify to {new_model_name}")


@task(klass=InvokeWrapper)
async def modify_predictor_format(ctx, mid=None, vid=None):
    """
    将旧版predictor数据修改成新版
    """
    from remarkable.models.model_version import NewModelVersion
    from remarkable.pw_models.model import NewMold

    if not mid:
        all_molds = await NewMold.find_by_kwargs(delegate="all")
        mold_ids = [mold.id for mold in all_molds]
    else:
        mold_ids = [mid]
    logging.info(f"{mold_ids=}")
    for mold_id in mold_ids:
        logging.info(f"process {mold_id=}")
        params = {
            "mold": mold_id,
            "delegate": "all",
        }
        if vid:
            params["id"] = vid
        model_versions = await NewModelVersion.find_by_kwargs(**params)
        for model_version in model_versions:
            if not model_version.predictors:
                continue
            predictors = []
            for predictor_option in model_version.predictors:
                if "model" in predictor_option:
                    predictors.append(
                        {
                            "path": predictor_option["path"],
                            "models": [
                                {
                                    "name": predictor_option["model"],
                                }
                            ],
                        }
                    )
            if not predictors:
                continue
            logging.info(f"modify_predictor_format for: {model_version.id=}")
            await model_version.update_(predictors=predictors)
