import datetime
import email.policy
import getpass
import poplib
from contextlib import contextmanager
from email import message_from_bytes
from email.message import EmailMessage

from bs4 import BeautifulSoup, Doctype

from remarkable.service.dcm_email.model import Attachment, Email, EmailUser


def get_body_contents(html):
    soup = BeautifulSoup(html, "html")
    for item in soup.contents:
        if isinstance(item, Doctype):
            item.extract()

    for attr in ["head", "html", "body"]:
        if attr == "head":
            if getattr(soup, attr):
                soup.head.extract()
            continue

        if getattr(soup, attr):
            getattr(soup, attr).unwrap()

    return soup.prettify()


class EmailReceiver:
    client = None

    def __init__(self, host, enable_ssl=True):
        client_cls = poplib.POP3_SSL if enable_ssl else poplib.POP3
        self.client = client_cls(host)

        self._context = None

        print(self.client.welcome.decode())

    @contextmanager
    def with_user(self, user_email, password):
        self._context = {
            "user_email": user_email,
            "password": password,
        }

        yield

        self._context = None

    @staticmethod
    def _get_body_html(message: "EmailMessage"):
        html_content = ""
        text_content = ""

        for part in message.walk():
            content_type = part.get_content_type()
            if content_type == "text/html":
                charset = part.get_content_charset() or "utf-8"
                html_content = part.get_payload(decode=True).decode(charset)
            if content_type == "text/plain":
                charset = part.get_content_charset() or "utf-8"
                text_content = part.get_payload(decode=True).decode(charset)

        result = html_content or text_content or ""
        if result:
            try:
                result = get_body_contents(result)
            except Exception:
                pass

        return result

    def get_available_emails(self, receive_date=datetime.datetime.now(datetime.UTC)) -> list[Email]:
        assert self._context is not None, "You must use this method within a `with_user` context"

        start_of_day = datetime.datetime.combine(receive_date, datetime.time.min, datetime.UTC)
        end_of_day = start_of_day + datetime.timedelta(hours=24)

        self.client.user(self._context["user_email"])
        self.client.pass_(self._context["password"])

        (num_msgs, total) = self.client.stat()

        emails = []

        for i in range(1, num_msgs + 1):
            (header, msg, octets) = self.client.retr(i)
            message = message_from_bytes(b"\n".join(msg), policy=email.policy.default)
            receive_at = message.get("Date").datetime.astimezone(datetime.UTC)
            if start_of_day <= receive_at < end_of_day:
                subject = str(message.get("Subject"))
                attachments = []
                for attachment in message.iter_attachments():
                    attachments.append(Attachment(filename=attachment.get_filename(), data=attachment.get_content()))

                body = self._get_body_html(message)
                sender = EmailUser(addresses=list(message.get("From").addresses))
                receiver = EmailUser(addresses=list(message.get("To").addresses))
                emails.append(
                    Email(
                        sent_at=receive_at,
                        from_=sender,
                        to=receiver,
                        subject=subject,
                        attachments=attachments,
                        body=body,
                    )
                )

        return emails


if __name__ == "__main__":
    service = EmailReceiver("pop.qq.com")
    mail_address = getpass.getpass("Email:")
    password = getpass.getpass()
    with service.with_user(mail_address, password):
        target_datetime = datetime.datetime.now(datetime.UTC) - datetime.timedelta(days=1)
        mails = service.get_available_emails(target_datetime)
        print(mails)
