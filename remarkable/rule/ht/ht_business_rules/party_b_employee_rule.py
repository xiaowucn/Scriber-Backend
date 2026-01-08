import json
import re

from remarkable.common.constants import ComplianceStatus
from remarkable.rule.common import get_texts_map
from remarkable.rule.ht.ht_business_rules.common import party_employee_regs
from remarkable.rule.ht.ht_business_rules.result import get_diff_res, get_xpath
from remarkable.rule.rule import LegacyRule


class PartyBEmployeeRule(LegacyRule):
    """
    乙方的权利和义务 乙方项目人员 需包含如下安全生产相关条款
    """

    def __init__(self):
        super(PartyBEmployeeRule, self).__init__("固定条款对比")
        self.cols = {
            "partyb_employee_safety": "乙方项目人员-安全生产相关条款",
        }

        self.patterns = {
            "乙方项目人员-应急处理原条款": re.compile(
                r"""^[1234567890一二三四五六七八九十、（）\(\)\s]*乙方项目人员必须严格遵守安全生产法律、法规、标准、安全生产规章制度和操作规程，熟练掌握事故防范措施和事故应急处理预案。""",
                re.X | re.I,
            ),
            "乙方项目人员-人员专业性条款": re.compile(
                r"""^[1234567890一二三四五六七八九十、（）\(\)\s]*乙方必须对其项目人员进行安全教育和安全技术培训，使其掌握履行本合同必备的安全知识，熟练操作安全操作规程，经安全生产技术考核合格后，
            方可进行上岗作业。对经培训考核不合格、安全技能不具备或者不适应所在岗位要求的乙方项目人员，甲方有权要求乙方予以更换。""",
                re.X | re.I,
            ),
            "乙方项目人员-消防安全条款": re.compile(
                r"""^[1234567890一二三四五六七八九十、（）\(\)\s]*乙方项目人员必须配合甲方做好消防安全工作，消除麻痹思想，.*?按时参加防火灾及安全疏散应急演练，确保消防安全专项工作取得实效。""",
                re.X | re.I,
            ),
            "乙方项目人员-安全培训条款": re.compile(
                r"""^[1234567890一二三四五六七八九十、（）\(\)\s]*乙方必须配合甲方加强安全培训教育工作，强化人员安全意识。乙方每年应对项目人员进行至少一次安全培训。""",
                re.X | re.I,
            ),
            "乙方项目人员-网络安全条款": re.compile(
                r"""^[1234567890一二三四五六七八九十、（）\(\)\s]*乙方项目人员必须配合甲方按年度网络安全意识教育计划向每位员工科普网络安全知识，增强员工网络安全意识，并提高网络安全技能。""",
                re.X | re.I,
            ),
            "乙方项目人员-安全规定条款": re.compile(
                r"""^[1234567890一二三四五六七八九十、（）\(\)\s]*甲方对乙方人员执行规章制度及履行安全职责情况，有权进行检查、监督、考核。凡不遵守安全规定的，违反安全操作规程的项目人员，
            及时进行纠正、处罚，直至停止其工作并要求乙方予以更换。""",
                re.X | re.I,
            ),
        }

    def check(self, question, pdfinsight):
        specific_num = get_texts_map(self.cols, question, need_split=True)
        ret = []
        ele_info = specific_num["partyb_employee_safety"]
        if not ele_info["texts"]:
            return ret
        texts = ele_info["texts"].split("\n")
        extract_ret = {k: {} for k, v in self.patterns.items()}
        for text in texts:
            if not text:
                continue
            for key, reg in party_employee_regs.items():
                if reg.search(text):
                    extract_ret[key]["diff_detail"] = {"text_diff": get_diff_res(text, self.patterns[key])}
                    break
        detail = {}
        comment_list = []
        result = ComplianceStatus.COMPLIANCE.value
        for key, extract_info in extract_ret.items():
            if extract_info:
                diff_detail = extract_info["diff_detail"]["text_diff"]
                if all(not i for i in diff_detail.values()):
                    comment_list.append(f"{key}正确")
                else:
                    comment_list.append(f"与模板有差异：{key}")
                    detail.update({key: diff_detail})
                    result = ComplianceStatus.NONCOMPLIANCE.value
            else:
                comment_list.append(f"缺少：{key}")

                result = ComplianceStatus.NONCOMPLIANCE.value
        detail.update({"label_info": json.dumps(comment_list, ensure_ascii=False)})
        ret.append(
            (
                [
                    ele_info.get("schema_key", ""),
                ],
                result,
                json.dumps(comment_list, ensure_ascii=False),
                {"xpath": get_xpath(ele_info, pdfinsight)},
                "乙方项目人员-安全生产相关条款",
                detail,
            )
        )
        return ret
