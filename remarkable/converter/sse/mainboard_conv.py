import re
from collections import defaultdict
from copy import deepcopy

from remarkable.converter import SSEBaseConverter
from remarkable.converter.utils import (
    chinese_number_convert,
    convert_unit,
    get_currency_unit,
    keep_number_only,
)
from remarkable.plugins.sse.sse_answer_formatter import AnswerItem


class AssetDisposalConverter(SSEBaseConverter):
    """01 资产处置公告"""

    def convert(self, *args, **kwargs):
        path = "（二级）"
        for item in self.answer_in[path].values():
            item["是否构成重大资产重组"] = self.update_text_in_answer(
                item.get("是否构成重大资产重组"), self.convert_enum_value
            )
            item["资产价值"] = self.update_text_in_answer(item.get("资产价值"), convert_unit)
        return self.answer_in


class RegularOperateDataMaterialConverter(SSEBaseConverter):
    """02 定期经营数据-临时公告-原材料"""

    def convert(self, *args, **kwargs):
        for item in self.answer_in["原材料"].values():
            item["同比变动比例（%）"] = self.update_text_in_answer(
                item["同比变动比例（%）"], keep_number_only, attr="同比变动比例（%）"
            )

        return self.answer_in


class RegularOperateDataProductConverter(SSEBaseConverter):
    """02 定期经营数据-临时公告-主要产品"""

    def convert(self, *args, **kwargs):
        for item in self.answer_in["主要产品"].values():
            item["销量"] = self.update_text_in_answer(
                item["销量"], convert_unit, from_unit=item["销量单位"].plain_text, to_unit="吨"
            )
            item["销售收入"] = self.update_text_in_answer(
                item["销售收入"], convert_unit, from_unit=item["销售收入单位"].plain_text, to_unit="万元"
            )
            item["同比变动比例（%）"] = self.update_text_in_answer(
                item["同比变动比例（%）"], keep_number_only, attr="同比变动比例（%）"
            )
            item["平均售价"] = self.update_text_in_answer(
                item["平均售价"], convert_unit, from_unit=item["平均售价单位"].plain_text, to_unit="万元/吨"
            )
            item["产量"] = self.update_text_in_answer(
                item["产量"], convert_unit, from_unit=item["产量单位"].plain_text, to_unit="吨"
            )
            item["上期同期平均售价"] = self.update_text_in_answer(
                item["上期同期平均售价"], convert_unit, from_unit=item["平均售价单位"].plain_text, to_unit="万元/吨"
            )
        return self.answer_in


class CorporationArticlesConverter(SSEBaseConverter):
    """03 公司章程公告-公司章程"""

    def convert(self, *args, **kwargs):
        for path, item in self.answer_in.items():
            self.answer_in[path] = self.update_text_in_answer(item, chinese_number_convert)
        return self.answer_in


class AnnResoluteBoardSupervisonConverter(SSEBaseConverter):
    """
    04 监事会决议公告
        议案名称
        会议名称
        同意
        反对
        弃权
        是否通过
        监事会召开日期
        应到人数
        实到人数
    """

    @staticmethod
    def ensure_vote_result(item):
        vote_result = item.get("是否通过")
        if vote_result and vote_result.value:
            return item
        agree = int(keep_number_only(item.get("同意").plain_text))
        total = int(keep_number_only(item.get("实到人数").plain_text))

        if agree and total:
            result = "是" if 2 * agree > total else "否"
            item["是否通过"] = AnswerItem(None, value=result)
        return item

    def convert(self, *args, **kwargs):
        paths = ["同意", "反对", "弃权"]
        for item in self.answer_in["（二级）"].values():
            for path in paths:
                item[path] = self.update_text_in_answer(item.get(path), keep_number_only)
            item.update(
                {
                    "会议名称": self.answer_in.get("会议名称"),
                    "监事会召开日期": self.answer_in.get("监事会召开日期"),
                    "应到人数": self.answer_in.get("应到人数"),
                    "实到人数": self.answer_in.get("实到人数"),
                }
            )
            self.ensure_vote_result(item)
            item["是否通过"] = self.update_text_in_answer(item["是否通过"], self.convert_enum_value)
        return self.answer_in


class EntrustVoteRightConverter(SSEBaseConverter):
    """06 委托表决权相关公告"""

    def convert(self, *args, **kwargs):
        path_list = ["股份数量", "股份比例"]
        for item in self.answer_in["（二级）"].values():
            for path in path_list:
                item[path] = self.update_text_in_answer(item.get(path), keep_number_only)

        return self.answer_in


class ApplBankrupLiquidateAnnConverter(SSEBaseConverter):
    """08 申请破产清算公告"""

    def convert(self, *args, **kwargs):
        path = "实际控制人或控股股东是否涉及破产清算"
        self.answer_in[path] = self.update_text_in_answer(self.answer_in[path], self.convert_enum_value)
        return self.answer_in


class AnnSaleAssetsConverter(SSEBaseConverter):
    """10 出售资产公告"""

    def convert(self, *args, **kwargs):
        need_convert_value = ["资产总额", "负债总额", "净资产", "营业收入", "净利润"]
        for item in self.answer_in["交易详情"].values():
            from_unit = item.get("单位").plain_text
            kwargs = {"from_unit": from_unit}
            for path in need_convert_value:
                item[path] = self.update_text_in_answer(item.get(path), convert_unit, **kwargs)
            item["单位"] = self.update_text_in_answer(item.get("单位"), get_currency_unit)
        return self.answer_in


class DebtOverdueConverter(SSEBaseConverter):
    """11 债务逾期公告"""

    def convert(self, *args, **kwargs):
        need_convert_value = ["逾期金额（本金）", "逾期金额（欠息）", "累计逾期金额"]
        for item in self.answer_in["（二级）"].values():
            from_unit = item.get("单位").plain_text
            kwargs.update({"from_unit": from_unit})
            for path in need_convert_value:
                item[path] = self.update_text_in_answer(item.get(path), convert_unit, **kwargs)
            item["单位"] = self.update_text_in_answer(item.get("单位"), get_currency_unit)

        return self.answer_in


class RemuDomesticAccountFirmsConverter(SSEBaseConverter):
    """12 境内会计师事务所报酬"""

    def convert(self, *args, **kwargs):
        path = "（二级）"
        new_path_answer = {}
        for ans in self.answer_in[path].values():
            for idx, item in enumerate(ans.get("境内会计师事务所报酬", {}).values()):
                from_unit = item.get("单位").plain_text
                kwargs.update({"from_unit": from_unit})
                item["金额"] = self.update_text_in_answer(item.get("金额"), convert_unit, **kwargs)
                path_answer = deepcopy(ans)
                path_answer["境内会计师事务所报酬-金额"] = item["金额"]
                path_answer["境内会计师事务所报酬-单位"] = item["单位"]
                new_path_answer[idx] = path_answer
        self.answer_in[path] = new_path_answer

        return self.answer_in


class AnnualKeyPollutionDischargeConverter(SSEBaseConverter):
    """14 年报-排污"""

    def convert(self, *args, **kwargs):
        path_need_convert = "是否排污"
        self.answer_in[path_need_convert] = self.convert_enum_value(self.answer_in.get(path_need_convert))

        return self.answer_in


class InterimAnnAdministPenaltyConverter(SSEBaseConverter):
    """15 临时公告-行政处罚"""

    def convert(self, *args, **kwargs):
        need_convert_value = ["处罚金额"]
        for item in self.answer_in["（二级）"].values():
            item["处罚部门"] = self.answer_in.get("处罚部门")
            for path in need_convert_value:
                item[path] = self.update_text_in_answer(item.get(path), convert_unit)

        return self.answer_in


class AssetSeizureFreezeConverter(SSEBaseConverter):
    """21 资产查封冻结公告"""

    def gen_overview_data(self, path="查封/冻结概述", base_key="资产类型") -> defaultdict[str, AnswerItem]:
        enum_values = ("股权", "土地及地上附着物", "银行账户")
        res = defaultdict(dict)
        for item in self.answer_in[path].values():
            enum_value = item[base_key].value
            if enum_value:
                res.setdefault(enum_value, deepcopy(item))
        # 没有对应到(没有明确写明类别)的再分配一次
        for value in enum_values:
            for item in self.answer_in[path].values():
                if not item[base_key].value:
                    res.setdefault(value, deepcopy(item))
                    break
        return res

    @staticmethod
    def fill_in_data(item: dict[str, AnswerItem], ref_map: dict[str, AnswerItem]):
        for key, value in ref_map.items():
            item.setdefault(key, value)

    @staticmethod
    def overwrite_enum_value(item):
        # 用 data 内容覆盖枚举内容
        item.plain_text = item.simple_text(enum=False)

    @staticmethod
    def split_freeze_period(text):
        # 日期拆分成两段
        texts = re.split(r"[-—–]", text, maxsplit=1)
        if len(texts) == 1:
            texts = texts + [""]
        return texts

    def convert(self, *args, **kwargs):
        path = "查封/冻结详情"
        group_base_key = "资产类型"
        overview_data = self.gen_overview_data(base_key=group_base_key)
        for item in self.answer_in[path].values():
            self.fill_in_data(item, overview_data.get(item[group_base_key].value, {}))
            item[group_base_key] = self.update_text_in_answer(
                item.get(group_base_key),
                self.convert_enum_value,
                convert_map={"股权": "1", "土地及地上附着物": "2", "银行账户": "3"},
            )
            item["账面价值"] = self.update_text_in_answer(item.get("账面价值"), convert_unit, from_unit="万元")
            item["被冻结金额或数量"] = self.update_text_in_answer(
                item.get("被冻结金额或数量"), convert_unit, from_unit=item.get("单位").plain_text
            )
            item["变动情况"] = self.update_text_in_answer(
                item.get("变动情况"),
                self.convert_enum_value,
                convert_map={"解除冻结": "1", "新增冻结": "2", "账户资金增加": "3", "账户资金减少": "4"},
            )
            # FIXME: schema 字段类型应该是枚举
            item["是否已解封"] = self.update_text_in_answer(item.get("是否已解封"), self.convert_enum_value)
            item["账号"] = self.update_text_in_answer(item.get("账号"), keep_number_only)
            item["资产账面价值合计"] = self.update_text_in_answer(
                item.get("资产账面价值合计"), convert_unit, from_unit="万元"
            )
            self.overwrite_enum_value(item["公司名称"])
            item["资产账面价值合计占总资产比例"] = self.update_text_in_answer(
                item.get("资产账面价值合计占总资产比例"), keep_number_only
            )
            start_str, end_str = self.split_freeze_period(item.get("冻结期限").plain_text)
            item["冻结期限（开始）"] = AnswerItem(data=[], text=start_str)
            item["冻结期限（结束）"] = AnswerItem(data=[], text=end_str)
        return self.answer_in


class ConcertedActionConverter(SSEBaseConverter):
    """22 一致行动人公告"""

    def convert(self, *args, **kwargs):
        path_list = ["持股比例"]
        for item in self.answer_in["分组"].values():
            for path in path_list:
                item[path] = self.update_text_in_answer(item.get(path), keep_number_only)

        return self.answer_in
