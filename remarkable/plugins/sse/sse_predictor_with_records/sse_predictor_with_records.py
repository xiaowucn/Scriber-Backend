# pylint: skip-file
# import os
import json
from copy import deepcopy

from remarkable.plugins.sse.sse_predictor_with_records import utils
from remarkable.plugins.sse.sse_predictor_with_records.get_expandable_group import GetExpandableGroup

debug_mode = 0


def get_key(key_list):
    key = ""
    key_list_len = len(key_list)
    for i, _ in enumerate(key_list):
        key += _.split(":")[0]
        if i != key_list_len - 1:
            key += "@"
    return key


def get_cell_key_for_box(ele, box_c_x, box_c_y, box_page_key):
    for cell_key in ele["cells"]:
        cell = ele["cells"][cell_key]
        c_l, c_t, c_r, c_b = cell["box"]
        if c_l <= box_c_x <= c_r and c_t <= box_c_y <= c_b and box_page_key == cell["page"]:
            y, x = [int(_) for _ in cell_key.split("_")]
            return (y, x)
    return None


def judge_is_tbl_data(boxes, page_keys, tbl):
    tbl_l, tbl_t, tbl_r, tbl_b = tbl["outline"]
    cell_keys = []
    for i, box in enumerate(boxes):
        box_l, box_t, box_r, box_b = box
        box_c_x, box_c_y = 0.5 * (box_l + box_r), 0.5 * (box_t + box_b)
        if page_keys[i] == tbl["page"]:
            if not (tbl_l <= box_c_x <= tbl_r and tbl_t <= box_c_y <= tbl_b):
                return None
        cell_key = get_cell_key_for_box(tbl, box_c_x, box_c_y, page_keys[i])
        if cell_key is None:
            return None
        cell_keys.append(cell_key)
    return cell_keys


def add_single_data_answers(single_data_answers, results, page_key):
    # 里面的answer全都是该页的
    def add_group_data_answers(new_v, results, page_key):
        answer_num = len(list(new_v.values())[0])
        cur_results = [[] for _ in range(answer_num)]
        if answer_num <= 1:
            return results
        for v in new_v.values():
            if len(v) != answer_num:
                return results
            for i, box in enumerate(v):
                cur_results[i].extend(box)
        if page_key not in results:
            results[page_key] = cur_results
        else:
            results[page_key].append(cur_results)
        return results

    all_single_answers = {}
    for k, box in single_data_answers.items():
        attributes = k.split("@")
        if len(attributes) != 3:
            continue
        new_k = attributes[0] + "@" + attributes[1]
        new_v = attributes[2]
        if new_k not in all_single_answers:
            all_single_answers[new_k] = {new_v: box}
        else:
            all_single_answers[new_k][new_v] = box
    for new_v in all_single_answers.values():
        results = add_group_data_answers(new_v, results, page_key)
    return results


def is_schema_or_not(name):
    if name.count("@") == 1:
        return True
    return False


def get_table_page_keys(tbl):
    page_keys = []
    for cell_key in tbl["cells"]:
        page_key = tbl["cells"][cell_key]["page"]
        if page_key not in page_keys:
            page_keys.append(page_key)
    return page_keys


def get_table_outlines_for_many_pages_table(tbl):
    outlines = {}
    for cell_key in tbl["cells"]:
        cell = tbl["cells"][cell_key]
        page_key = cell["page"]
        if page_key not in outlines:
            outlines[page_key] = [cell["box"][0], cell["box"][1], cell["box"][2], cell["box"][3]]
        else:
            outlines[page_key] = [
                min(cell["box"][0], outlines[page_key][0]),
                min(cell["box"][1], outlines[page_key][1]),
                max(cell["box"][2], outlines[page_key][2]),
                max(cell["box"][3], outlines[page_key][3]),
            ]
    return outlines


def merge_boxes_in_one_cell(tbl, data):
    for data_ in data:
        if len(data_["boxes"]) == 1:
            continue
        will_delete_idxes = []
        occupied_cells = {}
        for i, box in enumerate(data_["boxes"]):
            box_page = box["page"]
            box_x_c = 0.5 * (box["box"]["box_left"] + box["box"]["box_right"])
            box_y_c = 0.5 * (box["box"]["box_top"] + box["box"]["box_bottom"])
            for cell_key in tbl["cells"]:
                cell = tbl["cells"][cell_key]
                cell_page = cell["page"]
                if cell_page != box_page:
                    continue
                if cell["box"][0] <= box_x_c <= cell["box"][2] and cell["box"][1] <= box_y_c <= cell["box"][3]:
                    if cell_key not in occupied_cells:
                        occupied_cells[cell_key] = i
                    else:
                        will_delete_idxes.append(i)
                        data_["boxes"][occupied_cells[cell_key]]["box"]["box_left"] = min(
                            data_["boxes"][occupied_cells[cell_key]]["box"]["box_left"], box["box"]["box_left"]
                        )
                        data_["boxes"][occupied_cells[cell_key]]["box"]["box_top"] = min(
                            data_["boxes"][occupied_cells[cell_key]]["box"]["box_top"], box["box"]["box_top"]
                        )
                        data_["boxes"][occupied_cells[cell_key]]["box"]["box_right"] = max(
                            data_["boxes"][occupied_cells[cell_key]]["box"]["box_right"], box["box"]["box_right"]
                        )
                        data_["boxes"][occupied_cells[cell_key]]["box"]["box_bottom"] = max(
                            data_["boxes"][occupied_cells[cell_key]]["box"]["box_bottom"], box["box"]["box_bottom"]
                        )
                    break
        will_delete_idxes.sort(reverse=True)
        for del_idx in will_delete_idxes:
            del data_["boxes"][del_idx]
    return data


def get_y_sum(result):
    output = 0
    for _ in result:
        output += _[0]
    return output


def get_x_sum(result):
    output = 0
    for _ in result:
        output += _[1]
    return output


def convert_cell_key_format(cell_key):
    if isinstance(cell_key, str):
        y, x = cell_key.split("_")
        y, x = int(y), int(x)
        return y, x
    return cell_key


def flat_list(cell_keys):
    output = []
    for _ in cell_keys:
        output.extend(_)
    return output


def judge_result(predict_cell_keys, result):
    for result_ in result:
        if result_ not in predict_cell_keys:
            return False
    return True


def get_intersection(cell_keys, result):
    intersection_num = 0
    for _ in result:
        if _ in cell_keys:
            intersection_num += 1
    return intersection_num


def all_cells_in_one_col(tbl, cell_keys):
    merges = tbl["merged"]
    flatten_merges = flat_list(merges)
    if list(cell_keys[0]) not in flatten_merges:
        for cell_key in cell_keys:
            if list(cell_key) in flatten_merges:
                return False
        return True
    else:
        c_r = 0
        for merge in merges:
            if list(cell_keys[0]) in merge:
                c_r = max(merge, key=lambda x: x[1])[1]
                break
        for cell_key in cell_keys:
            if list(cell_key) not in flatten_merges:
                return False
            for merge in merges:
                if list(cell_key) in merge:
                    cur_c_r = max(merge, key=lambda x: x[1])[1]
                    if cur_c_r != c_r:
                        return False
                    break
        return True


def judge_is_all_y_diff(tbl, record0, record1):
    distance = record1[0][0] - record0[0][0]
    record_len = len(record0)
    if distance > 0:
        if not all_cells_in_one_col(tbl, record0) or not all_cells_in_one_col(tbl, record1):
            return False, 0
        for i in range(record_len):
            if record1[i][0] - record0[i][0] != distance or record1[i][1] != record0[i][1]:
                return False, 0
        return True, distance
    else:
        return False, 0


def judge_is_all_x_diff(tbl, record0, record1):
    flatten_merges = flat_list(tbl["merged"])
    distance = record1[0][1] - record0[0][1]
    record_len = len(record0)
    if distance > 0:
        for i in range(record_len):
            if (
                record1[i][1] - record0[i][1] != distance
                or record1[i][0] != record0[i][0]
                or [record0[i][0], record0[i][1]] in flatten_merges
                or [record1[i][0], record1[i][1]] in flatten_merges
            ):
                return False, 0
        return True, distance
    else:
        return False, 0


def judge_is_y_diff_except_col_0(tbl, record0, record1):
    record_len = len(record0)
    distance = 0
    col_0_key = ()
    for i in range(record_len):
        if record0[i][1] == 0 and record1[i][1] == 0:
            continue
        if record0[i][1] != 0 and record1[i][1] != 0:
            distance = record1[i][0] - record0[i][0]
            break
        if debug_mode:
            print("return point 1")
        return False, 0, ()
    for i in range(record_len):
        if record0[i][1] == 0 and record0[i] == record1[i]:
            col_0_key = record0[i]
    if not col_0_key:
        if debug_mode:
            print("return point 2")
        return False, 0, ()
    if [col_0_key[0], col_0_key[1]] not in flat_list(tbl["merged"]):
        if debug_mode:
            print("return point 3")
        return False, 0, ()
    for i in range(record_len):
        if record0[i][1] != 0 and record1[i][1] != 0 and record1[i][0] - record0[i][0] != distance:
            if debug_mode:
                print("return point 4")
            return False, 0, ()
    return True, distance, col_0_key


def judge_is_y_diff_except_head(tbl, record0, record1):
    record_len = len(record0)
    distance = 0
    head_key = ()
    for i in range(record_len):
        if record0[i][0] == 0 and record1[i][0] == 0:
            continue
        if record0[i][0] != 0 and record1[i][0] != 0:
            distance = record1[i][0] - record0[i][0]
            break
        return False, 0, ()
    for i in range(record_len):
        if record0[i][0] == 0 and record0[i] == record1[i]:
            head_key = record0[i]
    if not head_key:
        return False, 0, ()
    if list(head_key) not in flat_list(tbl["merged"]):
        return False, 0, ()
    for i in range(record_len):
        if record0[i][0] != 0 and record1[i][0] != 0 and record1[i][0] - record0[i][0] != distance:
            return False, 0, ()
    return True, distance, head_key


def judge_is_y_diff_except_col_0_and_head(tbl, record0, record1):
    record_len = len(record0)
    distance = 0
    head_key = ()
    for i in range(record_len):
        if (record0[i][0] == 0 and record1[i][0] == 0) or (record0[i][1] == 0 and record1[i][1] == 0):
            continue
        if record0[i][1] != 0 and record1[i][1] != 0 and record0[i][0] != 0 and record1[i][0] != 0:
            distance = record1[i][0] - record0[i][0]
            break
        return False, 0, ()
    for i in range(record_len):
        if record0[i][0] == 0 and record0[i] == record1[i]:
            head_key = record0[i]
    if not head_key:
        return False, 0, ()
    if list(head_key) not in flat_list(tbl["merged"]):
        return False, 0, ()
    for i in range(record_len):
        if (
            record0[i][1] != 0
            and record1[i][1] != 0
            and record0[i][0] != 0
            and record1[i][0] != 0
            and record1[i][0] - record0[i][0] != distance
        ):
            return False, 0, ()
    return True, distance, head_key


def judge_no_merge_in_cells(known_cell_keys, tbl):
    flatten_merges = flat_list(tbl["merged"])
    for cell_key in known_cell_keys:
        if list(cell_key) in flatten_merges:
            return False
    return True


def judge_left_side_have_merge(tbl, cell_keys):
    most_top_cell_key = min(cell_keys, key=lambda x: x[1])
    merges = tbl["merged"]
    detect_key = [most_top_cell_key[0], most_top_cell_key[1] - 1]
    if detect_key in flat_list(merges):
        for merge in merges:
            if detect_key in merge:
                return True, max(merge, key=lambda x: x[0])[0]
    return False, 0


def get_merge_max_y(tbl, merged_key):
    for merge in tbl["merged"]:
        if list(merged_key) in merge:
            return max(merge, key=lambda x: x[0])[0]
    return -1


def get_merge_max_x(tbl, merged_key):
    for merge in tbl["merged"]:
        if list(merged_key) in merge:
            return max(merge, key=lambda x: x[1])[1]
    return -1


def get_index_in_group(group, merged_key):
    for i, member in enumerate(group):
        if merged_key in member:
            return i
    return -1


def get_index_in_merges(merges, merged_key):
    for i, member in enumerate(merges):
        if merged_key in member:
            return i
    return -1


def get_refer_key(tbl, key):
    if str(key[0]) + "_" + str(key[1]) in tbl["cells"]:
        return str(key[0]) + "_" + str(key[1])
    for merge_group in tbl["merged"]:
        if key in merge_group:
            refer_y = min(merge_group, key=lambda x: x[0])[0]
            refer_x = min(merge_group, key=lambda x: x[1])[1]
            return str(refer_y) + "_" + str(refer_x)
    return ""


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


def get_row_merge_cell_idx(tbl, merged_key):
    key = list(merged_key)
    for merge_group in tbl["merged"]:
        if key in merge_group:
            return (min(merge_group, key=lambda x: x[0])[0], merged_key[1])
    return merged_key


class SsePredictorWithRecord:
    @classmethod
    def predict_with_one_record(cls, tbl, known_record):
        if not known_record:
            return []
        tbl, new2old_row_idx_map = utils.preprocess_table(tbl)
        tbl, tbl_type, x_label_keys, y_label_keys, y_ranges = utils.add_movable_cell_info(tbl, known_record)
        records = cls.get_rest_records(tbl, known_record, tbl_type, x_label_keys, y_label_keys, y_ranges)
        records = cls.add_expandable_group_to_result(tbl, records, tbl_type)
        # cls.judge_result(records, record_len)
        if new2old_row_idx_map:
            records = utils.restore_records(records, new2old_row_idx_map)
        return records

    @classmethod
    def judge_new_key_in_records(cls, new_key, records):
        for record in records:
            if new_key in record:
                return True
        return False

    @classmethod
    def get_rest_records(cls, tbl, known_record, tbl_type, x_label_keys, y_label_keys, y_ranges):
        row_num = utils.get_row_cell_num(tbl)
        records = deepcopy([known_record])
        record_type = utils.get_record_type(tbl, known_record)
        if debug_mode:
            print(tbl_type, record_type)
        if record_type == utils.single_record:
            if tbl_type == utils.no_merge_tbl:
                i = 1
                know_y, known_x = known_record[0]
                while i < row_num:
                    new_key = (know_y + i, known_x)
                    if new_key in tbl["cells"]:
                        if tbl["cells"][new_key].get("movable"):
                            records.append([new_key])
                            i += 1
                        else:
                            break
                    else:
                        i += 1
            else:
                pass
        elif record_type in [utils.have_head_record, utils.unknown_record_type]:
            if tbl_type == utils.col_0_row_merge_tbl:
                i = 1
                is_right_new_record = True
                range_ = []
                while True:
                    continue_expand = False
                    new_record = []
                    for key in known_record:
                        range_ = utils.find_int_in_range(key[0], y_ranges)
                        if range_:
                            break
                    if range_:
                        for key in known_record:
                            if tbl["cells"][key].get("movable"):
                                new_key = (key[0] + i, key[1])
                                if new_key not in tbl["cells"]:
                                    is_right_new_record = False
                                    break
                                if tbl["cells"][new_key].get("movable") is False:
                                    is_right_new_record = False
                                    break
                                if not range_[0] <= new_key[0] <= range_[1]:
                                    is_right_new_record = False
                                    break
                                else:
                                    continue_expand = True
                                if cls.judge_new_key_in_records(new_key, records):
                                    new_record.append(key)
                                else:
                                    new_record.append(new_key)
                            else:
                                new_record.append(key)
                        if is_right_new_record:
                            if new_record not in records:
                                records.append(new_record)
                            else:
                                break
                            i += 1
                        elif continue_expand:
                            i += 1
                        else:
                            break
                    else:
                        break
            elif tbl_type == utils.head_col_merge_tbl:
                i = 1
                is_right_new_record = True
                while True:
                    new_record = []
                    for key in known_record:
                        if tbl["cells"][key].get("movable"):
                            new_key = (key[0] + i, key[1])
                            if new_key not in tbl["cells"]:
                                is_right_new_record = False
                                break
                            if tbl["cells"][new_key].get("movable") is False:
                                is_right_new_record = False
                                break
                            if cls.judge_new_key_in_records(new_key, records):
                                new_record.append(key)
                            else:
                                new_record.append(new_key)
                        else:
                            new_record.append(key)
                    if is_right_new_record:
                        if new_record not in records:
                            records.append(new_record)
                        else:
                            break
                        i += 1
                    else:
                        break
            elif tbl_type == utils.no_merge_tbl:
                i = 1
                is_right_new_record = True
                while True:
                    new_record = []
                    for key in known_record:
                        if tbl["cells"][key].get("movable"):
                            new_key = (key[0] + i, key[1])
                            if new_key not in tbl["cells"]:
                                is_right_new_record = False
                                break
                            if tbl["cells"][new_key].get("movable") is False:
                                is_right_new_record = False
                                break
                            if cls.judge_new_key_in_records(new_key, records):
                                new_record.append(key)
                            else:
                                new_record.append(new_key)
                        else:
                            new_record.append(key)
                    if is_right_new_record:
                        if new_record not in records:
                            records.append(new_record)
                        else:
                            break
                        i += 1
                    else:
                        break
            elif tbl_type == utils.col_0_row_merge_and_head_col_merge_tbl:
                i = 1
                is_right_new_record = True
                range_ = []
                while True:
                    continue_expand = False
                    new_record = []
                    for key in known_record:
                        range_ = utils.find_int_in_range(key[0], y_ranges)
                        if range_:
                            break
                    if range_:
                        for key in known_record:
                            if tbl["cells"][key].get("movable"):
                                new_key = (key[0] + i, key[1])
                                if new_key not in tbl["cells"]:
                                    is_right_new_record = False
                                    break
                                if tbl["cells"][new_key].get("movable") is False:
                                    is_right_new_record = False
                                    break
                                if not range_[0] <= new_key[0] <= range_[1]:
                                    is_right_new_record = False
                                    break
                                else:
                                    continue_expand = True
                                if cls.judge_new_key_in_records(new_key, records):
                                    new_record.append(key)
                                else:
                                    new_record.append(new_key)
                            else:
                                new_record.append(key)
                        if is_right_new_record:
                            if new_record not in records:
                                records.append(new_record)
                            else:
                                break
                            i += 1
                        elif continue_expand:
                            i += 1
                        else:
                            break
                    else:
                        break
            elif tbl_type == utils.most_wide_col_merge_tbl:
                if [1, 0] in x_label_keys:
                    first_label_key = (1, 0)
                elif [0, 0] in x_label_keys:
                    first_label_key = (0, 0)
                else:
                    return records
                for label_key in x_label_keys:
                    records_ = []
                    if tuple(label_key) == first_label_key:
                        i = label_key[0] - first_label_key[0] + 1
                    else:
                        i = label_key[0] - first_label_key[0]
                    is_right_new_record = True
                    while True:
                        new_record = []
                        for key in known_record:
                            if tbl["cells"][key].get("movable"):
                                new_key = (key[0] + i, key[1])
                                if new_key not in tbl["cells"]:
                                    is_right_new_record = False
                                    break
                                if tbl["cells"][new_key].get("movable") is False:
                                    is_right_new_record = False
                                    break
                                if cls.judge_new_key_in_records(new_key, records_):
                                    new_record.append(key)
                                else:
                                    new_record.append(new_key)
                            elif (key[0] + i, 0) == tuple(label_key):
                                new_record.append((key[0] + i, 0))
                            else:
                                new_record.append(key)
                        if is_right_new_record:
                            if new_record not in records:
                                records.append(new_record)
                                records_.append(new_record)
                            else:
                                break
                            i += 1
                        else:
                            break
            elif tbl_type == utils.unknown_type_tbl:
                i = 1
                is_right_new_record = True
                while True:
                    new_record = []
                    for key in known_record:
                        if tbl["cells"][key].get("movable"):
                            new_key = (key[0] + i, key[1])
                            if new_key not in tbl["cells"]:
                                if new_key[0] < row_num and judge_key_in_row_merge(tbl, new_key):
                                    new_key = key
                                else:
                                    is_right_new_record = False
                                    break
                            if tbl["cells"][new_key].get("movable") is False:
                                is_right_new_record = False
                                break
                            if cls.judge_new_key_in_records(new_key, records):
                                new_record.append(key)
                            else:
                                new_record.append(new_key)
                        else:
                            new_record.append(key)
                    if is_right_new_record:
                        if new_record not in records:
                            records.append(new_record)
                        else:
                            break
                        i += 1
                    else:
                        break
            else:
                pass
        elif record_type == utils.horizontal_record:
            i = 1
            is_right_new_record = True
            while True:
                new_record = []
                for key in known_record:
                    if tbl["cells"][key].get("movable"):
                        new_key = (key[0] + i, key[1])
                        if new_key not in tbl["cells"]:
                            if new_key[0] < row_num and judge_key_in_row_merge(tbl, new_key):
                                new_key = key
                            else:
                                is_right_new_record = False
                                break
                        if tbl["cells"][new_key].get("movable") is False:
                            is_right_new_record = False
                            break
                        if cls.judge_new_key_in_records(new_key, records):
                            new_record.append(key)
                        else:
                            new_record.append(new_key)
                    else:
                        new_record.append(key)

                if is_right_new_record:
                    if new_record not in records:
                        records.append(new_record)
                    else:
                        break
                    i += 1
                else:
                    break
        elif record_type == utils.semi_horzontal_record:
            if tbl_type == utils.col_0_row_merge_tbl:
                i = 1
                is_right_new_record = True
                range_ = []
                while True:
                    continue_expand = False
                    new_record = []
                    for key in known_record:
                        range_ = utils.find_int_in_range(key[0], y_ranges)
                        if range_:
                            break
                    if range_:
                        for key in known_record:
                            if tbl["cells"][key].get("movable"):
                                new_key = (key[0] + i, key[1])
                                if new_key not in tbl["cells"]:
                                    is_right_new_record = False
                                    break
                                if tbl["cells"][new_key].get("movable") is False:
                                    is_right_new_record = False
                                    break
                                if not range_[0] <= new_key[0] <= range_[1]:
                                    is_right_new_record = False
                                    break
                                else:
                                    continue_expand = True
                                if cls.judge_new_key_in_records(new_key, records):
                                    new_record.append(key)
                                else:
                                    new_record.append(new_key)
                            else:
                                new_record.append(key)
                        if is_right_new_record:
                            if new_record not in records:
                                records.append(new_record)
                            else:
                                break
                            i += 1
                        elif continue_expand:
                            i += 1
                        else:
                            break
                    else:
                        break
            elif tbl_type == utils.col_0_row_merge_and_head_col_merge_tbl:
                i = 1
                is_right_new_record = True
                range_ = []
                while True:
                    continue_expand = False
                    new_record = []
                    for key in known_record:
                        range_ = utils.find_int_in_range(key[0], y_ranges)
                        if range_:
                            break
                    if range_:
                        for key in known_record:
                            if tbl["cells"][key].get("movable"):
                                new_key = (key[0] + i, key[1])
                                if new_key not in tbl["cells"]:
                                    is_right_new_record = False
                                    break
                                if tbl["cells"][new_key].get("movable") is False:
                                    is_right_new_record = False
                                    break
                                if not range_[0] <= new_key[0] <= range_[1]:
                                    is_right_new_record = False
                                    break
                                else:
                                    continue_expand = True
                                if cls.judge_new_key_in_records(new_key, records):
                                    new_record.append(key)
                                else:
                                    new_record.append(new_key)
                            else:
                                new_record.append(key)
                        if is_right_new_record:
                            if new_record not in records:
                                records.append(new_record)
                            else:
                                break
                            i += 1
                        elif continue_expand:
                            i += 1
                        else:
                            break
                    else:
                        break
            else:
                i = 1
                is_right_new_record = True
                while True:
                    new_record = []
                    for key in known_record:
                        if tbl["cells"][key].get("movable"):
                            new_key = (key[0] + i, key[1])
                            if new_key not in tbl["cells"]:
                                if new_key[0] < row_num and judge_key_in_row_merge(tbl, new_key):
                                    new_key = get_row_merge_cell_idx(tbl, new_key)
                                else:
                                    is_right_new_record = False
                                    break
                            if tbl["cells"][new_key].get("movable") is False:
                                is_right_new_record = False
                                break
                            # if cls.judge_new_key_in_records(new_key, records):
                            #     new_record.append(key)
                            # else:
                            #     new_record.append(new_key)
                            new_record.append(new_key)
                        else:
                            new_record.append(key)
                    if is_right_new_record:
                        if new_record not in records:
                            records.append(new_record)
                        else:
                            break
                        i += 1
                    else:
                        break
        elif record_type == utils.vertical_record:
            i = 1
            is_right_new_record = True
            while True:
                new_record = []
                for key in known_record:
                    if tbl["cells"][key].get("movable"):
                        new_key = (key[0], key[1] + i)
                        if new_key not in tbl["cells"]:
                            is_right_new_record = False
                            break
                        if tbl["cells"][new_key].get("movable") is False:
                            is_right_new_record = False
                            break
                        if cls.judge_new_key_in_records(new_key, records):
                            new_record.append(key)
                        else:
                            new_record.append(new_key)
                    else:
                        new_record.append(key)

                if is_right_new_record:
                    if new_record not in records:
                        records.append(new_record)
                    else:
                        break

                    i += 1
                else:
                    break
        elif record_type == utils.tall_and_short_record:
            left_key = min(known_record, key=lambda x: x[1])
            right_key = max(known_record, key=lambda x: x[1])
            x = right_key[1]
            start_y = tbl["cells"][right_key]["range"][3]
            end_y = tbl["cells"][left_key]["range"][3]
            for y in range(start_y, end_y):
                if (y, x) in tbl["cells"]:
                    records.append([left_key, (y, x)])
        else:
            pass
        return records

    @classmethod
    def get_intersection(cls, list1, list2):
        intersection = []
        for _ in list1:
            if _ in list2:
                intersection.append(_)
        return intersection

    @classmethod
    def add_expandable_group_to_result(cls, tbl, records, tbl_type):
        tbl2 = deepcopy(tbl)
        groups = GetExpandableGroup.get_expandable_group(tbl2)
        if not groups:
            return records
        new_records = deepcopy(records)
        if len(groups) > 2:
            groups = groups[:2]

        # 第一个group
        group = groups[0]
        # 寻找已知记录的member index
        known_member_idx = -1
        known_member = []
        for member_idx, member in enumerate(group):
            keys_in_member = cls.get_intersection(member, records[0])
            if keys_in_member:
                known_member_idx = member_idx
                known_member = member
                break
        if known_member_idx == -1:
            return records
        known_label_key = group[known_member_idx][0]
        for member_idx, member in enumerate(group):
            if member_idx == known_member_idx:
                continue
            x_diff = member[0][1] - known_label_key[1]
            y_diff = member[0][0] - known_label_key[0]
            first_member_records_num = len(records)
            for record_idx, record in enumerate(records):
                keys_in_member = cls.get_intersection(known_member, record)
                is_right_new_record = True
                new_record = []
                for key in record:
                    if key in keys_in_member:
                        new_key = (key[0] + y_diff, key[1] + x_diff)
                        if new_key not in tbl["cells"] or new_key not in member:
                            is_right_new_record = False
                            break
                        new_record.append(new_key)
                    else:
                        new_record.append(key)
                if is_right_new_record and new_record not in new_records:
                    new_records.append(new_record)
                if record_idx == first_member_records_num - 1 and tbl_type == utils.col_0_row_merge_tbl:
                    col_0_cell_keys = [_ for _ in new_record if _[1] == 0]
                    if not col_0_cell_keys:
                        continue
                    col_0_cell_key = col_0_cell_keys[0]
                    new_record_except_col_0_cell = [_ for _ in new_record if _[1] != 0]
                    if not col_0_cell_key or not new_record_except_col_0_cell:
                        continue
                    cur_bottom = max(new_record_except_col_0_cell, key=lambda x: x[0])[0]
                    bottom = tbl["cells"][col_0_cell_key]["range"][3] - 1
                    top = col_0_cell_key[0]
                    if top <= cur_bottom < bottom:
                        start_record = deepcopy(new_record)
                        for y in range(cur_bottom + 1, bottom + 1):
                            new_record = []
                            is_right_new_record = True
                            for key in start_record:
                                if key[1] == 0:
                                    new_record.append(key)
                                else:
                                    new_key = (y, key[1])
                                    if new_key not in tbl["cells"]:
                                        is_right_new_record = False
                                        break
                                    new_record.append(new_key)
                            if is_right_new_record and new_record not in new_records:
                                new_records.append(new_record)

        # 第二个group
        if len(groups) == 2:
            records = deepcopy(new_records)
            group = groups[1]
            # 寻找已知记录的member index
            known_member_idx = -1
            known_member = []
            for member_idx, member in enumerate(group):
                keys_in_member = cls.get_intersection(member, records[0])
                if keys_in_member:
                    known_member_idx = member_idx
                    known_member = member
                    break
            if known_member_idx == -1:
                return records
            known_label_key = group[known_member_idx][0]
            for member_idx, member in enumerate(group):
                if member_idx == known_member_idx:
                    continue
                x_diff = member[0][1] - known_label_key[1]
                y_diff = member[0][0] - known_label_key[0]
                first_member_records_num = len(records)
                for record_idx, record in enumerate(records):
                    keys_in_member = cls.get_intersection(known_member, record)
                    is_right_new_record = True
                    new_record = []
                    for key in record:
                        if key in keys_in_member:
                            new_key = (key[0] + y_diff, key[1] + x_diff)
                            if new_key not in tbl["cells"] or new_key not in member:
                                is_right_new_record = False
                                break
                            new_record.append(new_key)
                        else:
                            new_record.append(key)
                    if is_right_new_record and new_record not in new_records:
                        new_records.append(new_record)
                    if record_idx == first_member_records_num - 1 and tbl_type == utils.col_0_row_merge_tbl:
                        col_0_cell_keys = [_ for _ in new_record if _[1] == 0]
                        if not col_0_cell_keys:
                            continue
                        col_0_cell_key = col_0_cell_keys[0]
                        new_record_except_col_0_cell = [_ for _ in new_record if _[1] != 0]
                        if not col_0_cell_key or not new_record_except_col_0_cell:
                            continue
                        cur_bottom = max(new_record_except_col_0_cell, key=lambda x: x[0])[0]
                        bottom = tbl["cells"][col_0_cell_key]["range"][3] - 1
                        top = col_0_cell_key[0]
                        if top <= cur_bottom < bottom:
                            start_record = deepcopy(new_record)
                            for y in range(cur_bottom + 1, bottom + 1):
                                new_record = []
                                is_right_new_record = True
                                for key in start_record:
                                    if key[1] == 0:
                                        new_record.append(key)
                                    else:
                                        new_key = (y, key[1])
                                        if new_key not in tbl["cells"]:
                                            is_right_new_record = False
                                            break
                                        new_record.append(new_key)
                                if is_right_new_record and new_record not in new_records:
                                    new_records.append(new_record)

        return new_records

    @classmethod
    def judge_result(cls, records, record_len):
        for record in records:
            if len(record) != record_len:
                print("ERROR!")


def debug_table():
    json_fpath = "/data/huyp/tmp/1.json"
    with open(json_fpath, "r") as json_file:
        tbl = json.load(json_file)[0]
    result = SsePredictorWithRecord.predict_with_one_record(tbl, [(2, 0), (2, 2), (2, 3), (2, 4)])
    print(result)


if __name__ == "__main__":
    # if not debug_mode:
    #     # run_known_answers()
    #     # run()
    #     run_pdfinsight_tables()
    #     # pass
    # else:
    #     # run_known_answers_specific_table(28, '1546')
    #     run_specific_pdfinsight_tables('48518', '149', 0, [(3,0),(0,1),(1,1),(2,1),(3,1)])
    debug_table()
