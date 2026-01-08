from __future__ import with_statement

import re
from logging.config import fileConfig
from unittest.mock import patch

from alembic import context
from sqlalchemy import create_engine, engine_from_config, pool

# this is the Alembic Config object, which provides
# access to the values within the .ini file in use.
config = context.config

# Interpret the config file for Python logging.
# This line sets up loggers basically.
fileConfig(config.config_file_name)

# add your model's MetaData object here
# for 'autogenerate' support
# from myapp import mymodel
# target_metadata = mymodel.Base.metadata
target_metadata = None

# other values from the config, defined by the needs of env.py,
# can be acquired:
# my_important_option = config.get_main_option("my_important_option")
# ... etc.

dburl = context.get_x_argument(as_dictionary=True).get("dburl")
dbschema = context.get_x_argument(as_dictionary=True).get("dbschema")


def patch_get_server_version_info(self, connection):
    v = connection.execute("select pg_catalog.version()").scalar()
    m = re.match(
        r".*(?:PostgreSQL|EnterpriseDB) " r"(\d+)\.?(\d+)?(?:\.(\d+))?(?:\.\d+)?(?:devel|beta)?",
        v,
    )
    if not m:
        return 9, 2, 4  # GaussDB, for cgs_th, docs_pfb#1084
    return tuple([int(x) for x in m.group(1, 2, 3) if x is not None])


@patch("sqlalchemy.dialects.postgresql.base.PGDialect._get_server_version_info", patch_get_server_version_info)
def run_migrations_offline():
    """Run migrations in 'offline' mode.

    This configures the context with just a URL
    and not an Engine, though an Engine is acceptable
    here as well.  By skipping the Engine creation
    we don't even need a DBAPI to be available.

    Calls to context.execute() here emit the given string to the
    script output.

    """
    url = dburl or config.get_main_option("sqlalchemy.url")
    context.configure(url=url, target_metadata=target_metadata, literal_binds=True)

    with context.begin_transaction():
        context.run_migrations()


@patch("sqlalchemy.dialects.postgresql.base.PGDialect._get_server_version_info", patch_get_server_version_info)
def run_migrations_online():
    """Run migrations in 'online' mode.

    In this scenario we need to create an Engine
    and associate a connection with the context.

    """
    if dburl:
        kwargs = {}
        if dbschema:
            kwargs = {"connect_args": {"options": f"-c search_path={dbschema}"}}
        connectable = create_engine(dburl, **kwargs)
    else:
        connectable = engine_from_config(
            config.get_section(config.config_ini_section),
            prefix="sqlalchemy.",
            poolclass=pool.NullPool,
        )
    with connectable.connect() as connection:
        context.configure(
            connection=connection,
            target_metadata=target_metadata,
            transactional_ddl=True,
            transaction_per_migration=True,
        )

        with context.begin_transaction():
            context.run_migrations()


if context.is_offline_mode():
    run_migrations_offline()
else:
    run_migrations_online()
