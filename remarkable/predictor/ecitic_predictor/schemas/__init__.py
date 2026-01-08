R_REPORT_TITLE_PATTERNS = (
    r"(?P<content>^关于(.|\s)+?的公告)",
    r"(?P<content>.*的公告)",
)
R_IGNORE_HEADER_PATTERNS = [
    r"[合总小共]计$",
]
R_CHANGE_FLAGS = [
    r"(变更|修改)(如下|为)[：:。]",
]
R_CONTRACT = r"[《\(（]?(资产管理合同|原合同|资管合同)[\)）》]?中?"
R_CHAPTER = r"[章条节条、]"

R_BOTTOM_ANCHOR_REGS_BASE = [
    r"(表述|约定)(如下|为)[：:。]",
    r"如下(条款|变更)[：:。]",
    r"^[\d一二三四五六七八九十]+、\s*将.*(中|修改为[：:。])$",
    r"^[\d一二三四五六七八九十]+、修改",
    r"^[\d一二三四五六七八九十]+、.*?对.*进行修改",
    r"原约定[:：]",
    r"书面同意",
    r"(删除|增加|减少)[如以]下(内容|约定)[:：]",
]
R_BOTTOM_ANCHOR_REGS = [
    *R_BOTTOM_ANCHOR_REGS_BASE,
    R_CONTRACT,
]
R_HEADER_PATTERN = [r"(现|变更后)条款", r"修改后"]
R_LEFT_BRACKETS = r"([【(（]+)?"
R_RIGHT_BRACKETS = r"([）)】]+)?"
