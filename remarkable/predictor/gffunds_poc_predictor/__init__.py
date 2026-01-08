from remarkable.common.util import clean_txt
from remarkable.predictor.base_prophet import BaseProphet
from remarkable.predictor.predictor import JudgeByRegex


class BusinessApplicationA(JudgeByRegex):
    col_patterns = {
        "巨额未确认部分是否继续": {
            "继续赎回": [
                r"顺延",
            ],
            "放弃超额部分": [
                r"撤销",
            ],
        },
    }
    multi_answer_col_patterns = {
        "交易类型": {
            "values": {
                "基金转换": r"(?:基金)?转换",
                "赎回": "赎回|退出",
                "申购": "认购|申购|参与|申[(（]认[)）]购",
                "转托管": "转托管",
                "设置分红方式": "变更分红方式",
            },
        }
    }


class BusinessApplicationB(JudgeByRegex):
    col_patterns = {
        "收费方式": {
            "前端收费": [
                r"前端",
            ],
            "后端收费": [
                r"后端",
            ],
        },
        "分红方式": {
            "现金分红": [
                r"现金(分红|红利)",
            ],
            "红利再投资": [
                r"红利再投资?",
            ],
        },
        "巨额未确认部分是否继续": {
            "继续赎回": [
                r"顺延",
            ],
            "放弃超额部分": [
                r"撤销|取消",
            ],
        },
    }
    multi_answer_col_patterns = {
        "交易类型": {
            "values": {
                "基金转换": r"基金转换",
                "赎回": "赎回",
                "申购": "认/申购",
                "转托管": "转托管",
                "设置分红方式": "变更分红方式",
            },
        }
    }


class BusinessApplicationTemplate(JudgeByRegex):
    col_patterns = {
        "巨额未确认部分是否继续": {
            "继续赎回": "是|处",
            "放弃超额部分": "否",
        },
    }
    multi_answer_col_patterns = {
        "交易类型": {
            "values": {
                "基金转换": r"(?:基金)?转换",
                "赎回": "赎回|退出",
                "申购": "认购|申购|参与",
                "转托管": "转托管",
                "设置分红方式": "变更分红方式 ",
            },
        }
    }


class BusinessApplicationC(JudgeByRegex):
    col_patterns = {
        "巨额未确认部分是否继续": {
            "继续赎回": "是",
            "放弃超额部分": "否",
        },
        "分红方式": {
            "现金分红": [
                r"现金(分红|红利)",
            ],
            "红利再投资": [
                r"红利再投资?",
            ],
        },
    }
    multi_answer_col_patterns = {
        "交易类型": {
            "values": {
                "基金转换": r"转换",
                "赎回": "赎回",
                "申购": "申[(（]认[）)]购",
                "转托管": "转托管",
                "设置分红方式": "变更分红方式",
            },
        }
    }


class BusinessApplicationD(JudgeByRegex):
    col_patterns = {
        "巨额未确认部分是否继续": {
            "继续赎回": "是",
            "放弃超额部分": "否",
        },
        "分红方式": {
            "现金分红": [
                r"现金(分红|红利)",
            ],
            "红利再投资": [
                r"红利再投资?",
            ],
        },
    }
    multi_answer_col_patterns = {
        "交易类型": {
            "values": {
                "基金转换": r"转换",
                "赎回": "赎回",
                "申购": r"申[(（]?认[）)]购",
                "转托管": "转托管",
            },
        }
    }


class BusinessApplicationE(JudgeByRegex):
    col_patterns = {
        "巨额未确认部分是否继续": {
            "继续赎回": "是",
            "放弃超额部分": "否",
        },
    }
    multi_answer_col_patterns = {
        "交易类型": {
            "values": {
                "基金转换": r"产品转换",
                "赎回": "赎回",
                "申购": "认/申购",
                "转托管": "转托管",
                "设置分红方式": "分红",
            },
        }
    }


class BusinessApplicationF(JudgeByRegex):
    col_patterns = {
        "巨额未确认部分是否继续": {
            "继续赎回": "延迟办理",
            "放弃超额部分": "撤[销消]",
        },
        "交易币种": {"人民币": r"[￥¥]", "美元": r"美元"},
    }
    multi_answer_col_patterns = {
        "交易类型": {
            "values": {
                "基金转换": r"产品转换",
                "赎回": "赎回",
                "申购": "认购/申购",
                "转托管": "转托管",
                "设置分红方式": "分红",
            },
        }
    }


class BusinessApplicationG(JudgeByRegex):
    multi_answer_col_patterns = {
        "交易类型": {
            "values": {
                "赎回": "赎回",
                "申购": "认/申购",
            },
        }
    }


class BusinessApplicationOther(JudgeByRegex):
    multi_answer_col_patterns = {
        "交易类型": {
            "values": {"赎回": "赎回", "转托管": r"转托管", "撤单": "撤单", "设置分红方式": "分红方式修改"},
        }
    }


class FundQuater(JudgeByRegex):
    col_patterns = {
        "产品类型": {
            "公募基金": [r"公募基金"],
            "私募资产管理计划": [r"私募资产管理计划"],
            "其他组合": [r"其他组合"],
            "合计": [r"合计"],
        }
    }


class Prophet(BaseProphet):
    def parse_enum_value(self, predictor_result, schema):
        if self.enum_predictor:
            return self.enum_predictor.predict(predictor_result, schema)
        return None

    def get_enum_predictor(self):
        enum_classes = {
            "广发业务申请表A": BusinessApplicationA,
            "广发业务申请表B": BusinessApplicationB,
            "广发业务申请表C": BusinessApplicationC,
            "广发业务申请表D": BusinessApplicationD,
            "广发业务申请表E": BusinessApplicationE,
            "广发业务申请表F": BusinessApplicationF,
            "广发业务申请表G": BusinessApplicationG,
            "广发业务申请表模板": BusinessApplicationTemplate,
            "广发业务申请表其他模板": BusinessApplicationOther,
            "广发基金季报": FundQuater,
            "广发基金季报1": FundQuater,
        }
        if predictor := (enum_classes.get(self._mold.name) or enum_classes.get(clean_txt(self._mold.name))):
            return predictor()
