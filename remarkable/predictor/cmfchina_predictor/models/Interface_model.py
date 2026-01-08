import base64
import json
import logging
import time

import httpx

from remarkable import config
from remarkable.common.exceptions import CmfChinaAPIError
from remarkable.common.storage import localstorage
from remarkable.db import pw_db
from remarkable.models.cmf_china import CmfChinaEmailFileInfo, CmfModel
from remarkable.models.new_file import NewFile
from remarkable.predictor.cmfchina_predictor.models.serialization_answer import (
    BoxesModel,
    ExcelFieldModel,
    FieldAnswerModel,
    GroupFieldAnswerModel,
    OriginAnswerModel,
)
from remarkable.predictor.models.base_model import BaseModel
from remarkable.predictor.mold_schema import SchemaItem
from remarkable.predictor.schema_answer import CmfChinaOutlineResult, CmfExcelResult, PredictorResultGroup
from remarkable.schema.special_answer import Box

logger = logging.getLogger(__name__)


def predict_answer_by_interface(url: str, file_path_dict: dict, model_id: str, data: str):
    if not url:
        raise Exception(f"Model<{model_id}> address is empty")
    timeout = config.get_config("cmfchina.model_interface_timeout") or 600
    with httpx.Client(verify=False, timeout=timeout, transport=httpx.HTTPTransport(retries=3)) as client:
        # 示例
        # response = requests.post(url, files=[
        #     ('files', ('测试样本.xlsx', open(file_path1, 'rb'), 'application/pdf')),
        #     ('files', ('节假日1.pdf', open(file_path1, 'rb'), 'application/pdf')),
        # ],data={'type': 'pension_ranking', 'data': ''})
        files = [
            ("files", (name, localstorage.read_file(file_path), "application/pdf"))
            for name, file_path in file_path_dict.items()
        ]
        start_time = time.time()
        try:
            resp = client.post(url=url, files=files, data={"type": f"{model_id}", "data": data})
            if resp.status_code == 200:
                data = resp.json()
                if data.get("status") != "success":
                    raise Exception(data.get("info"))
                return data
            raise Exception
        except httpx.TimeoutException as exp:
            logger.exception(f"CMF China predict interface request timeout, url: {url}, error: {exp}")
            raise CmfChinaAPIError from exp
        except Exception as exp:
            logging.exception(f"CMF China predict failed, url: {url}, error: {exp}")
            raise CmfChinaAPIError from exp
        finally:
            elapsed_time = time.time() - start_time
            logger.info(f"CMF China predict the time taken for interface requests: {elapsed_time:.2f} second")


class InterfaceModel(BaseModel):
    @property
    def file_name(self):
        return self.predictor.prophet.metadata.get("file_name") or ""

    @property
    def pdf_path(self):
        return self.predictor.prophet.metadata.get("pdf_path") or ""

    @property
    def excel_path(self):
        return self.predictor.prophet.metadata.get("excel_path") or ""

    @property
    def model_name(self):
        return self.predictor.prophet.metadata.get("model_name") or ""

    @property
    def model_id(self):
        return self.predictor.prophet.metadata["model_id"]

    @property
    def url(self):
        return self.predictor.prophet.metadata.get("model_url") or ""

    def predict_schema_answer(self, elements):
        if not self.url:
            logger.error("Cmf china custom model url is empty")
            return []
        logger.info(f"Start interface model predict: {self.url}")

        if not self.file_name or not (self.pdf_path or self.excel_path):
            return []
        data = ""
        fid = self.predictor.prophet.metadata.get("fid")
        if fid:
            with pw_db.allow_sync():
                if (
                    info_data := CmfChinaEmailFileInfo.select(
                        CmfChinaEmailFileInfo.host,
                        CmfChinaEmailFileInfo.account,
                        CmfChinaEmailFileInfo.sent_at,
                        CmfChinaEmailFileInfo.subject,
                        CmfChinaEmailFileInfo.from_.alias("from"),
                        CmfChinaEmailFileInfo.to,
                        CmfChinaEmailFileInfo.cc,
                    )
                    .where(CmfChinaEmailFileInfo.fid == fid)
                    .dicts()
                    .first()
                ):
                    data = json.dumps(info_data)
        file_path_dict = {self.file_name: self.pdf_path or self.excel_path}
        original_answer = OriginAnswerModel.model_validate(
            predict_answer_by_interface(self.url, file_path_dict, self.model_id, data)
        )
        with pw_db.allow_sync():
            metadata = {"schema_aliases": original_answer.schema_aliases}
            CmfModel.update(metadata=metadata).where(CmfModel.id == self.model_id).execute()
            excel_base64 = None
            for base64_data in original_answer.excel_base64:
                if base64_data:
                    excel_base64 = base64_data
                    break

            if fid and excel_base64:
                file = NewFile.select().where(NewFile.id == fid).first()
                if file.is_excel:
                    logger.info(f"update excel file: {fid}")
                    localstorage.write_file(file.path(), base64.b64decode(excel_base64))
        res = self.convert_answer(original_answer)
        logger.info(f"End interface model predict: {self.url}")
        return res

    def get_schema_by_alias(self, schema: SchemaItem, alias: str):
        for sub_schema in schema.children:
            if sub_schema.alias == alias:
                return sub_schema
            if sub_schema.children:
                if temp_schema := self.get_schema_by_alias(sub_schema, alias):
                    return temp_schema
        return None

    def convert_box(self, page_index: int, original_box: Box):
        size = self.pdfinsight.data.get("pages", {}).get(str(page_index), {}).get("size")
        if size and len(size) == 2:
            return [
                size[0] * original_box.box_left,
                size[1] * original_box.box_top,
                size[0] * original_box.box_right,
                size[1] * original_box.box_bottom,
            ]
        return original_box.outline

    def convert_answer(self, res):
        def build_answer(filed: FieldAnswerModel, parent_schema: SchemaItem):
            if not parent_schema:
                return None
            schema = self.get_schema_by_alias(parent_schema, filed.key)
            if not schema:
                return None
            results = []
            if self.excel_path and isinstance(filed.position, ExcelFieldModel):
                results = [
                    CmfExcelResult(
                        {"col": filed.position.col, "row": filed.position.row}, filed.position.sheet_name, filed.text
                    )
                ]
            elif self.pdf_path and isinstance(filed.position, BoxesModel):
                page_box = []
                for index, box in enumerate(filed.position.boxes):
                    page_box.append(
                        {
                            "text": filed.text if index == 0 else "",
                            "page": box.page,
                            "outline": self.convert_box(box.page, box.box),
                        }
                    )
                results = [
                    CmfChinaOutlineResult(
                        page_box,
                        filed.text,
                    )
                ]
            return self.create_result(results, schema=schema, score=filed.probability)

        if res.pdf_type != self.model_id:
            logger.error(f"Cmf china model id not match, expect: {self.model_id}, actual: {res.pdf_type}")
            return []
        file_groups_answer_results = []
        for key, file in res.files.items():
            if not (schema := self.get_schema_by_alias(self.schema, key)):
                continue
            file_groups = []
            for fields in file.file_groups:
                file_answer_results = []
                for filed in fields:
                    if not (sub_schema := self.get_schema_by_alias(schema, filed.key)):
                        continue
                    if isinstance(filed, FieldAnswerModel):
                        if filed_answer := build_answer(filed, schema):
                            file_answer_results.append(filed_answer)
                    elif isinstance(filed, GroupFieldAnswerModel):
                        group = []
                        for group_list in filed.group_list:
                            sub_group = []
                            for sub_field in group_list:
                                if isinstance(sub_field, FieldAnswerModel):
                                    if filed_answer := build_answer(sub_field, sub_schema):
                                        sub_group.append(filed_answer)
                            group.append(sub_group)
                        group_answer = PredictorResultGroup(group, schema=sub_schema)
                        file_answer_results.append(group_answer)
                if not file_answer_results:
                    continue
                file_groups.append(file_answer_results)
            if schema.name:
                file_groups_answer = PredictorResultGroup(
                    file_groups,
                    schema=schema,
                )
                file_groups_answer_results.append(file_groups_answer)
        return file_groups_answer_results
