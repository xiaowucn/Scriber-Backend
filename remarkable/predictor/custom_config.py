import attr

from remarkable.common.exceptions import ConfigError
from remarkable.config import get_config


@attr.define
class ModelConfigBase:
    name: str = attr.ib()
    multi: bool = attr.ib(default=False)
    multi_elements: bool = attr.ib(default=False)


@attr.define
class CustomConfig:
    models: list[ModelConfigBase] = attr.ib()
    path: list[str] = attr.ib(default=attr.Factory(list))
    enum_config: dict = attr.ib(default=attr.Factory(dict))


@attr.define
class AutoModelConfig(ModelConfigBase):
    model_intro = {
        "doc": "程序会自动选择最佳的提取模式",
        "name": "简易模型",
        "config_key": "auto",
        # 'use_answer_pattern': {
        #     'desc': '取标注内容自身特征',
        #     'default': False,
        # },
        # 'need_match_length': {
        #     'desc': '提取结果匹配标注内容的长度限制',
        #     'default': False,
        # },
        "multi": {
            "desc": "单段落内、提取多个结果（默认只提取1个）",
            "default": False,
        },
        "multi_elements": {
            "desc": "从多个元素块中提取（默认只从1个元素块提取）",
            "default": False,
        },
        # 'location_threshold': {
        #     'desc': '限制段落最低阈值（默认不限制）',
        #     'default': None,
        #     'need_input': True,
        # },
        # 'syllabus_regs': {
        #     'desc': '正向正则，匹配章节标题，仅对匹配到章节下的段落进行提取',
        #     'default': [],
        #     # 'need_input': True,
        #     'need_reg': True,
        # },
        "custom_regs": {
            "desc": "采用正则表达式直接提取具体内容",
            "default": [],
            "need_reg": True,
        },
        "ignore_case": {
            "desc": "是否忽略英文大小写，默认忽略",
            "default": True,
        },
        "cnt_of_anchor_elts": {
            "desc": "前方第几个段落满足正则条件",
            "default": 0,
            "need_input": True,
        },
        "anchor_regs": {
            "desc": "锚点正则表达式",
            "default": [],
            # 'need_input': True,
            "need_reg": True,
        },
        # "model_alternative": {
        #     'desc': '配置的正则没有生效时使用训练的模型进行提取,若配置为False,则仅使用界面配置的正则',
        #     'default': True,
        # },
        # 'neglect_patterns': {
        #     'desc': '需要忽略的正则表达式',
        #     'default': [],
        # },
    }
    syllabus_regs: list[str] = attr.ib(default=attr.Factory(list))
    use_answer_pattern: bool = attr.ib(default=False)
    ignore_case: bool = attr.ib(default=True)
    # neglect_patterns: List[str] = attr.ib(default=attr.Factory(list))
    custom_regs: list[str] = attr.ib(default=attr.Factory(list))
    anchor_regs: list[str] = attr.ib(default=attr.Factory(list))
    cnt_of_anchor_elts: int = attr.ib(default=0, converter=int)

    # model_alternative: bool = attr.ib(default=True)
    # need_match_length: bool = attr.ib(default=False)

    def __attrs_post_init__(self):
        self.syllabus_regs = [rf"{syllabus_reg}" for syllabus_reg in self.syllabus_regs if syllabus_reg]
        self.anchor_regs = [rf"{anchor_reg}" for anchor_reg in self.anchor_regs if anchor_reg]
        if self.cnt_of_anchor_elts == 0:
            if self.anchor_regs:
                raise ConfigError('配置"锚点正则表达式"，必须配置"前方第几个段落满足正则条件"')
            return
        if self.cnt_of_anchor_elts < 1:
            raise ConfigError('"前方第几个段落满足正则条件"必须大于0')
        if not self.anchor_regs:
            raise ConfigError('配置"前方第几个段落满足正则条件"，必须配置"锚点正则表达式"')


@attr.define
class CellPartialTextConfig(ModelConfigBase):
    model_intro = {
        "doc": "适用于从表格中提取指定单元格或单元格内部分内容",
        "name": "单元格部分文本",
        "config_key": "cell_partial_text",
        # 'use_answer_pattern': {
        #     'desc': '取标注内容自身特征',
        #     'default': False,
        # },
        # 'need_match_length': {
        #     'desc': '提取结果匹配标注内容的长度限制',
        #     'default': False,
        # },
        # "multi": {
        #     'desc': '单段落内、提取多个结果（默认只提取1个）',
        #     'default': False,
        # },
        "multi_elements": {
            "desc": "从多个表格中提取（默认只从1个段落提取）",
            "default": False,
        },
        # 'location_threshold': {
        #     'desc': '限制段落最低阈值（默认不限制）',
        #     'default': None,
        #     'need_input': True,
        # },
        # 'syllabus_regs': {
        #     'desc': '正向正则，匹配章节标题，仅对匹配到章节下的段落进行提取',
        #     'default': [],
        #     # 'need_input': True,
        #     'need_reg': True,
        # },
        "regs": {
            "desc": "采用正则表达式直接提取具体内容",
            "default": [],
            # 'need_input': True,
            "need_reg": True,
        },
        # 'cnt_of_anchor_elts': {
        #     'desc': '前方第几个段落满足正则条件',
        #     'default': 0,
        #     'need_input': True,
        # },
        # 'anchor_reg': {
        #     'desc': '锚点正则表达式',
        #     'default': [],
        #     'need_input': True,
        #     'need_reg': True,
        # },
        # "model_alternative": {
        #     'desc': '配置的正则没有生效时使用训练的模型进行提取,若配置为False,则仅使用界面配置的正则',
        #     'default': True,
        # },
        # 'neglect_patterns': {
        #     'desc': '需要忽略的正则表达式',
        #     'default': [],
        # },
    }
    syllabus_regs: list[str] = attr.ib(default=attr.Factory(list))
    # use_answer_pattern: bool = attr.ib(default=False)
    # neglect_patterns: List[str] = attr.ib(default=attr.Factory(list))
    regs: list[str] = attr.ib(default=attr.Factory(list))
    # anchor_reg: List[str] = attr.ib(default=attr.Factory(list))
    # cnt_of_anchor_elts: int = attr.ib(default=0)
    # model_alternative: bool = attr.ib(default=False)
    # need_match_length: bool = attr.ib(default=False)
    width_from_all_rows: bool = attr.ib(default=True)

    def __attrs_post_init__(self):
        self.syllabus_regs = [rf"{syllabus_reg}" for syllabus_reg in self.syllabus_regs]


@attr.define
class PartialTextConfig(ModelConfigBase):
    model_intro = {
        "doc": "适用于提取指定段落或特定部分的文本内容",
        "name": "段落部分文本",
        "config_key": "partial_text",
        # 'use_answer_pattern': {
        #     'desc': '取标注内容自身特征',
        #     'default': False,
        # },
        # 'need_match_length': {
        #     'desc': '提取结果匹配标注内容的长度限制',
        #     'default': False,
        # },
        "multi": {
            "desc": "单段落内提取多个结果（默认只提取1个）",
            "default": False,
        },
        "multi_elements": {
            "desc": "从多个段落中提取（默认只从1个段落提取）",
            "default": False,
        },
        # 'location_threshold': {
        #     'desc': '限制段落最低阈值（默认不限制）',
        #     'default': None,
        #     'need_input': True,
        # },
        "syllabus_regs": {
            "desc": "正向正则，匹配章节标题，仅对匹配到章节下的段落进行提取",
            "default": [],
            # 'need_input': True,
            "need_reg": True,
        },
        # "regs": {
        #     'desc': '采用正则表达式直接提取具体内容',
        #     'default': [],
        #     'need_input': True,
        #     'need_reg': True,
        # },
        # 'cnt_of_anchor_elts': {
        #     'desc': '前方第几个段落满足正则条件',
        #     'default': 0,
        #     'need_input': True,
        # },
        # 'anchor_reg': {
        #     'desc': '锚点正则表达式',
        #     'default': [],
        #     'need_input': True,
        #     'need_reg': True,
        # },
        # "model_alternative": {
        #     'desc': '配置的正则没有生效时使用训练的模型进行提取,若配置为False,则仅使用界面配置的正则',
        #     'default': True,
        # },
        "neglect_patterns": {
            "desc": "负面正则，过滤错误的初步定位元素块",
            "default": [],
            "need_reg": True,
        },
        "neglect_answer_patterns": {
            "desc": "负面答案正则，用来过滤错误的答案",
            "default": [],
            "need_reg": True,
        },
        # 'neglect_patterns': [],  # 负面正则  用来过滤错误的初步定位元素块
        # 'neglect_answer_patterns': [],  # 负面答案正则  用来过滤错误的答案
    }
    syllabus_regs: list[str] = attr.ib(default=attr.Factory(list))
    use_answer_pattern: bool = attr.ib(default=False)
    neglect_patterns: list[str] = attr.ib(default=attr.Factory(list))
    neglect_answer_patterns: list[str] = attr.ib(default=attr.Factory(list))

    # regs: List[str] = attr.ib(default=attr.Factory(list))
    # anchor_reg: List[str] = attr.ib(default=attr.Factory(list))
    # cnt_of_anchor_elts: int = attr.ib(default=0)
    # model_alternative: bool = attr.ib(default=False)
    # need_match_length: bool = attr.ib(default=False)

    def __attrs_post_init__(self):
        self.syllabus_regs = [rf"{syllabus_reg}" for syllabus_reg in self.syllabus_regs]


@attr.define
class ScoreFilterConfig(ModelConfigBase):
    model_intro = {
        "doc": "使用特定的定位方式，找到需要提取的内容并提取",
        "name": "段落/表格定位",
        "config_key": "score_filter",
        "multi_elements": {
            "desc": "是否从多个元素块中提取",
            "default": False,
        },
        "sort_by_index": {
            "desc": "是否按元素块在文中的自然顺序排序",
            "default": False,
        },
        "threshold": {
            "desc": "初步定位元素块阈值下限",
            "default": 0,
            "need_input": True,
        },
        "aim_types": {
            "desc": "答案类型",
            "enum": ["PARAGRAPH", "TABLE"],
            "default": [],
        },
    }
    sort_by_index: bool = attr.ib(default=False)
    threshold: float = attr.ib(default=0.0, converter=float)
    aim_types: list[str] = attr.ib(default=attr.Factory(list))

    @threshold.validator
    def check(self, attributes, value):
        if not 0 <= value < 1:
            raise ValueError("阈值是0-1之间的小数")

    # def __attrs_post_init__(self):
    #     if isinstance(self.aim_types, str):
    #         self.aim_types = [self.aim_types]


@attr.define
class SyllabusEltConfig(ModelConfigBase):
    model_intro = {
        "doc": "适用于整个章节内容提取，包括标题、子标题、正文等",
        "name": "整个章节",
        "config_key": "syllabus_elt_v2",
        "multi": {
            "desc": "是否提取多个章节",
            "default": False,
        },
        # 'multi_level': {
        #     'desc': '是否支持多级章节',
        #     'default': False,
        # },
        # 'keep_parent': {
        #     'desc': '保留父级标题',
        #     'default': False,
        # },
        # 'order_by': {
        #     'desc': '遍历章节时的排序方式',
        #     'enum': ['index', 'level'],
        #     'default': 'index',
        # },
        # 'reverse': {
        #     'desc': '是否倒序遍历章节',
        #     'default': False,
        # },
        "only_first": {
            "desc": "只取章节下的第一个元素块",
            "default": False,
        },
        "include_title": {
            "desc": "包含章节标题",
            "default": False,
        },
        # 'match_method': {
        #     'desc': '寻找标题时的匹配方式，默认为精确匹配，若选择similarity，则根据相似度匹配',
        #     'enum': ['extract', 'similarity'],
        #     'default': 'extract',
        # },
        "inject_custom_patterns": {
            "desc": "正则表达式提取章节",
            "default": [],
            "need_reg": True,
        },
        # 'only_inject_features': {
        #     'desc': '仅使用特征白名单中的特征',
        #     'default': False,
        # },
        # 'neglect_patterns': {
        #     'desc': '章节特征黑名单',
        #     'default': [],
        # },
    }
    only_first: bool = attr.ib(default=False)
    include_title: bool = attr.ib(default=False)
    inject_custom_patterns: list[str] = attr.ib(default=attr.Factory(list))


@attr.define
class TableKVConfig(ModelConfigBase):
    model_intro = {
        "doc": "适用于从表格中提取多个键值对信息，这类表格每一行都显示一个数据字段及其相关值",
        "name": "多个键值对列示表",
        "config_key": "custom_table_kv",
        "__config": {
            "allow_select_primary_key": True,
        },
        "multi": {
            "desc": "是否提取多个答案",
            "default": False,
        },
        "multi_elements": {
            "desc": "是否从多个表格中提取",
            "default": False,
        },
        "sub_primary_key": {
            "desc": "主键选择",
            "default": [],
            "need_select": True,
        },
        # 'feature_white_list': {
        #     'desc': '特征白名单',
        #     'default': [],
        #     'need_reg': True,
        # },
        # 'feature_black_list': {
        #     'desc': '特征黑名单',
        #     'default': [],
        #     'need_reg': True,
        # },
        "regs": {
            "desc": "根据key提取到value后,再尝试根据正则提取更精确的答案",
            "default": [],
            "need_reg": True,
        },
        # "kv_directions": {
        #     "desc": "数据结构",
        #     "default": ["left_and_right"],
        #     "options": ["left_and_right", "up_and_down"],
        # },
        # "neglect_regs": {
        #     "desc": "负向正则",
        #     "default": [],
        #     "need_reg": True,
        # },
        # 'only_matched_value': {
        #     'desc': 'value是否必须匹配regs',
        #     'default': False,
        #     'need_reg': True,
        # },
        # 暂不开放
        # 'split_single_column_table': {
        #     'desc': '尝试拆分单列表,需搭配regs',
        #     'default': False,
        # },
        # 'width_from_all_rows': {
        #     'desc': '默认取表格第一行宽度, 为True时取最宽的行',
        #     'default': False,
        # },
    }
    regs: list[str] = attr.ib(default=attr.Factory(list))
    sub_primary_key: list[str] = attr.ib(default=attr.Factory(list))
    keep_dummy: bool = attr.ib(default=True)
    deduplicate_by_cell: bool = attr.ib(default=False)
    kv_directions: list[str] = attr.ib(default=attr.Factory(list))
    neglect_regs: list[str] = attr.ib(default=attr.Factory(list))


@attr.define
class TableRowConfig(ModelConfigBase):
    model_intro = {
        "doc": "适用于从表格中提取多个数据行来获取所需要的信息，在这类表格中，每个数据行通常包含多个数据字段",
        "name": "关系表（多行数据列示）",
        "config_key": "table_row",
        # 'multi': {
        #     'desc': '是否提取多个答案',
        #     'default': True,
        # },
        "multi_elements": {
            "desc": "是否从多个表格中提取",
            "default": True,
        },
        # 'filter_serial_number': {
        #     'desc': '忽略序号列',
        #     'default': False,
        # },
        # 'feature_white_list': {
        #     'desc': '特征白名单',
        #     'default': [],
        # },
        # 'feature_black_list': {
        #     'desc': '特征黑名单',
        #     'default': [],
        #     'need_reg': True,
        # },
        # 'neglect_patterns': {
        #     'desc': '需要忽略的行',
        #     'default': [],
        #     'need_reg': True,
        # },
        # 'header_regs': {
        #     'desc': '行头和列头需匹配的正则',
        #     'default': [],
        # },
        "neglect_row_header_regs": {
            "desc": "忽略的特殊行",
            "default": [],
            "need_reg": True,
        },
        "neglect_col_header_regs": {
            "desc": "忽略的特殊列",
            "default": [],
            "need_reg": True,
        },
        "neglect_patterns": {
            "desc": "忽略的特殊单元格",
            "default": [],
            "need_reg": True,
        },
        "neglect_title_patterns": {
            "desc": "忽略的表格标题",
            "default": [],
            "need_reg": True,
        },
        # 'title_patterns': {
        #     'desc': '表格标题必须包含的正则表达式',
        #     'default': [],
        #     'need_reg': True,
        # },
        # 'parse_by': {
        #     'desc': '按行/列读取表格',
        #     'enum': ['row', 'col'],
        #     'default': 'row',
        #     'need_train_again': True,
        # },
        # 'feature_from': {
        #     'desc': '特征来源',
        #     'enum': ['header', 'self', 'left_cells', 'right_cells'],
        #     'default': 'header',
        #     'need_train_again':  True,
        # },
    }
    multi: bool = attr.ib(default=True)
    multi_elements: bool = attr.ib(default=True)
    feature_black_list: list[str] = attr.ib(default=attr.Factory(list))
    neglect_patterns: list[str] = attr.ib(default=attr.Factory(list))
    neglect_row_header_regs: list[str] = attr.ib(default=attr.Factory(list))
    neglect_col_header_regs: list[str] = attr.ib(default=attr.Factory(list))
    neglect_title_patterns: list[str] = attr.ib(default=attr.Factory(list))


@attr.define
class TableTupleConfig(ModelConfigBase):
    model_intro = {
        "doc": "适用于从二维信息表中提取所需要的信息，这类表格通常包含多行数据和多列属性",
        "name": "二维信息表",
        "config_key": "table_tuple",
        # 'multi': {
        #     'desc': '是否提取多个答案',
        #     'default': True,
        # },
        "multi_elements": {
            "desc": "是否从多个表格中提取",
            "default": True,
        },
        "neglect_title_patterns": {
            "desc": "表格标题黑名单",
            "default": [],
            "need_reg": True,
        },
        "title_patterns": {
            "desc": "表格标题白名单",
            "default": [],
            "need_reg": True,
        },
        # 'distinguish_year': {
        #     'desc': '区分年份',
        #     'default': True,
        # },
        # 'dimensions': {
        #     'desc': '附加维度字段',
        #     'default': [],
        # },
        # 'feature_black_list': {
        #     'desc': '特征黑名单',
        #     'default': [],
        # },
        # 'feature_white_list': {
        #     'desc': '特征白名单',
        #     'default': [],
        # },
    }

    multi: bool = attr.ib(default=True)
    neglect_title_patterns: list[str] = attr.ib(default=attr.Factory(list))
    title_patterns: list[str] = attr.ib(default=attr.Factory(list))


@attr.define
class FixedPositionConfig(ModelConfigBase):
    model_intro = {
        "doc": "在文档固定位置出现的属性，如证券代码、证券简称、公告编号等",
        "name": "固定位置提取",
        "config_key": "fixed_position",
        # 'multi': {
        #     'desc': '是否提取多个答案',
        #     'default': True,
        # },
        "multi_elements": {
            "desc": "是否从多个元素块中提取",
            "default": True,
        },
        "pages": {
            "desc": "答案出现的指定页码，可填写多个，如:1,2,3或者-1,-2,-3",
            "default": [],
            "need_reg": True,
        },
        "positions": {
            "desc": "答案出现的元素块序号，可填写多个，如:1,2,3或者-1,-2,-3",
            "default": [],
            "need_reg": True,
        },
        "regs": {
            "desc": "正则表达式",
            "default": [],
            "need_reg": True,
        },
        # 'anchor_regs': {
        #     'desc': '锚点正则表达式（前一个段落）',
        #     'default': [],
        # },
        # 'use_crude_answer': {
        #     'desc': '使用初步定位答案',
        #     'default': False,
        # },
    }

    pages: list[str] = attr.ib(default=attr.Factory(list))
    positions: list[str] = attr.ib(default=attr.Factory(list))
    regs: list[str] = attr.ib(default=attr.Factory(list))

    def __attrs_post_init__(self):
        self.pages = [i for i in self.pages if i]
        self.positions = [i for i in self.positions if i]
        self.regs = [rf"{reg}" for reg in self.regs if reg]
        if any("，" in i for i in self.pages):
            raise ConfigError("页码配置中不能有，")
        if any("，" in i for i in self.positions):
            raise ConfigError("元素块序号配置中不能有，")


@attr.define
class ParaMatchConfig(ModelConfigBase):
    model_intro = {
        "doc": "根据正则提取段落内容",
        "name": "段落提取",
        "config_key": "para_match",
        "use_crude_answer": {
            "desc": "使用初步定位答案",
            "default": True,
        },
        "index_range": {
            "desc": "元素块序号",
            "default": (0, 20),
        },
        "combine_paragraphs": {
            "desc": "拼接多个段落为一个答案",
            "default": False,
        },
        "split_pattern": {
            "desc": "将一个段落分隔成多个答案，分隔符正则长度限制为1",
            "default": [],
        },
        "enum_from_multi_element": {
            "desc": "从多个元素块确定枚举值",
            "default": False,
        },
        "paragraph_pattern": {
            "desc": "段落正则",
            "default": [],
        },
        "content_pattern": {
            "desc": "内容正则",
            "default": [],
        },
        "anchor_regs": {
            "desc": "锚点正则表达式（前一个段落）",
            "default": [],
        },
        "include_anchor": {
            "desc": "提取锚点所在段落",
            "default": False,
        },
        # 'current_regs': {
        #     'desc': '提取锚点所在段落',
        #     'default': False,
        # },
    }


@attr.define
class MiddleParasConfig(ModelConfigBase):
    model_intro = {
        "doc": "找到前后两个锚点,取中间的段落或表格",
        "name": "中间元素块",
        "config_key": "middle_paras",
        "use_top_crude_neighbor": {
            "desc": "使用初步定位得分最高的元素块周围的元素块",
            "default": True,
        },
        "use_syllabus_model": {
            "desc": "使用指定的章节确定初步范围",
            "default": True,
        },
        "top_anchor_regs": {
            "desc": "顶部锚点正则表达式",
            "default": [],
            "need_reg": True,
        },
        "bottom_anchor_regs": {
            "desc": "底部锚点正则表达式",
            "default": [],
            "need_reg": True,
        },
        "include_top_anchor": {
            "desc": "包含顶部锚点",
            "default": True,
        },
        "include_bottom_anchor": {
            "desc": "包含底部锚点",
            "default": False,
        },
        "top_greed": {
            "desc": "顶部贪婪模式,即截出来的元素块尽量多",
            "default": True,
        },
        # 'top_continue_greed': {
        #     'desc': '顶部贪婪必须连续',
        #     'default': False,
        # },
        # 'bottom_greed': {
        #     'desc': '底部贪婪模式,即截出来的元素块尽量多',
        #     'default': False,
        # },
        # 'bottom_continue_greed': {
        #     'desc': '底部贪婪必须连续',
        #     'default': False,
        # },
        "top_default": {
            "desc": "第一个元素块作为顶部锚点备选方案",
            "default": False,
        },
        "bottom_default": {
            "desc": "最后一个元素块作为底部锚点备选方案",
            "default": False,
        },
        "top_anchor_content_regs": {
            "desc": "从顶部锚点提取内容的正则表达式",
            "default": [],
            "need_reg": True,
        },
        "bottom_anchor_content_regs": {
            "desc": "从底部锚点提取内容的正则表达式",
            "default": [],
            "need_reg": True,
        },
        # 'possible_element_counts': {
        #     'desc': '',
        #     'default': [],
        # },
        # 'use_direct_elements': {
        #     'desc': '',
        #     'default': [],
        # },
    }

    keep_parent: bool = attr.ib(default=True)
    use_top_crude_neighbor: bool = attr.ib(default=True)
    use_syllabus_model: bool = attr.ib(default=True)
    top_anchor_regs: bool = attr.ib(default=True)
    bottom_anchor_regs: bool = attr.ib(default=True)
    include_top_anchor: bool = attr.ib(default=True)
    include_bottom_anchor: bool = attr.ib(default=False)
    top_default: bool = attr.ib(default=False)
    top_greed: bool = attr.ib(default=True)
    bottom_default: bool = attr.ib(default=False)
    top_anchor_content_regs: list[str] = attr.ib(default=attr.Factory(list))
    bottom_anchor_content_regs: list[str] = attr.ib(default=attr.Factory(list))


@attr.define
class LLMConfig(ModelConfigBase):
    model_intro = {
        "doc": "通过提示词来提取答案",
        "name": "大模型提取",
        "config_key": "llm",
        # "prompt": {
        #     "desc": "提示词",
        #     "default": "",
        # },
    }

    # prompt: str = attr.ib(default="")


@attr.define
class ConfiginCode(ModelConfigBase):
    model_intro = {
        "doc": "后端预置设置",
        "name": "后端预置设置",
        "config_key": "config_in_code",
    }


model_config_map = {
    "partial_text": PartialTextConfig,
    "cell_partial_text": CellPartialTextConfig,
    "score_filter": ScoreFilterConfig,
    "syllabus_elt_v2": SyllabusEltConfig,
    "custom_table_kv": TableKVConfig,
    "table_row": TableRowConfig,
    "config_in_code": ConfiginCode,
    "table_tuple": TableTupleConfig,
    "fixed_position": FixedPositionConfig,
    "auto": AutoModelConfig,
    "middle_paras": MiddleParasConfig,
    # todo 以下暂不开放
    # 'para_match': ParaMatchConfig,
    # 'remote_call': PartialTextConfig, # TODO 待完善
}

if get_config("ai.openai.embedding_model"):
    model_config_map["llm"] = LLMConfig
