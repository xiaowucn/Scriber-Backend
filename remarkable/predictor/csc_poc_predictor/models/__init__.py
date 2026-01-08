# -*- coding: utf-8 -*-
from remarkable.predictor.csc_poc_predictor.models.fake_table import FakeTable
from remarkable.predictor.csc_poc_predictor.models.holder_row import HolderRow
from remarkable.predictor.csc_poc_predictor.models.isin import Isin
from remarkable.predictor.csc_poc_predictor.models.octopus_amount import OctopusAmount
from remarkable.predictor.csc_poc_predictor.models.octopus_kv import OctopusKv
from remarkable.predictor.csc_poc_predictor.models.party_ab import PartyAB
from remarkable.predictor.csc_poc_predictor.models.register_holders import RegisterHolders

model_config = {
    "octopus_kv": OctopusKv,
    "holder_row": HolderRow,
    "octopus_amount": OctopusAmount,
    "party_ab": PartyAB,
    "fake_table": FakeTable,
    "register_holders": RegisterHolders,
    "isin": Isin,
}
