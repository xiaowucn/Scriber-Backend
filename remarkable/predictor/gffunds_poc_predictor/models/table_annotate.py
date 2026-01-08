from remarkable.common.pattern import PatternCollection
from remarkable.common.util import clean_txt
from remarkable.predictor.models.syllabus_elt_v2 import SyllabusEltV2
from remarkable.predictor.schema_answer import OutlineResult


class TableAnnotate(SyllabusEltV2):
    def __init__(self, options, schema, predictor=None):
        super().__init__(options, schema, predictor=predictor)
        self.annotate_pattern = PatternCollection(self.get_config("annotate_pattern", r"^注"))
        self.note_pattern = PatternCollection(self.get_config("note_pattern", []))
        self.syllabus_pattern = PatternCollection([r"^[\d]{2}[.][\d]+", r"^[\d][.][\d]+"])

    @property
    def break_pattern(self):
        return PatternCollection(self.get_config("break_pattern", []))

    def predict_schema_answer(self, elements):
        self.load_model_data()
        answer_results = []
        for col in self.columns:
            model_data = self.get_model_data(col)
            if not model_data:
                return answer_results
            aim_syllabuses = self.get_aim_syllabus(
                model_data, syllabus_black_list=PatternCollection(self.get_config("syllabus_black_list", column=col))
            )
            if not aim_syllabuses:
                return answer_results
            page_box = self.find_table_annotate(aim_syllabuses)
            if not page_box:
                return answer_results
            text = "\n".join(i["text"] for i in page_box)
            elements = self.get_elements_from_page_box(page_box)
            if not elements:
                continue
            element_results = [
                OutlineResult(page_box=page_box, text=text, element=elements[0], origin_elements=elements)
            ]
            answer_result = self.create_result(element_results, text=text, column=col)
            answer_results.append(answer_result)
        return answer_results

    def find_table_annotate(self, syllabuses):
        elements = []
        for aim_syl in syllabuses:
            table_index = None
            start, end = aim_syl["range"]
            # 没有表格存在，但是有注释说明，表明相关信息，一般来说不会以注释开头
            last_type = None
            for idx in range(start + 1, end):
                elt_type, elt = self.pdfinsight.find_element_by_index(idx)
                clean_text = clean_txt(elt.get("text") or "")
                if last_type in ("PAGE_HEADER", "PAGE_FOOTER") and "text" in elt and len(elt["text"]) < 5:
                    # https://gitpd.paodingai.com/cheftin/docs_scriber/-/issues/2621#note_362327
                    # 跳过页眉页脚后的短文本
                    continue
                if elt_type == "PARAGRAPH" and not self.annotate_pattern.nexts(clean_text):
                    if self.ignore_pattern.nexts(clean_text):
                        continue
                    if self.break_pattern.patterns and self.break_pattern.nexts(clean_text):
                        return self.pdfinsight.elements_outline(elements)

                    if self.note_pattern.nexts(clean_text):
                        elements.append(elt)
                    elif elt["syllabus"] == aim_syl["index"]:
                        elements.append(elt)

                if elt_type in ["TABLE", "IMAGE"]:
                    elements.clear()
                    table_index = idx
                    break
                last_type = elt_type

            if table_index:
                # 具有表格，遍历获取表格下边的注释内容
                for idx in range(table_index + 1, end):
                    elt_type, elt = self.pdfinsight.find_element_by_index(idx)
                    clean_text = clean_txt(elt.get("text") or "")
                    if self.break_pattern and self.break_pattern.nexts(clean_text):
                        break
                    if self.ignore_pattern and self.ignore_pattern.nexts(clean_text):
                        continue

                    if elt_type == "PARAGRAPH" and self.annotate_pattern.nexts(clean_text):
                        for i in range(idx, aim_syl["range"][1]):
                            elt_type, elt = self.pdfinsight.find_element_by_index(i)
                            if elt and elt_type == "PARAGRAPH":
                                clean_text = clean_txt(elt["text"])
                                if self.syllabus_pattern.nexts(clean_text):
                                    break

                                if self.break_pattern and self.break_pattern.nexts(clean_text):
                                    break
                                if self.ignore_pattern and self.ignore_pattern.nexts(clean_text):
                                    continue
                                elements.append(elt)
                        break

            if elements:
                break

        return self.pdfinsight.elements_outline(elements)
