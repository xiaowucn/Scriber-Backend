from remarkable.pdfinsight.reader import PdfinsightReader


def split_template_interdoc(interdoc_path):
    reader = PdfinsightReader(interdoc_path)
    top_3_syllabuses = [syllabus for syllabus in reader.syllabuses if syllabus.get("level") <= 3]
    top_3_parents = {syllabus["parent"] for syllabus in top_3_syllabuses}
    rule_syllabuses = [syllabus for syllabus in top_3_syllabuses if syllabus["index"] not in top_3_parents]

    rules_text = []
    for syllabus in rule_syllabuses:
        elements = reader.get_elements_by_syllabus(syllabus)
        element_texts = [ele["text"] for ele in elements if ele.get("text")]
        if element_texts:
            rules_text.append("\n".join(element_texts))

    return rules_text
