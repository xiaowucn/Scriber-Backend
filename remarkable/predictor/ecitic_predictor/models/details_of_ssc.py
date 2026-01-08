from itertools import chain

from remarkable.predictor.models.table_row import TableRow


class DetailsOfSSC(TableRow):
    def prepare_table(self, element):
        # 1. 必须约束表格列数
        if self.calc_table_size(element) < len(self.columns) - 1:
            return None
        table = super(DetailsOfSSC, self).prepare_table(element)

        # 2. `股东名称`必然在表格上方，可能会被识别成一个小表格，需要按组装成段落，方便后续处理
        for elt in table.elements_above:
            if elt["class"] == "TABLE":
                chars = chain(
                    *(
                        cell["chars"]
                        for cell in sorted(elt["cells"].values(), key=lambda x: (x["row"], x["col"]))
                        if not cell.get("dummy")
                    )
                )
                elt["class"] = "PARAGRAPH"
                elt["chars"] = list(chars)
                elt["text"] = "".join(c["text"] for c in elt["chars"])
                elt.pop("cells")
        return table
