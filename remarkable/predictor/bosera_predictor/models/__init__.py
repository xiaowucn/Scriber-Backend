# -*- coding: utf-8 -*-
from remarkable.predictor.bosera_predictor.models.investment_proportion import InvestmentProportion
from remarkable.predictor.csc_poc_predictor.models import OctopusKv

model_config = {
    "octopus_kv": OctopusKv,
    "investment_proportion": InvestmentProportion,
}
