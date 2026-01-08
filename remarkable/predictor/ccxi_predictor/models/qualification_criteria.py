from remarkable.common.pattern import PatternCollection
from remarkable.common.util import clean_txt
from remarkable.pdfinsight.reader import PdfinsightSyllabus
from remarkable.predictor.ccxi_predictor.models.fake_model import FakeModel
from remarkable.predictor.mold_schema import SchemaItem
from remarkable.predictor.schema_answer import CharResult, OutlineResult

start_serial_num_pattern = PatternCollection(
    [
        r"^[(（]?[a-zA-Z\d]+[)）]",
    ]
)


class QualificationCriteria(FakeModel):
    def __init__(self, options: dict, schema: SchemaItem, predictor):
        super(QualificationCriteria, self).__init__(options, schema, predictor=predictor)

    def train(self, dataset, **kwargs):
        pass

    def predict_schema_answer(self, elements):
        answer_results = []
        sections = self.parse_sections()

        para_flag = PatternCollection(self.config.get("para_flag"))
        invalid_flag = PatternCollection(self.config.get("invalid_flag")) if self.config.get("invalid_flag") else None
        content_pattern = (
            PatternCollection(self.config.get("content_pattern")) if self.config.get("content_pattern") else None
        )
        special_keyword_pattern = (
            PatternCollection(self.config.get("special_keyword")) if self.config.get("special_keyword") else None
        )
        for flag, section in sections.items():
            if not para_flag.nexts(flag):
                continue
            if invalid_flag and invalid_flag.nexts(flag):
                continue
            if content_pattern:
                # 定位到段落后精确提取
                for para in section:
                    matcher = content_pattern.nexts(clean_txt(para["text"]))
                    if matcher:
                        dst_chars = self.get_dst_chars_from_matcher(matcher, para)
                        if not dst_chars:
                            continue
                        answer_result = self.create_result([CharResult(para, dst_chars)], column=self.schema.name)
                        answer_results.append(answer_result)
                        break

            else:
                para_range = {"range": (section[0]["index"], section[-1]["index"] + 1)}
                answer_results.extend(self.parse_answer_from_outline(para_range, special_keyword_pattern))
            if not self.multi and answer_results:
                break
        return answer_results

    def parse_answer_from_outline(self, para_range, special_keyword_pattern=None):
        answer_results = []
        page_box = PdfinsightSyllabus.syl_outline(para_range, self.pdfinsight, include_title=True)
        text = "\n".join(i["text"] for i in page_box)
        if special_keyword_pattern and not special_keyword_pattern.nexts(clean_txt(text)):
            return answer_results
        elements = []
        for box in page_box:
            box["text"] = start_serial_num_pattern.sub("", box["text"])
            elements.extend(box["elements"])
        if not elements:
            return answer_results
        element_results = [OutlineResult(page_box=page_box, text=text, element=elements[0], origin_elements=elements)]
        answer_result = self.create_result(element_results, text=text, column=self.schema.name)
        answer_results.append(answer_result)
        return answer_results
