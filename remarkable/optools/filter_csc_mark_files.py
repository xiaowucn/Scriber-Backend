import asyncio
import csv

from pdfparser.pdftools.pdf_doc import PDFDoc
from playhouse.postgres_ext import ServerSide

from remarkable.answer.reader import AnswerReader
from remarkable.common.constants import JSONConverterStyle
from remarkable.db import pw_db
from remarkable.models.new_file import NewFile
from remarkable.pw_models.model import NewAnswer
from remarkable.pw_models.question import NewQuestion


def file_iter():
    """找出所有含有斜杠的文件"""
    with pw_db.allow_sync():
        for file in ServerSide(NewFile.select().order_by(NewFile.id.desc())):
            path = file.pdf_path(abs_path=True)
            try:
                doc = PDFDoc(path)
                has_slash = False
                for page in doc.pages.values():
                    for item in page.get("texts", []):
                        if "/" in (item.get("text") or ""):
                            has_slash = True
                            break
                    if has_slash:
                        break
                if has_slash:
                    yield file
            except:  # noqa
                pass


async def main():
    bids = ["bid价格", "bid数量", "bid价格类型", "bid是否请示"]
    ofrs = ["ofr价格", "ofr数量", "ofr价格类型", "ofr是否请示"]
    with open("/tmp/out.csv", "w", newline="") as f:
        csv_writer = csv.writer(f)
        csv_writer.writerow(["file_id", "file_name", "url", "has_mark"])
        for file in file_iter():
            has_mark = False
            for qid, mid, data in await pw_db.execute(  # noqa
                NewAnswer.select(NewAnswer.qid, NewQuestion.mold, NewAnswer.data)
                .where(
                    NewAnswer.qid == NewQuestion.id,
                    NewFile.id == file.id,
                    NewAnswer.data.is_null(False),
                )
                .join(NewQuestion, on=(NewAnswer.qid == NewQuestion.id))
                .join(NewFile, on=(NewQuestion.fid == NewFile.id))
                .order_by(NewAnswer.id.desc())
                .namedtuples()
            ):
                try:
                    answer = AnswerReader(data).to_json(JSONConverterStyle.ENUM)
                except:  # noqa
                    continue
                for item in answer["报价信息"]:
                    # 标记有标注 bid 和 ofr 的数据
                    if any(item.get(k) for k in bids) and any(item.get(k) for k in ofrs):
                        has_mark = True
                        break
                if has_mark:
                    break
            csv_writer.writerow(
                [
                    file.id,
                    file.name,
                    f"http://scriber-csc-mark.test.paodingai.com/#/project/remark/"
                    f"{qid}?projectId={file.pid}&treeId={file.tree_id}&fileId={file.id}&schemaId={mid}",
                    has_mark,
                ]
            )


if __name__ == "__main__":
    asyncio.run(main())
