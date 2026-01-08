from peewee import IntegerField, TextField
from pgvector.peewee import VectorField

from remarkable.db import pw_db
from remarkable.pw_models.base import BaseModel
from remarkable.service.chatgpt import OpenAIClient


class Embedding(BaseModel):
    file_id = IntegerField()
    index = IntegerField()
    embedding = VectorField(1536)
    text = TextField()

    MAX_EMBEDDING_LIMIT = 50

    @classmethod
    def semantic_search_query(cls, fid: int, query_text: str, limit: int = 10):
        question_embedding = OpenAIClient().get_embddings([query_text])
        embedding_str = list(question_embedding)[0]
        distance_col = cls.embedding.cosine_distance(embedding_str)
        return (
            cls.select(
                cls.index,
                (1 - distance_col).alias("score"),
            )
            .where(cls.file_id == fid)
            .order_by(distance_col)
            .limit(limit)
            .dicts()
        )

    @classmethod
    async def semantic_search(cls, fid: int, query_text: str, limit: int = 10):
        return list(await pw_db.execute(cls.semantic_search_query(fid, query_text, limit)))
