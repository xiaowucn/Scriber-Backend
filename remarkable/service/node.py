import html
import json
import logging
import re
import uuid
from collections import Counter, defaultdict
from copy import deepcopy
from functools import lru_cache
from uuid import uuid4

from pdfparser.utils.autodoc.content_util import delete_whitespace

P_SDT_XPATH = re.compile(r"/w:sdt\[\d+\]|/w:sdtContent\[\d+\]")

XPATH_MAPPING = {
    "doc": "/w:document[{}]",
    "body": "/w:body[{}]",
    "section": "/w:section[{}]",
    "sdt": "/w:sdt[{}]",
    "paragraph": "/w:p[{}]",
    "numbering": "/w:p[{}]",
    "table": "/w:tbl[{}]",
    "text": "/w:r[{}]",
    "table_row": "/w:tr[{}]",
    "table_cell": "/w:tc[{}]",
}


def set_keys(data, keys, value):
    if not isinstance(data, dict):
        return False

    if not keys or not isinstance(keys, (list, tuple)):
        return False

    last = keys[-1]
    if len(keys) == 1:
        data[last] = value
        return True

    for key in keys[:-1]:
        if not data.get(key):
            data[key] = {}
            data = data[key]
        else:
            data = data.setdefault(key, {})

    data[last] = value
    return True


def get_keys(data, keys, default=None):
    if not isinstance(data, dict):
        return default

    if not keys or not isinstance(keys, (list, tuple)):
        return None

    last = keys[-1]
    if len(keys) == 1:
        return data.get(last, default)

    for key in keys[:-1]:
        data = data.get(key) or {}

    return data.get(last, default)


def find_group(depth, group_stack, transform):
    if transform and "repeat" in transform["func"]:
        if not group_stack:
            group_stack.append({"depth": depth, **transform})
        elif depth <= group_stack[-1]["depth"] and group_stack[-1]["id"] != transform["id"]:
            while group_stack and depth <= group_stack[-1]["depth"]:
                group_stack.pop()
            group_stack.append({"depth": depth, **transform})
        elif group_stack[-1]["id"] != transform["id"] or depth > group_stack[-1]["depth"]:
            group_stack.append({"depth": depth, **transform})
        return group_stack[-1]["var"][0]
    if group_stack and depth > group_stack[-1]["depth"]:
        return group_stack[-1]["var"][0]
    if group_stack:
        group_stack.pop()
        return find_group(depth, group_stack, transform)
    return None


def get_node_by_xpath(xpath, xpath_to_node):
    return xpath_to_node.get(xpath)


def xpath_range_text(text, start=None, end=None, numbering_len=0):
    # 如果只有start，没有end，就是取后半段数据，后半段应该需要包含空白字符
    count = 0
    if start and end is None:
        for char_idx, char in enumerate(text):
            if count == start:
                return text[char_idx:]
            if numbering_len > char_idx or delete_whitespace(char):
                count += 1

    start = start or 0
    if start >= len(delete_whitespace(text)):
        return ""
    pos_mapping = {}
    count = 0
    for char_idx, char in enumerate(text):
        if numbering_len > char_idx or delete_whitespace(char):
            pos_mapping[count] = char_idx
            count += 1
    pos_mapping[count] = len(text)
    if end is None:
        end = count
    return text[pos_mapping.get(start, 0) : pos_mapping.get(end, count)]


def split_option(option):
    if "==" in option:
        left, right = option.split("==")
        return left, "==", right
    if "!=" in option:
        left, right = option.split("!=")
        return left, "!=", right
    return None, None, None


class NodeIter:
    def __init__(self, node):
        self.node = node
        self.stack = [node]

    def find_node_by_path(self, node, path):
        if not path:
            return node
        if path[0] >= len(node.content):
            return None
        return self.find_node_by_path(node.content[path[0]], path[1:])

    def __next__(self):
        if len(self.stack) == 0:
            raise StopIteration()
        node = self.stack.pop()
        if node.type != "text":
            self.stack.extend(node.content[::-1])
        return node


class Node:
    P_DOC_PR = re.compile(r"(?P<a>docPr(?:[^>]*) id=')(?P<id>\d+)'")

    def __init__(self, node, parent=None, root=None, **options):
        self.is_root = not parent
        self.node = node
        self._root = root
        self.type = node["type"]
        self.attrs = node.get("attrs", {})
        self.xpath = node.get("xpath")
        self._xpath_to_node = {}
        if not self.attrs.get("id"):
            if self.xpath:
                self.attrs["id"] = self.xpath
            else:
                self.attrs["id"] = str(uuid4())
        self.marks = node.get("marks", [])
        self.parent = parent
        if self.type != "text":
            self.content = []
            for child in node.get("content", []):
                _root = root
                if self.is_root:
                    _root = self
                self.content.append(NODE_MAPPING.get(child["type"], Node)(child, self, _root, **options))
        else:
            self.content = node["text"]

    def __iter__(self):
        return NodeIter(self)

    @property
    def root(self):
        if self.is_root:
            return self
        return self._root

    @root.setter
    def root(self, _root):
        self._root = _root

    @property
    def xpath_to_node(self):
        if not self._xpath_to_node:
            xpath_to_node = defaultdict(list)
            for node in self:
                xpath_to_node[node.xpath].append(node)
            self._xpath_to_node = xpath_to_node
        return self._xpath_to_node

    @classmethod
    @lru_cache(maxsize=128)
    def get_style_by_id(cls, root, style_id):
        res = []
        if not style_id:
            return []
        if style := get_keys(root.attrs, ["docStyles", "mapping", style_id]):
            res.append(style)
            if style.get("children", {}).get("basedOn"):
                res.extend(cls.get_style_by_id(root, style["children"]["basedOn"]["value"]))
        return res

    @property
    def reference_styles(self):
        if self.root and self.attrs.get("properties", {}).get("pStyle"):
            return self.get_style_by_id(self.root, self.attrs["properties"]["pStyle"].get("attributes", {}).get("val"))
        return []

    @property
    def super_script(self):
        return False

    @property
    def bold(self):
        if self.attrs.get("properties", {}).get("rPr", {}).get("children", {}).get("b"):
            return True
        for item in self.reference_styles:
            if item.get("children", {}).get("rPr", {}).get("children", {}).get("b"):
                return True
        return False

    @property
    def depth(self):
        cnt = 0
        curr = self
        while curr.parent:
            curr = curr.parent
            cnt += 1
        return cnt

    @property
    def text(self):
        res = ""
        for node in self:
            if (
                node.type == "text"
                and node.parent
                and node.parent.type not in ("footnoteReference", "endnoteReference")
            ):
                res += node.content
        return res

    @property
    def id(self):
        return self.attrs.get("id")

    @text.setter
    def text(self, _text):
        if self.type == "text":
            self.content = _text
        else:
            if self.content:
                for child_idx, child in enumerate(self.content):
                    if child.type not in ("bookmark", "br"):
                        child.text = _text
                        self.content = self.content[: child_idx + 1]
                        break

    @property
    def old_transform(self):
        transform = None
        if self.type != "text":
            transform = self.attrs.get("ctrlTemplate")
        else:
            template_mark = ([mark for mark in self.marks if mark["type"] == "ctrl_template"] or [None])[0]
            if template_mark:
                transform = template_mark["attrs"]
        if transform and transform.get("func") == "if" and len(transform.get("var", [])) == 1:
            transform["var"] = ["exist", transform["var"][0]]
        return transform

    @property
    def ctrl_tags(self):
        tags = []
        if self.type != "text":
            if "areaInfo" in self.attrs:
                tags = (self.attrs["areaInfo"].get("glazer") or {}).get("ctrlTags") or []
            else:
                tags = (self.attrs.get("glazer") or {}).get("ctrlTags") or []
        else:
            template_mark = ([mark for mark in self.marks if mark["type"] == "ctrl_tags"] or [None])[0]
            if template_mark:
                tags = template_mark["attrs"]["tags"] or []
        return tags

    @ctrl_tags.setter
    def ctrl_tags(self, tags):
        if not tags:
            return
        if self.type != "text":
            if "areaInfo" in self.attrs:
                set_keys(self.attrs, ["areaInfo", "ctrlTags"], tags)
            else:
                set_keys(self.attrs, ["glazer", "ctrlTags"], tags)
        else:
            template_mark = ([mark for mark in self.marks if mark["type"] == "ctrl_tags"] or [None])[0]
            if not template_mark:
                template_mark = {"type": "ctrl_tags", "attrs": {"tags": []}}
                self.marks.append(template_mark)
            set_keys(template_mark, ["attrs", "tags"], tags)

    def transforms(self, func=None):
        transforms = self.ctrl_tags

        if not transforms:
            transform = self.old_transform
            if transform:
                transforms = [transform]
        if func:
            transforms = [transform for transform in transforms if transform["func"] == func]
        for transform in transforms:
            if transform.get("func") == "if" and len(transform.get("var", [])) == 1:
                transform["var"] = ["exist", transform["var"][0]]
        return transforms

    def get_transforms(self, func=None):
        res = []
        for node in self:
            transforms = node.transforms(func)
            for transform in transforms:
                if not res or res[-1]["id"] != transform["id"]:
                    res.append({**transform, "nodes": [node]})
                else:
                    res[-1]["nodes"].append(node)
        return res

    def get_child_by_type(self, node_type, include_self=False):
        res = []
        if include_self and self.type == node_type:
            res.append(self)
        if self.type != "text":
            for child in self.content:
                if child.type == node_type:
                    res.append(child)
                res.extend(child.get_child_by_type(node_type))
        return res

    def get_child_by_types(self, node_types, include_self=False):
        if include_self and self.type in node_types:
            return [self]

        res = []
        if self.type != "text":
            for child in self.content:
                if child.type in node_types:
                    res.append(child)
                else:
                    res.extend(child.get_child_by_types(node_types))
        return res

    def get_child_by_xpath(self, xpath, include_self=False):
        if not xpath:
            return []
        res = []
        if include_self and self.xpath == xpath:
            res.append(self)
        if self.type != "text":
            for child in self.content:
                if child.xpath == xpath:
                    res.append(child)
                    continue
                res.extend(child.get_child_by_xpath(xpath))
        return res

    @staticmethod
    def update_node_id(node):
        for item in node:
            if item.attrs.get("id") is not None:
                item.attrs["id"] = uuid4().hex

    def clone(self, reset_id=True):
        node = self.__class__(json.loads(json.dumps(self.to_json())), self.parent)
        if reset_id:
            self.update_node_id(node)
        return node

    def is_label_point(self):
        label_mark = [mark for mark in self.marks if mark["type"] in ("material", "annotation-tip")]
        if label_mark:
            return True
        label_mark = [
            mark
            for mark in self.marks
            if mark["type"] in ("quadruple",) and mark["attrs"]["quadruple"].get("type", "") != "placeholder"
        ]
        if label_mark:
            return True
        return False

    def get_quadruples(self):
        quadruples = []
        prev_quadruple_id = None
        group_stack = []
        for node in self:
            transforms = (node.transforms("repeat") + node.transforms("section_repeat")) or [None]
            group = find_group(node.depth, group_stack, transforms[0])
            if node.type != "text":
                continue
            quadruple_mark = ([mark for mark in node.marks if mark["type"] == "quadruple"] or [None])[0]
            if not quadruple_mark:
                continue
            quadruple_id = quadruple_mark["attrs"]["id"]
            if quadruple_id == prev_quadruple_id:
                quadruples[-1]["nodes"].append(node)
                quadruples[-1]["text"] += node.text
            else:
                quadruples.append(
                    {
                        "nodes": [node],
                        "id": quadruple_id,
                        "quadruple": quadruple_mark["attrs"]["quadruple"],
                        "text": node.text,
                        "group": group,
                        "groups": [group_["var"][0] for group_ in group_stack],
                    }
                )
            prev_quadruple_id = quadruple_id
        return quadruples

    def get_if_transforms(self):
        group_stack = []
        for node in self:
            transforms = (node.transforms("repeat") + node.transforms("section_repeat")) or [None]
            group = find_group(node.depth, group_stack, transforms[0])
            for transform in node.transforms("if"):
                transform["group"] = group
                transform["groups"] = [group_["var"][0] for group_ in group_stack]

        if_transforms = []
        for transform in self.get_transforms("if"):
            if len(transform["var"]) == 1:
                transform["var"] = ["exist", transform["var"][0]]
            if_transforms.append(transform)
        return if_transforms

    def get_annotation_tips(self):
        annotation_tips = []
        prev_annotation_tip_id = None
        for node in self:
            annotation_tip_mark = ([mark for mark in node.marks if mark["type"] == "annotation-tip"] or [None])[0]
            if not annotation_tip_mark:
                continue
            annotation_tip_id = annotation_tip_mark["attrs"]["id"]
            if annotation_tip_id == prev_annotation_tip_id:
                annotation_tips[-1]["nodes"].append(node)
                annotation_tips[-1]["text"] += node.text
            else:
                annotation_tips.append(
                    {
                        "nodes": [node],
                        "id": annotation_tip_id,
                        "attr": annotation_tip_mark["attrs"]["tip"],
                        "text": node.text,
                        "group": None,
                    }
                )
            prev_annotation_tip_id = annotation_tip_id

        return annotation_tips

    def get_materials(self):
        materials = []
        prev_material_id = None
        for node in self:
            material_mark = ([mark for mark in node.marks if mark["type"] == "material"] or [None])[0]
            if not material_mark:
                continue
            material_id = material_mark["attrs"]["id"]
            if material_id == prev_material_id:
                materials[-1]["nodes"].append(node)
                materials[-1]["text"] += node.text
            else:
                materials.append(
                    {
                        "nodes": [node],
                        "id": material_id,
                        "attrs": material_mark["attrs"],
                        "text": node.text,
                        "group": None,
                    }
                )
            prev_material_id = material_id

        for material in materials[::-1]:
            if "materials" not in material["attrs"] or not material["attrs"]["materials"]:
                materials.remove(material)
                continue
            material_option = material["attrs"]["materials"][0]["option"]
            left, op, right = split_option(material_option)
            if left and op and right:
                material.update({"key": left})
            else:
                material.update({"key": None})
        return materials

    def extend(self, nodes, before=False):
        for idx, child in enumerate(self.parent.content):
            if child is self:
                if before:
                    self.parent.content = self.parent.content[:idx] + nodes + self.parent.content[idx:]
                else:
                    self.parent.content = self.parent.content[: idx + 1] + nodes + self.parent.content[idx + 1 :]
                break
        for node in nodes:
            node.root = self.root
            node.parent = self.parent

    def replace(self, nodes):
        for idx, child in enumerate(self.parent.content):
            if child is self:
                self.parent.content = self.parent.content[:idx] + nodes + self.parent.content[idx + 1 :]
                break
        for node in nodes:
            node.parent = self.parent

    def before(self, nodes):
        for idx, child in enumerate(self.parent.content):
            if child is self:
                self.parent.content = self.parent.content[:idx] + nodes + self.parent.content[idx:]
                break
        for node in nodes:
            node.parent = self.parent

    def delete(self):
        self.parent.content = [node for node in self.parent.content if node is not self]

    def xpath_range_text(self, start=None, end=None):
        return xpath_range_text(self.text, start, end)

    def tables(self):
        res = []
        for node in self:
            if node.type == "table":
                res.append(node)
        return res

    def set_glazer_attr(self, key, value):
        if not self.attrs.get("glazer"):
            self.attrs["glazer"] = {"attributes": {}, "children": []}
        self.attrs["glazer"].setdefault("attributes", {})[key] = value

    def delete_glazer_attr(self, key):
        if key in get_keys(self.attrs, ["glazer", "attributes"], {}):
            self.attrs["glazer"]["attributes"].pop(key)

    def get_glazer_attr(self, key):
        return ((self.attrs.get("glazer") or {}).get("attributes") or {}).get(key)

    @classmethod
    def mv_numbering(cls, doc, old_root, num_id):
        assert old_root, "root node is missing"
        new_number = deepcopy(old_root.attrs["numbering"]["instance"][num_id])
        new_abstract_number = deepcopy(
            old_root.attrs["numbering"]["abstract"][new_number["children"]["abstractNumId"]["value"]]
        )
        new_abstract_num_id = doc.next_abstract_number_id
        new_abstract_number["attributes"]["abstractNumId"] = new_abstract_num_id
        new_abstract_number["children"]["nsid"]["attributes"]["val"] = doc.next_ns_id
        new_abstract_number["children"]["tmpl"]["attributes"]["val"] = doc.next_tmpl_id
        new_number["attributes"]["numId"] = doc.next_number_id
        new_number["children"]["abstractNumId"]["value"] = new_abstract_num_id
        new_number["children"]["abstractNumId"]["attributes"]["val"] = new_abstract_num_id
        doc.attrs["numbering"]["instance"][new_number["attributes"]["numId"]] = new_number
        doc.attrs["numbering"]["abstract"][new_abstract_num_id] = new_abstract_number
        return new_number, new_abstract_number

    @classmethod
    def mv_numbering_of_node(cls, doc, node, node_root=None):
        root = node.root or node_root
        return cls.mv_numbering(doc, root, node.attrs["numId"])

    def clone_number(self, number_id):
        doc = self
        while doc.type != "doc":
            doc = self.parent
        new_number = deepcopy(doc.attrs["numbering"]["instance"][number_id])
        new_abstract_number = deepcopy(
            doc.attrs["numbering"]["abstract"][new_number["children"]["abstractNumId"]["value"]]
        )
        new_abstract_number["attributes"]["abstractNumId"] = self.next_abstract_number_id
        new_abstract_number["children"]["nsid"]["attributes"]["val"] = self.next_ns_id
        new_abstract_number["children"]["tmpl"]["attributes"]["val"] = self.next_tmpl_id
        new_number["attributes"]["numId"] = doc.next_number_id
        new_number["children"]["abstractNumId"]["value"] = new_abstract_number["attributes"]["abstractNumId"]
        new_number["children"]["abstractNumId"]["attributes"]["val"] = new_abstract_number["attributes"][
            "abstractNumId"
        ]
        doc.attrs["numbering"]["instance"][new_number["attributes"]["numId"]] = new_number
        doc.attrs["numbering"]["abstract"][new_abstract_number["attributes"]["abstractNumId"]] = new_abstract_number
        return new_number["attributes"]["numId"], new_abstract_number["attributes"]["abstractNumId"]

    @property
    def next_number_id(self):
        if not self.attrs["numbering"].get("instance"):
            self.attrs["numbering"]["instance"] = {}
        numbers = [int(number) for number in self.attrs["numbering"]["instance"].keys()]
        if numbers:
            return str(max(numbers) + 1)
        return "1"

    @property
    def next_abstract_number_id(self):
        if not self.attrs["numbering"].get("abstract"):
            self.attrs["numbering"]["abstract"] = {}
        numbers = [int(number) for number in self.attrs["numbering"]["abstract"].keys()]
        if numbers:
            return str(max(numbers) + 1)
        return "1"

    @property
    def next_ns_id(self):
        numbers = [
            int(get_keys(number, ["children", "nsid", "attributes", "val"]) or "0", 16)
            for number in self.attrs["numbering"]["abstract"].values()
        ]
        if numbers:
            return hex(max(numbers) + 1)[2:].upper().zfill(8)
        return "00000000"

    @property
    def next_tmpl_id(self):
        numbers = [
            int(get_keys(number, ["children", "tmpl", "attributes", "val"]) or "0", 16)
            for number in self.attrs["numbering"]["abstract"].values()
        ]
        if numbers:
            return hex(max(numbers) + 1)[2:].upper().zfill(8)
        return "00000000"

    @property
    def next_drawing_id(self):
        doc_pr_id = 1
        for node in self.root:
            if node.type == "drawing":
                pr_id = self.P_DOC_PR.search(node.attrs["ooxml"])
                if not pr_id:
                    continue
                doc_pr_id = max(int(pr_id.group("id")), doc_pr_id)
        return doc_pr_id + 1

    def update_drawing_id(self, drawing_id=None):
        if drawing_id is None:
            drawing_id = self.next_drawing_id
        for node in self:
            if node.type == "drawing":
                if self.P_DOC_PR.search(node.attrs["ooxml"]):
                    node.attrs["ooxml"] = self.P_DOC_PR.sub(r"\g<a>{}'".format(drawing_id), node.attrs["ooxml"])
                    node.attrs["src"] = f"{drawing_id}.png"
                    node.attrs["name"] = f"{drawing_id}.png"
                drawing_id += 1
        return drawing_id

    @property
    def outline_level(self):
        if self.type not in ("paragraph", "numbering"):
            return None
        level = (
            self.attrs.get("properties", {}).get("outlineLvl", {}).get("attributes", {}).get("val")
            or self.get_heading_from_ref_style()
        )
        if level is None:
            return None
        return int(level)

    def get_heading_from_ref_style(self):
        for item in self.reference_styles:
            level = (
                item.get("children", {})
                .get("pPr", {})
                .get("children", {})
                .get("outlineLvl", {})
                .get("attributes", {})
                .get("val")
            )
            if level is not None:
                return level
        return None

    @property
    def prev(self):
        prev = None
        for child in self.parent.content:
            if child is self:
                return prev
            prev = child
        return None

    @staticmethod
    def gen_xpath(node, parent_xpath, idx=1):
        """
        会覆盖的原始的xpath数据，慎重使用
        :param node:
        :param parent_xpath:
        :param idx:
        :return:
        """
        if node.type in XPATH_MAPPING.keys():
            xpath = XPATH_MAPPING[node.type].format(idx)
            node.xpath = parent_xpath + xpath
            if node.type == "text":
                return
        else:
            node.xpath = parent_xpath + f"/w:{node.type}[{idx}]"
        for sub_idx, sub_node in enumerate(node.content, start=1):
            Node.gen_xpath(sub_node, node.xpath, sub_idx)

    def delete_xpath(self):
        """
        慎重使用
        """
        self.xpath = None
        if self.type == "text":
            return
        for sub_node in self.content:
            sub_node.delete_xpath()

    def update_text(self, text):
        txt_nodes = self.get_child_by_type("text", include_self=True)
        if not txt_nodes:
            return
        txt_nodes[0].text = text
        for node in txt_nodes[1:]:
            node.text = ""

    def remove_quadruple(self):
        self.marks = [mark for mark in self.marks if mark["type"] != "quadruple"]

    @staticmethod
    def create_correlation_mark(correlation):
        return {
            "type": "quadruple",
            "attrs": {
                "id": correlation["id"],
                "quadruple": {
                    "correlation": correlation,
                    "updated": correlation["status"] == "find",
                    "type": "correlation",
                },
            },
        }

    def append_mark(self, mark):
        for text_node in self.get_child_by_type("text", True):
            text_node.marks.append(mark)

    def to_json(self, delete_cell_empty_run=True):
        if self.type == "doc":
            for child in self:
                if not delete_cell_empty_run and (
                    child.type == "table_cell" or (child.parent and child.parent.type == "table_cell")
                ):
                    continue
                if child.type != "text":
                    child.content = [c for c in child.content if c.type != "text" or c.content]
        node = {"attrs": self.attrs, "marks": self.marks, "type": self.type, "xpath": self.xpath}
        if self.type == "text":
            node["text"] = self.content  # replace('>', '&gt;').replace('<', '&lt;')
        else:
            node["content"] = [child.to_json() for child in self.content]
        return node

    def is_combobox_node(self):
        if self.type != "text":
            return False
        for mark in self.marks:
            if mark["type"] != "ctrl_tags":
                continue
            for tag in mark.get("attrs", {}).get("tags", []):
                if tag.get("data", {}).get("comboBox"):
                    return True
        return False

    def ensure_actual_pos(self, start, length):
        begin = start
        end = start + length
        for idx, _char in enumerate(self.text):
            if idx > end:
                break
            if not _char.strip():
                if idx < start:
                    begin -= 1
                elif start <= idx < end:
                    length -= 1
        return begin, length

    def get_docx_run_meta(self, start, end):
        if self.type not in ("paragraph", "numbering"):
            return None
        length = end - start
        start, length = self.ensure_actual_pos(start, length)
        para_char_idxs = []
        text_nodes = [con for con in self.content if con.type == "text"]

        for run_idx, run in enumerate(text_nodes):
            run_length = len(run.text)
            para_char_idxs.extend([run_idx] * run_length)
        char_idxs = para_char_idxs[start : start + length]
        run_idxs = sorted(set(char_idxs))
        res = [
            {
                "xpath": text_nodes[run_idxs[0]].xpath,
                "start": Counter(para_char_idxs[:start])[run_idxs[0]],
                "length": min([Counter(char_idxs)[run_idxs[0]], length]),
            }
        ]
        length -= res[-1]["length"]
        for run_idx in run_idxs[1:]:
            if length <= 0:
                break
            res.append(
                {"xpath": text_nodes[run_idx].xpath, "start": 0, "length": min(len(text_nodes[run_idx].text), length)}
            )
            length -= res[-1]["length"]
        return res

    @property
    def complete_text(self):
        if self.type == "numbering" and (numbering := self.attrs.get("template", "").replace("%1", "1")):
            return numbering + self.text
        return self.text


class CorrelationNode(Node):
    P_NUM = re.compile(r"\d")

    @classmethod
    def create(cls, text_node, correlation, editer="office", parent=None):
        if isinstance(text_node, (list, tuple)):
            parent = text_node[0].parent
        else:
            parent = text_node.parent
            text_node = [text_node]
        node = cls(
            {"type": "correlation", "content": [], "attrs": {"glazer": {"attributes": {"correlation": correlation}}}},
            parent=parent,
        )

        for item in text_node:
            item.parent = node
        child_nodes = text_node
        if editer == "wps" and (correlation.get("rate") or correlation.get("ratio")):
            has_split = False
            new_child_nodes = []
            for txt_node in text_node:
                if has_split:
                    new_child_nodes.append(txt_node)
                    continue
                if matched := cls.P_NUM.search(txt_node.content):
                    has_split = True
                    start = matched.start()
                    if start != 0:
                        befort_node = txt_node.clone()
                        befort_node.content = befort_node.content[:start]
                        new_child_nodes.append(befort_node)
                    end = matched.end()
                    first_num_node = txt_node.clone()
                    first_num_node.content = first_num_node.content[start:end]
                    first_num_node.set_glazer_attr("is_rate", 1)
                    new_child_nodes.append(first_num_node)

                    txt_node.content = txt_node.content[end:]
                    new_child_nodes.append(txt_node)
            if new_child_nodes:
                child_nodes = new_child_nodes

        node.content = child_nodes
        return node

    @classmethod
    def get_sdtcontent_correlation(cls, node):
        for tag in node.ctrl_tags:
            if tag["func"] and tag["func"].startswith("correlation_"):
                try:
                    func = html.unescape(tag["func"])
                    data = json.loads(func.split("_", maxsplit=2)[-1])
                except Exception as e:
                    logging.exception(e)
                else:
                    return data, data["id"]
        return None, None

    @classmethod
    def remove_correlation_ctrl_tags(cls, node):
        tags = node.ctrl_tags
        indexes = [index for index, item in enumerate(tags) if item["func"].startswith("correlation_")]
        for index in reversed(indexes):
            tags.pop(index)

    @property
    def correlation(self):
        return get_keys(self.attrs, ["glazer", "attributes", "correlation"])

    @property
    def key(self):
        return self.correlation.get("key")


class BookmarkNode(Node):
    @classmethod
    def is_uuid(cls, name):
        if len(name) != 32:
            return False

        try:
            uuid.UUID(name)
            return True
        except ValueError:
            return False

    def is_start(self):
        return self.attrs["xmlName"] == "bookmarkStart"

    def is_end(self):
        return self.attrs["xmlName"] == "bookmarkEnd"

    @property
    def get_bookmark_id(self):
        return self.attrs["elementAttributes"]["id"]

    @property
    def get_bookmark_name(self):
        return self.attrs.get("elementAttributes", {}).get("name")

    def is_glazer_node(self, bookmark_mapping):
        if self.attrs["xmlName"] == "bookmarkEnd":
            if self.get_bookmark_id in bookmark_mapping:
                return True
            return False
        name = self.get_bookmark_name
        return self.is_uuid(name) or name.startswith("rate_")

    def is_correlation_node(self, bookmark_mapping):
        if self.attrs["xmlName"] == "bookmarkEnd":
            if self.get_bookmark_id not in bookmark_mapping:
                return False
            name = bookmark_mapping[self.get_bookmark_id]
        else:
            name = self.attrs.get("elementAttributes", {}).get("name")
        return self.is_uuid(name)


class TextNode(Node):
    @property
    def bold(self):
        for mark in self.marks:
            if mark["type"] == "data_keeper":
                if mark.get("attrs", {}).get("runAttrs", {}).get("properties", {}).get("b"):
                    return True
        return False

    @classmethod
    def create(cls, parent=None, root=None):
        return cls(
            {
                "attrs": {},
                "marks": [
                    {
                        "type": "data_keeper",
                        "attrs": {
                            "runAttrs": {
                                "elementAttributes": {},
                                "properties": {},
                                "glazer": None,
                                "cssClass": "run-text default-style",
                                "id": uuid.uuid4().hex,
                            },
                        },
                    }
                ],
                "type": "text",
                "xpath": None,
                "text": "",
            },
            parent,
            root,
        )


class ParagraphNode(Node):
    @classmethod
    def create(cls, parent=None, root=None):
        return cls(
            {
                "attrs": {
                    "elementAttributes": {},
                    "properties": {},
                    "glazer": None,
                    "cssClass": "editor-node paragraph-node default-style",
                    "id": uuid.uuid4().hex,
                },
                "type": "paragraph",
                "xpath": None,
                "content": [],
            },
            parent,
            root,
        )


class BrNode(Node):
    @classmethod
    def create(cls, parent=None, root=None):
        return cls(
            {
                "attrs": {
                    "elementAttributes": {"type": "page"},
                    "properties": {},
                    "glazer": None,
                    "cssClass": "run-text default-style",
                    "runAttrs": {
                        "elementAttributes": {},
                        "properties": {},
                        "glazer": None,
                        "cssClass": "run-text default-style",
                    },
                },
                "type": "br",
                "xpath": None,
                "content": [],
            },
            parent,
            root,
        )

    @classmethod
    def render_page_break_node(cls, nodes):
        if not nodes:
            nodes = [ParagraphNode.create()]
        paragraph = nodes[-1]
        if paragraph.type not in ["numbering", "paragraph"]:
            nodes.append(ParagraphNode.create())
            paragraph = nodes[-1]
        paragraph.content.append(cls.create(parent=paragraph))
        return nodes


class TableCellNode(Node):
    def __init__(self, node, parent=None, root=None, **options):
        if options.get("reset_cell_id"):
            if attrs := node.get("attrs"):
                attrs["id"] = None
        super().__init__(node, parent, root, **options)


class TableNode(Node):
    @classmethod
    def create(cls, row_count, col_count, style_mapping):
        pass

    @classmethod
    def create_new_cell(cls, cell, sub_span=0):
        new_cell = {}
        new_cell.update(cell)
        new_cell["sub_row_span"] = cell.get("sub_row_span", 0) + sub_span + 1
        return cell

    def fill_empty_cell_node(self):
        for node in self.get_child_by_type("table_cell"):
            paras = node.get_child_by_type("paragraph")
            if not paras:
                para = ParagraphNode.create(node, self.root)
                node.content.append(para)
                paras = [para]

            if any(para.get_child_by_type("text") for para in paras):
                continue
            text = TextNode.create(paras[0], self.root)
            paras[0].content.append(text)

    def table2sheet(self):
        columns = len(self.attrs.get("colwidth", []))
        rows = []
        content_cell_map = {}
        for row in self.content:
            row_data = []
            grid_before = row.attrs.get("properties", {}).get("gridBefore", {}).get("attributes", {}).get("val")
            if grid_before:
                row_data.extend(
                    int(grid_before)
                    * [
                        {
                            "cell_id": "",
                            "text": "",
                            "col_span": 1,
                            "sub_col_span": 0,
                            "row_span": 1,
                        }
                    ]
                )
            for cell in row.content:
                col_span = cell.attrs.get("colspan", 1)
                text = "".join(
                    text_node.text
                    for text_node in cell.get_child_by_types(
                        {
                            "text",
                        }
                    )
                )
                for i in range(col_span):
                    row_data.append(
                        {
                            "cell_id": cell.attrs.get("id"),
                            "text": text,
                            "col_span": col_span,
                            "sub_col_span": i,
                            "row_span": cell.attrs.get("rowspan", 1),
                        }
                    )
                    content_cell_map[cell.attrs.get("id")] = cell

            if rows:
                sum_col_span = sum(item["col_span"] for item in row_data if not item.get("sub_col_span"))
                if sum_col_span != columns:
                    for index, cell in enumerate(rows[-1]):
                        if cell["row_span"] - cell.get("sub_row_span", 0) > 1:
                            row_data.insert(index, self.create_new_cell(cell))

            rows.append(row_data)
            for i in range(min((item["row_span"] - item.get("sub_row_span", 0) for item in row_data), default=1) - 1):
                temp_row = []
                for cell in row_data:
                    temp_row.append(self.create_new_cell(cell, i))
                rows.append(temp_row)

        sheet = {"merged": [], "rowCount": len(rows), "columnCount": columns, "cells": {}, "id": self.attrs.get("id")}
        for row_index, row in enumerate(rows):
            for col_index, col in enumerate(row):
                sheet["cells"][f"{row_index}_{col_index}"] = col

        return sheet, content_cell_map

    def remove_surround(self):
        """
        移除表格环绕
        """
        if tbl_ppr := get_keys(self.attrs, ["properties", "tblpPr", "attributes"]):
            for _key in ("horzAnchor", "vertAnchor", "leftFromText", "rightFromText", "tblpY", "tblpX"):
                tbl_ppr.pop(_key, None)
        self.attrs["properties"].pop("tblOverlap", None)


NODE_MAPPING = {
    "default": Node,
    "table": TableNode,
    "text": TextNode,
    "paragraph": ParagraphNode,
    "bookmark": BookmarkNode,
    "table_cell": TableCellNode,
    "correlation": CorrelationNode,
    "br": BrNode,
}
