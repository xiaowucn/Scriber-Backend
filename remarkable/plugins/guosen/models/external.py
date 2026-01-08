import re

from sqlalchemy import TIMESTAMP, Column, String, Text
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.ext.hybrid import hybrid_property

_Base = declarative_base()

P_QUOTED = re.compile(r"[(（].+[）)]")


class DWDSecuInfo(_Base):
    __tablename__ = "DWD_secuCode"

    id = Column(Text, primary_key=True)
    stock_code = Column(String, name="combCode")
    _stock_abbr = Column(String, name="secuAbbr")
    _stock_name = Column(String, name="secuName")
    exchange_code = Column(String, name="exchangeCode")
    exchange = Column(String)
    is_delete = Column(String, name="isDelete")
    trading_code = Column(String, name="tradingCode")
    sf_type_code = Column(String, name="sFtypeCode")
    country_code = Column(String, name="countryCode")
    u_time = Column(TIMESTAMP, name="uTime")

    @hybrid_property
    def stock_abbr(self) -> str:
        return P_QUOTED.sub("", self._stock_abbr)

    @stock_abbr.expression
    def stock_abbr(cls) -> str:  # noqa
        return cls._stock_abbr

    @hybrid_property
    def stock_name(self) -> str:
        return P_QUOTED.sub("", self._stock_name)

    @stock_name.expression
    def stock_name(cls) -> str:  # noqa
        return cls._stock_name
