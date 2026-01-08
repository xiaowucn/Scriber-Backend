import pickle
from collections import namedtuple

from remarkable.config import project_root
from remarkable.predictor.models.partial_text import PartialText
from remarkable.predictor.mold_schema import SchemaItem

Predictor = namedtuple('Predictor', ['columns', 'primary_key'])


def test_is_cross_page_para():
    dataset_path = f'{project_root}/data/tests/partial_text_dataset.pkl'
    with open(dataset_path, 'rb') as fb:
        dataset = pickle.load(fb)
    node = dataset['node']
    elements = dataset['elements']
    schema = SchemaItem({}, ['新股申购的金额限制'])
    predictor = Predictor(columns='', primary_key=[])
    partial_text_model = PartialText(options={}, schema=schema, predictor=predictor)
    features = partial_text_model.process_answer_node(node, elements)
    assert len(features) == 1
    assert len(features[0]) == 3
    assert features[0][1].text == '基金财产参与股票发行申购，本基金所申报的金额不超过本基金的总资产'
