import json
import logging
from importlib import import_module

from remarkable.common.enums import AuditAnswerType, TaskType
from remarkable.config import get_config
from remarkable.db import pw_db
from remarkable.models.new_file import NewFile
from remarkable.pw_models.model import NewAuditStatus, NewMold
from remarkable.pw_models.question import NewQuestion
from remarkable.schema.cgs.rules import AuditStatusType

logger = logging.getLogger(__name__)


def create_inspector(file, mold, question):
    utils_module = import_module("remarkable.checker")
    pkg_name = get_config("inspector.package_name")

    inspector_package = utils_module.load_inspector_config(pkg_name)
    instance = utils_module.make_inspector_instance(inspector_package, file, mold, question)
    return instance


async def audit_file_rules(fid: int, labels: dict[str, int] = None, audit_preset_answer: bool = False) -> list:
    results = []
    file = await NewFile.find_by_id(fid)
    if not file or file.task_type != TaskType.AUDIT.value:
        return results
    inspect_fields = (file.meta_info or {}).get("inspect_fields")

    question = await NewQuestion.get_master_question(fid)
    mold = await NewMold.find_by_id(question.mold)
    audit_status = await pw_db.create(
        NewAuditStatus,
        fid=fid,
        schema_id=question.mold,
        status=AuditStatusType.PROCESS.value,
        answer_type=AuditAnswerType.final_answer,
    )
    try:
        logger.info(f"inspector.check for {file.id}")
        inspector = create_inspector(file, mold, question)
        if not await inspector.ready_to_check():
            logger.info("inspector not ready")
            return results

        context = await inspector.build_context()
        results = await inspector.start_check(context, labels=labels, inspect_fields=inspect_fields)

        await audit_status.set_status(AuditStatusType.DONE.value)
    except Exception as e:
        logger.exception(e)
        await audit_status.set_status(AuditStatusType.FAILED.value)

    if audit_preset_answer:
        preset_answer_status = await NewAuditStatus.create(
            fid=fid,
            schema_id=question.mold,
            status=AuditStatusType.PROCESS.value,
            answer_type=AuditAnswerType.preset_answer,
        )
        try:
            inspector = create_inspector(file, mold, question)
            context = await inspector.build_context_for_preset_answer()

            await inspector.start_check(context, labels=labels, inspect_fields=inspect_fields)
        except Exception as e:
            logger.exception(e)
            await preset_answer_status.set_status(AuditStatusType.DONE.value)

    return results


async def audit_file_rules_by_mold(
    fid: int, schema_id: int = None, labels: dict[str, int] = None, audit_preset_answer: bool = False
) -> list:
    results = []
    file = await NewFile.find_by_id(fid)
    if not file or file.task_type != TaskType.AUDIT.value:
        return results
    inspect_fields = (file.meta_info or {}).get("inspect_fields")
    conditions = [NewQuestion.fid == fid]
    if schema_id:
        conditions.append(NewQuestion.mold == schema_id)

    questions = await pw_db.execute(NewQuestion.select().where(*conditions))
    for question in questions:
        results.extend(await audit_file_rules_by_question(file, question, inspect_fields, labels, audit_preset_answer))
    return results


async def audit_file_rules_by_question(
    file: NewFile,
    question: NewQuestion,
    inspect_fields: dict[str, int] = None,
    labels: dict[str, int] = None,
    audit_preset_answer: bool = False,
) -> list:
    mold = await NewMold.find_by_id(question.mold)
    if not mold:
        logger.warning(f"mold not found, mid<{question.mold}>")
        return []
    audit_status = await pw_db.create(
        NewAuditStatus,
        fid=file.id,
        schema_id=mold.id,
        status=AuditStatusType.PROCESS.value,
        answer_type=AuditAnswerType.final_answer,
    )
    results = []
    try:
        logger.info(f"inspector.check for fid<{file.id}>, qid<{question.id}>")
        inspector = create_inspector(file, mold, question)
        if not await inspector.ready_to_check():
            logger.info("inspector not ready")
            return []

        context = await inspector.build_context()
        results = await inspector.start_check(context, labels=labels, inspect_fields=inspect_fields)

        await audit_status.set_status(AuditStatusType.DONE.value)
    except Exception as e:
        logger.exception(e)
        await audit_status.set_status(AuditStatusType.FAILED.value)

    if audit_preset_answer:
        preset_answer_status = await NewAuditStatus.create(
            fid=file.id,
            schema_id=question.mold,
            status=AuditStatusType.PROCESS.value,
            answer_type=AuditAnswerType.preset_answer,
        )
        try:
            inspector = create_inspector(file, mold, question)
            context = await inspector.build_context_for_preset_answer()

            await inspector.start_check(context, labels=labels, inspect_fields=inspect_fields)
        except Exception as e:
            logger.exception(e)
            await preset_answer_status.set_status(AuditStatusType.DONE.value)

    return results


async def main(fid):
    # labels = await get_updated_rule_labels(fid, 7, ['["私募-基金合同:0","基金名称:0"]'])
    labels = {"schema_474": 138820, "schema_439_2": 138811}
    labels = {}
    # results = await audit_file_rules(fid, labels=labels)
    # results = await audit_file_rules_by_mold(fid, schema_id=2, labels=labels)
    results = await audit_file_rules_by_mold(fid, labels=labels, audit_preset_answer=True)
    for item in results:
        print(json.dumps(item.to_dict(), indent=2, ensure_ascii=False))
        print(item.title)


if __name__ == "__main__":
    import asyncio

    asyncio.run(main(1699))
    # asyncio.run(main(1063))
