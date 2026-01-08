from remarkable.common.pattern import PatternCollection
from remarkable.predictor.models.para_match import ParaMatch
from remarkable.predictor.schema_answer import CharResult, ParagraphResult


class ReBuyDate(ParaMatch):
    def create_content_result(self, element, matched=None, use_cleaned_text=False):
        chars = element.get("chars", [])
        content_pattern = PatternCollection(self.config.get("content_pattern"))
        matches = list(content_pattern.finditer(element["text"]))
        # 时间一般会命中两处, 一般购买时间会在最后提到
        if matches:
            start, end = matches[-1].span("dst")
            chars = chars[start:end]
            return [CharResult(element, chars)]
        return [ParagraphResult(element, chars)]
