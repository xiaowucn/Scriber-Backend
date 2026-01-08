"""表格/段落周围内容提取"""

from remarkable.plugins.predict.models.partial_text_v3 import PartialTextV3


class NearbyElt(PartialTextV3):
    model_intro = {
        "doc": "表格周围相邻内容/段落文字提取（如年份、单位）",
        "name": "相邻内容",
        "hide": True,
    }

    @classmethod
    def model_template(cls):
        template = {
            "regs": [],
            "type": "",
            "pos": (),
        }
        default_model_template = cls.default_model_template()
        default_model_template.update(template)
        return default_model_template

    def predict(self, elements, **kwargs):
        elements = (
            kwargs.get("candidates", [])
            if self.same_elt_with_parent
            else kwargs.get("candidates", []) + (elements or [])
        )
        enlarged_elts = []
        blocks = self.config.get("blocks", [])
        if not blocks:
            blocks.append(
                {
                    "pos": self.config.get("pos", (0, -3)),
                }
            )
        for block in blocks:
            start, end = block["pos"]
            for elt in elements:
                enlarge = self.pdfinsight.find_elements_near_by(
                    elt["index"],
                    amount=abs(start - end),
                    step=1 if start < end else -1,
                    include=self.config.get("include_self", True),
                    aim_types=block.get("aim_types", ["PARAGRAPH"]),
                    neg_patterns=self.config.get("neg_patterns"),
                )
                enlarged_elts.extend(enlarge)
        answers = super(NearbyElt, self).predict(enlarged_elts, **kwargs)
        return self.pick_nearest_answer(answers, **kwargs)

    def pick_nearest_answer(self, answers, **kwargs):
        """取距离上级answer最近的(非表格)元素块作为答案"""
        if not answers or len(answers) == 1:
            return answers
        answer = {}
        parent_elt_idxs = [
            item.data[0].elt["index"]
            for item in kwargs.get("parent_answer", {}).values()
            if item.data and item.data[0].elt_typ == "table"
        ]
        if not parent_elt_idxs:
            return answers

        ref_elt_idx = max(parent_elt_idxs)
        if max(self.config.get("pos") or (0, -3)) <= 0:
            ref_elt_idx = min(parent_elt_idxs)
        for col in self.columns:
            values = [item[col] for item in answers if item[col].data and item[col].data[0].elt_idx]
            answer[col] = sorted(values, key=lambda x: abs(x.data[0].elt_idx - ref_elt_idx))[0]
        return [answer]
