from collections import defaultdict
from typing import Pattern

from remarkable.pdfinsight.reader import PdfinsightReader
from remarkable.plugins.cgs.common.fund_classification import (
    AssetClassifyName,
    DisclosureEnum,
    FundTypeEnum,
    PublicFundClassifyName,
    RelationEnum,
)
from remarkable.plugins.cgs.common.template_condition import AllMatchRelation, TemplateRelation
from remarkable.plugins.cgs.common.utils import get_outlines
from remarkable.plugins.cgs.schemas.reasons import IgnoreConditionItem, MissContentReasonItem


class BaseChecker:
    def __init__(self, reader, file, manager, schema_id=None, labels=None, answer_reader=None, **kwargs):
        self.reader = reader
        self.file = file
        self.schema_id = schema_id
        self.manager = manager
        self.labels = labels or {}
        self.answer_reader = answer_reader

    def check(self):
        raise NotImplementedError

    @classmethod
    def extract_paragraphs_by_matcher(cls, reader: PdfinsightReader, chapter_regexps: list[Pattern]):
        paragraphs = []
        for chapter in reader.find_sylls_by_pattern(chapter_regexps):
            paragraphs.extend([reader.find_element_by_index(idx)[-1] for idx in range(*chapter["range"])])
        return paragraphs

    @staticmethod
    def filter_same_reason(reasons):
        # 过滤相同原因的错误
        # https://gitpd.paodingai.com/cheftin/docs_scriber/-/issues/1613
        # 仅过滤IgnoreConditionItem和MissContentReasonItem
        filter_reasons = []
        reason_dict = defaultdict(list)
        for idx, reason in enumerate(reasons):
            if isinstance(reason, (IgnoreConditionItem, MissContentReasonItem)):
                reason_dict[reason.reason_text].append((idx, reason))
            else:
                filter_reasons.append((idx, reason))
        for vals in reason_dict.values():
            filter_reasons.append(vals[0])
        return [reason for _, reason in sorted(filter_reasons, key=lambda x: x[0])]

    def filter_schema_fields(self, schema_fields):
        temp_list = []
        for schema_field in schema_fields:
            if isinstance(schema_field, tuple):
                if self.manager.verify_condition(schema_field[1]):
                    temp_list.append(schema_field[0])
            else:
                temp_list.append(schema_field)
        return temp_list

    def generate_reason_by_template_conditions(self, template_relations: list[TemplateRelation]):
        reasons = set()
        conditions = []

        for item in template_relations:
            if self.manager.verify_condition([item]):
                continue
            for val_condition in item.values:
                if isinstance(val_condition, AllMatchRelation):
                    val_conditions = val_condition.values
                else:
                    val_conditions = [val_condition]
                for relation in val_conditions:
                    relation.name = relation.name or item.name
                    # 投资范围可能存在多个条件，均不满足，全部提示
                    if relation in conditions:
                        continue
                    conditions.append(relation)

        condition_dicts = defaultdict(set)
        for condition in conditions:
            values = self.manager.classification_mapping.get(condition.name)
            if not values:
                # 交易所类型，先判断是否为上市交易，否则提示为非上市，是则提示无法判断
                if condition.name == PublicFundClassifyName.STOCK_BOURSE:
                    values = self.manager.classification_mapping.get(PublicFundClassifyName.LISTED_TRANSACTION)
                    if values[0] == DisclosureEnum.NO:
                        reasons.add(f"该基金不是{PublicFundClassifyName.LISTED_TRANSACTION}")
                        continue
                if condition.name == PublicFundClassifyName.SHARE_CATEGORY:
                    values = self.manager.classification_mapping.get(PublicFundClassifyName.SHARE_CLASSIFY)
                    if values[0] == DisclosureEnum.NO:
                        reasons.add(f"该基金未披露{PublicFundClassifyName.SHARE_CLASSIFY}")
                        continue
                # https://gitpd.paodingai.com/cheftin/docs_scriber/-/issues/2217
                # https://gitpd.paodingai.com/cheftin/docs_scriber/-/issues/2248#note_336301
                reasons.add("当前基金不满足规则中的预设条件")
                continue
            if condition.name == PublicFundClassifyName.FUND_TYPE:
                # 基金类型中指数增强型、股票指数型、债券指数型可能同时存在且包含指数型或股票型或债券型，过滤重复类型及包含的类型数据
                values = self.filter_similar_types(values[:])
            prefix = "为"
            contents = [condition.name] if isinstance(condition.value, DisclosureEnum) else [x.value for x in values]
            # 侧袋机制、份额分类、份额类别需要调整为有无披露
            if condition.name in (
                PublicFundClassifyName.SIDE_POCKET,
                PublicFundClassifyName.SHARE_CLASSIFY,
                PublicFundClassifyName.SHARE_CATEGORY,
                AssetClassifyName.INVESTMENT_ADVISER,
                AssetClassifyName.PROJECT_GENERAL_MEETING,
            ):
                prefix = "未披露" if not values or any(val == DisclosureEnum.NO for val in values) else "披露了"
            elif condition.name in (
                PublicFundClassifyName.LISTED_TRANSACTION,
                AssetClassifyName.NON_STANDARD_INVESTMENT,
            ):
                prefix = "不是" if not values or any(val == DisclosureEnum.NO for val in values) else "是"
            elif condition.name == PublicFundClassifyName.INVESTMENT_SCOPE:
                contents = [condition.value.value]
                prefix = (
                    f"{PublicFundClassifyName.INVESTMENT_SCOPE}"
                    f"{'不包含' if condition.relation == RelationEnum.EQUAL else '包含'}"
                )
            condition_dicts[prefix].add("、".join(contents))
        for prefix, contents in condition_dicts.items():
            reasons.add(f"该基金{prefix.lstrip('基金')}{'、'.join(contents)}")
        return "；".join(reasons)

    @staticmethod
    def filter_similar_types(values: list):
        if FundTypeEnum.STOCK_INDEX in values:
            values.remove(FundTypeEnum.INDEX)
        if FundTypeEnum.BOND_INDEX in values:
            values.remove(FundTypeEnum.BOND)
            if FundTypeEnum.INDEX in values:
                values.remove(FundTypeEnum.INDEX)
        if FundTypeEnum.STOCK_INDEX in values:
            values.remove(FundTypeEnum.STOCK)
            if FundTypeEnum.INDEX in values:
                values.remove(FundTypeEnum.INDEX)
        return values

    def calc_outlines_by_paragraphs(self, paragraphs):
        if not paragraphs:
            return {}
        paragraphs = sorted(paragraphs, key=lambda x: x["index"])
        min_index, max_index = paragraphs[0]["index"], paragraphs[-1]["index"]
        all_paragraphs = []
        for index in range(min_index, max_index + 1):
            _, para = self.reader.find_element_by_index(index)
            if para:
                all_paragraphs.append(para)

        return get_outlines(all_paragraphs)
