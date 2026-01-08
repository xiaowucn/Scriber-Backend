import os.path
import tempfile

from jinja2 import Environment, PackageLoader, select_autoescape
from pdfparser.pdftools.pdfium_util import PDFiumUtil
from PIL.Image import Image

from remarkable.service.dcm_email.model import Email, get_fake_email
from remarkable.service.dcm_email.pdf_generator import create_pdf

env = Environment(loader=PackageLoader("remarkable.service.dcm_email", "templates"), autoescape=select_autoescape())


def get_html(template: str, **kwargs):
    return env.from_string(template).render(**kwargs)


def get_screenshot(email: Email, tmp_dir: str) -> Image:
    template_text = env.get_template("email.html").render(email=email)
    with tempfile.TemporaryDirectory(dir=tmp_dir) as tmp_dir:
        email_pdf = os.path.join(tmp_dir, "email.pdf")
        create_pdf(template_text, output=email_pdf)
        return PDFiumUtil.get_page_bitmap(email_pdf, 0)


if __name__ == "__main__":
    email = get_fake_email()

    img = get_screenshot(email, "/tmp")
    img.save("/tmp/邮件截图.png")
