import re
from copy import deepcopy

from remarkable.common.pattern import PatternCollection
from remarkable.common.util import clean_txt
from remarkable.predictor.models.base_model import BaseModel
from remarkable.predictor.mold_schema import SchemaItem

para_flag_pattern = PatternCollection(
    [
        r"^[（(]?[\d\.]+[)）]?《?(?P<flag>.{0,10}?)》?[：:]",
        r"^([（(]\d+[)）])?《?(?P<flag>.{0,31}?)》?[：:]",
        r"^([（(]\d+[)）])?\.?(?P<flag>信用级别)",
        r"^\d+\.?(?P<flag>信用级别)",
        r"^[（(]?[\d\.]+[)）]?[《“]?(?P<flag>资产折价率)[》”]?[：:跑；]",
        r"(?P<flag>专项计划.*?终止以前)",
        r"^([（(]\d+[)）])?《?(?P<flag>.*评级机构.*)》?[：:；]",
    ]
)

invalid_para_flag_pattern = PatternCollection(
    [
        r".{31,}[：:]$",
        r"\d\d:\d\d",
        r"发生差额补足启动事件的处理[：:]$",
        r"发生.*?类差额补足启动事件的情况下，差额补足金额计算方式为[：:]",
        r'在["“]?专项计划终止日["”]?之前，系指以下任一事件[：:]',
        r"（[a-z]）自动生效的加速清偿事件[：:]",
        r"（[a-z]）需经宣布生效的加速清偿事件[：:]",
        r"^(?P<flag>(开户行|开户人|账号|户名|开户银行|大额支付行号))[：:]",
        r"^([（(]\d+[)）])?《?(?P<flag>[A-Z].*?关于“.*?”.*)》?[：:]",
        r"^(?P<flag>([（(][\da-zA-Z]+[)）])?(自动生效的加速清偿事件|需经宣布生效的加速清偿事件))[：:]",
        r"^(?P<flag>\([a-z]\)“累计违约率”超过)[：:]",
        r"^(?P<flag>之相对应的数值)[：:]",
        r"^(?P<flag>第.*?年.*)[：:]",
        r"^(?P<flag>[ABCDabcd]\.关于.*?(借款人|抵押贷款|抵押房产).*?的标准)[：:]",
        r"^(?P<flag>([（(][a-z][)）])?在专项计划终止日之前，系指以下任一事件)[：:]",
        r"^(?P<flag>即如下指定日期，具体如下)[：:]",
        r"^(?P<flag>在发生下述任一情形时，管理人在当个循环购买日不再购买基础资产)[：:]",
        r"^(?P<flag>率”?超过与之相对应的数值)[：:]",
        r"^(?P<flag>\d.*?就信托购买的分期资产而言.*?其资产折价率如下表所示)[：:]",
        r"^(?P<flag>日存在以下任何一种情况的“账单分期”)[：:]",
        r"^(?P<flag>为避免歧义，优先级资产支持证券的预期支付额的含义为)[：:]",
        r"^(?P<flag>就支持计划的基础资产而言.*?系指在对应的基准日.*?支持计划设立日)[：:]",
        r"^(?P<flag>言，系指在循环购买基础资产对应基准日及循环购买日)[：:]",
        r"^(?P<flag>[（(]\w+[)）]截至回购起算日二十四时（\d+)[：:]",
        r"^(?P<flag>[（(]\w+[)）]【运营维持承诺人/保证人】评级下降至【AA】级\(含\)以下)[：:]",
        r"^(?P<flag>[（(]\w+[)）]原始权益人或运营维持承诺人/保证人发生丧失清偿能力事件)[：:]",
        r"^(?P<flag>专项计划设立日和循环购买日)[：:]",
        r"^(?P<flag>自动生效的提前终止事件)[：:]",
        r"^(?P<flag>b\).*?专项计划账户和/或监管账户被有权机关查封、冻结)[：:]",
        r"^(?P<flag>c\).*?运营维持承诺人/保证人】评级下降至【AA】级\(不含\)以下)[：:]",
        r"^(?P<flag>c\).*?运营维持承诺人/保证人】评级下降至【AA】级\(不含\)以下)[：:]",
    ]
)

direct_invalid_flag = PatternCollection(
    [
        r"自专项计划设立日起，至以下两者中较早发生之前[：:]",
    ]
)

chief_next_para_invalid_start_pattern = PatternCollection(
    [
        r"^[(（]",
        r"^\d+[)）]",
        r"^\d+\.",
        r"^[\u4e00-\u9fa5/T()（）]{0,10}[:：]",
    ]
)

chief_next_para_invalid_pattern = PatternCollection(
    [
        r"^(?P<flag>.{0,31}?)》?[：:]",
    ]
)

colon_patterns = PatternCollection([r"[：:]"])


# 下面的这些chief所在的section中， 以`（[a-z]）`开头的段落 容易被误识别成章节，这种段落不能被识别成chief
special_chief_pattern = PatternCollection(
    [
        r"违约资产|违约(抵押)?贷款|违约账单分期|违约(基础)?资产|不良(基础)?资产",
        r"违约事件",
        r"加速清偿事件|违约事件|差额支付启动事件",
        r"提前摊还事件|加速清偿事件|^循环购买$",
        r"评级下调事件",
        r"基准日",
    ]
)

invalid_syllables_flag_pattern = PatternCollection(
    [
        r"^[（(][a-zA-Z]+[)）]",
        r"自动生效的加速清偿事件",
        r"需经宣布生效的加速清偿事件",
        r"未发生加速清偿事件且专项计划未发生本标准条款约定的终止精形的情况",
        r"专项计划资金”不足以支付“优先级资产支持证券”及“次优先级资产支持证券",
        r"信用评级机构对优先.*?级资产支持证券的跟踪评级下调至.*?以下级别",
        r"^[iv]+[\.．].*?(原始权益人|影响)",
        r"^(?P<flag>(开户行|开户人|账号|户名))[：:]",
        r"^(?P<flag>[ABCDabcd]\.关于.*?(借款人|抵押贷款|抵押房产).*?的标准)[：:]",
        r"[a-zA-Z]\)发生对“资产服务机构.*?原始权益人.*?重大不利影响”的事件",
        r"[a-zA-Z]\)?.*?其他担任替代的担保人.*?实质上相同的担保文件",
        r"予以重组、重新确定还款计划或展期的.*?基础资产",
    ]
)

start_serial_num_pattern = PatternCollection(
    [
        r"^[(（]?[a-zA-Z\d]+[)）](?P<dst>.*)",
    ]
)


class FakeModel(BaseModel):
    def __init__(self, options: dict, schema: SchemaItem, predictor):
        super(FakeModel, self).__init__(options, schema, predictor=predictor)

    def train(self, dataset, **kwargs):
        pass

    def predict_schema_answer(self, elements):
        pass

    def parse_sections(self, include_table=False):
        sections = {}
        current_chief = None
        merged_para_idx = set()
        invalid_type = ["PARAGRAPH"]
        if include_table:
            invalid_type.append("TABLE")
        for _, elements in self.pdfinsight.element_dict.items():
            for index, element in enumerate(elements):
                element = element.data
                if element["class"] in invalid_type:
                    if element["class"] == "TABLE":
                        if not current_chief:
                            continue
                        sections.setdefault(current_chief, []).append(element)
                        continue
                    if element["index"] in merged_para_idx:
                        continue
                    sub_chief = self.get_sub_chief(current_chief, elements, index)
                    if sub_chief:
                        current_chief = sub_chief
                    if not current_chief:
                        continue
                    if element["continued"]:
                        page_merged_paragraph_idx = deepcopy(element["page_merged_paragraph"]["paragraph_indices"])
                        if element["index"] in page_merged_paragraph_idx:
                            page_merged_paragraph_idx.remove(element["index"])
                        merged_para_idx = merged_para_idx.union(set(page_merged_paragraph_idx))
                    if element["index"] in merged_para_idx:
                        continue
                    sections.setdefault(current_chief, []).append(element)
        return sections

    def get_sub_chief(self, last_chief, elements, index):
        chief = None
        para = elements[index].data
        match = para_flag_pattern.nexts(clean_txt(para["text"]))
        invalid_match = self.is_invalid_chief(para, last_chief, elements, index)
        if match and not invalid_match:
            chief = match.group("flag")
        if chief:
            return chief
        if not invalid_match and para.get("index") in self.pdfinsight_syllabus.elt_syllabus_dict.keys():
            syllabus = self.pdfinsight_syllabus.elt_syllabus_dict[para.get("index")]
            if syllabus["level"] >= 4:
                return None
            if (
                last_chief
                and special_chief_pattern.nexts(last_chief)
                and invalid_syllables_flag_pattern.nexts(clean_txt(para.get("text")))
            ):
                return None
            return para.get("text")
        return None

    @staticmethod
    def is_invalid_chief(para, last_chief, elements, index):
        clean_para_text = clean_txt(para["text"])
        invalid_match = invalid_para_flag_pattern.nexts(clean_para_text)
        direct_invalid_match = direct_invalid_flag.nexts(clean_para_text)
        matcher = colon_patterns.finditer(clean_para_text)
        last_element = None
        if direct_invalid_match:
            return True
        if index - 1 >= 0:
            last_element = elements[index - 1].data
            if last_element["class"] != "PARAGRAPH":
                last_element = None
        if last_element and last_chief:
            last_element_matcher = PatternCollection(rf"{re.escape(last_chief)}").nexts(clean_txt(last_element["text"]))
            if last_element_matcher:
                start_mather = chief_next_para_invalid_start_pattern.nexts(clean_para_text)
                para_mather = chief_next_para_invalid_pattern.nexts(clean_para_text)
                if not start_mather and para_mather:
                    return True
        if len(list(matcher)) > 1:
            return False
        return invalid_match

    def remove_serial_chars(self, element, dst_chars):
        matcher = start_serial_num_pattern.nexts(clean_txt(element["text"]))
        if not matcher:
            return dst_chars
        dst_chars = self.get_dst_chars_from_matcher(matcher, element)
        if dst_chars:
            return dst_chars
        return dst_chars
