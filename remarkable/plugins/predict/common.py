import logging
import re
from collections import Counter
from copy import deepcopy
from functools import lru_cache
from typing import Pattern

from remarkable.common.pattern import PatternCollection
from remarkable.common.util import clean_txt
from remarkable.pdfinsight.text_util import clear_syl_title
from remarkable.plugins.cgs.common.patterns_util import P_CATALOG_TITLE

P_CLEAN_CATALOG_NUM = PatternCollection(
    [
        r"[:：]?[\.-]*([\d]|[IVXLCM])+$",
    ]
)


def is_paragraph_elt(elt):
    return elt.get("class") in ["PARAGRAPH", "PAGE_HEADER", "PAGE_FOOTER"]


def is_shape_with_text(elt):
    if elt.get("class") == "SHAPE" and elt.get("text"):
        return True
    return False


def is_stamp_with_text(elt):
    if elt.get("class") == "STAMP" and elt.get("text"):
        return True
    return False


def is_table_elt(elt):
    return elt.get("class") in ["TABLE"]


def extend_list(left, right):
    if not isinstance(left, list):
        left = [left]
    ret = deepcopy(left)
    if isinstance(right, list):
        ret.extend(right)
    else:
        ret.append(right)
    return ret


def build_feature_pattern(feature: str, match_method: str | None = None) -> list[Pattern]:
    patterns = []
    try:
        if feature.startswith("__regex__"):
            patterns = [re.compile(p) for p in filter(None, feature.split("__regex__"))]
        elif match_method == "extract":
            patterns = [re.compile(rf"^{re.escape(f)}$") for f in feature.split("|")]
        else:
            # contain or other conditions
            patterns = [re.compile(rf"{re.escape(f)}") for f in feature.split("|")]
    except:  # noqa
        logging.error(f"invalid feature:{feature}")
    return patterns


def clean_syllabus_feature(model_data: Counter) -> Counter:
    cleaned_data = Counter()
    for feature, count in model_data.most_common():
        split_char = "__regex__" if feature.startswith("__regex__") else "|"
        if split_char == "|":
            feature = split_char.join([clear_syl_title(p) for p in filter(None, feature.split(split_char))])
        cleaned_data.update({feature: count})
    return cleaned_data


@lru_cache()
def clear_syl_title_num(title):
    title = clean_txt(title)
    return P_CLEAN_CATALOG_NUM.sub("", title).strip()


@lru_cache()
def is_catalog(title):
    return P_CATALOG_TITLE.nexts(title)


def find_nearest_syl(elt_idx, sylls):
    """
    获取一个元素块上方最近的章节标题
    """
    for syl in sylls:
        start_id, to_id = syl["range"]
        if to_id - start_id <= 1:
            continue
        if start_id + 1 == elt_idx:
            return syl
    return None


def find_syl_by_elt_index(elt_idx, sylls):
    """Unique element index"""
    sylls = [s for s in sylls if elt_idx in range(*s["range"])]
    return sorted(sylls, key=lambda s: s["index"])


def get_element_candidates(crude_answers, path, priors=None, limit=10):
    crude_answers = crude_answers or {}
    priors = priors or []
    _candidates = []
    key = "-".join(path)
    if key in crude_answers:
        _candidates = crude_answers[key]
    else:
        for name, elements in crude_answers.items():
            if name.startswith(key):
                if any(name.endswith(prior) for prior in priors):
                    elements = deepcopy(elements)
                    for ele in elements:
                        ele["ordering"] = ele["score"] + 0.5
                _candidates.extend(elements)
    _distinct_set = set()
    for item in sorted(_candidates, key=lambda c: c.get("ordering", c["score"]), reverse=True):
        if item["element_index"] in _distinct_set:
            continue
        _distinct_set.add(item["element_index"])
        yield item
        if limit and len(_distinct_set) == limit:
            return


def is_syl_elt(element, syllabus_dict):
    syllabuse = syllabus_dict.get(element["syllabus"])
    if syllabuse and syllabuse["element"] == element["index"]:
        return True
    return False
