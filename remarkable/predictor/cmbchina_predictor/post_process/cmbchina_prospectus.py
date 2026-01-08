import re

from remarkable.predictor.cmbchina_predictor import R_A_Z
from remarkable.predictor.schema_answer import PredictorResult

R_NO_RATE = re.compile(r"不(支付|收取)申购费")


# https://scriber-cmbchina.test.paodingai.com/scriber/#/project/remark/11186?projectId=36&treeId=59&fileId=879&schemaId=2
def post_process_subscription_rate(answers: list[dict[str, list[PredictorResult]]], **kwargs) -> list[dict]:
    """
    处理申购费率数据的后处理逻辑

    业务规则：
    如果答案里面已经有某基金不需要支付申购费，则删除这个基金其他的数据
    通过基金名称中的大写字母（如A、B、C类份额）来识别不同基金

    Args:
        answers: 包含申购费率数据的答案列表
        **kwargs: 额外参数

    Returns:
        list[dict]: 处理后的答案列表
    """
    # 收集所有基金的免费信息
    fund_no_rate_map = {}

    # 第一遍遍历：识别哪些基金不收取申购费
    for index, answer in enumerate(answers):
        if not isinstance(answer, dict):
            continue
        has_no_rate = False
        fund_names_with_letters = []
        # 提取基金名称和申购费信息
        for key, items in answer.items():
            if key == "基金名称":
                # 查找包含大写字母的基金名称（如A类、B类份额）
                for item in items:
                    if R_A_Z.search(item.text):
                        fund_names_with_letters.append(item.text)
            elif key == "申购费":
                # 检查是否包含不收费的描述
                if any(R_NO_RATE.search(item.text) for item in items):
                    has_no_rate = True

        # 如果找到基金名称且该基金不收费，记录基金名称和免费记录的索引
        if fund_names_with_letters and has_no_rate:
            for fund_name in fund_names_with_letters:
                if fund_name not in fund_no_rate_map:
                    fund_no_rate_map[fund_name] = [index]
                else:
                    fund_no_rate_map[fund_name].append(index)

    if not fund_no_rate_map:
        return answers

    # 收集所有免费记录的索引
    no_rate_indices = set()
    for indices_list in fund_no_rate_map.values():
        no_rate_indices.update(indices_list)

    # 收集需要删除的索引（有免费记录的基金的收费记录）
    indices_to_remove = set()

    for index, answer in enumerate(answers):
        if not isinstance(answer, dict):
            continue
        # 如果当前记录是免费记录，跳过
        if index in no_rate_indices:
            continue

        # 检查当前记录的基金是否有免费记录
        fund_name = None
        for key, items in answer.items():
            if key != "基金名称":
                continue
            for item in items:
                if not (match := R_A_Z.search(item.text)):
                    continue
                if any(match.group() in key for key in fund_no_rate_map.keys()):
                    fund_name = item.text
                    break
            if fund_name:
                break

        # 如果该基金有免费记录，标记当前收费记录为删除
        if fund_name:
            indices_to_remove.add(index)

    # 构建过滤后的答案列表
    filtered_answers = [answer for index, answer in enumerate(answers) if index not in indices_to_remove]

    return filtered_answers
