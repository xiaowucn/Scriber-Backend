import logging

import attr

from remarkable.common.constants import ComplianceStatus
from remarkable.pdfinsight.reader import PdfinsightReader
from remarkable.plugins.predict.answer import AnswerNode
from remarkable.rule.rule import CheckPointItemSchema, InspectItem, Rule, revise_answer


def compliance_check(
    meta: dict,
    answer: AnswerNode,
    pdfinsight: PdfinsightReader,
    root_node: AnswerNode,
    parent_node: AnswerNode,
) -> InspectItem:
    res_item = InspectItem.new(second_rule=meta["path"][0])
    if not answer.data.plain_text:
        res_item.result = ComplianceStatus.NONCONTAIN
        res_item.comment = ComplianceStatus.status_anno_map()[res_item.result]
    # 如果有自定义检查方法则按照自定义检查方法逻辑判断
    elif callable(meta.get("check_func")):
        res_item = meta.get("check_func")(answer, pdfinsight, root_node, parent_node)
    else:
        # 默认有值即合规
        res_item.schema_cols = answer.fullpath.split("_")
        res_item.result = ComplianceStatus.COMPLIANCE
        res_item.comment = answer.data.plain_text
    return res_item


def default_check_func(
    point_name: str, meta: dict, root_node: AnswerNode, pdfinsight: PdfinsightReader
) -> list[InspectItem]:
    ret = []
    group_by = meta.get("group_by")
    schema_answer = root_node[meta["key"]]
    for node in [n for _, n in schema_answer.items() if not n.isleaf()]:
        # 根据group_by对应attr枚举值分组, 跳过非本组答案
        if group_by:
            ans = node.get(group_by, None)
            if not ans or revise_answer(ans).data.value != (meta.get("group_value") or point_name):
                logging.warning(f"{point_name}: {group_by} does not match, skip it")
                continue

        res_item = InspectItem.new(result=ComplianceStatus.COMPLIANCE, second_rule=point_name)
        for _attr in meta["attrs"]:
            ans = node.get("_".join(_attr["path"]), None)
            checked_result = compliance_check(_attr, revise_answer(ans), pdfinsight, root_node, node)
            if checked_result.result != ComplianceStatus.COMPLIANCE:
                res_item.result = ComplianceStatus.NONCOMPLIANCE

            # 默认定位到第一个有答案的子节点答案位置
            if not res_item.schema_cols and checked_result.schema_cols:
                res_item.schema_cols = checked_result.schema_cols
                res_item.comment = checked_result.comment
            res_item.detail["sub_cols"].append(checked_result)

        ret.append(res_item)
    return ret


class POChecker(Rule):
    """
    每个 Rule class 包含若干检查点;
    每个检查点(check point)需检查 schema 节点数据(一对多);
    每个 schema 节点数据含有多个子节点数据(一对多)
    """

    check_points = {
        # "check_point1": [
        #     {
        #         "key": "parent path1",
        #         "check_func": "func1",  # 自定义检查方法
        #         "attrs": [
        #             {
        #                 "path": ["child path1"],
        #                 "check_func": "func2",
        #             },
        #             {
        #                 "path": ["child path2"],
        #             },
        #         ],
        #     },
        #     {
        #         "key": "parent path2",
        #         "attrs": [
        #             {
        #                 "path": ["child path1"],
        #             },
        #             {
        #                 "path": ["child path2"],
        #             },
        #         ],
        #     },
        # ],
        # "check_point2": [
        #     ...
        # ],
    }

    def __init__(self, name):
        super(POChecker, self).__init__(name)
        self.validate_checkpoints()

    @classmethod
    def validate_checkpoints(cls):
        if not isinstance(cls.check_points, dict):
            raise ValueError
        for k, items in cls.check_points.items():
            if not isinstance(k, str) or not isinstance(items, list):
                raise TypeError
            for item in items:
                errors = CheckPointItemSchema().validate(item)
                if errors:
                    raise ValueError(f"{errors}")
        logging.debug(f"{cls.__name__}: check points data validation passed.")

    def organize_output(self, rows: list[InspectItem]) -> list[InspectItem]:
        raise NotImplementedError

    def check(self, answer: AnswerNode, pdfinsight: PdfinsightReader, meta) -> list[InspectItem]:
        self.meta = meta
        ret = []
        for name, schemas in self.check_points.items():
            group = []
            for schema in schemas:
                if schema["key"] not in answer:
                    continue
                func = schema["check_func"] if callable(schema.get("check_func")) else default_check_func
                group.extend(func(name, schema, answer, pdfinsight))

            ret.extend(group)

        return self.organize_output(ret)
