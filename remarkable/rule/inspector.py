import json
import logging
from collections import defaultdict
from copy import deepcopy

import attr

from remarkable import config
from remarkable.common.constants import AuditStatusEnum, ComplianceStatus
from remarkable.common.storage import localstorage
from remarkable.common.util import ClassBakery
from remarkable.models.new_file import NewFile
from remarkable.pdfinsight.reader import PdfinsightReader
from remarkable.predictor.mold_schema import MoldSchema
from remarkable.pw_models.model import NewFileMeta, NewMold, NewRuleClass, NewRuleItem
from remarkable.pw_models.question import NewQuestion
from remarkable.rule.rule import Rule, gen_answer_node


class LegacyInspector:
    rules: dict = {}
    mold: NewMold = None
    doc: NewFile = None
    question: NewQuestion = None

    def __init__(self, **kwargs):
        """
        rules: {
            "schema1_name": [Rul1, Rule2],
            "default": [Rul1],
        }
        """
        for _attr, value in kwargs.items():
            setattr(self, _attr, value)

    @staticmethod
    def build_schema(schema_info, root_schema_name):
        data = {
            "type": schema_info.get("type"),
            "label": schema_info.get("name"),
            "words": schema_info.get("words", ""),
            "multi": schema_info.get("multi"),
            "required": schema_info.get("required"),
        }
        if data["label"] == root_schema_name:  # 根结点没有这两项
            del data["multi"]
            del data["required"]
        return {"data": data}

    def build_col(self, schema_info, parent_path, index_l, root_schema_name):
        schema = self.build_schema(schema_info, root_schema_name)

        path_l = deepcopy(parent_path)
        path_l.append(schema_info["name"])

        col = {
            "schema": schema,
            "score": -1,
            "data": [],
            "key": json.dumps([":".join([path, idx]) for path, idx in zip(path_l, index_l)]),
        }
        return col

    def gen_rule_result(self, _file, question, mold):
        """Deprecated legacy func"""
        root_schema_name = mold.data["schemas"][0]["name"]
        schema_dict = {schema["name"]: schema for schema in mold.data["schemas"]}
        pdfinsight = None
        pdfinsight_path = _file.pdfinsight_path()
        if pdfinsight_path:
            pdfinsight = PdfinsightReader(localstorage.mount(pdfinsight_path))
        rules = self.rules[mold.name] if mold.name in self.rules else self.rules.get("default", [])
        rule_results = []
        for rule in rules:
            for result in rule.check(question, pdfinsight):
                if not result:
                    continue
                rule_name, check_result = result
                col_attributes = deepcopy(schema_dict[root_schema_name]["schema"][rule_name])
                col_attributes.update({"name": rule_name})
                rule_result = self.build_col(
                    col_attributes, [root_schema_name], index_l=("0", "0"), root_schema_name=root_schema_name
                )
                rule_result["data"] = []
                rule_result["value"] = check_result
                rule_result["misc"] = {}
                rule_results.append(rule_result)
        return rule_results

    def check(self):
        return self.gen_rule_result(self.doc, self.question, self.mold)


class Inspector:
    crude_elt_limit = config.get_config("web.limit_of_crude_elts", 5)
    rules: list[Rule] = []
    mold: NewMold = None
    doc: NewFile = None
    question: NewQuestion = None
    questions: dict[str, NewQuestion] = None
    meta: defaultdict[str, list[NewFileMeta]] = defaultdict(list)

    def __init__(self, *args, **kwargs):
        for _attr, value in kwargs.items():
            setattr(self, _attr, value)

    def check(self) -> dict[str, list[dict]]:
        check_results = defaultdict(list)
        if not self.rules:
            logging.error(f'No rules found in instance: "{self.__class__}"')
            return check_results

        pdfinsight = (
            PdfinsightReader(localstorage.mount(self.doc.pdfinsight_path())) if self.doc.pdfinsight_path() else None
        )
        answer_nodes = {}
        for mold_name, question in self.questions.items():
            answer_node = gen_answer_node(question, pdfinsight)
            if answer_node:
                answer_nodes[mold_name] = answer_node
        if not answer_nodes:
            return check_results

        for rule in self.rules:
            results = []
            try:
                results = rule.check_answers(answer_nodes, pdfinsight, self.meta)
            except Exception as e:
                logging.exception(e)
            for item in [attr.asdict(r) for r in results if r is not None]:
                check_results[rule.name].append(
                    {
                        "rule": rule.name,
                        "schema_cols": item["schema_cols"],
                        "result": item["result"],
                        "comment": item["comment"],
                        "comment_pos": item["comment_pos"],
                        "fid": self.doc.id,
                        "audit_status": AuditStatusEnum.SKIP
                        if item["result"] == ComplianceStatus.IGNORE
                        else AuditStatusEnum.UNAUDITED,  # 默认待审核
                        "second_rule": item["second_rule"],
                        "detail": item["detail"],
                    }
                )
        return check_results


def get_crude_key(second_rule, schema):
    crude_key = second_rule
    for schema_key, schema_info in schema[0]["schema"].items():
        if schema_key == second_rule and schema_info.get("type") not in MoldSchema.basic_types:
            for item in schema:
                if item["name"] == schema_info.get("type"):
                    crude_key = "-".join((schema_key, item["orders"][0]))
                    break
            break
    return crude_key


def get_title_xpath(pdfinsight):
    # 若找不到对应元素块，则标注到文章标题处
    if not pdfinsight:
        return {}
    xpath = {}
    title_page_eles = pdfinsight.element_dict.get(0, [])
    if title_page_eles:
        title_ele = title_page_eles[0]
        xpath = title_ele.data.get("docx_meta", {})
    return xpath


class AnswerInspectorFactory(ClassBakery):
    CLASSNAME_OVER_CONFIG = None
    CLASS = {}  # this cache mast be different with AnswerPredictorFactory
    config_entry = "web.classes.answer_inspector"

    @classmethod
    async def create(cls, mold: NewMold, *args, **kwargs) -> Inspector | None:
        clazz = cls.get_class(mold.name)
        if not clazz:
            return None
        kwargs["mold"] = mold
        rule_groups = []
        for rule_class in await NewRuleClass.list_by_mold(mold=mold.id):
            items = await NewRuleItem.list_by_rule_class(rule_class.id)
            rule_groups.append((rule_class, items))
        args = (mold.name, rule_groups)
        return clazz(*args, **kwargs)
