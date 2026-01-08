from remarkable.predictor.cmbchina_predictor.models.classified_fund_partial_text import ClassifiedFundPartialText
from remarkable.predictor.cmbchina_predictor.models.fund_name import FundName
from remarkable.predictor.cmbchina_predictor.models.maturity_date import MaturityDate
from remarkable.predictor.cmbchina_predictor.models.rdjusted_rate import AdjustedRate
from remarkable.predictor.cmbchina_predictor.models.split_table_row import SplitTableRow
from remarkable.predictor.cmbchina_predictor.models.subscription import Subscription
from remarkable.predictor.cmbchina_predictor.models.subscription_rate import SubscriptionRate
from remarkable.predictor.cmbchina_predictor.models.table_header import TableHeader
from remarkable.predictor.cmbchina_predictor.models.table_regroup import TableRegroup
from remarkable.predictor.cmbchina_predictor.models.table_subscription import TableSubscription

model_config = {
    "subscription": Subscription,
    "adjusted_rate": AdjustedRate,
    "table_header": TableHeader,
    "table_subscription": TableSubscription,
    "fund_name": FundName,
    "classified_fund_partial_text": ClassifiedFundPartialText,
    "subscription_rate": SubscriptionRate,
    "split_table_row": SplitTableRow,
    "table_regroup": TableRegroup,
    "maturity_date": MaturityDate,
}
