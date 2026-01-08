# https://gitpd.paodingai.com/cheftin/docs_scriber/-/issues/3391
import json
import logging
import operator
import os
import re
import tempfile
from dataclasses import dataclass
from decimal import Decimal
from pathlib import Path

import click
from openpyxl.workbook import Workbook

from remarkable.answer.node import AnswerItem
from remarkable.answer.reader import AnswerReader
from remarkable.common.multiprocess import run_by_batch
from remarkable.common.util import clean_txt
from remarkable.config import target_path
from remarkable.db import pw_db
from remarkable.models.new_file import NewFile
from remarkable.optools.fm_upload import FMUploader
from remarkable.pw_models.model import NewAnswer
from remarkable.pw_models.question import NewQuestion

MID = 2


def gen_url(fid: int, tree_id: int, qid: int) -> str:
    # return f"http://100.64.0.3:22102/#/search?fileid={fid}"
    return f"http://100.64.0.3:22102/#/project/remark/{qid}?treeId={tree_id}&fileId={fid}&schemaId={MID}&projectId={tree_id}"


def gen_public_url(fid: int, tree_id: int, qid: int) -> str:
    return f"http://scriber-csc-mark.test.paodingai.com/#/project/remark/{qid}?treeId={tree_id}&fileId={fid}&schemaId={MID}&projectId={tree_id}"


@dataclass
class AnswerCompose:
    key_path: str
    text: str
    enum: str

    def __hash__(self):
        return hash((self.key_path, self.text, self.enum))


@dataclass
class DiffRes:
    res: bool
    fid: int
    url: str
    public_url: str
    desc: str | None = ""

    def to_line(self):
        return [self.fid, self.url, self.public_url, self.desc]


def find_different_keys(dict1, dict2):
    common_keys = set(dict1.keys()) & set(dict2.keys())
    different_keys = set(dict1.keys()) ^ set(dict2.keys())
    for key in common_keys:
        if dict1[key] != dict2[key]:
            different_keys.add(key)

    return different_keys


async def find_diff_res(fid: int, qid: int) -> DiffRes | None:
    file = await NewFile.find_by_id(fid)
    if not file:
        return DiffRes(True, fid, "", "", "文件未找到")
    url = gen_url(file.id, file.tree_id, qid)
    public_url = gen_public_url(file.id, file.tree_id, qid)
    query = (
        NewAnswer.select()
        .join(NewQuestion, on=(NewAnswer.qid == NewQuestion.id))
        .join(NewFile, on=(NewQuestion.fid == NewFile.id))
        .where((NewQuestion.mold == MID) & (NewFile.id == fid))
        .order_by(NewAnswer.created_utc)
    )
    answers = list(await pw_db.execute(query))
    if len(answers) < 2:
        return DiffRes(True, fid, url, public_url, "只有一份答案")
    if len(answers) == 3:
        logging.info(f"{fid} 已经有第三份答案")
    first_answer, second_answer = answers[0], answers[1]
    first_answer = AnswerReader(first_answer.data)
    second_answer = AnswerReader(second_answer.data)
    first_answer_nodes = list(first_answer.find_nodes(["报价信息"]))
    second_answer_nodes = list(second_answer.find_nodes(["报价信息"]))
    if len(first_answer_nodes) != len(second_answer_nodes):
        logging.info(f"{fid} 答案数量不一致")
        return DiffRes(False, fid, url, public_url, "答案数量不一致")
    descriptions = []
    first_answer_nodes.sort(key=operator.attrgetter("fullpath"))
    second_answer_nodes.sort(key=operator.attrgetter("fullpath"))
    for first_item, second_item in zip(first_answer_nodes, second_answer_nodes):
        first_item_texts = {}
        for key, item in first_item.items():
            if plain_text := AnswerItem(**item.data).plain_text:
                first_item_texts[key[0]] = plain_text

        second_item_texts = {}
        for key, item in second_item.items():
            if plain_text := AnswerItem(**item.data).plain_text:
                second_item_texts[key[0]] = plain_text

        if first_item_texts != second_item_texts:
            different_keys = find_different_keys(first_item_texts, second_item_texts)
            description = f"第{first_item.idx + 1}个答案不一致，不一致的字段有：{','.join(different_keys)}"
            descriptions.append(description)
    if descriptions:
        return DiffRes(False, fid, url, public_url, "\n\n".join(descriptions))

    return DiffRes(True, fid, url, public_url, "正确")


@click.command()
@click.option("--fid", type=int, help="File ID to process")
@click.option("--start", type=int, help="Start file ID range")
@click.option("--end", type=int, help="End file ID range")
def main(fid: int | None = None, start: int | None = None, end: int | None = None):
    cond = NewQuestion.mold == MID
    if fid:
        cond &= NewFile.id == fid
    if start:
        cond &= NewFile.id >= start
    if end:
        cond &= NewFile.id <= end
    query = (
        NewFile.select(NewFile.id.alias("fid"), NewQuestion.id.alias("qid"))
        .join(NewQuestion, on=(NewFile.id == NewQuestion.fid))
        .where(cond)
    )
    with pw_db.allow_sync():
        tasks = []
        for row in query.execute():
            tasks.append((row.fid, row.newquestion.qid))
    workbook = Workbook()
    sheet = workbook.active
    sheet.append(["fileid", "url", "public_url", "desc"])
    for items in run_by_batch(find_diff_res, tasks):
        for item in items:
            if not item:
                continue
            logging.info(f"file id: {item.fid}, {item.desc}")
            sheet.append(item.to_line())

    with tempfile.NamedTemporaryFile(prefix="csc-market-diff-res-", suffix=".xlsx") as tmp_fp:
        excel_path = tmp_fp.name
        workbook.save(excel_path)
        FMUploader().upload(Path(excel_path))


BOND_CODE = "债券代码"
BOND_NAME = "债券简称"
R_BOND_CODE_SUFFIX = re.compile(r"\.(sh|sz|ib)", re.IGNORECASE)

VOLUME_SCALE = {
    re.compile("kw|千万", re.IGNORECASE): 1000,
    re.compile("e|亿", re.IGNORECASE): 10000,
    re.compile("\b(w|万)\b", re.IGNORECASE): 1,
}

ENUM_DEFAULT_VALUE = {
    "报价方向": "ofr",
    "bid价格类型": "5-意向",
    "ofr价格类型": "5-意向",
    "bid是否请示": "否",
    "ofr是否请示": "否",
}
P_NULL_VALUE = re.compile("[-*]|bid|ofr", re.IGNORECASE)
P_NOT_NUM = re.compile(r"[^\d.]")


def compare_number_field(name, value1, value2):
    if value1 and value2:
        value1 = clean_txt(value1.get("text") or "")
        value2 = clean_txt(value2.get("text") or "")
        if (value1 == value2) or (P_NOT_NUM.sub("", value1) == P_NOT_NUM.sub("", value2)):
            return True
        # 根据单位计算真实值再比较
        for pattern, scale in VOLUME_SCALE.items():
            if pattern.search(value1) or pattern.search(value2):
                num_value1 = (
                    Decimal(P_NOT_NUM.sub("", value1)) * scale
                    if pattern.search(value1)
                    else Decimal(P_NOT_NUM.sub("", value1))
                )
                num_value2 = (
                    Decimal(P_NOT_NUM.sub("", value2)) * scale
                    if pattern.search(value2)
                    else Decimal(P_NOT_NUM.sub("", value2))
                )
                return num_value1 == num_value2
        return False
    else:
        # 处理默认值情况
        not_null_value = (value1 or value2).get("text")
        if not_null_value and P_NULL_VALUE.sub("", clean_txt(not_null_value)):
            return False
    return True


def compare_enum_field(name, value1, value2):
    if value1 and value2:
        if value1.get("choices") and value2.get("choices"):
            if value1.get("choices")[0] == value2.get("choices")[0]:
                return True
            elif name == "报价方向" and value1.get("choices")[0] == "unknown" and value2.get("choices")[0] == "ofr":
                return True
            else:
                return False
        elif value1.get("text") and value2.get("text"):
            return value1.get("text").lower() == value2.get("text").lower()
        return True
    else:
        # 处理默认值和None情况
        not_null_value = value1 or value2
        if enum_value := not_null_value.get("choices"):
            if (not enum_value) or (enum_value[0] == ENUM_DEFAULT_VALUE[name]):
                return True
        return False


async def find_json_diff(fid, file1, file2) -> DiffRes | None:
    cond = NewQuestion.mold == MID
    cond &= NewFile.id == fid
    query = (
        NewFile.select(NewFile.id.alias("fid"), NewFile.tree_id.alias("tree_id"), NewQuestion.id.alias("qid"))
        .join(NewQuestion, on=(NewFile.id == NewQuestion.fid))
        .where(cond)
    )
    res = await pw_db.first(query)
    url = gen_url(res.fid, res.tree_id, res.newquestion.qid)
    public_url = gen_public_url(res.fid, res.tree_id, res.newquestion.qid)

    if not os.path.exists(file2):
        return DiffRes(False, fid, url, public_url, "缺少正则答案")
    with open(file1, "r", encoding="utf-8") as f1:
        data1 = json.load(f1)
    with open(file2, "r", encoding="utf-8") as f2:
        data2 = json.load(f2)
    # 比较两个 JSON 对象
    list1 = data1.get("报价信息", [])
    list2 = data2.get("报价信息", [])
    desc = []
    if len(list1) != len(list2):
        return DiffRes(False, fid, url, public_url, "答案数量不一致")
    for idx, item in enumerate(zip(list1, list2)):
        item1 = item[0]
        item2 = item[1]
        # 比较债券和简称:
        if (
            R_BOND_CODE_SUFFIX.sub("", ((item1.get(BOND_CODE) or {}).get("text", "") or ""))
            != R_BOND_CODE_SUFFIX.sub("", item2[BOND_CODE]["text"])
            and ((item1.get(BOND_NAME) or {}).get("text", "") or "") != item2[BOND_NAME]["text"]
        ):
            desc.append("债券代码或简称不一致")
        # 比较枚举字段
        for field in ["报价方向", "bid价格类型", "ofr价格类型", "bid是否请示", "ofr是否请示"]:
            if (item1[field] or item2[field]) and not compare_enum_field(field, item1[field], item2[field]):
                desc.append(f"第{idx + 1}个答案{field}字段不一致")
        # 比较数量字段
        for field in ["bid价格", "bid数量", "ofr价格", "ofr数量"]:
            if (item1[field] or item2[field]) and not compare_number_field(field, item1[field], item2[field]):
                desc.append(f"第{idx + 1}个答案{field}字段不一致")
    if desc:
        return DiffRes(False, fid, url, public_url, "\n\n".join(desc))
    return DiffRes(True, fid, url, public_url, "正确")


async def diff_json():
    export_folder = target_path("data/csc_output")
    parsed_folder = target_path("data/csc_regex_parsed")
    workbook = Workbook()
    sheet = workbook.active
    sheet.append(["fileid", "url", "public_url", "desc"])
    tmp_res = []
    for root, _, files in os.walk(export_folder):
        for export_file in files:
            if os.path.splitext(export_file)[1] == ".json":
                fid = int(export_file.split("_")[-1].replace(".json", ""))
                diff_res = await find_json_diff(fid, f"{root}/{export_file}", f"{parsed_folder}/{export_file}")
                sheet.append(diff_res.to_line())
                tmp_res.append(diff_res.to_line())
    with tempfile.NamedTemporaryFile(prefix="csc-market-diff-res-", suffix=".xlsx", delete=False) as tmp_fp:
        excel_path = tmp_fp.name
        workbook.save(excel_path)
        # FMUploader().upload(Path(excel_path))


if __name__ == "__main__":
    main()
