import re
from collections import Counter, namedtuple
from copy import deepcopy

from remarkable.common.pattern import PatternCollection
from remarkable.common.util import clean_txt, index_in_space_string
from remarkable.predictor.models.syllabus_elt_v2 import SyllabusEltV2
from remarkable.predictor.schema_answer import CharResult, NoBoxResult, ParagraphResult, TableResult
from remarkable.predictor.sse_predictor import SSEPoc


class NewShareholder(SyllabusEltV2):
    next_p = [
        r"^.{,4}基本[情详状概][情况]$",
        r"^((?!(合伙人|计划)).)*基本[情详状概][情况]如下\w*?[:：]?$",
    ]
    current_p = [
        r"[创建成设][建立办]于(?P<dst>.*)?[年月日号]|[于在].*?[年月日号].*?[创建成设][建立办]",
        r"(?P<dst>.*)?身份证?编?号.*?\d+",
    ]
    group_patterns = PatternCollection(current_p + next_p + [r"^[详请]见.*?股东"])
    detail_next_patterns = PatternCollection(next_p)
    detail_current_patterns = PatternCollection(current_p)
    syllabus_title_patterns = PatternCollection(
        [r"^\s*[第一二三四五六七八九十\d\s章节.、\-()（）\[\]]*\s*(?P<dst>[\w\s]+)"]
    )
    title_patterns = PatternCollection(
        [
            r"(?P<dst>\w+)([直间]接)持有.*?基本[情详状概][情况]",
            r"(?P<dst>\w+)基本[情详状概][情况]",
            r"(?P<dst>\w+)持有.*?基本[情详状概][情况]",
            r"(?P<dst>\w+).*?身份证?编?号.*?\d+",
        ]
    )
    name_patterns = PatternCollection(
        [
            r"^(公司|企业|集团|股东|组织|股东组织|组织股东)?名称$",
        ]
    )
    nationality_patterns = PatternCollection([r"(?P<dst>[^\d,\.，。]+)国籍", r"国籍(?P<dst>[^\d,\.，。]+)"])
    identity_number_patterns = PatternCollection([r"身份证?\D*(?P<dst>[\d\*Xx]+)"])
    pra_right_patterns = PatternCollection([r"(?P<dst>\w+(境外|永久)+\w+权)"])

    def revise_model(self, data):
        """
        "发行人基本情况|发行人的股本情况|最近一年发行人新增股东情况|最近一年新增股东的基本情况|曾年生"
        -> "发行人基本情况|发行人的股本情况|最近一年发行人新增股东情况|最近一年新增股东的基本情况"
        """
        ret = Counter()
        for key, count in data.items():
            titles = key.split("|")
            parent = None
            # 倒序取到符合 pattern 的章节名
            for idx, title in enumerate(titles[::-1]):
                if any(re.search(reg, title) for reg in self.config.get("patterns", [])):
                    parent = "|".join(titles[:-idx] if idx > 0 else titles)
                    break
            if parent:
                ret[parent] = ret.get(parent, 0) + count
        return ret

    def filter_elts(self, syllabus):
        elements = []
        elts = list(range(syllabus["range"][0], syllabus["range"][1]))
        aim_idx = 0
        for idx, elt_idx in enumerate(elts):
            elt_type, elt = self.pdfinsight.find_element_by_index(elt_idx)
            if not elt:
                continue
            if self.pdfinsight_syllabus.is_syllabus_elt(elt) and PatternCollection(self.config.get("patterns")).nexts(
                clean_txt(elt["text"])
            ):
                aim_idx = idx
            elements.append((elt_type, elt))
        # 1. 去掉多余的 syllabuses
        # 2. 仅保留段落&表格
        for elt_type, elt in elements[aim_idx:]:
            if elt_type in ("PARAGRAPH", "TABLE"):
                yield elt_type, elt

    def offset_idx(self, elements, last_idx):
        offset = 0
        for _, pre_elt in elements[:last_idx][::-1]:
            if not self.pdfinsight_syllabus.is_syllabus_elt(pre_elt):
                break
        return offset

    def calc_group_syllabus_level(self, syllabus):
        """
        A(L1)
            -> a(L2)   # 期望获取到这一章节的 level, 最适合作为分组依据
                -> a1(L3)  # 多个连续的同级章节 level 只算一个 count
                -> a2(L3)
                    -> a21(L4)
                    -> ...
                -> ...
                -> an(L3)
            -> b(L2)
                -> b1(L3)
                -> b2(L3)
                -> ...
                -> bn(L3)
            -> ...
                -> ...
                -> ...
        @param syllabus: 章节
        @return: 当前章节下最适合作为分组依据的子章节 level
        """

        def count_level(syl):
            nonlocal counter, last_level
            for idx in syl["children"]:
                item = self.pdfinsight_syllabus.syllabus_dict[idx]
                current_level = item["level"]
                if current_level != last_level:
                    # 多个连续的同级章节 level 只算一个 count
                    counter.update([current_level])
                last_level = current_level
                count_level(item)

        counter, last_level = Counter(), 0
        count_level(syllabus)
        for level, _ in counter.most_common():
            return level

    def group_by_syllabus(self, syllabus):
        elements = list(self.filter_elts(syllabus))
        if any(
            re.search(r"[无未没]有?新增加?的?股东", clean_txt(e["text"]))
            for e_type, e in elements
            if e_type == "PARAGRAPH"
        ):
            # 段落中只要有"没有新增股东"相关描述, 就返回空(一般这种情况只有一段话, 就是没有新增股东云云)
            return
        level = self.calc_group_syllabus_level(syllabus)
        if not level or level <= syllabus["level"]:
            # 没有子章节暂时先不考虑
            return
        last_idx = 0
        for idx, (_, elt) in enumerate(elements):
            if (
                self.pdfinsight_syllabus.is_syllabus_elt(elt)
                and self.pdfinsight_syllabus.elt_syllabus_dict[elt["index"]]["level"] == level
            ):
                if last_idx:
                    yield elements[
                        last_idx - self.offset_idx(elements, last_idx) : idx - self.offset_idx(elements, idx)
                    ]
                last_idx = idx
        yield elements[last_idx - self.offset_idx(elements, last_idx) :]

    def predict_schema_answer(self, elements):
        answer_results = []
        model_data = self.get_model_data()
        if not model_data:
            return answer_results
        aim_syllabuses = self.get_aim_syllabus(self.revise_model(model_data))
        if not aim_syllabuses:
            return answer_results

        # 只取第一个匹配到的章节
        aim_syllabus = list(aim_syllabuses)[0]
        for groups in self.group_by_syllabus(aim_syllabus):
            if not groups:
                # 分配到空组, 不太常见的情况, 忽略
                continue
            new_groups = self.split_elements(groups)
            result = {}
            title_name_result = self.parse_title_name(new_groups)
            if title_name_result:
                result[self.schema.name] = [self.create_result([title_name_result], column=self.schema.name)]

            name_from_table, name_result = self.parse_name(title_name_result, new_groups)
            if name_result:
                result["名称"] = [self.create_result([name_result], column="名称")]

            if self.config.get("need_detail", False):
                detail = self.parse_detail(new_groups)
                if detail:
                    result["详见"] = [self.create_result([detail], column="详见")]

            found_date = self.parse_found_date(new_groups)
            if found_date:
                result["成立时间（非自然人）"] = [self.create_result([found_date], column="成立时间（非自然人）")]

            if not result.get("成立时间（非自然人）"):
                nationality = self.parse_nationality(new_groups)
                if nationality:
                    result["国籍（自然人）"] = [self.create_result([nationality], column="国籍（自然人）")]
                pra_right = self.parse_pra_right(new_groups)
                if pra_right:
                    result["是否拥有永久境外居留权（自然人）"] = [
                        self.create_result([pra_right], column="是否拥有永久境外居留权（自然人）")
                    ]
                identity_number = self.parse_identity_number(new_groups)
                if identity_number:
                    result["身份证号码（自然人）"] = [
                        self.create_result([identity_number], column="身份证号码（自然人）")
                    ]

            # NOTE: 该字段需要尽可能的提取到内容, 类型不确定无法进行下面属性的提取
            shareholder_type = self.parse_shareholder_type(result, new_groups, name_result if name_from_table else None)
            if shareholder_type:
                result["股东类型"] = [self.create_result([shareholder_type], column="股东类型")]
            shareholder_enum = self.shareholder_enum(shareholder_type)

            if shareholder_enum == "法人":
                # TODO:
                # '注册资本（法人）': None,
                # '实收资本（法人）': None,
                # '注册地（法人）': None,
                # '主要生产经营地（法人）': None,
                # '股东构成（法人）': None,
                # '实际控制人（法人）': None,
                pass
            elif shareholder_enum == "合伙企业":
                business_premises = self.parse_business_premises(new_groups)
                if business_premises:
                    result["经营场所（合伙企业）"] = [
                        self.create_result([business_premises], column="经营场所（合伙企业）")
                    ]
                # '出资人构成（合伙企业）': None,

            answer_results.append(result)
        return answer_results

    def parse_title_name(self, groups):
        ret = None
        if groups:
            _, first_elt = groups[0]
            if self.pdfinsight_syllabus.is_syllabus_elt(first_elt) and "情况" not in clean_txt(first_elt["text"]):
                ret = self.parse_char_result(self.syllabus_title_patterns, groups[:1])
        return ret or self.parse_char_result(self.title_patterns, groups)

    def parse_name(self, title_name_result, groups):
        from_table = False
        ret = self.parse_char_result(self.name_patterns, groups, offset=1)
        if ret:
            from_table = True
        patterns = deepcopy(self.current_p)
        if title_name_result:
            patterns.insert(0, rf"(?P<dst>{title_name_result.text})")
        if not ret:
            ret = self.parse_char_result(PatternCollection(patterns), groups)
        return from_table, ret

    @staticmethod
    def split_elements(groups):
        new_groups = []
        for elt_type, elt in groups:
            # 重组表格, 从左到右从上到下, 每个单元格作为一个段落返回
            if elt_type == "TABLE":
                for idx in sorted(elt["cells"].keys(), key=lambda x: (int(x.split("_")[0]), int(x.split("_")[1]))):
                    fake_para = elt["cells"][idx]
                    fake_para["_table"] = elt
                    new_groups.append((elt_type, fake_para))
            else:
                new_groups.append((elt_type, elt))
        return new_groups

    def parse_nationality(self, groups):
        return self.parse_char_result(self.nationality_patterns, groups)

    @staticmethod
    def parse_char_result(pattern: PatternCollection, elements: list[tuple[str, dict]], offset=0) -> CharResult | None:
        for idx, (_, elt) in enumerate(elements):
            # 去空格
            elt_text = clean_txt(elt["text"])
            elt_chars = [i for i in elt["chars"] if not re.search(r"^\s+$", i["text"])]
            # 只要 match 就返回
            match = pattern.nexts(elt_text)
            if match:
                if offset == 0:
                    start, end = index_in_space_string(elt_text, match.span("dst"))
                    return CharResult({}, elt_chars[start:end])
                elif len(elements) > idx + offset:
                    return CharResult({}, elements[idx + offset][1]["chars"])
                else:
                    return CharResult({}, elements[-1][1]["chars"])
        return None

    def parse_identity_number(self, new_groups):
        return self.parse_char_result(self.identity_number_patterns, new_groups)

    def parse_pra_right(self, new_groups):
        return self.parse_char_result(self.pra_right_patterns, new_groups)

    def parse_detail(self, new_groups):
        if len(new_groups) < 3:
            # 两段内容取最后一段
            elt_type, elt = new_groups[-1]
            return TableResult(elt["_table"], []) if elt_type == "TABLE" else ParagraphResult(elt, elt["chars"])

        for idx, (elt_type, elt) in enumerate(new_groups):
            match = self.parse_char_result(self.detail_next_patterns, [(elt_type, elt)], offset=1)
            # 标题下方段落 or 表格
            if match and idx < len(new_groups) - 1:
                elt_type, item = new_groups[idx + 1]
                return TableResult(item["_table"], []) if elt_type == "TABLE" else ParagraphResult(item, item["chars"])
        for elt_type, elt in new_groups:
            # 无标题, 取段落
            match = self.parse_char_result(self.detail_current_patterns, [(elt_type, elt)])
            if match:
                return TableResult(elt["_table"], []) if elt_type == "TABLE" else ParagraphResult(elt, elt["chars"])
        return None

    def parse_shareholder_type(self, result, new_groups, name_result=None):
        # 名称取自table相对准确, 更适合作为判断股东类型依据
        if name_result:
            return NoBoxResult(name_result.text)
        # 其次则是同为表格中的公司类别描述, 但可能没有
        ret = self.parse_char_result(PatternCollection([r"^(公司|企业)类[型别]$"]), new_groups, offset=1)
        # 再次去详见内容碰碰运气
        if not ret and result.get("详见"):
            ret = self.parse_char_result(PatternCollection([r"(?P<dst>(有限)?(责任)?(合伙)?(企业|公司))"]), new_groups)
        if ret:
            return ret
        # 最坏的情况, 所有正则全miss, 则根据已提取到的column后缀来判断
        if any(k.endswith("（法人）") for k in result):
            return NoBoxResult("法人")
        elif any(k.endswith("（自然人）") for k in result):
            return NoBoxResult("自然人")
        elif any(k.endswith("（合伙企业）") for k in result):
            return NoBoxResult("合伙企业")
        return ret

    def parse_found_date(self, new_groups):
        return self.parse_char_result(PatternCollection([r"^([成创]立|创建)(日期|时间)$"]), new_groups, offset=1)

    @staticmethod
    def shareholder_enum(shareholder_type):
        if not shareholder_type:
            return None
        schema = namedtuple("Schema", ["name"])._make(["股东类型"])
        return SSEPoc().predict(shareholder_type, schema)

    def parse_business_premises(self, new_groups):
        return self.parse_char_result(PatternCollection([r"[经营办][业营公]场?[地所点][址点]?$"]), new_groups, offset=1)
