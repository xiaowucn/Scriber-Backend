import json
from itertools import chain

from calliper_diff.diff_data import diff_data

from remarkable.common.diff import calliper_diff
from remarkable.common.util import read_zip_first_file
from remarkable.config import project_root
from remarkable.routers.schemas.law_template import reset_paras_after_diff
from remarkable.utils.rule_para import MockedRule as Rule
from remarkable.utils.rule_para import calc_diff_ratio, format_diff_result, generate_rules_paras


def test_calliper_diff():
    interdoc1 = json.loads(read_zip_first_file(f"{project_root}/data/tests/interdoc/diff-test1.pdf.zip"))
    interdoc2 = json.loads(read_zip_first_file(f"{project_root}/data/tests/interdoc/diff-test2.pdf.zip"))
    param = {
        "kaiti_bold": False,  # 是否包含楷体加粗差异
        "ignore_case": True,  # 是否忽略大小写
        "ignore_punctuations": False,  # 是否忽略标点差异
        "ignore_chapt_numbers": True,  # 是否忽略章节号差异
        "char_ignore_rule": "all",
        "detailed_diff_log": False,
        "debug_data_path": None,
        "fontname": "",
        "fontstyle": "",
        "include_equal": False,
    }
    diff_res = calliper_diff(interdoc1, interdoc2, param=param)
    assert diff_res[0]["type"] == "chars_replace"
    assert diff_res[0]["left"] == ["兮", "兮", "四", "!"]
    assert diff_res[0]["right"] == ["西", "八", "。"]

    # diff result must be serializable
    json.dumps(diff_res)


def test_diff_law_rules():
    rules1 = [
        Rule(1, content="基金管理人应当建立内部控制制度"),
        Rule(2, content="基金托管人履行托管职责"),
        Rule(3, content="基金投资应当遵循分散原则"),
        Rule(4, content="基金费用应当公开透明"),
        Rule(5, content="基金信息应当及时披露"),
        Rule(6, content="基金风险管理制度"),
        Rule(7, content="基金合规监督机制"),
        Rule(8, content="基金清算程序规定"),
    ]

    rules2 = [
        Rule(101, content="基金管理人应当建立健全的内部控制制度"),  # 对应1，修改
        Rule(102, content="基金托管人履行托管职责"),  # 对应2，保持不变
        Rule(103, content="基金投资应当严格遵循风险分散原则"),  # 对应3，修改
        # 4,5,6 被删除 (连续删除)
        Rule(107, content="基金合规监督机制"),  # 对应7，保持不变
        Rule(108, content="基金清算程序应当规范透明"),  # 对应8，修改
        Rule(201, content="投资者保护措施"),  # 新增
        Rule(202, content="业绩评价标准"),  # 新增
        Rule(203, content="税收处理"),  # 新增 (连续新增)
    ]
    para1 = generate_rules_paras(rules1)
    para2 = generate_rules_paras(rules2)

    dcp = {
        "ignore_header_footer": False,
        "ignore_punctuations": True,
        "include_equal": True,
        "ignore_diff_on_toc_page": False,
        "similarity_diff_offset": 0,
    }
    diff_result, _ = diff_data(para1, para2, dcp)

    assert [diff["type"] for diff in diff_result] == [
        "equal",
        "para_delete",
        "chars_replace",
        "equal",
        "chars_replace",
        "para_insert",
        "chars_replace",
    ]  # 新版是对的, 最后两处: 应为先修改再删除

    ratio = calc_diff_ratio(diff_result)
    assert ratio == 56

    rule_map = {rule.id: rule for rule in chain(rules1, rules2)}
    diff = [diff for part in diff_result for diff in format_diff_result(part, rule_map)]
    equal_pairs = [(item["left"][0].id, item["right"][0].id) for item in diff if item["equal"]]
    assert equal_pairs == [(2, 102), (7, 107)]
    assert len(diff) == 11

    # test reset_paras_after_diff
    reset_paras_after_diff(para1["paragraphs"])
    reset_paras_after_diff(para2["paragraphs"])
    diff_data(para1, para2, dcp)  # diff without exception after reset
