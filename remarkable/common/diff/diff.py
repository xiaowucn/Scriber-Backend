import re
from copy import deepcopy
from typing import Pattern

import attr

from remarkable.common.diff.mixins import P_SERIAL
from remarkable.common.diff.para_similarity import SimilarPara
from remarkable.common.diff.transaction_ref import MainItem, SimplePara, SubItem


class Differ:
    @staticmethod
    def split_diff_by_char(texts_diff: list[dict[str, str]]):
        for text_diff in texts_diff:
            for char in text_diff["text"]:
                yield {"text": char, "diff": text_diff["diff"], "type": "normal"}

    @staticmethod
    def group_diff_in_para(chars_diff: list[dict[str, str]]) -> list[dict[str, str | int]]:
        if not chars_diff:
            return []
        para_diff = chars_diff[0]
        for char_diff in chars_diff[1:]:
            if para_diff["diff"] == char_diff["diff"]:
                if para_diff.get("sub_para_id") == char_diff.get("sub_para_id") or para_diff.get(
                    "para_id"
                ) == char_diff.get("para_id"):
                    if para_diff["type"] == char_diff["type"]:
                        para_diff["text"] = para_diff["text"] + char_diff["text"]
                        continue
            yield para_diff
            para_diff = char_diff
        yield para_diff

    @staticmethod
    def group_diff_by_type(chars_diff: list[dict[str, str]]) -> list[dict[str, str | int]]:
        if not chars_diff:
            return []
        para_diff = chars_diff[0]
        for char_diff in chars_diff[1:]:
            if para_diff["diff"] == char_diff["diff"]:
                para_diff["text"] = para_diff["text"] + char_diff["text"]
                continue
            yield para_diff
            para_diff = char_diff
        yield para_diff

    @classmethod
    def group_diff_by_para(
        cls, chars_diff: list[dict[str, str | int]], main_char2para: list[dict], sub_char2para: list[int]
    ):
        """
        返回按照段落分组之后的char diff
        :param chars_diff:
        :param main_char2para: MainItem.char2para
        :param sub_char2para: SubItem.char2para
        :return:
        """
        main_char2para = deepcopy(main_char2para)
        sub_char2para = deepcopy(sub_char2para)
        para_chars_diff: list[list[dict]] = [[] for _ in {item["para_id"] for item in main_char2para}]
        last_main_para_id = 0
        for char_diff in chars_diff:
            diff_type = cls.get_real_type(char_diff["diff"])
            if diff_type in ["extra", "same"]:
                char_diff["sub_para_id"] = sub_char2para.pop(0)
                if char_diff["diff"].startswith("delete_"):
                    continue
            if diff_type in ["lack", "same"]:
                while True:
                    item = main_char2para[0]
                    if "text" in item:
                        para_id: int = item.pop("para_id")
                        para_chars_diff[para_id].append(main_char2para.pop(0))
                    else:
                        break
                last_main_para_id = main_char2para.pop(0)["para_id"]
            # 如果是多出来的text, 合并到上一个主文档的段落
            para_chars_diff[last_main_para_id].append(char_diff)
        para_chars_diff[-1].extend(main_char2para)
        return [list(cls.group_diff_in_para(chars_diff)) for chars_diff in para_chars_diff]

    @classmethod
    def get_real_type(cls, diff_type: str):
        for prefix in ("ignore_", "delete_"):
            diff_type = diff_type.replace(prefix, "")
        return diff_type

    @classmethod
    def move_extra_diff(cls, paras_diff: list[list[dict[str, str | int]]]):
        """一个段落的最后一个diff如果是extra, 向后找下一个段落, 直到找到一个段落中存在extra的diff, 且sub para id一样, 插入到段落开头的序号后面"""
        para_node = ParaNode.from_list(paras_diff)
        while para_node.next_para:
            if not (para_node.para_diff and para_node.para_diff[-1]["diff"] == "extra"):
                para_node = para_node.next_para
                continue
            para_diff = para_node.para_diff
            extra_text_diff = para_diff[-1]
            if any(text_diff.get("sub_para_id") == extra_text_diff["sub_para_id"] for text_diff in para_diff[:-1]):
                para_node = para_node.next_para
                continue

            # 找到目标para diff
            next_node = para_node.find_next_extra_para(extra_text_diff["sub_para_id"])
            if next_node is None:
                para_node = para_node.next_para
                continue

            # 移动text diff到后面的para diff中
            i = 0
            for text_diff in next_node.para_diff:
                if text_diff["type"] != "serial":
                    break
            next_node.para_diff.insert(i, extra_text_diff)
            para_diff.pop()

            para_node = para_node.next_para

    def mark(self, main_text: str, sub_text: str) -> list[dict[str, str]]:
        texts_diff = SimilarPara.group_para_diff_text(SimilarPara.get_para_diff(main_text, sub_text, False))
        return list(self.split_diff_by_char(texts_diff))


@attr.s
class ParaNode:
    para_diff: list[dict] = attr.ib(default=attr.Factory(list))
    next_para: "ParaNode" | None = attr.ib(default=None)

    @classmethod
    def from_list(cls, paras_diff: list[list[dict]]) -> "ParaNode":
        if not paras_diff:
            raise IndexError
        start_node = para_node = cls(paras_diff[0])
        for para_diff in paras_diff[1:]:
            para_node.next_para = cls(para_diff)
            para_node = para_node.next_para
        return start_node

    def find_next_extra_para(self, sub_para_id: int) -> "ParaNode" | None:
        if self.next_para is None:
            return
        if any(text_diff.get("sub_para_id") == sub_para_id for text_diff in self.next_para.para_diff):
            return self.next_para
        return self.next_para.find_next_extra_para(sub_para_id)


class TransactionRefDiffer(Differ):
    """交易文件引用交叉检查的默认Differ"""

    extra_regs = ()

    @property
    def common_regs(self) -> tuple[Pattern]:
        return (re.compile("计划管理人"),)

    def mark(self, main_text, sub_text, first="left", extras=()):
        chars_diff = super().mark(main_text, sub_text)
        self._mark_ignore_diff(chars_diff, extras)
        texts_diff = list(self.group_diff_by_type(chars_diff))
        if first == "left":
            for i, (prev_text_diff, text_diff) in enumerate(zip(texts_diff[:-1], texts_diff[1:])):
                if (prev_text_diff["diff"], text_diff["diff"]) == ("extra", "lack"):
                    texts_diff[i], texts_diff[i + 1] = texts_diff[i + 1], texts_diff[i]
        return list(self.split_diff_by_char(texts_diff))

    def _mark_ignore_diff(self, chars_diff: list[dict[str, str]], extras: tuple[Pattern]):
        text = "".join(diff["text"] for diff in chars_diff)
        for pattern in self.common_regs + self.extra_regs + extras:
            for matched in pattern.finditer(text):
                start, end = matched.start(), matched.end()
                split_diff = chars_diff[start:end]
                if all(diff["diff"] == "lack" for diff in split_diff):
                    continue
                if all(diff["diff"] == "extra" for diff in split_diff):
                    continue
                for diff in split_diff:
                    if diff["diff"] != "same":
                        diff["diff"] = f"ignore_{diff['diff']}"

    def get_ratio(self, text_l: str, text_r: str, ignore_serial=True) -> float:
        if not text_l:
            return 0
        if ignore_serial:
            text_l = P_SERIAL.sub("", text_l)
            text_r = P_SERIAL.sub("", text_r)
        chars_diff = super().mark(text_l, text_r)
        same_chars = [char_diff for char_diff in chars_diff if char_diff["diff"] == "same"]
        return len(same_chars) / len(text_l)


@attr.s
class DiffUtil:
    paras: list[str] = attr.ib()
    templates: list[str] = attr.ib()

    def compare(self):
        """
        extra是templates比paras多的, lack是paras比templates多的
        """
        main_item_paras = SimplePara.batch_create(self.paras)
        sub_item_paras = SimplePara.batch_create(self.templates)
        main_item = MainItem(paras=main_item_paras, found=True, title="")
        sub_item = SubItem(paras=sub_item_paras, found=False)

        return main_item.get_para_diff(sub_item)

    @staticmethod
    def parse_diff_result(diff_result):
        for items in diff_result:
            res = {i["diff"] for i in items}
            if "lack" in res or "extra" in res:
                return False
        return True


if __name__ == "__main__":
    paras = [
        "1、前言",
        "订立本合同的目的、依据和原则：",
        "1、订立本合同的目的是明确本合同当事人的权利义务111、规范本基金的运作、保护基金份额持有人的合法权益。",
        "2、订立本合同的依据是《中华人民共和国民法典》、《中华人民共和国证券投资基金法》（以下简称《基金法》）和《私募投资基金管理人登记和基金备案办法（试行）》，《关于私募投资基金开户和结算有关问题的通知》，《私募投资基金监督管理暂行办法》（以下简称《私募办法》）,《私募投资基金募集行为管理办法》，《私募投资基金信息披露管理办法》，《关于发布私募投资基金合同指引的通知》,，《证券期货经营机构私募资产管理业务运作管理暂行规定》、《证券期货投资者适当性管理办法》、《基金募集机构投资者适当性管理实施指引（试行）》及其他法律法规的有关规定。",
        "3、订立本合同的原则是平等自愿、诚实信用、充分保护基金份额持有人的合法权益。本合同是约定本合同当事人之间基本权利义务的法律文件，其他与本基金相关的涉及本合同当事人之间权利义务关系的任何文件或表述，均以本合同为准。本合同的当事人包括基金管理人、基金托管人和基金份额持有人。基金合同的当事人按照《基金法》、本合同及其他有关法律法规规定享有权利、承担义务。",
        "本基金按照中国法律法规成立并运作，应当以届时有效的法律法规的规定为准。",
    ]
    templates = [
        "一、前言",
        "订立本合同的目的、依据和原则：",
        "1、订立本合同的目的是明确本合同当事人的权利义务、规范本基金的运作、保护基金份额持有人的合法权益。",
        "2、订立本合同的依据是《中华人民共和国民法典》、《中华人民共和国证券投资基金法》（以下简称《基金法》）和《私募投资基金管理人登记和基金备案办法（试行）》，《关于私募投资基金开户和结算有关问题的通知》，《私募投资基金监督管理暂行办法》（以下简称《私募办法》）,《私募投资基金募集行为管理办法》，《私募投资基金信息披露管理办法》，《关于发布私募投资基金合同指引的通知》,，《证券期货经营机构私募资产管理业务运作管理暂行规定》、《证券期货投资者适当性管理办法》、《基金募集机构投资者适当性管理实施指引（试行）》及其他法律法规的有关规定。",
        "3、订立本合同的原则是平等自愿、诚实信用、充分保护基金份额持有人的合法权益。本合同是约定本合同当事人之间基本权利义务的法律文件，其他与本基金相关的涉及本合同当事人之间权利义务关系的任何文件或表述，均以本合同为准。本合同的当事人包括基金管理人、基金托管人和基金份额持有人。基金合同的当事人按照《基金法》、本合同及其他有关法律法规规定享有权利、承担义务。",
        "本基金按照中国法律法规成立并运作，若本合同的内容与届时有效的法律法规的强制性规定不一致，应当以届时有效的法律法规的规定为准。",
    ]
    diff_util = DiffUtil(paras, templates)
    from pprint import pprint

    pprint(diff_util.compare())
