import csv

from remarkable.common.util import clean_txt, loop_wrapper
from remarkable.models.new_file import NewFile
from remarkable.pw_models.model import NewAnswer
from remarkable.pw_models.question import NewQuestion

DUMP_PATH = "./私募基金合同_基金投资范围.csv"


async def fetch_all_answers(mid):
    files = await NewFile.find_by_kwargs(delegate="all")
    rows = [["file_id", "label_answer", "url"]]
    for file in files:
        question = await NewQuestion.find_by_fid_mid(file.id, mid)
        if not question:
            continue
        label_answer = await NewAnswer.find_standard(qid=question.id)
        if not label_answer:
            continue
        for item in label_answer.data["userAnswer"]["items"]:
            if "基金投资范围" in item["key"]:
                answer_texts = []
                for data_item in item["data"]:
                    boxes = data_item["boxes"]
                    for box_info in boxes:
                        answer_texts.append(clean_txt(box_info["text"]))
                rows.append(
                    [
                        file.id,
                        "".join(answer_texts),
                        f"http://bj.cheftin.cn:22103/#/search?fileid={file.id}",
                    ]
                )

    return rows


def export_to_csv(rows):
    with open(DUMP_PATH, "w", newline="") as csv_file:
        writer = csv.writer(csv_file)
        writer.writerows(rows)


@loop_wrapper
async def main():
    rows = await fetch_all_answers(mid=7)
    export_to_csv(rows)


if __name__ == "__main__":
    main()
