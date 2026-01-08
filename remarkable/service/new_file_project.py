import logging

from psycopg2.errors import UniqueViolation

from remarkable.common.enums import TaskType
from remarkable.common.exceptions import CustomError
from remarkable.db import pw_db
from remarkable.models.new_file import NewFile
from remarkable.models.new_user import ADMIN
from remarkable.pw_models.model import NewFileProject, NewFileTree
from remarkable.service.new_file_tree import NewFileTreeService

logger = logging.getLogger(__name__)


class NewFileProjectService:
    @classmethod
    async def create(
        cls, name: str, default_molds=None, uid: int = ADMIN.id, rtree_id: int = 0, **kwargs
    ) -> NewFileProject:
        if not default_molds:
            default_molds = []
        project = await NewFileProject.find_by_kwargs(name=name)
        if project:
            logger.info(f"project name<{project.name}> is existed")
            return project

        async with pw_db.atomic():
            try:
                project: NewFileProject = await pw_db.create(
                    NewFileProject, name=name, default_molds=default_molds, uid=uid, rtree_id=rtree_id, **kwargs
                )
                await project.create_root_tree()
            except UniqueViolation as e:
                # Handle race condition: another concurrent request may have created the project
                logger.warning(f"UniqueViolation when creating project '{name}': {e}")
                project = await NewFileProject.find_by_kwargs(name=name)
                if project:
                    logger.info(f"Project '{name}' was created by concurrent request, returning existing project")
                    return project
                # If not found by name, it's a different unique constraint violation (e.g., primary key)
                logger.error(f"UniqueViolation but project '{name}' not found, re-raising exception")
                raise
        return project

    @classmethod
    async def update(cls, project, params, process_files):
        file_count = await pw_db.count(
            NewFile.select().where(NewFile.pid == project.id, NewFile.task_type == TaskType.CLEAN_FILE.value)
        )
        if file_count > 0:
            raise CustomError(_("schema cannot be specified for clean documents"))
        permission = params.pop("permission", None)
        default_molds = params.get("default_molds")
        name = params.get("name")
        same_name_project = await NewFileProject.find_by_kwargs(name=name)
        if same_name_project and same_name_project.id != project.id:
            raise CustomError(_("project name is existed"))

        project_tree = await NewFileTree.find_by_id(project.rtree_id)
        files = []
        async with pw_db.atomic():
            await project_tree.update_(
                name=params.get("name", project.name),
                meta=params.get("meta", project.meta),
                default_scenario_id=params["default_scenario_id"],
                default_task_type=params["default_task_type"],
            )
            if default_molds is not None:
                files = await NewFileTreeService.update_child_molds(project_tree, default_molds)

            if permission and project.public and permission == "private":
                raise CustomError(_("Changing a public project to a private project is not supported"))
            if permission and permission in ("public", "private"):
                params["public"] = permission == "public"
            if params:
                await project.update_(**params)

        await process_files(files)
        return project

    @classmethod
    async def get_project_trash(cls, project):
        trash_name = f"{project.id}_trash"
        project_trash = await NewFileProject.find_by_kwargs(name=trash_name)
        if not project_trash:
            project_trash = await cls.create(name=trash_name, visible=False)
        return project_trash
