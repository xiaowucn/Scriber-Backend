from itertools import groupby
from operator import attrgetter

from peewee import fn

from remarkable.common.enums import AuditAnswerType, TaskType
from remarkable.db import pw_db
from remarkable.pw_models.law_judge import JudgeStatusEnum, LawJudgeResult
from remarkable.pw_models.model import NewAuditStatus
from remarkable.schema.cgs.rules import AuditStatusType


async def fill_files_status(files):
    file_ids_with_scenario = {file["id"]: idx for idx, file in enumerate(files) if file.get("scenario")}
    if file_ids_with_scenario:
        judge_status_query = (
            LawJudgeResult.select(
                LawJudgeResult.file_id,
                LawJudgeResult.judge_status,
                fn.COUNT(LawJudgeResult.judge_status).alias("count"),
            )
            .where(LawJudgeResult.file_id.in_(list(file_ids_with_scenario)))
            .group_by(LawJudgeResult.file_id, LawJudgeResult.judge_status)
            .order_by(LawJudgeResult.file_id)
        )
        judge_status = await pw_db.execute(judge_status_query)
        file_status_info = {}
        for file_id, status in groupby(judge_status, attrgetter("file_id")):
            counter = {}
            for result in status:
                counter[result.judge_status] = result.count
            file_status_info[file_id] = {
                "judge_status_count": counter,
                "judge_status": LawJudgeResult.display_status_by_counter(counter),
            }
        for file_id, idx in file_ids_with_scenario.items():
            files[idx].update(file_status_info.get(file_id, {"judge_status": JudgeStatusEnum.TODO}))

    file_ids = {file["id"]: idx for idx, file in enumerate(files) if file["task_type"] == TaskType.AUDIT.value}
    if file_ids:
        cte = (
            NewAuditStatus.select(
                NewAuditStatus.fid,
                NewAuditStatus.status,
                fn.ROW_NUMBER()
                .over(partition_by=[NewAuditStatus.fid], order_by=[NewAuditStatus.id.desc()])
                .alias("rnk"),
            )
            .where(
                (NewAuditStatus.fid.in_(list(file_ids))) & (NewAuditStatus.answer_type == AuditAnswerType.final_answer)
            )
            .cte("audit_subq")
        )
        audit_query = cte.select_from(cte.c.fid, cte.c.status).where(cte.c.rnk == 1).with_cte(cte)
        audit_status_map = dict(await pw_db.execute(audit_query.tuples()))
        for file_id, idx in file_ids.items():
            files[idx]["audit_status"] = audit_status_map.get(file_id, AuditStatusType.TODO.value)
