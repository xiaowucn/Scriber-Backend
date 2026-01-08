"""
03 公司章程公告-公司章程
"""

from remarkable.predictor.common_pattern import ZH_NUMBER_CHAR_PATTERN

number_pattern = rf"({ZH_NUMBER_CHAR_PATTERN}|\d)+"
person_number = rf"({ZH_NUMBER_CHAR_PATTERN}+|\s*\d+\s*)[名人]"

independent_director_patterns = [
    rf"独立董事(?P<entity>{person_number})",
    rf"(?P<entity>{person_number})[^，。]*?独立董事",
]

prophet_config = {
    "predictor_options": [
        {
            "path": ["董事人数"],
            "models": [
                {
                    "name": "relation_entity",
                    "relation_pattern": rf"第{ZH_NUMBER_CHAR_PATTERN}+条\s+董事会由{person_number}董事组成",
                    "filter_sentences_use_pattern": False,
                    "entity_options": [
                        {
                            "schema_name": "董事人数",
                            "patterns": [rf"董事会由(?P<entity>{person_number})董事组成"],
                        },
                        {
                            "schema_name": "独立董事人数",
                            "patterns": independent_director_patterns,
                        },
                    ],
                },
            ],
        },
        {
            "path": ["独立董事人数"],
            "models": [
                {
                    "name": "relation_entity",
                    "relation_pattern": rf"第{ZH_NUMBER_CHAR_PATTERN}+条\s+.*?董事会设{person_number}独立董事",
                    "filter_sentences_use_pattern": False,
                    "entity_options": [
                        {
                            "schema_name": "独立董事人数",
                            "patterns": [rf"董事会设(?P<entity>{person_number})独立董事"],
                        },
                    ],
                },
            ],
        },
        {
            "path": ["监事人数"],
            "models": [
                {
                    "name": "relation_entity",
                    "relation_pattern": rf"第{ZH_NUMBER_CHAR_PATTERN}+条\s+.*?监事会由{person_number}监事组成",
                    "filter_sentences_use_pattern": False,
                    "entity_options": [
                        {
                            "schema_name": "监事人数",
                            "patterns": [rf"监事会由(?P<entity>{person_number})监事组成"],
                        },
                    ],
                },
            ],
        },
    ],
}
