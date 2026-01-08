import typing as t
from collections.abc import Mapping
from functools import partial
from typing import Type, TypedDict

from marshmallow import Schema
from webargs import tornadoparser

from remarkable.config import get_config


class DictSchemaType(TypedDict):
    __root__: t.Any


SchemaType = t.Union["Schema", Type["Schema"], DictSchemaType]  # noqa: UP006
DecoratedType = t.TypeVar("DecoratedType", bound=t.Callable[..., t.Any])


def _annotate(func: t.Any, **kwargs: t.Any) -> None:
    if not hasattr(func, "spec__"):
        func.spec__ = {}
    for key, value in kwargs.items():
        if key == "body":
            if key in func.spec__:
                func.spec__[key].append(value)
            else:
                func.spec__[key] = [value]
        else:
            func.spec__[key] = value


def _generate_schema_from_mapping(schema: DictSchemaType, schema_name: str | None) -> Type[Schema]:  # noqa: UP006
    return Schema.from_dict(schema, name=schema_name)()  # type: ignore


def param_checker(
    use_webargs: t.Callable,
    schema: SchemaType,
    schema_name: str = "",
    location: str = "json",
    example: t.Any | None = None,
    examples: dict[str, t.Any] | None = None,
    **kwargs: t.Any,
) -> t.Callable[[DecoratedType], DecoratedType]:
    def decorator(func):
        if not (get_config("web.render_api_docs")):
            return use_webargs(schema, location=location, **kwargs)(func)
        _schema_name: str = schema_name or f"{func.__qualname__.replace('.', '_')}_{location}"
        _schema = schema
        if isinstance(_schema, Mapping):
            _schema = _generate_schema_from_mapping(_schema, _schema_name)
        if isinstance(_schema, type):
            _schema = _schema()

        supported_locations = [
            "json",
            "query",
            "headers",
            "cookies",
            "files",
            "form",
            "querystring",
        ]
        if location not in supported_locations:
            raise ValueError(f"Unknown input location {location}. supported are: {supported_locations}")

        if location == "json":
            _annotate(
                func,
                body=_schema,
                media_type="application/json",
                body_example=example,
                body_examples=examples,
            )
        elif location in ("form", "files"):
            _annotate(
                func,
                body=_schema,
                media_type="multipart/form-data",
                body_example=example,
                body_examples=examples,
            )
        else:
            if not hasattr(func, "spec__") or func.spec__.get("args") is None:
                _annotate(func, args=[])
            func.spec__["args"].append((_schema, location))
        return use_webargs(_schema, location=location, **kwargs)(func)

    return decorator


use_args = partial(param_checker, tornadoparser.use_args)
use_kwargs = partial(param_checker, tornadoparser.use_kwargs)


def doc(
    summary: str | None = None,
    description: str | None = None,
    tag: str | None = None,
    tags: list[str] | None = None,
    responses: list[int] | dict[int, str] | None = None,
    deprecated: bool | None = None,
    hide: bool | None = None,
    operation_id: str | None = None,
) -> t.Callable[[DecoratedType], DecoratedType]:
    _tags = None
    if tag is not None:
        _tags = [tag]
    elif tags is not None:
        _tags = tags

    def decorator(func):
        if not (get_config("web.render_api_docs")):
            return func
        _annotate(
            func,
            summary=summary,
            description=description,
            tags=_tags,
            responses=responses,
            deprecated=deprecated,
            hide=hide,
            operation_id=operation_id,
        )
        return func

    return decorator


class EmptySchema(Schema):
    pass


def rsp_checker(
    schema: SchemaType,
    schema_name: str = "",
    status_code: int = 200,
    description: str | None = None,
    example: t.Any | None = None,
    examples: dict[str, t.Any] | None = None,
) -> t.Callable[[DecoratedType], DecoratedType]:
    def decorator(func):
        if not (get_config("web.render_api_docs")):
            return func

        _schema_name: str = schema_name or f"{func.__qualname__.replace('.', '_')}_rsp"
        _schema = schema
        if not _schema:
            _schema = EmptySchema
        if isinstance(_schema, Mapping):
            _schema = _generate_schema_from_mapping(_schema, _schema_name)
        if isinstance(_schema, type):  # pragma: no cover
            _schema = _schema()

        _annotate(
            func,
            response={
                "schema": _schema,
                "status_code": status_code,
                "description": description,
                "example": example,
                "examples": examples,
            },
        )

        return func

    return decorator
