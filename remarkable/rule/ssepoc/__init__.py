from remarkable.rule.inspector import Inspector

from .rules.main_business import MainBusiness
from .rules.shareholder import NewAddShareholder
from .rules.staff import CoreStaffChange
from .rules.vip import TopFiveVIP


class SsePocInspector(Inspector):
    def __init__(self, *args, **kwargs):
        kwargs["rules"] = [
            NewAddShareholder("申报前后引入新股东"),
            CoreStaffChange("董监高核心人员变动"),
            TopFiveVIP("前五大客户"),
        ]
        super(SsePocInspector, self).__init__(*args, **kwargs)


class SSEPOCTEMPInspector(Inspector):
    def __init__(self, *args, **kwargs):
        kwargs["rules"] = [
            MainBusiness("业务收入披露正确性检查"),
        ]
        super(SSEPOCTEMPInspector, self).__init__(*args, **kwargs)
