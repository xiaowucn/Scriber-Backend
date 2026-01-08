import logging
import tempfile
from pathlib import Path

from utensils.archive_reader import detect_archive

from remarkable import config

logger = logging.getLogger(__name__)


def decompression_files(file_path: Path, action: str = "action", support_filetype_suffixes=(".pdf", ".doc", ".docx")):
    # 直接压缩包文件类型：.zip,.7z,.rar,.tar,.tgz,.tar.gz
    # support_filetype_suffixes 表示需要解压的文件类型后缀
    # action: 创建的文件夹作用，用于区分各个解压的文件不被重叠
    with tempfile.TemporaryDirectory(
        prefix=f"compressed_{action}_work_dir_", dir=config.get_config("web.tmp_dir")
    ) as temp_dir:
        try:
            archive = detect_archive(
                filepath=file_path,
                support_filetype_suffixes=support_filetype_suffixes,
            )
            files = archive.all_files_info()
            archive.export(files, Path(temp_dir))
        except Exception:
            logger.warning(f"Failed to decompress the file:<{file_path}>")
            return
        for file in files:
            yield file
