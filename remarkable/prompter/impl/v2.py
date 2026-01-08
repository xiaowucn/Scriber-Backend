import logging

from remarkable import config
from remarkable.pdfinsight.reader import PdfinsightReader
from remarkable.prompter.element import element_info


class AnswerPrompterV2:
    def __init__(self, schema_id, vid=0):
        self.files = []
        self.attributes = {}
        self.schema_id = schema_id
        self.vid = vid
        self.timestamp = 0

    def elements(self, pdfinsight_reader):
        _elements = []
        _elements.extend(
            [para for para in pdfinsight_reader.paragraphs if "......" not in para["text"] and not para.get("fragment")]
        )
        _elements.extend([elt for elt in pdfinsight_reader.tables if not elt.get("fragment")])
        _elements.extend(pdfinsight_reader.page_headers)
        return _elements

    def prompt_all(self, pdfinsight_path, **kwargs):
        file_id = kwargs.get("file_id") or 0
        reader = PdfinsightReader(pdfinsight_path, data=kwargs.get("pdfinsight_data"))
        if not self.elements(reader):
            logging.warning("empty pdfinsight %s", file_id)
            return {}
        doc_elements = {e.get("index"): element_info(e.get("index"), e, reader, {}) for e in self.elements(reader)}

        from remarkable.prompter.utils import pred

        res = pred(
            self.schema_id,
            self.vid,
            pred_start=file_id,
            pred_end=file_id,
            dict_data={file_id: doc_elements},
            use_syllabuses=config.get_config("prompter.use_syllabuses", True),
            tokenization=(config.get_config("prompter.tokenization") or None),
            context_length=config.get_config("prompter.context_length", 1),
            rules_use_post_process=(config.get_config("prompter.post_process") or []),
            separate_paragraph_table=config.get_config("prompter.separate_paragraph_table", True),
        )
        if not res:
            return None

        prompt_result = {}
        for aid, items in res.get(file_id, {}).items():
            prompt_result[aid] = []
            for item in items:
                etype, ele = reader.find_element_by_index(item["element_index"])
                prompt_result[aid].append((item["score"], ele, [], etype))

        return prompt_result
