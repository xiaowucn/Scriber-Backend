import datetime
import gzip
import json
import logging

from remarkable import config
from remarkable.common.constants import CCXI_CACHE_PATH
from remarkable.common.diff import fake_interdocs

logger = logging.getLogger(__name__)


def utc_now():
    return int(datetime.datetime.utcnow().timestamp())


def add_url(items):
    """返回列表中添加跳转Calliper比对结果的url"""
    lst = []
    url = "{}/#/pdfDiffResult?compareId={{cmp_id}}&file1={{fid1}}&file2={{fid2}}".format(
        config.get_config("diff.calliper_domain")
    )
    for item in items:
        item["url"] = url.format(cmp_id=item["cmp_id"], fid1=item["dst_fid1"], fid2=item["dst_fid2"])
        lst.append(item)
    return lst


def get_cache_for_diff(file):
    file_path = CCXI_CACHE_PATH / file.pdfinsight[:2] / file.pdfinsight[2:]
    if not file_path.exists():
        return None
    with gzip.open(file_path, "rb") as file_obj:
        data = json.load(file_obj)
    return data


def gen_cache_for_diff(answer, reader):
    from remarkable.answer.common import dump_key

    items = answer["userAnswer"]["items"]
    docs = fake_interdocs(items, reader, key_dumps_func=dump_key)

    file_path = CCXI_CACHE_PATH / reader.path.split("/")[-2]
    file_name = reader.path.split("/")[-1]
    if not file_path.exists():
        file_path.mkdir(parents=True)

    with gzip.open(file_path / file_name, "wt") as file_obj:
        json.dump(docs, file_obj, ensure_ascii=False)

    logger.info("cache pdfinsight info done.")
    return docs
