import asyncio
import http
import json
import logging
import os
import pickle
import re
import tempfile
import urllib.parse
from io import BytesIO
from zipfile import ZIP_DEFLATED, ZipFile

import httpx
import requests
import zstandard
from invoke import task
from utensils.syncer import sync

from remarkable.common.util import loop_wrapper
from remarkable.config import get_config
from remarkable.db import IS_MYSQL, db, peewee_transaction_wrapper, pw_db
from remarkable.devtools import InvokeWrapper

SYNC_HOST = (get_config("web.apis.sync_host") or "").rstrip("/")


def _get_sync_tables():
    """Lazy load SYNC_TABLES to avoid circular imports"""
    from remarkable.models.cmf_china import CmfModelAuditAccuracy
    from remarkable.models.model_version import NewModelVersion
    from remarkable.models.new_file import NewFile
    from remarkable.pw_models.answer_data import NewAnswerData
    from remarkable.pw_models.audit_rule import NewAuditResult, NewAuditRule
    from remarkable.pw_models.law import LawCheckPoint
    from remarkable.pw_models.law_judge import LawJudgeResult
    from remarkable.pw_models.model import (
        NewAnswer,
        NewExtractMethod,
        NewFileMeta,
        NewFileProject,
        NewFileTree,
        NewMold,
        NewRuleClass,
        NewRuleItem,
        NewRuleResult,
        NewSpecialAnswer,
        NewTrainingData,
    )
    from remarkable.pw_models.question import NewQuestion

    return {
        "file": NewFile,
        "question": NewQuestion,
        "mold": NewMold,
        "model_version": NewModelVersion,
        "training_data": NewTrainingData,
        "answer": NewAnswer,
        "special_answer": NewSpecialAnswer,
        "tree": NewFileTree,
        "project": NewFileProject,
        "file_meta": NewFileMeta,
        "rule_results": NewRuleResult,
        "extract_methods": NewExtractMethod,
        "rule_classes": NewRuleClass,
        "rule_items": NewRuleItem,
        "answer_data": NewAnswerData,
        "cgs_result": NewAuditResult,
        "cgs_rule": NewAuditRule,
        "law_judge_result": LawJudgeResult,
        "law_check_point": LawCheckPoint,
        "cmf_model_audit_accuracy": CmfModelAuditAccuracy,
    }


async def create_model_for_rows(table, rows):
    if isinstance(rows, list):
        for row in rows:
            await create_model(table, row)
    else:
        await create_model(table, rows)


async def create_model(table, columns):
    from remarkable.common.constants import ModelEnableStatus

    SYNC_TABLES = _get_sync_tables()
    if not columns:
        return None
    # if 'uid' in columns:
    #     columns['uid'] = 1
    if table == "model_version" and "enable" in columns:
        # 默认不使用线上配置模型
        columns["enable"] = ModelEnableStatus.DISABLE.value
    data = await SYNC_TABLES[table].create_or_update(**columns)
    if not IS_MYSQL and "id" in columns:
        await _update_id_seq(SYNC_TABLES[table].table_name())
    return data


def encode_path(path):
    from remarkable.security import authtoken

    app_name = get_config("app.app_id")
    secret_key = get_config("app.secret_key")
    return authtoken.encode_url(path, app_name, secret_key)


async def _update_id_seq(table):
    rows = await db.raw_sql("SELECT c.relname FROM pg_class c WHERE c.relkind = 'S';", "all")
    for (relname,) in rows:
        if re.search(r"^{}_id.*".format(table), relname):
            seq_table = relname
            break
    else:
        return await db.raw_sql("select version()", "status")
    sql = "SELECT setval('{}', (SELECT MAX(id) FROM {})+1);".format(seq_table, table)
    await db.raw_sql(sql, "status")


def _sync_file(args):
    from remarkable.common.storage import localstorage

    file_id, mold, pdf_cache, local_path, host, model_version = args
    parsed_host = urllib.parse.urlparse(host)
    try:
        if local_path and os.path.isfile(local_path):
            zip_file = ZipFile(open(local_path, "rb"))
        else:
            url = (
                f"{parsed_host.scheme}://{parsed_host.netloc}{parsed_host.path}/api/v1/plugins/debug/file/{file_id}/export/{int(pdf_cache)}?key="
                f"u-never-know&mold={mold or 0}&model_version={int(model_version)}"
            )
            logging.info(url)
            rsp = requests.get(url, timeout=60)
            if rsp.status_code != http.HTTPStatus.OK:
                logging.error(f"{file_id} download failed, status code: {rsp.status_code}, content: {rsp.content}")
                return None
            zip_file = ZipFile(BytesIO(rsp.content), "r")
        add_prefix = get_config("client.add_time_hierarchy", False)
        meta = None
        for filename in zip_file.namelist():
            if filename == "meta.json":
                data = zip_file.read(filename)
                if isinstance(data, bytes):
                    data = data.decode("utf-8")
                meta = json.loads(data)
            elif filename.startswith(localstorage.cache_root):
                if pdf_cache:
                    localstorage.write_file(filename, zip_file.read(filename))
            else:
                if add_prefix:
                    filepath = filename
                else:
                    filepath = os.path.join(filename[:2], filename[2:])
                localstorage.write_file(filepath, zip_file.read(filename))
    except Exception as exp:
        logging.error(exp)
        meta = []
    return meta


@task
def file(ctx, file_id=0, mold_id=0, pdf_cache=False, local_path=None, model_version=False):
    loop_wrapper(_sync_files)(
        [int(file_id)], mold=int(mold_id), pdf_cache=pdf_cache, local_path=local_path, model_version=model_version
    )


@task
def files(
    ctx,
    start=0,
    end=0,
    from_file="",
    tree_id=0,
    file_only=False,
    mold=None,
    pdf_cache=False,
    workers=0,
    batch_size=50,
    model_version=False,
    no_pkey=False,
    sync_config_path=None,
):
    mold = int(mold) if mold else 0

    if int(tree_id) > 0:
        fids = get_fids(tree_id)
    elif from_file:
        with open(from_file, "r") as file_obj:
            fids = [int(i.strip()) for i in file_obj if i.strip().isdigit()]
    else:
        fids = list(range(int(start), int(end) + 1))

    loop_wrapper(_sync_files)(
        fids,
        mold=mold,
        pdf_cache=pdf_cache,
        workers=workers,
        batch_size=batch_size,
        file_only=file_only,
        model_version=model_version,
        no_pkey=no_pkey,
        sync_config_path=sync_config_path,
    )


async def sync_no_pkey(meta: dict[str, dict | list[dict]], sync_config: dict):
    """
    同步范围: ['file', 'question', 'answer']
    将文件置于tree_id对应的文件夹下
    sync_config:
        {
            "tree_id": 100,
            "mold_map": {"1": "2"},
            "file_uid": 1,
            "answer_uis": 2,
        }
    :return:
    """
    from remarkable.common.exceptions import CustomError
    from remarkable.pw_models.model import NewFileProject, NewFileTree
    from remarkable.pw_models.question import NewQuestion

    tree_id = sync_config["tree_id"]
    file_uid = sync_config["file_uid"]
    answer_uid = sync_config["answer_uid"]

    file_tree = await NewFileTree.get_by_id(tree_id)
    if not file_tree:
        raise CustomError("Item Not Found")
    project = await NewFileProject.find_by_id(file_tree.pid)
    if not project:
        raise CustomError("Item Not Found")

    mold_map = {int(key): int(value) for key, value in sync_config["mold_map"].items()}
    file_data = meta["file"]
    file_data.pop("id")
    file_data["uid"] = file_uid
    file_data["tree_id"] = tree_id
    file_data["pid"] = project.id
    file_molds = []
    for mold in file_data["molds"]:
        if mold in mold_map:
            file_molds.append(mold_map[mold])
    file_data["molds"] = file_molds
    file = await create_model("file", file_data)

    qid_map = {}
    for question_data in meta["question"]:
        if question_data["mold"] not in mold_map:
            continue
        question_data["mold"] = mold_map[question_data["mold"]]
        question_data["fid"] = file.id
        question_data["data"]["file_id"] = file.id
        question_data["checksum"] = NewQuestion.gen_checksum(file.id, question_data["mold"])
        question_data.pop("mark_uids")
        question_data.pop("mark_users")
        qid = question_data.pop("id")
        question = await create_model("question", question_data)
        qid_map[qid] = question.id

    for answer_data in meta["answer"]:
        if answer_data["qid"] not in qid_map:
            continue
        answer_data["qid"] = qid_map[answer_data["qid"]]
        answer_data["uid"] = answer_uid
        answer_data.pop("id")
        await create_model("answer", answer_data)


# @func_transaction
async def update_if_existed(meta, mold, dst_mold):
    from remarkable.models.new_file import NewFile
    from remarkable.pw_models.model import NewMold
    from remarkable.pw_models.question import NewQuestion

    try:
        _mold = await NewMold.find_by_id(dst_mold or mold["id"])
        if not _mold and mold:
            # 目标schema不存在则新建一个
            mold["id"] = dst_mold
            mold["uid"] = 1
            await create_model("mold", mold)

        _file = await NewFile.find_by_hash(meta["file"]["hash"])

        if _file:
            await NewFile.update_by_pk(_file.id, pdfinsight=meta["file"]["pdfinsight"])
        else:
            # 删除可能存在的被标记删除的文件记录
            await db.raw_sql(
                "DELETE FROM file WHERE hash = %(hash)s AND deleted_utc != 0;",
                "status",
                **{"hash": meta["file"]["hash"]},
            )
            # 不需要id, 直接使用目标数据库id sequence
            meta["file"].pop("id")
            # tree_id, pid赋0, 隐藏文件
            meta["file"]["tree_id"] = 0
            meta["file"]["pid"] = 0
            # 更新schema id
            meta["file"]["mold"] = dst_mold
            _file = await create_model("file", meta["file"])

        # 刷新question表关联fid
        meta["question"]["data"]["file_id"] = _file.id
        meta["question"]["checksum"] = NewQuestion.gen_checksum(_file.id, mold)

        # 使用用户答案填充预测答案
        if meta["answers"]:
            meta["question"]["preset_answer"] = meta["answers"][0]["data"]
        else:
            meta["question"]["preset_answer"] = meta["question"]["preset_answer"]

        question = await NewQuestion.find_by_fid_mid(_file.id, mold)
        if question:
            # 发现本地已关联question, 更新answer相关字段内容
            await pw_db.update(
                question,
                preset_answer=meta["question"]["preset_answer"],
                crude_answer=meta["question"]["preset_answer"],
                confirmed_answer=meta["question"]["confirmed_answer"],
            )

        else:
            # 本地无关联question则新建
            meta["question"].pop("id")
            await create_model("question", meta["question"])
    except Exception as e:
        logging.error("sync file %s error: %s", meta["file"]["id"], e)
    else:
        logging.info("sync file %s success", meta["file"]["id"])


# @func_transaction
async def cover_if_existed(meta: dict[str, dict | list[dict]], file_only=False):
    from remarkable.common.constants import AIStatus, QuestionStatus
    from remarkable.pw_models.law import (
        Law,
        LawCPsScenarios,
        LawOrder,
        LawRule,
        LawRulesScenarios,
        LawRuleStatus,
        LawScenario,
        LawsScenarios,
        LawStatus,
    )
    from remarkable.pw_models.law_judge import LawJudgeResult

    try:
        if file_only:
            # 清状态, 跳过不需要的表
            for table in ["mold", "answer", "special_answer", "answer_data", "law_check_point", "law_judge_result"]:
                meta.pop(table, None)
            for col in ["preset_answer", "crude_answer", "answer"]:
                meta["question"][col] = None
            meta["question"]["status"] = QuestionStatus.TODO
            meta["question"]["ai_status"] = AIStatus.SKIP_PREDICT
            for col in ["mark_uids", "mark_users"]:
                meta["file"][col] = []
            meta["file"]["progress"] = None

        if cps := meta.get("law_check_point"):
            # 这里将LawJudgeResult 和 LawCheckPoint的引用补全, id取负 (方便debug)
            # 另: 同步法规文件(文档库管理)使用命令`invoke sync.law`
            file_id = meta["file"]["id"]
            _scenario = await LawScenario.create_or_update(id=-file_id, name=str(-file_id), user_id=1)
            meta["file"]["scenario_id"] = _scenario.id
            _order = await LawOrder.create_or_update(id=-file_id, rank=-file_id, name=f"sync file {file_id}", user_id=1)
            await LawsScenarios.create_or_update(law_id=_order.id, scenario_id=_scenario.id, user_id=1)
            _law = await Law.create_or_update(
                id=-file_id, order_id=_order.id, name=f"sync file {file_id}", is_current=True, status=LawStatus.SPLIT
            )
            _rule = await LawRule.create_or_update(
                id=-file_id,
                law_id=_law.id,
                order_id=_order.id,
                content=f"file {file_id}",  # 没有同步role, debug前临时修改
                enable=True,
                status=LawRuleStatus.CONVERTED,
            )
            await LawRulesScenarios.create_or_update(
                rule_id=_rule.id, scenario_id=_scenario.id, user_id=1, order_id=_order.id, law_id=_law.id
            )
            for cp in cps:
                cp["order_id"] = _order.id
                cp["law_id"] = _law.id
                cp["rule_id"] = _rule.id
                await LawCPsScenarios.create_or_update(cp_id=cp["id"], scenario_id=_scenario.id, user_id=1)
            await pw_db.execute(LawJudgeResult.delete().where(LawJudgeResult.file == file_id))
            for result in meta.get("law_judge_result", []):
                result["law_order_id"] = _order.id
                result["rule_id"] = _rule.id

        for table, rows in meta.items():
            await create_model_for_rows(table, rows)
    except Exception as e:
        # logging.error("sync file %s error: %s", meta['file']['id'], e)
        logging.exception("", exc_info=e)
    else:
        logging.info("sync file %s success", meta["file"]["id"])


async def _sync_files(
    fids: list[int],
    mold=None,
    pdf_cache=False,
    workers=0,
    batch_size=50,
    local_path="",
    file_only=False,
    model_version=False,
    no_pkey=False,
    sync_config_path=None,
):
    from remarkable.common.multiprocess import run_by_batch

    if no_pkey:
        assert sync_config_path
        sync_config = json.load(open(sync_config_path, "r"))

    tasks = [(file_id, mold, pdf_cache, local_path, SYNC_HOST, model_version) for file_id in fids]
    for data in run_by_batch(_sync_file, tasks, batch_size=batch_size, workers=workers):
        for meta in data:
            if not meta:
                continue
            if no_pkey:
                await sync_no_pkey(meta, sync_config)
            else:
                await cover_if_existed(meta, file_only)


async def _fetch_pdf_cache(dst_dir: str, fid: int) -> str | None:
    from remarkable.common.storage import localstorage

    url = f"{SYNC_HOST}/api/v1/plugins/debug/file/{fid}/export/1?key=u-never-know"
    async with httpx.AsyncClient(verify=False, timeout=30) as client:
        rsp = await client.get(url)
        if not httpx.codes.is_success(rsp.status_code):
            logging.error(f"{fid} download failed, status code: {rsp.status_code}, content: {rsp.content}")
            return None
    out_path = os.path.join(dst_dir, f"{fid}.zip")
    with ZipFile(BytesIO(rsp.content)) as zip_in, ZipFile(out_path, "w", compression=ZIP_DEFLATED) as zip_out:
        count = 0
        file_meta = None
        for filename in zip_in.namelist():
            if filename == "meta.json":
                file_meta = json.loads(zip_in.read(filename).decode())["file"]
                continue
            if file_meta and filename.replace("/", "").startswith(file_meta["pdf"]):
                count += 1
                zip_out.writestr(f"{file_meta['id']}_{file_meta['name']}", zip_in.read(filename))
                continue
            # kind = filetype.guess(zip_in.read(filename))
            # if kind and kind.extension == 'pdf':
            #     count += 1
            #     zip_out.writestr(f'{fid}_origin.pdf', zip_in.read(filename))
            #     continue
            if filename.startswith(localstorage.cache_root):
                count += 1
                zip_out.writestr(os.path.basename(filename), zip_in.read(filename))
    if count == 0:
        logging.error(f"No cache file found in {fid}")
        return None
    return out_path


def seq_iter(seq, step=5):
    from_idx, to_idx = 0, step
    while chunk := seq[from_idx:to_idx]:
        from_idx, to_idx = to_idx, to_idx + step
        yield chunk


@task(klass=InvokeWrapper)
async def fetch_pdf_cache(
    ctx,
    start=0,
    end=0,
    from_file="",
    tree_id=0,
    dst_dir="",
    workers=5,
):
    """下载PDF&缓存"""
    if not dst_dir:
        dst_dir = tempfile.mkdtemp(dir=ctx["project_root"])
        logging.warning(f"No dst_dir specified, use temp dir({dst_dir}) instead")
    if not os.path.exists(dst_dir):
        os.makedirs(dst_dir)
    if int(tree_id) > 0:
        fids = get_fids(tree_id)
    elif from_file:
        with open(from_file, "r") as file_obj:
            fids = [int(i.strip()) for i in file_obj if i.strip().isdigit()]
    else:
        fids = list(range(int(start), int(end) + 1))

    for file_ids in seq_iter(fids, workers):
        await asyncio.gather(*(_fetch_pdf_cache(dst_dir, i) for i in file_ids))


def get_fid_list(mold, host):
    if host:
        global SYNC_HOST
        SYNC_HOST = host
    url = "{}/api/v1/plugins/debug/mold/{}/files?key=u-never-known".format(SYNC_HOST, mold)
    rsp = requests.get(url, timeout=10)
    if rsp.status_code != 200:
        logging.error(rsp.status_code, rsp.text)
        return []
    return rsp.json()["data"]


@task
def questions(ctx, src_mold, host=None):
    """同步指定环境某schema相关缓存答案到本地"""
    _sync_files(get_fid_list(src_mold, host))


def fetch_meta(host, fid, binary=False):
    from remarkable.common.storage import localstorage

    meta = None
    url = "{}/api/v1/plugins/debug/file/{}/export?key=u-never-know".format(host, fid)
    response = requests.get(url, timeout=10)
    if response.status_code != 200:
        logging.error(response.status_code, response.text)
        return meta

    zip_file = ZipFile(BytesIO(response.content), "r")
    for filename in zip_file.namelist():
        if filename != "meta.json":
            if binary:
                filepath = os.path.join(filename[:2], filename[2:])
                localstorage.write_file(filepath, zip_file.read(filename))
        else:
            data = zip_file.read(filename)
            if isinstance(data, bytes):
                data = data.decode("utf-8")
            meta = json.loads(data)
    return meta


@task
def export_all_answer(ctx, mold=2, host=None):
    """导出指定schema下所有文档的预测/标注答案"""
    from remarkable.common.util import export_answer

    std_dir, pred_dir = "mold_{}/std_dir".format(mold), "mold_{}/pred_dir".format(mold)
    if not os.path.exists(std_dir):
        os.makedirs(std_dir)
    if not os.path.exists(pred_dir):
        os.makedirs(pred_dir)

    for fid in get_fid_list(mold, host):
        meta = fetch_meta(host, fid)
        if meta:
            logging.info("Meta data get, file id: %s", fid)
            qid = meta["question"]["id"]
            if meta.get("answer") and meta["answer"].get("data"):
                std_ans = export_answer(meta["answer"]["data"], mold)
            else:
                logging.warning("Standard answer not found, qid: %s", qid)
                continue
            if meta["question"].get("preset_answer"):
                pred_ans = export_answer(meta["question"]["preset_answer"], mold)
            else:
                logging.warning("Predict answer not found, qid: %s", qid)
                continue
            with (
                open(os.path.join(std_dir, "{}_standard.json".format(qid)), "w") as std_fh,
                open(os.path.join(pred_dir, "{}_predict.json".format(qid)), "w") as pred_fh,
            ):
                std_fh.write(json.dumps(std_ans, ensure_ascii=False, indent=4))
                pred_fh.write(json.dumps(pred_ans, ensure_ascii=False, indent=4))
        else:
            logging.warning("No meta data found, skip file id: %s", fid)


@task
def re_run_cmp_task(ctx, mold, host=None, force=1):
    """重跑完备性审核任务"""
    host = host if host else SYNC_HOST
    url = "{}/api/v1/plugins/debug/mold/{}/files?key=u-never-known".format(host, mold)

    rsp = requests.get(url, timeout=10)
    if rsp.status_code != 200:
        logging.error(rsp.status_code, rsp.text)
        return

    for fid in rsp.json()["data"]:
        url = "{}/api/v1/plugins/debug/rule/{}/recheck?key=u-never-known&force={}".format(host, fid, force)
        rsp = requests.get(url, timeout=10)
        if rsp.status_code == 200:
            logging.info("file: %s task was launched successfully", fid)
        else:
            logging.error(rsp.status_code, rsp.text)


@task
def set_seq_id(ctx, seq_id=10000, force=False, seqname=None):
    """批量重设所有table的sequence id"""

    @loop_wrapper
    @peewee_transaction_wrapper
    async def _run():
        sql = "SELECT sequence_name FROM information_schema.sequences "
        if seqname:
            sql += "where sequence_name = '{}';".format(seqname)
        tables = await db.raw_sql(sql, "all")
        for (table,) in tables:
            value = await db.raw_sql("SELECT last_value FROM {}".format(table), "scalar")
            if force or value < seq_id:
                await db.raw_sql("SELECT setval('{table}', {id});".format(table=table, id=seq_id))

            logging.info(
                'The next seq id of table "%s" will start from %s',
                table,
                seq_id + 1 if force or value < seq_id else value + 1,
            )

    _run()


def get_related_fids(fid):
    path = f"/api/v1/plugins/debug/files/{fid}/related_fids"
    url = f"{SYNC_HOST}{encode_path(path)}"
    rsp = requests.get(url, timeout=10)
    return rsp.json()["data"] if rsp.ok else [fid]


def get_fids(tree_id, host=None):
    if host is None:
        host = SYNC_HOST
    path = f"/api/v1/plugins/debug/tree/{tree_id}/file_ids"
    url = f"{host}{encode_path(path)}"
    if "scriber" in host:
        url = f"{encode_path(host + path)}"  # 如果有subpath需要用这个
    rsp = requests.get(url, timeout=10)
    return rsp.json()["data"] if rsp.ok else []


@task(klass=InvokeWrapper)
async def chinaamc_cmp_task(_, task_id: str, pdf_cache=True):
    """同步华夏基金营销部比对任务数据"""
    from remarkable.models.new_user import NewAdminUser
    from remarkable.security.crypto_util import encode_jwt, make_bearer_header

    async with httpx.AsyncClient(headers=make_bearer_header(encode_jwt({"sub": "admin"}))) as client:
        response = await client.get(f"{SYNC_HOST}/api/v1/plugins/chinaamc_yx/compare-tasks/{task_id}/sync")
        response.raise_for_status()
    dctx = zstandard.ZstdDecompressor()
    cmp_task, *others = pickle.loads(dctx.decompress(response.content))
    user_info = cmp_task.user.to_dict()
    if cmp_task.user.name == "admin":
        for col in ["permission"]:
            user_info.pop(col)
        if local_user := await pw_db.first(NewAdminUser.select().where(NewAdminUser.name == "admin")):
            user_info["salt"] = local_user.salt
            user_info["password"] = local_user.password
    await cmp_task.user.__class__.insert_or_update(**user_info)
    await _update_id_seq(cmp_task.user.__class__.table_name())

    await cmp_task.project.__class__.insert_or_update(**cmp_task.project.to_dict())
    await _update_id_seq(cmp_task.project.__class__.table_name())

    task_dict = cmp_task.to_dict(recurse=False)
    task_dict["uid"] = task_dict.pop("user")
    task_dict["pid"] = task_dict.pop("project")
    await cmp_task.__class__.insert_or_update(**task_dict)
    await _update_id_seq(cmp_task.__class__.table_name())

    for other in others:
        await other.__class__.insert_or_update(**other.to_dict(recurse=False))
        await _update_id_seq(other.__class__.table_name())

    await _sync_files(cmp_task.fids, pdf_cache=pdf_cache)


@task
@sync
async def law(ctx, rank, jwt_token: str):
    from remarkable.common.storage import localstorage
    from remarkable.pw_models.law import (
        Law,
        LawCheckPoint,
        LawOrder,
        LawRule,
        LawRulesScenarios,
        LawScenario,
        LawsScenarios,
    )

    if not jwt_token.startswith("Bearer "):
        jwt_token = f"Bearer {jwt_token}"
    url = f"{SYNC_HOST}/api/v2/debug/laws/{rank}/debug-data"
    async with httpx.AsyncClient(verify=False, timeout=60) as client:
        rsp = await client.get(url, headers={"Authorization": jwt_token})
        if not httpx.codes.is_success(rsp.status_code):
            logging.error(f"law_file {rank} download failed, status code: {rsp.status_code}, content: {rsp.content}")
            return None
    with ZipFile(BytesIO(rsp.content)) as zip_file:
        from remarkable.routers.schemas.debug import DebugLawSchema

        law_order = DebugLawSchema.model_validate_json(zip_file.read("law.json"))
        rule_count = cp_count = draft_count = 0
        async with pw_db.atomic():
            scenario_map = dict(
                await pw_db.execute(
                    LawScenario.select(LawScenario.name, LawScenario.id)
                    .where(LawScenario.name.in_(law_order.scenario_names))
                    .tuples()
                )
            )
            if miss_scenario_names := [name for name in law_order.scenario_names if name not in scenario_map]:
                ids = await LawScenario.bulk_insert(
                    [{"name": name, "user_id": 1} for name in miss_scenario_names], iter_ids=True
                )
                scenario_map.update({name: pk for name, pk in zip(miss_scenario_names, list(ids))})

            rank = await LawOrder.max_rank_with_lock() + 1
            _law_order = await pw_db.create(
                LawOrder,
                rank=rank,
                name=law_order.name,
                is_template=law_order.is_template,
                refresh_status=law_order.refresh_status,
                meta=law_order.meta,
                user_id=1,
            )
            for scenario_id in scenario_map.values():
                await pw_db.create(LawsScenarios, law_id=_law_order.id, scenario_id=scenario_id, user=1)
            for law_file in law_order.laws:
                _law = await pw_db.create(Law, order_id=_law_order.id, **law_file.model_dump(exclude={"law_rules"}))
                if _law.pdfinsight:
                    localstorage.write_file(_law.pdfinsight_path(), zip_file.read(_law.pdfinsight))
                elif _law.chatdoc_unique:
                    pass
                else:
                    localstorage.write_file(_law.file_path(), zip_file.read(_law.hash))

                rules = [
                    {
                        "law_id": _law.id,
                        "order_id": _law_order.id,
                        **rule.model_dump(exclude={"scenario_names", "check_points"}),
                    }
                    for rule in law_file.law_rules
                ]
                rule_ids = list(await LawRule.bulk_insert(rules, iter_ids=True))
                rule_count += len(rule_ids)
                await LawRulesScenarios.bulk_insert(
                    [
                        {
                            "rule_id": rule_id,
                            "scenario_id": scenario_map[scenario_name],
                            "order_id": _law_order.id,
                            "law_id": _law.id,
                        }
                        for rule_id, rule in zip(rule_ids, law_file.law_rules)
                        for scenario_name in rule.scenario_names
                        if scenario_name in scenario_name
                    ]
                )
                check_points = []
                idx = 0
                draft_map = {}
                for rule_id, rule in zip(rule_ids, law_file.law_rules):
                    for check_point in rule.check_points:
                        check_points.append(
                            {"order_id": _law_order.id, "law_id": _law.id, "rule_id": rule_id}
                            | check_point.model_dump(exclude={"draft"})
                        )
                        if check_point.draft:
                            draft_map[idx] = {
                                "order_id": _law_order.id,
                                "law_id": _law.id,
                                "rule_id": rule_id,
                            } | check_point.draft.model_dump()
                        idx += 1
                cp_ids = list(await LawCheckPoint.bulk_insert(check_points, iter_ids=True))
                cp_count += len(cp_ids)
                draft_check_points = [_data | {"parent_id": cp_ids[_idx]} for _idx, _data in draft_map.items()]
                await LawCheckPoint.bulk_insert(draft_check_points)
                draft_count += len(draft_check_points)
    if _law_order.meta and "ratio" in _law_order.meta:
        from remarkable.worker.tasks.law_tasks import diff_law_rules_process

        await diff_law_rules_process(_law_order.id)
    print(
        f"synced law rank={rank} id={_law_order.id}, law files={len(law_order.laws)} rules={rule_count} "
        f"check_points={cp_count} draft={draft_count}"
    )

    return None


if __name__ == "__main__":
    # files = (get_config('sync.files') or [])
    asyncio.run(_sync_files([1078]))
