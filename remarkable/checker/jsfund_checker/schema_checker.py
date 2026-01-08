from __future__ import annotations

from typing import Generator

from remarkable.checker.cgs_checker.public_asset_management.schema_checker import (
    FundNameSchemaChecker,
)
from remarkable.checker.cgs_checker.schema_checker import get_schema_checker
from remarkable.checker.cgs_checker.util import is_skip_check
from remarkable.plugins.cgs.schemas.reasons import ResultItem

SCHEMA_CHECKER = [FundNameSchemaChecker]


def check_schema(file, mold, manager, reader, labels, inspect_fields) -> Generator[ResultItem, None]:
    schema_names = {mold.name}

    for checker in get_schema_checker(schema_names, checkers=SCHEMA_CHECKER):
        if is_skip_check(checker, inspect_fields, labels):
            continue

        template_checker = checker(reader, file, manager, schema_id=mold.id, labels=labels)
        # https://gitpd.paodingai.com/cheftin/docs_scriber/-/issues/2108
        item = template_checker.prev_check() or template_checker.check()
        if not item:
            continue
        yield item
