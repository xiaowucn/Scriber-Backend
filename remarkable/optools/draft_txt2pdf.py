import re

from remarkable.common.pattern import PatternCollection

P_SEP = PatternCollection(r"^以下[为是]")
P_SPACE = PatternCollection(r"\s+")
P_COLON = PatternCollection(r"[:：]")


def split_to_blocks(path: str) -> tuple[list[str], list[list[str]]]:
    blocks = [[]]
    with open(path) as fp:
        for line in fp:
            line = line.strip()
            if P_SEP.nexts(line):
                blocks.append([blocks[-1].pop(), line])
            else:
                blocks[-1].append(line)
    for idx, lines in enumerate(blocks):
        blocks[idx] = [line for line in lines if line]
    return blocks[0], blocks[1:]


def calc_min_spaces(lines: list[str]) -> int:
    spaces = []
    for line in lines:
        for match in P_SPACE.finditer(line):
            spaces.append(len(match.group()))
    if not spaces:
        raise ValueError(f"No spaces found in {lines}")
    return min(spaces)


def parse_header(lines: list[str]) -> str:
    """
    输入示例：
        ['海通证券股份有限公司天津金男路营业部汇总对账单', '客户号：0400034300       客户姓名：哈哈哈哈2号', '开始日期：2024年10月28日
         结束日期：2024年10月28日', '承上日资金余额：30,020.24']
    输出示例：
        # 海通证券股份有限公司天津金男路营业部汇总对账单

        | 项目/序号 |1 |
        | --- | ---------- |
        | 客户号 | 0400034300 |
        | 客户姓名 | 哈哈哈哈2号 |
        | 开始日期 | 2024年10月28日 |
        | 结束日期 | 2024年10月28日 |
        | 承上日资金余额 | 30,020.24 |
    """
    header, *table_lines = lines
    min_spaces = calc_min_spaces(table_lines)
    space_pattern = re.compile(r"\s{%d,}" % min_spaces)
    tables = []
    for line in table_lines:
        lines = space_pattern.split(line, maxsplit=1)
        tables.extend([[i.strip() for i in P_COLON.split(line)] for line in lines])
    # tables = list(zip(*tables))
    md_content = f"# {header}\n\n"
    for idx, row in enumerate(tables):
        if idx == 0:
            md_content += "| 项目/序号 | " + " | ".join(str(i + 1) for i in range(len(row) - 1)) + " |\n"
            md_content += "| " + " | ".join("-" * len(i) for i in row) + " |\n"
        md_content += "| " + " | ".join(row) + " |\n"
    return md_content


def is_valid_amount_line(line: str) -> bool:
    """判断是否是有效的金额（包含千分位）"""
    total, amount_counts = 0, 0
    for amount in P_SPACE.split(line):
        total += 1
        if re.search(r"^[+-]?\d{1,3}(,\d{3})*(\.\d+)?$", amount):
            amount_counts += 1
    return amount_counts / total > 0.618


def parse_block(block: list[str]) -> str:
    """
    输入示例：
        以下为“人民币“的对账单
        ======================================================================================================================================================================================================
        发生日期 市场      股东代码      证券代码      摘要                              成交数            成交均价              库存数            变动金额            资金余额              交易费
        ------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------
        20240028  沪A                     688288        股息入帐特文器材                       0               0.000               2,300              404.80           30,323.34                0.00
        ------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------
        ======================================================================================================================================================================================================
        请注意：交易类资金变动的变动金额为成交金额含费用（如印花税、手续费、过户费等）!..
    输出示例：
        > 以下为“人民币“的对账单

        | 发生日期 | 市场 | 股东代码 | 证券代码 | 摘要 | 成交数 | 成交均价 | 库存数 | 变动金额 | 资金余额 | 交易费 |
        | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
        | 20240028 | 沪A |  | 688288 | 股息入帐特文器材 | 0 | 0.000 | 2,300 | 404.80 | 30,323.34 | 0.00 |

        > 请注意：交易类资金变动的变动金额为成交金额含费用（如印花税、手续费、过户费等）!..
    """
    from_idx = None
    to_idx = None
    for idx, line in enumerate(block):
        if P_SEP.nexts(line):
            from_idx = idx + 1
        if is_split_line(line) or is_valid_amount_line(line):
            to_idx = idx + 1
    if from_idx is None or to_idx is None:
        raise ValueError(f"Invalid block: {block}")
    above_lines = [line for line in block[:from_idx] if not is_split_line(line)]
    table_lines = [line for line in block[from_idx:to_idx] if not is_split_line(line)]
    below_lines = [line for line in block[to_idx:] if not is_split_line(line)]
    min_spaces = calc_min_spaces(table_lines)
    space_pattern = re.compile(r"\s{%d,}" % min_spaces)
    table_contents = []
    for idx, line in enumerate(table_lines):
        table_contents.append("| " + " | ".join(i.strip() for i in space_pattern.split(line)) + " |")
        if idx == 0:
            table_contents.append("| " + " | ".join("-" * len(i) for i in space_pattern.split(line)) + " |")
    content = "\n\n".join(f"> {line}" for line in above_lines)
    content += "\n\n" + "\n".join(table_contents) + "\n\n"
    content += "\n\n".join(f"> {line}" for line in below_lines)
    return content


def is_split_line(line):
    return line.startswith("---") or line.startswith("===")


def main(path: str):
    header, blocks = split_to_blocks(path)
    md_content = f"{parse_header(header)}\n\n"
    for block in blocks:
        md_content += parse_block(block) + "\n"
    return md_content


if __name__ == "__main__":
    # TODO:
    #  1. 单元格缺失、内容换行
    #  2. 金额列对齐
    #  3. 转横版PDF或者翻转表格，保证表格不换行
    txt_path = "0389641250汇总对账单20230518.txt"
    print(main(txt_path))
