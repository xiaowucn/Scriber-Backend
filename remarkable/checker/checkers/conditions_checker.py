import copy
import itertools
import logging
from collections import defaultdict
from itertools import zip_longest

from remarkable.checker.checkers.template_checker import BaseTemplateChecker
from remarkable.common.constants import RuleType
from remarkable.common.convert_number_util import NumberUtil
from remarkable.common.pattern import PatternCollection
from remarkable.common.util import clean_txt
from remarkable.plugins.cgs.common.enum_utils import ConvertContentEnum
from remarkable.plugins.cgs.common.extract_basic_info import ExtractFundBasicInfo
from remarkable.plugins.cgs.common.fund_classification import PublicFundClassifyName
from remarkable.plugins.cgs.common.para_similarity import DiffResult, ParagraphSimilarity
from remarkable.plugins.cgs.common.patterns_util import (
    P_EXCLUDE_SENTENCE,
    P_LINK_SENTENCE,
    P_PERCENTAGE_UNIT,
    P_PUBLIC_SIMILARITY_PATTERNS,
    P_PURE_PERCENTAGE_WITHOUT_UNIT,
    P_STOCK_SIMILARITY_PATTERN,
)
from remarkable.plugins.cgs.common.template_condition import (
    AllMatchRelation,
    ContentConditional,
    ContentValueRelation,
    ContentValueTypeEnum,
    TemplateName,
)
from remarkable.plugins.cgs.common.utils import (
    get_outlines,
    get_paragraphs_by_schema_fields,
    get_xpath_by_outlines,
)
from remarkable.plugins.cgs.schemas.reasons import (
    ConflictReasonItem,
    IgnoreConditionItem,
    MatchFailedItem,
    MatchReasonItem,
    MissContentReasonItem,
    NoMatchReasonItem,
    ResultItem,
    SchemaFailedItem,
    Template,
)
from remarkable.plugins.predict.common import is_paragraph_elt


class BaseConditionsChecker(BaseTemplateChecker):
    TEMPLATES = []
    P_SERIAL_NUM = PatternCollection(r"^[(（]?(?P<num>[\d一二三四五六七八九十]+)[）)]?")
    P_REPLACE_KEY = PatternCollection(r"{(?P<key>[A-Z]+_\d+)}")
    # https://gitpd.paodingai.com/cheftin/docs_scriber/-/issues/2272#note_351380
    SYNONYM_PATTERNS = P_PUBLIC_SIMILARITY_PATTERNS
    IGNORE_EXTRA_PARA = False
    # https://gitpd.paodingai.com/cheftin/docs_scriber/-/issues/2385#note_345021
    CONVERT_TYPES = ConvertContentEnum.member_values()
    SOURCE = ""

    def extract_template_by_inner_replace(self, template, paragraphs):
        # 段内替换
        # 文中固定位置提取（属性），一般为提取交易所、基金类型，
        # 配置为指定提取函数字符串,及默认值, 配置的函数需要添加至ExtractFundBasicInfo类中
        match_templates = []
        format_dict = {}
        for key, func_dict in template["rules"].items():
            if not hasattr(ExtractFundBasicInfo, func_dict["func"]):
                logging.error(f"Class {ExtractFundBasicInfo.__name__} has no {func_dict['func']}")
                val = "***"
            else:
                val = getattr(ExtractFundBasicInfo, func_dict["func"])(self)
            format_dict[key] = val
        for item in template["items"]:
            match_templates.extend(self.get_split_templates(item, paragraphs))
        return self.format_templates_by_match_result(match_templates, format_dict)

    def extract_template_by_inner_recombination(self, template, paragraphs: list[dict]):
        # 段内重组
        # 根据rules中配置的多个词组，拆分位置，取每个词组中连接次的位置，按顺序拼接
        # 部分词语会有条件，不满足则忽略
        match_templates = []
        format_dict = {}
        for key, condition in template["rules"].items():
            format_dict[key] = condition["default"]
            format_vals = None
            missing_vals = None
            for para in paragraphs:
                if not is_paragraph_elt(para):
                    continue
                content = clean_txt(para["text"])
                if not (res := condition["para_pattern"].nexts(content)):
                    continue

                # 多选段落，以“、与和及”等词进行拼接
                match_content = res.group("content")
                exclude_pos = []
                p_exclude = [P_EXCLUDE_SENTENCE]
                if pattern := condition.get("exclude_patterns"):
                    p_exclude.append(pattern)
                for check_pattern in p_exclude:
                    for _res in check_pattern.finditer(match_content):
                        exclude_pos.extend(range(*_res.span()))
                # 根据“、与和及”等词拆分当前段落，
                content_list = []
                next_pos = 0
                for link_res in P_LINK_SENTENCE.finditer(match_content):
                    start, end = link_res.span()
                    if start in exclude_pos:
                        continue
                    content_list.append((match_content[next_pos:start], link_res.group()))
                    next_pos = end
                if len(match_content) != next_pos:
                    content_list.append((match_content[next_pos:], ""))
                # 按联结词划分词组，按顺序匹配正则
                temp_format_vals = []
                temp_missing_vals = []
                for check_pattern in condition["patterns"]:
                    if not isinstance(check_pattern, dict):
                        logging.error("Template rules are incorrectly configured")
                        logging.error(template["items"])
                        continue
                    for idx, (value, link_str) in enumerate(content_list):
                        if self.manager.verify_condition(check_pattern.get("conditions")) and check_pattern[
                            "pattern"
                        ].nexts(value):
                            temp_format_vals.append((idx, [check_pattern["value"], link_str]))
                            break
                    else:
                        if self.manager.verify_condition(check_pattern.get("conditions")) and check_pattern.get(
                            "required", True
                        ):
                            temp_missing_vals.append(check_pattern["value"])

                if missing_vals is None or len(missing_vals) > len(temp_missing_vals):
                    missing_vals = temp_missing_vals
                    format_vals = temp_format_vals

            if format_vals or missing_vals:
                sorted_vals = []
                for _, vals in sorted(format_vals, key=lambda x: x[0]):
                    sorted_vals.extend(vals)
                # 默认不需要最后一位联结词
                format_val = "".join(sorted_vals[:-1])
                if missing_vals:
                    if format_val:
                        format_val = f"{format_val}、{'、'.join(missing_vals)}"
                    else:
                        format_val = f"{'、'.join(missing_vals)}"
                format_dict[key] = format_val or condition["default"]
        for item in template["items"]:
            match_templates.extend(self.get_split_templates(item, paragraphs))
        return self.format_templates_by_match_result(match_templates, format_dict)

    def extract_template_by_recombination(self, template, paragraphs: list[dict]):
        # 多段重组
        format_templates = []
        for _, _, template_items in self.combined_templates(template, paragraphs):
            format_templates.extend(template_items)

        return format_templates

    def extract_template_by_chapter_recombination(self, template, paragraphs: list[dict]):
        format_templates = []
        if len(template["patterns"]) != len(template["items"]) != len(template["child_items"]):
            logging.error("Template rules are incorrectly configured，Check template items length")
            logging.error(template)
            return []
        child_items = template["child_items"]
        for idx, para_index, template_items in self.combined_templates(template, paragraphs):
            # 仅过滤了当前位置之前的段落，后面可能也存在干扰段落，后续根据具体文档再进行处理
            filter_paras = [para for para in paragraphs if para["index"] > para_index]
            child_templates = self.get_split_templates(child_items[idx], filter_paras)
            template_items.extend(child_templates)
            format_templates.extend(template_items)

        return format_templates

    def combined_templates(self, template, paragraphs: list[dict]):
        # 重新组合模板顺序
        if len(template["patterns"]) != len(template["items"]):
            logging.error("Template rules are incorrectly configured，Check template patterns or items")
            logging.error(template)
            return []
        items = []
        un_match_items = []
        for idx, pattern in enumerate(template["patterns"]):
            for para in paragraphs:
                if not is_paragraph_elt(para):
                    continue
                if not (res := pattern.nexts(clean_txt(para["text"]))):
                    continue
                items.append((idx, res.start(), para))
                break
            else:
                un_match_items.append((idx, 0, {}))
        mapping = defaultdict(list)
        match_items = []
        for idx, start, para in items:
            mapping[para["index"]].append((idx, start, para))
        for _, values in sorted(mapping.items(), key=lambda x: x[0]):
            values = sorted(values, key=lambda x: x[1])
            match_items.extend(values)

        format_templates = []
        serial_num_pattern = template.get("serial_num_pattern")
        default_prefix_type = template.get("default_prefix_type")
        indexes = set()
        prev_prefix = ""
        template_items = template["items"]
        for idx, _, para in match_items + un_match_items:
            item = template_items[idx]
            paras = [para] if para else []
            para_index = para["index"] if para else -1
            match_templates = self.get_split_templates(item, paras)
            if not serial_num_pattern or not paras:
                prefix = ""
                # 根据匹配位置还原序号，差异较大的项目序号会存在比较乱的场景
                if serial_num_pattern and default_prefix_type:
                    prev_prefix = str(NumberUtil.cn_number_2_digit(prev_prefix) + 1)
                    prefix = default_prefix_type.format(num=f"{prev_prefix} ")
                format_templates.append((idx, para_index, self.format_recombination_templates(prefix, match_templates)))
                continue
            serial_num = ""
            if res := serial_num_pattern.nexts(clean_txt(para["text"])):
                if para["index"] not in indexes:
                    serial_num = res.group("prefix")
                else:
                    indexes.add(para["index"])
                prev_prefix = res.group("num")
            format_templates.append((idx, para_index, self.format_recombination_templates(serial_num, match_templates)))

        return format_templates

    @staticmethod
    def format_recombination_templates(prefix, match_templates):
        format_templates = []
        for template in match_templates:
            if template and isinstance(template, str):
                template = f"{prefix}{template}"
            elif isinstance(template, list):
                template = [f"{prefix}{sub_template}" for sub_template in template if sub_template]
            if template:
                format_templates.append(template)
        return format_templates

    def extract_template_by_inner_refer(self, templates, paragraphs: list[dict]):
        # 段内引用
        format_dict = {}
        for key, condition in templates["rules"].items():
            paras = paragraphs
            if condition.get("refer_chapters"):
                _, paras = self.reader.find_paragraphs_by_chapters(
                    condition["refer_chapters"]["chapters"], is_continued_chapter=False
                )
            refer_num = set()
            multi_select = bool(condition.get("multiple"))
            for pattern in condition["patterns"]:
                for para in paras:
                    if not is_paragraph_elt(para):
                        continue
                    content = clean_txt(para["text"])
                    if not pattern.nexts(content):
                        continue
                    if res := self.P_SERIAL_NUM.nexts(content):
                        refer_num.add(res.groupdict()["num"])
                    if not multi_select:
                        break
            # 引用数字连续递增，则拆为两种，1、2、3或1-3
            format_dict[key] = self.recombination_refer_num(refer_num) or condition["default"]

        match_templates = []
        for item in templates["items"]:
            match_templates.extend(self.get_split_templates(item, paragraphs))

        return self.format_templates_by_match_result(match_templates, format_dict)

    def extract_template_by_single_select(self, templates, paragraphs: list[dict]):
        format_dict = {}
        for key, condition in templates["rules"].items():
            format_dict[key] = condition["default"]
            is_match = False
            for para in paragraphs:
                if not is_paragraph_elt(para):
                    continue
                if not (res := condition["para_pattern"].nexts(clean_txt(para["text"]))):
                    continue
                for check_pattern in condition["patterns"]:
                    if isinstance(check_pattern, dict) and (
                        not check_pattern.get("conditions")
                        or self.manager.verify_condition(check_pattern["conditions"])
                    ):
                        if check_pattern["pattern"].nexts(res.groupdict()["content"]):
                            is_match = True
                            format_dict[key] = check_pattern["content"]
                            break
                if is_match:
                    break

        match_templates = []
        for item in templates["items"]:
            match_templates.extend(self.get_split_templates(item, paragraphs))

        return self.format_templates_by_match_result(match_templates, format_dict)

    @classmethod
    def recombination_refer_num(cls, refer_nums: set):
        refer_nums = sorted([str(NumberUtil.cn_number_2_digit(val)) for val in refer_nums], key=int)
        if NumberUtil.is_increment(refer_nums):
            return [f"{min(refer_nums, key=int)}-{max(refer_nums, key=int)}", "、".join(refer_nums)]
        return "、".join(refer_nums)

    @classmethod
    def generate_format_items(cls, template_item: str, match_result: dict):
        format_dicts = cls.recombination_format_dict(template_item, match_result)
        if format_dicts:
            return [template_item.format(**_dict) for _dict in format_dicts]
        return [template_item]

    @classmethod
    def format_templates_by_match_result(cls, template_items, match_result: dict):
        format_templates = []
        for item in template_items:
            if isinstance(item, list) and all(isinstance(sub_item, str) for sub_item in item):
                sub_templates = []
                for sub_item in item:
                    sub_templates.extend(cls.generate_format_items(sub_item, match_result))
                if sub_templates:
                    format_templates.append(sub_templates)
            elif isinstance(item, str):
                sub_templates = cls.generate_format_items(item, match_result)
                format_templates.append(sub_templates)
        return format_templates

    @classmethod
    def recombination_format_dict(cls, template: str, match_result: dict):
        """
        example:
            input: {key1: '1', key2: [1,2]}
            output: [
                {key1: '1', key2: '1'},
                {key1: '1', key2: '2'},
            ]
        """
        template_dict = {}
        for match in cls.P_REPLACE_KEY.finditer(template):
            key = match.groupdict()["key"]
            template_dict[key] = match_result.get(key, "{" + key + "}")

        format_dicts = []
        if not template_dict:
            return template_dict
        for key, val in template_dict.items():
            if isinstance(val, str):
                if not format_dicts:
                    format_dicts = [{key: val}]
                    continue
                for item in format_dicts:
                    item[key] = val
            elif isinstance(val, list):
                if not format_dicts:
                    format_dicts = [{key: child_val} for child_val in val]
                    continue
                format_dicts = format_dicts * len(val)
                for child_val in val:
                    for item in format_dicts:
                        item[key] = child_val
        return format_dicts

    def match_template(self, template, paragraphs=None, required=False, similarity_patterns=None):
        if not paragraphs and template.get("chapter"):
            is_continued_chapter = template["chapter"].get("is_continued_chapter", True)
            _, paragraphs = self.reader.find_paragraphs_by_chapters(
                template["chapter"]["chapters"], is_continued_chapter=is_continued_chapter
            )
        items = template["items"]
        match_templates = self.split_templates_by_conditions(items, paragraphs=paragraphs)
        match_templates = self.recombined_template(match_templates)
        return self.generate_reason_by_template(
            template,
            match_templates,
            paragraphs,
            required=required,
            similarity_patterns=similarity_patterns,
        )

    def match_template_multi_paragraphs(self, template, paragraphs=None, required=False, similarity_patterns=None):
        if not paragraphs and template.get("chapter"):
            is_continued_chapter = template["chapter"].get("is_continued_chapter", True)
            _, paragraphs = self.reader.find_paragraphs_by_chapters(
                template["chapter"]["chapters"], is_continued_chapter=is_continued_chapter
            )
        match_templates = []
        default_items = template.get("default_items", [])
        for item in template["items"]:
            if default_items:
                item["items"] = default_items + item["items"]
            templates = self.split_templates_by_conditions([item], paragraphs=paragraphs)
            templates = self.recombined_template(templates)
            match_templates.extend(templates)
        return self.generate_reason_by_template(
            template,
            match_templates,
            paragraphs,
            required=required,
            similarity_patterns=similarity_patterns,
        )

    def generate_reason_by_template(
        self, template, match_templates, paragraphs, required=False, similarity_patterns=None
    ):
        match_templates = [list(filter(None, item)) for item in match_templates]
        if not match_templates:
            return IgnoreConditionItem(reason_text=self.generate_unmatch_reason(template["items"]))
        return self.compare_paragraphs_with_template(
            template,
            match_templates,
            paragraphs,
            required=required,
            similarity_patterns=similarity_patterns,
            min_ratio=template.get("min_ratio", 0.6),
        )

    def compare_paragraphs_with_template(
        self, template, template_paragraphs, paragraphs, required=False, similarity_patterns=None, min_ratio=0.7
    ):
        # 多种表述的模板，任意一种表述为空，则非必须
        required &= all(template_paragraphs)
        # 从行开始，按列依次组合
        origin_content = "\n".join(template_paragraphs[0])
        name = template.get("name")
        content_title = template.get("content_title")
        ignore_extra_para = template.get("ignore_extra_para", self.IGNORE_EXTRA_PARA)
        split_sentence = template.get("split_sentence", True)
        source = template.get("source") or ""

        # 从全文里取数据
        if not paragraphs:
            _, paragraphs = self.get_paragraphs(template)
        if not paragraphs:
            if template.get("chapter"):
                return MissContentReasonItem(
                    reason_text=self.render_text(template["chapter"]["miss_detail"]["reason_text"]),
                    miss_content=template["chapter"]["miss_detail"].get("miss_content"),
                    template=Template(content=origin_content, name=name),
                    matched=not required,
                )
            return NoMatchReasonItem(template=Template(content=origin_content, name=name), matched=not required)

        # 数值检查
        reasons, template_paragraphs = self.check_content_value(template, paragraphs, template_paragraphs)
        if reasons and all(item for item in reasons):
            # 多个模板均不满足条件，默认返回第一条
            outlines = get_outlines(paragraphs)
            return MatchFailedItem(
                page=min(outlines, key=int, default=0),
                outlines=outlines,
                reason_text="；\n".join(set(reasons[0])),
            )

        group_similarity = defaultdict(list)
        current_similarities = []
        for current_templates in template_paragraphs:
            current_similarity = ParagraphSimilarity(
                current_templates,
                paragraphs,
                fill_paragraph=False,
                similarity_patterns=similarity_patterns,
                ratio=min_ratio,
                ignore_extra_para=ignore_extra_para,
                convert_types=self.CONVERT_TYPES,
                split_sentence=split_sentence,
            )
            if current_similarity.max_ratio > self.MIN_RATIO_THRESHOLD_VALUE:
                group_similarity[current_similarity.valid_sentences_count].append(current_similarity)
                current_similarities.append(current_similarity)

        similarity = None
        if group_similarity:
            # 1、取匹配到段落数最多，相似度最高的模版
            similarities = group_similarity[max(group_similarity)]
            similarity = max(similarities, key=lambda x: x.max_ratio)

            # 2、取相似度最高的模版
            similarities = list(itertools.chain.from_iterable(group_similarity.values()))
            similarity_temp = max(similarities, key=lambda x: x.max_ratio)

            # 3、如果相差大于阈值，且匹配到段落的最大比例小于0.8的时候，取相似度最高的模版
            if similarity_temp != similarity:
                if (
                    similarity_temp.max_ratio - similarity.max_ratio > self.DIFFERENCE_VALUE
                    and similarity.max_ratio < self.THRESHOLD_VALUE
                ):
                    similarity = similarity_temp

        # https://gitpd.paodingai.com/cheftin/docs_scriber/-/issues/1958
        if similarity:
            outlines = similarity.right_outlines
            if reasons and (reason := reasons[current_similarities.index(similarity)]):
                reason_text = "；\n".join(set(reason))
                outlines = get_outlines(paragraphs)
                return MatchFailedItem(
                    page=min(outlines, key=int, default=0),
                    outlines=outlines,
                    reason_text=reason_text,
                )
            if similarity.is_full_matched_or_contain or similarity.is_full_matched_without_extra_para:
                return MatchReasonItem(
                    template=Template(content=similarity.left_content, name=name, content_title=content_title),
                    content=similarity.right_content,
                    content_title="当前合同",
                    page=min(outlines, key=int, default=0),
                    outlines=outlines,
                    diff=similarity.simple_results,
                    source=source,
                )

            if similarity.is_matched:
                page = min(outlines.keys(), key=int, default=0)
                return ConflictReasonItem(
                    template=Template(content=similarity.left_content, name=name, content_title=content_title),
                    content=similarity.right_content,
                    page=page,
                    content_title="当前合同",
                    outlines=outlines,
                    diff=similarity.simple_results,
                    reason_text=self.render_text(template.get("diff_text")),
                    xpath=get_xpath_by_outlines(self.reader, outlines),
                    source=source,
                )
        for reason, template_content in zip(reasons, template_paragraphs):
            if not reason:
                origin_content = "\n".join(template_content)
                break
        return NoMatchReasonItem(template=Template(content=origin_content, name=name), matched=not required)

    def check_schema_fields(self, schema_fields):
        reasons = []
        for field in schema_fields:
            answer = self.manager.get(field)
            if not answer or not answer.value:
                reasons.append(SchemaFailedItem(reason_text=f"要素“{field}”为空", suggestion=f"请补充“{field}”"))
        return reasons

    def init_check_result(self, template):
        # 根据当前规则中所有conditions来获取所依赖的schema_field
        schema_fields = copy.copy(template.get("schema_fields")) or []
        schema_fields.extend(self.get_schema_fields_by_template(template))
        return ResultItem(
            name=template["name"],
            related_name=template["related_name"],
            is_compliance=False,
            reasons=[],
            schema_id=self.schema_id,
            fid=self.file.id,
            suggestion="",
            label=template["label"],
            origin_contents=self.get_origin_contents(template),
            schema_results=self.manager.build_schema_results(set(schema_fields)),
            tip=template.get("tip"),
            rule_type=template.get("rule_type", RuleType.TEMPLATE.value),
            contract_content=self.get_contract_content(template),
        )

    def verify_schema_fields(self, template):
        origin_schema_fields = template.get("schema_fields", [])
        schema_fields = self.filter_schema_fields(origin_schema_fields)
        template["schema_fields"] = schema_fields
        # schema_fields不满足条件，直接返回
        if not schema_fields and origin_schema_fields:
            conditions = []
            for item in origin_schema_fields:
                if isinstance(item, tuple):
                    conditions.extend(item[1])
            reasons = [IgnoreConditionItem(reason_text=self.generate_reason_by_template_conditions(conditions))]
            return self.after_match_template(template, reasons, False)
        return False, None

    def generate_result_by_templates(self, template, templates=None):
        valid_types = ["PARAGRAPH", "TABLE"]
        matched, reasons = self.verify_schema_fields(template)
        result = self.init_check_result(template)
        if reasons:
            result.reasons = reasons
            result.is_compliance = matched
            return result
        schema_fields = template["schema_fields"]
        answer_chapter, common_paragraphs = (
            get_paragraphs_by_schema_fields(self.reader, self.manager, schema_fields, valid_types=valid_types)
            if schema_fields
            else (None, None)
        )
        reasons = self.check_schema_fields(schema_fields)
        miss_content = False
        templates = templates or template["templates"]
        match_templates = []
        for template_item in templates:
            match_templates.extend(self.split_templates_by_conditions(template_item["items"]))

        if not match_templates:
            reasons = []
            for template_item in templates:
                reasons.append(IgnoreConditionItem(reason_text=self.generate_unmatch_reason(template_item["items"])))
        elif schema_fields and len(reasons) == len(schema_fields):
            # https://gitpd.paodingai.com/cheftin/docs_scriber/-/issues/2996#note_420591
            if not template.get("required_schema", True):
                for reason in reasons:
                    if isinstance(reason, SchemaFailedItem):
                        reason.matched = True
        else:
            templates_required = []
            templates_matched = []
            # 投资范围包含期货时，合同中“证券交易所”的表述，均调整为“证券、期货交易所”=“证券/期货交易所”=“证券交易所、期货交易所”
            answer = self.manager.get("基金投资范围")
            synonym_patterns = self.SYNONYM_PATTERNS
            if (
                answer
                and answer.value
                and "期货" in answer.value
                and P_STOCK_SIMILARITY_PATTERN not in synonym_patterns
            ):
                synonym_patterns.append(P_STOCK_SIMILARITY_PATTERN)
            for template_item in templates:
                required = template_item.get("required", True)
                if template_item.get("name") == TemplateName.LAW_NAME:
                    template_item["source"] = self.SOURCE
                templates_required.append(required)
                paragraphs = common_paragraphs
                # https://gitpd.paodingai.com/cheftin/docs_scriber/-/issues/2075
                if schem_reasons := self.check_schema_fields(
                    self.filter_schema_fields(template_item.get("rule_fields", []))
                ):
                    reasons.extend(schem_reasons)
                    continue
                # 规则条款内的schema_fields独立检查，全部没有答案不进行一致性检查
                child_schema_fields = template_item.get("schema_fields", [])
                if child_schema_fields:
                    child_reasons = self.check_schema_fields(child_schema_fields)
                    reasons.extend(child_reasons)
                    if len(child_reasons) == len(child_schema_fields):
                        continue
                    # 根据当前答案，取合并
                    answer_chapter, paragraphs = get_paragraphs_by_schema_fields(
                        self.reader, self.manager, child_schema_fields, valid_types=valid_types
                    )

                if child_schema_fields or schema_fields:
                    if not paragraphs:
                        reasons.append(MatchFailedItem(reason_text="当前规则对应的要素答案未找到对应内容"))
                        continue
                    # 检查答案对应的章节与配置的是否一致, 仅作测试
                    # self.check_answer_chapter_with_config_chapter_for_test(template, template_item, answer_chapter, schema_fields+child_schema_fields)
                    template_item["chapter"] = None
                reason = self.match_template(
                    template_item, paragraphs=paragraphs, required=required, similarity_patterns=synonym_patterns
                )
                reasons.append(reason)
                templates_matched.append(reason.matched)
            # https://gitpd.paodingai.com/cheftin/docs_scriber/-/issues/1808
            # 任意一个匹配到则为False, 都未匹配到，则required如存在任意一个为True则为True
            miss_content = not (any(templates_matched)) and any(templates_required)
        matched, reasons = self.after_match_template(template, reasons, miss_content)
        result.reasons = reasons
        result.is_compliance = matched
        return result

    def check_answer_chapter_with_config_chapter_for_test(self, base_template, template, answer_chapter, schema_fields):
        is_continued_chapter = template["chapter"].get("is_continued_chapter", True)
        config_chapters, _ = self.reader.find_paragraphs_by_chapters(
            template["chapter"]["chapters"], is_continued_chapter=is_continued_chapter
        )
        if config_chapters and config_chapters[-1]["element"] != answer_chapter["element"]:
            # 获取当前到根章节
            config_chapters = self.reader.syllabus_reader.find_by_index(config_chapters[-1]["index"])
            answer_chapters = self.reader.syllabus_reader.find_by_index(answer_chapter["index"])
            print("====" * 20)
            print(base_template["label"].split("_")[-1], schema_fields)
            print("  ".join([item["title"] for item in answer_chapters]))
            print("  ".join([item["title"] for item in config_chapters]))

    @classmethod
    def get_schema_fields_by_template(cls, template) -> [str]:
        schema_fields = []
        conditions = []
        for child_template in template["templates"]:
            conditions.extend(cls.get_all_conditions_by_items(child_template["items"]))
        schema_name_dict = PublicFundClassifyName.answer_field_map()
        for condition in conditions:
            for relation in condition.values:
                if isinstance(relation, AllMatchRelation):
                    for child_relation in relation.values:
                        for name in schema_name_dict.get(child_relation.name or condition.name, []):
                            schema_fields.append(name)
                else:
                    for name in schema_name_dict.get(relation.name or condition.name, []):
                        schema_fields.append(name)

        return schema_fields

    @classmethod
    def get_all_conditions_by_items(cls, template_items):
        conditionals = []
        for item in template_items:
            if not isinstance(item, dict):
                continue
            # if child_optional := (item.get('single_optional') or item.get('multi_optional')):
            if child_optional := item.get("single_optional"):
                if child_conditionals := cls.get_all_conditions_by_items(child_optional):
                    conditionals.extend(child_conditionals)
            else:
                if item.get("conditions"):
                    conditionals.extend(item["conditions"])
                if child_conditionals := cls.get_all_conditions_by_items(item["items"]):
                    conditionals.extend(child_conditionals)
        return conditionals

    def check_content_value(self, template, paragraphs, template_paragraphs):
        content_condition: ContentValueRelation | None = template.get("content_condition", None)
        if not content_condition:
            return [], template_paragraphs
        extract_values = {}
        origin_ratio_values = {}
        refer_index = None
        for key, val in content_condition.patterns.items():
            extract_values[key] = None
            origin_ratio_values[key] = None
            if isinstance(val, dict):
                for rule in val["conditions"]:
                    if self.manager.verify_condition(rule["rules"]):
                        val = rule["value"]
                        break
                else:
                    val = val["default"]
            if not isinstance(val, PatternCollection):
                extract_values[key] = val
                continue
            match_values = {}
            for para in paragraphs:
                if not is_paragraph_elt(para):
                    continue
                clean_content = clean_txt(para["text"])
                match = val.nexts(clean_content)
                if not match:
                    continue
                match_values[para["index"]] = match
            if not match_values:
                continue
            match_value_keys = list(match_values.keys())
            match_values_len = len(match_value_keys)
            if match_values_len == 1 and not refer_index:
                refer_index = match_value_keys[0]
            elif match_values_len > 1 and refer_index:
                index = min(match_values, key=lambda x: abs(x - refer_index))
                extract_values[key] = match_values[index].group("val")
                origin_ratio_values[key] = {"index": index, "match": match_values[index]}
                continue
            index = match_value_keys[0]
            extract_values[key] = match_values[index].group("val")
            origin_ratio_values[key] = {"index": match_value_keys[0], "match": match_values[index]}

        reason_mapping = defaultdict(list)
        for condition in content_condition.conditions:
            condition_val = extract_values[condition.key]
            condition_reasons = []
            if not condition_val:
                extract_values[condition.key] = condition.key
                reason_mapping[condition.key].append(f"请补充{condition.name}")
                continue
            condition_val = self.fix_interval_percentage_unit(
                condition, condition.key, condition_val, origin_ratio_values
            )
            valid_keys = []
            if condition.valid_keys:
                for key, rules in condition.valid_keys.items():
                    if self.manager.verify_condition(rules):
                        valid_keys.append(key)
            for rule in condition.rules:
                # rules内多个规则为与关系，如需添加或，则配置在同一层dict内，以key区分
                error_rule = []
                for name, relation in rule.items():
                    if valid_keys and name not in valid_keys:
                        continue
                    value = self.fix_interval_percentage_unit(
                        condition, name, extract_values[name], origin_ratio_values
                    )
                    if condition.content_type == ContentValueTypeEnum.PERCENTAGE and str(value).isdigit():
                        value = f"{value}%"
                    if not ContentConditional.compare_value_with_relation(
                        condition_val, value, relation["relation"], content_type=condition.content_type
                    ):
                        error_rule.append((relation, value))
                if len(error_rule) == len(rule):
                    format_reason = []
                    for relation, val in error_rule:
                        if val is not None:
                            format_reason.append(f"{relation['relation'].values[1]}{relation['name'] or val}")
                        else:
                            condition_reasons.append(f"请补充{relation['name']}")
                    if format_reason:
                        condition_reasons.append(f"{condition.name}应{'或'.join(format_reason)}")
            if condition_reasons:
                reason_mapping[condition.key].append("且".join(condition_reasons))

        # 剔除模板中未出现的检查值
        for key, val in extract_values.items():
            if val is None:
                extract_values[key] = key

        reasons = []
        correct_templates = []
        # 根据已匹配的值更新模板，未匹配数据将key还原到模板中
        # 当前模板的子项不存在key或该key无错误信息，则保存，对应key如果在模板中则提示错误信息
        for child_templates in template_paragraphs:
            format_templates = [_template.format(**extract_values) for _template in child_templates]
            error_reasons = []
            for key, vals in reason_mapping.items():
                if any(key in para_content for para_content in child_templates):
                    error_reasons.extend(vals)
            reasons.append(error_reasons)
            correct_templates.append(format_templates)
        return reasons, correct_templates

    def fix_interval_percentage_unit(self, condition, key, value, extract_mapping):
        if condition.content_type != ContentValueTypeEnum.PERCENTAGE:
            return value
        if key not in extract_mapping or not extract_mapping[key]:
            return value
        if not P_PURE_PERCENTAGE_WITHOUT_UNIT.nexts(value):
            return value
        unit = "%"
        _, para = self.reader.find_element_by_index(extract_mapping[key]["index"])
        val_match = extract_mapping[key]["match"]
        for match in P_PERCENTAGE_UNIT.finditer(clean_txt(para["text"])):
            # 10-100%
            if 0 < match.start() - val_match.span("val")[-1] < 5:
                unit = match.group()
                break
        return f"{value}{unit}"

    @classmethod
    def get_conditions_by_template_items(cls, template_items):
        conditionals = []
        for item in template_items:
            if not isinstance(item, dict):
                continue
            if item.get("conditions"):
                # https://gitpd.paodingai.com/cheftin/docs_scriber/-/issues/2222
                # 父级条件不满足，仅保留当前条件
                conditionals.append(item)
            # elif item.get('multi_optional'):
            #     for c_condition in item['multi_optional']:
            #         conditionals.append(c_condition)
            elif item.get("single_optional"):
                # 单选内的条件均为且，需要合在一起
                single_conditions = {"conditions": []}
                for c_condition in item["single_optional"]:
                    if not c_condition.get("conditions"):
                        continue
                    single_conditions["conditions"].extend(c_condition["conditions"])
                if single_conditions["conditions"]:
                    conditionals.append(single_conditions)
                continue

        return conditionals

    def generate_unmatch_reason(self, template_items):
        """
        template最外层items内存在多个条件，均未匹配到，生成默认reason
        多个conditional关系为或, 同一个condition内多个条件为且
        """
        conditionals = self.get_conditions_by_template_items(template_items)
        template_relations = []
        for condition in conditionals:
            if not condition.get("conditions"):
                continue
            template_relations.extend(condition["conditions"])

        return self.generate_reason_by_template_conditions(template_relations)

    def check(self):
        results = []
        templates = copy.deepcopy(self.get_templates())
        for template in templates:
            result = self.generate_result_by_templates(template)
            # 过滤相同原因的错误
            self.filter_result(result, template)
            results.append(result)

        return results


class BaseSentenceMultipleChecker(BaseConditionsChecker):
    # 单个段落多次比较
    TEMPLATES = []

    def generate_match_reason(self, template_item, results: list[DiffResult], paragraphs=None):
        page = None
        outlines = {}
        if results or paragraphs:
            outlines = self.get_outlines_by_diff_results([results], paragraphs=paragraphs)
            page = min(outlines.keys(), default=0)
        return MatchReasonItem(
            template=Template(
                content_title=template_item["content_title"],
                content=self.get_content_by_diff_results(results),
                name=template_item["name"],
            ),
            content=self.get_content_by_diff_results(results, is_left=False),
            page=page,
            content_title="当前合同",
            outlines=outlines,
            diff=self.mock_diff_html_by_diff_content(results),
            xpath=get_xpath_by_outlines(self.reader, outlines),
        )

    def generate_conflict_reason(self, template_item, results: list[DiffResult], paragraphs=None):
        page = None
        outlines = {}
        if results or paragraphs:
            outlines = self.get_outlines_by_diff_results([results], paragraphs=paragraphs)
            page = min(outlines.keys(), default=0)
        return ConflictReasonItem(
            template=Template(
                content_title=template_item["content_title"],
                content=self.get_content_by_diff_results(results),
                name=template_item["name"],
            ),
            content=self.get_content_by_diff_results(results, is_left=False),
            page=page,
            content_title="当前合同",
            outlines=outlines,
            diff=self.mock_diff_html_by_diff_content(results),
            reason_text=template_item.get("diff_text"),
            xpath=get_xpath_by_outlines(self.reader, outlines),
        )

    def compare_template(self, template):
        diff_list = []
        matched, reasons = self.verify_schema_fields(template)
        if reasons:
            return matched, reasons
        schema_fields = template["schema_fields"]
        _, paragraphs = (
            get_paragraphs_by_schema_fields(self.reader, self.manager, schema_fields) if schema_fields else (None, None)
        )

        for template_item in template["templates"]:
            reason_results = []
            _, paragraphs = (_, paragraphs) if schema_fields else self.get_paragraphs(template_item)
            if not paragraphs and template.get("chapter"):
                reason_results.append(
                    MissContentReasonItem(
                        reason_text=self.render_text(template["chapter"]["miss_detail"]["reason_text"]),
                        miss_content=template["chapter"]["miss_detail"].get("miss_content"),
                        matched=False,
                    )
                )
                continue
            match_templates = self.split_templates_by_conditions(template_item["items"], paragraphs=paragraphs)
            match_templates = self.recombined_template(match_templates)
            template_content = ""
            results = []
            if not match_templates:
                reason_results.append(
                    IgnoreConditionItem(reason_text=self.generate_unmatch_reason(template_item["items"]))
                )
            else:
                # 数值检查
                error_reasons, match_templates = self.check_content_value(template_item, paragraphs, match_templates)
                if any(len(match_items) > 1 for match_items in match_templates):
                    logging.error("Sentence Multiple Compare Template rules are incorrectly configured")
                    logging.error(template)
                    return []
                if error_reasons and all(reasons for reasons in error_reasons):
                    # 多个模板均不满足条件，默认返回第一条
                    # https://gitpd.paodingai.com/cheftin/docs_scriber/-/issues/2376
                    outlines = get_outlines(paragraphs)
                    reason_results.append(
                        MatchFailedItem(
                            page=min(outlines, key=int, default=0),
                            outlines=outlines,
                            reason_text="；\n".join(set(error_reasons[0])),
                        )
                    )
                else:
                    all_results = defaultdict(list)
                    template_content = match_templates[0][0]
                    for items, reasons in zip_longest(match_templates, error_reasons, fillvalue=[]):
                        current_results = ParagraphSimilarity.search_split_sentences(
                            items, paragraphs, min_ratio=template_item.get("min_ratio", 0.7)
                        )
                        for para_index, current_result in current_results:
                            all_results[para_index].append(
                                (
                                    current_result,
                                    reasons,
                                    ParagraphSimilarity.calc_weighted_average_ratio([current_result]),
                                )
                            )
                    if all_results:
                        for single_results in all_results.values():
                            single_result, reasons, _ = sorted(single_results, key=lambda x: x[-1])[-1]
                            if reasons:
                                outlines = self.get_outlines_by_diff_results(single_result, paragraphs)
                                reason_results.append(
                                    MatchFailedItem(
                                        page=min(outlines, key=int, default=0),
                                        outlines=outlines,
                                        reason_text="；\n".join(set(reasons)),
                                    )
                                )
                            else:
                                results.append(single_result)
            diff_list.append((template_item, template_content, results, reason_results))
        return self.generate_template_compare_reason(diff_list)

    def get_outlines_by_diff_results(self, group_results: list[list[DiffResult]], paragraphs=None):
        outline_mapping = defaultdict(list)
        if paragraphs:
            # https://gitpd.paodingai.com/cheftin/docs_scriber/-/issues/2466#note_351239
            outline_mapping = self.calc_outlines_by_paragraphs(paragraphs)
        elif group_results:
            for diff_results in group_results:
                for result in diff_results:
                    if result and result.right:
                        for key, boxes in get_outlines([result.right.origin]).items():
                            outline_mapping[key].extend(boxes)

        return outline_mapping

    def generate_template_compare_reason(self, diff_list: list[tuple[dict, str, list[list[DiffResult]] | None, list]]):
        reasons = []
        for template_item, template_content, group_results, reason_results in diff_list:
            if not group_results and reason_results:
                reasons.extend(reason_results)
                continue
            if not group_results:
                reasons.append(
                    NoMatchReasonItem(
                        template=Template(name=template_item["name"], content=template_content),
                        reason_text=f"未找到与{template_item['name']}匹配的内容",
                    )
                )
                continue

            if any(ParagraphSimilarity.judge_is_full_matched(results) for results in group_results):
                reasons = []
                for result in group_results:
                    reasons.append(self.generate_match_reason(template_item, result))
                return True, reasons

            for results in group_results:
                if ParagraphSimilarity.judge_is_full_matched(results):
                    reasons.append(self.generate_match_reason(template_item, results))
                elif ParagraphSimilarity.judge_is_matched(results):
                    reasons.append(self.generate_conflict_reason(template_item, results))

        return False, reasons

    @staticmethod
    def get_content_by_diff_results(results: list[DiffResult], is_left=True):
        if is_left:
            return "".join([item.left_content for item in results])
        return "".join([item.right_content for item in results])

    def check(self):
        results = []
        for template in self.get_templates():
            matched, reasons = self.compare_template(template)
            results.append(
                ResultItem(
                    name=template["name"],
                    related_name=template["related_name"],
                    is_compliance=matched,
                    reasons=reasons,
                    fid=self.file.id,
                    origin_contents=self.get_origin_contents(template),
                    schema_id=self.schema_id,
                    suggestion=self.generate_suggestion_by_reasons(template, reasons),
                    label=template["label"],
                    schema_results=self.manager.build_schema_results(template.get("schema_fields") or []),
                    tip=template.get("tip"),
                    contract_content=self.get_contract_content(template),
                )
            )
        return results
