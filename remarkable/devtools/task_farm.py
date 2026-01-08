import json
import logging
import os
import shutil

import requests
from farm import Farm
from invoke import task

from remarkable.devtools import sql_file_filter


class CustomFarm(Farm):
    def upload(self, src_path, tags, from_file_id=None):
        file_name = os.path.basename(src_path)
        upload_url = "%s/files" % self.api_prefix
        print("upload %s" % src_path, upload_url)
        with open(src_path, "rb") as r_f:
            if from_file_id is None:
                data = {"tags": tags, "file_name": file_name}
            else:
                data = {"tags": tags, "file_name": file_name, "from_file_id": from_file_id}
            response = requests.post(upload_url, data=data, files={"file": r_f}, cookies=self.cookies)
            if response.status_code != 200:
                raise RuntimeError(response.json())
        print("file id: %s" % response.json()["id"])
        return response.json()


@task
def uploader(_, start=0, end=0, mold=None, qstatus="2,5,10", overwrite=False):
    """上传至farm"""
    from remarkable.common.util import loop_wrapper

    loop_wrapper(_upload_to_farm)(start, end, mold=mold, qstatus=qstatus, overwrite=overwrite)


async def _upload_to_farm(start, end, mold, qstatus, overwrite):
    from remarkable.common.storage import localstorage
    from remarkable.config import get_config
    from remarkable.db import db
    from remarkable.models.new_file import NewFile
    from remarkable.pw_models.question import NewQuestion

    farm_url = get_config("dpp.farm")
    roster_url = get_config("dpp.roster")
    farm_env = get_config("dpp.farm_env", default="farm_test")
    tags = [get_config("dpp.tags.%s" % "scriber_kcb_pdf")]

    _farm = CustomFarm(farm_url, None, None, None, roster_url, farm_env=farm_env)

    if qstatus:
        qstatus = [int(i) for i in qstatus.split(",")]

    sql = """
    select id from file where pdf is not null and array_length(file.molds, 1) > 0
    """
    # todo: 必须是pdf/
    if not overwrite:  # 全量
        sql += " and file.farm_id is null"

    sql = sql_file_filter(sql, start, end, mold)
    async for (fid,) in db.iterate(db.text(sql)):
        _file = await NewFile.find_by_id(fid)
        if not _file:
            continue

        questions = await NewQuestion.find_by_fid(_file.id)
        question_statuses = [question.status for question in questions]
        if question_statuses and not set(question_statuses).intersection(set(qstatus)):
            continue

        tmp_dir = "/tmp/"
        if not os.path.exists(tmp_dir):
            os.mkdir(tmp_dir)
        clear_file = []  # 记录临时文件，最后删除
        file_path = os.path.join(tmp_dir, "_".join(map(str, [_file.id, _file.name])))
        clear_file.append(file_path)
        print("--------", _file.id, _file.name, file_path)
        data = localstorage.read_file(_file.pdf_path())
        with open(file_path, "wb") as pdf:
            pdf.write(data)

        try:
            resp = _farm.upload(file_path, tags)
            farm_id = resp["id"]
            logging.info("pdf done: %s", farm_id)
            await NewFile.update_by_pk(_file.id, farm_id=farm_id)

            # 上传pdfinsight
            insight_path = localstorage.mount(_file.pdfinsight_path())
            if insight_path and os.path.exists(insight_path):
                new_insight_path = os.path.join(tmp_dir, ".".join([os.path.basename(file_path), "interdoc"]))
                clear_file.append(new_insight_path)
                shutil.copyfile(insight_path, new_insight_path)
                resp = _farm.upload(
                    new_insight_path,
                    [get_config("dpp.tags.%s" % "hunter_json_from_scriber_kcb")],
                    from_file_id=farm_id,
                )
                logging.info("pdfinsight done: %s", resp["id"])

            # 上传标注答案
            sql = """
                select a.data as answer
                  from question as q
                  left join answer as a on q.id=a.qid and a.status=1
                  where a.data is not null and q.fid=%s and q.mold=%s, q.deleted_utc=0
                  order by a.updated_utc desc limit 1;
            """ % (
                _file.id,
                mold,
            )
            answer = await db.raw_sql(sql, "scalar")
            if not answer:
                continue
            answer_path = os.path.join(tmp_dir, ".".join([os.path.basename(file_path), "json"]))
            clear_file.append(answer_path)
            with open(answer_path, "w") as w_f:
                json.dump(answer, w_f)

            if os.path.exists(answer_path):
                resp = _farm.upload(
                    answer_path, [get_config("dpp.tags.%s" % "scriber_kcb_answer")], from_file_id=farm_id
                )
                logging.info("answer done: %s", resp["id"])

        except Exception as e:
            print(e)
        finally:
            for c_f in clear_file:
                if os.path.exists(c_f):
                    os.remove(c_f)
