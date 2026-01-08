from remarkable.common.pattern import PatternCollection
from remarkable.common.util import clean_txt
from remarkable.pdfinsight.reader import PdfinsightSyllabus
from remarkable.predictor.ccxi_predictor.models.fake_model import FakeModel
from remarkable.predictor.ccxi_predictor.models.qualification_criteria import start_serial_num_pattern
from remarkable.predictor.mold_schema import SchemaItem
from remarkable.predictor.schema_answer import OutlineResult

base_flag_path = PatternCollection(r"基础资产")
special_invalid_pattern = PatternCollection(
    [
        r"包括初始基础资产和后续入池基础资产",
        r"基础资产应?包括初始基础资产及新增基础资产",
        r"基础资产清单中所列示的基础交易文件项下",
    ]
)


class RevolvingPurchaseAssets(FakeModel):
    def __init__(self, options: dict, schema: SchemaItem, predictor):
        super(RevolvingPurchaseAssets, self).__init__(options, schema, predictor=predictor)

    def train(self, dataset, **kwargs):
        pass

    def predict_schema_answer(self, elements):
        answer_results = []
        sections = self.parse_sections()

        para_flag = PatternCollection(self.config.get("para_flag"))

        special_keyword_pattern = (
            PatternCollection(self.config.get("special_keyword")) if self.config.get("special_keyword") else None
        )
        for flag, section in sections.items():
            if not para_flag.nexts(flag):
                continue
            base_flag_match = base_flag_path.nexts(flag)
            para_range = {"range": (section[0]["index"], section[-1]["index"] + 1)}
            page_box = PdfinsightSyllabus.syl_outline(para_range, self.pdfinsight, include_title=True)
            text = "\n".join(i["text"] for i in page_box)
            if base_flag_match and special_invalid_pattern.nexts(clean_txt(text)):
                continue
            answer_results.extend(self.parse_answer_from_outline(page_box, text, special_keyword_pattern))
            if not self.multi and answer_results:
                break
        return answer_results

    def parse_answer_from_outline(self, page_box, text, special_keyword_pattern=None):
        answer_results = []
        if special_keyword_pattern and not special_keyword_pattern.nexts(clean_txt(text)):
            return answer_results
        elements = []
        for box in page_box:
            box["text"] = start_serial_num_pattern.sub("", box["text"])
            elements.extend(box["elements"])
        if not elements:
            return answer_results
        element_results = [OutlineResult(page_box=page_box, text=text, element=elements[0])]
        answer_result = self.create_result(element_results, text=text, column=self.schema.name)
        answer_results.append(answer_result)
        return answer_results
