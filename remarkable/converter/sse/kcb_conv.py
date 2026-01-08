from collections import defaultdict
from copy import deepcopy
from functools import reduce

from remarkable.converter import SSEBaseConverter
from remarkable.converter.utils import convert_unit, keep_number_only


class KCBProspectusConverter(SSEBaseConverter):
    """科创板招股说明书信息抽取"""

    def convert(self, *args, **kwargs):
        return self.answer_in


class Kcb1801Converter(SSEBaseConverter):
    """
    1801 回购方案
    """

    def convert(self, *args, **kwargs):
        sub_paths = ["回购价格或价格上限", "回购价格或价格上限单位"]
        self.answer_in["回购价格上限"] = self.combine_sub_items(self.fake_sub_items(self.answer_in, sub_paths))
        sub_paths = ["回购价格或价格下限", "回购价格或价格下限单位"]
        self.answer_in["回购价格下限"] = self.combine_sub_items(self.fake_sub_items(self.answer_in, sub_paths))
        self.answer_in["价格区间"] = self.combine_sub_items(
            self.fake_sub_items(self.answer_in, ["回购价格上限", "回购价格下限"])
        )
        self.answer_in["拟回购股份的用途、数量、占公司总股本的比例、资金总额（提取表格）"] = self.combine_sub_items(
            self.answer_in["（二级）"]
        )
        self.answer_in["回购期限"] = self.combine_sub_items(self.answer_in["回购期限"])
        return self.answer_in


class Kcb2402Converter(SSEBaseConverter):
    """2402 股份被冻结"""

    def convert(self, *args, **kwargs):
        for item in self.answer_in["二级"].values():
            path = "冻结股份数量及占公司总股本比例"
            sub_paths = ["冻结股份数量", "冻结股份数量占公司总股本比例"]
            item[path] = self.combine_sub_items(self.fake_sub_items(item, sub_paths))

            path = "冻结期限"
            sub_paths = ["冻结起始日", "冻结到期日"]
            item[path] = self.combine_sub_items(self.fake_sub_items(item, sub_paths))

            for path in "股份被冻结的影响分析", "公告类型":
                item[path] = self.answer_in[path]
        return self.answer_in


class Kcb0706Converter(SSEBaseConverter):
    """
    0706 科创板上市公司募集资金临时补充流动资金
    """

    def convert(self, *args, **kwargs):
        self.answer_in["募集资金净额"] = self.update_text_in_answer(self.answer_in["募集资金净额"], convert_unit)
        self.answer_in["补充流动资金的金额"] = self.update_text_in_answer(
            self.answer_in["补充流动资金的金额"], convert_unit
        )
        return self.answer_in


class Kcb1402Converter(SSEBaseConverter):
    """
    1402 再融资预案
    todo: 暂无文档
    """

    def convert(self, *args, **kwargs):
        return None


class Kcb2108Converter(SSEBaseConverter):
    """2108 股权激励计划授予"""

    def convert(self, *args, **kwargs):
        self.answer_in["行权价格（期权）"] = self.update_text_in_answer(
            self.answer_in["行权价格（期权）"], convert_unit
        )
        self.answer_in["授予价格（限制性股票）"] = self.update_text_in_answer(
            self.answer_in["授予价格（限制性股票）"], convert_unit
        )
        path = "激励对象名单及授予情况"
        for item in self.answer_in[path].values():
            path = "董事、高管、核心技术人员"
            item[f"子项-{path}"] = self.combine_sub_items(item[path], paths=["姓名", "获授数量"])

            path = "其他人员"
            item[f"子项-{path}"] = self.combine_sub_items(item[path], paths=["获授数量"])

            for path in "董事、高管、核心技术人员", "其他人员", "预留部分":
                item.pop(path, None)
        self.answer_in["激励对象名单及授予情况"] = self.combine_sub_items(self.answer_in["激励对象名单及授予情况"])
        return self.answer_in


class Kcb0426Converter(SSEBaseConverter):
    """
    0426 与私募基金合作投资
    """

    def convert(self, *args, **kwargs):
        self.answer_in["投资金额"] = self.update_text_in_answer(self.answer_in["投资金额"], convert_unit)
        return self.answer_in


class Kcb0601Converter(SSEBaseConverter):
    """0601 年度担保预计"""

    def convert(self, *args, **kwargs):
        for item in self.answer_in["（二级）"].values():
            for path in (
                "上市公司及其控股子公司逾期担保累计金额",
                "上市公司及其控股子公司对外担保总额",
                "上市公司对控股子公司提供的担保总额",
            ):
                item[path] = self.update_text_in_answer(self.answer_in[path], convert_unit)
            item["担保金额"] = self.update_text_in_answer(item["担保金额"], convert_unit)
            for path in (
                "上市公司对控股子公司提供的担保总额占净资产比例",
                "上市公司及其控股子公司对外担保总额占净资产比例",
            ):
                item[path] = self.update_text_in_answer(self.answer_in[path], keep_number_only)
            for path in "被担保人是否是关联方", "关联关系":
                item[path].plain_text = f"{path}: {item[path].plain_text}"
            item["被担保人是否是关联方及关联关系"] = item["被担保人是否是关联方"] + item["关联关系"]
        return self.answer_in


class Kcb0402Converter(SSEBaseConverter):
    """0402 出售资产"""

    _group_base_key = "出售或购买的标的名称"

    def get_transaction_detail(self):
        res = defaultdict(dict)
        for item in self.answer_in["交易详情"].values():
            res.setdefault(item[self._group_base_key].plain_text, item)
        return res

    def fill_in_data(self, item, ref_item):
        likely_key = self.get_most_likely_key(item[self._group_base_key].plain_text, ref_item.keys())
        for key, value in ref_item[likely_key].items():
            item.setdefault(key, value)

    def convert(self, *args, **kwargs):
        transaction_detail = self.get_transaction_detail()
        for item in self.answer_in["交易标的情况"].values():
            self.fill_in_data(item, transaction_detail)
            for path in ("交易事项", "董事会审议反对及弃权情况", "本次交易带来的影响"):
                item[path] = self.answer_in[path]
            item["标的账面价值"] = self.update_text_in_answer(
                item["标的账面价值"], convert_unit, from_unit=item.get("账面价值单位").plain_text
            )
            item["标的评估价值"] = self.update_text_in_answer(
                item.get("被冻结金额或数量"), convert_unit, from_unit=item.get("评估价值单位").plain_text
            )
            item["交易金额"] = self.update_text_in_answer(item.get("交易金额"), convert_unit)
            item["标的增值率"] = self.update_text_in_answer(item.get("标的增值率"), keep_number_only)

        return self.answer_in


class Kcb0806Converter(SSEBaseConverter):
    """0806 业绩快报"""

    def convert(self, *args, **kwargs):
        for item in self.answer_in["业绩快报"].values():
            for path in "增减变动的原因", "业绩快报期间":
                item[path] = self.answer_in[path]
            paths = "主要财务数据和指标名称", "主要财务数据和指标", "主要财务数据和指标单位"
            for path in paths:
                item[path].plain_text = f"{path}: {item[path].plain_text}"
            item["主要财务数据和指标"] = reduce(lambda x, y: x + y, [item[p] for p in paths])
        return self.answer_in


class Kcb1411Converter(SSEBaseConverter):
    """1411 配股发行"""

    def convert(self, *args, **kwargs):
        for path in "发行的每股价格", "本次可认购数量":
            self.answer_in[path] = self.update_text_in_answer(self.answer_in[path], convert_unit)
        return self.answer_in


class Kcb0705Converter(SSEBaseConverter):
    """0705 用募集资金置换预先投入的自筹资金（KCB数据）"""

    def convert(self, *args, **kwargs):
        paths = (
            "用于置换的金额（合计数）",
            "预先支付发行费用金额（总计）",
            "募集资金净额",
            "计划投入募集资金金额",
            "预先投入募投项目金额",
        )
        for path in paths:
            self.answer_in[path] = self.update_text_in_answer(self.answer_in[path], convert_unit)
        for path in "董事会反对情况", "董事会弃权情况":
            self.answer_in[path] = self.combine_sub_items(self.answer_in[path])
        return self.answer_in


class Kcb1301Converter(SSEBaseConverter):
    """1301 减持简式权益变动报告书"""

    def convert(self, *args, **kwargs):
        for item in self.answer_in["二级"].values():
            if not item["减持人/增持人权益变动前后持股情况-变动前持股数量"].is_empty:
                item[
                    "减持人/增持人权益变动前后持股情况-变动前持股数量"
                ].plain_text = f"变动前持股数量: {item['减持人/增持人权益变动前后持股情况-变动前持股数量'].plain_text}"
            if not item["减持人/增持人权益变动前后持股情况-变动前持股比例"].is_empty:
                item[
                    "减持人/增持人权益变动前后持股情况-变动前持股比例"
                ].plain_text = f"变动前持股比例: {item['减持人/增持人权益变动前后持股情况-变动前持股比例'].plain_text}"
            item["减持人/增持人的减持前的持股情况"] = (
                item["减持人/增持人权益变动前后持股情况-变动前持股数量"]
                + item["减持人/增持人权益变动前后持股情况-变动前持股比例"]
            )

            if not item["减持人/增持人权益变动前后持股情况-变动后持股数量"].is_empty:
                item[
                    "减持人/增持人权益变动前后持股情况-变动后持股数量"
                ].plain_text = f"变动后持股数量: {item['减持人/增持人权益变动前后持股情况-变动后持股数量'].plain_text}"
            if not item["减持人/增持人权益变动前后持股情况-变动后持股比例"].is_empty:
                item[
                    "减持人/增持人权益变动前后持股情况-变动后持股比例"
                ].plain_text = f"变动后持股比例: {item['减持人/增持人权益变动前后持股情况-变动后持股比例'].plain_text}"
            item["减持人/增持人的减持后的持股情况"] = (
                item["减持人/增持人权益变动前后持股情况-变动后持股数量"]
                + item["减持人/增持人权益变动前后持股情况-变动后持股比例"]
            )
        return self.answer_in


class Kcb1302Converter(Kcb1301Converter):
    """1302 增持简式权益变动报告书"""


class Kcb1303Converter(Kcb1301Converter):
    """1303 增持详式权益变动报告书"""


class Kcb2130Converter(SSEBaseConverter):
    """2130 员工持股计划草案"""

    def convert(self, *args, **kwargs):
        path = "资金来源及金额"
        self.answer_in[path] = self.combine_sub_items(self.answer_in[path])
        return self.answer_in


class Kcb2604Converter(SSEBaseConverter):
    """2604 计提大额资产减值准备"""

    def convert(self, *args, **kwargs):
        path = "减值情况"
        for item in self.answer_in[path].values():
            item["计提大额资产减值准备金额"] = self.update_text_in_answer(
                item["计提大额资产减值准备金额"], convert_unit, from_unit=item["单位"].plain_text
            )
            item["对当年利润影响数"] = self.update_text_in_answer(self.answer_in["对当年利润影响数"], convert_unit)
        return self.answer_in


class Kcb2619Converter(SSEBaseConverter):
    """2619 获得财政补贴"""

    def convert(self, *args, **kwargs):
        for item in self.answer_in["（二级）"].values():
            item["收到补助的金额"] = item["收到补助的金额"] + item["收到补助的金额单位"]
            item["收到补助的金额"].plain_text = item["收到补助的金额"].plain_text.replace("\n", "")
        return self.answer_in


class Kcb2620Converter(Kcb2619Converter):
    """2620 获得其他补贴"""


class Kcb0708Converter(SSEBaseConverter):
    """0708 募集资金存放与使用情况报告"""

    def convert(self, *args, **kwargs):
        path = "前次募集和本次募集差异情况"
        self.answer_in[path] = self.combine_sub_items(self.answer_in[path])
        for item in self.answer_in["（二级）"].values():
            item[path] = self.answer_in[path]
            for key in "募集资金净额", "募集资金余额":
                item[key] = self.update_text_in_answer(item[key], convert_unit)
            other_item = next(iter(self.answer_in["是否存在变更"].values()), None)
            if other_item:
                item["存在变更的原因和情况"] = other_item["存在变更的原因和情况"]
                item["是否存在"] = other_item["是否存在"]
        return self.answer_in


class Kcb0709Converter(SSEBaseConverter):
    """0709 前次募集资金使用情况报告"""

    def convert(self, *args, **kwargs):
        for path in "募集资金净额", "募集资金余额":
            self.answer_in[path] = self.combine_sub_items(self.answer_in[path])
        return self.answer_in


class Kcb0809Converter(SSEBaseConverter):
    """0809 业绩预告更正"""

    def group_by_path(self, path, base_key):
        res = defaultdict(dict)
        for item in self.answer_in[path].values():
            item = deepcopy(item)
            key = item[base_key].plain_text
            item.pop(base_key, None)
            res.setdefault(key, self.combine_sub_items({0: item}))
        return res

    def convert(self, *args, **kwargs):
        base_key = "业绩预告类别"
        before_content = self.group_by_path("更正前预告内容", base_key)
        after_content = self.group_by_path("更正后预告内容", base_key)
        for item in self.answer_in["更正前预告内容"].values():
            item["更正前预告内容"] = before_content[item[base_key].plain_text]
            item["更正后预告内容"] = after_content[item[base_key].plain_text]
            item["业绩预告区间"] = self.combine_sub_items(self.answer_in["业绩预告区间"])
            item["本期业绩变化的原因"] = self.answer_in["本期业绩变化的原因"]
        return self.answer_in


class Kcb2404Converter(SSEBaseConverter):
    """2404 股份冻结解除"""

    def convert(self, *args, **kwargs):
        for item in self.answer_in["二级"].values():
            path = "被解冻人持有上市公司股份总数以及占公司总股本比例"
            sub_paths = ["被解冻人持有上市公司股份总数", "被解冻人持有上市公司股份总数占公司总股本比例"]
            item[path] = self.combine_sub_items(self.fake_sub_items(item, sub_paths))

            path = "本次解冻后剩余被被冻结股份数量以及占其持股总数、公司总股本比例"
            sub_paths = [
                "本次解冻后剩余被冻结股份数量",
                "本次解冻后剩余被冻结股份数量占其持股总数比例",
                "本次解冻后剩余被冻结股份数量占公司总股本比例",
            ]
            item[path] = self.combine_sub_items(self.fake_sub_items(item, sub_paths))

            path = "解冻股份数量及占公司总股本比例"
            sub_paths = ["解冻股份数量", "解冻股份数量占公司总股本比例"]
            item[path] = self.combine_sub_items(self.fake_sub_items(item, sub_paths))
        return self.answer_in


class Kcb2601Converter(SSEBaseConverter):
    """2601 重大亏损或重大损失"""

    def convert(self, *args, **kwargs):
        self.answer_in["金额"] = self.update_text_in_answer(self.answer_in["金额"], convert_unit)
        return self.answer_in


class Kcb2710Converter(SSEBaseConverter):
    """2710 变更会计政策或者会计估计"""

    def convert(self, *args, **kwargs):
        path = "是否需要追溯调整"
        item = next(iter(self.answer_in[path].values()), None)
        if not item:
            return None
        self.answer_in["收入是否调整"] = item["收入是否调整"]
        self.answer_in["净利润是否调整"] = item["净利润是否调整"]
        self.answer_in[path] = self.combine_sub_items(self.answer_in[path])
        return self.answer_in


class Kcb2403Converter(SSEBaseConverter):
    """2403 股份质押解除"""

    def convert(self, *args, **kwargs):
        path = "二级"
        for item in self.answer_in[path].values():
            item["公告类型"] = self.answer_in["公告类型"]
            key = "本次解质后剩余被质押股份数量以及占其持股总数、公司总股本比例"
            sub_paths = [
                "本次解质后剩余被质押股份数量",
                "本次解质后剩余被质押股份数量占其持股总数比例",
                "本次解质后剩余被质押股份数量占公司总股本比例",
            ]
            item[key] = self.combine_sub_items(self.fake_sub_items(item, sub_paths))
            keys = ["本次解质股份数量占公司总股本比例", "原出质人持有上市公司股份总数占公司总股本比例"]
            for key in keys:
                item[key] = self.update_text_in_answer(item[key], keep_number_only)
        return self.answer_in


class Kcb0901Converter(SSEBaseConverter):
    """0901 实施利润分配和资本公积金转增"""

    def convert(self, *args, **kwargs):
        path = "利润分配发放年度及发放名称"
        self.answer_in[path] = self.combine_sub_items(self.answer_in[path])
        return self.answer_in


class Kcb1213Converter(SSEBaseConverter):
    """1213 因股东披露权益变动报告书或收购报告书的提示"""

    def convert(self, *args, **kwargs):
        path = "二级"
        for item in self.answer_in[path].values():
            for path in "变动后股份数量占比", "变动前股份占比":
                item[path] = self.update_text_in_answer(item[path], keep_number_only)
            for path in "变动是否使公司控股股东及实际控制人发生变化", "是否触及要约收购", "增持或减持":
                item[path] = self.answer_in[path]
        return self.answer_in


class Kcb1214Converter(SSEBaseConverter):
    """1214 控股股东或实际控制人发生变动的提示"""

    def convert(self, *args, **kwargs):
        path = "二级"
        for item in self.answer_in[path].values():
            for path in "变动是否使公司控股股东及实际控制人发生变化", "是否触及要约收购", "增持或减持":
                item[path] = self.answer_in[path]

            path = "变动前股份数量"
            sub_paths = ["变动前股份数量", "变动前股份数量单位"]
            item[path] = self.combine_sub_items(self.fake_sub_items(item, sub_paths))

            path = "变动后股份数量"
            sub_paths = ["变动后股份数量", "变动后股份数量单位"]
            item[path] = self.combine_sub_items(self.fake_sub_items(item, sub_paths))
        return self.answer_in


class Kcb0501Converter(SSEBaseConverter):
    """0501 日常关联交易"""

    def group_by_path(self, path, base_key):
        res = defaultdict(dict)
        for item in self.answer_in[path].values():
            res.setdefault(item[base_key].plain_text, item)
        return res

    def fill_in_data(self, item, ref_item, base_key):
        likely_key = self.get_most_likely_key(item[base_key].plain_text, ref_item.keys())
        for key, value in ref_item[likely_key].values():
            item.setdefault(key, value)

    def convert(self, *args, **kwargs):
        base_key = "关联方名称"
        daily_trans = self.group_by_path("本次日常关联交易", base_key)
        last_daily_trans = self.group_by_path("前次日常关联交易", base_key)
        for item in self.answer_in["（二级）"].values():
            for trans in daily_trans, last_daily_trans:
                self.fill_in_data(item, trans, base_key)
            for path in ("日常关联交易对上市公司的影响", "审议程序", "董事会投票情况"):
                item[path] = self.answer_in[path]
            item["本次日常关联交易预计金额"] = self.update_text_in_answer(
                item["本次日常关联交易预计金额"],
                convert_unit,
                from_unit=item.get("本次日常关联交易预计金额单位").plain_text,
            )
        return self.answer_in


class Kcb1220Converter(SSEBaseConverter):
    """1220 股东减持计划"""

    def convert(self, *args, **kwargs):
        for item in self.answer_in["（二级）"].values():
            for path in "价格", "数量", "金额":
                paths = (f"{path}（下限）", f"{path}（上限）")
                item[f"{path}上下限"] = self.combine_sub_items(self.fake_sub_items(item, paths))
            paths = ["本次减持前持股数量", "本次减持前持股比例"]
            item["本次减持前持股数量、持股比例"] = self.combine_sub_items(self.fake_sub_items(item, paths))
        return self.answer_in


class Kcb0405Converter(SSEBaseConverter):
    """0405 委托贷款"""

    def convert(self, *args, **kwargs):
        for item in self.answer_in["（二级）"].values():
            item["投资金额"] = self.update_text_in_answer(item["投资金额"], convert_unit)
        return self.answer_in


class Kcb0406Converter(SSEBaseConverter):
    """0406 提供财务资助"""

    def convert(self, *args, **kwargs):
        for item in self.answer_in["（二级）"].values():
            item["投资金额"] = self.update_text_in_answer(item["投资金额"], convert_unit)
            path = "董事会审议否决及弃权情况"
            item[path] = self.combine_sub_items(item[path])
        return self.answer_in


class Kcb0419Converter(SSEBaseConverter):
    """0419 签订日常经营合同"""

    def convert(self, *args, **kwargs):
        for item in self.answer_in["（二级）"].values():
            item["合同金额"] = self.update_text_in_answer(item["合同金额"], convert_unit)

            for path in "合同标的情况", "董事会反对及弃权情况":
                item[path] = self.combine_sub_items(item[path])

            new_path = "合同对方是否为关联方及其关联关系"
            sub_paths = ["合同对方是否为关联方", "关联关系"]
            item[new_path] = self.combine_sub_items(self.fake_sub_items(item, sub_paths))
        return self.answer_in


class Kcb0421Converter(SSEBaseConverter):
    """0421 新建项目"""

    def convert(self, *args, **kwargs):
        for item in self.answer_in["（二级）"].values():
            item["投资金额"] = self.update_text_in_answer(item["投资金额"], convert_unit)

            path = "董事会审议否决及弃权情况"
            item[path] = self.combine_sub_items(item[path])
        return self.answer_in


class Kcb0502Converter(SSEBaseConverter):
    """0502 向关联人提供担保或反担保"""

    def convert(self, *args, **kwargs):
        for item in self.answer_in["（二级）"].values():
            paths = ["上市公司对控股子公司提供的担保总额占净资产比例", "上市公司及其控股子公司对外担保总额占净资产比例"]
            for path in paths:
                item[path] = self.update_text_in_answer(self.answer_in[path], keep_number_only)

            paths = [
                "上市公司及其控股子公司逾期担保累计金额",
                "上市公司及其控股子公司对外担保总额",
                "上市公司对控股子公司提供的担保总额",
            ]
            for path in paths:
                item[path] = self.update_text_in_answer(self.answer_in[path], convert_unit)

            item["担保金额"] = self.update_text_in_answer(item["担保金额"], convert_unit)
            new_path = "被担保人是否是关联方及关联关系"
            sub_paths = ["被担保人是否是关联方", "关联关系"]
            item[new_path] = self.combine_sub_items(self.fake_sub_items(item, sub_paths))
        return self.answer_in


class Kcb0509Converter(SSEBaseConverter):
    """0509\t接受关联人财务资助"""

    def convert(self, *args, **kwargs):
        for item in self.answer_in["（二级）"].values():
            paths = ["交易金额", "标的的评估值", "标的的账面价值"]
            for path in paths:
                item[path] = self.update_text_in_answer(item[path], convert_unit)
        return self.answer_in


class Kcb0512Converter(Kcb0509Converter):
    """0512 委托关联人管理资产和业务"""


class Kcb0527Converter(Kcb0509Converter):
    """0527\t与关联人财务公司的交易"""


class Kcb0528Converter(SSEBaseConverter):
    """0528 关联交易的提示"""

    def convert(self, *args, **kwargs):
        for item in self.answer_in["（二级）"].values():
            paths = ["交易金额", "标的的评估值", "标的的账面价值"]
            for path in paths:
                item[path] = self.update_text_in_answer(item[path], convert_unit)

            sub_paths = ["交易标的名称（key）", "交易标的名称（补充）"]
            item["交易标的名称"] = self.combine_sub_items(self.fake_sub_items(item, sub_paths))
        return self.answer_in


class Kcb0529Converter(Kcb0528Converter):
    """0529 关联交易的进展"""


class Kcb0530Converter(Kcb0528Converter):
    """0530 关联交易的完成"""


class Kcb0602Converter(SSEBaseConverter):
    """0602\t为控股子公司提供担保"""

    def convert(self, *args, **kwargs):
        for item in self.answer_in["（二级）"].values():
            path = "上市公司及其控股子公司对外担保总额"
            item[path] = self.update_text_in_answer(self.answer_in[path], convert_unit)

            # NOTE: schema 有问题, '数字'其实应该是'单位'
            for path in "上市公司及其控股子公司逾期担保累计金额", "上市公司对控股子公司提供的担保总额":
                item[path] = self.combine_sub_items(self.answer_in[path])

            item["担保金额"] = self.update_text_in_answer(item["担保金额"], convert_unit)
            for path in (
                "上市公司对控股子公司提供的担保总额占净资产比例",
                "上市公司及其控股子公司对外担保总额占净资产比例",
            ):
                item[path] = self.update_text_in_answer(self.answer_in[path], keep_number_only)
        return self.answer_in


class Kcb0603Converter(SSEBaseConverter):
    """0603\t其他对外担保"""

    def convert(self, *args, **kwargs):
        for item in self.answer_in["（二级）"].values():
            paths = [
                "上市公司及其控股子公司逾期担保累计金额",
                "上市公司及其控股子公司对外担保总额",
                "上市公司对控股子公司提供的担保总额",
            ]
            for path in paths:
                item[path] = self.update_text_in_answer(self.answer_in[path], convert_unit)
            item["担保金额"] = self.update_text_in_answer(item["担保金额"], convert_unit)
            for path in (
                "上市公司对控股子公司提供的担保总额占净资产比例",
                "上市公司及其控股子公司对外担保总额占净资产比例",
            ):
                item[path] = self.update_text_in_answer(self.answer_in[path], keep_number_only)
        return self.answer_in


class Kcb0604Converter(Kcb0603Converter):
    """0604 提供反担保"""


class Kcb1221Converter(SSEBaseConverter):
    """1221 股东减持进展"""

    def convert(self, *args, **kwargs):
        for item in self.answer_in["（二级）"].values():
            paths = ["本次已减持的股份数量", "减持主体目前持股数量", "本次已减持金额"]
            for path in paths:
                item[path] = self.update_text_in_answer(item[path], convert_unit)

            paths = ["本次已减持持股比例", "减持主体目前持股比例"]
            for path in paths:
                item[path] = self.update_text_in_answer(item[path], keep_number_only)

            path = "本次减持前减持主体持股数量、持股比例"
            sub_paths = ["本次减持前持股数量", "本次减持前持股比例"]
            item[path] = self.combine_sub_items(self.fake_sub_items(item, sub_paths))
        return self.answer_in


class Kcb1222Converter(SSEBaseConverter):
    """1222 股东增持计划"""

    def convert(self, *args, **kwargs):
        for item in self.answer_in["（二级）"].values():
            for path in "价格", "数量", "金额":
                paths = (f"{path}（下限）", f"{path}（上限）")
                item[f"{path}上下限"] = self.combine_sub_items(self.fake_sub_items(item, paths))
            paths = ["增持主体本次增持前已持有股份的数量", "增持主体本次增持前持股比例"]
            item["增持主体本次增持前已持有股份的数量、持股比例"] = self.combine_sub_items(
                self.fake_sub_items(item, paths)
            )
        return self.answer_in


class Kcb1223Converter(SSEBaseConverter):
    """1223 股东增持进展"""

    def convert(self, *args, **kwargs):
        for item in self.answer_in["（二级）"].values():
            paths = ["本次已增持的股份数量", "增持主体目前持股数量", "本次已增持金额"]
            for path in paths:
                item[path] = self.update_text_in_answer(item[path], convert_unit)

            paths = ["本次已增持持股比例", "增持主体目前持股比例"]
            for path in paths:
                item[path] = self.update_text_in_answer(item[path], keep_number_only)

            path = "本次增持前增持主体持股数量、持股比例"
            sub_paths = ["增持主体增持前已持有股份的数量", "增持主体增持前持股比例"]
            item[path] = self.combine_sub_items(self.fake_sub_items(item, sub_paths))
        return self.answer_in


class Kcb1809Converter(SSEBaseConverter):
    """1809 回购实施结果暨股份变动"""

    def convert(self, *args, **kwargs):
        path = "实际回购股份数量占公司比例"
        self.answer_in[path] = self.update_text_in_answer(self.answer_in[path], keep_number_only)
        path = "计划与实际执行情况对比"
        self.answer_in[path] = self.combine_sub_items(self.answer_in[path])
        return self.answer_in


class Kcb1224Converter(SSEBaseConverter):
    """1224 股东增持计划完成"""

    def convert(self, *args, **kwargs):
        for item in self.answer_in["（二级）"].values():
            paths = ["本次实际增持股份数量", "本次实际增持金额"]
            for path in paths:
                item[path] = self.update_text_in_answer(item[path], convert_unit)

            paths = ["本次实际增持股份比例", "增持主体本次增持后的实际持股比例"]
            for path in paths:
                item[path] = self.update_text_in_answer(item[path], keep_number_only)

            path = "增持主体本次增持前已持有股份的数量、持股比例"
            sub_paths = ["增持主体本次增持前已持有股份的数量", "增持主体本次增持前持股比例"]
            item[path] = self.combine_sub_items(self.fake_sub_items(item, sub_paths))
        return self.answer_in


class Kcb0504Converter(SSEBaseConverter):
    """0504 向关联人出售资产"""

    def convert(self, *args, **kwargs):
        for item in self.answer_in["（二级）"].values():
            paths = ["交易金额", "标的评估值", "标的的账面价值"]
            for path in paths:
                item[path] = self.update_text_in_answer(item[path], convert_unit)

            path = "出售或购买的标的名称"
            sub_paths = ["出售或购买的标的名称（key）", "出售或购买的标的名称（补充）"]
            item[path] = self.combine_sub_items(self.fake_sub_items(item, sub_paths))

            path = "董事会审议反对及弃权情况"
            item[path] = self.combine_sub_items(item[path])
        return self.answer_in


class Kcb1921Converter(SSEBaseConverter):
    """1921 可转债募集说明书摘要"""

    def convert(self, *args, **kwargs):
        paths = ["可转债发行的金额", "初始转股价", "可转债面值"]
        for path in paths:
            self.answer_in[path] = self.update_text_in_answer(self.answer_in[path], convert_unit)
        return self.answer_in


class Kcb2101Converter(SSEBaseConverter):
    """2101 股权激励计划草案摘要"""

    def convert(self, *args, **kwargs):
        paths = ["股权激励占比（占公司股本总额比例）"]
        for path in paths:
            self.answer_in[path] = self.update_text_in_answer(self.answer_in[path], keep_number_only)

        path = "股票授予价格"
        sub_paths = ["普通限制性股票授予价格", "股票期权行权价格", "限制性股票单元授予价格"]
        self.answer_in[path] = self.combine_sub_items(self.fake_sub_items(self.answer_in, sub_paths))

        path = "股票授予价格确定方法"
        sub_paths = ["普通限制性股票授予价格确定方法", "股票期权行权价格的确定方法", "限制性股票单元授予价格确定方法"]
        self.answer_in[path] = self.combine_sub_items(self.fake_sub_items(self.answer_in, sub_paths))

        path = "股票授予条件"
        sub_paths = ["普通限制性股票授予条件", "股票期权授予条件", "限制性股票单元授予条件"]
        self.answer_in[path] = self.combine_sub_items(self.fake_sub_items(self.answer_in, sub_paths))
        return self.answer_in


class Kcb0503Converter(Kcb0504Converter):
    """0503 向关联人购买资产"""


class Kcb1805Converter(SSEBaseConverter):
    """1805 回购实施进展"""

    def convert(self, *args, **kwargs):
        paths = ["已实际回购股份数量占公司总股本的比例", "已实际回购股份数量占回购规模下限的比例"]
        for path in paths:
            self.answer_in[path] = self.update_text_in_answer(self.answer_in[path], keep_number_only)

        path = "购买支付的金额"
        self.answer_in[path] = self.answer_in[path] + self.answer_in[f"{path}单位"]
        self.answer_in[path] = self.update_text_in_answer(self.answer_in[path], convert_unit)

        paths = ["购买的最高价", "购买的最低价"]
        for path in paths:
            self.answer_in[path] = self.answer_in[path] + self.answer_in[f"{path}单位"]
        path = "价格区间"
        self.answer_in[path] = self.combine_sub_items(self.fake_sub_items(self.answer_in, paths))

        path = "回购期限"
        self.answer_in[path] = self.combine_sub_items(self.answer_in[path])

        path = "拟回购股份的数量"
        self.answer_in[path] = self.answer_in[path] + self.answer_in[f"{path}单位"]
        path = "拟回购股份资金总额"
        self.answer_in[path] = self.combine_sub_items(self.answer_in[path])
        path = "拟回购股份的用途、数量、占公司总股本的比例、资金总额（提取表格）"
        sub_paths = ["拟回购股份的用途", "拟回购股份的数量", "拟回购股份占公司总股本的比例", "拟回购股份资金总额"]
        self.answer_in[path] = self.combine_sub_items(self.fake_sub_items(self.answer_in, sub_paths))
        return self.answer_in


class Kcb0401Converter(Kcb0504Converter):
    """0401 购买资产"""


class Kcb0702Converter(SSEBaseConverter):
    """0702 超募资金/结余募集资金的使用（KCB数据）"""

    def convert(self, *args, **kwargs):
        paths = ["董事会反对情况", "董事会弃权情况"]
        for path in paths:
            self.answer_in[path] = self.combine_sub_items(self.answer_in[path])

        paths = ["本次使用占超募资金的比例"]
        for path in paths:
            self.answer_in[path] = self.update_text_in_answer(self.answer_in[path], keep_number_only)

        paths = ["计划投入募集资金金额"]
        for path in paths:
            self.answer_in[path] = self.update_text_in_answer(self.answer_in[path], convert_unit)
        return self.answer_in


class Kcb2401Converter(SSEBaseConverter):
    """2401 股份被质押"""

    def convert(self, *args, **kwargs):
        for item in self.answer_in["二级"].values():
            path = "质押期限"
            sub_paths = ["质押起始日", "质押到期日"]
            item[path] = self.combine_sub_items(self.fake_sub_items(item, sub_paths))

            paths = ["本次质押后累计质押股份数量占公司总股本的比例", "本次质押后累计质押股份数量占其持股总数的比例"]
            for path in paths:
                item[path] = self.update_text_in_answer(item[path], keep_number_only)

            path = "可能被平仓的股份数比例"
            item[path] = self.update_text_in_answer(self.answer_in[path], keep_number_only)

            paths = [
                "股份质押对上市公司控制权和日常经营的影响",
                "是否属于控股股东及其一致行动人质押股份占其所持股份的比例达到80%以上的情况",
                "是否属于控股股东及其一致行动人质押股份出现平仓风险",
                "是否属于控股股东及其一致行动人质押股份占其所持股份的比例达到50%以上的情况",
                "是否属于控股股东及其一致行动人质押股份占其所持股份的比例达到50%以上，且出现债务逾期或其他资信恶化情形",
                "可能被平仓的股份数量",
                "平仓风险的化解措施",
            ]
            for path in paths:
                item[path] = self.answer_in[path]

            paths = ["质押股份数量", "出质人持有上市公司股份总数", "本次质押后累计质押股份数量"]
            for path in paths:
                item[path] = self.update_text_in_answer(self.combine_sub_items(item[path], kv_fmt=False), convert_unit)

            path = "质押股份数量以及占公司总股本比例"
            sub_paths = ["质押股份数量", "质押股份数量占公司总股本比例"]
            item[path] = self.combine_sub_items(self.fake_sub_items(item, sub_paths))

            path = "出质人持有上市公司股份总数以及占公司总股本比例"
            sub_paths = ["出质人持有上市公司股份总数", "出质人持有上市公司股份总数占公司总股本比例"]
            item[path] = self.combine_sub_items(self.fake_sub_items(item, sub_paths))
        return self.answer_in


class Kcb0902Converter(SSEBaseConverter):
    """0902 董事会审议高送转"""

    def convert(self, *args, **kwargs):
        for path in "利润分配或公积金转增股本的具体比例", "持股比例":
            self.answer_in[path] = self.update_text_in_answer(self.answer_in[path], keep_number_only)
        return self.answer_in


class Kcb0403Converter(SSEBaseConverter):
    """0403 对外投资"""

    def convert(self, *args, **kwargs):
        for item in self.answer_in["（二级）"].values():
            paths = ["投资金额"]
            for path in paths:
                item[path] = self.update_text_in_answer(item[path], convert_unit)

            path = "董事会审议否决及弃权情况"
            item[path] = self.combine_sub_items(item[path])
        return self.answer_in


class Kcb0404Converter(SSEBaseConverter):
    """0404 委托理财"""

    def convert(self, *args, **kwargs):
        for item in self.answer_in["（二级）"].values():
            path = "董事会审议否决及弃权情况"
            item[path] = self.combine_sub_items(item[path])
        return self.answer_in


class Kcb0508Converter(SSEBaseConverter):
    """0508 向关联人提供财务资助"""

    def convert(self, *args, **kwargs):
        for item in self.answer_in["（二级）"].values():
            paths = ["投资金额"]
            for path in paths:
                item[path] = self.update_text_in_answer(item[path], convert_unit)
        return self.answer_in


class Kcb0505Converter(Kcb0403Converter):
    """0505 与关联人共同投资"""


class Kcb0506Converter(Kcb0403Converter):
    """0506 向关联人委托理财"""


class Kcb0507Converter(Kcb0403Converter):
    """0507 向关联人委托贷款"""
