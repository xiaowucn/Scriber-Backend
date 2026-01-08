import logging
import re
from itertools import zip_longest

import chardet

from remarkable.common.pattern import PatternCollection

P_SEP = PatternCollection(r"^以下[为是]")
P_SPACE = PatternCollection(r"\s+")
P_COLON = PatternCollection(r"[:：]")

RMB_PATTERN = PatternCollection(r"人民币.*?对账单")
OPEN_FUND_PATTERN = PatternCollection(r"开放式基金")

EXCHANGE_PATTERN = PatternCollection(r"^沪A|深港|深A$")

MIN_BLOCK_SIZE = 3

RMB_HEADER_LEN = 11
OPEN_FUND_HEADER_LEN = 13

# 证券代码简称
SECURITY_ABBR_PATTERN = PatternCollection(r"\d{6}[\u4e00-\u9fa5]+\S*")
# 6位数字证券代码
SECURITY_CODE_PATTERN = PatternCollection(r"^[\d]{6}$")
# 数字
NUM_PATTERN = re.compile(r"^[+-]?\d{1,3}(,\d{3})*(\.\d+)?$")

RMB_HEADER_PATTERN = {
    "市场": PatternCollection(r"^沪A|深港|深A$"),
    "股东代码": PatternCollection(r"^[a-zA-z\d]+$"),
    "证券代码": SECURITY_CODE_PATTERN,
    "摘要": PatternCollection(r"^\S+$"),
}
OPEN_FUND_HEAD_PATTERN = {
    "股东代码": PatternCollection(r"^[a-zA-z\d]+$"),
    "证券代码简称": SECURITY_ABBR_PATTERN,
}

logger = logging.getLogger(__name__)


class GTJACheckListContentError(Exception):
    pass


def is_split_line(line):
    return line.startswith("---") or line.startswith("===")


def calc_min_spaces(lines: list[str]) -> int:
    spaces = []
    for line in lines:
        for match in P_SPACE.finditer(line):
            spaces.append(len(match.group()))
    if not spaces:
        logger.error(f"No spaces found in {lines}")
        raise ValueError(f"No spaces found in {lines}")
    return min(spaces)


def parse_header(lines: list[str]):
    header_data = {}
    header, *table_lines = lines
    min_spaces = calc_min_spaces(table_lines)
    space_pattern = re.compile(r"(?<![:：])\s{%d,}" % max(min_spaces, 2))
    for line in table_lines:
        lines = space_pattern.split(line, maxsplit=1)
        header_data.update({P_COLON.split(line)[0].strip(): P_COLON.split(line)[-1].strip() for line in lines})
    return header_data


def parse_block(block: list[str]):
    res_data = {}
    from_idx = None
    to_idx = None
    data_type = None
    for idx, line in enumerate(block):
        if P_SEP.nexts(line):
            from_idx = idx + 1
            if RMB_PATTERN.nexts(line):
                data_type = "RMB_DATA"
            elif OPEN_FUND_PATTERN.nexts(line):
                data_type = "OPEN_FUND_DATA"
            else:
                return res_data
        if (is_split_line(line) and line.startswith("---")) or is_valid_amount_line(line):
            to_idx = idx + 1
    if from_idx is None or to_idx is None:
        logger.error(f"Invalid block: {block}")
        raise ValueError(f"Invalid block: {block}")
    table_lines = [line for line in block[from_idx:to_idx] if not is_split_line(line)]
    if "RMB_DATA" == data_type:
        res_data["rmb"] = parse_rmb_data(table_lines)
    elif "OPEN_FUND_DATA" == data_type:
        res_data["open_fund"] = parse_open_fund_data(table_lines)
    return res_data


def parse_rmb_data(table: list[str]) -> list[dict]:
    num_max = 6
    table_header = []
    res = []
    min_spaces = calc_min_spaces(table)
    """
     发生日期 市场   股东代码      证券代码      摘    要                    成交数     成交均价     库存数         变动金额         资金余额       交易费
    """
    space_pattern = re.compile(r"\s{%d,}" % min_spaces)
    for idx, line in enumerate(table):
        if idx == 0:
            table_header = space_pattern.split(line)
            if RMB_HEADER_LEN != len(table_header):
                logger.error(f"Invalid table header {line}")
                return res
        else:
            table_content = space_pattern.split(line)
            if len(table_content) == len(table_header):
                res.append(dict(zip(table_header, table_content)))
            else:
                """
                发生日期:   6位数值，不为空
                市场:  沪A、深港、深A ，可能为空
                股东代码: 字母数字组合，长度不定，可能为空
                证券代码: 6位数值 ，可能为空
                摘要:字符串、长度不定，可能为空
                """
                # 把内容和表头对齐
                data_dict = {}
                num_cnt = 0
                for i in range(len(table_content) - 1, -1, -1):
                    if NUM_PATTERN.search(table_content[i]):
                        num_cnt += 1
                if num_cnt == num_max:
                    data_dict = dict(zip(table_header[-num_max:], table_content[-num_max:]))
                elif num_cnt < num_max:
                    data_dict = dict(zip_longest(table_header[-num_max:], table_content[-num_cnt:], fillvalue=None))
                # 取非数字部分
                left_content = table_content[: len(table_content) - num_cnt]
                if left_len := len(left_content) == (RMB_HEADER_LEN - num_max):
                    data_dict.update(dict(zip(table_content[:left_len], left_content)))
                else:
                    # 非数字部分对齐
                    data_dict[table_header[0]] = table_content[0]
                    start = 1
                    for head in table_header[1 : RMB_HEADER_LEN - num_max]:
                        if start > len(left_content) - 1:
                            data_dict[head] = None
                        pattern = RMB_HEADER_PATTERN.get(head)
                        if pattern.nexts(left_content[start]):
                            data_dict[head] = left_content[start]
                            start += 1
                        else:
                            data_dict[head] = None
                    if (
                        data_dict.get("证券代码") is None
                        and data_dict.get("股东代码") is not None
                        and SECURITY_CODE_PATTERN.nexts(data_dict.get("股东代码"))
                    ):
                        data_dict["证券代码"] = data_dict["股东代码"]
                        data_dict["股东代码"] = None
                res.append(data_dict)
    return res


def parse_open_fund_data(table: list[str]) -> list[dict]:
    num_max = 11
    table_header = []
    res = []
    min_spaces = calc_min_spaces(table)
    space_pattern = re.compile(r"\s{%d,}" % min_spaces)
    for idx, line in enumerate(table):
        if idx == 0:
            table_header = space_pattern.split(line)
            if OPEN_FUND_HEADER_LEN != len(table_header):
                logger.error(f"Invalid table header {line}")
                return res
        else:
            table_content = space_pattern.split(line)
            """
                开放式基金持股清单-股东代码、证券简称可能写在一起，拆解“6位字母数字+汉字+XXX” 为证券简称
            """
            # 第一个元素是否包含证券代码
            if find := SECURITY_ABBR_PATTERN.nexts(table_content[0]):
                security_abbr = find.group()
                table_content[0] = table_content[0].replace(security_abbr, "")
                table_content.insert(1, security_abbr)
            if len(table_content) == len(table_header):
                res.append(dict(zip(table_header, table_content)))
            else:
                # 把内容和表头对齐
                data_dict = {}
                num_cnt = 0
                for i in range(len(table_content) - 1, -1, -1):
                    if NUM_PATTERN.search(table_content[i]):
                        num_cnt += 1
                if num_cnt == num_max:
                    data_dict = dict(zip(table_header[-num_max:], table_content[-num_max:]))
                elif num_cnt < num_max:
                    data_dict = dict(zip_longest(table_header[-num_max:], table_content[-num_cnt:], fillvalue=None))
                # 取非数字部分
                """
                    股东代码:字母+数字组合 ，长度不定，可能为空
                    证券代码简称:6位字母数字+汉字+XXX，长度不定，可能为空
                """
                left_content = table_content[: len(table_content) - num_cnt]
                if (left_len := len(left_content)) == OPEN_FUND_HEADER_LEN - num_max:
                    data_dict.update(dict(zip(table_header[:left_len], left_content)))
                else:
                    start = 0
                    for head in table_header[: RMB_HEADER_LEN - num_max]:
                        if start > len(left_content) - 1:
                            data_dict[head] = None
                        pattern = RMB_HEADER_PATTERN.get(head)
                        if pattern.nexts(left_content[start]):
                            data_dict[head] = left_content[start]
                            start += 1
                        else:
                            data_dict[head] = None
                res.append(data_dict)
    return res


def is_valid_amount_line(line: str) -> bool:
    """判断是否是有效的金额（包含千分位）"""
    total, amount_counts = 0, 0
    for amount in P_SPACE.split(line):
        total += 1
        if NUM_PATTERN.search(amount):
            amount_counts += 1
    return amount_counts / total > 0.618


def parse(data: bytes):
    encoding = chardet.detect(data).get("encoding", "utf-8")
    str_content = data.decode(encoding)
    blocks = [[]]
    for line in str_content.splitlines():
        line = line.strip()
        line = line.replace("\xa0", "")
        line = re.sub(r"摘\s+要", "摘要", line)
        if P_SEP.nexts(line):
            blocks.append([blocks[-1].pop(), line])
        else:
            blocks[-1].append(line)
    for idx, lines in enumerate(blocks):
        blocks[idx] = [line for line in lines if line]
    if len(blocks) < MIN_BLOCK_SIZE:
        raise GTJACheckListContentError(f"Invalid file, blocks size less than {MIN_BLOCK_SIZE}")
    header, blocks = blocks[0], blocks[1:]
    res = parse_header(header)
    res["rmb"] = []
    res["open_fund"] = []
    for block in blocks:
        res.update(parse_block(block))
    return res
