from remarkable.common.box_util import get_bound_box
from remarkable.common.pattern import PatternCollection
from remarkable.common.util import clean_txt
from remarkable.predictor.models.base_model import BaseModel
from remarkable.predictor.models.partial_text import PartialText
from remarkable.predictor.models.table_kv import KeyValueTable
from remarkable.predictor.schema_answer import CharResult

INDUSTRY = PatternCollection(
    [
        r"“(?P<dst>农林牧渔|采矿业|制造业|水电煤气|建筑业|批发零售|运输仓储|住宿餐饮|信息技术|金融业|房地产|商务服务|科研服务|公共环保|居民服务|教育|卫生|文化传播|综合)”"
    ]
)
INDUSTRY_SEGMENTATION = PatternCollection(
    [
        r"“?(?P<dst>农业|林业|畜牧业|渔业|农、林、牧、渔服务业|煤炭开采和洗选业|石油和天然气开采业|黑色金属矿采选业|有色金属矿采选业|非金属矿采选业|开采辅助活动|其他采矿业|农副产品加工业|食品制造业|酒、饮料和精制茶制造业|烟草制品业|纺织业|纺织服装、服饰业|皮革、毛皮、羽毛及其制品和制鞋业|木材加工和木、竹、藤、棕、草制品业|家具制造业|造纸和纸制品业|印刷和记录媒介复制业|文教、工美、体育和娱乐用品制造业|石油加工、炼焦和核燃料加工业|化学原料和化学制品制造业|医药制造业|化学纤维制造业|橡胶和塑料制品业|非金属矿物制品业|黑色金属冶炼和压延加工业|有色金属冶炼和压延加工业|金属制品业|通用设备制造业|专用设备制造业|汽车制造业|铁路、船舶、航空航天和其他运输设备制造业|电器机械和器材制造业|计算机、通信和其他电子设备制造业|仪器仪表制造业|其他制造业|废弃资源综合利用业|金属制品、机械和设备修理业|电力、热力生产和供应业|燃气生产和供应业|水的生产和供应业|房屋建筑业|土木工程建筑业|建筑安装业|建筑装饰和其他建筑业|批发业|零售业|铁路运输业|道路运输业|水上运输业|航空运输业|管道运输业|装卸搬运和运输代理业|仓储业|邮政业|住宿业|餐饮业|电信、广播电视和卫星传输服务|互联网和相关服务|软件和信息技术服务业|货币金融服务|资本市场服务|保险业|其他金融业|房地产业|租赁业|商务服务业|研究和试验发展|专业技术服务业|科技推广和应用服务业|水利管理业|生态保护和环境治理业|公共设施管理业|居民服务业|机动车、电子产品和日用产品修理业|其他服务业|教育|卫生|社会工作|新闻和出版业|广播、电视、电影和影视录音制作业|文化艺术业|体育|娱乐业)”?",
        r"“(?P<dst>综合)”",
    ]
)


class TransferStationModel(BaseModel):
    def train(self, dataset, **kwargs):
        pass

    def predict_schema_answer(self, elements):
        pass

    def filter_industry(self, answer_results, from_para=False):
        for answer_result in answer_results:
            col = "证监会行业"
            industry = answer_result.get("证监会行业", [])
            if industry:
                industry = self.get_industry_answer(col, industry, INDUSTRY, from_para)
                answer_result[col] = industry
            col = "证监会行业细分"
            industry_segmentation = answer_result.get(col, [])
            if industry_segmentation:
                industry_segmentation = self.get_industry_answer(
                    col, industry_segmentation, INDUSTRY_SEGMENTATION, from_para
                )
                answer_result[col] = industry_segmentation

    def get_industry_answer(self, col, industry_segmentation, pattern, from_para=False):
        ret = []
        process_answers = set()
        for answer in industry_segmentation:
            element_result = answer.element_results[0]
            element = answer.relative_elements[0]
            if from_para:
                matcher_obj = element_result.element
                element_text = element["text"]
                answer_box = get_bound_box([char["box"] for char in element_result.chars])
            else:
                parsed_cell = element_result.parsed_cells[0]
                matcher_obj = parsed_cell.raw_cell
                element_text = parsed_cell.text
                answer_box = parsed_cell.outline
            for matcher in pattern.finditer(clean_txt(element_text)):
                if matcher:
                    name_dst_chars = self.get_dst_chars_from_matcher(matcher, matcher_obj)
                    if not name_dst_chars:
                        continue
                    preset_answer_box = get_bound_box([char["box"] for char in name_dst_chars])
                    overlap = self.pdfinsight.overlap_percent(answer_box, preset_answer_box)
                    answer_text = "".join([i["text"] for i in name_dst_chars])
                    if overlap > 0.8 and answer_text not in process_answers:
                        process_answers.add(answer_text)
                        ret.append(self.create_result([CharResult(element, name_dst_chars)], column=col))
        return ret


class IndustryClassification(KeyValueTable, TransferStationModel):
    def __init__(self, options, schema, predictor):
        super(IndustryClassification, self).__init__(options, schema, predictor)

    def predict_schema_answer(self, elements):
        answer_results = super(IndustryClassification, self).predict_schema_answer(elements)
        self.filter_industry(answer_results)
        return answer_results


class ChapterSixIndustryClassification(PartialText, TransferStationModel):
    def predict_schema_answer(self, elements):
        answer_results = super(ChapterSixIndustryClassification, self).predict_schema_answer(elements)
        if answer_results:
            self.filter_industry(answer_results, from_para=True)
        answer_results = self.get_industry_from_crude_answer(elements, answer_results)
        return answer_results

    def get_industry_from_crude_answer(self, elements, answer_results):
        has_answer_col = []
        for answer_result in answer_results:
            has_answer_col.extend(list(answer_result.keys()))
        ret = []
        for element in elements:
            element_text = element["text"]
            col_pattern = {
                "证监会行业": INDUSTRY,
                "证监会行业细分": INDUSTRY_SEGMENTATION,
            }
            for col, pattern in col_pattern.items():
                if col in has_answer_col:
                    continue
                for matcher in pattern.finditer(clean_txt(element_text)):
                    if matcher:
                        name_dst_chars = self.get_dst_chars_from_matcher(matcher, element)
                        if not name_dst_chars:
                            continue
                        ret.append(self.create_result([CharResult(element, name_dst_chars)], column=col))
                        break
            if ret:
                break
        return answer_results + ret
