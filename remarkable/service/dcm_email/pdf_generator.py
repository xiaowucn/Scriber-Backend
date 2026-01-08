import typing

from weasyprint import HTML


def create_pdf(html_file: str | typing.TextIO, output):
    content = html_file if isinstance(html_file, str) else html_file.read()

    html = HTML(string=content)
    html.write_pdf(output)
