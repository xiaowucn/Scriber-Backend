"""copied from: https://gitpd.paodingai.com/cheftin/calliper/-/blob/release_dev/pkg/calliper_diff/test/mock_para.py"""

from functools import cached_property
from itertools import chain

from remarkable.pdfinsight.reader import PdfinsightReader


class RulePara:
    def __init__(self, rules, page=0):
        self.rules = rules
        self.page = page

    def get_mocked_paras(self):
        mocked_paras = []
        for rule in self.rules:
            idx = rule.id
            para_text = rule.content
            if not para_text:
                continue
            para_chars = self.get_mocked_chars(para_text, idx)
            merged_page_rects = PdfinsightReader.merge_char_rects(para_chars, pos_key="box")
            outlines = [
                (merged_rect.x, merged_rect.y, merged_rect.xx, merged_rect.yy)
                for merged_rect in merged_page_rects[self.page]
            ]
            mocked_para = {
                "chars": para_chars,
                "text": para_text,
                "page": self.page,
                "outline": outlines[0],
                "type": "PARAGRAPH_1",
                "index": idx,
                "continued": False,
                "syllabus": 0,
                "page_merged_paragraph": None,
            }
            mocked_paras.append(mocked_para)
        return mocked_paras

    def get_mocked_chars(self, para_text, para_idx, start=100):
        mocked_chars = []
        for idx, each_char in enumerate(list(para_text)):
            mocked_char = {
                "text": each_char,
                "box": [idx, start + para_idx, idx + 1, start + para_idx + 1],
                "page": self.page,
            }
            mocked_chars.append(mocked_char)
        return mocked_chars


def generate_rules_paras(law_rules, page=0):
    return {
        "paragraphs": RulePara(law_rules, page=page).get_mocked_paras(),
        "syllabuses": [{"index": 0, "level": 1, "parent": -1, "children": [], "title": ""}],
    }


class MockedRule:
    def __init__(self, i, content):
        self.id = i
        self.content = content

    def add_ranges(self, value):
        self.ranges.append(value)

    @cached_property
    def ranges(self):
        return []


def generate_mocked_paras(para_texts, page=0, start=0):
    mock_rules = [MockedRule(i, text) for i, text in enumerate(para_texts, start=start)]
    return generate_rules_paras(mock_rules, page=page)


def format_diff_result(diff, rule_map):
    if diff["type"] == "para_delete":
        diff["right_idxes"] = diff["right_eles"] = []
        diff["right_box"] = {}
        return [
            {
                "type": "para_delete",
                "equal": False,
                "left": [rule_map[idx]],
                "right": [],
            }
            for idx in diff["left_idxes"]
        ]
    if diff["type"] == "para_insert":
        diff["left_idxes"] = diff["left_eles"] = []
        diff["left_box"] = {}
        return [
            {
                "type": "para_insert",
                "equal": False,
                "left": [],
                "right": [rule_map[idx]],
            }
            for idx in diff["right_idxes"]
        ]

    for box in chain(*chain(diff["left_box"].values(), diff["right_box"].values())):
        for idx in range(box[1] - 100, box[3] - 100):
            if box[0] == box[2]:
                continue
            rule_map[idx].add_ranges((box[0], box[2]))
    ret = {
        "type": diff["type"],
        "equal": diff["type"] == "equal" and len(diff["left_idxes"]) == 1 == len(diff["right_idxes"]),
        "left": [rule_map[idx] for idx in diff["left_idxes"]],
        "right": [rule_map[idx] for idx in diff["right_idxes"]],
    }
    return [ret]


def calc_diff_ratio(result, ele_keys=("left_eles", "right_eles")):
    chars = equal = 0
    for diff in result:
        count = sum(map(len, [para.origin_chars for para in chain(*[diff[ele] for ele in ele_keys])]))
        chars += count
        equal += diff["ratio"] * count
    return chars and equal * 100 // chars
