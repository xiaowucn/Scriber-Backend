# 两个章节之间的检查

CHAPTERS_TEMPLATES = [
    # {
    #     "label": "template_402",
    #     "related_name": "关联交易",
    #     "name": "合同中关联交易的约定应保持一致",
    #     "from": "20140821 私募投资基金监督管理暂行办法（中国证券监督管理委员会令第105号）",
    #     "origin": "同一私募基金管理人管理不同类别私募基金的，应当坚持专业化管理原则；管理可能导致利益输送或者利益冲突的不同私募基金的，应当建立防范利益输送和利益冲突的机制。",
    #     "diff_suggestion": "请修改十八章中的关联关系、关联交易及利益冲突的内容，与十一章中的关联关系、关联交易及利益冲突的内容保持一致",
    #     "diff_text": "十一章与十八章的关联关系、关联交易及利益冲突的内容不一致",
    #     "left": {
    #         "chapter": [re.compile(r"私募基金的投资"), re.compile(r"关联关系、关联交易及利益冲突")],
    #         "miss_detail": {
    #             "reason_text": "未找到十一章中的关联关系、关联交易及利益冲突",
    #             "miss_content": "十一章中的关联关系、关联交易及利益冲突",
    #         },
    #         "ignore_elements": {
    #             "chapter": {"indexes": [0]},
    #         },
    #     },
    #     "right": {
    #         "chapter": [re.compile(r"风险揭示"), re.compile(r"关联关系、关联交易及利益冲突风险")],
    #         "miss_detail": {
    #             "reason_text": "未找到十八章中的关联关系、关联交易及利益冲突",
    #             "miss_content": "十八章中的关联关系、关联交易及利益冲突风险",
    #         },
    #         "ignore_elements": {
    #             "chapter": {"indexes": [0]},
    #         },
    #     },
    # }
]
