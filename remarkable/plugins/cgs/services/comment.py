import asyncio
import datetime
import json
import logging
import os
import re
import shutil
import tempfile
import zipfile
from collections import defaultdict
from pathlib import Path
from urllib.parse import urljoin
from xml.dom.minidom import parseString

import glazer_docx_convert
from pdfparser.pdftools.pdf_annotation import AnnotColor, AnnotItem, AnnotType, PDFAnnot
from pdfparser.pdftools.pdf_element import extract_interdoc_images_data

from remarkable import config
from remarkable.common.answer_util import AnswerLocation
from remarkable.common.constants import RuleType
from remarkable.common.enums import ClientName
from remarkable.common.exceptions import CustomError, ItemNotFound
from remarkable.common.storage import LocalStorage, localstorage, tmp_storage
from remarkable.common.util import read_zip_first_file, subprocess_exec
from remarkable.config import get_config
from remarkable.db import pw_db
from remarkable.models.new_file import NewFile
from remarkable.pdfinsight.reader import PdfinsightReader
from remarkable.plugins.fileapi.convert_pdf import convert_by_office
from remarkable.pw_models.answer_data import NewAnswerData
from remarkable.pw_models.audit_rule import NewAuditResult
from remarkable.pw_models.law_judge import LawJudgeResult, LawJudgeResultRecord
from remarkable.pw_models.model import NewAuditResultRecord
from remarkable.security import authtoken
from remarkable.service.comment import find_pages_by_type, remove_blank_pages, remove_title
from remarkable.service.node import Node
from remarkable.service.pdf2docx import pdf2docx
from remarkable.value_obj import CGSFileMeta

annotation_storage = tmp_storage.mount("cgs_comment")
logger = logging.getLogger(__name__)

DEFAULT_USER = "AI"
DEFAULT_JUDGE = "AI（大模型）"
P_WP = re.compile(r"w:p\[(?P<p>\d+)\]")


def gen_comment_position_items(results):
    for result in results:
        if result.suggestion:
            if isinstance(result, LawJudgeResult) and result.rule_type == RuleType.TEMPLATE:
                for reason in result.reasons:
                    for page, outlines, suggestion in reason.get("annotations", []):
                        page_outlines = {str(page): outlines}
                        yield page_outlines, result, suggestion
                continue

            outlines = None
            if result.reasons:
                for reason in result.reasons:
                    if reason.get("outlines"):
                        outlines = reason["outlines"]
                        break

            if not outlines and result.schema_results:
                for schema_item in result.schema_results:
                    if schema_item.get("outlines"):
                        outlines = schema_item["outlines"]
                        break
            if outlines:
                yield outlines, result, result.comment


def get_comment_positions(results):
    comment_positions = defaultdict(list)

    for outlines, result, suggestion in gen_comment_position_items(results):
        for page, outline in outlines.items():
            comment_positions[int(page)].append([outline, result, suggestion])
    return comment_positions


def get_xpath_details(pdfinsight_reader: PdfinsightReader, xpath: str, outlines: dict[str, list], answer_text: str):
    start, end = None, None
    if xpath and "," not in xpath:  # 仅在单xpath的情况下尝试确定start & end
        for page, outline_list in outlines.items():
            page = int(page)
            first_outline = outline_list[0]
            _, element = pdfinsight_reader.find_element_by_outline(page, first_outline)
            if element:
                answer_location = AnswerLocation(answer_text, element, first_outline=first_outline, page=page)
                start, end, _, _ = answer_location.details(pdfinsight_reader)
            break  # 只从第一页的第一个outline找
    return xpath, start, end


def get_comment_xpath(reader, results):
    comment_xpath = []

    for result in results:
        if result.suggestion:
            if isinstance(result, LawJudgeResult) and result.rule_type == RuleType.TEMPLATE:
                for reason in result.reasons:
                    for page, outlines, suggestion in reason.get("annotations", []):
                        page_outlines = {str(page): outlines}
                        xpath, start, end = get_xpath_details(
                            reader,
                            reason.get("xpath"),
                            page_outlines,
                            suggestion,
                        )
                        if xpath:
                            comment_xpath.append([xpath, result, start, end, suggestion])
                continue

            xpath, start, end = None, None, None
            if result.reasons:
                for reason in result.reasons:
                    xpath, start, end = get_xpath_details(
                        reader,
                        reason.get("xpath"),
                        reason.get("outlines", {}),
                        reason.get("content") or reason.get("text"),
                    )
                    if xpath:
                        break

            if not xpath and result.schema_results:
                for schema_item in result.schema_results:
                    xpath, start, end = get_xpath_details(
                        reader,
                        schema_item.get("xpath"),
                        schema_item.get("outlines", {}),
                        schema_item.get("content") or schema_item.get("text"),
                    )
                    if xpath:
                        break
            if xpath:
                comment_xpath.append([xpath, result, start, end, result.comment])
    return comment_xpath


def get_annotation_json(reader, results, last_modified_users, default_user=DEFAULT_USER):
    comment_positions = get_comment_xpath(reader, results)
    annotation_json = []
    for xpath, result, start, end, comment_text in comment_positions:
        user_name = last_modified_users.get(result.id) or default_user
        annot_time = datetime.datetime.fromtimestamp(result.updated_utc).strftime("%Y-%m-%d %H:%M:%S")
        annotation_json.append(
            {
                "xpath": xpath,
                "comment": user_name + "\n" + annot_time + "\n" + comment_text,
                "type": "error",
                "start": start,
                "end": end,
            }
        )
    return annotation_json


def export_pdf_comment(_file, output_path, page_annots):
    annot = PDFAnnot(localstorage.mount(_file.pdf_path()))

    annot.insert_batch(page_annots, output_path)
    return output_path


def generate_pdf_page_annots(comment_positions, last_modified_users, default_user=DEFAULT_USER):
    res = defaultdict(list)
    for page, items in comment_positions.items():
        for outlines, result, comment_text in items:
            user_name = last_modified_users.get(result.id) or default_user
            annot_time = datetime.datetime.fromtimestamp(result.updated_utc).strftime("%Y-%m-%d %H:%M:%S")

            if ClientName.cmfchina == config.get_config("client.name"):
                texts = [annot_time + "\n", comment_text]
                if result.reasons:
                    texts.extend(
                        [
                            "\n",
                            f"不通过原因：{','.join(r.get('reason_text') for r in result.reasons if r.get('reason_text'))}",
                        ]
                    )
            else:
                texts = [user_name + "\n", annot_time + "\n", comment_text]
            res[int(page)].append(
                AnnotItem(
                    outlines,
                    AnnotColor.YELLOW.value,
                    AnnotType.FPDF_ANNOT_HIGHLIGHT,
                    texts=texts,
                    fontsize=20,
                )
            )
    return res


def export_pdf_to_annotated_docx(file, comment_positions, output_path):
    """
    pdf导出word并批注处理流程
    1.从interdoc 里用 outlines 获取 element_index 和cell_index 位置信息
    2.在pdf2docx前 在 段落上标记 comment_start, comment_end, comment_cell属性.记录要批注的位置
    3.由于python-docx不支持批注，只能先创建占位占位段落，后续导出完成后xml里替换.
    4.pdf2docx
    6.解压docx后准备按照ECMA376标准修改OOXML
    6.在document.xml里找到占位内容，替换为批注引用
    7.创建comment part: 重置/创建comments.xml, commentsExtended.xml, 将批注内容写上这两个文件
    8.刷新 relations 文件: document.xml.rels
    9.刷新content_types 文件:  [Content_Types].xml
    9.zip打包docx
    """
    path = localstorage.mount(file.pdfinsight_path())
    interdoc = json.loads(read_zip_first_file(path))
    extract_interdoc_images_data(localstorage.mount(file.pdf_path()), interdoc, scale=2)
    docx = pdf2docx(interdoc, comment_positions)
    localstorage.write_file(output_path, docx)

    return output_path


def export_docx_comment(file: NewFile, annotation_json, output_path):
    docx_path = file.revise_docx_path() or file.docx_path()
    if not docx_path:
        raise CustomError("doc file is not ready")

    with tempfile.TemporaryDirectory(dir=get_config("web.tmp_dir")) as tmp_dir:
        tmp_json_path = os.path.join(tmp_dir, "tmp.json")
        tmp_docx_path = os.path.join(tmp_dir, "tmp.docx")

        with open(tmp_json_path, "w", encoding="utf-8") as file_pbj:
            json.dump(annotation_json, file_pbj)
        shutil.copy(localstorage.mount(docx_path), tmp_docx_path)

        word_insight_dll = config.get_config("web.revision_tools")
        try:
            # 需要配置web.revision_tools, 并在web.revision_tools所指向的路径下增加配置文件
            subprocess_exec("%s -d %s --json %s" % (word_insight_dll, tmp_docx_path, tmp_json_path))
        except Exception as e:
            logger.error(f"add annotation failed, error_info {str(e)}")
            return None
        shutil.copy(tmp_docx_path, output_path)
    return output_path


async def export_result_comment(export_type, fid, schema_id, is_admin, user_id):
    file = await NewFile.find_by_id(fid)
    if not file:
        raise ItemNotFound()
    results = await NewAuditResult.get_results(fid, [schema_id], is_admin, user_id, only_incompliance=True)
    last_modified_users = await NewAuditResultRecord.get_last_modified_users([r.id for r in results])
    law_results = await LawJudgeResult.get_judge_results(fid)
    law_modified_users = await LawJudgeResultRecord.get_last_modified_users([r.id for r in law_results])

    reader = PdfinsightReader(localstorage.mount(file.pdfinsight_path()))

    annotation_dir = LocalStorage(annotation_storage).mount(file.hash[:2])
    if not os.path.exists(annotation_dir):
        os.makedirs(annotation_dir)

    if export_type == "pdf":
        output_path = os.path.join(annotation_dir, "{}.批注文件.pdf".format(os.path.splitext(file.name)[0]))
        page_annots = generate_pdf_page_annots(get_comment_positions(results), last_modified_users)
        law_page_annots = generate_pdf_page_annots(
            get_comment_positions(law_results), law_modified_users, DEFAULT_JUDGE
        )
        for page, annots in law_page_annots.items():
            page_annots[page].extend(annots)
        export_pdf_comment(file, output_path, page_annots)
        return output_path

    elif export_type == "docx":
        output_path = os.path.join(annotation_dir, "{}.批注文件.docx".format(os.path.splitext(file.name)[0]))
        if file.is_pdf:
            return export_pdf_to_annotated_docx(
                file,
                [
                    *[
                        [
                            {page: outline},
                            result.unique_id,
                            suggestion or result.comment,
                            last_modified_users.get(result.id) or DEFAULT_USER,
                        ]
                        for outlines, result, suggestion in gen_comment_position_items(results)
                        for page, outline in outlines.items()
                    ],
                    *[
                        [
                            {page: outline},
                            result.unique_id,
                            suggestion or result.comment,
                            law_modified_users.get(result.id) or DEFAULT_JUDGE,
                        ]
                        for outlines, result, suggestion in gen_comment_position_items(law_results)
                        for page, outline in outlines.items()
                    ],
                ],
                output_path,
            )

        export_docx_comment(
            file,
            get_annotation_json(reader, results, last_modified_users)
            + get_annotation_json(reader, law_results, law_modified_users, DEFAULT_JUDGE),
            output_path,
        )

        return output_path
    return None


def remove_doc_title(filename, body, doc_type):
    return remove_title(filename, body, doc_type)


def remove_text_formatting(content):
    """
    递归删除docx文件中指定文本的color和highlight属性

    Args:
        content: 文档内容节点列表
    """

    def _remove_properties_from_dict(properties):
        """从属性字典中移除color和highlight属性"""
        for attr in ("color", "highlight"):
            if attr in properties:
                del properties[attr]
        if rpr := properties.get("rPr"):
            if childern := rpr.get("children"):
                _remove_properties_from_dict(childern)

    for node in content:
        # 处理节点的node属性
        if hasattr(node, "node") and isinstance(node.node, dict):
            node_dict = node.node

            # 处理marks中的属性
            for mark in node_dict.get("marks", []):
                properties = mark.get("attrs", {}).get("runAttrs", {}).get("properties", {})
                _remove_properties_from_dict(properties)

            # 处理直接的attrs属性
            if attrs := node_dict.get("attrs"):
                properties = attrs.get("runAttrs", {}).get("properties", {})
                _remove_properties_from_dict(properties)
                properties = attrs.get("properties", {})
                _remove_properties_from_dict(properties)

        # 递归处理子内容
        if hasattr(node, "content") and isinstance(node.content, list):
            remove_text_formatting(node.content)


def _remove_formatting_nodes_with_lxml(xml_file_path):
    """
    使用 minidom 删除 XML 文件中的 w:highlight 和 w:color 节点，保持原始格式和命名空间前缀
    Args:
        xml_file_path: XML 文件路径
    Returns:
        删除的节点数量统计 (highlight_count, color_count)
    """

    # 读取 XML 文件内容
    with open(str(xml_file_path), "r", encoding="utf-8") as f:
        xml_content = f.read()

    # 使用 minidom 解析 XML
    dom = parseString(xml_content)

    def find_elements_by_local_name(node, local_name):
        """递归查找指定本地名称的所有元素"""
        result = []
        if node.nodeType == node.ELEMENT_NODE and node.localName == local_name:
            result.append(node)

        # 递归查找子节点
        for child in node.childNodes:
            if child.nodeType == child.ELEMENT_NODE:
                result.extend(find_elements_by_local_name(child, local_name))

        return result

    # 统计删除的节点
    highlight_count = 0
    color_count = 0

    # 查找并删除高亮节点
    highlight_elements = find_elements_by_local_name(dom.documentElement, "highlight")
    for elem in highlight_elements:
        if elem.parentNode:
            elem.parentNode.removeChild(elem)
            highlight_count += 1

    # 查找并删除颜色相关节点
    color_targets = ["color", "schemeClr", "textFill"]
    for target in color_targets:
        color_elements = find_elements_by_local_name(dom.documentElement, target)
        for elem in color_elements:
            if elem.parentNode:
                elem.parentNode.removeChild(elem)
                color_count += 1

    # 保存修改后的 XML，保持原始格式和编码
    if highlight_count > 0 or color_count > 0:
        with open(str(xml_file_path), "w", encoding="utf-8") as f:
            # 使用 toprettyxml 来保持格式，但去掉多余的空白行
            xml_output = dom.toxml()
            f.write(xml_output)

    return highlight_count, color_count


def remove_docx_formatting_nodes(work_dir, docx_path):
    """
    解压docx文件，删除多个XML文件中的w:highlight和w:color节点，然后重新打包
    处理的文件包括：header*.xml, footer*.xml, styles.xml, numbering.xml, document.xml
    Args:
        work_dir: 工作目录路径
        docx_path: docx文件路径
    """

    extract_dir = work_dir / "docx_extracted"

    # 解压docx文件
    with zipfile.ZipFile(docx_path, "r") as zip_ref:
        zip_ref.extractall(extract_dir)

    # 查找包含header,footer和styles的XML文件
    word_dir = extract_dir / "word"
    if word_dir.exists():
        # 查找xml文件中的highlight和color节点
        xml_files = []
        # 正文
        xml_files.extend(word_dir.glob("document.xml"))
        # header文件
        xml_files.extend(word_dir.glob("header*.xml"))
        # footer文件
        xml_files.extend(word_dir.glob("footer*.xml"))
        # styles文件
        xml_files.extend(word_dir.glob("styles.xml"))
        # 序号文件
        xml_files.extend(word_dir.glob("numbering.xml"))

        for xml_file in xml_files:
            if not xml_file.exists():
                continue

            logger.info(f"处理XML文件: {xml_file.name}")
            try:
                # 使用 lxml 处理 XML 文件
                highlight_count, color_count = _remove_formatting_nodes_with_lxml(xml_file)

                # 日志记录
                if highlight_count > 0 or color_count > 0:
                    removed_info = []
                    if highlight_count > 0:
                        removed_info.append(f"{highlight_count} 个 highlight 节点")
                    if color_count > 0:
                        removed_info.append(f"{color_count} 个 color 节点")
                    logger.info(f"已从 {xml_file.name} 中删除: {', '.join(removed_info)}")
                else:
                    logger.debug(f"{xml_file.name} 中未找到 highlight 或 color 节点")

            except Exception as e:
                logger.error(f"处理文件 {xml_file.name} 时出错: {e}")

        # 重新打包为docx文件
        with zipfile.ZipFile(docx_path, "w", zipfile.ZIP_DEFLATED) as zip_ref:
            for file_path in extract_dir.rglob("*"):
                if file_path.is_file():
                    arc_name = file_path.relative_to(extract_dir)
                    zip_ref.write(file_path, arc_name)
        logger.info(f"已重新打包docx文件: {docx_path}")


async def remove_docx_blank_comments(fid: int, docx_path: str, pdfinsight_path: str, work_dir: str) -> CGSFileMeta:
    if not docx_path or not pdfinsight_path:
        raise FileNotFoundError(f"file not found: {docx_path=}, {pdfinsight_path=}")

    work_dir = Path(work_dir)
    clean_docx_path = (work_dir / "clean_file.docx").as_posix()
    clean_pdf_path = (work_dir / "clean_file.pdf").as_posix()
    # 因用glazer_docx_convert.export_docx导出docx文档，是不会生成批注，所以不需要删除批注的过程，只需要记录批注的页码
    json_path = work_dir / "clean_file.json"
    try:
        # 1、是否有修订,获得接受修订的文档，不能使用PDFinsight返回的revise docx,否则不能判断是否有修订
        revisions = glazer_docx_convert.revise_docx(
            docx_path=docx_path, output_path=clean_docx_path, keep_comments=True
        )
        # 2、获取docx_json
        docx_node = Node(
            glazer_docx_convert.convert_docx_to_json(docx_path=clean_docx_path, output_json_path=json_path.as_posix())
        )
        # 3、删除空白页
        blank_pages, xpath_page_dict = remove_blank_pages(pdfinsight_path, docx_node)
        # 4、记录批注页码
        comment_pages = find_pages_by_type(docx_node, xpath_page_dict, "commentRange")
        # 5、保存json
        json_path.write_text(json.dumps(docx_node.to_json()))
        # 6、导出docx
        glazer_docx_convert.export_docx(
            source_docx_path=clean_docx_path, json_path=json_path.as_posix(), output_path=clean_docx_path
        )
        # 7、解压docx文件并删除header和footer XML文件中的w:highlight和w:color节点
        remove_docx_formatting_nodes(work_dir, clean_docx_path)
        # 8、调用 Office 服务将 docx 转为 PDF
        await call_docx2pdf_service(fid, clean_docx_path)

        res = CGSFileMeta(clean_path={"clean_docx_path": clean_docx_path, "clean_pdf_path": clean_pdf_path})
        if blank_pages:
            res.clean_file.blank_pages = sorted(page + 1 for page in blank_pages)
        if comment_pages:
            res.clean_file.comment_pages = sorted(page + 1 for page in comment_pages)
        if revisions.get("revisions") and revisions["revisions"]:
            res.clean_file.revisions = list(revisions["revisions"])
        return res
    except Exception as e:
        logging.exception(e)
        logging.error(f"{fid=}, remove docx blank comments failed")


async def call_docx2pdf_service(fid: int, src_path: str):
    callback_url = urljoin(
        f"http://{get_config('web.domain')}",
        f"/api/v1/plugins/cgs/clean-files/{fid}/callback",
    )
    app_id = get_config("cgs.auth.app_id")
    secret = get_config("cgs.auth.secret_key")
    encode_url = authtoken.encode_url(callback_url, app_id, secret, exclude_path=True)
    await convert_by_office(encode_url, fid, src_path)


async def edit_answer_data(qid: int, add: list, update: list, delete: list, uid: int):
    data = {}
    if delete:
        cond = (NewAnswerData.qid == qid) & (NewAnswerData.id.in_(x["id"] for x in delete))
        await pw_db.execute(NewAnswerData.delete().where(cond))  # 物理删除
    if add:
        for item in add:
            item["qid"] = qid
            item["uid"] = uid
            item["record"] = [NewAnswerData.gen_empty_record()]
        added = await NewAnswerData.insert_and_returning(add, returning=[NewAnswerData.id, NewAnswerData.key])
        data["add"] = added
    if update:
        await NewAnswerData.batch_update(update, uid, qid)

    return data


if __name__ == "__main__":

    async def main():
        await remove_docx_blank_comments(
            1,
            # "/home/xuf-e/Downloads/cgs/恒睿保睿套利1号私募证券投资基金基金合同.docx",
            "/home/xuf-e/Downloads/cgs/恒睿保睿套利1号私募证券投资基金基金合同_2.docx",
            "",
            "/home/xuf-e/Downloads/cgs/test/",
        )
        # await export_result_comment("docx", 491, 7, True, 1)
        # await export_result_comment("pdf", 491, 7, True, 1)

    asyncio.run(main())
