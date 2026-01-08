from copy import deepcopy

from remarkable.common.constants import TableType
from remarkable.common.pattern import PatternCollection
from remarkable.common.util import clean_txt
from remarkable.pdfinsight.parser import parse_table
from remarkable.pdfinsight.reader import PdfinsightSyllabus
from remarkable.predictor.ccxi_predictor.models.fake_model import FakeModel
from remarkable.predictor.ccxi_predictor.models.qualification_criteria import start_serial_num_pattern
from remarkable.predictor.mold_schema import SchemaItem
from remarkable.predictor.schema_answer import CharResult, OutlineResult, PredictorResultGroup, TableResult

relevant_date_flag = PatternCollection(
    [
        r"信托终止日|计息日|回收款归集日|预期到期日",
        r"应收账款回收计算日",
        r"加速清偿初始核算日",
        r"工程尾款回收计算日",
        r"分配基准日",
        r"(?<!分配)基准日",
        r"(普通|处分|清算|终止|期间|特定)(分配)?兑付日",
        r"收益分配日",
        r"回收期间",
        r"基金收益核算日",
        r"^“初始核算日",
        r"A日",
        r"循环购买日",
        r"专项计划设立日",
        r"(?<!(应收账款回收|工程尾款回收))计算日",
        r"支付日",
        r"兑付日",
    ]
)


class CollectionPaymentForStandard(FakeModel):
    def __init__(self, options: dict, schema: SchemaItem, predictor):
        super(CollectionPaymentForStandard, self).__init__(options, schema, predictor=predictor)

    def predict_schema_answer(self, elements):
        answer_results = []
        sections = self.parse_sections(include_table=True)
        paragraph_pattern = PatternCollection(self.get_config("paragraph_pattern", column=self.schema.name))
        invalid_paragraph_pattern = PatternCollection(
            self.get_config("invalid_paragraph_pattern", column=self.schema.name)
        )
        para_flag = PatternCollection(self.get_config("para_flag", column=self.schema.name))
        column = "回收款转付日（频率相关）"
        if self.predictor.schema_name == "支付频率":
            column = "支付日（频率相关）"
        for flag, section in sections.items():
            if not para_flag.nexts(flag):
                continue
            collection_thing = set()
            is_include_table = any(element["class"] == "TABLE" for element in section)
            if is_include_table:
                thing_answer = self.parse_answer_from_outline(
                    {"range": (section[0]["index"], section[-1]["index"] + 1)}, column
                )
                thing_text = ""
                for element in section:
                    if element["class"] == "TABLE":
                        self.process_table_answer(element, sections, answer_results, column)
                    elif element["class"] == "PARAGRAPH":
                        thing_text += clean_txt(element["text"])
                date_answers = self.get_date_answer(thing_text, sections)
                self.add_date_to_answer(date_answers, answer_results, thing_answer)
                break
            for element in section:
                if invalid_paragraph_pattern and invalid_paragraph_pattern.nexts(clean_txt(element["text"])):
                    continue
                matchers = paragraph_pattern.finditer(clean_txt(element["text"]))
                for matcher in matchers:
                    if not matcher:
                        continue
                    dst_chars = self.get_dst_chars_from_matcher(matcher, element)
                    if not dst_chars:
                        continue
                    thing = "".join([char["text"] for char in dst_chars])
                    if thing in collection_thing:
                        continue
                    collection_thing.add(thing)
                    thing_answer = self.create_result(
                        [CharResult(element, dst_chars)],
                        column=column,
                        schema=self.predictor.find_child_schema(column),
                    )
                    date_answers = self.get_date_answer(thing, sections)
                    self.add_date_to_answer(date_answers, answer_results, thing_answer)
                if answer_results and not self.multi:
                    break
            if answer_results and not self.multi:
                break
        return answer_results

    def add_date_to_answer(self, date_answers, answer_results, thing_answer):
        if date_answers:
            for date_answer in date_answers:
                group = [deepcopy(thing_answer), date_answer]
                group_answer = PredictorResultGroup(
                    [group], schema=self.predictor.parent.find_child_schema(self.predictor.schema_name)
                )
                answer_results.append(group_answer)
        else:
            group = [deepcopy(thing_answer)]
            group_answer = PredictorResultGroup(
                [group], schema=self.predictor.parent.find_child_schema(self.predictor.schema_name)
            )
            answer_results.append(group_answer)

    def get_date_answer(self, thing, sections):
        data_answer = []
        date_flags = set()
        for date_flag_matcher in relevant_date_flag.finditer(clean_txt(thing)):
            if not date_flag_matcher:
                continue
            date_flag = date_flag_matcher.group()
            if date_flag in date_flags:
                continue
            date_flags.add(date_flag)
            for _flag, data_section in sections.items():
                if not PatternCollection(date_flag).nexts(_flag):
                    continue
                data_section = sections.get(_flag, [])
                relevant_date = PatternCollection(rf"(?P<dst>{date_flag}.*?[:：].*)")
                if date_flag == "兑付日":
                    relevant_date = PatternCollection(rf"(\s|\)|）)(?P<dst>{date_flag}.*?[:：].*)")
                for date_para in data_section:
                    if date_para["class"] == "TABLE":
                        continue
                    date_matcher = relevant_date.nexts(clean_txt(date_para["text"]))
                    if not date_matcher:
                        continue
                    dst_chars = self.get_dst_chars_from_matcher(date_matcher, date_para)
                    if not dst_chars:
                        continue
                    dst_chars = self.remove_serial_chars(date_para, dst_chars)
                    data_answer.append(
                        self.create_result(
                            [CharResult(date_para, dst_chars)],
                            column="相关日期（频率相关）",
                            schema=self.predictor.find_child_schema("相关日期（频率相关）"),
                        )
                    )
                    break
        return data_answer

    def parse_answer_from_outline(self, para_range, column):
        page_box = PdfinsightSyllabus.syl_outline(para_range, self.pdfinsight, include_title=True)
        elements = []
        for box in page_box:
            box["text"] = start_serial_num_pattern.sub("", box["text"])
            elements.extend(box["elements"])
        if not elements:
            return None
        element_results = [OutlineResult(page_box=page_box, element=elements[0])]
        answer_result = self.create_result(
            element_results, column=column, schema=self.predictor.find_child_schema(column)
        )
        return answer_result

    def process_table_answer(self, element, sections, answer_results, column):
        for cell in element["cells"].values():
            date_answers_from_table = self.get_date_answer(clean_txt(cell["text"]), sections)
            if date_answers_from_table:
                table = parse_table(
                    element,
                    tabletype=TableType.TUPLE.value,
                    pdfinsight_reader=self.pdfinsight,
                )
                rix, cix = cell["index"].split("_")
                element_results = [TableResult(element, [table.cell(int(rix), int(cix))], text=cell["text"])]
                thing_answer = self.create_result(
                    element_results, column=column, schema=self.predictor.find_child_schema(column)
                )
                self.add_date_to_answer(date_answers_from_table, answer_results, thing_answer)
                break
