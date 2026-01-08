"""Delete Table Data.

Usage:
  manipulate_table_data.py delete [--host=HOST] [--port=PORT] [--username=USERNAME] [--password=PASSWORD] [--database=DATABASE] <path>
  manipulate_table_data.py query [--host=HOST] [--port=PORT] [--username=USERNAME] [--password=PASSWORD] [--database=DATABASE] <table_name> <pkey>

Options:
  -h --help            show this help message and exit
  --host=HOST          MySQL host [default: 192.168.60.187]
  --port=PORT          MySQL port [default: 3306]
  --username=USERNAME  MySQL username [default: duguangting]
  --password=PASSWORD  MySQL password [default: 123456]
  --database=DATABASE  MySQL database [default: ipo]
"""

import logging
import os

import docopt
from sqlalchemy import create_engine
from sqlalchemy.engine.url import URL
from sqlalchemy.orm import sessionmaker

from remarkable.plugins.zjh.cli.tools import construct_url, query_file_info_by_file_name

logger = logging.getLogger()
logger.setLevel(logging.INFO)

db_session = None

table_cn_name = {
    "compliance": "合规性结果",
    "director_information": "董事基本情况",
    "major_lawsuit": "重大诉讼事项",
    "fund_raising": "募集资金与运用",
    "patent": "专利",
    "issuer_information": "发行人相关信息",
    "major_client": "主要客户",
    "major_supplier": "主要供应商",
    "major_contract": "重大合同",
    "issuer_profession": "发行人所处行业",
    "profitability": "盈利能力",
    "balance": "资产负债表",
    "cash_flow": "现金流量表",
    "income": "利润表",
    "main_financial_indicators": "主要财务指标表",
    "actual_controller_info": "实际控制人情况",
    "paraphrase": "释义",
    "controlling_shareholder_info": "控股股东情况",
    "supervisor_information": "监事基本情况",
    "management_information": "高管基本情况",
    "core_technician_info": "核心技术人员基本情况",
}


def delete_table_data(prospectus_md5):
    for key in table_cn_name:
        query = "DELETE FROM {} WHERE prospectus_md5 = :prospectus_md5;".format(key)
        db_session.execute(query, {"prospectus_md5": prospectus_md5})
    db_session.execute("DELETE FROM file WHERE prospectus_md5 = :prospectus_md5;", {"prospectus_md5": prospectus_md5})
    db_session.commit()


def init_db_session(host="192.168.60.187", port=3306, username="duguangting", password="123456", database="ipo"):
    global db_session
    dsn_url = URL(drivername="mysql", host=host, port=port, username=username, password=password, database=database)
    engine = create_engine(dsn_url, echo=False)
    DBSession = sessionmaker(engine, autocommit=False)
    db_session = DBSession()


def query_file_name(table_name, pkey):
    sql = """
        SELECT prospectus_name FROM file, {table_name}
        WHERE file.prospectus_md5 = {table_name}.prospectus_md5 AND {table_name}.pkey = :pkey
    """.format(table_name=table_name)
    fetch_res = db_session.execute(sql, {"pkey": pkey}).fetchone()
    return fetch_res[0]


def cli():
    args = docopt.docopt(__doc__)

    host = args["--host"]
    port = int(args["--port"])
    username = args["--username"]
    password = args["--password"]
    database = args["--database"]
    logging.info("Connect host: %s, port: %s, database: %s", host, port, database)
    init_db_session(host, port, username, password, database)
    if args["delete"]:
        path = args["<path>"]
        for _file in os.listdir(path):
            if _file.endswith("json"):
                name = _file.split(".", 1)[0]
                delete_table_data(name)
    elif args["query"]:
        file_name = query_file_name(args["<table_name>"], args["<pkey>"])
        query_res = query_file_info_by_file_name(file_name)
        logging.info(query_res)
        url = construct_url(query_res["file_id"], query_res["qid"])
        logging.info(url)


if __name__ == "__main__":
    cli()
