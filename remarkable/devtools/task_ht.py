import json
import logging
import os
import shutil
from itertools import combinations
from pathlib import Path

from invoke import task
from tornado.ioloop import IOLoop

from remarkable.config import get_config
from remarkable.db import peewee_transaction_wrapper
from remarkable.devtools import InvokeWrapper, deploy_model_to_special_version


@task
def encrypt_file(ctx, need_bak=True, start=None, end=None, mold=None):
    """加密文件"""
    from remarkable.common.storage import localstorage
    from remarkable.models.new_file import NewFile

    def copy_file():
        tmp_dir = get_config("web.tmp_dir")
        tmp_bak_path = os.path.join(tmp_dir, "files_bak")
        if os.path.exists(tmp_bak_path):
            shutil.rmtree(tmp_bak_path)
        shutil.copytree(localstorage.root, tmp_bak_path)

    @peewee_transaction_wrapper
    async def process_all_file(start, end, mold):
        files = await NewFile.list_by_range(start=start, end=end, mold=mold)
        for file in files:
            encrypt(file.hash)
            # encrypt(file.docx)
            # encrypt(file.pdf)
            logging.info(f"encrypt_file for file id: {file.id}")

    def encrypt(path):
        file_path = localstorage.mount(os.path.join(path[:2], path[2:]))
        if not localstorage.exists(file_path):
            logging.info("file not exists: %s", path)
            return
        data = localstorage.read_file(file_path)
        localstorage.write_file(file_path, data, encrypt=True)

    async def _run():
        if need_bak:
            copy_file()
        await process_all_file(start, end, mold)
        logging.info("All encrypt_file done!!!")

    IOLoop.current().run_sync(_run)


def get_pattern_str(reg: "SRE_Pattern"):  # noqa: F821
    if not reg:
        return None
    return reg.pattern


@peewee_transaction_wrapper
async def _move_ht_predictor():
    from remarkable.common.constants import ExtractMethodType
    from remarkable.predictor.ht_predictor.software_contract_predictor.predictor import HtPredictor
    from remarkable.pw_models.model import NewExtractMethod, NewMold

    for mold_name, clazz in HtPredictor.get_contract_map().items():
        mold = await NewMold.find_by_name(mold_name)
        await NewExtractMethod.clear_by_mold(mold.id)
        for path, patterns in clazz.firgue_patterns.items():
            data = {
                "regs": [get_pattern_str(x) for x in patterns.get("regs", [])],
                "anchor_reg": get_pattern_str(patterns.get("anchor_reg")),
                "cnt_of_anchor_elts": patterns.get("cnt_of_anchor_elts"),
                "cnt_of_res": patterns.get("cnt_of_res"),
            }
            params = {
                "path": path,
                "mold": mold.id,
                "data": json.dumps(data, ensure_ascii=False),
                "method_type": ExtractMethodType.FIRGUE.value,
            }
            await NewExtractMethod.create(**params)

        for path, patterns in clazz.term_patterns.items():
            num = patterns.get("limit", len(patterns["regs"]))
            regs = [".*".join([get_pattern_str(x) for x in pair]) for pair in combinations(patterns["regs"], num)]
            data = {
                "regs": regs,
                "anchor_reg": get_pattern_str(patterns.get("anchor_reg")),
                "cnt_of_anchor_elts": patterns.get("cnt_of_anchor_elts"),
                "cnt_of_res": patterns.get("cnt_of_res"),
            }
            params = {
                "path": path,
                "mold": mold.id,
                "data": json.dumps(data, ensure_ascii=False),
                "method_type": ExtractMethodType.TERM.value,
            }
            await NewExtractMethod.create(**params)

    logging.info("move_ht_predictor done!!!")


@task
def move_ht_predictor(ctx):
    IOLoop.current().run_sync(_move_ht_predictor)


@task
def move_ht_rules(ctx):
    from remarkable.optools.import_custom_rules import import_custom_rules

    async def _run():
        await import_custom_rules()
        logging.info("import_custom_rules done!!!")

    IOLoop.current().run_sync(_run)


@task
def modify_rule_item(ctx, cid):
    from remarkable.pw_models.model import NewRuleItem

    async def _run():
        items = await NewRuleItem.list_by_rule_class(cid)
        for item in items:
            patterns = item.data["patterns"]
            if isinstance(patterns, str):
                logging.info(f"modify rule class for {item.name}")
                item.data["patterns"] = [patterns]
            await item.update_(**{"data": item.data})

    IOLoop.current().run_sync(_run)


@task
def decrypt_tmp_file(ctx, start=None, end=None, mold=None):
    from remarkable.common.storage import localstorage
    from remarkable.models.new_file import NewFile

    @peewee_transaction_wrapper
    async def process_all_file(start, end, mold):
        files = await NewFile.list_by_range(start=start, end=end, mold=mold)
        for file in files:
            if not file.pdf_path():
                continue
            decrypt(file)

    def decrypt(file):
        logging.info(file.pdf_path())
        data = localstorage.read_file(file.pdf_path())
        if data and data[:7] == b"gAAAAAB":
            data = localstorage.read_file(file.pdf_path(), auto_detect=True)
            localstorage.delete_file(file.pdf_path())
            localstorage.write_file(file.pdf_path(), data)
            logging.info(f"decrypt for file id: {file.id}")
        else:
            logging.info(f"skip for file id: {file.id}")

    async def _run():
        await process_all_file(start, end, mold)
        logging.info("All encrypt_file done!!!")

    IOLoop.current().run_sync(_run)


@task(klass=InvokeWrapper)
async def add_default_mold_class(ctx, class_name="章节模板对比", schema_name="私募类基金合同"):
    from remarkable.common.constants import RuleMethodType
    from remarkable.config import get_config
    from remarkable.pw_models.model import NewMold, NewRuleClass

    is_fund = get_config("ht_fund") or False
    if not is_fund:
        logging.info("not fund env, don't have to execute it")
        return
    mold = await NewMold.find_by_name(schema_name)
    if not mold:
        logging.info("mold not exists")
        return

    classes = await NewRuleClass.list_by_mold(mold.id)
    for class_item in classes:
        if class_item.name == class_name:
            logging.info(f"{class_name} already existed")
            return
    rule_class = await NewRuleClass.create(
        **{
            "name": class_name,
            "mold": mold.id,
            "method_type": RuleMethodType.TERM.value,
        }
    )
    if rule_class:
        logging.info("create mold_class successfully...")
        logging.info(rule_class.to_dict())
    else:
        logging.info("create mold_class failed, please check...")


@task(klass=InvokeWrapper)
async def create_default_model_version(ctx):
    # create a default model version for ht fund schema
    from remarkable.common.constants import ModelEnableStatus, ModelType, PredictorTrainingStatus
    from remarkable.config import get_config
    from remarkable.models.model_version import NewModelVersion
    from remarkable.predictor.ht_predictor.schemas.fund_schema import predictor_options as ht_predictor_options
    from remarkable.pw_models.model import NewMold

    schema_name = "私募类基金合同"
    is_fund = get_config("ht_fund") or False
    if not is_fund:
        logging.info("not fund env, don't have to execute it")
        return
    mold = await NewMold.find_by_name(schema_name)
    if not mold:
        logging.info("mold not exists")
        return
    mold = await NewMold.find_by_name(schema_name)
    predictors = []
    default_models = [{"name": "config_in_code"}]
    default_version_name = "后端预置版本"
    model_version = await NewModelVersion.find_by_kwargs(name=default_version_name, mold=mold.id)
    training_cache_dir = Path(get_config("training_cache_dir"))
    # model_config = (get_config('available_models') or {})
    for predictor_option in ht_predictor_options:
        # models = predictor_option['models']
        path = predictor_option["path"]
        predictors.append(
            {
                "path": path,
                "models": default_models,
            }
        )
        # if len(models) > 1:
        #     predictors.append(
        #         {
        #             'path': path,
        #             'models': default_models,
        #         }
        #     )
        #     continue
        # model_name = models[0]['name']
        # if model_name in available_models:
        #     predictors.append(predictor_option)
        # else:
        #     predictors.append(
        #         {
        #             'path': path,
        #             'models': default_models,
        #         }
        #     )
    if model_version:
        logging.info(f"default model version exists, model_version id is {model_version.id}")
        logging.info("update model version to enable")
        await model_version.update_(enable=ModelEnableStatus.ENABLE.value, predictors=predictors)
        deploy_model_to_special_version(training_cache_dir, mold.id, model_version.id)
        return

    model_version = await NewModelVersion.create(
        **{
            "mold": mold.id,
            "name": default_version_name,
            "model_type": ModelType.PREDICT.value,
            "status": PredictorTrainingStatus.DONE.value,
            "dirs": [],
            "files": [],
            "enable": ModelEnableStatus.ENABLE.value,
            "predictors": predictors,
            "predictor_option": mold.predictor_option,
        },
    )
    logging.info("default model version successfully created")
    # deploy model to this model_version
    deploy_model_to_special_version(training_cache_dir, mold.id, model_version.id)


@task(klass=InvokeWrapper)
async def call_esb(ctx, fid, mid=2):
    from remarkable.converter.utils import call_workshop, prepare_data
    from remarkable.pw_models.question import NewQuestion

    logging.info(f"start to push preset_answer, fid:{fid}")
    question = await NewQuestion.find_by_fid_mid(fid, mid)
    meta_data = await prepare_data(question.id)
    meta_data.answer = meta_data.question.preset_answer
    await call_workshop(meta_data, debug=True)
    logging.info(f"push preset_answer success, fid:{fid}")
