import base64
import hashlib
import logging
import os
from datetime import datetime, timedelta, timezone
from uuid import uuid4

import httpx

from remarkable import config

MOCKED_DATA = {
    "明世伙伴基金管理（珠海）有限公司": {
        "data": {
            "Datas": [
                {
                    "SetupDate": 20180808,
                    "CorpId": "qcc919d34bd414441b0518fdb359f58b8",
                    "RegNo": "440003000516966",
                    "LegPerName": "齐亮",
                    "RegCptlCrrc": "人民币",
                    "EconomyIndustryCategoryName": "金融业",
                    "UnifiedSocialCrdCode": "91440400MA5243YD07",
                    "BusiScope": "章程记载的经营范围：资产管理、投资管理、投资咨询（私募基金管理人未完成在中国证"
                    "券投资基金业协会登记的，不得开展私募基金业务）。（依法须经批准的项目，经相关部门批准后方可开展经营活动）〓",
                    "EconomyIndustryCategoryCode": "J",
                    "CorpSts": "在营（开业）",
                    "CorpAddr": "珠海市横琴新区宝华路6号105室-55220（集中办公区）",
                    "CorpName": "明世伙伴基金管理(珠海)有限公司",
                    "CorpProvince": "广东",
                    "RegOfficeName": "珠海横琴新区市场监督管理局",
                    "ApproveDate": 20200722,
                    "EconomyIndustryCode": "6713",
                    "EconomyIndustryName": "基金管理服务",
                    "CorpTypeName": "有限责任公司（非自然人投资或控股的法人独资）",
                    "BusiTermFrom": 20180808,
                    "RegCptl": 3.0e7,
                }
            ],
            "IndexName": "edw-corpmain",
            "Scroll": "1m",
            "Took": "3563ms",
            "TotalHits": 1,
        },
        "meta": {"code": "0000", "message": "", "success": True},
    },
    "中国银河投资管理有限公司": {
        "data": {
            "Datas": [
                {
                    "CorpCity": "北京市",
                    "SetupDate": 20070126,
                    "LegPerName": "宋卫刚",
                    "RegNo": "100000000040694",
                    "RegCptlCrrc": "人民币",
                    "EconomyIndustryCategoryName": "金融业",
                    "UnifiedSocialCrdCode": "91110000710934537G",
                    "BusiScope": "证券经纪；证券投资咨询；与证券交易、证券投资活动有关的财务顾问；证券承销与保荐；证券自营；融资融券；证券投资基金代销；为"
                    "期货公司提供中间介绍业务；代销金融产品；证券投资基金托管业务；保险兼业代理业务；销售贵金属制品。（市场主体依法自主选择经营项目，开展经营活动；依法须经批准的项目，"
                    "经相关部门批准后依批准的内容开展经营活动；不得从事国家和本市产业政策禁止和限制类项目的经营活动。）",
                    "EconomyIndustryCategoryCode": "J",
                    "CorpSts": "在营（开业）",
                    "CorpAddr": "北京市西城区西城区金融大街35号国际企业大厦C座",
                    "CorpName": "中国银河投资管理有限公司",
                    "CorpProvince": "北京",
                    "RegOfficeName": "北京市市场监督管理局",
                    "ApproveDate": 20210713,
                    "EconomyIndustryCode": "6712",
                    "BusiTermTo": 99991231,
                    "EconomyIndustryName": "证券经纪交易服务",
                    "CorpCounty": "西城区",
                    "CorpTypeName": "其他股份有限公司（上市）",
                    "BusiTermFrom": 20070126,
                    "RegCptl": 1.0137258757e10,
                }
            ],
            "IndexName": "edw-corpmain",
            "Scroll": "1m",
            "Took": "17ms",
            "TotalHits": 7426,
        },
        "meta": {"code": "0000", "message": "", "success": True},
    },
    "上海尚雅投资管理有限公司": {
        "data": {
            "Datas": [
                {
                    "CorpCity": "北京市",
                    "SetupDate": 20070126,
                    "LegPerName": "陈共炎",
                    "RegNo": "100000000040694",
                    "RegCptlCrrc": "人民币",
                    "EconomyIndustryCategoryName": "金融业",
                    "UnifiedSocialCrdCode": "91110000710934537G",
                    "BusiScope": "证券经纪；证券投资咨询；与证券交易、证券投资活动有关的财务顾问；证券承销与保荐；证券自营；融资融券；证券"
                    "投资基金代销；为期货公司提供中间介绍业务；代销金融产品；证券投资基金托管业务；保险兼业代理业务；销售贵金属制品。（市场主体依法自主选择经营项目，开展经营活动"
                    "；依法须经批准的项目，经相关部门批准后依批准的内容开展经营活动；不得从事国家和本市产业政策禁止和限制类项目的经营活动。）",
                    "EconomyIndustryCategoryCode": "J",
                    "CorpSts": "在营（开业）",
                    "CorpAddr": "北京市西城区金融大街35号2-6层",
                    "CorpName": "上海尚雅投资管理有限公司",
                    "CorpProvince": "北京",
                    "RegOfficeName": "北京市市场监督管理局",
                    "ApproveDate": 20210713,
                    "EconomyIndustryCode": "6712",
                    "BusiTermTo": 99991231,
                    "EconomyIndustryName": "证券经纪交易服务",
                    "CorpCounty": "西城区",
                    "CorpTypeName": "其他股份有限公司（上市）",
                    "BusiTermFrom": 20070126,
                    "RegCptl": 1.0137258757e10,
                }
            ],
            "IndexName": "edw-corpmain",
            "Scroll": "1m",
            "Took": "17ms",
            "TotalHits": 7426,
        },
        "meta": {"code": "0000", "message": "", "success": True},
    },
    "中国银河证券股份有限公司北京分公司": {
        "data": {
            "Datas": [
                {
                    "CorpCity": "北京市",
                    "SetupDate": 20110726,
                    "LegPerName": "张凯慧",
                    "RegNo": "110102014098895",
                    "RegCptlCrrc": "人民币",
                    "EconomyIndustryCategoryName": "金融业",
                    "UnifiedSocialCrdCode": "9111010258083510X9",
                    "BusiScope": "证券经纪；证券投资咨询；证券投资基金代销；与证券交易、证券投资活动有关的财务顾问；代销金融产品；证券承销与保荐（仅"
                    "限项目承揽、项目信息传递与推荐、客户关系维护等辅助工作）；保险兼业代理业务。（领取本执照后，应到证监会取得行政许可；市场主体依法自主选择经营项目，开"
                    "展经营活动；依法须经批准的项目，经相关部门批准后依批准的内容开展经营活动；不得从事国家和本市产业政策禁止和限制类项目的经营活动。）",
                    "EconomyIndustryCategoryCode": "J",
                    "CorpSts": "在营（开业）",
                    "CorpAddr": "北京市西城区太平桥大街111号五层",
                    "CorpName": "中国银河证券股份有限公司北京分公司",
                    "CorpProvince": "北京",
                    "RegOfficeName": "北京市西城区市场监督管理局",
                    "ApproveDate": 20200527,
                    "EconomyIndustryCode": "6712",
                    "BusiTermTo": 99991231,
                    "EconomyIndustryName": "证券经纪交易服务",
                    "CorpCounty": "西城区",
                    "CorpTypeName": "其他股份有限公司分公司（上市）",
                    "BusiTermFrom": 20110726,
                }
            ],
            "IndexName": "edw-corpmain",
            "Scroll": "1m",
            "Took": "17ms",
            "TotalHits": 7426,
        },
        "meta": {"code": "0000", "message": "", "success": True},
    },
}


MANAGER_MOCKED_DATA = {
    "中国银河投资管理有限公司": {
        "data": {
            "Datas": [
                {
                    "FInfoLawFirm": "江苏铭天律师事务所",
                    "Opdate": "2021-04-12T10:23:55.000Z",
                    "Opmode": "1",
                    "FInfoSolSig": "宋卫刚",
                    "IsNew": 1,
                    "IsMember": 0,
                    "FInfoRegcapital": 1000.0,
                    "FInfoCrncyCode": "人民币",
                    "FInfoSequence": "P1000682",
                    "FInfoAddress": "北京市",
                    "FInfoManagedFundType": "私募资产配置类管理人",
                    "FInfoDisclosurewebsite": "https://gs.amac.org.cn/"
                    "amac-infodisc/res/pof/manager/1703152121109661.html",
                    "FInfoPaidcapital": 301.0,
                    "FInfoTotalemployees": 3,
                    "AnnDate": "20210412",
                    "MsgKey": "chfmanagerinfo",
                    "FInfoEstablishTime": "20161116",
                    "Mopdate": "2021-04-12T10:08:11.000Z",
                    "BizDate": 20220120,
                    "FInfoCorpFundmanagementcomp": "中国银河投资管理有限公司",
                    "FInfoReportingTime": "20190529",
                    "FInfoOrgCode": "91330206MA282YME6R",
                    "FInfoLegalOpinion": "办结",
                    "ObjectId": "{47C41A88-C5BB-11E7-AAC1-6C0B84DE254B}",
                    "FInfoRatio": 30.1,
                    "FInfoCompanyid": "aKZpoTxLgC",
                    "FInfoOffice": "北京市",
                    "FInfoRegistrationTime": "20170921",
                    "FManagementScaleInterval": "0-5亿元",
                    "_id": "4eb9651df92da09db5e7be81915a90a433b76286",
                    "FInfoCompProperty": "内资企业",
                }
            ],
            "IndexName": "edw-corpmain",
            "Scroll": "1m",
            "Took": "17ms",
            "TotalHits": 7426,
        },
        "meta": {"code": "0000", "message": "", "success": True},
    },
    "上海尚雅投资管理有限公司": {
        "data": {
            "Datas": [
                {
                    "FInfoLawFirm": "江苏铭天律师事务所",
                    "Opdate": "2021-04-12T10:23:55.000Z",
                    "Opmode": "1",
                    "FInfoSolSig": "石波",
                    "IsNew": 1,
                    "IsMember": 0,
                    "FInfoRegcapital": 1000.0,
                    "FInfoCrncyCode": "人民币",
                    "FInfoSequence": "P1000271",
                    "FInfoAddress": "上海市",
                    "FInfoManagedFundType": "私募证券投资基金管理人",
                    "FInfoDisclosurewebsite": "https://gs.amac.org.cn/"
                    "amac-infodisc/res/pof/manager/1703152121109661.html",
                    "FInfoPaidcapital": 301.0,
                    "FInfoTotalemployees": 3,
                    "AnnDate": "20210412",
                    "MsgKey": "chfmanagerinfo",
                    "FInfoEstablishTime": "20161116",
                    "Mopdate": "2021-04-12T10:08:11.000Z",
                    "BizDate": 20220120,
                    "FInfoCorpFundmanagementcomp": "上海尚雅投资管理有限公司",
                    "FInfoReportingTime": "20190529",
                    "FInfoOrgCode": "91330206MA282YME6R",
                    "FInfoLegalOpinion": "办结",
                    "ObjectId": "{47C41A88-C5BB-11E7-AAC1-6C0B84DE254B}",
                    "FInfoRatio": 30.1,
                    "FInfoCompanyid": "aKZpoTxLgC",
                    "FInfoOffice": "上海市",
                    "FInfoRegistrationTime": "20170921",
                    "FManagementScaleInterval": "0-5亿元",
                    "_id": "4eb9651df92da09db5e7be81915a90a433b76286",
                    "FInfoCompProperty": "内资企业",
                }
            ],
            "IndexName": "edw-corpmain",
            "Scroll": "1m",
            "Took": "17ms",
            "TotalHits": 7426,
        },
        "meta": {"code": "0000", "message": "", "success": True},
    },
}


class ESBClient:
    def __init__(self):
        self.user = config.get_config("cgs.esb.user")
        self.password = config.get_config("cgs.esb.password")
        self.call_timeout = config.get_config("cgs.esb.call_timeout", default=10)

    def build_request_headers(self, function_no, function_version, caller_system_code):
        _created = datetime.now(timezone(timedelta(hours=8))).isoformat(timespec="seconds")
        _nonce = self.generate_nonce()
        _password_digest = self.calc_digest(_nonce, _created, self.password)
        _headers = {
            "Content-Type": "application/json;charset=UTF-8",
            "Tracking-Id": str(uuid4()),  # 调用方生成的唯一标识，用以跟踪某一请求
            "User": self.user,  # ESB分配的用户名
            "Created": _created,  # 请求创建时间，必须为东8区。2021-11-18T17:59:17+08:00
            "Nonce": _nonce,  # 随机数
            "Password-Digest": _password_digest,  # 密码摘要
            "Function-No": function_no,  # 功能号
            "Function-Version": function_version,  # 功能号版本
            "Caller-System-Code": caller_system_code,  # 调用方系统代码，由ESB告知，为数据中心统一定义的系统三字代码
            "Accept-Encoding": "",  # 可选。填gzip，则返回的是压缩后的数据
        }
        return _headers

    @classmethod
    def generate_nonce(cls, length=20):
        origin_byte = os.urandom(length)
        return base64.b64encode(origin_byte).decode("ascii")

    @classmethod
    def calc_digest(cls, nonce: str, created: str, password: str):
        sha1 = hashlib.sha1()
        sha1.update(base64.b64decode(nonce))
        sha1.update(bytes(created, encoding="ascii"))
        sha1.update(bytes(password, encoding="ascii"))
        digest = sha1.digest()
        return base64.b64encode(digest).decode("ascii")

    @classmethod
    def build_query_body_by_name(cls, key, value):
        _body = {
            "relaType": "AND",
            "openScroll": False,
            "size": 10,
            "conditions": [{"value": value, "key": key}],
        }
        return _body

    async def get_chf_manager_info(self, name: str):
        if config.get_config("cgs.esb.debug"):
            logging.warning("debug mode!!! skip fetch api results")
            if name in MANAGER_MOCKED_DATA:
                return MANAGER_MOCKED_DATA[name]["data"]["Datas"]
            return []

        url = config.get_config("cgs.esb.apis.manager.url")
        body = self.build_query_body_by_name("FInfoCorpFundmanagementcomp", name)
        function_no = config.get_config("cgs.esb.apis.manager.function_no")
        function_version = config.get_config("cgs.esb.apis.manager.function_version")
        caller_system_code = config.get_config("cgs.esb.apis.manager.caller_system_code")
        headers = self.build_request_headers(function_no, function_version, caller_system_code)

        logging.info(f"start fetch api results for {function_no}: {url},\n headers: {headers}\n body: {body}")

        return await self.get_info(url, headers, body)

    async def get_sda_info(self, name):
        if config.get_config("cgs.esb.debug"):
            logging.warning("debug mode!!! skip fetch api results")
            if name in MOCKED_DATA:
                return MOCKED_DATA[name]["data"]["Datas"]
            return []

        url = config.get_config("cgs.esb.apis.sda.url")
        body = self.build_query_body_by_name("CorpName", name)

        function_no = config.get_config("cgs.esb.apis.sda.function_no")
        function_version = config.get_config("cgs.esb.apis.sda.function_version")
        caller_system_code = config.get_config("cgs.esb.apis.sda.caller_system_code")
        headers = self.build_request_headers(function_no, function_version, caller_system_code)

        logging.info(f"start fetch api results for {function_no}: {url},\n headers: {headers}\n body: {body}")

        return await self.get_info(url, headers, body)

    async def get_info(self, url, headers, body):
        try:
            async with httpx.AsyncClient(headers=headers, timeout=self.call_timeout) as client:
                response = await client.post(url=url, json=body)
                if response.status_code == 200:
                    data = response.json()

                    logging.info(f"get api results: {data}")

                    results = data.get("data", {}).get("Datas") or []
                    return results
                logging.error(response.text)
        except Exception as exp:
            logging.exception(exp)
        return []


if __name__ == "__main__":
    import asyncio

    rsp = asyncio.run(ESBClient().get_sda_info("明世伙伴基金管理（珠海）有限公司"))
    print(rsp)
