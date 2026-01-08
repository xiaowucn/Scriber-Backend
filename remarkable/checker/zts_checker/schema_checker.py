from remarkable.checker.cgs_checker.util import is_skip_check
from remarkable.checker.zts_checker.corporate_bond.schema_checker import (
    BorrowingFundsFormula1Checker,
    BorrowingFundsFormula2Checker,
    ConsistencyCompareChecker,
    GuaranteeFormula1Checker,
    GuaranteeFormula2Checker,
    RestrictedFundsFormula2Checker,
)

SCHEMA_CHECKER = [
    ConsistencyCompareChecker,
    # RestrictedFundsFormula1Checker,
    RestrictedFundsFormula2Checker,
    BorrowingFundsFormula1Checker,
    BorrowingFundsFormula2Checker,
    GuaranteeFormula1Checker,
    GuaranteeFormula2Checker,
]


def get_schema_checker(checkers: list):
    classes = []
    for checker in checkers:
        classes.append(checker)
    return classes


def check_schema(file, mold, managers, reader, labels, inspect_fields, doc_types, answer_reader):
    for checker in get_schema_checker(SCHEMA_CHECKER):
        if is_skip_check(checker, inspect_fields, labels):
            continue

        template_checker = checker(
            reader, file, managers, mold=mold, labels=labels, doc_types=doc_types, answer_reader=answer_reader
        )
        items = template_checker.check()
        if not items:
            continue

        for item in items:
            yield item
