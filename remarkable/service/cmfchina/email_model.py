import dataclasses
import datetime
from email.headerregistry import Address

from remarkable.service.dcm_email.model import Attachment


@dataclasses.dataclass(frozen=True)
class EmailUser:
    addresses: list[Address]


@dataclasses.dataclass(frozen=True)
class CmfEmail:
    host: str
    account: str
    email_id: int
    attachments: list[Attachment]
    content_attachment: Attachment
    sent_at: datetime.datetime | None
    from_: EmailUser
    to: EmailUser
    cc: EmailUser
    subject: str
