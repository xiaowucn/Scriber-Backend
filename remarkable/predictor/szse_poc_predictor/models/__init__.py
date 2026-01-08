# -*- coding: utf-8 -*-
from remarkable.predictor.sse_predictor.models import HolderInfo
from remarkable.predictor.szse_poc_predictor.models.actual_control_situation import ActualControlSituation
from remarkable.predictor.szse_poc_predictor.models.basic_information import (
    BasicInformation,
    ChapterFiveBasicInformation,
)
from remarkable.predictor.szse_poc_predictor.models.complex_gross_margin import ComplexGrossMargin
from remarkable.predictor.szse_poc_predictor.models.consolidated_balance_sheet import ConsolidatedBalanceSheet
from remarkable.predictor.szse_poc_predictor.models.director_information import DirectorInformation
from remarkable.predictor.szse_poc_predictor.models.distribution_profile import DistributionProfile
from remarkable.predictor.szse_poc_predictor.models.employees_num import EmployeesNum
from remarkable.predictor.szse_poc_predictor.models.gross_profit_table import GrossProfitTable
from remarkable.predictor.szse_poc_predictor.models.industry_classification import (
    ChapterSixIndustryClassification,
    IndustryClassification,
)
from remarkable.predictor.szse_poc_predictor.models.institutions_concerned import InstitutionsConcerned
from remarkable.predictor.szse_poc_predictor.models.interpretation import Interpretation
from remarkable.predictor.szse_poc_predictor.models.last_capital_increase import LastCapitalIncrease
from remarkable.predictor.szse_poc_predictor.models.nonrecurring_income import NonRecurringIncome
from remarkable.predictor.szse_poc_predictor.models.period_fee_schedule import PeriodFeeSchedule
from remarkable.predictor.szse_poc_predictor.models.return_on_net_assets import ReturnOnNetAssets
from remarkable.predictor.szse_poc_predictor.models.szse_holder_info import SzseHolderInfo

model_config = {
    "complex_gross_margin": ComplexGrossMargin,
    "return_on_net_assets": ReturnOnNetAssets,
    "nonrecurring_income": NonRecurringIncome,
    "consolidated_balance_sheet": ConsolidatedBalanceSheet,
    "employees_num": EmployeesNum,
    "gross_profit_table": GrossProfitTable,
    "period_fee_schedule": PeriodFeeSchedule,
    "interpretation": Interpretation,
    "distribution_profile": DistributionProfile,
    "institutions_concerned": InstitutionsConcerned,
    "holder_info": HolderInfo,
    "szse_holder_info": SzseHolderInfo,
    "director_information": DirectorInformation,
    "actual_control_situation": ActualControlSituation,
    "industry_classification": IndustryClassification,
    "six_industry_classification": ChapterSixIndustryClassification,
    "basic_information": BasicInformation,
    "five_basic_information": ChapterFiveBasicInformation,
    "last_capital_increase": LastCapitalIncrease,
}
