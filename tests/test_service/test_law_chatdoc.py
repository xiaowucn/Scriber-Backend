from remarkable.service.law_chatdoc import filter_and_transform_tree


def test_filter_and_transform_tree():
    # 1. 定义一个能覆盖所有场景的输入数据
    test_input = [
        {
            "name": "根文件夹A",
            "node_type": 4,
            "children": [
                {"name": "文档A1 (忽略无附件的status -40)", "node_type": 1, "doc_status": -40, "children": []},
                {"name": "文档A2 (移除, status 0)", "node_type": 2, "doc_status": 0, "children": []},
                {
                    "name": "空文档A3 (但因附件而保留)",
                    "node_type": 1,
                    "doc_status": -40,
                    "children": [
                        {"name": "附件A3-1 (保留, status 300)", "node_type": 5, "doc_status": 300, "children": []}
                    ],
                },
            ],
        },
        {
            "name": "根文件夹B (将被完全移除)",
            "node_type": 4,
            "children": [
                {"name": "文档B1 (移除, status 100)", "node_type": 3, "doc_status": 100, "children": []},
                {"name": "附件B2 (移除, status -40)", "node_type": 5, "doc_status": -40, "children": []},
            ],
        },
    ]

    # 2. 定义我们期望得到的、完全精确的输出结果
    expected_output = [
        {
            "children": [
                {
                    "name": "空文档A3 (但因附件而保留)",
                    "node_type": 1,
                    "doc_status": -40,
                    "is_file": True,
                    "is_empty": True,
                    "children": [
                        {"name": "附件A3-1 (保留, status 300)", "node_type": 5, "doc_status": 300, "children": []}
                    ],
                }
            ],
            "is_folder": True,
            "name": "根文件夹A",
            "node_type": 4,
        }
    ]

    # 3. 执行函数并使用 assert 进行断言
    actual_output = filter_and_transform_tree(test_input)

    # assert 会深度比较两个列表/字典，如果不完全相等，测试就会失败
    assert actual_output == expected_output
