import importlib
import json
import logging

from remarkable import config
from remarkable.common.constants import AnswerResult
from remarkable.db import pw_db
from remarkable.pw_models.model import NewDocument
from remarkable.pw_models.question import NewQuestion


class AnswerComparerFactory:
    CLASSNAME_OVER_CONFIG = None
    CLASS = None

    @classmethod
    def get_class(cls):
        if not cls.CLASS:
            class_fullname = cls.CLASSNAME_OVER_CONFIG or config.get_config(
                "web.classes.answer_comparer", "remarkable.data.answer_comparer.JsonAnswerComparer"
            )
            last_dot_index = class_fullname.rindex(".")
            mod_name, clazz_name = class_fullname[:last_dot_index], class_fullname[last_dot_index + 1 :]
            module = importlib.import_module(mod_name)
            clazz = getattr(module, clazz_name)
            cls.CLASS = clazz
        return cls.CLASS

    @classmethod
    def create(cls, question_data=None, doc_data=None):
        clazz = cls.get_class()
        return clazz(question_data, doc_data)


class JsonAnswerComparer:
    def __init__(self, question_data, doc_data):
        pass

    def compare(self, answer_1, answer_2):
        return json.dumps(answer_1) == json.dumps(answer_2)


def count_compare_result(answers, results, model, comparer):
    all_same = True
    result_count = {}
    for answer in answers:
        if model["id"] == answer["id"]:
            results[answer["id"]] = AnswerResult.CORRECT.value
            continue
        logging.debug("comparing: %s <--> %s", model["id"], answer["id"])
        if comparer.__class__.__name__ == "ScriberAnswerComparerWithCount":
            comparer.reset_status()
            _result, _count_status = comparer.compare(model["data"], answer["data"])
            if _result:
                results[answer["id"]] = AnswerResult.CORRECT.value
            else:
                results[answer["id"]] = AnswerResult.INCORRECT.value
                all_same = False
            result_count[answer["id"]] = _count_status
        else:
            if comparer.compare(model["data"], answer["data"]):
                results[answer["id"]] = AnswerResult.CORRECT.value
            else:
                results[answer["id"]] = AnswerResult.INCORRECT.value
                all_same = False
    return all_same, result_count


async def update_question_status(_id, status):
    await pw_db.execute(NewQuestion.update(status=status).where(NewQuestion.id == _id))


async def fetch_question_data(qid):
    data, did = None, None
    question = await NewQuestion.find_by_id(qid)
    if question:
        data = question.data
        did = question.did
    return data, did


async def fetch_doc_data(did):
    return await pw_db.scalar(NewDocument.data).where(NewDocument.id == did)
