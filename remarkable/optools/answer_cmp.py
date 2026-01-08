#!/usr/bin/env python
# encoding: utf8
# pylint: skip-file
from __future__ import division

import argparse
import copy
import glob
import json
import os
import re
import sys

PY2 = int(sys.version[0]) == 2

if PY2:
    text_type = unicode  # noqa
    binary_type = str
    string_types = (str, unicode)  # noqa
    unicode = unicode  # noqa
    basestring = basestring  # noqa
    from collections import OrderedDict as dict
else:
    text_type = str
    binary_type = bytes
    string_types = (str,)
    unicode = str
    basestring = (str, bytes)

# 招股说明书属性
template_2 = {
    "B-1-1": {
        "label": "发行人基本情况",
        "keys": [],
        "attrs": [
            "发行人名称",
            "成立日期",
            "行业分类",
            "在其他交易场所(申请)挂牌或上市的情况",
        ],
    },
    "B-1-2": {
        "label": "本次发行的有关中介机构",
        "keys": [],
        "attrs": [
            "保荐人",
            "主承销商",
            "发行人律师",
            "其他承销机构",
        ],
    },
    "B-2-1": {
        "label": "本次发行的基本情况",
        "keys": [],
        "attrs": [
            "每股面值",
            "发行股数",
            "发行股数占发行后总股本比例",
            "发行后总股本",
            "募集资金总额",
            "募集资金净额",
            "募集资金投资项目",
            "发行费用概算",
        ],
    },
    "B-3": {
        "label": "发行人报告期的主要财务数据和财务指标",
        "keys": ["时间"],
        "attrs": [
            "时间",
            "资产总额",
            "归属于母公司所有者权益",
        ],
    },
    "B-6-1": {
        "label": "发行人选择的具体上市标准",
        "keys": [],
        "attrs": [
            "条款编号",
        ],
    },
    "B-6-2": {
        "label": "发行人选择的具体上市标准",
        "keys": [],
        "attrs": [
            "具体标准内容",
        ],
    },
    "C-2-1": {
        "label": "中介机构_保荐人(主承销商)",
        "keys": [],
        "attrs": [
            "机构名称",
            "发行代表人",
        ],
    },
    "E-8-1": {
        "label": "发行人股东情况_实际控制人",
        "keys": [],
        "attrs": [
            "实际控制人",
        ],
    },
    "E-8-5": {
        "label": "发行人股东情况_控股股东/实际控制人股份质押情况",
        "keys": [],
        "attrs": [
            "控股股东/实际控制人股份是否存在质押情况",
        ],
    },
    "E-9-2": {
        "label": "发行人股东情况_前十名股东",
        "keys": ["股东姓名/名称"],
        "attrs": [
            "股东姓名/名称",
            "持股数量",
            "持股比例",
        ],
    },
    "E-9-6": {
        "label": "发行人股东情况_股东关系",
        "keys": [],
        "attrs": [
            "股东关系",
        ],
    },
    "E-10-1": {
        "label": "发行人股东情况_董事会成员",
        "keys": ["姓名"],
        "attrs": [
            "姓名",
            "任期",
            "简历",
        ],
    },
    "F-4-2": {
        "label": "业务与技术_前五供应商",
        "keys": ["供应商名称", "时间"],
        "attrs": [
            "时间",
            "供应商名称",
            "采购额",
            "货币单位",
        ],
    },
    "G-3": {
        "label": "公司治理与独立性_发行人协议控制架构情况",
        "keys": [],
        "attrs": [
            "发行人协议控制架构情况",
        ],
    },
    "H-1-3": {
        "label": "财务会计信息_合并资产负债表",
        "keys": ["时间"],
        "attrs": [
            "时间",
            "货币基金(流动资产)",
            "长期股权投资(非流动资产)",
            "非流动资产合计(非流动资产)",
            "资产总计",
        ],
    },
    "H-2": {
        "label": "财务会计信息_审计意见",
        "keys": [],
        "attrs": [
            "审计意见",
        ],
    },
    "H-10-2": {
        "label": "财务会计信息_营业收入分区域分析",
        "keys": ["时间", "地区"],
        "attrs": [
            "时间",
            "地区",
            "收入",
            "单位",
            "占比",
        ],
    },
    "I-1-1": {
        "label": "募集资金_募集资金总量及使用情况",
        "keys": ["项目名称"],
        "attrs": [
            "货币单位",
            "项目名称",
            "总投资额",
            "募集资金投资额",
            "审批文号",
        ],
    },
    "K-3": {
        "label": "其他重要事项_重大诉讼",
        "keys": [],
        "attrs": [
            "是否有重大诉讼",
            "重大诉讼情况",
        ],
    },
}
# 变更证券简称公告
template_3 = {
    "A": {"label": "证券代码", "keys": [], "attrs": ["证券代码"]},
    "B": {"label": "证券简称", "keys": [], "attrs": ["证券简称"]},
    "C": {"label": "公告编号", "keys": [], "attrs": ["公告编号"]},
    "D": {"label": "变更后的证券简称", "keys": [], "attrs": ["变更后的证券简称"]},
    "E": {
        "label": "变更日期",
        "keys": [],
        "attrs": [
            "变更日期",
        ],
    },
    "F": {"label": "公告日", "keys": [], "attrs": ["公告日"]},
}
templates = {2: template_2, 3: template_3}
sep = " > "
fit_dict = {}
std_answer = {}


# confusion matrix
# [ [true negative, false positive],
#   [false negative, true positive] ]


def clean_txt(_str):
    if _str is None:  # TODO: 有可能混入None, 需要排查导出脚本
        _str = "null"
    return re.sub(r"\s+", "", _str)


def remove_useless_substring(_str):
    return re.sub(r"[\s\t\n]", "", _str)


def clean_data(data):
    if isinstance(data, (tuple, list)):
        data = [clean_data(e) for e in data]
    elif isinstance(data, dict):
        for key in data:
            data[key] = clean_data(data[key])
    elif isinstance(data, basestring):
        data = remove_useless_substring(data)
    return data


def same_value(list1, list2):
    if list1 == list2:
        return True
    list_1 = map(clean_txt, list1)
    list_2 = map(clean_txt, list2)
    if any(x == y for y in list_2 for x in list_1) or any(x == y for y in list_1 for x in list_2):
        return True
    return False


def cm_given_sets(label_ids, predict_ids):
    label_ids_set = set(label_ids)
    predict_ids_set = set(predict_ids)
    fn = len(label_ids_set - predict_ids_set)
    fp = len(predict_ids_set - label_ids_set)
    tp = len(predict_ids_set.intersection(label_ids_set))
    return [[0, fp], [fn, tp]]


def matrix_plus(m1, m2):
    assert len(m1) == len(m2)
    if not m1:
        return m1
    n_row = len(m1)
    assert all(len(m1[i]) == len(m2[i]) for i in range(n_row))
    n_col = len(m1[0])
    result = []
    for i in range(n_row):
        row = []
        for j in range(n_col):
            row.append(m1[i][j] + m2[i][j])
        result.append(row)
    return result


def has_neg(cm):
    return cm[0][1] + cm[1][0] >= 1


def cm_to_prf1(cm):
    """
    :param cm: [tn, fp], [fn, tp]
    :return: p, r, f1
    """
    tp, truth_positive, predict_positive = cm_to_tp_t_p(cm)
    precision = tp / predict_positive if predict_positive else 1.0
    recall = tp / truth_positive if truth_positive else 1.0
    f1 = 2 * precision * recall / (precision + recall) if precision + recall else 0
    return precision, recall, f1


def cm_to_tp_t_p(cm):
    [_, fp], [fn, tp] = cm
    truth_positive = fn + tp
    predict_positive = fp + tp
    return tp, truth_positive, predict_positive


def update_file_cms(accum_cms, new_cm):
    """
    :param accum_cms: 一个 AnsComparer.cm 对象
    :param new_cm:
    :return:
    """
    for l1_attr, new_l1_performance in new_cm.items():
        l1_performance = accum_cms.setdefault(l1_attr, {})
        l1_performance.setdefault("cm", [[0, 0], [0, 0]])
        l1_performance["cm"] = matrix_plus(l1_performance["cm"], new_l1_performance["cm"])
        if "attrs" in new_l1_performance:
            new_l2_performance = new_l1_performance["attrs"]
            l2_performance = l1_performance.setdefault("attrs", {})
            for attr, new_l2_cm in new_l2_performance.items():
                l2_performance.setdefault(attr, [[0, 0], [0, 0]])
                l2_performance[attr] = matrix_plus(l2_performance[attr], new_l2_cm)
    return accum_cms


class AnsComparer:
    def __init__(self, f1, f2, mold):
        self.label_answer = json.load(open(f1, encoding="utf8"))
        self.label_answer = clean_data(self.label_answer)
        assert self.label_answer, "标注答案为空"
        self.preset_answer = json.load(open(f2, encoding="utf8"))
        self.preset_answer = clean_data(self.preset_answer)
        assert self.preset_answer, "预测答案为空"
        self.cm = {}  # confusion matrix, {'一级指标label': {'cm': [], 'attrs': {'二级指标': [cm], ...}}}
        for pos, info in self.label_answer.items():
            std_answer.setdefault(pos, {}).setdefault("record", []).extend(info.get("record", []))
        self.mold = mold

    def level1_record_str(self, record):
        """
        把一级字段中的一条记录变成一个 str 作为这个记录的 identifier
        相同的记录有相同的 identifier
        """
        record_str = ""
        keys = sorted(record.keys())
        for l2_attr in keys:
            value_str = "{}".format(sorted(record[l2_attr]))
            record_str += l2_attr + value_str
        return record_str

    def records_list_to_dict(self, records, keys):
        records_dict = {}
        for record in records:
            key = "".join([str(record.get(k, [])) for k in keys])
            records_dict[key] = record

    def add_order(self, records):
        for i, record in enumerate(records):
            record["$index$"] = i

    def cmp(self):
        for code, info in self.mold.items():
            records1 = self.label_answer.get(code, {}).get("record", [])
            records2 = self.preset_answer.get(code, {}).get("record", [])
            performance = {}
            if not info["keys"]:
                # 未定义主键的，只比较第一组值
                record1 = records1[0] if records1 else {}
                record2 = records2[0] if records2 else {}
                record1_strs = [self.level1_record_str(record1)] if records1 else []
                record2_strs = [self.level1_record_str(record2)] if records2 else []
                performance["cm"] = cm_given_sets(record1_strs, record2_strs)
                performance["attrs"] = {}
                for attr in info["attrs"]:
                    key = sep.join([info["label"], attr])
                    label_list = record1.get(attr, [])
                    predict_list = record2.get(attr, [])
                    cm = cm_given_sets(label_list, predict_list)
                    performance["attrs"][attr] = cm
                    if has_neg(cm):
                        print("--------------------- 预测错误: %s" % key)
                        print("                      标注答案: %s" % label_list)
                        print("                      预测答案: %s" % predict_list)
            else:
                # 有定义主键的，说明这个一级字段允许多条记录，那么不记录其二级字段的cm
                if info.get("ordered", False):
                    self.add_order(records1)
                    self.add_order(records2)
                records1_id_list = [self.level1_record_str(r) for r in records1]
                records2_id_list = [self.level1_record_str(r) for r in records2]
                performance["cm"] = cm_given_sets(records1_id_list, records2_id_list)
            self.cm["{}_{}".format(code, info["label"])] = performance


def mean(list_):
    return sum(list_) / len(list_)


def cms_to_report_matrix(cms):
    def cm_to_report_record(cm, level, name):
        p, r, f1 = cm_to_prf1(cm)
        true_positive, truth_positive, predict_positive = cm_to_tp_t_p(cm)
        return [p, r, f1, true_positive, predict_positive, truth_positive, level, name, cm]

    cols = ["precision", "recall", "f1", "match", "predict", "truth", "level", "attr", "混淆矩阵"]
    all_records = []
    precisions = []
    recalls = []
    f1s = []
    for attr_name, perform in cms.items():
        if "attrs" not in perform:
            record = cm_to_report_record(perform["cm"], 1, attr_name)
            all_records.append(record)
            precisions.append(record[0])
            recalls.append(record[1])
            f1s.append(record[2])
        else:
            for l2_attr_name, l2_cm in perform["attrs"].items():
                record = cm_to_report_record(l2_cm, 2, "{} > {}".format(attr_name, l2_attr_name))
                all_records.append(record)
                precisions.append(record[0])
                recalls.append(record[1])
                f1s.append(record[2])
    all_records.append([mean(precisions), mean(recalls), mean(f1s), 0, 0, 0, 0, "整体得分", ""])
    return cols, all_records


def report(cols, all_records, output_file=None):
    """
    打印报表
    :param cols: 指标名称
    :param all_records: 所有要打印的记录
    :param output_file: file path
    :return:
    """
    print("  {:>10} {:>8} {:>8} | {:>8} {:>8} {:>8} | {:>6}| {}".format(*cols))
    for record in all_records:
        print("  {:>10.2f} {:>8.2f} {:>8.2f} | {:>8.0f} {:>8.0f} {:>8.0f} | {:>6}| {}".format(*record))

    if output_file is None:
        return
    try:
        import pandas as pd

        df = pd.DataFrame(all_records, columns=cols)
        # style.background_gradient('RdYlGn', subset=['precision', 'recall', 'f1'], axis=1)
        df.to_excel(output_file, index=None, float_format="%.3f")
    except ImportError:
        print("install pandas first to get Excel output (pip install pandas)")


def cmp_file(file1, file2, mold_id):
    if not (os.path.isfile(file1) and os.path.isfile(file2)):
        sys.exit("Invalid file detected, check your input param please")
    cmp_obj = AnsComparer(file1, file2, templates[mold_id])
    cmp_obj.cmp()
    return cmp_obj


def gather_files_results(all_cms):
    records = []  # 三维数组，file - record - col
    for cms in all_cms.values():
        cols, file_records = cms_to_report_matrix(cms)
        records.append(file_records)
    n_files = len(records)
    if not records:
        return [], []
    output_records = []
    for i in range(len(records[0])):
        record = copy.deepcopy(records[0][i])
        for j, col in enumerate(cols):
            if col in ["precision", "recall", "f1"]:
                record[j] = mean([records[fi][i][j] for fi in range(n_files)])
            elif col in ["predict", "match", "truth"]:
                record[j] = sum([records[fi][i][j] for fi in range(n_files)])
        output_records.append(record)
    return cols, output_records


def cmp_dirs(std_dir, pred_dir, mold_id):
    if not os.path.isdir(std_dir):
        sys.exit("folder {} not find".format(std_dir))
    if not os.path.isdir(pred_dir):
        sys.exit("folder {} not find".format(pred_dir))
    all_cms = {}
    std_files = glob.glob("{}/*.json".format(std_dir))
    pred_files = glob.glob("{}/*.json".format(pred_dir))
    std_files_dict = {os.path.basename(f).split("_")[0]: f for f in std_files}
    pred_files_dict = {os.path.basename(f).split("_")[0]: f for f in pred_files}
    for i, (prefix, std_file) in enumerate(std_files_dict.items()):
        if prefix not in pred_files_dict:
            print("  Warn: File with prefix {} not find in prediction".format(prefix))
            continue
        pred_file = pred_files_dict[prefix]
        print('{}: Start to compare "{}" base on "{}"'.format(i, std_file, pred_file))
        all_cms[prefix] = cmp_file(std_file, pred_file, mold_id).cm
    print("==========" * 10)
    print("Summary:")
    print("\tCompared {} file".format(len(all_cms)))
    n_not_found = len(std_files) - len(all_cms)
    if n_not_found:
        print("\t {} file not find in prediction".format(n_not_found))
    # summary_cms = {}
    # for cms in all_cms.values():
    #     update_file_cms(summary_cms, cms)
    cols, output_records = gather_files_results(all_cms)
    return cols, output_records


def main(args):
    if args.dirs and len(args.dirs) == 2 and args.mold in (2, 3):
        col, records = cmp_dirs(args.dirs[0], args.dirs[1], args.mold)
    elif args.files and len(args.files) == 2 and args.mold in (2, 3):
        col, records = cms_to_report_matrix(cmp_file(args.files[0], args.files[1], args.mold).cm)
    else:
        sys.exit("Usage: {} -h (for help info)".format(sys.argv[0]))
    report(col, records, args.output)


if __name__ == "__main__":
    parser = argparse.ArgumentParser("Answer Compare Tool")
    parser.add_argument("-m", "--mold", type=int, required=True, help="2: 招股说明书, 3: 变更证券简称")
    parser.add_argument(
        "-o",
        "--output",
        default=None,
        help="保存为 Excel，保存路径如 a.xlsx。保存在运行这个代码的文件夹下。需要首先在命令行安装 Pandas，方法： pip install pandas",
    )
    group = parser.add_mutually_exclusive_group()
    group.add_argument("-f", "--files", nargs="+", default=[], help="std_file, pred_file")
    group.add_argument("-d", "--dirs", nargs="+", default=[], help="std_dir, pred_dir")
    main(parser.parse_args())
