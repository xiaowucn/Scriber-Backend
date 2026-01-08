from copy import deepcopy

from remarkable.common.pattern import PatternCollection
from remarkable.common.util import clean_txt
from remarkable.predictor.ccxi_predictor.models.fake_model import FakeModel
from remarkable.predictor.mold_schema import SchemaItem
from remarkable.predictor.schema_answer import CharResult, PredictorResultGroup

relevant_date_flag = PatternCollection(
    [
        r"计算日|支付日|信托终止日|回收款归集日|计息日|回收款转付日|应收账款回收计算日|回收款归集日|预期到期日",
        r"专项计划设立日|加速清偿初始核算日|初始核算日",
        r"工程尾款回收计算日",
        r"基准日",
        r"(普通|处分|清算|终止|期间)分配兑付日",
        r"收益分配日",
        r"预计到期日",
    ]
)

start_invalid_date = ("回收款转付日", "回收款归集日")


class CollectionPayment(FakeModel):
    def __init__(self, options: dict, schema: SchemaItem, predictor):
        super(CollectionPayment, self).__init__(options, schema, predictor=predictor)

    def predict_schema_answer(self, elements):
        answer_results = []
        sections = self.parse_sections()
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
            for para in section:
                if invalid_paragraph_pattern and invalid_paragraph_pattern.nexts(clean_txt(para["text"])):
                    continue
                matchers = paragraph_pattern.finditer(clean_txt(para["text"]))
                for matcher in matchers:
                    if not matcher:
                        continue
                    dst_chars = self.get_dst_chars_from_matcher(matcher, para)
                    if not dst_chars:
                        continue
                    thing = "".join([char["text"] for char in dst_chars])
                    thing_answer = self.create_result(
                        [CharResult(para, dst_chars)],
                        column=column,
                        schema=self.predictor.find_child_schema(column),
                    )

                    date_answers = self.get_date_answer(thing, para, sections)
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
                if answer_results and not self.multi:
                    break
            if answer_results and not self.multi:
                break
        return answer_results

    def get_date_answer(self, thing, para, sections):
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
                for date_para in data_section:
                    date_matcher = relevant_date.nexts(clean_txt(date_para["text"]))
                    if not date_matcher:
                        continue
                    dst_chars = self.get_dst_chars_from_matcher(date_matcher, date_para)
                    if not dst_chars:
                        continue
                    dst_chars = self.remove_serial_chars(date_para, dst_chars)
                    answer_text = "".join([char["text"] for char in dst_chars])
                    if _flag in start_invalid_date and answer_text.startswith(_flag):
                        continue
                    data_answer.append(
                        self.create_result(
                            [CharResult(para, dst_chars)],
                            column="相关日期（频率相关）",
                            schema=self.predictor.find_child_schema("相关日期（频率相关）"),
                        )
                    )
        return data_answer
