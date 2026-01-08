# -*- coding: utf-8 -*-
from remarkable.predictor.swhysc_poc_predictor.models.compensatory_rate import CompensatoryRate, GuaranteeObject
from remarkable.predictor.swhysc_poc_predictor.models.planned_circulation_cap import PlannedCirculationCap

model_config = {
    "planned_circulation_cap": PlannedCirculationCap,
    "compensatory_rate": CompensatoryRate,
    "guarantee_object": GuaranteeObject,
}
