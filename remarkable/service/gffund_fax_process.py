from pandas import DataFrame
from utensils.util import generate_timestamp

from remarkable.models.gffund import GFFundFaxMapping


def process_df_fax(df: DataFrame):
    name_set = {
        "广发业务申请表A",
        "广发业务申请表B",
        "广发业务申请表C",
        "广发业务申请表D",
        "广发业务申请表E",
        "广发业务申请表F",
        "广发业务申请表G",
        "广发业务申请表模板",
        "广发业务申请表其他模板",
        "广发业务申请表模板/广发业务申请表其他模板",
    }
    column1_data = df.iloc[:, 0]
    column2_data = df.iloc[:, 1]
    if not set(column2_data).issubset(name_set):
        raise ValueError("column2 must be in {}".format(name_set))
    data = [{"fax": fax, "model_name": model_name.split("/")} for fax, model_name in zip(column1_data, column2_data)]
    # NOTE: GaussDB does not support ON CONFLICT DO UPDATE
    # https://support.huaweicloud.com/intl/en-us/sqlreference-dws/dws_06_0006.html
    return GFFundFaxMapping.insert_many(data).on_conflict(
        "update",
        conflict_target=[GFFundFaxMapping.fax],
        preserve=[GFFundFaxMapping.model_name],
        update={
            GFFundFaxMapping.updated_utc: generate_timestamp(),
        },
    )
