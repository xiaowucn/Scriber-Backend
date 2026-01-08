import logging
import re
from collections import defaultdict, namedtuple
from copy import deepcopy

from invoke import task

from remarkable.db import peewee_transaction_wrapper
from remarkable.devtools import InvokeWrapper

R_REMOVE_INDEX = re.compile(r":\d+")


@task(klass=InvokeWrapper)
async def delete_word(ctx, mid, field_name, start=None, end=None, workers=0):
    """
    删除schema中的某个字段后，迁移答案
    删除操作是在界面手动进行
    """
    from remarkable.common.multiprocess import run_in_multiprocess
    from remarkable.pw_models.question import NewQuestion

    questions = await NewQuestion.list_by_range(mold=mid, start=start, end=end, special_cols=["id"])
    tasks = [(question.id, mid, "delete", field_name) for question in questions]
    run_in_multiprocess(migrate_answer, tasks, workers=workers, ctx_method="spawn")


@task(klass=InvokeWrapper)
async def modify_word(ctx, mid, from_field="", to_field="", start=None, end=None, workers=0):
    """
    修改schema中的某个字段后，迁移答案
    修改操作是在界面手动进行
    """
    from remarkable.common.multiprocess import run_in_multiprocess
    from remarkable.pw_models.question import NewQuestion

    questions = await NewQuestion.list_by_range(mold=mid, start=start, end=end, special_cols=["id"])
    tasks = [(question.id, mid, "modify", from_field, to_field) for question in questions]
    run_in_multiprocess(migrate_answer, tasks, workers=workers, ctx_method="spawn")


@peewee_transaction_wrapper
async def migrate_answer(args):
    """
    action maybe is delete、modify、 add, every action should has a function
    # todo add function for add
    """
    from remarkable.pw_models.model import NewAnswer, NewMold
    from remarkable.pw_models.question import NewQuestion

    answer_tuple = namedtuple("Answer", ["id", "table", "col", "data"])
    qid, mid, action, *params = args
    mold = await NewMold.find_by_id(mid)
    if not mold:
        logging.info("Mold not found")
        return
    # 更新mold表的checksum  # 在界面手动更新schema时已经执行了下面的操作
    # mold.update_mold_checksum()
    answers = await NewAnswer.get_answers_by_qid(qid)
    all_answers = [answer_tuple._make([answer.id, "answer", "data", answer.data]) for answer in answers]
    question = await NewQuestion.find_by_id(qid)
    if question and question.preset_answer:
        all_answers.append(answer_tuple._make([qid, "question", "preset_answer", question.preset_answer]))
    if question and question.answer:
        all_answers.append(answer_tuple._make([qid, "question", "answer", question.answer]))
    for answer in all_answers:
        if answer.data["schema"].get("version") == mold.checksum:
            logging.info(f"file<{question.fid}> table<{answer.table}> id<{answer.id}> has same schema version")
            continue
        if action == "delete":
            (field_name,) = params
            delete_item(answer, field_name)
        if action == "modify":
            from_field, to_field = params
            modify_item(answer, from_field, to_field)
        answer.data["schema"] = deepcopy(mold.data)
        answer.data["schema"]["version"] = mold.checksum
        if answer.table == "answer":
            await NewAnswer.update_by_pk(answer.id, data=answer.data)
        if answer.table == "question":
            await NewQuestion.update_by_pk(answer.id, **{answer.col: answer.data})
        logging.info(f"update file<{question.fid}> table<{answer.table}> id<{answer.id}> to version {mold.checksum}")


def delete_item(answer, field_name):
    for key in "userAnswer", "rule_result":
        answer_data = answer.data.get(key, {}).get("items", [])
        if not answer_data:
            continue
        answer.data[key]["items"] = [item for item in answer_data if field_name not in item["key"]]
    return answer


def modify_item(answer, from_field, to_field):
    answer_data = answer.data["userAnswer"]["items"]
    for item in answer_data:
        key = item["key"]
        if f'"{from_field}:' in key:
            replaced_key = key.replace(from_field, to_field)
            logging.info(f"{key}, changes to {replaced_key}")
            item["key"] = replaced_key
            item["schema"]["data"]["label"] = to_field
    return answer


@task(klass=InvokeWrapper)
async def add_field_id_to_answer(ctx, mid=None):
    from remarkable.answer.reader import AnswerReader
    from remarkable.common.util import clean_txt, compact_dumps
    from remarkable.db import pw_db
    from remarkable.models.cmf_china import CmfUserCheckFields
    from remarkable.predictor.mold_schema import MoldSchema
    from remarkable.pw_models.answer_data import NewAnswerData, NewAnswerDataStat
    from remarkable.pw_models.model import NewMold, NewMoldField
    from remarkable.pw_models.question import NewQuestion
    from remarkable.service.mold_field import MoldFieldService
    from remarkable.service.new_mold import NewMoldService

    query = NewMold.select().order_by(NewMold.id)
    if mid:
        query = query.where(NewMold.id == mid)
    molds = await pw_db.execute(query)
    questions = await pw_db.execute(NewQuestion.select())
    # audit_result = await pw_db.execute(NewAuditResult.select())

    mold_question = defaultdict(list)
    for question in questions:
        mold_question[question.mold].append(question)

    def gen_field_id_mapping(
        data_list: list[NewAnswerData | NewAnswerDataStat],
        path_mapping: dict[str, list[str]],
        field_uuid_mapping: dict[str, int],
    ):
        res_map = {}
        for data in data_list:
            if not data.key:
                print(f"answer_data: {data.id}, key is None")
                continue
            if isinstance(data, NewAnswerData):
                key = R_REMOVE_INDEX.sub("", data.key)
            else:
                key = data.key
            if uuid_path := path_mapping.get(clean_txt(key)):
                if mold_field_id := field_uuid_mapping.get(compact_dumps(uuid_path)):
                    res_map[data.id] = mold_field_id
        return res_map

    def add_uuid_path_to_answer(
        answer,
        path_mapping: dict[str, list[str]],
    ):
        answer_reader = AnswerReader(answer)
        for item in answer_reader.items:
            key = clean_txt(R_REMOVE_INDEX.sub("", item["key"]))
            if uuid_path := path_mapping.get(key):
                item["md5"] = compact_dumps(uuid_path)

    print("start add_field_id_to_answer")

    async with pw_db.atomic():
        # 删除之前所有的用户选择列表
        await pw_db.execute(CmfUserCheckFields.delete())

        for mold in molds:
            if await NewMoldField.find_by_kwargs(mid=mold.id):
                continue
            print(f"sync mold:{mold.name}")
            await NewMoldService.update_field(mold)

            uuid_path_mapping = MoldSchema(mold.data).get_path_mapping()
            mold_field_mapping = await MoldFieldService.get_mold_field_uuid_path(mold.id)
            mold_field_uuid_path = {compact_dumps(row.path): row.id for row in mold_field_mapping}

            # 刷新question
            if questions := mold_question.get(mold.id):
                answer_id_mapping = {}
                preset_answer_id_mapping = {}
                for question in questions:
                    answer_data_list = list(
                        await pw_db.execute(NewAnswerData.select().where(NewAnswerData.qid == question.id))
                    )
                    answer_data_stat_list = list(
                        await pw_db.execute(NewAnswerDataStat.select().where(NewAnswerDataStat.qid == question.id))
                    )
                    bulk_map = gen_field_id_mapping(answer_data_list, uuid_path_mapping, mold_field_uuid_path)
                    await NewAnswerData.bulk_update(NewAnswerData.mold_field_id, NewAnswerData.id, bulk_map)
                    bulk_map = gen_field_id_mapping(answer_data_stat_list, uuid_path_mapping, mold_field_uuid_path)
                    await NewAnswerDataStat.bulk_update(NewAnswerDataStat.mold_field_id, NewAnswerDataStat.id, bulk_map)

                    if question.answer:
                        add_uuid_path_to_answer(question.answer, uuid_path_mapping)
                        answer_id_mapping[question.id] = compact_dumps(question.answer)
                    if question.preset_answer:
                        add_uuid_path_to_answer(question.preset_answer, uuid_path_mapping)
                        preset_answer_id_mapping[question.id] = compact_dumps(question.preset_answer)
                await NewQuestion.bulk_update(NewQuestion.answer, NewQuestion.id, answer_id_mapping)
                await NewQuestion.bulk_update(NewQuestion.preset_answer, NewQuestion.id, preset_answer_id_mapping)
            # 刷新audit result
            # TODO

    print("end add_field_id_to_answer")


if __name__ == "__main__":
    from invoke import Context

    add_field_id_to_answer(Context())
