import logging
from collections import defaultdict
from dataclasses import dataclass, field
from operator import itemgetter

from flashtext import KeywordProcessor

from remarkable.common.enums import NafmiiTaskType as TaskType
from remarkable.db import pw_db
from remarkable.models.nafmii import NafmiiFileInfo, SensitiveWord, WordType
from remarkable.models.new_file import NewFile
from remarkable.pdfinsight.reader import PdfinsightReader
from remarkable.plugins.nafmii.enums import OperationType
from remarkable.predictor.schema_answer import CellCharResult, CharResult

logger = logging.getLogger(__name__)


@dataclass
class _Predictor:
    reader: PdfinsightReader
    _word_processor: KeywordProcessor = field(init=False)

    def finditer(self):
        for para in self.reader.paragraphs:
            chapters = self.reader.find_syllabuses_by_index(para["syllabus"])
            positions = [chapter["title"] for chapter in chapters]
            for text, start, end in self._word_processor.extract_keywords(para["text"], span_info=True):
                yield (
                    text,
                    {
                        "data": [CharResult(para, para["chars"][start:end]).to_answer()],
                        "positions": positions,
                        "operation": OperationType.add,
                        "index": para["index"],
                    },
                )

        indices = set()
        for table in self.reader.tables:
            page_merged_table_index = table.get("page_merged_table")
            if isinstance(page_merged_table_index, int) and page_merged_table_index in indices:
                continue
            chapters = self.reader.find_syllabuses_by_index(table["syllabus"])
            positions = [chapter["title"] for chapter in chapters]
            for cell in table["cells"].values():
                if cell.get("dummy"):
                    continue
                for text, start, end in self._word_processor.extract_keywords(cell["text"], span_info=True):
                    yield (
                        text,
                        {
                            "data": [CellCharResult(table, cell["chars"][start:end], [cell]).to_answer()],
                            "positions": positions,
                            "operation": OperationType.add,
                            "index": table["index"],
                        },
                    )

            indices.add(table["index"])


@dataclass
class SensitiveWordPredictor(_Predictor):
    sensitive_words: dict[str, str]

    def __post_init__(self):
        self._word_processor = KeywordProcessor()
        self._word_processor.add_keywords_from_list(list(self.sensitive_words))

    def predict_answer(self):
        answer = defaultdict(list)
        for text, res in self.finditer():
            answer[self.sensitive_words[text]].append(res)

        return [{"key": key, "items": sorted(items, key=itemgetter("index"))} for key, items in answer.items()]


@dataclass
class KeywordPredictor(_Predictor):
    keywords: list[str]

    def __post_init__(self):
        self._word_processor = KeywordProcessor()
        self._word_processor.add_keywords_from_list(self.keywords)

    def predict_answer(self):
        answer = defaultdict(list)
        for text, res in self.finditer():
            answer[text].append(res)
        return [{"key": key, "items": sorted(items, key=itemgetter("index"))} for key, items in answer.items()]


async def predict_sensitive_word(file: NewFile):
    file_info = await NafmiiFileInfo.find_by_kwargs(file=file)
    if TaskType.T003 not in file_info.task_types:
        return []
    logger.info(f"start to predict sensitive word for file {file.id}")
    sys_ids = [0, file_info.sys_id]
    records = await pw_db.prefetch(
        SensitiveWord.select(SensitiveWord.name, SensitiveWord.type).where(SensitiveWord.sys_id.in_(sys_ids)),
        WordType.select(WordType.id, WordType.name),
    )
    sensitive_words = {word.name: word.type.name for word in records}
    predictor = SensitiveWordPredictor(PdfinsightReader(file.pdfinsight_path(abs_path=True)), sensitive_words)
    try:
        return predictor.predict_answer()
    finally:
        logger.info(f"finish to predict sensitive word for file {file.id}")


async def predict_keyword(file: NewFile):
    file_info = await NafmiiFileInfo.find_by_kwargs(file=file)
    if TaskType.T002 not in file_info.task_types:
        return []
    logger.info(f"start to predict keyword for file {file.id}")
    predictor = KeywordPredictor(PdfinsightReader(file.pdfinsight_path(abs_path=True)), file_info.keywords)
    try:
        return predictor.predict_answer()
    finally:
        logger.info(f"finish to predict keyword for file {file.id}")
