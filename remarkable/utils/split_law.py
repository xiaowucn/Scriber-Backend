# -*-coding:utf-8-*-
import itertools
import json
import logging
import re

from utensils.zip import read_zip_first_file

from remarkable.common.pattern import PatternCollection

P_EMPTY = re.compile(r"[^\S\n]")
P_NON_SENTENCE = re.compile(r"(?<![。！？：；.!?:;])\n")
P_REMOVE_JIE = re.compile(r"\n第?[一二三四五六七八九十零百千\d]{1,6}?节.+[^。！？：；.!?:;]$")
P_SECTION_TIAO = re.compile(r"^(?P<tiao>第?[一二三四五六七八九十零百千\d]{1,6}?条|\d+(\.\d+)*)\s*")

P_LEGISLATION_ZHANG = PatternCollection(
    [
        re.compile(r"^第?[一二三四五六七八九十零百千]{1,6}?章.*?$"),
        re.compile(r"^第?\d{1,6}?章.*?$"),
    ]
)
P_LEGISLATION_JIE = PatternCollection(
    [
        re.compile(r"^第?[一二三四五六七八九十零百千]{1,6}?节.*?$"),
        re.compile(r"^第?\d{1,6}?节.*?$"),
    ]
)
P_LEGISLATION_TIAO = PatternCollection(
    [
        re.compile(r"^第?[一二三四五六七八九十零百千]{1,6}?条\s*.*?$"),
        re.compile(r"^第?\d{1,6}?条\s*.*?$"),
        re.compile(r"^第.{1,6}?条?至第?.{1,6}?条$"),
    ]
)

P_LEGISLATION_NUM_DASH = re.compile(r"^\d+-(\d+-)*\d+\s+")
P_LEGISLATION_NUM_CHINESE = re.compile(r"^[一二三四五六七八九十零百千]+、")
P_LEGISLATION_NUM_POINT = re.compile(r"^\d+\.(\d+\.)*\d+\s+")


class LegislationSplitNode:
    def __init__(self, patterns: list = None, parent: "LegislationSplitNode" = None):
        if not isinstance(patterns, PatternCollection):
            patterns = PatternCollection(patterns)
        self.patterns = patterns
        self.parent = parent
        self.children = []

    def __repr__(self, level=0):
        indent = "  " * level
        parent_patterns = self.parent.patterns if self.parent else None
        representation = f"{indent}LegislationSplitNode(patterns={self.patterns}, parent_patterns={parent_patterns})\n"

        for child in self.children:
            representation += child.__repr__(level + 1)

        return representation

    def append_child(self, child: "LegislationSplitNode"):
        self.children.append(child)

    def is_leaf(self) -> bool:
        return len(self.children) == 0

    def ancestor_nodes(self) -> list["LegislationSplitNode"]:
        return_nodes = [self]
        node = self
        while node.parent:
            node = node.parent
            return_nodes.append(node)

        return return_nodes

    def available_pattern_nodes(self) -> list["LegislationSplitNode"]:
        available_nodes = self.ancestor_nodes()
        if not self.is_leaf():
            available_nodes.extend(self.children)

        return available_nodes

    def is_child(self, node: "LegislationSplitNode") -> bool:
        return node in self.children


class LegislationSplit:
    def __init__(self):
        self.pattern_tree_root = self.build_pattern_tree()
        self.current_node = self.pattern_tree_root

    def build_pattern_tree(self) -> LegislationSplitNode:
        tree_map = {
            "patterns": [],
            "children": [
                {
                    "patterns": P_LEGISLATION_ZHANG,
                    "children": [
                        {"patterns": P_LEGISLATION_TIAO, "children": []},
                        {"patterns": P_LEGISLATION_NUM_POINT, "children": []},
                        {
                            "patterns": P_LEGISLATION_JIE,
                            "children": [
                                {"patterns": P_LEGISLATION_NUM_POINT, "children": []},
                            ],
                        },
                    ],
                },
                {
                    "patterns": P_LEGISLATION_TIAO,
                    "children": [],
                },
                {
                    "patterns": P_LEGISLATION_NUM_DASH,
                    "children": [],
                },
                {"patterns": P_LEGISLATION_NUM_CHINESE, "children": []},
            ],
        }
        root_node = self._build_tree(tree_map)
        return root_node

    def _build_tree(self, child_map: dict, parent: LegislationSplitNode | None = None):
        node = LegislationSplitNode(parent=parent, patterns=child_map.get("patterns", []))
        for _map in child_map.get("children", []):
            child_node = self._build_tree(_map, node)
            node.append_child(child_node)

        return node

    def match_legislation(self, text: str) -> bool:
        available_nodes = self.current_node.available_pattern_nodes()

        for pattern_node in available_nodes:
            if pattern_node.patterns.nexts(text):
                if self.current_node.is_child(pattern_node):
                    self.current_node = pattern_node
                return True

        return False

    def legislation_split(
        self, elements: list[dict], ignore_top_unmatch=False, ignore_bottom_extra=False
    ) -> list[list[dict[str, int]]]:
        split_list = []
        is_match = False
        for element in elements:
            element_index = element["index"]
            text = element.get("text")
            typ = element.get("type")
            if typ in ["PAGE_HEADER", "PAGE_FOOTER"]:
                continue

            if text and self.match_legislation(text.strip()):
                is_match = True
                split_list.append([element])
                logging.debug(f"matched: element_index:{element_index}, {text}")
            else:
                if ignore_top_unmatch and not split_list:
                    continue
                if is_match is False or typ in ["TABLE"]:
                    logging.debug(f"unmatched {text=}")
                    split_list.append([element])
                else:
                    last_type = split_list[-1][0]["type"]
                    if last_type in ["TABLE"]:
                        logging.debug("unmatched Table, new part...")
                        split_list.append([element])
                    else:
                        split_list[-1].append(element)
                        logging.debug(f"append {text=}")

        if ignore_bottom_extra and split_list and len(split_list[-1]) > 1:
            for idx, ele in enumerate(split_list[-1][1:], start=1):
                text = ele.get("text")
                if text and text.strip().startswith("附表 "):
                    split_list[-1][idx:] = []
                    break

        return split_list


def clean_rule(txt):
    return P_EMPTY.sub("", txt or "")


def filter_rules(split_list: list[list[dict]]):
    result = []
    for elements in split_list:
        if P_LEGISLATION_ZHANG.nexts(elements[0].get("text", "")):
            continue
        if P_LEGISLATION_JIE.nexts(elements[0].get("text", "")):
            continue
        text = "\n".join(clean_rule(ele.get("text")) for ele in elements)
        text = text.strip()
        text = P_REMOVE_JIE.sub("", text)
        text = P_NON_SENTENCE.sub("", text)
        text = P_SECTION_TIAO.sub(r"\g<tiao>　", text)
        if text:
            result.append({"text": text})

    return result


def split_interdoc(interdoc_path):
    interdoc_data = json.loads(read_zip_first_file(interdoc_path))

    element_contents = interdoc_data.get("paragraphs", [])
    if syllabuses := interdoc_data.get("syllabuses", []):
        top_index = syllabuses[0]["element"]
        if isinstance(top_index, int):
            element_contents = list(itertools.dropwhile(lambda ele: ele["index"] < top_index, element_contents))

    split = LegislationSplit()
    split_list = split.legislation_split(element_contents, ignore_top_unmatch=True, ignore_bottom_extra=True)

    rules = filter_rules(split_list)
    rules_text = [ele["text"] for ele in rules]
    return rules_text
