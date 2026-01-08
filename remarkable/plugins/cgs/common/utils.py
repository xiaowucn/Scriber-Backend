import copy
import logging
from collections import defaultdict

import httpx

from remarkable.common.exceptions import CustomError
from remarkable.common.util import clean_txt, generate_timestamp
from remarkable.config import get_config
from remarkable.pdfinsight.reader import PdfinsightReader, PdfinsightSyllabus
from remarkable.plugins.cgs.common.patterns_util import (
    P_CATALOGUE,
    P_LINE_NUMBER,
    P_SELECT_ELE,
    P_SUGGESTION,
)
from remarkable.security.authtoken import _generate_token

logger = logging.getLogger(__name__)


def get_xpath_by_outlines(reader: PdfinsightReader, outlines: dict) -> str:
    xpath = []
    for page, outline in outlines.items():
        xpath.append(get_xpath_by_outline(reader, page, outline[0]))
    return ",".join(xpath)


def get_xpath_by_outline(reader: PdfinsightReader, page: int, outline: tuple[float, float, float, float]) -> str:
    page = int(page)
    if not outline:
        return ""
    elements = reader.find_elements_by_outline(page, outline)
    if not elements:
        return ""
    elements_xpath = [(ele.get("docx_meta") or {}).get("xpath") for _, ele in elements]
    etype, ele = elements[0]
    if etype == "TABLE":
        cell_idxes = reader.find_cell_idxes_by_outline(ele, outline, page)
        cells_xpath = []
        for cell_idx in cell_idxes:
            cell = ele["cells"].get(cell_idx)
            if not cell:
                continue
            if cell_xpath := (cell.get("docx_meta") or {}).get("xpath"):
                cells_xpath.append(cell_xpath)
        if cells_xpath:
            return ",".join(cells_xpath)
    return ",".join([x for x in elements_xpath if x])


def get_chapter_info_by_outline(reader, outlines, extra_keys: tuple | None = None):
    if not reader or not outlines:
        return []
    elements = []
    for page, outline in outlines.items():
        elements.extend(reader.find_elements_by_outline(page=int(page), outline=outline[0]))

    for _, element in sorted(elements, key=lambda x: x[1]["index"]):
        chapters = reader.syllabus_reader.find_by_elt_index(element["index"])
        if chapters:
            if extra_keys:
                results = []
                for item in chapters:
                    chapter = {"index": item["index"], "title": item["title"]}
                    for key in extra_keys:
                        chapter[key] = item.get(key)
                    results.append(chapter)
                return results
            return [{"index": item["index"], "title": item["title"]} for item in chapters]
    return []


def find_common_parent_chapter(reader: PdfinsightReader, schema_answers: list):
    chapters = [get_chapter_info_by_outline(reader, answer.outlines) for answer in schema_answers]
    chapters = [[chapter["index"] for chapter in items] for items in chapters if items]
    if not chapters:
        return None
    common_chapters = set(chapters[0]).intersection(*chapters[1:])
    if not common_chapters:
        return None
    chapters = []
    for idx in sorted(common_chapters):
        if chapter := reader.syllabus_reader.syllabus_dict.get(idx):
            chapters.append(chapter)
    return chapters


def get_paragraphs_by_schema_answers(reader: PdfinsightReader, schema_answers: list, valid_types=None):
    # 此方法可能会返回表格，通过valid_types限制返回类型，默认只返回PARAGRAPH
    common_chapters = find_common_parent_chapter(reader, schema_answers)
    if not common_chapters:
        paras = []
        # https://gitpd.paodingai.com/cheftin/docs_scriber/-/issues/2344#note_345807
        for answer in schema_answers:
            for page, outline in answer.outlines.items():
                paras.extend([para for _, para in reader.find_elements_by_outline(page=int(page), outline=outline[0])])
        return None, paras
    answer_paras = get_paragraphs_by_answers(reader, schema_answers)
    parent_chapter = common_chapters[-1]
    # 当前章节与答案段落一致，则找该章节的父章节
    if answer_paras[0]["index"] == parent_chapter["element"]:
        parent_chapter = None
        if len(common_chapters) > 1:
            parent_chapter = common_chapters[-2]
    # 无父章节或父章节为目录，则直接返回答案对应的段落
    if not parent_chapter or P_CATALOGUE.nexts(parent_chapter["title"]):
        return parent_chapter, answer_paras
    paras = reader.get_elements_by_syllabus(parent_chapter, valid_types=valid_types)
    # 仅测试时开放
    if get_config("cgs.test_inspect_mode"):
        paras = update_para_by_answer_for_test(paras, schema_answers, reader)
    return parent_chapter, paras


def get_paragraphs_by_schema_fields(
    reader: PdfinsightReader, manager, schema_fields, valid_types=None, without_chapter=False
):
    # 此方法可能会返回表格，通过valid_types限制返回类型，默认只返回PARAGRAPH
    schema_answers = [manager.get(field) for field in schema_fields]
    chapter, paragraphs = get_paragraphs_by_schema_answers(reader, schema_answers, valid_types=valid_types)
    if without_chapter and chapter:
        paragraphs = [para for para in paragraphs if para["index"] != chapter["element"]]
    return chapter, paragraphs


def update_para_by_answer_for_test(paras, schema_answers, reader):
    if not any(answer.answer and answer.answer.get("record") for answer in schema_answers):
        return paras
    paras = copy.deepcopy(paras)
    overlap_threshold = 0.618
    for answer in schema_answers:
        if len(answer.outlines) < 1 or not (answer.answer and answer.answer.get("record")):
            continue
        max_overlap = None
        match_paras = []
        for page, outlines in answer.outlines.items():
            for para in paras:
                if str(para["page"]) != page:
                    continue
                overlap = reader.overlap_percent(outlines[0], para["outline"], base="min")
                if overlap == 0:
                    continue

                if max_overlap is None or max_overlap[1] < overlap:
                    max_overlap = (para, overlap)

                if overlap > overlap_threshold:
                    match_paras.append(para)
            if not match_paras and max_overlap is not None:
                match_paras.append(max_overlap[0])
        if match_paras:
            # 仅处理段落与答案行数一致的场景
            answer_texts = answer.value.split("\n")
            if len(answer_texts) != len(match_paras):
                continue
            match_paras = sorted(match_paras, key=lambda x: x["index"])
            for text, para in zip(answer_texts, match_paras):
                para["text"] = text
    return paras


def get_paragraphs_by_answers(reader: PdfinsightReader, schema_answers: list):
    answer_paras = []
    for answer in schema_answers:
        for page, outlines in answer.outlines.items():
            for _, para in reader.find_elements_by_outline(int(page), outlines[0]):
                answer_paras.append(para)
    answer_paras = sorted(answer_paras, key=lambda x: x["index"])
    return answer_paras


def get_chapter_title_text(chapters):
    if not chapters:
        return ""

    if "目录" in chapters[0]["title"]:
        if len(chapters) == 1:
            return ""
        del chapters[0]

    chapter_titles = [chapters[-1]["title"]]
    if len(chapters) >= 2:
        if chapters[0]["title"] != chapters[-1]["title"]:
            chapter_titles = [chapters[0]["title"], chapters[-1]["title"]]

    title = "，".join(chapter_titles)
    if title:
        return title + "，"
    return ""


def render_suggestion(title, rule_name="", content="", suggestion="", prefix="合同"):
    template = f"{prefix}，" if prefix else ""
    if rule_name not in title:
        return f"{template}{title}{rule_name}，请将“{content}”修改为“{suggestion}”"
    return f"{template}{title}，请将“{content}”修改为“{suggestion}”"


def generate_suggestion(diff_item, suggestion, title, rule_name):
    if diff_item["type"] == "del":
        suggestion = append_suggestion(suggestion, f"请在{rule_name}中补充“{diff_item['left']}”")
    elif diff_item["type"] == "match":
        suggestion = append_suggestion(
            suggestion,
            render_suggestion(
                title, rule_name, diff_item["right"], combine_line_no(diff_item["right"], diff_item["left"])
            ),
        )
    return suggestion


def format_suggestion(content: str, manager):
    mapping = {
        "position": lambda ans: (ans.chapter_title or "").rstrip("，"),
        "paragraph": lambda ans: ans.value,
    }

    arr = list(content)
    for group in reversed(list(P_SUGGESTION.finditer(content))):
        if not manager.is_schema_field(group.group("schema_name")):
            continue

        answer = manager.get(group.group("schema_name"))
        if answer.value is None:
            return None

        func = mapping.get(group.group("anchor"))
        if func:
            value = func(answer) or ""
            arr[group.start() : group.end()] = list(value)

    return "".join(arr)


def replace_synonym(synonym_arr, text):
    if not synonym_arr or not text:
        return text

    for words in synonym_arr:
        base_word = words[0]
        for word in words[1:]:
            if word:
                text = text.replace(word, base_word)
    return text


def get_outlines(paragraphs):
    if not paragraphs:
        return {}
    elements = [item for item in paragraphs if not item.get("outlines")]
    outlines = PdfinsightSyllabus.elements_outline(elements)
    outline = defaultdict(list)
    for item in outlines:
        outline[str(item["page"])].append(item["outline"])

    if len(elements) != paragraphs:
        elements = [item for item in paragraphs if item.get("outlines")]
        for item in elements:
            for page, _outlines in item["outlines"].items():
                outline[page].extend(_outlines)

        for page, outlines in outline.items():
            outline[page] = [
                [
                    min(e[0] for e in outlines),
                    min(e[1] for e in outlines),
                    max(e[2] for e in outlines),
                    max(e[3] for e in outlines),
                ]
            ]
    return outline


def is_empty(value):
    if value is None:
        return True
    if isinstance(value, (int, float, bool)):
        return False
    return not value


def combine_line_no(content, template):
    if "\n" not in content:
        searched = P_LINE_NUMBER.search(content)
        if searched:
            template_content = P_LINE_NUMBER.sub("", template)
            return f"{searched.group('number')}{template_content}"
    else:
        # TODO 多行的替换规则？
        pass
    return template


def append_suggestion(origin, suggestion, separator="\n\n"):
    if not suggestion:
        return origin
    if not origin:
        return suggestion
    return separator.join([origin, suggestion])


def split_suggestion(suggestion, separator="\n"):
    if not suggestion:
        return []
    return [item for item in suggestion.split(separator) if item]


CN_RATE = (
    (10, "十"),
    (100, "百"),
    (1000, "千"),
    (10000, "万"),
    (100000000, "亿"),
    (1000000000000, "兆"),
)

CN_NUM = {
    0: "〇",
    1: "一",
    2: "二",
    3: "三",
    4: "四",
    5: "五",
    6: "六",
    7: "七",
    8: "八",
    9: "九",
}


def _number2chinese(number):
    text = ""
    if number < 10:
        text += CN_NUM[number]
        return text
    for rate_number, chinese_char in reversed(CN_RATE):
        if number >= rate_number:
            mod, last = divmod(number, rate_number)
            text += _number2chinese(mod)
            text += chinese_char
            if last != 0:
                if str(number)[len(str(mod)) :].startswith("0"):
                    text += CN_NUM[0]
                text += _number2chinese(last)
            break
    return text


def number2chinese(number):
    text = _number2chinese(number)
    if text.startswith("一十"):
        text = text[1:]
    return text


def is_matched_fund_manager_types(types, fund_manager_type):
    if not fund_manager_type:
        return False

    if not isinstance(types, (list, tuple)):
        types = [types]

    for item in types:
        if item in fund_manager_type:
            return True

    return False


async def get_review_fields(glazer_id):
    def auth_url(api, params=None):
        app_id = get_config("app.auth.glazer.app_id")
        secret_key = get_config("app.auth.glazer.secret_key")
        timestamp = generate_timestamp()

        token = _generate_token(url, app_id, secret_key, params, generate_timestamp(), cut_subpath=False)
        return f"{api}?_token={token}&_timestamp={timestamp}"

    glazer_host = get_config("app.auth.glazer.url")
    url = f"{glazer_host}/api/v1/imitator/cgs-tg/projects/{glazer_id}/scriber-element-list"
    url = auth_url(url)
    logger.info(f"get_review_fields url: {url}")
    if not url:
        raise CustomError("cgs.review_fields_url not found")
    async with httpx.AsyncClient(verify=False, timeout=30) as client:
        rsp = await client.get(url)
        if not httpx.codes.is_success(rsp.status_code):
            logger.error(
                f"glazer_id {glazer_id} get review_fields failed, status code: {rsp.status_code}, content: {rsp.text}"
            )
            raise CustomError("get review_fields failed")
    return list(rsp.json()["data"])


def group_table_cells_by_row(table):
    ret = defaultdict(list)
    for index, cell in sorted(table["cells"].items(), key=lambda x: (x[0].split("_")[1], x[0].split("_")[0])):
        ret[int(index.split("_")[0])].append(cell)
    return ret


def calc_outline_by_box_dicts(box_dicts):
    if not box_dicts:
        return []
    boxes = list(zip(*[cell["box"] for cell in box_dicts]))
    return [min(boxes[0]), min(boxes[1]), max(boxes[2]), max(boxes[3])]


def calc_merged_paragraph_by_chars(chars, exclude_page=None):
    if not chars or not exclude_page:
        return {}
    page_merged_paragraph = defaultdict()
    include_chars = [char for char in chars if char["page"] != exclude_page]
    if include_chars:
        page_merged_paragraph["page"] = include_chars[0]["page"]
        page_merged_paragraph["outline"] = calc_outline_by_box_dicts(include_chars)
    return page_merged_paragraph


def convert_table_to_sentences_by_row(table):
    # 按行拆分，每行作为一个段落，合并chars, 计算outline
    sentences = []
    table_index = table["index"]
    page = table["page"]
    for row_idx, cells in sorted(group_table_cells_by_row(table).items()):
        chars = [char for cell in cells for char in cell["chars"]]
        text = "".join([cell["text"] for cell in cells])
        text = text.replace("\n", "")
        cell_page = min((cell["page"] for cell in cells), default=page)
        merged_paragraph = calc_merged_paragraph_by_chars(chars, exclude_page=cell_page)
        if merged_paragraph:
            merged_paragraph["text"] = text
            merged_paragraph["chars"] = chars
        row_sentence = {
            "table_index": table_index,
            "class": "PARAGRAPH",
            "page": cell_page,
            "row": row_idx,
            "text": text,
            "chars": chars,
            "outline": calc_outline_by_box_dicts(cells),
            "page_merged_paragraph": merged_paragraph,
        }
        sentences.append(row_sentence)
    return sentences


def check_contain_content(source: str, target: str) -> bool:
    if not source or not target:
        return False
    source = clean_txt(source)
    res = P_SELECT_ELE.nexts(source)
    pos = source.find(target)
    if not res:
        return pos > -1
    return res and res.start() + 1 == pos
