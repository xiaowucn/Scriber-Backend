from remarkable.predictor.predict import ParaResult, ResultOfPredictor

from .model_base import PredictModelBase


class MultiParas(PredictModelBase):
    model_intro = {
        "doc": "提取多个段落作为结果",
        "name": "多个段落",
        "hide": True,
    }

    def __init__(self, *args, **kwargs):
        super(MultiParas, self).__init__(*args, **kwargs)
        self.config.update({"multi_elements": True})
        self.need_training = False

    @classmethod
    def model_template(cls):
        template = {}
        default_model_template = cls.default_model_template()
        default_model_template.update(template)
        return default_model_template

    def train(self, dataset, **kwargs):
        model = {}
        self.model = model

    def predict(self, elements, **kwargs):
        score = kwargs.get("score", 0)
        if score < self.config.get("threshold", 0.5):
            return []
        answers = []
        elements = elements or []
        for element in elements:
            answer = {}
            for col in self.columns:
                if element["class"] == "PARAGRAPH":
                    answer[col] = ResultOfPredictor([ParaResult(element["chars"], element)], score=element.get("score"))
            answers.append(answer)
        return answers

    def predict_with_elements(self, crude_answers, **kwargs):
        index_list = []
        candidates = self._get_element_candidates(
            crude_answers,
            self.config["path"],
            priors=self.config.get("element_candidate_priors", []),
            limit=self.config.get("element_candidate_count", 10),
        )
        for item in candidates:
            etype, ele = self.pdfinsight.find_element_by_index(item["element_index"])
            answers = self.predict([ele], score=item.get("score", 0), **kwargs)
            if answers:
                index_list.append(ele["index"])
        ele_results = []
        if not index_list:
            return ele_results
        index_list = self.fix_merge_index(index_list)
        col = self.config.get("path")[-1]
        answer_list = []
        for _index in range(index_list[0], index_list[-1] + 1):
            etype, element = self.pdfinsight.find_element_by_index(_index)
            if etype == "PARAGRAPH":
                answer_list.append(ParaResult(element["chars"], element))
        answer = {col: ResultOfPredictor(answer_list)}
        etype, element = self.pdfinsight.find_element_by_index(index_list[0])
        ele_results.append(
            (
                element,
                [
                    answer,
                ],
            )
        )
        return ele_results

    def fix_merge_index(self, index_list):
        """
        获取合并元素块的index
        :param index_list:
        :return:
        """
        index_list = sorted(index_list)
        for _index in range(index_list[0] - 1, 0, -1):
            etype, element = self.pdfinsight.find_element_by_index(_index)
            if etype != "PARAGRAPH":
                continue
            if element.get("continued", False):
                index_list.insert(0, element["index"])
            else:
                break

        for _index in range(index_list[-1] + 1, 10000):
            etype, element = self.pdfinsight.find_element_by_index(_index)
            if etype != "PARAGRAPH":
                continue
            if element.get("continued", False):
                index_list.insert(0, element["index"])
            else:
                break
        return index_list
