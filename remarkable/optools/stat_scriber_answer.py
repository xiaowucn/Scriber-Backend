import argparse
import itertools
import json
import logging
import os
import re
from functools import cached_property
from operator import and_
from random import randint

import pandas as pd

from remarkable import config
from remarkable.common.constants import AccuracyRecordStatus, SpecialAnswerType
from remarkable.common.exceptions import CustomError
from remarkable.common.schema import Schema, attribute_id
from remarkable.common.util import box_to_outline, clean_txt, loop_wrapper
from remarkable.config import get_config, project_root
from remarkable.db import pw_db
from remarkable.models.model_version import NewModelVersion
from remarkable.models.new_file import NewFile
from remarkable.models.new_model_answer import ModelAnswer
from remarkable.optools.stat_util import (
    AnswerMeasure,
    ComplianceAnswerCompare,
    ComplianceAnswerPrepare,
    CrudeAnswerCompare,
    CrudeAnswerPrepare,
    PresetAnswerCompare,
    PresetAnswerPrepare,
    SSESchema5AnswerPrepare,
    compare_preset_data,
    error_report,
)
from remarkable.optools.table_util import TableUtil
from remarkable.pdfinsight.html import para_to_html, tbl_to_html
from remarkable.pw_models.model import NewAccuracyRecord, NewMold, NewSpecialAnswer
from remarkable.pw_models.question import NewQuestion

args = None


class StatScriberAnswer:
    html = {}
    report = {}
    attr_tbl_heads = {}

    def __init__(self, headnum=None, threshold=None, **kwargs):
        self.headnum = headnum or 5
        self.threshold = threshold or 0
        self.from_id = kwargs.get("from_id", 0)
        self.to_id = kwargs.get("to_id", 0)
        self.files_ids = kwargs.get("files_ids")
        self.count_label = kwargs.get("count_label")
        self.print_diff = kwargs.get("print_diff")
        self.mold = kwargs.get("mold")
        self.save = kwargs.get("save")
        self.orderby = kwargs.get("orderby")
        self.ratio = kwargs.get("ratio")
        self.strict = kwargs.get("strict")
        self.tree_s = kwargs.get("tree_s")
        self.host = kwargs.get("host")
        self.bydoc = kwargs.get("bydoc")
        self.vid = kwargs.get("vid", 0)
        self.answers = kwargs.get("answers")
        self.white_list = kwargs.get("white_list")
        self.acid = kwargs.get("acid")
        self.skip_reg = kwargs.get("skip_reg")
        self.test_accuracy_online = kwargs.get("test_accuracy_online")
        self.save_stat_result = kwargs.get("save_stat_result")
        self.export_excel = kwargs.get("export_excel")
        self.diff_model = kwargs.get("diff_model")

    @property
    async def qids(self):
        query = NewFile.select(NewQuestion.id.distinct()).join(NewQuestion, on=(NewFile.id == NewQuestion.fid))
        if self.mold is not None:
            query = query.where(NewQuestion.mold == self.mold)
        else:
            raise Exception("mold is needed")

        if self.from_id:
            query = query.where(NewFile.id >= self.from_id)
        if self.to_id:
            query = query.where(NewFile.id <= self.to_id)
        if self.tree_s:
            query = query.where(NewFile.tree_id.in_(self.tree_s))
        if self.files_ids:
            query = query.where(NewFile.id.in_(self.files_ids))
        query = query.order_by(NewQuestion.id)

        return await pw_db.scalars(query)

    @property
    async def fids(self):
        query = NewFile.select(NewFile.id).join(NewQuestion, on=(NewFile.id == NewQuestion.fid))
        cond = NewQuestion.id.in_(await self.qids)
        files = await pw_db.execute(query.where(cond))
        return [x.id for x in files]

    async def save_result(self, stat_result, count, diff_vid, crude):
        if self.save:
            export_excel_path = None
            mold = await NewMold.get_by_id(self.mold)
            if self.export_excel:
                export_excel_path = await error_report.export_stat_data(
                    stat_result, mold, self.acid, await self.fids, self.vid, diff_vid
                )

            stat_result.update({"from_id": self.from_id, "to_id": self.to_id, "mold": self.mold})
            await self.dump_stat_result(
                stat_result,
                mold=mold,
                crude=crude,
                test=self.save,
                file_count=count,
                vid=self.vid,
                tree_s=self.tree_s,
                acid=self.acid,
                export_path=export_excel_path,
            )

    @staticmethod
    def get_file_url(host, qid, tree_id, fid, mold, pid, file_name):
        file_url = "http://%s/#/project/remark/%s?treeId=%s&fileId=%s&schemaId=%s&projectId=%s&fileName=%s" % (
            host,
            qid,
            tree_id,
            fid,
            mold,
            pid,
            file_name,
        )
        return file_url

    async def stat_crude_answer(self):
        answer_compare = CrudeAnswerCompare(strict=self.strict, white_list_path=self.white_list, headnum=self.headnum)
        answer_prepare = CrudeAnswerPrepare(vid=self.vid, threshold=self.threshold, headnum=self.headnum)
        measure = AnswerMeasure(answer_compare, answer_prepare)
        stat_result = await self.stat_answer(measure)
        return stat_result

    async def stat_compliance_answer(self):
        answer_compare = ComplianceAnswerCompare(strict=self.strict, white_list_path=self.white_list)
        answer_prepare = ComplianceAnswerPrepare()
        measure = AnswerMeasure(answer_compare, answer_prepare)
        stat_result = await self.stat_answer(measure)
        return stat_result

    async def stat_answer(self, measure):
        try:
            return await self._stat_answer(measure)
        except Exception as exp:
            logging.exception(exp)
        if self.acid:
            await NewAccuracyRecord.update_by_pk(self.acid, status=AccuracyRecordStatus.FAILED.value)

    @cached_property
    def file_info(self):
        return {}

    async def _stat_answer(self, measure):
        for record in await pw_db.execute(
            NewQuestion.select(NewFile.id, NewFile.tree_id, NewQuestion.id.alias("qid"))
            .join(NewFile, on=and_(NewFile.id == NewQuestion.fid, NewQuestion.mold == self.mold))
            .namedtuples()
        ):
            self.file_info[record.id] = record
        diff_vid = None
        if self.diff_model:
            diff_version = await NewModelVersion.get_last_with_model_answer(self.mold, self.vid)
            diff_vid = diff_version.id
            if not diff_vid:
                raise CustomError(f"Cannot get_last_with_model_answer for mold:{self.mold}, vid:{self.vid}")

        for qid in await self.qids:
            question = await NewQuestion.find_by_id(qid)
            special_answer = None
            if self.test_accuracy_online:
                special_answer = await NewSpecialAnswer.get_first_one(
                    cond=(NewSpecialAnswer.qid == qid)
                    & (NewSpecialAnswer.answer_type == SpecialAnswerType.TEST_ACCURACY_PRESET.value)
                )

            answer = self.answers.get(question.fid, {}) if self.answers else None
            old_version_answer = None
            if diff_vid:
                old_version_answer = await ModelAnswer.get_answer(diff_vid, qid)
                if not old_version_answer:
                    raise CustomError(f"Not model_answer for qid: {qid}, mid: {self.mold}, vid:{diff_vid}")
                special_answer = await ModelAnswer.get_answer(self.vid, qid)
                if not special_answer:
                    raise CustomError(f"Not model_answer for qid: {qid}, mid: {self.mold}, vid:{self.vid}")

            try:
                answer, standard = await measure.answer_prepare(question, answer, special_answer, old_version_answer)
                if not standard:
                    logging.error(f"__SKIP__: no standard answer, qid:{qid}, fid:{question.fid}")
                    continue
                if not answer:
                    logging.error(f"__SKIP__: no answer, qid:{qid}, fid:{question.fid}")
                    continue
                measure.append(question.fid, answer, standard, self.skip_reg)
                logging.info(f"Stat: qid:{qid}, fid:{question.fid}, count:{measure.docs_count}")
            except Exception as ex:
                logging.exception(ex)
                logging.error(f"__Error__: qid:{qid}, fid:{question.fid}")
        stat_result = self.print_report(measure.docs_count, measure.fits, measure.attr_cnt)
        error_report.set_host(self.host)
        error_report.file_info.update(self.file_info)
        error_report.export_file(self.mold)
        await self.save_result(stat_result, measure.docs_count, diff_vid, crude=False)

        return stat_result

    async def stat_preset_answer(self):
        answer_compare = PresetAnswerCompare(strict=self.strict, white_list_path=self.white_list)
        answer_prepare = PresetAnswerPrepare()
        measure = AnswerMeasure(answer_compare, answer_prepare)
        stat_result = await self.stat_answer(measure)
        return stat_result

    async def stat_sse_schema5(self):
        answer_compare = PresetAnswerCompare(strict=self.strict, white_list_path=self.white_list)
        answer_prepare = SSESchema5AnswerPrepare()
        measure = AnswerMeasure(answer_compare, answer_prepare)
        stat_result = await self.stat_answer(measure)
        return stat_result

    def check_preset_answer(self, fid, preset_answer, answer, fits, crude_answer, file_url=None):
        # print('~~~~ preset_answer', len(preset_answer['userAnswer']['items']))
        # print('~~~~ answer', len(answer['userAnswer']['items']))
        for item in preset_answer.get("userAnswer", {}).get("items", []):
            aid = attribute_id(json.loads(item["key"]))
            self.predict_attr_cnt.update({aid: 1})

        attr_l = []
        for schema in answer["schema"]["schemas"]:
            attr_l.extend(schema["orders"])

        for item in answer.get("userAnswer", {}).get("items", []):
            aid = attribute_id(json.loads(item["key"]))
            if not item["data"]:
                continue
            attr = item["schema"]["data"]["label"]
            if attr not in attr_l:
                continue
            # if attr not in ['交易金额']:
            #     continue
            # print('attr', aid)
            predict = [
                each
                for each in preset_answer.get("userAnswer", {}).get("items", [])
                if aid == attribute_id(json.loads(each["key"]))
            ]
            field_fit = bool(compare_preset_data(item["data"], attr, predict, self.strict))
            # print('field_fit', field_fit)
            if not field_fit and (self.print_diff in ("all", attr)):  # TODO 待迁移
                logging.info("==== %s  %s ====", str(fid), attr)
                for data in item["data"]:
                    text = "".join([b["text"] for b in data["boxes"]])
                    pages = ",".join(list({str(b["page"]) for b in data["boxes"]}))
                    print("label  answer:", text, "page_%s" % pages)
                for preset_data in predict:
                    for p_data in preset_data:
                        text = "".join([b["text"] for b in p_data["boxes"]])
                        pages = ",".join(list({str(b["page"]) for b in p_data["boxes"]}))
                        print("preset answer:", text, "page_%s" % pages)

            self.export_tbl_headers(fid, attr, item, crude_answer)  # TODO 待迁移
            self.export_html(attr, item, predict, field_fit, crude_answer, file_url)  # TODO 待迁移

            attr_fits = fits.setdefault(aid, {"name": aid, "fits": []})
            attr_fits["fits"].append([field_fit])
        return fits

    def export_html(self, attr, item, predict, field_fit, crude_answer, file_url):
        if not field_fit and args and attr == args.export:  # 导出标注html
            elements = []
            for k, v in crude_answer.items():
                if k in (attr, "收购标的情况-%s" % attr):  # todo:其他二级属性
                    for x in v:
                        elements.append(x["element"])

            res = {}

            def get_predict_outline(predict, elts, idx):
                res = []
                for preset_data in predict:
                    for p_data in preset_data:
                        for p_box in p_data.get("boxes", []):
                            page = p_box["page"]
                            box = p_box["box"]
                            outline = box_to_outline(box)
                            etype, element = self.find_element_by_outline(elts, page, outline)
                            if element is not None and element["index"] == idx:
                                res.append((page, outline))
                return res

            for label_data in item.get("data", []):
                for box_info in label_data.get("boxes", []):
                    page = box_info["page"]
                    box = box_info["box"]
                    outline = box_to_outline(box)
                    _, element = self.find_element_by_outline(elements, page, outline)
                    if element is not None:
                        res.setdefault(element["index"], {}).setdefault("elt", element)
                        res.setdefault(element["index"], {}).setdefault("label_outline", []).append((page, outline))
                        res.setdefault(element["index"], {}).setdefault("predict_outline", []).extend(
                            get_predict_outline(predict, elements, element["index"])
                        )

            for info in res.values():
                if info["elt"]["class"] == "TABLE":
                    label_html_str = tbl_to_html(info["elt"], blue=info.get("label_outline", []), red=[])
                    predict_html_str = tbl_to_html(info["elt"], blue=[], red=info.get("predict_outline", []))
                else:
                    label_html_str = para_to_html(info["elt"], blue=info.get("label_outline", []), red=[])
                    predict_html_str = para_to_html(info["elt"], blue=[], red=info.get("predict_outline", []))
                self.html.setdefault(attr, []).extend(
                    [
                        "<li>",
                        "<a href='%s' target='_blank'>%s</a>" % (file_url, file_url),
                        "页码：%s" % (int(info["elt"]["page"]) + 1),
                        '<p class="blue">标注答案：</p>' + label_html_str,
                        '<p class="red">预测答案：</p>' + predict_html_str,
                        "</li>",
                        "<br/>",
                        "<br/>",
                    ]
                )

    def export_tbl_headers(self, fid, attr, item, crude_answer):
        if args and args.exportjson:  # 导出标注tbl_headers
            elements = []
            for k, v in crude_answer.items():
                if attr in k:
                    for x in v:
                        elements.append(x["element"])
            for label_data in item.get("data", []):
                for box_info in label_data.get("boxes", []):
                    page = box_info["page"]
                    box = box_info["box"]
                    outline = box_to_outline(box)
                    etype, element = self.find_element_by_outline(elements, page, outline)
                    if etype != "TABLE":
                        continue
                    for idx, cell in element["cells"].items():
                        if clean_txt(cell["text"]) == clean_txt(box_info.get("text", "")) and not cell.get("dummy"):
                            tr_heads, td_heads = TableUtil.get_cell_headers(element, idx)
                            self.attr_tbl_heads.setdefault(attr, []).append(
                                {"tr_heads": tr_heads, "td_heads": td_heads, "file_id": fid}
                            )

    def find_element_by_outline(self, elements, page, outline, debug=False):
        overlap_threshold = 0.618

        def inter_x(*outlines):
            overlap_length = min(outlines[0][2], outlines[1][2]) - max(outlines[0][0], outlines[1][0])
            return overlap_length if overlap_length > 0 else 0

        def inter_y(*outlines):
            overlap_length = min(outlines[0][3], outlines[1][3]) - max(outlines[0][1], outlines[1][1])
            return overlap_length if overlap_length > 0 else 0

        def area(*outlines):
            return (outlines[1][3] - outlines[1][1]) * (outlines[1][2] - outlines[1][0])

        def overlap_percent(*outlines):
            return inter_y(*outlines) * inter_x(*outlines) / area(*outlines)

        def rcnn(*outlines):
            return overlap_percent(*outlines) > overlap_threshold

        max_overlap = None
        if debug:
            logging.info("find outline: %s", outline)
        for elt in [element for element in elements if element and element.get("page") == page]:
            overlap = overlap_percent(outline, elt["outline"])
            if debug:
                logging.info("%.2f, %s", overlap, elt["outline"])
            if overlap > 0 and max_overlap is None:
                max_overlap = (elt, overlap)
            elif overlap > 0 and max_overlap[1] < overlap:
                max_overlap = (elt, overlap)
            # if overlap > overlap_threshold:
            #     return self._return(elt.data)

        if max_overlap is not None:
            return max_overlap[0].get("class"), max_overlap[0]
        return None, None

    @classmethod
    def stat_field_fits(cls, field):
        field_fits = field["fits"]
        fit, total = sum(itertools.chain(*field_fits)), len(list(itertools.chain(*field_fits)))
        percent = float(fit) / float(total or 1)  # R = TP/TP+FN
        res = []
        if field["idx_fits"]:
            for topn in [5, 3, 2, 1]:
                topn_fits = [[1 if 1 in item[:topn] else 0 for item in doc] for doc in field["idx_fits"]]
                _fit, _total = sum(itertools.chain(*topn_fits)), len(list(itertools.chain(*topn_fits)))
                _percent = float(_fit) / float(_total or 1)
                res.append((_fit, _total, round(_percent, 3)))
        return fit, total, round(percent, 3), res

    @classmethod
    def stat_field_fits_by_document(cls, field):
        field_fits = field["fits"]
        rates = [len([1 for fit in _doc if fit]) / len(_doc or 1) for _doc in field_fits]
        fit, total = sum(rates), len(rates)
        percent = fit / (total or 1)
        res = []
        return fit, total, round(percent, 3), res

    # @classmethod
    # def print_fits(cls, count, fits):
    #     logging.info("<======文件数量：%s======", count)
    #     all_fits = []
    #     for key, item in sorted(fits.items(), key=lambda x: x[0]):
    #         stat_fit = cls.stat_field_fits(item)
    #         logging.info("field(total): %s: %s", item['name'], '|'.join([str(i) for i in stat_fit]))
    #         all_fits.append(stat_fit[:2])

    #         if 'idx_fits' in item:
    #             format_idx_fits = []
    #             for idx_fits in zip(*item['idx_fits']):
    #                 format_idx_fits.append('|'.join([str(i) for i in cls.stat_field_fits(idx_fits)]))
    #             logging.info("field(index): %s: %s", item['name'], ', '.join(format_idx_fits))

    #     stat_fits = list(zip(*all_fits))
    #     if stat_fits:
    #         total_fit, total = sum(stat_fits[0]), sum(stat_fits[1])
    #         total_percent = float(total_fit) / float(total)
    #         logging.info("total: %s, %s, %s", total_fit, total, total_percent)
    #     logging.info("======文件数量：%s======>", count)
    """
    fits: {
        "attr key": {
            "name": "attr name",
            "fits": [
                [1, 1, 0],  // 对应一个文档的多个答案
                [1, 0],
            ],
            "idx_fits": [
                [           // 对应一个文档的多个答案
                    [1, 0, 0, 0, 0],    //对应 fits[0] 每个预测位置是否正确
                    [0, 1, 0, 0, 0],
                    [0, 0, 0, 0, 0],    //对应 fits[1] 每个预测位置是否正确
                ],
                [...],
            ]
        }
    }
    """

    @classmethod
    def collect_report_records(cls, res):
        records = []
        for item in res:
            # only for dev
            # if item['rate'] == 1.00 and item['precision'] == 1.00:
            #     continue
            records.append(
                (
                    item["name"],
                    item["rate"],
                    item["precision"],
                    item["total"],
                    item["predict"],
                    item["match"],
                    item["detail"],
                )
            )
        records = pd.DataFrame(records, columns=["name", "recall", "precision", "sample", "predict", "match", "detail"])
        return records

    def print_report(self, count, fits, attr_cnt, tagged_counter=None):
        all_fits = []
        idx_fits = {}
        res = []
        # print(fits['主要财务数据和财务指标-时间'])
        _ratio_range = (self.ratio or "100,100").split(",")
        ratio_start = int(_ratio_range[0])
        ratio_end = int(_ratio_range[1]) if len(_ratio_range) > 1 else ratio_start
        for key, item in sorted(fits.items(), key=lambda x: x[0]):
            ratio = float(randint(ratio_start, ratio_end)) / 100
            if self.bydoc:
                stat_fit = self.stat_field_fits_by_document(item)
            else:
                stat_fit = self.stat_field_fits(item)
            # hard code: ignore 0
            # if stat_fit[0] == 0:
            #     continue
            precision = (stat_fit[0] * ratio / attr_cnt[key]) if attr_cnt.get(key) else 0  # 精度：P=TP/TP+FP
            res.append(
                {
                    "name": key,
                    "rate": stat_fit[2] * ratio,
                    "match": stat_fit[0] * ratio,
                    "total": stat_fit[1],
                    "precision": round(precision, 3) if precision <= 1 else 1,
                    "tagged": tagged_counter[item["name"]] if tagged_counter else 0,
                    "detail": [r[2] for r in stat_fit[3]],
                    "predict": attr_cnt[key],
                }
            )
            all_fits.append(stat_fit[:2])
            if item["idx_fits"]:
                idx_fits[key] = list(itertools.chain(*item["idx_fits"]))
        if not all_fits:
            logging.debug("没有文件")
            return {}

        def _sortkey(_str):
            try:
                return int(_str.split("-")[0].strip("A"))
            except ValueError:
                return _str

        if self.orderby == "name":
            res.sort(key=lambda x: _sortkey(x["name"]), reverse=False)
        else:
            res.sort(key=lambda x: float(x["rate"]), reverse=True)

        report_records = self.collect_report_records(res)
        pd.set_option("display.unicode.ambiguous_as_wide", True)
        pd.set_option("display.unicode.east_asian_width", True)
        pd.set_option("display.max_columns", None)
        pd.set_option("display.max_rows", None)
        pd.set_option("max_colwidth", 60)
        pd.set_option("display.width", 1000)
        if self.save_stat_result:
            report_records.to_csv("./stat_result.csv")
        print(report_records)

        if self.bydoc:
            total_fit, total = sum(r["rate"] for r in res), len(res)
        else:
            total_fit, total = sum(r["match"] for r in res), sum(r["total"] for r in res)
        total_percent = float(total_fit) / float(total)
        total_predict = sum(attr_cnt.values())
        precision = total_fit / total_predict if total_predict else 0
        print(
            f"fit: {total_fit}, sample: {total}, predict: {total_predict}, recall: {total_percent:.4f}, precision: {precision:.4f}"
        )
        print(f"======文件数量：{count}======")
        top_n_result = []

        result = {
            "result": res,
            "total": total,  # 标注总数
            "total_predict": total_predict,  # 预测总数
            "total_fit": total_fit,  # 预测且正确（交集）
            "total_percent": total_percent,  # recall
            "total_precision": total_fit / total_predict if total_predict else 0,  # precsion
        }
        if idx_fits:
            result.update({"top_n_result": top_n_result})

        if args and args.export:
            if not os.path.exists(args.export_dir):
                os.mkdir(args.export_dir)
            for attr, html_str_l in self.html.items():
                with open(os.path.join(args.export_dir, "%s.html" % attr), "w") as html_f:
                    html_f.write(
                        "<style>.red{color: red;font-weight: bold;}.blue{color: green;font-weight: bold;}</style>"
                    )
                    html_f.write("<ol>")
                    html_f.write("\n".join(html_str_l))
                    html_f.write("</ol>")
        if args and args.exportjson:
            export_dir = config.get_config("web.predict_from_memory.data_dir")
            if not os.path.exists(export_dir):
                os.mkdir(export_dir)
            for attr, data in self.attr_tbl_heads.items():
                json.dump(data, open(os.path.join(export_dir, "%s.json" % attr), "w"))
            # ext = '_'.join(map(str, [args.fromid, args.toid]))
            # for attr, data in cls.attr_tbl_heads.items():
            #     json.dump(data, open(os.path.join(export_dir, '%s.json.%s' % (attr, ext)), 'w'))
        return result

    @staticmethod
    def save_error_reports(error_reports):
        report_dir = os.path.join(project_root, "error_reports")
        if not os.path.exists(report_dir):
            os.mkdir(report_dir)
        for name, urls in error_reports.items():
            filepath = os.path.join(report_dir, "%s.md" % re.sub(r"/", "", name))
            if os.path.exists(filepath):
                os.remove(filepath)
            with open(filepath, "w") as dumpfp:
                dumpfp.write("# %s\r\n" % (name,))
                for url in urls:
                    dumpfp.write("- %s\r\n" % (url,))

    async def dump_stat_result(
        self, data, mold, crude, test, file_count, vid=0, tree_s=None, acid=None, export_path=None
    ):
        schema = Schema(mold.data)
        result_map = {x["name"]: x for x in data["result"]}
        ordered_result = []
        for field in schema.iter_schema_attr():
            aid = "-".join(field[1:])
            ordered_result.append(result_map.get(aid) or {"name": aid, "rate": 0})

        data["result"] = ordered_result
        if self.diff_model:
            old_version = await NewModelVersion.get_last_with_model_answer(mold.id, vid)
            model_version = await NewModelVersion.find_by_id(vid)
            data["old_version_name"] = old_version.name
            data["version_name"] = model_version.name

        params = {
            "model_type": 2 if crude else 1,
            "test": test,
            "data": json.dumps(data),
            "mold": mold.id,
            "file_count": file_count,
            "vid": vid,
            "dirs": tree_s if tree_s else [],
            "export_path": export_path,
            "status": AccuracyRecordStatus.DONE.value,
        }
        if acid:
            await NewAccuracyRecord.update_by_pk(acid, **params)
        else:
            await NewAccuracyRecord.create(**params)


@loop_wrapper
async def main():
    print(args.crude, args.save, args.fromid, args.toid)
    stat = StatScriberAnswer(
        headnum=args.headnum,
        threshold=args.threshold,
        from_id=args.fromid,
        to_id=args.toid,
        count_label=args.label,
        print_diff=args.diff,
        mold=args.mold,
        save=args.save,
        orderby=args.orderby,
        ratio=args.ratio,
        strict=args.strict,
        host=args.host,
        bydoc=args.bydoc,
        white_list=args.whitelist,
        skip_reg=args.skip_reg,
        test_accuracy_online=args.test_accuracy_online,
        save_stat_result=args.save_stat_result,
    )
    async with pw_db.atomic():
        if args.crude:
            await stat.stat_crude_answer()
        elif args.compliance:
            await stat.stat_compliance_answer()
        elif args.sse_schema5:
            await stat.stat_sse_schema5()
        else:
            await stat.stat_preset_answer()


if __name__ == "__main__":
    host = get_config("web.domain")
    parser = argparse.ArgumentParser(description="Stat scriber answer.")
    parser.add_argument("-c", "--crude", dest="crude", action="store_true", help="stat crude or preset answer")
    parser.add_argument(
        "-s", "--save", type=int, nargs="?", default=0, help="store result as train_set if 0 else test_set"
    )
    parser.add_argument("-l", "--label", dest="label", action="store_true", help="count label answer")
    parser.add_argument("-d", "--diff", dest="diff", nargs="?", const="all", help="print diff of answers")
    parser.add_argument("-e", "--export", dest="export", nargs="?", const="", help="export label answer")
    parser.add_argument("-ej", "--exportjson", dest="exportjson", nargs="?", const="", help="export label json")
    parser.add_argument(
        "-ed", "--exportdir", dest="export_dir", nargs="?", default="html", help="export label answer dir"
    )
    parser.add_argument("-f", "--fromid", type=int, nargs="?", default=0, help="stat from file id")
    parser.add_argument("-t", "--toid", type=int, nargs="?", default=0, help="stat to file id")
    parser.add_argument("-n", "--headnum", type=int, nargs="?", default=5, help="count of field answer options")
    parser.add_argument("-m", "--mold", type=int, nargs="?", default=-1, required=True, help="stat mold id")
    parser.add_argument("-r", "--ratio", type=str, help="scale ratio range")
    parser.add_argument("--bydoc", dest="bydoc", action="store_true", help="stat answer average by doc")
    parser.add_argument("--orderby", dest="orderby", help="order by col: name or rate")
    parser.add_argument("--threshold", type=float, dest="threshold", help="crude answer threshold value")
    parser.add_argument("--strict", dest="strict", action="store_true", help="statistic with strict standard")
    parser.add_argument("-cm", dest="compliance", action="store_true", help="stat rule results")
    parser.add_argument("-u", "--host", type=str, nargs="?", default=host, help="scriber host:port")
    parser.add_argument("-ex", dest="sse_schema5", action="store_true")
    parser.add_argument("--szse-export", dest="szse_export", action="store_true", help="stat szse export results")
    parser.add_argument("--whitelist", type=str, help="white list path")
    parser.add_argument("--skip-reg", type=str, help="skip schema")
    parser.add_argument("--test-accuracy-online", dest="test_accuracy_online", type=str, help="test_accuracy_online")
    parser.add_argument("-ssr", "--save-stat-result", action="store_true", help="save stat result to csv")
    parser.set_defaults(crude=False, label=False, strict=False)
    args = parser.parse_args()

    main()
