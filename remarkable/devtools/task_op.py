"""
主要放一些和主业务流程相关的命令
"""

import functools
import json
import logging
import os
import shutil
import time
import traceback
from copy import deepcopy
from pathlib import Path

from invoke import task
from tornado.ioloop import IOLoop

from remarkable.common.util import loop_wrapper
from remarkable.config import get_config, project_root
from remarkable.db import IS_GAUSSDB, IS_MYSQL, db, peewee_transaction_wrapper, pw_db
from remarkable.devtools import (
    InvokeWrapper,
    model_version_export_path,
    qid_from_stdin,
    read_ids_from_file,
    sql_file_filter,
)


@task
def make_pdf_cache(ctx, start, end, force=False, sync=False):
    """批量补充 pdf 缓存"""
    from remarkable.worker.tasks import cache_pdf_file

    for fid in range(int(start), int(end) + 1):
        if sync:
            cache_pdf_file(fid, force=force)
        else:
            cache_pdf_file.delay(fid, force=force)


@task(klass=InvokeWrapper)
async def make_questions(ctx, start, end):
    """批量生成题目（用于修复生成题目失败的文档）"""
    from remarkable.models.new_file import NewFile
    from remarkable.pw_models.question import NewQuestion

    async with pw_db.atomic():
        for i in range(start, end + 1):
            _file = await NewFile.find_by_id(i)
            if _file:
                print("make question: file {}".format(i))
                for mold in _file.molds:
                    await NewQuestion.create_by_mold(_file.id, mold)


@peewee_transaction_wrapper
async def _update_names(update_info):
    from remarkable.models.new_file import NewFile

    for file_id, name in update_info.items():
        print("update file_id {}, name {}".format(file_id, name))
        await NewFile.update_by_pk(file_id, name=name)


@task
def update_filename(ctx, file_path):
    update_info = {}
    with open(file_path, "r", encoding="utf-8") as input_file:
        for line in input_file.readlines():
            line_data = line.split("\t")
            if len(line_data) <= 2:
                continue
            print("{} ----> {}".format(line_data[1], line_data[-1].strip()))
            update_info[int(line_data[0])] = line_data[-1].strip()
    func = functools.partial(_update_names, update_info)
    IOLoop.current().run_sync(func)


@task
def import_schema(ctx, name=None, reset=False, overwrite=False, only=None):
    """导入 data/schema.json 到数据库, 参数: (name='schema', )"""
    if name is None:
        name = get_config("client.name")
    loop_wrapper(_import_schema)(name, reset=reset, overwrite=overwrite, only=only)


@peewee_transaction_wrapper
async def _import_schema(name, reset=False, overwrite=False, only=None):
    """导入 data/schema.json 到数据库, 参数: (name='schema', )"""
    from remarkable.common.util import generate_timestamp, md5json
    from remarkable.pw_models.model import NewMold

    if reset is True:
        await pw_db.execute("update mold set deleted_utc=extract(epoch from now())::int")
    await modify_seq_id()
    file_path = Path(project_root) / "data" / "schema" / f"{name}_schema.json"
    if not Path.exists(file_path):
        logging.info(f'{file_path} not found, please check parameter: "name"')
        return
    with open(file_path, "r") as schema_fp:
        schema_list = json.load(schema_fp)
    for idx, _schema in enumerate(schema_list):
        schema = _schema["data"]
        deleted_utc = _schema["deleted_utc"]
        mold_type = _schema.get("mold_type", 0)
        predictor_option = _schema.get("predictor_option", {"framework_version": "1.0"})
        predictors = _schema.get("predictors")
        meta = _schema.get("meta", {})
        master = _schema.get("master")
        name = schema["schemas"][0]["name"]

        if only and name != only:
            continue

        logging.info("import schema %s", name)
        params = {
            "name": name,
            "checksum": md5json(schema),
            "data": schema,
            "predictor_option": predictor_option,
            "predictors": predictors,
            "mold_type": mold_type,
            "deleted_utc": deleted_utc,
            "meta": meta,
            "master": master,
        }
        mold = await NewMold.find_by_kwargs(name=name, deleted_utc=deleted_utc)  # 导出的数据里可能包含deleted_utc>0的
        new_mold = None
        if not mold:
            logging.info("create new mold...")
            params["created_utc"] = generate_timestamp() + idx
            new_mold = await pw_db.create(NewMold, **params)
        else:
            if overwrite:
                logging.info("update mold...")
                await mold.update_(**params)
            else:
                logging.info(f"mold: {name} exists, you can force update by set overwrite True.")

        logging.info(
            f"import schema {name}(id={new_mold.id if new_mold else mold.id}), you may copy prompter model for it."
        )
        await modify_seq_id()


async def modify_seq_id():
    seq_name = "mold" if IS_MYSQL else "mold_id_seq"
    seq_data = await pw_db.get_seq_by_name(seq_name)
    old_seq_id = seq_data.seq_id if seq_data else 1

    get_max_id = "select max(id) as seq_id from mold;"
    seq_data = await pw_db.first(get_max_id)
    max_id = seq_data.seq_id if seq_data.seq_id else 1

    if old_seq_id >= max_id:  # seq_id 不需要修改
        return

    restart_value = max_id + 1
    if IS_GAUSSDB:
        # GaussDB 使用 SETVAL
        alter_seq_sql = f"SELECT SETVAL('mold_id_seq', {restart_value}, true);"
    elif IS_MYSQL:
        # MySQL 使用 ALTER TABLE 修改 AUTO_INCREMENT
        alter_seq_sql = f"ALTER TABLE mold AUTO_INCREMENT = {restart_value};"
    else:
        # PostgreSQL 使用 ALTER SEQUENCE
        alter_seq_sql = f"ALTER SEQUENCE mold_id_seq RESTART WITH {restart_value};"

    await pw_db.execute(alter_seq_sql)
    logging.info("modify seq_id %s to: %s", old_seq_id, restart_value)


@task(
    help={
        "delta": "delta为True时, 为增量导出指定的schema, 也适用于更新某些schema的信息",
        "mold_ids": "schema id 的字符串列表，例如 -m 1,2,3,4",
    }
)
def export_schema(ctx, start=None, end=None, name=None, delta=False, deleted_include=False, mold_ids=None):
    """导出 data/schema.json"""
    if name is None:
        name = get_config("client.name")
    if mold_ids:
        mold_ids = [int(i) for i in mold_ids.split(",")]
    _export_schema(start, end, name, delta, deleted_include, mold_ids)


@loop_wrapper
@peewee_transaction_wrapper
async def _export_schema(start, end, name, delta=False, deleted_include=False, mold_ids=None):
    from remarkable.pw_models.model import NewMold

    if mold_ids:
        molds = await pw_db.execute(NewMold.select(deleted_include=deleted_include).where(NewMold.id.in_(mold_ids)))
    else:
        molds = await NewMold.list_by_range(start, end, deleted_include)
    logging.info(f"export {len(molds)} schemas")
    if not molds:
        return
    schema_list = [
        {
            "data": mold.data,
            "predictor_option": mold.predictor_option,
            "mold_type": mold.mold_type,
            "deleted_utc": mold.deleted_utc,
            "predictors": mold.predictors,
            "meta": mold.meta,
            "master": mold.master,
        }
        for mold in molds
    ]
    schema_path = Path(project_root) / "data" / "schema"
    if not Path.exists(schema_path):
        Path.mkdir(schema_path)
    schema_file_path = schema_path / f"{name}_schema.json"
    if delta and schema_file_path.exists():
        schema_list = process_delta_schema(schema_file_path, schema_list)
    with open(schema_file_path, "w") as schema_fp:
        json.dump(schema_list, schema_fp, ensure_ascii=False, indent=4)
    logging.info(f"export file {schema_file_path} success...")


def process_delta_schema(schema_file_path, schema_list):
    with open(schema_file_path, "r") as schema_fp:
        origin_schema = json.load(schema_fp)
    origin_schema_names = {}
    for idx, schema in enumerate(origin_schema):
        origin_schema_names[schema["data"]["schemas"][0]["name"]] = idx

    # 统计需要修改的schema
    exists_idx = []
    for schema in schema_list:
        now_schema_name = schema["data"]["schemas"][0]["name"]
        origin_schema_idx = origin_schema_names.get(now_schema_name)
        if origin_schema_idx:
            exists_idx.append(origin_schema_idx)
            logging.info(f"{now_schema_name} exists, will use new schema data")

    # 保留不需要修改的schema
    need_hold_schema_list = []
    for idx, schema in enumerate(origin_schema):
        if idx not in exists_idx:
            need_hold_schema_list.append(schema)
    schema_list = need_hold_schema_list + schema_list
    return schema_list


@task
def copy_schema(ctx, mid, dst_name):
    """从已有的schema复制一个新的schema"""
    _copy_schema(mid, dst_name)


@loop_wrapper
@peewee_transaction_wrapper
async def _copy_schema(mid, dst_name):
    from remarkable.pw_models.model import NewMold

    from_mold = await NewMold.find_by_id(mid)
    if not from_mold:
        logging.info("mold not exists")
    data = deepcopy(from_mold.data)
    data["schemas"][0]["name"] = dst_name
    params = {
        "name": dst_name,
        "checksum": from_mold.checksum,
        "data": data,
        "predictor_option": from_mold.predictor_option,
        "mold_type": from_mold.mold_type,
    }
    new_mold = await NewMold.create(**params)
    logging.info(f"copy mold {from_mold.name} to {new_mold.name}")


@task(klass=InvokeWrapper)
async def make_pdfinsights(
    ctx,
    start=0,
    end=0,
    tree=0,
    mold=None,
    overwrite=False,
    ocr=False,
    garbled=False,
    from_file=None,
):
    """补充文档的 pdfinsight 信息"""
    from remarkable.common.constants import AIStatus, PDFParseStatus
    from remarkable.models.new_file import NewFile
    from remarkable.pw_models.question import NewQuestion
    from remarkable.worker.tasks import process_file

    cond = True
    if start:
        cond &= NewFile.id >= start
    if end:
        cond &= NewFile.id <= end
    if tree:
        cond &= NewFile.tree_id == tree
    if mold:
        cond &= NewFile.molds.contains(mold)
    if from_file:
        with open(from_file, "r", encoding="utf-8") as f:
            fids = [int(i.strip()) for i in f if i.strip().isdigit()]
            cond &= NewFile.id.in_(fids)
    files = await pw_db.execute(NewFile.select().where(cond))
    for file in files:
        if not file.pdfinsight or overwrite:
            file.pdf_parse_status = PDFParseStatus.PENDING
            cond = NewQuestion.fid == file.id
            if mold:
                cond &= NewQuestion.mold == int(mold)

            await pw_db.execute(NewQuestion.update(ai_status=AIStatus.TODO.value).where(cond))
        logging.info("make pdfinsight: file %s", file.id)
        await process_file(file, ocr=ocr, garbled=garbled)


@task
def inspect_rules(ctx, start=0, end=0, mold=None, workers=0):
    """审核"""
    sub_run_inspect(start, end, mold=mold, workers=workers)


@loop_wrapper
async def sub_run_inspect(start, end, mold=None, workers=0):
    from remarkable.common.multiprocess import run_in_multiprocess
    from remarkable.service.rule import (
        do_inspect_rule_pipe,
    )

    # TODO: 把 preset_answer 条件去掉了，需要后面的步骤检查是否 ready
    sql = """
    select file.id from file
    where array_length(file.molds, 1) > 0
    """
    sql = sql_file_filter(sql, start=start, end=end, mold=mold, order_by=" order by file.id desc")
    rows = await db.raw_sql(sql)
    run_in_multiprocess(do_inspect_rule_pipe, [fid for (fid,) in rows], workers=workers)


@peewee_transaction_wrapper
@qid_from_stdin
async def _update_file_progress(qid):
    from remarkable.common.file_progress import QuestionProgress

    question_progress = QuestionProgress(qid)
    await question_progress.update_progress()


@task
def update_file_progress(ctx):
    """更新文件标注进度"""
    IOLoop.current().run_sync(_update_file_progress)


@task
def export_answers(ctx, mold):
    from remarkable.optools.migrate_answer import do_export_answers

    do_export_answers(mold)


@task
def import_answers(ctx, mold):
    from remarkable.optools.migrate_answer import do_import_answers

    do_import_answers(mold)


@task
def run_crude_answer_statistic(ctx, mold, save=None, headnum=5, orderby="rate", from_id=0, to_id=-1):
    from remarkable.optools.stat_scriber_answer import StatScriberAnswer

    @loop_wrapper
    async def _run():
        await StatScriberAnswer(
            headnum=headnum, mold=mold, save=save, orderby="rate", prompt=False, from_id=from_id, to_id=to_id
        ).stat_crude_answer()

    _run()


@task
def set_question_answer(ctx, mold, start=None, end=None, project=None):
    """把正确答案填到question.answer中"""
    from remarkable.pw_models.question import NewQuestion
    from remarkable.service.answer import set_convert_answer

    @loop_wrapper
    @peewee_transaction_wrapper
    async def run():
        questions = await NewQuestion.list_by_range(mold=mold, start=start, end=end, project=project)
        for question in questions:
            try:
                logging.info("set question answer: %s", question.id)
                await question.set_answer()
                if get_config("web.answer_convert"):
                    await set_convert_answer(question.id)
            except Exception as ex:
                traceback.print_exc()
                logging.error("error in preset answer for question %s, %s", question.id, ex)

    run()


@task
def del_conf_comment(ctx, conf_path):
    """删除配置文件中的注释内容"""
    with open(conf_path, "r") as in_file, open(conf_path + ".out", "w") as out_file:
        for line in in_file:
            if line.startswith("#"):
                continue
            text = line.split("#")[0].rstrip()
            out_file.write(text + "\n")
    logging.info("All comments removed!")


@task
def migrate_answer_schema(
    ctx, mid, start=None, end=None, aim_mid=None, overwrite=False, safe_mode=False, update_timestamp=True
):
    """批量迁移答案 schema"""
    from remarkable.common.util import md5json
    from remarkable.pw_models.model import NewMold
    from remarkable.pw_models.question import NewQuestion
    from remarkable.service.new_question import MixinSchema, migrate_answers

    mid = int(mid)
    if not aim_mid:
        aim_mid = mid
    else:
        aim_mid = int(aim_mid)

    async def update_mold(mold_id):
        mold = await NewMold.find_by_id(mold_id)
        checksum = md5json(mold.data)
        if mold.checksum != checksum:
            logging.warning("Update checksum for mold %s", mold_id)
            await mold.update_(checksum=checksum)
        return mold

    @loop_wrapper
    @peewee_transaction_wrapper
    async def _run():
        aim_mold = await update_mold(aim_mid)
        questions = await NewQuestion.list_by_range(start=start, end=end, mold=mid)
        for question in questions:
            await migrate_answers(
                question,
                mixin_schema=MixinSchema(aim_mold),
                overwrite=overwrite,
                safe_mode=safe_mode,
                update_timestamp=update_timestamp,
            )

    _run()


@task
def clear_manual_tag(ctx, start, end, mold=None, attrs=None, clear=False, file_id_path=None):
    """
    清空manual标记，方便重跑时覆盖
    inv op.clear-manual-tag 500 --attrs="业务与技术-前五供应商,业务与技术-前五客户,IPO利润表（合并） --clear"
    """
    from remarkable.models.new_file import NewFile
    from remarkable.pw_models.model import NewSpecialAnswer
    from remarkable.pw_models.question import NewQuestion

    @loop_wrapper
    @peewee_transaction_wrapper
    async def _run(start, end, mold, attrs, clear, file_id_path):
        attrs = attrs.split(",") if attrs else []
        if file_id_path:
            file_ids = read_ids_from_file(file_id_path)
        else:
            files = await NewFile.list_by_range(mold, start, end)
            file_ids = [file.id for file in files]

        for fid in file_ids:
            logging.info("------file_id:%s-------:", fid)
            _file = await NewFile.find_by_id(fid)
            for mold_id in _file.molds:
                question = await NewQuestion.find_by_fid_mid(fid, mold_id)
                _answers = await NewSpecialAnswer.get_answers(question.id, NewSpecialAnswer.ANSWER_TYPE_EXPORT, top=1)
                if _answers:
                    _export_answer = _answers[0]
                    items = _export_answer.data["userAnswer"]["items"]
                    logging.info("答案总数:%s", len(items))
                    tag_num = 0
                    for item in items:
                        key_path = [x.split(":")[0] for x in json.loads(item["key"])]
                        if item.get("manual"):
                            if not attrs or any(attr in key_path for attr in attrs):
                                logging.info(item["key"])
                                logging.info(
                                    "page: %s",
                                    "、".join(
                                        [
                                            str(box.get("page", ""))
                                            for box_info in item["data"]
                                            for box in box_info["boxes"]
                                        ]
                                    ),
                                )
                                logging.info(
                                    "text: %s",
                                    "".join(
                                        [box.get("text", "") for box_info in item["data"] for box in box_info["boxes"]]
                                    ),
                                )
                                tag_num += 1
                                del item["manual"]
                    logging.info("有人工标记的答案数量:%s\n", tag_num)
                    if clear:
                        update_info = {
                            "data": _export_answer.data,
                        }
                        await NewSpecialAnswer.update_by_pk(_export_answer.id, **update_info)

    _run(start, end, mold, attrs, clear, file_id_path)


# @task
# def fix_sse_answer(ctx, start=None, end=None, mold=None, clear=False):
#     """
#     修改schema导致的`导出答案`错误
#     """
#
#     @loop_wrapper
#     @func_transaction
#     async def _run(start, end, mold):
#         sql = """
#         select f.id,f.qid,sa.data
#           from file as f
#           right join special_answer as sa on f.qid = sa.qid
#           where f.pdfinsight is not NULL and f.mold is not NULL
#           and sa.deleted_utc = 0 and sa.data is not NULL
#         """
#         sql = sql_file_filter(sql, start=start, end=end, mold=mold)
#
#         sql += " order by f.id;"
#
#         def error_key(key_path):
#             if len(key_path) == 2:
#                 if any(x in key_path[0] for x in ['IPO资产负债表', 'IPO利润表', 'IPO现金流量表']) and key_path[1] in ['项目']:
#                     return True
#             return False
#
#         update_sql = "update special_answer set data=null where qid = %(qid)s and answer_type='export_answer';"
#
#         res = []
#         async for fid, qid, answer in db.iterate(db.text(sql)):
#             print('-----------', fid, qid)
#             for item in answer['userAnswer']['items']:
#                 key_path = [x.split(':')[0] for x in json.loads(item['key'])][1:]
#                 if error_key(key_path):
#                     print(key_path)
#                     res.append(fid)
#                     if clear:
#                         await db.raw_sql(update_sql, **{"qid": qid})
#                     break
#         if res:
#             with open(os.path.join(project_root, 'data', 'fix_sse.json'), 'w') as w_p:
#                 w_p.write(','.join(map(str, res)))
#
#     _run(start, end, mold)


# @task
# def fix_answer_schema(ctx, start=0, end=0, mold=None, workers=0):
#     """修改schema名称之后，修改标注答案的key"""
#     IOLoop.current().run_sync(lambda: _fix_answer_schema(int(start), int(end), int(mold), workers))


# async def _fix_answer_schema(start, end, mold_id, workers=0):
#     # 获取mold_name
#     mold = await NewMold.find_by_id(mold_id)
#     mold_name, mold_checksum = mold.name, mold.checksum
#     sql = f"""
#         select a.id, a.data, f.id from answer a
#         left join question as q on a.qid = q.id
#         left join file as f on q.id = f.qid
#     """
#     sql = sql_file_filter(sql, start=start, end=end, mold=mold.id)

#     rows = await db.raw_sql(sql)
#     tasks = [(answer_id, answer, fid, mold_name, mold_checksum) for (answer_id, answer, fid) in rows]
#     run_in_multiprocess(_fix_answer, tasks, workers=workers, debug=True)


# def _fix_answer(args):
#     def _fix_schema(answer, mold_name, fid, mold_checksum):
#         if answer['schema']['schemas'][0]['name'] == mold_name:
#             logging.info('file %s answer already update...', fid)
#             return answer
#         answer['schema']['schemas'][0]['name'] = mold_name
#         answer['schema']['version'] = mold_checksum
#         for item in answer['userAnswer']['items']:
#             ori_key = item['key']
#             key_list = json.loads(ori_key)
#             schema_key = key_list[0]
#             schema_key_list = schema_key.split(':')
#             schema_key_list[0] = mold_name
#             key_list[0] = ':'.join(schema_key_list)
#             item['key'] = json.dumps(key_list, ensure_ascii=False)
#         logging.info('update file %s answer schema name to %s success...', fid, mold_name)
#         return answer

#     @loop_wrapper
#     async def run():
#         (answer_id, answer, fid, mold_name, mold_checksum) = args
#         answer = _fix_schema(answer, mold_name, fid, mold_checksum)
#         await NewAnswer.update_by_pk(answer_id, data=answer)

#     run()


@task(iterable=["mold"], help={"mold": "指定多个schema"})
def deploy_sse_anno_model(ctx, mold=None):
    """批量部署上交所公告模型"""
    from remarkable.pw_models.model import NewMold
    from remarkable.service.predictor import PREDICTOR_MODEL_FILES
    from remarkable.service.prompter import PROMPTER_MODEL_FILES

    async def _deploy_model(_schema_name, vid, archive_path, model_files):
        from remarkable.common.file_util import copy_model_file

        mold = await NewMold.find_by_name(_schema_name)
        if not mold:
            logging.error("can't find mold by name: %s", _schema_name)
            return
        schema_id = mold.id

        tmp_dir = os.path.join("/tmp", "scriber_%d" % time.time())
        if os.path.exists(tmp_dir):
            shutil.rmtree(tmp_dir)
        if not os.path.exists(archive_path):
            logging.info("%s not exist", archive_path)
            return
        shutil.unpack_archive(archive_path, tmp_dir)

        model_dir = os.path.join(get_config("training_cache_dir"), str(schema_id), str(vid))
        for fname in model_files:
            if copy_model_file(tmp_dir, model_dir, fname):
                print("copy file %s" % fname)
            else:
                print("file %s not exist" % fname)

        shutil.rmtree(tmp_dir)
        print("deploy %s to schema %s" % (archive_path, schema_id))

    @loop_wrapper
    @peewee_transaction_wrapper
    async def _run():
        config_map = get_config("prophet.config_map") or {}
        for schema_name in config_map.keys():
            if mold and schema_name not in mold:
                continue
            logging.info("*" * 50)
            logging.info("start deploy model for %s ...", schema_name)
            mold_num, _ = schema_name.split()
            name = f"sse_anno_{mold_num}"
            predictor_archive_path = os.path.join(project_root, "data", "model", "%s_predictor.zip" % name)
            prompter_archive_path = os.path.join(project_root, "data", "model", "%s_v2.zip" % name)

            await _deploy_model(schema_name, 0, predictor_archive_path, PREDICTOR_MODEL_FILES)
            await _deploy_model(schema_name, 0, prompter_archive_path, PROMPTER_MODEL_FILES)
            logging.info("deploy model for %s success ...", schema_name)

    _run()


@task
def push_predict_answer(ctx, qid):
    """
    推送预测答案
    """
    from remarkable.converter.utils import push_answer_to_remote

    @loop_wrapper
    async def run():
        await push_answer_to_remote(qid)

    run()


@task
def make_customer_answer(ctx, mold=None, start=None, end=None, project=None, tree_s=None, workers=0):
    """
    将question.answer转成客户定制化答案
    :return:
    """
    from remarkable.common.multiprocess import run_in_multiprocess
    from remarkable.converter.utils import generate_customer_answer
    from remarkable.pw_models.question import NewQuestion

    @loop_wrapper
    async def run():
        return [
            q.id
            for q in await NewQuestion.list_by_range(
                mold=mold,
                start=start,
                end=end,
                project=project,
                tree_l=tree_s,
                special_cols=["id"],
            )
        ]

    run_in_multiprocess(generate_customer_answer, run(), workers=workers, ctx_method="spawn")


@task
def gen_field_map(ctx, mold=3):
    """
    深交所生成 字段映射 文件 默认生成 `重组报告业务i`的字段映射文件
    """
    from remarkable.worker.tasks.export_tasks import gen_field_map_file

    @loop_wrapper
    @peewee_transaction_wrapper
    async def _run(mold):
        await gen_field_map_file(mold)

    _run(mold)


@task
def schema_to_group(ctx, mold="", group=""):
    """
    深交所：指定schema到项目组
    """
    from remarkable.pw_models.model import NewMold

    @loop_wrapper
    @peewee_transaction_wrapper
    async def _run(mold, group):
        if not (mold and group):
            raise RuntimeError("mold and group are necessary")
        for mold_id in mold.split(","):
            _mold = await NewMold.find_by_id(mold_id)
            if not _mold:
                continue
            logging.info("assign schema%s(%s) to group:%s", _mold.id, _mold.name, group)
            await _mold.update_(group_tags=group.split(","))

    _run(mold, group)


@task
def clear_sync_schedule_lock(ctx):
    from remarkable.service.sync import clear_sync_schedule_lock as _clear

    _clear()


@task
def run_updown_stream_sync(ctx):
    from remarkable.plugins.answer_poster.tasks import answer_sync
    from remarkable.plugins.synchronization.tasks import file_sync
    from remarkable.service.sync import clear_sync_schedule_lock

    clear_sync_schedule_lock()

    @loop_wrapper
    async def run():
        await file_sync()
        await answer_sync()

    run()


@task
def update_framework_version(ctx, mold_id, version="2.0"):
    """
    升级预测框架版本
    inv op.update-framework-version 7
    """
    from remarkable.pw_models.model import NewMold

    @loop_wrapper
    @peewee_transaction_wrapper
    async def run():
        mold = await NewMold.find_by_id(mold_id)
        if not mold:
            return
        predictor_option = mold.predictor_option if mold.predictor_option else {}
        predictor_option.update({"framework_version": version})
        await mold.update_(predictor_option=predictor_option)
        logging.info(f"change mold {mold.name} framework_version to {version}")

    run()


@task(klass=InvokeWrapper)
async def gen_developer_predictors(ctx, mid, name="", overwrite=False):
    """
    name 可指定模型版本名称
    force为True 可强制更新对应模型版本的模型文件
    """
    from remarkable.service.deploy import deploy_developer_model_version

    await deploy_developer_model_version(mid, name, overwrite)


@task(
    klass=InvokeWrapper,
    help={
        "dev": "是否为开发环境（本地开发环境模型默认不启用db模型）",
        "mid": "既可以是schema id，也可以是schema name",
        "enable": "是否启用模型（如果没有模型版本概念的环境，需要显式启用当前模型）",
    },
)
async def deploy_model(ctx, mid, name="", version_id=None, version_name="", overwrite=False, dev=False, enable=False):
    """部署模型（包括predictor和prompter）"""
    from remarkable.service.deploy import deploy_developer_model_version, deploy_predictor_model, deploy_prompter_model

    if not version_id:
        version_id = (
            (await deploy_developer_model_version(mid, version_name, overwrite, is_enabled=enable)) if not dev else 0
        )
    version_id = int(version_id)
    await deploy_predictor_model(mid, name, version_id)
    await deploy_prompter_model(mid, name, version_id)


@task(
    klass=InvokeWrapper,
    help={"vid": "模型版本id"},
)
async def export_model_version(ctx, vid):
    """导出模型版本"""
    from remarkable.models.model_version import NewModelVersion

    model_version = await NewModelVersion.find_by_id(vid)
    if not model_version:
        logging.info("model version not exists")

    export_path = model_version_export_path(vid)
    with open(export_path, "w", encoding="utf-8") as file_obj:
        json.dump(model_version.to_dict(), file_obj, ensure_ascii=False)

    logging.info(f"export model_version to {export_path}")


@task(
    klass=InvokeWrapper,
    help={"import_path": "模型版本导出文件所在路径"},
)
async def import_model_version(ctx, mid, import_path):
    """导入模型版本"""
    from remarkable.common.constants import ModelEnableStatus
    from remarkable.models.model_version import NewModelVersion
    from remarkable.pw_models.model import NewMold

    mold = await NewMold.find_by_id(mid)
    if not mold:
        logging.info("mold not exists")

    with open(import_path, "r", encoding="utf-8") as file_obj:
        model_version = json.load(file_obj)

        new_model_version = await NewModelVersion.create(
            **{
                "mold": mid,
                "name": model_version["name"],
                "model_type": model_version["model_type"],
                "status": model_version["status"],
                "dirs": [],
                "files": [],
                "enable": ModelEnableStatus.DISABLE.value,
                "predictors": model_version["predictors"],
                "predictor_option": model_version["predictor_option"],
            },
        )

    logging.info(f"import model_version from {import_path}, {new_model_version.id=}")
