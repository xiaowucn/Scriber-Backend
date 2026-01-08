from peewee import IntegerField

from remarkable.db import pw_db
from remarkable.pw_models.base import BaseModel
from remarkable.pw_orm import field


class ModelAnswer(BaseModel):
    vid = IntegerField()
    qid = IntegerField()
    data = field.JSONField(default=dict)
    created_utc = IntegerField()
    updated_utc = IntegerField()

    class Meta:
        table_name = "model_answer"

    @classmethod
    async def update_or_create(cls, vid, qid, data):
        answer = await pw_db.first(cls.select().where(cls.vid == vid, cls.qid == qid))
        if answer:
            answer.data = data
            await pw_db.update(answer)
        else:
            await cls.create(vid=vid, qid=qid, data=data)

    @classmethod
    async def get_answer(cls, vid, qid):
        answer = await pw_db.first(cls.select().where(cls.vid == vid, cls.qid == qid))
        return answer
