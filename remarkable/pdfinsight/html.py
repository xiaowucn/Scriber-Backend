class Table2Html:
    @classmethod
    def table2html(cls, table, blue=None, red=None):
        # rows = table['grid']['rows']
        # cols = table['grid']['columns']
        # merged = table.get('merged', [])
        cells = table.get("cells", [])
        idxes = [key.split("_") for key in cells.keys()]
        row_len = max([int(r[0]) for r in idxes])
        col_len = max([int(r[1]) for r in idxes])
        # merged_merged = merged_util.merge_merged_cell(merged)
        table_html = "<table border='1' style='border-collapse:collapse'>"
        # row_len, col_len = len(rows), len(cols)
        for row in range(row_len + 1):
            table_html += "<tr>\n"
            for col in range(col_len + 1):
                cell = cls.get_cell(cells, row, col)
                rowspan, colspan = cls.calculate_span(cell, row, col)
                if rowspan < 1 or colspan < 1:
                    continue
                text = hightlight_text(cell["chars"], blue, red)
                table_html += "<td align='{}' rowspan='{}' colspan='{}'>{}</td>\n".format(
                    cell["styles"]["align"], rowspan, colspan, text
                )
            table_html += "</tr>\n"
        table_html += "</table>\n"
        return table_html

    @classmethod
    def calculate_span(cls, cell, row, col):
        return (
            cell["bottom"] - cell["top"] if row == cell["top"] else 0,
            cell["right"] - cell["left"] if col == cell["left"] else 0,
        )

    @classmethod
    def get_cell(cls, cells, row, col):
        return cells["{}_{}".format(row, col)]

    @classmethod
    def list2ranges(cls, lst, bound):
        ranges = []
        for i in lst:
            if ranges:
                if ranges[-1][1] == i - 1:
                    ranges[-1][1] = i
                else:
                    ranges.append([i, i])
            else:
                ranges.append([i, i])

        all_ranges = []
        cur = 0
        for x1, x2 in ranges:
            if cur < x1:
                all_ranges.extend(zip(range(cur, x1), range(cur, x1)))
            all_ranges.append((x1, x2 + 1))
            cur = x2 + 1
        if cur < bound:
            all_ranges.extend(zip(range(cur, bound), range(cur, bound)))
        return all_ranges


def para_to_html(ele, blue=None, red=None):
    return "<p>%s</p>" % (hightlight_text(ele["chars"], blue, red))


def tbl_to_html(ele, blue=None, red=None):
    return Table2Html.table2html(ele, blue, red)


def hightlight_text(chars, blue=None, red=None):
    html_chars = []
    for char in chars:
        catch = False
        for page, highlight_box in blue or []:
            if page == char["page"] and box_in_box(char["box"], highlight_box):
                html_chars.append('<span class="blue">%s</span>' % char["text"])
                catch = True
                break
        if catch:
            continue

        for page, highlight_box in red or []:
            if page == char["page"] and box_in_box(char["box"], highlight_box):
                html_chars.append('<span class="red">%s</span>' % char["text"])
                catch = True
                break
        if catch:
            continue

        html_chars.append(char["text"])

    return "".join(html_chars)


def box_in_box(*outlines):
    overlap_length = min(outlines[0][2], outlines[1][2]) - max(outlines[0][0], outlines[1][0])
    inter_x = overlap_length if overlap_length > 0 else 0

    overlap_length = min(outlines[0][3], outlines[1][3]) - max(outlines[0][1], outlines[1][1])
    inter_y = overlap_length if overlap_length > 0 else 0

    area0 = (outlines[0][3] - outlines[0][1]) * (outlines[0][2] - outlines[0][0])
    area1 = (outlines[1][3] - outlines[1][1]) * (outlines[1][2] - outlines[1][0])

    if min(area0, area1) == 0:
        return False

    overlap_percent = inter_y * inter_x / min(area0, area1)

    return overlap_percent > 0.618
