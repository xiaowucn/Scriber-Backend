import re

from remarkable.prompter.impl.manual import ManualAnswerPrompter


class SSEManualCrudeAnswerPrompter(ManualAnswerPrompter):
    def __init__(self, schema_id):
        super(SSEManualCrudeAnswerPrompter, self).__init__(schema_id)
        self.element_finder.update(
            {
                "发行人情况-": self.issuer_info,
                "中介机构-": self.agency_info,
                "发行情况-": self.issue_detail,
                "财务数据-": self.financial_info,
                "主要财务数据和财务指标": self.financial_info,
                "上市标准-": self.listing_info,
                "保荐人-": self.sponsor_info,
                "实际控制人-": self.actual_controller,
                "持股": self.shareholder,
                "前十名股东": self.shareholder,
                "股东关系": self.shareholder_relation,
                "董事会成员": self.director,
                "前五供应商": self.supplier,
                "合并资产负债表": self.combined_balance_sheet,
                "审计意见": self.audit_opinion,
                "营业收入分区域分析": self.income_analysis,
                "募集资金总量及使用情况": self.funds_usage,
            }
        )

    def issuer_info(self, path):
        """发行人情况-*"""
        res = []
        syll_patterns = [
            [
                re.compile(r"概览"),
                re.compile(r"发行.*人.*基本情况"),
            ],
        ]
        content_patterns = [
            [
                re.compile(r"发行人名称"),
            ],
        ]
        res.extend(self.find_elements(syll_patterns=syll_patterns, table_patterns=content_patterns))
        return res

    def agency_info(self, path):
        """中介机构-*"""
        res = []
        syll_patterns = [
            [
                re.compile(r"概览"),
                re.compile(r"发行.*人.*基本情况"),
            ],
        ]
        content_patterns = [
            [
                re.compile(r"保荐人"),
            ],
        ]
        res.extend(self.find_elements(syll_patterns=syll_patterns, table_patterns=content_patterns))
        return res

    def issue_detail(self, path):
        """发行情况-*"""
        res = []
        syll_patterns = [
            [
                re.compile(r"概览"),
                re.compile(r"本次发行概况"),
            ],
        ]
        content_patterns = [
            [
                re.compile(r"股票种类"),
            ],
        ]
        res.extend(self.find_elements(syll_patterns=syll_patterns, table_patterns=content_patterns))
        return res

    def financial_info(self, path):
        """财务数据-* / 主要财务数据和财务指标"""
        res = []
        syll_patterns = [
            [
                re.compile(r"概览"),
                re.compile(r"财务数据"),
            ],
        ]
        content_patterns = [
            [
                re.compile(r"资产总额"),
            ],
        ]
        res.extend(self.find_elements(syll_patterns=syll_patterns, table_patterns=content_patterns))
        return res

    def listing_info(self, path):
        """上市标准*"""
        res = []
        syll_patterns = [
            [
                re.compile(r"概览"),
                re.compile(r"上市标准"),
            ],
        ]
        content_patterns = [
            [
                re.compile(r"上市标准"),
            ],
        ]
        res.extend(self.find_elements(syll_patterns=syll_patterns, para_patterns=content_patterns))
        return res

    def sponsor_info(self, path):
        """保荐人-*"""
        res = []
        syll_patterns = [
            [
                re.compile(r"发行概况"),
                re.compile(r"[有相]关(?:当事人|机构)"),
            ],
        ]
        content_patterns = [
            [
                re.compile(r"保荐人"),
                # re.compile(r".*"),
            ],
        ]
        res.extend(self.find_elements(syll_patterns=syll_patterns, table_patterns=content_patterns))
        return res

    def actual_controller(self, path):
        """实际控制人-*"""
        res = []
        syll_patterns = [
            [
                re.compile(r"发行人基本情况"),
                re.compile(r"实际控制人"),
            ],
        ]
        content_patterns = [
            [
                re.compile(r"(为本公司的?|不存在)实际控制人"),
            ],
        ]
        res.extend(self.find_elements(syll_patterns=syll_patterns, para_patterns=content_patterns))
        return res

    def shareholder(self, path):
        """持股* / 前十名股东"""
        res = []
        syll_patterns = [
            [
                re.compile(r"发行人基本情况"),
                re.compile(r"发行人股本的?情况"),
                re.compile(r"前十"),
            ],
        ]
        content_patterns = [
            [
                re.compile(r"持股数量|所持股份"),
                re.compile(r"比例"),
            ],
        ]
        res.extend(self.find_elements(syll_patterns=syll_patterns, table_patterns=content_patterns))
        return res

    def shareholder_relation(self, path):
        """股东关系"""
        res = []
        syll_patterns = [
            [
                re.compile(r"发行人基本情况"),
                re.compile(r"发行人股本情况"),
                re.compile(r"股东间.*关系"),
            ],
        ]
        content_patterns = [
            [
                re.compile(r".*"),
            ],
        ]
        res.extend(
            self.find_elements(
                syll_patterns=syll_patterns, para_patterns=content_patterns, table_patterns=content_patterns
            )
        )
        return res

    def director(self, path):
        """董事会成员"""
        res = []
        syll_patterns = [
            [
                re.compile(r"发行人基本情况"),
                re.compile(r"董事.*(简介|概况|(简要|提名)情况)"),
                re.compile(r"董事会成员"),
            ],
        ]
        content_patterns = [
            [
                re.compile(r"姓名"),
                re.compile(r"职位|任职"),
            ],
        ]
        res.extend(self.find_elements(syll_patterns=syll_patterns, table_patterns=content_patterns))
        return res

    def supplier(self, path):
        """前五供应商*"""
        res = []
        syll_patterns = [
            [
                re.compile(r"业务与技术"),
                re.compile(r"供应"),
            ],
        ]
        content_patterns = [
            [
                re.compile(r"供应商名称"),
            ],
        ]
        res.extend(self.find_elements(syll_patterns=syll_patterns, table_patterns=content_patterns))
        return res

    def combined_balance_sheet(self, path):
        """合并资产负债表*"""
        res = []
        syll_patterns = [
            [
                re.compile(r"财务会计信息"),
                re.compile(r"财务报表"),
                re.compile(r"合并.*报表|资产负债表"),
            ],
        ]
        content_patterns = [
            [
                re.compile(r"非流动资产"),
                re.compile(r"资产总计"),
            ],
        ]
        res.extend(self.find_elements(syll_patterns=syll_patterns, table_patterns=content_patterns))
        return res

    def audit_opinion(self, path):
        """审计意见"""
        res = []
        syll_patterns = [
            [
                re.compile(r"财务会计信息"),
                re.compile(r"审计意见"),
            ],
        ]
        content_patterns = [
            [
                re.compile(r"审计意见"),
            ],
        ]
        res.extend(self.find_elements(syll_patterns=syll_patterns, para_patterns=content_patterns))
        return res

    def income_analysis(self, path):
        """营业收入分区域分析*"""
        res = []
        syll_patterns = [
            [
                # re.compile(r"财务会计信息"),
                # re.compile(r"经营成果"),
                # re.compile(r"营业收入"),
                re.compile(r"构成分析"),
                re.compile(r"按.*(区域|地区)"),
            ],
        ]
        content_patterns = [
            [
                re.compile(r"(地区|区域)"),
            ],
        ]
        res.extend(self.find_elements(syll_patterns=syll_patterns, table_patterns=content_patterns))
        return res

    def funds_usage(self, path):
        """募集资金总量及使用情况*"""
        res = []
        syll_patterns = [
            [
                re.compile(r"募集资金运用"),
                re.compile(r"概况|使用安排|运用情况"),
            ],
        ]
        content_patterns = [
            [
                re.compile(r"金额|投资额"),
            ],
        ]
        res.extend(self.find_elements(syll_patterns=syll_patterns, table_patterns=content_patterns))
        return res
