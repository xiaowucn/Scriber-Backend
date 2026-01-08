# coding: utf-8
# ==========================================================================
#   Copyright (C) 2017 All rights reserved.
#
#   filename : format_describe.py
#   author   : chendian / okcd00@qq.com
#   date     : 2017-09-05
#   desc     : API for showing data formats for new types
#              Updating.
# ==========================================================================

from __future__ import print_function


class Describe:
    def __init__(self, cls_name):
        self.obj = cls_name
        self.desc = self.generate_function(cls_name)

    def __call__(self, *args, **kwargs):
        return self.desc(args[0])

    def generate_function(self, cls_name):
        functions = {
            "LabelMark": self.lm_describe,
        }
        return functions[cls_name]

    def lm_describe(self, type):
        if type == "dict":
            print("sentence dict as a list with dicts below:")
            print(
                """
        {
            words: [
                "发行人", "固定资产", "逐年", "增加", "主要", "原因", "是", "发行人", "自", "2015年", "起",
                "开展", "经营", "租赁", "业务", "，", "新增", "较", "多", "租赁", "用", "固定资产", "。"
            ],
            sentence: "发行人固定资产逐年增加主要原因是发行人自2015年起开展经营租赁业务，新增较多租赁用固定资产。",
            sid: "39130370",
            times: {
                1: {
                    position: 20,
                    tag: "$TIME1$",
                    word_index: 9,
                    value: "2015年",
                    checksum: "024052b3f87542334275656890a33e59"
                },
            },
            values: {},
            attributes: {
                1: {
                    position: 3,
                    tag: "$ATTR_MONEY$",
                    word_index: 1,
                    value: "固定资产",
                    checksum: "21eec20cc7523723adb2e1ae1b3a4021"
                },
                2: {
                    position: 42,
                    tag: "$ATTR_MONEY$",
                    word_index: 21,
                    value: "固定资产",
                    checksum: "8119655199802050955d628944ac25a3"
                }
            },
        },
                """
            )
        elif type == "json":
            print("FrontEnd's JSON data as a list with dicts below:")
            print(
                """
        [Temporary @ Sep05]

        "M2":{                    # "𝑀_𝑖"的下标可以按需定义，保持升序增长即可
            "Name":  "M2",        # 名称字段是为后续额外的功能做准备
            "C":     (0, 12),     # Cause 原因，由两个下标组成的pair，为闭区间
            "R":     (16, 29),    # Result 结果，由两个下标组成的pair，为闭区间
            "Link":  [13,14,15],  # Link 连接词，连接词的下标可不连续，考虑到 "所致"
            "Range": (0, 29),     # 该因果关系涉及的words下标范围，即CLR的左右界
            "Related": {"R":"M1"} # 该因果关系中包含的子级因果关系，没有则为空
        }

                """
            )
        elif type == "mid":
            print("mid product as a list with dicts below:")
            print(
                """
        {
            words: [
                "发行人", "固定资产", "逐年", "增加", "主要", "原因", "是", "发行人", "自", "2015年", "起",
                "开展", "经营", "租赁", "业务", "，", "新增", "较", "多", "租赁", "用", "固定资产", "。"
            ],
            sentence: "发行人固定资产逐年增加主要原因是发行人自2015年起开展经营租赁业务，新增较多租赁用固定资产。",
            position: [
                0,  3,  7,  9,  11, 13, 15, 16, 19, 20, 25, 26,
                28, 30, 32, 34, 35, 37, 38, 39, 41, 42, 46
            ],
            mark_id: 6,
            sid: "39130370",
            voc_index: [
                28, 4, 118, 35, 31, 76, 39, 28, 320, 0, 248, 472,
                54, 240, 38, 20, 230, 30, 199, 240, 637, 4, 22
            ],
            link_word: [
                "主要原因是"
            ],
            link_pos: [
                [11]
            ],
        },
                """
            )
        else:
            print("Invalid input, types should in {dict, mid, json}")


if __name__ == "__main__":
    des = Describe("LabelMark")
    des("mid")
