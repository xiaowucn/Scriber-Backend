import re

from remarkable.common.util import clean_txt, group_cells


class FinancialAttribute:
    # (?P < target >.{2, 5}\s * [1 - 9]\d * (\.\d * | 0\.\d * [1 - 9]\d *)? % \s * 的?股权)
    P_TARGET_STRIP = re.compile(r"([\s\d.%]+)?的?股?权?份$")
    P_TARGET_SYL_L1_4 = re.compile(r"(?:标的|置入)(?:资产|公司)?(?:基本)?(?:情况|概况)")
    P_TARGET_SYL_L1_10 = re.compile(r"(?:财务|会计).{0,4}?$")
    P_TARGET_SYL_LN = re.compile(r"(?:财务|资产)(?:数据|指标|情况|状况|概况)")
    P_PASS_SYL = re.compile(r"(下属|子公司|[参控]股)")

    CLEAN_ATTR_PATTERN = re.compile(
        r"(?:[(（].*[)）])|(?:\n)|(?:(?<![:：])\s)|(?:^[(（]?[一二三四五六七八九十\d]+[)）.,:、，：]+)|(?:[╱]?[(（](?!含|不含|母公司|少数).*[)）]$)|(?:—)|(?:项目)",
        re.S,
    )
    CLEAN_ATTR_SUM_PATTERN = re.compile(r"(?:[合总小]计$)|(?:[总净]额$)", re.S)
    CLEAN_OVERDRIVE_ATTR_PATTERN = re.compile(r"^[其中加减：:]+[：:]+\s*|[、\+\-\*\/△]+")
    FINANCIAL_TABLE_PATTERN = [
        re.compile(r"(合并)?资产负债表$"),
        re.compile(r"(合并)?利润表$"),
        re.compile(r"(合并)?现金流量表$"),
    ]

    TARGET_ATTRS = {
        "其他应收款": [re.compile(r"^其[他它]应收账?款项?$")],
        "净利润": [re.compile(r"^净利润?$"), re.compile(r"^溢利$")],
        "净资产": [
            re.compile(r"^净资产额?$|^资产净值$"),
            re.compile(r"^(所有者|股东)权益([总合][计额])$"),
            re.compile(r"^(所有者|股东)权益$"),
        ],
        "存货周转率": [re.compile(r"^存货的?周转(率|次数)$")],
        "存货金额": [re.compile(r"^存货(金额)?$")],
        "应收票据": [re.compile(r"^应收票据$")],
        "应收账款": [re.compile(r"^应收[账帐]?款$")],
        "毛利率": [
            re.compile(r"^综合毛利润?率$"),
            re.compile(r"^毛利润?率$"),
            re.compile(r"^销售毛利润?率$"),
            re.compile(r"^[合总]计$"),  # todo：table_title
            re.compile(r"^小计$"),
            re.compile(r"^主营业务毛利润?率$"),
        ],
        "流动资产合计": [re.compile(r"^流动资产[合总]计$"), re.compile(r"^流动资产$")],
        "管理费用": [re.compile(r"^管理费用?$")],
        "经营活动现金流量净额": [
            re.compile(r"^经营性?(活动)?(.*)?的?净?现金(流[量|入]?)?净(额|流[量|入]?)$"),
            re.compile(r"^经营性?(活动)?(.*)?的?净?现金流[量|入]?$"),
        ],
        "营业利润": [re.compile(r"^营业总?利润$")],
        "营业成本": [re.compile(r"^营业(成本|支出)$"), re.compile(r"^营业总(成本|支出)$")],
        "营业收入": [re.compile(r"^[运经]?营业?收入?额?$"), re.compile(r"^[运经]?营业?总收入?额?$")],
        "资产减值损失": [re.compile(r"^资产减值损失$"), re.compile(r"^计提资产减值损失$")],
        "资产负债率": [re.compile(r"^(资产)?负债比?[率例]$")],
        "销售费用": [re.compile(r"^销售费用$")],
        "非经常性损益": [
            re.compile(r"^归属于?母?公司(普通股)?(所有者|股东)?的?非经常性损益净额$"),
            re.compile(r"^归属于?母?公司(普通股)?(所有者|股东)?的?非经常性损益(合计|总额|总计)$"),
            re.compile(r"^归属于?母?公司(普通股)?(所有者|股东)?的?非经常性损益$"),
            re.compile(r"^非经常性损益净额$"),
            re.compile(r"^非经常性损益(合计|总额|总计)$"),
            re.compile(r"^[合总]计$"),  # todo：table_title
            re.compile(r"^小计$"),
            re.compile(r"^非经常性损益$"),
        ],
        "预付账款": [re.compile(r"^预付[账帐]?款项?$"), re.compile(r"^总预付[账帐]?款项?$")],
    }

    def __init__(self, reader, **kwargs):
        self.reader = reader
        self.clean_target_attrs = {attr: self.clean_attr(attr, overdrive=True) for attr in self.TARGET_ATTRS}
        self.options = kwargs
        self.b_multi_target = len(kwargs.get("target_maps", {})) > 1
        for target_name in kwargs.get("target_maps", {}):  # 毛利率表格中只出现标的名
            self.TARGET_ATTRS["毛利率"].append(re.compile(r"^%s(毛利润?率)?$" % target_name))

    def get_target_attributes(self, target):
        target = self.target_name(target)
        tables = self.find_target_tables(target)
        attributes = {}
        for table in tables:
            table_attrs = self.table_attrs(table)
            # print('target_table', table['page'], table_attrs)
            for attr in self.TARGET_ATTRS:
                clean_attr = self.clean_target_attrs.get(attr, attr)
                if attr not in attributes:
                    idx, cell = self.find_cell_by_attr(table, table_attrs, clean_attr)
                    if cell is not None:
                        attributes[attr] = (table, idx, cell)
        for attr in self.TARGET_ATTRS:
            if attr not in attributes:
                attributes[attr] = None
        return attributes

    def get_target_attribute(self, target, attribute):
        target = self.target_name(target)
        tables = self.find_target_tables(target)
        clean_attr = self.clean_attr(attribute, overdrive=True)
        for table in tables:
            table_attrs = self.table_attrs(table)
            idx, cell = self.find_cell_by_attr(table, table_attrs, clean_attr)
            if cell is not None:
                return (table, idx, cell)
        return None

    @classmethod
    def target_name(cls, target):
        return cls.P_TARGET_STRIP.sub("", target)

    def find_target_tables(self, target, target_required=False):
        tables = []
        for syl in self.find_target_syllabus_4(target, target_required):
            # print('find_target_syllabus_4', syl)
            tables.extend(self.find_tables_by_syllabus(syl))
        for syl in self.find_target_syllabus_10(target):
            # print('find_target_syllabus_10', syl)
            tables.extend(self.find_tables_by_syllabus(syl))
        return tables

    def find_target_syllabus_4(self, target, target_required=False):
        syl_dict = self.reader.syllabus_dict
        syl_1 = None
        for _, syl in sorted(syl_dict.items(), key=lambda x: x[0]):
            if syl["level"] <= 1 and self.P_TARGET_SYL_L1_4.search(clean_txt(syl["title"])) is not None:
                syl_1 = syl
                break

        if syl_1 is None:
            return []

        def match_syl(syl, target_match, pos_match, matched):
            target_match_ys, pos_match_ys = target_match, pos_match
            for child in [syl_dict.get(idx) for idx in syl.get("children", [])]:
                child_title = clean_txt(child["title"])
                if self.P_PASS_SYL.search(child_title):
                    continue
                target_match = target_match_ys or target in child_title
                pos_match = pos_match_ys or self.P_TARGET_SYL_LN.search(child_title) is not None
                if target_match and pos_match and self.find_tables_by_syllabus(child):
                    matched.append(child)
                    continue
                match_syl(child, target_match, pos_match, matched)
                target_match, pos_match = target_match_ys, pos_match_ys

        matches = []
        target_match = not self.b_multi_target
        match_syl(syl_1, target_match, False, matches)
        if not matches and not target_required:
            match_syl(syl_1, True, False, matches)
        return matches or [syl_1]

    def find_target_syllabus_10(self, target):
        syl_dict = self.reader.syllabus_dict
        syl_1 = None
        for _, syl in sorted(syl_dict.items(), key=lambda x: x[0]):
            if syl["level"] <= 1 and self.P_TARGET_SYL_L1_10.search(clean_txt(syl["title"])) is not None:
                syl_1 = syl
                break

        if syl_1 is None:
            return []

        def match_syl(syl, matches, match_fun, positive_match):
            negative_match = False
            for child in [syl_dict.get(idx) for idx in syl.get("children", [])]:
                child_title = clean_txt(child["title"])
                if len(child_title) >= 30:
                    continue
                if match_fun(target, child_title) and self.find_tables_by_syllabus(child):
                    if positive_match:
                        matches.append(child)
                    else:
                        negative_match = True
                        continue
                else:
                    if not match_syl(child, matches, match_fun, positive_match) and not positive_match:
                        matches.append(child)
                        for i in [syl_dict.get(idx) for idx in child.get("children", [])]:
                            if i in matches:
                                matches.remove(i)
            return negative_match

        matches = []
        match_syl(syl_1, matches, lambda x, y: x in y, True)
        if not matches:
            match_syl(syl_1, matches, lambda x, y: "上市" in y, False)
        return matches

    def find_tables_by_syllabus(self, syllabus):
        tables = []
        if syllabus is None:
            return tables
        start, end = syllabus["range"]
        for tbl in self.reader.tables:
            if start <= tbl.get("index", -1000) < end:
                tables.append(tbl)
        return tables

    def table_attrs(self, table, overdrive=True, cleansum=True):
        attrs = {}
        cells_by_row, cells_by_col = group_cells(table["cells"])
        attr_cells = {
            self.clean_attr(cell["text"], overdrive=overdrive, cleansum=cleansum): row
            for row, cell in cells_by_col.get("0", {}).items()
            if row != "0"
        }  # 取第一列

        for fin_attr, alias_l in self.TARGET_ATTRS.items():
            for pattern in alias_l:  # 别名优先级
                for cell_attr, row in attr_cells.items():
                    if cell_attr and pattern.search(cell_attr):
                        attrs.setdefault(fin_attr, []).append(row)
        return attrs

    def find_cell_by_attr(self, table, attrs, attr):
        row = attrs.get(attr)
        if row is None:
            return None, None
        for col in range(1, len(table["grid"]["columns"]) + 1):
            cell = table["cells"].get("{}_{}".format(row, col))
            if not cell:
                continue
            return "{}_{}".format(row, col), cell
        return None, None

    @classmethod
    def clean_attr(cls, attr, overdrive=False, cleansum=True):
        attr = cls.CLEAN_ATTR_PATTERN.sub("", attr.strip())
        if cleansum:
            attr = cls.CLEAN_ATTR_SUM_PATTERN.sub("", attr)
        if overdrive:
            attr = cls.CLEAN_OVERDRIVE_ATTR_PATTERN.sub("", attr)
        return attr


# if __name__ == '__main__':
#     import sys
#     from remarkable.pdfinsight.reader import PdfinsightReader

#     path = sys.argv[1]
#     reader = PdfinsightReader(path)
#     target = ''
#     attrs = FinancialAttribute(reader).get_target_attributes(target)
#     for attr, item in attrs.items():
#         if not item:
#             continue
#         (table, idx, cell) = item
#         print(attr, table['page'], table['index'], idx, cell['text'])
# print(FinancialAttribute.target_name('星海电子10.0%的股份'))
