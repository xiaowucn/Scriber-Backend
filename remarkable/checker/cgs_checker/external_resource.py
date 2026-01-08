import logging

import httpx

from remarkable.checker.cgs_checker.cgs_esb_client import ESBClient
from remarkable.plugins.cgs.common.para_similarity import ParagraphSimilarity


class ExternalResource:
    FIELD_MAPPING = {}
    IGNORE_FIELDS = []

    def __init__(self, manager):
        self.manager = manager

    def get_name(self):
        return self.manager.get("基金管理人-名称").value or self.manager.get("基金管理人概况-名称").value

    def build_fields_result(self, results):
        fields_result = {}
        for field, spider_field in self.FIELD_MAPPING.items():
            fields_result[field] = {}
            for item in results:
                if spider_field not in item:
                    continue

                matched = False
                compare_result = ParagraphSimilarity.compare_two_text(
                    self.manager.get(field).value or "", item[spider_field] or ""
                )
                if compare_result.is_full_matched and item[spider_field]:
                    matched = True
                elif fields_result.get(field):  # 只找第一个
                    continue

                fields_result[field] = {
                    "matched": matched,
                    "text": item[spider_field],
                    "answer": self.manager.get(field),
                    "ignore_check": field in self.IGNORE_FIELDS,
                    "diff": [
                        {
                            "html": compare_result.html_diff_content,
                            "left": compare_result.left_content,
                            "right": compare_result.right_content,
                        }
                    ]
                    if field not in self.IGNORE_FIELDS and self.manager.get(field).value
                    else None,
                }

            if not fields_result.get(field):
                fields_result[field] = {
                    "matched": False,
                    "text": None,
                    "answer": self.manager.get(field),
                    "ignore_check": field in self.IGNORE_FIELDS,
                    "diff": None,
                }
        return fields_result

    async def get(self):
        results = []
        fund_manager_name = self.get_name()
        if fund_manager_name:
            results = await self.get_outer_resource_by_name(fund_manager_name)
        return self.build_fields_result(results)

    async def get_outer_resource_by_name(self, name):
        raise NotImplementedError


class AMACSource(ExternalResource):
    FIELD_MAPPING = {
        "基金管理人概况-名称": "FInfoCorpFundmanagementcomp",
        "基金管理人概况-住所": "FInfoAddress",
        "基金管理人概况-通讯地址": "FInfoOffice",
        "基金管理人概况-法定代表人/执行事务合伙人（委派代表）（如有）": "FInfoSolSig",
        "基金管理人概况-在基金业协会登记编号": "FInfoSequence",
        "基金管理人概况-类型": "FInfoManagedFundType",
        "基金管理人-名称": "FInfoCorpFundmanagementcomp",  # 第一页里的
    }

    IGNORE_FIELDS = {"基金管理人概况-类型"}

    async def get_outer_resource_by_name(self, name):
        try:
            return await ESBClient().get_chf_manager_info(name)
        except httpx.HTTPError as e:
            logging.exception(e)
        return []


class CGSSource(ExternalResource):
    FIELD_MAPPING = {
        "基金管理人概况-名称": "CorpName",
        "基金管理人-名称": "CorpName",  # 第一页里的
        "基金管理人概况-住所": "CorpAddr",
        "基金管理人概况-法定代表人/执行事务合伙人（委派代表）（如有）": "LegPerName",
    }

    async def get_outer_resource_by_name(self, name):
        results = []
        company = await ESBClient().get_sda_info(name)
        if isinstance(company, dict):
            results.append(company)
        else:
            results = company
        return results
