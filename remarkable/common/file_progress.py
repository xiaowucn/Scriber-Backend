import json
import logging

from remarkable.common.enums import ExtractType
from remarkable.data.answer_tools import load_key_path
from remarkable.db import pw_db
from remarkable.pw_models.model import NewAnswer
from remarkable.pw_models.question import NewQuestion


class QuestionProgress:
    def __init__(self, qid):
        self.qid = int(qid)
        self.counted_key = set()

    @staticmethod
    def calc_progress_total(data):
        schema_total = sum(
            1
            for schema_info in data["schema"]["schemas"][0]["schema"].values()
            if schema_info["extract_type"] != ExtractType.LLM.value
        )
        custom_total = len(data.get("custom_field", {}).get("items", []))
        return schema_total + custom_total

    def rule_finished(self, rule):
        key_path = [k.name for k in load_key_path(rule.get("key"))]
        if len(key_path) == 1:  # not root rule
            return False
        count_key = json.dumps(key_path[:2])
        if count_key in self.counted_key:
            return False

        for item in rule.get("data", []):
            if item.get("value", ""):
                self.counted_key.add(count_key)
                return True
            else:
                for _box in item.get("boxes", []):
                    if _box:
                        self.counted_key.add(count_key)
                        return True
        return False

    async def calc_progress(self):
        progress = []
        for answer in await pw_db.execute(NewAnswer.select(NewAnswer.data).where(NewAnswer.qid == self.qid)):
            data = answer.data
            self.counted_key.clear()
            total = self.calc_progress_total(data)
            if total <= 0:
                continue
            finished = 0
            for rule in data["userAnswer"]["items"]:
                if self.rule_finished(rule) and rule["schema"]["data"]["extract_type"] != ExtractType.LLM.value:
                    finished += 1
            for rule in data.get("custom_field", {}).get("items", []):
                if self.rule_finished(rule):
                    finished += 1
            progress.append((finished, total))
        if not progress:
            return ""

        min_ = (-1, -1)
        for finished, total in progress:
            if finished / total <= min_[0] / min_[1]:
                min_ = (finished, total)
        return "{}/{}".format(min_[0], min_[1])

    async def update_progress(self):
        progress = await self.calc_progress()
        if not progress:
            return
        question = await NewQuestion.update_by_pk(self.qid, progress=progress)
        if question.progress != progress:
            logging.error("更新progress失败: qid=%s", self.qid)
