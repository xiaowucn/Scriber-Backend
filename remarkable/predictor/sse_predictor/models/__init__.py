from remarkable.predictor.sse_predictor.models.connected_transaction import ConnectedTransaction
from remarkable.predictor.sse_predictor.models.holderinfo import HolderInfo
from remarkable.predictor.sse_predictor.models.main_business import MainBusiness
from remarkable.predictor.sse_predictor.models.new_shareholder import NewShareholder
from remarkable.predictor.sse_predictor.models.top_five_customers import TopFiveCustomers
from remarkable.predictor.sse_predictor.models.top_five_customers_notes import TopFiveCustomersNotes

model_config = {
    "new_shareholder": NewShareholder,
    "connected_transaction": ConnectedTransaction,
    "top_five_customers_notes": TopFiveCustomersNotes,
    "top_five_customers": TopFiveCustomers,
    "holder_info": HolderInfo,
    "main_business": MainBusiness,
}
