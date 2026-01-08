# """
# 基金合同（海通证券） -->  私募类基金合同
# """
#
# import logging
# import os
# import shutil
# import tempfile
# from copy import deepcopy
#
# from remarkable.common.util import loop_wrapper, md5json
# from remarkable.config import get_config
# from remarkable.db import peewee_transaction_wrapper
# from remarkable.models.answer import Answer
# from remarkable.models.mold import Mold
# from remarkable.service.predictor import predictor_model_path
#
# OLD_NAME = "基金合同（海通证券）"
# NEW_NAME = "私募类基金合同"
#
#
# async def update_mold(mold_name=OLD_NAME):
#     mold = await NewMold.find_by_name(mold_name)
#     if not mold:
#         return None
#     mold.name = NEW_NAME
#     for schema in mold.data["schemas"]:
#         if schema["name"] == mold_name:
#             schema["name"] = NEW_NAME
#     mold.checksum = md5json(mold.data)
#     await mold.update_(name=NEW_NAME, data=mold.data, checksum=mold.checksum)
#     return mold
#
#
# @loop_wrapper
# @peewee_transaction_wrapper
# async def update_ht_fund_answer(mold_name="基金合同（海通证券）"):
#     aim_mold = await update_mold(mold_name)
#     if not aim_mold:
#         return None
#     # find all file
#     files = await NewFile.find_by_kwargs(delegate="all")
#     for file in files:
#         # find answer
#         question = await NewQuestion.find_by_fid_mid(file.id, aim_mold.id)
#         if not question:
#             continue
#         await update_question(question, aim_mold, file.id)
#         answer = await Answer.find_by_kwargs(qid=question.id)
#         if not answer:
#             continue
#         await update_answer(answer, aim_mold, file.id)
#
#     return aim_mold
#
#
# async def update_question(question, aim_mold, fid):
#     for answer in (question.answer, question.preset_answer):
#         if not answer:
#             continue
#         for item in answer["userAnswer"]["items"]:
#             key = item["key"]
#             if OLD_NAME in key:
#                 key = key.replace("基金合同（海通证券）:0", "私募类基金合同:0")
#                 item["key"] = key
#         answer["schema"] = deepcopy(aim_mold.data)
#         answer["schema"]["version"] = aim_mold.checksum
#     await Question.update_by_pk(question.id, answer=question.answer, preset_answer=question.preset_answer)
#     logging.info(f"update question: {question.id}, file: {fid}")
#
#
# async def update_answer(answer, aim_mold, fid):
#     # edit answer
#     for item in answer.data["userAnswer"]["items"]:
#         key = item["key"]
#         if OLD_NAME in key:
#             key = key.replace("基金合同（海通证券）:0", "私募类基金合同:0")
#             item["key"] = key
#     answer.data["schema"] = deepcopy(aim_mold.data)
#     answer.data["schema"]["version"] = aim_mold.checksum
#     await NewAnswer.update_by_pk(answer.id, data=answer.data)
#     logging.info(f"update answer: {answer.qid}, file: {fid}")
#
#
# @loop_wrapper
# async def copy_special_model(mold):
#     """
#     将本地训练的模型拷贝至客户环境指定目录
#     """
#     if not mold:
#         logging.info("schema and answer update success, only copy predictor file")
#         mold = await NewMold.find_by_name(NEW_NAME)
#     if not mold:
#         raise Exception("find new name schema error!")
#     model_dir = os.path.join(get_config("training_cache_dir"), str(mold.id), "0", "predictors")
#     archive_path = predictor_model_path("ht_fund_simple")
#     with tempfile.TemporaryDirectory() as tmp_dir:
#         shutil.unpack_archive(archive_path, tmp_dir)
#         files = os.listdir(os.path.join(tmp_dir, "predictors"))
#         for file in files:
#             source = os.path.join(tmp_dir, "predictors", file)
#             shutil.copy2(source, model_dir)
#             logging.info(f"deploy {file} to {model_dir}")
#
#
# def main():
#     aim_mold = update_ht_fund_answer()
#     copy_special_model(aim_mold)
#
#
# if __name__ == "__main__":
#     main()
