import json
import logging
import time

from remarkable.db import init_rdb

# from remarkable.config import get_config


def _cached_files_key(schema_id):
    return "s_%s_files" % schema_id


def _words_key(schema_id, attr, kind):
    return "s_%s_k_%s_%s" % (schema_id, attr, kind)


def is_loaded(schema_id, fid):
    rdb = init_rdb()
    return rdb.hexists(_cached_files_key(schema_id), fid)


def push_loaded_file(schema_id, fid):
    rdb = init_rdb()
    rdb.hset(_cached_files_key(schema_id), fid, "1")


def pop_loaded_file(schema_id, fid):
    rdb = init_rdb()
    rdb.hdel(_cached_files_key(schema_id), fid)


def list_loaded_files(schema_id):
    rdb = init_rdb()
    return [int(key) for key in rdb.hgetall(_cached_files_key(schema_id)).keys()]


def update_ngrams(schema_id, _dict, attr="global", kind="content", power=1):
    rdb = init_rdb()
    for word, times in _dict.items():
        try:
            rdb.hincrby(_words_key(schema_id, attr, kind), word, amount=times * power)
        except Exception as ex:
            logging.error("can't cache words %s, %s", word, ex)


def update_texts_around(schema_id, attr, text_around):
    rdb = init_rdb()
    rdb.rpush(_words_key(schema_id, attr, "text_around"), json.dumps(text_around))


def get_texts_around(schema_id, attr):
    rdb = init_rdb()
    key = _words_key(schema_id, attr, "text_around")
    texts_len = rdb.llen(key)
    texts = [json.loads(text) for text in rdb.lrange(key, 0, texts_len)]
    return texts


# def update_ngrams_by_words(schema_id, words, attr="global", kind="content", power=1):
#     for word in words:
#         try:
#             rdb.hincrby(_words_key(schema_id, attr, kind), word, amount=1 * power)
#         except Exception as ex:
#             logging.error("can't cache words %s, %s", word, ex)

# def get_ngram(schema_id, word, attr="global", kind="content"):
#     rdb = init_rdb()
#     return int(rdb.hget(_words_key(schema_id, attr, kind), word) or "0")


def get_ngrams(schema_id, attr, kind="content"):
    rdb = init_rdb()
    return {k: int(v) for k, v in rdb.hgetall(_words_key(schema_id, attr, kind)).items()}


def clear_ngram_cache(schema_id):
    rdb = init_rdb()
    for key in rdb.keys("s_%s*" % schema_id):
        rdb.delete(key)


_training_tasks_key = "trainning_tasks"


def push_training_task(schema_id):
    rdb = init_rdb()
    if not rdb.zscore(_training_tasks_key, schema_id):
        try:
            rdb.zadd(_training_tasks_key, schema_id, time.time())
        except AttributeError:
            rdb.zadd(_training_tasks_key, {schema_id: time.time()})
        return True
    else:
        return False


def pop_training_task():
    rdb = init_rdb()
    top1tasks = rdb.zrange(_training_tasks_key, 0, 0)
    if top1tasks:
        _task = int(top1tasks[0])
        rdb.zrem(_training_tasks_key, _task)
        return _task
    else:
        return None


def training_task_empty():
    rdb = init_rdb()
    return rdb.zrange(_training_tasks_key, 0, 0) is None


def _updated_files_key(schema_id):
    return "updated_files_s%s" % (schema_id,)


def push_updated_files(schema_id, fid):
    rdb = init_rdb()
    rdb.lpush(_updated_files_key(schema_id), fid)


def pop_all_updated_files(schema_id):
    rdb = init_rdb()
    _key = _updated_files_key(schema_id)
    _all = rdb.lrange(_key, 0, -1)
    rdb.delete(_key)
    return [int(_id) for _id in _all]
