from remarkable.predictor.models.base_model import BaseModel


def test_get_config():
    config = {
        "name": "table_row",
        "target_element": "table",
        "use_all_elements": True,
        "multi_elements": True,
        "股东名称": {
            "from_title": "helloworld",
        },
        "feature_white_list": {
            "申购区间": r"__regex__申购[金份]额",
        },
        "regs": '1',
        "基金名称": {
            "from_title": r"(?P<dst>([A-Z]类)",
        },
    }
    assert BaseModel._get_config(config, "table_row", "from_title", column="股东名称") == "helloworld"
    config = {"model|table_row": config}
    assert BaseModel._get_config(config, "table_row", "from_title", column="股东名称") == "helloworld"

    model_name = "table_row"
    columns = ['申购区间', '基金名称']

    sample = [
        {
            "key": "feature_white_list",
            "column": "申购区间",
            "value": r"__regex__申购[金份]额",
        },
        {
            "key": "feature_white_list",
            "column": "基金名称",
            "value": None,
        },
        {
            "key": "regs",
            "column": None,
            "value": '1',
        },
        {
            "key": "from_title",
            "column": "基金名称",
            "value": r"(?P<dst>([A-Z]类)",
        },
    ]

    for item in sample:
        value = BaseModel._get_config(config, model_name, item["key"], column=item["column"], columns=columns)
        assert value == item["value"]
