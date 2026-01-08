import logging
import re
from collections import defaultdict
from typing import Pattern

import attr

from remarkable.common.diff.mixins import P_SERIAL, DiffMixin
from remarkable.common.rectangle import Rectangle, null_rect

PATTERN_MAP = {
    "standard_term": ((re.compile(r"本?《?标准条款》?"), "标准条款"),),
    "asset_trading": ((re.compile(r"本?协议"), "协议"),),
    "legal_opinion": (
        (re.compile(r"本?《?法律意见书》?"), "法律意见书"),
        (re.compile(r"本所(经办)?(律师)?"), "律师"),
        (re.compile(r"我们"), "律师"),
    ),
    "cash_prediction": ((re.compile(r"我所|我们"), "事务所"),),
    "rating_report": ((re.compile(r"本机构|我们"), "公司"),),
    "service_trading": (
        (re.compile(r"本?协议"), "协议"),
        (re.compile(r"本?合同"), "合同"),
    ),
    "trust_contract": ((re.compile(r"本?合同"), "合同"),),
    "fund_custody_contract": ((re.compile(r"本?合同"), "合同"),),
}


def get_trans_ref_differ():
    from remarkable.common.diff.diff import TransactionRefDiffer

    return TransactionRefDiffer()


@attr.s
class SimplePara:
    """
    used as IParagraph alternative to debug text diff
    """

    text: str = attr.ib()
    index: int = attr.ib()

    @classmethod
    def batch_create(cls, texts: list[str]) -> list["SimplePara"]:
        res = []
        for index, text in enumerate(texts):
            res.append(cls(text=text, index=index))
        return res


@attr.s
class MainItem(DiffMixin):
    found: bool = attr.ib()
    paras: list[SimplePara] = attr.ib()
    title: str = attr.ib()
    tables: list[dict] = attr.ib(default=attr.Factory(list))
    extra_indices: set[int] = attr.ib(default=attr.Factory(set))  # 需要在计算outline时过滤的para或table的index
    doclet_type: str = attr.ib(default=None)
    part_found: bool = attr.ib(default=False)
    _fixed_para_texts: list[str] | None = attr.ib(default=None)
    _char2para: list[dict] | None = attr.ib(default=None)
    _index2pos: dict[int, int] | None = attr.ib(default=None)

    @property
    def page(self):
        return self.pages[0]

    @property
    def pages(self):
        return sorted(self.outlines.keys())

    @property
    def special_methods(self):
        return [self._handle_common, self._handle_quote, self._handle_sentence]

    @property
    def common_regs(self) -> list[Pattern]:
        return [P_SERIAL]

    @property
    def outlines(self):
        extra_indices = set()
        for index_l, para in zip(sorted(self.extra_indices, reverse=True), self.paras[::-1]):
            if index_l != para.index:
                break
            extra_indices.add(index_l)
        check_paras = [para for para in self.paras if para.index not in extra_indices]
        check_tables = [table for table in self.tables if table.index not in extra_indices]
        page_outlines = self.group_page_outlines_by_column(check_paras, check_tables)
        result = defaultdict(list)
        for page, column_outlines in page_outlines.items():
            for outlines in column_outlines.values():
                page_rect = null_rect
                for outline in outlines:
                    rect = Rectangle(*outline)
                    page_rect = page_rect.union(rect)
                result[page].append([page_rect.x, page_rect.y, page_rect.xx, page_rect.yy])
        return result

    @property
    def index2pos(self):
        if self._index2pos is not None:
            return self._index2pos
        self._index2pos = {para.index: i for i, para in enumerate(self.paras)}
        return self._index2pos

    def reverse(self):
        self.paras.reverse()
        self._index2pos = None
        self._fixed_para_texts = None

    @staticmethod
    def group_page_outlines_by_column(paras, tables):
        page_outlines = defaultdict(lambda: defaultdict(list))
        for ipara in paras:
            for paragraph in ipara.paragraphs:
                column = paragraph["position"][-1] if paragraph.get("position") else 0
                page_outlines[paragraph["page"]][column].append(paragraph["outline"])

        for itable in tables:
            for table in itable.tables:
                column = table["position"][-1] if table.get("position") else 0
                page_outlines[table["page"]][column].append(table["outline"])
        return page_outlines

    def get_para_diff(self, other: "SubItem", institutions: list[str] = (), remove_title=True):
        """
        比较多个段落与多个段落的差异, 以主文档的段落为准, 将diff结果重新按照段落分开
        """
        if not self.paras:
            return []
        logging.info("%s is comparing with %s", self.title, other.title)
        differ = get_trans_ref_differ()
        extras = tuple(re.compile(institution) for institution in institutions)
        marked_chars_diff = differ.mark(self.text, other.text, extras=extras)
        marked_paras_diff = differ.group_diff_by_para(marked_chars_diff, self.char2para, other.char2para)
        differ.move_extra_diff(marked_paras_diff)

        for i, para_diff in enumerate(marked_paras_diff):
            del_sub_indices = []
            last_text_diff = None
            keep_diff_pos = []
            for j, text_diff in enumerate(para_diff):
                if last_text_diff is None:
                    last_text_diff = text_diff
                diff_type = text_diff["diff"].replace("ignore_", "")
                last_diff_type = last_text_diff["diff"].replace("ignore_", "")
                # 如果连续两个diff都是副文档比主文档多, 且第二个diff和第一个不是副文档的同一个段落, 需要忽略掉第二个
                if diff_type == last_diff_type == "extra" and last_text_diff.get("sub_para_id") != text_diff.get(
                    "sub_para_id"
                ):
                    continue
                # 如果副文档比主文档多的text是副文档的一整个段落, 需要忽略掉
                if diff_type == "extra" and text_diff["text"].startswith(
                    other.fixed_para_texts[text_diff["sub_para_id"]]
                ):
                    merged_text = text_diff["text"]
                    for sub_para_id, text in enumerate(
                        other.fixed_para_texts[text_diff["sub_para_id"] :], start=text_diff["sub_para_id"]
                    ):
                        if merged_text.startswith(text):
                            del_sub_indices.append(other.paras[sub_para_id].index)
                            if sub_para_id == 1 and remove_title:
                                other.paras = other.paras[2:]
                                other.reset()
                                return self.get_para_diff(other, institutions, remove_title=False)
                            merged_text = merged_text[len(text) :]
                        else:
                            break
                else:
                    keep_diff_pos.append(j)
                    last_text_diff = text_diff
            other.extra_indices.update(del_sub_indices)
            para_diff = [text_diff for pos, text_diff in enumerate(para_diff) if pos in keep_diff_pos]
            marked_paras_diff[i] = para_diff

            for text_diff in para_diff:
                if text_diff["diff"].startswith("ignore_"):
                    text_diff["diff"] = "same"
                text_diff["index"] = self.paras[i].index
                if "sub_para_id" in text_diff:
                    text_diff["sub_index"] = other.paras[text_diff["sub_para_id"]].index
        return marked_paras_diff


@attr.s
class SubItem(MainItem):
    title: str = attr.ib(default=None)
    paras: list[SimplePara] = attr.ib(default=attr.Factory(list))
    sub_entities: list = attr.ib(default=attr.Factory(list))
    _char2para: list[int] | None = attr.ib(default=None)

    @property
    def chapter(self):
        return self.paras[0].text if self.paras else None

    @property
    def fixed_para_texts(self):
        if self._fixed_para_texts is not None:
            return self._fixed_para_texts
        texts = super().fixed_para_texts
        if self.doclet_type not in PATTERN_MAP:
            return texts
        for i, text in enumerate(texts):
            for pattern, repl in PATTERN_MAP[self.doclet_type]:
                text = pattern.sub(repl, text)
                texts[i] = text
        self._fixed_para_texts = texts
        return self._fixed_para_texts

    @property
    def char2para(self) -> list[int]:
        return [i for i, fixed_para_text in enumerate(self.fixed_para_texts) for _ in fixed_para_text]

    def reset(self):
        self._fixed_para_texts = None
        self._char2para = None
