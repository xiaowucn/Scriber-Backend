import os
import shutil

from invoke import task
from speedy.peewee_plus.orm import TRUE, fn
from tornado.ioloop import IOLoop

from remarkable.devtools import InvokeWrapper, int_or_none

# @task
# def build_model(ctx, schema_id, update=False, clear=False, limit=0, start=None, end=None):
#     @loop_wrapper
#     @func_transaction
#     async def run():
#         builder = AnswerPrompterBuilder(schema_id)
#         if clear:
#             builder.clear()
#         if update:
#             await builder.update(limit, start, end)
#         await builder.bulid()

#     run()


# @task
# def update_model_async(ctx, schema_id):
#     update_model.delay(schema_id)


# @task
# def make_questions(ctx, start, end):
#     IOLoop.current().run_sync(lambda: _make_questions(int(start), int(end)))


@task
def load_data_v2(ctx, schema_id, vid=0, update=False, clear=False, limit=0, start=None, end=None):
    schema_id = int(schema_id)
    from remarkable.service.prompter import load_data_v2 as _load_data_v2

    IOLoop().run_sync(lambda: _load_data_v2(schema_id, vid, update, clear, limit, start, end))


@task
def extract_feature_v2(ctx, schema_id, vid=0, start=0, end=0, for_test=False):
    start = int(start)
    end = float(end or "Inf")
    schema_id = int(schema_id)
    from remarkable.service.prompter import extract_feature_v2 as _extract_feature_v2

    _extract_feature_v2(schema_id, vid=vid, start=start, end=end, for_test=for_test)


@task
def train_v2(ctx, schema_id, vid=0):
    schema_id = int(schema_id)
    from remarkable.service.prompter import train_v2 as _train_v2

    _train_v2(schema_id, vid=vid)


@task
def archive_modelv2_for(ctx, schema_id, vid=0, name="szse"):
    from remarkable.service.prompter import PROMPTER_MODEL_FILES, archive_model, model_v2_path

    archive_path = model_v2_path(name)
    archive_model(os.path.splitext(archive_path)[0], PROMPTER_MODEL_FILES, schema_id, vid)


@task
def deploy_model_for(ctx, schema, name="szse"):
    """将预训练模型部署到指定 schema 下"""
    from remarkable.config import project_root

    model_path = os.path.join(project_root, "data", "model", name)
    aim_dir = os.path.join(project_root, "data", "prompter")
    if not os.path.exists(aim_dir):
        os.makedirs(aim_dir)
    shutil.copy(model_path, os.path.join(aim_dir, "%s.pkl" % (schema,)))


@task(klass=InvokeWrapper)
async def deploy_modelv2_for(ctx, schema_id, vid=0, name="szse"):
    """将预训练模型部署到指定 schema 下"""
    from remarkable.service.deploy import deploy_prompter_model

    await deploy_prompter_model(schema_id, name, vid)


@task
def prompt_element(ctx, start=None, end=None, mold=None, overwrite=False, workers=0, save=None, god=False, vid=None):
    """预测答案（初步定位）"""
    from remarkable import logger
    from remarkable.common.multiprocess import run_by_batch
    from remarkable.db import pw_db
    from remarkable.pw_models.question import NewQuestion
    from remarkable.service.prompter import predict_crude_answer_by_range

    start = int_or_none(start)
    end = int_or_none(end)
    mold = int_or_none(mold)
    vid = int_or_none(vid)
    stmt = TRUE
    if start:
        stmt &= NewQuestion.fid >= start
    else:
        subquery = NewQuestion.select(fn.MIN(NewQuestion.fid))
        stmt &= NewQuestion.fid >= subquery
    if end:
        stmt &= NewQuestion.fid <= end
    else:
        subquery = NewQuestion.select(fn.MAX(NewQuestion.fid))
        stmt &= NewQuestion.fid <= subquery

    if mold:
        stmt &= NewQuestion.mold == mold

    tasks = []
    with pw_db.allow_sync():
        for question in NewQuestion.select(NewQuestion.fid).where(stmt).order_by(NewQuestion.fid.desc()):
            tasks.append((question.fid, question.fid, mold, overwrite, save, god, vid))

    logger.info(f"Total: {len(tasks)}, Min fid: {tasks[-1][0]}, Max fid: {tasks[0][0]}")

    for _ in run_by_batch(predict_crude_answer_by_range, tasks, workers=workers):
        pass


@task(klass=InvokeWrapper)
async def stat(ctx, mold=None, start=None, end=None, headnum=10, save=0, host=None):
    from remarkable.optools.stat_scriber_answer import StatScriberAnswer

    await StatScriberAnswer(
        headnum=headnum,
        from_id=start,
        to_id=end,
        mold=mold,
        save=save,
        host=host,
    ).stat_crude_answer()
