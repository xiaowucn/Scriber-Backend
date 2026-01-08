import csv
import io

from remarkable.common.exceptions import CustomError
from remarkable.pw_models.audit_rule import NewAuditResult

CSV_HEADER = ["章节", "名称", "合规情况(人工判定)", "合规情况(AI判定)", "不合规原因", "修改意见"]


async def get_csv_data(results) -> list[list[str]]:
    if not results:
        raise CustomError(_("no data needs to export"), resp_status_code=404)

    csv_data = [CSV_HEADER]
    csv_data.extend([build_csv_row(result) for result in results])
    return csv_data


def build_csv_row(result: NewAuditResult) -> list[str]:
    # 章节, 名称, 人工确认合规结果, AI确认合规结果
    row = [result.title, result.name, result.is_compliance, result.is_compliance_ai]
    # 不合规原因
    reason = ";".join([reason["reason_text"] for reason in result.reasons if not reason["matched"]])
    row.append(reason)
    # 修改意见
    row.append(result.suggestion)
    return row


async def get_csv_bytes(results) -> bytes:
    csv_data = await get_csv_data(results)
    with io.StringIO() as csv_file:
        writer = csv.writer(csv_file)
        writer.writerows(csv_data)
        return csv_file.getvalue().encode()
