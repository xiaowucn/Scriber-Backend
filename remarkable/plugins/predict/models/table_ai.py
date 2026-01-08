"""AI 表格提取模型
暂只支持上交所招股书
"""

import logging

from aipod.rpc.client import AIClient

from remarkable.config import get_config
from remarkable.predictor.predict import ResultOfPredictor, TblResult

from .model_base import PredictModelBase


class AITable(PredictModelBase):
    model_intro = {
        "doc": """
        AI 表格提取模型
        """,
        "name": "表格AI模型",
        "hide": True,
    }

    @classmethod
    def model_template(cls):
        return cls.default_model_template()

    def __init__(self, *args, **kwargs):
        super(AITable, self).__init__(*args, **kwargs)
        self.need_training = False
        self.expand = get_config("ai.table_extract.expand")
        model_address = get_config("ai.table_extract.address")
        if not model_address:
            raise Exception("need ai.table_extract.address")
        self.client = AIClient(address=model_address)

    def train(self, dataset, **kwargs):
        return

    def predict(self, elements, **kwargs):
        answers = []
        tbls = []
        sylls = []
        top_key = self.config["path"][:]
        for element in elements:
            if element["class"] != "TABLE":
                continue
            syll = [t["title"] for t in self.pdfinsight.find_syllabuses_by_index(element["index"])]
            tbls.append(element)
            sylls.append(syll)

        # _key = '前五客户'
        # if any(_key in x for x in top_key):
        #     import time
        #     import json
        #     with open(f'/tmp/table_ai_errors_{_key}_{int(time.time()*1000)}.json', "w") as error_fp:
        #         json.dump(
        #             {"tbls": tbls, "top_key": top_key, "bot_keys": self.columns, "sylls": sylls},
        #             error_fp,
        #             indent=4,
        #             ensure_ascii=False,
        #         )
        #     print(f'dump for {_key}!')

        try:
            all_result = self.client.predict(
                tbls=tbls, top_key=top_key, bot_keys=self.columns, sylls=sylls, expand=self.expand
            )
        except Exception as ex:
            logging.error(ex)
            # import time
            # import json
            # with open(f'/tmp/table_ai_errors_{int(time.time()*1000)}.json', "w") as error_fp:
            #     json.dump(
            #         {"tbls": tbls, "top_key": top_key, "bot_keys": self.columns, "sylls": sylls, "error": str(ex)},
            #         error_fp,
            #         indent=4,
            #         ensure_ascii=False,
            #     )
        else:
            for tbl, res in zip(tbls, all_result):
                if not res or res == "use_rule":
                    continue
                for group in res:
                    answer = {}
                    for key, cellidx in zip(self.columns, group):
                        if not cellidx:
                            continue
                        answer[key] = ResultOfPredictor([TblResult([f"{cellidx[0]}_{cellidx[1]}"], tbl)])
                    answers.append(answer)
        return answers

    def predict_just_table(self, elements):
        answers = []
        for element in elements:
            table_answer = {}
            if element["class"] != "TABLE":
                continue
            for col in self.columns:
                if col in ("（表格）", ">表格<"):
                    # 大表格，取整个表格
                    table_answer[col] = ResultOfPredictor([TblResult([], element)])
                elif col == "币种" or (col.startswith("<") and "单位" in col):
                    _answer = self.find_special_attr(col, element)
                    if _answer:
                        table_answer[col] = _answer
                else:
                    # 其他字段，pass
                    pass
            if table_answer:
                answers.append(table_answer)
        return answers
