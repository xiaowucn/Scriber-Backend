from remarkable.checker.cgs_checker.private_fund.template_checker import (
    ChaptersTemplateChecker,
    ChapterWithTemplateChecker,
    NormalTemplateChecker,
    SentenceSearcher,
)
from remarkable.checker.cgs_checker.public_asset_management.template_checker import (
    PublicAssetManagementTemplateChecker,
    PublicAssetReplaceTemplateChecker,
    PublicAssetSentenceTemplateChecker,
    PublicAssetSingleWithRatioChecker,
)
from remarkable.checker.cgs_checker.public_custody.template_checker import (
    PublicCustodyReplaceTemplateChecker,
    PublicCustodySingleWithRatioChecker,
    PublicCustodyTemplateChecker,
)
from remarkable.checker.cgs_checker.public_fund.template_checker import (
    PublicMultiWithConditionsChecker,
    PublicNormalTemplateChecker,
    PublicReplaceTemplateChecker,
    PublicSingleWithRatioChecker,
)
from remarkable.checker.cgs_checker.util import is_skip_check


def check_by_templates(file, mold, manager, reader, labels, inspect_fields, fund_manager_info, schema_names=None):
    schema_names = schema_names or [mold.name]

    for checker in [
        NormalTemplateChecker,
        ChaptersTemplateChecker,
        ChapterWithTemplateChecker,
        SentenceSearcher,
        PublicNormalTemplateChecker,
        PublicMultiWithConditionsChecker,
        PublicSingleWithRatioChecker,
        PublicReplaceTemplateChecker,
        PublicCustodyTemplateChecker,
        PublicCustodySingleWithRatioChecker,
        PublicCustodyReplaceTemplateChecker,
        PublicAssetManagementTemplateChecker,
        PublicAssetSingleWithRatioChecker,
        PublicAssetReplaceTemplateChecker,
        PublicAssetSentenceTemplateChecker,
    ]:
        if checker.SCHEMA_NAME not in schema_names:
            continue
        for item in checker(
            reader=reader,
            manager=manager,
            file=file,
            schema_id=mold.id,
            labels=labels,
            fund_manager_info=fund_manager_info,
        ).check():
            if is_skip_check(item, inspect_fields, labels):
                continue

            yield item
