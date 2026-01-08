import ftplib
import logging
import os
import shutil
import uuid
from urllib.parse import urlparse

import requests
from sqlalchemy import Column, MetaData, String, Table, create_engine
from sqlalchemy.engine.url import URL
from sqlalchemy.orm import mapper, sessionmaker

from remarkable.common.util import name2driver
from remarkable.config import project_root
from remarkable.db import pw_db
from remarkable.models.new_file import NewFile
from remarkable.models.new_user import ADMIN
from remarkable.pw_models.model import NewFileTree
from remarkable.service.new_file import NewFileService
from remarkable.worker.tasks import process_file


class Performer:
    def __init__(self, config):
        self.config = config
        self.ext_db = self.create_ext_db_session()
        self.link_tbl = self.create_models()
        self.files = []
        self.dump_dir = os.path.join(project_root, "data", "sync_external_file", "".join(str(uuid.uuid4()).split("-")))
        self.tree_id = int(self.config["tree_id"][-1]) if self.config.get("tree_id") else 0
        self.agreement_map = {
            "ftp": FtpDownloader,
            "http": HttpDownloader,
            "https": HttpDownloader,
            "hdfs": HdfsDownloader,  # todo
            "smb": SmbDownloader,  # todo
        }
        try:
            os.makedirs(self.dump_dir)
        except FileExistsError:
            pass

    def create_ext_db_session(self):
        dsn_url = URL(
            drivername=name2driver(self.config.get("db_driver")),
            username=self.config.get("db_user"),
            password=self.config.get("db_password"),
            host=self.config.get("db_host"),
            port=self.config.get("db_port"),
            database=self.config.get("db_name"),
        )
        engine = create_engine(dsn_url, echo=True)
        session_maker = sessionmaker(engine)
        session = session_maker()
        return session

    def create_models(self):
        metadata = MetaData(bind=self.ext_db)
        link_table = Table(
            self.config["db_table"],
            metadata,
            Column(self.config["db_table_pk"], String, primary_key=True),
            Column(self.config["db_table_link"], String),
        )
        link_type = type(self.config["db_table"], (object,), {})
        mapper(link_type, link_table)
        return link_type

    def gen_downloader(self, link):
        res = urlparse(link)
        downloader = None
        if res.scheme in self.agreement_map:
            downloader = self.agreement_map[res.scheme]
        elif os.path.exists(link):  # 本地文件
            downloader = LocalFileDownloader
        return downloader

    async def download(self):
        """
        下载上游文档
        """
        for row in self.ext_db.query(self.link_tbl).all():
            logging.debug("fetch record from upstream: %s", row.__dict__)
            link = getattr(row, self.config["db_table_link"], None)
            doc_id = getattr(row, self.config["db_table_pk"], None)
            if not link or not doc_id:
                logging.error(
                    f"missing {self.config['db_table_pk']} or "
                    f"{self.config['db_table_link']} in record ({doc_id}, {link})"
                )
                continue
            clz = self.gen_downloader(link)
            if not clz:
                logging.error(f"can't support such agreement {link}")
                continue
            _, file_name = os.path.split(link)
            file_path = os.path.join(self.dump_dir, "".join(str(uuid.uuid4()).split("-")))
            logging.info(f">>>>>>>>  {link}")
            file_ = await NewFile.find_by_kwargs(
                **{
                    "link": link,
                    "mold": self.config.get("schema_id"),
                    "tree_id": self.tree_id,
                }
            )
            if row:
                logging.info(f"file {link} exists {file_}, pass")
                continue
            try:
                downloader = clz(link, file_path)
                logging.info(f"downloading {link} > {file_path}")
                downloader.download()
                self.files.append(
                    {
                        "id": doc_id,
                        "link": link,
                        "path": file_path,
                        "name": file_name,
                    }
                )
            except Exception as exp:
                logging.error(f"error in download file({doc_id}, {link})")
                logging.exception(exp)
                continue

    async def upload(self):
        """
        上传到scriber
        """
        for file_info in self.files:
            try:
                logging.info("upload file to scriber: %s", file_info)
                with open(file_info["path"], "rb") as file_obj:
                    data = file_obj.read()
                file = await create_file(
                    file_info["name"],
                    data,
                    self.config["tree_id"],
                    mold=self.config["schema_id"],
                    link=file_info["link"],
                )
                await process_file(file)
            except Exception as exp:
                logging.error(f"error in upload file({file_info['doc_id']}, {file_info['link']})")
                logging.exception(exp)

    def __del__(self):
        logging.info("clear external_file cache in  %s ...", self.dump_dir)
        if os.path.exists(self.dump_dir):
            shutil.rmtree(self.dump_dir)


async def create_file(filename, data, tree_id, **kwargs):
    from remarkable.pw_models.model import NewFileProject

    async with pw_db.atomic():
        _tree = await NewFileTree.find_by_id(tree_id)
        assert _tree, "tree_id %s is not exist" % tree_id
        _project = await NewFileProject.find_by_id(_tree.pid)
        mold = kwargs.get("schema_id")
        if mold:
            molds = [mold]
        else:
            molds = await NewFileTree.find_default_molds(_tree.id)

        params = {
            "name": filename,
            "body": data,
            "molds": molds,
            "pid": _project.id,
            "tree_id": _tree.id,
            "uid": kwargs.get("uid", ADMIN.id),
            "link": kwargs.get("link", ""),
        }
        file = await NewFileService.create_file(**params)
        return file


class Downloader:
    def __init__(self, link, file_path):
        self.link = link
        self.file_path = file_path

    def download(self):
        raise NotImplementedError


class LocalFileDownloader(Downloader):
    def download(self):
        shutil.copyfile(self.link, self.file_path)


class HttpDownloader(Downloader):
    def download(self):
        resp = requests.get(self.link, timeout=30)
        if resp.status_code != 200:
            raise Exception(f"link {self.link} returns {resp.status_code}")
        with open(self.file_path, "wb") as pdf_fp:
            pdf_fp.write(resp.content)


class FtpDownloader(Downloader):
    def __init__(self, link, file_path):
        super().__init__(link, file_path)
        res = urlparse(link)
        self.ftp = ftplib.FTP()
        self.ftp.connect(res.hostname, res.port)
        self.ftp.login(res.username, res.password)

    def download(self):
        with open(self.file_path, "wb") as file_handler:
            self.ftp.retrbinary("RETR " + os.path.basename(self.link), file_handler.write)

    def __del__(self):
        self.ftp.quit()


class HdfsDownloader(Downloader):
    def download(self):
        pass


class SmbDownloader(Downloader):
    def download(self):
        pass
