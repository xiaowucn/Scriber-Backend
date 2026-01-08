# encoding=utf-8
"""
相似段落，或者多个连续的相似段落生成算法

主要是根据找到的每一对相似段落，逐渐进行合并，最后得到最终的相似段落结果

1. 连续段落 只可能出现在两个文档中，即使基准文档中有同一处连续段落对应了不同文件的连续段落，也会有多个不同的相似段落Correlation实例
"""

import difflib
import re
import time
from builtins import range, str
from copy import deepcopy
from typing import Iterator, Sequence

from remarkable.common.diff.transaction_ref import MainItem, SubItem
from remarkable.common.rectangle import Rectangle

RED = "0xff0000"
DOTTED_RED = "0x000080"
GREEN = "0x00ff00"
BLUE = "0x0000ff"


class SafeDiffer(difflib.Differ):
    def compare(self, a: Sequence[str], b: Sequence[str], autojunk: bool) -> Iterator[str]:
        cruncher = difflib.SequenceMatcher(self.linejunk, a, b, autojunk=autojunk)
        for tag, alo, ahi, blo, bhi in cruncher.get_opcodes():
            if tag == "replace":
                res = super(SafeDiffer, self)._fancy_replace(a, alo, ahi, b, blo, bhi)
            elif tag == "delete":
                res = self._dump("-", a, alo, ahi)
            elif tag == "insert":
                res = self._dump("+", b, blo, bhi)
            elif tag == "equal":
                res = self._dump(" ", a, alo, ahi)
            else:
                raise ValueError("unknown tag %r" % (tag,))

            yield from res


class SimilarPara:
    P_INVALID_SYMBOL_DIFF = re.compile(r"^[、：:（()）《》【】〔〕，,；;。“”‘’\"\']$")

    def __init__(
        self,
        doc_id,
        main_paras,
        main_doclet_type,
        compare_paras,
        compare_doclet_type,
        min_length=10,
        content_type="paragraph",
        distributed=False,
        executors=4,
        measure=0.6,
        main_tables=None,
        sub_tables=None,
        revision_type=None,
    ):
        main_tables = main_tables or {}
        sub_tables = sub_tables or {}
        self.min_length = min_length
        self.doc_id = doc_id
        self.main_doclet_type = main_doclet_type
        self.compare_doclet_type = compare_doclet_type
        self.same_doclet = main_doclet_type == compare_doclet_type
        self.content_type = content_type
        self.main_paras = self.make_link_para(self.filter_para(main_paras), main_tables)
        self.compare_paras = self.make_link_para(self.filter_para(compare_paras), sub_tables)
        self.compare_paras_index = {para.index: para for para in self.compare_paras}
        self.distributed = distributed
        self.executors = executors
        self.measure = measure
        self.main_tables = main_tables
        self.sub_tables = sub_tables
        self.revision_type = revision_type

    def filter_para(self, paras):
        paras = [para for para in paras if len(para.text) > self.min_length and "....." not in para.text]
        return paras

    @staticmethod
    def make_link_para(paras, tables):
        paras_len = len(paras)
        if paras_len <= 1:
            return paras
        sorted_paras = sorted(paras, key=lambda x: x.index)
        current, _next = 0, 1
        while current < paras_len:
            if _next == paras_len:
                sorted_paras[current].next_para_index = None
            else:
                if sorted_paras[_next].index == sorted_paras[current].index + 1:
                    sorted_paras[current].next_para_index = sorted_paras[_next].index
                elif sorted_paras[current].page + 1 == sorted_paras[_next].page:
                    for index in range(sorted_paras[current].index, sorted_paras[_next].index):
                        if index in tables:
                            sorted_paras[current].next_para_index = None
                            break
                    else:
                        sorted_paras[current].next_para_index = sorted_paras[_next].index
                elif sorted_paras[current].page == sorted_paras[_next].page:
                    sorted_paras[current].next_para_index = sorted_paras[_next].index
                else:
                    sorted_paras[current].next_para_index = None
            current += 1
            _next += 1
        return paras

    @staticmethod
    def get_para_new_similarity(para_a, para_b):
        match = sum((para_a & para_b).values())
        if match == 0:
            return 0
        num_x = sum(para_a.values())
        num_y = sum(para_b.values())
        sim = match * 2 / (num_x + num_y)
        return sim

    @staticmethod
    def get_para_similarity(para_a, para_b):
        matcher = difflib.SequenceMatcher(None, para_a, para_b)
        return matcher.ratio()

    @staticmethod
    def get_para_diff(para_a, para_b, autojunk=True):
        differ = SafeDiffer()
        return list(differ.compare(para_a, para_b, autojunk=autojunk))

    @staticmethod
    def group_para_diff_text(diff):
        if not diff:
            return []
        MARK_MAP = {"+": "extra", "-": "lack", " ": "same"}
        ret = []
        prev, cur = 0, 0
        while cur < len(diff):
            if diff[cur][0] != diff[prev][0]:
                # 去掉比较结果中的空格
                text = "".join([item[-1] for item in diff[prev:cur]])
                if text.strip():
                    ret.append({"diff": MARK_MAP[diff[prev][0]], "text": text})
                prev = cur
            cur += 1

        ret.append({"diff": MARK_MAP[diff[prev][0]], "text": "".join([item[-1] for item in diff[prev:cur]])})

        return ret

    def merge_broken_elements(self, similar_indexes):
        # 两篇文档看作自上而下的两条序列
        # 其中，由于识别问题，部分段落被错误切分成多个元素块，
        # 因此，这些元素块需要合并，
        # 合并元素块的顶部元素块为top，底部元素块为bottom

        pairs = []
        min_increase_ratio = 0.03
        bottom_main_index = -1
        before_match_ratio = 0
        for main_index, compare_indexes in enumerate(similar_indexes):
            if main_index <= bottom_main_index or not compare_indexes:
                continue
            top_main_index = bottom_main_index = main_index
            bottom_compare_index = -1
            for compare_index in compare_indexes:
                if compare_index <= bottom_compare_index:
                    continue
                top_compare_index = bottom_compare_index = compare_index
                main_para_counter = deepcopy(self.main_paras[main_index].counter)
                compare_para_counter = deepcopy(self.compare_paras[compare_index].counter)
                match_ratio = self.get_para_new_similarity(main_para_counter, compare_para_counter)
                changed = True  # 开启第一次循环

                # 每次对当前匹配的pair两侧元素块进行上下搜索
                while changed:
                    changed = False

                    if bottom_main_index + 1 < len(self.main_paras):
                        new_match_ratio = self.get_para_new_similarity(
                            main_para_counter + self.main_paras[bottom_main_index + 1].counter, compare_para_counter
                        )
                        if new_match_ratio > match_ratio + min_increase_ratio:
                            bottom_main_index += 1
                            main_para_counter += self.main_paras[bottom_main_index].counter
                            match_ratio = new_match_ratio
                            changed = True

                    if top_main_index - 1 >= 0:
                        new_match_ratio = self.get_para_new_similarity(
                            main_para_counter + self.main_paras[top_main_index - 1].counter, compare_para_counter
                        )
                        if new_match_ratio > match_ratio + min_increase_ratio:
                            top_main_index -= 1
                            main_para_counter += self.main_paras[top_main_index].counter
                            match_ratio = new_match_ratio
                            changed = True

                    if bottom_compare_index + 1 < len(self.compare_paras):
                        new_match_ratio = self.get_para_new_similarity(
                            compare_para_counter + self.compare_paras[bottom_compare_index + 1].counter,
                            main_para_counter,
                        )
                        if new_match_ratio > match_ratio + min_increase_ratio:
                            bottom_compare_index += 1
                            compare_para_counter += self.compare_paras[bottom_compare_index].counter
                            match_ratio = new_match_ratio
                            changed = True

                    if top_compare_index - 1 >= 0:
                        new_match_ratio = self.get_para_new_similarity(
                            compare_para_counter + self.compare_paras[top_compare_index - 1].counter, main_para_counter
                        )
                        if new_match_ratio > match_ratio + min_increase_ratio:
                            top_compare_index -= 1
                            compare_para_counter += self.compare_paras[top_compare_index].counter
                            match_ratio = new_match_ratio
                            changed = True

                if match_ratio > self.measure:
                    if (
                        pairs
                        and pairs[-1][0] == [top_main_index, bottom_main_index]
                        and pairs[-1][1][1] >= top_compare_index
                        and match_ratio > before_match_ratio
                    ):
                        pairs.pop()
                    pairs.append([[top_main_index, bottom_main_index], [top_compare_index, bottom_compare_index]])
                    before_match_ratio = match_ratio

        return pairs

    def generate_corr_pairs(self, pairs):
        corr_pairs = []

        for main_para_indexes, compare_para_indexes in pairs:
            left_node = ParaNode(self.doc_id, self.main_doclet_type, self.main_paras[main_para_indexes[0]])
            right_node = ParaNode(self.doc_id, self.compare_doclet_type, self.compare_paras[compare_para_indexes[0]])
            para_pair = ParaCorrelationPair(left_node, right_node, [], self.content_type, self.revision_type)

            for main_para_index in range(main_para_indexes[0] + 1, main_para_indexes[1] + 1):
                para_node = ParaNode(self.doc_id, self.main_doclet_type, self.main_paras[main_para_index])
                para_pair._left.append(para_node)
                para_pair.left_next = para_node.next_para
                para_pair.left_para_index.append(self.main_paras[main_para_index].index)
                para_pair.left_len += 1

            for compare_para_index in range(compare_para_indexes[0] + 1, compare_para_indexes[1] + 1):
                para_node = ParaNode(self.doc_id, self.main_doclet_type, self.compare_paras[compare_para_index])
                para_pair._right.append(para_node)
                para_pair.right_next = para_node.next_para
                para_pair.right_para_index.append(self.compare_paras[compare_para_index].index)
                para_pair.right_len += 1

            main_paras = [x.para for x in para_pair._left]
            sub_paras = [x.para for x in para_pair._right]
            diff_by_para = MainItem(main_paras).get_para_diff(SubItem(sub_paras))
            para_pair.diff_data = diff_by_para

            corr_pairs.append(para_pair)

        return corr_pairs

    def _similar_para_compare_distributed(self, main_paras):
        pairs = []
        # print '{} {} compare start: {}'.format(os.getpid(), len(main_paras), time.time())
        for main_para in main_paras:
            similar_pairs = self._similar_para_compare(main_para)
            pairs.extend(similar_pairs)
        return pairs

    def generate_similar_para_pairs(self, strict=True):
        # pool = Pool(self.executors)
        # similar_indexes = pool.map(self._get_similar_paras, self.main_paras)
        # pool.close()
        similar_indexes = [self._get_similar_paras(x, strict=strict) for x in self.main_paras]
        pairs = self.merge_broken_elements(similar_indexes)
        pairs = self.generate_corr_pairs(pairs)
        merged_pairs = self.merge_para_pairs(pairs)
        return merged_pairs

    # def generate_similar_para_pairs(self):
    #     pairs = []
    #     _similar_para_compare_func = self._similar_para_compare
    #     if config.get_config('webif.similar_para.use_lsh', True):
    #         _similar_para_compare_func = self._similar_para_compare_lsh
    #     for main_para in self.main_paras:
    #         similar_pairs = _similar_para_compare_func(main_para)
    #         pairs.extend(similar_pairs)
    #     return pairs

    # def merge_pairs(pairs):
    #     # print('start merge pairs...{}'.format(time.time()))
    #     merged_pairs = SimilarPara.merge_para_pairs(deepcopy(pairs))
    #     # merged_pairs = self.merge_single_pairs(merged_pairs)
    #     merged_pairs, duplicate_pairs = SimilarPara.filter_small_pairs(merged_pairs)
    #     _pairs = SimilarPara.filter_duplicate_pairs(duplicate_pairs, pairs)
    #     merged_pairs.extend(_pairs)
    #     return merged_pairs

    @staticmethod
    def filter_duplicate_pairs(duplicate_pairs, pairs):
        ret_pairs = []
        split_pairs = []
        for pairs_tuple in duplicate_pairs:
            group_pairs = []
            # 将([merge_pair1], merge_pair2)转换为([[pair1, pair2, pair3]],[_pair2, _pair3, _pair4])
            for pair in pairs_tuple[0]:
                group_pairs1 = SimilarPara.get_pairs(pair, pairs)
                group_pairs.append(group_pairs1)
            group_pairs2 = SimilarPara.get_pairs(pairs_tuple[1], pairs)
            # 记录两个pair_list里left[0].para_index相同的pair
            group_pair2_indexes = []
            for group_pairs1 in group_pairs:
                pair1_indexes = []
                pair2_indexes = []
                for pair1 in group_pairs1:
                    for pair2 in group_pairs2:
                        pair1_para_index = pair1.left[0].para_index
                        if pair1_para_index == pair2.left[0].para_index:
                            pair1_indexes.append(group_pairs1.index(pair1))
                            pair2_indexes.append(group_pairs2.index(pair2))
                group_pair2_indexes.append(pair2_indexes)
                # 拆分处理pairs_tuple[0]
                group_pair1_intersect = group_pairs1[pair1_indexes[0] : pair1_indexes[-1] + 1]
                extend_pair1 = [pair for pair in group_pairs1 if pair not in group_pair1_intersect]
                split_pairs.append(group_pair1_intersect)
                split_pairs.append(extend_pair1)
            # 拆分处理pairs_tuple[1]
            common_pairs = []
            for _pair2_indexes in group_pair2_indexes:
                group_pair2_intersect = group_pairs2[_pair2_indexes[0] : _pair2_indexes[-1] + 1]
                common_pairs.extend(group_pair2_intersect)
                split_pairs.append(group_pair2_intersect)
            extend_pair2 = [pair for pair in group_pairs2 if pair not in common_pairs]
            split_pairs.append(extend_pair2)
        # 重新合并
        for idx, _pairs in enumerate(split_pairs):
            if _pairs and _pairs not in split_pairs[:idx]:
                merged_pair = SimilarPara.merge_para_pairs(_pairs)
                ret_pairs.extend(merged_pair)
        return set(ret_pairs)

    @staticmethod
    def get_pairs(merged_pairs, pairs):
        # 将merge后的merged_pairs.left 对应到pairs中的单个pair
        pairs1 = []
        for pair in pairs:
            if (
                pair.left_doclet_type == merged_pairs.left_doclet_type
                and pair.right_doclet_type == merged_pairs.right_doclet_type
            ):
                for idx, para_node in enumerate(merged_pairs.left):
                    left = para_node
                    right = merged_pairs.right[idx]
                    pair_left = pair.left[0]
                    pair_right = pair.right[0]
                    if pair_left.para_index == left.para_index and pair_right.para_index == right.para_index:
                        pairs1.append(pair)
        return pairs1

    @staticmethod
    def merge_para_pairs(pairs):
        print("start merge para pairs...{}".format(time.time()))
        if not pairs:
            return pairs
        # pairs是排序的，因此可以迭代的进行合并
        merged_pairs = [pairs[0]]
        left_merged = set()
        right_merged = set()
        for pair in pairs[1:]:
            if pair.left[0].para_index in left_merged or pair.right[0].para_index in right_merged:
                # 如果某个元素块被合并了，那么合并的元素块仅能参与一次匹配
                continue
            for merged_pair in merged_pairs[::-1]:
                merged = merged_pair.merge(pair)
                if merged:
                    for left in merged_pair.left:
                        left_merged.add(left.para_index)
                    for right in merged_pair.left:
                        right_merged.add(right.para_index)
                    break
            if not merged:
                merged_pairs.append(pair)

        merged_pairs2 = []
        for pair in merged_pairs:
            if pair.left_len == 1 and pair.right_len == 1:
                if pair.left[0].para_index in left_merged or pair.right[0].para_index in right_merged:
                    continue
            merged_pairs2.append(pair)

        return merged_pairs2

    @staticmethod
    def _filter_small_pairs(pair, filtered_pairs):
        """
        如果没有和一个矩形相交，则为一个独立矩形
        :param pair:
        :param filtered_pairs:
        :return:
        """
        for filtered_pair in filtered_pairs:
            if pair[1] == filtered_pair[1]:
                return False
            intersected = filtered_pair[1].does_intersect(pair[1])
            if intersected:
                return True
        return False

    @staticmethod
    def merge_single_pairs(pairs):
        print("start merge single pairs...{}".format(time.time()))
        merged_pairs = []
        single_pairs_map = {}
        for pair in pairs:
            if pair.left_len == 1:
                if pair.left[0].para_index not in single_pairs_map:
                    single_pairs_map[pair.left[0].para_index] = pair
                else:
                    single_pairs_map[pair.left[0].para_index].merge_single(pair)
            else:
                merged_pairs.append(pair)
        merged_pairs.extend(list(single_pairs_map.values()))
        return merged_pairs

    @staticmethod
    def get_pair_paras_length(pair):
        ret = {}
        for name in ["left", "right"]:
            paras_length = 0
            for para_node in getattr(pair, name):
                paras_length += len(para_node.para.text)
            ret[name] = paras_length
        return ret


class ParaNode:
    def __init__(self, doc_id, doclet_type, para):
        self.doc_id = doc_id
        self.doclet_type = doclet_type
        self.para = para

    @property
    def next_para(self):
        return self.para.next_para_index

    @property
    def para_index(self):
        return self.para.index

    @property
    def page(self):
        return self.para.page

    @property
    def outlines(self):
        return self.para.outlines


class ParaCorrelationPair:
    cn = re.compile(r"[\u4e00-\u9fa5]")

    def __init__(self, left, right, diff_data, content_type, revision_type):
        self._left = [left]
        self._right = [right]
        self.left_len = 1
        self.right_len = 1
        self.left_next = left.next_para
        self.right_next = right.next_para
        self.left_para_index = [left.para_index]
        self.right_para_index = [right.para_index]
        self.page = left.page
        self.diff_data = [diff_data]
        self.left_doclet_type = left.doclet_type
        self.right_doclet_type = right.doclet_type
        self.content_type = content_type
        self.revision_type = revision_type
        self._outline_rects = {}

    def append_pair(self, another_pair, _reverse=False):
        if _reverse:
            self._left = another_pair.left + self._left
            self._right = another_pair.right + self._right
            self.diff_data = another_pair.diff_data + self.diff_data
            self.page = another_pair.page
        else:
            self._left = self._left + another_pair.left
            self._right = self._right + another_pair.right
            self.diff_data = self.diff_data + another_pair.diff_data
            self.left_next = another_pair.left_next
            self.right_next = another_pair.right_next
        self.left_len += 1
        self.right_len += 1
        self.left_para_index.extend(another_pair.left_para_index)
        self.right_para_index.extend(another_pair.right_para_index)

    @property
    def pair_outline_rects(self):
        if self._outline_rects:
            return self._outline_rects
        for left in self.left:
            for outline in left.outlines:
                if outline["page"] not in self._outline_rects:
                    self._outline_rects[outline["page"]] = Rectangle(*outline["outline"])
                else:
                    self._outline_rects[outline["page"]] = self._outline_rects[outline["page"]].union(
                        Rectangle(*outline["outline"])
                    )
        return self._outline_rects

    @property
    def texts_same(self):
        if not self.diff_data:
            return True
        for para in self.diff_data:
            # 假定序号只出现在前4
            for index, item in enumerate(para):
                if item["diff"] == "same":
                    continue
                if index > 3:
                    return False
                if self.cn.search(item["text"]):
                    return False
        return True

    @property
    def left(self):
        return self._left

    @property
    def right(self):
        return self._right

    def merge_single(self, another_pair):
        if self.left_len == 1 and another_pair.left_len == 1:
            if self.left[0].para_index == another_pair.left[0].para_index:
                self.right_len += 1
                self.right.extend(another_pair.right)
                # no need to update left_next and right_next
                return True
        return False

    def merge(self, another_pair):
        if (
            another_pair.left_doclet_type != self.left_doclet_type
            or another_pair.right_doclet_type != self.right_doclet_type
        ):
            return False
        if self.left_next == another_pair.left[0].para_index and self.right_next == another_pair.right[0].para_index:
            self.append_pair(another_pair)
            return True
        if another_pair.left_next == self.left[0].para_index and another_pair.right_next == self.right[0].para_index:
            self.append_pair(another_pair, _reverse=True)
            return True
        return False
