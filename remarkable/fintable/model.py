import io
import json
import logging
import time
from pathlib import Path

from aipod.model import AIModelBase

from remarkable.answer.reader import AnswerReader
from remarkable.common.util import md5json, read_zip_first_file
from remarkable.config import get_config, project_root
from remarkable.fintable.predictor import Prophet
from remarkable.fintable.predictor.schemas.maintable_schema import prophet_config
from remarkable.pw_models.model import NewMold


class FintableModel(AIModelBase):
    def __init__(self, *args, **kwargs):
        super(FintableModel, self).__init__(*args, **kwargs)
        self.mold_id = 1  # NOTE: hard code the mold id (just use for finding the trained model path)
        self.schema_path = Path(project_root, "data", "schema", "fintable_schema.json")

    def build_mold(self):
        mold_data = json.loads(self.schema_path.read_text())[0]
        mold = NewMold(
            id=self.mold_id,
            name=mold_data["data"]["schemas"][0]["name"],
            checksum=md5json(mold_data["data"]),
            data=mold_data["data"],
            predictor_option=mold_data["predictor_option"],
            mold_type=mold_data["mold_type"],
        )
        return mold

    @property
    def predict_model(self):
        mold = self.build_mold()
        prophet = Prophet(prophet_config, mold, version_id=0)
        return prophet

    @staticmethod
    def build_crude_answer(aim_elements):
        crude_answers = {}
        for table, eid in aim_elements.items():
            if not eid:
                continue
            crude_answers[f"{table}-报告期"] = [
                {
                    "element_index": eid,
                    "score": 1,
                }
            ]
        return crude_answers

    def predict(self, binary_data=None, **kwargs):
        """
        binary_data: pdfinsight
        aim_elements: {
            "资产负债表": 1001,
            "现金流量表": 1011,
            "利润表": 1021,
        }
        """
        logging.debug("recevied predict request")
        if get_config("debug"):
            request_log = RequestLog("data/requests")
            request_log.dump_request(binary_data, kwargs)
        logging.debug("read interdoc")
        pdfinsight_io = io.BytesIO(binary_data)
        pdfinsight_data = json.loads(read_zip_first_file(pdfinsight_io))
        logging.debug("build crude answer")
        crude_answer = self.build_crude_answer(kwargs.get("aim_elements", {}))
        logging.debug("run predict")
        result = self.predict_model.run_predict(crude_answer=crude_answer, pdfinsight_data=pdfinsight_data)
        logging.debug(f"predict finish, with {len(result['userAnswer']['items'])} items")

        reader = AnswerReader(result)
        node, _ = reader.build_answer_tree()
        return node.to_dict()


class RequestLog:
    def __init__(self, logdir) -> None:
        self.logdir = Path(logdir)
        self.logdir.mkdir(exist_ok=True)

    def request_dir(self):
        _dir = self.logdir / str(time.time()).replace(".", "")
        _dir.mkdir(exist_ok=True)
        return _dir

    def dump_request(self, binary_data, kwargs):
        dump_dir = self.request_dir()
        if binary_data:
            (dump_dir / "data.bin").write_bytes(binary_data)
        if kwargs:
            (dump_dir / "kwargs.json").write_text(json.dumps(kwargs, ensure_ascii=False, indent=4))


if __name__ == "__main__":
    from aipod.rpc.client import AIClient

    # aim_elements = {
    #     "资产负债表": 5,
    #     "现金流量表": 17,
    #     "利润表": 11,
    # }
    aim_elts = {
        "资产负债表": 5,
        "现金流量表": 49,
        "利润表": 43,
    }
    bin_path = Path("/Users/ferstar/Downloads/fabric/test1.bin")
    model = AIClient(address="localhost:50051")
    res = model.predict(binary_data=bin_path.read_bytes(), aim_elements=aim_elts)
    (bin_path.parent / "debug.json").write_text(json.dumps(res, ensure_ascii=False, indent=4))
    # print(res)
