import json
from copy import deepcopy
from dataclasses import dataclass
from functools import reduce

from remarkable.answer.common import gen_key_md5, is_empty_answer, is_empty_answer_item
from remarkable.common.schema import Schema
from remarkable.common.util import compact_dumps
from remarkable.config import get_config
from remarkable.schema.answer import AnswerGroup, UserAnswer


@dataclass
class AnswerUtil:
    @staticmethod
    def _modify_answer_item(answer: UserAnswer):
        for key in "userAnswer", "rule_result", "custom_field":
            for item in answer.data.get(key, {}).get("items", []):
                if not item.get("key"):
                    # rule_result中可能存在key为空的情况
                    continue
                item["key"] = compact_dumps(json.loads(item["key"]))  # 去掉逗号后空格
                item["marker"] = item.get("marker") or {
                    "id": answer.uid,
                    "name": answer.name,
                    "others": [],
                }  # 添加标注用户信息

    @staticmethod
    def _level1_answer_groups(answer, answer_type="userAnswer"):
        groups = {}
        for item in answer.get(answer_type, {}).get("items", []):
            if not item.get("key"):
                # rule_result中可能存在key为空的情况
                continue
            keypath = [p.split(":")[0] for p in json.loads(item["key"])]
            group = groups.setdefault(keypath[1], AnswerGroup())
            group.items.append(item)
            group.manual = group.manual or item.get("manual", False)
        return groups

    @staticmethod
    def answer_items(answer, key="userAnswer"):
        return answer.get(key, {}).get("items", [])

    @classmethod
    def _merge_custom_answer(cls, answers: list[UserAnswer], base_item: dict | None):
        is_empty = is_empty_answer(base_item, check_key="custom_field")
        if is_empty:
            *others, base = answers
        else:
            base = UserAnswer._make([0, "", base_item])
            others = answers
        custom_answer = {"version": "2.2", "items": []}
        if not others:
            custom_answer["items"].extend(cls.answer_items(base.data, "custom_field"))
            return custom_answer

        base_answer = {gen_key_md5(item): item for item in cls.answer_items(base.data, "custom_field")}
        for income in others[::-1]:  # 新字段靠后
            income_answer = {gen_key_md5(item): item for item in cls.answer_items(income.data, "custom_field")}
            for key, item in income_answer.items():
                marker = deepcopy(item.setdefault("marker", {"id": income.uid, "name": income.name, "others": []}))
                if key in base_answer:
                    base_item = base_answer[key]
                    # 更新标注人员信息
                    if "marker" in base_item and base_item["marker"]["id"] != income.uid:
                        base_item["marker"].update(
                            {
                                "id": income.uid,
                                "name": income.name,
                                # 按顺序取标注人员集合(不包括最后提交答案的用户), 并把最近的标注用户顺序提前
                                "others": reduce(
                                    lambda x, y: x + [y] if y not in x + [income.name] else x,
                                    [[base_item["marker"]["name"]]] + base_item["marker"]["others"],
                                ),
                            }
                        )
                    item["marker"] = base_item.setdefault("marker", {"id": base.uid, "name": base.name, "others": []})
                else:
                    item["marker"] = marker
                    base_answer[gen_key_md5(item)] = item
                custom_answer["items"].append(item)

        return custom_answer

    @classmethod
    def merge_answers(cls, answers: list[UserAnswer], *, schema_data: dict, base_answer=None):
        if not answers:
            return None
        merged_answer = deepcopy(answers[-1].data)
        if str(merged_answer.get("userAnswer", {}).get("version", "0")) < "2.0":
            raise RuntimeError("can't merge answer version below than 2.0")
        schema = Schema(schema_data)
        item_groups = {}
        rule_groups = {}
        for answer in answers:
            if not answer.data:
                continue
            cls._modify_answer_item(answer)
            cls._merge_to(item_groups, cls._level1_answer_groups(answer.data), schema)

            if answer.data.get("rule_result"):
                cls._merge_to(rule_groups, cls._level1_answer_groups(answer.data, "rule_result"), schema)

        merged_answer["custom_field"] = cls._merge_custom_answer(answers, base_answer)

        items_list = []
        for group in item_groups.values():
            items_list.extend(group.items)
        merged_answer["userAnswer"]["items"] = items_list

        # 合并合规答案
        rule_items_list = []
        for group in rule_groups.values():
            rule_items_list.extend(group.items)
        if rule_items_list:
            merged_answer["rule_result"]["items"] = rule_items_list

        return merged_answer

    @staticmethod
    def _merge_to(groups, new_groups, schema):
        for name in new_groups:
            try:
                valid_attrs = set(schema.find_attr_type([name])["orders"])
            except Exception:  # noqa
                valid_attrs = set()
            current_attrs = set()
            for item in new_groups[name].items:
                if not get_config("web.merge_empty_item") and is_empty_answer_item(item):
                    continue
                key_path = json.loads(item["key"])
                if len(key_path) < 3:  # TODO: schema属性层级过多可能会有问题
                    continue
                current_attrs.add(key_path[2].split(":")[0])
            if current_attrs.issubset(valid_attrs) and (
                name not in groups or not groups[name].manual or new_groups[name].manual
            ):
                if not get_config("web.merge_empty_item"):  # 空答案丢掉
                    new_groups[name].items = [i for i in new_groups[name].items if not is_empty_answer_item(i)]
                if name in groups and groups[name].items:
                    # 保留参与标注用户信息
                    marker = deepcopy(groups[name].items[0]["marker"])
                    marker["others"].append(marker["name"])
                    for _item in new_groups[name].items:
                        _others = [i for i in marker["others"] if i != marker["name"]]
                        _item["marker"]["others"].extend(_others)
                groups[name] = new_groups[name]
