from collections import defaultdict
from itertools import product

import numpy as np

MAX_DIFF_COUNT = 90


def gen_lcs(paragraphs_a, paragraphs_b, diff_mapping):
    length_a = len(paragraphs_a)
    length_b = len(paragraphs_b)
    c = np.zeros((length_a + 1, length_b + 1))
    flag = np.zeros((length_a + 1, length_b + 1))

    for i in range(1, length_a + 1):
        for j in range(1, length_b + 1):
            result = diff_mapping.get((i - 1, j - 1))
            if result:
                c[i, j] = c[i - 1, j - 1] + 1
                flag[i, j] = 2
            else:
                if c[i - 1, j] >= c[i, j - 1]:
                    c[i, j] = c[i - 1, j]
                    flag[i, j] = 1
                else:
                    c[i, j] = c[i, j - 1]
                    flag[i, j] = 3
    return c, flag


def get_lcs(paragraphs_a, paragraphs_b, diff_mapping):
    i = len(paragraphs_a)
    j = len(paragraphs_b)
    if i == 0 or j == 0:
        return []

    full_lcs = []
    if i + j <= MAX_DIFF_COUNT:
        match_items = defaultdict(list)
        keys = diff_mapping.keys()
        left_idxes = sorted({idx[0] for idx in keys})
        right_idxes = sorted({idx[1] for idx in keys})
        # 分别以左和右作为基准行查找匹配的子串,取最长子串内的最大匹配
        l_r_datas = calc_full_lcs_by_diff_mapping(left_idxes, right_idxes, diff_mapping)
        reverse_mapping = {(r, l): val for (l, r), val in diff_mapping.items()}  # noqa
        r_l_datas = calc_full_lcs_by_diff_mapping(right_idxes, left_idxes, reverse_mapping)
        merge_datas = l_r_datas + [[(l, r) for r, l in items] for items in r_l_datas]  # noqa
        for items in merge_datas:
            match_items[len(items)].append(items)
        max_ratio = 0
        if match_items:
            for items in match_items[max(match_items.keys())]:
                diffs = [diff_mapping[(l_idx, r_idx)] for (l_idx, r_idx) in items]
                ratio = sum(item.ratio for item in diffs)
                if not full_lcs or max_ratio < ratio:
                    full_lcs = diffs
                    max_ratio = ratio

        if len(left_idxes) == len(full_lcs):
            return full_lcs

    ratios, flag = gen_lcs(paragraphs_a, paragraphs_b, diff_mapping)
    lcs = []
    while i > 0 and j > 0:
        if flag[i][j] == 2:
            lcs = [diff_mapping.get((i - 1, j - 1))] + lcs
            i -= 1
            j -= 1
            continue
        if flag[i][j] == 1:
            i -= 1
            continue
        if flag[i][j] == 3:
            j -= 1
            continue
        break
    return lcs if len(lcs) > len(full_lcs) else full_lcs


def calc_full_lcs_by_diff_mapping(left_idxes, right_idxes, diff_mapping):
    if not left_idxes:
        return []
    l_idx = left_idxes[0]
    lcs = [[(l_idx, r_idx)] for r_idx in right_idxes if (l_idx, r_idx) in diff_mapping]
    if len(left_idxes) == 1:
        return lcs

    result = calc_full_lcs_by_diff_mapping(left_idxes[1:], right_idxes, diff_mapping)
    if not result:
        return lcs

    new_lcs = []
    # prev在tails x轴的上层，整体从右下角向左上角做排列组合，如果存在x轴不同，y轴相等，则拆分
    is_match = False
    for prevs, tails in product(lcs, result):
        prev = prevs[0]
        first_tail = tails[0]
        if prev[-1] == first_tail[-1]:
            new_lcs.append([prev, *tails[1:]])
            new_lcs.append(tails)
            is_match = True
        elif prev[-1] < first_tail[-1]:
            new_lcs.append([prev, *tails])
            is_match = True
    if not is_match:
        return result
    return new_lcs
