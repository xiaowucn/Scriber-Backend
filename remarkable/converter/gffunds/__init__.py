import copy
import json
import logging
import os
import platform
import re
import tempfile
from collections import defaultdict
from dataclasses import asdict
from datetime import datetime
from pathlib import Path

import httpx
import oracledb
import pandas as pd

from remarkable import config
from remarkable.answer.reader import AnswerReader
from remarkable.common.constants import TableType
from remarkable.common.pattern import PatternCollection
from remarkable.common.storage import localstorage
from remarkable.common.util import clean_txt
from remarkable.converter import AnswerWorkShop, SimpleJSONConverter
from remarkable.converter.gffunds.post_struct import PostField
from remarkable.converter.gffunds.table_struct import (
    TReportResultOut,
    TReportTable,
    TReportTableExtend,
)
from remarkable.db import pw_db
from remarkable.infrastructure.mattermost import MMPoster
from remarkable.models.new_file import NewFile
from remarkable.models.new_user import NewAdminUser
from remarkable.optools.fm_upload import FMUploader
from remarkable.pdfinsight.parser import parse_table
from remarkable.pdfinsight.reader import PdfinsightReader
from remarkable.predictor import load_prophet_config
from remarkable.predictor.gffunds_poc_predictor.models.parse_money import ParseMoney
from remarkable.pw_models.model import NewMold
from remarkable.security.crypto_util import rsa_encrypt

DATE_PATTERN = re.compile(r"(?P<year>\d+)年(?P<month>\d+)月(?P<day>\d+)日")

logger = logging.getLogger(__name__)


P_SPECIAL_CELL_TEXT_REG = PatternCollection([r"^所有外币相对人民币(升|贬)值\s+\d+%$"])


class GFFundsWorkShop(AnswerWorkShop):
    def __init__(self, metadata, debug=False):
        super().__init__(metadata, debug)
        self.pdfinsight = PdfinsightReader(localstorage.mount(self.file.pdfinsight_path()), include_special_table=True)
        self.convert_answer = SimpleJSONConverter(self.answer).convert(item_handler=lambda x: x.origin_text)
        self.report_period = self.extract_report_period()
        self.report_name = self.convert_answer.get("报告名称") or self.file.name

    @property
    async def model(self):
        if self.file.molds and (mold := await NewMold.find_by_id(self.file.molds[0])):
            return mold
        raise ValueError(f"文件[{self.file.id}]:未配置模型，请检查配置")

    @property
    async def report_type(self):
        model = await self.model
        if model.name == "广发基金季报1":
            return "季报"
        elif model.name == "广发基金年中报":
            return "年报"
        elif model.name == "广发招募说明书":
            return "招募说明书"
        elif model.name.startswith("广发业务申请表"):
            return "申请表"
        else:
            raise ValueError(f"文件[{self.file.id}]:模型配置错误，请检查配置")

    @staticmethod
    def _db_connection():
        instant_client_dir = None
        if platform.system() == "Darwin":
            instant_client_dir = None  # "/opt/oracle/client_11_2"
        if os.getenv("LD_LIBRARY_PATH") is None and instant_client_dir is None:
            raise OSError("please install oracle client_11_2 or high version and set LD_LIBRARY_PATH ENVIRONMENT")
        oracledb.init_oracle_client(lib_dir=instant_client_dir)
        user = config.get_config("customer_settings.oracle.user", "system")
        dsn = config.get_config("customer_settings.oracle.dsn", "localhost/XE")
        password = config.get_config("customer_settings.oracle.password", "oracle")
        connection = oracledb.connect(user=user, password=password, dsn=dsn)
        return connection

    async def work(self):
        try:
            mold_obj = await self.model
        except ValueError as e:
            logger.exception(e)
            return
        if mold_obj.name not in config.get_config("prophet.config_map"):
            logger.warning(f"模型:{mold_obj.name}为非内置模型，无需处理")
            return
        ignore_insert_schema = config.get_config("customer_settings.ignore_insert_schema")
        # 更新金额小写的值
        self._update_answer(mold_obj)
        if mold_obj.name not in ignore_insert_schema:
            report_type = await self.report_type
            if report_type in ["年报", "季报"] and (report_name := self.convert_answer["报告名称"]):
                self.convert_answer["报告名称"] = clean_txt(report_name)
            tables = copy.deepcopy(self.pdfinsight.table_dict)
            current_time = datetime.now()
            base_info = {
                "file_id": self.file.id,
                "vc_seq_no": self.project.id,
                "project_name": self.project.name,
                "dt_report_date": self.report_period,
                "vc_report_type": report_type,
                "vc_report_name": self.report_name,
                "dt_insert_time": current_time,
                "dt_update_time": current_time,
            }
            if config.get_config("customer_settings.export_to_csv"):
                return await self.export_to_csv(tables, base_info)
            table_data, extend_row_dict = self.construct_table_data(tables, base_info)
            connection = self._db_connection()
            try:
                with connection.cursor() as cursor:
                    self.clear_data(cursor)
                    await self.insert_report_to_db(cursor, current_time)
                    self.insert_db_table_data(cursor, table_data)
                    if extend_row_dict:
                        self.insert_extend_db_table(cursor, extend_row_dict)
                    connection.commit()
                    logger.info("季报/年报数据插入数据库成功，文件id：%s", self.file.id)
                    inserted = True
            except oracledb.Error as error:
                connection.rollback()
                logger.exception(f"insert data error: {error}")
                inserted = False
            if db_notify_url := config.get_config("customer_settings.db_notify_url"):
                project_file_cnt = await pw_db.count(NewFile.select().where(NewFile.pid == self.project.id))
                user = await NewAdminUser.get_by_id(self.project.uid, fields=("name",))
                data = {
                    "fileId": str(self.file.id),
                    "fileName": self.file.name,
                    "projectName": self.project.name,
                    "documentSum": project_file_cnt,
                    "saveSuccess": inserted,
                    "noticePersons": [f"{user.name}"] if user else [],
                }
                await self.post_request(db_notify_url, data=data)
        else:
            msg = json.dumps(
                PostField.build_request_body(self.file, self.convert_answer, mold_obj.name), ensure_ascii=False
            )
            encrypted_msg = rsa_encrypt(msg, config.get_config("customer_settings.rsa_public_key"), encoding="GBK")
            logger.debug(f"msg: {msg}")
            logger.debug(f"encrypted_msg: {encrypted_msg}")
            if config.get_config("customer_settings.mm_notify"):
                attachments = [
                    {
                        "fallback": "test",
                        "color": "#FF8000",
                        "author_name": "Scriber",
                        "text": f"```json\n{msg}\n```",
                        "title": "广发基金申请表json数据",
                    }
                ]
                info = (
                    f"[广发基金申请表文件: {self.file.name}]"
                    f"(http://{config.get_config('web.domain')}/#/search?fileid={self.file.id}) 信息提取完成"
                )
                return await MMPoster.send(msg=info, error=False, attachments=attachments)
            if zx_system_url := config.get_config("customer_settings.system_url"):
                await self.post_request(zx_system_url, params={"version": 1.0, "encmsg": encrypted_msg})

    def extract_report_period(self):
        report_date_str = self.convert_answer.get("报告日期") or ""
        if date_search := DATE_PATTERN.search(report_date_str):
            return datetime.strptime(
                f"{date_search.group('year')}-{date_search.group('month')}-{date_search.group('day')}", "%Y-%m-%d"
            )
        return None

    async def export_to_csv(self, tables, base_info):
        tables_list = []
        for table in sorted(set(tables.values()), key=lambda x: x.index):
            table_rows = self.table_rows(table)
            for row_idx, row in enumerate(table_rows.values()):
                column = 0
                field = {**base_info, "l_table_no": table.index, "l_table_line": row_idx}
                for cell in row:
                    self.extract_cell_text(cell, column, field)
                    column += 1
                tables_list.append(field)
        data_frame = pd.DataFrame.from_dict(tables_list)
        with tempfile.NamedTemporaryFile(suffix=".csv", dir=config.get_config("web.tmp_dir")) as f:
            data_frame.to_csv(f.name)
            downlaod_url, expire_seconds = FMUploader().upload(Path(f.name))
            await MMPoster.send(
                msg=f"文件{self.file.id}表格内字段csv解析结果: {downlaod_url=} {expire_seconds=}", error=False
            )

    def construct_table_data(self, tables, base_info):
        table_data = []
        extend_row_dict = defaultdict(dict)
        for table in sorted(set(tables.values()), key=lambda x: x.index):
            table_rows = self.table_rows(table)
            for row_idx, row in enumerate(table_rows.values()):
                column = 0
                insert_ext_table = False
                field = {**base_info, "l_table_no": table.index, "l_table_line": row_idx}
                for cell in row:
                    self.extract_cell_text(cell, column, field)
                    column += 1
                    if cell["text"] and len(cell["text"].encode("utf-8")) >= 4000:
                        insert_ext_table = True
                row_data = TReportTable(**field)
                table_data.append(asdict(row_data))
                if insert_ext_table:
                    row_info, key = self.extract_extend_row_info(base_info, row, row_idx, table)
                    extend_row_dict[key].update(row_info)
        return table_data, extend_row_dict

    def clear_data(self, cursor):
        for table in (TReportTable, TReportResultOut):
            cursor.execute(table.delete_with_fid(self.file.id))

    def table_rows(self, table):
        table_rows = defaultdict(list)
        for cell_idx, cell_value in table.cells.items():
            row_num = cell_idx.split("_")[0]
            cell_value.update({"cell_idx": cell_idx})
            if row_num not in table_rows:
                table_rows[row_num] = [cell_value]
            else:
                table_rows[row_num].append(cell_value)
            table_rows[row_num].sort(key=self.sort_cells)
        return dict(sorted(table_rows.items(), key=lambda d: int(d[0])))

    async def extract_report_answer(self, current_time):
        base_info = {
            "l_file_id": self.file.id,
            "vc_seq_no": self.project.id,
            "vc_fund_code": self.convert_answer.get("基金代码"),
            "dt_report_date": self.report_period,
            "vc_report_type": await self.report_type,
            "vc_report_name": self.report_name,
            "dt_insert_time": current_time,
            "dt_update_time": current_time,
        }
        normal_results = []
        combination_results = []
        for key, value in self.convert_answer.items():
            is_clob = 0
            clob_value = None
            if isinstance(value, list):
                combination_results.append(self.extract_combination_answer(key, value, base_info))
            else:
                if value and len(value.encode("utf-8")) >= 4000:
                    is_clob = 1
                    clob_value = value
                    value = None
                result = TReportResultOut(
                    **base_info, vc_key=key, vc_value=value, l_is_clob=is_clob, clob_value=clob_value
                ).to_dict()
                normal_results.append(result)
        return combination_results, normal_results

    async def insert_report_to_db(self, cursor, current_time):
        combination_answer, normal_answer = await self.extract_report_answer(current_time)
        insert_sql = TReportResultOut.insert_sql()
        returning_sql = TReportResultOut.returning_pk_sql()
        cursor.executemany(insert_sql, normal_answer)
        for answer in combination_answer:
            if isinstance(answer, dict):
                cursor.execute(insert_sql, answer)
            else:
                pk = cursor.var(str)
                parent = answer[0]
                parent.update({"pk": pk})
                cursor.execute(returning_sql, parent)
                self.update_parent_id(int(pk.getvalue()[0]), answer[1:])
                cursor.executemany(insert_sql, answer[1:])

    def _update_answer(self, mold: NewMold):
        def format_num_str(num_str):
            try:
                return "{:.2f}".format(float(num_str))
            except ValueError:
                logger.error("Invalid number str: %s", num_str)
                return num_str

        convert_answer = self.convert_answer
        path = "金(份)额小写"
        row_pattern, content_pattern = self._get_pattern(mold, path)
        if convert_answer.get(path):
            # 获取答案所在的outline
            box = list(AnswerReader(self.answer).find_nodes([path]))[0].data.data[0]["boxes"][0]["box"]
            # 获取答案所在的元素块
            elements = self.pdfinsight.find_elements_by_outline(page=0, outline=box)
            if not elements:
                return None
            # 识别为段落的不做处理
            tables = [el[1] for el in elements if el[0] == "TABLE"]
            if not tables:
                return None
            # 如果为嵌套表格，那么筛选出父表格和子表格，子表格的index比父表格的大，因此取最大的就好
            element = max(tables, key=lambda x: x["index"])
            table = parse_table(element, tabletype=TableType.TUPLE.value, pdfinsight_reader=self.pdfinsight)
            # 取出元或者点所在的cell,这个点单位后面的数字要添加小数点，用来确定金额小写的准确数值
            # +----+----+----+----+----+----+----+
            # | 万 | 仟 | 佰 | 拾 | 元/点| 角 | 分 |
            # +----+----+----+----+----+----+----+
            # | 1 | 2 | 3 | 4 | 5 | 6 | 7 |
            # +----+----+----+----+----+----+----+
            decimal_point_cells = (
                table.find_cells_by_text("点")
                + table.find_cells_by_text("元")
                + table.find_cells_by_text("份")
                + table.find_cells_by_text("个")
            )
            valid_rows = ParseMoney.matched_rows(table, row_pattern)
            for valid_row in valid_rows:
                _, cells = ParseMoney.get_answer_from_merge_row(content_pattern, valid_row)
                if decimal_point_cells and cells:
                    cells = [cell for cell in cells if not cell.dummy]
                    # 点/元所在的单元格应该在数字的上方，所以他们的列相等，但是行要小于数字所在的单元格
                    # 一般
                    matches = [
                        (decimal_cell, idx)
                        for decimal_cell in decimal_point_cells
                        for idx, num_cell in enumerate(cells)
                        if num_cell.colidx == decimal_cell.colidx
                        and decimal_cell.rowidx < num_cell.rowidx <= decimal_cell.rowidx + 2
                    ]
                    if matches:
                        cell, idx = matches[0]
                        text = "".join([clean_txt(cell.text) for cell in cells])
                        # https://gitpd.paodingai.com/cheftin/docs_scriber/-/issues/1069
                        # 单元格识别的时候，没有将单元格拆开，导致idx值与真实值存在差异
                        idx += len(text) - len(cells)
                        if text[idx].isdigit():
                            convert_answer[path] = f"{text[: idx + 1]}.{text[idx + 1 :]}"
                        else:
                            convert_answer[path] = f"{text[:idx]}.{text[idx + 1 :]}"
                        break
            convert_answer[path] = format_num_str(convert_answer[path])
        return convert_answer

    @staticmethod
    def _get_pattern(mold: NewMold, path: str):
        try:
            prophet_config = load_prophet_config(mold)
        except ModuleNotFoundError as e:
            logger.info(e)
            return None, None
        for reg_config in prophet_config["predictor_options"]:
            if reg_config["path"] == [path]:
                for model in reg_config["models"]:
                    if model["name"] == "parse_money":
                        return PatternCollection(model["row_pattern"]), PatternCollection(model["content_pattern"])
        return None, None

    @staticmethod
    def update_parent_id(pk: int, data: list[dict]):
        for dic in data:
            dic["l_par_id"] = pk

    @staticmethod
    def extract_combination_answer(key, value, base_info):
        """
        仅支持二级嵌套答案
        """
        res = []
        parent = TReportResultOut(**base_info, vc_key=key, vc_value=None, l_level=1, l_leaf=0).to_dict()
        if value:
            res.append(parent)
            for idx, answer in enumerate(value, start=1):
                for k, v in answer.items():
                    l_is_clob = 0
                    clob_value = None
                    if v and len(v.encode("utf-8")) >= 4000:
                        l_is_clob = 1
                        clob_value = v
                        v = None
                    res.append(
                        TReportResultOut(
                            **base_info,
                            vc_key=f"{key}-{k}",
                            vc_value=v,
                            l_is_clob=l_is_clob,
                            clob_value=clob_value,
                            l_level=2,
                            l_block=idx,
                        ).to_dict()
                    )
            return res
        return parent

    @staticmethod
    def insert_db_table_data(cursor, table_data):
        sql = TReportTable.insert_sql()
        cursor.executemany(sql, table_data)

    @staticmethod
    def insert_extend_db_table(cursor, row_dict):
        query_condition = [row.split("|") for row in row_dict]
        query_sql = TReportTable.query_sql()
        insert_sql = TReportTableExtend.insert_sql()
        ext_buildings = []
        for params in query_condition:
            fix_params = params[:]
            fix_params[0] = datetime.strptime(fix_params[0], "%Y-%m-%d %H:%M:%S")
            cursor.execute(query_sql, fix_params)
            vc_id = cursor.fetchone()[0]
            row = row_dict.get("|".join(params)).get("|".join(params))
            row.update({"vc_id": vc_id})
            ext_building = TReportTableExtend(**row)
            ext_buildings.append(asdict(ext_building))
        cursor.executemany(insert_sql, ext_buildings)

    @staticmethod
    def sort_cells(row):
        return int(row["cell_idx"].split("_")[-1])

    def extract_cell_text(self, cell, column, field: dict):
        if cell.get("dummy", False):
            cell["text"] = ""
        if tb_merge := field.get("tb_merge"):
            if cell.get("dummy", False):
                field["tb_merge"] = f"{tb_merge},{cell['cell_idx']}"
        else:
            field["tb_merge"] = cell["cell_idx"] if cell.get("dummy", False) else None
        text = self.remove_special_text_spaces(self.truncate_string(cell["text"]))
        text = re.sub(r"[\n\r]", "", text)
        field.update({f"col{column}": text})

    @staticmethod
    def remove_special_text_spaces(text):
        if P_SPECIAL_CELL_TEXT_REG.nexts(text):
            return clean_txt(text)
        return text

    @staticmethod
    def truncate_string(input_string, max_bytes=4000, encoding="utf-8"):
        if len(input_string.encode(encoding)) <= max_bytes:
            return input_string
        truncated_bytes = input_string.encode(encoding)[:max_bytes]
        truncated_string = truncated_bytes.decode(encoding, "ignore")
        return truncated_string

    @staticmethod
    def extract_extend_row_info(base_info, row, row_idx, table):
        column = 0
        long_text_dict = defaultdict(dict)
        key = f"{base_info['dt_report_date']}|{base_info['vc_report_type']}|{base_info['vc_report_name']}|{table.index}|{row_idx}"
        base_dict = {
            "vc_id": None,
            "dt_insert_time": base_info["dt_insert_time"],
            "dt_update_time": base_info["dt_update_time"],
        }
        long_text_dict[key].update(base_dict)
        for cell in row:
            long_text_dict[key].update(
                {
                    f"col{column}": cell["text"] if cell["text"] else None,
                }
            )
            column += 1
        return long_text_dict, key

    async def post_request(self, url, data=None, params=None):
        async with httpx.AsyncClient(verify=False, timeout=5, transport=httpx.AsyncHTTPTransport(retries=3)) as client:
            try:
                response = await client.post(
                    url=url,
                    params=params,
                    json=data,
                )
                response.raise_for_status()
                response_json = response.json()
                if response_json.get("retcode") != "0000" or response_json.get("errcode") != 0:
                    logger.error(f"file: {self.file.id} send request error: {response_json}")
            except Exception as exc:
                logger.exception(f"file: {self.file.id} send request error: {exc}")
