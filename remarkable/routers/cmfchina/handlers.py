import urllib

from fastapi import APIRouter, Depends
from starlette.responses import FileResponse

from remarkable.config import project_root
from remarkable.db import pw_db
from remarkable.dependencies import check_user_permission
from remarkable.models.cmf_china import CmfABCompare
from remarkable.models.new_file import NewFile
from remarkable.models.new_user import NewAdminUser
from remarkable.pw_models.model import NewMold, NewMoldField
from remarkable.routers.cmfchina.permission import get_model
from remarkable.schema.cmfchina.schema import (
    CmfABCompareSchema,
    CmfAnswerData,
    CmfAnswerDataRes,
    CmfMoldFieldSchema,
    CmfProbabilitySchema,
)
from remarkable.service.cmfchina.cmf_group import CMFGroupService
from remarkable.service.cmfchina.service import CmfChinaService
from remarkable.service.cmfchina.util import sync_answer_data_stat
from remarkable.worker.tasks import inspect_rule_task

router = APIRouter()


@router.post(
    r"/molds/{mold_id}/ab-compare",
    description="新增或更新AB比对推送数据",
    dependencies=[Depends(check_user_permission("browse"))],
)
async def create_ab_url(
    schema: CmfABCompareSchema, mold: NewMold = Depends(get_model(NewMold, detail="场景不存在"))
) -> None:
    await CmfABCompare.create_or_update(mold_id=mold.id, url=schema.url, use_llm=schema.use_llm, prompt=schema.prompt)


@router.get(
    r"/molds/{mold_id}/ab-compare",
    description="获取AB比对推送数据",
    dependencies=[Depends(check_user_permission("browse"))],
)
async def get_ab_url(mold: NewMold = Depends(get_model(NewMold, detail="场景不存在"))) -> CmfABCompareSchema | None:
    return await pw_db.first(CmfABCompare.select().where(CmfABCompare.mold_id == mold.id).dicts())


@router.get(r"/push-example", description="下载推送样例", dependencies=[Depends(check_user_permission("browse"))])
async def download_push_example():
    file_path = f"{project_root}/data/cmf_china/example/push.json"
    filename = "推送样例.json"

    encoded_filename = urllib.parse.quote(filename)

    return FileResponse(
        path=file_path,
        filename=filename,
        headers={"Content-Disposition": f"attachment; filename*=UTF-8''{encoded_filename}"},
    )


@router.get(r"/callback-example", description="下载回调样例", dependencies=[Depends(check_user_permission("browse"))])
async def download_callback_example():
    file_path = f"{project_root}/data/cmf_china/example/callback.json"
    filename = "回调样例.json"

    encoded_filename = urllib.parse.quote(filename)

    return FileResponse(
        path=file_path,
        filename=filename,
        headers={"Content-Disposition": f"attachment; filename*=UTF-8''{encoded_filename}"},
    )


@router.post(
    r"/files/{fid:int}/answer_data",
    description="提交要素答案",
)
async def update_answer_data(
    data: CmfAnswerData,
    file: NewFile = Depends(get_model(NewFile, alias="fid", detail="文件不存在")),
    user: NewAdminUser = Depends(check_user_permission("inspect")),
) -> CmfAnswerDataRes:
    async with pw_db.atomic():
        res = await CmfChinaService.edit_answer_data(file, data.add, data.update, data.delete, user.id)
        await CmfChinaService.update_inspector_results(file, data.delete, data.add, data.update)
        ids = [add.get("id") for add in res.get("add", []) if add.get("id")]
        ids.extend([data.id for data in data.update + data.delete])
        await sync_answer_data_stat(ids)
    # 提交答案后直接运行审核
    if data.add or data.update or data.delete:
        inspect_rule_task.delay(file.id)
    return res


@router.get(
    r"/files/{fid:int}/answer_data",
    description="获取要素答案",
)
async def get_answer_data(
    file: NewFile = Depends(get_model(NewFile, alias="fid", detail="文件不存在")),
    user: NewAdminUser = Depends(check_user_permission("inspect")),
) -> list:
    if not user.is_admin:
        group_mold_ids = await CMFGroupService.get_user_group_molds(user.id)
    else:
        group_mold_ids = None
    res = await CmfChinaService.get_answer_data(file, group_mold_ids)
    return res


@router.get(
    r"/molds/{mold_id:int}/probabilities",
    description="获取字段阈值",
    dependencies=[Depends(check_user_permission("browse"))],
    response_model=list[CmfMoldFieldSchema],
)
async def get_probabilities(mold: NewMold = Depends(get_model(NewMold, detail="场景不存在"))):
    return await CmfChinaService.get_probabilities(mold.id)


@router.post(
    r"/fields/{field_id:int}/probability",
    description="设置字段阈值",
    dependencies=[Depends(check_user_permission("browse"))],
)
async def set_probability(
    probability: CmfProbabilitySchema,
    field: NewMoldField = Depends(get_model(NewMoldField, alias="field_id", detail="字段不存在")),
):
    return await CmfChinaService.set_probability(field.id, probability.probability)
