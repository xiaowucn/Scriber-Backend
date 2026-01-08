import inspect


def is_skip_check(checker, inspect_fields, labels):
    if inspect.isclass(checker):
        label = checker.LABEL
        schema_fields = checker.SCHEMA_FIELDS
    else:
        label = checker.label
        schema_fields = checker.schema_fields

    if labels and label not in labels:
        return True

    if inspect_fields and not set(inspect_fields).intersection(set(schema_fields)):
        return True

    return False
