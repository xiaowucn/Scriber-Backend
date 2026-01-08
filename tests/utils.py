from unittest.mock import MagicMock

from remarkable.config import create_test_config


def mock_session(handler, data=None):
    if data is None:
        data = {}

    session_manager = MagicMock()
    session_manager.__getitem__.side_effect = data.__getitem__

    handler.__session_manager = session_manager

def mock_get_config(data: dict):
    test_config = create_test_config()
    test_config.merge(data)

    def _inner(key_string: str, default=None):
        return test_config.get(key_string, default)

    return _inner