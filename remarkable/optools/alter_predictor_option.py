import argparse
import json

from tornado.ioloop import IOLoop

from remarkable.pw_models.model import NewMold


async def set_framework_version(mold_id, framework_version="2.0"):
    mold = await NewMold.find_by_id(mold_id)
    mold.predictor_option["framework_version"] = framework_version
    predictor_option = json.dumps(mold.predictor_option, ensure_ascii=False)
    await mold.update_(predictor_option=predictor_option)


async def batch_set_framework_version(mold_ids, framework_version="2.0"):
    for mold_id in mold_ids:
        await set_framework_version(mold_id, framework_version)


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Alter predictor_option of Mold.")
    parser.add_argument("mold_ids", metavar="MOLD_ID", type=int, nargs="+", help="mold id list to be modified")
    parser.add_argument(
        "--framework-version", type=str, metavar="1.0/2.0", default="2.0", help="framework version of predictor"
    )

    args = parser.parse_args()
    loop = IOLoop()
    loop.run_sync(lambda: batch_set_framework_version(args.mold_ids, framework_version=args.framework_version))
