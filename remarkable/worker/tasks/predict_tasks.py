"""
异步预测任务
"""

import json
import logging
import os
from itertools import groupby
from operator import attrgetter

import celery
from utensils.syncer import sync

from remarkable import config
from remarkable.common.constants import (
    AIStatus,
    MoldType,
    PDFParseStatus,
)
from remarkable.common.enums import ClientName
from remarkable.common.exceptions import InvalidInterdocError, PDFInsightNotFound
from remarkable.common.util import loop_wrapper
from remarkable.db import peewee_transaction_wrapper, pw_db
from remarkable.models.cmf_china import CmfMoldModelRef
from remarkable.models.model_version import ModelVersionWithFK
from remarkable.models.new_file import NewFile
from remarkable.predictor.predict import predict_answer
from remarkable.pw_models.law import LawCheckPoint
from remarkable.pw_models.law_judge import JudgeStatusEnum, LawJudgeResult
from remarkable.pw_models.model import MoldWithFK, NewTimeRecord
from remarkable.pw_models.question import NewQuestion, QuestionWithFK
from remarkable.service.law import judge_file_law_rule, judge_file_law_templates
from remarkable.service.law_chatdoc import is_document_parsed, upload_pdf_with_interdoc_to_chatdoc
from remarkable.service.new_file import NewFileService
from remarkable.service.new_question import NewQuestionService
from remarkable.service.prompter import (
    predict_crude_answer_by_range,
    predict_crude_answer_delegate,
)
from remarkable.service.statistics import save_stat_result
from remarkable.worker.app import app
from remarkable.worker.tasks.studio_tasks import re_extract_answer_by_studio

logger = logging.getLogger(__name__)


def _generate_record(fid, cp):
    return {
        "file_id": fid,
        "law_order_id": cp.order_id,
        "rule_id": cp.rule_id,
        "cp_id": cp.id,
        "judge_status": JudgeStatusEnum.TODO,
        "name": cp.alias_name or cp.name,
    }


async def judge_file(fid):
    file = await NewFile.find_by_id(fid, include_deleted=True)
    if file and file.scenario_id:
        if not file.chatdoc_unique:
            # 按需将合同文件+interdoc上传到chatdoc
            chatdoc_unique = await upload_pdf_with_interdoc_to_chatdoc(file)
            await pw_db.update(file, chatdoc_unique=chatdoc_unique)

        if not await is_document_parsed(file.chatdoc_unique):
            logger.info("ChatDOC not parsed")
            judge_file_task.apply_async(args=(file.id,), kwargs={}, countdown=60)
            return

        async with pw_db.atomic():
            await LawJudgeResult.reset_judge_results(file.id)

            check_points = await pw_db.execute(
                LawCheckPoint.active_by_scenario(file.scenario_id)
                .where(LawCheckPoint.check_method.is_null(False))  # 仅模型规则
                .order_by(LawCheckPoint.rule_id, LawCheckPoint.id)
            )

            template_cps = await pw_db.execute(
                LawCheckPoint.active_by_scenario(file.scenario_id).where(LawCheckPoint.check_method.is_null())
            )
            todo_records = [_generate_record(file.id, cp) for cp in template_cps]

            rule_cp_ids = []
            for rule_id, rule_cps in groupby(check_points, attrgetter("rule_id")):
                cp_ids = []
                for cp in rule_cps:
                    cp_ids.append(cp.id)
                    todo_records.append(_generate_record(file.id, cp))
                rule_cp_ids.append((rule_id, cp_ids))

            if todo_records:
                await LawJudgeResult.bulk_insert(todo_records)
            else:
                await pw_db.create(
                    LawJudgeResult,
                    file_id=file.id,
                    judge_status=JudgeStatusEnum.MISSING.value,
                )

        template_cp_ids = [cp.id for cp in template_cps]
        judge_file_law_templates_task.delay(file.id, template_cp_ids)

        for rule_id, cp_ids in rule_cp_ids:
            judge_file_law_rule_task.delay(file.id, file.chatdoc_unique, rule_id, cp_ids)
        return len(todo_records)
    return 0


@app.task
@sync
async def judge_file_task(fid):
    await judge_file(fid)


@app.task
@sync
async def preset_answer_by_fid_task(fid, force_predict=False, file_answer_merge_strategy=None):
    await judge_file(fid)
    if ClientName.cmfchina == config.get_config("client.name"):
        await cmf_china_preset_answer_by_fid(
            fid, force_predict=force_predict, file_answer_merge_strategy=file_answer_merge_strategy
        )
    else:
        await preset_answer_by_fid(
            fid, force_predict=force_predict, file_answer_merge_strategy=file_answer_merge_strategy
        )


@app.task
@sync
async def judge_file_law_templates_task(file_id, cp_ids):
    await judge_file_law_templates(file_id, cp_ids)


@app.task
@sync
async def judge_file_law_rule_task(file_id, chatdoc_unique, rule_id, cp_ids):
    logger.info(f"start judge file law rule task: {file_id}, {chatdoc_unique}, {rule_id}, {cp_ids}")
    await judge_file_law_rule(file_id, chatdoc_unique, rule_id, cp_ids)


async def preset_answer_by_fid(fid, force_predict=False, file_answer_merge_strategy=None):
    async with pw_db.atomic():
        questions: list[QuestionWithFK] = await pw_db.prefetch(
            QuestionWithFK.select(for_update=True)
            .join(MoldWithFK)
            .where((QuestionWithFK.file == fid) & (MoldWithFK.mold_type != MoldType.LLM)),
            MoldWithFK.select(),
            NewFile.select(),
            ModelVersionWithFK.select(),
        )
        if not questions:
            logger.error(f"No question found for fid: {fid}, maybe the previous db transaction has not been completed")
            return
        file = questions[0].file
        if not file:
            logger.error("file not existed before check pdfinsight")
            return
        try:
            elements = NewFileService.check_pdfinsight(file)
        except (PDFInsightNotFound, InvalidInterdocError) as exp:
            logger.exception(str(exp))
            file.pdf_parse_status = (
                PDFParseStatus.FAIL if isinstance(exp, PDFInsightNotFound) else PDFParseStatus.UN_CONFIRMED
            )
            await pw_db.update(file, only=[NewFile.pdf_parse_status])
            return

        logger.info(f"length of pdfinsight elements: {len(elements)} , file id: {fid}")
        question_ids = await start_preset_answer(file, questions, force_predict)

    for question_id in question_ids:
        await NewQuestionService.post_pipe(question_id, file.id, file.meta_info)
    await NewFileService.post_pipe(
        file.id,
        triggered_by_predict=True,
        file_answer_merge_strategy=file_answer_merge_strategy,
    )


async def cmf_china_preset_answer_by_fid(fid, force_predict=False, file_answer_merge_strategy=None):
    questions: list[QuestionWithFK] = await pw_db.prefetch(
        QuestionWithFK.select()
        .join(MoldWithFK)
        .where((QuestionWithFK.file == fid) & (MoldWithFK.mold_type != MoldType.LLM)),
        MoldWithFK.select(),
        NewFile.select(),
        CmfMoldModelRef.select(),
    )

    if not questions:
        logger.error(f"No question found for fid: {fid}, maybe the previous db transaction has not been completed")
        return
    file = questions[0].file
    if not file:
        logger.error("file not existed before check pdfinsight")
        return
    if not file.is_excel:
        try:
            elements = NewFileService.check_pdfinsight(file)
        except (PDFInsightNotFound, InvalidInterdocError) as exp:
            logger.exception(str(exp))
            file.pdf_parse_status = (
                PDFParseStatus.FAIL if isinstance(exp, PDFInsightNotFound) else PDFParseStatus.UN_CONFIRMED
            )
            await pw_db.update(file, only=[NewFile.pdf_parse_status])
            return
        logger.info(f"length of pdfinsight elements: {len(elements)} , file id: {fid}")

    question_ids = await start_preset_answer(file, questions, force_predict)

    for question_id in question_ids:
        await NewQuestionService.post_pipe(question_id, file.id, file.meta_info)
    await NewFileService.post_pipe(
        file.id,
        triggered_by_predict=True,
        file_answer_merge_strategy=file_answer_merge_strategy,
    )


async def start_preset_answer(file: NewFile, questions: list[QuestionWithFK], force_predict: bool):
    question_ids = []
    for question in questions:
        if not question.mold or (
            question.mold.model_versions and not any(m.enable for m in question.mold.model_versions)
        ):
            logger.warning(f"{question.id=}, {question.mold.id=} | No enabled model version")
            await question.update_record(exclusive_status=AIStatus.DISABLE)
            continue
        if question.mold and not question.mold.model_versions:
            logger.warning(f"{question.id=}, {question.mold.id=} | Uncorrelated model")
            await question.update_record(exclusive_status=AIStatus.UNCORRELATED)
            continue
        if question.ai_status == AIStatus.SKIP_PREDICT:
            continue
        if not force_predict and question.ai_status != AIStatus.TODO:
            continue
        try:
            await NewTimeRecord.update_record(file.id, "preset_stamp")
            if not file.is_excel and ClientName.cmfchina != config.get_config("client.name"):
                await recruit_preset_answer(file, question)  # 初步定位，预测元素块
            await NewTimeRecord.update_record(file.id, "prompt_stamp")
            await predict_answer(question)

            await question.set_answer()
            question_ids.append(question.id)
        except Exception as exp:
            logger.exception(exp)
            continue

    return question_ids


@app.task
@loop_wrapper
async def preset_answer_by_qid(qid, force_predict=False):
    question: QuestionWithFK = await pw_db.prefetch_one(
        QuestionWithFK.select()
        .join(MoldWithFK)
        .where((QuestionWithFK.id == qid) & (MoldWithFK.mold_type != MoldType.LLM)),
        MoldWithFK.select(),
        NewFile.select(),
        ModelVersionWithFK.select(),
    )

    file = question.file
    if not question or not file:
        logger.info(f"No question found, skip preset for qid:{qid}")
        return
    if question.ai_status == AIStatus.SKIP_PREDICT:
        logger.info(f"question.ai_status is AIStatus.NOPREDICT, skip preset for qid:{qid}")
        return
    if not force_predict and question.ai_status != AIStatus.TODO:
        logger.info(f"question.ai_status is not AIStatus.TODO, skip preset for qid:{qid}")
        return

    logger.info(f"preset_answer_by_qid: {qid}")
    question_ids = await start_preset_answer(file, [question], force_predict)

    if question.id in question_ids:
        await NewQuestionService.post_pipe(question.id, file.id, file.meta_info)
    await NewFileService.post_pipe(file.id, triggered_by_predict=True)


@app.task
@loop_wrapper
async def inspect_rule_task(fid):
    """完备性审核"""
    from remarkable.service.rule import do_inspect_rule_pipe

    await do_inspect_rule_pipe(fid)


async def recruit_preset_answer(file: NewFile, question: NewQuestion):
    """复制了缓存答案后，补充分析的中间结果（crude_answer/pdfinsight）
    注：pdfinsight 暂未实现
    """
    if file.pdfinsight is None:
        raise NotImplementedError(f"file {file.id} have no pdfinsight")

    if config.get_config("web.predict_crude_elements", True):
        logger.info(f"prompt element: {file.id=}, {question.id=}")
        crude_answer = await predict_crude_answer_delegate(file.id, question.id, file=file)
        await question.update_(crude_answer=crude_answer)
    return question.crude_answer


@app.task
@loop_wrapper
@peewee_transaction_wrapper
async def run_preset_answer_stat(
    mold,
    preset_path=None,
    save=None,
    vid=0,
    tree_s=None,
    acid=None,
    headnum=10,
    test_accuracy=False,
    export_excel=False,
    files_ids=None,
    diff_model=None,
):
    await save_stat_result(
        preset_path,
        headnum,
        mold,
        save,
        vid,
        tree_s,
        acid,
        test_accuracy=test_accuracy,
        export_excel=export_excel,
        files_ids=files_ids,
        diff_model=diff_model,
    )


@app.task
@loop_wrapper
async def preset_answer_online(fid, qid, vid, preset_path, test_accuracy):
    file = await NewFile.find_by_id(fid)
    if not file:
        logger.error(f"can't find file: {fid}")
        return
    async with pw_db.atomic():
        question = await NewQuestion.find_by_id(qid, for_update=True)
        if not question:
            logger.error(f"can't find question: {qid}")
            return

        await question.update_record(exclusive_status=AIStatus.DOING)
        logger.info(f"update question {question.id} status to <DOING>")

        try:
            logger.info(f"prompt element for file: {fid}")
            await predict_crude_answer_delegate(
                fid, qid, vid=vid, save_db=True, test_accuracy=test_accuracy
            )  # 初步定位
            logger.info(f"preset_answer_online for file: {fid}")
            answer = await predict_answer(question, vid, test_accuracy=test_accuracy)
        except PDFInsightNotFound as e:
            logger.exception(e)
            return
        except Exception as e:
            logger.exception(e)
            return

    await question.set_answer()
    await NewQuestionService.post_pipe(qid, fid, file.meta_info)
    await NewFileService.post_pipe(file.id, triggered_by_predict=True)

    if preset_path and os.path.exists(preset_path):
        with open(os.path.join(preset_path, "%s.json" % fid), "w") as file_obj:
            json.dump(answer, file_obj)


@app.task
@loop_wrapper
async def preset_answers_for_mold_online(mold_id, mv_id=0, **kwargs):
    tree_s = kwargs.get("tree_s", [])
    preset_path = kwargs.get("preset_path")
    save = kwargs.get("save")
    test_accuracy = kwargs.get("test_accuracy")
    kwargs.update(vid=mv_id)
    files_ids = kwargs.get("files_ids")
    not_in_fids = kwargs.get("not_in_fids", [])

    questions = await NewQuestion.list_by_range(
        mold=mold_id, tree_l=tree_s, files_ids=files_ids, special_cols=["id", "fid", "mold", "llm_status"]
    )
    logger.info(f"update special question status to {AIStatus.TODO} for mold {mold_id}")
    await NewQuestion.reset_predict_status(questions)
    available_questions = []
    for question in questions:
        file = await NewFile.find_by_id(question.fid)
        if file.id in not_in_fids:
            continue
        if not file.pdfinsight:
            continue
        re_extract_answer_by_studio.delay(file.id, [mold_id])
        available_questions.append(question)
    batch_task = preset_answer_online.starmap(
        [(q.fid, q.id, mv_id, preset_path, test_accuracy) for q in available_questions]
    )
    tasks = [batch_task]
    if save:
        tasks.append(run_preset_answer_stat.signature((mold_id,), kwargs, immutable=True))

    workflow = celery.chain(*tasks)
    workflow()


@app.task
@loop_wrapper
async def run_prompt(schema_id, mv_id=0, **kwargs):
    await predict_crude_answer_by_range(None, None, mold=schema_id, overwrite=True, headnum=5, vid=mv_id, **kwargs)
