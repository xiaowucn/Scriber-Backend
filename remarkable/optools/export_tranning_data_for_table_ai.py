import json
import logging
from pathlib import Path

from remarkable.answer.node import AnswerNode
from remarkable.answer.reader import AnswerReader
from remarkable.common.multiprocess import run_in_multiprocess
from remarkable.common.schema import Schema
from remarkable.common.storage import localstorage
from remarkable.common.util import loop_wrapper
from remarkable.models.new_file import NewFile

# from remarkable.common.constants import QuestionStatus
from remarkable.pdfinsight.reader import PdfinsightReader
from remarkable.predictor.mold_schema import MoldSchema
from remarkable.predictor.predictor import get_element_candidates
from remarkable.pw_models.model import NewAnswer, NewMold, NewSpecialAnswer
from remarkable.pw_models.question import NewQuestion

dump_path = Path("data", "table_ai_data")


async def export_answer(mid: int, start: int, end: int, pids: list[int] = None, workers=4, answer_from="user"):
    dump_path.mkdir(exist_ok=True)
    # TODO: iter with a sql
    mold = await NewMold.find_by_id(mid)
    if not mold:
        raise Exception(f"can't find mold {mid}")
    schema = Schema(mold.data)
    tasks = []
    for fid in range(start, end + 1):
        file = await NewFile.find_by_id(fid)
        question = await NewQuestion.find_by_fid_mid(fid, mid)
        if not file or not question:
            logging.debug(f"can't find file or question, pass fid: {fid}")
            continue
        if pids and file.pid not in pids:
            logging.debug(f"project not match, pass fid: {fid}")
            continue
        answer = await get_annotation_answer(question, answer_from)
        if not answer:
            logging.debug(f"have no annotation answer, pass fid: {fid}")
            continue
        if question.no_crude_answer:
            logging.warning(f"have no crude_answer, pass fid: {fid}")
            continue
        tasks.append(
            (
                fid,
                localstorage.mount(file.pdfinsight_path()),
                schema,
                answer,
                question.crude_answer,
                dump_path / f"{fid}.json",
            )
        )
        if len(tasks) >= workers * 2:
            run_in_multiprocess(dump_training_data, tasks, workers=workers)
            tasks.clear()
    if tasks:
        run_in_multiprocess(dump_training_data, tasks, workers=workers)
        tasks.clear()


async def get_annotation_answer(question, answer_from):
    answer_data = None
    if answer_from == "user":
        # 从用户答案中取
        answer = await NewAnswer.find_standard(question.id)
        if answer:
            answer_data = answer.data
    elif answer_from == "merge":
        # 从合并答案 question.answer 中取
        answer_data = question.answer
    else:
        # 从 special answer 中取指定类型
        special_answers = await NewSpecialAnswer.get_answers(question.id, answer_from, top=1)
        if special_answers:
            answer_data = special_answers[0].data

    return answer_data


def dump_training_data(args):
    fid, pdfinsight_path, schema, answer_data, crude_answer, save_path = args
    logging.info(f"exporting file {fid}")
    pdfinsight = PdfinsightReader(pdfinsight_path)
    data = build_table_ai_training_data(schema, answer_data, crude_answer, pdfinsight)
    with open(save_path, "w") as dfp:
        json.dump(data, dfp)
    logging.info(f"export answer for file {fid} success")


def build_table_ai_training_data(schema: Schema, answer: dict, crude_answer: dict, pdfinsight: PdfinsightReader):
    """导出 table ai 模型训练所需的数据格式
    {
        "answer": {
            "财务指标表_非经常性损益_数值": {
                table_index1: [
                    ("财务指标表", "1", "1_1"),
                    ("财务指标表", "2", "2_1"),
                    ("财务指标表", "3", "3_1"),
                    ],  // 正例
                table_index2: [],  // 负例
                ...
            },
            "另一个指标...": {},
        },
        "groups": {
            "财务指标表": [
                "财务指标表_报告期",
                "财务指标表_非经常性损益_数值"
                "财务指标表_非经常性损益_单位",
                ...
            ]
        },
        "tables": {
            table_index: {
                "syll": ["一级目录", "二级目录"]，
                "cells": {
                    cell_idx: text,
                    ...
                }
            }
        }
    }
    """
    answers = {}
    tables = {}
    groups = {}

    mold_schema = MoldSchema(schema.mold)
    answer_reader = AnswerReader(answer)
    for column_path in schema.iter_schema_attr():
        column_path = column_path[1:]  # 去掉 schema 名称
        column_schema = mold_schema.find_schema_by_path(column_path)
        if column_schema.parent.is_amount:
            group_end = -2
        else:
            group_end = -1
        group_name, column_name = "_".join(column_path[0:group_end]), "_".join(column_path)
        groups.setdefault(group_name, []).append(column_name)
        column_answers = {}
        answers[column_name] = column_answers

        # 添加正例
        answer_nodes = answer_reader.find_nodes(column_path)
        for node in answer_nodes:
            for table_idx, answer_cells in find_answer_table(pdfinsight, node, group_end=group_end).items():
                column_answers[table_idx] = list(set(column_answers.get(table_idx, []) + answer_cells))

        # 添加负例
        crude_answer_items = get_column_crude_answers(crude_answer, column_path)
        for item in crude_answer_items:
            if item["element_index"] in column_answers:
                continue
            column_answers[item["element_index"]] = []

        # 表格信息
        for idx in column_answers:
            if idx in tables:
                continue
            tables[idx] = format_table(pdfinsight, idx)

    return {
        "answer": answers,
        "tables": tables,
        "groups": groups,
    }


def get_column_crude_answers(crude_answer, aim_path):
    # NOTE: 暂针对深交所，取整个表格所有字段的并排重
    #       以后应该是根据 predictor 配置获取
    candidates = get_element_candidates(
        crude_answer,
        aim_path[:1],  # 暂针对深交所
        limit=10,
    )
    return [c for c in candidates if c.get("element_type") == "TABLE"]


def find_answer_table(pdfinsight: PdfinsightReader, answer_node: AnswerNode, group_end: int) -> dict[int, list[str]]:
    """
    RETURN: {
        table_index: [(0, "0_1"), (1, "1_1")],
        ....
    }
    """
    tables = {}
    answer_item = answer_node.data
    group_name = "_".join([c[0] for c in answer_node.path[1:group_end]])
    group_idx = "_".join([str(c[1]) for c in answer_node.path[1:group_end]])
    for data in answer_item["data"]:
        for box in data["boxes"]:
            page = box["page"]
            outline = (box["box"]["box_left"], box["box"]["box_top"], box["box"]["box_right"], box["box"]["box_bottom"])
            for etype, ele in pdfinsight.find_elements_by_outline(page, outline):
                if etype != "TABLE":
                    continue
                if pdfinsight.overlap_percent(ele["outline"], outline, base="element") > 0.9:
                    # 框整个表格的 pass
                    continue
                page_merged_table = ele.get("page_merged_table")
                if page_merged_table:
                    # 为口径一致，使用合并表格的第一个元素块
                    if isinstance(page_merged_table, int):
                        real_idx = page_merged_table
                    else:
                        real_idx = page_merged_table["index"]
                    _, ele = pdfinsight.find_element_by_index(real_idx)
                cells = pdfinsight.find_cell_idxes_by_outline(ele, outline, page)
                tables.setdefault(ele["index"], []).extend([(group_name, group_idx, c) for c in cells])
    return tables


def format_table(pdfinsight: PdfinsightReader, idx: int):
    etype, ele = pdfinsight.find_element_by_index(idx)
    if etype != "TABLE":
        return None
    syll = [s["title"] for s in pdfinsight.syllabus_reader.find_by_elt_index(idx)]
    cells = {n: {"text": c["text"], "page": c["page"], "box": c["box"]} for n, c in ele["cells"].items()}
    return {
        "syll": syll,
        "cells": cells,
    }


@loop_wrapper
async def main():
    # 上交所科创板
    # await export_answer(4, 1, 5000, [6], workers=16, answer_from="export_answer")
    # 深交所创业板IPO
    await export_answer(2, 1, 1000, [1, 7], workers=16, answer_from="user")


if __name__ == "__main__":
    main()
