import logging
import re
from collections import namedtuple
from copy import deepcopy

from remarkable.pw_models.model import NewMold

DocElement = namedtuple("DocElement", ["att", "texts"])


def filter_str(txt, drop_cn=False, fix_figures=True):
    """
    删除文本中的特殊字符, 将多余空格替换为一个
    默认不删除中文及全角标点
    """
    if not isinstance(txt, str):
        raise TypeError
    if drop_cn:
        punctuation = (
            "＂＃＄％＆＇（）＊＋，－／：；＜＝＞"
            "＠［＼］＾＿｀｛｜｝～｟｠｢｣､\u3000、"
            "〃〈〉《》「」『』【】〔〕〖〗〘〙〚〛〜〝〞"
            "〟〰〾〿–—‘’‛“”„‟…‧﹏﹑﹔·！？｡。"
        )
        characters = (
            "〇\u4e00-\u9fff"
            "\u3400-\u4dbf"
            "\uf900-\ufaff"
            "\U00020000-\U0002a6df"
            "\U0002a700-\U0002b73f"
            "\U0002b740-\U0002b81f"
            "\U0002f800-\U0002fa1f"
        )
        txt = re.sub("[{}]+".format(punctuation + characters), " ", txt)
    # 替换多个\r\n\t等为空格
    txt = re.sub(r"[\r\t\n]+", " ", txt)
    # 将多余空格替换为一个
    txt = re.sub(r"\s+", " ", txt)
    # 删掉/左右的空格
    txt = re.sub(r"\s?(/)\s?", r"\1", txt)
    # 删除数字间的空格
    txt = re.sub(r"(\d)\s?(\d)\s?", r"\1\2", txt)
    if fix_figures:  # 删除数字间的千分位逗号
        txt = re.sub(r"(\d)\s*?[,，]\s*?(\d{3}(?!\d))", r"\1\2", txt.strip())
    # 删掉'n i l'间的空格(忽略大小写)
    txt = re.sub(r"(?i)(n)\s?(i)\s?(l)", r"\1\2\3", txt)
    # 将连续重复三次以上的字母替换成一个, 如 aaasssskkk -> ask
    txt = re.sub(r"([a-zA-Z])\1{2,}", r"\1", txt)
    return txt


def elt_text_list(elt, need_type=False, drop_cn=False, fix_figures=True):
    if elt["class"] == "TABLE":
        text_l = [cell["text"] for cell in elt["cells"].values() if not cell.get("dummy")]
    else:
        text_l = [
            elt.get("text", ""),
        ]

    ret = [filter_str(text, drop_cn=drop_cn, fix_figures=fix_figures) for text in text_l]
    return ret if not need_type else [DocElement(elt["class"], i) for i in ret]


class Schema:
    def __init__(self, mold):
        if isinstance(mold, NewMold):
            mold = mold.data
        assert isinstance(mold, dict), "mold error"
        self.schemas = mold["schemas"]
        self.root_name = self.schemas[0]["name"]
        self.schema_dict = {schema["name"]: schema for schema in self.schemas}
        self.enum_dict = {s["label"]: s for s in mold.get("schema_types")}
        self.enum_types = list(self.enum_dict.keys())
        self.basic_types = ["文本", "数字", "日期"] + self.enum_types

    @classmethod
    def join_path(cls, parent, name):
        path = deepcopy(parent)
        path.append(name)
        return path

    def iter_schema_attr(self):
        def iter_schema(path, schema, field_name):
            path = Schema.join_path(path, field_name)
            for name in schema["orders"]:
                # 按顺序取schema
                item = schema["schema"][name]
                if item["type"] in self.basic_types:
                    yield Schema.join_path(path, name)
                elif item["type"] in self.schema_dict:
                    yield from iter_schema(path, self.schema_dict[item["type"]], name)
                else:
                    logging.error("unknown type %s", item["type"])

        yield from iter_schema([], self.schemas[0], self.root_name)

    @property
    def root_rules_map(self):
        """
        key: 根节点名
        value: 子节点集合(如果没有子节点, 则与根节点一致)
        """
        ret = {}
        for row in self.iter_schema_attr():
            if len(row) == 2:
                if row[-1] in ret:
                    raise Exception(row[-1])
                ret[row[-1]] = [row[-1]]
            elif len(row) == 3:
                if row[1] in ret:
                    ret[row[1]].append(row[2])
                else:
                    ret[row[1]] = [row[2]]
            else:
                pass
        return ret

    @property
    def rule_names_map(self):
        """
        key: 子节点名
        value: 同级的所有子节点集合
        """
        ret = {}
        for rule, items in self.root_rules_map.items():
            for index, item in enumerate(items):
                if re.search(r"\(?A\d+", item):
                    ret[item] = items
                elif item.startswith("("):
                    ret["({}.{})".format(rule, (index + 1) // 2)] = items
                else:
                    ret["{}.{}".format(rule, (index + 2) // 2)] = items
        return ret

    @property
    def rule_root_map(self):
        """
        key: 规则名, 如A1, (A1)等
        value: 根节点规则名
            举例: 若key=A28.1, 对应根节点名应为A28
        """
        ret = {}
        for rule, items in self.root_rules_map.items():
            for index, item in enumerate(items):
                if re.search(r"\(?A\d+", item):
                    ret[item] = rule
                elif item.startswith("("):
                    ret["({}.{})".format(rule, (index + 1) // 2)] = rule
                else:
                    ret["{}.{}".format(rule, (index + 2) // 2)] = rule
        return ret

    @property
    def name_rule_map(self):
        """从schema中按rule_name: rule导出rules"""
        ret = {}
        for rule, items in self.root_rules_map.items():
            for index, item in enumerate(items):
                if re.search(r"\(?A\d+", item):
                    ret[item] = item
                elif item.startswith("("):
                    ret[item] = "({}.{})".format(rule, (index + 1) // 2)
                else:
                    ret[item] = "{}.{}".format(rule, (index + 2) // 2)
        return ret

    @property
    def rule_name_map(self):
        """从schema中按rule: rule_name导出rules"""
        return {v: k for k, v in self.name_rule_map.items()}

    def rule2crude_key(self, rule):
        """
        转换rule为crude_answer中的key
            1. 一级属性, 不做修改
            2. 二级属性, 与对应一级属性拼接
        :param rule: 'A10.1'
        :return: 'A10-Name of every subsidiary'
        """
        root = self.rule_root_map[rule]
        _type = self.schema_dict[self.root_name]["schema"][root]["type"]
        if _type not in self.enum_types:
            return "{}-{}".format(root, self.rule_name_map[rule])
        else:
            return rule

    def crude_key2rule(self, crude_key):
        return self.name_rule_map[crude_key.split("-")[-1]]

    def enum_value(self, label, index=0):
        """按名称取对应index的schema枚举值"""
        enums = self.enum_dict[label]["values"]
        if index >= len(enums):
            index = -1
        return enums[index]["name"]

    def rule_enum_value(self, rule, index=0):
        """按rule取对应index的schema枚举值"""
        if index is None:
            return None
        root = self.rule_root_map[rule]
        _type = self.schema_dict[self.root_name]["schema"][root]["type"]
        if _type not in self.enum_types:
            _type = self.schema_dict[_type]["schema"][self.rule_name_map[rule]]["type"]
        return self.enum_value(_type, index)

    def get_rules_by_type(self, rule_type=None):
        def has_bracket(value):
            if rule_type == "compliance":
                return "(" in value
            elif rule_type == "disclose":
                return "(" not in value
            else:
                return True

        return [rule for rule, _ in self.name_rule_map.items() if has_bracket(rule)]

    def label_enum_value(self, label, index=0):
        """按label取对应index的枚举值"""
        return self.rule_enum_value(self.name_rule_map[label], index)
