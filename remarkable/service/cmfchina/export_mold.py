from __future__ import annotations

from pydantic import BaseModel, ConfigDict, ValidationError, field_validator, model_validator

from remarkable.common.exceptions import CustomError
from remarkable.predictor.mold_schema import MoldSchema


class ExportBaseModel(BaseModel):
    name: str
    alias: str

    @field_validator("name")
    @classmethod
    def check_name(cls, v):
        if not v:
            raise CustomError("名称为空")
        return v

    @field_validator("alias")
    @classmethod
    def check_alias(cls, v):
        if not v:
            raise CustomError("别名为空")
        return v


class CheckDuplicateModel(BaseModel):
    def check_duplicate(self):
        name_counts = {}
        for item in self.items:
            name_counts[item.name] = name_counts.get(item.name, 0) + 1

        duplicate_names = [name for name, count in name_counts.items() if count > 1]

        # 检查别名重复
        alias_counts = {}
        for item in self.items:
            alias_counts[item.alias] = alias_counts.get(item.alias, 0) + 1

        duplicate_aliases = [alias for alias, count in alias_counts.items() if count > 1]

        # 构建详细错误信息
        error_msgs = []
        if duplicate_names:
            error_msgs.append(f"名称重复:{','.join(duplicate_names)}")
        if duplicate_aliases:
            error_msgs.append(f"别名重复:{','.join(duplicate_aliases)}")

        if error_msgs:
            raise CustomError("\n".join(error_msgs))


class FieldModel(ExportBaseModel):
    model_config = ConfigDict(extra="forbid")

    type: str = "文本"

    @model_validator(mode="after")
    def check(self):
        if self.type not in MoldSchema.basic_types:
            raise CustomError(
                f"字段 {self.name} 类型输入错误，请修改后重新上传\n类型必须为其中之一： {'、'.join(MoldSchema.basic_types)}"
            )
        return self


class GroupModel(ExportBaseModel, CheckDuplicateModel):
    type: str
    items: list[GroupModel | FieldModel]

    @field_validator("type")
    @classmethod
    def validate_type(cls, v):
        if not v:
            raise CustomError("类型为空")
        return v

    @model_validator(mode="after")
    def check(self):
        self.check_duplicate()
        if self.type in MoldSchema.basic_types:
            raise CustomError(
                f"字段 {self.name} 组合类型错误，请修改后重新上传\n基本类型 {'、'.join(MoldSchema.basic_types)} 不能用做组合类型"
            )
        return self


class CmfImportMoldModel(CheckDuplicateModel):
    name: str | None = None
    alias: str | None = None
    items: list[GroupModel]

    @model_validator(mode="after")
    def check(self):
        self.check_duplicate()
        return self


class ExportMoldConvert:
    @classmethod
    def import_to_mold(cls, import_data: CmfImportMoldModel) -> dict:
        group_name_list = []

        def convert_schema(mold_data):
            schemas = []
            schema = {
                "name": mold_data.type if isinstance(mold_data, GroupModel) else mold_data.name,
                "alias": mold_data.alias,
                "orders": [],
                "schema": {},
            }
            for item in mold_data.items:
                schema["orders"].append(item.name)
                schema["schema"].update(
                    {
                        item.name: {
                            "type": item.type,
                            "alias": item.alias,
                            "multi": True,
                            "required": False,
                        }
                    }
                )

                if isinstance(item, GroupModel) and item.type not in group_name_list:
                    group_name_list.append(item.type)
                    schemas.extend(convert_schema(item))
            schemas.insert(0, schema)
            return schemas

        res = {"schemas": convert_schema(import_data), "schema_types": []}
        return res

    @classmethod
    def mold_to_export(cls, mold_data: MoldSchema) -> dict:
        def convert(schema):
            items = []
            for item in schema.children:
                temp_item = {"name": item.name, "alias": item.alias, "type": item.parent.schema[item.name]["type"]}
                if item.children:
                    temp_item["items"] = convert(item)
                items.append(temp_item)
            return items

        res = {"name": mold_data.root_schema.name, "alias": mold_data.root_schema.alias}
        if items := convert(mold_data.root_schema):
            res["items"] = items
        return res


if __name__ == "__main__":
    json_data = {
        "name": "基金合同",
        "alias": "fund_contract",
        "items": [
            {
                "name": "xxxx",
                "type": "xxxx",
                "alias": "xxxx",
                "items": [
                    {"name": "基金代码", "alias": "fund_code", "type": "文本"},
                    {"name": "基金名称", "alias": "fund_name", "type": "文本"},
                    {
                        "name": "托管人",
                        "type": "托管人",
                        "alias": "trustee",
                        "items": [
                            {"name": "地址", "alias": "address", "type": "文本"},
                            {"name": "电话", "alias": "phone_num", "type": "文本"},
                        ],
                    },
                    {
                        "name": "托管人1",
                        "type": "托管人",
                        "alias": "trustee1",
                        "items": [
                            {"name": "地址1", "alias": "address", "type": "文本"},
                            {"name": "电话1", "alias": "phone_num", "type": "文本"},
                        ],
                    },
                    {
                        "name": "管理人",
                        "type": "管理人",
                        "alias": "manager",
                        "items": [
                            {"name": "地址", "alias": "address", "type": "文本"},
                            {"name": "电话", "alias": "phone_num", "type": "文本"},
                        ],
                    },
                    {
                        "name": "管理人1",
                        "type": "管理人",
                        "alias": "manager1",
                        "items": [
                            {"name": "地址", "alias": "address", "type": "文本"},
                            {"name": "电话", "alias": "phone_num", "type": "文本"},
                        ],
                    },
                ],
            }
        ],
    }
    try:
        data = CmfImportMoldModel.model_validate(json_data)
        print(data)
    except CustomError as exp:
        print(exp)
    except ValidationError as exp:
        print(str(exp))
