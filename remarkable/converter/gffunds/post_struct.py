import logging
from dataclasses import asdict, dataclass

PURCHASE_MAP = {
    "基金账号": "fundacco",
    "交易账号": "tradeacco",
    "基金代码": "fundcode",
    "分红方式": "dividendmethod",
    "收费方式": "sharetype",
    "交易币种": "moneytype",
    "金(份)额小写": "balance",  # 金额小写
}

REDEEM_MAP = {
    "基金账号": "fundacco",
    "交易账号": "tradeacco",
    "基金代码": "fundcode",
    "巨额未确认部分是否继续": "lagerredeemdealflag",
    "是否全部赎回": "allredeemflag",
    "金(份)额小写": "requestshare",
}

FUND_SWITCHING_MAP = {
    "基金账号": "fundacco",
    "交易账号": "tradeacco",
    "转出基金代码": "fundcode",
    "转入基金代码": "otherfundcode",
    "巨额未确认部分是否继续": "lagerredeemdealflag",
    "金(份)额小写": "requestshare",
}

DIVIDEND_METHOD_MAP = {
    "基金账号": "fundacco",
    "交易账号": "tradeacco",
    "基金代码": "fundcode",
    "分红方式": "dividendmethod",
    "分红方式列表": "dividendmethod",
}
HOSTING_MAP = {
    "基金账号": "fundacco",
    "交易账号": "tradeacco",
    "转托管基金代码": "fundcode",
    "金(份)额小写": "requestshare",
    # '转出网点代码': '',
    "转入网点代码": "othersaleno",
    "转入网点席位号": "otherbranchcode",
    # '转出申请单编号': '',
}

TRANSACTION_TYPE_MAP = {
    "申购": (PURCHASE_MAP, "022"),
    "赎回": (REDEEM_MAP, "024"),
    "设置分红方式": (DIVIDEND_METHOD_MAP, "029"),
    "基金转换": (FUND_SWITCHING_MAP, "036"),
    "转托管": (HOSTING_MAP, "026"),
}

UNDEFINED_TRANSACTION_TYPE_ELEMENT_MAP = {
    "基金账号": "fundacco",
    "交易账号": "tradeacco",
    "收费方式": "sharetype",
    "交易币种": "moneytype",
    "是否全部赎回": "allredeemflag",
    "巨额未确认部分是否继续": "lagerredeemdealflag",
    "分红方式": "dividendmethod",
    "转入基金代码": "otherfundcode",
    "转入网点代码": "othersaleno",
    "转入网点席位号": "otherbranchcode",
}
FEE_TYPE = {"前端收费": "A", "后端收费": "B"}
LARGE_REDEEM_DEAL = {"继续赎回": "1", "放弃超额部分": "0"}
ALL_REDEEM_DEAL = {"是": "1", "否": None}
DIVIDENDS_TYPE = {"现金分红": "1", "红利再投资": "0"}
MONEY_TYPE = {"人民币": "156", "美元": "840"}


@dataclass
class PostField:
    id: str | None = None  # 文件id
    fileId: str | None = None  # 广发系统文件id
    busincode: str | None = None  # 接口功能(交易类型)
    fundacco: str | None = None  # 基金账号
    tradeacco: str | None = None  # 交易账号
    fundcode: str | None = None  # 基金代码/转出基金代码
    sharetype: str | None = None  # 份额类别
    balance: str | None = None  # 认/申购金额(金额小写，交易类型为：申购）
    moneytype: str | None = None  # 交易币种
    allredeemflag: str | None = None  # 全额赎回标志
    lagerredeemdealflag: str | None = None  # 巨额赎回处理
    requestshare: str | None = None  # 赎回份额/转换份额(金额小写,交易类型为：转托管，赎回，基金转换)
    dividendmethod: str | None = None  # 分红方式
    otherfundcode: str | None = None  # 转入基金代码
    othersaleno: str | None = None  # 转入网点代码
    otherbranchcode: str | None = None  # 转入网点席位号
    retcode: str | None = None  # 0-成功；1-失败(当所有字段为空时表示失败）

    def __post_init__(self):
        self.sharetype = FEE_TYPE.get(self.sharetype) if self.busincode == TRANSACTION_TYPE_MAP["申购"][1] else None
        self.allredeemflag = ALL_REDEEM_DEAL.get(self.allredeemflag)
        self.lagerredeemdealflag = (
            LARGE_REDEEM_DEAL.get(self.lagerredeemdealflag, LARGE_REDEEM_DEAL["继续赎回"])
            if self.busincode in (TRANSACTION_TYPE_MAP["赎回"][1], TRANSACTION_TYPE_MAP["基金转换"][1])
            else None
        )
        self.dividendmethod = DIVIDENDS_TYPE.get(self.dividendmethod)
        self.moneytype = MONEY_TYPE.get(self.moneytype) if self.busincode == TRANSACTION_TYPE_MAP["申购"][1] else None
        if self.allredeemflag == "1":
            # 全额赎回时 requestshare 不用上传
            self.requestshare = None

    def to_dict(self):
        res = asdict(self)
        res["retcode"] = "0" if any(res.values()) else "1"
        return res

    @classmethod
    def build_request_body(cls, file, convert_answer: dict[str, str | None], schema_name: str):
        """根据配置好的字典将答案组装为客户定制的请求体"""
        dividend_map = {"分红方式基金代码": "fundcode", "分红方式选择": "dividendmethod"}
        body = []
        extract_element_map_list = cls.group_element_by_type(convert_answer)
        for element, business_code in extract_element_map_list:
            data = {"busincode": business_code}
            # 在广发基金其他模板中分红方式是个列表，里面嵌套的字典，需要按照列表的长度来组装body数据
            # [{'分红方式基金代码': '123123133423', '分红方式选择': '红利再投资'}, {'分红方式基金代码': '3245325436', '分红方式选择': '现金分红'}]
            if dividend := convert_answer.get("分红方式列表"):
                # 转换分红方式列表列表里的fundcode，dividendmethod字段
                for item in dividend:
                    new_data = data.copy()
                    for key, value in item.items():
                        new_data.update({dividend_map[key]: value})
                    body.append(new_data)
                # 转换列表里其他字段
                for ele in body:
                    for key, value in element.items():
                        if value in ele or key == "分红方式列表":
                            continue
                        ele.update({value: convert_answer.get(key)})
            else:
                for key, value in element.items():
                    if key == "分红方式列表":
                        continue
                    data.update({value: convert_answer.get(key)})
                body.append(data)
        request_body = []
        # https://gitpd.paodingai.com/cheftin/docs_scriber/-/issues/1271
        # 模板E可能会提取到分红方式，但只有交易类型为：设置分红方式 才需要填这个值
        if schema_name == "广发业务申请表E":
            for element in body:
                if element.get("busincode") != TRANSACTION_TYPE_MAP["设置分红方式"][1]:
                    element.pop("dividendmethod", None)
        for element in body:
            res = PostField(**element).to_dict()
            res.update({"id": file.id, "fileId": file.meta_info.get("gffund_file_id") if file.meta_info else None})
            request_body.append(res)
        return request_body

    @staticmethod
    def group_element_by_type(convert_answer: dict[str, str | None]):
        """将要进行字段转换的答案按照交易类型分组"""
        # 交易类型为多个时，其值用'\n'分割， 例如 '申购\n赎回', E模板-申购及分红方式修改会出现该现象 file_id：509
        try:
            return [TRANSACTION_TYPE_MAP[trans_tp] for trans_tp in convert_answer.get("交易类型", "").split("\n")]
        except KeyError as e:
            logging.exception(e)
            return [(UNDEFINED_TRANSACTION_TYPE_ELEMENT_MAP, None)]
