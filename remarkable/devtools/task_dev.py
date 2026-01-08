"""
主要放一些辅助性的、运维性的命令
"""

import gzip
import json
import logging
import os
import re
from copy import deepcopy
from pathlib import Path

import openpyxl
import requests
from invoke import task

from remarkable.common.util import loop_wrapper
from remarkable.config import get_config, project_root
from remarkable.db import peewee_transaction_wrapper, pw_db
from remarkable.devtools import InvokeWrapper, _rm_file_in_deleted_tree

logger = logging.getLogger(__name__)


@task
def fetch_districts(ctx, url=""):
    """爬取中国县以上行政区信息拼成re pattern存入文件"""
    if not url:
        # from http://www.mca.gov.cn/article/sj/xzqh/2020/
        url = "http://www.mca.gov.cn/article/sj/xzqh/2020/2020/202003061536.html"
    pattern = re.compile(r">(?P<dst>[^x00-xff]*?[市省])<")
    rsp = requests.get(url, timeout=30)
    dst_path = os.path.join(ctx["project_root"], "data", "districts_cn.gz")
    if rsp.ok:
        with gzip.open(dst_path, "wt") as dst_obj:
            dst_obj.write("|".join(match.group("dst") for match in pattern.finditer(rsp.text)))
    logging.info(f"all districts were saved to {dst_path}")


@task(klass=InvokeWrapper)
async def stat_parse_time(ctx, fid=None, start=None, end=None, time_threshold=None):
    from remarkable.pw_models.model import NewTimeRecord
    from remarkable.service.statistics import get_avg_parsing_time, parsing_time_for_file

    fids = set()
    if start and end:
        for i in range(int(start), int(end) + 1):
            fids.add(str(i))
    all_time, pdfinsight_time, parser_time, prompt_time, preset_time = [], [], [], [], []
    if fid:
        fids.add(fid)
    for fid in fids:
        time_record = await NewTimeRecord.find_by_fid(fid)
        if not time_record:
            continue
        if not time_record.upload_stamp or not time_record.preset_stamp:
            continue
        parsing_time = await parsing_time_for_file(fid, time_threshold)
        if not parsing_time:
            continue
        if parsing_time.whole_process_time:
            print(parsing_time.whole_process_time)
            all_time.append(parsing_time.whole_process_time)
        pdfinsight_time.append((parsing_time.insight_parse_stamp - parsing_time.upload_stamp).total_seconds())
        parser_time.append((parsing_time.pdf_parse_stamp - parsing_time.insight_parse_stamp).total_seconds())
        if parsing_time.prompt_stamp:
            prompt_time.append((parsing_time.prompt_stamp - parsing_time.pdf_parse_stamp).total_seconds())
            preset_time.append((parsing_time.preset_stamp - parsing_time.prompt_stamp).total_seconds())
        else:
            prompt_time.append(0)
            preset_time.append((parsing_time.preset_stamp - parsing_time.pdf_parse_stamp).total_seconds())
    if not all_time:
        logging.info("文件总数为：0")
        return

    logging.info(f"文件总数为：{len(all_time)}, 文件平均解析时间为: {get_avg_parsing_time(all_time)}")
    logging.info(f"pdfinsight平均解析时间为: {get_avg_parsing_time(pdfinsight_time)}")
    logging.info(f"pdfparser平均解析时间为: {get_avg_parsing_time(parser_time)}")
    logging.info(f"初步定位平均解析时间为: {get_avg_parsing_time(prompt_time)}")
    logging.info(f"精确定位平均解析时间为: {get_avg_parsing_time(preset_time)}")


@task
def rm_file_in_deleted_tree(ctx):
    _rm_file_in_deleted_tree()


@task
def adjust_answer_outline(ctx, start=0, end=0, mold=0):
    """缩小答案外框"""
    from remarkable.answer.common import fix_answer_outline
    from remarkable.common.storage import localstorage
    from remarkable.models.new_file import NewFile
    from remarkable.pw_models.question import NewQuestion

    @loop_wrapper
    async def run(*args):
        start, end, mold = args
        questions = await NewQuestion.list_by_range(mold=mold, start=start, end=end)
        for question in questions:
            if not question.answer:
                logging.warning(f"No answer found, fid: {question.fid}, qid: {question.id}")
                continue
            logging.info(f"Resize text box size for file: {question.fid}, qid: {question.id}")
            _file = await NewFile.find_by_qid(question.id)
            pdf_path = localstorage.mount(_file.pdf_path())
            answer = fix_answer_outline(pdf_path, question.answer, remove_manual=True)
            await question.update_(answer=answer)

    run(int(start), int(end), int(mold))


@task
def reset_project_uid(ctx, pid, uid):
    """
    更改项目所属用户
    :param ctx:
    :param pid:
    :param uid:
    :return:
    """
    from remarkable.models.new_user import NewAdminUser
    from remarkable.pw_models.model import NewFileProject

    @loop_wrapper
    async def run(project_id, user_id):
        file_project = await NewFileProject.find_by_id(project_id)
        if not file_project:
            logging.warning(f"No file_project found, project_id: {project_id}")
            return
        user = await NewAdminUser.find_by_id(user_id)
        if not user:
            logging.warning(f"No user found, user_id: {user_id}")
            return

        await file_project.update_(uid=user_id)
        logging.info(f"Update user of {file_project.name} to {user.name}")

    run(int(pid), int(uid))


@task
def migrate_answers(ctx, mold_id=0, from_field="", to_field="", start=None, end=None):
    """
    用于修改schema中的字段名后,保留原标注答案
    这里没有修改question.preset_answer和question.answer，一般在修改标注答案之后会重新训练+重跑预测答案
    :param ctx:
    :param mold_id:
    :param from_field:
    :param to_field:
    :param start:
    :param end:
    :return:
    """
    from remarkable.pw_models.model import NewAnswer, NewMold
    from remarkable.pw_models.question import NewQuestion

    @loop_wrapper
    @peewee_transaction_wrapper
    async def run():
        mold = await NewMold.find_by_id(mold_id)
        # find all file
        questions = await NewQuestion.list_by_range(mold=mold_id, start=start, end=end, special_cols=["id", "fid"])
        for question in questions:
            answers = await NewAnswer.get_answers_by_qid(qid=question.id)
            # edit answer
            for answer in answers:
                answer_data = answer.data["userAnswer"]["items"]
                for item in answer_data:
                    key = item["key"]
                    if f'"{from_field}:' in key:
                        logging.info(f"{key}, changes to")
                        key = key.replace(from_field, to_field)
                        logging.info(f"{key}")
                        item["key"] = key
                        item["schema"]["data"]["label"] = "to_field"
                answer.data["schema"] = deepcopy(mold.data)
                answer.data["schema"]["version"] = mold.checksum
                await answer.update_(data=answer.data)
                logging.info(f"update answer data: {answer.qid}, file: {question.fid}")

    run()


@task
def import_cgs_dev_rules(ctx):
    """
    导入银河的研发审核规则
    :return:
    """
    from remarkable.pw_models.model import NewAuditDevRule

    @loop_wrapper
    @peewee_transaction_wrapper
    async def run():
        data_path = Path(project_root) / "remarkable/plugins/cgs/data/开发规则数据.xlsx"
        workbook = openpyxl.load_workbook(data_path, read_only=True)
        sheet = workbook.worksheets[0]
        for idx, row in enumerate(sheet.rows):
            if idx == 0:
                continue
            law_id = row[0].value
            law = row[1].value
            name = row[2].value
            rule_type = row[3].value
            content = row[4].value
            await NewAuditDevRule.create(law_id=law_id, law=law, name=name, rule_type=rule_type, content=content)

    run()


@task
def set_mold_master(ctx, mold_name, master_mold_name):
    """
    设置mold.master为master_mold
    :param ctx:
    :param mold_name: mold.name:
    :param master_mold_name: master_mold.name:
    :return:
    """
    from remarkable.pw_models.model import NewMold

    @loop_wrapper
    async def run():
        mold = await NewMold.find_by_name(mold_name)
        if not mold:
            logging.warning(f"No mold found, mold_name: {mold_name}")
            return
        master_mold = await NewMold.find_by_name(master_mold_name)
        if not master_mold:
            logging.warning(f"No master_mold found, master_mold_name: {master_mold}")
            return
        await mold.update_(master=master_mold.id)
        logging.info(f"Set mold.master = {master_mold.name} where {mold.name=}")

    run()


@task(klass=InvokeWrapper)
async def stat_mold(ctx, mold_id: int):
    """
    统计mold叶子节点的数量
    :param ctx:
    :param mold_id:
    :return:
    """
    from remarkable.predictor.mold_schema import MoldSchema
    from remarkable.pw_models.model import NewMold

    def count_sub_fields(field_type):
        total = 0
        sub_fields = schemas_map[field_type]
        for _, info in sub_fields["schema"].items():
            if info["type"] in MoldSchema.basic_types:
                total += 1
            else:
                total += count_sub_fields(info["type"])
        return total

    mold = await NewMold.find_by_id(mold_id)
    if not mold:
        logging.warning(f"No mold found, mold_name: {mold_id}")
        return
    schemas = mold.data["schemas"]
    schemas_map = {x["name"]: x for x in schemas}
    counts = count_sub_fields(mold.name)
    print(f"{mold.name} total number of fields : {counts}")


@task(klass=InvokeWrapper)
async def gen_mold_meta(ctx, start: int = None, end: int = None):
    """
    生成默认mold.meta
    """
    from remarkable.pw_models.model import NewMold

    for mold in await NewMold.list_by_range(start, end):
        logging.info(f"update default_meta for {mold.id}")
        await mold.update_default_meta()


@task(klass=InvokeWrapper)
async def modify_answer_schema(ctx, mold_id, old_name, new_name):
    """
    修改schema名称之后，修改标注答案的key
    """
    from remarkable.pw_models.model import NewAnswer, NewMold
    from remarkable.pw_models.question import NewQuestion

    # 修改mold.name通过页面接口来实现
    mold = await NewMold.find_by_id(mold_id)
    if not mold:
        logging.warning(f"No mold found, mold_id: {mold_id}")
        return

    questions = await NewQuestion.find_by_kwargs(delegate="all", mold=mold_id)
    for question in questions:
        answers = await pw_db.execute(NewAnswer.select().where(NewAnswer.qid == question.id))
        if not answers:
            continue

        for answer in answers:
            answer.data["schema"]["schemas"][0]["name"] = new_name
            answer.data["schema"]["version"] = mold.checksum
            for item in answer.data["userAnswer"]["items"]:
                item["key"] = item["key"].replace(f"{old_name}:0", f"{new_name}:0")
            logging.info(f"modify_answer_schema for {question.id}, {answer.id}")
            await pw_db.update(answer)

        await question.set_answer()


@task(klass=InvokeWrapper)
async def import_chinaamc_yx_samples(ctx, overwrite=False):
    """
    导入范文及答案
    :param ctx:
    :param overwrite:
    :return:
    """
    from remarkable.models.new_user import ADMIN
    from remarkable.pw_models.model import NewAnswer, NewFileProject, NewFileTree, NewMold
    from remarkable.pw_models.question import NewQuestion
    from remarkable.service.new_file import NewFileService
    from remarkable.service.new_file_project import NewFileProjectService
    from remarkable.worker.tasks import process_file

    samples_path = Path(f"{project_root}/data/chinaamc_yx/samples")
    project_name = get_config("chinaamc_yx.sample_project")
    project = await NewFileProject.find_by_kwargs(name=project_name)
    if project:
        if not overwrite:
            logger.info(f"{project.name} already exists")
            return
        await pw_db.delete(project)

    project = await NewFileProjectService.create(name=project_name, visible=False)
    file_tree = await NewFileTree.find_by_id(project.rtree_id)

    info = []
    for entry in samples_path.iterdir():
        if entry.suffix == ".pdf":
            filename = entry.name
            mold = await NewMold.find_by_kwargs(name=entry.stem)
            with open(entry, "rb") as fp:
                data = fp.read()

            newfile = await NewFileService.create_file(filename, data, [mold.id], project.id, file_tree.id, ADMIN.id)
            await process_file(newfile)
            logger.info(f"upload {newfile.name}")
            info.append({"fid": newfile.id, "mold": mold})

    for item in info:
        mold = item["mold"]
        question = await NewQuestion.find_by_kwargs(fid=item["fid"], mold=mold.id)
        with open(samples_path / f"{mold.name}.json") as file_obj:
            question_data = json.load(file_obj)
        await pw_db.update(question, answer=question_data["answer"])
        await NewAnswer.create(qid=question.id, data=question_data["answer"], uid=ADMIN.id)
        logger.info(f"update answer for {question.fid}")


@task(klass=InvokeWrapper)
async def modify_files_priority(ctx, priority, fids=None):
    from remarkable.models.new_file import NewFile

    cond = [NewFile.priority != priority]
    if fids is not None:
        if isinstance(fids, str):
            fids = [int(fid) for fid in fids.split() if fid.strip().isdigit()]
        elif isinstance(fids, (list, tuple)):
            fids = [int(fid) for fid in fids if str(fid).strip().isdigit()]
        else:
            fids = [int(fids)] if str(fids).strip().isdigit() else []
        if not fids:
            return
        cond.append(NewFile.id.in_(fids))
    await pw_db.execute(NewFile.update(priority=priority).where(*cond))


if __name__ == "__main__":
    import asyncio

    asyncio.run(import_chinaamc_yx_samples(""))
