"""
债券评级报告

X放大倍数（融资担保放大倍数）- 数额
--->
X放大倍数（融资担保放大倍数）- 金额
"""

import logging
from copy import deepcopy

from remarkable.common.util import loop_wrapper, md5json
from remarkable.db import peewee_transaction_wrapper
from remarkable.models.new_file import NewFile
from remarkable.pw_models.model import NewAnswer, NewMold
from remarkable.pw_models.question import NewQuestion


async def update_mold(mold_id):
    mold = await NewMold.find_by_id(mold_id)
    checksum = md5json(mold.data)
    if mold.checksum != checksum:
        logging.warning(
            f"Update checksum for mold {mold_id}",
        )
        await mold.update_(checksum=checksum)
        mold.checksum = checksum
    return mold


@loop_wrapper
@peewee_transaction_wrapper
async def update_swhysc_bond_rate_answer(mid=3):
    aim_mold = await update_mold(mid)
    # find all file
    files = await NewFile.find_by_kwargs(delegate="all", mold=mid)
    for file in files:
        # find answer
        question = await NewQuestion.find_by_fid_mid(file.id, mid)
        answer = await NewAnswer.find_standard(qid=question.id)
        if not answer:
            continue
        # edit answer
        for item in answer.data["userAnswer"]["items"]:
            key = item["key"]
            if "X放大倍数（融资担保放大倍数）" in key and "数额" in key:
                key = key.replace("""数额:0","数额:0""", """金额:0","数值:0""")
                item["key"] = key
        answer.data["schema"] = deepcopy(aim_mold.data)
        answer.data["schema"]["version"] = aim_mold.checksum
        await NewAnswer.update_by_pk(answer.id, data=answer.data)
        logging.info(f"update answer: {answer.qid}, file: {file.id}")


@loop_wrapper
@peewee_transaction_wrapper
async def update_china_stock_answer(mid=7):
    aim_mold = await update_mold(mid)
    # find all file
    files = await NewFile.find_by_kwargs(delegate="all", mold=mid)
    for file in files:
        # find answer
        question = await NewQuestion.find_by_fid_mid(file.id, mid)
        if not question:
            continue
        answer = await NewAnswer.find_standard(qid=question.id)
        if not answer:
            continue
        # edit answer
        answer_data = answer.data["userAnswer"]["items"]
        for item in answer_data:
            key = item["key"]
            if " 基金管理团队" in key:
                key = key.replace(""" 基金管理团队""", """基金管理团队""")
                item["key"] = key
                item["schema"]["data"]["label"] = "基金管理团队"
        answer.data["schema"] = deepcopy(aim_mold.data)
        answer.data["schema"]["version"] = aim_mold.checksum
        await NewAnswer.update_by_pk(answer.id, data=answer.data)
        logging.info(f"update answer data: {answer.qid}, file: {file.id}")


@loop_wrapper
@peewee_transaction_wrapper
async def update_csc_demand_note_answer(mid=2, fid=None):
    data_map = {
        "缴款价位_数值": "数值",
        "缴款价位_单位": "单位",
        "中标量_数值": "数值",
        "中标量_单位": "单位",
        "中标量（合计）_数值": "数值",
        "中标量（合计）_单位": "单位",
        "缴款金额（合计）_数值": "数值",
        "缴款金额（合计）_单位": "单位",
    }
    aim_mold = await update_mold(mid)
    # find all file
    if fid:
        files = await NewFile.find_by_kwargs(delegate="all", mold=mid, id=fid)
    else:
        files = await NewFile.find_by_kwargs(delegate="all", mold=mid)
    for file in files:
        # find answer
        question = await NewQuestion.find_by_fid_mid(file.id, mid)
        if not question:
            continue
        answer = await NewAnswer.find_standard(qid=question.id)
        if not answer:
            continue
        # edit answer
        answer_data = answer.data["userAnswer"]["items"]
        for item in answer_data:
            key = item["key"]
            for wrong_key, correct_key in data_map.items():
                if wrong_key in key:
                    key = key.replace(wrong_key, correct_key)
                    item["key"] = key
                    item["schema"]["data"]["label"] = correct_key
                    item["schema"]["meta"] = {}
        answer.data["schema"] = deepcopy(aim_mold.data)
        answer.data["schema"]["version"] = aim_mold.checksum
        await NewAnswer.update_by_pk(answer.id, data=answer.data)
        logging.info(f"update answer data: {answer.qid}, file: {file.id}")


if __name__ == "__main__":
    update_csc_demand_note_answer()
