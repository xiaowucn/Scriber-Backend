import logging
import re

from remarkable.common.pattern import PatternCollection
from remarkable.common.util import clean_txt, extract_text_by_ocr
from remarkable.config import get_config
from remarkable.predictor.models.base_model import BaseModel
from remarkable.predictor.schema_answer import CharResult, PredictorResultGroup

logger = logging.getLogger(__name__)

chapter_p = [
    re.compile(r"自基金转型以来基金(份额)?累计.*?净值增长率变动及其与同期业绩比较基准收益率变动的比较"),
    re.compile(r"自基金.*?以来基金(份额)?累计.*?净值增长率变动及其与同期业绩比较基准收益率变动的比较"),
    re.compile(r"3\.2\.1"),
    re.compile(r"3\.2\.2"),
    re.compile(r"广发.*?[A-Z].$"),
]

time_p = PatternCollection([r"20\d{2}-\d{2}-\d"])
# https://gitpd.paodingai.com/cheftin/docs_scriber/-/issues/2436
image_title_p = PatternCollection(
    [
        r"(?P<dst>广发.*?)[-—一\s]*?业绩基准",
        r"(?P<dst>广发.*?ETF.*?联接[A-Z])",
        r"(?P<dst>广发[-—一0-9A-Z\u4e00-\u9fa5]+[-—一\(（）\)A-Z]+[\(（）\)A-Z]+)",
        r"(?P<dst>广发[0-9A-Z\u4e00-\u9fa5\-—一]+[0-9A-Z\u4e00-\u9fa5]+)",
    ]
)

share_name_p = PatternCollection(
    [r"^\d.*?(?P<dst>广发.*[A-Z])", r"(?P<dst>^广发.*[A-Z].?)"],
    re.I,
)

share_name_p_1 = PatternCollection([r"\w+增长率.*?[与和及].*?收益率.*?对比图"])

fix_tail_p = PatternCollection([r"^[-—一\s]*业绩基准"])


class ReportTime(BaseModel):
    def train(self, dataset, **kwargs):
        pass

    @property
    def ocr_name(self):
        return get_config("client.ocr.service", "pai")

    def predict_schema_answer(self, elements):
        result = []
        aim_syllabuses = []
        for pattern in chapter_p:
            syllabuses = self.pdfinsight.find_sylls_by_pattern([pattern])
            if syllabuses:
                aim_syllabuses.extend(syllabuses)
        if not aim_syllabuses:
            return result
        for aim_syllabus in aim_syllabuses:
            all_elements = {}
            start, end = aim_syllabus["range"]
            for idx in range(start, end):
                _, elt = self.pdfinsight.find_element_by_index(idx)
                if not elt:
                    continue
                all_elements[idx] = elt

            share_idx_list = self.get_all_share_idx(all_elements)
            groups = []
            # if not share_idx_list:
            #     for element in all_elements.values():
            #         if element['class'] not in ['SHAPE', 'IMAGE']:
            #             continue
            #         groups.append(self.get_share_info(element, primary_key=1))
            #         break
            #     answer_result = PredictorResultGroup(
            #         groups,
            #         schema=self.predictor.parent.schema,
            #     )
            #     result.append({'报告期时间': [answer_result]})
            # else:
            for share_id in share_idx_list:
                for idx in range(share_id + 1, share_id + 6):
                    if idx in share_idx_list:
                        break
                    if idx not in all_elements:
                        _, element = self.pdfinsight.find_element_by_index(idx)
                    else:
                        element = all_elements[idx]
                    if not element:
                        continue
                    if element["class"] not in ["SHAPE", "IMAGE"]:
                        continue
                    groups.append(self.get_share_info(element, primary_key=1))
                    break  # 一个份额名称字段后面只包含一个图片信息
            if groups:
                answer_result = PredictorResultGroup(
                    groups,
                    schema=self.predictor.parent.schema,
                )
                result.append({"报告期时间": [answer_result]})
            if result:
                break
        return result

    @staticmethod
    def get_fixed_paras(paras):
        if len(paras) < 2:
            return paras
        if fix_tail_p.nexts(paras[-1]["text"]):
            paras[-2]["text"] += paras[-1]["text"]
            paras[-2]["chars"] += paras[-1]["chars"]
            paras.pop(-1)

        return paras

    def get_share_info(self, image, primary_key=None):
        start_time_answer, end_time_answer = None, None
        paras = extract_text_by_ocr(self.predictor.pdf_path, image["page"], image["outline"], self.ocr_name)
        paras = self.get_fixed_paras(paras)
        all_times = []
        share_para = {}
        dst_chars = []
        for para in paras:
            para["page"] = image["page"]
            para_text = clean_txt(para["text"])
            logger.info(f"image{image['index']} text: {para_text}")
            if time_p.nexts(para_text):
                all_times.append(para)
            if matcher := image_title_p.nexts(para_text):
                share_para = para
                for char in share_para["chars"]:
                    char["page"] = image["page"]
                dst_chars = self.get_dst_chars_from_matcher(matcher, para)
                # print(''.join([x['text'] for x in dst_chars]))
        if not all_times:
            return start_time_answer, end_time_answer
        start_time_para = all_times[0]
        for char in start_time_para["chars"]:
            char["page"] = image["page"]
        start_answer = self.create_result(
            [CharResult(start_time_para, start_time_para["chars"])],
            column="期初时间",
            schema=self.predictor.parent.find_child_schema("期初时间"),
            primary_key=primary_key,
        )
        end_time_para = all_times[-1]
        for char in end_time_para["chars"]:
            char["page"] = image["page"]
        end_answer = self.create_result(
            [CharResult(end_time_para, end_time_para["chars"])],
            column="期末时间",
            schema=self.predictor.parent.find_child_schema("期末时间"),
            primary_key=primary_key,
        )
        share_name = self.create_result(
            element_results=[CharResult(share_para, dst_chars)],
            column="份额名称",
            schema=self.predictor.parent.find_child_schema("份额名称"),
            primary_key=clean_txt(share_para.get("text") or "1"),
        )
        return [share_name, start_answer, end_answer]

    def get_all_share_idx(self, elements):
        ret = []
        for pattern in (share_name_p, share_name_p_1):
            for idx, element in elements.items():
                if element["class"] != "PARAGRAPH":
                    continue
                clean_text = clean_txt(element["text"])
                matcher = pattern.nexts(clean_text)
                if not matcher:
                    continue
                if not self.is_share_element(idx, elements):
                    continue
                ret.append(idx)
            if ret:
                break
        return ret

    @staticmethod
    def is_share_element(idx, elements):
        """
        判断元素组合类型
        正常情况：
        1. 规则名称段落+图片
            如果匹配到对应的规则名称，一般来说，下一个元素就是图片，直接判定结果为真
        非正常情况：
         2. 规则名称段落+干扰段落+图片
            如果匹配到了规则名称，下一个元素不是图片，则需向下接着查找，如果后续元素中前几个元素包含图片，那么一般认为这个就是需要的结果
            如果在下一个规则名称匹配到之前，中间还没有图片，那么就认为这条规则是错误的，应丢弃
        """
        if elements.get(idx + 1) and elements.get(idx + 1)["class"] == "IMAGE":
            return True
        for index, element in elements.items():
            if index <= idx:
                continue
            if element["class"] == "IMAGE":
                return True
            if element["class"] != "PARAGRAPH":
                continue
            clean_text = clean_txt(element["text"])
            if share_name_p.nexts(clean_text):
                return False
        return False
