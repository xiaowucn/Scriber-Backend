from remarkable.common.storage import localstorage
from remarkable.common.util import clean_txt, loop_wrapper
from remarkable.config import get_config
from remarkable.models.new_file import NewFile
from remarkable.pdfinsight.reader import PdfinsightReader
from remarkable.pw_models.question import NewQuestion


@loop_wrapper
async def print_word_answer(mid, schema_word=None):
    """
    打印指定schema字段的答案
    """
    files = await NewFile.list_by_range(mid)
    for file in files:
        reader = PdfinsightReader(localstorage.mount(file.pdfinsight_path()))
        question = await NewQuestion.find_by_fid_mid(file.id, mid)
        answer = await question.get_user_merged_answer()
        if not answer:
            continue
        print("\n")
        print(f"http://{get_config('web.domain')}/#/search?fileid={file.id}")
        print("+" * 30)
        answers = [
            # question.preset_answer['userAnswer']['items'],
            answer["userAnswer"]["items"],
        ]
        for items in answers:
            for item in items:
                if schema_word not in item["key"]:
                    continue
                answer_elements_index = []
                for data_item in item["data"]:
                    boxes = data_item["boxes"]
                    answer_texts = []
                    answer_elements = set()
                    for box_info in boxes:
                        outline = box_info["box"]
                        page = box_info["page"]
                        for _, elt in reader.find_elements_by_outline(page, list(outline.values())):
                            if not elt:
                                continue
                            answer_texts.append(clean_txt(box_info["text"]))
                            answer_elements.add(clean_txt(elt.get("text", "")))
                            answer_elements_index.append(elt["index"])
                    print("".join(answer_elements))
                    print("-" * 30)
                    print("".join(answer_texts))
                    print("+" * 30)
                if not answer_elements_index:
                    continue
                last_element_index = sorted(answer_elements_index)[-1]
                _type, elt = reader.find_element_by_index(last_element_index + 1)
                # print('********** next anchor')
                # print(clean_txt(elt['text']))
                # _type, elt = reader.find_element_by_index(last_element_index + 2)
                # print('********** next anchor')
                # print(clean_txt(elt.get('text', '')))


if __name__ == "__main__":
    print_word_answer(16, "岗位:0")
