import io
import json
import logging

from aipod.model import AIModelBase

from remarkable.common.util import md5json, read_zip_first_file
from remarkable.config import get_config
from remarkable.fintable.model import RequestLog
from remarkable.pw_models.model import NewMold


class ScriberModel(AIModelBase):
    """
    输入：interdoc
    输出：crude_answer, predict_answer, rule_results
    """

    def __init__(self, *args, **kwargs):
        super(ScriberModel, self).__init__(*args, **kwargs)
        self.mold_id = get_config("aipod.mold_id")
        schema_path = get_config("aipod.schema_path")
        if not schema_path:
            raise Exception("aipod.schema_path is needed")
        schema_name = get_config("aipod.schema_name")
        with open(schema_path, "r") as sfp:
            schema_dict = {s["data"]["schemas"][0]["name"]: s for s in json.load(sfp)}
            if schema_name not in schema_dict:
                raise Exception(f"can't find {schema_name} in {schema_path}")
        self.mold_data = schema_dict[schema_name]

    def build_mold(self):
        mold = NewMold(
            id=self.mold_id,
            name=self.mold_data["data"]["schemas"][0]["name"],
            checksum=md5json(self.mold_data["data"]),
            data=self.mold_data["data"],
            predictor_option=self.mold_data["predictor_option"],
            mold_type=self.mold_data["mold_type"],
        )
        return mold

    @staticmethod
    def predict_crude_answer(mold, pdfinsight_data):
        from remarkable.service.crude_answer import predict_crude_answer

        crude_answer = predict_crude_answer(None, mold.id, mold.data, pdfinsight_data=pdfinsight_data)
        return crude_answer

    @staticmethod
    def predict_answer(mold, pdfinsight_data, crude_answer):
        from remarkable.predictor.helpers import create_predictor_prophet

        prophet = create_predictor_prophet(mold, model_version=0)
        # NOTE: predictor v1 还需要传 file / metadata / anno_mold / anno_crude_answer，暂不支持
        answer = prophet.run_predict(
            crude_answer=crude_answer,
            pdfinsight_data=pdfinsight_data,
        )
        return answer

    @staticmethod
    def inspect_rules(mold, answer):
        # TODO: 暂不支持合规
        # from remarkable.rule.inspector import AnswerInspectorFactory
        # inspector = AnswerInspectorFactory.create(
        #     mold,
        #     doc=_file,
        #     question=question,
        #     meta=meta,
        # )
        return {}

    def predict(self, binary_data=None, **kwargs):
        """
        binary_data: pdfinsight
        """
        logging.debug("recevied predict request")
        if get_config("debug"):
            request_log = RequestLog("data/requests")
            request_log.dump_request(binary_data, kwargs)
        logging.debug("read interdoc")
        pdfinsight_io = io.BytesIO(binary_data)
        pdfinsight_data = json.loads(read_zip_first_file(pdfinsight_io))
        mold = self.build_mold()

        logging.debug("run prompt elments")
        crude_answer = self.predict_crude_answer(mold, pdfinsight_data)

        logging.debug("run predict answers")
        predict_answer = self.predict_answer(mold, pdfinsight_data, crude_answer)

        return {
            "crude_answer": crude_answer,
            "predict_answer": predict_answer,
        }
