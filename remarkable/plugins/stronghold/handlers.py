import hashlib

from tornado.httputil import HTTPFile
from webargs import fields

from remarkable.base_handler import Auth, BaseHandler
from remarkable.common.apispec_decorators import use_kwargs
from remarkable.config import get_config
from remarkable.db import peewee_transaction_wrapper, pw_db
from remarkable.file_flow.tasks.factory import create_flow_task
from remarkable.file_flow.uploaded_file import UploadedFile
from remarkable.models.new_file import NewFile
from remarkable.models.new_user import ADMIN
from remarkable.plugins.stronghold import plugin
from remarkable.pw_db_services import PeeweeService
from remarkable.pw_models.model import NewFileProject, NewFileTree
from remarkable.service.new_file_project import NewFileProjectService


async def get_project_and_file_tree_by_path(path: str):
    projects = await NewFileProject.find_by_kwargs(delegate="all")
    if projects:
        project = projects[0]
    else:
        project = await NewFileProjectService.create(name="stronghold", default_molds=[], preset_answer_model="")

    root_tree = await NewFileTree.find_by_kwargs(id=project.rtree_id)

    components = path[1:].split("/")
    ptree_id = root_tree.id
    file_tree = root_tree
    for component in components[:-1]:
        file_tree = await NewFileTree.find_by_kwargs(name=component, ptree_id=ptree_id)
        if file_tree is None:
            file_tree = await NewFileTree.create(
                **{
                    "ptree_id": ptree_id,
                    "pid": project.id,
                    "name": component,
                    "uid": ADMIN.id,
                    "default_molds": [],
                },
            )
        ptree_id = file_tree.id
    return project, file_tree, components[-1]


@plugin.route(r"/documents")
class UploadHandler(BaseHandler):
    args_schema = {
        "external_id": fields.Str(),
    }

    @Auth("browse")
    @use_kwargs({**args_schema}, location="form")
    @use_kwargs(
        {
            "files": fields.List(
                fields.Raw(),
                data_key="file",
                required=False,
                load_default=[],
            )
        },
        location="files",
    )
    async def post(self, external_id: str, files: list[HTTPFile]):
        project, file_tree, file_name = await get_project_and_file_tree_by_path(external_id)
        if not file_tree:
            return self.ext_error(_("Invalid treeId"))

        file_hash = hashlib.md5(files[0].body).hexdigest()
        file = await NewFile.find_by_kwargs(name=file_name, tree_id=file_tree.id, pid=project.id)

        if file is not None:
            if file.hash != file_hash:
                await file.soft_delete()
                file = None

        if file is None:
            uploaded_file = UploadedFile(filename=file_name, content=files[0].body)
            data = project.build_file_data(uploaded_file, file_tree.id, uid=project.uid)
            flow_task = await create_flow_task(get_config("client.name"))
            allow_duplicated_name = get_config("web.allow_same_name_file_in_project", True)
            db_service = PeeweeService.create()
            file = await flow_task.create(
                data,
                uploaded_file,
                using_pdfinsight_cache=True,
                allow_duplicated_name=allow_duplicated_name,
                db_service=db_service,
            )
            enable_ocr = await db_service.molds.verify_enable_ocr(
                file.molds, (get_config("web.force_ocr_mold_list") or [])
            )
            await flow_task.parse_file(file, enable_orc=enable_ocr, db_service=db_service)
        return self.data({})

    @Auth("browse")
    @use_kwargs({**args_schema, "path_type": fields.Str(load_default="File")}, location="query")
    async def delete(self, external_id: str, path_type: str):
        async with pw_db.atomic():
            if path_type == "Dir":
                project, file_tree, file_name = await get_project_and_file_tree_by_path(f"{external_id}/1.pdf")
                await file_tree.delete_()
            else:
                project, file_tree, file_name = await get_project_and_file_tree_by_path(external_id)
                file = await NewFile.find_by_kwargs(name=file_name, tree_id=file_tree.id, pid=project.id)
                if file:
                    await file.soft_delete()
                while True:
                    if file_tree.ptree_id == 0:
                        break
                    files = await NewFile.find_by_kwargs(tree_id=file_tree.id, delegate="all")
                    if files:
                        break
                    trees = await NewFileTree.find_by_kwargs(ptree_id=file_tree.id, delegate="all")
                    if trees:
                        break
                    await file_tree.delete_()
                    file_tree = await NewFileTree.find_by_id(file_tree.ptree_id)
        return self.data({})

    @Auth("browse")
    @peewee_transaction_wrapper
    async def get(self):
        files = await NewFile.find_by_kwargs(delegate="all")
        file_trees = {file_tree.id: file_tree for file_tree in await NewFileTree.find_by_kwargs(delegate="all")}
        res = []
        for file in files:
            tree_id = file.tree_id
            components = [file.name]
            while tree_id:
                file_tree = file_trees[tree_id]
                components.insert(0, file_tree.name)
                tree_id = file_tree.ptree_id

            res.append({"external_id": "/" + "/".join(components[1:])})
        return self.send_json(res)


@plugin.route(r"/tree-list")
class TreeListHandler(BaseHandler):
    args_schema = {
        "external_id": fields.Str(),
    }

    @Auth(["browse"])
    @use_kwargs({**args_schema}, location="query")
    async def get(self, external_id: str):
        project, file_tree, file_name = await get_project_and_file_tree_by_path(external_id)
        if project is None or file_tree is None:
            return self.error(_("path invalid"))
        file = await NewFile.find_by_kwargs(name=file_name, tree_id=file_tree.id, pid=project.id)
        if file is None:
            return self.error(_("path invalid"))
        trees = await NewFileTree.list_by_tree(file_tree.id)
        files = await NewFile.find_by_tree_id(file_tree.id)
        try:
            page = int(([_file.id for _file in files].index(file.id) + len(trees)) / 20) + 1
        except ValueError:
            page = 1
        return self.redirect(f"/#/project/{project.id}/tree/{file_tree.id}?file_id={file.id}&page={page}")
