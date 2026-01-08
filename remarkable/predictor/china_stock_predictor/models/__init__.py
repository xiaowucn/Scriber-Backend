# -*- coding: utf-8 -*-
from remarkable.predictor.china_stock_predictor.models.after_table_info import AfterTableInfo
from remarkable.predictor.china_stock_predictor.models.fund_account import FundAccount
from remarkable.predictor.china_stock_predictor.models.fund_name import FundName
from remarkable.predictor.china_stock_predictor.models.fund_people import FundPeople
from remarkable.predictor.china_stock_predictor.models.investment_scope import InvestmentScope
from remarkable.predictor.china_stock_predictor.models.kv_cell_text import KvCellText
from remarkable.predictor.china_stock_predictor.models.monitor_procedures import MonitorProcedures
from remarkable.predictor.china_stock_predictor.models.open_day import OpenDay
from remarkable.predictor.china_stock_predictor.models.operate_expenses import OperateExpenses
from remarkable.predictor.china_stock_predictor.models.perfect_copy_method import PerfectCopyMethod
from remarkable.predictor.china_stock_predictor.models.performance_calc import PerformanceCalc
from remarkable.predictor.china_stock_predictor.models.publicly_disclosed_information import (
    PubliclyDisclosedInformation,
)
from remarkable.predictor.china_stock_predictor.models.split_by_reg import SplitByReg
from remarkable.predictor.china_stock_predictor.models.table_kv_expand import KvCellExpand

model_config = {
    "kv_cell_text": KvCellText,
    "monitor_procedures": MonitorProcedures,
    "fund_account": FundAccount,
    "operate_expenses": OperateExpenses,
    "investment_scope": InvestmentScope,
    "performance_calc": PerformanceCalc,
    "open_day": OpenDay,
    "split_by_reg": SplitByReg,
    "after_table_info": AfterTableInfo,
    "fund_people": FundPeople,
    "fund_name": FundName,
    "publicly_disclosed_information": PubliclyDisclosedInformation,
    "perfect_copy_method": PerfectCopyMethod,
    "table_kv_expand": KvCellExpand,
}
