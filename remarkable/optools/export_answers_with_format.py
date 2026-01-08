import json
import logging
from pathlib import Path

from remarkable.answer.common import fix_answer_outline_interdoc
from remarkable.answer.reader import AnswerReader
from remarkable.common.multiprocess import run_in_multiprocess
from remarkable.common.storage import localstorage
from remarkable.common.util import loop_wrapper
from remarkable.models.new_file import NewFile
from remarkable.pdfinsight.reader import PdfinsightReader
from remarkable.pw_models.model import NewAnswer, NewMold, NewSpecialAnswer
from remarkable.pw_models.question import NewQuestion

logger = logging.getLogger(__name__)


async def export_answer(
    mid: int,
    start: int,
    end: int,
    pids: list[int] = None,
    workers=4,
    answer_from="user",
    dump_path="data/export_answers",
):
    dump_path = Path(dump_path)
    dump_path.mkdir(exist_ok=True)
    # TODO: iter with a sql
    mold = await NewMold.find_by_id(mid)
    if not mold:
        raise Exception(f"can't find mold {mid}")
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
        answer = await get_annotation_answer(question.id, answer_from, question=question)
        if not answer:
            logging.debug(f"have no annotation answer, pass fid: {fid}")
            continue
        tasks.append(
            (
                fid,
                localstorage.mount(file.pdfinsight_path()),
                answer,
                dump_path / f"{file.hash}.json",
            )
        )
        if len(tasks) >= workers * 2:
            run_in_multiprocess(dump_training_data, tasks, workers=workers)
            tasks.clear()
    if tasks:
        run_in_multiprocess(dump_training_data, tasks, workers=workers)
        tasks.clear()


async def get_annotation_answer(qid, answer_type, question=None, add_element_index=False):
    answer_data = {}
    if answer_type == "user":
        # 从用户答案中取
        answer = await NewAnswer.find_standard(qid)
        if answer:
            answer_data = answer.data
            logger.info(f"user answer, answer.id:{answer.id}")
    elif answer_type == "merge":
        # 从合并答案 question.answer 中取
        if not question:
            question = await NewQuestion.find_by_id(qid)
        if question:
            answer_data = question.answer
            logger.info(f"merge answer, question.id:{question.id}")
    else:
        # 从 special answer 中取指定类型
        special_answers = await NewSpecialAnswer.get_answers(qid, answer_type, top=1)
        if special_answers:
            answer_data = special_answers[0].data
            logger.info(f"special answer, special_answer.id:{special_answers[0].id}")

    if add_element_index:
        file = await NewFile.find_by_id(question.fid)
        reader = PdfinsightReader(localstorage.mount(file.pdfinsight_path()))
        answer_data = AnswerReader.add_element_index(answer_data, reader)

    return answer_data


def format_answer_to_json_tree(answer_data, interdoc_path):
    answer_data = fix_answer_outline_interdoc(interdoc_path, answer_data)
    reader = AnswerReader(answer_data)
    node, _ = reader.build_answer_tree()
    return node.to_dict()


# TODO: 答案格式化方法可扩展
def dump_training_data(fid, interdoc_path, answer_data, save_path):
    logging.info(f"exporting file {fid}")
    formated_answer = format_answer_to_json_tree(answer_data, interdoc_path)
    with Path(save_path).open("w") as dfp:
        json.dump(formated_answer, dfp)
    logging.info(f"export answer for file {fid} success")


@loop_wrapper
async def main():
    # 44033
    await export_answer(1, 1, 1000, [1], workers=16, answer_from="user")


if __name__ == "__main__":
    main()
