from remarkable.common.pattern import PatternCollection
from remarkable.common.util import clean_txt
from remarkable.pdfinsight.reader import PdfinsightSyllabus
from remarkable.predictor.models.base_model import BaseModel
from remarkable.predictor.mold_schema import SchemaItem
from remarkable.predictor.schema_answer import OutlineResult

# 投资范围
syllabus_pattern = PatternCollection(
    [
        r"基金的投资$",
    ]
)
top_para_pattern = PatternCollection(
    [
        r"[(（]二[)）]投资目[的标][：:]",
        r"投资范围",
    ]
)
bottom_para_pattern = PatternCollection(
    [
        # r'本基金成立后备案完成前',
        r"基金管理人在满足法律法规和监管部门要求",
    ]
)

syllabus_pattern1 = PatternCollection(
    [
        r"基金的基本情况",
    ]
)
top_para_pattern1 = PatternCollection(
    [
        r"本基金通过将基金投资者投入的资金|本基金通过灵活应用多种投资策略",
        r"投资于",
    ]
)
bottom_para_pattern1 = PatternCollection(
    [
        r"本基金成立后备案完成前",
        r"基金的存续期限",
    ]
)


investment_scope = [
    (syllabus_pattern, top_para_pattern, bottom_para_pattern),
    (syllabus_pattern1, top_para_pattern1, bottom_para_pattern1),
]

# 基金的投资
top_para_pattern3 = PatternCollection(
    [
        # r'基金管理人可以?根据业务需要变更投资经理',
        # r'实现主动管理',
        r"投资目标",
    ]
)
bottom_para_pattern3 = PatternCollection(
    [
        r"[(（][二三][)）]投资范围[：:]",
    ]
)


# 基金的基本情况
top_para_pattern4 = PatternCollection(
    [
        r"[(（][三四][)）]基金的投资目标和投资范围[：:]",
    ]
)
bottom_para_pattern4 = PatternCollection(
    [
        r"投资于",
    ]
)

investment_purpose = [
    (syllabus_pattern, top_para_pattern3, bottom_para_pattern3),
    (syllabus_pattern1, top_para_pattern4, bottom_para_pattern4),
]
# 投资策略
# syllabus 基金的投资
top_para_pattern5 = PatternCollection(
    [
        r"对投资范围的监督",
    ]
)
bottom_para_pattern5 = PatternCollection(
    [
        r"投资限制",
    ]
)

investment_strategy = [(syllabus_pattern, top_para_pattern5, bottom_para_pattern5)]

# 投资经理简介  基金的投资
top_para_pattern6 = PatternCollection(
    [
        r"[(（]一[)）]投资经理[：:]",
    ]
)
bottom_para_pattern6 = PatternCollection(
    [
        r"基金管理人可根据业务需要变更投资经理",
        r"[(（]二[)）]投资目[的标][：:]",
    ]
)

investment_manager_introduction = [(syllabus_pattern, top_para_pattern6, bottom_para_pattern6)]

all_patterns = {
    "投资范围": investment_scope,
    "投资目标": investment_purpose,
    "投资策略": investment_strategy,
    "投资经理简介": investment_manager_introduction,
}


class InvestmentScope(BaseModel):
    def train(self, dataset, **kwargs):
        pass

    def __init__(self, options: dict, schema: SchemaItem, predictor):
        super(InvestmentScope, self).__init__(options, schema, predictor=predictor)

    def predict_schema_answer(self, elements):
        ret = []
        for pattern, top_pattern, bottom_pattern in all_patterns[self.schema.path[-1]]:
            aim_syllabus = self.find_syllabus(pattern)
            start, end = aim_syllabus["range"]
            answer_paras = []
            is_start_match = False
            for idx in range(start + 1, end):
                elt_type, elt = self.pdfinsight.find_element_by_index(idx)
                if elt_type != "PARAGRAPH":
                    continue
                clean_text = clean_txt(elt["text"])
                if not is_start_match and top_pattern.nexts(clean_text):
                    is_start_match = True
                    continue
                if is_start_match and bottom_pattern.nexts(clean_text):
                    break
                if is_start_match:
                    answer_paras.append(elt)
            if not answer_paras:
                continue
            para_range = {"range": (answer_paras[0]["index"], answer_paras[-1]["index"] + 1)}
            ret.extend(self.parse_answer_from_outline(para_range))

        return ret

    def find_syllabus(self, pattern):
        for syllabus in self.pdfinsight_syllabus.syllabus_dict.values():
            if pattern.nexts(clean_txt(syllabus["title"])):
                return syllabus
        return None

    def parse_answer_from_outline(self, para_range):
        answer_results = []
        page_box = PdfinsightSyllabus.syl_outline(para_range, self.pdfinsight, include_title=True)
        text = "\n".join(i["text"] for i in page_box)
        elements = []
        for i in page_box:
            elements.extend(i["elements"])
        if not elements:
            return answer_results
        element_results = [OutlineResult(page_box=page_box, text=text, element=elements[0])]
        answer_result = self.create_result(element_results, text=text, column=self.schema.name)
        answer_results.append(answer_result)
        return answer_results
