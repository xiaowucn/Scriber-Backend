"""Tools for zjh

Usage:
  tools.py query [-u] [--file_id=FILE_ID] [--file_name=FILE_NAME]

Options:
  -h --help            show this help message and exit
  --file_id=FILE_ID    query file info by file_id
  --file_name=FILE_NAME  query file info by file_name
"""

import json
import logging
import os

import docopt

from remarkable.config import project_root

logger = logging.getLogger()
logger.setLevel(logging.INFO)

base_url = "http://xa.cheftin.com:1555/index.html#/project/question/{qid}?treeId=7&fileId={fid}&schemaId=4"
file_info_path = os.path.join(project_root, "data/zjh/file-info-map.json")
file_info_map = json.load(open(file_info_path, encoding="utf-8"))


def query_file_info_by_file_id(file_id):
    return file_info_map["data"][file_info_map["file_id_map"][file_id]]


def query_file_info_by_file_name(file_name):
    return file_info_map["data"][file_info_map["filename_map"][file_name]]


def construct_url(file_id, qid):
    return base_url.format(qid=qid, fid=file_id)


def cli():
    args = docopt.docopt(__doc__)
    if args["query"]:
        if args["--file_id"]:
            query_res = query_file_info_by_file_id(args["--file_id"])
        elif args["--file_name"]:
            query_res = query_file_info_by_file_name(args["--file_name"])
        else:
            return
        logging.info(query_res)
        if args["-u"]:
            url = construct_url(query_res["file_id"], query_res["qid"])
            logging.info(url)


if __name__ == "__main__":
    cli()
