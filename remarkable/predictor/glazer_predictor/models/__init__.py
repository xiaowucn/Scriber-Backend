from remarkable.predictor.glazer_predictor.models.bond_abbreviation import BondAbbreviation
from remarkable.predictor.glazer_predictor.models.bond_manager import BondManager
from remarkable.predictor.glazer_predictor.models.bond_period import BondPeriod
from remarkable.predictor.glazer_predictor.models.consignee_info import ConsigneeInfo
from remarkable.predictor.glazer_predictor.models.consignee_info_detail import ConsigneeInfoDetail
from remarkable.predictor.glazer_predictor.models.group_by_position import GroupByPosition
from remarkable.predictor.glazer_predictor.models.interpretation_table_row import InterpretationTableRow
from remarkable.predictor.glazer_predictor.models.issuing_scale_multi import IssuingScaleMulti
from remarkable.predictor.glazer_predictor.models.issuing_scale_single import IssuingScaleSingle
from remarkable.predictor.glazer_predictor.models.main_consignee import MainConsignee
from remarkable.predictor.glazer_predictor.models.notice_consignee_info import NoticeConsigneeInfo
from remarkable.predictor.glazer_predictor.models.paragraph_selector import ParagraphSelector
from remarkable.predictor.glazer_predictor.models.securities_license_key import SecuritiesLicenseKey
from remarkable.predictor.glazer_predictor.models.sub_account import SubAccount

model_config = {
    "consignee_info": ConsigneeInfo,
    "bond_manager": BondManager,
    "bond_abbreviation": BondAbbreviation,
    "main_consignee": MainConsignee,
    "interpretation_table_row": InterpretationTableRow,
    "issuing_scale_single": IssuingScaleSingle,
    "issuing_scale_multi": IssuingScaleMulti,
    "securities_license_key": SecuritiesLicenseKey,
    "group_by_position": GroupByPosition,
    "notice_consignee_info": NoticeConsigneeInfo,
    "paragraph_selector": ParagraphSelector,
    "consignee_info_detail": ConsigneeInfoDetail,
    "bond_period": BondPeriod,
    "sub_account": SubAccount,
}
