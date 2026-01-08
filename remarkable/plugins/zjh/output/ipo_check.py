# pylint: skip-file

import json
import os
import re
from copy import deepcopy
from functools import partial
from operator import itemgetter

from remarkable import config
from remarkable.plugins.zjh.ipo_route import (
    _IF_ANY_PASS_FIELDS,
    _IF_ANY_PASS_PATHS,
    _IF_NONE_PASS_FIELDS,
    _IF_NONE_PASS_PATHS,
    _PASS_FIELDS,
    _PASS_PATHS,
    mirror,
    route,
    statements,
)
from remarkable.plugins.zjh.util import format_string

EXPORT_DIR = os.path.join(config.get_config("web.data_dir").replace("files", "ipo_export"))


def ipo_rule_map(key):
    rule_map = {
        "《上市管理办法》第二十六条": "《首次公开发行股票并上市管理办法》第二十六条--发行人应当符合下列条件: (一)最近3个会计年度净利润均为正数且累计超过人民币3000万元，"
        "净利润以扣除非经常性 损益前后较低者为计算依据; (二)最近3个会计年度经营活动产生的现金流量净额累计超过人民币5000万元;或者最近 3个会计年度营业收入累计超"
        "过人民币3亿元; (三)发行前股本总额不少于人民币3000万元; (四)最近一期末无形资产(扣除土地使用权、水面养殖权和采矿权等后)占净资产的比例不 高于20%;(五)最"
        "近一期末不存在未弥补亏损。",
        "《创业板上市管理办法》第十一条": "《首次公开发行股票并在创业板上市管理办法》第十一条--发行人申请首次公开发行股票应当符合下列条件: (一)发行人是依法设立且持续经营三年以上的"
        "股份有限公司。有限责任公司按原账面净资产值折股整体变更为股份有限公司的，持续经营时间可以从有限责任公司成立之日起计算;(二)最近两年连续盈利，最近两年净"
        "利润累计不少于一千万元;或者最近一年盈利，最近一年营业收入不少于五千万元。净利润以扣除非经常性损益前后孰低者为计算依据;(三)最近一期末净资产不少于二千万"
        "元，且不存在未弥补亏损;(四)发行后股本总额不少于三千万元。",
        "《创业板招股说明书》第七十四条": "《公开发行证券的公司信息披露内容与格式准则第28号——创业板公司招股说明书》第七十四条--发行人应列表披露最近三年及一期的主要财务指标。主要包括流"
        "动比率、速动比率、资产负债率(母公司)、应收账款周转率、存货周转率、息税折旧摊销前利润、归属于发行人股东的净利润、归属于发行人股东扣除非经常性损益后的净利"
        "润、利息保障倍数、每股经营活动产生的现金流量、每股净现金流量、基本每股收益、稀释每股收益、归属于发行人股东的每股净资产、净资产收益率、无形资产(扣除土地使"
        "用权、水面养殖权和采矿权等后)占净资产的比例。除特别指出外，上述财务指标应以合并财务报表的数据为基础进行计算。其中，净资产收益率和每股收益的计算应执行中国"
        "证监会的有关规定。",
    }
    rule_map_from_ipo_route_statements = {
        "《招股说明书》第四十四条": "《公开发行证券的公司信息披露内容与格式准则第1号——招股说明书》第四十四条--发行人应根据重要性原则披露主营业务的具体情况，包括:(一)主要产"
        "品或服务的用途;(二)主要产品的工艺流程图或服务的流程图; (三)主要经营模式，包括采购模式、生产模式和销售模式; (四)列表披露报告期内各期主要产品(或"
        "服务)的产能、产量、销量、销售收入，产品或服 务的主要消费群体、销售价格的变动情况;报告期内各期向前五名客户合计的销售额占当期销 售总额的百分比，如"
        "向单个客户的销售比例超过总额的50%或严重依赖于少数客户的，应披露 其名称及销售比例。如该客户为发行人的关联方，则应披露产品最终实现销售的情况。受同"
        "一实际控制人控制的销售客户，应合并计算销售额; (五)报告期内主要产品的原材料和能源及其供应情况，主要原材料和能源的价格变动趋势、 主要原材料和能源占"
        "成本的比重;报告期内各期向前五名供应商合计的采购额占当期采购总额 的百分比，如向单个供应商的采购比例超过总额的50%或严重依赖于少数供应商的，应披露其"
        "名称及采购比例。受同一实际控制人控制的供应商，应合并计算采购额;",
        "《招股说明书》第四十五条": "《公开发行证券的公司信息披露内容与格式准则第1号——招股说明书》第四十五条--发行人应列表披露与其业务相关的主要固定资产及无形资产，主要包括:"
        " (一)生产经营所使用的主要生产设备、房屋建筑物及其取得和使用情况、成新率或尚可使用 年限、在发行人及下属企业的分布情况等; (二)商标、专利、非专利技"
        "术、土地使用权、水面养殖权、探矿权、采矿权等主要无形资产 的数量、取得方式和时间、使用情况、使用期限或保护期、最近一期末账面价值，以及上述资 产对发"
        "行人生产经营的重要程度。 发行人允许他人使用自己所有的资产，或作为被许可方使用他人资产的，应简要披露许可合同 的主要内容，包括许可人、被许可人、许可"
        "使用的具体资产内容、许可方式、许可年限、许可 使用费等，以及合同履行情况。若发行人所有或使用的资产存在纠纷或潜在纠纷的，应明确说明。",
        "《招股说明书》第五十八条": "《公开发行证券的公司信息披露内容与格式准则第1号——招股说明书》第五十八条--发行人应披露董事、监事、高级管理人员及核心技术人员的简要情况，"
        "主要包括: (一)姓名、国籍及境外居留权;(二)性别;(三)年龄;(四)学历;(五)职称;(六)主要业务经历;(七)曾经担任的重要职务及任期;(八)现任职务及任期。"
        "对核心技术人员还应披露其主要成果及获得的奖项。 对于董事、监事，应披露其提名人，并披露上述人员的选聘情况。",
        "《招股说明书》第二十九条": "《公开发行证券的公司信息披露内容与格式准则第1号——招股说明书》第二十九条--发行人应披露其基本情况，主要包括:(一)注册中、英文名称;(二)注册"
        "资本;(三)法定代表人;(四)成立日期;(五)住所和邮政编码;(六)电话、传真号码(七)互联网网址;(八)电子信箱。",
        "《招股说明书》第三十六条": "《公开发行证券的公司信息披露内容与格式准则第1号——招股说明书》第三十六条--发行人应披露有关股本的情况，主要包括: (一)本次发行前的总股本、"
        "本次发行的股份，以及本次发行的股份占发行后总股本的比例; (二)前十名股东;(三)前十名自然人股东及其在发行人处担任的职务; (四)若有国有股份或外资股份"
        "的，须根据有关主管部门对股份设置的批复文件披露股东名称 、持股数量、持股比例。涉及国有股的，应在国家股股东之后标注“SS”(State- ownshareholder"
        "的缩写)，在国有法人股股东之后标注“SLS”State-own(Legal- personShareholder的缩写)，并披露前述标识的依据及标识的含义; (五)股东中的战略投资"
        "者持股及其简况; (六)本次发行前各股东间的关联关系及关联股东的各自持股比例; (七)本次发行前股东所持股份的流通限制和自愿锁定股份的承诺。",
        "《招股说明书》第三十五条": "《公开发行证券的公司信息披露内容与格式准则第1号——招股说明书》第三十五条--发行人应披露发起人、持有发行人5%以上股份的主要股东及实际控制人的"
        "基本情况，主要包 括: (一)发起人、持有发行人5%以上股份的主要股东及实际控制人如为法人，应披露成立时间 、注册资本、实收资本、注册地和主要生产经营地、"
        "股东构成、主营业务、最近一年及一期的 总资产、净资产、净利润，并标明有关财务数据是否经过审计及审计机构名称;如为自然人 ，则应披露国籍、是否拥有永久境"
        "外居留权、身份证号码、住所; (二)控股股东和实际控制人控制的其他企业的成立时间、注册资本、实收资本、注册地和主 要生产经营地、主营业务、最近一年及一期"
        "的总资产、净资产、净利润，并标明这些数据是否 经过审计及审计机构名称; (三)控股股东和实际控制人直接或间接持有发行人的股份是否存在质押或其他有争议的情"
        "况 。实际控制人应披露到最终的国有控股主体或自然人为止。",
        "《招股说明书》第七十一条": "《公开发行证券的公司信息披露内容与格式准则第1号——招股说明书》第七十一条--发行人运行三年以上的，应披露最近三年及一期的资产负债表、利润表和"
        "现金流量表;运行不 足三年的，应披露最近三年及一期的利润表以及设立后各年及最近一期的资产负债表和现金流 量表。发行人编制合并财务报表的，应同时披露合并"
        "财务报表和母公司财务报表。",
        "《招股说明书》第一百零六条": "《公开发行证券的公司信息披露内容与格式准则第1号——招股说明书》第一百零六条--发行人应披露:(一)预计募集资金数额; (二)募集资金原则上应用于"
        "主营业务。按投资项目的轻重缓急顺序，列表披露预计募集资金 投入的时间进度及项目履行的审批、核准或备案情况; (三)若所筹资金不能满足项目资金需求的，应"
        "说明缺口部分的资金来源及落实情况。",
        "《招股说明书》第一百四十条": "《公开发行证券的公司信息披露内容与格式准则第1号——招股说明书》第一百四十条--发行人应当披露其基本情况，主要包括:(一)发行人基本资料，包括:"
        "【待添加表格】(二)发行人历史沿革及改制重组情况，主要包括:1.发行人的设立方式;2.发起人及其投入的资产内容。(三)有关股本的情况，主要包括:1.总股本、"
        "本次发行的股份、股份流通限制和锁定安排; 2.以表格方式披露下述人员的持股数量及比例:(1)发起人;(2)前十名股东;(3)前十名自然人股东;(4)国家股、国有法"
        "人股股东，并注明标识及其含义;(5)外资股股东。3.发行人的发起人、控股股东和主要股东之间的关联关系。 (四)发行人的主营业务、主要产品或服务及其用途、产"
        "品销售方式和渠道、所需主要原材料 、行业竞争情况以及发行人在行业中的竞争地位。 (五)发行人业务及生产经营有关的资产权属情况。对发行人业务及生产经营所"
        "必须的商标、 土地使用权、专利与非专利技术、重要特许权利等，应明确披露这些权利的使用及权属情况。 (六)同业竞争和关联交易情况，以及有关独立董事对关联"
        "交易发表的意见，并以表格形式披 露报告期内关联交易对发行人财务状况和经营成果的影响。 (七)董事、监事、高级管理人员，以图表形式披露上述人员的基本情况"
        "及其兼职情况、薪酬 情况以及与发行人及其控股子公司间的股权关系或其他利益关系。【待添加表格】(八)发行人控股股东及其实际控制人的简要情况。 (九)发行人"
        "应简要披露其财务会计信息及管理层讨论与分析，主要包括: 1.发行人运行三年以上的，披露最近三年及一期的资产负债表、利润表和现金流量表;运行不 足三年的，"
        "应披露最近三年及一期的利润表以及设立后各年及最近一期的资产负债表和现金流量表。发行人编制了合并财务报表的，仅披露合并财务报表即可。 2.以合并财务报"
        "表的数据为基础披露最近三年及一期非经常性损益的具体内容及金额，计算最 近三年及一期扣除非经常性损益后的净利润金额。 3.列表披露最近三年及一期的流动比"
        "率、速动比率、资产负债率(母公司)、应收账款周转率 、存货周转率、息税折旧摊销前利润、利息保障倍数、每股经营活动的现金流量、每股净现金 流量、每股收益、"
        "净资产收益率、无形资产(扣除土地使用权、水面养殖权和采矿权等后)占 净资产的比例。除特别指出外，上述财务指标应以合并财务报表的数据为基础进行计算。 "
        "4.简要盈利预测表(如有)。 5.管理层对公司财务状况、盈利能力及现金流量的报告期内情况及未来趋势的简要讨论与分析 ，重点披露报告期内公司营业收入及净利润"
        "的主要来源、现实及可预见的主要影响因素分析。 6.最近三年股利分配政策和实际分配情况、发行前滚存利润的分配政策及分配情况、发行后股 利分配政策。 7.发行"
        "人控股子公司或纳入发行人合并会计报表的其他企业的基本情况，主要包括:公司成立 日期、注册资本、实收资本、股权结构、主要管理人员、主营业务、主要产品或服"
        "务、最近一年及一期主要财务数据。",
        "《招股说明书》第一百四十三条": "《公开发行证券的公司信息披露内容与格式准则第1号——招股说明书》第一百四十三条--发行人应披露对投资者作出投资决策有重要影响的其他事项，如重"
        "大合同、重大诉讼或仲裁事 项等。",
        "《招股说明书》第一百四十一条": "《公开发行证券的公司信息披露内容与格式准则第1号——招股说明书》第一百四十一条--发行人应简要披露本次募集资金投资项目的具体安排和计划，以及"
        "对项目发展前景的分析。",
        "《招股说明书》第一百二十六条": "《公开发行证券的公司信息披露内容与格式准则第1号——招股说明书》第一百二十六条--发行人应披露对财务状况、经营成果、声誉、业务活动、未来前景"
        "等可能产生较大影响的诉讼 或仲裁事项，主要包括:(一)案件受理情况和基本案情;(二)诉讼或仲裁请求;(三)判决、裁决结果及执行情况;(四)诉讼、仲裁案件对发"
        "行人的影响。",
        "《招股说明书》第一百二十八条": "《公开发行证券的公司信息披露内容与格式准则第1号——招股说明书》第一百二十八条--发行人应披露董事、监事、高级管理人员和核心技术人员涉及刑事"
        "诉讼的情况。",
        "《招股说明书》第一百二十七条": "《公开发行证券的公司信息披露内容与格式准则第1号——招股说明书》第一百二十七条--发行人应披露控股股东或实际控制人、控股子公司，发行人董事、"
        "监事、高级管理人员和核心 技术人员作为一方当事人的重大诉讼或仲裁事项。",
        "《招股说明书》第一百一十一条": "《公开发行证券的公司信息披露内容与格式准则第1号——招股说明书》第一百一十一条--募集资金用于扩大现有产品产能的，发行人应结合现有各类产品在"
        "报告期内的产能、产量、销量、产销率、销售区域，项目达产后各类产品新增的产能、产量，以及本行业的发展趋势、有关产品的市场容量、主要竞争对手等情况对项"
        "目的市场前景进行详细的分析论证。募集资金用于新产品开发生产的，发行人应结合新产品的市场容量、主要竞争对手、行业发展趋势、技术保障、项目投产后新增产"
        "能情况，对项目的市场前景进行详细的分析论证。",
        "《创业板上市管理办法》第十一条": "《首次公开发行股票并在创业板上市管理办法》第十一条--发行人申请首次公开发行股票应当符合下列条件: (一)发行人是依法设立且持续经营三年以上的"
        "股份有限公司。有限责任公司按原账面净资产值折股整体变更为股份有限公司的，持续经营时间可以从有限责任公司成立之日起计算;(二)最近两年连续盈利，最近两年净"
        "利润累计不少于一千万元;或者最近一年盈利，最近一年营业收入不少于五千万元。净利润以扣除非经常性损益前后孰低者为计算依据;(三)最近一期末净资产不少于二千万"
        "元，且不存在未弥补亏损;(四)发行后股本总额不少于三千万元。",
        "《创业板招股说明书》第四十四条": "《创业板公开发行证券的公司信息披露内容与格式准则第28号——创业板公司招股说明书》第四十四条--发行人应按对业务经营的重要性程度列表披露与其业"
        "务相关的主要固定资产、无形资产等资源 要素，主要包括: (一)经营使用的主要生产设备、房屋建筑物，披露取得和使用情况、成新率或尚可使用年限 、在发行人及"
        "下属企业的分布情况以及设备大修或技术改造的周期、计划实施安排及对公司经 营的影响; (二)主要无形资产情况，主要包括商标、已取得的专利、非专利技术、土"
        "地使用权、水面养 殖权、探矿权、采矿权等的数量、取得方式和时间、使用情况以及目前的法律状态，披露使用 期限或保护期、最近一期末账面价值，以及上述资产对"
        "发行人生产经营的重要程度; (三)其他对发行人经营发生作用的资源要素。 发行人允许他人使用自己所有的资源要素，或作为被许可方使用他人资源要素的，应简要披"
        "露许可合同的主要内容，包括许可人、被许可人、许可使用的具体资源要素内容、许可方式、许可年限、许可使用费等，以及合同履行情况。若发行人所有或使用的资"
        "源要素存在纠纷或潜在纠纷的，应明确说明。",
        "《创业板招股说明书》第四十二条": "《创业板公开发行证券的公司信息披露内容与格式准则第28号——创业板公司招股说明书》第四十二条--发行人应披露销售情况和主要客户，包括: (一)报"
        "告期内各期主要产品或服务的规模(产能、产量、销量，或服务能力、服务量)、销 售收入，产品或服务的主要客户群体、销售价格的总体变动情况。存在多种销售模式"
        "的，应披 露各销售模式的规模及占当期销售总额的比重; (二)报告期内各期向前五名客户合计的销售额占当期销售总额的百分比，向单个客户的销售 比例超过总额的"
        "50%、前五名客户中新增的客户或严重依赖于少数客户的，应披露其名称或姓 名、销售比例。该客户为发行人关联方的，则应披露产品最终实现销售的情况。受同一实"
        "际控 制人控制的销售客户，应合并计算销售额。",
        "《创业板招股说明书》第四十三条": "《创业板公开发行证券的公司信息披露内容与格式准则第28号——创业板公司招股说明书》第四十三条--发行人应披露采购情况和主要供应商，包括: (一)"
        "报告期内采购产品、原材料、能源或接受服务的情况，相关价格变动趋势; (二)报告期内各期向前五名供应商合计的采购额占当期采购总额的百分比，向单个供应商的"
        "采购比例超过总额的50%、前五名供应商中新增的供应商或严重依赖于少数供应商的，应披露 其名称或姓名、采购比例。受同一实际控制人控制的供应商，应合并计算"
        "采购额。",
        "《创业板招股说明书》第六十六条": "《创业板公开发行证券的公司信息披露内容与格式准则第28号——创业板公司招股说明书》第六十六条--发行人应披露最近三年及一期的资产负债表、利润"
        "表和现金流量表。发行人编制合并财务报表 的，应披露合并财务报表。",
        "《创业板招股说明书》第八十八条": "《创业板公开发行证券的公司信息披露内容与格式准则第28号——创业板公司招股说明书》第八十八条--发行人应根据重要性原则披露募集资金运用情况: "
        "(一)募集资金的具体用途，简要分析募集资金具体用途的可行性及其与发行人现有主要业务 、核心技术之间的关系; (二)投资概算情况。发行人所筹资金如不能满足"
        "预计资金使用需求的，应说明缺口部分的资 金来源及落实情况;如所筹资金超过预计募集资金数额的，应说明相关资金在运用和管理上的 安排;(三)募集资金具体用"
        "途所需的时间周期和时间进度; (四)募集资金运用涉及履行审批、核准或备案程序的，应披露相关的履行情况; (五)募集资金运用涉及环保问题的，应披露可能存在"
        "的环保问题、采取的措施及资金投入情 况; (六)募集资金运用涉及新取得土地或房产的，应披露取得方式、进展情况及未能如期取得对14募集资金具体用途的影响; "
        "(七)募集资金运用涉及与他人合作的，应披露合作方基本情况、合作方式、各方权利义务关 系; (八)募集资金向实际控制人、控股股东及其关联方收购资产，如果对"
        "被收购资产有效益承诺 的，应披露效益无法完成时的补偿责任;(九)募集资金的专户存储安排。",
        "《创业板招股说明书》第五十五条": "《创业板公开发行证券的公司信息披露内容与格式准则第28号——创业板公司招股说明书》第五十五条--发行人应披露董事、监事、高级管理人员及其他核"
        "心人员的简要情况，主要包括: (一)姓名、国籍及境外居留权;(二)性别;(三)年龄;(四)学历及专业背景;(五)职称; (六)主要业务经历及实际负责的业务活动;对发"
        "行人设立、发展有重要影响的董事、监事、 高级管理人员及其他核心人员，还应披露其创业或从业历程; (七)曾经担任的重要职务及任期;(八)现任发行人的职务及任期;",
        "《创业板招股说明书》第九十六条": "《创业板公开发行证券的公司信息披露内容与格式准则第28号——创业板公司招股说明书》第九十六条--发行人应披露控股股东或实际控制人、控股子公司，"
        "发行人董事、监事、高级管理人员和其他 核心人员作为一方当事人的重大诉讼或仲裁事项。 发行人应披露控股股东、实际控制人最近三年内是否存在重大违法行为。",
        "《创业板招股说明书》第九十五条": "《创业板公开发行证券的公司信息披露内容与格式准则第28号——创业板公司招股说明书》第九十五条--发行人应披露对财务状况、经营成果、声誉、业务活"
        "动、未来前景等可能产生较大影响的诉讼 或仲裁事项，主要包括:(一)案件受理情况和基本案情;(二)诉讼或仲裁请求;(三)判决、裁决结果及执行情况;(四)诉讼、仲"
        "裁案件对发行人的影响。",
        "《创业板招股说明书》第九十七条": "《创业板公开发行证券的公司信息披露内容与格式准则第28号——创业板公司招股说明书》第九十七条--发行人应披露董事、监事、高级管理人员和其他核心"
        "人员涉及刑事诉讼的情况。",
        "《创业板招股说明书》第三十六条": "《创业板公开发行证券的公司信息披露内容与格式准则第28号——创业板公司招股说明书》第三十六条--发行人应披露有关股本的情况，主要包括: (一)本次"
        "发行前的总股本、本次发行及公开发售的股份，以及本次发行及公开发售的股份占 发行后总股本的比例;(二)本次发行前后的前十名股东; (三)本次发行前后的前十名自"
        "然人股东及其在发行人处担任的职务; (四)发行人股本有国有股份或外资股份的，应根据有关主管部门对股份设置的批复文件披露 相应的股东名称、持股数量、持股比例。"
        "涉及国有股的，应在国有股东之后标注 “SS”(State-ownedShareholder的缩写)，披露前述标识的依据及标识的含义，并披露国 有股转持情况; (五)最近一年发行"
        "人新增股东的持股数量及变化情况、取得股份的时间、价格和定价依据。 属于战略投资者的，应予注明并说明具体的战略关系。 新增股东为法人的，应披露其主要股东及"
        "实际控制人;为自然人的，应披露国籍、拥有永久境 外居留权情况(如有)、身份证号码;为合伙企业的，应披露其普通合伙人及实际控制人、有 限合伙人(如有)的情况; "
        "(六)本次发行前各股东间的关联关系及关联股东的各自持股比例; (七)发行人股东公开发售股份的，应披露公开发售股份对发行人的控制权、治理结构及生产 经营产生"
        "的影响，并提示投资者关注上述事项。",
        "《创业板招股说明书》第三十五条": "《创业板公开发行证券的公司信息披露内容与格式准则第28号——创业板公司招股说明书》第三十五条--发行人应披露持有发行人5%以上股份的主要股东及实"
        "际控制人的基本情况，主要包括: (一)持有发行人5%以上股份的主要股东及实际控制人为法人的，应披露成立时间、注册资 本、实收资本、注册地和主要生产经营地、"
        "股东构成、主营业务及其与发行人主营业务的关系 ;为自然人的，应披露国籍、是否拥有永久境外居留权、身份证号码;为合伙企业的，应披露 合伙人构成、出资比例及"
        "合伙企业的实际控制人。 发行人的控股股东及实际控制人为法人的，还应披露最近一年及一期末的总资产、净资产、最 近一年及一期的净利润，并标明有关财务数据是"
        "否经过审计及审计机构名称; (二)控股股东和实际控制人控制的其他企业的情况，主要包括成立时间、注册资本、实收资 本、注册地和主要生产经营地、主营业务及其"
        "与发行人主营业务的关系、最近一年及一期末的 总资产、净资产、最近一年及一期的净利润，并标明有关财务数据是否经过审计及审计机构名称; (三)控股股东和实际"
        "控制人直接或间接持有发行人的股份是否存在质押或其他有争议的情况 ;(四)实际控制人应披露至最终的国有控股主体、集体组织、自然人; (五)无控股股东、实际控制"
        "人的，应参照本条对发行人控股股东及实际控制人的要求披露对 发行人有重大影响的股东情况。"
        "并提示投资者关注上述事项。",
        "《创业板招股说明书》第三十一条": "《创业板公开发行证券的公司信息披露内容与格式准则第28号——创业板公司招股说明书》第三十一条--发行人应披露其基本情况，主要包括:(一)注册中、"
        "英文名称;(二)注册资本;(三)法定代表人;(四)成立日期;(五)住所和邮政编码;(六)电话、传真号码;(七)互联网网址;(八)电子信箱;(九)负责信息披露和投资者"
        "关系的部门、负责人和电话号码。",
        "《创业板招股说明书》第七十四条": "《创业板公开发行证券的公司信息披露内容与格式准则第28号——创业板公司招股说明书》第七十四条--发行人应列表披露最近三年及一期的主要财务指标。"
        "主要包括流动比率、速动比率、资产负债率(母公司)、应收账款周转率、存货周转率、息税折旧摊销前利润、归属于发行人股东的净利润、归属于发行人股东扣除非经"
        "常性损益后的净利润、利息保障倍数、每股经营活动产生的现金流量、每股净现金流量、基本每股收益、稀释每股收益、归属于发行人股东的每股净资产、净资产收益"
        "率、无形资产(扣除土地使用权、水面养殖权和采矿权等后)占净资产的比例。除特别指出外，上述财务指标应以合并财务报表的数据为基础进行计算。其中，净资产收"
        "益率和每股收益的计算应执行中国证监会的有关规定。",
        "《创业板招股说明书》第七十八条": "《创业板公开发行证券的公司信息披露内容与格式准则第28号——创业板公司招股说明书》第七十八条--盈利能力分析一般应包括下列内容:(一)发行人应"
        "按照利润表项目逐项分析最近三年及一期经营成果变化的原因，对于变动幅度较大的项目应重点说明;(二)发行人应列表披露最近三年及一期营业收入的构成及比例，"
        "并分别按产品或服务类别及业务、地区分部列示，分析营业收入增减变化的情况及原因;披露主要产品或服务的销售价格、销售量的变化情况及原因;营业收入存在季节"
        "性波动的，应分析季节性因素对各季度经营成果的影响;(三)发行人应结合最近三年及一期营业成本的主要构成情况，主要原材料和能源的采购数量及采购价格等，披"
        "露最近三年及一期发行人营业成本增减变化情况及原因;(四)发行人应披露最近三年及一期销售费用、管理费用和财务费用的构成及变化情况;应披露最近三年及一期"
        "的销售费用率，如果与同行业可比上市公司的销售费用率存在显著差异，还应结合发行人的销售模式和业务特点分析差异的原因;应披露管理费用、财务费用占销售收"
        "入的比重，并解释异常波动的原因;(五)发行人应披露营业利润、利润总额和净利润金额，分析发行人净利润的主要来源及净利润增减变化情况及原因;(六)发行人应"
        "披露最近三年及一期的综合毛利率、分产品或服务的毛利率及变动情况;报告期内毛利率发生重大变化的，还应用数据说明相关因素对毛利率变动的影响程度;应与同行"
        "业上市公司中与发行人相同或相近产品或服务的毛利率对比，如存在显著差异，应结合发行人经营模式、产品销售价格和产品成本等，披露差异的原因及对净利润的影"
        "响;(七)发行人主要产品的销售价格或主要原材料、能源价格频繁变动且影响较大的，应针对价格变动对公司利润的影响作敏感性分析;(八)发行人最近三年及一期非"
        "经常性损益、合并财务报表范围以外的投资收益对公司经营成果有重大影响的，应当分析原因及对公司盈利能力稳定性的影响;应披露报告期内收到的政府补助，披露"
        "其中金额较大项目的主要信息;(九)发行人应按税种分项披露最近三年及一期公司缴纳的税额，说明所得税费用(收益)与会计利润的关系;应披露最近三年及一期税收"
        "政策的变化及对发行人的影响，是否面临即将实施的重大税收政策调整及对发行人可能存在的影响。",
        "《上市管理办法》第三十条": "《首次公开发行股票并上市管理办法》第三十条--发行人不得有下列影响持续盈利能力的情形: (一)发行人的经营模式、产品或服务的品种结构已经或者将发生重大"
        "变化，并对发行人的持 续盈利能力构成重大不利影响; (二)发行人的行业地位或发行人所处行业的经营环境已经或者将发生重大变化，并对发行人 的持续盈利能力构成重大"
        "不利影响; (三)发行人最近1个会计年度的营业收入或净利润对关联方或者存在重大不确定性的客户存 在重大依赖; (四)发行人最近1个会计年度的净利润主要来自合并财务"
        "报表范围以外的投资收益; (五)发行人在用的商标、专利、专有技术以及特许经营权等重要资产或技术的取得或者使用 存在重大不利变化的风险; (六)其他可能对发行人持"
        "续盈利能力构成重大不利影响的情形。",
    }
    rule_map.update(rule_map_from_ipo_route_statements)
    return rule_map[key]


def _compose_entry(idx, value, value_path, state, company_data, is_startup=False, is_maiden=False):
    entry = {}
    _postive, _negative = "符合 ", "违反 "

    entry["id"] = idx
    entry["字段名称"] = "-".join(value_path)
    entry["是否存在异常"] = 1 if not value else 0
    entry["异常字段"] = "" if value else "-".join(value_path)

    if state and not is_maiden:  # 1st stage
        state_ = (
            list(filter(lambda x: "创业板" in x, state))
            if is_startup
            else list(filter(lambda x: "创业板" not in x, state))
        )
        entry["相关法律条款"] = "\n".join([_postive + x for x in state_] if value else [_negative + x for x in state_])
    elif state and is_maiden and not is_startup:  # 2nd stage
        state_ = state
        entry["相关法律条款"] = "\n".join([_postive + x for x in state_] if value else [_negative + x for x in state_])
    elif state and is_startup and is_maiden:  # 3rd stage
        state_ = state
        entry["相关法律条款"] = "\n".join([_postive + x for x in state_] if value else [_negative + x for x in state_])

    if is_maiden:
        entry["异常类型"] = "" if value else "不满足规定"
        entry["异常字段具体内容"] = "" if value else company_data
    else:
        entry["异常类型"] = "" if value else "披露不完整"
        # shows 'None' for missing field, add 'or \'\'' to show nothing
        entry["异常字段具体内容"] = (
            ""
            if value
            else _get_value(
                idx,
                value_path,
                company_data,
                filt=True,
            )
        )

    if not is_maiden and not value:  # keep this until next version
        _fill_null(entry["异常字段具体内容"], value_path[-1])

    if "违反" in entry.get("相关法律条款", ""):
        entry["相关法律条款"] = transfer_rule_to_detail(entry["相关法律条款"])
    return entry


def transfer_rule_to_detail(rules):
    rules = format_string(rules)
    rule_detail_list = []
    for rule in rules.split("条"):
        if not rule:
            continue
        rule_name = rule.replace("违反", "").strip()
        if not rule_name.endswith("条"):
            rule_name += "条"
        rule_detail = "违反" + ipo_rule_map(rule_name)
        rule_detail_list.append(rule_detail)
    return "\n".join(rule_detail_list)


def _fill_null(entry, field):
    if isinstance(entry, dict) and entry.get(field) in [None, ""]:
        entry[field] = None
    elif isinstance(entry, list) and not isinstance(entry, str):
        for entry_ in entry:
            _fill_null(entry_, field)


def _get_value(idx, paths=None, target=None, filt=False, ret_lst=False, ret_elts=False, across=False):
    paths = [] if paths is None else paths
    target = {} if target is None else target
    if not paths:
        return "" if not filt else True

    result = ""
    if len(paths) == 1 and across:
        result = target.get(paths[0], "") if not filt else not target.get(paths[0], "")
    elif len(paths) == 1 and not across:
        result = target.get(paths[0], "") if not filt else target

    if len(paths) == 1:
        return result

    if paths[0] in target:
        target_ = target[paths[0]]
        if isinstance(target_, dict):
            result = _get_value(idx, paths[1:], target[paths[0]], filt=filt, across=across)
        elif isinstance(target_, list) and not isinstance(target_, str) and target_ and isinstance(target_[0], dict):
            if ret_lst:
                return target_, paths[1:]  #

            if ret_elts:
                pfn = partial(
                    _get_value,
                    idx,
                    paths[1:],
                )
                return list(map(pfn, target_))

            if filt:
                pfn = partial(_get_value, idx, paths[1:], filt=True, across=True)
                result = list(filter(pfn, target_))
            else:
                pfn = partial(
                    _get_value,
                    idx,
                    paths[1:],
                )
                result = all(map(pfn, target_))
        else:  # ENDS HERE, GOT None
            result = "" if not filt else target[paths[0]] or None
    else:
        result = "" or None

    return result


def _get_exclude_fields(company_data):
    exclude_fields = ["合并资产负债表", "合并利润表", "合并现金流量表", "基本财务指标"]
    for path in _IF_ANY_PASS_PATHS:
        value = _get_value(None, path, company_data)
        if isinstance(value, dict) and not all(value.values()) and any(value.values()):
            lst = [
                field
                for key, value_ in value.items()
                if not value_
                for field in _IF_ANY_PASS_FIELDS[path[0]].get(key, [])
            ]
            exclude_fields.extend(lst)

    #
    for path in _IF_NONE_PASS_PATHS:
        value = _get_value(None, path, company_data)
        if not value:
            exclude_fields.extend(_IF_NONE_PASS_FIELDS[path[0]])

    for path in _PASS_PATHS:
        fields = _PASS_FIELDS[path[0]]
        if isinstance(fields, dict):
            for v in fields.values():
                exclude_fields.extend(v)
        else:
            exclude_fields.extend(fields)

    return exclude_fields


def _load(fname):
    try:
        with open(fname, "r", encoding="utf-8") as fpin:
            return json.load(fpin)
    except FileNotFoundError:
        return {}


def _dump(company_entry, fpath):
    with open(fpath, "w") as fpout:
        json.dump(company_entry, fpout, ensure_ascii=False, indent=2)


def _convert(
    fstr,
):
    if not isinstance(fstr, str) or re.search(r"[^,.%\-\—\s\d]+", fstr):
        # print('\t_CONVERTING UNKNOWN OBJ: {}'.format(fstr))
        return 0

    fstr = re.sub(r",|\s*", "", fstr)
    if fstr in ["", "-", "—", "--"]:
        return 0
    elif fstr.endswith("%"):
        return float(fstr.rstrip("%"))
    else:
        return float(fstr)


def _iter_dict(data, pre_path=None):
    pre_path = [] if pre_path is None else pre_path
    result = []
    for key, field in data.items():
        if isinstance(field, dict):
            ret = _iter_dict(field, pre_path[:] + [key])
            result.extend(ret)
        else:
            result.append((key, field))

    return result


def _get_group_value(fields, company_data, scale=1, mask=None, order=None):
    mask = [] if mask is None else mask
    order = [] if order is None else order
    paths_ = [route.get(x, {}).get("path", "") for x in fields]
    pfn = partial(_get_value, None, target=company_data, ret_elts=True)
    elts_lst = list(map(pfn, paths_))

    if mask:
        # 1. first try,  deal field with mask
        # print('\tDEAL WITH MASK')
        # elts_lst = [[itm for itm, mask_ in zip(elt, mask) if mask_] for elt in elts_lst ]
        # elts_lst = [[_convert(itm) * scale for itm in elt] for elt in elts_lst ]

        # 2. second try, deal fields with order
        cnt = mask.count(True)
        elts_lst = [[elt[idx] for idx in order[:cnt]] for elt in elts_lst]
        elts_lst = [[_convert(itm) * scale for itm in elt] for elt in elts_lst]

    return elts_lst


def ipo(fname):
    def update_entry(entry):
        nonlocal idx
        company_entry[idx] = entry
        idx += 1

    company_data = _load(fname)
    if not company_data:
        # logging
        return

    company_entry = {}
    company_entry["公司名"] = company_data.get("发行人基本情况", {}).get("公司名称") or ""
    company_entry["招股说明书名"] = company_data.get("招股说明书名称") or ""
    company_entry["时间"] = company_data.get("招股说明书预先披露日期") or ""
    is_startup = True if "创业板" in company_entry["招股说明书名"] else False
    is_maiden = True if "首次公开发行" in company_entry["招股说明书名"] else False
    exclude_fields = _get_exclude_fields(company_data)
    idx = 1

    for key, state in _iter_dict(statements):
        if key in exclude_fields:
            continue

        value_path = mirror.get(key)
        value = None
        if value_path:
            value = _get_value(None, value_path, company_data)
        else:
            # print('\tGOT NO VALUE_PATH FOR:', [key])
            pass

        # if value is None:
        #     # print('\tgot None value for:', [key], value_path)
        #     entry = _compose_entry(idx, value, value_path, state, company_data, is_startup=is_startup)
        #     pass
        # else:
        #     entry = _compose_entry(idx, value, value_path, state, company_data, is_startup=is_startup)

        if not value:
            entry = _compose_entry(idx, value, value_path, state, company_data, is_startup=is_startup)
            update_entry(entry)

    # # TODO: EXTRACTING MASS CODE
    if is_maiden:
        # 0. ['83','84'] ["报表日期", "货币单位"]
        def _get_mask_scale(fields):
            elts_lst = _get_group_value(fields, company_data)
            mask = [not re.search(r"月|\-", epoc) for epoc in elts_lst[0]]

            order = list(range(len(elts_lst[0])))
            try:
                idx = mask.index(False)
            except ValueError:
                idx = None
            else:
                order[idx] = float("inf")

            if idx is not None:
                order = sorted(zip(order, elts_lst[0]), key=itemgetter(1), reverse=True)
                order = [elt[0] for elt in order]
                order = sorted(zip(order, range(len(elts_lst[0]))), key=itemgetter(0))
                order = [elt[1] for elt in order]

            scale = 1
            if elts_lst and elts_lst[1] and elts_lst[1][0]:
                if elts_lst[1][0] == "元":
                    scale = 0.0001

            # for efficiency
            # mask = [] if all(mask) else mask
            # order = [] if order == [0, 1, 2] else order
            return scale, mask, order

        fields = ["83", "84"]
        scale, mask, order = _get_mask_scale(fields)

        # IF 营业利润+营业外收入-营业外支出少于3000万；
        # # 1. ['189','190','191']
        fields = ["189", "190", "191"]
        elts_lst = _get_group_value(fields, company_data, scale, mask, order)

        def maiden_func_1(elts_lst, state):
            total = sum(elts_lst[0]) + sum(elts_lst[1]) - sum(elts_lst[2])
            if total < 3000:
                value, [value_path, comp_data] = "", "营业利润+营业外收入-营业外支出|少于3000万".split("|")
                # else:
                #     value, [value_path, comp_data] = True, ['营业利润+营业外收入-营业外支出', '']
                entry = _compose_entry(
                    idx, value, [value_path], state, "{:.2f}{}".format(total, comp_data), is_maiden=True
                )
                update_entry(entry)

        maiden_func_1(elts_lst, ["《上市管理办法》第二十六条"])

        # IF ·（T-1）+·（T-2）+·（T-3）少于5000万；
        # # 2. ['231']
        fields = ["231"]
        elts_lst = _get_group_value(fields, company_data, scale, mask, order)

        def maiden_func_2(elts_lst, state):
            total = sum(elts_lst[0])
            if total < 5000:
                value, [value_path, comp_data] = (
                    "",
                    "经营活动产生的现金流量净额（T-1）+（T-2）+（T-3）|少于5000万".split("|"),
                )
                # else:
                #     value, [value_path, comp_data] = True, ['经营活动产生的现金流量净额（T-1）+·（T-2）+·（T-2）', '']
                entry = _compose_entry(
                    idx, value, [value_path], state, "{:.2f}{}".format(total, comp_data), is_maiden=True
                )
                update_entry(entry)

        maiden_func_2(elts_lst, ["《上市管理办法》第二十六条"])

        # IF ·（T-1）+·（T-2）+·（T-2）少于3亿；
        # # 3. ['167']
        fields = ["167"]
        elts_lst = _get_group_value(fields, company_data, scale, mask, order)

        def maiden_func_3(elts_lst, state):
            total = sum(elts_lst[0])
            if total < 30000:
                value, [value_path, comp_data] = "", "营业收入（T-1）+（T-2）+（T-3）|少于30000万".split("|")
                # else:
                #     value, [value_path, comp_data] = True, ['营业收入（T-1）+·（T-2）+·（T-2）', '']
                entry = _compose_entry(
                    idx, value, [value_path], state, "{:.2f}{}".format(total, comp_data), is_maiden=True
                )
                update_entry(entry)

        maiden_func_3(elts_lst, ["《上市管理办法》第二十六条"])

        # IF 无形资产（扣除土地使用权、水面养殖权和采矿权等后）占净资产的比例（%） > 高于20%；
        # # 4. ['267']
        fields = ["267"]
        elts_lst = _get_group_value(fields, company_data, scale, mask, order)

        def maiden_func_4(elts_lst, state):
            total = sum(elts_lst[0])
            if total > 20:
                value, [value_path, comp_data] = (
                    "",
                    "无形资产（扣除土地使用权、水面养殖权和采矿权等后）占净资产的比例（%）|高于20%".split("|"),
                )
                # else:
                #     value, [value_path, comp_data] = True, ['无形资产（扣除土地使用权、水面养殖权和采矿权等后）占净资产的比例（%）', '']
                entry = _compose_entry(
                    idx, value, [value_path], state, "{:.2f}%{}".format(total, comp_data), is_maiden=True
                )
                update_entry(entry)

        maiden_func_4(elts_lst, ["《上市管理办法》第二十六条"])

    if is_startup and is_maiden:
        # IF ·（T-1）>0 && ·（T-2）>0 && ·（T-1）+·（T-2）>=1000万；
        # # 5.1 ['195']
        fields = ["195"]
        elts_lst = _get_group_value(fields, company_data, scale, mask, order)

        def startup_maiden_func_1(elts_lst, state):
            profit = elts_lst[0]
            total = sum(profit[:2])
            if profit[0] > 0 and profit[1] > 0 and total >= 1000:
                return None
            else:
                value, [value_path, comp_data] = (
                    "",
                    "净利润（T-1）<0 或 （T-2）<0 或 （T-1）+（T-2）|<1000万".split("|"),
                )
                entry = _compose_entry(
                    idx,
                    value,
                    [value_path],
                    state,
                    "{:.2f}{}".format(total, comp_data),
                    is_startup=True,
                    is_maiden=True,
                )
                return entry

        entry_51 = startup_maiden_func_1(elts_lst, ["《创业板上市管理办法》第十一条"])

        # IF ·（T-1）>0 && ·（T-1）>=5000万；
        # # 5.2 ['195','167']
        fields = ["195", "167"]
        elts_lst = _get_group_value(fields, company_data, scale, mask, order)

        def startup_maiden_func_2(elts_lst, state):
            profit, revenue = elts_lst[0], elts_lst[1]
            total = sum(profit[:2])
            if profit[0] > 0 and revenue[0] >= 5000:
                return None
            else:
                value, [value_path, comp_data] = "", "净利润（T-1）<0 或 营业收入（T-1）|<5000万".split("|")
                entry = _compose_entry(
                    idx,
                    value,
                    [value_path],
                    state,
                    "{:.2f}{}".format(total, comp_data),
                    is_startup=True,
                    is_maiden=True,
                )
                return entry

        entry_52 = startup_maiden_func_2(elts_lst, ["《创业板上市管理办法》第十一条"])

        # 5.1 && 5.2
        if entry_51 and entry_52:
            update_entry(entry_51)
            update_entry(entry_52)

        # IF 净资产（T-1）<2000万；
        # # 7. ['164']
        fields = ["164"]
        elts_lst = _get_group_value(fields, company_data, scale, mask, order)

        def startup_maiden_func_3(elts_lst, state):
            profit = elts_lst[0]
            # total = sum(profit[:2])
            if profit[0] < 2000:
                value, [value_path, comp_data] = "", "净资产（T-1）|<2000万".split("|")
                # else:
                #     value, [value_path, comp_data] = True, ['', '']
                entry = _compose_entry(
                    idx,
                    value,
                    [value_path],
                    state,
                    "{:.2f}{}".format(profit[0], comp_data),
                    is_startup=True,
                    is_maiden=True,
                )
                update_entry(entry)

        startup_maiden_func_3(elts_lst, ["《创业板上市管理办法》第十一条"])

        # IF 其中一项不存在：
        # # 8. ['263', '264', '266', '268', '269', '271', '197', '272', '274', '275', '200', '201', '276', '267']
        fields = ["263", "264", "266", "268", "269", "271", "197", "272", "274", "275", "200", "201", "276", "267"]
        elts_lst = _get_group_value(
            fields,
            company_data,
        )

        def startup_maiden_func_4(elts_lst, state):
            empty_field = []
            for field, value in zip(fields, elts_lst):
                if not value or list(filter(lambda x: x == "", value)):
                    empty_field.append(route.get(field, {}).get("path", ""))
            if empty_field:
                empty_field = ["_".join(field) for field in empty_field]
                value, [value_path, comp_data] = "", "必须字段|至少其中一项不存在".split("|")
                # else:
                #     value, [value_path, comp_data] = True, ['', '']
                entry = _compose_entry(
                    idx,
                    value,
                    [value_path],
                    state,
                    "{}{}".format(empty_field, comp_data),
                    is_startup=True,
                    is_maiden=True,
                )
                update_entry(entry)

        startup_maiden_func_4(elts_lst, ["《创业板招股说明书》第七十四条"])

    # 统一社会信用代码&组织机构代码都不合规,才认为是不合规
    code_1 = None
    code_2 = None
    company_entry_copy = deepcopy(company_entry)
    for k, v in company_entry_copy.items():
        if isinstance(v, dict):
            if v["字段名称"] == "发行人基本情况-组织机构代码":
                code_1 = {k: company_entry.pop(k)}
            if v["字段名称"] == "发行人基本情况-统一社会信用代码":
                code_2 = {k: company_entry.pop(k)}
    if code_1 and code_2:
        company_entry.update(code_1)
        company_entry.update(code_2)

    return company_entry


if __name__ == "__main__":

    def ipo_run(fdir):
        if not os.path.isdir(EXPORT_DIR):
            os.makedirs(EXPORT_DIR)

        for idx, file_ in enumerate(os.listdir(fdir)):
            if not file_.endswith(".json"):
                continue

            print("START", "-" * 8, idx, file_)
            fpath = os.path.join(fdir, file_)
            company_entry = ipo(fpath)
            fpath = os.path.join(EXPORT_DIR, file_)
            _dump(company_entry, fpath)
            print("\tDUMPED: {}".format(fpath))

    fdir_ = "/Users/liuchao/Downloads/ipo_check"
    ipo_run(fdir_)
