import logging
import os
import random
import shutil
import subprocess

import requests

from remarkable import config
from remarkable.common.storage import localstorage
from remarkable.common.util import loop_wrapper, md5sum
from remarkable.models.new_file import NewFile
from remarkable.plugins.diff.common import utc_now
from remarkable.pw_models.model import NewDiffFile, NewDiffRecord
from remarkable.worker.app import app

from .constants import CompareStatus, DocStatus

tmp_dir = config.get_config("web.tmp_dir")
if not os.path.exists(tmp_dir):
    os.makedirs(tmp_dir)


class ConvertFailException(Exception):
    pass


class CleanUpException(Exception):
    pass


def _convert_name(name):
    """改文件名后缀为PDF, 同时将环境名如ht_作为前缀"""
    return "{}_{}.pdf".format(config.get_config("client.name"), os.path.splitext(name)[0])


@app.task
@loop_wrapper
async def doc2pdf(_file):
    pdf_hash = _file.get("pdf_hash", "")
    pdf_path = localstorage.mount(os.path.join(pdf_hash[:2], pdf_hash[2:]))
    if os.path.isfile(pdf_path) and pdf_hash == md5sum(pdf_path):
        logging.info("PDF file: %s detected, skip it", _file["id"])
        return pdf_hash

    src_fp = localstorage.mount(_file["path"])
    in_fp = _doc2pdf(tmp_dir, src_fp)
    if in_fp:
        out_fp = in_fp + ".pdf"
        pdf_hash = md5sum(out_fp)
        des_fp = localstorage.mount(os.path.join(pdf_hash[:2], pdf_hash[2:]))
        if not os.path.exists(os.path.dirname(des_fp)):
            os.makedirs(os.path.dirname(des_fp))
        if not os.path.exists(des_fp):
            shutil.move(out_fp, des_fp)
        else:
            os.remove(out_fp)
        await NewDiffFile.update_by_pk(
            _file["id"], pdf_hash=pdf_hash, status=DocStatus.CONVERTED.value, updated_utc=utc_now()
        )
        return pdf_hash

    await NewDiffFile.update_by_pk(_file["id"], status=DocStatus.FAILED_CONVERT.value, updated_utc=utc_now())
    raise ConvertFailException


def _doc2pdf(temp_dir: str, src_fp: str) -> str:
    in_fp = os.path.join(temp_dir, "{}{}".format(utc_now(), random.randint(1000, 9999)))
    shutil.copy(src_fp, in_fp)
    command = 'mono {} "{}"'.format(config.get_config("web.pdf_converter"), in_fp)
    with subprocess.Popen(command, stdout=subprocess.PIPE, stderr=subprocess.PIPE, shell=True) as cmd_process:
        out, err = cmd_process.communicate()
    os.remove(in_fp)
    if not err:
        logging.info(out)
        return in_fp
    logging.info(err)
    return ""


@app.task
@loop_wrapper
async def push2calliper(rec, cookies, inner=False):
    if rec["status"] in (CompareStatus.DONE.value, CompareStatus.COMPARING.value):
        logging.info("Diff result already exists: %s, no need to push", rec["id"])
        return

    file1 = await NewFile.find_by_id(rec["fid1"])
    if inner:
        file2 = await NewFile.find_by_id(rec["fid2"])
    else:
        file2 = await NewDiffFile.find_by_id(rec["fid2"])

    calliper_url = "{}/api/v1/compare".format(config.get_config("diff.calliper_domain"))
    querystring = {
        "callback": "http://{}/api/v1/plugins/diff/{}/status".format(config.get_config("web.domain"), rec["id"])
    }
    files = {
        "file1": (
            _convert_name(file1.name),
            open(localstorage.mount(file1.pdf_path()), "rb"),
        ),
        "file2": (
            _convert_name(file2.name),
            open(localstorage.mount(file2.pdf_path()), "rb"),
        ),
    }
    try:
        rsp = requests.post(calliper_url, params=querystring, files=files, cookies=cookies, timeout=(3, 5))
    except requests.exceptions.RequestException as e:
        logging.error("push files to calliper failed: %s", e)
        await NewDiffRecord.update_by_pk(
            rec["id"],
            name1=file1.name,
            name2=file2.name,
            status=CompareStatus.NET_PROBLEM.value,
            updated_utc=utc_now(),
        )
    else:
        if rsp.status_code == 200 and rsp.json().get("status") == "ok":
            rsp_data = rsp.json().get("data")
            await NewDiffRecord.update_by_pk(
                rec["id"],
                cmp_id=rsp_data["id"],
                name1=file1.name,
                name2=file2.name,
                dst_fid1=rsp_data["file1_id"],
                dst_fid2=rsp_data["file2_id"],
                status=CompareStatus.COMPARING.value,
                updated_utc=utc_now(),
            )
            logging.info("push files to calliper success: %s", rsp_data)
        else:
            logging.error("push files to calliper failed")
            await NewDiffRecord.update_by_pk(
                rec["id"],
                name1=file1.name,
                name2=file2.name,
                status=CompareStatus.REMOTE_ERROR.value,
                updated_utc=utc_now(),
            )


@app.task(autoretry_for=(CleanUpException,), retry_kwargs={"max_retries": 1})
@loop_wrapper
async def clean_up(rec):
    """
    任务超过3min没有接收到callback信息, 一般可以认为该任务失败, 改状态标记为超时
    TODO: 超时的记录直接删除?
    """
    diff_rec = await NewDiffRecord.find_by_kwargs(id=rec["id"])
    if diff_rec.status != CompareStatus.DONE.value:
        if utc_now() - diff_rec.created_utc < 150:
            raise CleanUpException("Just a hack hooks, no need to care it.")
        logging.warning("Compare task: %s timeout, will be marked as timeout stat.", rec["id"])
        await NewDiffRecord.update_by_pk(rec["id"], status=CompareStatus.TIMEOUT.value, updated_utc=utc_now())
