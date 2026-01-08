import os
import sys

from invoke import Collection

if os.getenv("PSYCOPG2_GAUSS", "").lower() == "true":
    sys.path.insert(0, "/usr/lib/paoding/dist-packages")

import remarkable.devtools.task_cmfchina as cmfchina
import remarkable.devtools.task_db as db
import remarkable.devtools.task_debug as debug
import remarkable.devtools.task_dev as dev
import remarkable.devtools.task_export as export
import remarkable.devtools.task_farm as farm
import remarkable.devtools.task_gffunds_db as gffunds_db
import remarkable.devtools.task_ht as ht
import remarkable.devtools.task_i18n as i18n
import remarkable.devtools.task_lint as lint
import remarkable.devtools.task_op as op
import remarkable.devtools.task_predictor as predictor
import remarkable.devtools.task_prompter as prompter
import remarkable.devtools.task_schema as schema
import remarkable.devtools.task_storage as storage
import remarkable.devtools.task_sync as sync
import remarkable.devtools.task_test as test
import remarkable.devtools.task_worker as worker
from remarkable.config import project_root

config_file = "{}/config/config-{}.yml".format(project_root, os.environ.get("ENV") or "dev")


namespace = Collection()
namespace.configure({"project_root": project_root, "config_file": config_file})


namespace.add_collection(Collection.from_module(lint, name="lint"))
namespace.add_collection(Collection.from_module(db, name="db"))
namespace.add_collection(Collection.from_module(worker, name="worker"))
namespace.add_collection(Collection.from_module(i18n, name="i18n"))
namespace.add_collection(Collection.from_module(op, name="op"))
namespace.add_collection(Collection.from_module(prompter, name="prompter"))
namespace.add_collection(Collection.from_module(sync, name="sync"))
namespace.add_collection(Collection.from_module(farm, name="farm"))
namespace.add_collection(Collection.from_module(predictor, name="predictor"))
namespace.add_collection(Collection.from_module(storage, name="storage"))
namespace.add_collection(Collection.from_module(export, name="export"))
namespace.add_collection(Collection.from_module(debug, name="debug"))
namespace.add_collection(Collection.from_module(test, name="test"))
namespace.add_collection(Collection.from_module(ht, name="ht"))
namespace.add_collection(Collection.from_module(dev, name="dev"))
namespace.add_collection(Collection.from_module(schema, name="schema"))
namespace.add_collection(Collection.from_module(gffunds_db, name="gffunds-db"))
namespace.add_collection(Collection.from_module(cmfchina, name="cmfchina"))
