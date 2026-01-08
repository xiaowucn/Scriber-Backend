import re

from remarkable.common.pattern import PatternCollection


class TestPatternCollection:
    def test_compile(self):
        p_list = [None, '', re.compile(r'hello'), ['a', None, 'b']]
        expected_list = [re.compile(r''), re.compile(r'hello'), re.compile(r'a'), re.compile(r'b')]
        assert expected_list == PatternCollection(p_list).pattern_objects

    def test_nexts(self):
        text = 'hello world!'
        match = PatternCollection('w').nexts(text)
        assert match
        assert match.group() == 'w'

    def test_match(self):
        text = 'hello world!'
        assert not list(PatternCollection('w').match(text))
        assert list(PatternCollection(['w', 'h']).match(text))

    def test_finditer(self):
        text = 'helloworld'
        expected_list = ['h', 'e', 'l', 'l', 'l', 'l', 'l', 'l', 'o', 'o', 'w', 'o', 'o', 'r', 'l', 'l', 'l', 'd']
        assert expected_list == [p.group() for p in PatternCollection(list(text)).finditer(text)]

    def test_sub(self):
        text = 'hello world'
        assert PatternCollection(['h', 'w', 'o', ' ']).sub('1', text) == '1ell1111rld'
