import re

from remarkable.db import pw_db
from remarkable.pw_models.answer_data import NewAnswerData, NewAnswerDataStat

R_REMOVE_INDEX = re.compile(r":\d+")


async def sync_answer_data_stat(ids: list[int] = None):
    query = (
        NewAnswerData.select()
        .where(NewAnswerData.key.is_null(False), NewAnswerData.value.is_null(False), NewAnswerData.data.is_null(False))
        .order_by(NewAnswerData.id)
    )
    if ids:
        query = query.where(NewAnswerData.id.in_(ids))
        await pw_db.execute(NewAnswerDataStat.delete().where(NewAnswerDataStat.answer_data_id.in_(ids)))
    data_list = list(await pw_db.execute(query))
    res = []

    def gen_data(data, record, value):
        return {
            "answer_data_id": data.id,
            "record": record,
            "qid": data.qid,
            "uid": data.uid,
            "key": key,
            "content": value,
            "score": None if data.score is None else data.score,
            "mold_field_id": data.mold_field_id,
        }

    for data in data_list:
        key = R_REMOVE_INDEX.sub("", data.key)
        record = bool(data.record)
        if data.value:
            for value in data.value:
                res.append(gen_data(data, record, value))
        elif data.data:
            for item in data.data:
                res.append(
                    gen_data(
                        data,
                        record,
                        item.get("text")
                        or "\n".join(box.get("text") for box in item.get("boxes", []) if box.get("text")),
                    )
                )
        else:
            res.append(gen_data(data, record, ""))
    await NewAnswerDataStat.bulk_insert(res)


if __name__ == "__main__":
    import asyncio

    asyncio.run(sync_answer_data_stat())
