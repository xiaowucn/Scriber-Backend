import httpx
from fastapi import HTTPException
from starlette.status import HTTP_400_BAD_REQUEST
from utensils.util import httpx_client

from remarkable import config, logger
from remarkable.common.constants import LLMStatus, MoldType
from remarkable.common.enums import ExtractType
from remarkable.db import pw_db
from remarkable.models.model_version import ModelVersionWithFK
from remarkable.pw_models.model import MoldWithFK, NewMold
from remarkable.pw_models.question import NewQuestion
from remarkable.routers.schemas.mold import MoldDataSchema, StudioSchema, StudioSchemaProperty, StudioSchemaSchemas
from remarkable.security.crypto_util import encode_jwt


async def register_studio_hook():
    url = f"{config.get_config('app.auth.studio.url')}{config.get_config('app.auth.studio.app_hook')}"
    callback_url = (
        f"{config.get_config('web.scheme', 'http')}://{config.get_config('web.domain')}/api/v2/files/extract-complete"
    )
    try:
        result = await _make_request(
            "post",
            url,
            json={"api_key": encode_jwt({"sub": "admin"}), "url": callback_url, "params": {"update_if_exists": True}},
        )
        logger.info(f"create studio hook success id: {result['data']['id']}")
    except Exception as e:
        logger.warning(f"create studio hook failed: {e}")


async def _make_request(method, url, timeout: int | None = config.get_config("app.auth.studio.timeout"), **kwargs):
    async with httpx_client(timeout=timeout) as client:
        try:
            response = await getattr(client, method)(
                url, headers={"Authorization": f"Bearer {config.get_config('app.auth.studio.api_key')}"}, **kwargs
            )
        except httpx.TimeoutException as e:
            raise HTTPException(400, "调用 chatdoc studio api 超时") from e
        else:
            if response.status_code != 200:
                raise HTTPException(HTTP_400_BAD_REQUEST, response.text)
            return response.json()


def build_app_schema(data: MoldDataSchema) -> StudioSchema:
    type_dict = {
        "文本": "string",
        "数字": "number",
        "日期": "string",
    }
    main_schema = data.schemas[0]
    enum_schema_dict = {}
    for schema_type in data.schema_types:
        enum_schema_dict[schema_type.label] = schema_type

    combination_schema_dict = {}
    for schema in data.schemas[1:]:
        combination_schema_dict[schema.name] = schema

    properties = {}
    for idx, (key, value) in enumerate(main_schema.schema.items()):
        order_idx = main_schema.orders.index(key) if main_schema.orders else idx
        if value.extract_type != ExtractType.LLM:
            continue
        if value.type in enum_schema_dict:
            enum_schema = enum_schema_dict[value.type]
            properties[key] = StudioSchemaProperty(
                description=value.description,
                enum=[item.name for item in enum_schema.values],
                property_order=order_idx,
            )
        elif value.type in combination_schema_dict:
            combination_schema = combination_schema_dict[value.type]
            sub_schemas = {}
            for sub_idx, (sub_key, schema) in enumerate(combination_schema.schema.items()):
                sub_order_idx = combination_schema.orders.index(sub_key) if combination_schema.orders else sub_idx
                if schema.type in enum_schema_dict:
                    enum_schema = enum_schema_dict[schema.type]
                    sub_schemas[sub_key] = StudioSchemaProperty(
                        description=schema.description,
                        enum=[item.name for item in enum_schema.values],
                        property_order=sub_order_idx,
                    )
                else:
                    sub_schemas[sub_key] = StudioSchemaProperty(
                        type=type_dict[schema.type],
                        description=schema.description,
                        property_order=sub_order_idx,
                    )
            properties[key] = StudioSchemaProperty(
                type="array",
                description=value.description,
                property_order=order_idx,
                items={
                    "type": "object",
                    "properties": sub_schemas,
                },
            )
        else:
            items = None
            if value.multi:
                property_type = "array"
                items = {"type": type_dict[value.type]}
            else:
                property_type = type_dict[value.type]
            properties[key] = StudioSchemaProperty(
                type=property_type, description=value.description, property_order=order_idx, items=items
            )

    studio_schema_schemas = StudioSchemaSchemas(
        type="object",
        properties=properties,
    )

    return StudioSchema(schemas=studio_schema_schemas)


async def create_app(name, model_name, schema):
    url = f"{config.get_config('app.auth.studio.url')}{config.get_config('app.auth.studio.app')}"
    result = await _make_request(
        "post",
        url,
        json={"name": name, "model_name": model_name, "schema": schema},
    )
    return result["data"]


async def update_app(name, model_name, schema, app_id):
    url = f"{config.get_config('app.auth.studio.url')}{config.get_config('app.auth.studio.app_with_id')}"
    url = url.format(app_id)
    built_schema = build_app_schema(MoldDataSchema.model_validate(schema))
    return await _make_request(
        "put",
        url,
        json={
            "name": name,
            "model_name": model_name,
            "schema": built_schema.model_dump(exclude_none=True, by_alias=True),
        },
    )


async def delete_app(app_id):
    url = f"{config.get_config('app.auth.studio.url')}{config.get_config('app.auth.studio.app_with_id')}"
    url = url.format(app_id)
    return await _make_request(
        "delete",
        url,
    )


async def add_file_using_studio(fid, upload_id, mold_ids):
    molds = await pw_db.prefetch(
        MoldWithFK.select().where(
            MoldWithFK.id.in_(mold_ids), MoldWithFK.mold_type.in_([MoldType.LLM, MoldType.HYBRID])
        ),
        ModelVersionWithFK.select(),
    )
    await register_studio_hook()
    for mold in molds:
        async with pw_db.atomic():
            fields = [NewQuestion.id, NewQuestion.mold, NewQuestion.exclusive_status, NewQuestion.llm_status]
            question = await pw_db.first(NewQuestion.select(*fields, for_update=True).filter(fid=fid, mold=mold.id))
            if mold.mold_type == MoldType.HYBRID and question.llm_status is LLMStatus.SKIP_PREDICT:
                continue
            try:
                await add_file_using_app(mold.studio_app_id, upload_id)
                llm_status = LLMStatus.DOING
            except Exception as e:
                logger.error(f"add_file_using_app: {mold.studio_app_id}, upload_id: {upload_id}, failed: {e}")
                llm_status = LLMStatus.FAILED

            await question.update_record(llm_status=llm_status)


async def remove_file_from_studio_app(fid, upload_id, mold_ids):
    molds = await pw_db.execute(
        NewMold.select().where(NewMold.id.in_(mold_ids), NewMold.mold_type.in_([MoldType.LLM, MoldType.HYBRID]))
    )
    for mold in molds:
        try:
            await remove_file_from_app(mold.studio_app_id, upload_id)
        except Exception as e:
            logger.error(f"remove_file_from_app: {mold.studio_app_id}, upload_id: {upload_id}, failed: {e}")


async def re_extract_by_studio(fid, upload_id, mold_ids):
    molds = await pw_db.prefetch(
        MoldWithFK.select().where(
            MoldWithFK.id.in_(mold_ids), MoldWithFK.mold_type.in_([MoldType.LLM, MoldType.HYBRID])
        ),
        ModelVersionWithFK.select(),
    )
    await register_studio_hook()
    for mold in molds:
        async with pw_db.atomic():
            fields = [NewQuestion.id, NewQuestion.mold, NewQuestion.exclusive_status, NewQuestion.llm_status]
            question = await pw_db.first(NewQuestion.select(*fields, for_update=True).filter(fid=fid, mold=mold.id))
            try:
                if mold.mold_type == MoldType.HYBRID and (
                    not mold.model_versions or not any(m.enable for m in mold.model_versions)
                ):
                    continue
                if question.llm_status == LLMStatus.SKIP_PREDICT:
                    await add_file_using_app(mold.studio_app_id, upload_id)
                else:
                    await re_extract_using_app(mold.studio_app_id, upload_id)
                llm_status = LLMStatus.DOING
            except Exception as e:
                logger.error(f"re_extract_using_app failed: {e}")
                llm_status = LLMStatus.FAILED

            await question.update_record(llm_status=llm_status)


async def re_extract_using_app(app_id, upload_id):
    url = f"{config.get_config('app.auth.studio.url')}{config.get_config('app.auth.studio.app_extract_again')}"
    url = url.format(app_id, upload_id)
    return await _make_request("get", url)


async def add_file_using_app(app_id, upload_id):
    url = f"{config.get_config('app.auth.studio.url')}{config.get_config('app.auth.studio.app_upload')}"
    url = url.format(app_id)
    return await _make_request(
        "post",
        url,
        json={"upload_id": upload_id},
    )


async def remove_file_from_app(app_id, upload_id):
    url = f"{config.get_config('app.auth.studio.url')}{config.get_config('app.auth.studio.app_remove_upload')}"
    url = url.format(app_id, upload_id)
    return await _make_request("delete", url)


async def get_extract_result(app_id, upload_id):
    url = f"{config.get_config('app.auth.studio.url')}{config.get_config('app.auth.studio.app_upload_extraction')}"
    url = url.format(app_id, upload_id)
    result = await _make_request(
        "get",
        url,
    )
    return result["data"]


async def get_trace_result(app_id, upload_id):
    url = f"{config.get_config('app.auth.studio.url')}{config.get_config('app.auth.studio.app_upload_trace')}"
    url = url.format(app_id, upload_id)
    result = await _make_request(
        "get",
        url,
    )
    return result["data"]


def get_llm_list():
    return [{"model": llm} for llm in config.get_config("app.auth.studio.llm_list", [])]


async def upload_pdf_to_studio(file):
    files = {"file": (file["filename"], file["body"])}
    url = f"{config.get_config('app.auth.studio.url')}{config.get_config('app.auth.studio.upload')}"
    result = await _make_request("post", url, timeout=config.get_config("app.auth.studio.timeout") * 10, files=files)
    return result["data"]["upload_id"]
