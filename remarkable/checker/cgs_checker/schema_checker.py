from __future__ import annotations

from typing import TYPE_CHECKING, Generator

from remarkable.checker.cgs_checker.private_fund.schema_checker import (
    PrivateFundSchemaChecker,
)
from remarkable.checker.cgs_checker.public_asset_management.schema_checker import AssetSchemaChecker
from remarkable.checker.cgs_checker.public_custody.schema_checker import (
    PublicCustodySchemaChecker,
)
from remarkable.checker.cgs_checker.public_fund.schema_checker import (
    PublicFundSchemaChecker,
)
from remarkable.checker.cgs_checker.util import is_skip_check

if TYPE_CHECKING:
    from remarkable.plugins.cgs.schemas.reasons import ResultItem

SCHEMA_CHECKER = [PrivateFundSchemaChecker, PublicFundSchemaChecker, PublicCustodySchemaChecker, AssetSchemaChecker]


def get_schema_checker(schema_names: set[str], checkers=None):
    subclasses = []
    for checker in checkers:
        if checker.SCHEMA_NAME in schema_names:
            child_subclasses = checker.__subclasses__()
            if child_subclasses:
                subclasses.extend(child_subclasses)
                subclasses.extend(get_schema_checker(schema_names, checkers=child_subclasses))
    return subclasses


def check_schema(file, mold, manager, reader, labels, inspect_fields, fund_manager_info) -> Generator[ResultItem, None]:
    schema_names = {mold.name}

    for checker in get_schema_checker(schema_names, checkers=SCHEMA_CHECKER):
        if is_skip_check(checker, inspect_fields, labels):
            continue

        template_checker = checker(
            reader, file, manager, schema_id=mold.id, labels=labels, fund_manager_info=fund_manager_info
        )
        # https://gitpd.paodingai.com/cheftin/docs_scriber/-/issues/2108
        item = template_checker.prev_check() or template_checker.check()
        if not item:
            continue
        yield item
