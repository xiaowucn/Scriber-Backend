import logging

from remarkable import config
from remarkable.checker.default_checker import Inspector as DefaultInspector
from remarkable.db import peewee_transaction_wrapper

logger = logging.getLogger(__name__)


class Inspector(DefaultInspector):
    @property
    def inspect_name(self):
        return "gffunds-checker"

    async def run_check(self, **kwargs):
        audit_results = await super().run_check(**kwargs)
        await super().save_results(
            audit_results, kwargs.get("labels"), is_preset_answer=self.context.using_preset_answer
        )
        if not (url := config.get_config("customer_settings.audit_system_url")):
            return []

        await self.send_to_server(url)
        return []
