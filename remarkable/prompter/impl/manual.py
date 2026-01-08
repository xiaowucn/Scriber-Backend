from remarkable.common.schema import Schema, attribute_id
from remarkable.pdfinsight.reader import PdfinsightReader


class ManualAnswerPrompter:
    def __init__(self, schema_id):
        self.files = []
        self.attributes = {}
        self.schema_id = schema_id
        self.timestamp = 0
        self.element_finder = {}
        self.reader = None
        # self.cache = {}

    def find_attr_related_elements(self, path):
        key = path[1]
        # if key in self.cache:
        #     return self.cache[key]
        if key in self.element_finder:
            return self.element_finder[key](path)
        for reg_key in self.element_finder:
            if key.startswith(reg_key):
                return self.element_finder[reg_key](path)
        return []

    def find_elements(self, syll_patterns=None, para_patterns=None, table_patterns=None):
        """
        根据 patterns 查找内容，这里 三个 patterns 都是数组，满足一组 syll + para/table 即可
        """
        res = []
        ranges = []
        if syll_patterns:
            sylls = []
            for pattern in syll_patterns:
                sylls.extend(self.reader.find_sylls_by_pattern(pattern))
            ranges = [syll["range"] for syll in sylls]
        else:
            ranges.append((0, float("Inf")))

        for start, end in ranges:
            for pattern in table_patterns or []:
                res.extend(self.reader.find_tables_by_pattern(pattern, start, end))
            for pattern in para_patterns or []:
                res.extend(self.reader.find_paragraphs_by_pattern(pattern, start, end))
        return res

    def prompt_all(self, pdfinsight_path, **kwargs):
        mold = kwargs.get("mold_data")
        if not mold:
            raise Exception("mold_data is needed")
        self.reader = PdfinsightReader(pdfinsight_path, data=kwargs.get("pdfinsight_data"))

        res = {}
        schema = Schema(mold)
        for key_path in schema.iter_schema_attr():
            items = []
            aid = attribute_id(key_path)
            elements = self.find_attr_related_elements(key_path)
            print("%s: %s" % (aid, len(elements)))
            for ele in elements:
                if ele["index"] not in [item[1]["index"] for item in items]:
                    items.append((1, ele, [], ele["class"]))
            res[aid] = items
        return res
