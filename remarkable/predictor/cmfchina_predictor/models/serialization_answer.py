from typing import Annotated

from pydantic import BaseModel, BeforeValidator, ConfigDict, Field, model_validator

from remarkable.common.constants import SAFE_SEPARATOR
from remarkable.schema.special_answer import Box


class CmfFieldBaseModel(BaseModel):
    model_config = ConfigDict(from_attributes=True)


class ExcelFieldModel(CmfFieldBaseModel):
    sheet_name: str
    col: int
    row: int

    @model_validator(mode="before")
    @classmethod
    def check(cls, val):
        if isinstance(val, (dict, cls)):
            return val
        if isinstance(val, str) and ";" in val:
            datas = val.split(";")
            col, row = datas[1].split(":")
            return super().model_validate({"sheet_name": datas[0], "col": int(col), "row": int(row)})
        raise ValueError


class BoxFieldModel(CmfFieldBaseModel):
    box: Box
    page: int

    @model_validator(mode="before")
    @classmethod
    def check(cls, val):
        if isinstance(val, (dict, cls)):
            return val
        if isinstance(val, str) and "_" in val:
            page, _, left, top, right, down = val.split("_")
            return super().model_validate(
                {
                    "page": int(page),
                    "box": Box(
                        box_top=float(top), box_left=float(left), box_right=float(right), box_bottom=float(down)
                    ),
                }
            )
        raise ValueError


class BoxesModel(CmfFieldBaseModel):
    boxes: list[BoxFieldModel]

    @model_validator(mode="before")
    @classmethod
    def check(cls, val: str):
        if isinstance(val, (dict, cls)):
            return val
        if "_" in val:
            return {"boxes": [BoxFieldModel.model_validate(item) for item in val.split(";")]}
        raise ValueError


class FieldAnswerModel(CmfFieldBaseModel):
    key: str
    text: str
    probability: float
    position: ExcelFieldModel | BoxesModel
    is_correct: int | None = None

    @model_validator(mode="before")
    @classmethod
    def check(cls, val: str):
        if isinstance(val, cls):
            return val
        if isinstance(val, dict) and "group_list" in val:
            raise ValueError
        return val


class GroupFieldAnswerModel(CmfFieldBaseModel):
    key: str
    group_list: list[list[FieldAnswerModel]]

    @model_validator(mode="before")
    @classmethod
    def check(cls, val: str):
        if isinstance(val, cls):
            return val
        if isinstance(val, dict) and "group_list" in val:
            for index, item in enumerate(val["group_list"]):
                val["group_list"][index] = [{"key": key, **value} for key, value in item.items()]
            return val
        raise ValueError


class FileAnswerModel(BaseModel):
    file_groups: list[list[FieldAnswerModel | GroupFieldAnswerModel]]


def convert_to_int(v: str | int) -> int:
    if isinstance(v, str):
        try:
            return int(v)
        except ValueError as err:
            raise ValueError(f"无法将字符串 '{v}' 转换为整数") from err
    return v


IntLike = Annotated[int, BeforeValidator(convert_to_int)]


class OriginAnswerModel(BaseModel):
    pdf_type: IntLike
    serialNo: str
    status: str
    time: str
    files: dict[str, FileAnswerModel] = Field(alias="list")
    schema_aliases: dict[str, bool]
    excel_base64: list[str] = []

    @model_validator(mode="before")
    @classmethod
    def check(cls, val: dict):
        schema_aliases = {}
        for file_key, answers in val["list"].items():
            file_groups = []
            val["list"][file_key] = {"file_groups": []}
            for fi in answers:
                group_answer = []
                for key, value in fi.items():
                    if isinstance(value, list):
                        group_answer.append({"key": key, "group_list": value})
                        for item in value:
                            for sub_key in item.keys():
                                schema_aliases[f"{file_key}{SAFE_SEPARATOR}{key}{SAFE_SEPARATOR}{sub_key}"] = True
                    else:
                        schema_aliases[f"{file_key}{SAFE_SEPARATOR}{key}"] = True
                        group_answer.append({"key": key, **value})
                file_groups.append(group_answer)
            val["list"][file_key]["file_groups"] = file_groups
        val["schema_aliases"] = schema_aliases
        return val


data = {
    "pdf_type": "pension_ranking",
    "serialNo": "20241108092627085675",
    "status": "success",
    "time": "2024-11-08 08:52:10",
    "list": {
        "file_2": [
            {
                "TA_code": {
                    "text": "17",
                    "probability": 0.9996409131084505,
                    "position": "基金产品发行参数;3:4",
                    "is_correct": 1,
                },
                "fund_code": {
                    "text": "007950",
                    "probability": 0.9996081368076659,
                    "position": "基金产品发行参数;3:5",
                    "is_correct": 1,
                },
            },
            {
                "TA_code": {
                    "text": "17",
                    "probability": 0.9996409131084505,
                    "position": "基金产品发行参数1;3:4",
                    "is_correct": 1,
                },
                "fund_code": {
                    "text": "007950",
                    "probability": 0.9996081368076659,
                    "position": "基金产品发行参数1;3:5",
                    "is_correct": 1,
                },
            },
        ],
        "file_1": [
            {
                "Fund_code": {
                    "text": "019547",
                    "probability": 0.9994,
                    "position": "0_table_0.2452_0.5748_0.3056_0.5943",
                },
                "Pause_date": {
                    "text": "20240619",
                    "probability": 0.9699,
                    "position": "0_plain_0.1495_0.2803_0.8375_0.3056",
                },
                "Recovery_date": {
                    "text": "20240620",
                    "probability": 0.9829,
                    "position": "0_plain_0.1486_0.3061_0.8388_0.3314",
                },
                "Fund_status": {
                    "probability": 0.9989,
                    "text": "20240619 暂停,20240620 正常",
                    "position": "0_table_0.1137_0.2147_0.1422_0.2271",
                },
                "file_type": {
                    "probability": 0.9989,
                    "text": "节假日",
                    "position": "0_table_0.1137_0.2147_0.1422_0.2271",
                },
                "interest_payment_list": [
                    {
                        "interest_payment_settlement_date": {
                            "text": "20230121",
                            "probability": "0.9999",
                            "position": "0_table_0.2724_0.6158_0.3683_0.6331;0_table_0.2441_0.6444_0.3945_0.6603",
                        },
                        "interest_payment_interest_amount": {
                            "text": "1132361.11",
                            "probability": "0.9999",
                            "position": "0_table_0.4957_0.6335_0.6748_0.6501;0_table_0.4973_0.652_0.9616_0.6678",
                        },
                        "interest_payment_date": {
                            "text": "",
                            "probability": "0",
                            "position": "2_table_0.9999_0.9999_0.9999_0.9999",
                        },
                    },
                    {
                        "interest_payment_settlement_date": {
                            "text": "20230221",
                            "probability": "0.9999",
                            "position": "0_table_0.27241_0.61581_0.36831_0.63311;0_table_0.2452_0.6825_0.3934_0.698",
                        },
                        "interest_payment_interest_amount": {
                            "text": "1132361.11",
                            "probability": "0.9999",
                            "position": "0_table_0.4963_0.6712_0.686_0.6878",
                        },
                        "interest_payment_date": {
                            "text": "",
                            "probability": "0",
                            "position": "2_table_0.9999_0.9999_0.9999_0.9999",
                        },
                    },
                ],
                "group_1": [
                    {
                        "name": {
                            "text": "名字1_1",
                            "probability": "0.9999",
                            "position": "0_table_0.2724_0.6158_0.3683_0.6331;0_table_0.2441_0.6444_0.3945_0.6603",
                        },
                        "code": {
                            "text": "代码1_1",
                            "probability": "0.9999",
                            "position": "0_table_0.4957_0.6335_0.6748_0.6501;0_table_0.4973_0.652_0.9616_0.6678",
                        },
                        "name_code": {
                            "text": "",
                            "probability": "0",
                            "position": "2_table_0.9999_0.9999_0.9999_0.9999",
                        },
                    },
                    {
                        "name": {
                            "text": "名字1_1",
                            "probability": "0.9999",
                            "position": "0_table_0.27241_0.61581_0.36831_0.63311;0_table_0.2452_0.6825_0.3934_0.698",
                        },
                        "code": {
                            "text": "代码1_2",
                            "probability": "0.9999",
                            "position": "0_table_0.4963_0.6712_0.686_0.6878",
                        },
                        "name_code": {
                            "text": "",
                            "probability": "0",
                            "position": "2_table_0.9999_0.9999_0.9999_0.9999",
                        },
                    },
                ],
                "group_2": [
                    {
                        "name": {
                            "text": "名字2_1",
                            "probability": "0.9999",
                            "position": "0_table_0.2724_0.6158_0.3683_0.6331;0_table_0.2441_0.6444_0.3945_0.6603",
                        },
                        "code": {
                            "text": "代码2_1",
                            "probability": "0.9999",
                            "position": "0_table_0.4957_0.6335_0.6748_0.6501;0_table_0.4973_0.652_0.9616_0.6678",
                        },
                        "name_code": {
                            "text": "",
                            "probability": "0",
                            "position": "2_table_0.9999_0.9999_0.9999_0.9999",
                        },
                    },
                    {
                        "name": {
                            "text": "名字2_2",
                            "probability": "0.9999",
                            "position": "0_table_0.27241_0.61581_0.36831_0.63311;0_table_0.2452_0.6825_0.3934_0.698",
                        },
                        "code": {
                            "text": "代码2_2",
                            "probability": "0.9999",
                            "position": "0_table_0.4963_0.6712_0.686_0.6878",
                        },
                        "name_code": {
                            "text": "",
                            "probability": "0",
                            "position": "2_table_0.9999_0.9999_0.9999_0.9999",
                        },
                    },
                ],
            },
            {
                "Fund_code": {
                    "text": "019548",
                    "probability": 0.9994,
                    "position": "0_table_0.2452_0.6549_0.3056_0.6744",
                },
                "Pause_date": {
                    "text": "20240619",
                    "probability": 0.9699,
                    "position": "0_plain_0.1495_0.2803_0.8375_0.3056",
                },
                "Recovery_date": {
                    "text": "20240620",
                    "probability": 0.9829,
                    "position": "0_plain_0.1486_0.3061_0.8388_0.3314",
                },
                "Fund_status": {
                    "probability": 0.9989,
                    "text": "20240619 暂停,20240620 正常",
                    "position": "0_table_0.1137_0.2147_0.1422_0.2271",
                },
                "file_type": {
                    "probability": 0.9989,
                    "text": "节假日",
                    "position": "0_table_0.1137_0.2147_0.1422_0.2271",
                },
            },
        ],
    },
    "excel_base64": [
        "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",
        "",
    ],
}

if __name__ == "__main__":
    data = OriginAnswerModel.model_validate(data)
    print(data)
