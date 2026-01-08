# -*- coding: utf-8 -*-
from remarkable.predictor.common_poc_predictor.models.drafting_unit import DraftingUnit
from remarkable.predictor.common_poc_predictor.models.draftsmangpt import (
    DraftsCompanyGPT,
    DraftsManGPT,
)
from remarkable.predictor.common_poc_predictor.models.terms_and_definitions import (
    TermsDefinitions,
)

model_config = {
    "terms_and_definitions": TermsDefinitions,
    "drafting_unit": DraftingUnit,
    "drafts_man_gpt": DraftsManGPT,
    "drafts_company_gpt": DraftsCompanyGPT,
}
