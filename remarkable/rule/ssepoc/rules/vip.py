from functools import lru_cache

from remarkable.common.constants import ComplianceStatus
from remarkable.pdfinsight.reader import PdfinsightReader
from remarkable.plugins.predict.answer import AnswerNode
from remarkable.rule.rule import InspectItem, revise_answer
from remarkable.rule.ssepoc.rules import POChecker


def check_disclosure(
    answer: AnswerNode, pdfinsight: PdfinsightReader, root_node: AnswerNode, parent_node: AnswerNode
) -> InspectItem:
    """
    主要客户中提到的关联方是否在关联交易情况中披露
    :param answer:
    :param pdfinsight:
    :param root_node:
    :param parent_node:
    :return:
    """
    counterparties = get_counterparties(root_node)
    inspect_item = InspectItem.new(result=ComplianceStatus.COMPLIANCE)
    name = answer.data.plain_text
    if not is_related(answer, root_node, parent_node):
        inspect_item.result = ComplianceStatus.IGNORE
    else:
        inspect_item.schema_cols = answer.fullpath.split("_")
        if name not in counterparties:
            inspect_item.result = ComplianceStatus.NONCOMPLIANCE

    inspect_item.comment = ComplianceStatus.status_anno_map()[inspect_item.result]
    inspect_item.second_rule = f"关联方:{name}, 披露交易情况"

    return inspect_item


@lru_cache()
def get_counterparties(root_node):
    counterparties = []
    for key in ["公司治理与独立性-经常性关联交易情况", "公司治理与独立性-偶发性关联交易情况"]:
        connected_transaction = root_node.get(key, {})
        for node in connected_transaction.values():
            ans = node.get("关联交易对手", {})
            for leaf in ans.values():
                counterparties.append(leaf.data.plain_text)
    return counterparties


@lru_cache()
def get_related_party(root_node):
    top_five_comment = root_node.get("业务与技术-前五客户注释", {})
    top_five_paragraph = root_node.get("业务与技术-前五客户段落", {})
    related_comments = []
    for node in top_five_comment.values():
        ans = node.get("注释内容", {})
        for leaf in ans.values():
            if leaf.data.value == "关联情况":
                related_comments.append(leaf.data.simple_text(enum=False))

    related_parties = []
    for node in top_five_paragraph.values():
        ans = node.get("关联方", {})
        for leaf in ans.values():
            related_parties.append(leaf.data.plain_text)

    return related_parties, related_comments


def is_related(answer: AnswerNode, root_node: AnswerNode, parent_node: AnswerNode) -> bool:
    """
    是否是关联方
    :param answer:
    :param root_node:
    :param parent_node:
    :return:
    """
    related_parties, related_comments = get_related_party(root_node)
    name = answer.data.plain_text
    if parent_node.get("是否关联方", None) and revise_answer(parent_node["是否关联方"]).data.value == "是":
        return True
    elif name in related_parties:
        return True
    elif any(name in x for x in related_comments):
        return True

    return False


class TopFiveVIP(POChecker):
    check_points = {
        "关联方披露": [
            {
                "key": "业务与技术-前五客户",
                "attrs": [
                    {
                        "path": ["名称"],
                        "check_func": check_disclosure,
                    }
                ],
            },
        ],
    }

    def organize_output(self, rows: list[InspectItem]) -> list[InspectItem]:
        exists = []
        output = []
        for row in rows:
            if row.detail["sub_cols"][0].result in [ComplianceStatus.IGNORE, ComplianceStatus.NONCONTAIN]:
                continue
            row.second_rule = row.detail["sub_cols"][0].second_rule
            if row.second_rule in exists:
                continue
            exists.append(row.second_rule)
            row.detail["sub_cols"] = []
            row.comment = ""
            output.append(row)
        head = InspectItem.new(
            result=ComplianceStatus.IGNORE, comment="是" if output else "否", second_rule="存在关联方"
        )
        output.insert(0, head)
        return output
