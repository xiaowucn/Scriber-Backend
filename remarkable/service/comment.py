import datetime
import os
import re
import tempfile
import zipfile
from collections import defaultdict
from io import BytesIO
from itertools import chain
from xml.dom import minidom

import pikepdf

from remarkable import config
from remarkable.common.storage import localstorage
from remarkable.pdfinsight.reader import Index, PdfinsightReader
from remarkable.plugins.ext_api.common import is_table_elt
from remarkable.service.node import Node, get_keys

COMMENT_ROOT_TEMPLATE = """<?xml version="1.0" encoding="UTF-8" standalone="yes"?>
<w:comments
    xmlns:wpc="http://schemas.microsoft.com/office/word/2010/wordprocessingCanvas"
    xmlns:mc="http://schemas.openxmlformats.org/markup-compatibility/2006"
    xmlns:o="urn:schemas-microsoft-com:office:office"
    xmlns:r="http://schemas.openxmlformats.org/officeDocument/2006/relationships"
    xmlns:m="http://schemas.openxmlformats.org/officeDocument/2006/math"
    xmlns:v="urn:schemas-microsoft-com:vml"
    xmlns:wp14="http://schemas.microsoft.com/office/word/2010/wordprocessingDrawing"
    xmlns:wp="http://schemas.openxmlformats.org/drawingml/2006/wordprocessingDrawing"
    xmlns:w="http://schemas.openxmlformats.org/wordprocessingml/2006/main"
    xmlns:w14="http://schemas.microsoft.com/office/word/2010/wordml"
    xmlns:w15="http://schemas.microsoft.com/office/word/2012/wordml"
    xmlns:w10="urn:schemas-microsoft-com:office:word"
    xmlns:wpg="http://schemas.microsoft.com/office/word/2010/wordprocessingGroup"
    xmlns:wpi="http://schemas.microsoft.com/office/word/2010/wordprocessingInk"
    xmlns:wne="http://schemas.microsoft.com/office/word/2006/wordml"
    xmlns:wps="http://schemas.microsoft.com/office/word/2010/wordprocessingShape"
    xmlns:wpsCustomData="http://www.wps.cn/officeDocument/2013/wpsCustomData"
    mc:Ignorable="w14 w15 wp14">
</w:comments>
"""

COMMENT_EXTENDED_ROOT_TEMPLATE = """<?xml version="1.0" encoding="UTF-8" standalone="yes"?>
<w:commentsEx
    xmlns:wpc="http://schemas.microsoft.com/office/word/2010/wordprocessingCanvas"
    xmlns:mc="http://schemas.openxmlformats.org/markup-compatibility/2006"
    xmlns:o="urn:schemas-microsoft-com:office:office"
    xmlns:r="http://schemas.openxmlformats.org/officeDocument/2006/relationships"
    xmlns:m="http://schemas.openxmlformats.org/officeDocument/2006/math"
    xmlns:v="urn:schemas-microsoft-com:vml"
    xmlns:wp14="http://schemas.microsoft.com/office/word/2010/wordprocessingDrawing"
    xmlns:wp="http://schemas.openxmlformats.org/drawingml/2006/wordprocessingDrawing"
    xmlns:w="http://schemas.openxmlformats.org/wordprocessingml/2006/main"
    xmlns:w14="http://schemas.microsoft.com/office/word/2010/wordml"
    xmlns:w15="http://schemas.microsoft.com/office/word/2012/wordml"
    xmlns:w10="urn:schemas-microsoft-com:office:word"
    xmlns:wpg="http://schemas.microsoft.com/office/word/2010/wordprocessingGroup"
    xmlns:wpi="http://schemas.microsoft.com/office/word/2010/wordprocessingInk"
    xmlns:wne="http://schemas.microsoft.com/office/word/2006/wordml"
    xmlns:wps="http://schemas.microsoft.com/office/word/2010/wordprocessingShape"
    xmlns:wpsCustomData="http://www.wps.cn/officeDocument/2013/wpsCustomData"
    mc:Ignorable="w14 w15 wp14">
</w:commentsEx>
"""

TEMPLATE_MAPPING = {
    "comments": {
        "partUrl": "/word/comments.xml",
        "contentType": "application/vnd.openxmlformats-officedocument.wordprocessingml.comments+xml",
        "partType": "xml",
        "relationshipType": "http://schemas.openxmlformats.org/officeDocument/2006/relationships/comments",
        "template": COMMENT_ROOT_TEMPLATE,
    },
    "commentsExtended": {
        "partUrl": "/word/commentsExtended.xml",
        "contentType": "application/vnd.openxmlformats-officedocument.wordprocessingml.commentsExtended+xml",
        "partType": "xml",
        "relationshipType": "http://schemas.microsoft.com/office/2011/relationships/commentsExtended",
        "template": COMMENT_EXTENDED_ROOT_TEMPLATE,
    },
    "title": {
        "partUrl": "/docProps/core.xml",
    },
}

P_COMMENT = re.compile(
    r"\$\$\$\$SCRIBER_COMMENT_(?P<comment_id>\d+)"
    r"\$\$\$\$(?P<comment_type>comment_start|comment_end|comment_cell)"
    r"\$\$\$\$(?P<comment>.*?)"
    r"\$\$\$\$(?P<user_name>.*?)"
    r"\$\$\$\$SCRIBER_COMMENT_(?P<comment_id_1>\d+)"
    r"\$\$\$\$\$"
)

PAGE_HEADER_FOOTER = ("PAGE_HEADER", "PAGE_FOOTER")


class XmlReader:
    def __init__(self, path):
        self.path = path
        with open(self.path, "rt") as file:
            self.dom = minidom.parseString(file.read())

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        with open(self.path, "wt") as file:
            file.write(self.dom.toxml())


class CommentReplacer:
    def __init__(self, temp_dir, path):
        self.path = path
        self.temp_dir = temp_dir
        self.zip_dir = os.path.join(self.temp_dir, "zip_dir")
        if not os.path.exists(self.zip_dir):
            os.makedirs(self.zip_dir)

    @classmethod
    def remove_prefix_path(cls, path):
        path = path.lstrip("/")
        if path.startswith("word/"):
            return path[5:]
        return path

    def extract_docx(self):
        with zipfile.ZipFile(self.path, "r") as zip_file:
            zip_file.extractall(self.zip_dir)

    @classmethod
    def create_comment_start(cls, dom, node, comment_id):
        comment_start = dom.createElement("w:commentRangeStart")
        comment_start.setAttribute("w:id", comment_id)
        node.insertBefore(comment_start, node.firstChild)

    @classmethod
    def create_comment_end(cls, dom, node, comment_id):
        comment_end = dom.createElement("w:commentRangeEnd")
        comment_end.setAttribute("w:id", comment_id)
        node.appendChild(comment_end)
        comment_ref = dom.createElement("w:commentReference")
        comment_ref.setAttribute("w:id", comment_id)
        node.appendChild(comment_ref)

    def replace_document_comments(self):
        comments = {}
        document_path = os.path.join(self.zip_dir, "word/document.xml")
        with XmlReader(document_path) as reader:
            nodes = {}
            for node in reader.dom.getElementsByTagName("w:p"):
                matched = P_COMMENT.search("".join(self.get_node_text(node)))
                if matched and matched.group("comment_id") == matched.group("comment_id_1"):
                    nodes[node] = matched.groupdict()
                    comments[matched.group("comment_id")] = matched.groupdict()

            for node, comment_info in nodes.items():
                comment_id = comment_info.get("comment_id")
                comments[comment_id] = comment_info

                if comment_info.get("comment_type") == "comment_cell":
                    for child in node.parentNode.childNodes:
                        if child.nodeName == "w:p":
                            self.create_comment_start(reader.dom, child, comment_id)
                            self.create_comment_end(reader.dom, child, comment_id)

                elif comment_info.get("comment_type") == "comment_start":
                    next_sibling = node.nextSibling
                    while next_sibling and (next_sibling.nodeName not in ("w:tbl", "w:p") or next_sibling in nodes):
                        next_sibling = next_sibling.nextSibling
                    if next_sibling:
                        self.create_comment_start(reader.dom, next_sibling, comment_id)
                elif comment_info.get("comment_type") == "comment_end":
                    prev_sibling = node.previousSibling
                    while prev_sibling and (prev_sibling.nodeName not in ("w:tbl", "w:p") or prev_sibling in nodes):
                        prev_sibling = prev_sibling.previousSibling
                    if prev_sibling:
                        self.create_comment_end(reader.dom, prev_sibling, comment_id)
                node.parentNode.removeChild(node)

        return comments

    @classmethod
    def get_node_text(cls, node):
        texts = []
        for child in node.childNodes:
            if child.nodeName == "#text":
                texts.append(child.nodeValue)
            elif child.childNodes:
                texts.extend(cls.get_node_text(child))
        return texts

    def add_content_type(self, content_type, part_name):
        content_type_path = os.path.join(self.zip_dir, "[Content_Types].xml")
        with XmlReader(content_type_path) as reader:
            root = reader.dom.childNodes[0]
            for item in root.childNodes:
                if item.nodeName == "Override" and item.getAttribute("ContentType") == content_type:
                    return
            element = reader.dom.createElement("Override")
            element.setAttribute("ContentType", content_type)
            element.setAttribute("PartName", part_name)
            root.appendChild(element)

    def add_relation(self, target, relation_type):
        relation_path = os.path.join(self.zip_dir, "word/_rels/document.xml.rels")
        with XmlReader(relation_path) as reader:
            root = reader.dom.childNodes[0]
            ids = []
            for item in root.childNodes:
                if item.nodeName == "Relationship":
                    rid = item.getAttribute("Id")
                    if rid and rid.startswith("rId"):
                        ids.append(int(rid[3:]))
                    if item.getAttribute("Type") == relation_type:
                        return

            max_id = f"rId{max(ids) + 1}"
            element = reader.dom.createElement("Relationship")
            element.setAttribute("Id", max_id)
            element.setAttribute("Target", self.remove_prefix_path(target))
            element.setAttribute("Type", relation_type)
            root.appendChild(element)

    @classmethod
    def create_comment_record(cls, dom, comment_id, comment_info):
        comment = dom.createElement("w:comment")
        comment.setAttribute("w:id", comment_id)
        comment.setAttribute("w:author", comment_info["user_name"])
        comment.setAttribute("w:initials", "r")
        comment.setAttribute("w:date", datetime.datetime.now().isoformat()[:19] + "Z")

        paragraph = dom.createElement("w:p")
        paragraph.setAttribute("w:paraId", cls.get_comment_para_id(comment_id))
        run = dom.createElement("w:r")
        text_node = dom.createElement("w:t")
        text_node.appendChild(dom.createTextNode(comment_info["comment"]))

        run.appendChild(text_node)
        paragraph.appendChild(run)
        comment.appendChild(paragraph)
        dom.childNodes[0].appendChild(comment)

    @classmethod
    def get_comment_para_id(cls, comment_id):
        return hex((int(comment_id) + 1))[2:].zfill(8).lower()

    @classmethod
    def create_comment_ex_record(cls, dom, comment_id):
        comment_ex = dom.createElement("w15:commentEx")
        comment_ex.setAttribute("w15:paraId", cls.get_comment_para_id(comment_id))
        comment_ex.setAttribute("w15:done", "0")
        dom.childNodes[0].appendChild(comment_ex)

    def create_docx(self):
        with BytesIO() as buffer:
            with zipfile.ZipFile(buffer, "w") as zip_file:
                for root, _, files in os.walk(self.zip_dir):
                    for file_ in files:
                        file_path = os.path.join(root, file_)
                        zip_file.write(file_path, arcname=file_path.replace(self.zip_dir, ""))
            return buffer.getvalue()

    def replace(self):
        self.extract_docx()

        with self.get_or_create_part("comments", reset=True) as comment_part:
            comment_mapping = self.replace_document_comments()
            for comment_id, comment_info in comment_mapping.items():
                self.create_comment_record(comment_part.dom, comment_id, comment_info)

        with self.get_or_create_part("commentsExtended", reset=True) as reader:
            for comment_id, _ in comment_mapping.items():
                self.create_comment_ex_record(reader.dom, comment_id)

        return self.create_docx()

    def get_or_create_part(self, part_name, reset=True):
        part_info = TEMPLATE_MAPPING[part_name]
        part_path = os.path.join(self.zip_dir, part_info["partUrl"].lstrip("/"))
        if not os.path.exists(part_path) or reset:
            with open(part_path, "wt") as file:
                file.write(part_info["template"])

            self.add_content_type(part_info["contentType"], part_info["partUrl"])
            self.add_relation(part_info["partUrl"], part_info["relationshipType"])

        return XmlReader(part_path)

    def remove_title(self):
        """删除属性标题"""
        self.extract_docx()
        title_path = os.path.join(self.zip_dir, TEMPLATE_MAPPING["title"]["partUrl"].lstrip("/"))
        with XmlReader(title_path) as reader:
            for node in reader.dom.getElementsByTagName("dc:title"):
                node.parentNode.removeChild(node)
        return self.create_docx()

    def del_document_comments(self):
        """删除批注"""
        document_path = os.path.join(self.zip_dir, TEMPLATE_MAPPING["document"]["partUrl"])
        with XmlReader(document_path) as reader:
            reader.dom.removeChild("w:commentRangeStart")
            reader.dom.removeChild("w:commentRangeEnd")
            reader.dom.removeChild("w:commentReference")
        comment_path = os.path.join(self.zip_dir, TEMPLATE_MAPPING["comments"]["partUrl"])
        if os.path.exists(comment_path):
            os.remove(comment_path)

    def remove_revise(self):
        """删除修订"""

    def gen_clean_docx(self):
        """清稿文件"""
        self.extract_docx()
        self.del_document_comments()
        self.create_docx()
        # with self.get_or_create_part('document') as reader:
        #     # for comment_id, comment_info in comment_mapping.items():
        #     #     self.create_comment_ex_record(reader.dom, comment_id)


def render_comment(comment_id, comment, user_name, comment_type):
    return (
        f"$$$$SCRIBER_COMMENT_{comment_id}"
        f"$$$${comment_type}"
        f"$$$${comment}"
        f"$$$${user_name}"
        f"$$$$SCRIBER_COMMENT_{comment_id}$$$$$"
    )


def get_comment_position_from_interdoc(comment_outlines, interdoc):
    comment_mapping, positions = get_positions_mapping(comment_outlines, interdoc)

    comment_indexes = []

    for result_id, indexes in positions.items():
        prev = []
        prev_result_id = None
        part = []
        for index, cells in sorted(indexes):
            if not prev or (not prev[1] and not cells):
                part.append([index, cells])
            else:
                comment_indexes.append([part, *comment_mapping[result_id]])
                part = [[index, cells]]
            prev = (index, cells)
            prev_result_id = result_id

        if part and prev_result_id:
            comment_indexes.append([part, *comment_mapping[prev_result_id]])

    return sorted(comment_indexes, key=lambda x: x[0][0])


def find_elements_by_outline(element_mapping, page, outline, max_overlap=0.618):
    for item in element_mapping.get(int(page)) or []:
        overlap = PdfinsightReader.overlap_percent(item["outline"], outline, base="min")
        if overlap > max_overlap:
            yield item


def find_cells_by_outline(element, page, outline, max_overlap=0.618):
    for cell_index, cell in element["cells"].items():
        if int(cell["page"]) != int(page):
            continue
        overlap = PdfinsightReader.overlap_percent(cell["box"], outline, base="min")
        if overlap > max_overlap:
            yield tuple(int(item) for item in cell_index.split("_"))


def get_positions_mapping(comment_outlines, interdoc):
    positions = defaultdict(set)
    element_mapping = defaultdict(list)
    for item in sorted(chain(interdoc["tables"], interdoc["paragraphs"]), key=lambda x: x["index"]):
        element_mapping[int(item["page"])].append(item)

    comment_mapping = {}
    for outlines, result_id, comment, user_name in comment_outlines:
        comment_mapping[result_id] = [comment, user_name]
        for page, page_outlines in outlines.items():
            for outline in page_outlines:
                for element in find_elements_by_outline(element_mapping, int(page), outline):
                    cells = []
                    if "cells" in element:
                        cells = list(find_cells_by_outline(element, page, outline))
                    positions[result_id].add((element["index"], tuple(cells)))
    return comment_mapping, positions


def add_comments_in_elements(interdoc, comment_positions):
    element_mapping = {
        item["index"]: item
        for item in sorted(chain(interdoc["tables"], interdoc["paragraphs"]), key=lambda x: x["index"])
    }

    commend_id = 0
    for positions, comment, user_name in comment_positions:
        # 如果没有cells上的
        if not positions[0][1]:
            indexes = [element_index for element_index, _ in positions if element_index in element_mapping]
            start = indexes[0]
            end = indexes[-1]

            if (
                element_mapping[start].get("page_merged_paragraph")
                and element_mapping[start]["page_merged_paragraph"]["paragraph_indices"][0]
            ):
                start = element_mapping[start]["page_merged_paragraph"]["paragraph_indices"][0]

            if (
                element_mapping[end].get("page_merged_paragraph")
                and element_mapping[end]["page_merged_paragraph"]["paragraph_indices"][0]
            ):
                end = element_mapping[end]["page_merged_paragraph"]["paragraph_indices"][0]

            element_mapping[start].setdefault("comment_start", []).append([commend_id, comment, user_name])
            element_mapping[end].setdefault("comment_end", []).append([commend_id, comment, user_name])
            commend_id += 1
        else:
            # 如果批注了一个表格的所有cell。那就批注整个表格
            if len(positions) == 1:
                element = element_mapping[positions[0][0]]
                if set(positions[0][1]) == (
                    tuple(int(_item) for _item in cell_index.split("_")) for cell_index in element["cells"]
                ):
                    element.setdefault("comment_start", []).append([commend_id, comment, user_name])
                    element.setdefault("comment_end", []).append([commend_id, comment, user_name])
                    commend_id += 1
                    continue

            for element_index, cells in positions:
                if element_index not in element_mapping:
                    continue
                element = element_mapping[element_index]
                if element["class"] != "TABLE":
                    continue

                for cell_index, cell in element["cells"].items():
                    if tuple(int(_item) for _item in cell_index.split("_")) in cells:
                        cell.setdefault("comment_cell", []).append([commend_id, comment, user_name])
                        commend_id += 1


def replace_comments(docx):
    # 将docx文档里的批注占位段落 替换为批注
    with tempfile.TemporaryDirectory(dir=config.get_config("web.tmp_dir")) as tmp_dir:
        path = os.path.join(tmp_dir, "comment.temp.docx")
        docx.save(path)

        return CommentReplacer(tmp_dir, path).replace()


def remove_title(filename, body, doc_type):
    with tempfile.TemporaryDirectory(dir=config.get_config("web.tmp_dir")) as tmp_dir:
        full_path = os.path.join(tmp_dir, filename)
        localstorage.write_file(full_path, body)
        if doc_type == ".pdf":
            with pikepdf.open(full_path, allow_overwriting_input=True) as pdf_obj:
                pdf_obj.docinfo.Title = ""
                pdf_obj.save(fix_metadata_version=False)
        else:
            docx = CommentReplacer(tmp_dir, full_path).remove_title()
            full_path = localstorage.write_file(full_path, docx)
        return localstorage.read_file(full_path)


def group_consecutive_numbers(arr: list) -> list:
    # 内部元素必须为int
    if not arr:
        return []
    arr.sort()
    result = []
    group = [arr[0]]
    for i in range(1, len(arr)):
        if arr[i] == arr[i - 1] + 1:
            group.append(arr[i])
        else:
            result.append(group)
            group = [arr[i]]
    result.append(group)
    return result


def get_current_page_front_back_xpath(
    group_blank_pages: list[list[int]], page: int, elements: list[Index], blank_page_dict: dict[int, dict[str, str]]
):
    """获取空白页前后的xpath"""
    for group_index, pages in enumerate(group_blank_pages):
        for blank_page in pages:
            if page + 1 == blank_page:
                # 前一页取最后一个非页眉页脚元素的xpath
                for element in reversed(elements):
                    data = element.data
                    if (temp := data.get("docx_meta", {}).get("xpath")) and data["class"] not in PAGE_HEADER_FOOTER:
                        blank_page_dict[group_index]["front"] = temp
                        break
            if page - 1 == blank_page:
                # 后一页取第一个非页眉页脚元素的xpath
                for element in elements:
                    data = element.data
                    if (temp := data.get("docx_meta", {}).get("xpath")) and data["class"] not in PAGE_HEADER_FOOTER:
                        blank_page_dict[group_index]["back"] = temp
                        break


def get_front_back_xpath(interdoc: PdfinsightReader, group_blank_pages: list[list[int]]):
    blank_page_dict = defaultdict(dict)
    xpath_page_dict = {}
    for page, elements in interdoc.element_dict.items():
        for element in elements:
            data = element.data
            if is_table_elt(data):
                for cell in data.get("cells", {}).values():
                    if not (docx_meta := cell.get("docx_meta")):
                        continue
                    if not (paragraphs := docx_meta.get("paragraphs")):
                        continue
                    for paragraph in paragraphs:
                        if not (xpath := paragraph.get("xpath")):
                            continue
                        xpath_page_dict[xpath] = page
            elif xpath := (data.get("docx_meta") or {}).get("xpath"):
                xpath_page_dict[xpath] = page
        get_current_page_front_back_xpath(group_blank_pages, page, elements, blank_page_dict)
    return blank_page_dict, xpath_page_dict


def delete_node(deleted_elements: dict[int, list[Node]], find_back_br: bool, find_front_br: bool):
    # 处理BR
    for group in deleted_elements.values():
        prev_nodes = []
        xpaths = {item.xpath for item in group}
        for item in group[0].parent.content:
            if item.xpath in xpaths:
                break
            if item.type in {"paragraph", "numbering", "table"}:
                prev_nodes.append(item)

        if not prev_nodes or prev_nodes[-1].type == "table":
            continue

        for item in group:
            if br_nodes := item.get_child_by_type("br"):
                if (not find_back_br and not find_front_br) and get_keys(
                    br_nodes[0].attrs, ["elementAttributes", "type"]
                ) == "page":
                    br_clone = br_nodes[0].clone()
                    br_clone.parent = prev_nodes[-1]
                    prev_nodes[-1].content.append(br_clone)
                    break
    # 删除节点
    for group in deleted_elements.values():
        for item in group:
            if item.prev and item.parent and item.prev.type == "table" and item.parent.type == "section":
                # 如果section节点最后一个是表格，需要保留表格后的段落,不能被删除，如果删除掉，则表格格式会被破坏
                continue
            item.delete()
            if not item.parent.content:
                item.parent.delete()


def delete_last_page_br(docx_node: Node):
    if not docx_node.content:
        return
    for element_content in reversed(docx_node.content[-1].content):
        if isinstance(element_content.content, list):
            if not element_content.content:
                break
            if get_keys(element_content.content[-1].attrs, ["elementAttributes", "type"]) == "page":
                element_content.content[-1].delete()
                if not element_content.content[-1].parent.content:
                    element_content.content[-1].parent.delete()
            break


def delete_section_first_page_br(docx_node: Node):
    for item in docx_node.content:
        if item.type == "section" and isinstance(item.content, list) and item.content:
            for element_content in item.content:
                if not isinstance(element_content.content, list) or not element_content.content:
                    break
                if get_keys(element_content.content[0].attrs, ["elementAttributes", "type"]) == "page":
                    element_content.content[0].delete()
                    if not element_content.content[0].parent.content:
                        element_content.content[0].parent.delete()
                break
            # if br_nodes := item.get_child_by_type("br"):
            #     for br in br_nodes:
            #         br.delete()
            #         if not br.parent.content:
            #             br.parent.delete()


def remove_blank_pages(pdfinsight_path: str, docx_node: Node):
    interdoc = PdfinsightReader(pdfinsight_path)
    blank_pages = []
    pages = [int(key) for key in interdoc.data["pages"].keys()]
    # 1、记录空白页面
    for page_index in pages:
        exist_paragraph = False
        if elements := interdoc.element_dict.get(page_index):
            for element in elements:
                if element.data["class"] not in PAGE_HEADER_FOOTER:
                    exist_paragraph = True
                    break
        if not exist_paragraph or not elements:
            blank_pages.append(page_index)
    group_blank_pages = group_consecutive_numbers(blank_pages)
    # 2、查找空白页前后的xpath
    blank_page_dict, xpath_page_dict = get_front_back_xpath(interdoc, group_blank_pages)

    # 3、找到空白页对应的节点并删除中间的xpath节点
    for part_index, blank_xpath in blank_page_dict.items():
        deleted_elements = defaultdict(list)
        front_xpath = blank_xpath.get("front")
        back_xpath = blank_xpath.get("back")
        front_ele_content = None
        back_ele_content = None

        if not front_xpath and not back_xpath:
            continue

        for chapter_content in docx_node.content:
            for element_content in chapter_content.content:
                if not (xpath := element_content.xpath):
                    continue
                if front_xpath and xpath == front_xpath:
                    front_ele_content = element_content
                    continue
                if back_xpath and xpath == back_xpath:
                    back_ele_content = element_content
                    break
                if front_ele_content or not front_xpath:
                    deleted_elements[part_index].append(element_content)
            if back_ele_content:
                break
        find_front_br = False
        if front_ele_content:
            if front_childs := front_ele_content.get_child_by_types({"br", "text"}):
                if get_keys(front_childs[-1].attrs, ["elementAttributes", "type"]) == "page":
                    find_front_br = True
            if front_ele_content.parent.type == "section" and front_ele_content.parent.content:
                parent_content_last_element = front_ele_content.parent.content[-1]
                if front_ele_content == parent_content_last_element:
                    find_front_br = True
                elif childs := parent_content_last_element.get_child_by_types({"br", "text"}):
                    if get_keys(childs[-1].attrs, ["elementAttributes", "type"]) == "page":
                        find_front_br = True
        find_back_br = False
        if back_ele_content:
            if backchilds := back_ele_content.get_child_by_types({"br", "text"}):
                if get_keys(backchilds[0].attrs, ["elementAttributes", "type"]) == "page":
                    find_back_br = True
                    if find_front_br:
                        backchilds[0].delete()
        delete_node(deleted_elements, find_front_br, find_back_br)

    # 4、最后一页有分页符
    delete_last_page_br(docx_node)

    # 5、section第一个br
    delete_section_first_page_br(docx_node)

    return blank_pages, xpath_page_dict


def find_pages_by_type(json_data, xpath_page_dict, find_type):
    comment_pages = set()
    for item in json_data.get_child_by_type(find_type):
        page = xpath_page_dict.get(item.parent.xpath)
        if page is not None:
            comment_pages.add(page)
    return comment_pages


def is_hidden_file(file_path):
    """检查文件是否是隐藏的"""
    # Linux/macOS
    return file_path.name.startswith(".")


def safe_truncate_bytes(s, max_bytes, encoding="utf-8"):
    """按字节截断字符串，确保不破坏 UTF-8 字符"""
    encoded = s.encode(encoding)
    truncated = encoded[:max_bytes]
    # 尝试解码，如果失败则丢弃最后一个不完整字符
    while True:
        try:
            return truncated.decode(encoding)
        except UnicodeDecodeError:
            truncated = truncated[:-1]  # 丢弃最后一个字节再试


def shorten_path_bytes(filepath, max_path_bytes=4096, max_name_bytes=255):
    dirname, filename = os.path.split(filepath)
    basename, ext = os.path.splitext(filename)

    # 先缩短文件名
    basename_bytes = basename.encode("utf-8")
    ext_bytes = ext.encode("utf-8")
    if len(basename_bytes) + len(ext_bytes) > max_name_bytes:
        basename = safe_truncate_bytes(basename, max_name_bytes - len(ext_bytes))

    # 再缩短目录路径（从后往前逐级检查）
    dir_bytes = dirname.encode("utf-8")
    while len(dir_bytes) + len(basename.encode("utf-8")) + len(ext_bytes) + 1 > max_path_bytes:
        dir_parts = dirname.split(os.sep)
        if not dir_parts:
            break
        dir_parts.pop()  # 移除最后一级
        dirname = os.sep.join(dir_parts) or os.sep
        dir_bytes = dirname.encode("utf-8")

    return os.path.join(dirname, basename + ext)
