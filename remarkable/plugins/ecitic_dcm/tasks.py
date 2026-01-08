import datetime
import io
import logging

import httpx

from remarkable.common.util import loop_wrapper
from remarkable.config import get_config
from remarkable.db import pw_db
from remarkable.models.ecitic_dcm import (
    DcmBondLimit,
    DcmBondOrder,
    DcmProject,
    DcmProjectFileProjectRef,
    DcmUnderWriteRate,
)
from remarkable.plugins.ecitic_dcm.service import DcmFileService, DcmProjectService, EmailPasswordCryptor
from remarkable.pw_models.model import NewFileProject, NewMold
from remarkable.service.dcm_email import Email, get_screenshot
from remarkable.service.dcm_email.email_receiver import EmailReceiver
from remarkable.service.new_file_project import NewFileProjectService
from remarkable.worker.app import app
from remarkable.worker.tasks import process_file

logger = logging.getLogger(__name__)


def get_dcmbk_url(name):
    rest_domain = get_config("citics_dcm.rest_domain")
    book_urls = get_config("citics_dcm.book_urls")
    return f"{rest_domain}{book_urls[name]}"


def get_today_date():
    date = datetime.datetime.today().strftime("%Y%m%d")
    return date


@app.task
@loop_wrapper
async def sync_dcmbk_project():
    url = get_dcmbk_url("project_today")
    date = get_today_date()
    logger.info(f"开始同步中信证券DCM簿记系统数据:{date}")
    projects = await DcmProject.find_by_kwargs(delegate="all", publish_start_date=date)
    project_ids = [p.project_id for p in projects]
    project_names = [p.project_name for p in projects]
    default_molds = await NewMold.tolerate_schema_ids("申购单")

    async with httpx.AsyncClient(verify=False, timeout=10, transport=httpx.AsyncHTTPTransport(retries=3)) as client:
        resp = await client.get(f"{url}?publishStartDate={date}")
        items = resp.json()
        items = [
            item
            for item in items
            if item["project_id"] not in project_ids and item["project_name"] not in project_names
        ]
        logger.info(f"新增项目:{[item['project_id'] for item in items]}")

    async with pw_db.atomic():
        dcm_project_ids = list(await DcmProject.bulk_insert(items, iter_ids=True))
        dcm_projects = await pw_db.execute(DcmProject.select().where(DcmProject.id << dcm_project_ids))
        for dcm_project in dcm_projects:
            project = await NewFileProjectService.create(
                name=f"{date}_{dcm_project.project_name}", default_molds=default_molds
            )
            await DcmProjectFileProjectRef.create(dcm_project_id=dcm_project.id, file_project_id=project.id)

    await sync_dcmbk_project_related_data()


async def sync_dcmbk_project_related_data():
    related_keys = [
        ("bond_order", DcmBondOrder, "orderapply_id"),
        ("bond_limit", DcmBondLimit, "limit_id"),
        ("bond_under_write_rate", DcmUnderWriteRate, "underwritegroup_id"),
    ]
    date = get_today_date()
    query = DcmProject.select(DcmProject.project_id).where(DcmProject.publish_start_date == date)
    project_ids = await pw_db.scalars(query)
    async with httpx.AsyncClient(verify=False, timeout=10, transport=httpx.AsyncHTTPTransport(retries=3)) as client:
        for project_id in project_ids:
            sync_items_map = {}
            for key, _, _ in related_keys:
                url = get_dcmbk_url(key)
                resp = await client.get(f"{url}?dcmbkProjectId={project_id}")
                sync_items_map[key] = resp.json()

            async with pw_db.atomic():
                for key, model, p_key in related_keys:
                    items = sync_items_map[key]
                    exist_items = await pw_db.execute(model.select().where(model.project_id == project_id).dicts())
                    exist_peks = [item[p_key] for item in exist_items]
                    items = [item for item in items if item[p_key] not in exist_peks]
                    logger.info(
                        f"新增{key}:{[item[p_key] for item in items]}",
                    )
                    await model.bulk_insert(items)


@app.task
@loop_wrapper
async def sync_data_from_email():
    date = get_today_date()
    logger.info(f"开始从中信证券DCM邮箱中同步数据:{date}")
    dcm_projects = await DcmProject.find_by_kwargs(delegate="all", publish_start_date=date)
    for dcm_project in dcm_projects:
        mails = await sync_data_from_email_by_project(dcm_project)
        # mail = get_fake_email()  # only for test
        # mails = [mail]
        project = await DcmProjectService.get_file_project_by_dcm_project_id(dcm_project.id)
        for mail in mails:  # TODO 如何去重
            await upload_file_from_mail(project, mail)


async def sync_data_from_email_by_project(dcm_project):
    email_host = dcm_project.email_host or get_config("citics_dcm.email_host")
    service = EmailReceiver(email_host)
    logger.info(f"开始同步项目:{dcm_project.project_name}")
    address = dcm_project.email_address
    password = EmailPasswordCryptor.decrypt(dcm_project.email_password)
    with service.with_user(address, password):
        target_datetime = datetime.datetime.now(datetime.UTC) - datetime.timedelta(days=1)
        mails = service.get_available_emails(target_datetime)
        return mails


async def upload_file_from_mail(project: NewFileProject, mail: Email):
    for attachment in mail.attachments:
        image = get_screenshot(mail, get_config("web.tmp_dir"))
        b_image = io.BytesIO()
        image.save(b_image, format="JPEG")
        file = await DcmFileService.create(
            mail=mail,
            image_bytes=b_image.getvalue(),  # 保存邮件截图
            name=attachment.filename,
            body=attachment.data,
            molds=[],
            pid=project.id,
            tree_id=project.rtree_id,
            uid=project.uid,
        )
        await process_file(file)


async def main():
    await sync_dcmbk_project()


if __name__ == "__main__":
    import asyncio

    asyncio.run(main())
