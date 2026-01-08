import logging

import httpx

from remarkable.config import get_config
from remarkable.db import pw_db
from remarkable.models.ecitic import EciticPush, EciticTemplate
from remarkable.pw_models.model import NewFileProject

logger = logging.getLogger(__name__)


async def send_email_to_ecitic_tg(subject, content, address):
    url = get_config("citics.email_url")
    sender = get_config("citics.email_sender")

    data = {
        "sender": sender,
        "address": address,
        "subject": subject,
        "content": content,
    }
    async with httpx.AsyncClient(timeout=30, transport=httpx.AsyncHTTPTransport(verify=False, retries=3)) as client:
        try:
            resp = await client.post(url, json=data)
        except Exception as exp:
            logger.exception(exp)
        else:
            logger.info(f"send email {content}, {resp.text})")


async def send_fail_email_to_ecitic_tg(file, fail_msg):
    website = get_config("citics.website")
    project = await NewFileProject.find_by_id(file.pid)
    subject = f"【{project.name}】《{file.name}》{fail_msg}，请登录【中信中证参数提取与稽核】系统进行查看"
    content = f"【{project.name}】《{file.name}》{fail_msg}，请登录【中信中证参数提取与稽核】({website})系统进行查看"
    templates_query = EciticTemplate.select().where(EciticTemplate.id.in_((file.meta_info or {}).get("templates", [])))
    templates = await pw_db.execute(templates_query)
    for template in templates:
        push_query = EciticPush.select().where(EciticPush.template == template.id)
        push_configs = await pw_db.execute(push_query)
        for push_config in push_configs:
            await send_email_to_ecitic_tg(subject, content, push_config.email)
