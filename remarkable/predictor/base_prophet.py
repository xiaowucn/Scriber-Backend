import json
import logging
import pickle
from collections import defaultdict, namedtuple
from pathlib import Path

from remarkable import config
from remarkable.common.exceptions import ConfigurationError
from remarkable.common.storage import localstorage
from remarkable.config import get_config
from remarkable.pdfinsight.reader import PdfinsightReader
from remarkable.plugins.predict.answer import AnswerReader
from remarkable.predictor.dataset import DatasetItem
from remarkable.predictor.mold_schema import MoldSchema
from remarkable.predictor.predictor import SchemaPredictor

PredictorContext = namedtuple("PredictorContext", ["crude_answer", "reader", "metadata"])
logger = logging.getLogger(__name__)


def find_item_elements(_pdfinsight, item):
    _elements = {}
    for data in item["data"]:
        data.setdefault("elements", [])
        for box in data["boxes"]:
            outline = (box["box"]["box_left"], box["box"]["box_top"], box["box"]["box_right"], box["box"]["box_bottom"])
            for _etype, ele in _pdfinsight.find_elements_by_outline(box["page"], outline):
                _elements[ele["index"]] = ele
                data["elements"].append(ele["index"])
    return _elements


class BaseProphet:
    debug = True
    depends_root_predictor = True

    def __init__(self, prophet_config, mold, version_id=0):
        self.base_dir = Path(get_config("training_cache_dir"))
        self._mold = mold
        self._version_id = str(version_id)
        self.prophet_config = prophet_config
        # self.validate_config()
        self.mold_schema = MoldSchema(mold.data)
        self.predictor_config = self.load_config(prophet_config["predictor_options"])
        self.depends: dict[str, list[str]] = prophet_config.get("depends", defaultdict(list))
        self.answer = defaultdict(list)
        self.predictor_context = None
        # TODO: 需要可以指定 Predictor 实现
        if self.depends_root_predictor:
            self.root_predictor = SchemaPredictor(self.root_schema, {"path": self.root_schema.path}, prophet=self)
        self.answer_version = str(config.get_config("prompter.answer_version", "2.2"))
        self.enum_predictor = self.get_enum_predictor()

    @property
    def predictor_options(self):
        return self.prophet_config["predictor_options"]

    @property
    def root_schema(self):
        return self.mold_schema.root_schema

    @property
    def predictors(self):
        predictors = self.root_predictor.sub_predictors[:]
        high_priority_names = []
        for names in self.depends.values():
            high_priority_names.extend(names)
        predictors.sort(key=lambda x: 0 if x.schema_name in high_priority_names else 100)
        return predictors

    @property
    def dataset_dir(self):
        return self.base_dir.joinpath(f"{self._mold.id}", self._version_id, "answers")

    @property
    def model_data_dir(self):
        return self.base_dir.joinpath(f"{self._mold.id}", self._version_id, "predictors")

    @property
    def crude_answer(self):
        return self.predictor_context.crude_answer

    @property
    def reader(self):
        return self.predictor_context.reader

    @property
    def merge_schema_answers(self):
        return self.prophet_config.get("merge_schema_answers", False)

    @property
    def metadata(self):
        return self.predictor_context.metadata

    def parse_value(self, predictor_result):
        schema = predictor_result.schema
        if self.mold_schema.is_enum_schema(schema):
            return self.parse_enum_value(predictor_result, schema)

        return None

    def parse_enum_value(self, predictor_result, schema):
        raise NotImplementedError

    def get_enum_predictor(self):
        raise NotImplementedError

    @staticmethod
    def _process_answer(answer):
        if not answer:
            return answer
        user_answer = answer["userAnswer"]
        valid_items = []
        for item in user_answer["items"]:
            valid_data = []
            for data in item["data"]:
                boxes = [x for x in data["boxes"] if x["box"]]
                if not boxes:
                    continue
                data["boxes"] = boxes
                valid_data.append(data)
            if not valid_data:
                continue
            item["data"] = valid_data
            valid_items.append(item)
        user_answer["items"] = valid_items
        answer["userAnswer"] = user_answer
        return answer

    def prepare_dataset(self, meta):
        logging.info(f"loading file: {meta['fid']}, qid: {meta['qid']}")
        answer_reader = AnswerReader(self._process_answer(meta["answer"]))
        pdfinsight_path = localstorage.mount(meta["pdfinsight_path"])
        reader = PdfinsightReader(pdfinsight_path)
        root_node = answer_reader._tree
        if not root_node:
            logging.warning(
                f"can't find answer root node for file:{meta['fid']}",
            )
            return
        elements = {}
        for leaf_node in root_node.descendants(only_leaf=True):
            elements.update(find_item_elements(reader, leaf_node.data))
        data_item = DatasetItem(
            answer_reader.main_schema["name"],
            {"elements": elements, "syllabuses": reader.syllabuses},
            answer_reader,
            meta["fid"],
        )
        self.dataset_dir.mkdir(parents=True, exist_ok=True)
        with open(self.dataset_dir.joinpath(f"{meta['qid']}.pkl"), "wb") as file_obj:
            pickle.dump(data_item, file_obj)
        logging.info(f"dataset saved: {meta['fid']}, qid: {meta['qid']}")

    async def run_dump_dataset(self, start, end, tree_l=None):
        from remarkable.predictor.helpers import prepare_prophet_dataset

        files = await prepare_prophet_dataset(self._mold, start, end, vid=self._version_id, prophet=self, tree_l=tree_l)
        return files

    def run_train(self):
        self.prepare_dir(self.model_data_dir)
        self.root_predictor.train()

    def run_predict(self, **kwargs):
        crude_answer = kwargs["crude_answer"]
        pdfinsight_path = kwargs["pdfinsight_path"]
        pdfinsight_data = kwargs.get("pdfinsight_data")

        self.predictor_context = self._bind_context(
            crude_answer, pdfinsight_path, pdfinsight_data=pdfinsight_data, metadata=kwargs.get("metadata")
        )

        self.predict_answer()
        answer_items = self.collect_answer_items()

        return self.build_question_answer(answer_items)

    def validate_config(self):
        try:
            json.dumps(self.prophet_config)
        except TypeError as e:
            raise ConfigurationError("Configuration of prophet must can be serialized by json.dumps") from e

    def add_answer_result(self, path_key, answer_result):
        self.answer[path_key].append(answer_result)

    def get_answer_result(self, path_key):
        return self.answer[path_key]

    def build_question_answer(self, answer_items):
        """Build final answer with current structure."""
        if self.answer_version < "2.2":
            raise NotImplementedError("not implement for answer version under 2.2")

        return self.build_v_2_2_question_answer(answer_items)

    def build_v_2_2_question_answer(self, answer_items):
        schema = {
            "schema_types": self._mold.data.get("schema_types", []),
            "schemas": self._mold.data.get("schemas", []),
            "version": self._mold.checksum,
        }

        answer = {"schema": schema, "userAnswer": {"version": "2.2", "items": answer_items}}
        return answer

    def collect_answer_items(self):
        items = []
        for answer_results in self.answer.values():
            for result in answer_results:
                items.append(result.answer)
        return items

    @staticmethod
    def gen_answer_key(answer, index):
        if isinstance(answer["key"], str):
            key_path = json.loads(answer["key"])
        else:
            key_path = answer["key"]
        result = [f"{i}:0" for i in key_path[:-1]] + [f"{key_path[-1]}:{index}"]
        return json.dumps(result, ensure_ascii=False)

    def predict_answer(self):
        tree_answer = self.root_predictor.predict()
        tree_answer = self.revise_answer(tree_answer)
        for path_key, answer_items in tree_answer.items():
            for item in answer_items:
                self.add_answer_result(path_key, item)

    def load_config(self, predictor_options):
        root_path = [self.root_schema.name]
        return {json.dumps(root_path + item["path"], ensure_ascii=False): item for item in predictor_options}

    @classmethod
    def prepare_dir(cls, directory):
        directory.mkdir(parents=True, exist_ok=True)

    @staticmethod
    def _bind_context(crude_answer, pdfinsight_path, pdfinsight_data=None, metadata=None):
        if not pdfinsight_data:
            pdfinsight_path = localstorage.mount(pdfinsight_path)
        else:
            pdfinsight_path = None
        reader = PdfinsightReader(pdfinsight_path, data=pdfinsight_data)
        logger.info("========interdoc model_version========")
        for key, value in reader.data["model_version"].items():
            logger.info(f"{key}: {value}")

        return PredictorContext(crude_answer, reader, metadata)

    @staticmethod
    def post_process(preset_answer):
        return preset_answer

    def revise_answer(self, tree_answer):
        return tree_answer


class PredictorV1ProphetAdapter(BaseProphet):
    depends_root_predictor = False

    def __init__(self, mold, version_id=0, **kwargs):
        super().__init__({"predictor_options": {}}, mold, version_id=version_id)
        predictor = self._create_v1_predictor(vid=self._version_id, **kwargs)
        self.predictor_config = getattr(predictor, "predictor_config", [])

    @property
    def predictor_options(self):
        return self.predictor_config

    def _create_v1_predictor(self, *args, **kwargs):
        from remarkable.predictor.predict import AnswerPredictorFactory

        predictor = AnswerPredictorFactory.create(self._mold, *args, **kwargs)
        return predictor

    def run_predict(self, crude_answer, pdfinsight_path, **kwargs):
        _file = kwargs.get("file")
        metadata = kwargs.get("metadata")
        predictor = self._create_v1_predictor(
            _file,
            crude_answer,
            metadata,
            vid=self._version_id,
            anno_mold=kwargs.get("anno_mold"),
            anno_crude_answer=kwargs.get("anno_crude_answer"),
        )

        if predictor:
            # TODO: predictor init
            answer = predictor.predict_answer()
        else:
            answer = None
        return answer

    def run_train(self):
        predictor = self._create_v1_predictor(vid=self._version_id)
        predictor.train()

    async def run_dump_dataset(self, start, end, tree_l=None):
        from remarkable.plugins.predict.predictor import dump_dataset

        predictor = self._create_v1_predictor(vid=self._version_id)
        files = await dump_dataset(self._mold.id, start, end, predictor.predictor, vid=self._version_id, tree_l=tree_l)
        return files

    def get_enum_predictor(self):
        pass

    def parse_enum_value(self, predictor_result, schema):
        pass
