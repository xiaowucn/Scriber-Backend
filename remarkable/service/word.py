import logging

from remarkable.common.util import subprocess_exec
from remarkable.config import get_config
from remarkable.service.new_file import html2pdf

logger = logging.getLogger(__name__)


def word2pdf(in_path: str, out_path: str | None = None):
    # 除csc客户外，此方法废弃
    # 要支持word转pdf必须部署远程转码服务，scriber本地不再做支持
    command = f"mono {get_config('web.pdf_converter')} {in_path}"
    if out_path:
        command += f" {out_path}"
    subprocess_exec(command, timeout=360)


async def text2pdf(in_path, out_path):
    lines = [
        """<!DOCTYPE html>
<html>
<head>
<style>
  pre {
        white-space: pre-wrap;
    }
</style>
</head>
<body>"""
    ]
    with open(in_path) as txt_fp:
        for line in txt_fp:
            lines.append(f"<pre>{line}</pre>")
    lines.append("</body>\n</html>\n")
    pdf = await html2pdf("\n".join(lines))
    with open(out_path, "wb") as fp:
        fp.write(pdf)
    return out_path


def ppt2pdf(in_path, out_path):
    from unoserver.client import UnoClient

    client = UnoClient(
        server=get_config("unoserver.host"),
        port=int(get_config("unoserver.port")),
        host_location="remote",
    )
    client.convert(inpath=in_path, outpath=out_path, convert_to="pdf")
    logger.info("convert ppt to pdf done")
