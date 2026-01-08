from dataclasses import dataclass

from remarkable.common.util import box_to_outline, clean_txt, index_in_space_string


@dataclass
class AnswerLocation:
    answer_text: str
    element: dict
    first_box: dict = None
    first_outline: tuple = None
    first_box_text: str = None
    page: int = None
    element_class: str = ""

    def __post_init__(self):
        if self.element:
            self.element_class = self.element["class"]
        if self.first_box:
            self.first_outline = self.first_outline or box_to_outline(self.first_box["box"])
            self.page = self.page or int(self.first_box["page"])
            self.first_box_text = self.first_box_text or self.first_box["text"]

    def details(self, pdfinsight_reader):
        start = None
        end = None
        row = None
        col = None
        precise_element = None

        if not (self.element and self.answer_text):
            return start, end, row, col

        if self.element_class == "TABLE" and self.first_outline:
            aim_cell_idx = pdfinsight_reader.find_cell_idx_by_outline(self.element, self.first_outline, self.page)
            if aim_cell_idx:
                row, col = aim_cell_idx.split("_")
                precise_element = self.element["cells"].get(aim_cell_idx)

        elif self.element_class == "PARAGRAPH":
            precise_element = self.element

        _, chars_before_outline = pdfinsight_reader.find_chars_before_outline(self.page, self.first_outline)
        text_before_outline = "".join(x["text"] for x in chars_before_outline)
        if precise_element:
            if self.first_box_text:
                start, end = self.get_char_range(precise_element["text"], self.first_box_text, text_before_outline)
            if start is None:
                start, end = self.get_char_range(precise_element["text"], self.answer_text, text_before_outline)

        return start, end, row, col

    @staticmethod
    def get_char_range(element_text, text, text_before_outline):
        start, end = None, None
        if element_text.startswith(text_before_outline):
            start = len(text_before_outline)
        else:
            start = element_text.find(text)
        if start != -1:
            end = start + len(text)
        else:
            c_start = clean_txt(element_text).find(clean_txt(text))
            if c_start != -1:
                c_end = c_start + len(text)
                start, end = index_in_space_string(element_text, (c_start, c_end))

        return start, end
