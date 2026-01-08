from collections import defaultdict

from remarkable.common.constants import ComplianceStatus
from remarkable.common.rectangle import Rectangle
from remarkable.common.storage import localstorage
from remarkable.plugins.zjh.extract_pos import extract_ipo_position
from remarkable.rule.common import get_all_schema, get_texts_map
from remarkable.rule.inspector import LegacyInspector
from remarkable.rule.rule import LegacyRule

if not localstorage.exists("inspect_rule"):
    localstorage.create_dir("inspect_rule")

# constant
csv_file_id = 0
csv_file_name = 3
csv_file_checksum = 5

check_item_correct = 0
check_item_wrong = 1
check_item_miss = 2


class CompleteCsrcInspector(LegacyInspector):
    def __init__(self, **kwargs):
        kwargs["rules"] = {"default": [DefaultRule()]}
        super(CompleteCsrcInspector, self).__init__(**kwargs)


class DefaultRule(LegacyRule):
    def __init__(self):
        super(DefaultRule, self).__init__("完备性检查")

    def check(self, question, pdfinsight):
        schema = get_all_schema(question)
        cols = schema["orders"]
        specific_num = get_texts_map(cols, question)
        ret = []
        for col_cn in cols:
            ele_info = specific_num.get(col_cn, {})
            xpath = {}
            text = str(ele_info["texts"]).strip()
            comment_res = "披露" if text and text != "0" else "未披露"
            comment = col_cn + comment_res
            result = ComplianceStatus.COMPLIANCE.value if text and text != "0" else ComplianceStatus.NONCOMPLIANCE.value
            schema_cols = ele_info.get("schema_key", "")
            detail = {"line_infos": ele_info["line_infos"]}
            ret.append(([schema_cols], result, comment, xpath, col_cn, detail))
        return ret


def find_item_in_check_result(ipo_check_result, item):
    comment = ""
    last_field = item.split("-")[-1]
    for value in ipo_check_result.values():
        if not isinstance(value, dict):
            continue
        exception_field = value["异常字段"].split("-")[-1]
        if last_field == exception_field or value["异常字段"].startswith(item):
            comment = "披露不完整，需人工审核"
    return bool(comment), comment if comment else "披露完整"


def init_check_item(second_rule):
    return {
        "rule": "完备性审核",
        "second_rule": second_rule,
        "result": None,  # 0 合规 / 1 不合规 / 2 未出现 / 3 待定，需人工审核
        "comment": "",
        "detail": [],  # position list
    }


def merge_pos(answer_pos_item):
    check_item_pos = defaultdict(list)
    for pos_info in answer_pos_item:
        if "box" in pos_info:
            check_item_pos[pos_info["page"]].append(pos_info["box"])
        else:
            for item_pos_infos in pos_info.values():
                if not isinstance(item_pos_infos, list):
                    continue
                for item_pos_info in item_pos_infos:
                    check_item_pos[item_pos_info["page"]].append(item_pos_info["box"])
    check_item_result = []
    for page, poses in check_item_pos.items():
        base_rect = Rectangle(*poses[0])
        for pos in poses[1:]:
            base_rect = base_rect.union(Rectangle(*pos))
        check_item_result.append({"out_line": [base_rect.x, base_rect.y, base_rect.xx, base_rect.yy], "page": page})
    return check_item_result


def _merge_output_len_1(item, answer_pos, ipo_check_result):
    check_item = init_check_item(item)
    if item in answer_pos.keys():
        check_item_result = merge_pos(answer_pos[item])
        check_item["detail"] = check_item_result
        exception, comment = find_item_in_check_result(ipo_check_result, item)
        check_item["comment"] = comment
        check_item["result"] = check_item_wrong if exception else check_item_correct
    else:
        check_item["result"] = check_item_miss
        check_item["comment"] = "未披露"
    return check_item


def _merge_output_items(items, answer_pos, ipo_check_result):
    check_items = []
    for item in items:
        check_item = init_check_item(item)
        if item in answer_pos:
            check_item_result = merge_pos(answer_pos[item])
            check_item["detail"] = check_item_result
            exception, comment = find_item_in_check_result(ipo_check_result, item[0])
            check_item["comment"] = comment
            check_item["result"] = check_item_wrong if exception else check_item_correct
        else:
            check_item["result"] = check_item_miss
        check_items.append(check_item)
    return check_items


def _merge_output_data(preset_answer, rule_data):
    # answer = read_answer(file_id)
    answer_pos = read_answer_position(preset_answer)
    # ipo_check_result = read_ipo_check_result(file_info['filename'].split('.')[0])
    ipo_check_result = rule_data
    merge_res = []
    for item in schema_zjh_order:
        if len(item) == 1:
            check_item = _merge_output_len_1(item[0], answer_pos, ipo_check_result)
            merge_res.append(check_item)
        else:
            check_items = _merge_output_items(item[1], answer_pos, ipo_check_result)
            merge_res.extend(check_items)
    return merge_res


def read_answer_position(answer):
    position_data = extract_ipo_position(answer["userAnswer"], merged=False)
    return position_data


schema_zjh_order = [
    ["释义"],
    [
        "发行人基本情况",
        [
            "发行人-公司名称",
            "发行人-法定代表人姓名",
            "发行人-统一社会信用代码",
            "发行人-组织机构代码",
            "发行人-成立日期",
            "发行人-注册资本",
            "发行人-注册地址",
            "发行人-办公地址",
            "发行人-电话",
            "发行人-传真号码",
            "发行人-电子邮箱",
            "发行人-邮政编码",
        ],
    ],
    ["控股股东简要情况", ["控股股东-法人", "控股股东-自然人", "控股股东-其他"]],
    ["实际控制人简要情况", ["实际控制人-国有控股主体", "实际控制人-自然人", "实际控制人-其他"]],
    ["董事基本情况"],
    ["监事基本情况"],
    ["高管基本情况"],
    ["核心技术人员基本情况"],
    ["财务基本情况及财务指标", ["合并资产负债表", "合并利润表", "合并现金流量表", "基本财务指标"]],
    ["重大诉讼事项"],
    ["募集资金与运用"],
    ["专利"],
    ["主要客户"],
    ["主要供应商"],
    ["重大合同"],
    ["发行人所处行业", ["行业分类标准", "行业分类代码", "行业分类名称"]],
    ["盈利能力", ["营业收入分析", "营业成本分析"]],
]
