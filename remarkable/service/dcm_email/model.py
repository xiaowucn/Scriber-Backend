import dataclasses
import datetime
from email.headerregistry import Address


@dataclasses.dataclass(frozen=True)
class Attachment:
    filename: str
    data: bytes

    def __str__(self):
        return f"Attachment<{self.filename}>"


@dataclasses.dataclass(frozen=True)
class EmailUser:
    addresses: list[Address]


@dataclasses.dataclass(frozen=True)
class Email:
    sent_at: datetime.datetime
    from_: EmailUser
    to: EmailUser
    subject: str
    body: str
    attachments: list[Attachment]


def get_fake_email() -> Email:
    """
    Returns a fake email object with some dummy data.
    """

    body = "<p>芬兰有53个芬兰语不为单一官方语言的市镇。芬兰语和瑞典语都是芬兰的官方语言。根据芬兰《语言法》，如果一个市镇少数语言群体至少占人口的8％，或一种少数语言至少有3000名使用者，则官方会认定该市镇为双语市镇。如果少数语言群体的比例下降到8％以下，之前的双语市镇地位仍然存在。如果比例低于6％，则根据市镇议会的建议，市镇可以通过市政法令将双语市镇地位保留十年。因为少数语言至少有3000名使用者而成为双语市镇的城市包括芬兰首都赫尔辛基和芬蘭瑞典人的文化中心图尔库。在奥兰群岛，芬兰语几乎缺席日常生活，且《奥兰自治法》规定瑞典语为该自治区的唯一官方语言。33个市镇是芬兰语和瑞典语的双语市镇，其中15个市镇瑞典语人口占多数，18个市镇芬兰语人口占多数。</p>"

    sender = EmailUser(
        addresses=[
            Address("孙泽远", "sunzeyuan", "citics.com"),
        ]
    )
    receiver = EmailUser(
        addresses=[
            Address("孙泽近", "sunzejin", "citics.com"),
        ]
    )
    email = Email(
        subject="24中关0506-国寿安保sd02",
        from_=sender,
        to=receiver,
        sent_at=datetime.datetime.now(),
        body=body,
        attachments=[
            Attachment(filename="test1.pdf", data=b""),
            Attachment(filename="test2.png", data=b""),
        ],
    )
    return email
