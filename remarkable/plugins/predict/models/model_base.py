# pylint: skip-file
import logging
import pickle
import re
from copy import deepcopy

from remarkable.common.pattern import RE_TYPE
from remarkable.common.schema import Schema
from remarkable.common.util import clean_txt, index_in_space_string
from remarkable.pdfinsight.reader import PdfinsightReader
from remarkable.predictor.predict import CharResult, ResultOfPredictor

DIMENSION_PATTERNS = {
    "date": re.compile(r"\d{4}\s*(?:年[度初中末]?|\.|-|\/)(\d{1,2}(?:月份?|\.|-|\/)?(?:\d{1,2}[日号]?)?)?")
}

SPECIAL_ATTR_PATTERNS = {
    "date": [
        r"(?P<dst>[\d一二三四五六七八九〇○零]{4}(?:年[度初中末]?|\.|-|/)([\d一二三四五六七八九十零〇○]{1,2}(?:月份?|\.|-|/)?(?:[\d一二三四五六七八九十零〇○]{1,2}[日号]?)?)?)"
    ],
    "number": [r"[\d一二三四五六七八九〇零○]+"],
    "<金额单位>": [r"(?P<dst>\w?元)"],
    "<数量单位>": [
        r"单位[:：](.*?)(?P<dst>[百千万亿]?股)",
        r"数.*?\w?(?P<dst>股)",
        r"[(（](?P<dst>人)[)）]",
        r"(?P<dst>人)数",
    ],
    "<百分比单位>": [r"(?P<dst>%)"],
    "<每股收益单位>": [r"(?P<dst>元/股)", r"每[^(（]*?(?P<dst>元)"],
    "币种": [r"(?P<dst>人民币|美元)"],
}

NOTICE_BASE_PREDICTORS = [
    {
        "path": ["公司全称"],
        "model": "fixed_position",
        "positions": list(range(-10, 0))[::-1],
        "regs": [r"(?P<dst>.*公司)"],
        "anchor_regs": [SPECIAL_ATTR_PATTERNS["date"][0]],
    },
    {
        "path": ["公司简称"],
        "model": "fixed_position",
        "positions": list(range(0, 3)),
        "regs": [r"(?<=简称[:：])(?P<dst>.*?)(?=\s?(公告|证券|股票|编[号码]))", r"简称[:：](?P<dst>.*)"],
    },
    {
        "path": ["公司代码"],
        "model": "fixed_position",
        "positions": list(range(0, 3)),
        "regs": [r"(?<=代码[:：])(?P<dst>\d{6})", r"代码[:：](?P<dst>\d{6})"],
    },
    {
        "path": ["公告编号"],
        "model": "fixed_position",
        "positions": list(range(0, 3)),
        "regs": [r"(公告)?编号[:：](?P<dst>临?[\d\-\s－]*)"],
    },
    {
        "path": ["公告时间"],
        "model": "fixed_position",
        "positions": list(range(-10, 0))[::-1],
        "regs": SPECIAL_ATTR_PATTERNS["date"],
    },
]


class PredictModelBase:
    model_intro = {"doc": "", "name": ""}

    def __init__(self, mold, config, **kwargs):
        self.mold = mold
        self.schema = Schema(mold.data)
        self.config = config
        self.model = {}
        self.columns = kwargs.get("columns", [self.config["path"][-1]])
        self.sub_predictors = kwargs.get("sub_predictors", {})
        self.dump_path = kwargs.get("dump_path")
        self.pdfinsight = kwargs.get("pdfinsight")
        self.leaf = kwargs.get("leaf")
        self.same_elt_with_parent = self.config.get("same_elt_with_parent", False)
        self.base_on_crude_element = True
        self.base_on_fixed_position = False
        self.need_training = True
        self.run_sub_predictors = True
        self.file = kwargs.get("file")

    def train(self, dataset, **kwargs):
        if self.need_training:
            raise NotImplementedError()

    @classmethod
    def default_model_template(cls):
        template = {"path": ["<path>"]}
        return template

    @classmethod
    def model_template(cls):
        raise NotImplementedError()

    @classmethod
    def get_lower_case_name(cls):
        reg = re.compile(r"[A-Z][a-z]+")
        words = reg.findall(cls.__name__)
        words = [word.lower() for word in words]
        return "_".join(words)

    def print_model(self):
        print("\n==== model data of %s ====" % self.config["path"])
        for key, item in self.model.items():
            print("\n# %s:" % key)
            print(item)

    def run_predict(self, crude_answers, **kwargs):
        if self.base_on_crude_element:
            results = self.predict_with_elements(crude_answers, **kwargs)
        else:
            results = self.predict_without_elements(**kwargs)
        return results

    def predict_without_elements(self, **kwargs):
        results = []
        answers = self.predict(None, **kwargs)
        if answers:
            results.append((None, answers))
        return results

    def predict_with_elements(self, crude_answers, **kwargs):
        results = []
        candidate_elts = []
        location_threshold = self.config.get("location_threshold") or {}
        if self.same_elt_with_parent:
            for item in kwargs.get("candidates") or []:
                candidate_elts.append(item)
        else:
            candidates = self._get_element_candidates(
                crude_answers,
                self.config["path"],
                priors=self.config.get("element_candidate_priors", []),
                limit=self.config.get("element_candidate_count", 10),
                min_score=self.config.get("element_min_score", 0.05),
                ranges=kwargs.get("ranges"),
            )
            for item in candidates:
                if item.get("element_index"):
                    etype, ele = self.pdfinsight.find_element_by_index(item["element_index"])
                    if not ele or item["score"] < location_threshold.get(etype.lower(), 0.1):
                        continue
                    ele["score"] = item["score"]
                    candidate_elts.append(ele)
        if self.config.get("just_table") and hasattr(self, "predict_just_table"):
            for elt in candidate_elts:
                if elt["class"] != "TABLE":
                    continue
                answers = self.predict_just_table([elt])
                if answers:
                    results.append((elt, answers))
        else:
            for elt in candidate_elts:
                answers = self.predict([elt], score=elt.get("score", 0), **kwargs)
                if answers:
                    results.append((elt, answers))
        return results

    def _get_element_candidates(self, crude_answers, path, priors=None, limit=10, min_score=0.05, ranges=None):
        priors = priors or []
        _candidates = []
        key = "-".join(path)
        if key in crude_answers:
            _candidates = crude_answers[key]
        else:
            # 按 column 顺序来更好一些
            for name, elements in crude_answers.items():
                if name.startswith(key):
                    if any(name.endswith(prior) for prior in priors):
                        elements = deepcopy(elements)
                        for ele in elements:
                            ele["ordering"] = ele["score"] + 0.5
                    _candidates.extend(elements)
        _candidates = [c for c in _candidates if c["score"] > min_score]
        if ranges:

            def contains_in_ranges(_ranges, idx):
                for _range in _ranges:
                    if isinstance(_range, int):
                        if idx == _range:
                            return True
                    elif isinstance(_range, (tuple, list)):
                        if _range[0] <= idx < _range[1]:
                            return True
                return False

            _candidates = [c for c in _candidates if contains_in_ranges(ranges, c["element_index"])]
        _distinct_set = set()
        candi_types = self.config.get("candi_types", [])
        for item in sorted(_candidates, key=lambda c: c.get("ordering", c["score"]), reverse=True):
            if item["element_index"] in _distinct_set:
                continue
            if candi_types and item.get("element_type") not in candi_types:
                continue
            _distinct_set.add(item["element_index"])
            yield item
            if limit and len(_distinct_set) >= limit:
                return

    def predict(self, elements, **kwargs):
        return NotImplementedError()

    def dump(self):
        if not self.dump_path:
            raise Exception("not set dump_path for model: %s" % self.config)
        with open(self.dump_path, "wb") as model_fp:
            pickle.dump(self.model, model_fp)
        for sub_predictor in self.sub_predictors.values():
            sub_predictor.dump()

    # def load(self):
    #     if not self.dump_path:
    #         logging.error("not set dump_path for model: %s", self.config)
    #     elif not os.path.exists(self.dump_path):
    #         logging.warning("can't find model features: %s", self.dump_path)
    #     else:
    #         with open(self.dump_path, "rb") as model_fp:
    #             self.model = pickle.load(model_fp)
    #     for sub in self.sub_predictors.values():
    #         sub.load()

    @staticmethod
    def select_elements(elements, box):
        selected = []
        for ele in elements:
            if not ele["page"] == box["page"]:
                continue
            if PdfinsightReader.overlap_percent(ele["outline"], box["box"], base="box") > 0.2:
                selected.append(ele)
            elif PdfinsightReader.overlap_percent(ele["outline"], box["box"], base="element") > 0.2:
                selected.append(ele)
        return selected

    @staticmethod
    def same_text(cell, text):
        cell_text = cell if isinstance(cell, str) else cell["text"]
        if text.startswith("D_") and text[2:] in DIMENSION_PATTERNS:
            return DIMENSION_PATTERNS[text[2:]].match(cell_text)
        return clean_txt(cell_text) == clean_txt(text)

    @staticmethod
    def same_box(cell, box):
        if cell.get("fake"):
            return False
        if cell["page"] != box["page"]:
            return False
        box_outline = (box["box"]["box_left"], box["box"]["box_top"], box["box"]["box_right"], box["box"]["box_bottom"])
        if PdfinsightReader.overlap_percent(cell["box"], box_outline, base="box") < 0.5:
            return False
        return True

    @staticmethod
    def same_cell(cell, val, mode):
        if mode == "text":
            return PredictModelBase.same_text(cell, val)
        elif mode == "box":
            return PredictModelBase.same_box(cell, val)
        else:
            raise Exception("undefined cell compare mode: %s" % mode)

    @staticmethod
    def text_feature_key(texts):
        revise_texts = []
        for text in texts:
            text = clean_txt(text)
            for _type, _pattern in DIMENSION_PATTERNS.items():
                if _pattern.match(text):
                    revise_texts.append("D_%s" % _type)
                    break
            else:
                revise_texts.append(text)
        return "|".join(sorted(revise_texts))

    # def vaild_answer(self, item):
    #     """检查是否是有效的答案条目
    #     默认实现是填充了 1/4 以上的字段
    #     也可定义某些项目必填, 或者排除 `合计` 等条目
    #     """
    #     vaild_config = self.config.get("valid", {})
    #     if isinstance(item, dict):
    #         acceptable_fullfill_percent = vaild_config.get("fullfill", 0)
    #         if acceptable_fullfill_percent > 0 and not self.config.get("just_table"):
    #             _fullfill_percent = len([col for col in self.columns if item.get(col)]) / len(self.columns)
    #             if _fullfill_percent < acceptable_fullfill_percent:
    #                 return False

    #         need_columns = vaild_config.get("needs", [])
    #         if any(col for col in need_columns if not item.get("col")):
    #             return False
    #     return True

    @staticmethod
    def judge_enum_value(answers, enums):
        """
        根据内容判断枚举值
        TODO: 多项判断
        :param answers: [ResultOfPredictor, ...]
        :param enums: 枚举值列表, ['是', '否']
        :return: str, 比如'是'
        """
        if enums == ["是", "否"]:
            pattern = re.compile(r"不|没有|未|非|无")
            for ans in filter(None, answers):
                text = getattr(ans.data[0], "elt", {"text": ""}).get("text", "")
                if pattern.search(text):
                    ret = enums[1]  # 否
                    break
            else:
                ret = enums[0]  # 是
        else:
            ret = enums[0]
        return ret

    def get_enum_values(self, parent_name, child_name):
        """
        获取子属性枚举值
        :param parent_name: str, 父节点
        :param child_name: str, 子节点
        :return: ['是', '否'] 非枚举值返回空list
        """
        values = []
        try:
            root_name = self.schema.schemas[0]["name"]
            _type = self.schema.schema_dict[root_name]["schema"][parent_name]["type"]
            if _type not in self.schema.enum_dict.keys():
                _type = self.schema.schema_dict[_type]["schema"][child_name]["type"]
            values = self.schema.enum_dict[_type]["values"]
        except KeyError:
            logging.debug("%s - %s 非枚举值", parent_name, child_name)
        return [value["name"] for value in values] if values else values

    def find_special_attr(self, col, elt, **kwargs):
        """
        从当前或上一个element中获取特定属性信息
        :param col: 币种, <金额单位>, <每股收益单位>, <百分比单位>, <**单位>其中之一
        :param elt:
        :return: ResultOfPredictor object or None
        """

        def is_same_tbl(tbl_1, tbl_2):
            if tbl_1["type"] == tbl_2["type"] == "TABLE":
                if all(cell == tbl_2["cells"].get(cell_idx) for cell_idx, cell in tbl_1["cells"]):
                    return True
            return False

        def _filter_chars(item):
            patterns = []
            # 正则优先级: 特殊属性 > 配置文件 > 词频统计
            if col in SPECIAL_ATTR_PATTERNS:
                patterns.extend(SPECIAL_ATTR_PATTERNS[col])
            if col == "年度":
                patterns.extend(SPECIAL_ATTR_PATTERNS["date"])
            patterns.extend(self.config.get("regs", []))

            for reg_p in kwargs.get("patterns", []):
                if reg_p is None:
                    print("error!")
                if reg_p.startswith("D_"):
                    patterns.extend(SPECIAL_ATTR_PATTERNS.get(reg_p.split("_")[-1]))
                else:
                    patterns.append(reg_p)

            for pattern in patterns:
                if isinstance(pattern, str):
                    pattern = re.compile(r"{}".format(pattern))

                if isinstance(pattern, RE_TYPE):
                    match = pattern.search(clean_txt(item["text"]))
                    if match:
                        try:
                            m_s, m_e = match.span("dst")
                        except IndexError:
                            # 正则未指定dst参数, 直接返回当前element所有chars
                            return item["chars"]
                        sp_start, sp_end = index_in_space_string(clean_txt(item["text"]), (m_s, m_e))
                        # 去掉空的文本框, 可能是space/\n\r\t其中一种
                        chars = [i for i in item["chars"] if not re.search(r"^\s+$", i["text"])]
                        return chars[sp_start:sp_end]
            return None

        def _find_special_attr(idx):
            chars = None
            ele_typ, _elt = self.pdfinsight.find_element_by_index(idx)
            if ele_typ == "PARAGRAPH":
                chars = _filter_chars(_elt)
            elif ele_typ == "TABLE":
                base_cells = []
                patterns = kwargs.get("unit_priority", {}).get(col, [])
                for pattern in patterns:
                    for cell in _elt["cells"].values():
                        if re.search(pattern, cell["text"]):
                            base_cells.append(cell)
                for cell in base_cells:
                    chars = _filter_chars(cell)
                    if chars:
                        return CharResult(chars, elt_idx=idx, elt=elt)
                for _idx, cell in _elt["cells"].items():
                    chars = _filter_chars(cell)
                    if chars:
                        return CharResult(chars, elt_idx=idx, elt=elt)
            else:
                logging.debug("不支持的元素类型: %s", ele_typ)
            return CharResult(chars, elt_idx=idx, elt=elt) if chars else None

        ret = []
        if col in SPECIAL_ATTR_PATTERNS:
            start, end = 0, -3
        else:
            start, end = self.config.get("pos", (0, 1))

        # 跳过页眉/页脚/跨页表格
        extended = 0
        for idx in range(start, end, 1 if start < end else -1):
            _idx = elt["index"] + idx
            ele_typ, _elt = self.pdfinsight.find_element_by_index(_idx)
            if not _elt:
                continue
            if ele_typ in ["PAGE_HEADER", "PAGE_FOOTER"]:
                extended += 1
            elif ele_typ == "TABLE" and is_same_tbl(_elt, elt):
                extended += 1
        idx_list = sorted([elt["index"] + idx for idx in range(start, end, 1 if start < end else -1)], reverse=True)
        idx_list.extend(list(range(idx_list[-1] - 1, idx_list[-1] - 1 - extended, -1)))

        for _idx in idx_list:
            unit = _find_special_attr(_idx if _idx > 0 else 0)
            if unit:
                ret.append(unit)
                break
        else:
            logging.debug("未找到: %s", col)
        return ResultOfPredictor(ret) if ret else None


class EmptyPredictor(PredictModelBase):
    model_intro = {}

    def __init__(self, *args, **kwargs):
        super(EmptyPredictor, self).__init__(*args, **kwargs)
        self.base_on_crude_element = False
        self.need_training = False

    @classmethod
    def model_template(cls):
        template = {}
        default_model_template = cls.default_model_template()
        default_model_template.update(template)
        return default_model_template

    def predict(self, elements, **kwargs):
        answer = {}
        for col in self.columns:
            answer[col] = []
        return [answer]


class TableRecordTuple:
    def __init__(self, header_cells, val_cell, dimension_cell=None):
        self.header = header_cells
        self.val = val_cell
        self.dimension = dimension_cell


class TableRecordItem(list):
    def __init__(self, tuples=None):
        super(TableRecordItem, self).__init__(tuples or [])  # list of tuples

    def append_tuple(self, header_cells, val_cell, dimension_cell=None):
        _item = TableRecordTuple(header_cells, val_cell, dimension_cell)
        return self.append(_item)


class TableRecords(dict):
    def __init__(self, items=None):
        super(TableRecords, self).__init__(items or {})  # key: TableRecordItem

    def append_tuple(self, key, header_cells, val_cell, dimension_cell=None):
        _item = TableRecordTuple(header_cells, val_cell, dimension_cell)
        if dimension_cell:
            key = "%s_%s" % (key, clean_txt(dimension_cell["text"]))
        self.setdefault(key, TableRecordItem()).append_tuple(header_cells, val_cell, dimension_cell)
