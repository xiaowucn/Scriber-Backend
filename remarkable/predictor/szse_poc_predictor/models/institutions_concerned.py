import re
from copy import deepcopy

from remarkable.common.constants import TableType
from remarkable.common.pattern import PatternCollection
from remarkable.common.util import clean_txt
from remarkable.pdfinsight.parser import parse_table
from remarkable.predictor.models.base_model import BaseModel
from remarkable.predictor.schema_answer import (
    CellCharResult,
    CharResult,
    PredictorResult,
    PredictorResultGroup,
    TableCellsResult,
)

INVALID_ROOT_SYLLABUS_PATTERN = [r"二.*?概览|^本次发行概况$"]

INVALID_SYLLABUS_PATTERN = [r"人员的权益关系$|相关机构承诺$"]
INVALID_PARA_SECTIONS = [
    r"发行人与相关中介机构关系的说明$|发行人与本次发行中介机构的关系$|股权关系或其他[权利]益关系|战略配售情况"
]

MIDDLE_COL_PATTERN = [r"指"]
FIRST_COL_PATTERN = [r"序号"]

ABBREVIATION = "简称"
FULL_NAME = "全称/释义"

SPONSOR = "保荐(人|机构)(（主承销商）)?"

ORGANIZATION_COL_PATTERN = [rf"(?P<dst>名称|户名|(开户|收款)银行|{SPONSOR})"]

ORGANIZATION_VALUE_PATTERN = [rf"(名称|户名|开户银行|{SPONSOR})[:：](?P<dst>.*)"]


ORGANIZATION_TYPE_PATTERN = [
    rf"(?P<dst>{SPONSOR}收款银行)",
    rf"(?P<dst>{SPONSOR}会计师)",
    rf"(?P<dst>{SPONSOR}律师)",
    rf"(?P<dst>{SPONSOR})",
    r"(?P<dst>联席主承销商)",
    r"(?P<dst>(律师事务所|发行人律师))",
    r"(?P<dst>收款银行)",
    r"(?P<dst>发行人会计师)",
    r"(?P<dst>会计师事务所)",
    r"(?P<dst>资产评估机构|资产评估及资产评估复核机构)",
    r"(?P<dst>验资(复核)?机构)",
    r"(?P<dst>申报会计师)",
    r"(?P<dst>股票登记机构)",
    r"(?P<dst>股票上市交易所|拟?(申请)?上市的?(证券)?交易所)",
    r"(?P<dst>审计机构)",
    r"(?P<dst>发行人)",
]

ORGANIZATION_NAME_PATTERN = [
    rf"(名称|户名|开户银行|{SPONSOR})[:：](?P<dst>.*)",
    r"发行人.*?[:：](?P<dst>.*)",
    r"联席主承销商[:：](?P<dst>.*)",
    r"保荐(人|机构)(（主承销商）)?.*?[:：](?P<dst>.*)",
    r"(律师事务所|发行人律师).*?[:：](?P<dst>.*)",
    r"发行人会计师.*?[:：](?P<dst>.*)",
    r"会计师事务所.*?[:：](?P<dst>.*)",
    r"申报会计师.*?[:：](?P<dst>.*)",
    r"验资(复核)?机构.*?[:：](?P<dst>.*)",
    r"资产评估机构.*?[:：](?P<dst>.*)",
    r"资产评估及资产评估复核机构.*?[:：](?P<dst>.*)",
    r"股票登记机构.*?[:：](?P<dst>.*)",
    r"收款银行.*?[:：](?P<dst>.*)",
    r"(股票上市交易所|拟?(申请)?上市的?(证券)?交易所.*?[:：])(?P<dst>.*)",
    r"审计机构.*?[:：](?P<dst>.*)",
]

PERSONNEL_INFORMATION_PATTERN = [
    r"(?P<dst>联系人)",
    r"(?P<dst>保荐代表人)",
    r"(?P<dst>项目协办人)",
    r"(?P<dst>项目组成员)",
    r"(?P<dst>项目组?协办人)",
    r"(?P<dst>项目组?(其他)?经办人)",
    r"(?P<dst>项目组其他成员)",
    r"(?P<dst>会计事务所负责人)",
    r"(?P<dst>负责人)",
    r"(?P<dst>法定代表人)",
    r"(?P<dst>经办律师)",
    r"(?P<dst>(经办|签字)注册会计师)",
    r"(?P<dst>经办会计师)",
    r"(?P<dst>其他经办人员)",
    r"(?P<dst>经办评估师)",
    r"(?P<dst>(经办?注册|签字)(资产)?评估师)",
    r"(?P<dst>经办?资产评估师)",
    r"(?P<dst>执行事务合伙人)",
]

PERSONNEL_VALUE_PATTERN = [
    r"联系人.*?[:：](?P<dst>.*)",
    r"保荐代表人.*?[:：](?P<dst>.*)",
    r"项目协办人.*?[:：](?P<dst>.*)",
    r"项目组成员.*?[:：](?P<dst>.*)",
    r"项目组?协办人.*?[:：](?P<dst>.*)",
    r"项目组?(其他)?经办人.*?[:：](?P<dst>.*)",
    r"项目组其他成员.*?[:：](?P<dst>.*)",
    r"会计事务所负责人.*?[:：](?P<dst>.*)",
    r"负责人.*?[:：](?P<dst>.*)",
    r"法定代表人.*?[:：](?P<dst>.*)",
    r"经办律师.*?[:：](?P<dst>.*)",
    r"(经办|签字)注册会计师.*?[:：](?P<dst>.*)",
    r"经办会计师.*?[:：](?P<dst>.*)",
    r"其他经办人员.*?[:：](?P<dst>.*)",
    r"经办评估师.*?[:：](?P<dst>.*)",
    r"(经办?注册|签字)(资产)?评估师.*?[:：](?P<dst>.*)",
    r"经办?资产评估师.*?[:：](?P<dst>.*)",
    r"执行事务合伙人.*?[:：](?P<dst>.*)",
]


PERSONNEL_SPLIT_PATTERN = r"、"
PERSONNEL_PATTERN = re.compile(r"\W+")

RELATED_INSTITUTIONS_PATTERN = [
    r"(本次|与)发行的?有关的?(中介)?机构(和人员)?|本次发行新(股票?)?的?[有相]关的?当事人|中介机构"
]

MAILING_ADDRESS_KEY_PATTERN = [r"联系地址"]

MAILING_ADDRESS_VALUE_PATTERN = [
    r"联系地址.*?[:：](?P<dst>.*)",
]

REGISTERED_ADDRESS_KEY_PATTERN = [r"注册地址"]

REGISTERED_ADDRESS_VALUE_PATTERN = [
    r"注册地址.*?[:：](?P<dst>.*)",
]

SPECIAL_NAME_ENUM = {
    "会计师事务所": "会计师事务所负责人",
    "律师事务所": "律师事务所负责人",
    "发行人律师": "律师事务所负责人",
    "资产评估机构": "评估事务所负责人",
}

PRINCIPAL_PATTERN = PatternCollection([r"负责人[：:]?"])


class InstitutionsConcerned(BaseModel):
    def __init__(self, options, schema, predictor):
        super(InstitutionsConcerned, self).__init__(options, schema, predictor)

    def train(self, dataset, **kwargs):
        pass

    def predict_schema_answer(self, elements) -> list[dict[str, list[PredictorResult]]]:
        rets = []
        # 根据初步定位结果定位到 `有关发行机构` 章节
        related_institutions_syllabuses = self.get_candidate_syllabus(elements)
        processed_big_tables = set()
        for syllabus_index in related_institutions_syllabuses:
            current_syllabus = self.pdfinsight_syllabus.syllabus_dict[syllabus_index]
            if PatternCollection(INVALID_SYLLABUS_PATTERN).nexts(clean_txt(current_syllabus["title"])):
                continue
            sub_syllabuses = current_syllabus["children"]
            if sub_syllabuses:
                for syllabus_id in sub_syllabuses:
                    syllabus = self.pdfinsight_syllabus.syllabus_dict[syllabus_id]
                    group_elements = self.get_elements_by_syllabus(syllabus)
                    section_class = self.classify_section(group_elements, syllabus)
                    if section_class == "single_table":
                        rets.extend(self.precess_single_section(group_elements, syllabus))
                    elif section_class == "paras":
                        if any(
                            (
                                PatternCollection(INVALID_PARA_SECTIONS).nexts(element["text"])
                                for element in group_elements
                                if element["class"] == "PARAGRAPH"
                            )
                        ):
                            continue
                        rets.extend(self.process_paras_section(group_elements, syllabus))
                    elif section_class == "big_table":
                        # 整个表格
                        rets.extend(self.process_big_table_section(processed_big_tables, elements=group_elements))
            else:
                # 整个表格
                rets.extend(self.process_big_table_section(processed_big_tables, current_syllabus=current_syllabus))
        return rets

    def process_big_table_section(self, processed_big_tables, elements=None, current_syllabus=None):
        if not elements:
            elements = []
            for element_index in range(*current_syllabus.get("range")):
                _, aim_element = self.pdfinsight.find_element_by_index(element_index)
                elements.append(aim_element)
        for element in elements:
            if element["class"] != "TABLE" or element["index"] in processed_big_tables:
                continue
            if isinstance(element["page_merged_table"], int) and element["page_merged_table"] in processed_big_tables:
                continue
            table = parse_table(element, tabletype=TableType.KV.value, pdfinsight_reader=self.pdfinsight)
            processed_big_tables.add(element["index"])
            return self.process_complete_table(element, table)
        return []

    def precess_single_section(self, elements, syllabus):
        rets = []
        for element in elements:
            if element["index"] == syllabus["element"]:
                continue
            # 单个表格
            if element.get("class") in ["TABLE"]:
                table = parse_table(element, tabletype=TableType.KV.value, pdfinsight_reader=self.pdfinsight)
                rets.extend(self.process_single_table(element, table))
        return rets

    def get_elements_by_syllabus(self, syllabus):
        rets = []
        for element_index in range(*syllabus["range"]):
            _, aim_element = self.pdfinsight.find_element_by_index(element_index)
            rets.append(aim_element)
        return rets

    def get_candidate_syllabus(self, elements):
        related_institutions_syllabus = set()
        for element in elements:
            syllabus_index = element.get("syllabus")
            if syllabus_index == -1 or syllabus_index is None:
                continue
            syllabus = self.pdfinsight_syllabus.syllabus_dict[syllabus_index]
            root_syllabus = self.pdfinsight_syllabus.get_root_syllabus(syllabus)
            if PatternCollection(INVALID_ROOT_SYLLABUS_PATTERN).nexts(clean_txt(root_syllabus["title"])):
                continue
            if PatternCollection(ORGANIZATION_TYPE_PATTERN).nexts(clean_txt(syllabus["title"])):
                # 单个机构
                if syllabus["parent"] == -1:
                    continue
                syllabus_parent = self.pdfinsight_syllabus.syllabus_dict[syllabus["parent"]]
                related_institutions_syllabus.add(syllabus_parent["index"])
            elif PatternCollection(RELATED_INSTITUTIONS_PATTERN).nexts(clean_txt(syllabus["title"])):
                # 多个机构在一个表格中
                related_institutions_syllabus.add(syllabus["index"])

        return related_institutions_syllabus

    def process_paras_section(self, group_elements, syllabus):
        answer_result = {}
        # 解析 机构类型
        for element in group_elements:
            if element["index"] == syllabus["element"]:
                matcher = PatternCollection(ORGANIZATION_TYPE_PATTERN).nexts(clean_txt(element["text"]))
                if matcher:
                    dst_chars = self.get_dst_chars_from_matcher(matcher, element)
                    if not dst_chars:
                        continue
                    answer_result["机构类型"] = [
                        self.create_result([CharResult(element, dst_chars)], column="机构类型")
                    ]
                    break

        # 解析 机构名称
        for element in group_elements:
            if element["class"] == "TABLE":
                table = parse_table(element, tabletype=TableType.KV.value, pdfinsight_reader=self.pdfinsight)
                table_answer = self.process_single_table(element, table)
                if table_answer and table_answer[0].get("名称"):
                    answer_result["名称"] = table_answer[0].get("名称")
                if table_answer and table_answer[0].get("通讯地址"):
                    answer_result["通讯地址"] = table_answer[0].get("通讯地址")
                if table_answer and table_answer[0].get("注册地址"):
                    answer_result["注册地址"] = table_answer[0].get("注册地址")
                    break
            elif element["class"] == "PARAGRAPH":
                matcher = PatternCollection(ORGANIZATION_NAME_PATTERN).nexts(clean_txt(element["text"]))
                if matcher:
                    dst_chars = self.get_dst_chars_from_matcher(matcher, element)
                    if not dst_chars:
                        continue
                    answer_result["名称"] = [self.create_result([CharResult(element, dst_chars)], column="名称")]
                    break
        mail_address_answer = self.extract_mail_address_answer_from_paras(group_elements)
        if mail_address_answer:
            answer_result["通讯地址"] = [mail_address_answer]

        register_address_answer = self.extract_register_address_answer_from_paras(group_elements)
        if register_address_answer:
            answer_result["注册地址"] = [register_address_answer]
        # 解析 人员信息
        person_info_answers = self.extract_person_info_for_para_section(group_elements)
        if person_info_answers:
            answer_result["人员信息"] = person_info_answers
        return [answer_result] if answer_result else []

    def get_answer_from_above(self, col, table, element, table_title, pattern):
        answer = None
        for above_element in table.elements_above:
            if above_element.get("class") in ["TABLE"]:
                break
            if above_element.get("class") not in ["PARAGRAPH"]:
                continue
            if table_title == above_element.get("text", ""):
                name_matcher = PatternCollection(pattern).nexts(clean_txt(table_title))
                if name_matcher:
                    dst_chars = self.get_dst_chars_from_matcher(name_matcher, above_element)
                    if not dst_chars:
                        continue
                    answer = self.create_result([CharResult(element, dst_chars)], column=col)
                    break
        return answer

    def process_single_table(self, element, table):
        rets = []
        answer_result = {}
        table_title = table.title.text if table.title else element.get("title")
        organization_type_answer = self.get_answer_from_above(
            "机构类型", table, element, table_title, ORGANIZATION_TYPE_PATTERN
        )
        name_answer = self.get_answer_from_above("名称", table, element, table_title, ORGANIZATION_NAME_PATTERN)
        if not organization_type_answer:
            return []
        answer_result["机构类型"] = [organization_type_answer]

        first_row = table.rows[0]
        name_answer = name_answer or self.get_organ_name_from_special_row(first_row, element)
        if name_answer:
            answer_result["名称"] = [name_answer]

        address_answer = self.extract_mail_address_answer(element, table.rows)
        if address_answer:
            answer_result["通讯地址"] = [address_answer]

        register_address_answer = self.extract_register_address_answer(element, table.rows)
        if register_address_answer:
            answer_result["注册地址"] = [register_address_answer]

        person_info_answers = self.extract_person_info_for_table(element, table, table.rows)
        if person_info_answers:
            answer_result["人员信息"] = person_info_answers
        rets.append(answer_result)
        return rets

    def process_complete_table(self, element, table):
        rets = []
        organization_tags = self.gen_tag_for_complete_table(table)
        regions = self.parser_regions_for_organization(organization_tags)
        for start, end in regions:
            answer_result = {}
            region_first_row = table.rows[start]
            if not region_first_row[-1].text:
                continue
            if len({cell.text for cell in region_first_row}) == 1:
                organ_dst_chars = self.get_dst_chars_from_pattern(ORGANIZATION_TYPE_PATTERN, cell=region_first_row[0])
                name_dst_chars = self.get_dst_chars_from_pattern(ORGANIZATION_NAME_PATTERN, cell=region_first_row[0])
                name_answer = None
                if not name_dst_chars:
                    name_answer = self.get_organ_name_from_special_row(table.rows[start + 1], element)
                if not (name_dst_chars or name_answer) or not organ_dst_chars:
                    continue
                if not name_answer:
                    name_answer = self.create_result(
                        [CellCharResult(element, name_dst_chars, [region_first_row[0]])], column="名称"
                    )
                if not name_answer:
                    continue
                answer_result["机构类型"] = [
                    self.create_result(
                        [CellCharResult(element, organ_dst_chars, [region_first_row[0]])], column="机构类型"
                    )
                ]
                answer_result["名称"] = [name_answer]
            else:
                answer_result["名称"] = [
                    self.create_result([TableCellsResult(element, [region_first_row[-1]])], column="名称")
                ]
                self.get_organization_from_title(region_first_row, answer_result, element, table)

            mail_address_answer = self.extract_mail_address_answer(element, table.rows[start + 1 : end + 1])
            if mail_address_answer:
                answer_result["通讯地址"] = [mail_address_answer]

            register_address_answer = self.extract_register_address_answer(element, table.rows[start + 1 : end + 1])
            if register_address_answer:
                answer_result["注册地址"] = [register_address_answer]

            person_info_answers = self.extract_person_info_for_table(
                element, table, table.rows[start + 1 : end + 1], origin_idx=start + 1
            )
            if person_info_answers:
                answer_result["人员信息"] = person_info_answers
            rets.append(answer_result)
        return rets

    def get_organization_from_title(self, region_first_row, answer_result, element, table):
        if region_first_row[0].text != "机构名称":
            for cell in region_first_row[:2]:
                if cell.text.isdigit():
                    continue
                answer_result["机构类型"] = [self.create_result([TableCellsResult(element, [cell])], column="机构类型")]
                break
        else:
            table_title = table.title.text if table.title else element.get("title")
            organization_type_answer = self.get_answer_from_above(
                "机构类型", table, element, table_title, ORGANIZATION_TYPE_PATTERN
            )
            if organization_type_answer:
                answer_result["机构类型"] = [organization_type_answer]

    def extract_person_info_for_para_section(
        self,
        elements,
    ):
        person_info_answers = []
        for element in elements:
            if element["class"] == "TABLE":
                table = parse_table(element, tabletype=TableType.KV.value, pdfinsight_reader=self.pdfinsight)
                person_info_answers.extend(self.extract_person_info_for_table(element, table, table.rows))
            elif element["class"] == "PARAGRAPH":
                element_text = clean_txt(element["text"])
                person_info_answer = self.extract_person_info_from_a_line(element, element_text)
                if person_info_answer:
                    person_info_answers.extend(person_info_answer)
        return person_info_answers

    def extract_person_info_from_a_line(self, element, element_text, cell=None, table=None, idx=None):
        person_info_answers = []
        if PatternCollection(PERSONNEL_INFORMATION_PATTERN).nexts(element_text):
            person_answers = []
            if cell:
                identity_dst_chars = self.get_dst_chars_from_pattern(PERSONNEL_INFORMATION_PATTERN, cell=cell)
            else:
                identity_dst_chars = self.get_dst_chars_from_pattern(PERSONNEL_INFORMATION_PATTERN, para=element)
            identity_answer = self.get_identity_answer(element, table, identity_dst_chars, idx)
            if PatternCollection([PERSONNEL_SPLIT_PATTERN]).search(clean_txt(element_text)):
                include_person_matcher = PatternCollection(PERSONNEL_VALUE_PATTERN).nexts(clean_txt(element_text))
                if include_person_matcher:
                    element_text = include_person_matcher.groupdict().get("dst", None)
                for text in PERSONNEL_PATTERN.split(clean_txt(element_text)):
                    text_host = cell.raw_cell if cell else element
                    name_dst_chars = self.get_dst_chars_from_text(text, text_host)
                    if not name_dst_chars:
                        continue
                    person_answers.append(self.create_result([CharResult(element, name_dst_chars)], column="姓名"))
            else:
                matcher = PatternCollection(PERSONNEL_VALUE_PATTERN).nexts(clean_txt(element_text))
                if matcher:
                    text_host = cell.raw_cell if cell else element
                    name_dst_chars = self.get_dst_chars_from_matcher(matcher, text_host)
                    if not name_dst_chars:
                        return None
                    person_answers.append(self.create_result([CharResult(element, name_dst_chars)], column="姓名"))

            if not person_answers:
                return None
            person_info_answers = self.gen_predictor_result_group(person_answers, identity_answer)
        return person_info_answers

    def gen_predictor_result_group(self, person_answers, identity_answer):
        person_info_answers = []
        for person_answer in person_answers:
            group = [deepcopy(identity_answer), person_answer]
            person_info_answer = PredictorResultGroup(
                [group], schema=self.predictor.parent.find_child_schema("人员信息")
            )
            person_info_answers.append(person_info_answer)
        return person_info_answers

    def get_identity_answer(self, element, table, identity_dst_chars, idx):
        enum_value = None
        if "".join([i["text"] for i in identity_dst_chars]) == "负责人":
            enum_value = self.gen_enum_value(idx, element, table)
        identity_answer = self.create_result([CharResult(element, identity_dst_chars)], column="身份", value=enum_value)
        return identity_answer

    def extract_mail_address_answer(self, element, rows):
        address_answer = None
        for row in rows:
            key_cell_text = clean_txt(row[0].text)
            if PatternCollection(MAILING_ADDRESS_KEY_PATTERN).nexts(key_cell_text):
                address_answer = self.create_result([TableCellsResult(element, [row[-1]])], column="通讯地址")
                break
        return address_answer

    def extract_register_address_answer(self, element, rows):
        address_answer = None
        for row in rows:
            key_cell_text = clean_txt(row[0].text)
            if PatternCollection(REGISTERED_ADDRESS_KEY_PATTERN).nexts(key_cell_text):
                address_answer = self.create_result([TableCellsResult(element, [row[-1]])], column="注册地址")
                break
        return address_answer

    def extract_mail_address_answer_from_paras(self, elements):
        address_answer = None
        for element in elements:
            if element["class"] != "PARAGRAPH":
                continue
            element_text = clean_txt(element["text"])
            matcher = PatternCollection(MAILING_ADDRESS_KEY_PATTERN).nexts(element_text)
            if matcher:
                dst_chars = self.get_dst_chars_from_pattern(MAILING_ADDRESS_VALUE_PATTERN, para=element)
                if not dst_chars:
                    continue
                address_answer = self.create_result([CharResult(element, dst_chars)], column="通讯地址")
                break
        return address_answer

    def extract_register_address_answer_from_paras(self, elements):
        address_answer = None
        for element in elements:
            if element["class"] != "PARAGRAPH":
                continue
            element_text = clean_txt(element["text"])
            matcher = PatternCollection(REGISTERED_ADDRESS_KEY_PATTERN).nexts(element_text)
            if matcher:
                dst_chars = self.get_dst_chars_from_pattern(REGISTERED_ADDRESS_VALUE_PATTERN, para=element)
                if not dst_chars:
                    continue
                address_answer = self.create_result([CharResult(element, dst_chars)], column="注册地址")
                break
        return address_answer

    def extract_person_info_for_table(self, element, table, rows, origin_idx=None):
        person_info_answers = []
        for idx, row in enumerate(rows):
            if len({cell.text for cell in row}) == 1:
                key_cell_text = clean_txt(row[0].text)
                person_info_answer = self.extract_person_info_from_a_line(
                    element, key_cell_text, cell=row[0], table=table, idx=idx
                )
                if person_info_answer:
                    person_info_answers.extend(person_info_answer)
            else:
                tag_num = 1 if len(row) == 3 and row[0].text == "" else 0
                key_cell_text = clean_txt(row[tag_num].text)
                if PatternCollection(PERSONNEL_INFORMATION_PATTERN).nexts(key_cell_text):
                    person_answers, identity_answer = self.get_person_answers_from_row(
                        element, table, row, key_cell_text, idx, origin_idx
                    )
                    if not person_answers:
                        continue
                    person_info_answers.extend(self.gen_predictor_result_group(person_answers, identity_answer))
        return person_info_answers

    def get_person_answers_from_row(self, element, table, row, key_cell_text, idx, origin_idx):
        person_answers = []
        enum_value = None
        if PRINCIPAL_PATTERN.nexts(clean_txt(key_cell_text)):
            idx = idx + origin_idx if origin_idx else idx
            enum_value = self.gen_enum_value(idx, element, table)
        tag_num = 1 if len(row) == 3 and row[0].text == "" else 0
        identity_answer = self.create_result(
            [TableCellsResult(element, [row[tag_num]])], column="身份", value=enum_value
        )
        person_cell = row[-1]
        if PatternCollection([PERSONNEL_SPLIT_PATTERN]).nexts(clean_txt(person_cell.text)):
            for text in PERSONNEL_PATTERN.split(clean_txt(person_cell.text)):
                dst_chars = self.get_dst_chars_from_text(text, table.raw_rows[person_cell.rowidx][person_cell.colidx])
                if not dst_chars:
                    continue
                person_answers.append(
                    self.create_result([CellCharResult(element, dst_chars, [person_cell])], column="姓名")
                )
        else:
            person_answers.append(
                self.create_result(
                    [CellCharResult(element, person_cell.raw_cell["chars"], [person_cell])], column="姓名"
                )
            )
        return person_answers, identity_answer

    def get_organ_name_from_special_row(self, row, element):
        if len({cell.text for cell in row}) == 1:
            include_person_matcher = PatternCollection(ORGANIZATION_NAME_PATTERN).nexts(clean_txt(row[0].text))
            if include_person_matcher:
                name_dst_chars = self.get_dst_chars_from_matcher(include_person_matcher, row[0].raw_cell)
                if name_dst_chars:
                    return self.create_result([CharResult(element, name_dst_chars)], column="名称")
        if PatternCollection(ORGANIZATION_COL_PATTERN).nexts(clean_txt(row[0].text)):
            return self.create_result([TableCellsResult(element, [row[-1]])], column="名称")
        return None

    @staticmethod
    def classify_table_element(table):
        organization_nums = 0
        for row in table.rows:
            row_text = "".join([clean_txt(cell.text) for cell in row])
            if PatternCollection(ORGANIZATION_TYPE_PATTERN).nexts(row_text):
                organization_nums += 1
                if organization_nums > 1:
                    return "complete_table"
        return "single_table"

    @staticmethod
    def classify_section(elements, syllabus):
        para_nums = 0
        table_nums = 0
        tables = []
        for element in elements:
            if element["index"] == syllabus["element"]:
                continue
            if element["class"] == "PARAGRAPH":
                para_nums += 1
            elif element["class"] == "TABLE":
                table_nums += 1
                tables.append(element)
        if table_nums == 1 and para_nums == 0:
            return "single_table"
        # 跨页表格认为是一个
        if table_nums == 2:
            table_ids = [table["index"] for table in tables]
            for table in tables:
                if table["page_merged_table"] in table_ids:
                    return "single_table"
        # 跨多页表格认为是一个大表格
        if table_nums == 3:
            major_table_id = None
            merged_table_index = set()
            for table in tables:
                if isinstance(table["page_merged_table"], dict):
                    major_table_id = table["index"]
                elif isinstance(table["page_merged_table"], int):
                    merged_table_index.add(table["page_merged_table"])
            if len(merged_table_index) == 1 and major_table_id and list(merged_table_index)[0] == major_table_id:
                return "big_table"

        return "paras"

    @staticmethod
    def gen_tag_for_complete_table(table):
        ret = []
        for row in table.rows:
            tag_num = 1 if len(row) == 3 and row[0].text.isdigit() else 0
            first_cell_text = clean_txt(row[tag_num].text)
            if PatternCollection(ORGANIZATION_TYPE_PATTERN).nexts(first_cell_text):
                ret.append("organization")
            else:
                ret.append("data")
        return ret

    @staticmethod
    def parser_regions_for_organization(
        organization_tags,
    ):
        regions = []
        region = None
        for ridx, tag in enumerate(organization_tags):
            if ridx == 0 or (tag == "organization"):
                # start a new region
                region = [ridx, ridx]
                regions.append(region)
            else:
                region[1] = ridx

        return regions

    def get_dst_chars_from_pattern(self, pattern, para=None, cell=None):
        if cell:
            matcher = PatternCollection(pattern).nexts(clean_txt(cell.text))
            if matcher:
                dst_chars = self.get_dst_chars_from_matcher(matcher, cell.raw_cell)
                if dst_chars:
                    return dst_chars
        if para:
            matcher = PatternCollection(pattern).nexts(clean_txt(para["text"]))
            if matcher:
                dst_chars = self.get_dst_chars_from_matcher(matcher, para)
                if dst_chars:
                    return dst_chars
        return None

    def gen_enum_value(self, idx, element, table):
        enum_value = None
        if table and table.rows:
            answer_above_rows = table.rows[:idx][::-1]
            if answer_above_rows:
                for row in answer_above_rows:
                    for cell in row:
                        matcher = PatternCollection(ORGANIZATION_TYPE_PATTERN).nexts(clean_txt(cell.text))
                        enum_value = self.get_enum_from_matcher(matcher)
                        if enum_value:
                            return enum_value
            if not enum_value:
                table_title = table.title.text if table.title else element.get("title")
                for above_element in table.elements_above:
                    if above_element.get("class") in ["TABLE"]:
                        break
                    if above_element.get("class") not in ["PARAGRAPH"]:
                        continue
                    if table_title == above_element.get("text", ""):
                        matcher = PatternCollection(ORGANIZATION_TYPE_PATTERN).nexts(clean_txt(table_title))
                        enum_value = self.get_enum_from_matcher(matcher)
        else:
            matcher = PatternCollection(ORGANIZATION_TYPE_PATTERN).nexts(clean_txt(element["text"]))
            enum_value = self.get_enum_from_matcher(matcher)
        return enum_value

    @staticmethod
    def get_enum_from_matcher(matcher):
        if not matcher:
            return None
        value = matcher.groupdict().get("dst", None)
        if not value:
            return None
        enum_value = SPECIAL_NAME_ENUM.get(value)
        if enum_value:
            return enum_value
        return None
