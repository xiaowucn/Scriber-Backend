from .pension_plan import PensionPlan
from .product_abb import ETFFundType, ProductAbbSubmission
from .stock_style_cov import StockStyleConv

model_config = {
    "pension_plan": PensionPlan,
    "product_abb_submission": ProductAbbSubmission,
    "etf_fund_type": ETFFundType,
    "stock_style_conv": StockStyleConv,
}
