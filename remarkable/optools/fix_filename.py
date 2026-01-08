import logging
import sys

from utensils.zip import ZipFilePlus

from remarkable.common.util import loop_wrapper
from remarkable.db import db, peewee_transaction_wrapper


async def fetch_file(fid=None):
    sql = "select id, name from file"
    if fid is not None:
        sql += " where id=%(fid)s"
    return await db.raw_sql(sql, {"fid": fid})


async def update_filename(fid, filename):
    sql = "update file set name=%(name)s where id=%(id)s;"
    await db.raw_sql(sql, **{"id": fid, "name": filename})


@loop_wrapper
@peewee_transaction_wrapper
async def fix_filename(_fid=None):
    files = await fetch_file(_fid)
    for fid, name in files:
        fixname = ZipFilePlus.fix_encoding(name)
        logging.info(f"{fid}, {name}, {fixname}")
        if name != fixname:
            await update_filename(fid, fixname)


if __name__ == "__main__":
    FILE_ID = sys.argv[1] if len(sys.argv) > 1 else None
    fix_filename(FILE_ID)
