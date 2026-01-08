from remarkable.answer.node import AnswerItem


def test_answer_item():
    ans_item = AnswerItem(data=[1], key='key', text='text')
    assert ans_item.data == [1]
    assert ans_item['key'] == 'key'
    assert ans_item['text'] == 'text'
    assert ans_item.key == 'key'
    assert ans_item.text == 'text'
    ans_item.value = 'value'
    assert ans_item['value'] == 'value'
    assert ans_item.plain_text == 'value'
    ans_item.plain_text = 'new_text'
    assert ans_item.plain_text == 'new_text'

    ans_item_1 = AnswerItem(item={'text': '1'})
    assert ans_item_1.data == []
    assert ans_item_1['data'] == []
    assert ans_item_1.text == '1'
    assert ans_item_1.plain_text == '1'
    ans_item = ans_item + ans_item_1
    assert ans_item.plain_text == 'new_text\n1'
