import logging

import numpy

from remarkable.db import pw_db
from remarkable.models.new_file import NewFile
from remarkable.pw_models.model import NewTimeRecord

logger = logging.getLogger(__name__)


def get_avg_parsing_time(stamp):
    avg_stamp = int(numpy.mean(stamp))
    if avg_stamp >= 60:
        return f"{avg_stamp // 60}分{avg_stamp % 60}秒"
    return f"{avg_stamp}秒"


async def stat_pdfinsight_time(start=None, end=None, mold=None, time_threshold=None):
    time_threshold = int(time_threshold)
    fids = set()
    if start and end:
        for i in range(int(start), int(end) + 1):
            fids.add(str(i))
    if mold:
        query = NewFile.select().where(NewFile.molds.contains(mold), NewFile.pdfinsight.is_null(False))
        files = await pw_db.execute(query)
        for file in files:
            fids.add(str(file.id))

    pdfinsight_time = []
    for fid in fids:
        time_record = await NewTimeRecord.find_by_fid(fid)
        file = await NewFile.find_by_id(fid)
        if not time_record or not file:
            continue
        if not file.created_utc or not time_record.insight_parse_stamp:
            continue

        process_time = time_record.insight_parse_stamp - file.created_utc
        if time_threshold and process_time > time_threshold:
            logging.info(f"超时文件:{fid}, {process_time}s")
            continue
        pdfinsight_time.append(process_time)
    if not pdfinsight_time:
        logging.info("文件总数为：0")
        return

    logging.info(f"文件总数为：{len(pdfinsight_time)}")
    logging.info(f"pdfinsight平均解析时间为: {get_avg_parsing_time(pdfinsight_time)}")


if __name__ == "__main__":
    import asyncio
    import sys

    start, end, mold, time_threshold = sys.argv[1:]
    asyncio.run(stat_pdfinsight_time(start, end, mold, int(time_threshold)))
