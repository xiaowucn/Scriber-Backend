import json
import logging
import os
import shutil
import tempfile
from pathlib import Path
from zipfile import ZipFile

import peewee

from remarkable import config
from remarkable.common.constants import SpecialAnswerType
from remarkable.common.exceptions import CustomError
from remarkable.common.file_util import copy_model_file
from remarkable.common.storage import localstorage
from remarkable.config import get_config, project_root
from remarkable.db import pw_db
from remarkable.models.model_version import NewModelVersion
from remarkable.models.new_file import NewFile
from remarkable.optools.stat_scriber_answer import StatScriberAnswer
from remarkable.prompter.builder import AnswerPrompterBuilder
from remarkable.prompter.utils import extract_pred_feature, extract_train_feature, train
from remarkable.pw_models.model import NewMold, NewSpecialAnswer
from remarkable.pw_models.question import NewQuestion
from remarkable.service.crude_answer import predict_crude_answer

logger = logging.getLogger(__name__)


async def load_data_v2(schema_id, vid=0, update=False, clear=False, limit=0, start=None, end=None, cond=None):
    mold_data = await get_mold_data(schema_id)
    rows = await get_files_data(schema_id, limit, start, end, cond)
    tasks = []
    for file_id, pdfinsight, _, _, answer in rows:
        tasks.append((file_id, pdfinsight, answer))
    builder = AnswerPrompterBuilder(schema_id, vid)
    if clear:
        builder.clear()
    builder.update(mold_data, tasks)
    if vid:
        await NewModelVersion.update_by_pk(
            vid,
            files=[row[0] for row in tasks],
        )


def extract_feature_v2(schema_id, vid=0, start=0, end=0, for_test=False):
    if not for_test:
        extract_train_feature(
            schema_id,
            start,
            end,
            use_syllabuses=config.get_config("prompter.use_syllabuses", True),
            tokenization=(config.get_config("prompter.tokenization") or None),
            context_length=config.get_config("prompter.context_length", 1),
            separate_paragraph_table=config.get_config("prompter.separate_paragraph_table", True),
            vid=vid,
        )
    else:
        extract_pred_feature(schema_id, vid, start, end)


def train_v2(schema_id, vid=0):
    train(
        schema_id,
        vid=vid,
        rules_use_post_process=(config.get_config("prompter.post_process") or []),
        multi_process=True,
    )


async def predict_crude_answer_delegate(
    fid,
    qid,
    godmode=False,
    mid=None,
    mold=None,
    vid=None,
    save_db=False,
    save_path=None,
    file=None,
    test_accuracy=False,
):
    if not config.get_config("web.predict_crude_elements", True):
        return None

    file: NewFile = file or (await NewFile.find_by_id(fid))
    if not file:
        return None

    question: NewQuestion = await NewQuestion.find_by_id(qid)
    if not question:
        return None

    known_answer = None
    if godmode:
        known_answer = question.answer

    if not mold:
        mid = mid or question.mold
        mold = await NewMold.find_by_id(mid)

    if vid is None:
        vid = await NewModelVersion.get_enabled_version(mold.id)

    if not file.pdfinsight:
        return None
    assert localstorage.exists(file.pdfinsight_path())

    pdfinsight_path = localstorage.mount(file.pdfinsight_path())
    crude_answer = predict_crude_answer(
        pdfinsight_path, mold.id, mold.data, godmode=godmode, vid=vid, known_answer=known_answer, file_id=fid
    )
    if test_accuracy:
        await NewSpecialAnswer.update_or_create_crude(
            question.id, SpecialAnswerType.TEST_ACCURACY_CRUDE.value, crude_answer
        )
    if not test_accuracy and save_db:
        await question.update_(crude_answer=crude_answer)

    if save_path:
        with open(os.path.join(save_path, "%s.json" % fid), "w") as file_obj:
            json.dump(crude_answer, file_obj)

    return crude_answer


async def predict_crude_answer_by_range(
    start,
    end,
    mold=None,
    overwrite=False,
    save=None,
    _db=None,
    headnum=10,
    god=False,
    vid=0,
    crude_path=None,
    tree_s=None,
    acid=None,
):
    filter_crude_answer = None if overwrite else False
    questions_to_predict = await NewQuestion.list_by_range(
        mold=mold,
        start=start,
        end=end,
        have_crude_answer=filter_crude_answer,
        tree_l=tree_s,
        special_cols=["id", "fid"],
    )
    for question in questions_to_predict:
        try:
            await predict_crude_answer_delegate(
                question.fid, question.id, god, None, None, vid, crude_path is None, crude_path, None
            )
        except Exception as e:
            logger.exception(e)
    if save:
        answers = {}
        if crude_path and os.path.exists(crude_path):
            for root, _, names in os.walk(crude_path):
                for name in names:
                    fid, ext = os.path.splitext(name)
                    if fid.isdigit() and ext == ".json":
                        with open(os.path.join(root, name)) as file_obj:
                            answer = json.load(file_obj)
                        answers.setdefault(int(fid), answer)
            shutil.rmtree(crude_path)
        await StatScriberAnswer(
            headnum=headnum, mold=mold, save=save, prompt=False, vid=vid, answers=answers, tree_s=tree_s, acid=acid
        ).stat_crude_answer()


async def get_files_data(schema_id, limit=0, start=None, end=None, cond=None):
    answer_convert = {}
    for source_name, target_name in (config.get_config("web.answer_convert") or {}).items():
        source_mold = await NewMold.find_by_name(source_name)
        target_mold = await NewMold.find_by_name(target_name)
        if source_mold and target_mold:
            answer_convert.setdefault(target_mold.id, source_mold.id)
    if schema_id in answer_convert:
        schema_id = answer_convert[schema_id]
        fetch_question_sql = """
            select
                file.id , file.pdfinsight, question.id, question.data, special_answer.data as answer_data
            from question
            left join file on file.id=question.fid
            left join special_answer on special_answer.qid=question.id and special_answer.answer_type='export_answer'
            where question.mold={mold} and question.deleted_utc=0 and file.pdfinsight is not NULL and question.status in ({training_data_status})
        """
    else:
        fetch_question_sql = """
            select
                file.id , file.pdfinsight, question.id, question.data, question.answer as answer_data
            from question
            left join file on file.id = question.fid
            where question.mold={mold} and question.deleted_utc=0 and file.pdfinsight is not NULL and question.status in ({training_data_status})
        """
    if start is not None:
        fetch_question_sql += " and file.id >= %s" % start
    if end is not None:
        fetch_question_sql += " and file.id <= %s" % end
    if cond:
        fetch_question_sql += cond
    fetch_question_sql += " order by file.id"
    fetch_question_sql = fetch_question_sql.format(
        training_data_status=config.get_config("prompter.training_data_status", "2, 5, 10, 100"), mold=int(schema_id)
    )
    if limit:
        fetch_question_sql += " limit %s" % limit
    rows = await pw_db.execute(fetch_question_sql, default_row_type=peewee.ROW.TUPLE)
    return rows


async def get_mold_data(schema_id):
    mold = await NewMold.find_by_id(schema_id)
    if not mold:
        raise CustomError(f"can't find mold: {str(schema_id)}")
    return mold.data


def deploy_model(model_path: str | ZipFile, file_names: list, schema_id: int, vid: int = 0):
    training_cache_dir = Path(get_config("training_cache_dir"))
    model_dir = training_cache_dir / str(schema_id) / str(vid)
    if isinstance(model_path, ZipFile):
        model_path.extractall(model_dir)
        return
    with tempfile.TemporaryDirectory() as import_temp_dir:
        shutil.unpack_archive(model_path, import_temp_dir, format="zip")
        logger.info(f"copy file to {model_dir} ...")
        for file_name in file_names:
            if copy_model_file(import_temp_dir, model_dir, file_name):
                logger.info(f"copy file {file_name} success")
            else:
                logger.warning(f"model_version: {vid}, file {file_name} not exist, please check")


def archive_model(export_file_name: str, file_names: list, schema_id: int, vid: int = 0):
    training_cache_dir = Path(get_config("training_cache_dir"))
    model_dir = training_cache_dir / str(schema_id) / str(vid)
    with tempfile.TemporaryDirectory() as export_tmp_dir:
        for file_name in file_names:
            copy_model_file(model_dir, export_tmp_dir, file_name)

        archived_file = shutil.make_archive(export_file_name, "zip", root_dir=export_tmp_dir)
        logger.info(f"pack the model files for schema {schema_id} to {archived_file}")
        return archived_file


def model_v2_path(name):
    return os.path.join(project_root, "data", "model", "%s_v2.zip" % name)


PROMPTER_MODEL_FILES = (
    "feature/count_paragraph.pkl",
    "feature/count_syllabuse.pkl",
    "feature/count_table.pkl",
    "feature/count_vocab.pkl",
    "feature/rules.pkl",
    "models/",
)
