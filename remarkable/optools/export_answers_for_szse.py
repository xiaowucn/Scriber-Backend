import collections
import json
import logging
import os
import shutil
import time
import traceback
import zipfile
from copy import deepcopy
from datetime import datetime
from operator import itemgetter

from peewee import fn
from utensils.zip import ZipFilePlus

from remarkable.answer.reader import AnswerReader
from remarkable.common.constants import JSONConverterStyle
from remarkable.common.enums import ClientName, ExportStatus
from remarkable.common.multiprocess import run_by_batch
from remarkable.common.storage import localstorage
from remarkable.common.util import box_to_outline, clean_txt
from remarkable.config import get_config, project_root
from remarkable.db import pw_db
from remarkable.models.new_file import NewFile
from remarkable.pdfinsight.reader import PdfinsightReader
from remarkable.pw_models.answer_data import NewAnswerData
from remarkable.pw_models.model import NewAnswer, NewMold, NewTrainingData
from remarkable.pw_models.question import NewQuestion
from remarkable.pw_orm import func
from remarkable.service.comment import shorten_path_bytes
from remarkable.service.new_mold import NewMoldService

LabelInfo = collections.namedtuple("LabelInfo", ("label", "answers", "left_index", "right_index"))


async def fetch_all_answers(mold_id, export_type="json", tree_s=None, files_ids=None, only_fid=False):
    if get_config("data_flow.file_answer.generate"):
        return await fetch_all_answer_data(mold_id, tree_s, files_ids, only_fid)

    cond = NewQuestion.mold == mold_id

    if tree_s:
        cond &= NewFile.tree_id.in_(tree_s)
    if files_ids:
        cond &= NewFile.id.in_(files_ids)

    if export_type == "txt":  # 导出标注txt 从answer表中获取
        cond &= NewAnswer.data.is_null(False)
        cte_fields = [
            NewQuestion.id.alias("qid"),
            NewAnswer.data.alias("data"),
            NewFile.id.alias("fid"),
            NewFile.name,
            NewFile.pdfinsight,
            fn.Row_Number()
            .over(
                partition_by=[NewQuestion.id],
                order_by=[NewAnswer.standard.desc(), NewAnswer.updated_utc.desc()],
            )
            .alias("rank"),
        ]

        cte = (
            NewQuestion.select(*cte_fields)
            .join(NewAnswer, on=(NewAnswer.qid == NewQuestion.id))
            .join(NewFile, on=(NewFile.id == NewQuestion.fid))
            .where(cond)
            .cte("cte")
        )
        # query = peewee.Select([cte], [cte.c.qid, cte.c.fid, cte.c.data]).where(cte.c.rank == 1).from_(cte).with_cte(cte)
        if only_fid:
            fields = [cte.c.fid]
        else:
            fields = (cte.c.qid, cte.c.data, cte.c.fid, cte.c.name, cte.c.pdfinsight)
        query = (
            NewQuestion.select(*fields).join(cte, on=(NewQuestion.id == cte.c.qid)).where(cte.c.rank == 1).with_cte(cte)
        )

    else:
        cond &= NewQuestion.answer.is_null(False)
        if only_fid:
            fields = [NewFile.id.alias("fid")]
        else:
            fields = [
                NewQuestion.id.alias("qid"),
                NewQuestion.answer.alias("data"),
                NewFile.id.alias("fid"),
                NewFile.name,
                NewFile.pdfinsight,
            ]
        query = NewQuestion.select(*fields).join(NewFile, on=(NewFile.id == NewQuestion.fid)).where(cond)
    rows = await pw_db.execute(query.dicts())
    return rows


async def fetch_all_answer_data(mold_id, tree_s=None, files_ids=None, only_fid=False):
    cond = NewQuestion.mold == mold_id
    if tree_s:
        cond &= NewFile.tree_id.in_(tree_s)
    if files_ids:
        cond &= NewFile.id.in_(files_ids)

    if only_fid:
        fields = [NewFile.id.alias("fid")]
    else:
        fields = [
            NewAnswerData.qid.alias("qid"),
            func.ARRAY_AGG(NewAnswerData.jsonb_build_object("key", "data", "value")).alias("data_agg"),
            NewFile.id.alias("fid"),
            NewFile.name,
            NewFile.pdfinsight,
        ]

    query = (
        NewAnswerData.select(*fields)
        .join(NewQuestion, on=(NewAnswerData.qid == NewQuestion.id))
        .join(NewFile, on=(NewFile.id == NewQuestion.fid))
        .where(cond)
        .group_by(NewAnswerData.qid, NewFile.id)
    )

    rows = await pw_db.execute(query.dicts())
    if only_fid:
        return rows

    molds = await NewMold.get_related_molds(mold_id)
    mold, _ = NewMoldService.master_mold_with_merged_schemas(molds)
    p_molds_name = NewMoldService.get_p_molds_name(molds)

    for row in rows:
        for item in row["data_agg"]:
            item["key"] = NewMoldService.update_merged_answer_key_path(p_molds_name, molds[0], item["key"])
        row["data_agg"] = sorted(row["data_agg"], key=itemgetter("key"))
        row["data"] = {"schema": mold.data, "userAnswer": {"items": row.pop("data_agg")}}
    return rows


def fill_element_info(answer, pdfinsight):
    reader = PdfinsightReader(localstorage.mount(os.path.join(pdfinsight[:2], pdfinsight[2:])))
    if float(get_config("prompter.answer_version", "2.2")) >= 2.0:
        answer = AnswerReader.add_element_index(answer, reader)
    else:
        for schema in answer.get("userAnswer", {}).values():
            for item in schema.get("items", []):
                for field in item.get("fields", []):
                    # load Mapping
                    for component in field.get("components") or []:
                        frame = component.get("frameData")
                        page = frame.get("page")
                        top = float(frame.get("top"))
                        left = float(frame.get("left"))
                        height = float(frame.get("height"))
                        width = float(frame.get("width"))
                        outline = (left, top, left + width, top + height)
                        etype, element = reader.find_element_by_outline(page, outline)
                        if element is None:
                            logging.error("can't find element by page %s, outline %s", page, outline)
                            frame["element_index"] = None
                        else:
                            frame["element_index"] = element.get("index")

    revise_elements = []
    for para in reader.paragraphs:
        revise_elements.append(revise_para(para))
    for page_header in reader.page_headers:
        revise_elements.append(revise_para(page_header))
    for page_footer in reader.page_footers:
        revise_elements.append(revise_para(page_footer))
    for tbl in reader.tables:
        revise_elements.append(revise_table(tbl))
    answer["elements"] = sorted(revise_elements, key=lambda x: x["index"])
    answer["syllabuses"] = sorted([revise_syll(e) for e in reader.syllabuses], key=lambda x: x["index"])

    return answer


def revise_table(element):
    tbl = deepcopy(element)
    tbl.pop("outline", None)
    tbl.pop("grid", None)
    for cell in tbl.get("cells").values():
        cell.pop("styles", None)
        cell.pop("chars", None)
        cell.pop("styles_diff", None)
    return tbl


def revise_syll(element):
    syll = deepcopy(element)
    syll["dest"].pop("box", None)
    return syll


def revise_para(element):
    para = deepcopy(element)
    para.pop("outline", None)
    para.pop("outline_score", None)
    para.pop("outline_parsed_by", None)
    para.pop("chars", None)
    return para


def run_export_answer(args):
    answer, fid, filename, _, task_id, _ = args
    try:
        start = time.time()
        dump_filename = "%s_%s.json" % (fid, ZipFilePlus.fix_encoding(filename))
        dump_dir = os.path.join(project_root, "data", "export_answer_data")
        if task_id is not None:
            dump_dir = os.path.join(dump_dir, str(task_id))
        dump_path = os.path.join(dump_dir, dump_filename)
        if os.path.exists(dump_path):
            return dump_path
        logging.info("begin to export answer for file %s_%s", fid, filename)

        with open(dump_path, "w") as dump_fp:
            json.dump(
                AnswerReader(answer).to_json(style=JSONConverterStyle.PLAIN_TEXT), dump_fp, ensure_ascii=False, indent=4
            )
        logging.info("finished export answer for file %s_%s, cost %.2fs", fid, filename, time.time() - start)
        return dump_path
    except Exception as ex:
        logging.error("occur error in handling file %s", fid)
        logging.error(ex)
        traceback.print_exc()


def run_export_answer_txt(args):
    answer, fid, filename, pdfinsight, task_id, mold_name = args
    if not pdfinsight:
        logging.error("file %s have no pdfinsight result, pass", filename)
        return None
    try:
        start = time.time()
        dump_filename = "%s_%s.txt" % (fid, ZipFilePlus.fix_encoding(filename))
        dump_dir = os.path.join(project_root, "data", "export_answer_data")
        if task_id is not None:
            dump_dir = os.path.join(dump_dir, str(task_id))
        dump_path = os.path.join(dump_dir, dump_filename)
        if os.path.exists(dump_path):
            return dump_path
        logging.info("begin to export answer for file %s_%s", fid, filename)
        revise_answer = gen_text_from_answer(answer, pdfinsight, mold_name)
        with open(dump_path, "w") as dump_fp:
            dump_fp.write(revise_answer)
        logging.info("finished export answer for file %s_%s, cost %.2fs", fid, filename, time.time() - start)
        return dump_path
    except Exception as ex:
        logging.error("occur error in handling file %s", fid)
        logging.error(ex)
        traceback.print_exc()


def gen_text_from_answer(answer, pdfinsight, mold_name):
    ret = ""
    reader = PdfinsightReader(localstorage.mount(os.path.join(pdfinsight[:2], pdfinsight[2:])))
    field_mapping = read_field_mapping(mold_name)
    # 根据答案生成元素块index 和答案的映射
    element_answer_map = gen_element_answer_map(answer, reader)
    # 遍历所有的元素块
    ret = traverse_answer(reader, element_answer_map, field_mapping)
    return ret


ElementAnswerMapitem = collections.namedtuple("ElementAnswerMapitem", ["label", "page", "outline"])


def gen_element_answer_map(answer, reader):
    element_answer_map = collections.defaultdict(list)
    for item in answer["userAnswer"]["items"]:
        key_list = json.loads(item["key"])
        label = "-".join([i.split(":")[0] for i in key_list[1:]])
        for i in item["data"]:
            if not i:
                continue
            for j in i["boxes"]:
                box_lines = j["box"]
                out_line = box_to_outline(box_lines)
                for _, ele in reader.find_elements_by_outline(j["page"], out_line):
                    element_answer_map[ele["index"]].append(ElementAnswerMapitem(label, j["page"], out_line))
    return element_answer_map


class BlockCharAssembler:
    def __init__(self, chars, field_mapping):
        self.chars = chars
        self.field_mapping = field_mapping
        self.groups = []
        self._assembling = {}

    def _assemble_char(self, char, labels):
        if char is None:
            for label, group in self._assembling.items():
                self.groups.append((label, group))
            return

        for label in list(self._assembling.keys()):
            group = self._assembling[label]
            if label in labels:
                group.append(char)
                labels.remove(label)
            else:
                self.groups.append((label, group))
                self._assembling.pop(label)

        for label in labels:
            self._assembling[label] = [char]

    def assemble_for_answers(self, answers: list[ElementAnswerMapitem]) -> list[tuple[str, str]]:
        for char in self.chars:
            labels = {
                self.field_mapping[a.label]
                for a in answers
                if PdfinsightReader.is_box_in_box_by_center(char["box"], a.outline)
            }
            if not labels:
                labels.add("/o")
            self._assemble_char(char, labels)
        self._assemble_char(None, [])
        texts_with_label = [(label, clean_txt("".join(c["text"] for c in chars))) for (label, chars) in self.groups]
        return [t for t in texts_with_label if t[1]]


def traverse_answer(reader, element_answer_map, field_mapping):
    def _handle_paragraph(para, items):
        # 去除跨页段落的后半部分
        if para.data.get("continued"):
            chars = [i for i in para.data["chars"] if i["page"] == para.data["page"]]
        else:
            chars = para.data["chars"]
        assembler = BlockCharAssembler(chars, field_mapping)
        return assembler.assemble_for_answers(items)

    def _handle_table(tbl, items):
        _texts_with_label = []
        sorted_cells = [(*k.split("_"), v) for k, v in tbl.data["cells"].items()]
        sorted_cells = sorted(sorted_cells, key=lambda cell: (int(cell[0]), int(cell[1])))
        last_ridx = None
        for ridx, _, cell in sorted_cells:
            if last_ridx is not None:
                if last_ridx == ridx:
                    _texts_with_label.append(("", "\\t"))
                else:
                    _texts_with_label.append(("", "\\n"))
            assembler = BlockCharAssembler(cell["chars"], field_mapping)
            _texts_with_label.extend(assembler.assemble_for_answers(items))
            last_ridx = ridx
        _texts_with_label.append(("", "\\n"))
        return _texts_with_label

    def _merge_same_label(data):
        merges = []
        merged_label = None
        merged_text = None
        for _label, _text in data:
            if merged_text is None:
                merged_label = _label
                merged_text = _text
                continue
            if _label and _label != merged_label:
                merges.append((merged_label, merged_text))
                merged_label = _label
                merged_text = _text
            else:
                merged_text += _text
        if merged_text is not None:
            merges.append((merged_label, merged_text))
        return merges

    def text_label_str(text, label):
        prefix, suffix = "", ""
        if text.startswith("\\t") or text.startswith("\\n"):
            prefix = f"{text[:2]}/o "
            text = text[2:]
        if text.endswith("\\t") or text.endswith("\\n"):
            suffix = f"{text[-2:]}/o "
            text = text[:-2]
        return f"{prefix}{text}{label} {suffix}"

    texts_with_label = []
    for page, elements in reader.element_dict.items():
        if page != 0:
            elements = elements[1:-1]
        for ele in elements:
            labels = element_answer_map.get(ele.index, [])
            if ele.data["class"] in ["PARAGRAPH", "PAGE_HEADER", "PAGE_FOOTER"]:
                texts_with_label.extend(_handle_paragraph(ele, labels))
            elif ele.data["class"] in ["TABLE"]:
                texts_with_label.extend(_handle_table(ele, labels))
            else:
                continue
    texts_with_label = _merge_same_label(texts_with_label)
    return "".join([text_label_str(text, label) for label, text in texts_with_label])


def read_field_mapping(mold_name):
    ret = {}
    file_path = os.path.join(project_root, "data", "szse_field_map", f"{mold_name}_field_map.txt")
    with open(file_path, "r") as file_obj:
        datas = file_obj.readlines()
    for data in datas:
        data_list = data.split()
        ret[" ".join(data_list[1:])] = data_list[0]
    return ret


def export_to_csv(args):
    # answer, fid, filename, pdfinsight, task_id, mold_name
    answer, fid, filename, _, task_id, _ = args
    try:
        start = time.time()
        f_name = ZipFilePlus.fix_encoding(filename)
        f_name = os.path.splitext(f_name)[0] if len(os.path.splitext(f_name)) == 2 else filename
        dump_filename = f"{fid}_{f_name}.csv"
        dump_dir = os.path.join(project_root, "data", "export_answer_data")
        if task_id is not None:
            dump_dir = os.path.join(dump_dir, str(task_id))
        dump_path = os.path.join(dump_dir, dump_filename)
        dump_path = shorten_path_bytes(dump_path)
        if os.path.exists(dump_path):
            return dump_path
        logging.info(f"begin to export answer for file {fid}_{filename}")
        with open(dump_path, "wb") as csv_f:
            csv_f.write(AnswerReader(answer).to_csv())
        logging.info(f"finished export answer for file {fid}_{filename}, cost {time.time() - start: .2f}")
        return dump_path
    except Exception as ex:
        logging.error(
            f"occur error in handling file {fid}",
        )
        logging.error(ex)
        traceback.print_exc()


def export_answer_data_to_csv(answer, fid, filename, mold_id, mold_name, task_id):
    try:
        start = time.time()
        f_name = ZipFilePlus.fix_encoding(filename)
        f_name = os.path.splitext(f_name)[0] if len(os.path.splitext(f_name)) == 2 else filename
        dump_filename = f"{fid}_{f_name}_{mold_id}_{mold_name}.csv"
        dump_dir = os.path.join(project_root, "data", "export_answer_data")
        if task_id is not None:
            dump_dir = os.path.join(dump_dir, str(task_id))
        dump_path = os.path.join(dump_dir, dump_filename)
        dump_path = shorten_path_bytes(dump_path)
        if os.path.exists(dump_path):
            return dump_path
        logging.info(f"begin to export answer for {dump_filename}")
        with open(dump_path, "wb") as csv_f:
            csv_f.write(AnswerReader(answer).to_csv())
        logging.info(f"finished export answer for {dump_filename}, cost {time.time() - start: .2f}")
        return dump_path
    except Exception as ex:
        logging.error(
            f"occur error in handling file {fid}",
        )
        logging.error(ex)
        traceback.print_exc()


async def export_answer_scheduler(task_id: int):
    training_data = await NewTrainingData.find_by_id(task_id)
    if not training_data or training_data.export_type not in ["csv", "json", "txt"]:
        logging.error("task error, task_id：%s", task_id)
        await training_data.update_(status=ExportStatus.FAILED)
        return

    mold_obj = await NewMold.find_by_id(training_data.mold)
    if not mold_obj:
        logging.error("mold error, task_id：%s", task_id)
        await training_data.update_(status=ExportStatus.FAILED)
        return
    mold_name = mold_obj.name
    dump_dir = os.path.join(project_root, "data", "export_answer_data", str(task_id))
    if not os.path.exists(dump_dir):
        os.makedirs(dump_dir)
    rows = await fetch_all_answers(
        mold_obj.id, export_type=training_data.export_type, tree_s=training_data.dirs, files_ids=training_data.files_ids
    )
    tasks = [
        (row["data"], row["fid"], row["name"], row["pdfinsight"], task_id, mold_name) for row in rows if row["data"]
    ]
    if not tasks:
        logging.error("has no answers, task_id：%s", task_id)
        await training_data.update_(status=ExportStatus.FAILED)
        return

    if training_data.export_type == "csv":
        worker = export_to_csv
    elif training_data.export_type == "json":
        worker = run_export_answer
    elif training_data.export_type == "txt":
        worker = run_export_answer_txt
        field_map_file_path = os.path.join(project_root, "data", "szse_field_map", f"{mold_name}_field_map.txt")
        if not localstorage.exists(field_map_file_path):
            from remarkable.worker.tasks.export_tasks import gen_field_map_file

            await gen_field_map_file(training_data.mold)
    # debug=True，临时不使用多进程
    for dumped_files in run_by_batch(worker, tasks, batch_size=10, workers=8):
        await training_data.update_(task_done=training_data.task_done + len(dumped_files))
    # 压缩并删除临时文件
    if get_config("client.name") == ClientName.cmfchina:
        zip_path = os.path.join(
            project_root, "data", "export_answer_data", f"{mold_obj.name} {datetime.now().strftime('%Y%m%d%H%M%S')}.zip"
        )
    else:
        zip_path = os.path.join(project_root, "data", "export_answer_data", f"task_{task_id}.zip")
    if training_data.export_type == "txt":
        field_map_file_path = os.path.join(project_root, "data", "szse_field_map", f"{mold_name}_field_map.txt")
        dump_filename = "标注数据.txt"
        dump_path = os.path.join(dump_dir, dump_filename)
        with open(dump_path, "a+") as dump_fp:
            for _file in os.listdir(dump_dir):
                _file = os.path.join(dump_dir, _file)
                if dump_filename in _file:
                    continue
                with open(_file, "r") as obj:
                    dump_fp.writelines([obj.readline(), "\n"])
        with zipfile.ZipFile(zip_path, "w") as zfp:
            zfp.write(dump_path, "标注数据.txt", compress_type=zipfile.ZIP_DEFLATED)
            zfp.write(field_map_file_path, "字段映射.txt", compress_type=zipfile.ZIP_DEFLATED)

    else:
        with zipfile.ZipFile(zip_path, "w") as zfp:
            for _file in os.listdir(dump_dir):
                _file = os.path.join(dump_dir, _file)
                zfp.write(_file, os.path.split(_file)[-1], compress_type=zipfile.ZIP_DEFLATED)
    if os.path.exists(dump_dir):
        shutil.rmtree(dump_dir)
    # 记录下载地址
    await training_data.update_(zip_path=zip_path, status=ExportStatus.FINISH)


if __name__ == "__main__":
    import asyncio

    asyncio.run(fetch_all_answers(17, "csv"))
