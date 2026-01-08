import re

from remarkable.common.storage import localstorage
from remarkable.common.util import loop_wrapper
from remarkable.models.new_file import NewFile
from remarkable.pdfinsight.reader import PdfinsightReader
from remarkable.plugins.predict.models.sse.other_related_agencies import clean_text

P_IGNORE_TEXT = re.compile(r"[A-Za-z]+$|（职业）")
P_SPLIT = re.compile(r"(?:\d+\-+)+\d*")


@loop_wrapper
async def load_words_from_pdf(fid):
    file = await NewFile.find_by_id(fid)
    reader = PdfinsightReader(localstorage.mount(file.pdfinsight_path()))

    texts = set()
    for table in reader.find_tables_by_pattern([re.compile(r"[大中小细]类")]):
        if "中类" in clean_text(table["cells"]["0_0"]["text"]):
            for index, item in table["cells"].items():
                row, col = [int(i) for i in index.split("_")]
                if row == 0:
                    continue
                if col != 3:
                    continue
                for word in P_SPLIT.split(clean_text(item["text"])):
                    text = P_IGNORE_TEXT.sub("", word)
                    if text:
                        texts.add(text)

    for item in sorted(texts, key=len):
        print(item)


if __name__ == "__main__":
    load_words_from_pdf(623)
