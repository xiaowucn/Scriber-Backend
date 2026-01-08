from typing import TYPE_CHECKING

import aiofiles
import httpx
from utensils.util import httpx_client

from remarkable import config
from remarkable.common.async_redis_cache import redis_acache_with_lock
from remarkable.common.exceptions import CustomError

if TYPE_CHECKING:
    from remarkable.models.new_file import NewFile

_scriber_folder_id = None


def auth_chatdoc():
    return {"Authorization": f"Bearer {config.get_config('app.auth.chatdoc.api_key')}"}


def fix_ext(node):
    if ext := node.get("ext"):
        name = node["name"]
        if not name.endswith(ext):
            node["name"] = f"{name}{ext}"


def filter_and_transform_tree(node_list: list) -> list:
    """
    根据规则递归过滤和转换树形结构。

    规则:
    1. 附件 (node_type=5): 保留 doc_status == 300 的。
    2. 文档 (非4, 非5): 保留 doc_status 为 300 或 -40 的。
    3. 文件夹 (node_type=4): 如果过滤后仍有子节点，则保留。
    4. 转换: 为所有被保留的附件增加一个 'is_attachment': True 的标记。
    """
    filtered_list = []

    for node in node_list:
        # 1. 递归处理子节点
        children = node.get("children", [])
        filtered_children = []
        if children:
            filtered_children = filter_and_transform_tree(children)

        # 2. 判断当前节点是否应该被保留
        node_type = node.get("node_type")
        doc_status = node.get("doc_status")

        meets_own_criteria = False

        if node_type == 5:  # 附件
            if doc_status == 300:
                meets_own_criteria = True
        elif node_type == 4:
            node["is_folder"] = True
            meets_own_criteria = bool(filtered_children)
        else:
            node["is_file"] = True
            if doc_status == 300:
                meets_own_criteria = True
            elif doc_status == -40:
                node["is_empty"] = True
                meets_own_criteria = bool(filtered_children)

        # 最终决定：如果节点自身满足条件，或者它有后代被保留，则保留该节点
        if meets_own_criteria:
            # 3. 创建新节点并进行转换
            new_node = node.copy()
            new_node["children"] = filtered_children
            if not node.get("is_folder"):
                fix_ext(new_node)

            filtered_list.append(new_node)

    return filtered_list


@redis_acache_with_lock(
    expire_seconds=config.get_config("app.auth.chatdoc.public_api_cache_seconds", 3600), lock_timeout=10
)
async def public_laws():
    url = f"{config.get_config('app.auth.chatdoc.url')}{config.get_config('app.auth.chatdoc.public_api')}"
    async with httpx_client(
        headers=auth_chatdoc(), timeout=float(config.get_config("app.auth.chatdoc.timeout", 60))
    ) as client:
        response = await client.get(url)
        response.raise_for_status()
        public_tree = response.json()["data"]["children"]
        return filter_and_transform_tree(public_tree)


def mark_created_laws(tree, created_uniques):
    for node in tree:
        if not node.get("is_folder"):
            unique = node.get("upload_record_id")
            node["is_created"] = bool(unique and unique in created_uniques)

        children = node.get("children")
        if children:
            mark_created_laws(children, created_uniques)


async def upload_pdf_with_interdoc_to_chatdoc(file: "NewFile"):
    if not file.scenario_id:
        raise CustomError("missing scenario_id")
    if not file.pdfinsight:
        raise CustomError("pdfinsight is not available")

    async with aiofiles.open(file.pdf_path(abs_path=True), "rb") as pdf:
        pdf_content = await pdf.read()
    async with aiofiles.open(file.pdfinsight_path(abs_path=True), "rb") as f:
        interdoc = await f.read()

    files = {"file": (f"{file.name}.pdf", pdf_content), "interdoc": (f"{file.name}.interdoc.zip", interdoc)}
    url = f"{config.get_config('app.auth.chatdoc.url')}{config.get_config('app.auth.chatdoc.api_pdf_with_interdoc')}"
    async with httpx_client(timeout=float(config.get_config("app.auth.chatdoc.timeout", 60))) as client:
        rsp = await client.post(url, files=files, headers=auth_chatdoc())
        rsp.raise_for_status()
        return rsp.json()["data"]["id"]


async def is_document_parsed(chatdoc_unique):
    url = (
        f"{config.get_config('app.auth.chatdoc.url')}{config.get_config('app.auth.chatdoc.api_upload_record_info')}"
        % chatdoc_unique
    )
    async with httpx_client(timeout=float(config.get_config("app.auth.chatdoc.timeout", 60))) as client:
        rsp = await client.get(url, headers=auth_chatdoc())
        rsp.raise_for_status()
        status = rsp.json()["data"]["status"]
        return status >= 300 or status < 0


async def download_chatdoc_interdoc(chatdoc_unique):
    url = (
        f"{config.get_config('app.auth.chatdoc.url')}{config.get_config('app.auth.chatdoc.api_download_interdoc')}"
        % chatdoc_unique
    )
    async with httpx_client(timeout=float(config.get_config("app.auth.chatdoc.timeout", 60))) as client:
        rsp = await client.get(url, headers=auth_chatdoc())
        rsp.raise_for_status()
        return rsp.content


async def download_chatdoc_origin(chatdoc_unique):
    url = f"{config.get_config('app.auth.chatdoc.url')}{config.get_config('app.auth.chatdoc.api_download_origin')}"
    async with httpx_client(timeout=float(config.get_config("app.auth.chatdoc.timeout", 60))) as client:
        rsp = await client.post(
            url,
            headers=auth_chatdoc(),
            json={"upload_ids": [chatdoc_unique]},
        )
        rsp.raise_for_status()
        return rsp.content


async def get_answer_detail_trace(id, answer_text, answer_range):
    url = f"{config.get_config('app.auth.chatdoc.url')}{config.get_config('app.auth.chatdoc.api_detail_trace')}"
    async with httpx_client(timeout=float(config.get_config("app.auth.chatdoc.timeout", 60))) as client:
        rsp = await client.post(
            url,
            headers=auth_chatdoc(),
            json={"interaction_id": id, "selected_answer_text": answer_text, "selected_answer_range": answer_range},
        )
        rsp.raise_for_status()
        return rsp.json()["data"]


async def ask_chatdoc(chatdoc_unique, question):
    url = f"{config.get_config('app.auth.chatdoc.url')}{config.get_config('app.auth.chatdoc.ask_question_api')}"
    async with httpx_client(
        headers=auth_chatdoc(), timeout=float(config.get_config("app.auth.chatdoc.ai_timeout", 300))
    ) as client:
        response = await client.post(
            url,
            json={
                "question": question,
                "model": config.get_config("app.auth.chatdoc.model"),
                "upload_id": chatdoc_unique,
                "chain_of_thought": False,
                "deep_search_count": 3,
                "stream": False,
                "question_returning_retrieve_elements": True,
                "eager_trace_detail": True,
            },
        )
        response.raise_for_status()
        return response.json()["data"]


if __name__ == "__main__":
    import asyncio

    async def del_chatdoc(fid):
        url = f"{config.get_config('app.auth.chatdoc.url')}/api/cgs/external/knowledge/personal/file"
        async with httpx.AsyncClient(
            headers=auth_chatdoc(), verify=False, timeout=httpx.Timeout(timeout=30.0)
        ) as client:
            response = await client.request("DELETE", url, json={"file_id": fid})
            print(response.json())

    asyncio.run(download_chatdoc_interdoc("dd9074c0-3b91-497b-b5d0-5e62ab9fd4ae"))
