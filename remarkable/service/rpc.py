import json
import logging
import os
from io import BytesIO
from typing import Any
from zipfile import ZipFile

from aipod.model import AIModelBase
from aipod.rpc.client import AIClient

from remarkable.common.constants import RPCTaskType
from remarkable.common.storage import localstorage
from remarkable.common.util import import_class_by_path
from remarkable.config import get_config
from remarkable.models.new_file import NewFile
from remarkable.pdfinsight.reader import PdfinsightReader
from remarkable.predictor.base_prophet import BaseProphet
from remarkable.prompter.builder import AnswerPrompterBuilder
from remarkable.prompter.element import element_info
from remarkable.prompter.impl.v2 import AnswerPrompterV2
from remarkable.pw_models.model import NewMold
from remarkable.pw_models.question import NewQuestion


def extract_bin_data(binary_data):
    if not binary_data:
        return {}
    with ZipFile(BytesIO(binary_data), "r") as zip_file:
        for name in zip_file.namelist():
            if name == "meta":
                data = zip_file.read(name)
                if isinstance(data, bytes):
                    data = data.decode("utf-8")
                meta = json.loads(data)
            else:
                path = os.path.join(name[:2], name[2:])
                if not localstorage.exists(path):
                    localstorage.write_file(path, zip_file.read(name))
    return meta


def pack_bin_data(data_pairs: list[tuple[str, dict | bytes]]) -> bytes:
    res = BytesIO()
    for name, data in data_pairs:
        with ZipFile(res, "w") as res_fp:
            if name == "meta":
                res_fp.writestr(name, json.dumps(data).encode("utf-8"))
            else:
                res_fp.writestr(name, data)
    res.seek(0)
    return res.read()


def wrap_run_predict(instance: BaseProphet, **kwargs):
    rpc_address = get_config("prompter.rpc_address")
    if not rpc_address:
        raise Exception("need model server address: prompter.rpc_address")
    model = AIClient(address=rpc_address, version=kwargs.get("vid", 0))
    data_pairs = [
        (kwargs["file"].pdfinsight, localstorage.read_file(kwargs["file"].pdfinsight_path())),
        ("meta", {k: v.to_dict() if hasattr(v, "to_dict") else v for k, v in kwargs.items()}),
    ]
    return model.predict(
        binary_data=pack_bin_data(data_pairs),
        task_type=RPCTaskType.PREDICTOR,
        prophet_config=instance.prophet_config,
        class_path=f"{instance.__module__}.{instance.__class__.__name__}",
    )


def wrap_gen_rule_result(instance, doc: NewFile, question: NewQuestion, mold: NewMold) -> list:
    rpc_address = get_config("prompter.rpc_address")
    if not rpc_address:
        raise Exception("need model server address: prompter.rpc_address")
    model = AIClient(address=rpc_address, version=0)
    data_pairs = [("meta", {"doc": doc.to_dict(), "question": question.to_dict(), "mold": mold.to_dict()})]
    if doc.pdfinsight_path():
        data_pairs.append((doc.pdfinsight, localstorage.read_file(doc.pdfinsight_path())))
    return model.predict(
        binary_data=pack_bin_data(data_pairs),
        task_type=RPCTaskType.INSPECTOR,
        class_path=f"{instance.__module__}.{instance.__class__.__name__}",
    )


class AnswerPrompterBuilderRPC(AnswerPrompterBuilder):
    def load(self):
        return AnswerPrompterRPC(self.schema_id, self.vid)


class AnswerPrompterRPC(AnswerPrompterV2):
    def __init__(self, schema_id, vid=0):
        super(AnswerPrompterRPC, self).__init__(schema_id, vid)
        rpc_address = get_config("prompter.rpc_address")
        if not rpc_address:
            raise Exception("need model server address: prompter.rpc_address")
        self.model = AIClient(address=rpc_address, version=str(vid))

    def prompt_all(self, pdfinsight_path, **kwargs):
        file_id = kwargs.get("file_id") or 0
        prompt_result = {}
        reader = PdfinsightReader(pdfinsight_path, data=kwargs.get("pdfinsight_data"))
        if not self.elements(reader):
            logging.warning(f"empty pdfinsight {file_id}")
            return prompt_result
        doc_elements = {e.get("index"): element_info(e.get("index"), e, reader, {}) for e in self.elements(reader)}
        res = self.model.predict(
            binary_data=pack_bin_data([("meta", {"dict_data": {file_id: doc_elements}})]),
            task_type=RPCTaskType.PROMPTER,
            mold_id=self.schema_id,
            vid=self.vid,
            pred_start=file_id,
            pred_end=file_id,
            use_syllabuses=get_config("prompter.use_syllabuses", True),
            tokenization=(get_config("prompter.tokenization") or None),
            context_length=get_config("prompter.context_length", 1),
            rules_use_post_process=(get_config("prompter.post_process") or []),
            separate_paragraph_table=get_config("prompter.separate_paragraph_table", True),
        )
        if not res:
            return prompt_result

        for aid, items in res.get(file_id, {}).items():
            prompt_result[aid] = []
            for item in items:
                etype, ele = reader.find_element_by_index(item["element_index"])
                prompt_result[aid].append((item["score"], ele, [], etype))

        return prompt_result


class PIPELine(AIModelBase):
    def train(self, binary_data: bytes = None, **kwargs) -> Any:
        pass

    def __init__(self, version=None, datapath=None, **kwargs):
        if datapath is None:
            datapath = get_config("training_cache_dir")
        super(PIPELine, self).__init__(version, datapath, **kwargs)

    def predict(self, binary_data=None, **kwargs):
        task_type = kwargs.pop("task_type", RPCTaskType.PROMPTER)
        meta = extract_bin_data(binary_data)
        kwargs.update(meta)
        if task_type == RPCTaskType.PROMPTER:
            return self.do_prompt(**kwargs)
        if task_type == RPCTaskType.PREDICTOR:
            return self.do_predict(**kwargs)
        if task_type == RPCTaskType.INSPECTOR:
            return self.do_inspect(**kwargs)
        return None

    @staticmethod
    def do_prompt(**kwargs):
        from remarkable.prompter.utils import pred

        mold_id = kwargs.pop("mold_id")
        vid = kwargs.pop("vid")
        return pred(mold_id, vid, **kwargs)

    @staticmethod
    def do_predict(**kwargs):
        class_path = kwargs.pop("class_path", "remarkable.predictor.default_predictor.utils")
        clazz: BaseProphet = import_class_by_path(class_path)
        if not clazz:
            raise Exception(f'import module failed: "{class_path}"')
        prophet = clazz(kwargs.pop("prophet_config"), NewMold(**kwargs.pop("mold")), kwargs.pop("vid"))
        return prophet.run_predict(file=NewFile(**kwargs.pop("file")), **kwargs)

    @staticmethod
    def do_inspect(**kwargs):
        class_path = kwargs.pop("class_path")
        clazz = import_class_by_path(class_path)
        if not clazz:
            raise Exception(f'import module failed: "{class_path}"')
        return clazz().gen_rule_result(
            NewFile(**kwargs.pop("doc")), NewQuestion(**kwargs.pop("question")), NewMold(**kwargs.pop("mold"))
        )
