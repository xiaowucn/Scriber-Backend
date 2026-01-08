"""
导入导出命令
"""

import gzip
import json
import logging
import os
import pickle
import re
import shutil
import tarfile
import tempfile
import traceback
from collections import defaultdict
from functools import partial
from pathlib import Path

import openpyxl
from invoke import Context, task
from openpyxl.workbook import Workbook
from pdfparser.pdftools.pdf_doc import PDFDoc
from peewee import JOIN
from playhouse.postgres_ext import ServerSide

from remarkable.answer.node import AnswerItem
from remarkable.common.util import loop_wrapper
from remarkable.config import get_config
from remarkable.db import db, peewee_transaction_wrapper, pw_db
from remarkable.devtools import InvokeWrapper, read_ids_from_file, sql_file_filter
from remarkable.schema.special_answer import MultiBox

logger = logging.getLogger(__name__)


@task
def answers_with_format(ctx, mold, start, end, project=None, workers=0, path="data/export_answers"):
    """
    导出树形结构的标注答案(mold, start, end, project=None, path="data/export_answers", workers=0)
    """
    from remarkable.optools.export_answers_with_format import export_answer

    pids = [int(c) for c in project.split(",")] if project else None
    loop_wrapper(export_answer)(int(mold), int(start), int(end), pids=pids, workers=workers, dump_path=path)


@task(iterable=["orphan"], help={"orphan": "导出指定(多个)文件的缓存, 此参数与-s, -e互斥"})
def export_special_answer(ctx, start=0, end=0, mold=0, orphan=None, path=None, workers=0, need_insight=True):
    """导出待缓存的答案, 参数：(start=-1, end=-1, orphan=None, path=None, workers=0)"""
    _export_special_answer(int(start), int(end), int(mold), orphan, path, workers, need_insight)


@loop_wrapper
async def _export_special_answer(start, end, mold, orphan, path, workers, need_insight):
    from remarkable.models.new_file import NewFile

    data_dir = get_config("web.data_dir")
    sql = """
    select file.id, question.id from file
    inner join question on file.id = question.fid
    where tree_id != 0
    and pid !=0
    """
    if orphan:
        sql += " and file.id in ({})".format(", ".join(orphan))
    else:
        sql = sql_file_filter(sql, start=start, end=end)

    sql = sql_file_filter(sql, mold=mold)

    sql += " order by file.id"
    rows = await db.raw_sql(sql)
    tmp_path = os.path.join(data_dir, "sse_tmp")
    if os.path.exists(tmp_path):
        shutil.rmtree(tmp_path)
    os.mkdir(tmp_path)
    saved_path = path if path else data_dir
    for fid, qid in rows:
        try:
            _file = await NewFile.find_by_id(fid)
            if _file and _file.molds:
                # tasks.append((_file, qid, saved_path, tmp_path))
                await save_answer(_file, qid, saved_path, tmp_path)
        except Exception as ex:
            traceback.print_exc()
            logging.error("error in export_special_answer for file %s, %s", fid, ex)
    # run_in_multiprocess(save_answer, tasks, workers=workers)

    insight_tar_path = os.path.join(path, "all_pdfinsight.tar.gz")
    if need_insight:
        with tarfile.open(insight_tar_path, "w:gz") as tar:
            tar.add(tmp_path, arcname=os.path.basename(data_dir))
    shutil.rmtree(tmp_path)


@peewee_transaction_wrapper
async def save_answer(file, qid, saved_path, tmp_path):
    from remarkable.answer.common import fix_answer_outline
    from remarkable.common.storage import localstorage
    from remarkable.pw_models.model import NewSpecialAnswer

    data_dir = get_config("web.data_dir")
    ex_answers = await NewSpecialAnswer.get_answers(qid, NewSpecialAnswer.ANSWER_TYPE_EXPORT, top=1)
    if not ex_answers:
        return
    if file.pdfinsight_path():
        new_pdfinsight_path = os.path.join(tmp_path, file.pdfinsight[:2])
        if not os.path.exists(new_pdfinsight_path):
            os.mkdir(new_pdfinsight_path)
        shutil.copy(os.path.join(data_dir, file.pdfinsight_path()), new_pdfinsight_path)
    logging.info("export file %s, qid %s", file.id, qid)
    pdf_path = localstorage.mount(file.pdf_path())
    answer_data = fix_answer_outline(pdf_path, ex_answers[0].data)
    saved_answer = {"name": file.name, "hash": file.hash, "answer": answer_data, "pdfinsight": file.pdfinsight}
    special_answer_path = os.path.join(saved_path, f"{file.id}_{qid}_special_answers.pkl")
    with gzip.open(special_answer_path, "wb") as _fp:
        pickle.dump(saved_answer, _fp, protocol=-1)


@task
def import_special_answer(ctx, mold, path=None, workers=0, need_insight=False):
    """导入缓存答案，参数：(mold, path=None, works=None)"""
    _import_answers(int(mold), path, workers, need_insight)


@loop_wrapper
async def _import_answers(mold, path, workers, need_insight):
    data_dir = get_config("web.data_dir")

    async def get_old_sequence_id(length_of_answers):
        seq_sql = """select max(id) as max_cache_id from file where id < 10000"""
        _max_cache_id = await db.raw_sql(seq_sql, "scalar")
        if not _max_cache_id:
            return True, 0

        get_seq_id_sql = """select last_value from file_id_seq;"""
        _last_seq_id = await db.raw_sql(get_seq_id_sql, "scalar")
        logging.info("last_seq_id is %s", _last_seq_id)
        _max_cache_id = _max_cache_id if _max_cache_id else 0
        all_file_sum = _max_cache_id + length_of_answers
        if all_file_sum > 10000:
            return False, _last_seq_id, _max_cache_id

        return True, _last_seq_id, _max_cache_id

    path = path if path else data_dir
    special_answers = [name for name in os.listdir(path) if "special_answers" in name]

    # 获取mold_name
    sql = "select name from mold where id = %(mold_id)s;"
    mold_name = await db.raw_sql(sql, "scalar", mold_id=mold)
    if not mold_name:
        logging.info("please check mold...")
        return

    # 获取是否将数据导入到10000以下以及导入前的seq_id,
    flag, last_seq_id, max_cache_id = await get_old_sequence_id(len(special_answers))

    # 导入答案
    logging.info("import answer...")
    # tasks = []
    # workers = int(workers) if workers else int(cpu_count() / 2)
    for file_name, fid in zip(special_answers, range(max_cache_id + 1, max_cache_id + len(special_answers) + 1)):
        await _run_import_answer(os.path.join(path, file_name), mold_name, mold, flag, fid)
    # run_in_multiprocess(_run_import_answer, tasks, workers=workers)

    # 修改导入后的seq_id
    if flag:
        last_seq_id = last_seq_id if last_seq_id > 10000 else 10000
        seq_id_sql = """SELECT setval('file_id_seq',  %(last_seq_id)s);"""
        status_rsp = await db.raw_sql(seq_id_sql, "status", **{"last_seq_id": last_seq_id})
        if db.get_count_in_status_rsp(status_rsp) == 0:
            logging.error("update seq_id failed...")
            return

        logging.info("update seq_id to %s success...", last_seq_id)

    # 导入pdfinsight文件
    if need_insight:
        logging.info("import pdfinsight file...")
        with tarfile.open(os.path.join(path, "all_pdfinsight.tar.gz"), mode="r:gz") as tar:
            names = tar.getnames()
            for name in names:
                if name:
                    dst_path = os.path.join(data_dir)
                    tar.extract(name, path=dst_path)
        logging.info("load pdfinsight success...")


@peewee_transaction_wrapper
async def _run_import_answer(file_path, mold_name, mold, flag, fid):
    from remarkable.models.new_file import NewFile
    from remarkable.pw_models.question import NewQuestion

    with gzip.open(file_path, "rb") as _fp:
        answer = pickle.load(_fp)
    question_answer = answer["answer"]
    question_answer["schema"]["schemas"][0]["name"] = mold_name
    for item in question_answer["userAnswer"]["items"]:
        ori_key = item["key"]
        if item.get("marker"):
            item.pop("marker")
        key_list = json.loads(ori_key)
        schema_key = key_list[0]
        schema_key_list = schema_key.split(":")
        schema_key_list[0] = mold_name
        key_list[0] = ":".join(schema_key_list)
        item["key"] = json.dumps(key_list, ensure_ascii=False)
    fname, fhash, answer, pdfinsight = answer["name"], answer["hash"], answer["answer"], answer["pdfinsight"]

    # 删除旧缓存
    delete_id = 0
    delete_qid = 0
    delete_file_sql = """delete from file where hash = %(fhash)s and tree_id = 0 and pid = 0 returning id, qid;"""
    delete_data = await db.raw_sql(delete_file_sql, "first", **{"fhash": fhash})
    if delete_data:
        delete_id, delete_qid = delete_data

    if delete_qid:
        await db.raw_sql("delete from question where id = %(id)s;", **{"id": delete_qid})
    fid = delete_id if delete_id else fid
    qid = delete_qid if delete_qid else None

    insert_file_sql = """insert into file(id, tree_id, pid, name, hash, pdf, mold, pdfinsight, qid)
        values(%(fid)s, 0, 0, %(name)s, %(hash)s, %(pdf)s, %(mold)s, %(pdfinsight)s, %(qid)s)
        returning id;
        """
    fid = await db.raw_sql(
        insert_file_sql,
        "scalar",
        **{
            "fid": fid,
            "name": fname,
            "hash": fhash,
            "pdf": fhash,
            "mold": mold,
            "pdfinsight": pdfinsight,
            "qid": qid,
        },
    )
    if delete_qid:
        # 重利用删除的question_id
        insert_question_sql = """insert into question(id, data, checksum, fid, mold, answer)
                        values(%(id)s, %(data)s, %(checksum)s, %(fid)s, %(mold)s, %(answer)s)
                        returning id;
                        """
        await db.raw_sql(
            insert_question_sql,
            **{
                "id": delete_qid,
                "data": json.dumps({"file_id": fid}),
                "checksum": NewQuestion.gen_checksum(fid, mold),
                "fid": fid,
                "mold": mold,
                "answer": json.dumps(answer),
            },
        )
    else:
        insert_question_sql = """insert into question(data, checksum, fid, mold, answer)
            values(%(data)s, %(checksum)s, %(fid)s, %(mold)s, %(answer)s)
            returning id;
            """
        qid = await db.raw_sql(
            insert_question_sql,
            "scalar",
            **{
                "data": json.dumps({"file_id": fid}),
                "checksum": NewQuestion.gen_checksum(fid, mold),
                "fid": fid,
                "mold": mold,
                "answer": json.dumps(answer),
            },
        )

    # 关联file <-> question
    await NewFile.update_by_pk(fid, qid=delete_qid or qid)
    logging.info("import file %s, qid %s", fid, qid)


@task
def dump_dataset_for_training(
    ctx, mold, start=-1, end=-1, project=None, tree=None, save_path="data_set_for_training", workers=0
):
    """导出 初步定位答案 & 标注答案 & 导出答案, 相关schema, 文档元素块信息"""
    from remarkable.common.multiprocess import run_in_multiprocess
    from remarkable.devtools import _dump_one_file
    from remarkable.models.new_file import NewFile
    from remarkable.pw_models.model import NewSpecialAnswer
    from remarkable.pw_models.question import NewQuestion

    @loop_wrapper
    @peewee_transaction_wrapper
    async def _run():
        if not os.path.exists(save_path):
            os.makedirs(save_path)
        questions = await NewQuestion.list_by_range(mold=mold, start=start, end=end, project=project, tree_l=tree)
        tasks = []
        batch_size = workers * 2 if workers else 12
        for question in questions:
            file = await NewFile.find_by_id(question.fid)
            ex_answers = await NewSpecialAnswer.get_answers(question.id, NewSpecialAnswer.ANSWER_TYPE_EXPORT, top=1)
            tasks.append((file.id, file.name, file, question, ex_answers, save_path))
            if len(tasks) >= batch_size:
                run_in_multiprocess(_dump_one_file, tasks, workers=workers)
                tasks.clear()
        if tasks:
            run_in_multiprocess(_dump_one_file, tasks, workers=workers)

    _run()


@task(klass=InvokeWrapper)
async def stat_octopus(ctx):
    from remarkable.service.statistics import stat_octopus_parsing_time

    await stat_octopus_parsing_time()


@task(klass=InvokeWrapper)
async def field_answer(ctx, field, mold, start=None, end=None, project=None, tree=None):
    """
    导出指定字段的答案
    """
    from remarkable.answer.reader import AnswerReader
    from remarkable.common.util import dump_data_to_worksheet
    from remarkable.pw_models.question import NewQuestion

    questions = await NewQuestion.list_by_range(mold=mold, start=start, end=end, project=project, tree_l=tree)
    data = []
    for question in questions:
        logging.info(question.fid)
        try:
            answer_reader = AnswerReader(question.answer)
            nodes = answer_reader.find_nodes([field])
            for node in nodes:
                data.append([question.fid, node.data.plain_text])
        except Exception as e:
            logging.exception(e)

    workbook = openpyxl.Workbook()
    headers = ["fid", field]
    dump_data_to_worksheet(workbook, headers, data)
    dump_filename = f"{field}.xlsx"
    workbook.save(dump_filename)


def csc_export_simple_json_v2(enum_types: set[str], pdf_doc: PDFDoc, item: AnswerItem):
    """
    中信建投报价标注数据导出, 增加position字段
    return: {
        "choices": [
            "ch1",
            "ch2",
            ...
        ],
        "text": "text",
        "potions:" 0
    }
    """
    from remarkable.schema.special_answer import MultiBox

    ret = {"text": None}
    if not item or not (item.data or item.value or item.text):
        return ret

    text = item.simple_text(enum=False)
    if text and isinstance(text, list):
        text = "\n".join(text)
        ret = {"text": text or None}
    if data := item.get("data"):
        try:
            ret["position"] = get_position(pdf_doc, MultiBox(**data[0]["boxes"][0]))
        except Exception:
            logger.warning("get position error %s", item)
    if item.schema.get("data", {}).get("type") in enum_types:
        ret["choices"] = []

    if "choices" in ret and item.value:
        if isinstance(item.value, list):
            ret["choices"].extend(item.value)
        elif isinstance(item.value, str):
            ret["choices"].append(item.value)
        else:
            raise TypeError(f"Unexpected type of value: {item.value}")
    return ret


def find_element_by_outline_with_offset(page, outline):
    def inter_x(*outlines):
        overlap_length = min(outlines[0][2], outlines[1][2]) - max(outlines[0][0], outlines[1][0])
        return overlap_length if overlap_length > 0 else 0

    def inter_y(*outlines):
        overlap_length = min(outlines[0][3], outlines[1][3]) - max(outlines[0][1], outlines[1][1])
        return overlap_length if overlap_length > 0 else 0

    def area(*outlines):
        return (outlines[1][3] - outlines[1][1]) * (outlines[1][2] - outlines[1][0])

    def overlap_percent(*outlines):
        try:
            return inter_y(*outlines) * inter_x(*outlines) / area(*outlines)
        except ZeroDivisionError:
            return 0

    offset = 0
    max_overlap = (0, None)
    for elt in page["texts"]:
        overlap = overlap_percent(outline, elt["box"])
        # logging.debug("%.2f, %s", overlap, elt['outline'])
        if overlap == 0:
            offset += len(elt["chars"]) + len(elt["white_chars"])
            continue
        if max_overlap[1] is None or max_overlap[0] < overlap:
            max_overlap = (overlap, elt)
            char_max_overlap = (0, None)
            char_offset = 0
            for char in elt["chars"]:
                char_overlap = overlap_percent(outline, char["box"])
                if char_overlap == 0:
                    char_offset += 1
                    continue
                if char_max_overlap[1] is None or char_max_overlap[0] < char_overlap:
                    offset += char_offset + len(
                        [white_char for white_char in elt["white_chars"] if white_char["box"][0] < char["box"][0]]
                    )
                    break
            break
    return (offset, max_overlap[1]) if max_overlap[1] else (0, None)


def is_new_line(text: dict, cur_line):
    if not cur_line:
        return False
    if abs(cur_line[-1]["box"][1] - text["box"][1]) > 20:
        return True
    return False


def group_texts_by_real_line(path: str):
    """
    将pdf中text 按照txt的行分组
    """
    pdf_doc = PDFDoc(path)
    line_contents = []
    for page_idx in range(len(pdf_doc.pages)):
        page = pdf_doc.pages[page_idx]
        lines = defaultdict(list)
        line_idx = 0
        for text in page["texts"]:
            if is_new_line(text, lines[line_idx]):
                line_idx += 1
            text["line_idx"] = line_idx
            lines[line_idx].append(text)
        page["lines"] = lines
        for line_idx in range(len(lines)):
            line_content = "".join(text["text"] for text in lines[line_idx])
            line_contents.append(line_content)
    pdf_doc.txt_content = "\n".join(line_contents)
    return pdf_doc


def get_position(pdf_doc, box_data: MultiBox):
    offset, dst_elt = find_element_by_outline_with_offset(pdf_doc.pages[box_data.page], box_data.box.outline)
    if not dst_elt:
        raise ValueError("No element matched")
    offset = offset + dst_elt["line_idx"]
    for page_idx in range(box_data.page):
        page = pdf_doc.pages[page_idx]
        offset += sum(len(text["chars"]) + len(text["white_chars"]) for text in page["texts"]) + len(page["lines"])
    return offset


@task(iterable=["pids"])
def user_marked_answer(ctx, mid: int, pids: list[int], exclude_file: str | None = None):
    """
    用户标注数据导出
    https://gitpd.paodingai.com/cheftin/docs_scriber/-/issues/8269

    目录结构：
    projectId_projectName
      fileId_fileName_user1.json
      fileId_fileName_user2.json
    """
    from remarkable.common.constants import ADMIN_ID, AnswerStatus
    from remarkable.common.storage import localstorage
    from remarkable.config import target_path
    from remarkable.converter import SimpleJSONConverter
    from remarkable.models.new_file import NewFile
    from remarkable.models.new_user import NewAdminUser
    from remarkable.optools.export_csc_diff_res import group_texts_by_real_line
    from remarkable.pw_models.model import NewAnswer, NewFileProject
    from remarkable.pw_models.question import NewQuestion

    cond = (NewQuestion.mold == int(mid)) & (NewFile.pid.in_([int(p) for p in pids]))
    if exclude_file:
        cond &= NewFile.id.not_in(list(read_ids_from_file(exclude_file)))
    cond &= (NewAnswer.uid != ADMIN_ID) & (NewAnswer.status == AnswerStatus.VALID)
    stmt = (
        NewQuestion.select(
            NewFile.id.alias("file_id"),
            NewFile.name.alias("file_name"),
            NewFile.pdf.alias("pdf_hash"),
            NewFileProject.id.alias("project_id"),
            NewFileProject.name.alias("project_name"),
            NewAnswer.data.alias("answer_data"),
            NewAdminUser.name.alias("user_name"),
        )
        .join(NewFile, on=(NewQuestion.fid == NewFile.id))
        .join(NewFileProject, on=(NewFile.pid == NewFileProject.id))
        .join(NewAnswer, on=(NewAnswer.qid == NewQuestion.id))
        .join(
            NewAdminUser,
            join_type=JOIN.LEFT_OUTER,
            on=(NewAnswer.uid == NewAdminUser.id),
            include_deleted=True,
        )
        .where(cond)
        .order_by(NewFileProject.id, NewFile.id, NewAnswer.uid)
        .namedtuples()
    )
    with pw_db.allow_sync():
        for row in ServerSide(stmt):
            logger.info(row.file_id)
            if not row.answer_data:
                continue
            user_name = row.user_name if row.user_name else "deleted_user"
            pdf_path = localstorage.mount(os.path.join(row.pdf_hash[:2], row.pdf_hash[2:]))
            pdf_doc = group_texts_by_real_line(pdf_path)
            enum_types = {s["label"] for s in row.answer_data["schema"]["schema_types"]}
            if not row.answer_data["userAnswer"]["items"]:
                logger.warning(f"file {row.file_id} has no answer")
                res = {}
            else:
                res = SimpleJSONConverter(row.answer_data).convert(
                    item_handler=partial(csc_export_simple_json_v2, enum_types, pdf_doc)
                )
            work_dir = Path(target_path(f"data/user_marked_answer/{row.project_id}_{row.project_name}"))
            work_dir.mkdir(parents=True, exist_ok=True)
            file_path = work_dir / f"{row.file_id}_{os.path.splitext(row.file_name)[0]}_{user_name}.json"
            with open(file_path, "w") as file_obj:
                json.dump(res, file_obj, ensure_ascii=False)
            logger.info(f"end export project {row.project_id}")
    logger.info("end export")


@task(klass=InvokeWrapper, iterable=["pids"])
async def csc_broker_quote_export(ctx, mid: int, pids: list[int], exclude_file: str | None = None):
    """
    中信建投报价标注数据导出
    """
    from remarkable.common.constants import AnswerStatus
    from remarkable.common.storage import localstorage
    from remarkable.config import target_path
    from remarkable.converter import SimpleJSONConverter
    from remarkable.models.new_file import NewFile
    from remarkable.optools.export_csc_diff_res import group_texts_by_real_line
    from remarkable.pw_models.model import NewAnswer, NewFileProject
    from remarkable.pw_models.question import NewQuestion

    cond = NewQuestion.mold == int(mid)
    if exclude_file:
        cond &= NewFile.id.not_in(list(read_ids_from_file(exclude_file)))

    for pid in map(int, pids):
        logger.info(f"start export project {pid}")
        file_project = await NewFileProject.find_by_id(pid)
        dump_path = Path(target_path(f"data/csc_output/{file_project.name}"))
        if dump_path.exists():
            logger.warning(f"dump path {dump_path} exists, skip")
            continue
        else:
            dump_path.mkdir(parents=True)

        cond &= NewFile.pid == pid
        questions = await pw_db.execute(
            NewQuestion.select(NewQuestion.id, NewFile)
            .join(NewFile, on=(NewQuestion.fid == NewFile.id), attr="file")
            .where(cond)
        )
        for question in questions:
            logger.info(question.file.id)
            newest_answer_data = await pw_db.scalar(
                NewAnswer.select(NewAnswer.data)
                .where(
                    NewAnswer.qid == question.id,
                    NewAnswer.status == AnswerStatus.VALID,
                )
                .order_by(NewAnswer.updated_utc.desc())
            )
            if not newest_answer_data:
                continue
            pdf_path = localstorage.mount(question.file.pdf_path())
            pdf_doc = group_texts_by_real_line(pdf_path)
            new_file_name = re.sub(r"\.txt$", "", re.sub(":", "_", question.file.name))
            enum_types = {s["label"] for s in newest_answer_data["schema"]["schema_types"]}
            if not newest_answer_data["userAnswer"]["items"]:
                logger.info(f"file {question.file.id} has no answer")
                res = {}
            else:
                res = SimpleJSONConverter(newest_answer_data).convert(
                    item_handler=partial(csc_export_simple_json_v2, enum_types, pdf_doc)
                )
            file_path = dump_path / rf"{new_file_name}_{question.file.id}.txt"
            with open(dump_path / rf"{new_file_name}_{question.file.id}.json", "w") as file_obj:
                json.dump(res, file_obj, ensure_ascii=False)
            localstorage.write_file(str(file_path), pdf_doc.txt_content.encode("utf-8"))
        logger.info(f"end export project {pid}")


CSC_CONTENT_PATTERN = re.compile(r"估值|中债|中证|行权|到期|票面|行[/|]到")


@task(klass=InvokeWrapper)
async def stat_csc_broker_quote_content(ctx, mold: int, project: int = None):
    """
    中信建投报价文本内容统计
    """
    from remarkable.common.storage import localstorage
    from remarkable.models.new_file import NewFile
    from remarkable.optools.export_csc_diff_res import gen_public_url, gen_url
    from remarkable.pw_models.model import NewFileProject
    from remarkable.pw_models.question import NewQuestion

    cond = NewQuestion.mold == mold
    if project:
        cond &= NewFile.pid == project
    questions = await pw_db.execute(
        NewQuestion.select(NewQuestion.id, NewFile, NewFileProject)
        .join(NewFile, on=(NewQuestion.fid == NewFile.id), attr="file")
        .join(NewFileProject, on=(NewFile.pid == NewFileProject.id), attr="project")
        .where(cond)
        .order_by(NewFile.id)
    )
    workbook = Workbook()
    sheet = workbook.active
    sheet.append(["fileid", "pid", "pname", "url", "public_url", "keyword"])
    for question in questions:
        url = gen_url(question.file.id, question.file.tree_id, question.id)
        public_url = gen_public_url(question.file.id, question.file.tree_id, question.id)
        txt_content = localstorage.read_file(question.file.path()).decode("utf-8")
        if matched := CSC_CONTENT_PATTERN.search(txt_content):
            sheet.append(
                [question.file.id, question.file.pid, question.file.project.name, url, public_url, matched.group()]
            )
    with tempfile.NamedTemporaryFile(prefix="stat_csc_txt_content_", suffix=".xlsx", delete=False) as tmp_fp:
        excel_path = tmp_fp.name
        workbook.save(excel_path)


if __name__ == "__main__":
    ctx = Context()
    user_marked_answer(ctx, mid=2, pids=[2, 3, 4, 5, 7])
    # stat_csc_broker_quote_content(ctx, mold=2)
