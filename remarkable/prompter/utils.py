import gc
import json
import logging
import os
import pickle
import re
import sys
import time
import warnings
from collections import defaultdict
from copy import deepcopy
from pathlib import Path

import joblib
import numpy as np
import onnxruntime as rt
import pandas as pd
import rjieba as jieba
from imblearn.over_sampling import ADASYN
from scipy.sparse import csr_matrix, hstack, load_npz, save_npz
from skl2onnx import convert_sklearn
from skl2onnx.common.data_types import FloatTensorType
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.linear_model import LogisticRegression
from sklearn.metrics import classification_report, f1_score, precision_score, recall_score, roc_auc_score
from sklearn.model_selection import train_test_split

from remarkable import config
from remarkable.common.exceptions import ModelDataNotFound
from remarkable.common.multiprocess import run_in_multiprocess
from remarkable.common.util import limit_numpy_threads
from remarkable.config import get_config
from remarkable.prompter.builder import load_file_elements

logger = logging.getLogger(__name__)


def _jieba_cut(text: str) -> str:
    return " ".join(jieba.cut(text))


# 生成json文件->提取训练集特征并保存vectorizer->训练模型并评估训练效果
# ->通过保存的vectorizer提取测试或预测集特征->加载模型评估或预测
def extract_train_feature(
    schema_id,
    train_start=0,
    train_end=0,
    use_context=True,
    context_length=1,
    ngram_1=1,
    ngram_2=1,
    separate_paragraph_table=True,
    use_pages_percent=True,
    use_syllabuses=True,
    tokenization=None,
    vid=0,
):
    logging.info("start extracting train data feature")
    start_time = time.time()

    ids = []
    attrs = []
    texts_ori = []
    types = []
    classes = []
    pages = []
    pages_percent = []
    outlines = []
    syllabuses = []
    train_index = []  # 参与训练的文档ID
    train_length = []  # 参与训练的元素块个数

    elements_dir = Path(get_config("training_cache_dir")) / str(schema_id) / str(vid or 0) / "elements"
    assert elements_dir.exists(), f"Can't find elements dir: {elements_dir}"

    for path in elements_dir.glob("*.json.zst"):
        doc_id = int(path.name.split(".")[0])
        if (train_start and train_start > doc_id) or (train_end and train_end < doc_id):
            continue
        if (data := load_file_elements(path)) and (data_len := len(data)):
            train_index.append(doc_id)
            train_length.append(data_len)
            logging.info("extract_train_feature mold:%s, file:%s, data:%s", schema_id, doc_id, data_len)
            sorted_data = sorted(data.items(), key=lambda x: int(x[0]))
            ids.extend(x[0] for x in sorted_data)
            attrs.extend(x[1]["attrs"] for x in sorted_data)
            texts_ori.extend(x[1]["text"] or "None" for x in sorted_data)
            classes.extend(x[1]["class"] for x in sorted_data)
            temp = [x[1]["page"] + 1 for x in sorted_data]
            pages.extend(temp)
            pages_percent.extend((np.array(temp, dtype=float) / max(temp)).tolist())
            outlines.extend(x[1]["outline"] for x in sorted_data)
            if use_syllabuses:
                temp = (x[1]["syllabuse"] for x in sorted_data)
                syllabuses.extend(" ".join(y["title"] for y in x) if x else "None" for x in temp)

    rules = sorted({rule for attr in attrs for rule in attr})
    labels = defaultdict(lambda: np.zeros(len(attrs), dtype=int))
    for i, attr in enumerate(attrs):
        for rule in attr:
            labels[rule][i] = 1

    logging.info("extract_train_feature texts_ori length: %s", len(texts_ori))

    if tokenization == "jieba":
        texts = run_in_multiprocess(
            _jieba_cut, texts_ori, workers=(config.get_config("prompter.workers") or 0), pool_type="thread"
        )
    else:
        texts = texts_ori

    count_vocab = False
    count_paragraph = False
    count_table = False
    count_syllabuse = False

    if separate_paragraph_table:
        logging.info("start separate_paragraph_table")
        train_inter_paragraph = [texts[i] if x == "PARAGRAPH" else "None" for i, x in enumerate(classes)]
        train_inter_table = [texts[i] if x == "TABLE" else "None" for i, x in enumerate(classes)]

        count_paragraph = TfidfVectorizer(ngram_range=(ngram_1, ngram_2), min_df=0.001)
        count_table = TfidfVectorizer(ngram_range=(ngram_1, ngram_2), min_df=0.001)

        train_inter_paragraph = count_paragraph.fit_transform(train_inter_paragraph)
        train_inter_table = count_table.fit_transform(train_inter_table)

        train_inter_vocab = hstack((train_inter_paragraph, train_inter_table)).tocsr()

        del train_inter_paragraph
        del train_inter_table
        gc.collect()

        logging.info("finish separate_paragraph_table")
    else:
        count_vocab = TfidfVectorizer(ngram_range=(ngram_1, ngram_2), min_df=0.001)
        train_inter_vocab = count_vocab.fit_transform(texts)

    if use_context:
        logging.info("start use_context")
        texts_length = len(texts)
        texts_before = [" ".join(texts[i : i + context_length]) for i in range(texts_length - context_length)]
        for _ in range(context_length):
            texts_before.insert(0, "None")
        if separate_paragraph_table:
            count_vocab = TfidfVectorizer(ngram_range=(ngram_1, ngram_2), min_df=0.001)
            train_inter_vocab_before = count_vocab.fit_transform(texts_before)
        else:
            train_inter_vocab_before = count_vocab.transform(texts_before)
        del texts_before
        gc.collect()

        texts_after = [" ".join(texts[i : i + context_length]) for i in range(context_length, texts_length)]
        for _ in range(context_length):
            texts_after.append("None")
        train_inter_vocab_after = count_vocab.transform(texts_after)

        del texts_after
        gc.collect()

        train_data = hstack((train_inter_vocab, train_inter_vocab_before, train_inter_vocab_after)).tocsr()

        del train_inter_vocab
        del train_inter_vocab_before
        del train_inter_vocab_after
        gc.collect()

        logging.info("finish use_context")
    else:
        train_data = train_inter_vocab

    if use_pages_percent:
        logging.info("start use_pages_percent")
        # train_data = hstack((train_data, csr_matrix(pages_percent).reshape(-1, 1))).tocsr()
        train_data = hstack((train_data, csr_matrix(pages_percent).reshape(-1, 1))).tocsr()
        logging.info("finish use_pages_percent")

    if use_syllabuses:
        logging.info("start use_syllabuses")
        count_syllabuse = TfidfVectorizer(ngram_range=(ngram_1, ngram_2), min_df=0.001)
        train_syllabuse = count_syllabuse.fit_transform(syllabuses)
        del syllabuses
        train_data = hstack((train_data, train_syllabuse)).tocsr()
        logging.info("finish use_syllabuses")

    logging.info("start saving")
    feature_path = os.path.join(get_config("training_cache_dir"), str(schema_id), str(vid or 0), "feature/")
    if not os.path.exists(feature_path):
        os.makedirs(feature_path)
    save_npz(feature_path + "train_data.npz", train_data)
    del train_data

    elements_info = {
        "ids": ids,
        "texts": texts_ori,
        "types": types,
        "classes": classes,
        "pages": pages,
        "outlines": outlines,
        "train_length": train_length,
        "train_index": train_index,
        "labels": dict(labels),
    }

    with open(feature_path + "train_elements_info.pkl", "wb") as f:
        pickle.dump(elements_info, f)

    if count_vocab:
        with open(feature_path + "count_vocab.pkl", "wb") as f:
            pickle.dump(count_vocab, f)
    if count_paragraph:
        with open(feature_path + "count_paragraph.pkl", "wb") as f:
            pickle.dump(count_paragraph, f)
    if count_table:
        with open(feature_path + "count_table.pkl", "wb") as f:
            pickle.dump(count_table, f)
    if count_syllabuse:
        with open(feature_path + "count_syllabuse.pkl", "wb") as f:
            pickle.dump(count_syllabuse, f)

    with open(feature_path + "rules.pkl", "wb") as f:
        pickle.dump(rules, f)

    logging.info("finish saving")
    logging.info("finished extracting train data feature in %.2fs", time.time() - start_time)


def extract_pred_feature(
    schema_id,
    vid=0,
    pred_start=0,
    pred_end=0,
    dict_data=None,
    use_context=True,
    context_length=1,
    save=True,
    separate_paragraph_table=True,
    use_pages_percent=True,
    use_syllabuses=True,
    tokenization=None,
):
    logging.info("start extracting pred data feature")
    start_time = time.time()
    feature_path = os.path.join(get_config("training_cache_dir"), str(schema_id), str(vid or 0), "feature/")
    with open(feature_path + "rules.pkl", "rb") as f:
        rules = pickle.load(f)

    ids = []
    attrs = []
    texts_ori = []
    types = []
    classes = []
    pages = []
    pages_percent = []
    outlines = []
    syllabuses = []
    pred_index = []
    pred_length = []

    elements_path = os.path.join(get_config("training_cache_dir"), str(schema_id), str(vid or 0), "elements/")
    if dict_data:
        doc_id_list = list(dict_data.keys())
        for doc_id in doc_id_list:
            logger.info(f"extracting for file: {doc_id}")
            pred_index.append(doc_id)
            pred_length.append(len(dict_data[doc_id]))
            sorted_data = sorted(dict_data[doc_id].items(), key=lambda x: int(x[0]), reverse=False)
            ids += [int(x[0]) for x in sorted_data]
            attrs += [x[1]["attrs"] for x in sorted_data]
            texts_ori += [x[1]["text"] for x in sorted_data]
            classes += [x[1]["class"] for x in sorted_data]
            temp = [x[1]["page"] + 1 for x in sorted_data]
            pages += temp
            pages_percent += list(np.array(temp, dtype=float) / max(temp))
            outlines += [x[1]["outline"] for x in sorted_data]
            if use_syllabuses:
                temp = [x[1]["syllabuse"] for x in sorted_data]
                syllabuses += [" ".join([y["title"] for y in x]) if x != [] else "None" for x in temp]
    else:
        for root, _, names in os.walk(elements_path):
            for name in names:
                doc_id = int(name.split(".")[0])
                logger.info(f"extracting for file: f{doc_id}")
                if pred_start <= doc_id <= pred_end:
                    with open(root + name) as f:
                        data = json.load(f)
                        if data == {}:
                            continue
                        pred_index.append(doc_id)
                        pred_length.append(len(data))
                        sorted_data = sorted(data.items(), key=lambda x: int(x[0]), reverse=False)
                        ids += [int(x[0]) for x in sorted_data]
                        attrs += [x[1]["attrs"] for x in sorted_data]
                        texts_ori += [x[1]["text"] for x in sorted_data]
                        classes += [x[1]["class"] for x in sorted_data]
                        temp = [x[1]["page"] + 1 for x in sorted_data]
                        pages += temp
                        pages_percent += list(np.array(temp, dtype=float) / max(temp))
                        outlines += [x[1]["outline"] for x in sorted_data]
                        if use_syllabuses:
                            temp = [x[1]["syllabuse"] for x in sorted_data]
                            syllabuses += [" ".join([y["title"] for y in x]) if x != [] else "None" for x in temp]

    labels = {}
    for rule in rules:
        labels[rule] = np.zeros(len(attrs), dtype=int)
        for i in range(len(attrs)):
            if rule in attrs[i]:
                labels[rule][i] = 1

    for i, text in enumerate(texts_ori):
        if text is None:
            texts_ori[i] = "None"

    if tokenization == "jieba":
        texts = run_in_multiprocess(
            _jieba_cut, texts_ori, workers=(config.get_config("prompter.workers") or 0), debug=True
        )
    else:
        texts = texts_ori

    if separate_paragraph_table:
        logging.info("start separate_paragraph_table")
        pred_inter_paragraph = [texts[i] if x == "PARAGRAPH" else "None" for i, x in enumerate(classes)]
        pred_inter_table = [texts[i] if x == "TABLE" else "None" for i, x in enumerate(classes)]

        with open(feature_path + "count_paragraph.pkl", "rb") as f:
            count_paragraph = pickle.load(f)

        with open(feature_path + "count_table.pkl", "rb") as f:
            count_table = pickle.load(f)

        pred_inter_paragraph = count_paragraph.transform(pred_inter_paragraph)
        pred_inter_table = count_table.transform(pred_inter_table)

        pred_inter_vocab = hstack((pred_inter_paragraph, pred_inter_table)).tocsr()
        logging.info("finish separate_paragraph_table")
    else:
        with open(feature_path + "count_vocab.pkl", "rb") as f:
            count_vocab = pickle.load(f)
        pred_inter_vocab = count_vocab.transform(texts)

    if use_context:
        logging.info("start use_context")
        texts_length = len(texts)
        texts_before = [" ".join(texts[i : i + context_length]) for i in range(texts_length - context_length)]
        for _ in range(context_length):
            texts_before.insert(0, "None")
        texts_after = [" ".join(texts[i : i + context_length]) for i in range(context_length, texts_length)]
        for _ in range(context_length):
            texts_after.append("None")

        if separate_paragraph_table:
            with open(feature_path + "count_vocab.pkl", "rb") as f:
                count_vocab = pickle.load(f)
            pred_inter_vocab_before = count_vocab.transform(texts_before)
        else:
            pred_inter_vocab_before = count_vocab.transform(texts_before)
        pred_inter_vocab_after = count_vocab.transform(texts_after)

        pred_data = hstack((pred_inter_vocab, pred_inter_vocab_before, pred_inter_vocab_after)).tocsr()
        logging.info("finish use_context")
    else:
        pred_data = pred_inter_vocab

    if use_pages_percent:
        logging.info("start use_pages_percent")
        pred_data = hstack((pred_data, csr_matrix(pages_percent).reshape(-1, 1))).tocsr()
        logging.info("finish use_pages_percent")

    if use_syllabuses:
        logging.info("start use_syllabuses")
        with open(feature_path + "count_syllabuse.pkl", "rb") as f:
            count_syllabuse = pickle.load(f)
        pred_syllabuse = count_syllabuse.transform(syllabuses)
        pred_data = hstack((pred_data, pred_syllabuse)).tocsr()
        logging.info("finish use_syllabuses")

    logging.info("finished extracting pred data feature in %.2fs", time.time() - start_time)
    if save:
        logging.info("start saving")
        feature_path = os.path.join(get_config("training_cache_dir"), str(schema_id), str(vid or 0), "feature/")
        if not os.path.exists(feature_path):
            os.makedirs(feature_path)
        save_npz(feature_path + "pred_data.npz", pred_data)
        pred_elements_info = {
            "ids": ids,
            "texts": texts_ori,
            "types": types,
            "classes": classes,
            "pages": pages,
            "outlines": outlines,
            "pred_length": pred_length,
            "pred_index": pred_index,
            "labels": labels,
        }

        with open(feature_path + "pred_elements_info.pkl", "wb") as f:
            pickle.dump(pred_elements_info, f)

        logging.info("finish saving")
    else:
        return ids, texts_ori, pages, outlines, classes, pred_length, pred_index, pred_data


def train(schema_id, vid=0, rules_use_post_process=None, multi_process=False):
    rules_use_post_process = rules_use_post_process or []
    logging.info("start training")
    start_time = time.time()

    feature_path = Path(get_config("training_cache_dir")) / str(schema_id) / str(vid or 0) / "feature"

    train_data = load_npz(feature_path / "train_data.npz")

    with open(feature_path / "train_elements_info.pkl", "rb") as f:
        elements_info = pickle.load(f)

    ids = elements_info.get("ids")
    texts = elements_info.get("texts")
    pages = elements_info.get("pages")
    outlines = elements_info.get("outlines")
    train_length = elements_info.get("train_length")
    train_index = elements_info.get("train_index")
    labels = elements_info.get("labels")

    rules = list(labels)

    del elements_info
    gc.collect()

    model_dir = Path(get_config("training_cache_dir")) / str(schema_id) / str(vid or 0) / "models"
    model_dir.mkdir(parents=True, exist_ok=True)

    if multi_process:
        result = {}
        for index in train_index:
            temp = {}
            for rule in rules:
                temp[rule] = []
            result[int(index)] = temp
        train_answers = run_in_multiprocess(
            _train_multiprocess,
            [
                (
                    schema_id,
                    vid,
                    rule,
                    labels,
                    train_data,
                    train_length,
                    train_index,
                    rules_use_post_process,
                    ids,
                    pages,
                    outlines,
                    texts,
                )
                for rule in rules
            ],
            workers=(config.get_config("prompter.workers") or 0),
        )
        logging.info("finished training in %.2fs", time.time() - start_time)
        for train_answer in train_answers:
            rule = str(list(train_answer[train_index[0]].keys())[0])
            for doc_id in train_index:
                result[doc_id][rule] = train_answer[doc_id][rule]
        return result

    result = pd.DataFrame(
        columns=[
            "rule",
            "tr_p",
            "tr_r",
            "tr_f1",
            "tr_auc",
            "tr_rate",
            "tr_match",
            "tr_total",
            "tr_pred_true",
            "tr_label_true",
        ],
    )
    result_path = os.path.join(get_config("training_cache_dir"), str(schema_id), str(vid or 0), "results/")
    threshold = 0.5
    model_dir = os.path.join(get_config("training_cache_dir"), str(schema_id), str(vid or 0), "models/")

    train_answers = {}
    for index in train_index:
        temp = {}
        for rule in rules:
            temp[rule] = []
        train_answers[int(index)] = temp

    for idx, rule in enumerate(rules):
        t2 = time.time()
        print(idx + 1, " Rule:", rule)
        y_train = labels[rule]

        model = better_lr_train(rule, train_data, y_train)

        if "/" in rule:
            rule2 = re.sub("/", "_", rule)
        else:
            rule2 = rule
        save_model_path = Path(model_dir + rule2 + "_lr.onnx")
        if not os.path.exists(model_dir):
            os.makedirs(model_dir, exist_ok=True)
        # 定义输入特征类型
        initial_type = [("fload_input", FloatTensorType([None, train_data.shape[1]]))]
        # 转换模型
        onnx_model = convert_sklearn(model, initial_types=initial_type)
        # 保存ONNX模型
        save_model_path.write_bytes(onnx_model.SerializeToString())

        y_train_pred = mixin_predict(save_model_path, train_data)

        start = end = 0
        for i, length in enumerate(train_length):
            end += length
            doc_id = int(train_index[i])

            if rule in rules_use_post_process:
                page_list = []
                for block_id in np.argsort(y_train_pred[start:end])[::-1]:
                    all_block_id = block_id + start
                    if pages[all_block_id] not in page_list:
                        page_list.append(pages[all_block_id])
                    else:
                        continue
                    block_info = {}
                    block_info["score"] = y_train_pred[all_block_id]
                    block_info["element_index"] = ids[all_block_id]
                    block_info["page"] = pages[all_block_id]
                    block_info["outline"] = outlines[all_block_id]
                    train_answers[doc_id][rule].append(block_info)
                    if len(page_list) == 5:
                        break
            else:
                for block_id in np.argsort(y_train_pred[start:end])[::-1][:5]:
                    all_block_id = block_id + start
                    block_info = {}
                    block_info["score"] = y_train_pred[all_block_id]
                    block_info["element_index"] = ids[all_block_id]
                    block_info["page"] = pages[all_block_id]
                    block_info["outline"] = outlines[all_block_id]
                    block_info["text"] = texts[all_block_id]
                    train_answers[doc_id][rule].append(block_info)
            start = end

        y_train_pred2 = deepcopy(y_train_pred)
        y_train_pred2[y_train_pred2 > threshold] = 1
        y_train_pred2[y_train_pred2 <= threshold] = 0
        precision = precision_score(y_train, y_train_pred2)
        recall = recall_score(y_train, y_train_pred2)
        f1 = f1_score(y_train, y_train_pred2)
        train_auc = 0
        if 1 in y_train:
            train_auc = roc_auc_score(y_train, y_train_pred)
        train_pred_true = sum(y_train_pred2)
        train_label_true = sum(labels[rule])

        print("TRAIN")
        print(f"{precision=}")
        print(f"{recall=}")
        print(f"{f1=}")
        print(f"{train_auc=}")
        result.loc[idx, "rule"] = rule
        result.loc[idx, "tr_p"] = round(precision, 3)
        result.loc[idx, "tr_r"] = round(recall, 3)
        result.loc[idx, "tr_f1"] = round(f1, 3)
        result.loc[idx, "tr_auc"] = train_auc
        result.loc[idx, "tr_pred_true"] = train_pred_true
        result.loc[idx, "tr_label_true"] = train_label_true
        print("cost:", time.time() - t2)

    logging.info("finished training in %.2fs", time.time() - start_time)

    if not os.path.exists(result_path):
        os.makedirs(result_path)
    result.to_csv(result_path + "train_result.csv", index=False)

    return train_answers


def init_onnx_session(model_path):
    # 创建ONNX运行时会话
    # NOTE: 限制线程数，避免k8s之类平台的资源限制问题
    options = rt.SessionOptions()
    options.inter_op_num_threads = 1
    options.intra_op_num_threads = 1
    onnx_session = rt.InferenceSession(model_path, sess_options=options)
    return onnx_session


def _onnx_predict(onnx_session: rt.InferenceSession, data) -> np.ndarray:
    input_name = onnx_session.get_inputs()[0].name
    # ONNX 要求输入为密集数组，通常为 float32 类型，所以需要转换
    dense_array = data.toarray().astype(np.float32)
    predictions = onnx_session.run(None, {input_name: dense_array})
    # 获取预测为正例的概率
    return np.array([p[1] for p in predictions[1]])


def mixin_predict(model_path: Path, data) -> np.ndarray:
    for ext in (".ort", ".onnx"):
        onnx_path = model_path.parent / f"{model_path.stem}{ext}"
        if onnx_path.exists():
            with limit_numpy_threads():
                onnx_session = init_onnx_session(onnx_path)
                return _onnx_predict(onnx_session, data)

    model = _safe_load_sklearn_model(model_path)
    return model.predict_proba(data)[:, 1]


def _safe_load_sklearn_model(model_path):
    # Ignore UserWarning: Trying to unpickle estimator LogisticRegression from version 0.23.1 when using version 1.2.2.
    # This might lead to breaking code or invalid results. Use at your own risk. For more info please refer to:
    # https://scikit-learn.org/stable/model_persistence.html#security-maintainability-limitations
    warnings.filterwarnings("ignore", category=UserWarning, module="sklearn")
    try:
        return joblib.load(model_path)
    except ModuleNotFoundError:
        import sklearn

        assert hasattr(sklearn.linear_model, "_logistic"), 'No module named "sklearn.linear_model._logistic'
        sys.modules["sklearn.linear_model.logistic"] = sklearn.linear_model._logistic
    return joblib.load(model_path)


def pred(
    schema_id,
    vid,
    pred_start=0,
    pred_end=0,
    dict_data=None,
    rules_use_post_process=None,
    has_label=False,
    direct=True,
    context_length=1,
    use_syllabuses=True,
    tokenization=None,
    separate_paragraph_table=True,
):
    feature_path = os.path.join(get_config("training_cache_dir"), str(schema_id), str(vid or 0), "feature/")
    if not os.path.exists(feature_path):
        raise ModelDataNotFound(f"Can't find model for {schema_id=} because path {feature_path} not exists")

    if direct:
        ids, texts, pages, outlines, classes, pred_length, pred_index, pred_data = extract_pred_feature(
            schema_id=schema_id,
            vid=vid,
            pred_start=pred_start,
            pred_end=pred_end,
            dict_data=dict_data,
            save=False,
            context_length=context_length,
            use_syllabuses=use_syllabuses,
            tokenization=tokenization,
            separate_paragraph_table=separate_paragraph_table,
        )
    else:
        pred_data = load_npz(feature_path + "pred_data.npz")

        with open(feature_path + "pred_elements_info.pkl", "rb") as f:
            elements_info = pickle.load(f)

        ids = elements_info.get("ids")
        texts = elements_info.get("texts")
        classes = elements_info.get("classes")
        pages = elements_info.get("pages")
        outlines = elements_info.get("outlines")
        pred_length = elements_info.get("pred_length")
        pred_index = elements_info.get("pred_index")

        if has_label:
            labels = elements_info.get("labels")
        else:
            labels = None
    logging.info("start predicting")
    start_time = time.time()

    with open(feature_path + "rules.pkl", "rb") as f:
        rules = pickle.load(f)

    if has_label:
        result = pd.DataFrame(
            index=["ALL"] + list(rules),
            columns=[
                "pr_p",
                "pr_r",
                "pr_f1",
                "pr_auc",
                "pr_rate",
                "pr_match",
                "pr_total",
                "pr_pred_true",
                "pr_label_true",
            ],
        )
    result_path = os.path.join(get_config("training_cache_dir"), str(schema_id), str(vid or 0), "results/")
    threshold = 0.5
    model_path = os.path.join(get_config("training_cache_dir"), str(schema_id), str(vid or 0), "models/")

    pred_answers = {}
    for index in pred_index:
        temp = {}
        for rule in rules:
            temp[rule] = []
        pred_answers[int(index)] = temp

    for i, rule in enumerate(rules):
        # print(i + 1, ' Rule:', rule)

        if has_label:
            y_pred = labels[rule]

        if "/" in rule:
            rule2 = re.sub("/", "_", rule)
        else:
            rule2 = rule

        y_pred_pred = mixin_predict(Path(model_path + rule2 + "_lr.model"), pred_data)

        start = end = 0
        for i, length in enumerate(pred_length):
            end += length
            doc_id = int(pred_index[i])

            if rule in rules_use_post_process:
                page_list = []
                for block_id in np.argsort(y_pred_pred[start:end])[::-1]:
                    all_block_id = block_id + start
                    if pages[all_block_id] not in page_list:
                        page_list.append(pages[all_block_id])
                    else:
                        continue
                    block_info = {}
                    block_info["score"] = y_pred_pred[all_block_id]
                    block_info["element_index"] = ids[all_block_id]
                    block_info["page"] = pages[all_block_id]
                    block_info["outline"] = outlines[all_block_id]
                    block_info["text"] = texts[all_block_id]
                    block_info["class"] = classes[all_block_id]
                    pred_answers[doc_id][rule].append(block_info)
                    if len(page_list) == 5:
                        break
            else:
                for block_id in np.argsort(y_pred_pred[start:end])[::-1][:20]:
                    all_block_id = block_id + start
                    block_info = {}
                    block_info["score"] = y_pred_pred[all_block_id]
                    block_info["element_index"] = ids[all_block_id]
                    block_info["page"] = pages[all_block_id]
                    block_info["outline"] = outlines[all_block_id]
                    block_info["text"] = texts[all_block_id]
                    block_info["class"] = classes[all_block_id]
                    if has_label:
                        block_info["label"] = y_pred[all_block_id]
                    pred_answers[doc_id][rule].append(block_info)
            start = end

        if has_label:
            y_pred_pred2 = deepcopy(y_pred_pred)
            y_pred_pred2[y_pred_pred2 > threshold] = 1
            y_pred_pred2[y_pred_pred2 <= threshold] = 0
            precision = precision_score(y_pred, y_pred_pred2)
            recall = recall_score(y_pred, y_pred_pred2)
            f1 = f1_score(y_pred, y_pred_pred2)
            pred_auc = 0
            if 1 in y_pred:
                pred_auc = roc_auc_score(y_pred, y_pred_pred)
            pred_pred_true = sum(y_pred_pred2)
            pred_label_true = sum(labels[rule])

            print("pred")
            print("precision:{}", precision)
            print("recall:", recall)
            print("f1:", f1)
            print("pred_auc:", pred_auc)

            result.loc[rule]["pr_p"] = round(precision, 3)
            result.loc[rule]["pr_r"] = round(recall, 3)
            result.loc[rule]["pr_f1"] = round(f1, 3)
            result.loc[rule]["pr_auc"] = pred_auc
            result.loc[rule]["pr_pred_true"] = pred_pred_true
            result.loc[rule]["pr_label_true"] = pred_label_true
        #  print('cost:', time.time() - t2)

    logging.info("finished predicting in %.2fs", time.time() - start_time)

    if has_label:
        if not os.path.exists(result_path):
            os.makedirs(result_path)
        result.to_csv(result_path + "pred_result.csv")

    return pred_answers


def _train_multiprocess(
    schema_id,
    vid,
    rule,
    labels,
    train_data,
    train_length,
    train_index,
    rules_use_post_process,
    ids,
    pages,
    outlines,
    texts,
):
    logging.info("start training for rule %s", rule)
    start_time = time.time()
    model_path = os.path.join(get_config("training_cache_dir"), str(schema_id), str(vid or 0), "models/")
    if "/" in rule:
        rule2 = re.sub("/", "_", rule)
    else:
        rule2 = rule
    y_train = labels[rule]

    train_answer = {}
    for index in train_index:
        train_answer[int(index)] = {}
        train_answer[int(index)][rule] = []

    if sum(y_train) == 0:
        return train_answer

    model = better_lr_train(rule, train_data, y_train)

    if not os.path.exists(model_path):
        os.makedirs(model_path, exist_ok=True)

    inital_type = [("fload_input", FloatTensorType([None, train_data.shape[1]]))]
    onnx_model = convert_sklearn(model, initial_types=inital_type)
    save_model_path = Path(model_path + rule2 + "_lr.onnx")
    save_model_path.write_bytes(onnx_model.SerializeToString())

    y_train_pred = mixin_predict(save_model_path, train_data)

    start = end = 0
    for i, length in enumerate(train_length):
        end += length
        doc_id = int(train_index[i])

        if rule in rules_use_post_process:
            page_list = []
            for block_id in np.argsort(y_train_pred[start:end])[::-1]:
                all_block_id = block_id + start
                if pages[all_block_id] not in page_list:
                    page_list.append(pages[all_block_id])
                else:
                    continue
                block_info = {}
                block_info["score"] = y_train_pred[all_block_id]
                block_info["element_index"] = ids[all_block_id]
                block_info["page"] = pages[all_block_id]
                block_info["outline"] = outlines[all_block_id]
                train_answer[doc_id][rule].append(block_info)
                if len(page_list) == 5:
                    break
        else:
            for block_id in np.argsort(y_train_pred[start:end])[::-1][:5]:
                all_block_id = block_id + start
                block_info = {}
                block_info["score"] = y_train_pred[all_block_id]
                block_info["element_index"] = ids[all_block_id]
                block_info["page"] = pages[all_block_id]
                block_info["outline"] = outlines[all_block_id]
                block_info["text"] = texts[all_block_id]
                train_answer[doc_id][rule].append(block_info)
        start = end
    logging.info("finished training for rule %s in %.2fs", rule, time.time() - start_time)
    return train_answer


def better_lr_train(label: str, x_origin, y_origin, need_report=False) -> LogisticRegression:
    """
    二八分测试、训练集，使用ADASYN处理类别不平衡问题，训练逻辑回归模型，并在测试集上评估模型
    :param label: 字段名称
    :param x_origin: 训练集特征
    :param y_origin: 训练集标签
    :param need_report: 是否需要在测试集上评估模型，默认不评估，使用全量数据训练
    """
    random_state = 42  # 固定随机种子，保证每次训练结果一致
    model = LogisticRegression(random_state=random_state, class_weight="balanced")
    try:
        if need_report:
            x_train, x_test, y_train, y_test = train_test_split(
                x_origin,
                y_origin,
                test_size=0.2,
                random_state=random_state,
            )
        else:
            x_train, x_test, y_train, y_test = x_origin, x_origin, y_origin, y_origin
        # 处理类别不平衡
        adasyn = ADASYN(random_state=random_state, n_neighbors=3)
        x_resampled, y_resampled = adasyn.fit_resample(x_train, y_train)
    except Exception as e:
        # 有些字段样本数量太少，直接使用原始数据训练逻辑回归
        logger.warning(f"类别平衡优化失败，使用全量数据进行训练，建议增加标注数量 [{label}]: {e}")
        x_resampled, x_test, y_resampled, y_test = x_origin, x_origin, y_origin, y_origin

    model.fit(x_resampled, y_resampled)

    if need_report:
        predictions = model.predict(x_test)
        report = classification_report(y_test, predictions, zero_division=0)
        logger.info(f"Train report for [{label}]:\n{report}")
    return model


if __name__ == "__main__":
    pass
