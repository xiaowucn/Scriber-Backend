from remarkable.answer.reader import AnswerReader
from remarkable.common.util import clean_txt
from remarkable.predictor.base_prophet import BaseProphet
from remarkable.predictor.predictor import JudgeByRegex


class CiticIssueAnnouncement(JudgeByRegex):
    col_patterns = {
        "是否分期发行": {
            "否": [r"不|没有|未"],
            "是": ["分期发行"],
        },
        "债券期限": {"多品种": [r"[2-9两二三四五六七八九十]个品种"], "单品种": ""},
    }


class CiticIssueAnnouncementPlusOne(JudgeByRegex):
    col_patterns = {  # noqa: F811
        "承销方式": {  # skip
            "代销": [
                r"代销",
            ],
            "全额包销": [
                r"全额包销",
            ],
            "余额包销": [
                r"余额包销",
            ],
            "其他": [r".+"],
            "信息缺失": [r"^$"],
        },
        "CISP发行方式": {
            "同时面向公众投资者和合格投资者公开发行": [
                r"面向公众投资者和(合格|专业)(机构)?投资者",
                r"面向(合格|专业)(机构)?投资者和公众投资者",
            ],
            "仅面向合格投资者公开发行": [
                r"面向(合格|专业)(机构)?投资者公开发行",
            ],
            "非公开发行": [
                r"非公开发行",
            ],
            "信息缺失": [r"^$"],
        },
        "SZSE发行方式": {  # skip
            "网上发行": [
                r"网上",
            ],
            "网下发行": [
                r"网下",
            ],
            "网上发行;网下发行": [r"网上.*网下", "网下.*网上"],
        },
        "本金偿还方式": {  # skip
            "到期一次性偿还": [
                r"到期一次性偿还",
                r"到期一次还本.",
                r"到期归还本金和最后一年利息",
            ],
            "分期偿还": [
                r"分期偿还",
            ],
            "其他": [r".+"],
            "信息缺失": [r"^$"],
        },
        "利率类型": {  # skip
            "无利率类型": [
                r"无利率类型",
            ],
            "固定利率": [
                r"固定利率",
            ],
            "浮动利率": [
                r"浮动利率",
            ],
            "挂钩浮动": [
                r"挂钩浮动",
            ],
            "与Shibor挂钩浮动": [
                r"与Shibor挂钩浮动",
            ],
            "与Libor挂钩浮动": [
                r"与Libor挂钩浮动",
            ],
            "与银行间市场7天质押式回购利率挂钩浮动": [
                r"与银行间市场7天质押式回购利率挂钩浮动",
            ],
            "与1年期定期存款基准利率挂钩浮动": [
                r"与1年期定期存款基准利率挂钩浮动",
            ],
            "与1至3年期贷款基准利率挂钩浮动": [
                r"与1至3年期贷款基准利率挂钩浮动",
            ],
            "与1年期贷款基础利率LPR挂钩浮动": [
                r"与1年期贷款基础利率LPR挂钩浮动",
            ],
            "与3年期国债收益率挂钩": [
                r"与3年期国债收益率挂钩",
            ],
            "与5年期国债收益率挂钩": [
                r"与5年期国债收益率挂钩",
            ],
            "与其他利率或其他标的挂钩浮动": [
                r"与其他利率或其他标的挂钩浮动",
            ],
            "累进浮动": [
                r"累进浮动",
            ],
            "其他浮动方式": [r".+"],
            "信息缺失": [r"^$"],
        },
        "SZSE期数": {  # skip
            "一": [r"第一期"],
            "二": [r"第二期"],
            "三": [r"第三期"],
            "四": [r"第四期"],
            "五": [r"第五期"],
            "六": [r"第六期"],
            "七": [r"第七期"],
            "八": [r"第八期"],
            "九": [r"第九期"],
            "十": [r"第十期"],
            "十一": [r"第十一期"],
            "十二": [r"第十二期"],
            "十三": [r"第十三期"],
            "十四": [r"第十四期"],
            "十五": [r"第十五期"],
            "十六": [r"第十六期"],
            "十七": [r"第十七期"],
            "十八": [r"第十八期"],
            "十九": [r"第十九期"],
            "二十": [r"第二十期"],
        },
        "SZSE利率形式": {  # skip
            "固定利率": [
                r"固定利率",
            ],
            "浮动利率": [
                r"浮动利率",
            ],
        },
        "SZSE还本方式": {  # skip
            "到期按面值偿还": [
                r"到期按面值偿还",
            ],
            "到期一次还本付息": [
                r"到期一次还本付息",
            ],
            "到期还本并支付最后一期利息": [
                r"到期还本并支付最后一期利息",
            ],
            "存在提前兑付并支付对应部分利息": [
                r"存在提前兑付并支付对应部分利息",
            ],
        },
        "SSE评级展望": {
            "正面": [
                r"正面",
            ],
            "稳定": [
                r"稳定",
            ],
            "负面": [
                r"负面",
            ],
        },
        "派息周期": {
            "月": [
                r"月",
            ],
            "日": [
                r"日",
            ],
        },
    }


class CiticIssueAnnouncementPlusTwo(JudgeByRegex):
    col_patterns = {  # noqa: F811
        "票面利率选择权": {
            "利率调整": [".+"],
        },
        "赎回债券选择权": {
            "赎回": [r".+"],
        },
        "回售债券选择权": {
            "回售": [r".+"],
        },
        "发行人续期选择权": {
            "可续期债重定价": [r"可续期"],
        },
        "债券期限含权情况": {
            "含权": ["附.*权", "有权"],
            "不含权": [r".*"],
        },
        "SZSE债券期限（单位）": {
            "年": [r"年"],
            "月": [r"月"],
            "日": [r"日"],
        },
    }
    multi_answer_col_patterns = {
        "SZSE募集资金用途": {
            "values": {
                "补充流动资金": ["补充.*?(营运|流动)资金"],
                "偿还银行贷款": [r"偿还银行贷款"],
                "保障房建设": [r"保障房建设"],
                "其他项目/投资建设": [
                    r"建设项目",
                    r"项目建设",
                    r"项目专项投资",
                    r"产业项目",
                ],
                "其他": [
                    r"偿还.*?(负债|债|银行贷款|公司借款)",
                    r"(偿还|支付).*?\d+.*?(本金|回收款|利息)",
                    r"对全资子公司出资",
                ],
            },
        },
        "CISP募集资金用途": {
            "values": {
                "补充营运/流动资金": [r"补充.*?(营运|流动)资金"],
                "偿还债务（银行贷款、公司借款等）": [r"偿还.*?(负债|债|贷款|公司借款)"],
                "项目专项投资": [
                    r"建设项目",
                    r"项目建设",
                    r"项目专项投资",
                    r"产业项目",
                ],
                "股权投资": [r"股权投资"],
                "其他": [
                    r"(偿还|支付).*?\d+.*?(本金|回收款|利息)",
                    r"对全资子公司出资",
                ],
            }
        },
    }


class Prophet(BaseProphet):
    def parse_enum_value(self, predictor_result, schema):
        if self.enum_predictor:
            return self.enum_predictor.predict(predictor_result, schema)
        return None

    def get_enum_predictor(self):
        enum_classes = {
            "中信-募集书抽取": CiticIssueAnnouncement,
            "中信-募集书抽取-附加一": CiticIssueAnnouncementPlusOne,
            "中信-募集书抽取-附加二": CiticIssueAnnouncementPlusTwo,
        }
        if predictor := (enum_classes.get(self._mold.name) or enum_classes.get(clean_txt(self._mold.name))):
            return predictor()

    @staticmethod
    def post_process(preset_answer):
        answer_reader = AnswerReader(preset_answer)
        all_pop_fields = []

        mutual_exclusion_fields = {  # 丢掉key
            "发行人设立情况及历史沿革": ["发行人设立情况", "发行人历史沿革"],
            "控股股东及实际控制人情况": ["发行人控股股东情况", "发行人实际控制人情况"],
            "发行人行业地位、竞争优势、战略目标、发展规划": [
                "公司所处行业地位",
                "公司面临的主要竞争状况",
                "公司经营方针和战略",
            ],
            "发行人所在行业状况、行业地位、竞争状况、经营方针及战略": [
                "所在行业状况",
                "公司所处行业地位",
                "公司面临的主要竞争状况",
                "公司经营方针和战略",
            ],
        }

        mutual_exclusion_fields_1 = {  # 丢掉value
        }

        for pop_field, exclusion_fields in mutual_exclusion_fields.items():
            for exclusion_field in exclusion_fields:
                if answer_reader.find_nodes([exclusion_field]):
                    all_pop_fields.append(pop_field)
                    break

        for exclusion_field, pop_fields in mutual_exclusion_fields_1.items():
            if answer_reader.find_nodes([exclusion_field]):
                all_pop_fields.extend(pop_fields)

        answer_items = []
        for item in answer_reader.items:
            label = item["schema"]["data"]["label"]
            if label in all_pop_fields:
                continue

            answer_items.append(item)
        preset_answer["userAnswer"]["items"] = answer_items
        return preset_answer
