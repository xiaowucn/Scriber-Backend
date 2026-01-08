from collections import defaultdict

from remarkable.common.constants import TableType
from remarkable.common.pattern import PatternCollection
from remarkable.common.util import clean_txt
from remarkable.pdfinsight.parser import parse_table
from remarkable.predictor.models.table_tuple import TupleTable

INCOME_SCHEMA = "扣除所得税影响后的非经常性损益"
PROFIT_SCHEMA = "扣除非经常性损益后的归属于母公司所有者净利润"

special_feature = [r"[小合]计"]

invalid_under_cell_patterns = [r"所得税的?影响|减[：:].*?所得税|减[：:].*?非经常性损益净额|扣税后非经常性损益"]
valid_above_cell_patterns = [r"所得税的?影响"]
valid_above_cell_patterns2 = [r"少数股东权益"]
valid_in_invalid_pattern = PatternCollection([r"-"])
invalid_income_patterns = [r"扣除非经常性损益后归属于母公司股东的净利润"]


invalid_profit_patterns = [
    r"归属于母公司股东的?非经常性损益净额|归属于发行人股东的?非经常性损益",
    r"^扣除非经常性损益后的净利润$",
    r"^归属于母公司股东的净利润(（万元）)?$",
    r"^非经常性损益净额$",
]
invalid_profit_cell_patterns = [r"减"]

INVALID_TABLE_TITLE = PatternCollection(
    [
        r"\d-\d月",
        r"盈利能力稳定性的影响",
        r"非经常性损益的主要项目和金额",
        r"非经常性损益对经营成果的影响",
        r"非经常性损益明?细?表主要数据$",
        r"经致同会计师事务所鉴证的非经常性损益情况如下",  # 818 笛东规划
        r"公司财务费用构成情况如下",  # 806 杭州华塑
        r"根据初步测算.*?年业绩预计情况如下",  # 810 软通动力
        r"合并利润表主要数据",  # 813 上海国缆
        r"投资收益",  # 812 深圳安培
        r"公司.*?年的业绩预计情况如下",  # 807 无锡金通
        r"利润表主要数据",  # 807 无锡金通
    ]
)


class NonRecurringIncome(TupleTable):
    target_element = None
    filter_elements_by_target = True

    def __init__(self, options, schema, predictor):
        super(NonRecurringIncome, self).__init__(options, schema, predictor)

    def predict_schema_answer(self, elements):
        rets = []
        for element in elements:
            table = parse_table(element, tabletype=TableType.TUPLE.value, pdfinsight_reader=self.pdfinsight)
            table_title = table.title.text if table.title else element["title"]
            if table_title and INVALID_TABLE_TITLE.nexts(clean_txt(table_title)):
                continue
            answer_results = super(NonRecurringIncome, self).predict_schema_answer([element])
            answer_results = self.filter_answer_results(answer_results, table)
            rets = self.append_answer(rets, answer_results)
        return rets

    @staticmethod
    def filter_answer_results(answer_results, table):
        income_schema_rets = []
        profit_schema_rets = []
        for answer_result in answer_results:
            is_valid_income = True
            is_valid_profit = True
            has_subtotal = False  # 是否是小计合计行
            for key, item in answer_result.items():
                element_result = item[0].element_results[0]
                parsed_cell = element_result.parsed_cells[0]
                if key == INCOME_SCHEMA:
                    for cell in parsed_cell.headers:
                        if PatternCollection(special_feature).nexts(clean_txt(cell.text)):
                            has_subtotal = True
                            break
                    if parsed_cell.rowidx - 1 < 0:
                        continue
                    above_cell = table.rows[parsed_cell.rowidx - 1][parsed_cell.colidx]
                    under_cell = None
                    if parsed_cell.rowidx + 1 < table.height:
                        under_cell = table.rows[parsed_cell.rowidx + 1][parsed_cell.colidx]
                    if has_subtotal:
                        for cell in above_cell.headers:
                            if PatternCollection(valid_above_cell_patterns).nexts(clean_txt(cell.text)):
                                is_valid_income = True
                                break
                        if under_cell:
                            for cell in under_cell.headers:
                                if PatternCollection(invalid_under_cell_patterns).nexts(clean_txt(cell.text)):
                                    is_valid_income = False
                                    break
                    for cell in parsed_cell.headers:
                        if PatternCollection(invalid_income_patterns).nexts(clean_txt(cell.text)):
                            is_valid_income = False
                            break
                    # 答案上面不能出现 `少数股东权益` 相关行
                    # todo 暂时注释 提取口径问题 先提出来
                    # for cell in above_cell.headers:
                    # if PatternCollection(valid_above_cell_patterns2).nexts(clean_txt(cell.text)):
                    #     is_valid_income = False
                    # 答案上面出现 `少数股东权益` 相关行 但是其内容是空的或者是'-' 这种是对的
                    # todo 暂时注释 等到客户确认后再放开
                    # other_cells = cell.table.rows[cell.rowidx][cell.colidx + 1 :]
                    # cells_text = ''.join({i.text for i in other_cells})
                    # if valid_in_invalid_pattern.nexts(cells_text):
                    #     is_valid_income = True
                    # break
                    if is_valid_income and len(income_schema_rets) <= 4:
                        income_schema_rets.append(answer_result)
                if key == PROFIT_SCHEMA:
                    for cell in parsed_cell.headers:
                        if PatternCollection(invalid_profit_patterns).nexts(clean_txt(cell.text)):
                            is_valid_profit = False
                            break
                    if is_valid_profit and parsed_cell.rowidx + 1 == table.height and len(profit_schema_rets) <= 4:
                        profit_schema_rets.append(answer_result)
                        break
                    under_cell = None
                    if parsed_cell.rowidx + 1 < table.height:
                        under_cell = table.rows[parsed_cell.rowidx + 1][parsed_cell.colidx]
                    if under_cell:
                        for cell in under_cell.headers:
                            if PatternCollection(invalid_profit_cell_patterns).nexts(clean_txt(cell.text)):
                                is_valid_profit = False
                                break
                    if is_valid_profit and len(profit_schema_rets) <= 4:
                        profit_schema_rets.append(answer_result)

        return income_schema_rets + profit_schema_rets

    @staticmethod
    def count_answers_by_column(answer_results):
        answer_map = defaultdict(list)
        for answer_result in answer_results:
            for key, value in answer_result.items():
                answer_map[key].append(value)
        ret = {
            INCOME_SCHEMA: len(answer_map.get(INCOME_SCHEMA, [])),
            PROFIT_SCHEMA: len(answer_map.get(PROFIT_SCHEMA, [])),
        }
        return ret

    def append_answer(self, rets, answer_results):
        if not rets:
            rets.extend(answer_results)
            return rets
        origin_counts = self.count_answers_by_column(rets)
        if origin_counts[INCOME_SCHEMA] >= 4:
            for answer_result in answer_results:
                if INCOME_SCHEMA in answer_result:
                    continue
                rets.append(answer_result)
        if origin_counts[PROFIT_SCHEMA] >= 4:
            for answer_result in answer_results:
                if PROFIT_SCHEMA in answer_result:
                    continue
                rets.append(answer_result)
        return rets
