import logging
import re
from collections import Counter
from functools import cached_property

from remarkable.common.constants import TableType
from remarkable.common.pattern import PatternCollection
from remarkable.common.util import clean_txt, index_in_space_string
from remarkable.pdfinsight.parser import parse_table
from remarkable.predictor.eltype import ElementClassifier, ElementType
from remarkable.predictor.models.base_model import BaseModel
from remarkable.predictor.models.cell_partial_text import CellPartialText, KvPartialText
from remarkable.predictor.models.partial_text import PartialText
from remarkable.predictor.models.table_row import TableRow
from remarkable.predictor.models.table_tuple import TupleTable
from remarkable.predictor.mold_schema import SchemaItem
from remarkable.predictor.schema_answer import CharResult, PredictorResult

logger = logging.getLogger(__name__)


class AutoModel(BaseModel):
    """
    AutoModel is a model that can predict answer bade on the element type.
    """

    filter_elements_by_target = True

    def __init__(self, options: dict, schema: SchemaItem, predictor):
        super().__init__(options, schema, predictor=predictor)
        # auto_model 的 sub_primary_key 是默认配置为了所有的columns, 见SchemaPredictor.sub_primary_key
        self.ignore_case = self.get_config("ignore_case", True)
        self.pattern_flags = re.I if self.ignore_case else 0
        self.anchor_regs = PatternCollection(self.get_config("anchor_regs", []), self.pattern_flags)
        self.cnt_of_anchor_elts = int(self.get_config("cnt_of_anchor_elts", 1))

    @property
    def width_from_all_rows(self):
        return self.get_config("width_from_all_rows", False)  # 默认取表格第一行宽度, 为True时取最宽的行

    @cached_property
    def models(self) -> dict[ElementType, BaseModel]:
        from remarkable.predictor.predictor import predictor_models

        models = {
            ElementType.PARAGRAPH: PartialText,
            ElementType.TABLE_TUPLE: TupleTable,
            ElementType.TABLE_KV: KvPartialText,
            ElementType.TABLE_ROW: TableRow,
            ElementType.TABLE_ONE_COL: CellPartialText,
        }
        # 允许用户自定义自动提取模型，如：
        # custom_models:
        #   table_kv: table_kv  # 用 table_kv 模型提取表格键值对而不是默认的 kv_partial_text 模型
        custom_models: dict[str, str] = self.get_config("custom_models", {})
        assert isinstance(custom_models, dict), '"custom_models" must be a Dict[str, str].'
        for etype, model_name in custom_models.items():
            if not model_name:
                # 如果模型名为空，则不使用该模型
                models.pop(ElementType.phrase_to_enum(etype), None)
                continue
            if model_name not in predictor_models:
                raise ValueError(f'"{model_name}" is not a valid model name.')
            models[ElementType.phrase_to_enum(etype)] = predictor_models[model_name]
        return {t: clz(self._options, self.schema, predictor=self.predictor) for t, clz in models.items()}

    def patterns(self, column=None):
        custom_regs = self.get_config("custom_regs", [])
        if isinstance(custom_regs, list):
            return PatternCollection(custom_regs, self.pattern_flags)
        if isinstance(custom_regs, dict) and column:
            column_patterns = custom_regs.get(column, [])
            return PatternCollection(column_patterns, self.pattern_flags)
        return PatternCollection([], self.pattern_flags)

    def train(self, dataset, **kwargs):
        model_data = {}
        table_type = None
        for etype, model in self.models.items():
            model.train(dataset, **kwargs)
            model_data[etype] = model.model_data
        label_table_type = self.classify_table_type(dataset)
        if label_table_type == ElementType.TABLE_ROW:
            model_data[ElementType.TABLE_TUPLE] = self.default_model_data()
            table_type = "table_row"
        elif label_table_type == ElementType.TABLE_TUPLE:
            table_type = "table_tuple"
            model_data[ElementType.TABLE_ROW] = self.default_model_data()
        self.model_data = {self.schema.name: model_data}
        if table_type:
            # todo 在预测时使用该信息
            self.model_data["__additional_information"] = {"table_type": table_type}

    def get_model(self, etype: ElementType) -> BaseModel | None:
        if etype not in self.models:
            return None
        model = self.models[etype]
        if self.model_data:
            # 加载模型数据
            if etype == ElementType.TABLE_TUPLE and not self.model_data[etype]:
                return None
            model.model_data = self.model_data[etype]
        return model

    def load_model_data(self):
        """加载模型数据
        两种来源：1. 由自身 predictor 提供 2. 由代理类创建时直接填充 model_data
        """
        if self.model_data and self.model_data.get(self.schema.name):
            # 从elements_collector_based过来的数据模型，没有取当前schema下的数据模型
            self.model_data = self.model_data.get(self.schema.name)
        if not self.model_data:
            self.model_data = self.get_model_data() or self.get_model_data(name="auto")

    def predict_schema_answer(self, elements) -> list[dict[str, list[PredictorResult]]]:
        self.load_model_data()
        answer_results = []
        classifier = ElementClassifier()
        for element in elements:
            ele_type = classifier.get_type(element)
            if element["class"] == "TABLE":
                if self.get_config("custom_regs", []):
                    # 界面配置 custom_regs 时， 表格模型只期望使用 cell_partial_text 模型
                    logger.info(f"{element['index']=} is a table, but custom_regs is set, use table_one_col model")
                    ele_type = ElementType.TABLE_ONE_COL
                else:
                    if ele_type not in (ElementType.TABLE_KV, ElementType.TABLE_ONE_COL):
                        if ele_type == ElementType.TABLE_TUPLE:
                            model = self.get_model(ele_type)
                            if any(item for item in model.model_data.values()):
                                ele_type = ElementType.TABLE_TUPLE
                            else:
                                ele_type = ElementType.TABLE_ROW
            logger.info(f"{element['index']=}, {ele_type.name}")
            model = self.get_model(ele_type)
            logger.info(f"{model=}")
            if not model:
                continue
            if self.anchor_regs and not self.is_valid(element):
                logger.info(f"{element['index']=} is not valid")
                continue
            results = model.predict_schema_answer([element])
            if not results:
                continue
            answer_results.extend(results)
            if not self.multi_elements:
                break

        need_supplementary_columns = self.need_supplementary_answer(answer_results)
        all_elements = self.get_special_elements(page_range=self.get_config("page_range"))
        if need_supplementary_columns:
            logger.info(f"{need_supplementary_columns=}")
            answer = {}
            for column in need_supplementary_columns:
                column_results = self.extract_by_regs(elements, column)
                if column_results:
                    logger.info(f"extracted answer from extract_by_regs, {column=}")
                else:
                    column_results = self.extract_by_regs(all_elements, column)
                    if column_results:
                        logger.info(f"extracted answer from extract_by_regs by all_elements, {column=}")
                if column_results:
                    answer[column] = column_results
            if answer:
                answer_results.append(answer)
        return answer_results

    def need_supplementary_answer(self, answer_results):
        if not answer_results:
            return self.columns
        if len(self.columns) == 1:
            return []
        has_answer_columns = set()
        for column in self.columns:
            for answer_result in answer_results:
                if answer_result.get(column):
                    has_answer_columns.add(column)

        need_supplementary_columns = set(self.columns).difference(has_answer_columns)
        return need_supplementary_columns

    def classify_table_type(self, dataset):
        # table_row 和 table_tuple 不太好区分
        # 如果第一列中有标注单元格， 那么认为此表格是table_row
        # 如果所有的标注单元格都没有第一列的， 认为此表格是table_tuple
        label_cells = []
        for _, col_path in self.columns_with_fullpath():
            for item in dataset:
                for node in self.find_answer_nodes(item, col_path):
                    if node.data is None:
                        continue
                    answer = node.data
                    elements = item.data["elements"]
                    for answer_data in answer["data"]:
                        if not answer_data["boxes"]:
                            continue
                        answer_tables = {
                            idx: parse_table(
                                elements[idx],
                                tabletype=TableType.TUPLE.value,
                                width_from_all_rows=self.width_from_all_rows,
                            )
                            for idx in answer_data["elements"]
                            if elements[idx]["class"] == "TABLE"
                        }
                        for box in answer_data["boxes"]:
                            for table in answer_tables.values():
                                for aim_cell in table.find_cells_by_outline(box["page"], box["box"]) or []:
                                    label_cells.append(aim_cell)

        label_cell_cols = {cell.colidx for cell in label_cells}
        if 0 in label_cell_cols:
            return ElementType.TABLE_ROW
        return ElementType.TABLE_TUPLE

    def default_model_data(self):
        model_data = {}
        for col, _ in self.columns_with_fullpath():
            model_data.setdefault(col, Counter())
        return model_data

    def extract_by_regs(self, elements, column):
        answer_results = []
        patterns = self.patterns(column)
        if not patterns:
            return []
        paras = self.gen_fake_paras(elements)
        for para in paras:
            matchers = patterns.finditer(clean_txt(para["text"]))
            element = para.get("__table", para)
            for matcher in matchers:
                if not matcher:
                    continue
                if self.anchor_regs and not self.is_valid(para):
                    continue
                if "dst" in matcher.groupdict():
                    c_start, c_end = matcher.span("dst")
                else:
                    c_start, c_end = matcher.span()
                sp_start, sp_end = index_in_space_string(para["text"], (c_start, c_end))
                chars = para["chars"][sp_start:sp_end]
                if not chars:
                    continue
                element_results = [CharResult(element, chars)]
                answer_result = self.create_result(element_results, column=column)
                answer_results.append(answer_result)
                if answer_results and not self.multi:
                    break
            if answer_results and not self.multi_elements:
                break
        return answer_results

    def is_valid(self, current_para):
        res = False
        prev_elts = self.pdfinsight.find_elements_near_by(
            current_para["index"], step=-1, amount=self.cnt_of_anchor_elts, aim_types=["PARAGRAPH", "TABLE"]
        )
        anchor_paras = self.gen_fake_paras(prev_elts)
        for anchor_para in anchor_paras:
            if self.anchor_regs.nexts(clean_txt(anchor_para.get("text", ""))):
                res = True
                break

        return res

    @staticmethod
    def gen_fake_paras(elements):
        paras = []
        for element in elements:
            if ElementClassifier.like_paragraph(element) and element.get("text"):
                paras.append(element)
            elif ElementClassifier.is_table(element):
                table = parse_table(element, tabletype=TableType.TUPLE.value)
                for row in table.rows:
                    row_texts = ""
                    row_chars = []
                    for cell in row:
                        if cell.dummy and cell.text in row_texts:
                            logger.debug(f"<auto.gen_fake_paras>: {cell.text=} is dummy, skip...")
                            continue
                        row_chars.extend(cell.raw_cell["chars"])
                        row_texts += cell.text
                    fake_cell = {
                        "__table": element,
                        "text": row_texts,
                        "chars": row_chars,
                        "index": element["index"],
                    }
                    paras.append(fake_cell)
        return paras
