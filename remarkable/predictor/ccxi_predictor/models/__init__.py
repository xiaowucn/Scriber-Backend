# -*- coding: utf-8 -*-
from remarkable.predictor.ccxi_predictor.models.cash_flow import CashFlow
from remarkable.predictor.ccxi_predictor.models.clearance_repo import ClearanceRepo
from remarkable.predictor.ccxi_predictor.models.collection_payment import CollectionPayment
from remarkable.predictor.ccxi_predictor.models.collection_payment_for_standard import CollectionPaymentForStandard
from remarkable.predictor.ccxi_predictor.models.monitor_indicator import MonitorIndicator
from remarkable.predictor.ccxi_predictor.models.monitor_indicator_for_standard import MonitorIndicatorForStandard
from remarkable.predictor.ccxi_predictor.models.period_interest import PeriodInterest
from remarkable.predictor.ccxi_predictor.models.qualification_criteria import QualificationCriteria
from remarkable.predictor.ccxi_predictor.models.revolving_purchase_assets import RevolvingPurchaseAssets
from remarkable.predictor.ccxi_predictor.models.sub_chief_member import SubChiefMember

model_config = {
    "qualification_criteria": QualificationCriteria,
    "period_interest": PeriodInterest,
    "sub_chief_member": SubChiefMember,
    "monitor_indicator": MonitorIndicator,
    "monitor_indicator_for_standard": MonitorIndicatorForStandard,
    "collection_payment": CollectionPayment,
    "collection_payment_for_standard": CollectionPaymentForStandard,
    "clearance_repo": ClearanceRepo,
    "revolving_purchase_assets": RevolvingPurchaseAssets,
    "cash_flow": CashFlow,
}
