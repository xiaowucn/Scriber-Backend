import collections
import logging
import time
from urllib.parse import quote

import requests
from invoke import task
from utensils.syncer import sync


@task
def rm_answer(ctx, qid, uid):
    """
    删除指定用户在该question上的标注答案
    :param ctx:
    :param qid:
    :param uid:
    :return:
    """
    from remarkable.common.util import loop_wrapper
    from remarkable.models.new_user import NewAdminUser
    from remarkable.pw_models.model import NewAnswer
    from remarkable.pw_models.question import NewQuestion
    from remarkable.service.new_question import NewQuestionService

    @loop_wrapper
    async def run():
        user = await NewAdminUser.find_by_id(uid)
        answer = await NewAnswer.find_by_kwargs(qid=qid, uid=uid)
        question = await NewQuestion.find_by_id(qid)
        if not answer:
            logging.info(f"answer not found, qid: {qid}, uid: {uid}")
            return
        if not user:
            logging.info(f"user not found, uid: {uid}")
            return
        if not question:
            logging.info(f"question not found, qid: {qid}")
            return

        await answer.delete()
        logging.info(f"delete answer data, qid: {qid}, uid: {uid}")

        await NewQuestionService.update_markers(question)
        logging.info("update mark_uids and mark_users")

        await NewQuestion.update_by_pk(qid, **{"health": question.health + 1})
        logging.info(f"update question health to {question.health + 1}")

        await question.set_answer()
        logging.info("done!")

    run()


def get_stock_info(query):
    """从新浪财经行情中心查询上/深交所上市公司股票简称/代码
    via: http://vip.stock.finance.sina.com.cn/
    """
    stock_item = collections.namedtuple("StockItem", ["name", "code"])
    headers = {
        "Cache-Control": "no-cache",
        "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) Chrome/89.0.4389.90 Edg/89.0.774.63",
        "Referer": "http://vip.stock.finance.sina.com.cn/",
    }
    name = f"suggestdata_{int(time.time())}000"
    # 沪深type: 11,12,13,14,15
    rsp = requests.get(
        f"http://suggest3.sinajs.cn/suggest/type=11,12,13,14,15&key={quote(query)}&name={name}",
        headers=headers,
        verify=False,
    )
    if rsp.status_code != 200:
        return None
    first_item = rsp.text[rsp.text.find('"') : -1].strip('"').split(";")[0]
    if not first_item:
        return None
    _, _, stock_code, _, stock_name, *_ = first_item.split(",")
    return stock_item(stock_name, stock_code)


@task(iterable=["default_molds"])
@sync
async def create_or_update_project(ctx, name, default_molds=None, public=True):
    """
    :param name:
    :param default_molds:
    :param public:
    :return:
    """
    from remarkable import logger
    from remarkable.models.new_user import ADMIN
    from remarkable.pw_models.model import NewFileProject
    from remarkable.service.new_file_project import NewFileProjectService

    default_molds = [int(m) for m in default_molds if m.strip().isdigit()]
    if project := await NewFileProject.find_by_kwargs(name=name):
        logger.warning(f"{project.id=}, {project.name} already exists, will update it")
        return await project.update_(default_molds=default_molds or project.default_molds, public=public)

    project = await NewFileProjectService.create(name, default_molds, uid=ADMIN.id, public=public)
    logger.info(f"{project.id=}, rtree_id:{project.rtree_id=} created")


@task
def create_tree(ctx, ptree_id, name, default_molds=None):
    """
    新建目录
    :param ctx:
    :param ptree_id: 所属项目的tree_id
    :param name:
    :param default_molds:
    :return:
    """
    from remarkable.common.exceptions import CustomError
    from remarkable.common.util import loop_wrapper
    from remarkable.models.new_user import ADMIN
    from remarkable.pw_models.model import NewFileProject, NewFileTree
    from remarkable.service.new_file_tree import NewFileTreeService

    @loop_wrapper
    async def run():
        tree = await NewFileTree.find_by_id(ptree_id)
        if not tree:
            raise CustomError("can't find the tree")

        project = await NewFileProject.find_by_id(tree.pid)
        if not project:
            raise CustomError("can't find the project")

        exists = await NewFileTreeService.exist(ptree_id, name)
        if exists:
            raise CustomError(_("Tree name is existed"))

        tree_default_molds = await NewFileTree.find_default_molds(ptree_id)
        new_tree = await NewFileTree.create(
            **{
                "ptree_id": tree.id,
                "pid": project.id,
                "name": name,
                "uid": ADMIN.id,
                "default_molds": default_molds or tree_default_molds,
            },
        )
        print(f"new_tree:{new_tree.id}")

    run()


@task
def release_redis_lock(ctx):
    """清除redis锁"""
    from remarkable.common.util import release_lock_keys

    release_lock_keys()
