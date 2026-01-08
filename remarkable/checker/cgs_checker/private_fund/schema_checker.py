import difflib
import json
import re
from collections import defaultdict
from copy import deepcopy
from decimal import Decimal
from functools import cached_property

from remarkable.checker.answers import Answer
from remarkable.checker.cgs_checker.base_schema_checker import BaseSchemaChecker
from remarkable.checker.checkers.conditions_checker import BaseConditionsChecker
from remarkable.common.constants import RuleType
from remarkable.common.pattern import PatternCollection
from remarkable.common.util import clean_txt
from remarkable.plugins.cgs.common.template_condition import TemplateName
from remarkable.plugins.cgs.common.utils import (
    append_suggestion,
    check_contain_content,
    get_outlines,
    is_matched_fund_manager_types,
    render_suggestion,
    replace_synonym,
)
from remarkable.plugins.cgs.globals import SYNONYM_WORDS
from remarkable.plugins.cgs.rules.blacklist import BLACK_WORDS
from remarkable.plugins.cgs.schemas.reasons import (
    IgnoreConditionItem,
    MatchFailedItem,
    MatchSuccessItem,
    ResultItem,
    SchemaFailedItem,
)

P_OPEN_DAY_DATE = PatternCollection(
    [
        r"[0-9一二三四五六七八九十〇]+年[0-9一二三四五六七八九十〇]+月[0-9一二三四五六七八九十〇]+日",
        r"每个.*?日.*?开放日",
        r"开放日.*?每个.*?日",
        r"开放日.*?第.*?个周",
        r"第.*?个周.*?开放日",
        r"开放日.*?每满.*?个自然日",
        r"每满.*?个自然日.*?开放日",
        r"开放日.*?每届满.*?个自然日",
        r"每届满.*?个自然日.*?开放日",
        r"开放日.*?每满.*?个月的月度对日",
        r"每满.*?个月的月度对日.*?开放日",
        r"开放日.*?每届满.*?个月的月度对日",
        r"每届满.*?个月的月度对日.*?开放日",
        r"每.*?日.*?开放日",
        r"开放日.*?每月计划成立日对日",
        r"每月计划成立日对日.*?开放日",
        r"开放日.*?每自然月.*?日",
        r"每自然月.*?日.*?开放日",
        r"开放日.*?每自然年.*?日",
        r"每自然年.*?日.*?开放日",
        r"每周.*?开放日",
        r"开放日.*?每周",
        # https://gitpd.paodingai.com/cheftin/docs_scriber/-/issues/959#note_237127
        r"每个(?:(?:交易日|工作日)[、/或]?){1,2}开放",
    ]
)

P_CLOSE_MODE = PatternCollection([r"^无|封闭式|不设置开放"])


class PrivateFundSchemaChecker(BaseSchemaChecker):
    SCHEMA_NAME = "私募-基金合同"
    NAME = ""
    RULE_TYPE = RuleType.SCHEMA.value
    LABEL = ""

    def check(self):
        raise NotImplementedError

    @classmethod
    def get_valid_subclasses(cls, schema_names: set[str]):
        if cls.SCHEMA_NAME in schema_names:
            return cls.__subclasses__()
        return []

    def init_result(self):
        return ResultItem(
            name=self.NAME,
            related_name=self.RELATED_NAME,
            is_compliance=True,
            reasons=[],
            suggestion=None,
            schema_id=self.schema_id,
            fid=self.file.id,
            schema_results=self.manager.build_schema_results(self.SCHEMA_FIELDS),
            label=self.LABEL,
            rule_type=self.RULE_TYPE,
            origin_contents=self.get_origin_contents(),
            contract_content=self.get_contract_content(),
        )

    @cached_property
    def result(self):
        return self.init_result()


class OpenDayChecker(PrivateFundSchemaChecker):
    RELATED_NAME = "运作方式、开放日"
    SCHEMA_FIELDS = ["开放日", "运作方式"]
    LABEL = "schema_32_1"
    NAME = "开放式基金可申购或赎回"
    FROM = "20150424 中华人民共和国证券投资基金法（主席令第23号  2015年4月24日修订）"
    ORIGIN = "采用开放式运作方式的基金（以下简称开放式基金），是指基金份额总额不固定，基金份额可以在基金合同约定的时间和场所申购或者赎回的基金。"

    def check(self):
        operation_mode = self.manager.get("运作方式")
        reasons = []
        matched = True
        suggestion = None
        if not operation_mode.value:
            reasons.append(MatchFailedItem(reason_text="运作方式为空"))
            matched = False
            suggestion = "请补充“运作方式”"
        elif "开放式" in operation_mode.value:
            open_day = self.manager.get("开放日")
            if not open_day.data_text or not P_OPEN_DAY_DATE.nexts(open_day.data_text):
                reasons.append(MatchFailedItem(reason_text="开放日未包含具体的开放日期"))
                matched = False
                title = open_day.chapter_title or ""
                suggestion = f"合同，{title}{self.RELATED_NAME}，请将“{open_day.data_text}”修改为具体的开放日期"
        elif "封闭式" in operation_mode.value:
            open_day = self.manager.get("开放日")
            if not (not open_day.data_text or P_CLOSE_MODE.nexts(open_day.data_text)):
                reasons.append(MatchFailedItem(reason_text="开放日未包含“无”或“封闭式”或“不设置开放”"))
                matched = False
                title = open_day.chapter_title or ""
                suggestion = (
                    f"合同，{title}{self.RELATED_NAME}，请将“{open_day.data_text}”修改为“无”或“封闭式”或“不设置开放”"
                )
        else:
            reasons.append(IgnoreConditionItem(reason_text="运作方式不是开放式或封闭式"))

        return ResultItem(
            name=self.NAME,
            related_name=self.RELATED_NAME,
            is_compliance=matched,
            reasons=reasons,
            suggestion=suggestion,
            schema_id=self.schema_id,
            fid=self.file.id,
            schema_results=self.manager.build_schema_results(self.SCHEMA_FIELDS),
            label=self.LABEL,
            origin_contents=self.get_origin_contents(),
        )


class OperationModeChecker(PrivateFundSchemaChecker):
    RELATED_NAME = "运作方式、开放日"
    SCHEMA_FIELDS = ["开放日", "运作方式"]
    LABEL = "schema_32_2"
    NAME = "开放日约定应符合运作方式"
    FROM = "20150424 中华人民共和国证券投资基金法（主席令第23号  2015年4月24日修订）"
    ORIGIN = "采用开放式运作方式的基金（以下简称开放式基金），是指基金份额总额不固定，基金份额可以在基金合同约定的时间和场所申购或者赎回的基金。"

    def check(self):
        operation_mode = self.manager.get("运作方式")
        open_day = self.manager.get("开放日")

        reasons = []
        matched = True
        suggestion = None
        matched_date = P_OPEN_DAY_DATE.nexts(open_day.data_text or "")
        if not open_day.data_text or P_CLOSE_MODE.nexts(open_day.data_text):
            if not operation_mode.value or "封闭式" not in operation_mode.value:
                value = open_day.data_text or "空"
                title = operation_mode.chapter_title
                suggestion = f"合同，{title}{self.RELATED_NAME}，请将“{operation_mode.value}”修改为封闭式"
                matched = False
                reasons.append(MatchFailedItem(reason_text=f"开放日为{value}，但运作方式不是封闭式"))
        elif matched_date:
            if not operation_mode.value or "开放式" not in operation_mode.value:
                reasons.append(MatchFailedItem(reason_text=f"开放日为{matched_date.group(0)}，但运作方式不是开放式"))
                matched = False
                title = operation_mode.chapter_title
                suggestion = f"合同，{title}{self.RELATED_NAME}，请将“{operation_mode.value}”修改为开放式"
        else:
            reasons.append(IgnoreConditionItem(reason_text="开放日无具体日期且不为“无”或“封闭式”或“不设置开放”"))
            matched = None

        return ResultItem(
            name=self.NAME,
            related_name=self.RELATED_NAME,
            is_compliance=matched,
            suggestion=suggestion,
            reasons=reasons,
            schema_id=self.schema_id,
            fid=self.file.id,
            schema_results=self.manager.build_schema_results(self.SCHEMA_FIELDS),
            label=self.LABEL,
            origin_contents=self.get_origin_contents(),
        )


class RiskLevelChecker(PrivateFundSchemaChecker):
    RELATED_NAME = "基金的风险等级、投资者风险承受能力等级"
    P_C_LEVEL = re.compile(r"C(\d+)")
    P_R_LEVEL = re.compile(r"R(\d+)")

    LEVEL_MAPPING = {
        "1": {"1", "2", "3", "4", "5"},
        "2": {"2", "3", "4", "5"},
        "3": {"3", "4", "5"},
        "4": {"4", "5"},
        "5": {
            "5",
        },
    }  # R_LEVEL: {C_LEVEL1, C_LEVEL2, ...}
    SCHEMA_FIELDS = ["本基金的风险等级", "适合的投资者风险承受能力等级"]
    LABEL = "schema_505"
    NAME = "基金风险等级和投资者风险承受能力等级应符合适当性匹配原则"
    FROM = "20170701 基金募集机构投资者适当性管理实施指引（试行)（基金业协会）"
    ORIGIN = (
        "基金募集机构要根据普通投资者风险承受能力和基金产品或者服务的风险等级建立以下适当性匹配原则：\n"
        "(一）C1型（含最低风险承受能力类别）普通投资者可以购买R1级基金产品或者服务；\n"
        "(二）C2型普通投资者可以购买R2级及以下风险等级的基金产品或者服务；\n"
        "(三）C3型普通投资者可以购买R3级及以下风险等级的基金产品或者服务；\n"
        "(四）C4型普通投资者可以购买R4级及以下风险等级的基金产品或者服务；\n"
        "(五）C5型普通投资者可以购买所有风险等级的基金产品或者服务。"
    )

    def check(self):
        level = self.manager.get("本基金的风险等级")
        matched_level = self.manager.get("适合的投资者风险承受能力等级")

        reasons = []
        matched = True
        suggestion = None
        if level.value and matched_level.value:
            r_level = self.P_R_LEVEL.search(level.value)
            c_level = self.P_C_LEVEL.findall(matched_level.value)
            if r_level:
                levels = self.LEVEL_MAPPING.get(r_level.group(1))
                for _level in c_level:
                    if _level not in levels:
                        reasons.append(
                            MatchFailedItem(reason_text="普通投资者风险承受能力和基金产品或者服务的风险等级不匹配")
                        )
                        matched = False
                        min_level = min(levels)
                        suggestion = f"根据基金风险等级，请修改普通投资者风险承受能力等级为C{min_level}"
                        if len(levels) > 1:
                            suggestion += "及以上"
                        break

        return ResultItem(
            name=self.NAME,
            related_name=self.RELATED_NAME,
            is_compliance=matched,
            reasons=reasons,
            suggestion=suggestion,
            schema_id=self.schema_id,
            fid=self.file.id,
            schema_results=self.manager.build_schema_results(self.SCHEMA_FIELDS),
            label=self.LABEL,
            origin_contents=self.get_origin_contents(),
        )


class SingleManagerChecker(PrivateFundSchemaChecker):
    RELATED_NAME = "管理人的义务"
    SCHEMA_FIELDS = ["基金管理人概况-名称"]
    LABEL = "schema_439_2"
    NAME = "管理人不得超过一家"
    FROM = "20191223 私募投资基金备案须知（基金业协会）"
    ORIGIN = "私募投资基金的管理人不得超过一家。"

    def check(self):
        reasons = []
        matched = True
        suggestion = None

        manager_details_len = len(self.manager.get_multi("基金管理人概况-名称"))
        if not manager_details_len:
            reasons.append(MatchFailedItem(reason_text="无管理人"))
            matched = False
            suggestion = f"{self.RELATED_NAME}、请补充基金管理人"
        elif manager_details_len > 1:
            reasons.append(MatchFailedItem(reason_text=f"管理人存在{manager_details_len}家"))
            matched = False
            suggestion = "根据法律法规规定，私募投资基金的管理人不得超过一家；请修改"

        return ResultItem(
            name=self.NAME,
            related_name=self.RELATED_NAME,
            is_compliance=matched,
            reasons=reasons,
            schema_id=self.schema_id,
            fid=self.file.id,
            schema_results=self.manager.build_schema_results(self.SCHEMA_FIELDS),
            suggestion=suggestion,
            label=self.LABEL,
            origin_contents=self.get_origin_contents(),
        )


class DurationChecker(PrivateFundSchemaChecker):
    RELATED_NAME = "存续期、基金名称"

    P_YEAR = re.compile(r"^\d+(\.\d+)?年$")
    P_FUND_NAME = re.compile(r".*(股权投资|资产配置).*")
    SCHEMA_FIELDS = ["存续期", "基金管理人概况-名称", "基金管理人-名称"]
    LABEL = "schema_454"
    NAME = "合同应约定明确的存续期"
    FROM = "20191223 私募投资基金备案须知（基金业协会）"
    ORIGIN = "私募投资基金应当约定明确的存续期。私募股权投资基金和私募资产配置基金约定的存续期不得少于5年,鼓励管理人设立存续期在7年及以上的私募股权投资基金。"

    def check(self):
        reasons = []
        matched = True
        suggestion = None

        duration = self.manager.get("存续期")
        if not duration or not duration.value:
            reasons.append(MatchFailedItem(reason_text="存续期为空"))
            matched = False
            suggestion = "请在基金基本情况表中补充存续期"
        else:
            if not self.P_YEAR.match(clean_txt(duration.value)):
                reasons.append(MatchFailedItem(reason_text="存续期非具体年份"))
                matched = False
                suggestion = f"合同，{duration.chapter_title}存续期，请将“{duration.value}”修改为具体年份"
            else:
                if self.fun_manager_type and is_matched_fund_manager_types(
                    ["私募股权、创业投资基金管理人", "私募资产配置类管理人"], self.fun_manager_type
                ):
                    if Decimal(clean_txt(duration.value)[:-1]) < 5:
                        reasons.append(MatchFailedItem(reason_text="存续期小于5年"))
                        matched = False
                        suggestion = "请将基金基本情况表中【存续期】修改为5年及5年以上"

        return ResultItem(
            name=self.NAME,
            related_name=self.RELATED_NAME,
            is_compliance=matched,
            reasons=reasons,
            schema_id=self.schema_id,
            fid=self.file.id,
            schema_results=self.manager.build_schema_results(self.SCHEMA_FIELDS),
            suggestion=suggestion,
            label=self.LABEL,
            origin_contents=self.get_origin_contents(),
        )


# class TempOpenDayChecker(PrivateFundSchemaChecker):
#     RELATED_NAME = "临时开放日"
#     P_TMP_OPEN_DAY = PatternCollection(r"当发生以下情况时.*可.*设置临时开放日")
#     P_OPERATE_CLOSE = PatternCollection(r"封闭式")
#     SCHEMA_FIELDS = ["临时开放日", "运作方式"]
#     LABEL = "schema_467_1"
#     NAME = "临时开放日需约定触发条件且只可赎回"
#     FROM = "20191223 私募投资基金备案须知（基金业协会）"
#     ORIGIN = [
#         "私募证券投资基金(含FOF)：基金合同中设置临时开放日的，应当明确临时开放日的触发条件，原则上不得利用临时开放日的安排继续认/申购（认缴）",
#         "《20230928 私募投资基金备案指引第1号——私募证券投资基金（中国基金业协会 2023年9月28日）》",
#         "第十一条 私募证券基金的基金合同应当明确约定封闭式、开放式等基金运作方式。开放式私募证券基金的基金合同应当设置固定开放日，明确投资者认（申）购、赎回时间、频率、程序以及限制事项。未按照基金合同约定征得投资者同意，私募基金管理人不得擅自更改投资者认（申）购、赎回时间、频率、程序以及限制事项。",
#         "私募证券基金设置临时开放日的，应当在基金合同中明确约定临时开放日的触发条件仅限于因法律、行政法规、监管政策调整、合同变更或解除等情形，不得利用临时开放日进行申购。私募基金管理人应当在临时开放日前2个交易日通知全体投资者。",
#     ]
#
#     def check(self):
#         reasons = []
#         matched = True
#         suggestion = None
#
#         tmp_open_day = self.manager.get("临时开放日")
#         operate_mode = self.manager.get("运作方式")
#         if self.P_OPERATE_CLOSE.nexts(operate_mode.value or ""):
#             reasons.append(IgnoreConditionItem(reason_text="运作方式类型为封闭式"))
#         else:
#             flag = True
#             if not tmp_open_day.value:
#                 flag = False
#             else:
#                 searched = self.P_TMP_OPEN_DAY.nexts(tmp_open_day.value)
#                 if not searched:
#                     flag = False
#
#             if not flag:
#                 reasons.append(MatchFailedItem(reason_text="未找到临时开放日的触发条件"))
#                 matched = False
#                 suggestion = "请在基金基本情况表中补充临时开放日的触发条件"
#
#         return ResultItem(
#             name=self.NAME,
#             related_name=self.RELATED_NAME,
#             is_compliance=matched,
#             reasons=reasons,
#             schema_id=self.schema_id,
#             fid=self.file.id,
#             schema_results=get_schema_results(self.SCHEMA_FIELDS, self.manager),
#             suggestion=suggestion,
#             label=self.LABEL,
#             origin_contents=self.get_origin_contents(),
#         )


class BondNameChecker(PrivateFundSchemaChecker):
    RELATED_NAME = "基金名称、投资顾问"
    P_INVALID_TEXT = re.compile(r"^((?:有限)?公司|(?:私募)?证券(?:投资)?(?:基金(?:管理)?)?|私募)$")
    P_DELETE_INVALID_TEXT = re.compile(r"((?:有限)?公司|(?:私募)?证券(?:投资)?(?:基金(?:管理)?)?)$")
    SCHEMA_FIELDS = ["基金管理人概况-名称", "基金名称", "基金管理人-名称"]
    LABEL = "schema_367"
    NAME = "基金名称应体现管理人名称"
    FROM = "20181120 私募投资基金命名指引（中国证券投资基金业协会）"
    ORIGIN = "契约型私募投资基金名称应当简单明了，列明私募投资基金管理人全称或能清晰代表私募投资基金管理人名称的简称。私募投资基金管理人聘请投资顾问的，私募投资基金名称中可以列明投资顾问机构的简称。"

    def check(self):
        reasons = []
        matched = True
        suggestion = None

        bond_name = self.manager.get("基金名称")
        company_name = self.manager.get_multi("基金管理人概况-名称")

        if not company_name or not company_name[0].value:
            reasons.append(MatchFailedItem(reason_text="未找到基金管理人"))
            suggestion = "请补充基金管理人"
            matched = False
        elif not bond_name.value:
            matched = False
            reasons.append(MatchFailedItem(reason_text="未找到基金名称"))
            suggestion = "请补充基金名称"
        else:
            name = self.P_DELETE_INVALID_TEXT.sub("", company_name[0].value)[:8]
            bond_name = self.P_DELETE_INVALID_TEXT.sub("", bond_name.value)[:8]

            blocks = difflib.SequenceMatcher(None, name, bond_name).get_matching_blocks()
            blocks = [item for item in blocks if item.size]

            if len(blocks) == 1 and self.P_INVALID_TEXT.search(name[blocks[0].a : blocks[0].a + blocks[0].size]):
                matched = False
                reasons.append(MatchFailedItem(reason_text="基金名称中未包含管理人简称"))
                suggestion = "请在基金名称中补充管理人全称或简称"
            else:
                prev = None
                results = []
                for block in blocks:
                    if prev and prev.a + prev.size != block.a:
                        matched = False
                        suggestion = "请在基金名称中补充管理人全称或简称"
                        reasons.append(MatchFailedItem(reason_text="基金名称中未包含管理人全称或简称"))
                        break

                    results.append(block)
                    prev = block
                else:
                    if (
                        len(
                            self.P_DELETE_INVALID_TEXT.sub(
                                "", "".join(name[item.a : item.a + item.size] for item in results)
                            )
                        )
                        < 2
                    ):
                        matched = False
                        suggestion = "请在基金名称中补充管理人全称或简称"
                        reasons.append(MatchFailedItem(reason_text="基金名称中未包含管理人全称或简称"))
                    else:
                        matched = True
                        reasons.append(MatchSuccessItem(reason_text="基金名称中包含管理人全称或简称"))
                        suggestion = None

        return ResultItem(
            name=self.NAME,
            related_name=self.RELATED_NAME,
            is_compliance=matched,
            reasons=reasons,
            schema_id=self.schema_id,
            fid=self.file.id,
            schema_results=self.manager.build_schema_results(self.SCHEMA_FIELDS),
            suggestion=suggestion,
            label=self.LABEL,
            origin_contents=self.get_origin_contents(),
        )


class InvestmentRiskChecker(PrivateFundSchemaChecker):
    RELATED_NAME = "风险揭示"
    P_CHAPTER = re.compile(r"风险揭示$")
    P_IGNORE_NUMBERING = re.compile(r"^\s*[(（【]?\s*[0-9一二三四五六七八九十a-z]+\s*[)）】,.，、\s]+\s*")
    P_IGNORE_TEXT = re.compile(r"(.*?)")
    P_SPLIT = re.compile(r"[;，；。\n]+")
    SCHEMA_FIELDS = ["基金投资范围-基金投资范围-基金基本情况表"]
    LABEL = "schema_348_2"
    NAME = "合同应当揭示私募基金的一般风险"
    FROM = "20160418 私募投资基金合同指引1号（契约型私募基金合同内容与格式指引）（中国基金业协会）"
    ORIGIN = (
        "私募基金管理人应当在基金合同中向投资者说明有关法律法规，须重点揭示管理人在管理、运用或处分财产过程中，私募基金可能面临的风险，包括但不限于：\n　　"
        "（二）私募基金的一般风险，包括资金损失风险、基金运营风险、流动性风险、募集失败风险、投资标的的风险、税收风险等。"
    )

    def get_investment_scope(self):
        investment_scope_table = self.manager.get("基金投资范围-基金投资范围-基金基本情况表")
        # investment_scope_paragraph = self.manager.get('基金投资范围-正文-投资范围')

        if content := investment_scope_table.value:
            for paragraph_text in self.P_SPLIT.split(content):
                text = self.P_IGNORE_NUMBERING.sub("", paragraph_text)
                text = self.P_IGNORE_TEXT.sub("", text)
                yield text, replace_synonym(SYNONYM_WORDS, text)

    def get_investment_risk(self):
        chapters = self.reader.find_sylls_by_pattern(
            [self.P_CHAPTER],
            order="index",
            reverse=False,
        )
        res = []
        elements = []
        if chapters:
            chapter = chapters[0]
            for index, item in self.reader.syllabus_dict.items():
                if chapter["range"][0] <= index <= chapter["range"][1]:
                    if item["title"]:
                        res.append([item["title"], replace_synonym(SYNONYM_WORDS, item["title"])])
            for _index in range(*chapter["range"]):
                elt_type, element = self.reader.find_element_by_index(_index)
                if elt_type == "PARAGRAPH" and not element.get("fragment"):
                    elements.append(element)

        return res, get_outlines(elements)

    def check(self):
        reasons = []
        matched = True
        suggestion = None

        scopes = list(self.get_investment_scope())
        risks, outlines = self.get_investment_risk()

        scope_matched = {item[1]: None for item in scopes}
        scope_mapping = {scope: origin for origin, scope in scopes}

        for _, scope in scopes:
            for _, risk in risks:
                if scope in risk:
                    scope_matched[scope] = risk
                    break

        page = None
        outline = None
        if outlines:
            page = min(outlines.keys())
            outline = outlines

        miss_scopes = [scope_mapping[scope] for scope, item in scope_matched.items() if not item]
        if miss_scopes or not risks:
            reasons.append(
                MatchFailedItem(reason_text="投资范围内容与《风险揭示》小标题内容不一致", page=page, outlines=outline)
            )
            suggestion = "投资范围内容应与《风险揭示》小标题内容一致"
            matched = False
        else:
            reasons.append(
                MatchSuccessItem(reason_text="投资范围内容与《风险揭示》小标题内容一致", page=page, outlines=outline)
            )

        return ResultItem(
            name=self.NAME,
            related_name=self.RELATED_NAME,
            is_compliance=matched,
            reasons=reasons,
            schema_id=self.schema_id,
            fid=self.file.id,
            schema_results=self.manager.build_schema_results(self.SCHEMA_FIELDS),
            suggestion=suggestion,
            label=self.LABEL,
            origin_contents=self.get_origin_contents(),
        )


class BondTypeChecker(PrivateFundSchemaChecker):
    RELATED_NAME = "基金类型、投资范围"
    SCHEMA_FIELDS = ["基金管理人概况-名称", "基金投资范围-基金投资范围-基金基本情况表", "基金管理人-名称"]
    LABEL = "schema_466"
    NAME = "私募证券投资基金的投资范围"
    FROM = "20191223 私募投资基金备案须知（基金业协会）"
    ORIGIN = "私募证券投资基金(含FOF)的投资范围主要包括股票、债券、期货合约、期权合约、证券类基金份额以及中国证监会认可的其他资产"
    MAPPING = {
        "证券投资": {"非上市公司的股权", "股权类私募基金", "股权类资产管理计划"},
        "股权投资": {"沪深北证券交易所上市交易的股票", "债券", "期货", "期权", "收益互换"},
        "创业投资": {"沪深北证券交易所上市交易的股票", "债券", "期货", "期权", "收益互换"},
    }

    def check(self):
        reasons = []
        matched = True
        suggestion = None

        fun_manager_name = self.manager.get("基金管理人-名称").value or self.manager.get("基金管理人概况-名称").value
        investment_scope = self.manager.get("基金投资范围-基金投资范围-基金基本情况表")

        if not fun_manager_name:
            matched = False
            reasons.append(MatchFailedItem(reason_text="未找到基金管理人"))
            suggestion = "请补充基金管理人"

        elif self.fun_manager_type:
            _type = self.get_fun_manager_type(self.fun_manager_type)
            if _type and _type in self.MAPPING:
                if not investment_scope or not investment_scope.value:
                    matched = False
                    reasons.append(MatchFailedItem(reason_text="未找到投资范围"))
                    suggestion = "请补充投资范围"
                else:
                    words = self.MAPPING.get(_type)
                    for word in words:
                        if word in investment_scope.value:
                            reasons.append(
                                MatchFailedItem(
                                    reason_text=f"基金管理人为{self.fun_manager_type}，与投资范围中的证券类型{word}不匹配"
                                )
                            )
                            title = investment_scope.chapter_title or ""
                            suggestion = f"合同，{title}{self.RELATED_NAME}，不能包括{'、'.join(words)}等关键词"
                            matched = False
                            break
                    else:
                        suggestion = None
                        reasons.append(
                            MatchSuccessItem(reason_text=f"基金管理人为{self.fun_manager_type}，与投资范围匹配")
                        )
            else:
                matched = None
                reasons.append(IgnoreConditionItem(reason_text="管理人类型为其他类型"))
                suggestion = None
        else:
            matched = None
            reasons.append(IgnoreConditionItem(reason_text="管理人类型为其他类型"))
            suggestion = None

        return ResultItem(
            name=self.NAME,
            related_name=self.RELATED_NAME,
            is_compliance=matched,
            reasons=reasons,
            schema_id=self.schema_id,
            fid=self.file.id,
            schema_results=self.manager.build_schema_results(self.SCHEMA_FIELDS),
            suggestion=suggestion,
            label=self.LABEL,
            origin_contents=self.get_origin_contents(),
        )


class BondNameFOFChecker(PrivateFundSchemaChecker):
    RELATED_NAME = "基金名称"
    SCHEMA_FIELDS = ["基金管理人概况-名称", "基金名称", "基金管理人-名称"]
    LABEL = "schema_365"
    NAME = "基金名称应体现投资业务类别"
    FROM = "20181120 私募投资基金命名指引（中国证券投资基金业协会）"
    ORIGIN = (
        "私募投资基金名称应当列明体现基金业务类别的字样，且应当与基金合同、合伙协议或者公司章程约定的基金投资范围、投资方向和风险收益特征保持一致。\n"
        "私募证券投资基金名称中可以使用“股票投资”、“混合投资”、“固定收益投资”、“期货投资”或者其他体现具体投资领域特点的字样。如未体现具体投资领域特点，则应当使用“证券投资”字样。\n"
        "私募股权投资基金名称中可以使用“创业投资”、“并购投资”、“基础设施投资”或者其他体现具体投资领域特点的字样。如未体现具体投资领域特点，则应当使用“股权投资”字样。"
    )

    MAPPING = {
        "证券投资": {"证券投资", "证券投资FOF", "股票投资", "混合投资", "固定收益投资", "期货投资"},
        "股权投资": {"股权投资", "股权投资FOF", "创业投资", "创业投资FOF", "并购投资", "基础设施投资"},
        "创业投资": {"股权投资", "股权投资FOF", "创业投资", "创业投资FOF", "并购投资", "基础设施投资"},
    }

    def check(self):
        reasons = []

        fun_manager_name = self.manager.get("基金管理人-名称").value or self.manager.get("基金管理人概况-名称").value
        bond_name = self.manager.get("基金名称")

        if not fun_manager_name:
            matched = False
            reasons.append(MatchFailedItem(reason_text="未找到基金管理人"))
            suggestion = "请补充基金管理人"

        elif self.fun_manager_type:
            name = bond_name.value
            _type = self.get_fun_manager_type(self.fun_manager_type)
            if _type and _type in self.MAPPING:
                if not bond_name or not bond_name.value:
                    matched = False
                    reasons.append(MatchFailedItem(reason_text="未找到基金名称"))
                    suggestion = "请补充基金名称"
                else:
                    words = self.MAPPING.get(_type)
                    if all(word not in name for word in words):
                        reasons.append(
                            MatchFailedItem(reason_text=f"基金管理人类型为{_type}，与基金名称中的基金类型不匹配")
                        )
                        title = bond_name.chapter_title or ""
                        suggestion = f"合同，{title}{name}，需包括{'、'.join(words)}等关键词"
                        matched = False
                    else:
                        suggestion = None
                        matched = True
                        reasons.append(
                            MatchFailedItem(reason_text=f"基金管理人类型为{_type}，与基金名称中的基金类型匹配")
                        )
            else:
                matched = None
                reasons.append(IgnoreConditionItem(reason_text="管理人类型为其他类型"))
                suggestion = None
        else:
            matched = None
            reasons.append(IgnoreConditionItem(reason_text="管理人类型为其他类型"))
            suggestion = None

        return ResultItem(
            name=self.NAME,
            related_name=self.RELATED_NAME,
            is_compliance=matched,
            reasons=reasons,
            schema_id=self.schema_id,
            fid=self.file.id,
            schema_results=self.manager.build_schema_results(self.SCHEMA_FIELDS),
            suggestion=suggestion,
            label=self.LABEL,
            origin_contents=self.get_origin_contents(),
        )


class SpecialBondNameFOFChecker(PrivateFundSchemaChecker):
    RELATED_NAME = "管理人类型、基金名称"
    SCHEMA_FIELDS = ["基金管理人概况-名称", "基金名称", "基金管理人-名称"]
    LABEL = "schema_471"
    FROM = "20191223 私募投资基金备案须知（基金业协会）"
    ORIGIN = "私募资产配置基金：应当主要采用基金中基金的投资方式"
    NAME = "私募资产配置基金应采用FOF形式"

    def check(self):
        reasons = []
        matched = True
        suggestion = None

        fun_manager_name = self.manager.get("基金管理人-名称").value or self.manager.get("基金管理人概况-名称").value
        bond_name = self.manager.get("基金名称")

        if not fun_manager_name:
            matched = False
            reasons.append(MatchFailedItem(reason_text="未找到基金管理人"))
            suggestion = append_suggestion(suggestion, "请补充基金管理人")

        if not bond_name or not bond_name.value:
            matched = False
            reasons.append(MatchFailedItem(reason_text="未找到基金名称"))
            suggestion = append_suggestion(suggestion, "请补充基金名称")

        elif self.fun_manager_type:
            name = bond_name.value
            _type = self.get_fun_manager_type(self.fun_manager_type)
            if _type == "资产配置":
                if "FOF" not in name:
                    matched = False
                    reasons.append(MatchFailedItem(reason_text="基金管理人类型为资产配置，基金名称未包含FOF字样"))
                    title = bond_name.chapter_title or ""
                    suggestion = f"合同，{title}{name}，应包含FOF字样"
                # else:
                #     suggestion = None
                #     matched = True
                #     reasons = [MatchSuccessItem(reason_text='基金管理人为资产配置类型，基金名称包含FOF字样')]
            else:
                matched = None
                reasons.append(MatchFailedItem(reason_text="管理人类型非资产配置"))
                suggestion = None
        else:
            reasons.append(IgnoreConditionItem(reason_text="基金管理人类型非资产配置"))
            suggestion = None
            matched = None
        return ResultItem(
            name=self.NAME,
            related_name=self.RELATED_NAME,
            is_compliance=matched,
            reasons=reasons,
            schema_id=self.schema_id,
            fid=self.file.id,
            schema_results=self.manager.build_schema_results(self.SCHEMA_FIELDS),
            suggestion=suggestion,
            label=self.LABEL,
            origin_contents=self.get_origin_contents(),
        )


class OperationModeCloseChecker(PrivateFundSchemaChecker):
    RELATED_NAME = "基金名称、运作方式"
    SCHEMA_FIELDS = ["基金管理人概况-名称", "基金管理人-名称", "运作方式"]
    LABEL = "schema_446"
    FROM = "20191223 私募投资基金备案须知（基金业协会）"
    ORIGIN = "私募股权投资基金（含创业投资基金，下同）和私募资产配置基金应当封闭运作，备案完成后不得开放认/申购（认缴）和赎回（退出），基金封闭运作期间的分红、退出投资项目减资、对违约投资者除名或替换以及基金份额转让不在此列。"
    NAME = "私募股权和私募资产配置基金应当封闭运作"

    def check(self):
        reasons = []
        matched = True
        suggestion = None

        operation_mode = self.manager.get("运作方式")
        fun_manager_name = self.manager.get("基金管理人-名称").value or self.manager.get("基金管理人概况-名称").value

        if not fun_manager_name:
            matched = False
            reasons.append(MatchFailedItem(reason_text="管理人名称为空"))
            suggestion = append_suggestion(suggestion, "请补充管理人名称")
        elif self.fun_manager_type and is_matched_fund_manager_types(
            ["私募股权、创业投资基金管理人", "私募资产配置类管理人"], self.fun_manager_type
        ):
            if not operation_mode.value:
                matched = False
                reasons.append(MatchFailedItem(reason_text="运作方式为空"))
                suggestion = append_suggestion(suggestion, "请补充运作方式")
            elif "封闭式" not in operation_mode.value:
                matched = False
                reasons.append(
                    MatchFailedItem(reason_text=f"管理人类型为{self.fun_manager_type or '空'}，运作方式不是封闭式")
                )
                title = operation_mode.chapter_title or ""
                suggestion = f"合同，{title}运作方式，请将“{operation_mode.value}”修改为封闭式"
        else:
            matched = None
            reasons.append(IgnoreConditionItem(reason_text=f"管理人类型为{self.fun_manager_type or '空'}"))

        return ResultItem(
            name=self.NAME,
            related_name=self.RELATED_NAME,
            is_compliance=matched,
            reasons=reasons,
            schema_id=self.schema_id,
            fid=self.file.id,
            schema_results=self.manager.build_schema_results(self.SCHEMA_FIELDS),
            suggestion=suggestion,
            label=self.LABEL,
            origin_contents=self.get_origin_contents(),
        )


class BlackListChecker(PrivateFundSchemaChecker):
    RELATED_NAME = "基金名称"
    SCHEMA_FIELDS = ["基金名称"]
    LABEL = "schema_370"
    FROM = "20181120 私募投资基金命名指引（中国证券投资基金业协会）"
    ORIGIN = "契约型私募投资基金名称应当符合《企业名称禁限用规则》相关规定。"
    NAME = "基金名称应符合《企业名称禁限用规则》"

    IGNORE_WORDS = re.compile(r"[（(]中国[）)]")

    def check(self):
        reasons = []
        matched = True
        suggestion = None

        bond_name = self.manager.get("基金名称").value
        if not bond_name:
            matched = False
            reasons.append(MatchFailedItem(reason_text="未找到基金名称"))
            suggestion = append_suggestion(suggestion, "请补基金名称")
        else:
            words = set()
            value = self.IGNORE_WORDS.sub("", bond_name)
            for word in BLACK_WORDS.split("\n"):
                if word and word in value:
                    words.add(word)

            if words:
                matched = False
                text = "、".join(words)
                reasons.append(MatchFailedItem(reason_text=f"基金名称中含有{text}"))
                suggestion = append_suggestion(suggestion, f"基金名称，请删除{text}")
            else:
                reasons.append(MatchSuccessItem(reason_text="基金名称不含禁用词汇"))

        return ResultItem(
            name=self.NAME,
            related_name=self.RELATED_NAME,
            is_compliance=matched,
            reasons=reasons,
            schema_id=self.schema_id,
            fid=self.file.id,
            schema_results=self.manager.build_schema_results(self.SCHEMA_FIELDS),
            suggestion=suggestion,
            label=self.LABEL,
            origin_contents=self.get_origin_contents(),
        )


class FundNameChecker(PrivateFundSchemaChecker):
    RELATED_NAME = "基金名称"
    SCHEMA_FIELDS = ["基金名称-封面", "基金名称", "募集结算资金专用账户及监督机构-账户名称"]
    LABEL = "schema_474"
    NAME = "全文基金名称保持一致"
    SUGGESTIONS_ON_REVISION = ["请添加基金名称", "全文基金名称需保持一致"]
    REASON = ["基金名称不可为空", "基金名称不是"]

    def check(self):
        fund_name_mode = self.manager.get(self.SCHEMA_FIELDS[0])
        reasons = []
        suggestion = None
        is_compliance = True

        if not fund_name_mode.value:
            reasons.append(MatchFailedItem(reason_text=self.REASON[0]))
            suggestion = self.SUGGESTIONS_ON_REVISION[0]
        else:
            for schema in self.SCHEMA_FIELDS:
                for schema_value in self.manager.get_multi(schema):
                    if schema_value.value and fund_name_mode.value not in schema_value.value:
                        is_compliance = False
                        reasons.append(
                            MatchFailedItem(
                                reason_text=f"{self.REASON[1]}“{fund_name_mode.value}”",
                                page=min(schema_value.outlines, key=int, default=0),
                                outlines=schema_value.outlines,
                            )
                        )

            for page_header in self.reader.page_headers:
                if fund_name_mode.value not in clean_txt(page_header["text"]):
                    is_compliance = False
                    outlines = get_outlines([page_header])
                    reasons.append(
                        MatchFailedItem(
                            reason_text=f"{self.REASON[1]}“{fund_name_mode.value}”",
                            page=min(outlines, key=int, default=0),
                            outlines=outlines,
                        )
                    )
                    break

        return ResultItem(
            name=self.NAME,
            related_name=self.RELATED_NAME,
            is_compliance=is_compliance,
            reasons=reasons,
            suggestion=suggestion,
            schema_id=self.schema_id,
            fid=self.file.id,
            schema_results=self.manager.build_schema_results(self.SCHEMA_FIELDS),
            label=self.LABEL,
            origin_contents=self.get_origin_contents(),
        )


class RaiseAccountChecker(PrivateFundSchemaChecker):
    RELATED_NAME = "募集方式、募集结算资金专用账户及监督机构"
    SCHEMA_FIELDS = ["募集方式"]
    LABEL = "template_3712_1"
    NAME = "直销募集账户及注册登记账户信息应保持一致"
    SUGGESTIONS_ON_REVISION = ["请添加募集方式", "请检查募集方式", "募集结算资金专用账户及监督机构账户类型不能为空"]
    REASON = ["募集方式为空", "募集方式非直销", "募集结算资金专用账户及监督机构账户类型为空"]
    INSTITUTIONAL_STRUCTURE = ["账户类型", "账户号", "账户名称", "开户银行"]
    RULE_TYPE = RuleType.TEMPLATE.value

    def check(self):
        # https://gitpd.paodingai.com/cheftin/docs_scriber/-/issues/3712#note_439249
        recruitment_method_mode = self.manager.get(self.SCHEMA_FIELDS[0])
        if not recruitment_method_mode.value:
            self.result.is_compliance = False
            self.result.reasons.append(MatchFailedItem(reason_text=self.REASON[0]))
            self.result.suggestion = self.SUGGESTIONS_ON_REVISION[0]
        elif not check_contain_content(recruitment_method_mode.value, "直销"):
            self.result.reasons.append(IgnoreConditionItem(reason_text=self.REASON[1]))
        if not self.result.reasons:
            direct_selling_index = -1
            register_index = -1
            for item in self.INSTITUTIONAL_STRUCTURE:
                raise_account_mode_list = self.manager.get_multi(f"募集结算资金专用账户及监督机构-{item}")
                if item == "账户类型":
                    for raise_account_mode in raise_account_mode_list:
                        if raise_account_mode.value == "直销情况下募集结算资金归集账户":
                            direct_selling_index = json.loads(raise_account_mode.answer["key"])[1].split(":")[1]
                        elif raise_account_mode.value == "注册登记账户":
                            register_index = json.loads(raise_account_mode.answer["key"])[1].split(":")[1]
                elif len(raise_account_mode_list) > 0:
                    direct_selling_mode = None
                    register_mode = None
                    for raise_account_mode in raise_account_mode_list:
                        if json.loads(raise_account_mode.answer["key"])[1].split(":")[1] == direct_selling_index:
                            direct_selling_mode = raise_account_mode
                        if json.loads(raise_account_mode.answer["key"])[1].split(":")[1] == register_index:
                            register_mode = raise_account_mode
                    if not direct_selling_mode and not register_mode:
                        continue
                    if not direct_selling_mode:
                        self.result.is_compliance = False
                        self.result.reasons.append(
                            MatchFailedItem(
                                reason_text=f"直销情况下募集结算资金归集账户:{item}为空",
                            )
                        )
                    if not register_mode:
                        self.result.is_compliance = False
                        self.result.reasons.append(
                            MatchFailedItem(
                                reason_text=f"注册登记账户:{item}为空",
                            )
                        )
                    if direct_selling_mode and register_mode:
                        outlines = deepcopy(register_mode.outlines)
                        for page, outline in direct_selling_mode.outlines.items():
                            if page in outlines:
                                outlines[page].extend(outline)
                            else:
                                outlines[page] = outline
                        if direct_selling_mode.value != register_mode.value:
                            self.result.is_compliance = False
                            self.result.reasons.append(
                                MatchFailedItem(
                                    reason_text=f"{item}不一致",
                                    page=min(direct_selling_mode.outlines, key=int, default=0),
                                    outlines=outlines,
                                )
                            )
                        else:
                            self.result.reasons.append(
                                MatchSuccessItem(
                                    reason_text=f"{item}一致",
                                    page=min(direct_selling_mode.outlines, key=int, default=0),
                                    outlines=outlines,
                                )
                            )

        return self.result


class RaiseAccountInfoChecker(PrivateFundSchemaChecker):
    RELATED_NAME = "募集结算资金专用账户及监督机构"
    SCHEMA_FIELDS = ["募集方式"]
    LABEL = "template_3712_2"
    NAME = "代销募集账户信息准确性验证"
    SUGGESTIONS_ON_REVISION = ["请添加募集方式", "请检查募集方式", "请检查募集结算资金归集账户"]
    REASON = ["募集方式为空", "募集方式不是代销", "募集结算资金专用账户及监督机构账户类型为空"]
    INSTITUTIONAL_STRUCTURE = ["账户类型", "账户名称", "账户号", "开户银行", "大额支付系统号"]
    TEMPLATES = {
        "代销机构付款账户": {
            "账户名称": "中国银河证券股份有限公司（客户）",
            "账户号": "860189068610001",
            "开户银行": "招商银行股份有限公司北京分行营业部",
            "大额支付系统号": "308100005027",
        },
        "代销机构收款账户": {
            "账户名称": "中国银河证券股份有限公司（客户）",
            "账户号": "0200250129200071648",
            "开户银行": "工行北京复兴门支行",
            "大额支付系统号": "102100025013",
        },
    }
    RULE_TYPE = RuleType.TEMPLATE.value

    def gen_result(self, mode: Answer, account: str, item: str, suggestions: list):
        template = self.TEMPLATES[account][item]
        if not mode:
            self.result.is_compliance = False
            self.result.reasons.append(MatchFailedItem(reason_text=f"{account}-{item}为空"))
            suggestions.append(f"请检查:{account}-{item}")
        elif mode.value != self.TEMPLATES[account][item]:
            self.result.is_compliance = False
            self.result.reasons.append(
                MatchFailedItem(
                    reason_text=f"{account}-{item} 值不为{template}",
                    page=min(mode.outlines, key=int, default=0),
                    outlines=mode.outlines,
                )
            )
            suggestions.append(
                render_suggestion(f"{account}-{item}", rule_name="", content=mode.value, suggestion=template, prefix="")
            )
        else:
            self.result.reasons.append(
                MatchSuccessItem(
                    page=min(mode.outlines, key=int, default=0),
                    outlines=mode.outlines,
                )
            )

    def check(self):
        recruitment_method_mode = self.manager.get(self.SCHEMA_FIELDS[0])
        if not recruitment_method_mode.value:
            self.result.is_compliance = False
            self.result.reasons.append(MatchFailedItem(reason_text=self.REASON[0]))
            self.result.suggestion = self.SUGGESTIONS_ON_REVISION[0]
        elif not check_contain_content(recruitment_method_mode.value, "代销"):
            self.result.reasons.append(IgnoreConditionItem(reason_text=self.REASON[1]))
        if not self.result.reasons:
            payment_index = -1
            collection_index = -1
            # 1. 先找账户类型,确定序列索引
            # 2. 再找其他相关属性
            suggestions = []
            modes_dict = defaultdict(dict)
            for item in self.INSTITUTIONAL_STRUCTURE:
                raise_account_mode_list = self.manager.get_multi(f"募集结算资金专用账户及监督机构-{item}")
                if item == "账户类型":
                    for raise_account_mode in raise_account_mode_list:
                        if raise_account_mode.value == "募集结算资金归集账户-代销机构付款账户":
                            payment_index = json.loads(raise_account_mode.answer["key"])[1].split(":")[1]
                        elif raise_account_mode.value == "募集结算资金归集账户-代销机构收款账户":
                            collection_index = json.loads(raise_account_mode.answer["key"])[1].split(":")[1]
                    if payment_index == -1:
                        self.result.reasons.append(MatchFailedItem(reason_text="未找到'代销机构收款账户'"))
                    if collection_index == -1:
                        self.result.reasons.append(MatchFailedItem(reason_text="未找到'代销机构收款账户'"))
                    if payment_index == -1 or collection_index == -1:
                        self.result.is_compliance = False
                        self.result.suggestion = self.SUGGESTIONS_ON_REVISION[2]
                        break
                    continue
                payment_mode = None
                collection_mode = None
                for raise_account_mode in raise_account_mode_list:
                    if json.loads(raise_account_mode.answer["key"])[1].split(":")[1] == payment_index:
                        payment_mode = raise_account_mode
                    if json.loads(raise_account_mode.answer["key"])[1].split(":")[1] == collection_index:
                        collection_mode = raise_account_mode
                modes_dict["代销机构付款账户"][item] = payment_mode
                modes_dict["代销机构收款账户"][item] = collection_mode
            for account, modes in modes_dict.items():
                for item, mode in modes.items():
                    self.gen_result(mode, account, item, suggestions)
            if suggestions:
                self.result.suggestion = "\n".join(suggestions)
        return self.result


class FundServiceFeeChecker(PrivateFundSchemaChecker):
    RELATED_NAME = "基金服务费"
    SCHEMA_FIELDS = ["基金服务费", "基金服务费-计提方法、计提标准和支付方式"]
    LABEL = "template_3712_8"
    NAME = "基金合同应明确列示基金服务费及其计算方法"
    SUGGESTIONS_ON_REVISION = ["请补充基金服务费", "请补充基金服务费-计提方法、计提标准和支付方式"]
    REASON = ["基金服务费为空", "基金服务费-计提方法、计提标准和支付方式为空"]

    RATE_TEMPLATE = [
        [
            "基金服务年费率：{X}%；",
        ],
        [
            "基金服务年费率：{X}%；",
            "基金服务费每日收取下限：{X1}元",
        ],
    ]

    SERVICE_CHARGE_TEMPLATES = [
        [
            "自本私募基金成立起，基金服务机构的基金服务费按本私募基金前一日基金资产净值的基金服务年费率计算，每日计提，按季支付。基金服务费的计算方法如下：",
            "每日应计提的基金服务费＝前一日的基金资产净值×基金服务年费率÷当年实际天数",
        ],
        [
            "本私募基金为基金服务费设置基金服务费每日收取下限（单位：人民币元，详见“基金基本情况表”），即实际每日计提基金服务费不足基金服务费每日收取下限时按照基金服务费每日收取下限收取。基金服务费的计算方法如下：",
            "每日应计提的基金服务费＝Max（前一日的基金资产净值×基金服务年费率÷当年实际天数，基金服务费每日收取下限）",
            "Max：表示两个计算值中取最大值。",
        ],
    ]
    P_FUND_FEE = PatternCollection(
        [
            r"基金服务年?费率[:：](?P<val>.*)[%％]",
            r"基金服务机构的基金服务费年费率[:：](?P<val>.*?)/年",
        ]
    )
    P_FUND_FEE_DAILY = PatternCollection([r"基金服务费每日收取下限[:：](?P<val>.*)元"])
    RULE_TYPE = RuleType.TEMPLATE.value

    def check(self):
        templates = []
        fund_service_fee_mold = self.manager.get(self.SCHEMA_FIELDS[0])
        if not fund_service_fee_mold.value:
            self.result.reasons.append(MatchFailedItem(reason_text=self.REASON[0]))
            self.result.suggestion = self.SUGGESTIONS_ON_REVISION[0]
            return self.result
        match1 = self.P_FUND_FEE.nexts(fund_service_fee_mold.value)
        match2 = self.P_FUND_FEE_DAILY.nexts(fund_service_fee_mold.value)
        data = {
            "X": match1.group("val") if match1 else "X",
            "X1": match2.group("val") if match2 else "X1",
        }

        fund_service_fee_daily_mold = self.manager.get(self.SCHEMA_FIELDS[1])
        if not fund_service_fee_daily_mold.value:
            self.result.reasons.append(MatchFailedItem(reason_text=self.REASON[1]))
            self.result.suggestion = self.SUGGESTIONS_ON_REVISION[1]
            return self.result

        for item in self.RATE_TEMPLATE:
            templates.append([_template.format(**data) for _template in item])
        suggestions = []
        right_templates = [fund_service_fee_mold, fund_service_fee_daily_mold]
        for idx, l_templates in enumerate([templates, self.SERVICE_CHARGE_TEMPLATES]):
            format_template = "\n".join(l_templates[1]) if match2 else "\n".join(l_templates[0])
            result = self.init_result()
            r_template = right_templates[idx]
            self.paragraph_similarity(
                result=result,
                paragraphs_left_list=l_templates,
                paragraphs_right=[r_template.value],
                outlines=r_template.outlines,
                origin_content=format_template,
                name=TemplateName.EDITING_NAME,
                content_title=TemplateName.EDITING_TITLE,
            )
            if result.reasons:
                self.result.reasons.extend(result.reasons)
            if result.suggestion:
                suggestions.append(result.suggestion)
            self.result.is_compliance &= result.is_compliance

        self.result.suggestion = "\n".join(suggestions)

        return self.result


class FundManagementFeeChecker(PrivateFundSchemaChecker):
    RELATED_NAME = "管理费"
    SCHEMA_FIELDS = ["基金管理费", "基金管理费-计提方法、计提标准和支付方式"]
    LABEL = "template_3712_9"
    NAME = "基金合同应明确列示管理费及其计算方法"
    SUGGESTIONS_ON_REVISION = ["请补充基金管理费", "请补充基金管理费-计提方法、计提标准和支付方式"]
    REASON = ["基金管理费为空", "基金管理费-计提方法、计提标准和支付方式为空"]
    TEMPLATES = [
        [
            "基金管理年费率：{X}%；",
            "自本私募基金成立起，基金管理人的管理费按本私募基金前一日基金资产净值的管理费年费率计算，每日计提，按季支付。计算方法如下：",
            "每日应计提的管理费＝前一日的基金资产净值×管理费年费率÷当年实际天数",
        ],
        [
            "A类份额基金管理年费率：{X}%；B类份额基金管理年费率：{X1}%",
            "自本私募基金成立起，基金管理人的管理费按本私募基金前一日基金资产净值的管理费年费率计算，每日计提，按季支付。计算方法如下：",
            "每日某类份额应计提的管理费＝前一日的该类基金份额的基金资产净值×该类基金份额的管理费年费率÷当年实际天数，每日本基金应计提的管理费为每类份额每日应计提管理费之和。",
        ],
    ]
    P_FUND_FEE = PatternCollection(
        [
            r"^基金管理年?费率[:：](?P<val>.*)[%％]",
            r"基金服务机构的基金服管理年费率[:：](?P<val>.*?)/年",
            r"A类份额基金管理年?费率[:：](?P<val>[^；;]*)[%％]",
        ]
    )
    P_FUND_FEE_DAILY = PatternCollection([r"B类份额基金管理年?费率[:：](?P<val>.*)[%％]"])

    def check(self):
        templates = []
        fund_service_fee_mold = self.manager.get(self.SCHEMA_FIELDS[0])
        if not fund_service_fee_mold.value:
            self.result.reasons.append(MatchFailedItem(reason_text=self.REASON[0]))
            self.result.suggestion = self.SUGGESTIONS_ON_REVISION[0]
            return self.result
        match1 = self.P_FUND_FEE.nexts(fund_service_fee_mold.value)
        match2 = self.P_FUND_FEE_DAILY.nexts(fund_service_fee_mold.value)
        data = {
            "X": match1.group("val") if match1 else "X",
            "X1": match2.group("val") if match2 else "X1",
        }
        for item in self.TEMPLATES:
            templates.append([_template.format(**data) for _template in item])
        if match1:
            format_template = "\n".join(templates[0])
        else:
            format_template = "\n".join(templates[1])

        fund_service_fee_daily_mold = self.manager.get(self.SCHEMA_FIELDS[1])
        if not fund_service_fee_daily_mold.value:
            self.result.reasons.append(MatchFailedItem(reason_text=self.REASON[1]))
            self.result.suggestion = self.SUGGESTIONS_ON_REVISION[1]
            return self.result
        outlines = fund_service_fee_mold.outlines
        outlines.update(fund_service_fee_daily_mold.outlines)
        self.paragraph_similarity(
            result=self.result,
            paragraphs_left_list=templates,
            paragraphs_right=[fund_service_fee_mold.value, fund_service_fee_daily_mold.value],
            outlines=outlines,
            origin_content=format_template,
            name=TemplateName.EDITING_NAME,
            content_title=TemplateName.EDITING_TITLE,
        )
        return self.result


class AntiMoneyLaunderingChecker(PrivateFundSchemaChecker):
    RULE_TYPE = RuleType.TEMPLATE.value
    RELATED_NAME = "管理人的权利义务"
    SCHEMA_FIELDS = ["基金管理人的声明与承诺"]
    LABEL = "template_428"
    NAME = "管理人/募集机构应履行反洗钱义务"
    FROM = "20160715 私募投资基金募集行为管理办法（中国基金业协会）"
    ORIGIN = "募集机构应当合理审慎地审查投资者是否符合私募基金合格投资者标准，依法履行反洗钱义务，"

    TEMPLATES = [
        {
            "name": TemplateName.EDITING_NAME,
            "content_title": TemplateName.EDITING_TITLE,
            "items": [
                "基金管理人同意并承诺配合托管人开展反洗钱和反恐怖融资工作，基金管理人承诺具备向基金托管人立即提供客户尽职调查必要信息的能力和条件。在基金托管人因履行反洗钱和反恐怖融资义务需开展客户尽职调查时，基金管理人承诺能够立即提供基金委托人身份信息、身份证件或其他身份证明文件以及其他资料的复印件或者影印件。如因基金管理人未履行相关法律法规规定的反洗钱义务而导致基金托管人遭受包括监管处罚在内的任何损失，基金管理人应向基金托管人承担赔偿责任。",
            ],
        },
        {
            "name": TemplateName.LAW_NAME,
            "content_title": TemplateName.LAW_TITLE,
            "items": ["募集机构应当合理审慎地审查投资者是否符合私募基金合格投资者标准，依法履行反洗钱义务。"],
        },
    ]

    def check(self):
        self.result.is_compliance = False
        answer = self.manager.get(self.SCHEMA_FIELDS[0])
        if not answer.value:
            self.result.reasons = [SchemaFailedItem(reason_text="基金管理人的声明与承诺不能为空")]
            self.result.suggestion = "请添加基金管理人的声明与承诺"
            return self.result

        condition_checker = BaseConditionsChecker(
            reader=self.reader,
            manager=self.manager,
            file=self.file,
            schema_id=self.schema_id,
            labels=self.labels,
            fund_manager_info=self.fund_manager_info,
        )
        template = {
            "label": self.LABEL,
            "schema_fields": self.SCHEMA_FIELDS,
            "related_name": self.RELATED_NAME,
            "name": self.NAME,
            "from": self.FROM,
            "origin": self.ORIGIN,
            "templates": self.TEMPLATES,
            "contract_content": self.CONTRACT_CONTENT,
        }
        condition_checker.TEMPLATES = [template]
        result = condition_checker.check()
        if not result:
            return
        result = result[0]
        result.rule_type = self.RULE_TYPE
        miss_content = not any(reason.matched for reason in result.reasons)
        matched, reasons = condition_checker.after_match_template(template, result.reasons, miss_content)
        result.reasons = reasons
        result.is_compliance = matched
        return result
