import asyncio

import openpyxl

from remarkable.common.util import dump_data_to_worksheet
from remarkable.db import peewee_transaction_wrapper
from remarkable.pw_models.audit_rule import NewAuditResult



async def export():
    fid = 1015
    schema_id = 7
    data = []
    results = await NewAuditResult.get_results_by_fid(fid=fid, schema_id=schema_id)
    for result in results:
        if result.rule_id or not result.schema_fields:
            continue
        data.append({"name": result.name, "schema_fields": "、".join(result.schema_fields)})

    headers = ["name", "schema_fields"]
    workbook = openpyxl.Workbook()
    worksheet = workbook.create_sheet(index=0)
    dump_data_to_worksheet(workbook, headers, data, worksheet=worksheet)
    workbook.save("export_rule.xlsx")

    return


if __name__ == "__main__":
    asyncio.run(export())
