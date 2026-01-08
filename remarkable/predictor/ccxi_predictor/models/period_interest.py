from copy import deepcopy

from remarkable.common.pattern import PatternCollection
from remarkable.common.util import clean_txt
from remarkable.predictor.ccxi_predictor import Iduciary
from remarkable.predictor.models.syllabus_elt import SyllabusElt
from remarkable.predictor.mold_schema import SchemaItem
from remarkable.predictor.schema_answer import ParagraphResult

col_patterns = deepcopy(Iduciary.col_patterns["封包期利息是否入池"])
col_patterns.pop("不适用")


class PeriodInterest(SyllabusElt):
    def __init__(self, options: dict, schema: SchemaItem, predictor):
        super(PeriodInterest, self).__init__(options, schema, predictor=predictor)

    def predict_schema_answer(self, elements):
        ret = []
        answer_results = super(PeriodInterest, self).predict_schema_answer(elements)
        if not answer_results:
            return ret
        answer_result = answer_results[0]
        outlines = answer_result.element_results[0].page_box
        for outline in outlines:
            page, outline = outline["page"], outline["outline"]
            elements = self.pdfinsight.find_elements_by_outline(page, outline)
            for ele_type, element in elements:
                if ele_type != "PARAGRAPH":
                    continue
                for key, item in col_patterns.items():
                    if PatternCollection(item).nexts(clean_txt(element["text"])):
                        para_result = [ParagraphResult(element, element["chars"])]
                        answer_result = self.create_result(
                            para_result, text=element["text"], column=self.schema.name, value=key
                        )
                        if answer_result:
                            ret.append(answer_result)
                            break
                if ret:
                    break
            if ret:
                break
        if not ret:
            return answer_results
        return ret
