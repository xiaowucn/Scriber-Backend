import logging
import tempfile
from collections import defaultdict

from aipod.rpc.client import AIClient
from grpc.aio import AioRpcError
from tornado.httputil import HTTPFile

from remarkable import config
from remarkable.common.constants import ADMIN_ID, CmfFiledStatus
from remarkable.db import pw_db
from remarkable.models.cmf_china import CmfChinaEmailFileInfo, CmfFiledFileInfo, CmfFiledScript
from remarkable.models.new_file import NewFile
from remarkable.pdfinsight.reader import PdfinsightReader, PdfinsightTable
from remarkable.plugins.ext_api.common import is_table_elt
from remarkable.pw_models.model import NewFileProject, NewFileTree, NewMold
from remarkable.service.cmfchina.cmf_group import CMFGroupService
from remarkable.service.cmfchina.common import SAMPLE_CODE_FILE_NAME
from remarkable.service.new_file import NewFileService
from remarkable.service.new_file_tree import NewFileTreeService
from remarkable.service.predictor import is_paragraph_elt

logger = logging.getLogger(__name__)


class CmfFiledFileService:
    @staticmethod
    def convert(file: NewFile):
        interdoc = PdfinsightReader(file.pdfinsight_path(abs_path=True))
        ret = defaultdict(list)
        for page, elements in interdoc.element_dict.items():
            for element in sorted(elements, key=lambda x: x.data["index"]):
                ele = element.data
                if is_table_elt(ele):
                    cover_text = PdfinsightTable(ele).markdown
                    ret[page].append(cover_text)
                elif is_paragraph_elt(ele):
                    ret[page].append(ele["text"])
        return ret

    @staticmethod
    async def get_projects_molds():
        def gen_subprojects(trees, ptree_id):
            return [
                {"name": t.name, "pid": t.id, "subprojects": gen_subprojects(trees, t.id)}
                for t in trees[::-1]
                if t.ptree_id == ptree_id
            ]

        projects = list(
            await pw_db.execute(
                NewFileProject.select(NewFileProject.name, NewFileProject.id.alias("pid"), NewFileProject.rtree_id)
                .where(NewFileProject.visible)
                .dicts()
            )
        )
        rtree_ids = [p["rtree_id"] for p in projects]
        trees = await NewFileTreeService.get_all_child_trees(rtree_ids)
        for p in projects:
            rtree_id = p.pop("rtree_id")
            p["subprojects"] = []
            for t in trees[::-1]:
                if t.ptree_id == rtree_id:
                    p["subprojects"].append({"name": t.name, "pid": t.id, "subprojects": gen_subprojects(trees, t.id)})
                    trees.pop(trees.index(t))

        molds = list(await pw_db.execute(NewMold.select(NewMold.name, NewMold.id.alias("mid")).dicts()))
        return {"projects": projects, "schemas": molds}

    @classmethod
    async def exec_python(cls, file: NewFile, email_file_info: CmfChinaEmailFileInfo | None = None) -> dict:
        logger.info(f"start CmfChina filed file<{file.id}> with python")
        _, script = await cls.get_filed_code(False)
        ctx = await cls.get_projects_molds()
        if email_file_info:
            ctx["email"] = {
                "from": email_file_info.from_,
                "to": email_file_info.to,
                "cc": email_file_info.cc,
                "subject": email_file_info.subject,
                "sent_at": email_file_info.sent_at,
                "is_content": email_file_info.is_content,
            }

        if file.is_excel:
            ctx["excel"] = {"name": file.name}
        else:
            ctx["elements"] = cls.convert(file)
        ctx["file_name"] = file.name
        metadata = [("x-func-name", "exec"), ("x-upstream", "scriber-cmf-china")]
        with tempfile.TemporaryDirectory() as tmpdir:
            client = AIClient(
                version="python-runner",
                address=config.get_config("ai.py_runner_addr"),
                datapath=tmpdir,
            )
            try:
                data = await client.chaos(script, ctx=ctx, metadata=metadata)
                logger.info(f"end CmfChina filed file<{file.id}> with python")
                return data
            except AioRpcError as exp:
                logger.exception(exp)
                return {"error_info": exp.details()}
            except Exception as exp:
                logger.exception(exp)
                return {"error_info": str(exp)}

    @classmethod
    async def filed_file(cls, file):
        # 根据分类代码返回的数据，刷新文件的工程和场景
        logger.info(f"start filed file<{file.id}>")
        cmf_china_file_info = await pw_db.first(CmfFiledFileInfo.select().where(CmfFiledFileInfo.fid == file.id))
        if not cmf_china_file_info:
            logger.info(f"file:{file.id} not uploaded by the filed system")
            return
        if cmf_china_file_info.status != CmfFiledStatus.WAIT:
            logger.info(f"file:{file.id} filed in progress")
            return
        cmf_china_file_info.status = CmfFiledStatus.DOING
        await pw_db.update(cmf_china_file_info, only=["status"])
        email_file_info = await pw_db.first(CmfChinaEmailFileInfo.select().where(CmfChinaEmailFileInfo.fid == file.id))
        try:
            data = await cls.exec_python(file, email_file_info)
        except FileNotFoundError:
            data = {"error_info": "未找到分类代码文件"}
        async with pw_db.atomic():
            if data and not data.get("error_info"):
                pid, mid, sub_project_name = (
                    data.get("pid", None),
                    data.get("mid", None),
                    data.get("sub_project_name", None),
                )
                logger.info(
                    f"Start assign project for file:{file.id} to pid:<{pid}> mid:<{mid}> sub_name:<{sub_project_name}>"
                )
                if pid and mid:
                    project = await NewFileProject.get_by_id(pid)
                    mold = await NewMold.get_by_id(mid)
                    if not project or not mold:
                        msgs = []
                        if not project:
                            logger.error(f"project: {pid} not found")
                            msgs.append(f"项目ID{pid}")
                        if not mold:
                            logger.error(f"mold: {mid} not found")
                            msgs.append(f"场景ID{pid}")
                        cmf_china_file_info.status = CmfFiledStatus.FAIL
                        cmf_china_file_info.fail_info = f"分类的{'和'.join(msgs)}在系统中不存在"
                    else:
                        file_tree = await NewFileTree.find_by_id(project.rtree_id)
                        if email_file_info and sub_project_name:
                            # 从邮件中获取的文件，分类代码返回了子项目名
                            add_sub_project = False
                            if email_file_info.is_content:
                                # 判断有没有附件，没有的话，不需要创建子目录
                                if await pw_db.exists(
                                    CmfChinaEmailFileInfo.select().where(
                                        CmfChinaEmailFileInfo.host == email_file_info.host,
                                        CmfChinaEmailFileInfo.email_id == email_file_info.email_id,
                                        CmfChinaEmailFileInfo.account == email_file_info.account,
                                        ~CmfChinaEmailFileInfo.is_content,
                                    )
                                ):
                                    add_sub_project = True
                            else:
                                # 是附件，需要创建子目录
                                add_sub_project = True
                            if add_sub_project:
                                file_tree = await NewFileTreeService.get_or_create(
                                    tid=project.rtree_id,
                                    pid=project.id,
                                    name=sub_project_name,
                                    default_molds=[mid],
                                    uid=ADMIN_ID,
                                )
                                if not file_tree:
                                    cmf_china_file_info.fail_info = f"创建子目录{sub_project_name}失败"
                                    cmf_china_file_info.status = CmfFiledStatus.FAIL
                                else:
                                    await CMFGroupService.add_group_to_tree_from_rtree(file_tree.id, project.rtree_id)
                        if file_tree:
                            # 更新文件 Tree_id 和 mid，开始预测文件
                            file.pid = pid
                            file.tree_id = file_tree.id
                            await pw_db.update(file, only=["pid", "tree_id"])
                            await NewFileService.update_molds(file, [int(mid)])
                            cmf_china_file_info.status = CmfFiledStatus.DONE
                else:
                    cmf_china_file_info.status = CmfFiledStatus.FAIL
                    msgs = []
                    if not pid:
                        msgs.append("项目ID")
                    if not mid:
                        msgs.append("场景ID")
                    cmf_china_file_info.fail_info = f"分类的{'和'.join(msgs)}未返回"
                logger.info(f"End assign project for file:{file.id}")
            else:
                cmf_china_file_info.status = CmfFiledStatus.FAIL
                cmf_china_file_info.fail_info = data["error_info"]

            await pw_db.update(cmf_china_file_info, only=["status", "fail_info"])
        logger.info(f"end filed file<{file.id}>")

    @staticmethod
    async def verify_filed(file, mids, pid, mold_names, project_name):
        try:
            data = await CmfFiledFileService.exec_python(file)
            if data["mid"] not in mids or data["pid"] != pid:
                msg = f"应关联{'、'.join(mold_names)}场景、上传至{project_name}项目中，目前分类结果为"
                if verify_mold := await NewMold.get_by_id(data["mid"]):
                    msg = f"{msg}关联{verify_mold.name}场景"
                else:
                    msg = f"{msg}未匹配到场景"
                if verify_project := await NewFileProject.get_by_id(data["pid"]):
                    msg = f"{msg}，上传{verify_project.name}项目中"
                else:
                    msg = f"{msg}，未匹配到项目"
                return False, msg
            return True, "测试通过"
        except FileNotFoundError:
            return False, "未找到分类代码文件"
        except Exception as e:
            return False, str(e)

    @staticmethod
    async def save_filed_code(code_file: HTTPFile):
        filed_script = await pw_db.first(CmfFiledScript.select().order_by(CmfFiledScript.id.desc()))
        if filed_script:
            filed_script.filename = code_file.filename
            filed_script.context = code_file.body.decode("utf-8")
            await pw_db.update(filed_script, only=["filename", "context"])
        else:
            await pw_db.create(
                CmfFiledScript, **{"filename": code_file.filename, "context": code_file.body.decode("utf-8")}
            )

    @staticmethod
    async def get_filed_code(sample: bool):
        if sample:
            sample_code = """
# 输入数据说明：
# 1:excel文件, 将增加excel的相关数据,目前只有name字段
# 2:非excel文件,会有elements元素块相关数据
# {
#     "projects": [
#         {
#             "name": "交易确认单",
#             "pid": 1,
#             "subprojects": [
#                 {
#                     "name": "证券类交易确认单",
#                     "pid": 11,
#                     "subprojects": [],
#                 },
#                 {
#                     "name": "外汇类交易确认单",
#                     "pid": 12,
#                     "subprojects": [
#                         {
#                             "name": "即期外汇类交易确认单",
#                             "pid": 121,
#                             "subprojects": [],
#                         },
#                         {
#                             "name": "远期外汇类交易确认单",
#                             "pid": 122,
#                             "subprojects": [],
#                         },
#                     ],
#                 },
#             ],
#         },
#         {
#             "name": "估值表",
#             "pid": 2,
#             "subprojects": [
#                 {
#                     "name": "年度估值表",
#                     "pid": 21,
#                     "subprojects": [
#                         {
#                             "name": "保险资金估值表",
#                             "pid": 211,
#                             "subprojects": [],
#                         }
#                     ],
#                 },
#                 {
#                     "name": "月度估值表",
#                     "pid": 22,
#                     "subprojects": [],
#                 },
#             ],
#         },
#     ],
#     "schemas": [
#         {"name": "交易确认单", "mid": 1},
#         {"name": "估值表", "mid": 2},
#     ],
#     "excel": {
#         "name": "估值表.xlsx",
#     },
#     "elements": {
#         "0": [
#             "确认单_元素块文本信息_1",
#             "确认单_元素块文本信息_2",
#         ],
#         "1": [
#             "确认单_元素块文本信息_3",
#             "确认单_元素块文本信息_4",
#             "确认单_元素块文本信息_5",
#         ],
#     },
#     "email": {
#         "from": [
#             "from_address@xxx.com",
#         ],
#         "to": [
#             "to_address@xxx.com",
#         ],
#         "cc": [
#             "cc_address@xxx.com",
#         ],
#         "subject": "估值表邮件主题",
#         "sent_at": "1748327015000",
#         "is_content": True,
#     },
# }


def get_project_id(projects: list, keyword: str) -> int:
    # 通过名称获工程名称
    for project in projects:
        if keyword == project["name"]:
            return project["pid"]
    return 0


def get_schema_id(schemas: list, keyword: str) -> int:
    # 通过名称获场景名称
    for schema in schemas:
        if keyword == schema["name"]:
            return schema["mid"]
    return 0


def main(data: dict):
    # 初始化 返回值
    res = {"pid": 0, "mid": 0}
    if excel_name := data.get("excel", {}).get("name"):
        # 打印excel文件名
        print(excel_name)
        if "估值表" in excel_name:
            # 获取项目名称为 `估值表` 的项目ID
            pid = get_project_id(data["projects"], "估值表")
            # 获取场景名称为`估值表` 的场景ID
            mid = get_schema_id(data["schemas"], "估值表")
            res = {"pid": pid, "mid": mid}
    elif page_elements := data.get("elements"):
        # 循环查找文本
        for page, elements in page_elements.items():
            print(page)  # 打印元素块页码
            for text in elements:
                print(text)  # 打印元素块文本信息
                # 元素块 包含 `确认单`关键字时
                if "确认单" in text:
                    # 获取项目名称为 `交易确认单` 的项目ID
                    pid = get_project_id(data["projects"], "交易确认单")
                    # 获取场景名称为`交易确认单` 的场景ID
                    mid = get_schema_id(data["schemas"], "交易确认单")
                    res = {"pid": pid, "mid": mid}
                    break
    if email_data := data.get("email"):
        # 打印发件人
        for form in email_data.get("from", []):
            print(form)
        # 打印收件人
        for to in email_data.get("to", []):
            print(to)
        # 打印抄送人
        for cc in email_data.get("cc", []):
            print(cc)
        # 打印发送日期(时间戳)
        print(email_data["sent_at"])
        # 打印邮件主题
        print(email_data["subject"])
        # 打印是否是为正文文档，True:正文文档，False:附件文档
        print(email_data["is_content"])
        # 如果是从邮箱来的文件，判断是否需要在已经获得项目下创建子项目
        if "估值表" in email_data["subject"]:
            res.update({"sub_project_name": "每日估值表"})
    return res
            """
            return SAMPLE_CODE_FILE_NAME, sample_code.encode("utf-8")
        filed_script = await pw_db.first(CmfFiledScript.select())
        if not filed_script:
            raise FileNotFoundError
        return filed_script.filename, filed_script.context.encode("utf-8")
