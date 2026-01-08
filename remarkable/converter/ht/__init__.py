import json
import logging
from datetime import datetime

import requests
from requests.structures import CaseInsensitiveDict

from remarkable import config
from remarkable.common.util import clean_txt
from remarkable.converter import AnswerWorkShop
from remarkable.plugins.ext_api.answer import AnswerReader
from remarkable.pw_models.model import NewFileMeta, NewSpecialAnswer


class HtSecAnswerWorkShop(AnswerWorkShop):
    async def work(self):
        if not config.get_config("ht.esb.switch"):
            logging.info("push switch not turned on， do nothing")
            return
        dst_url = config.get_config("ht.esb.url", default=10)
        call_timeout = config.get_config("ht.esb.call_timeout", default=10)
        answer_reader = AnswerReader(self.answer)
        answer_node = answer_reader.tree
        answer_data = self.build_answer_dict(answer_node, {})
        answer_data = self.add_crude_answer(answer_data)
        await NewSpecialAnswer.update_or_create(self.question.id, NewSpecialAnswer.ANSWER_TYPE_JSON, answer_data)

        logging.info(f"esb url {dst_url}")
        try:
            response = self.post_to_esb(dst_url, answer_data, call_timeout)
            if response.status_code == 200:
                data = response.text
                logging.info(f"get api results: {data}")
                await self.save_response_to_db(data)
            else:
                logging.error(response.text)
        except Exception as exp:
            logging.exception(exp)
        return []

    def post_to_esb(self, dst_url, answer, call_timeout):
        interface_code = config.get_config("ht.esb.interface_code") or ""
        consumer_code = config.get_config("ht.esb.consumer_code") or ""
        result = {
            "file_name": self.file.name,
            "answer": answer,
        }
        result = json.dumps(result, ensure_ascii=False)
        headers = CaseInsensitiveDict()
        headers["Content-Type"] = "application/soap+xml"

        data = f"""
<soapenv:Envelope xmlns:soapenv="http://schemas.xmlsoap.org/soap/envelope/" xmlns:hts="http://www.htsec.com/">
	<soapenv:Header/>
	<soapenv:Body>
		<hts:request>
			<messageRequestHead>
				<consumerCode>{consumer_code}</consumerCode>
				<interfaceCode>{interface_code}</interfaceCode>
				<regSN></regSN>
				<empCode></empCode>
				<branchCode></branchCode>
				<mac></mac>
				<bizCode></bizCode>
			</messageRequestHead>
			<messageRequestBody>
				<ID>{str(self.file.id)}</ID>
				<CODE>0</CODE>
				<NOTE></NOTE>
				<RESULT>{result}</RESULT>
			</messageRequestBody>
		</hts:request>
	</soapenv:Body>
</soapenv:Envelope>
"""
        resp = requests.post(dst_url, headers=headers, data=data.encode("utf-8"), timeout=call_timeout)

        return resp

    async def save_response_to_db(self, data):
        data = {"esb_response": data}
        file_meta = await NewFileMeta.find_by_kwargs(ignore_deleted=False, file_id=self.file.id)
        if file_meta:
            await file_meta.update_(raw_data=data)
        file_meta = await NewFileMeta.find_by_kwargs(ignore_deleted=False, hash=self.file.hash)
        if file_meta:
            await file_meta.update_(raw_data=data)
        else:
            file_meta_info = {
                "file_id": self.file.id,
                "hash": self.file.hash,
                "title": "",
                "stock_code": "",
                "stock_name": "",
                "report_year": datetime.now().year,
                "doc_type": "",
                "publish_time": datetime.now().timestamp(),
                "raw_data": data,  # 主要保存返回的data
                "created_utc": self.file.created_utc,
                "deleted_utc": 0,
            }
            await NewFileMeta.create(**file_meta_info)

    @staticmethod
    def build_request_headers():
        headers = {
            "interfaceCode": (config.get_config("ht.esb.interface_code") or ""),
            "consumerCode": (config.get_config("ht.esb.consumer_code") or ""),
        }

        return headers

    def build_query_body(self, answer):
        result = {
            "file_name": self.file.name,
            "answer": answer,
        }
        _body = {
            "ID": str(self.file.id),  # fid 必填，用于和托管系统数据同步
            "CODE": "0",  # 必填，0：识别成功，1：识别失败
            "NOTE": "识别成功",  # 非必填，简要说明识别失败原因
            "RESULT": json.dumps(result),
        }
        return _body

    def build_answer_dict(self, answer_nodes, answer):
        # todo `联系人（业务联系表）` 可能有多组答案 答案格式的改动涉及客户现场的下游系统 暂时先不修改
        for _, answer_node in answer_nodes.branches():
            for answer_dict in answer_node.values():
                answer_key = answer_dict.name
                if not answer_dict.branches():
                    items = []
                    for boxes in answer_dict.data.data:
                        if answer_dict.data.get("value"):
                            texts = ""
                            for box in boxes["boxes"]:
                                texts += clean_txt(box["text"])
                            ans = {"value": answer_dict.data.get("value"), "text": texts}
                            items.append(ans)
                        else:
                            texts = ""
                            for box in boxes["boxes"]:
                                texts += clean_txt(box["text"])
                            ans = {"text": texts}
                            items.append(ans)
                    answer[answer_key] = items
                else:
                    _answer = {}
                    _answer = self.build_answer_dict(answer_dict, _answer)
                    answer[answer_key] = _answer
        return answer

    def add_crude_answer(self, answer_data):
        # 没有预测答案的schema，
        crude_answer = self.question.crude_answer
        existed_keys = self.find_existed_keys(answer_data)
        all_keys = self.find_all_keys()
        missed_keys = [key for key in all_keys if key not in existed_keys]
        for key in missed_keys:
            items = crude_answer.get(key, [])
            answer_text = clean_txt(items[0].get("text", "")) if items else ""
            if "-" in key:
                second_col, third_col = key.split("-")
                old_second_answer = answer_data["私募类基金合同"].get(second_col, {})
                old_third_answer = old_second_answer.get(third_col, [])
                old_third_answer.append({"text": answer_text})
                old_second_answer[third_col] = old_third_answer
            else:
                answer_data["私募类基金合同"][key] = [{"text": answer_text}]
        return answer_data

    @staticmethod
    def find_existed_keys(answer_data):
        existed_keys = []
        for key, item in answer_data["私募类基金合同"].items():
            if isinstance(item, list) and item:
                existed_keys.append(key)
            elif isinstance(item, dict):
                for sub_key, sub_item in item.items():
                    if not sub_item:
                        continue
                    existed_keys.append(f"{key}-{sub_key}")
        return existed_keys

    def find_all_keys(self):
        all_keys = []
        schema_map = {}
        has_children_schema = {}
        for schema in self.answer["schema"]["schemas"]:
            schema_map[schema["name"]] = schema["orders"]
        for schema in self.answer["schema"]["schemas"]:
            for key, item in schema["schema"].items():
                if item["type"] in schema_map:
                    has_children_schema[key] = schema_map[item["type"]]
        for key in schema_map["私募类基金合同"]:
            if key in schema_map:
                for sub_key in schema_map[key]:
                    all_keys.append(f"{key}-{sub_key}")
            elif key in has_children_schema:
                for sub_key in has_children_schema[key]:
                    all_keys.append(f"{key}-{sub_key}")
            else:
                all_keys.append(key)
        return all_keys
