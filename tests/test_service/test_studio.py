from remarkable.service.studio import build_app_schema
from remarkable.routers.schemas.mold import MoldDataSchema


def test_reverse_app_schema():
    """
    测试 build_app_schema 函数
    """
    mold_data_json = {
        "schemas": [
            {
                "name": "个人信息",
                "orders": ["姓名", "年龄", "性别", "地址", "爱好"],
                "schema": {
                    "姓名": {
                        "type": "文本",
                        "required": False,
                        "multi": True,
                        "description": "姓名",
                        "extract_type": "llm",
                    },
                    "年龄": {
                        "type": "数字",
                        "required": False,
                        "multi": True,
                        "description": "年龄",
                        "extract_type": "llm",
                    },
                    "性别": {
                        "type": "性别",
                        "required": False,
                        "multi": False,
                        "description": "性别",
                        "extract_type": "llm",
                    },
                    "地址": {
                        "type": "地址",
                        "required": False,
                        "multi": False,
                        "description": "地址信息",
                        "extract_type": "llm",
                    },
                    "爱好": {"type": "文本", "required": False, "multi": True, "description": "爱好列表"},
                },
            },
            {
                "name": "地址",
                "schema": {
                    "省": {"type": "文本", "required": False, "multi": False, "description": "省份"},
                    "市": {
                        "type": "文本",
                        "required": False,
                        "multi": False,
                        "description": "城市",
                    },
                    "地址类型": {"type": "地址类型", "required": False, "multi": False, "description": "地址类型"},
                },
            },
        ],
        "schema_types": [
            {
                "label": "性别",
                "values": [{"name": "男", "isDefault": False}, {"name": "女", "isDefault": False}],
                "type": "enum",
            },
            {
                "label": "地址类型",
                "values": [
                    {"name": "家庭", "isDefault": False},
                    {"name": "公司", "isDefault": False},
                    {"name": "其他", "isDefault": False},
                ],
                "type": "enum",
            },
        ],
    }

    studio_app_json = {
        "schemas": {
            "type": "object",
            "properties": {
                "姓名": {"type": "array", "description": "姓名", "propertyOrder": 0, "items": {"type": "string"}},
                "年龄": {"type": "array", "description": "年龄", "propertyOrder": 1, "items": {"type": "number"}},
                "性别": {"description": "性别", "enum": ["男", "女"], "propertyOrder": 2},
                "地址": {
                    "type": "array",
                    "description": "地址信息",
                    "propertyOrder": 3,
                    "items": {
                        "type": "object",
                        "properties": {
                            "省": {"type": "string", "description": "省份", "propertyOrder": 0},
                            "市": {"type": "string", "description": "城市", "propertyOrder": 1},
                            "地址类型": {
                                "description": "地址类型",
                                "enum": ["家庭", "公司", "其他"],
                                "propertyOrder": 2,
                            },
                        },
                    },
                },
            },
        }
    }

    original_mold_data = MoldDataSchema.model_validate(mold_data_json)

    studio_schema = build_app_schema(original_mold_data)

    assert studio_schema.model_dump(by_alias=True, exclude_none=True) == studio_app_json
