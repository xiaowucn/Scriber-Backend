from unittest import TestCase

import attr

from remarkable.plugins.cgs.common.utils import format_suggestion


@attr.s
class Manager:
    schema_items = ['基金名称', '管理人姓名']
    mapping = attr.ib()

    def get(self, name):
        return self.mapping.get(name)

    def is_schema_field(self, name):
        return name in self.schema_items


@attr.s
class Answer:
    answer = attr.ib()
    chapter_title = attr.ib()
    value = attr.ib()


TEST_CASES = [
    {
        'content': 'ABC[基金名称][position]，建议：请修改。',
        'manager': Manager(
            {
                '基金名称': Answer(True, '章节名称', '章节内容'),
            }
        ),
        'assert': 'ABC章节名称，建议：请修改。',
    },
    {
        'content': 'ABC[基金名称][position]，建议：请修改。[基金名称][position]，不能包含敏感字',
        'manager': Manager(
            {
                '基金名称': Answer(True, '章节名称', '章节内容'),
            }
        ),
        'assert': 'ABC章节名称，建议：请修改。章节名称，不能包含敏感字',
    },
    {
        'content': 'ABC[基金名称][position]，建议：请修改。',
        'manager': Manager(
            {
                '基金名称': Answer(False, None, None),
            }
        ),
        'assert': None,
    },
    {
        'content': 'ABC[管理人姓名][position]，建议，请修改。[基金名称][paragraph]：建议：不能包含敏感字。[基金名称][position]：建议：不能包含敏感字',
        'manager': Manager(
            {
                '管理人姓名': Answer(True, '管理人姓名-章节', '管理人姓名-内容'),
                '基金名称': Answer(True, '基金名称-章节', '基金名称-内容'),
            }
        ),
        'assert': 'ABC管理人姓名-章节，建议，请修改。基金名称-内容：建议：不能包含敏感字。基金名称-章节：建议：不能包含敏感字',
    },
    {
        'content': 'ABC[管理人姓名][position]，建议，请修改。[基金名称][paragraph]：建议：不能包含敏感字。[基金名称][paragraph]：建议：不能包含敏感字',
        'manager': Manager(
            {
                '管理人姓名': Answer(True, '管理人姓名-章节', '管理人姓名-内容'),
                '基金名称': Answer(True, '基金名称-章节', '基金名称-内容'),
            }
        ),
        'assert': 'ABC管理人姓名-章节，建议，请修改。基金名称-内容：建议：不能包含敏感字。基金名称-内容：建议：不能包含敏感字',
    },
    {
        'content': 'ABC[管理人姓名][position]，建议，请修改。[基金名称][paragraph]：建议：不能包含敏感字。[基金名称][reserved]：建议：不能包含敏感字.[基金名称1][position]：建议：不能包含敏感字',
        'manager': Manager(
            {
                '管理人姓名': Answer(True, '管理人姓名-章节', '管理人姓名-内容'),
                '基金名称': Answer(True, '基金名称-章节', '基金名称-内容'),
            }
        ),
        'assert': 'ABC管理人姓名-章节，建议，请修改。基金名称-内容：建议：不能包含敏感字。[基金名称][reserved]：建议：不能包含敏感字.[基金名称1][position]：建议：不能包含敏感字',
    },
]


class TestCgsFormatSuggestion(TestCase):
    def test_format_suggestion(self):
        for case in TEST_CASES:
            formatted = format_suggestion(case['content'], case['manager'])
            self.assertEqual(case['assert'], formatted)
