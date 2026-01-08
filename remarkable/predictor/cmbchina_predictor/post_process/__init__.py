from remarkable.predictor.cmbchina_predictor.post_process.cmbchina import post_process_sale_platform
from remarkable.predictor.cmbchina_predictor.post_process.cmbchina_prospectus import post_process_subscription_rate

process_config = {
    "post_process_subscription_rate": post_process_subscription_rate,
    "post_process_sale_platform": post_process_sale_platform,
}
