import functools
import logging
import re
from decimal import Decimal, InvalidOperation

import requests

from remarkable import config
from remarkable.common.constants import AutoDocStatus
from remarkable.common.exceptions import CustomError
from remarkable.common.util import box_to_outline
from remarkable.db import pw_db
from remarkable.infrastructure.mattermost import MMPoster
from remarkable.models.new_file import NewFile
from remarkable.pw_models.model import NewMold, NewRuleDoc, NewRuleResult
from remarkable.security.authtoken import encode_url


def lower2upper(value, capital=True, prefix=False, classical=None):
    try:
        return lower2upper_processer(value, capital, prefix, classical)
    except InvalidOperation:
        return ""


def lower2upper_processer(value, capital=True, prefix=False, classical=None):
    """
    人民币数字转大写汉字
    :param value:
    :param capital:     True   大写汉字金额
                        False  一般汉字金额
    :param prefix:      True   以'人民币'开头
                        False, 无开头
    :param classical:   True   元
                        False  圆
    :return:
    """
    if value == 0:
        return 0
    # 默认大写金额用圆，一般汉字金额用元
    if classical is None:
        classical = bool(capital)

    # 汉字金额前缀
    if prefix is True:
        prefix = "人民币"
    else:
        prefix = ""

    # 汉字金额字符定义
    dunit = ("角", "分")
    if capital:
        num = ("零", "壹", "贰", "叁", "肆", "伍", "陆", "柒", "捌", "玖")
        iunit = [None, "拾", "佰", "仟", "万", "拾", "佰", "仟", "亿", "拾", "佰", "仟", "万", "拾", "佰", "仟"]
    else:
        num = ("〇", "一", "二", "三", "四", "五", "六", "七", "八", "九")
        iunit = [None, "十", "百", "千", "万", "十", "百", "千", "亿", "十", "百", "千", "万", "十", "百", "千"]
    if classical:
        iunit[0] = "元" if classical else "圆"
    # 转换为Decimal，并截断多余小数

    if not isinstance(value, Decimal):
        # value = re.sub(r'[,\s元]', '', value)
        value = Decimal(value).quantize(Decimal("0.01"))

    # 处理负数
    if value < 0:
        prefix += "负"  # 输出前缀，加负
        value = -value  # 取正数部分，无须过多考虑正负数舍入
        # assert - value + value == 0
    # 转化为字符串
    value_str = str(value)
    if len(value_str) > 19:
        raise ValueError("金额太大了，不知道该怎么表达。")
    istr, dstr = value_str.split(".")  # 小数部分和整数部分分别处理
    istr = istr[::-1]  # 翻转整数部分字符串
    ret = []  # 用于记录转换结果

    # 零
    if value == 0:
        return prefix + num[0] + iunit[0]
    haszero = False  # 用于标记零的使用
    if dstr == "00":
        haszero = True  # 如果无小数部分，则标记加过零，避免出现“圆零整”

    # 处理小数部分
    # 分
    if dstr[1] != "0":
        ret.append(dunit[1])
        ret.append(num[int(dstr[1])])
    else:
        ret.append("整")  # 无分，则加“整”
    # 角
    if dstr[0] != "0":
        ret.append(dunit[0])
        ret.append(num[int(dstr[0])])
    elif dstr[1] != "0":
        ret.append(num[0])  # 无角有分，添加“零”
        haszero = True  # 标记加过零了

    # 无整数部分
    if istr == "0":
        if haszero:  # 既然无整数部分，那么去掉角位置上的零
            ret.pop()
        ret.append(prefix)  # 加前缀
        ret.reverse()  # 翻转
        return "".join(ret)

    # 处理整数部分
    for idx, sub_str in enumerate(istr):
        sub_str = int(sub_str)
        if idx % 4 == 0:  # 在圆、万、亿等位上，即使是零，也必须有单位
            if idx == 8 and ret[-1] == iunit[4]:  # 亿和万之间全部为零的情况
                ret.pop()  # 去掉万
            ret.append(iunit[idx])
            if sub_str == 0:  # 处理这些位上为零的情况
                if not haszero:  # 如果以前没有加过零
                    ret.insert(-1, num[0])  # 则在单位后面加零
                    haszero = True  # 标记加过零了
            else:  # 处理不为零的情况
                ret.append(num[sub_str])
                haszero = False  # 重新开始标记加零的情况
        else:  # 在其他位置上
            if sub_str != 0:  # 不为零的情况
                ret.append(iunit[idx])
                ret.append(num[sub_str])
                haszero = False  # 重新开始标记加零的情况
            else:  # 处理为零的情况
                if not haszero:  # 如果以前没有加过零
                    ret.append(num[0])
                    haszero = True

    # 最终结果
    ret.append(prefix)
    ret.reverse()
    return "".join(ret)


def upper2lower(upper_value):
    cn_num = {
        "〇": 0,
        "一": 1,
        "二": 2,
        "三": 3,
        "四": 4,
        "五": 5,
        "六": 6,
        "七": 7,
        "八": 8,
        "九": 9,
        "零": 0,
        "壹": 1,
        "贰": 2,
        "叁": 3,
        "肆": 4,
        "伍": 5,
        "陆": 6,
        "柒": 7,
        "捌": 8,
        "玖": 9,
        "貮": 2,
        "两": 2,
    }

    cn_unit = {
        "分": 0.01,
        "角": 0.1,
        "元": 1,
        "圆": 1,
        "十": 10,
        "拾": 10,
        "百": 100,
        "佰": 100,
        "千": 1000,
        "仟": 1000,
        "万": 10000,
        "萬": 10000,
        "亿": 100000000,
        "億": 100000000,
        "兆": 1000000000000,
    }
    unit = 0  # current
    ldig = []  # digest
    for cndig in reversed(upper_value):
        if cndig in cn_unit:
            unit = cn_unit.get(cndig)
            if unit in [10000, 100000000]:
                ldig.append(unit)
                unit = 1
        else:
            dig = cn_num.get(cndig)
            if unit:
                dig *= unit
                unit = 0
            ldig.append(dig)
    if unit == 10:
        ldig.append(10)
    val, tmp = 0, 0
    for x in reversed(ldig):
        if x in [10000, 100000000]:
            val += tmp * x
            tmp = 0
        else:
            tmp += x
    val += tmp
    return val


def autodoc(func):
    @functools.wraps(func)
    async def wrapper(_file, *args, **kwargs):
        ret = None
        if not (config.get_config("web.push_autodoc")):
            ret = await func(_file, *args, **kwargs)
            return ret
        try:
            ret = await func(_file, *args, **kwargs)
        except Exception as e:
            await pw_db.execute(NewRuleDoc.update(status=AutoDocStatus.FAILED.value).where(NewRuleDoc.fid == _file.id))
            logging.error(e)
            await MMPoster.send(e, True)
        else:
            await pw_db.execute(NewRuleDoc.update(status=AutoDocStatus.DONE.value).where(NewRuleDoc.fid == _file.id))
            await push2autodoc(_file.id)
        return ret

    return wrapper


async def push2autodoc(fid):
    doc = await NewRuleDoc.find_by_kwargs(fid=fid, status=AutoDocStatus.DONE.value)
    if not doc:
        return
    ret = await NewRuleResult.find_by_kwargs("all", fid=fid)

    try:
        file = await NewFile.find_by_id(fid)
        if not file.molds or len(file.molds) > 1:
            # NOTE: 和 autodoc 对接的特定需求，暂不支持多 schema
            raise CustomError("multi molds is unsupported")
        schema = await NewMold.find_by_id(file.molds[0])

        app_id = config.get_config("app.auth.autodoc.app_id")
        secret_key = config.get_config("app.auth.autodoc.secret_key")
        if ret:
            payload = {"doclet_id": doc.doclet_id, "schema": schema.data, "records": ret}
        else:
            payload = {}

        logging.info(f"File: {fid}, {len(ret)} rules parsed")

        url = encode_url(doc.callback, app_id, secret_key)
        requests.post(url, json=payload, timeout=10)
    except requests.RequestException as e:
        logging.error(e)
        await MMPoster.send(
            """Push to AutoDoc Failed!\n> fid: {}\n> rules parsed: {}\n> doclet_id: {}\n> callback: {}\n> error: {}
            """.format(fid, len(ret), doc.doclet_id, doc.callback, e),
            True,
        )
    # else:
    #     mm_notify(
    #         '''Push to AutoDoc Success!\n> fid: {}\n> rules parsed: {}\n> doclet_id: {}\n> callback: {}
    #         '''.format(
    #             fid, len(ret), doc.doclet_id, doc.callback
    #         )
    #     )


def get_all_schema(question):
    preset_answer = question.preset_answer
    schemas = preset_answer["schema"]["schemas"]
    schema = schemas[0]
    return schema


def get_texts_map(cols, question, sub_lower=False, need_split=False):
    preset_answer = question.preset_answer
    reverse_cols = {v: k for k, v in cols.items()}
    specific_num = {k: {"texts": 0, "line_infos": []} for k, v in cols.items()}
    if not preset_answer:
        return specific_num
    for answer in preset_answer["userAnswer"]["items"]:
        origin_key = answer["key"].encode("utf-8").decode("unicode_escape")
        key = get_rule_by_key(origin_key)
        if key in cols.values():
            data_items = answer["data"]
            texts = ""
            line_infos = []
            cols_key = reverse_cols[key]
            for data in data_items:
                repair_text = data.get("text", "")
                need_origin = True
                if repair_text:
                    need_origin = False
                    texts += repair_text
                for box in data["boxes"]:
                    box_lines = box["box"]
                    out_line = [
                        box_lines["box_left"],
                        box_lines["box_top"],
                        box_lines["box_right"],
                        box_lines["box_bottom"],
                    ]
                    line_infos.append({"out_line": out_line, "page": box["page"]})

                    text = box.get("text", "")
                    if need_origin and text:
                        texts += text
                if need_split:
                    texts += "\n"
            if sub_lower and "lower" in cols_key:
                texts = re.sub(r"[\s,元]", "", texts)
                # try:
                #     texts = float(texts)
                # except ValueError:
                #     texts = 0
            # line_infos = merge_box(line_infos)
            specific_num[cols_key] = {
                "texts": texts,
                "line_infos": line_infos,
                "schema_key": answer["key"],
            }
    return specific_num


def get_rule_by_key(key):
    return key.split('"')[-2][:-2]


def get_xpath(pdfinsight, box=None, ele=None):
    x_paths = []
    if ele:
        xpath = ele.get("docx_meta", {}).get("xpath")
        if xpath:
            x_paths.append(xpath)
        return x_paths

    _, ele = pdfinsight.find_element_by_outline(box["page"], box_to_outline(box["box"]))
    if ele:
        xpath = ele.get("docx_meta", {}).get("xpath")
        if xpath:
            x_paths.append(xpath)
    return x_paths


if __name__ == "__main__":
    print(lower2upper("0"))
