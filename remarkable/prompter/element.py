import re


def element_info(eidx: int, ele, reader, attr_mapping: dict[int, set]):
    p_cut_cells = re.compile(r"[0-9\n,.]")
    einfo = {
        "type": ele.get("type"),
        "attrs": list(attr_mapping.get(eidx, [])),
        "page": ele.get("page"),
        "outline": ele.get("outline"),
        "class": ele.get("class"),
        "syllabuse": reader.find_syllabuses_by_index(eidx),
    }

    if ele.get("class") == "TABLE":
        einfo["class"] = "TABLE"
        table_cells = ele.get("cells")
        temp = []
        for value in table_cells.values():
            temp.append(p_cut_cells.sub("", value.get("text", "")))
        einfo["text"] = "\n".join(temp)
    if ele.get("class") in {"PARAGRAPH", "PAGE_HEADER", "PAGE_FOOTER"}:
        einfo["class"] = ele["class"]
        einfo["text"] = ele.get("text") or ""
    return einfo
