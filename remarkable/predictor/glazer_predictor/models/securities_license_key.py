import re

from remarkable.predictor.models.partial_text import PartialText

p_pattern = re.compile(r"(证监许可|上证函).*号")


class SecuritiesLicenseKey(PartialText):
    def predict_schema_answer(self, elements):
        is_aim_elt = False
        for element in elements:
            if p_pattern.search(element.get("text", "")):
                is_aim_elt = True
                break
        if not is_aim_elt:
            elements = self.pdfinsight.find_paragraphs_by_pattern([p_pattern], multi=False)
        return super(SecuritiesLicenseKey, self).predict_schema_answer(elements)
