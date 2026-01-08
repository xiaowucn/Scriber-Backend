import logging
import re
from typing import Literal

from jinja2.sandbox import SandboxedEnvironment
from openai.lib._pydantic import to_strict_json_schema  # noqa

from remarkable.routers.schemas import RepairLLMSchem
from remarkable.routers.schemas.law import (
    ContractComplianceResultLLMS,
    RuleCheckPointBaseLLMS,
    RuleCheckPointsLLMS,
    RuleFocusLLMS,
    RuleKeywordsSchema,
)
from remarkable.service.chatgpt import AsyncOpenAIClient
from remarkable.utils.split_law import P_SECTION_TIAO

logger = logging.getLogger(__name__)


json_schema_stuff = """

输出json_schema:
{{ json_schema }}
"""


def render_prompt(prompt_tpl, data, json_schema=None):
    env = SandboxedEnvironment()
    if json_schema:
        prompt_tpl = f"{prompt_tpl}{json_schema_stuff}"
        data["json_schema"] = to_strict_json_schema(json_schema)
    template = env.from_string(prompt_tpl)
    return template.render(**data)


rule_scenario_prompt = """请帮我从场景列表中选择法规的全部适用场景

场景列表: {{ scenarios }}
法规: {{ rule_content }}
"""


async def determine_rules_scenarios(rules: list[str], scenarios: list[str]) -> list[list[str]]:
    scenario_literal = Literal[tuple(scenarios)]

    class RuleScenariosLLMS(RepairLLMSchem):
        scenarios: list[scenario_literal]

    result = []
    openai_client = AsyncOpenAIClient()
    for rule in rules:
        content = render_prompt(
            rule_scenario_prompt,
            {
                "rule_content": rule,
                "scenarios": ",".join(scenarios),
            },
            json_schema=RuleScenariosLLMS,
        )
        messages = [{"role": "user", "content": content}]
        gpt_res = ""
        try:
            gpt_res = await openai_client.send_message(messages, response_format_type="json_object")
            schema = RuleScenariosLLMS.model_validate_json(gpt_res)
            result.append(schema.scenarios)
        except Exception as e:
            logger.exception(e)
            logger.info(gpt_res)
            result.append([])
    return result


rule_keywords_prompt = """你是金融行业相关法律法规资深人事, 帮我找出法规中关键词, 用来搜索相关合同文本

规则文本: {{ rule_content }}

请输出为关键词列表
"""


async def extract_rule_keywords(rule_content):
    content = render_prompt(rule_keywords_prompt, {"rule_content": rule_content}, json_schema=RuleKeywordsSchema)
    messages = [{"role": "user", "content": content}]
    openai_client = AsyncOpenAIClient()
    gpt_res = ""
    try:
        gpt_res = await openai_client.send_message(messages, response_format_type="json_object")
        res = RuleKeywordsSchema.model_validate_json(gpt_res)
    except Exception as e:
        logger.exception(e)
        logger.info(gpt_res)
        res = []
    return res


rule_focus_area_prompt = """
你需要从以下单条法规条款中，{{ method }}与{{ scenario }}合规相关的“关注领域/条款类型”（如“信息披露”），并为每个领域关联具体的行业风险。具体要求如下：

### 一、任务目标
基于{{ scenario }}监管的行业常识（如“信息披露缺失可能被监管处罚”），从给定的单条法规条款中{{ method }}核心约束内容，按“领域/条款类型”分类，并说明该条款对应的行业风险。

### 二、输入内容
法规名称:《{{ law_name }}》
法规条款： {{ rule_content }}
法规场景: {{ scenario }}


### 三、分析规则（需严格遵循）
#### 1. 提取核心约束内容
从单条条款中提取以下信息：
- 约束对象（如“{{ scenario }}管理人”“投资者”）；
- 核心要求（如“初始实缴规模≥1000万元”“不得短期赎回规避”）；
- 约束类型（禁止性/程序性/义务性）。

#### 2. 关联行业风险（基于模型内置知识）
根据{{ scenario }}行业的常见风险（如“信息披露风险”），将提取的核心约束内容与风险点匹配，判断其对应的行业风险。

#### 3. 生成关注领域
将核心约束内容归纳为更上层的领域/条款类型（如“投资者适当性管理”）。

### 四、输出格式（严格按JSON输出）
"""


async def analysis_rule_focus_area(rule, limit=False):
    content = render_prompt(
        rule_focus_area_prompt,
        {
            "scenario": "、".join(m.scenario.name for m in rule.rule_scenarios),
            "law_name": rule.order.name,
            "rule_content": rule.content,
            "method": "总结一条" if limit else "提取",
        },
        json_schema=RuleFocusLLMS,
    )
    messages = [{"role": "user", "content": content}]
    openai_client = AsyncOpenAIClient()
    gpt_res = ""
    try:
        gpt_res = await openai_client.send_message(messages, response_format_type="json_object")
        res = RuleFocusLLMS.model_validate_json(gpt_res)
    except Exception as e:
        logger.exception(e)
        logger.info(gpt_res)
        res = None
    return res


split_check_rule_prompt = """你需要基于以下信息，将法规《{{ law_name }}》的一条法规内容拆分为可执行的审核点，用于后续{{ scenario }}场景相关合同的合规审核；具体要求如下：

### 一、输入信息

- 法规名称:《{{ law_name }}》
- 法规条款： {{ rule_content }}

- 关注领域：
  1. {{ focus_name }}
- 核心要求：
  1. {{ focus_core }}
- 风险关联：
  1. {{ focus_risk }}

### 二、任务目标
从法规中提取与[关注领域]强相关的条款，拆分为审核点，每个审核点需包含以下信息：
- 法规依据（条款原文）；
- 审核点类型（禁止性/程序性/义务性）；
- 行为主体（约束对象，如“私募基金管理人”“投资者”）；
- 核心要求（需遵守的具体行为，需与输入的“核心要求”绑定）；
- 验证方式（审核时如何检查合规，需关联“风险关联”）；
- 排除原因（若条款不拆分，需说明原因）。

### 三、分析规则（模型需严格遵循）
#### 1. 定位关联条款
从法规中定位与[关注领域]直接相关的条款（如“初始实缴规模”“投资者赎回限制”“清算程序”等）。

#### 2. 匹配审核点类型
根据条款内容，判断其类型（禁止性/程序性/义务性）：
- 禁止性条款：法规中包含“不得”“禁止”等否定词，要求主体不做某事；
- 义务性条款：法规中包含“应当”“必须”等肯定词，要求主体做某事；
- 程序性条款：法规中规定行为流程、时限或形式（如“需在…前完成”“应通过…方式”）。

#### 3. 设计验证方式
验证方式需与[风险关联]绑定，确保审核能直接降低风险（如“检查合同是否约定初始实缴≥1000万元”对应“规模不足风险”）。

#### 4. 排除无关条款
若条款与[关注领域]无直接关联（如“争议解决方式”），标注“无”并说明原因。

### 四、输出格式（严格按JSON输出）
"""


async def split_rule_check_point(area, focus_point):
    content = render_prompt(
        split_check_rule_prompt,
        {
            "law_name": area.law_name,
            "rule_content": area.rule_content,
            "scenario": area.scenario,
            "focus_name": focus_point.focus_name,
            "focus_core": focus_point.focus_core,
            "focus_risk": focus_point.focus_risk,
        },
        json_schema=RuleCheckPointsLLMS,
    )
    messages = [{"role": "user", "content": content}]
    openai_client = AsyncOpenAIClient()
    gpt_res = ""
    try:
        gpt_res = await openai_client.send_message(messages, response_format_type="json_object")
        schema = RuleCheckPointsLLMS.model_validate_json(gpt_res)
        prefix_match = re.match(P_SECTION_TIAO, area.rule_content)
        if prefix_match:
            prefix = prefix_match.group("tiao")
            for check_point in schema.check_points:
                if re.match(P_SECTION_TIAO, check_point.rule_content):
                    check_point.rule_content = P_SECTION_TIAO.sub(r"\g<tiao>　", check_point.rule_content)
                else:
                    check_point.rule_content = f"{prefix}　{check_point.rule_content}"
        res = schema.check_points
    except Exception as e:
        logger.exception(e)
        logger.info(gpt_res)
        res = []
    return res


fill_template_check_rule_prompt = """### 一、任务目标
基于范文，总结核心约束内容和领域名称

### 二、输入内容
范文：
{{ rule_content }}

### 三、分析规则（模型需严格遵循）
#### 1. 提取核心约束内容
从范文中总结出以下信息：
- 约束对象：通过范文总结，如“私募基金管理人”“投资者”，需要唯一；
- 约束类型：禁止性/义务性/程序性，需要唯一；
- 领域名称：通过范文总结一个简单的名称；

输出格式（严格按JSON输出）
"""


async def fill_template_check_rule(rule):
    content = render_prompt(
        fill_template_check_rule_prompt,
        {
            "rule_content": rule.content,
        },
        json_schema=RuleCheckPointBaseLLMS,
    )
    messages = [{"role": "user", "content": content}]
    openai_client = AsyncOpenAIClient()
    gpt_res = ""
    try:
        gpt_res = await openai_client.send_message(messages, response_format_type="json_object")
        schema = RuleCheckPointBaseLLMS.model_validate_json(gpt_res)
        res = schema.row_data()
    except Exception as e:
        logger.exception(e)
        logger.info(gpt_res)
        res = {
            "name": "",
            "subject": "",
            "check_type": 0,
        }
    return res


contract_analysis_default_prompt = """请根据以下法规条款分析合同内容，找出相关的原文片段：

法规条款：{{ content }}

{% if keywords %}
关键字： {{ keywords }}
{% endif %}
{% if scenarios %}
适用场景：{{ scenarios }}
{% endif %}

请在合同中找出与此法规条款相关的内容，输出具体的原文片段。"""


def build_contract_analysis_question(law_rule):
    prompt_template = law_rule.prompt or contract_analysis_default_prompt
    scenarios = ", ".join([scenario.name for scenario in law_rule.scenarios])

    question = render_prompt(
        prompt_template, {"content": law_rule.content, "keywords": law_rule.keywords, "scenarios": scenarios}
    )

    return question


contract_compliance_check_prompt = """你需要基于以下已拆分的审核点，审核用户提供的文档片段是否合规。审核点的类型（禁止性/程序性/义务性）决定了审核的核心逻辑和验证方向，请严格按类型对应的规则执行审核。具体要求如下：

---

### **一、任务目标**
根据给定的审核点（包含法规依据、类型、行为主体、核心要求、验证方式），检查用户提供的合同片段是否满足所有相关审核点的要求。审核点的类型（禁止性/程序性/义务性）将直接决定审核的**关注方向**和**验证规则**，需严格按类型逻辑执行判断，输出合规性结论及依据。

---

### **二、输入内容**
#### 1. 法规信息
法规名称: {{ law_name }}

#### 2. 审核点列表
{% for check_point in check_points %}
**审核点ID({{ check_point.id }}):**
- 审核点名称: {{ check_point.name }}
- 条款原文: {{ check_point.rule_content }}
- 类型: {{ check_point.check_type }}
- 行为主体: {{ check_point.subject }}
- 核心要求: {{ check_point.core }}
- 验证方式: {{ check_point.check_method }}
{% endfor %}

#### 3. 待审核的合同片段
{% for content in contents %}
**合同内容:**
{{ content }}

{% endfor %}

---

### **三、审核逻辑说明（类型的核心作用）**
审核点的“类型”字段（禁止性/程序性/义务性）是本次审核的**核心逻辑开关**，具体作用如下：

| **类型**    | **审核逻辑方向**                                            | **验证重点** |
|------------|-----------------------------------------------------------|-----------------------------------------------------------------------------|
| **禁止性**  | 检查合同是否存在“禁止行为”或“违反禁止要求”的内容（如“不得做某事”）。  | 合同中是否包含禁止性表述（如“初始实缴≥1000万元”）；是否存在违反禁止的行为（如“初始实缴800万元”“短期赎回”）。|
| **程序性**  | 检查合同是否“规定了正确的流程或时限”（如“应该怎么做”）。            | 合同中是否明确了流程步骤（如“停止申购→清算”）；是否规定了时限（如“5个工作日内披露”）。  |
| **义务性**  | 检查合同是否“必须履行某类义务”（如“应当做某事”）。                 | 合同中是否明确规定了必须履行的义务（如“管理人需在5个工作日内披露”）；是否遗漏义务条款。  |

---

### **四、输出格式（严格按JSON输出，无额外解释）**
"""


async def check_contract_compliance(check_points, contents, law_name):
    content = render_prompt(
        contract_compliance_check_prompt,
        {
            "law_name": law_name,
            "check_points": check_points,
            "contents": contents,
        },
        json_schema=ContractComplianceResultLLMS,
    )

    messages = [{"role": "user", "content": content}]
    openai_client = AsyncOpenAIClient()

    gpt_res = await openai_client.send_message(messages, response_format_type="json_object")
    try:
        res = ContractComplianceResultLLMS.model_validate_json(gpt_res)
    except Exception as e:
        logger.error(gpt_res)
        raise e
    for check_point in res.check_points:
        if "片段" in check_point.judgment_basis:
            format_prompt = f"移除下面文本中`片段`编号等相关字样，使语句通顺后返回。(可移除不必要部分)\n\n{check_point.judgment_basis}"
            _res = await openai_client.send_message(
                [{"role": "user", "content": format_prompt}], response_format_type="json_object"
            )
            logger.info(f"rm 片段:\nin: {check_point.judgment_basis}\nout: {_res}")
            check_point.judgment_basis = _res
    return res


contract_integrity_check_prompt = """你是一位专业的合同条款完整性核查助手，需基于用户提供的「已匹配内容」「上方未匹配内容」「下方未匹配内容」三部分信息，系统检查已匹配内容的完整性（重点验证主/子序号连续性及段落覆盖度），并明确输出已匹配内容缺失的具体条款。

一、输入结构说明
• 已匹配内容（用户标记为「已核对」的连续条款片段（可能包含完整主序号+子序号，或主序号下的部分子序号））：```
{% for para in paras -%}
{{ para["text"] }}
{% endfor %}```

• 上方未匹配内容（已匹配内容之前未被核对的条款（位于已匹配内容的上方））：```
{% for para in top_paras -%}
{{ para["text"] }}
{% endfor %}```

• 下方未匹配内容（已匹配内容之后未被核对的条款（位于已匹配内容的下方））：```
{% for para in bottom_paras -%}
{{ para["text"] }}
{% endfor %}```

二、核心检查逻辑（需逐项验证）
1. 主序号连续性验证
• 目标：确认已匹配内容的主序号在全文中是否形成连续序列（即：上方未匹配的最后一个主序号 → 已匹配内容的主序号 → 下方未匹配的第一个主序号 是否无断裂）。
• 操作：提取上方未匹配内容的最大主序号（如（一））、已匹配内容的主序号（如（二））、下方未匹配内容的最小主序号（如（三）），检查是否满足「（一）→（二）→（三）」的连续递增关系。若存在跳跃（如上方是（一），已匹配是（三），缺失（二）），则记录主序号缺失。

2. 子序号连续性验证（针对已匹配内容的主序号）
• 目标：确认已匹配内容的主序号下，子序号是否完整（即：已匹配子序号的起始→结束是否与全文中该主序号下的子序号范围一致）。
• 操作：
  a. 提取已匹配内容主序号（如（二））下的子序号范围（如1.、2.）；
  b. 提取全文中该主序号下的完整子序号范围（需结合上方未匹配内容中该主序号的子序号 + 已匹配内容的子序号 + 下方未匹配内容中该主序号的子序号）；
  c. 对比已匹配子序号范围与全文子序号范围，若已匹配子序号未覆盖全文范围（如全文（二）下子序号应为1.、2.、3.、4.，但已匹配仅包含1.、2.，且3.、4.出现在下方未匹配内容中），则记录子序号缺失。

3. 段落覆盖度验证
• 目标：确认已匹配内容是否遗漏了其主序号下应有的关键条款（即使子序号连续，也可能存在条款内容缺失）。
• 操作：对比已匹配内容的条款文本与全文中该主序号下的完整条款文本（结合上下文未匹配内容），若存在关键信息缺失（如条款中关于「比例」「期限」等核心要素未在已匹配内容中体现），则记录段落覆盖缺失。

输出要求（需明确缺失内容）
1. 输出结果为（x,y）
  a. x是上方未匹配导致的缺失：因上方未匹配内容未覆盖而导致的已匹配内容前序缺失（如主序号（一）完全未出现在上方未匹配内容中，或（一）下子项2.缺失）； 如果未缺失，x记为 0；缺失一段内容，x记录为-1；缺失两段内容，x记录为-2，以此类推
  b. y是下方未匹配导致的缺失：因下方未匹配内容未覆盖而导致的已匹配内容后序缺失（如已匹配主序号（二）下应包含子项3.、4.，但3.、4.仅出现在下方未匹配内容中且未被纳入已匹配）。如果未缺失，y记为 0；缺失一段内容，y记录为 1；缺失两段内容，y记录为 2，以此类推

示例：
[-1,2] → 上方缺 1 段，下方缺 2 段
[-3,4] → 上方缺 3 段，下方缺 4 段
[0,0] → 前后完整

## 四、输出格式(json)
[-count, count]
"""

P_TOP_BOTTOM_PARAS = re.compile(r"-?(\d+)[,，]\s*(\d+)")


async def contract_integrity_check(paras, top_paras, bottom_paras):
    content = render_prompt(
        contract_integrity_check_prompt,
        {
            "paras": paras,
            "top_paras": top_paras,
            "bottom_paras": bottom_paras,
        },
    )

    messages = [{"role": "user", "content": content}]
    openai_client = AsyncOpenAIClient()

    gpt_res = await openai_client.send_message(messages, response_format_type="json_object")
    try:
        match = P_TOP_BOTTOM_PARAS.search(gpt_res)
        if match:
            top, bottom = match.groups()
            return -int(top), int(bottom)
    except Exception as e:
        logger.exception(e)
    return 0, 0
