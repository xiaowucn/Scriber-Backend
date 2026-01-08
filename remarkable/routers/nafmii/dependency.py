from fastapi import HTTPException, Request

from remarkable.config import get_config
from remarkable.plugins.nafmii.enums import DSFileType
from remarkable.pw_models.model import NewFileProject


async def get_project(file_type: DSFileType) -> NewFileProject:
    pid = get_config(f"nafmii.file_types.{file_type.value}.pid") or ""
    if not pid or not isinstance(pid, int):
        raise HTTPException(status_code=400, detail=f"pid of {file_type} not configured")
    project = await NewFileProject.find_by_id(pid)
    if not project:
        raise HTTPException(status_code=400, detail=f"project {pid} not found")
    return project


async def get_menu(request: Request) -> str:
    source = request.headers.get("X-Trigger-Source", "")
    if source == "task":
        return "识别任务管理"
    return "识别文件管理"
