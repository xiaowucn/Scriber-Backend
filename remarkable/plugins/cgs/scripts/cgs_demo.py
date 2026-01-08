import base64
import hashlib
import json
import os
import time
import urllib
from datetime import datetime

import requests
from Crypto.Cipher import AES


def aes_encrypt(plaintext, key, fill=False):
    if isinstance(plaintext, str):
        plaintext = plaintext.encode("utf-8")
    key = key.encode("utf8")
    blocksize = 16
    reminder_len = len(plaintext) % blocksize
    reminder = b""
    if reminder_len > 0:
        if fill:
            plaintext += b"\0" * (blocksize - reminder_len)
        else:
            plaintext, reminder = plaintext[:-reminder_len], plaintext[-reminder_len:]
    aes = AES.new(key, AES.MODE_CBC, key[11:27])
    return aes.encrypt(plaintext) + reminder


def encrypt_userinfo(user_info, key):
    return base64.b64encode(aes_encrypt(json.dumps(user_info).encode("utf-8"), key=key, fill=True)).decode("utf-8")


def revise_url(url, extra_params=None, excludes=None, exclude_domain=False):
    extra_params = extra_params or {}
    excludes = excludes or []
    main_url, query = urllib.parse.splitquery(url)
    if exclude_domain:
        main_url = urllib.parse.urlsplit(main_url).path
    params = urllib.parse.parse_qs(query) if query else {}
    params.update(extra_params)
    keys = list(params.keys())
    keys.sort()
    params_strings = []
    for key in keys:
        if key in excludes:
            continue
        values = params[key]
        if isinstance(values, list):
            values.sort()
            params_strings.extend([urllib.parse.urlencode({key: value}) for value in values])
        else:
            params_strings.append(urllib.parse.urlencode({key: values}))

    return "{}?{}".format(main_url, "&".join(params_strings)) if params_strings else main_url


def generate_timestamp():
    delta = datetime.utcnow() - datetime.utcfromtimestamp(0)
    return int(delta.total_seconds())


def _generate_token(url, app_id, secret_key, extra_params=None, timestamp=None, exclude_domain=True):
    url = revise_url(url, extra_params=extra_params, excludes=["_token", "_timestamp"], exclude_domain=exclude_domain)
    timestamp_now = timestamp or generate_timestamp()
    source = "{}#{}#{}#{}".format(url, app_id, secret_key, timestamp_now)
    token = hashlib.md5(source.encode()).hexdigest()
    return token


def encode_url(url, app_id, secret_key, params=None, timestamp=None, exclude_domain=True):
    timestamp = timestamp or generate_timestamp()
    token = _generate_token(
        url.replace("/scriber", ""), app_id, secret_key, params, timestamp, exclude_domain=exclude_domain
    )
    extra_params = {"_timestamp": timestamp, "_token": token}
    extra_params.update(params or {})
    url = revise_url(url, extra_params=extra_params)
    return url


def get_ai_status(ip_address, file_id, schema_id, auth_params):
    print("start get_ai_status")

    api = "{}/api/v1/plugins/cgs/files/{}/schemas/{}/ai-status".format(ip_address, file_id, schema_id)
    url = encode_url(api, **auth_params)
    print("result: ", url)
    response = requests.get(url)
    print(response)
    assert response.status_code == 200
    print(response.status_code)
    print(response.text)
    return response.json()["data"]


def upload_file(ip_address, file_path, schema_id, auth_params, tree_id=None, task_type="audit"):
    print("start upload_file")

    api = "{}/api/v1/plugins/cgs/files/upload".format(ip_address)
    url = encode_url(api, **auth_params)
    req_body = {
        "file": (os.path.basename(file_path), open(file_path, "rb").read()),
    }
    data = {"task_type": task_type}
    if tree_id:
        data["tree_id"] = tree_id
    elif schema_id:
        data["schema_id"] = schema_id
    else:
        raise AssertionError("miss tree_id or schema_id")

    response = requests.post(
        url,
        data=data,
        files=req_body,
    )
    print(response.text)
    assert response.status_code == 200
    assert response.json()["data"][0]["filename"] == os.path.basename(file_path)
    return response.json()["data"][0]["id"]


def get_question_by_id(ip_address, question_id, auth_params):
    print("start get_question_by_id")
    api = "{}/api/v1/plugins/cgs/questions/{}".format(ip_address, question_id)
    url = encode_url(api, **auth_params)
    print("result: ", url)
    response = requests.get(url)
    assert response.status_code == 200
    print(response.status_code)
    print(response.text)
    return response.json()["data"]


def get_results(ip_address, file_id, schema_id, export_type, auth_params):
    print("start get_results")
    api = "{}/api/v1/plugins/cgs/files/{}/schemas/{}/compare-result".format(ip_address, file_id, schema_id)
    url = encode_url(api, **auth_params, params={"export_type": export_type})
    print("result: ", url)
    response = requests.get(url)
    assert response.status_code == 200
    print(response.status_code)
    print(response.text)


def get_audit_page(ip_address, file_id, schema_id, user, auth_params):
    print("start get_audit_page")
    _u = encrypt_userinfo(user, auth_params["secret_key"])
    print(f"_u {_u}")
    api = "{}/api/v1/plugins/cgs/files/{}/schemas/{}/audit".format(ip_address, file_id, schema_id)
    url = encode_url(api, **auth_params, params={"_u": _u})
    print("result: ", url)
    response = requests.get(url)
    print(response)
    assert response.status_code == 200


def get_training_data(ip_address, schema_id, export_type, auth_params):
    print("start get_training_data")
    api = "{}/api/v1/plugins/cgs/training_data".format(ip_address)
    url = encode_url(api, **auth_params, params={"schema_id": schema_id, "export_type": export_type})
    print("result: ", url)
    response = requests.get(url)
    assert response.status_code == 200
    print(response.status_code)
    print(response.text)


if __name__ == "__main__":
    auth_params = {
        "app_id": "cgs",
        "secret_key": "069f0ba4d5c635e9b98fb94b7cd98cc4",
        "exclude_domain": True,
    }
    ip_address = "http://bj.cheftin.cn:22105"
    test_file = "/tmp/test-1.pdf"
    schema_id = 7  # schema管理里的id
    tree_id = 5  # 顶层目录点进去，页面上的url里的id  http://bj.cheftin.cn:22105/#/project/9/tree/92  92就是

    # 上传文件到schema默认文件夹
    file_id = 541
    # file_id = upload_file(ip_address, test_file, schema_id, auth_params)  # 以shchema_id传
    # file_id = upload_file(ip_address, test_file, None, auth_params, tree_id=tree_id)  # 以tree_id传

    # 获取异步处理状态
    question_id = None
    while not question_id:
        data = get_ai_status(ip_address, file_id, schema_id, auth_params)
        time.sleep(3)
        if data.get("question") and data["question"]["ai_status"] == 3:
            print("提取完成,检查审核状态")
            if data.get("audit") and data["audit"]["status"] == 3:
                question_id = data["question"]["id"]
                print("审核完成")
                break

    # 获取提取结果
    get_question_by_id(ip_address, question_id=question_id, auth_params=auth_params)

    # 获取审核结果
    get_results(ip_address, file_id, schema_id, "csv", auth_params)

    get_training_data(ip_address, schema_id, "csv", auth_params)

    # 跳转到审核页面
    user = {
        "uid": "zhuozhuang_it",
        "uname": "卓壮",
        "sys_code": "RSP",
    }
    get_audit_page(ip_address, file_id, schema_id, user, auth_params)
