import json
import logging
import os
from copy import deepcopy

from pdfparser.pdftools.pdf_doc import PDFDoc
from pdfparser.pdftools.pdf_util import PDFUtil
from speedy.peewee_plus.orm import and_

from remarkable import config
from remarkable.common.multiprocess import run_in_multiprocess
from remarkable.common.storage import localstorage
from remarkable.common.util import loop_wrapper
from remarkable.db import db, peewee_transaction_wrapper, pw_db
from remarkable.models.new_file import NewFile
from remarkable.pw_models.model import NewAnswer, NewMold
from remarkable.pw_models.question import NewQuestion

migration_path = config.target_path("data", "answers.json")


async def fetch_answers(mold, clear=False, dump_every_loop=True):
    if clear or not os.path.exists(migration_path):
        answers = {}
    else:
        with open(migration_path) as answer_fp:
            answers = json.load(answer_fp)
    fetch_user_answer_sql = """select f.id, f.name, f.hash, a.data from
    file f inner join question q on f.id = q.fid left join answer a on a.qid = q.id
    where q.mold=%(mold_id)s and q.status in (2, 5) and a.status = 1 and a.result = 1 and a.data is not NULL
    and q.deleted_utc = 0
    order by f.id;"""

    tasks = []
    async for fid, _, fhash, adata in db.iterate(db.text(fetch_user_answer_sql), mold_id=mold):
        if fhash in answers:
            continue
        _file = await NewFile.find_by_id(fid)
        if not _file:
            continue
        tasks.append((_file, adata))

    rets = run_in_multiprocess(fix_answer_outline, tasks)

    updated = False
    for _file, adata, fixed in rets or []:
        fid, fname, fhash = _file.id, _file.name, _file.hash
        if fhash in answers:
            continue
        answers[fhash] = {"name": fname, "hash": fhash, "answer": adata, "fixed": fixed}
        updated = True

    if dump_every_loop and updated:
        with open(migration_path, "w") as migration_fp:
            json.dump(answers, migration_fp)

    return answers


def fix_answer_outline(args):
    _file, answer = args
    if not _file or not _file.pdf:
        return _file, answer, False
    pdf_path = localstorage.mount(_file.pdf_path())
    if not os.path.exists(pdf_path):
        return _file, answer, False

    pages = []
    for col in answer["userAnswer"].values():
        for item in col["items"]:
            for field in item["fields"]:
                for component in field.get("components") or []:
                    print("==== fix frame ====")
                    frame = component.get("frameData")
                    page = frame.get("page")
                    if page not in pages:
                        pages.append(page)
    doc = PDFDoc(pdf_path, pages)

    for col in answer["userAnswer"].values():
        for item in col["items"]:
            for field in item["fields"]:
                for component in field.get("components") or []:
                    print("==== fix frame ====")
                    frame = component.get("frameData")
                    page = frame.get("page")
                    top = float(frame.get("top"))
                    left = float(frame.get("left"))
                    height = float(frame.get("height"))
                    width = float(frame.get("width"))
                    outline = (left, top, left + width, top + height)
                    print(frame)

                    chars = PDFUtil.chars_in_box_by_center(doc.pages[page], outline)
                    if not chars:
                        continue
                    print(len(chars))
                    fixed_outline = PDFUtil.get_bound_box([char["box"] for char in chars])
                    frame["top"] = format_coordinate(fixed_outline[1])
                    frame["left"] = format_coordinate(fixed_outline[0])
                    frame["topleft"] = [frame["top"], frame["left"]]
                    frame["height"] = format_coordinate(float(fixed_outline[3]) - float(fixed_outline[1]))
                    frame["width"] = format_coordinate(float(fixed_outline[2]) - float(fixed_outline[0]))
                    print(frame)
    return _file, answer, True


def find_chars_by_outline(path, page, outline):
    doc = PDFDoc(path, page_range=[page])
    return PDFUtil.chars_in_box_by_center(doc.pages[page], outline)


def format_coordinate(value):
    if isinstance(value, float):
        return "{:.4f}".format(value)
    return value


async def import_answers(answers, mold):
    async def _import_answer(fname, fhash, answer):
        insert_file_sql = """insert into file(tree_id, pid, name, hash, pdf, mold)
            values(0, 0, %(name)s, %(hash)s, %(pdf)s, %(mold_id)s)
            returning id;
            """
        fid = await db.raw_sql(
            insert_file_sql,
            "scalar",
            **{
                "name": fname,
                "hash": fhash,
                "pdf": fhash,
                "mold_id": mold,
            },
        )

        insert_question_sql = """insert into question(data, checksum, fid, mold, preset_answer)
            values(%(data)s, %(checksum)s, %(fid)s, %(mold)s, %(preset_answer)s)
            returning id;
            """
        qid = await db.raw_sql(
            insert_question_sql,
            "scalar",
            **{
                "data": json.dumps(
                    {
                        "file_id": fid,
                    }
                ),
                "checksum": NewQuestion.gen_checksum(fid, mold),
                "fid": fid,
                "mold": mold,
                "preset_answer": json.dumps(answer),
            },
        )
        await NewFile.update_by_pk(fid, qid=qid)

    for item in answers:
        await _import_answer(item["name"], item["hash"], item["answer"])


@loop_wrapper
@peewee_transaction_wrapper
async def do_export_answers(mold):
    answers = await fetch_answers(mold)
    with open(migration_path, "w") as migration_fp:
        json.dump(answers, migration_fp)


@loop_wrapper
@peewee_transaction_wrapper
async def do_import_answers(mold):
    with open(migration_path, "r") as migration_fp:
        answers = json.load(migration_fp)
    await import_answers(answers.values(), mold)


async def migrate_answers(mid, start, end, old_mold_name):
    mold = await NewMold.get_by_id(mid)
    answer_query = (
        NewAnswer.select()
        .join(NewQuestion, on=(NewQuestion.id == NewAnswer.qid))
        .join(NewFile, on=(NewFile.id == NewQuestion.fid))
    )
    cond = NewQuestion.mold == mid
    cond &= and_(NewFile.id >= start, NewFile.id <= end)

    # find answers
    answers = await pw_db.execute(answer_query.where(cond))
    if not answers:
        return
    for answer in answers:
        # edit answer
        for item in answer.data["userAnswer"]["items"]:
            key = item["key"]
            key = key.replace(old_mold_name, mold.name)
            item["key"] = key
        answer.data["schema"] = deepcopy(mold.data)
        answer.data["schema"]["version"] = mold.checksum
        await NewAnswer.update_by_pk(answer.id, data=answer.data)
        logging.info(f"update answer: {answer.qid=}")


if __name__ == "__main__":
    import asyncio

    asyncio.run(migrate_answers(3, 1, 1000, "富国基金"))
