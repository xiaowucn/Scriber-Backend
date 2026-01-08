from remarkable.rule.inspector import Inspector

from .rules.accounting_change import AccountingChange
from .rules.accounting_firm_change import AccountingFirmChange
from .rules.completeness import Completeness
from .rules.correct_operating_result import CorrectOperatingResult
from .rules.entrusted_finance_management import EntrustedFinanceManagement
from .rules.operating_result import OperatingResult
from .rules.provide_guarantee import ProvideGuarantee
from .rules.related_transaction import RelatedTransaction
from .rules.restricted_share_change import RestrictedShareChange
from .rules.transaction_standard import TransactionStandard


class SZSEPocInspector(Inspector):
    def __init__(self, *args, **kwargs):
        kwargs["rules"] = [
            TransactionStandard(),
            ProvideGuarantee(),
            RelatedTransaction(),
            OperatingResult(),
            CorrectOperatingResult(),
            AccountingChange(),
            AccountingFirmChange(),
            RestrictedShareChange(),
            EntrustedFinanceManagement(),
            Completeness("年报披露完备性-公司应当简要介绍报告期内公司主要资产发生的重大变化"),
            Completeness("年报披露完备性-公司应当简要介绍报告期内公司从事的主要业务"),
            Completeness("年报披露完备性-公司应当介绍报告期内重大资产和股权出售情况"),
            Completeness("年报披露完备性-公司应当披露公司主要控股参股公司分析"),
            Completeness("年报披露完备性-公司应当披露报告期内重大诉讼、仲裁事项"),
            Completeness("年报披露完备性-公司应当披露“归属于上市公司股东的扣除非经常性损益后的净利润”"),
            Completeness("年报披露完备性-公司应当披露报告期内核心竞争力的重要变化及对公司所产生的影响"),
            Completeness("年报披露完备性-公司应当披露未来发展展望"),
            Completeness("年报披露完备性-公司发生控股股东及其关联方非经营性占用资金情况的，应当进行披露"),
            Completeness("年报披露完备性-公司应当披露报告期内公司及其控股股东、实际控制人的诚信状况"),
        ]
        super(SZSEPocInspector, self).__init__(*args, **kwargs)
