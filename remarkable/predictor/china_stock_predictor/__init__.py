from remarkable.common.pattern import PatternCollection
from remarkable.common.util import clean_txt
from remarkable.predictor.base_prophet import BaseProphet
from remarkable.predictor.common_pattern import R_UNSELECTED
from remarkable.predictor.predictor import JudgeByRegex


class PrivateFundContract(JudgeByRegex):
    check_mark = r"[☑✓√■\uf052]"
    link_word = ".*"
    p_sub = PatternCollection(
        [
            r"每月按30个自然日",
            r"后的每月\d{1,2}日",
            r"每月不超过\d次",
        ]
    )

    @classmethod
    def clean_open_day(cls, text):
        text = cls.p_sub.sub("***", text)
        text = clean_txt(text)
        return text

    col_patterns = {
        "赎回费是否归属基金资产": {
            "否": [
                rf"{check_mark}否",
                r"^否$",
                r"赎回费不归属基金资产",
                r"赎回费归属管理人",
            ],
            "是": [
                rf"{check_mark}是",
                r"^是$",
                r"赎回费归属基金资产",
            ],
        },
        "募集机构的回访确认制度": {
            "不设置": [
                rf"{check_mark}不设置",
                r"不设置",
            ],
            "设置": [
                rf"{check_mark}设置",
                r"^设置$",
            ],
        },
        "运作方式": {
            "封闭式": [
                rf"{check_mark}封闭式",
                r"^封闭式$",
            ],
            "开放式": [
                rf"{check_mark}开放式",
                r"^(定期)?开放式$",
            ],
            "其他方式": [
                rf"{check_mark}其他方式",
                r"^其他方式$",
            ],
        },
        "估值核对频率": {
            "工作日": [
                rf"{check_mark}工作日",
                r"^工作日$",
            ],
            "自然周": [
                rf"{check_mark}自然周",
                r"^自然周$",
            ],
            "自然月": [
                rf"{check_mark}自然月",
                r"^自然月$",
            ],
            "自然季度": [
                rf"{check_mark}自然季度",
                r"^自然季度$",
            ],
        },
        "开放日": {
            "每日开放": [
                rf"每(个交易)?日{link_word}开放",
                rf"开放{link_word}每个交易日",
            ],
            "每周开放": [
                rf"每[个自然]*周{link_word}开放",
                rf"开放{link_word}每[个自然]*周",
                r"^每周[一二三四五]$",
            ],
            "每月开放": [
                rf"每[个自然]*月{link_word}开放",
                rf"开放{link_word}每[个自然]*月",
            ],
            "每季度开放": [
                rf"每[个自然]*季度?{link_word}开放",
                rf"开放{link_word}每[个自然]*季度?",
                rf"每[届满]*([3三][个自然]*月|90个自然日){link_word}开放",
                rf"开放{link_word}每[届满]*([3三][个自然]*月|90个自然日)",
                rf"之后届满[3三][个自然]*月{link_word}开放",
                rf"开放日{link_word}[123]月?(\d+日)?、[456]月?(\d+日)?、[789]月?(\d+日)?、[102]{{2}}月(\d+日)?",
                rf"[123]月?(\d+日)?、[456]月?(\d+日)?、[789]月?(\d+日)?、[102]{{2}}月(\d+日)?{link_word}(开放日|申请截止日)",
                r"季度固定开放日",
                r"每季基金成立日对日为开放日",
                r"每个季月",
            ],
            "每半年开放": [
                rf"每[届满]*([6六][个自然]*月|半年){link_word}开放",
                rf"开放{link_word}每[届满]*([6六][个自然]*月|半年)",
                r"本基金满[6六][个自然]*月后的首个工作日为本基金首个开放期内基金委托人办理申购、赎回申请的申请截止日",
                rf"开放{link_word}每(自然)?年的?[123456]月?(\d+日)?、[789012]{{1,2}}月",
                rf"每(自然)?年的?[123456]月?(\d+日)?[和、][789012]{{1,2}}月(\d+日)?{link_word}开放",
            ],
            "每年开放": [
                rf"每([1一个自然]*年|满?12个月){link_word}开放",
                rf"开放{link_word}每([1一个自然]*年|满?12个月)",
                rf"开放日本基金成立日起封闭期满后首个交易日及之后每7个自然月中{link_word}开放",
            ],
            "每2年开放": [rf"每[届满]*[2二两]个年{link_word}开放"],
            "每3年开放": [rf"每[届满]*[3三]个年{link_word}开放"],
            "无开放日": [r"^无$|本基金封闭运作|不设置开放日"],
        },
    }

    multi_answer_col_patterns = {
        "募集方式": {
            "values": {
                "直销": [
                    rf"{check_mark}直销",
                    rf"(?<!{R_UNSELECTED})直销",
                ],
                "代销": [
                    rf"{check_mark}代销",
                    rf"(?<!{R_UNSELECTED})代销",
                ],
            },
        },
        "募集机构": {
            "values": {
                "直销：基金管理人": [rf"{check_mark}直销", r"^直销[：:]基金管理人$", r"^基金管理人.直销"],
                "代销：基金管理人委托基金销售机构：": [
                    rf"{check_mark}代销",
                    r"^代销[：:]基金管理人委托基金销售机构[：:]$",
                ],
            },
        },
    }


class Prophet(BaseProphet):
    def parse_enum_value(self, predictor_result, schema):
        if self.enum_predictor:
            clean_func = clean_txt
            if schema.name == "开放日":
                clean_func = PrivateFundContract.clean_open_day
            return self.enum_predictor.predict(predictor_result, schema, clean_func)
        return None

    def get_enum_predictor(self):
        enum_classes = {
            "私募-基金合同": PrivateFundContract,
        }
        if predictor := (enum_classes.get(self._mold.name) or enum_classes.get(clean_txt(self._mold.name))):
            return predictor()
