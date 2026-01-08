import logging
from itertools import chain

from remarkable.common.pattern import PatternCollection
from remarkable.common.util import clean_txt
from remarkable.plugins.cgs.common.patterns_util import P_NUMBERING, R_CONJUNCTION
from remarkable.predictor.common_pattern import R_CN, R_COLON, R_COMMA, R_NOT_SENTENCE_END, R_SEMICOLON
from remarkable.predictor.ecitic_predictor.models.common import R_SPECIAL_TIPS
from remarkable.predictor.ecitic_predictor.models.splitter_mixin import ParaSplitterMixin
from remarkable.predictor.models.middle_paras import MiddleParas
from remarkable.predictor.models.para_match import ParaMatch
from remarkable.predictor.models.row_match import RowMatch
from remarkable.predictor.models.syllabus_based import SyllabusBased
from remarkable.predictor.models.syllabus_elt_v2 import SyllabusEltV2
from remarkable.predictor.models.table_kv import KeyValueTable
from remarkable.predictor.schema_answer import CharResult

logger = logging.getLogger(__name__)

R_LEFT_BRACKET = r"\{〔【（\("
R_RIGHT_BRACKET = r"\)）】〕\}"


P_NON_EXTRACTED_PARAGRAPH = PatternCollection(
    [
        rf"比例为?[{R_COLON}]",
        r"工作日",
        r"开放期",
        r"不(直接)?(投资于|参与)",
        r"保证金",
        r"备付金",
        r"不低于",
        r"如(法律法规|监管机构)",
        r"满足(以下|下述)",
        r"如.*（可.*|其他品种）",
        r"目标日期的?临近",
        r"在本基金.*前提下.*(相关责任|一致意见)",
        r"(协商|达成)一致",
        r"承担责任",
        r"内部制度(的?相关)?规定",
        rf"满足{R_NOT_SENTENCE_END}*要求",
        r"挂钩标",
    ]
)
P_NON_EXTRACTED_SENTENCE = PatternCollection(
    [
        r"^以下简称|下同|此外|从其规定|^但[须需]符合.*?规定|提高投资效率|进行风险管理|持有人大会",
        r"((法律法规|监管部门|根据)[{R_CONJUNCTION}]?){{1,2}}(的|另有|相关)?规定",
        r"此类业务.*",
        r"所投资(资产)?管理产品.*",
        r"由此承担.*",
        r"放大投资",
        r"相应的?利息",
        r"费用",
    ]
)

R_BRACKET = rf"{R_LEFT_BRACKET}{R_RIGHT_BRACKET}"

P_BRACKET_RANGE = PatternCollection(
    rf"[{R_LEFT_BRACKET}](?P<context>.*(?:[^{R_BRACKET}]|[{R_LEFT_BRACKET}](?:[^{R_BRACKET}]|[{R_LEFT_BRACKET}][^{R_BRACKET}]*[{R_RIGHT_BRACKET}])*[{R_RIGHT_BRACKET}]))[{R_RIGHT_BRACKET}]"
)
P_EXCLUDE_SENTENCE_BRACKET_RANGE = PatternCollection(
    rf"[{R_LEFT_BRACKET}](?:[^{R_BRACKET}]|[{R_LEFT_BRACKET}]([^{R_BRACKET}]|[{R_LEFT_BRACKET}][^{R_BRACKET}]*[{R_RIGHT_BRACKET}])*[{R_RIGHT_BRACKET}])*[{R_RIGHT_BRACKET}]"
)

P_NOT_BRACKET = PatternCollection(
    [
        rf"(?<=互联互通机制下)[{R_LEFT_BRACKET}](?=包括)",
        rf"[{R_RIGHT_BRACKET}](?=允许投资的标的)",
        rf"[{R_LEFT_BRACKET}]?(\d+\.[A-Z]+|\d{{1,3}}([,，]\d{{3}})+|含\d+天)[{R_RIGHT_BRACKET}]?",
        r"依法.*发行的资产管理产品",
        # https://gitpd.paodingai.com/cheftin/docs_scriber/-/issues/4353#note_500066
        rf"利率互换[{R_LEFT_BRACKET}]仅限((银行间|交易所)[和与]?){{2}}[{R_RIGHT_BRACKET}]",
    ]
)

P_IGNORED_SENTENCES = PatternCollection(
    [
        r"^\s+\d+$",
        r"^\s*(……)?[”\"]$",
        r"^(其他|简称)$",
        # https://gitpd.paodingai.com/cheftin/docs_scriber/-/issues/4353#note_497319
        r"本资产管理计划可能",
        # https://gitpd.paodingai.com/cheftin/docs_scriber/-/issues/7939#note_782468
        r"所列示资产.*计入相应资产类别计算",
        r"资产委托人已充分理解.*风险",
    ]
)

R_PATTERN_CENTRE = rf"[{R_LEFT_BRACKET}][^{R_BRACKET}]*[{R_RIGHT_BRACKET}]"
R_PAT_LEFT = rf"[{R_LEFT_BRACKET}](?:[^{R_BRACKET}]|"
R_PAT_RIGHT = rf")*[{R_RIGHT_BRACKET}]"

R_SPLIT_SYMBOL = rf"、，,.。{R_SEMICOLON}{R_COLON}{R_LEFT_BRACKET}"


def pattern_generate(pattern, depth=2):
    while depth:
        pattern = R_PAT_LEFT + pattern + R_PAT_RIGHT
        depth -= 1
    return pattern


class ScopeSplitter:
    """
    投资范围拆分器
    拆分规则：
        1、主要根据、和及拆分
        2、拆分带有括号的内容
    """

    P_PREFIX = PatternCollection(
        rf"[{R_CN}]{{2,10}}(?<!简称)[:：]|^[^{R_LEFT_BRACKET}]+?(可投资于|可投资|投资于|可参与)|(?<![{R_LEFT_BRACKET}])包?[括含](但?不限于)?|主要为"
    )
    P_SUFFIX = PatternCollection(
        [rf"[{R_RIGHT_BRACKET}](?P<context>.*{R_NOT_SENTENCE_END}+)[{R_COMMA}、。{R_SEMICOLON}]?"]
    )
    P_NOT_PREFIX = PatternCollection(
        [
            r"(?<!不)[均包][括含]",
            r"(?<!不)[括含]",
        ]
    )
    P_EXCLUDE_SENTENCE_TEXT = PatternCollection(
        [
            r"及其(?![他它])",
            r"(?<=次级债券)及其(?=[他它])",
            r"(?<=指数成份股)及",
            r"(?<=法律|法规|核准|上市)[或及]",
            r"(?<=发行|网上)[或和、]",
            # https://gitpd.paodingai.com/cheftin/docs_scriber/-/issues/4353
            r"(?<!出借给证券金融)(?<!及其子)公司[及或和、]",
            r"[或和、](?=注册|核准|网下)",
            r"(?<=内地|香港|台湾|澳门|大陆)与",
            r"(?<=证券交易所|期货交易所)[及或和、]",
            r"经港股通投资于",
            # https://gitpd.paodingai.com/cheftin/docs_scriber/-/issues/4353#note_497329
            r"依法发行及上市",
            r"基金(公司)?及(基金)?子公司",
            # https://gitpd.paodingai.com/cheftin/docs_scriber/-/issues/4353#note_497330
            rf"[^{R_SPLIT_SYMBOL}]*除外",
            # https://gitpd.paodingai.com/cheftin/docs_scriber/-/issues/4353#note_499924
            r"((交易所|银行间)[\/和]?){2}",
            # https://gitpd.paodingai.com/cheftin/docs_scriber/-/issues/4353#note_500131
            r"((主板|科创板|创业板)[、和与或]?){1,3}以?及其他依法发行上市的股票",
            rf"不超过{R_NOT_SENTENCE_END}*",
            # https://gitpd.paodingai.com/cheftin/docs_scriber/-/issues/4353#note_500047
            # rf"依法{R_NOT_SENTENCE_END}*机构[{R_LEFT_BRACKET}][均包]?[括含].*[{R_RIGHT_BRACKET}]{R_NOT_SENTENCE_END}*",
            # https://gitpd.paodingai.com/cheftin/docs_scriber/-/issues/4353#note_499820
            # 公司描述和股票代码
            rf"[(（]{R_NOT_SENTENCE_END}*股票代码[{R_COLON}][^{R_RIGHT_BRACKET}]*[)）]",
            rf"((法律法规|中国证监会|中国人民银行)[{R_CONJUNCTION}]?){{1,3}}认可{R_NOT_SENTENCE_END}*工具",
            *P_NOT_BRACKET.patterns,
            # https://gitpd.paodingai.com/cheftin/docs_scriber/-/issues/7939#note_782468
            r"所列示资产.*计入相应资产类别计算",
            r"资产委托人已充分理解.*风险",
            rf"在{R_NOT_SENTENCE_END}*交易所{R_NOT_SENTENCE_END}*设立的交易场所",
        ]
    )
    P_SPLITTER_NUMBERING = P_NUMBERING
    P_LINK_SENTENCE = PatternCollection(
        # [
        #     r"(.*类)?[:：]",
        #     rf"[{R_SPLIT_SYMBOL}和(或者?)即]",
        #     r"(本(基金|计划))?可?参?与",
        #     r"(?<!式)以?及",
        #     r"(?<!不)(?<!不均|不包)[均包]?[括含](但?不限于)?",
        #     rf"等.*?[{R_SPLIT_SYMBOL}和或及]?",
        #     rf"[^。；;(形式){R_COLON}]{{1,5}}投资于",
        #     r"仅限于",
        #     r"主要为",
        #     r"(?<=出借|融资)业务",
        #     r"\/",
        #     r"如",
        # ],
        rf"(.*类)?[:：]|(?<!以内)[{R_SPLIT_SYMBOL}和(或者?)即及]|等.*?[{R_SPLIT_SYMBOL}和(或者?)即及]?|(本(基金|计划))?可?参?与|(?<!式)以?及|(?<!不)(?<!不均|不包)只?[均包]?(?<!以内[{R_LEFT_BRACKET}])[括含](但?不限于)?|[^{R_SPLIT_SYMBOL}(形式)]{{1,5}}(?<!不可)投资于|仅限于|主要为|(?<=出借|融资)业务|\/|如"
    )

    P_EXCLUDE_PARAGRAPH = PatternCollection(
        [
            # https://gitpd.paodingai.com/cheftin/docs_scriber/-/issues/7939#note_782055
            rf"持有人在此授权并同意[{R_COLON}]",
            r"拟投资于上述投资范围中未明确列示",
        ]
    )

    def parse_bracket(self, text, next_pos, exclude_pos_text, content_list):
        # 1、判断是否为带有（）的句子 or 含有不拆分的括号内容
        if not (match_bracket_range := P_BRACKET_RANGE.nexts(text)) or P_NOT_BRACKET.nexts(text):
            return False
        context = match_bracket_range.group("context")
        context_start = match_bracket_range.start("context")
        # 2、判断是是否有前置语句 和拆分符号
        if not (match_prefix := self.P_PREFIX.nexts(context)) and not self.P_LINK_SENTENCE.nexts(context):
            return False
        # 获取后缀
        suffix_text = ""
        suffix_range = (0, 0)
        if match_suffix := self.P_SUFFIX.nexts(text):
            suffix_text = match_suffix.group("context")
            suffix_range = match_suffix.span()
        content_list.append((text[: context_start - 1], [(next_pos, next_pos + context_start - 1)]))
        # 前缀语句如果为不包含、不含的时候，不拆
        match_not_prefix = self.P_NOT_PREFIX.nexts(context) if self.P_NOT_PREFIX else None
        if match_prefix and match_not_prefix and match_prefix.end() != match_not_prefix.end():
            context = context[match_prefix.end() :]
            context_start += match_prefix.end()
        next_pos_sub = 0
        exclude_pos_bracket = []
        for _res in P_EXCLUDE_SENTENCE_BRACKET_RANGE.finditer(context):
            exclude_pos_bracket.extend(range(*_res.span()))
        for res in chain(self.P_LINK_SENTENCE.finditer(context), (None,)):
            sub_start, sub_end = res.span() if res else (len(context), 0)
            if sub_start + context_start + next_pos in exclude_pos_text or sub_start in exclude_pos_bracket:
                continue
            if next_pos_sub != sub_start:
                temp_text = context[next_pos_sub:sub_start]
                if not P_IGNORED_SENTENCES.nexts(temp_text):
                    parse_bracket = self.parse_bracket(
                        temp_text,
                        next_pos + next_pos_sub + context_start,
                        exclude_pos_text,
                        content_list,
                    )
                    if not parse_bracket and not P_NON_EXTRACTED_SENTENCE.nexts(temp_text):
                        if match_suffix:
                            content_list.append(
                                (
                                    temp_text + suffix_text,
                                    [
                                        (next_pos + next_pos_sub + context_start, next_pos + sub_start + context_start),
                                        (next_pos + suffix_range[0] + 1, next_pos + suffix_range[1]),
                                    ],
                                )
                            )
                        else:
                            content_list.append(
                                (
                                    temp_text,
                                    [(next_pos + next_pos_sub + context_start, next_pos + sub_start + context_start)],
                                )
                            )
            next_pos_sub = sub_end
        return True

    def delete_numbering(self, paragraph_text, chars):
        if self.P_SPLITTER_NUMBERING and (match_numering := self.P_SPLITTER_NUMBERING.nexts(paragraph_text)):
            return paragraph_text[match_numering.end() :], chars[match_numering.end() :], True
        return paragraph_text, chars, False

    def paragraph_text(self, element_result):
        if isinstance(element_result, dict):
            if not element_result.get("chars"):
                return "", [], False
            paragraph_text, chars, has_numbering = self.delete_numbering(
                element_result.get("text", "").rstrip(), element_result["chars"]
            )
        else:
            paragraph_text, chars, has_numbering = self.delete_numbering(
                element_result.text.rstrip(), element_result.chars
            )
        return paragraph_text, chars, has_numbering

    @staticmethod
    def element_index(element_result):
        if isinstance(element_result, dict):
            return element_result["index"]
        return element_result.element["index"]

    def find_paragraph(self, element_result, start_index):
        for i in range(1, 10):
            _, prefix_para = self.pdfinsight.find_element_by_index(self.element_index(element_result) - i)
            if prefix_para["index"] >= start_index:
                break
            prefix_para_text, _, prefix_has_numbering = self.paragraph_text(prefix_para)
            if R_SPECIAL_TIPS.nexts(prefix_para_text):
                return True, prefix_para_text, prefix_has_numbering
            if prefix_has_numbering:
                return False, prefix_para_text, prefix_has_numbering
        return False, "", False

    def run(self, element_result, start_index):
        paragraph_text, chars, has_numbering = self.paragraph_text(element_result)
        if not paragraph_text:
            return []
        if temp_match := R_SPECIAL_TIPS.nexts(paragraph_text):
            if res_chars := chars[temp_match.end() :]:
                return [res_chars]
        match_special, prefix_para_text, prefix_has_numbering = self.find_paragraph(element_result, start_index)
        if match_special:
            return [chars]

        if self.P_EXCLUDE_PARAGRAPH and self.P_EXCLUDE_PARAGRAPH.nexts(paragraph_text):
            return []
        if has_numbering and len(paragraph_text) <= 15:
            return []
        match = self.P_PREFIX.nexts(paragraph_text)
        if (not match and not has_numbering) or P_NON_EXTRACTED_PARAGRAPH.nexts(paragraph_text):
            if not (len(prefix_para_text) <= 15 and prefix_has_numbering):
                return []
        next_pos = match.end() if match else 0
        exclude_pos_bracket = []
        exclude_pos_text = []
        for _res in P_EXCLUDE_SENTENCE_BRACKET_RANGE.finditer(paragraph_text):
            exclude_pos_bracket.extend(range(*_res.span()))
        if self.P_EXCLUDE_SENTENCE_TEXT:
            for _res in self.P_EXCLUDE_SENTENCE_TEXT.finditer(paragraph_text):
                exclude_pos_text.extend(range(*_res.span()))
        content_list = []
        for link_res in chain(self.P_LINK_SENTENCE.finditer(paragraph_text), (None,)):
            start, end = link_res.span() if link_res else (len(paragraph_text), 0)
            if start in exclude_pos_bracket or start in exclude_pos_text:
                continue
            if start < next_pos:
                continue
            if next_pos != start:
                if temp := paragraph_text[next_pos:start]:
                    # 1、两个拆分符合之间有空格，要判断是否有真实的内容
                    # 2、判断是否是忽略的句子
                    if clean_txt(temp) and not P_IGNORED_SENTENCES.nexts(temp):
                        match_bracket = self.parse_bracket(temp, next_pos, exclude_pos_text, content_list)
                        if (
                            not match_bracket
                            and (not match or (match and next_pos >= match.end()))
                            and not P_NON_EXTRACTED_SENTENCE.nexts(temp)
                        ):
                            content_list.append((temp, [(next_pos, start)]))
            next_pos = end
        group_chars_list = []
        for _, span in content_list:
            dst_chars_list = []
            for start, end in span:
                dst_chars_list.extend(chars[start:end])
            group_chars_list.append(dst_chars_list)
        return group_chars_list

    def split(self, predict_elements):
        element_results = []
        first_element_index = self.element_index(predict_elements[0]) if predict_elements else None
        for predict_element in predict_elements:
            if dst_chars_list := self.run(predict_element, first_element_index):
                results = []
                for dst_chars in dst_chars_list:
                    if isinstance(predict_element, dict):
                        result = CharResult(
                            element=predict_element,
                            chars=dst_chars,
                        )
                    else:
                        result = CharResult(
                            element=predict_element.element,
                            chars=dst_chars,
                        )
                    results.append(result)
                element_results.extend(results)
        return element_results


class ScopeInvestmentSyllabus(ParaSplitterMixin, SyllabusEltV2, ScopeSplitter):
    pass


class ParaMatchSplitter(ParaSplitterMixin, ParaMatch, ScopeSplitter):
    pass


class ScopeInvestmentMiddle(ParaSplitterMixin, MiddleParas, ScopeSplitter):
    pass


class ScopeInvestmentSyllabusBased(ParaSplitterMixin, SyllabusBased, ScopeSplitter):
    pass


class RowMatchSplitter(ParaSplitterMixin, RowMatch, ScopeSplitter):
    pass


class KeyValueTableSplitter(KeyValueTable, ScopeSplitter):
    def predict_schema_answer(self, elements):
        parent_answers = super().predict_schema_answer(elements)
        if not parent_answers:
            return parent_answers
        predict_elements = []
        for answer_result in parent_answers:
            if not isinstance(answer_result, dict):
                continue
            for key, answers in answer_result.items():
                if key != "原文":
                    continue
                for answer in answers:
                    predict_elements.extend(answer.element_results)
        if not (element_results := self.split(predict_elements)):
            return parent_answers
        answer_results = [self.create_result(element_results, column="拆分")]
        for parent_answer in parent_answers:
            if isinstance(parent_answer, dict):
                answer_results.extend(parent_answer.get("原文", []))
            elif parent_answer.schema.name == "原文":
                answer_results.append(parent_answer)
                break
        return answer_results
