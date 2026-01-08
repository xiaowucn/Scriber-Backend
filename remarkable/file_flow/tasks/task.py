import hashlib
import logging
from enum import IntEnum, unique

from statemachine import StateMachine
from statemachine.states import States

from remarkable.common.constants import FAKE_DATA, PDFParseStatus, ZTSProjectStatus
from remarkable.common.exceptions import CustomError
from remarkable.common.storage import localstorage
from remarkable.common.util import generate_timestamp, run_singleton_task
from remarkable.config import get_config
from remarkable.db import pw_db
from remarkable.file_flow.uploaded_file import UploadedFile
from remarkable.hooks import InsightFinishHook
from remarkable.models.new_file import NewFile
from remarkable.pw_db_services import PeeweeService
from remarkable.worker.tasks import cache_pdf_file, convert_or_parse_file, embed_file

logger = logging.getLogger(__name__)


@unique
class TaskStatus(IntEnum):
    created = 0

    initialized = 1

    parsing = 2
    parse_fail = 298
    parse_success = 299

    caching = 3
    cache_fail = 398
    cache_success = 399

    predicting = 4

    process_answer = 5

    auditing = 6

    completed = 10000


class BaseTask(StateMachine):
    task_states = States.from_enum(
        TaskStatus, use_enum_instance=True, initial=TaskStatus.created, final={TaskStatus.completed}
    )

    create = task_states.created.to(task_states.initialized)
    parse_file = task_states.initialized.to(task_states.parsing)

    receive_success_callback = task_states.parsing.to(task_states.parse_success)
    receive_fail_callback = task_states.parsing.to(task_states.parse_fail) | task_states.parse_fail.to(
        task_states.completed
    )

    cache = task_states.parse_success.to(task_states.caching)
    cache_success = task_states.caching.to(task_states.cache_success)
    cache_fail = task_states.caching.to(task_states.cache_fail) | task_states.cache_fail.to(task_states.completed)

    predict = task_states.cache_success.to(task_states.predicting)

    modify_answer = task_states.predicting.to(task_states.process_answer)

    audit_answer = task_states.process_answer.to(task_states.auditing)

    complete_audit = task_states.auditing.to(task_states.completed)

    cycle = (
        create
        | parse_file
        | receive_success_callback
        | receive_fail_callback
        | cache
        | cache_success
        | cache_fail
        | predict
        | modify_answer
        | audit_answer
    )

    process_file_task_triggered: bool = False
    file: NewFile | None = None

    @create.on
    async def do_create(
        self,
        data: dict,
        uploaded_file: UploadedFile,
        interdoc_raw: bytes | None = None,
        *,
        using_pdfinsight_cache: bool = False,
        allow_duplicated_name: bool = False,
        db_service: PeeweeService,
        **kwargs,
    ):
        return await self.handle_create(
            data,
            uploaded_file,
            interdoc_raw,
            using_pdfinsight_cache=using_pdfinsight_cache,
            allow_duplicated_name=allow_duplicated_name,
            db_service=db_service,
            **kwargs,
        )

    # fixme: 状态机堆栈超出控制, 导致外层事务无效
    async def handle_create(
        self,
        data: dict,
        uploaded_file: UploadedFile,
        interdoc_raw: bytes | None = None,
        *,
        using_pdfinsight_cache: bool = False,
        allow_duplicated_name: bool = False,
        db_service: PeeweeService,
        **kwargs,
    ):
        raise NotImplementedError

    @create.after
    async def do_after_create(self, *args, db_service: PeeweeService):
        await self.handle_after_create(db_service)

    async def handle_after_create(self, db_service: PeeweeService):
        if self.file:
            time_record = await db_service.time_records.get_one_or_none(fid=self.file.id)
            if time_record:
                await db_service.time_records.update(time_record, {"upload_stamp": generate_timestamp()})
            else:
                await db_service.time_records.create({"fid": self.file.id, "upload_stamp": generate_timestamp()})

    @parse_file.on
    async def do_parse(
        self,
        file,
        force_ocr_pages=get_config("app.auth.pdfinsight.force_ocr_pages"),
        force_as_pdf: bool = False,
        enable_ocr: bool = False,
        garbled: bool = False,
        force: bool = False,
        *,
        db_service: PeeweeService,
    ):
        return await self.handle_parse(
            file,
            force_ocr_pages=force_ocr_pages,
            force_as_pdf=force_as_pdf,
            enable_ocr=enable_ocr,
            garbled=garbled,
            force=force,
            db_service=db_service,
        )

    async def handle_parse(
        self,
        file,
        force_ocr_pages=get_config("app.auth.pdfinsight.force_ocr_pages"),
        force_as_pdf: bool = False,
        enable_ocr: bool = False,
        garbled: bool = False,
        force: bool = False,
        *,
        db_service: PeeweeService,
    ):
        raise NotImplementedError

    @parse_file.after
    async def do_after_parse(self, file, db_service: PeeweeService):
        await self.handle_after_parse(file, db_service=db_service)

    async def handle_after_parse(self, file, db_service: PeeweeService):
        raise NotImplementedError

    @receive_success_callback.on
    async def do_receive_success_callback(
        self,
        file: NewFile,
        enable_embedding: bool = False,
        *,
        db_service: PeeweeService,
    ):
        # file = await db_service.files.get_one(id=file_id)
        # files = await db_service.files.list(File.pdfinsight.is_(None), File.id != file.id, hash=file.hash)
        # for row in files:
        #     data = {
        #         "pdf_parse_status": file.pdf_parse_status,
        #         "pdfinsight": file.pdfinsight,
        #         "pdf": file.pdf,
        #         "revise_docx": file.revise_docx,
        #         "meta_info": file.meta_info,
        #         "docx": file.docx,
        #     }
        #     await db_service.files.update(row, data)
        #
        # files = [file] + files
        # for row in files:
        #     time_record = await db_service.time_records.get_one_or_none(fid=row.id)
        #     time_data = {"insight_parse_stamp": generate_timestamp()}
        #     if time_record:
        #         await db_service.time_records.update(time_record, time_data)
        #     else:
        #         time_data["fid"] = row.id
        #         await db_service.time_records.create(time_data)
        #     # await NewTimeRecord.update_record(file.id, "insight_parse_stamp")
        await self.handle_receive_success_callback(file, enable_embedding=enable_embedding)

    async def handle_receive_success_callback(self, file: NewFile, enable_embedding: bool = False):
        raise NotImplementedError

    @receive_fail_callback.on
    async def do_receive_fail_callback(
        self,
        file_id: int,
        caused_by_coloring: bool = False,
        *,
        db_service: PeeweeService,
    ):
        await self.handle_receive_fail_callback(file_id, caused_by_coloring=caused_by_coloring, db_service=db_service)

    async def handle_receive_fail_callback(
        self, file_id: int, caused_by_coloring: bool = False, *, db_service: PeeweeService
    ):
        raise NotImplementedError

    @cache.on
    async def do_cache(self, file):
        return await self.handle_cache(file)

    async def handle_cache(self, file: NewFile, force: bool = False):
        raise NotImplementedError

    @predict.on
    async def do_predict(self, file: NewFile, force: bool = False):
        print("do_predict", file.id)

        await self.handle_predict(file, force=force)

    async def handle_predict(self, file: NewFile, force: bool = False):
        raise NotImplementedError

    @modify_answer.on
    async def do_modify(self, answer):
        return await self.handle_modify_answer(answer)

    async def handle_modify_answer(self, answer):
        raise NotImplementedError

    @audit_answer.on
    async def do_audit(self, answer):
        return await self.handle_audit_answer(answer)

    async def handle_audit_answer(self, answer):
        raise NotImplementedError

    async def _create_file(
        self,
        data: dict,
        uploaded_file: UploadedFile,
        interdoc_raw: bytes | None = None,
        *,
        using_pdfinsight_cache: bool = False,
        allow_duplicated_name: bool = False,
        db_service: PeeweeService,
    ):
        if not allow_duplicated_name:
            if await db_service.files.get_one_or_none(name=data["name"], pid=data["pid"]):
                raise CustomError(_("该项目下|已存在同名的文件"))

        logger.info(f"Start creating the file: {data['name']}")

        file = await self._create_with_cache(
            data, interdoc_raw, using_pdfinsight_cache=using_pdfinsight_cache, db_service=db_service
        )
        localstorage.write_file(file.path(), uploaded_file.content, encrypt=bool(get_config("app.file_encrypt_key")))
        if interdoc_raw:
            localstorage.write_file(file.pdfinsight_path(), interdoc_raw)

        logger.info(f"File created successfully, id:{file.id} name:{file.name}")

        return file

    @staticmethod
    async def _create_questions(file: NewFile, *, db_service: PeeweeService, **kwargs):
        await db_service.questions.create_for_file(file, kwargs.get("question_name"), kwargs.get("question_num"))

    @staticmethod
    async def _create_with_cache(
        data: dict,
        interdoc_raw: bytes | None = None,
        *,
        using_pdfinsight_cache: bool = True,
        db_service: PeeweeService,
    ):
        if interdoc_raw:
            data["pdfinsight"] = hashlib.md5(interdoc_raw).hexdigest()

        if using_pdfinsight_cache:
            same_file = await db_service.files.get_same_file(data["hash"])
            if same_file:
                logger.info(
                    f"Same file {same_file.id} found, with pdf: {same_file.pdf}, pdfinsight: {same_file.pdfinsight}"
                )
                if not data.get("pdf"):
                    data["pdf"] = same_file.pdf

                use_pdfinsight_cache_limit_hours = get_config("web.use_pdfinsight_cache_limit_hours")
                if use_pdfinsight_cache_limit_hours and same_file.pdfinsight_path() and not data.get("pdfinsight"):
                    created_recently = localstorage.is_created_recently(
                        same_file.pdfinsight_path(), use_pdfinsight_cache_limit_hours
                    )
                    if created_recently:
                        logger.info("Use pdfinsight cache")
                        data["pdfinsight"] = same_file.pdfinsight
                    else:
                        logger.info("Don't use pdfinsight cache")

        return await db_service.files.create(data)


class DefaultTask(BaseTask):
    async def handle_create(
        self,
        data: dict,
        uploaded_file: UploadedFile,
        interdoc_raw: bytes | None = None,
        *,
        using_pdfinsight_cache: bool = False,
        allow_duplicated_name: bool = False,
        db_service: PeeweeService,
        **kwargs,
    ):
        file = await self._create_file(
            data,
            uploaded_file,
            interdoc_raw,
            using_pdfinsight_cache=using_pdfinsight_cache,
            allow_duplicated_name=allow_duplicated_name,
            db_service=db_service,
        )

        await self._create_questions(file, db_service=db_service, **kwargs)

        self.file = file

        return file

    async def handle_parse(
        self,
        file,
        force_ocr_pages=get_config("app.auth.pdfinsight.force_ocr_pages"),
        force_as_pdf: bool = False,
        enable_ocr: bool = False,
        garbled: bool = False,
        force: bool = False,
        *,
        db_service: PeeweeService,
    ):
        # if get_config("customer_settings.parse_excel") and (
        #         project_name := get_config("customer_settings.default_tree_name")
        # ):
        #     project = await NewFileProject.find_by_kwargs(name=project_name)
        #     assert project, f"{project_name=}未找到，请检查配置"
        #     if project.id == file.pid:
        #         # 广发基金项目特殊配置：指定项目下的文件走 Excel 解析流程
        #         return run_singleton_task(parse_excel_task, file.id, project.id, project_name)
        if (
            force
            or not file.pdfinsight
            or file.pdf_parse_status
            in (
                PDFParseStatus.PENDING,
                PDFParseStatus.FAIL,
                PDFParseStatus.CANCELLED,
            )
        ):
            logger.info(
                "file: %s, force_parse_file: %s, pdfinsight: %s, pdf_parse_status: %s",
                file.id,
                force,
                file.pdfinsight,
                file.pdf_parse_status,
            )

            get_lock, _ = run_singleton_task(
                convert_or_parse_file,
                file,
                ocr=enable_ocr,
                garbled=garbled,
                lock_key=f"convert_or_parse_file:{file.hash}",
                force_ocr_pages=force_ocr_pages,
                force_as_pdf=force_as_pdf,
            )
            if get_lock:
                self.process_file_task_triggered = True

            return

    async def handle_after_parse(self, file, db_service: PeeweeService):
        if not self.process_file_task_triggered:
            return False

        data = {
            "pdf_parse_status": PDFParseStatus.PARSING if get_config("web.parse_pdf", True) else PDFParseStatus.COMPLETE
        }
        await db_service.files.update(file, data)

        return True

    async def handle_receive_success_callback(self, file: NewFile, enable_embedding: bool = False):
        await InsightFinishHook(file).__call__()
        if enable_embedding:
            await embed_file(file)

        await self.cache(file)

    async def handle_receive_fail_callback(
        self, file_id: int, caused_by_coloring: bool = False, *, db_service: PeeweeService
    ):
        print("do_receive_fail_callback", file_id)
        await db_service.files.update(file_id, {"pdf_parse_status": PDFParseStatus.FAIL})
        file = await db_service.files.get_one(id=file_id)
        same_file_conditions = (NewFile.hash == file.hash, NewFile.pdfinsight.is_null(), NewFile.id != file.id)
        await pw_db.execute(NewFile.update(pdf_parse_status=PDFParseStatus.FAIL).where(*same_file_conditions))

    async def handle_cache(self, file: NewFile, force: bool = False):
        cache_pdf_file.delay(file.id, force=force)

    async def handle_predict(self, file: NewFile, force: bool = False):
        if (get_config("web.preset_answer")) and file.molds:
            from remarkable.worker.tasks.predict_tasks import preset_answer_by_fid_task

            logger.info(f"web.preset_answer is True, start preset_answer for {file.id}")
            preset_answer_by_fid_task.apply_async(
                args=[file.id], kwargs={"force_predict": force}, priority=file.priority
            )


class ZtsTask(DefaultTask):
    async def handle_after_parse(self, file, db_service: PeeweeService):
        updated = await super().handle_after_parse(file, db_service)
        if updated:
            await db_service.projects.update(file.pid, {"status": ZTSProjectStatus.DOING.value})

    async def handle_receive_fail_callback(
        self, file_id: int, caused_by_coloring: bool = False, *, db_service: PeeweeService
    ):
        await super().handle_receive_fail_callback(file_id, caused_by_coloring, db_service=db_service)
        if not caused_by_coloring:
            file = await db_service.files.get_one(id=file_id)
            await db_service.projects.update(file.pid, {"status": ZTSProjectStatus.FAILED.value})


class CiticsTgTask(DefaultTask):
    async def handle_receive_fail_callback(
        self, file_id: int, caused_by_coloring: bool = False, *, db_service: PeeweeService
    ):
        await super().handle_receive_fail_callback(file_id, caused_by_coloring, db_service=db_service)
        if not caused_by_coloring and get_config("citics.email_url"):
            from remarkable.plugins.ecitic.tg_task import send_fail_email_to_ecitic_tg

            file = await db_service.files.get_one(id=file_id)
            await send_fail_email_to_ecitic_tg(file, "解析失败")


class CmfchinaTask(DefaultTask):
    async def handle_predict(self, file_id: int):
        from remarkable.plugins.cmfchina.tasks import predict_answer_by_interface_task

        predict_answer_by_interface_task.delay(file_id)


class CgsTask(DefaultTask):
    async def handle_create(
        self,
        data: dict,
        uploaded_file: UploadedFile,
        interdoc_raw: bytes | None = None,
        *,
        using_pdfinsight_cache: bool = False,
        allow_duplicated_name: bool = False,
        db_service: PeeweeService,
        **kwargs,
    ):
        file = await self._create_file(
            data,
            uploaded_file,
            interdoc_raw,
            using_pdfinsight_cache=using_pdfinsight_cache,
            allow_duplicated_name=allow_duplicated_name,
            db_service=db_service,
        )

        if uploaded_file.md5 in FAKE_DATA and file.molds[0] == 41:
            # from remarkable.service.new_question import NewQuestionService
            #
            # new_question = await Question.create_by_mold(newfile.id, molds[0], question_name, question_num)
            # answer = (await NewAnswer.get_answers_by_qid(FAKE_DATA[new_file_hash]["qid"]))[0]
            # await new_question.update_(preset_answer=answer.data, ai_status=AIStatus.FINISH)
            # await newfile.update_(pdf_parse_status=PDFParseStatus.COMPLETE, molds=molds)
            # await new_question.set_answer()
            # await NewQuestionService.post_pipe(new_question.id, newfile.id, newfile.meta_info)
            pass

        return file


class TestTask(StateMachine):
    task_states = States.from_enum(
        TaskStatus, use_enum_instance=True, initial=TaskStatus.created, final={TaskStatus.completed}
    )

    create = task_states.created.to(task_states.initialized)
    parse_file = task_states.initialized.to(task_states.parsing)

    receive_success_callback = task_states.parsing.to(task_states.parse_success)

    receive_fail_callback = task_states.parsing.to(task_states.parse_fail) | task_states.parse_fail.to(
        task_states.completed
    )

    cache = task_states.parse_success.to(task_states.caching)
    cache_success = task_states.caching.to(task_states.cache_success)
    cache_fail = task_states.caching.to(task_states.cache_fail) | task_states.cache_fail.to(task_states.completed)

    predict = task_states.cache_success.to(task_states.predicting)

    # predict = receive_success_callback | task_states.parse_success.to(task_states.predicting)

    modify_answer = task_states.predicting.to(task_states.process_answer)

    audit_answer = task_states.process_answer.to(task_states.auditing)

    complete_audit = task_states.auditing.to(task_states.completed)

    cycle = (
        create
        | parse_file
        | receive_success_callback
        | receive_fail_callback
        | cache
        | cache_success
        | cache_fail
        | predict
        | modify_answer
        | audit_answer
    )

    process_file_task_triggered: bool = False

    @create.on
    async def do_create(self, file, *, db_service: PeeweeService):
        await asyncio.sleep(1)
        print("do_create", file)
        self.file = file
        return file

    @create.after
    async def do_after_create(self, *args, db_service: PeeweeService):
        print("do_after_create", args, db_service)

    @parse_file.on
    async def do_parse(self, file):
        print("do_parse", file)
        self.process_file_task_triggered = False
        return True, {}

    @parse_file.after
    async def do_after_parse(self, file, db_service: PeeweeService):
        print("do_after_parse", file, db_service, self.process_file_task_triggered)

    @receive_success_callback.on
    async def do_receive_success_callback(self, file):
        print("do_receive_success_callback", file)

    @receive_success_callback.after
    async def do_after_receive_success_callback(self, file):
        print("do_after_receive_success_callback", file, self.current_state)
        await self.cache(file)

    @cache.after
    async def do_after_cache_success(self, file):
        print("do_after_cache_success", file)
        await self.cache_success(file)

    @receive_fail_callback.on
    async def do_receive_fail_callback(self, file):
        print("do_receive_fail_callback", file)

    @cache_success.on
    async def do_cache_success(self, file):
        await self.predict(file)

    @predict.on
    async def do_predict(self, file):
        print("do_predict", file)

        return {"answer": False}

    @modify_answer.on
    async def do_modify(self, answer):
        print("do_modify", answer)

        answer["answer"] = True

        return answer

    @audit_answer.on
    async def do_audit(self, answer):
        print("do_audit", answer)


if __name__ == "__main__":

    async def run():
        db_service = PeeweeService.create()
        sm = TestTask(start_value=TaskStatus.created)
        await sm.activate_initial_state()
        # print(sm._graph().to_string())
        file = await sm.create({}, db_service=db_service)
        await sm.parse_file(file, db_service=db_service)
        print(sm.current_state)
        # sm = TestTask(start_value=TaskStatus.parsing)
        # await sm.activate_initial_state()
        await sm.receive_success_callback(file)
        print(sm.current_state)
        # await sm.cache_success(file)
        print()

        # sm = TestTask(start_value=TaskStatus.parsing)
        # await sm.activate_initial_state()
        # await sm.receive_fail_callback({})
        # answer = await sm.predict(3)
        # answer = await sm.modify_answer(answer)
        # await sm.audit_answer(answer)
        # print("result3", file, sm.current_state)

    import asyncio

    asyncio.run(run())
