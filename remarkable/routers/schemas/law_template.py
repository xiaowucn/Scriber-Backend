import re
from contextlib import suppress
from functools import cached_property, partial
from typing import Literal

from calliper_diff.diff_data import ElementDeleteResult, ElementInsertResult, EqualResult, defaultdict, diff_data
from calliper_diff.diff_types import DiffType
from calliper_diff.word import WordDiffResultCollection
from pydantic import BaseModel, Field, PrivateAttr

from remarkable.common.box_util import get_bound_box
from remarkable.pdfinsight.text_util import clear_syl_title
from remarkable.plugins.cgs.common.patterns_util import P_NUMBERING
from remarkable.plugins.cgs.common.utils import get_chapter_info_by_outline, get_xpath_by_outlines
from remarkable.routers.schemas import ContractRects
from remarkable.utils.rule_para import calc_diff_ratio, generate_mocked_paras

P_CHAPTER_AND = re.compile(r"[＆&]")


def reset_paras_after_diff(paras):
    for para in paras:
        para.pop("calliper_element", None)
        if origin := para.get("origin_chars"):
            para["chars"] = origin


def filter_diff_eles_by_cell_paths(diff, right_cell_paths):
    right_eles = [
        ele for ele in diff["right_eles"] if "cell_path" in ele.element and ele.element["cell_path"] in right_cell_paths
    ]
    if right_eles:
        right_outline = defaultdict(list)
        for ele in right_eles:
            right_outline[f"page{ele.element['page']}"].append(ele.element["outline"])
        diff["item"].right_eles = diff["right_eles"] = right_eles
        diff["item"].right_outline = diff["item"].right_box = diff["right_outline"] = diff["right_box"] = right_outline
    return right_eles


def words_with_calliper_ignored(eles: list, words: list) -> list[str]:
    if not eles:
        return []

    result = [""]
    full_text = "\n".join(ele.element["text"] for ele in eles)
    itext = iter(full_text)
    for word in words:
        text = word.text
        with suppress(StopIteration):
            while char := next(itext):
                if char == text:
                    result.append(text)
                    break
                if char in text:
                    append_text = f"{result[-1]}{char}"
                    if text.startswith(append_text):
                        result[-1] += char
                        if result[-1] == text:
                            break
                    else:
                        result.append(char)
                    continue
                result[-1] += char
    result[-1] += "".join(list(itext))
    result[1] = result[0] + result[1]
    return result[1:]


def generate_diff_html(
    collection: WordDiffResultCollection | EqualResult | ElementInsertResult | ElementDeleteResult,
) -> str:
    """
    Generate formatted diff string with HTML tags showing deletions, unchanged text, and insertions.
    Format: "<s>删除</s>相同<u>新增</u>"
    Returns the diff string from left to right.
    """
    if isinstance(collection, ElementInsertResult):
        text = "\n".join(ele.element["text"] for ele in collection.right_eles)
        return f"<u>{text}</u>"

    if isinstance(collection, ElementDeleteResult):
        text = "\n".join(ele.element["text"] for ele in collection.left_eles)
        return f"<s>{text}</s>"

    if isinstance(collection, EqualResult) or not collection._collection:
        return "\n".join(ele.element["text"] for ele in collection.right_eles)

    # Reconstruct the text by processing each word diff result
    result_parts = []
    left_pos = 0

    # Sort diff results by their position in the original text
    sorted_diffs = sorted(collection._collection, key=lambda x: (x.left_data.idxes[0], x.right_data.idxes[0]))
    left_texts = words_with_calliper_ignored(collection.left_eles, collection.l_words)
    right_texts = words_with_calliper_ignored(collection.right_eles, collection.r_words)
    for diff in sorted_diffs:
        left_start, left_end = diff.left_data.idxes

        # Add unchanged text before this diff (from left side as reference)
        if left_start > left_pos:
            unchanged_text = "".join(left_texts[left_pos:left_start])
            if unchanged_text.strip():
                result_parts.append(unchanged_text)

        # Process the diff based on its type
        if diff.main_type == DiffType.CHARS_DELETE:
            # Only deletion - add <s> tags
            deleted_text = "".join(left_texts[left_start:left_end])
            if deleted_text.strip():
                result_parts.append(f"<s>{deleted_text}</s>")
        elif diff.main_type == DiffType.CHARS_INSERT:
            # Only insertion - add <u> tags
            inserted_text = "".join(right_texts[slice(*diff.right_data.idxes)])
            if inserted_text.strip():
                result_parts.append(f"<u>{inserted_text}</u>")
        elif diff.main_type == DiffType.CHARS_REPLACE:
            # Both deletion and insertion - add both tags
            deleted_text = "".join(left_texts[left_start:left_end])
            inserted_text = "".join(right_texts[slice(*diff.right_data.idxes)])
            if deleted_text.strip():
                result_parts.append(f"<s>{deleted_text}</s>")
            if inserted_text.strip():
                result_parts.append(f"<u>{inserted_text}</u>")
        left_pos = left_end

    # Add any remaining unchanged text from the end
    if left_pos < len(collection.l_words):
        unchanged_text = "".join(left_texts[left_pos:])
        if unchanged_text.strip():
            result_parts.append(unchanged_text)

    return "".join(result_parts)


def make_diff(left, diff_result):
    result = []
    for diff in diff_result:
        left = "\n".join([ele.element["text"] for ele in diff["left_eles"]])
        right = "\n".join([ele.element["text"] for ele in diff["right_eles"]])
        result.append(
            {
                "html": generate_diff_html(diff["item"]),
                "left": "" if diff["type"].endswith("insert") else left,
                "type": "equal" if diff.get("type") == "equal" else "match",
                "right": "" if diff["type"].endswith("delete") else right,
            }
        )
    if result:
        result[0]["is_top"] = True
    return result


class LawTplContent(BaseModel):
    chapters: list[str] = Field(default_factory=list)
    diff_context: bool = False
    content: str = Field(min_length=1)

    _any_chapters: list = PrivateAttr(default_factory=list)
    _any_result: dict = PrivateAttr(default_factory=dict)
    _annotations: list = PrivateAttr(default_factory=list)

    def find_chapters(self, reader, top_chapters):
        if not self.chapters:
            self.diff_context = False
            self._any_chapters = top_chapters
        else:
            for chapter in self.chapters:
                chapters = []
                for _chapter in P_CHAPTER_AND.split(chapter):
                    chapters.append(reader.find_sylls_by_clear_title(clear_syl_title(_chapter), multi=True))
                if all(chapters):
                    self._any_chapters.append(chapters)
        return self._any_chapters

    async def find_diff_with_contract_paras(self, contract_paras, chapter_name):
        template_paras = generate_mocked_paras([self.content])
        result = await self._do_diff(
            template_paras,
            {"paragraphs": contract_paras, "syllabuses": []},
            chapter_name,
            diff_context=True,  # 用户输入段落需要全部包含
        )
        self._any_result = result

    async def find_diff(self, reader):
        # 或章节 取相似度最高
        for all_chapters in self._any_chapters:
            result = {}  # &多章节, 取相似度最低
            for chapters in all_chapters:
                same_result = {}
                for chapter in chapters:  # 同名章节: 取相似度最高
                    # calliper diff 会修改, 无法复用
                    template_paras = generate_mocked_paras(self.content.split("\n"))
                    paras = reader.get_paragraphs_by_syllabus(chapter, table_cell_line_min_length=5)
                    result_data = await self._do_diff(
                        template_paras,
                        {"paragraphs": paras, "syllabuses": [chapter]},
                        chapter["title"],
                        self.diff_context,
                    )
                    if not same_result or result_data["ratio"] > same_result["ratio"]:
                        same_result = result_data

                if not result or same_result["ratio"] < result["ratio"]:
                    result = same_result

            if not self._any_result or result["ratio"] > self._any_result["ratio"]:
                self._any_result = result

    @classmethod
    async def _do_diff(cls, template_paras, right, chapter_name, diff_context):
        diff_result, _ = diff_data(
            template_paras,
            right,
            {
                "ignore_header_footer": False,
                "ignore_case": True,
                "ignore_punctuations": True,
                "ignore_chapt_numbers": True,
                "include_equal": True,
                "ignore_diff_on_toc_page": False,
                "similarity_diff_offset": 0,
                # "iter_count": 1,
            },
        )
        if all(diff["ratio"] == 0 for diff in diff_result):
            return {
                "ratio": 0,
                "data": [diff for diff in diff_result if diff["main_type"] == DiffType.PARA_DELETE],
                "chapter": chapter_name,
            }
        diff_result.sort(key=lambda x: (min(x["left_idxes"]), min(x["right_idxes"])))
        if diff_context:
            pass
        else:
            start_idx = 0
            for i, item in enumerate(diff_result):
                if item.get("main_type") == DiffType.PARA_INSERT:
                    start_idx = i + 1
                else:
                    break

            end_idx = len(diff_result)
            for i in range(len(diff_result) - 1, -1, -1):
                if diff_result[i].get("main_type") == DiffType.PARA_INSERT:
                    end_idx = i
                else:
                    break

            _diff_result = diff_result[start_idx:end_idx]
            _left_paras = [
                ele.element
                for diff in _diff_result
                if diff.get("main_type") != DiffType.PARA_DELETE
                for ele in diff["left_eles"]
            ]
            _right_paras = [
                ele.element
                for diff in _diff_result
                if diff.get("main_type") != DiffType.PARA_DELETE
                for ele in diff["right_eles"]
            ]
            _cell_paths = {ele["cell_path"] for ele in _right_paras if "cell_path" in ele}
            if _cell_paths:  # 存在相同单元格内容, 需要扩大diff
                _result = []
                for diff in diff_result[:start_idx]:
                    right_eles = filter_diff_eles_by_cell_paths(diff, _cell_paths)
                    if right_eles:
                        _result.append(diff)
                _result.extend(_diff_result)
                for diff in diff_result[end_idx:]:
                    right_eles = filter_diff_eles_by_cell_paths(diff, _cell_paths)
                    if right_eles:
                        _result.append(diff)
                diff_result = _result
            elif any(P_NUMBERING.nexts(_para["text"]) for _para in _left_paras) and (
                any(
                    P_NUMBERING.nexts(ele.element["text"])
                    for diff in reversed(diff_result[:start_idx])
                    for ele in diff["right_eles"]
                )
                or any(
                    P_NUMBERING.nexts(ele.element["text"])
                    for diff in diff_result[end_idx:]
                    for ele in diff["right_eles"]
                )
            ):
                from remarkable.service.law_prompt import contract_integrity_check

                # https://gitpd.paodingai.com/cheftin/docs_scriber/-/issues/8188 不检查上下文, 但却要同序号的上下文
                top_max_idx = min(para["index"] for para in _right_paras)
                top_paras = [para for para in right["paragraphs"] if para["index"] < top_max_idx]
                bottom_min_idx = max(para["index"] for para in _right_paras)
                bottom_paras = [para for para in right["paragraphs"] if para["index"] > bottom_min_idx]
                top, bottom = await contract_integrity_check(_right_paras, top_paras, bottom_paras)
                if top == bottom == 0:
                    diff_result = _diff_result
                else:
                    if top:
                        top_paras = top_paras[top:]
                    else:
                        top_paras = []
                    bottom_paras = bottom_paras[:bottom]
                    reset_paras_after_diff(right["paragraphs"])
                    reset_paras_after_diff(template_paras["paragraphs"])
                    right["paragraphs"] = [*top_paras, *_right_paras, *bottom_paras]
                    return await cls._do_diff(template_paras, right, chapter_name, diff_context=True)
            else:
                diff_result = _diff_result

        ratio = calc_diff_ratio(diff_result, ele_keys=("left_eles",))
        reset_paras_after_diff(right["paragraphs"])
        return {"ratio": ratio, "data": diff_result, "chapter": chapter_name}

    @property
    def result(self):
        return self._any_result.get("data", [])

    @property
    def ratio(self):
        return self._any_result.get("ratio", 0)

    @property
    def is_compliance(self):
        return self.ratio == 100

    def generate_schema_results(self, name):
        element_results = {}
        for diff in self.result:
            if diff["main_type"] in (DiffType.DELETE, DiffType.PARA_DELETE, DiffType.TABLE_DELETE):
                continue

            for ele in diff["right_eles"]:
                element = ele.element
                element_results[element["index"]] = {
                    "name": name,
                    "page": element["page"],
                    "text": element["text"],
                    "outlines": {str(element["page"]): [element["outline"]]},
                }
        return element_results

    def diff(self):
        return make_diff(self.content, self.result)

    def page_outlines(self):
        _page_outlines = defaultdict(list)
        for diff in self.result:
            if diff["main_type"] in (DiffType.DELETE, DiffType.PARA_DELETE, DiffType.TABLE_DELETE):
                continue
            for page_str, outlines in diff["right_outline"].items():
                page = page_str.removeprefix("page")
                _page_outlines[page].extend(outlines)
        return _page_outlines

    @property
    def suggestion(self):
        if self.is_compliance:
            return ""
        if self._any_result:
            suggestions = []
            if chapter := self._any_result["chapter"]:
                chapter = f"，{chapter}"
            for diff in self.result:
                if diff["main_type"] in (DiffType.EQUAL, DiffType.CHARS_EQUAL):
                    continue
                content = "\n".join([ele.element["text"] for ele in diff["right_eles"]])
                tpl_content = "\n".join([ele.element["text"] for ele in diff["left_eles"]])
                if diff["type"].endswith("delete"):
                    suggestion = f"合同{chapter}，请补充“{tpl_content}”"
                elif diff["type"].endswith("insert"):
                    suggestion = f"合同{chapter}，请删除“{content}”"
                else:
                    suggestion = f"合同{chapter}，请将“{content}”修改为“{tpl_content}”"
                # annotation for suggestion
                _diff_outlines = defaultdict(list)
                for page_str, outlines in diff["right_outline"].items():
                    page = page_str.removeprefix("page")
                    _diff_outlines[page].extend(outlines)
                for page, outlines in _diff_outlines.items():
                    self._annotations.append((page, outlines, suggestion))

                suggestions.append(suggestion)
            return "\n\n".join(suggestions)
        if self.chapters:
            return f"请在{P_CHAPTER_AND.sub('、', self.chapters[0])}中补充“ {self.content}”"
        return f"请在文档中补充“{self.content}”"

    @property
    def annotations(self):
        return self._annotations


class LawTemplateSchema(BaseModel):
    label: Literal["范文", "法规"]
    contents: list[LawTplContent] = Field(default_factory=list, min_length=1)

    _reason: dict = PrivateAttr(default_factory=dict)

    @property
    def is_template(self):
        return self.label == "范文"

    @property
    def avg_ratio(self):
        return sum(content.ratio for content in self.contents) / len(self.contents)

    def template(self):
        return {
            "name": self.label,
            "content": "\n".join(f"◇{content.content}" for content in self.contents),
            "content_title": "合同范文",
        }

    def miss_reason(self):
        return {
            "type": "tpl_conflict",
            "matched": False,
            "template": self.template(),
            "reason_text": f"未找到与{self.label}相同的内容",
            "content_title": f"当前{self.label}",
        }

    @cached_property
    def reason(self):
        return self._reason or self.miss_reason()

    async def compare(self, reader, contract_paras):
        for content in self.contents:
            if contract_paras:
                chapters = get_chapter_info_by_outline(
                    reader, {contract_paras[0]["page"]: [contract_paras[0]["outline"]]}
                )
                chapter_name = chapters[0]["title"] if chapters else ""
                await content.find_diff_with_contract_paras(contract_paras, chapter_name)
            else:
                await content.find_diff(reader)

        current_group_outlines = defaultdict(list)
        for content in self.contents:
            for page, outlines in content.page_outlines().items():
                current_group_outlines[page].extend(outlines)

        if not current_group_outlines:
            return

        self._reason = {
            "diff": [_diff for content in self.contents for _diff in content.diff()],
            "template": self.template(),
            "outlines": current_group_outlines,
            "page": min(current_group_outlines.keys(), key=int),
            "reason_text": f"匹配到{self.label}的内容" if self.is_compliance else f"与{self.label}不一致",
            "xpath": reader and get_xpath_by_outlines(reader, current_group_outlines),
        }

    @property
    def is_compliance(self):
        return all(content.is_compliance for content in self.contents)

    @property
    def suggestion(self):
        return "\n\n".join(content.suggestion for content in self.contents if not content.is_compliance)


class LawTemplatesSchema(BaseModel):
    groups: list[LawTemplateSchema] = Field(default_factory=list, min_length=1)

    @staticmethod
    def group_sort_func(group: LawTemplateSchema):
        return group.avg_ratio <= 0, not group.is_template, -group.avg_ratio

    @cached_property
    def sorted_groups(self):
        return sorted(self.groups, key=self.group_sort_func)

    @staticmethod
    def create_contract_paras(contract_rects):
        contract_paras = []
        for idx, (content_text, pages_boxes) in enumerate(contract_rects or []):
            min_int = partial(min, key=int)
            pages_boxes = sorted(pages_boxes, key=min_int)
            page = min_int(pages_boxes[0])
            outline = get_bound_box(pages_boxes[0][page])

            para = generate_mocked_paras([content_text], page=page, start=idx)["paragraphs"][0]
            para["outline"] = outline
            contract_paras.append(para)

        return contract_paras

    async def compare(self, reader, name, contract_rects: ContractRects | None):
        contract_paras = self.create_contract_paras(contract_rects)
        top_chapters = (
            []
            if contract_paras
            else [[[chapter]] for chapter in reader.syllabus_dict.values() if chapter["level"] == 1]
        )
        is_compliance = False
        for group in self.groups:
            if contract_paras:
                group_contents = []  # 直接走for-else分支
            else:
                if not top_chapters:
                    continue
                group_contents = group.contents

            # 组内是且, 组间是或
            for content in group_contents:
                any_chapters = content.find_chapters(reader, top_chapters)
                if not any_chapters:
                    break  # 指定章节不存在
            else:
                await group.compare(reader, contract_paras)
                if group.is_compliance:
                    is_compliance = True

        group = self.sorted_groups[0]
        if is_compliance:
            suggestion = ""
        else:
            suggestion = group.suggestion
        group.reason["annotations"] = [annotation for content in group.contents for annotation in content.annotations]
        reasons = [group.reason for group in self.groups]

        schema_results_dict = {}
        for group in self.groups:
            for content in group.contents:
                results = content.generate_schema_results(name)
                schema_results_dict.update(results)

        schema_results = [schema_results_dict[key] for key in sorted(schema_results_dict)]

        return is_compliance, reasons, suggestion, schema_results
