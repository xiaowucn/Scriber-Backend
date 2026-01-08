import base64
import datetime
import email
import logging
import os
import socket
from dataclasses import dataclass
from email.header import decode_header
from pathlib import Path
from typing import Iterable, Self

from imapclient import IMAPClient, exceptions, version_info
from tornado.httputil import HTTPFile

from remarkable.common.constants import FeatureSchema
from remarkable.common.exceptions import CustomError
from remarkable.common.zip import decompression_files
from remarkable.service.cmfchina.email_model import CmfEmail, EmailUser
from remarkable.service.cmfchina.validator import CmfPostFileValidator
from remarkable.service.dcm_email.model import Attachment
from remarkable.service.new_file import html2pdf

logger = logging.getLogger(__name__)

CONTENT_TYPES = ["text/plain", "text/html"]


def custom_decode_header(header):
    # 解析邮件头
    res = ""
    for part, encoding in decode_header(header):
        if encoding:
            res += part.decode(encoding)
        else:
            res += part.decode("utf-8") if isinstance(part, bytes) else part
    return res or header


@dataclass
class IMAPEmailReceiver:
    host: str
    account: str
    password: str
    port: int | None = None
    ssl: bool = True
    timeout: int = 30
    _client: IMAPClient | None = None

    def __enter__(self) -> Self:
        self._client = IMAPClient(host=self.host, ssl=self.ssl, timeout=self.timeout)
        self._client.login(self.account, self.password)
        # 使用动态获取的版本信息发送 IMAP ID
        self._client.id_({"name": IMAPClient.__name__, "version": ".".join(map(str, version_info[:3]))})
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        self._client.__exit__(exc_type, exc_val, exc_tb)
        self._client = None

    def parse_subject(self, email_message) -> str:
        # 解析邮件主题
        subject = email_message.get("Subject", "无主题")
        decoded_subject = decode_header(subject)
        final_subject = "".join(
            part.decode(encoding) if isinstance(part, bytes) else part for part, encoding in decoded_subject
        )
        return final_subject

    def parse_sent_at(self, email_message):
        # 解析邮件发送时间
        date_str = email_message.get("Date")
        send_at = None
        # 将日期字符串转换为datetime对象
        if date_str:
            date_tuple = email.utils.parsedate_tz(date_str)
            if date_tuple:
                # 转换为本地时区的datetime对象
                local_date = email.utils.mktime_tz(date_tuple)
                send_at = datetime.datetime.fromtimestamp(local_date)
        return send_at

    def parse_email_addresses(self, addresses) -> EmailUser:
        if not addresses:
            return EmailUser(addresses=[])
        # 处理多个地址的情况
        # 解析地址
        parsed = email.utils.getaddresses([addresses])
        if not parsed:
            return (None, None)

        display_name, addr = parsed[0]

        # 解码显示名称
        if display_name:
            try:
                decoded_parts = decode_header(display_name)
                display_name = "".join(
                    part.decode(charset) if charset else part.decode("utf-8", errors="replace")
                    for part, charset in decoded_parts
                )
            except Exception:
                display_name = display_name  # 如果解码失败，保持原样
        return EmailUser(addresses=[addr])

    def check_attachment(self, filename, data):
        try:
            CmfPostFileValidator.check_suffix(HTTPFile(filename=filename, body=data))
        except:  # noqa
            logger.warning(f"account<{self.account}> file:{filename}: suffix not supported")
            return None
        return Attachment(filename=filename, data=data)

    def download_attachments(self, data, filename):
        attachments = []
        suffix = os.path.splitext(filename)[1].lower()
        if suffix in FeatureSchema.from_config().supported_zip_suffixes:
            file_path = Path(filename)
            file_path.write_bytes(data)
            for file in decompression_files(
                file_path=file_path,
                action="cmf_email",
                support_filetype_suffixes=FeatureSchema.from_config().supported_suffixes,
            ):
                if attachment := self.check_attachment(file.name, file.export_file.read_bytes()):
                    attachments.append(attachment)
            file_path.unlink(missing_ok=True)
        else:
            if attachment := self.check_attachment(filename, data):
                attachments.append(attachment)
        return attachments

    @staticmethod
    async def convert_email_body_to_pdf(email_body: str) -> bytes:
        """
        使用 Playwright 将邮件正文转换为 PDF
        :param email_body: 邮件正文（HTML 或纯文本）
        """
        try:
            convert_html = f"""
            <!DOCTYPE html>
            <html>
                <head>
                    <meta charset="utf-8">
                    <style>
                        body {{
                            font-family: Arial, sans-serif;
                            line-height: 1.6;
                            margin: 20px;
                        }}
                        .text-container {{
                        word-wrap: break-word;
                        word-break: break-all;
                        white-space: normal;
                        }}
                    </style>
                </head>
                <body>
                <div class="text-container">{email_body}<div>
                </body>
            </html>
            """

            # 使用 Playwright 渲染并生成 PDF
            content = await html2pdf(convert_html)
            return content
        except Exception as e:
            logger.error(f"Error converting email to PDF: {e}")
        return b""

    def extract_all_resources(self, email_message):
        """提取所有资源（包括非标准Content-Type的图片）"""
        resources = {"images": {}, CONTENT_TYPES[0]: None, CONTENT_TYPES[1]: None, "attachments": []}

        def is_image_part(part):
            """判断是否是图片部分"""
            content_type = part.get_content_type().lower()
            filename = part.get_filename() or ""

            # 检查标准图片类型或带有图片扩展名的文件
            return (
                content_type.startswith("image/") or content_type == "application/octet-stream"
            ) or filename.lower().endswith((".png", ".jpg", ".jpeg", ".gif", ".bmp"))

        def process_part(part):
            content_type = part.get_content_type().lower()
            content_disposition = str(part.get("Content-Disposition", "")).lower()
            cid = (part.get("Content-ID", "") or "").strip("<>")
            filename = part.get_filename()

            try:
                payload = part.get_payload(decode=True)
                if payload is None:
                    return

                if content_type in CONTENT_TYPES:
                    try:
                        part_charset = part.get_content_charset() or "utf-8"
                        body_bytes = part.get_payload(decode=True)
                        resources[content_type] = body_bytes.decode(part_charset, errors="replace") + "\n"
                    except Exception as e:
                        logger.warning(f"account<{self.account}>: Error parsing body. Error: {e}")

                # 处理图片资源（包括非标准Content-Type但有图片扩展名的）
                if is_image_part(part):
                    # 确定正确的Content-Type
                    actual_content_type = content_type
                    if filename.lower().endswith(".png"):
                        actual_content_type = "image/png"
                    elif filename.lower().endswith((".jpg", ".jpeg")):
                        actual_content_type = "image/jpeg"
                    elif filename.lower().endswith(".gif"):
                        actual_content_type = "image/gif"
                    elif filename.lower().endswith(".bmp"):
                        actual_content_type = "image/bmp"

                    if cid or "inline" in content_disposition or not filename:
                        base64_data = base64.b64encode(payload).decode("ascii")
                        data_uri = f"data:{actual_content_type};base64,{base64_data}"
                        key = cid if cid else f"img_{len(resources['images'])}"
                        resources["images"][key] = data_uri
                    else:
                        filename = custom_decode_header(filename)
                        resources["attachments"].extend(self.download_attachments(payload, filename))
                    return

                # 处理其他附件
                if filename or "attachment" in content_disposition:
                    filename = custom_decode_header(filename)
                    resources["attachments"].extend(self.download_attachments(payload, filename))

            except Exception as e:
                logger.error(f"account<{self.account}>: Error processing part. Error: {e}")

        # 遍历邮件所有部分
        if email_message.is_multipart():
            for part in email_message.walk():
                process_part(part)
        else:
            process_part(email_message)
        return self.embed_images_in_html(resources)

    def embed_images_in_html(self, resources):
        if resources.get("images") and resources.get(CONTENT_TYPES[1]):
            for cid, data_uri in resources.get("images").items():
                resources[CONTENT_TYPES[1]] = resources.get(CONTENT_TYPES[1]).replace(f"cid:{cid}", data_uri)
        return resources

    async def email_iter(self, receive_date=datetime.datetime.now(datetime.UTC)) -> Iterable[CmfEmail]:
        # 格式化IMAP时间格式
        midnight = datetime.datetime.combine(receive_date, datetime.time.min)
        start_time = midnight.strftime("%d-%b-%Y")
        logger.info(f"Start sync {self.account} attachments")
        try:
            # 选择收件箱
            self._client.select_folder("INBOX", readonly=True)
            # 使用 SINCE 搜索从凌晨到当前时间的邮件
            messages = self._client.search(f"SINCE {start_time}")
            for email_id, data in self._client.fetch(messages, ["RFC822"]).items():
                # 解析邮件
                email_message = email.message_from_bytes(data[b"RFC822"])
                # 获取发件人
                from_addresses = self.parse_email_addresses(email_message.get("From"))
                # 获取收件人
                to_addresses = self.parse_email_addresses(email_message.get("To"))
                # 获取抄送人
                cc_addresses = self.parse_email_addresses(email_message.get("Cc"))

                # 获取发送时间
                sent_at = self.parse_sent_at(email_message)
                # 获取并解码主题
                email_subject = self.parse_subject(email_message)
                # 获取正文
                resources = self.extract_all_resources(email_message)
                pdf_body = await self.convert_email_body_to_pdf(
                    resources[CONTENT_TYPES[1]] or resources[CONTENT_TYPES[0]]
                )
                content_attachment = Attachment(filename=f"{email_subject}.pdf", data=pdf_body)

                # 获取附件
                if resources["attachments"] or content_attachment:
                    yield CmfEmail(
                        host=self.host,
                        account=self.account,
                        email_id=email_id,
                        attachments=resources["attachments"],
                        content_attachment=content_attachment,
                        sent_at=sent_at,
                        from_=from_addresses,
                        to=to_addresses,
                        cc=cc_addresses,
                        subject=email_subject,
                    )
        except Exception as e:
            logger.exception(str(e))
        logger.info(f"End sync {self.account} attachments")

    @staticmethod
    def verify(host, account, password):
        try:
            with IMAPEmailReceiver(host, account, password):
                pass
        except socket.gaierror as e:
            logger.error(f"Unable to resolve server address: {e}")
            raise CustomError("请检查服务器地址是否正确", errors=str(e)) from e
        except exceptions.LoginError as e:
            logger.error(f"Login failed: {e}")
            raise CustomError("输入的账号或密码错误", errors=str(e)) from e
        except exceptions.IMAPClientError as e:
            logger.error(f"IMAP operation failed: {e}")
            raise CustomError("IMAP操作失败", errors=str(e)) from e
        except Exception as e:
            logger.error(f"Unknown error: {e}")
            raise CustomError("未知错误", errors=str(e)) from e
