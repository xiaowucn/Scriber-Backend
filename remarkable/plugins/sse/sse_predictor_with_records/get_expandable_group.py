import re

from remarkable.plugins.sse.sse_predictor_with_records.utils import get_row_and_col_num

DEBUG_MODE = 0


# date_pattern = '(20\d\d年度?(1?\d月份?)?((1|2|3)?\d日)?)'
# right_patterns = [re.compile(r'^'+date_pattern+'[或/]?'+date_pattern+'?$'),
#                   re.compile(r'^\d+.?[^0-9.,]*$'),
#                   re.compile(r'^.*(公司)|(企业)$'),
#                   re.compile(r'^20\d\d.\d\d?.\d\d?$')]
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


def preprocess_text(text):
    return text.replace(" ", "").replace("\n", "")


def get_x_label_keys(tbl):
    date_keys = []
    for cell_key in tbl["cells"]:
        if cell_key[0] == 0:
            text = preprocess_text(tbl["cells"][cell_key]["text"])
            if is_date(text):
                date_keys.append(cell_key)
    date_keys.sort(key=lambda x: x[0])
    if len(date_keys) >= 2:
        return date_keys
    else:
        return []


class GetExpandableGroup:
    @classmethod
    def get_expandable_group(cls, tbl):
        # tbl = cls.convert_cell_key_format(tbl)
        tbl = cls.normalize_text(tbl)
        # tbl = cls.add_range_for_cells(tbl)
        groups = []
        horizontal_group = cls.get_horizontal_group(tbl)
        vertical_group = cls.get_vertical_group(tbl)
        if not horizontal_group and not vertical_group:
            return []
            # groups = cls.get_no_merge_groups(tbl)
            # return groups
        if horizontal_group:
            groups.append(horizontal_group)
        if vertical_group:
            groups.append(vertical_group)
        return groups

    @classmethod
    def normalize_text(cls, tbl):
        for cell_key in tbl["cells"]:
            cell = tbl["cells"][cell_key]
            if "text" in cell:
                tbl["cells"][cell_key]["text"] = cls.del_linefeed_for_text(cell["text"])
        return tbl

    @classmethod
    def convert_cell_key_format(cls, tbl):
        cells = {}
        for cell_key in tbl["cells"]:
            new_cell_key = cls.convert_cell_key(cell_key)
            cells[new_cell_key] = tbl["cells"][cell_key]
        tbl["cells"] = cells
        return tbl

    @classmethod
    def get_expandable_group_ranges(cls, tbl):
        groups = cls.get_expandable_group(tbl)
        group_ranges = []
        for i, group in enumerate(groups):
            group_ranges.append([])
            for member in group:
                member_min_x = min(member, key=lambda x: x[1])[1]
                member_max_x_key = max(member, key=lambda x: x[1])
                member_max_x = tbl["cells"][member_max_x_key]["range"][2]
                member_min_y = min(member, key=lambda x: x[0])[0]
                member_max_y_key = max(member, key=lambda x: x[0])
                member_max_y = tbl["cells"][member_max_y_key]["range"][3]
                group_ranges[i].append([member_min_x, member_min_y, member_max_x, member_max_y])
            group_ranges[i].sort(key=lambda x: x[0] + x[1])
        return group_ranges

    @classmethod
    def get_merge_range(cls, merge_group):
        min_y = min(merge_group, key=lambda x: x[0])[0]
        max_y = max(merge_group, key=lambda x: x[0])[0]
        min_x = min(merge_group, key=lambda x: x[1])[1]
        max_x = max(merge_group, key=lambda x: x[1])[1]
        return [min_x, min_y, max_x, max_y]

    @classmethod
    def get_head_merges(cls, merges):
        head_merge_ranges = []
        for merge_group in merges:
            min_x, min_y, max_x, max_y = cls.get_merge_range(merge_group)
            if min_y == max_y == 0:
                head_merge_ranges.append([min_x, min_y, max_x, max_y])
        return head_merge_ranges

    @classmethod
    def get_no_merge_tbl_head_date_group(cls, tbl, head_date_keys):
        row_num, _ = get_row_and_col_num(tbl)
        head_date_keys_x = [_[1] for _ in head_date_keys]
        valid_ys = []
        for y in range(row_num):
            is_valid_y = True
            for x in head_date_keys_x:
                if (y, x) not in tbl["cells"]:
                    is_valid_y = False
                    break
            if is_valid_y:
                valid_ys.append(y)
        group = []
        for idx, x in enumerate(head_date_keys_x):
            group.append([])
            for y in valid_ys:
                group[idx].append((y, x))
        return group

    @classmethod
    def get_horizontal_group(cls, tbl):
        head_date_keys = get_x_label_keys(tbl)
        if not head_date_keys:
            return []
        merges = tbl["merged"]
        first_row_merges = cls.get_head_merges(merges)
        if not first_row_merges:
            return cls.get_no_merge_tbl_head_date_group(tbl, head_date_keys)
            # return []
        if len(first_row_merges) == 1:
            row_1_merges = []
            left, right = first_row_merges[0][0], first_row_merges[0][2]
            if (1, left) in tbl["cells"]:
                row_1_merge_width = tbl["cells"][(1, left)]["range"][2] - tbl["cells"][(1, left)]["range"][0]
            else:
                return []
            if row_1_merge_width == 1:
                return []
            for x in range(left, right + 1):
                if (1, x) in tbl["cells"]:
                    cur_cell_l, cur_cell_r = tbl["cells"][(1, x)]["range"][0], tbl["cells"][(1, x)]["range"][2]
                    if cur_cell_r - cur_cell_l != row_1_merge_width:
                        return []
                    else:
                        row_1_merges.append([cur_cell_l, 1, cur_cell_r - 1, 1])

            first_merge_range = row_1_merges[0]
            merge_width = first_merge_range[2] - first_merge_range[0]
            # 如果各个merge的宽度不相等，则不认为它们是groups
            for merge in row_1_merges:
                if merge[2] - merge[0] != merge_width:
                    return []

            # get first group
            first_group = []
            for cell_key in tbl["cells"]:
                # cell_key = cls.convert_cell_key(cell_key)
                cell_r = tbl["cells"][cell_key]["range"][2]
                if first_merge_range[0] <= cell_key[1] and cell_r <= first_merge_range[2] + 1 and cell_key[0] >= 1:
                    first_group.append(cell_key)
            group = [first_group]

            # get the rest groups
            for merge in row_1_merges[1:]:
                group_distance = merge[0] - first_merge_range[0]
                # print(merge, first_merge_range, group_distance)
                cur_group = []
                # print(first_group)
                for group_key in first_group:
                    cur_group_key = (group_key[0], group_key[1] + group_distance)
                    if cur_group_key not in tbl["cells"]:
                        return []
                    cur_group.append(cur_group_key)
                group.append(cur_group)
        else:
            first_merge_range = first_row_merges[0]
            merge_width = first_merge_range[2] - first_merge_range[0]

            # 如果各个merge的宽度不相等，则不认为它们是groups
            for merge in first_row_merges:
                if merge[2] - merge[0] != merge_width:
                    return []

            # get first group
            first_group = []
            for cell_key in tbl["cells"]:
                # cell_key = cls.convert_cell_key(cell_key)
                cell_r = tbl["cells"][cell_key]["range"][2]
                if first_merge_range[0] <= cell_key[1] and cell_r <= first_merge_range[2] + 1:
                    first_group.append(cell_key)
            group = [first_group]

            # get the rest groups
            for merge in first_row_merges[1:]:
                group_distance = merge[0] - first_merge_range[0]
                cur_group = []
                for group_key in first_group:
                    cur_group_key = (group_key[0], group_key[1] + group_distance)
                    if cur_group_key not in tbl["cells"]:
                        return []
                    cur_group.append(cur_group_key)
                group.append(cur_group)
        return group

    @classmethod
    def get_first_col_merges(cls, merges, tbl):
        first_col_merges = []
        for merge_group in merges:
            min_x, min_y, max_x, max_y = cls.get_merge_range(merge_group)
            if min_x == max_x == 0:
                if (min_y, min_x) in tbl["cells"]:
                    text = tbl["cells"][(min_y, min_x)]["text"]
                    if is_date(text) or not text:
                        first_col_merges.append([min_x, min_y, max_x, max_y])
        return first_col_merges

    @classmethod
    def get_vertical_group(cls, tbl):
        merges = tbl["merged"]
        first_col_merges = cls.get_first_col_merges(merges, tbl)
        if DEBUG_MODE:
            print("first col merge: ", first_col_merges)
        if len(first_col_merges) < 2:
            return []
        first_merge_range = first_col_merges[0]
        merge_height = first_merge_range[3] - first_merge_range[1]

        # 如果各个merge的高度不相等，则不认为它们是groups
        for merge in first_col_merges:
            if merge[3] - merge[1] != merge_height and merge_height < 2:
                return []
            # 用来限制分支个数差异
            # if merge_height >= 4 and (merge_height - 2 > merge[3] - merge[1] or merge[3] - merge[1] > merge_height + 2):
            #     return []

        # get first group
        first_group = []
        for cell_key in tbl["cells"]:
            # cell_key = cls.convert_cell_key(cell_key)
            cell_b = tbl["cells"][cell_key]["range"][3]
            if first_merge_range[1] <= cell_key[0] and cell_b <= first_merge_range[3] + 1:
                first_group.append(cell_key)
        group = [first_group]
        if DEBUG_MODE:
            print("first group:", first_group)
        # get the rest groups
        for merge in first_col_merges[1:]:
            group_distance = merge[1] - first_merge_range[1]
            cur_group = []
            for group_key in first_group:
                cur_group_key = (group_key[0] + group_distance, group_key[1])
                if cur_group_key not in tbl["cells"] or cur_group_key[0] > merge[3]:
                    continue
                cur_group.append(cur_group_key)
            group.append(cur_group)
        return group

    # @classmethod
    # def get_no_merge_horizontal_group(cls, tbl):
    #     group_head_ranges = cls.get_no_merge_group_head_ranges(tbl)
    #     if DEBUG_MODE:
    #         print('group head ranges: ', group_head_ranges)
    #     if len(group_head_ranges) < 2:
    #         return []
    #     first_head_range = group_head_ranges[0]
    #
    #     first_group = []
    #     for cell_key in tbl['cells']:
    #         # cell_key = cls.convert_cell_key(cell_key)
    #         cell_r = tbl['cells'][cell_key]['range'][2]
    #         if first_head_range[0] <= cell_key[1] and cell_r <= first_head_range[2]:
    #             first_group.append(cell_key)
    #     group = [first_group]
    #
    #     # get the rest groups
    #     for head_range in group_head_ranges[1:]:
    #         group_distance = head_range[0] - first_head_range[0]
    #         cur_group = []
    #         for group_key in first_group:
    #             cur_group_key = (group_key[0], group_key[1]+group_distance)
    #             if cur_group_key not in tbl['cells']:
    #                 return []
    #             cur_group.append(cur_group_key)
    #         group.append(cur_group)
    #
    #     return group

    # @classmethod
    # def get_no_merge_vertical_group(cls, tbl):
    #     group_first_col_ranges = cls.get_no_merge_first_col_group_ranges(tbl)
    #     if len(group_first_col_ranges) < 2:
    #         return []
    #     first_range = group_first_col_ranges[0]
    #
    #     first_group = []
    #     for cell_key in tbl['cells']:
    #         # cell_key = cls.convert_cell_key(cell_key)
    #         cell_b = tbl['cells'][cell_key]['range'][3]
    #         if first_range[1] <= cell_key[0] and cell_b <= first_range[3]:
    #             first_group.append(cell_key)
    #     group = [first_group]
    #
    #     # get the rest groups
    #     for first_col_range in group_first_col_ranges[1:]:
    #         group_distance = first_col_range[1] - first_range[1]
    #         cur_group = []
    #         for group_key in first_group:
    #             cur_group_key = (group_key[0]+group_distance, group_key[1])
    #             if cur_group_key not in tbl['cells']:
    #                 return []
    #             cur_group.append(cur_group_key)
    #         group.append(cur_group)
    #
    #     return group

    @classmethod
    def del_linefeed_for_text(cls, text):
        new_text = ""
        for char in text:
            if char not in [" ", "\n"]:
                new_text += char
        return new_text

    # @classmethod
    # def is_right_text(cls, texts):
    #     choose_patterns = []
    #     for pattern in right_patterns:
    #         # if DEBUG_MODE:
    #         #     print(cls.del_linefeed_for_text(texts[0].strip()))
    #         if pattern.match(texts[0]):
    #             choose_patterns.append(pattern)
    #     if not choose_patterns:
    #         return False
    #     texts_num = len(texts)
    #     for pattern in choose_patterns:
    #         for i, text in enumerate(texts):
    #             # if DEBUG_MODE:
    #             #     print(cls.del_linefeed_for_text(text.strip()))
    #             if not pattern.match(text):
    #                 break
    #             elif i == texts_num - 1:
    #                 return True
    #             else:
    #                 pass
    #     return False

    @classmethod
    def convert_cell_key(cls, cell_key):
        if isinstance(cell_key, str):
            y, x = cell_key.split("_")
            cell_key = (int(y), int(x))
        return cell_key

    # @classmethod
    # def get_no_merge_group_head_ranges(cls, tbl):
    #     merges = cls.flat_merges(tbl['merged'])
    #     head_texts = {}
    #     head_char_num = {}
    #     head_char2key = {}
    #     for cell_key in tbl['cells']:
    #         cell = tbl['cells'][cell_key]
    #         # cell_key = cls.convert_cell_key(cell_key)
    #         if cell_key[0] != 0 or cell_key in merges:
    #             continue
    #         if 'text' in cell:
    #             head_texts[cell_key] = cell['text']
    #     for cell_key in head_texts:
    #         text = head_texts[cell_key]
    #         for char in text:
    #             if cls.is_digit(char):
    #                 if -1 not in head_char_num:
    #                     head_char_num[-1] = 1
    #                     head_char2key[-1] = [cell_key]
    #                 else:
    #                     if cell_key not in head_char2key[-1]:
    #                         head_char_num[-1] += 1
    #                         head_char2key[-1].append(cell_key)
    #             else:
    #                 if char in head_char_num:
    #                     if cell_key not in head_char2key[char]:
    #                         head_char_num[char] += 1
    #                         head_char2key[char].append(cell_key)
    #                 else:
    #                     head_char_num[char] = 1
    #                     head_char2key[char] = [cell_key]
    #
    #     if not head_char_num:
    #         return []
    #
    #     char_with_max_appear_num = max(head_char_num, key=lambda x: head_char_num[x])
    #     max_appear_num = head_char_num[char_with_max_appear_num]
    #     if max_appear_num == 1:
    #         return []
    #     # if DEBUG_MODE:
    #     #     print(json.dumps(head_char_num, ensure_ascii=False))
    #     #     print(json.dumps(head_char2key[char_with_max_appear_num], ensure_ascii=False))
    #     heads = head_char2key[char_with_max_appear_num]
    #     # 获取所有即将成为head的cells的text，并用正则表达式判断是否满足条件
    #     texts = []
    #     for key in heads:
    #         texts.append(tbl['cells'][key]['text'])
    #     # if DEBUG_MODE:
    #     #     print(cls.is_right_text(texts))
    #     # for text in texts:
    #     #     print(text, cls.is_right_text([text]))
    #     if not cls.is_right_text(texts):
    #         return []
    #     for i, _ in enumerate(heads):
    #         heads[i] = [_[1], _[0], _[1]+1, _[0]+1]
    #     return heads

    @classmethod
    def is_digit(cls, char):
        return char in "0123456789"

    # @classmethod
    # def get_no_merge_first_col_group_ranges(cls, tbl):
    #     merges = cls.flat_merges(tbl['merged'])
    #     first_col_texts = {}
    #     first_col_char_num = {}
    #     first_col_char2key = {}
    #     # first_col_keys = []
    #     for cell_key in tbl['cells']:
    #         cell = tbl['cells'][cell_key]
    #         # cell_key = cls.convert_cell_key(cell_key)
    #         if cell_key[1] != 0 or cell_key in merges:
    #             continue
    #         if 'text' in cell:
    #             first_col_texts[cell_key] = cell['text']
    #     for cell_key in first_col_texts:
    #         text = first_col_texts[cell_key]
    #         for char in text:
    #             if cls.is_digit(char):
    #                 if -1 not in first_col_char_num:
    #                     first_col_char_num[-1] = 1
    #                     # if cell_key not in first_col_keys:
    #                     first_col_char2key[-1] = [cell_key]
    #                     #     first_col_keys.append(cell_key)
    #                 else:
    #                     if cell_key not in first_col_char2key[-1]:
    #                         first_col_char_num[-1] += 1
    #                         first_col_char2key[-1].append(cell_key)
    #                     #     first_col_keys.append(cell_key)
    #             else:
    #                 if char in first_col_char_num:
    #                     if cell_key not in first_col_char2key[char]:
    #                         first_col_char_num[char] += 1
    #                         first_col_char2key[char].append(cell_key)
    #                     #     first_col_keys.append(cell_key)
    #                 else:
    #                     # if cell_key not in first_col_keys:
    #                     first_col_char_num[char] = 1
    #                     first_col_char2key[char] = [cell_key]
    #                     #     first_col_keys.append(cell_key)
    #
    #     if not first_col_char_num:
    #         return []
    #     char_with_max_appear_num = max(first_col_char_num, key=lambda x: first_col_char_num[x])
    #     max_appear_num = first_col_char_num[char_with_max_appear_num]
    #     if max_appear_num == 1:
    #         return []
    #     first_col_ranges = first_col_char2key[char_with_max_appear_num]
    #
    #     # 获取所有即将成为head的cells的text，并用正则表达式判断是否满足条件
    #     texts = []
    #     for key in first_col_ranges:
    #         texts.append(tbl['cells'][key]['text'])
    #
    #     if not cls.is_right_text(texts):
    #         return []
    #     for i, _ in enumerate(first_col_ranges):
    #         first_col_ranges[i] = [_[1], _[0], _[1]+1, _[0]+1]
    #
    #     return first_col_ranges

    # @classmethod
    # def get_no_merge_groups(cls, tbl):
    #     groups = []
    #     horizontal_group = cls.get_no_merge_horizontal_group(tbl)
    #     vertical_group = cls.get_no_merge_vertical_group(tbl)
    #     if horizontal_group:
    #         groups.append(horizontal_group)
    #     if vertical_group:
    #         groups.append(vertical_group)
    #
    #     return groups

    @classmethod
    def add_expandable_group_to_table(cls, tbl):
        groups = cls.get_expandable_group(tbl)
        if groups:
            tbl["groups"] = groups
        return tbl
