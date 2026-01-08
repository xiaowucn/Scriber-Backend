import json
import logging
import os
from json import JSONDecodeError
from typing import Annotated

from fastapi import APIRouter, Depends, File, HTTPException, Query, Response, UploadFile
from pydantic import ValidationError
from starlette.status import HTTP_400_BAD_REQUEST

from remarkable.common.constants import PDFParseStatus
from remarkable.common.exceptions import CustomError, InvalidMoldError
from remarkable.data.handlers import validate_model_name
from remarkable.dependencies import get_current_user
from remarkable.models.new_file import NewFile
from remarkable.models.query_helper import AsyncPagination
from remarkable.pw_models.model import NewMold
from remarkable.routers.schemas.mold import LLMTestSchema, MoldDataWithModelNameSchema, SearchUsableFilesSchema
from remarkable.service.new_mold import NewMoldService
from remarkable.service.studio import create_app, get_extract_result, get_llm_list, update_app

mold_router = APIRouter(prefix="", tags=["mold"])
logger = logging.getLogger(__name__)


@mold_router.get("/llm-list", dependencies=[Depends(get_current_user)])
async def get_llms():
    """
    Get LLM list.
    """
    return get_llm_list()


@mold_router.get("/molds/{mid}/usable-files", dependencies=[Depends(get_current_user)])
async def get_mold_usable_files(mid: int, form: Annotated[SearchUsableFilesSchema, Query(...)]):
    """
    Get files that are usable with the specified mold.
    """
    query = (
        NewFile.select()
        .where(NewFile.molds.contains(mid), NewFile.pdf_parse_status == PDFParseStatus.COMPLETE)
        .order_by(NewFile.id.desc())
    )

    data = await AsyncPagination(query, page=form.page, size=form.size).data()
    return data


@mold_router.post("/molds/{mid}/llm-test", dependencies=[Depends(get_current_user)])
async def get_mold_llm_test(mid: int, form: LLMTestSchema):
    """
    Get LLM test results for a specific mold and file.
    """
    mold = await NewMold.find_by_id(mid)
    if mold is None:
        raise HTTPException(HTTP_400_BAD_REQUEST, "操作对象不存在")

    file = await NewFile.find_by_id(form.fid)
    if file is None:
        raise HTTPException(HTTP_400_BAD_REQUEST, "未找到文件")

    data = await get_extract_result(mold.studio_app_id, file.studio_upload_id)
    return data


@mold_router.get("/molds/{mid}/export-mold-data", dependencies=[Depends(get_current_user)])
async def export_mold_data(mid: int):
    """
    Export mold data field as JSON file.
    """
    mold = await NewMold.find_by_id(mid)
    if mold is None:
        raise HTTPException(HTTP_400_BAD_REQUEST, "操作对象不存在")

    data = mold.data if mold.data is not None else {}
    if "schemas" in data and len(data["schemas"]) > 0:
        data["schemas"][0].pop("name")
    data["model_name"] = mold.model_name
    json_bytes = json.dumps(data, ensure_ascii=False, indent=2).encode("utf-8")
    filename = f"mold_data_{mid}.json"
    return Response(
        content=json_bytes,
        media_type="application/octet-stream",
        headers={"Content-Disposition": f"attachment; filename={filename}"},
    )


@mold_router.post("/molds/{mid}/import-mold-data", dependencies=[Depends(get_current_user)])
async def import_mold_data(mid: int, file: UploadFile = File(...)):
    """
    Import mold data from a JSON file and store it in the data field.
    """
    mold = await NewMold.find_by_id(mid)
    if mold is None:
        raise HTTPException(HTTP_400_BAD_REQUEST, "操作对象不存在")

    if os.path.splitext(file.filename)[-1].lower() != ".json":
        raise HTTPException(HTTP_400_BAD_REQUEST, "仅支持 JSON 格式文件")

    try:
        file_content = await file.read()
        json_str = file_content.decode("utf-8")
        json_data = json.loads(json_str, object_pairs_hook=NewMoldService.check_duplicate_keys)
    except JSONDecodeError:
        raise HTTPException(HTTP_400_BAD_REQUEST, "不是有效的 JSON 格式") from None
    except CustomError as e:
        raise HTTPException(HTTP_400_BAD_REQUEST, str(e)) from None
    except UnicodeDecodeError:
        raise HTTPException(HTTP_400_BAD_REQUEST, "文件编码不是UTF-8") from None

    try:
        if "schemas" in json_data and len(json_data["schemas"]) > 0:
            json_data["schemas"][0].update({"name": mold.name})
        mold_data = MoldDataWithModelNameSchema.model_validate(json_data)
        studio_app_id = mold.studio_app_id
        model_name = mold.model_name
        if mold_data.need_llm_extract:
            model_name = json_data.pop("model_name", "")

            validate_model_name(model_name)
            if not studio_app_id:
                schema_app = await create_app(mold.name, model_name, {"schemas": {}})
                studio_app_id = schema_app["id"]
        if studio_app_id:
            await update_app(mold.name, model_name, mold_data, studio_app_id)
        await NewMoldService.update(
            mold,
            data=mold_data.model_dump(),
            studio_app_id=studio_app_id,
            model_name=model_name,
            mold_type=mold_data.mold_type,
        )
        return json_data
    except InvalidMoldError as e:
        raise HTTPException(HTTP_400_BAD_REQUEST, str(e)) from None
    except ValidationError:
        raise HTTPException(HTTP_400_BAD_REQUEST, "数据格式有误，请检查") from None
    except Exception as e:
        logger.error(f"更新 mold 数据失败: {e}")
        raise HTTPException(HTTP_400_BAD_REQUEST, "更新数据失败") from None
