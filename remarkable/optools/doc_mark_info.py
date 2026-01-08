import asyncio
import json
import logging
import os
from collections import defaultdict

from remarkable.common.storage import localstorage
from remarkable.models.new_file import NewFile
from remarkable.pdfinsight.reader import PdfinsightReader
from remarkable.service.prompter import get_files_data


async def mark_info(schema_id, limit=None, start=None, end=None, cond=None):
    rows = await get_files_data(schema_id, limit, start, end, cond)
    for file_id, pdfinsight, _, _, answer in rows:
        pdfinsight_path = NewFile.get_path(pdfinsight)
        if not answer or not os.path.exists(localstorage.mount(pdfinsight_path)):
            logging.info(f"文件{file_id=}没有答案或者pdfinsight不存在")
            continue
        reader = PdfinsightReader(localstorage.mount(pdfinsight_path))
        marker_answers = []
        combined_answers = defaultdict(list)
        for item in answer.get("userAnswer", {}).get("items", []):
            index = []
            main_name, sub_name = get_schema_name(json.loads(item["key"]))
            text = ""
            pages = []
            for item_data in item.get("data", []):
                for box in item_data.get("boxes", []):
                    if not box["box"] or None in box["box"].values():
                        logging.error("box is None")
                        continue
                    text += f"{box['text']}"
                    page = box["page"]
                    pages.append(page)
                    outline = (
                        box["box"]["box_left"],
                        box["box"]["box_top"],
                        box["box"]["box_right"],
                        box["box"]["box_bottom"],
                    )
                    for _, element in reader.find_elements_by_outline(page, outline):
                        eidx = element.get("index")
                        index.append(eidx)
            if sub_name:
                combined_answers[main_name].append({sub_name: text, "index": index, "page": pages})
            else:
                marker_answers.append({main_name: text, "index": index, "page": pages})


def get_schema_name(key_path: list):
    """
    key_path: ['广发招募说明书:0', '注册登记人明细:1', '公司名称2（注册登记人）:0']
    """
    if len(key_path) <= 2:
        main_name = "-".join(p.split(":")[0] for p in key_path[1])
        sub_name = None
    else:
        main_name = key_path[1]
        sub_name = "-".join(p.split(":")[0] for p in key_path[2:])

    return main_name, sub_name


if __name__ == "__main__":
    asyncio.run(mark_info(schema_id=3, start=64, end=64))
