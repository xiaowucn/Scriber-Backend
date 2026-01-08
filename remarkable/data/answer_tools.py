# coding: utf-8
import json
from collections import namedtuple

KeyPathItem = namedtuple("KeyPathItem", ["name", "index"])


def load_key_path(path_str):
    key_path = []
    if not path_str:
        return key_path

    for item in json.loads(path_str):
        parts = item.split(":")
        name = parts[0]
        index = int(parts[1]) if len(parts) > 1 else 0
        key_path.append(KeyPathItem(name, index))
    return key_path


if __name__ == "__main__":
    print(load_key_path(""))
    print(load_key_path('["导出测试:0","内容:1","第一段:2"]'))
    print(load_key_path('["导出测试","内容","第一段:2"]'))
