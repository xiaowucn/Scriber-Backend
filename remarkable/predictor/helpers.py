import json
import logging
import os
import pickle
import shutil
from collections import defaultdict
from copy import deepcopy
from functools import partial
from importlib import import_module
from multiprocessing import cpu_count

from remarkable.common.constants import QuestionStatus
from remarkable.common.exceptions import CustomError
from remarkable.common.multiprocess import run_in_multiprocess
from remarkable.common.pattern import PatternCollection
from remarkable.common.schema import Schema
from remarkable.common.storage import localstorage
from remarkable.common.util import clean_txt
from remarkable.config import get_config
from remarkable.converter.utils import generate_customer_answer
from remarkable.models.model_version import NewModelVersion
from remarkable.models.new_file import NewFile
from remarkable.optools.stat_scriber_answer import StatScriberAnswer
from remarkable.pdfinsight.reader import PdfinsightReader
from remarkable.plugins.fileapi.common import is_valid_key_path
from remarkable.predictor.base_prophet import PredictorV1ProphetAdapter
from remarkable.predictor.predict import predict_answer
from remarkable.pw_models.model import NewMold
from remarkable.pw_models.question import NewQuestion
from remarkable.service.new_file import NewFileService
from remarkable.service.new_question import NewQuestionService
from remarkable.service.rpc import wrap_run_predict
from remarkable.service.rule import RuleService
from remarkable.utils.answer_util import AnswerUtil

logger = logging.getLogger(__name__)


class AnswerInspector:
    """
    对标注答案进行检查,将不符合预期正则的答案打印出来
    通过不断调整正则,使其能够匹配所有标注答案
    可以检查
        - 答案文本: p_content
        - 第一个段落: p_first
        - 最后一个段落: p_last
        - 前一个段落: p_prev
        - 后一个段落: p_next
    """

    def __init__(
        self,
        mid,
        start_id,
        stop_id,
        schema_word,
        p_content=None,
        p_first=None,
        p_last=None,
        p_prev=None,
        p_next=None,
        p_syllables=None,
        fids=None,
    ):
        self.mid = mid
        self.start_id = start_id
        self.stop_id = stop_id
        self.fids = fids
        self.schema_word = schema_word
        self.p_content = PatternCollection(p_content)
        self.p_first = PatternCollection(p_first)
        self.p_last = PatternCollection(p_last)
        self.p_prev = PatternCollection(p_prev)
        self.p_next = PatternCollection(p_next)
        self.p_syllables = PatternCollection(p_syllables)

    def print_next_paragraph(self, reader, answer_elements_index):
        if answer_elements_index:
            element = reader.find_next_paragraph(max(answer_elements_index))
            if element:
                print("next_element:")
                next_text = clean_txt(element.get("text", ""))
                if self.is_match(next_text, self.p_next):
                    print("matched")
                else:
                    print(next_text)
            else:
                print("cannot find next_element!")

    def print_prev_paragraph(self, reader, answer_elements_index):
        if answer_elements_index:
            element = reader.find_next_paragraph(min(answer_elements_index), step=-1)
            if element:
                print("prev_element:")
                prev_text = clean_txt(element.get("text", ""))
                if self.is_match(prev_text, self.p_prev):
                    print("matched")
                else:
                    print(prev_text)
            else:
                print("cannot find prev_element!")

    def print_syllables(self, reader, answer_elements_index):
        matched = False
        if answer_elements_index:
            syllabuses = reader.syllabus_reader.find_by_elt_index(answer_elements_index[0])
            for syllabus in syllabuses:
                matcher = self.p_syllables.nexts(clean_txt(syllabus.get("title", "")))
                if matcher:
                    matched = True
                    break
            if matched:
                print("matched")
            else:
                for syllabus in syllabuses:
                    print(syllabus.get("title"))

    @classmethod
    def is_match(cls, text, pattern):
        match = pattern.nexts(clean_txt(text))
        return match

    async def inspect_answer(self):
        files = await NewFile.list_by_range(self.mid, self.start_id, self.stop_id)
        for file in files:
            if self.fids and str(file.id) not in self.fids:
                continue
            print("\n")
            url = f"http://{get_config('web.domain')}/#/search?fileid={file.id}"
            print(url)
            if not file.pdfinsight_path():
                print("no pdfinsight found")
                continue
            reader = PdfinsightReader(localstorage.mount(file.pdfinsight_path()))
            question = await NewQuestion.find_by_fid_mid(file.id, self.mid)
            if not question:
                print("not question")
                continue
            answer = await question.get_user_merged_answer()
            if not answer:
                print("not answer")
                continue

            print("+" * 30)
            for item in answer["userAnswer"]["items"]:
                item_key = clean_txt(item["key"])
                if any(clean_txt(x) not in item_key for x in self.schema_word):
                    continue

                answer_elements_index = []
                for data_item in item["data"]:
                    boxes = data_item["boxes"]
                    # print(item['key'])
                    answer_texts = []
                    answer_elements_text = []
                    for box_info in boxes:
                        outline = box_info["box"]
                        page = box_info["page"]
                        answer_texts.append(clean_txt(box_info["text"]))
                        for _type, elt in reader.find_elements_by_outline(page, list(outline.values())):
                            if not elt:
                                logging.warning(f"No elt, fid:{file.id}, page:{page}, outline:{outline}")
                                continue
                            answer_elements_text.append(clean_txt(elt.get("text", "")))
                            answer_elements_index.append(elt["index"])

                    # for answer_element_text in answer_elements_text[-1:]:
                    #     print(answer_element_text)

                    print("-" * 30)
                    text = "".join(answer_texts)
                    if self.p_content.patterns:
                        print("content:")
                        if self.is_match(text, self.p_content):
                            print(f"matched: {text=}")
                        else:
                            print(text)

                    if not answer_elements_text:
                        continue
                    if self.p_first.patterns:
                        print("first_text:")
                        if self.is_match(answer_elements_text[0], self.p_first):
                            print("matched")
                        else:
                            print(answer_elements_text[0])
                    if self.p_last.patterns:
                        print("last_text:")
                        if self.is_match(answer_elements_text[-1], self.p_last):
                            print("matched")
                        else:
                            print(answer_elements_text[-1])
                    if self.p_prev.patterns:
                        self.print_prev_paragraph(reader, answer_elements_index)
                    if self.p_next.patterns:
                        self.print_next_paragraph(reader, answer_elements_index)
                    if self.p_syllables.patterns:
                        self.print_syllables(reader, answer_elements_index)
                    print("+" * 30)


async def _create_tasks(mold, start, end, tree_l=None):
    files = await NewFile.list_by_range(mold.id, start, end, tree_l=tree_l)
    tasks = []
    for file in files:
        question = await NewQuestion.find_by_fid_mid(file.id, mold.id)
        if not question:
            continue
        if not question.answer or not file or not file.pdfinsight_path():
            logging.warning(f"No answer found, skip qid: {question.id}")
            continue
        answer_data = await question.collect_answers()
        merge_answer = AnswerUtil.merge_answers(answer_data, schema_data=mold.data)
        task = {
            "mold_type": mold.mold_type,
            "fid": file.id,
            "qid": question.id,
            "answer": merge_answer,
            "pdfinsight_path": file.pdfinsight_path(),
            "pdf_path": file.pdf_path(),
        }
        tasks.append(task)

    return tasks


async def prepare_prophet_dataset(mold, start, end, vid=0, prophet=None, tree_l=None):
    workers = get_config("prompter.workers", cpu_count() // 2)
    tasks = await _create_tasks(mold, start, end, tree_l=tree_l)
    if not prophet:
        model_version = await NewModelVersion.find_by_id(vid)
        prophet = create_predictor_prophet(mold, model_version=model_version)

    # clear dataset dir first and then prepare dataset
    shutil.rmtree(prophet.dataset_dir, ignore_errors=True)
    run_in_multiprocess(safe_prepare_dataset, [(prophet, meta) for meta in tasks], workers=workers)
    return [task["fid"] for task in tasks]


def safe_prepare_dataset(params):
    prophet, meta = params
    try:
        prophet.prepare_dataset(meta)
    except Exception as exp:
        logging.exception(exp)


async def load_schema_dataset(mold_id, schema_name, file_id, vid=0):
    mold = await NewMold.find_by_id(mold_id)
    file = await NewFile.find_by_id(file_id)
    question = await NewQuestion.find_by_fid_mid(file.id, mold.id)
    model_version = await NewModelVersion.find_by_id(vid)
    prophet = create_predictor_prophet(mold, model_version=model_version)

    dataset_path = prophet.dataset_dir.joinpath(schema_name, f"{question.id}.pkl")
    dataset_data = None
    if dataset_path:
        with open(dataset_path, "rb") as dataset_file:
            dataset_data = pickle.load(dataset_file)

    print(dataset_data)


async def prepare_dataset(mold_id, start=0, end=0, vid=0):
    mold = await NewMold.find_by_id(mold_id)
    await prepare_prophet_dataset(mold, start, end, vid)


async def train_answer_data(mold_id, vid=0, special_rules=None):
    mold = await NewMold.find_by_id(mold_id)
    model_version = await NewModelVersion.find_by_id(vid)
    prophet = create_predictor_prophet(mold, model_version=model_version, special_rules=special_rules)
    prophet.run_train()


async def predict_mold_answer(mold_id, start=0, end=0, special_rules=None, skip_no_answer=False):
    mold = await NewMold.find_by_id(mold_id)
    assert mold, f"No mold found, {mold_id=}"
    if special_rules:
        if not isinstance(special_rules, list):
            special_rules = [special_rules]
        if not is_valid_key_path([mold.name, *special_rules], mold):
            raise CustomError("invalid path: (%s)" % special_rules)

    vid = await NewModelVersion.get_enabled_version(mold.id)

    files = await NewFile.list_by_range(mold_id, start, end)
    for file in files:
        question = await NewQuestion.find_by_fid_mid(file.id, mold.id)
        if not question:
            continue
        if skip_no_answer and question.status == QuestionStatus.TODO:
            continue
        if not file.pdfinsight_path():
            continue
        logging.info(f"preset answer for file, {vid=}, {file.id=}, {file.name=}, {question.id=}")
        await predict_answer(question, vid, special_rules)

        await question.set_answer()
        await NewQuestionService.post_pipe(question.id, file.id, file.meta_info)
        await NewFileService.post_pipe(file.id, triggered_by_predict=True)


async def inspect_rule(mold_id, start=0, end=0):
    files = await NewFile.list_by_range(mold_id, start, end)
    for _file in files:
        await RuleService.inspect_rules(_file)


async def gen_customer_answer(mid, start=0, end=0):
    files = await NewFile.list_by_range(mid, start, end)
    for file in files:
        question = await NewQuestion.find_by_fid_mid(file.id, mid)
        # 先合并答案
        await question.set_answer()
        await generate_customer_answer(question.id)


def create_predictor_prophet(mold, model_version=None, special_rules=None, **kwargs):
    version_id = model_version.id if model_version else 0
    predictor_framework = (
        model_version.predictor_option["framework_version"]
        if model_version
        else mold.predictor_option["framework_version"]
    )
    custom_predictors = model_version.predictors if model_version else []
    if predictor_framework == "2.0":
        utils_module, prophet_config = collect_prophet_config(custom_predictors, mold)
        prophet_config = filter_prophet_config(prophet_config, special_rules)
        instance = utils_module.make_prophet_instance(prophet_config, mold, version_id)
    else:
        kwargs["special_rules"] = special_rules
        instance = PredictorV1ProphetAdapter(mold, version_id, **kwargs)

    if get_config("prompter.mode") == "rpc":
        setattr(instance, "run_predict", partial(wrap_run_predict, instance, mold=mold, vid=version_id))  # noqa
    return instance


def filter_prophet_config(prophet_config, special_rules=None):
    predictor_options = prophet_config["predictor_options"]
    if special_rules:
        special_options = get_special_config(predictor_options, special_rules)
        prophet_config["predictor_options"] = special_options

    # 界面自定义配置中 组合字段的子项配置需要合并到组合字段中进行提取， 这里过滤掉子项的配置
    predictor_options = [i for i in prophet_config["predictor_options"] if not i.get("just_show")]
    prophet_config["predictor_options"] = predictor_options
    return prophet_config


def get_special_config(predictor_options: list, special_rules: list):
    if not isinstance(special_rules, list):
        special_rules = [special_rules]
    new_options = []
    for config in predictor_options:
        if config["path"] == special_rules:
            new_options.append(config)
            new_options.extend(get_depends_config(predictor_options, config))
            break

    return new_options


def get_depends_config(predictor_options: list, config: dict):
    new_options = []
    for model in config["models"]:
        if depends := model.get("depends") or model.get("elements_collect_config", {}).get("depends"):
            for depend in depends:
                new_options.extend(get_special_config(predictor_options, depend))
    return new_options


def collect_prophet_config(custom_predictors, mold):
    utils_module_from_code = import_module("remarkable.predictor")
    try:
        prophet_config = utils_module_from_code.load_prophet_config(mold)
    except ModuleNotFoundError as exp:
        logger.warning(exp)
        logger.warning("Will use default prophet config instead")
        utils_module = import_module("remarkable.predictor.default_predictor.utils")
        prophet_config = utils_module.load_prophet_config(mold, predictors=custom_predictors)
    else:
        utils_module = utils_module_from_code
        code_config = prophet_config["predictor_options"]
        code_config_schemas = defaultdict(list)
        for item in code_config:
            path = item["path"][0]  # 只比较一级字段
            code_config_schemas[path].append(item)

        custom_config_schemas = set()
        for item in custom_predictors:
            # 界面配置的 config_in_code 标明这个字段使用代码中的配置
            models = item["models"]
            models = [model for model in models if model["name"] == "config_in_code"]
            if not models:
                custom_config_schemas.add(item["path"][0])
        for key, items in code_config_schemas.items():
            if key not in custom_config_schemas:
                custom_predictors.extend(items)

        prophet_config["predictor_options"] = custom_predictors

    return utils_module, prophet_config


async def stat(mold_id, from_id, to_id, skip_reg=r"单位|币种", strict=False, files_ids=None):
    host = get_config("web.domain")
    await StatScriberAnswer(
        headnum=5,
        threshold=None,
        from_id=from_id,
        to_id=to_id,
        mold=mold_id,
        host=host,
        skip_reg=skip_reg,
        strict=strict,
        files_ids=files_ids,
    ).stat_preset_answer()


async def prophet_config_assist(mid):
    """
    辅助生成prophet_config
    :param mid:
    :return:
    """
    template = {
        "path": None,
        "models": [
            {
                "name": "syllabus_elt_v2",
            }
        ],
    }
    predictor_options = []
    mold = await NewMold.find_by_id(mid)
    schema = Schema(mold.data)
    for item in schema.iter_schema_attr():
        option = deepcopy(template)
        option["path"] = item[1:]
        predictor_options.append(option)

    with open("prophet_config.json", "w") as file_obj:
        print("已在当前路径下生成初始配置 prophet_config.json")
        json.dump(predictor_options, file_obj, ensure_ascii=False)


def set_ocr_env():
    """
    使用 pdfparser 包时设置的有关 ocr 的环境变量
    :return:
    """
    os.environ["PDFPARSER_CONFIG_OCR_PAI_CACHE"] = "false"
    os.environ["PDFPARSER_CONFIG_RPC_CLIENT_PAI_TARGET"] = "100.64.0.15:1889"


async def main():
    MID = 2
    START_ID = 83
    STOP_ID = 83
    # SPECIAL_RULES = ['基本情况', '报告名称']
    # SPECIAL_RULES = ["201291 管理费（%）"]
    SPECIAL_RULES = None
    # await prepare_dataset(MID, START_ID, STOP_ID)
    # await train_answer_data(MID, special_rules=SPECIAL_RULES)
    await predict_mold_answer(MID, START_ID, STOP_ID, special_rules=SPECIAL_RULES)
    # await gen_customer_answer(MID, START_ID, STOP_ID)
    # await inspect_rule(MID, START_ID, STOP_ID)
    # await stat(MID, START_ID, STOP_ID)


if __name__ == "__main__":
    import asyncio

    asyncio.run(main())
