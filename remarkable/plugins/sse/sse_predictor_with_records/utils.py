import re
from copy import deepcopy

# table types:
col_0_row_merge_tbl = "col_0_row_merge_tbl"
col_0_row_merge_and_head_col_merge_tbl = "col_0_row_merge_and_head_col_merge_tbl"
head_col_merge_tbl = "head_col_merge_tbl"
no_merge_tbl = "no_merge_tbl"
unknown_type_tbl = "unknown_type_tbl"
most_wide_col_merge_tbl = "most_wide_col_merge_tbl"

# record types:
single_record = "single_record"
have_head_record = "have_head_record"
horizontal_record = "horizontal_record"
semi_horzontal_record = "semi_horzontal_record"
vertical_record = "vertical_record"
unknown_record_type = "unknown_record_type"
tall_and_short_record = "tall_and_short_record"


def flat_merges(merges):
    output = []
    for _ in merges:
        output.extend(_)
    return output


def get_label_key(merges):
    label_key = merges[0][0]
    for merge_group in merges:
        for key in merge_group:
            if key[1] < label_key[1] or (key[1] == label_key[1] and key[0] < label_key[0]):
                label_key = key
    return tuple(label_key)


def judge_key_in_row_merge(tbl, cell_key):
    key = list(cell_key)
    for merge_group in tbl["merged"]:
        if key in merge_group:
            min_y = min(merge_group, key=lambda x: x[0])[0]
            max_y = max(merge_group, key=lambda x: x[0])[0]
            if min_y < max_y:
                return max_y
            else:
                return 0
    return 0


def judge_tall_and_short_record(tbl, record):
    if len(record) != 2:
        return False
    left_key = min(record, key=lambda x: x[1])
    right_key = max(record, key=lambda x: x[1])
    l_l, l_t, l_r, l_b = tbl["cells"][left_key]["range"]
    r_l, r_t, r_r, r_b = tbl["cells"][right_key]["range"]
    if l_t == r_t and l_b > r_b:
        return True
    return False


def get_record_type(tbl, record):
    if len(record) == 1:
        return single_record
    is_horizontal, is_vertical = True, True
    is_semi_horizontal = True
    left, t, r, b = tbl["cells"][record[0]]["range"]
    for key in record:
        cur_l, cur_t, cur_r, cur_b = tbl["cells"][key]["range"]
        if left != cur_l or r != cur_r:
            is_vertical = False
        if t != cur_t or b != cur_b:
            is_horizontal = False
        if t != cur_t:
            is_semi_horizontal = False

    if is_vertical:
        return vertical_record
    elif judge_tall_and_short_record(tbl, record):
        return tall_and_short_record
    elif is_horizontal:
        return horizontal_record
    elif is_semi_horizontal:
        return semi_horzontal_record
    else:
        return unknown_record_type


def judge_cell_0_0_merge_type(tbl):
    if "0_1" not in tbl["cells"] and "1_0" not in tbl["cells"] and "0_2" in tbl["cells"] and "2_0" in tbl["cells"]:
        return "row_and_col_merge_2*2"
    elif "0_1" not in tbl["cells"] and "1_0" in tbl["cells"] and "0_2" in tbl["cells"]:
        return "col_merge_2"
    elif "0_1" in tbl["cells"] and "1_0" not in tbl["cells"] and "2_0" in tbl["cells"]:
        return "row_merge_2"
    else:
        return ""


def convert_cell_keys(tbl):
    tbl_ = deepcopy(tbl)
    for cell_key in tbl_["cells"]:
        if isinstance(cell_key, str):
            y, x = cell_key.split("_")
            y, x = int(y), int(x)
            new_cell_key = (y, x)
            tbl["cells"][new_cell_key] = tbl["cells"].pop(cell_key)
    return tbl


def add_merge_info(tbl):
    keys = []
    boxes = []
    tbl_ = deepcopy(tbl)
    merge_idx2merge = {}
    merges = []
    for cell_key in tbl_["cells"]:
        y, x = cell_key
        cur_box = (tuple(tbl_["cells"][cell_key]["box"]), tbl_["cells"][cell_key]["page"])
        if cur_box not in boxes:
            keys.append(cell_key)
            boxes.append(cur_box)
            merge_idx2merge[cur_box] = [[y, x]]
        else:
            old_key_idx = boxes.index(cur_box)
            old_y, old_x = keys[old_key_idx][0], keys[old_key_idx][1]
            if old_y + old_x >= y + x:
                keys[old_key_idx] = cell_key
                tbl["cells"].pop((old_y, old_x))
            else:
                tbl["cells"].pop(cell_key)
            merge_idx2merge[cur_box].append([y, x])
    for merge_key in merge_idx2merge:
        cur_merge = merge_idx2merge[merge_key]
        if len(cur_merge) > 1:
            merges.append(cur_merge)
    tbl["merged"] = merges
    return tbl


def add_range_for_cells(tbl):
    merges = tbl["merged"]
    flatten_merges = flat_merges(merges)
    for cell_key in tbl["cells"]:
        c_t, c_l = cell_key
        if list(cell_key) not in flatten_merges:
            tbl["cells"][cell_key]["range"] = [c_l, c_t, c_l + 1, c_t + 1]
        else:
            tbl["cells"][cell_key]["range"] = get_range_for_merged_cell(cell_key, merges)
    return tbl


def get_range_for_merged_cell(cell_key, merges):
    for merge_group in merges:
        for merged_key in merge_group:
            if tuple(merged_key) == cell_key:
                merge_range = get_merge_range(merge_group)
                return [merge_range[0], merge_range[1], merge_range[2] + 1, merge_range[3] + 1]
    c_t, c_l = cell_key
    return [c_l, c_t, c_l + 1, c_t + 1]


def get_merge_range(merge_group):
    min_y = min(merge_group, key=lambda x: x[0])[0]
    max_y = max(merge_group, key=lambda x: x[0])[0]
    min_x = min(merge_group, key=lambda x: x[1])[1]
    max_x = max(merge_group, key=lambda x: x[1])[1]
    return [min_x, min_y, max_x, max_y]


def add_merge_info_for_cells(tbl):
    for cell_key in tbl["cells"]:
        cell = tbl["cells"][cell_key]
        is_col_merge_cell, is_row_merge_cell = False, False
        col_merge_len, row_merge_len = 1, 1
        c_l, c_t, c_r, c_b = cell["range"]
        if c_r != c_l + 1:
            is_col_merge_cell = True
            col_merge_len = c_r - c_l
        if c_b != c_t + 1:
            is_row_merge_cell = True
            row_merge_len = c_b - c_t
        tbl["cells"][cell_key]["col_merge_len"] = col_merge_len
        tbl["cells"][cell_key]["row_merge_len"] = row_merge_len
        if is_row_merge_cell and is_col_merge_cell:
            tbl["cells"][cell_key]["merge"] = "row_and_col_merge"
        elif is_col_merge_cell:
            tbl["cells"][cell_key]["merge"] = "col_merge"
        elif is_row_merge_cell:
            tbl["cells"][cell_key]["merge"] = "row_merge"
        else:
            tbl["cells"][cell_key]["merge"] = "no_merge"
    return tbl


def get_row_and_col_num(tbl):
    row_num, col_num = 0, 0
    for cell_key in tbl["cells"]:
        r, b = tbl["cells"][cell_key]["range"][2], tbl["cells"][cell_key]["range"][3]
        if r > col_num:
            col_num = r
        if b > row_num:
            row_num = b
    return row_num, col_num


def preprocess_table(tbl):
    new2old_row_idx_map = []
    tbl = convert_cell_keys(tbl)
    if "skip_rows" in tbl:
        tbl, new2old_row_idx_map = delete_useless_rows(tbl)
    tbl = add_merge_info(tbl)
    tbl = add_range_for_cells(tbl)
    tbl = add_merge_info_for_cells(tbl)
    return tbl, new2old_row_idx_map


def restore_records(records, new2old_row_idx_map):
    for i, record in enumerate(records):
        for j, cell_key in enumerate(record):
            records[i][j] = (new2old_row_idx_map[cell_key[0]], cell_key[1])
    return records


def delete_useless_rows(tbl):
    tbl_ = deepcopy(tbl)
    del tbl_["cells"]
    tbl_["cells"] = {}
    new2old_row_idx_map = {}
    useless_row_idxes = tbl["skip_rows"]
    row_num = 0
    for cell_key in tbl["cells"]:
        if cell_key[0] > row_num:
            row_num = cell_key[0]
    row_num += 1

    new_row_idx = 0
    for row_idx in range(row_num):
        if row_idx not in useless_row_idxes:
            new2old_row_idx_map[new_row_idx] = row_idx
            new_row_idx += 1
        else:
            pass
    old2new_row_idx_map = {value: key for key, value in new2old_row_idx_map.items()}

    for cell_key in tbl["cells"]:
        if cell_key[0] not in useless_row_idxes:
            cell = tbl["cells"][cell_key]
            tbl_["cells"][(old2new_row_idx_map[cell_key[0]], cell_key[1])] = cell

    return tbl_, new2old_row_idx_map


def get_col_cell_num(tbl):
    max_x = 0
    for cell_key in tbl["cells"]:
        if cell_key[1] > max_x:
            max_x = cell_key[1]
    return max_x + 1


def get_row_cell_num(tbl):
    max_y = 0
    for cell_key in tbl["cells"]:
        if cell_key[0] > max_y:
            max_y = cell_key[0]
    return max_y + 1


def get_title_lens(tbl):
    row_0_widths, row_1_widths, col_0_heights, col_1_heights = [], [], [], []
    cell_max_x, cell_max_y = get_col_cell_num(tbl), get_row_cell_num(tbl)
    for x in range(cell_max_x):
        if (0, x) not in tbl["cells"]:
            row_0_widths.append(0)
        else:
            row_0_widths.append(tbl["cells"][(0, x)]["range"][2] - tbl["cells"][(0, x)]["range"][0])
        if (1, x) not in tbl["cells"]:
            row_1_widths.append(0)
        else:
            row_1_widths.append(tbl["cells"][(1, x)]["range"][2] - tbl["cells"][(1, x)]["range"][0])
    for y in range(cell_max_y):
        if (y, 0) not in tbl["cells"]:
            col_0_heights.append(0)
        else:
            col_0_heights.append(tbl["cells"][(y, 0)]["range"][3] - tbl["cells"][(y, 0)]["range"][1])
        if (y, 1) not in tbl["cells"]:
            col_1_heights.append(0)
        else:
            col_1_heights.append(tbl["cells"][(y, 1)]["range"][3] - tbl["cells"][(y, 1)]["range"][1])
    return row_0_widths, row_1_widths, col_0_heights, col_1_heights


def get_head_and_col_0_merge_info(row_0_widths, col_0_heights, col_1_heights):
    merge_lens = []
    merge_idxs = []
    merge_nums = []
    for i, width in enumerate(row_0_widths):
        if width > 1 and i != 0:
            if width in merge_lens:
                cur_width_idx = merge_lens.index(width)
                merge_idxs[cur_width_idx].append(i)
                merge_nums[cur_width_idx] += 1
            else:
                merge_lens.append(width)
                merge_idxs.append([i])
                merge_nums.append(1)
    if not merge_nums:
        return [], []
    max_merge_idx = merge_nums.index(max(merge_nums))
    head_col_merge_range = []
    for _ in merge_idxs[max_merge_idx]:
        head_col_merge_range.append([_, _ + merge_lens[max_merge_idx]])

    real_merge_lens = []
    merge_lens = []
    merge_idxs = []
    merge_nums = []
    merge_range = []
    height_info = {}
    for i, height in enumerate(col_0_heights):
        if height > 1 and i != 0:
            real_height = get_real_height_for_col_merge(col_1_heights[i : i + height])
            height_info[i] = height
            if real_height in real_merge_lens:
                cur_height_idx = real_merge_lens.index(real_height)
                merge_idxs[cur_height_idx].append(i)
                merge_nums[cur_height_idx] += 1
            else:
                real_merge_lens.append(real_height)
                merge_idxs.append([i])
                merge_nums.append(1)
            if height in merge_lens:
                merge_lens.index(height)
            else:
                merge_lens.append(height)
    if not merge_nums:
        return [], []
    max_merge_idx = merge_nums.index(max(merge_nums))
    real_merge_len = real_merge_lens[max_merge_idx]
    if real_merge_len >= 3:
        for idx in merge_idxs[max_merge_idx]:
            merge_range.append([idx, idx + height_info[idx] - 1])
        if real_merge_len - 2 in real_merge_lens:
            cur_len_idx = real_merge_lens.index(real_merge_len - 2)
            for idx in merge_idxs[cur_len_idx]:
                merge_range.append([idx, idx + height_info[idx] - 1])
        if real_merge_len - 1 in real_merge_lens:
            cur_len_idx = real_merge_lens.index(real_merge_len - 1)
            for idx in merge_idxs[cur_len_idx]:
                merge_range.append([idx, idx + height_info[idx] - 1])
        if real_merge_len + 1 in real_merge_lens:
            cur_len_idx = real_merge_lens.index(real_merge_len + 1)
            for idx in merge_idxs[cur_len_idx]:
                merge_range.append([idx, idx + height_info[idx] - 1])
        if real_merge_len + 2 in real_merge_lens:
            cur_len_idx = real_merge_lens.index(real_merge_len + 2)
            for idx in merge_idxs[cur_len_idx]:
                merge_range.append([idx, idx + height_info[idx] - 1])
        if real_merge_len + 3 in real_merge_lens:
            cur_len_idx = real_merge_lens.index(real_merge_len + 3)
            for idx in merge_idxs[cur_len_idx]:
                merge_range.append([idx, idx + height_info[idx] - 1])
    else:
        for idx in merge_idxs[max_merge_idx]:
            merge_range.append([idx, idx + height_info[idx] - 1])
    return head_col_merge_range, merge_range


def get_head_merge_info(row_0_widths):
    merge_lens = []
    merge_idxs = []
    merge_nums = []
    for i, width in enumerate(row_0_widths):
        if width > 1:
            if width in merge_lens:
                cur_width_idx = merge_lens.index(width)
                merge_idxs[cur_width_idx].append(i)
                merge_nums[cur_width_idx] += 1
            else:
                merge_lens.append(width)
                merge_idxs.append([i])
                merge_nums.append(1)
    if not merge_nums:
        return -1, -1
    max_merge_idx = merge_nums.index(max(merge_nums))
    return merge_idxs[max_merge_idx], merge_lens[max_merge_idx]


def get_real_height_for_col_merge(col_1_heights):
    # 统计第一列在第0列合并单元格右侧的单元格个数
    real_height = 0
    for _ in col_1_heights:
        if _ > 0:
            real_height += 1
    return real_height


def get_col_0_merge_info(col_0_heights, col_1_heights):
    real_merge_lens = []
    merge_lens = []
    merge_idxs = []
    merge_nums = []
    merge_range = []
    height_info = {}
    for i, height in enumerate(col_0_heights):
        if height > 1:
            real_height = get_real_height_for_col_merge(col_1_heights[i : i + height])
            height_info[i] = height
            if real_height in real_merge_lens:
                cur_height_idx = real_merge_lens.index(real_height)
                merge_idxs[cur_height_idx].append(i)
                merge_nums[cur_height_idx] += 1
            else:
                real_merge_lens.append(real_height)
                merge_idxs.append([i])
                merge_nums.append(1)
            if height in merge_lens:
                pass
            else:
                merge_lens.append(height)
    if not merge_nums:
        return []
    max_merge_idx = merge_nums.index(max(merge_nums))
    real_merge_len = real_merge_lens[max_merge_idx]
    if real_merge_len >= 4:
        for idx in merge_idxs[max_merge_idx]:
            merge_range.append([idx, idx + height_info[idx] - 1])
        if real_merge_len - 2 in real_merge_lens:
            cur_len_idx = real_merge_lens.index(real_merge_len - 2)
            for idx in merge_idxs[cur_len_idx]:
                merge_range.append([idx, idx + height_info[idx] - 1])
        if real_merge_len - 1 in real_merge_lens:
            cur_len_idx = real_merge_lens.index(real_merge_len - 1)
            for idx in merge_idxs[cur_len_idx]:
                merge_range.append([idx, idx + height_info[idx] - 1])
        if real_merge_len + 1 in real_merge_lens:
            cur_len_idx = real_merge_lens.index(real_merge_len + 1)
            for idx in merge_idxs[cur_len_idx]:
                merge_range.append([idx, idx + height_info[idx] - 1])
        if real_merge_len + 2 in real_merge_lens:
            cur_len_idx = real_merge_lens.index(real_merge_len + 2)
            for idx in merge_idxs[cur_len_idx]:
                merge_range.append([idx, idx + height_info[idx] - 1])
        if real_merge_len + 3 in real_merge_lens:
            cur_len_idx = real_merge_lens.index(real_merge_len + 3)
            for idx in merge_idxs[cur_len_idx]:
                merge_range.append([idx, idx + height_info[idx] - 1])
    else:
        for idx in merge_idxs[max_merge_idx]:
            merge_range.append([idx, idx + height_info[idx] - 1])
    return merge_range


def get_non_zero_num(widths):
    i = 0
    for _ in widths:
        if _ > 0:
            i += 1
    return i


def judge_int_in_range(num, ranges):
    for range_ in ranges:
        if range_[0] <= num <= range_[1]:
            return True
    return False


def find_int_in_range(num, ranges):
    for range_ in ranges:
        if range_[0] <= num <= range_[1]:
            return [range_[0], range_[1]]
    return []


def get_record_range(record):
    min_x, max_x, min_y, max_y = 8192, 0, 8192, 0
    for key in record:
        min_x = min(min_x, key[1])
        max_x = max(max_x, key[1])
        min_y = min(min_y, key[0])
        max_y = max(max_y, key[0])
    return min_x, min_y, max_x, max_y


def judge_cell_key_in_col_merge(tbl, cell_key):
    if cell_key[0] < 0:
        return False
    merges = tbl["merged"]
    list_cell_key = list(cell_key)
    for merge_group in merges:
        if list_cell_key in merge_group:
            min_x = min(merge_group, key=lambda x: x[1])[1]
            max_x = max(merge_group, key=lambda x: x[1])[1]
            if min_x != max_x:
                return True
            return False
    return False


def count_bigger_than_1_num(nums):
    num = 0
    for _ in nums:
        if _ > 1:
            num += 1
    return num


def is_date(chars, high_recall=True):
    NEED_TO_TRANSFORM_TIMES = [
        "同比",
        "年初",
        "去年",
        "上年末",
        "上年",
        "期初",
        "期末",
        "上年同期",
        "上一年",
        "年末",
        "上期",
        "上一年末",
        "上一年度末",
        "同期",
        "上期末",
        "上一年年末",
        "去年同期",
        "上年同期",
        "上年度",
        "上期",
        "上半年",
        "上半年末",
        "上年期末",
        "去年末",
        "上年全年",
        "上年度同期",
        "[一两二三四1234]季度",
        "上一年度",
        "上年末",
        "之前年度",
        "往年",
        "前一会计年度",
        "去年年末",
        "去年期末",
        "当年末",
        "上一年末",
        "上一会计年度",
        "前两年",
        "前一年度",
        "前一年",
        "上年年末",
        "去年[一两二三四1234]季度",
        "同期末",
        "前三年",
        "上年同比",
        "去年同比",
    ]
    NEED_TO_TRANSFORM_TIMES.sort(key=lambda x: -len(x))
    NEED_TO_TRANSFORM_TIMES_REG = "(?:" + "|".join(NEED_TO_TRANSFORM_TIMES) + "){1}"
    DATETIMES = []
    DATETIMES.append(
        r"[12][789012][0-9]{2}(?:年度|年末|年)?(?:(?:[01]?[0-9\-]{0,5})[-/\\.月])?[末初前后底份]?(?:[0-3]{0,1}[0-9]{1}[日])?[-－—至到～~]{1,2}(?:(?:[12][789012][0-9]{2}(?:财|全|年全|年度上半|年上半|上半|年度下半|年下半|下半|年半)?年度?(?:[年期]?[前中后末底份])?)|(?:[第前]?[一二三四1234]季度?(?:[季期]?[末初前后底])?|[01]?[0-9\-－—至到～~月和一二三四五六七八九十]{0,6}月[末初前后底份]?(?:[0-3]?[0-9]日)?)){1,2}"
    )  # noqa
    DATETIMES.append(
        r"[12][789012][0-9]{2}(?:财|全|年全|年度上半|年上半|上半|年度下半|年下半|下半|年半)?年度?(?:[年期]?[末初前后底])?(?:[第前]?[一二三四1234]季度?(?:[季期]?[末初前后底])?|[01]?[0-9\-－—至到～~月和一二三四五六七八九十]{0,6}月[末初前后底份]?(?:[0-3]?[0-9]日)?)?(?:以来)?"
    )  # noqa
    DATETIMES.append(
        r"[12][789012][0-9]{2}[-/.－／][01]?[0-9](?:[-/.－／][0-3]?[0-9])?(?:[-－—至到～~]{1,2}[12][789012][0-9]{2}[-/.－／][01]?[0-9](?:[-/.－／][0-3]?[0-9])?)?(?![0-9])"
    )  # noqa
    DATETIMES.append(
        r"[0-9]{2}年(?:[第前]?[一二三四1234]季度?(?:[季期]?[末初前后底])?|[末初底]{1}|[01]?[0-9\-－—至到～~月和一二三四五六七八九十]{0,6}月[末初前后底份]?(?:[0-3]?[0-9]日)?)(?:以来)?"
    )  # noqa
    DATETIMES.append(NEED_TO_TRANSFORM_TIMES_REG)
    DATETIME = r"({})(?!五大|5大)".format(r"|".join(DATETIMES))
    P_DATETIME = re.compile(DATETIME)

    for iter1 in P_DATETIME.finditer("".join(chars)):
        start, end = iter1.start(), iter1.end()
        if end - start == len(chars):
            return True
    if high_recall:
        if len(chars) == 4 and chars[0] == "2" and chars[1] == "0" and chars[2] in "012":
            return True
    return False


def get_col_0_date_num(tbl):
    date_num = 0
    for cell_key in tbl["cells"]:
        if cell_key[1] != 0:
            continue
        cell = tbl["cells"][cell_key]
        text = cell["text"]
        if (is_date(text) or not text) and cell["range"][3] - cell["range"][1] > 1:
            date_num += 1
    return date_num


def add_movable_cell_info(tbl, known_record):
    row_0_widths, row_1_widths, col_0_heights, col_1_heights = get_title_lens(tbl)
    y_ranges = []
    min_x, min_y, max_x, max_y = get_record_range(known_record)
    record_type = get_record_type(tbl, record=known_record)
    head_merge_ranges, col_0_merge_ranges = get_head_and_col_0_merge_info(row_0_widths, col_0_heights, col_1_heights)
    if record_type == single_record:
        tbl_type = no_merge_tbl
        x_label_keys, y_label_keys = [], []
        known_y, known_x = known_record[0]
        known_bottom = tbl["cells"][known_record[0]]["range"][3]
        bottom_edge = 8192
        for x in range(known_x - 1, -1, -1):
            if (known_y, x) in tbl["cells"]:
                if tbl["cells"][(known_y, x)]["range"][3] > known_bottom:
                    bottom_edge = tbl["cells"][(known_y, x)]["range"][3]
                    break
        for y in range(known_y + 1, bottom_edge):
            if (y, known_x) in tbl["cells"]:
                tbl["cells"][(y, known_x)]["movable"] = True
    elif (row_0_widths[0] == len(row_0_widths) and (0, 0) in known_record) or (
        row_1_widths[0] == len(row_1_widths) and (1, 0) in known_record
    ):
        tbl_width = len(row_0_widths)
        tbl_type = most_wide_col_merge_tbl
        x_label_keys = []
        y_label_keys = []
        for cell_key in tbl["cells"]:
            if cell_key[1] == 0 and tbl["cells"][cell_key]["range"][2] == tbl_width:
                x_label_keys.append([cell_key[0], 0])
                tbl["cells"][cell_key]["movable"] = False
            else:
                tbl["cells"][cell_key]["movable"] = True
    elif 0 not in row_0_widths[2:] and 0 not in col_0_heights:
        # no merge
        tbl_type = no_merge_tbl
        x_label_keys = []
        y_label_keys = []
        if record_type == horizontal_record:
            for cell_key in tbl["cells"]:
                if cell_key[0] >= min_y and min_x <= cell_key[1] <= max_x:
                    tbl["cells"][cell_key]["movable"] = True
                else:
                    tbl["cells"][cell_key]["movable"] = False
        elif record_type == semi_horzontal_record:
            for cell_key in tbl["cells"]:
                if cell_key[0] >= min_y and min_x <= cell_key[1] <= max_x:
                    tbl["cells"][cell_key]["movable"] = True
                else:
                    tbl["cells"][cell_key]["movable"] = False
        elif record_type == vertical_record:
            for cell_key in tbl["cells"]:
                if cell_key[1] >= min_x and min_y <= cell_key[0] <= max_y:
                    tbl["cells"][cell_key]["movable"] = True
                else:
                    tbl["cells"][cell_key]["movable"] = False
        elif record_type == have_head_record:
            for cell_key in tbl["cells"]:
                if cell_key[0] == 0:
                    tbl["cells"][cell_key]["movable"] = False
                else:
                    tbl["cells"][cell_key]["movable"] = True
        elif record_type == unknown_record_type:
            for cell_key in tbl["cells"]:
                if cell_key[0] == 0:
                    tbl["cells"][cell_key]["movable"] = False
                else:
                    tbl["cells"][cell_key]["movable"] = True
        else:
            pass
    elif get_non_zero_num(row_0_widths) == 1:
        tbl_type = head_col_merge_tbl
        x_label_keys = []
        y_label_keys = []
        for idx, _ in enumerate(row_0_widths):
            if _ > 1:
                x_label_keys.append((0, idx))
        for cell_key in tbl["cells"]:
            if cell_key[0] != 0:
                tbl["cells"][cell_key]["movable"] = True
            else:
                tbl["cells"][cell_key]["movable"] = False
    elif (
        row_0_widths[0] == 1 and col_0_heights[0] in [1, 2, 3] and 0 in row_0_widths[1:] and 0 not in col_0_heights[3:]
    ) or (0 in row_0_widths and 0 not in col_0_heights[2:]):
        tbl_type = head_col_merge_tbl
        x_label_keys = []
        y_label_keys = []
        for idx, _ in enumerate(row_0_widths):
            if _ > 1:
                x_label_keys.append((0, idx))
        for cell_key in tbl["cells"]:
            if cell_key[0] == 0 or cell_key[0] == 1:
                tbl["cells"][cell_key]["movable"] = False
            elif cell_key[0] == 2 and judge_cell_key_in_col_merge(tbl, (cell_key[0] - 1, cell_key[1])):
                tbl["cells"][cell_key]["movable"] = False
            else:
                tbl["cells"][cell_key]["movable"] = True
    elif (
        0 in col_0_heights[2:]
        and 0 not in row_0_widths
        and count_bigger_than_1_num(col_0_heights) > 1
        and get_col_0_date_num(tbl) >= 2
    ):
        tbl_type = col_0_row_merge_tbl
        x_label_keys = []
        y_label_keys = []
        col_0_merge_ranges = get_col_0_merge_info(col_0_heights, col_1_heights)
        for cell_key in tbl["cells"]:
            if (cell_key[1] == 0 and judge_int_in_range(cell_key[0], col_0_merge_ranges)) or (
                cell_key[0] == 0 and not judge_int_in_range(cell_key[0], col_0_merge_ranges)
            ):
                tbl["cells"][cell_key]["movable"] = False
            else:
                tbl["cells"][cell_key]["movable"] = True
        for range_ in col_0_merge_ranges:
            y_label_keys.append((range_[0], 0))
        y_ranges = col_0_merge_ranges
    elif head_merge_ranges and col_0_merge_ranges:
        tbl_type = col_0_row_merge_and_head_col_merge_tbl
        x_label_keys = []
        y_label_keys = []
        for cell_key in tbl["cells"]:
            if cell_key[0] == 0 or cell_key[1] == 0:
                tbl["cells"][cell_key]["movable"] = False
            else:
                tbl["cells"][cell_key]["movable"] = True
        for range_ in col_0_merge_ranges:
            y_label_keys.append((range_[0], 0))
        for range_ in head_merge_ranges:
            x_label_keys.append((0, range_[0]))
        y_ranges = col_0_merge_ranges
    else:
        tbl_type = unknown_type_tbl
        x_label_keys = []
        y_label_keys = []
        for cell_key in tbl["cells"]:
            if min_x <= cell_key[1] <= max_x:
                tbl["cells"][cell_key]["movable"] = True
            else:
                tbl["cells"][cell_key]["movable"] = False

    return tbl, tbl_type, x_label_keys, y_label_keys, y_ranges
