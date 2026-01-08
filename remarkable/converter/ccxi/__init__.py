import logging
import re
from functools import partial

from remarkable.answer.reader import AnswerReader
from remarkable.common.exceptions import CustomError
from remarkable.common.storage import localstorage
from remarkable.common.util import box_to_outline, clean_txt
from remarkable.converter import AnswerWorkShop, SimpleJSONConverter
from remarkable.converter.utils import date_from_text
from remarkable.models.new_file import NewFile
from remarkable.pdfinsight.reader import PdfinsightReader
from remarkable.pw_models.model import NewCCXIContract, NewSpecialAnswer

p_date = re.compile(r"\d{4}[年/-]\d{1,2}[月/-]\d{1,2}[日]?")
logger = logging.getLogger(__name__)


class CCXIAnswerWorkShop(AnswerWorkShop):
    async def work(self):
        json_answer = self.ccxi_json_converter()
        await NewSpecialAnswer.update_or_create(self.question.id, NewSpecialAnswer.ANSWER_TYPE_JSON, json_answer)

    @staticmethod
    def ccxi_answer_node_to_dict(pdfinsight_reader, leaf_cols, answer_item):
        title = None
        related = []
        assert answer_item and answer_item.get("data") and answer_item["data"][0].get("boxes"), (
            "Empty data detected, please check the answer"
        )
        box = answer_item["data"][0]["boxes"][0]
        _, element = pdfinsight_reader.find_element_by_outline(box["page"], box_to_outline(box["box"]))
        if element:
            elt_syllabus_id = element.get("syllabus", -1)
            if elt_syllabus_id > 0:
                title = pdfinsight_reader.syllabus_dict[elt_syllabus_id]["title"]
        for col in leaf_cols:
            if col == answer_item["schema"]["data"]["label"]:  # skip self
                continue
            search_text = col.split("/")
            pattern_leaf_col = re.compile(r"{}".format("|".join(search_text)))
            match = pattern_leaf_col.findall(answer_item.plain_text)
            if match:
                related.append(col)

        return {"value": answer_item.plain_text, "title": title, "related": related}

    @staticmethod
    def all_leaf_cols(answer_reader):
        leaf_cols = []

        def _collect_leaf_cols(schema_dict, schema):
            for col_name, col in schema["schema"].items():
                if col["is_leaf"]:
                    leaf_cols.append(col_name)
                    continue
                _collect_leaf_cols(schema_dict, schema_dict[col["type"]])

        _collect_leaf_cols(answer_reader.schema_dict, answer_reader.main_schema)
        return leaf_cols

    def ccxi_json_converter(self):
        reader = PdfinsightReader(localstorage.mount(self.file.pdfinsight_path()))
        answer_reader = AnswerReader(self.answer)
        item_handler = partial(self.ccxi_answer_node_to_dict, reader, self.all_leaf_cols(answer_reader))
        return SimpleJSONConverter(self.answer).convert(item_handler=item_handler)


class CCXIContractConverter(CCXIAnswerWorkShop):
    @staticmethod
    def get_date_in_text(date_text):
        if p_date.search(date_text):
            date_in_text = date_from_text(date_text)
            return date_in_text
        return None

    async def work(self):
        json_answer = SimpleJSONConverter(self.answer).convert()
        date_text = clean_txt(json_answer["签订日期"] or "")
        date_in_text = self.get_date_in_text(date_text)
        if not date_in_text:
            logger.error(f"签订日期格式有误, fid:{self.file.id}")
            return
        date_signed = date_in_text.timestamp()
        json_answer["签订日期"] = date_in_text.strftime("%Y-%m-%d")

        contract = await NewCCXIContract.find_by_kwargs(qid=self.question.id)
        file = await NewFile.find_by_qid(self.question.id)
        params = {
            "qid": self.question.id,
            "fid": file.id,
            "tree_id": file.tree_id,
            "contract_no": clean_txt(json_answer.pop("合同编号") or ""),
            "company_name": json_answer.pop("企业名称"),
            "project_name": json_answer.pop("项目名称"),
            "third_party_name": json_answer.pop("合同签署第三方"),
            "area": json_answer.pop("地区"),
            "variety": json_answer.pop("品种"),
            "date_signed": date_signed,
            "meta": json_answer,
        }
        if contract:
            await contract.update_(**params)
        else:
            await NewCCXIContract.create(**params)

    @classmethod
    def check_before_submit(cls, answer):
        json_answer = SimpleJSONConverter(answer).convert()
        date_text = clean_txt(json_answer["签订日期"] or "")
        date_in_text = cls.get_date_in_text(date_text)
        if not date_in_text:
            raise CustomError('签订日期格式有误,正确格式为"2022-10-01".')
