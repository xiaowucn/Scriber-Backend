from remarkable.predictor.models.table_row import TableRow
from remarkable.predictor.utils import filter_table_cross_page


class RegisterHolders(TableRow):
    def predict_schema_answer(self, elements):
        if not elements:
            elements = get_elements_from_all_pages(self.pdfinsight)
        ret = super(RegisterHolders, self).predict_schema_answer(elements)
        return ret


def get_elements_from_all_pages(pdfinsight):
    elements = []
    for _, items in pdfinsight.element_dict.items():
        for item in items:
            if item.data["class"] == "TABLE":
                _, element = pdfinsight.find_element_by_index(item.index)
                if not element:
                    continue
                elements.append(element)
    return filter_table_cross_page(elements)
