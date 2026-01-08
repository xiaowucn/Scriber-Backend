import logging
import re
from collections import Counter
from copy import deepcopy

from remarkable.common.pattern import PatternCollection
from remarkable.common.util import clean_txt
from remarkable.pdfinsight.reader import PdfinsightSyllabus
from remarkable.predictor.eltype import ElementClassifier, ElementType
from remarkable.predictor.models.partial_text import PartialText
from remarkable.predictor.models.syllabus_elt_v2 import SyllabusEltV2
from remarkable.predictor.models.table_kv import KeyValueTable
from remarkable.predictor.models.table_tuple import TupleTable
from remarkable.predictor.mold_schema import SchemaItem
from remarkable.predictor.schema_answer import CharResult, PredictorResultGroup, TableCellsResult

UP_TO_NOW = r"\d{4}\s?年(\d{1,2}\s?月)?(至?今?|-)\s?(\d{4}\s?年)?\s?(\d{1,2}\s?月)?"

JOB_INFO_PATTERNS = [
    r"(?P<time>\d{4}\s?年(\d{1,2}\s?月)?)创办公司前身(?P<company>\w*)，",
    rf"(?P<time>{UP_TO_NOW})，?兼?任(?P<company>\w*?)(执行董事兼总经理|副?总经理|副?董事长?|监事|法定代表人)",
    r"(?P<time>\d{4}\s?年(\d{1,2}\s?月)?)至今历?任(?P<company>\w*)董事长?",
    rf"(?P<time>{UP_TO_NOW})担?任(?P<company>\w*?)(董事长兼)?总经理",
    r"(?P<time>\d{4}\s?年(\d{1,2}\s?月)).{0,10}?(创[立建]|任)(?P<company>\w*?)[，、]",
    r"(?P<time>\d{4}\s?年(\d{1,2}\s?月)?([至-]\s?\d{4}\s?年(\d{1,2}\s?月)?)?).{0,10}?(创建|任)(?P<company>\w*?)[，、]",
    rf"(?P<time>{UP_TO_NOW})担?任(?P<company>\w*?)(老师|主任|校长)",
    r"(?P<time>现任)(?P<company>\w*?)(副?总经理|董事)",
    r"(?P<time>\d{4}\s?年(\d{1,2}\s?月)?至?今?)在(?P<company>\w*?)工作",
    rf"(?P<time>{UP_TO_NOW}).*?(在|创办了)(?P<company>.*?)(担任|等单位)",
    rf"(?P<time>{UP_TO_NOW})任(?P<company>\w*)董事长?",
    r"(?P<time>现任)(?P<company>[\w（）]*?)(副?总经理|董事|、)",
    r"(?P<time>自公司设立至今).*?(?P<company>公司)",
]

SPLIT_PATTERNS = re.compile(r"[；。，]")
SPLIT_PATTERNS2 = re.compile(r"[；。]")

FULL_NAME_PATTERNS = [
    r"（?(?P<dst>\w*?)）?，?\s?([男女]士?|先生|中国国籍)",
]

FULL_NAME_HEADER = [
    r"(?<!公司)(姓名|名称)",
]

JOB_POSITION_PATTERNS = [
    r"(?P<dst>实际控制人)",
    r"(?P<dst>控股股东)",
]

ID_NUM = [r"(?P<dst>[\d\*]+)"]


class SzseHolderInfo(SyllabusEltV2):
    def __init__(self, options: dict, schema: SchemaItem, predictor):
        super(SzseHolderInfo, self).__init__(options, schema, predictor=predictor)

        syllabus_options = deepcopy(options)
        syllabus_options["keep_parent"] = True
        syllabus_options["multi"] = True
        self.syllabus_model = SyllabusEltV2(syllabus_options, schema, predictor=self.predictor)

        # 段落默认使用 partial_text 模型处理
        para_options = deepcopy(options)
        para_options["name"] = "partial_text"
        para_config = self.config.get("para_config", {})
        para_options.update(para_config)
        self.para_model = PartialText(options, self.schema, predictor=self.predictor)

        table_options = deepcopy(options)
        table_options["name"] = "table_kv"
        self.table_kv_model = KeyValueTable(table_options, self.schema, predictor=self.predictor)
        self.table_kv_model.target_element = ElementType.TABLE_KV

        table_options = deepcopy(options)
        table_options["name"] = "table_tuple"
        self.table_tuple_model = TupleTable(table_options, self.schema, predictor=self.predictor)
        self.table_tuple_model.target_element = ElementType.TABLE_TUPLE

    def train(self, dataset, **kwargs):
        self.model_data["syllabus"] = self.train_syll(dataset, **kwargs)
        self.para_model.train(dataset, **kwargs)
        self.model_data["paragraph"] = self.para_model.model_data
        self.table_kv_model.train(dataset, **kwargs)
        self.model_data["table_kv"] = self.table_kv_model.model_data
        self.table_tuple_model.train(dataset, **kwargs)
        self.model_data["table_tuple"] = self.table_tuple_model.model_data

    def load_model_data(self):
        self.model_data = self.predictor.model_data.get(self.name, {})
        self.para_model.model_data = self.model_data["paragraph"]
        self.table_kv_model.model_data = self.model_data["table_kv"]
        self.table_tuple_model.model_data = self.model_data["table_tuple"]

    def predict_schema_answer(self, elements):
        self.load_model_data()
        answer_results = []
        sections = []
        syllabus_model_data = self.get_model_data(column="syllabus")[self.schema.name]
        aim_syllabuses = self.get_aim_syllabus(syllabus_model_data)
        for syllabus in aim_syllabuses:
            sections.extend(self.parse_sections(syllabus, self.pdfinsight.syllabus_dict))

        for start, end in sections:
            section_answers = self.extract_from_section(start, end)
            if section_answers:
                answer_results.extend(section_answers)
        answer_results = self.add_job_info(answer_results)
        return answer_results

    def extract_from_section(self, start: int, end: int):
        answers = []
        for i in range(start, end):
            ele_type, element = self.pdfinsight.find_element_by_index(i)
            if not element:
                continue
            if ele_type == "PARAGRAPH":
                answers.extend(self.para_model.predict([element]))
            elif ElementClassifier.get_type(element) == ElementType.TABLE_TUPLE:
                answers.extend(self.table_tuple_model.predict([element]))
            elif ElementClassifier.get_type(element) == ElementType.TABLE_KV:
                answers.extend(self.table_kv_model.predict([element]))
        return answers

    @staticmethod
    def parse_sections(syllabus, syllabus_dict):
        sections = []
        if syllabus["children"]:
            # 每节是一个 section
            for sub_syllabus in (syllabus_dict[c] for c in syllabus["children"]):
                sections.append(sub_syllabus["range"])
        else:
            # 每段是一个 section
            start, end = syllabus["range"]
            if end - start < 50:
                for i in range(start, end):
                    sections.append((i, i + 1))
        return sections

    def train_syll(self, dataset, **kwargs):
        """训练定位章节特征"""
        model_data = {}
        for _, col_path in self.columns_with_fullpath():
            for item in dataset:
                syllabuses = item.data.get("syllabuses", [])
                if not syllabuses:
                    continue
                syl_reader = PdfinsightSyllabus(syllabuses)
                features = set()
                for node in self.find_answer_nodes(item, col_path):
                    if node.data is None:
                        continue
                    for answer_item_data in node.data["data"]:
                        syllabus = self.find_chapter_syllabus(answer_item_data, syl_reader)
                        if not syllabus:
                            logging.warning(f"can't find syllabus for answer item {answer_item_data}")
                            continue
                        feature = self.get_feature(syllabus, syl_reader.syllabus_dict)
                        features.add(feature)
                model_data.setdefault(self.schema.name, Counter()).update(features)
        return model_data

    def add_job_info(self, answer_results):
        ret = []
        processed_elements = set()
        processed_texts = set()
        for answer_result in answer_results:
            if not answer_result.get("全称"):
                full_name_answer = self.get_full_name(answer_result)
                if full_name_answer:
                    answer_result["全称"] = [full_name_answer]
                else:
                    ret.append(answer_result)
                    continue
            self.filter_id_num(answer_result)
            for predictor_result in answer_result["全称"][0].element_results:
                institution_info_answers = []
                answer = deepcopy(answer_result)
                element = predictor_result.element
                full_name_answer = self.create_result([predictor_result], column="全称")
                answer["全称"] = [full_name_answer]

                institutions_answers = self.get_institutions(element, processed_elements, processed_texts)
                if institutions_answers:
                    institution_info_answers.extend(institutions_answers)
                else:
                    ele_type, next_element = self.pdfinsight.find_element_by_index(element["index"] + 1)
                    if ele_type != "PARAGRAPH":
                        continue
                    institutions_answers = self.get_institutions(
                        next_element, processed_elements, processed_texts, is_skip=False
                    )
                    if institutions_answers:
                        institution_info_answers.extend(institutions_answers)
                if institutions_answers:
                    answer["任职机构情况"] = institution_info_answers
                if "职位" not in answer:
                    job_position_answers = self.get_job_position(answer_result)
                    if job_position_answers:
                        answer["职位"] = job_position_answers
                ret.append(answer)
        return ret

    def filter_id_num(self, answer_result):
        if not answer_result.get("身份证号"):
            return
        for predictor_result in answer_result["身份证号"][0].element_results:
            element = predictor_result.element
            element_text = clean_txt(element.get("text", ""))
            matcher = PatternCollection(ID_NUM).nexts(element_text)
            if matcher:
                dst_chars = self.get_dst_chars_from_matcher(matcher, element)
                if not dst_chars:
                    continue
                predictor_result = self.create_result([CharResult(element, dst_chars)], column="身份证号")
                answer_result["身份证号"] = [predictor_result]
                break

    def get_full_name(self, answer_result):
        full_name_answer = None
        for _, answers in answer_result.items():
            for answer in answers:
                for element in answer.relative_elements:
                    if element["class"] == "PARAGRAPH":
                        full_name_answer = self.get_full_name_from_para(element)
                        if full_name_answer:
                            return full_name_answer
                    elif element["class"] == "TABLE":
                        full_name_answer = self.get_full_name_from_table(element, answer)
                        if full_name_answer:
                            return full_name_answer
        return full_name_answer

    def get_full_name_from_para(self, element):
        element_text = clean_txt(element.get("text", ""))
        matcher = PatternCollection(FULL_NAME_PATTERNS).nexts(element_text)
        if matcher:
            dst_chars = self.get_dst_chars_from_matcher(matcher, element)
            if not dst_chars:
                return None
            full_name_answer = self.create_result([CharResult(element, dst_chars)], column="全称")
            return full_name_answer
        return None

    def get_full_name_from_table(self, element, answer):
        element_result = answer.element_results[0]
        if not element_result.parsed_cells:
            return None
        parsed_cell = element_result.parsed_cells[0]
        row_idx, col_idx = parsed_cell.rowidx, parsed_cell.colidx
        for cell in parsed_cell.table.rows[row_idx]:
            if cell.colidx == col_idx:
                continue
            if PatternCollection(FULL_NAME_HEADER).nexts(clean_txt("".join([i.text for i in cell.col_header_cells]))):
                full_name_answer = self.create_result([TableCellsResult(element, [cell])], column="全称")
                return full_name_answer
        return None

    def get_answer_from_syllabus_element(self, syllabus):
        job_position_answers = []
        for pattern in JOB_POSITION_PATTERNS:
            matcher = PatternCollection([pattern]).nexts(clean_txt(syllabus["title"]))
            if matcher:
                _, syllabus_element = self.pdfinsight.find_element_by_index(syllabus["element"])
                dst_chars = self.get_dst_chars_from_matcher(matcher, syllabus_element)
                if not dst_chars:
                    continue
                job_position_answers.append(
                    self.create_result([CharResult(syllabus_element, dst_chars)], column="职位")
                )
        return job_position_answers

    def get_job_position(self, answer_result):
        job_position_answers = []
        for _, answers in answer_result.items():
            for answer in answers:
                for element in answer.relative_elements:
                    syllabus_id = element.get("syllabus")
                    if not syllabus_id:
                        continue
                    syllabus = self.pdfinsight_syllabus.syllabus_dict[syllabus_id]
                    parent_syllabus = self.pdfinsight_syllabus.syllabus_dict[syllabus["parent"]]
                    job_position_answers.extend(self.get_answer_from_syllabus_element(syllabus))
                    if not job_position_answers:
                        job_position_answers.extend(self.get_answer_from_syllabus_element(parent_syllabus))
            if job_position_answers:
                break
        return job_position_answers

    def get_institutions(self, element, processed_elements, processed_texts, is_skip=True):
        institution_info_answers = []
        if is_skip and element["index"] in processed_elements:
            return institution_info_answers
        element_text = clean_txt(element.get("text", ""))
        processed_company = []
        institution_info_answers.extend(
            self.get_answers(SPLIT_PATTERNS, element_text, processed_texts, element, processed_company, is_skip)
        )
        institution_info_answers.extend(
            self.get_answers(SPLIT_PATTERNS2, element_text, processed_texts, element, processed_company, is_skip)
        )
        if is_skip:
            processed_elements.add(element["index"])
        return institution_info_answers

    def get_answers(self, pattern, element_text, processed_texts, element, processed_company, is_skip=True):
        rets = []
        for sub_text in pattern.split(element_text):
            if is_skip and sub_text in processed_texts:
                continue
            group = []
            matcher = PatternCollection(JOB_INFO_PATTERNS).nexts(sub_text)
            if matcher:
                time = matcher.groupdict()["time"]
                company = matcher.groupdict()["company"]
                time_dst_chars = self.get_dst_chars_from_text(time, element, matcher.span("time"))
                # 获取任职时间在文本中的位置，以此定位任职机构
                time_idx = element_text.index(time)
                company_dst_chars = self.get_dst_chars_from_text(company, element, (time_idx, len(element_text)))
                if is_skip and company not in processed_company:
                    group.append(self.create_result([CharResult(element, time_dst_chars)], column="任职期间"))
                    group.append(self.create_result([CharResult(element, company_dst_chars)], column="任职机构"))
                if is_skip:
                    processed_company.append(company)
                    processed_texts.add(sub_text)
            if not group:
                continue
            institution_info_answer = PredictorResultGroup(
                [group], schema=self.predictor.parent.find_child_schema("任职机构情况")
            )
            rets.append(institution_info_answer)
        return rets
