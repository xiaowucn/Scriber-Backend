import json
import os
import shutil
import time
from functools import cached_property
from pathlib import Path

import zstandard as zstd

from remarkable import config, logger
from remarkable.common.multiprocess import run_by_batch
from remarkable.common.schema import attribute_id
from remarkable.common.storage import localstorage
from remarkable.config import get_config
from remarkable.pdfinsight.reader import PdfinsightReader
from remarkable.prompter.element import element_info
from remarkable.prompter.impl.v2 import AnswerPrompterV2


class PrompterBuilderBase:
    def __init__(self, schema_id: int, vid: int = 0):
        self.cache_path = Path(get_config("training_cache_dir"))
        self.schema_id = schema_id
        self.vid = vid
        self.prompter = None
        self.timestamp = 0

    @cached_property
    def training_data_root(self):
        dir_path = self.cache_path / str(self.schema_id) / str(self.vid or 0) / "matrix"
        dir_path.mkdir(parents=True, exist_ok=True)
        return dir_path

    @cached_property
    def elements_dump_dir(self):
        dir_path = self.cache_path / str(self.schema_id) / str(self.vid or 0) / "elements"
        dir_path.mkdir(parents=True, exist_ok=True)
        return dir_path


def save_file_elements(dst_dir: Path | str, fid: int, data):
    if isinstance(dst_dir, str):
        dst_dir = Path(dst_dir)
    cctx = zstd.ZstdCompressor()
    with open(dst_dir / f"{fid}.json.zst", "wb") as fp:
        fp.write(cctx.compress(json.dumps(data, ensure_ascii=False, indent=2).encode()))


def load_file_elements(path: Path | str):
    if isinstance(path, str):
        path = Path(path)
    dctx = zstd.ZstdDecompressor()
    return json.loads(dctx.decompress(path.read_bytes()).decode())


def load_file(dst_dir: str, file_id: int, pdfinsight_path: str, answer):
    timestamp = time.time()
    logger.info(f"start load file {file_id}")
    reader = PdfinsightReader(localstorage.mount(pdfinsight_path))

    _attr_mapping = {}
    for item in answer.get("userAnswer", {}).get("items", []):
        aid = attribute_id(json.loads(item["key"]))
        for item_data in item.get("data", []):
            for box in item_data.get("boxes", []):
                if not box["box"] or None in box["box"].values():
                    logger.error("box is None")
                    continue
                page = box["page"]
                outline = (
                    box["box"]["box_left"],
                    box["box"]["box_top"],
                    box["box"]["box_right"],
                    box["box"]["box_bottom"],
                )
                for _, element in reader.find_elements_by_outline(page, outline):
                    eidx = element.get("index")
                    _attr_mapping.setdefault(eidx, set()).add(aid)

    dict_data = {}
    for ele in reader.paragraphs + reader.tables + reader.page_headers:  # + reader.page_footers
        eidx = ele.get("index")
        dict_data[eidx] = element_info(eidx, ele, reader, _attr_mapping)

    save_file_elements(dst_dir, file_id, dict_data)

    logger.info(f"finish load file {file_id}, cost {(time.time() - timestamp):.2f}")


class AnswerPrompterBuilder(PrompterBuilderBase):
    def dump(self, apply=True):
        pass

    def clear(self):
        for path in (self.elements_dump_dir, self.training_data_root):
            if path.exists():
                shutil.rmtree(path, ignore_errors=True)
                path.mkdir(parents=True, exist_ok=True)

    def load(self):
        return AnswerPrompterV2(self.schema_id, self.vid)

    def update(self, mold_data, rows):
        """
        1. 读取训练集的 interdoc 文档，记录每个元素块的 `关键字` 和 `正/负例标记`
        2. 汇总生成每个 attr 的 ngrams （在 redis 中）
        注：读取过的文件会记录在 redis 中，不清空的话，不会重新读取已读过的内容
        """
        if not mold_data:
            logger.error("can't find mold")
            return False
        tasks = []
        for file_id, pdfinsight, answer in rows:
            pdfinsight_path = localstorage.get_path(pdfinsight)
            if not answer or not os.path.exists(pdfinsight_path):
                continue
            tasks.append((self.elements_dump_dir.as_posix(), file_id, pdfinsight_path, answer))
        logger.info(f"find {len(tasks)} documents to update")
        for _ in run_by_batch(load_file, tasks, workers=(config.get_config("prompter.workers") or 0)):
            pass
        return tasks
