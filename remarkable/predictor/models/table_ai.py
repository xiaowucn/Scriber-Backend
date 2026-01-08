"""AI 表格提取模型
1. 根据配置，哪些字段调用模型提取一组值
    1.1 需要根据模型输出，判定是否是对的表格（过滤掉数据不完整的）
2. 后处理补充其他字段
3. 扩展为多组值

config:
{
    "name": "table_ai",
    "multi": True,  # 多组答案，自动扩展
    "multi_elements": True,  # 多个元素块
    "post_process": {
        "报告期": "date_from_header",  # 调用 date_from_header 方法提取
        "单位": "unit_from_table",  # 调用 unit_from_table 方法提取
    }
}
"""

import logging

from aipod.rpc.client import AIClient

from remarkable.common.constants import TableType
from remarkable.common.pattern import PatternCollection
from remarkable.config import get_config
from remarkable.pdfinsight.parser import ParsedTable, parse_table
from remarkable.predictor.common_pattern import DATE_PATTERN
from remarkable.predictor.dataset import DatasetItem
from remarkable.predictor.models.base_model import TableModel
from remarkable.predictor.schema_answer import PredictorResult, TableResult


class PostProcess:
    def __call__(self, tbl: ParsedTable, answer: dict[str, tuple[int]]) -> tuple[int]:
        raise NotImplementedError()


class FindDateFromHeader(PostProcess):
    pattern = PatternCollection(DATE_PATTERN)

    def __call__(self, tbl: ParsedTable, answer: dict[str, tuple[int]]) -> tuple[int]:
        for _, pos in answer.items():
            if not pos:
                continue
            cell = tbl.cell(*pos)
            for header_cell in cell.headers:
                if self.pattern.nexts(header_cell.text):
                    return (header_cell.original.rowidx, header_cell.original.colidx)
        return None


class AITable(TableModel):
    post_process_methods = {
        "find_date_from_header": FindDateFromHeader(),
    }

    def __init__(self, options, schema, predictor=None):
        super(AITable, self).__init__(options, schema, predictor=predictor)
        model_address = get_config("ai.table_extract.address")
        if not model_address:
            raise Exception("need ai.table_extract.address")
        self.client = AIClient(address=model_address)

    @property
    def multi(self):
        return self.get_config("multi", True)

    @property
    def post_process(self):
        return self.get_config("post_process", {})

    def ai_columns(self):
        """
        bot_keys 与 columns 不一致的地方在于：
            训练时用的是数值的叶子节点 `流动资产-数值`，而 columns 中叫 `流动资产`
        """
        bot_keys, columns = [], []
        for col in self.columns:
            if col in self.post_process:
                continue
            col_schema = self.predictor.parent.find_child_schema(col)
            if col_schema.is_leaf:
                columns.append(col)
                bot_keys.append(col)
            elif col_schema.is_amount:
                columns.append(col)
                bot_keys.append(f"{col}-数值")
        return bot_keys, columns

    def train(self, dataset: list[DatasetItem], **kwargs):
        return

    def extract_feature(self, elements, answer):
        return None

    def predict_schema_answer(self, elements) -> list[dict[str, list[PredictorResult]]]:
        answers = []
        tbls = []
        parsed_tbls = []
        sylls = []
        top_key = self.predictor.config["path"]
        elements = self.revise_elements(elements)

        for element in elements:
            if element["class"] != "TABLE":
                continue
            syll = [t["title"] for t in self.pdfinsight.find_syllabuses_by_index(element["index"])]
            tbls.append(element)
            parsed_tbls.append(parse_table(element, tabletype=TableType.TUPLE.value, pdfinsight_reader=self.pdfinsight))
            sylls.append(syll)

        # 调用模型
        bot_keys, ai_columns = self.ai_columns()
        logging.debug(f"call table ai service for predict {top_key}{bot_keys}")
        all_result = self.client.predict(tbls=tbls, top_key=top_key, bot_keys=bot_keys, sylls=sylls, action="first")
        for tbl, res in zip(parsed_tbls, all_result):
            if not res or not any(res):
                continue
            one_group = {k: tuple(v) if v else None for k, v in zip(ai_columns, res)}

            # 特殊字段后处理
            self.do_post_process(tbl, one_group)

            # 是否需要扩展
            if self.multi:
                all_groups = self._extend(tbl, one_group)
            else:
                all_groups = [one_group]

            # 构造答案
            for group in all_groups:
                answer = {}
                for key, cellidx in group.items():
                    if not cellidx:
                        continue
                    answer[key] = [self.create_result([TableResult(tbl.element, [tbl.cell(*cellidx)])], column=key)]
                if answer:
                    answers.append(answer)

            # 多元素块
            if answers and not self.multi_elements:
                break
        return answers

    def do_post_process(self, tbl: ParsedTable, answer: dict):
        post_process_res = {}
        for col, method_name in self.post_process.items():
            if method_name not in self.post_process_methods:
                post_process_res[col] = None
                logging.warning(f"can't find post process method: {method_name}")
            else:
                post_process_res[col] = self.post_process_methods[method_name](tbl, answer)
        answer.update(post_process_res)

    def _extend(self, tbl: ParsedTable, answer: dict) -> list[dict]:
        columns = [k for k, v in answer.items() if v]
        sample = [tuple(answer[c]) for c in columns]
        output = self.client.predict(tbls=[tbl.element], first_record=sample, action="expand")
        return [dict(zip(columns, item)) for item in output]
