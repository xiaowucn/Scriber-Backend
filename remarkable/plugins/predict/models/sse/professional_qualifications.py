import re
from collections import Counter
from itertools import groupby

from remarkable.pdfinsight.reader import PdfinsightSyllabus
from remarkable.plugins.predict.models.sse.group_extract_base import GroupExtractBase
from remarkable.plugins.predict.models.sse.other_related_agencies import clean_text
from remarkable.plugins.predict.models.table_row import RowTable
from remarkable.predictor.predict import ParaResult, ResultOfPredictor, TblResult

pass_pattern = re.compile(r"业务[与和]技术|[（\(]?\d[）\)]?.*")
qualification_pattern = re.compile(r"资质|公司业务经营许可和认证情况")
not_qualification_name_pattern = re.compile(r"序号|(企业|公司)名称|证书编号")


class ProfessionalQualifications(GroupExtractBase):
    model_intro = {
        "doc": "根据目录模型进行分组，每组元素块利用其它模型进行提取",
        "name": "业务与技术-专业资质情况",
        "hide": True,
    }

    def __init__(self, mold, config, **kwargs):
        table_model = RowTable(mold, config, **kwargs)
        super(ProfessionalQualifications, self).__init__(mold, config, table_model, **kwargs)

    def predict_with_elements(self, crude_answers, **kwargs):
        results = []
        processed_elts = []
        chapter_features = self.model.get("chapter")
        if not chapter_features:
            return results
        for key in [k for k, v in chapter_features.most_common()]:
            syllabuses = self.pdfinsight.syllabus_reader.find_sylls_by_name(key.split("|"))
            if not syllabuses:
                continue
            aim_syllabus = syllabuses[-1]
            results.extend(self.predict_with_section(crude_answers, aim_syllabus, processed_elts, **kwargs))
        return results

    def predict_with_section(self, crude_answers, syllabus, processed_elts, **kwargs):
        results = []
        groups = self.group_elts(syllabus)
        for group in groups:
            result = []
            para_answers = self.main_partial_text.predict(group["para_elt"], **kwargs)
            table_elts = self.pdfinsight.filter_table_cross_page(group["table_elt"])
            group["table_elt"] = table_elts
            table_answers = self.main_table_model.predict(table_elts, **kwargs)
            if group["table_elt"]:
                # 有表格时 从表格前的三个段落中找答案 若都有答案则取最后一个
                result.extend(self.precess_table_answer(group, para_answers, table_answers))
            else:
                # 没有表格的情况下 将每个段落为一组
                for para_answer in para_answers:
                    if len(para_answer) < 2:  # 过滤到仅有一个答案的元素块
                        continue
                    result.append(para_answer)
            if result:
                results.append((None, result))
        return results

    def precess_table_answer(self, group, para_answers, table_answers):
        result = []
        share_answer = {}
        if para_answers:
            for para_answer in para_answers[-3:]:
                share_answer.update(para_answer)
            # 表格上方存在多组答案 file id 343
            for para_answer in para_answers:
                if len(para_answer) < 3:  # 过滤到仅有一个答案的元素块
                    continue
                result.append(para_answer)
        if table_answers:
            # 从表格前段落中找资质名称 持有人
            qualification_name = share_answer.get("资质名称")
            if not qualification_name and group.get("para_elt"):
                # partial_text 没有提取到资质名称 需指定目录或段落
                for elt in group.get("para_elt")[::-1]:
                    # 段落是标题
                    if elt["index"] == self.pdfinsight.syllabus_dict[elt["syllabus"]]["element"]:
                        ret_elt = elt
                        break
                else:
                    ret_elt = group["para_elt"][-1]
                qualification_name = ResultOfPredictor([ParaResult(ret_elt["chars"], ret_elt)])
            holder = share_answer.get("持有人")
            for row_answer in table_answers:
                if len(row_answer) < 3:  # 过滤到仅有一个答案的元素块
                    continue
                name_answers = self.get_cell_from_group(row_answer, "资质名称", group)
                is_match = any(not_qualification_name_pattern.search(clean_text(i)) for i in name_answers)
                if qualification_name and is_match:
                    row_answer["资质名称"] = qualification_name
                if holder:
                    row_answer["持有人"] = holder
                result.append(row_answer)
        else:
            answer = {}
            # 表格模型没有输出时 将表格元素块加到'(表格)'中
            answer.update({"（表格）": ResultOfPredictor([TblResult([], group["table_elt"][0])])})
            if share_answer.get("资质名称"):
                answer["资质名称"] = share_answer.get("资质名称")
            if share_answer.get("持有人"):
                answer["持有人"] = share_answer.get("持有人")
            result.append(answer)
        return result

    def get_cell_from_group(self, answer, col, group):
        cell_ids = []
        for i in answer[col].data:
            cell_ids.extend(i.cells)
        cell_texts = []
        for element in group["table_elt"]:
            for cell_id in cell_ids:
                cell_row_id, cell_col_id = cell_id.split("_")
                row_headers = [element["cells"].get(f"{cell_row_id}_{i}", {}).get("text", "") for i in range(3)]
                col_headers = [element["cells"].get(f"{i}_{cell_col_id}", {}).get("text", "") for i in range(3)]
                cell_texts.extend(row_headers + col_headers)
            if cell_texts:
                break
        return cell_texts

    def group_elts(self, syllabus):
        groups = []
        # 若syllabus有children, 则按照标题分组
        sub_syllabues = syllabus["children"]
        if sub_syllabues:
            for sub_syllabus_index in syllabus["children"]:
                sub_syllabus = self.pdfinsight.syllabus_dict.get(sub_syllabus_index)
                start, end = sub_syllabus["range"][0], sub_syllabus["range"][-1]
                groups.extend(self.group_elt_in_syllabus(start, end))
        else:
            start, end = syllabus["range"][0], syllabus["range"][-1]
            groups.extend(self.group_elt_in_syllabus(start, end))
        return groups

    def group_elt_in_syllabus(self, start, end):
        groups = []
        elts = []
        for elt_index in range(start, end):
            elt_type, elt = self.pdfinsight.find_element_by_index(elt_index)
            if not elt or elt.get("class") not in ["PARAGRAPH", "TABLE"]:
                continue
            elts.append((elt_type, elt))
        grouped_elts = []
        for _, group_elts in groupby(elts, lambda x: x[0]):
            grouped_elts.append(group_elts)
        iter_group_elts = [grouped_elts[i : i + 2] for i in range(0, len(grouped_elts), 2)]
        for group_elt in iter_group_elts:
            group = {
                "para_elt": [],
                "table_elt": [],
            }
            if group_elt:
                group["para_elt"] = [i[1] for i in group_elt[0]]
            if len(group_elt) > 1:
                group["table_elt"] = [i[1] for i in group_elt[1]]
            groups.append(group)
        return groups

    def extract_chapter_feature(self, dataset, **kwargs):
        counter = Counter()
        for item in dataset:
            syll_reader = PdfinsightSyllabus(item.data.get("syllabuses", []))
            for key_col in item.answer.get("资质名称", {}).values():
                for eidx in key_col.relative_element_indexes:
                    element = item.data.get("elements", {}).get(eidx)
                    if not element or not element.get("syllabus"):
                        continue
                    syllabuses = syll_reader.find_by_index(element["syllabus"])
                    syllabus_titles = []
                    # 获取最后一个带有资质的标题
                    for syllabus in syllabuses:
                        if qualification_pattern.search(syllabus["title"]):
                            syllabus_titles.append(syllabus["title"])
                            break
                        else:
                            syllabus_titles.append(syllabus["title"])
                    syllabus_feature = "|".join(syllabus_titles)
                    counter.update([syllabus_feature])
        return counter
