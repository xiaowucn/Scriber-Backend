import asyncio
import datetime
import functools
import gzip
import json
import logging
import os
import shutil
import sys
from collections import OrderedDict
from copy import deepcopy
from pathlib import Path
from typing import Iterator

from invoke import Result, Task
from invoke.exceptions import Failure


class InvokeWrapper(Task):
    def __call__(self, *args, **kwargs):
        from remarkable.common.multiprocess import is_coroutine_func
        from remarkable.common.util import loop_wrapper
        from remarkable.config import get_config
        from remarkable.infrastructure.mattermost import MMPoster

        send_mm_notify = get_config("send_mm_notify") or False
        start_at = datetime.datetime.now()
        msg = f"Invoke task: {self.name}({args[1:]}, {kwargs})"
        try:
            if is_coroutine_func(self.body):
                result = loop_wrapper(self.body)(*args, **kwargs)
            else:
                result = self.body(*args, **kwargs)
        except Exception as exp:
            if send_mm_notify:
                import traceback

                asyncio.run(MMPoster.send(f"{msg} failed: \n```{traceback.format_exc()}```", error=True, force=True))
            raise exp
        if send_mm_notify:
            asyncio.run(
                MMPoster.send(f"{msg} done in {(datetime.datetime.now() - start_at).total_seconds()}s", force=True)
            )
        self.times_called += 1
        return result


def read_ids_from_file(path: str | Path) -> Iterator[int]:
    """
    Read ids from file, one id per line.
    Empty line and line start with # will be ignored.
    """
    path = Path(path) if isinstance(path, str) else path
    if not path.exists():
        raise FileNotFoundError(f"File {path} not found")

    with open(path, "r", encoding="utf-8") as file_obj:
        for line in file_obj:
            line = line.strip()
            if line and line.isdigit():
                yield int(line)


# ============================================================================
# Functions from tool.py
# ============================================================================


def proc_check(proc, msg="process failure"):
    """Check process return code and raise Failure if non-zero."""
    retcode = proc.wait()
    if retcode != 0:
        raise Failure(Result(msg, "", "", retcode, True))


def sql_file_filter(sql, start=None, end=None, mold=None, project=None, tree=None, order_by=None):
    """Filter SQL query with file conditions."""
    file_alias = "f" if "file as f" in sql else "file"

    if "where" not in sql:
        sql += " where true"

    if "join question q" in sql:
        sql += "and q.deleted_utc=0"
    elif "join question" in sql:
        sql += "and question.deleted_utc=0"

    sql += f" and {file_alias}.deleted_utc=0 "

    if start and int(start) > 0:
        sql += f" and {file_alias}.id>=%s" % start
    if end and int(end) > 0:
        sql += f" and {file_alias}.id<=%s" % end
    if mold:
        sql += f" and %s = any({file_alias}.molds)" % mold
    if project:
        sql += f" and {file_alias}.pid in (%s)" % project
    if tree:
        if isinstance(tree, (list, set)):
            tree = ",".join(str(c) for c in tree)
        sql += f" and {file_alias}.tree_id in (%s)" % tree

    if not order_by:
        order_by = f" order by {file_alias}.id"
    sql += order_by

    return sql


def int_or_none(arg):
    """Convert argument to int or return None."""
    if arg is None:
        return None
    return int(arg)


def qid_from_stdin(method):
    """Decorator to read question IDs from stdin and call method for each."""

    @functools.wraps(method)
    async def wrapper(*args, **kwargs):
        qid_list = sys.stdin.read().split()
        for qid in qid_list:
            await method(qid, *args, **kwargs)

    return wrapper


# ============================================================================
# Functions from utils.py
# ============================================================================


def deploy_model_to_special_version(training_cache_dir, mold_id, vid):
    """Deploy model to special version directory."""
    logging.info("copy model to special model_version")
    model_dir = training_cache_dir / str(mold_id) / str(vid)
    ori_model_dir = training_cache_dir / str(mold_id) / "0"
    if model_dir.exists():
        shutil.rmtree(model_dir)
    logging.info(f"copy model {ori_model_dir} to {model_dir}")
    shutil.copytree(ori_model_dir, model_dir)


def model_version_export_path(vid):
    """Get export path for model version."""
    from remarkable.config import project_root

    return os.path.join(project_root, "data", "model", f"model_version_{vid}.json")


# ============================================================================
# Functions from op_codes.py
# ============================================================================


def _rm_file_in_deleted_tree():
    from remarkable.common.util import loop_wrapper
    from remarkable.db import db, peewee_transaction_wrapper
    from remarkable.models.new_file import NewFile

    @loop_wrapper
    @peewee_transaction_wrapper
    async def _inner():
        sql = """
        select f.id from file f
        join file_tree t on f.tree_id=t.id
        where t.deleted_utc>0 and f.deleted_utc=0;
        """
        file_ids = await db.raw_sql(sql)

        for (file_id,) in file_ids:
            file = await NewFile.find_by_id(file_id)
            print(f"delete file {file.id}")
            await file.soft_delete()

    return _inner()


def _mini_pdfinsight(reader):
    def _revise_table(element):
        tbl = deepcopy(element)
        tbl.pop("grid", None)
        for cell in tbl.get("cells", {}).values():
            cell.pop("styles", None)
            cell.pop("chars", None)
            cell.pop("styles_diff", None)
        return tbl

    def _revise_para(element):
        para = deepcopy(element)
        para.pop("outline_score", None)
        para.pop("outline_parsed_by", None)
        para.pop("chars", None)
        return para

    mini_pdfinsight = {}
    elements = []
    for element in reader.paragraphs:
        elements.append(_revise_para(element))
    for element in reader.page_header:
        elements.append(_revise_para(element))
    for element in reader.page_footer:
        elements.append(_revise_para(element))
    for element in reader.tables:
        elements.append(_revise_table(element))

    mini_pdfinsight["elements"] = sorted(elements, key=lambda x: x["index"])
    mini_pdfinsight["syllabuses"] = sorted(reader.syllabuses, key=lambda x: x["index"])
    return mini_pdfinsight


def _reconstruct_answer(answer, pdfinsight_reader):
    from remarkable.answer.reader import load_scriber_answer
    from remarkable.common.util import box_to_outline
    from remarkable.plugins.sse.sse_answer_formatter import AnswerItem

    def convert_dict_to_list(data):
        """
        {
            '0':
                {
                    'col1': 'abc',
                    'col2': {'0': 'a', '1': 'b'}
                }
        }
        ==>
        [
            {
                'col1': 'abc',
                'col2': ['a', 'b']
            }
        ]
        :param data:
        :return:
        """
        if not (isinstance(data, dict) and (0 in data or "0" in data)):
            return data
        res = []
        keys = sorted(data.keys(), key=int)
        for key in keys:
            val = data[key]
            if isinstance(val, dict):
                group_item = OrderedDict()
                for _key in val:
                    group_item[_key] = convert_dict_to_list(val[_key])
                res.append(group_item)
            else:
                res.append(val)
        return res

    def fill_element_info(answer, reader):
        for item in answer.get("userAnswer", {}).get("items", []):
            is_big_table = "表格" in item["key"]
            for label_data in item.get("data", []):
                for box_info in label_data.get("boxes", []):
                    page = box_info["page"]
                    box = box_info["box"]
                    outline = box_to_outline(box)

                    box_info["elements"] = []
                    elements = reader.find_elements_by_outline(page, outline)
                    if elements is None:
                        logging.error("can't find elements by page %s, outline %s", page, outline)
                        continue

                    for etype, element in elements:
                        element_info = {"index": element["index"], "type": etype}
                        if not is_big_table:
                            element_info.update(reader.detail_locality_in_element(element, page, outline))
                        # 是否大表格标法，段落也可能在框大表格的时候框进去，表格也可能被错误地识别为段落
                        element_info["is_big_table"] = is_big_table

                        box_info["elements"].append(element_info)

        return answer

    if not answer:
        return None

    result = OrderedDict()
    answer = fill_element_info(answer, pdfinsight_reader)
    answer_tree = load_scriber_answer(answer)
    if answer_tree:
        root_key = list(answer_tree.keys())[0]
        root_node = answer_tree[root_key]
        for key, val in root_node.items():
            if isinstance(val, dict):
                result[key] = convert_dict_to_list(val)
            elif isinstance(val, AnswerItem):
                result[key] = [{key: val}]
            else:
                result[key] = val

        return {root_key: result}
    return None


def _reconstruct_crude_answer(answer, pdfinsight_reader, schema=None):
    def fill_crude_element_info(crude_answer, reader):
        for items in crude_answer.values():
            for item in items:
                page = item["page"]
                outline = item["outline"]
                item["elements"] = []
                elements = reader.find_elements_by_outline(page, outline)
                if elements is None:
                    logging.error("can't find elements by page %s, outline %s", page, outline)
                    continue
                for etype, element in elements:
                    element_info = {"index": element["index"], "type": etype}
                    if etype == "TABLE":
                        element_info["is_big_table"] = True  # table in crude_answer is all big_table
                    else:
                        element_info.update(reader.detail_locality_in_element(element, page, outline))
                    item["elements"].append(element_info)
        return crude_answer

    def fill_tree_node(keys, data, res):
        attr = keys.pop(0)
        if attr not in res:
            print(f"{attr} not in schema")
            res[attr] = {}
        if len(keys) == 1:
            res[attr].update({keys[0]: data})
        else:
            fill_tree_node(keys, data, res[attr])

    def load_crude_answer_tree(schema, answer):
        schema_dict = {sch["name"]: sch for sch in schema["schemas"]}
        root_name = schema["schemas"][0]["name"]

        res = OrderedDict()
        for attr in schema_dict[root_name]["orders"]:
            res[attr] = {}

        for key, answers in answer.items():
            key_list = key.rsplit("-", maxsplit=1)
            if len(key_list) == 1:
                res[key_list[0]] = answers
            else:
                fill_tree_node(key_list, answers, res)

        return {root_name: res}

    if not answer:
        return None

    answer = fill_crude_element_info(answer, pdfinsight_reader)
    answer_tree = load_crude_answer_tree(schema, answer)

    return answer_tree


def _dump_one_file(args):
    """fid: int, filename: str, file: File, label_answer: Question, ex_answers: List[SpecialAnswer]"""
    from remarkable.common.storage import localstorage
    from remarkable.pdfinsight.reader import PdfinsightReader
    from remarkable.plugins.sse.sse_answer_formatter import AnswerItem

    fid, filename, file, question, ex_answers, save_path = args
    logging.info("start dump answer for file %s", fid)
    filename = filename.replace("/", "-")
    path = os.path.join(save_path, f"{fid}_{filename}.json.gz")
    if os.path.exists(path):
        os.remove(path)
    try:
        # file = await NewFile.find_by_id(fid)
        reader = PdfinsightReader(localstorage.mount(file.pdfinsight_path()))

        # label_answer = await NewQuestion.find_by_fid(fid)
        label_schema = question.answer["schema"]

        label_answer_tree = _reconstruct_answer(question.answer, reader)
        crude_answer_tree = _reconstruct_crude_answer(question.crude_answer, reader, schema=label_schema)

        # ex_answers = await NewSpecialAnswer.get_answers(qid, NewSpecialAnswer.ANSWER_TYPE_EXPORT, top=1)
        if ex_answers:
            ex_answer = ex_answers[0]
            ex_schema = ex_answer.data["schema"]
            ex_answer_tree = _reconstruct_answer(ex_answer.data, reader)
        else:
            ex_schema = None
            ex_answer_tree = None

        mini_pdfinsight = _mini_pdfinsight(reader)  # 放到最后，以保留reconstruct_answer时，对table的处理
    except Exception:
        logging.exception("error in dump file %s dataset for training", fid)
    else:
        data = {
            "doc": mini_pdfinsight,
            "schema": label_schema,
            "answer": label_answer_tree,
            "crude_answer": crude_answer_tree,
            "export_schema": ex_schema,
            "export_answer": ex_answer_tree,
        }
        with gzip.open(path, "wt") as dumpfp:
            json.dump(data, dumpfp, ensure_ascii=False, indent=4, default=AnswerItem.simple_text)

        logging.info("dump answer for file %s finish, save to: %s", fid, path)
