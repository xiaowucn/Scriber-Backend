from remarkable.prompter.manager import prompter_manager


def predict_crude_answer(
    pdfinsight_path, mold_id, mold_data, godmode=False, vid=0, known_answer=None, file_id=None, pdfinsight_data=None
):
    prompter = prompter_manager.get_schema_prompter(mold_id, godmode, vid)
    if not prompter:
        return None

    meta = {
        "file_id": file_id,
        "mold_data": mold_data,
        "known_answer": known_answer,
    }
    if known_answer:
        meta["known_answer"] = known_answer
    if pdfinsight_data:
        meta["pdfinsight_data"] = pdfinsight_data
    res = prompter.prompt_all(pdfinsight_path, **meta)
    if not res:
        return None

    answer = {}
    for aid, items in res.items():
        answer[aid] = []
        for proba, ele, keywords, etype in items:
            text = ele.get("text")
            if etype == "TABLE":
                text = ele.get("title") or table_element_content_text(ele)
            answer[aid].append(
                {
                    "score": proba,
                    "element_index": ele.get("index"),
                    "text": text,
                    "page": ele.get("page"),
                    "outline": ele.get("outline"),
                    "element_type": etype,
                    "keywords": [(k.text, k.score) for k in keywords[:12]],
                    "element": ele if godmode else None,
                }
            )
    return answer


def table_element_content_text(ele):
    def cell_ordering(row_and_col):
        row, col = row_and_col.split("_")
        return int(row) * 1000 + int(col)

    return "|".join([v.get("text") for k, v in sorted(ele.get("cells").items(), key=lambda x: cell_ordering(x[0]))])
