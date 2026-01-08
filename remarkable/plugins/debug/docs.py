import re
from copy import deepcopy
from typing import Any, Iterable

from apispec import APISpec
from apispec.ext.marshmallow import MarshmallowPlugin
from marshmallow import Schema
from tornado import template

from remarkable.common.apispec_decorators import SchemaType

DOC_TITLE = "Scriber API"
DOC_VERSION = "1.0.0"
DOC_OPENAPI_VERSION = "3.0.0"
SWAGGER_UI_TEMPLATE = """<!DOCTYPE html>
<html>
<head>
<link type="text/css" rel="stylesheet" href="https://unpkg.com/swagger-ui-dist@5.9.0/swagger-ui.css">
<title>{{ title }} {{ version }}</title>
</head>
<body>
<div id="swagger-ui">
</div>
<script src="https://unpkg.com/swagger-ui-dist@5.9.0/swagger-ui-bundle.js"></script>
<!-- `SwaggerUIBundle` is now available on the page -->
<script>
const ui = SwaggerUIBundle({
url: '{{ api_url }}',
"dom_id": "#swagger-ui",
"layout": "BaseLayout",
"deepLinking": true,
"showExtensions": true,
"showCommonExtensions": true,
oauth2RedirectUrl: window.location.origin + '/docs/oauth2-redirect',
presets: [
    SwaggerUIBundle.presets.apis,
    SwaggerUIBundle.SwaggerUIStandalonePreset
    ],
})
</script>
</body>
</html>
"""


def generate_spec(handlers) -> APISpec:
    # TODO: 有 Schema 重名的情况
    spec = APISpec(
        title=DOC_TITLE,
        version=DOC_VERSION,
        openapi_version=DOC_OPENAPI_VERSION,
        plugins=[MarshmallowPlugin()],
    )

    # paths
    paths: dict[str, dict[str, Any]] = {}
    for url, handler in handlers:
        operations: dict[str, Any] = {}
        has_spec: bool = False
        for method in ["get", "post", "put", "patch", "delete"]:
            if not hasattr(handler, method):
                continue

            view_func = getattr(handler, method)

            if not hasattr(view_func, "spec__"):
                continue

            if view_func.spec__.get("hide"):
                continue

            has_spec = True
            operation_tags = None
            if view_func.spec__.get("tags"):
                operation_tags = view_func.spec__.get("tags")

            operation: dict[str, Any] = {
                "parameters": [
                    {"in": location, "schema": schema} for schema, location in view_func.spec__.get("args", [])
                ],
                "responses": {},
            }
            if operation_tags:
                operation["tags"] = operation_tags

            # summary
            if view_func.spec__.get("summary"):
                operation["summary"] = view_func.spec__.get("summary")

            # description
            if view_func.spec__.get("description"):
                operation["description"] = view_func.spec__.get("description")

            # deprecated
            if view_func.spec__.get("deprecated"):
                operation["deprecated"] = view_func.spec__.get("deprecated")

            # operationId
            operation_id = view_func.spec__.get("operation_id")
            if operation_id is None:
                operation["operationId"] = f"{method.lower()}_{handler.__name__}"
            else:
                operation["operationId"] = operation_id

            if view_func.spec__.get("response"):
                schema = view_func.spec__.get("response")["schema"]
                status_code: str = str(view_func.spec__.get("response")["status_code"])
                description: str = view_func.spec__.get("response")["description"] or "成功"
                example = view_func.spec__.get("response")["example"]
                examples = view_func.spec__.get("response")["examples"]
                _add_response(operation, status_code, schema, description, example, examples)
            # requestBody
            if view_func.spec__.get("body"):
                media_type = (
                    view_func.spec__["media_type"] if view_func.spec__.get("media_type") else "application/json"
                )
                operation["requestBody"] = {"content": {media_type: {"schema": merge_schema(view_func.spec__["body"])}}}
                if view_func.spec__.get("body_example"):
                    example = view_func.spec__.get("body_example")
                    operation["requestBody"]["content"][media_type]["example"] = example
                if view_func.spec__.get("body_examples"):
                    examples = view_func.spec__.get("body_examples")
                    operation["requestBody"]["content"][media_type]["examples"] = examples

            operations[method.lower()] = operation

        if not has_spec:
            continue

        # parameters
        path_arguments: Iterable = re.findall(r"\(\?P<([_a-z]+)>[^)]*\)", url)
        if path_arguments:
            arguments: list[dict[str, str]] = []
            for argument_name in path_arguments:
                argument = _get_argument("string", argument_name)
                arguments.append(argument)

            for operation in operations.values():
                operation["parameters"] = arguments + operation["parameters"]

        path: str = re.sub(r"\(\?P<([_a-z]+)>[^)]*\)", r"{\1}", url)
        if path not in paths:
            paths[path] = operations
        else:
            paths[path].update(operations)

    for path, operations in paths.items():
        # sort by method before adding them to the spec
        sorted_operations: dict[str, Any] = {}
        for method in ["get", "post", "put", "patch", "delete"]:
            if method in operations:
                sorted_operations[method] = operations[method]
        try:
            spec.path(path=path, operations=sorted_operations)
        except Exception as e:
            print(f"Error adding path {path} to spec: {e}")
    return spec


def _get_argument(argument_type: str, argument_name: str) -> dict[str, Any]:
    argument: dict[str, Any] = {"in": "path", "name": argument_name}
    if argument_type == "int:":
        argument["schema"] = {"type": "integer"}
    elif argument_type == "float:":
        argument["schema"] = {"type": "number"}
    else:
        argument["schema"] = {"type": "string"}
    return argument


def merge_schema(schemas: list):
    if len(schemas) == 1:
        return schemas[0]

    new_dict = deepcopy(schemas[0].fields)
    for schema in schemas[1:]:
        new_dict.update(schema.fields)
    return Schema.from_dict(new_dict, name=schemas[0].__class__.__name__)


def _add_response(
    operation: dict,
    status_code: str,
    schema: SchemaType | dict,
    description: str,
    example: Any | None = None,
    examples: dict[str, Any] | None = None,
) -> None:
    operation["responses"][status_code] = {}
    operation["responses"][status_code]["content"] = {"application/json": {"schema": schema}}
    operation["responses"][status_code]["description"] = description
    if example is not None:
        operation["responses"][status_code]["content"]["application/json"]["example"] = example
    if examples is not None:
        operation["responses"][status_code]["content"]["application/json"]["examples"] = examples


def generate_template(route_prefix="/api/v1"):
    prefix = f"{route_prefix}/__docs"
    return template.Template(SWAGGER_UI_TEMPLATE).generate(
        title=DOC_TITLE,
        version=DOC_VERSION,
        api_url=f"{prefix}/json",
    )
