import json

import requests

domain = 'http://localhost:8000'
token = 'oLdU3pvF05rWbBVgzgzd'
headers = {'access-token': token}


def upload_file():
    url = '/external_api/v1/upload'
    file_path = '/Users/liuchao/Downloads/TestFile.pdf'

    with open(file_path, 'rb') as file:
        files = {'file': file}
        data = {
            'tree_id': 14,
            "meta": json.dumps({"schema_ids": [2, 3]}),
        }
        response = requests.post(f"{domain}{url}", files=files, data=data, headers=headers)
        print(response.json())


def get_process_status(file_id):
    url = f'/external_api/v1/files/{file_id}/status'
    response = requests.get(f"{domain}{url}", headers=headers)
    print(response.json())


def get_result(file_id):
    url = f'/external_api/v1/file/{file_id}/result/json?simple=2'
    response = requests.get(f"{domain}{url}", headers=headers)
    print(response.json())


if __name__ == '__main__':
    upload_file()
    # get_process_status(120)
    # get_result(120)



