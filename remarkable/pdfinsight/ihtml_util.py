class IHtmlUtil:
    @classmethod
    def convert_table_to_html(cls, table):
        row_len, col_len = table.row_count, table.column_count
        cells = table.cells
        para_html = cls.convert_paragraphs_to_html(table.related_paras)
        table_html = "<table border='1' style='border-collapse:collapse'>"
        for row in range(row_len):
            tr_html = ""
            cell_count = 0
            if table.is_header_row(row):
                tr_html += "<thead><tr>\n"
            elif row == 0:
                tr_html += "<thead><tr>\n"
            else:
                tr_html += "<tr>\n"
            for col in range(col_len):
                cell = cells.get("{}_{}".format(row, col))
                rowspan, colspan = cls.calculate_span(cell, row, col)
                if rowspan < 1 or colspan < 1:
                    continue
                cell_count += 1
                align = cell.get("styles", {}).get("align", "center")
                if align == "unknown":
                    align = "center"
                tr_html += "<td align='{}' rowspan='{}' colspan='{}'>{}</td>\n".format(
                    align, rowspan, colspan, cell["text"]
                )
            if table.is_header_row(row):
                tr_html += "</tr></thead>\n"
            elif row == 0:
                tr_html += "</tr></thead>\n"
            else:
                tr_html += "</tr>\n"
            if cell_count > 0:
                table_html += tr_html
        table_html = table_html.replace("</thead>\n<thead>", "")
        table_html += "</table>\n"
        return para_html + table_html

    @classmethod
    def calculate_span(cls, cell, row, col):
        if not cell:
            return 0, 0
        if cell["left"] == col and cell["top"] == row:
            return cell["bottom"] - cell["top"], cell["right"] - cell["left"]
        else:
            return 0, 0

    @classmethod
    def convert_paragraphs_to_html(cls, paragraphs):
        return "".join([("<p>%s</p>" % para["text"]) for para in paragraphs if para])
