from .choose_account import ChooseAccount
from .fake_kv import FakeKV
from .fund_performance import FundPerformance
from .parse_money import ParseMoney
from .part_time_situation import PartTimeSituation
from .previous_column_cell import TablePreviousColumnCellContent
from .report_time import ReportTime
from .shape_text import ShapeText
from .syllabus_filter import GFFoundsSyllabusFilter
from .table_annotate import TableAnnotate
from .withdrawal_dividends import WithdrawalDividends

model_config = {
    "report_time": ReportTime,
    "part_time_situation": PartTimeSituation,
    "fund_performance": FundPerformance,
    "table_annotate": TableAnnotate,
    "previous_column_cell": TablePreviousColumnCellContent,
    "syllabus_filter": GFFoundsSyllabusFilter,
    "parse_money": ParseMoney,
    "withdrawal_dividends": WithdrawalDividends,
    "shape_text": ShapeText,
    "choose_account": ChooseAccount,
    "fake_kv": FakeKV,
}
