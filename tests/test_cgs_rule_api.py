import pytest

from remarkable.plugins.cgs import CGSHandler, handlers
from remarkable.plugins.cgs.rules.calculator import Token


class TestRuleApi:
    MID = 1
    @pytest.mark.gen_test
    async def test_expr_operators(self, http_client, login):
        login(handlers.ExprOperationHandler)
        rsp = await http_client.get("/plugins/cgs/expr-operators")
        assert rsp.status_code == 200
        assert set(rsp.json()["data"]) == set(Token.OPS.keys())

    @pytest.mark.gen_test
    async def test_validate_empty_rule(self, http_client, login):
        login(CGSHandler)

        data = {
            "name": "判空规则1",
            "schema_id": self.MID,
            "validate_company_info": True,
            "validate_bond_info": True,
            "tip_content": "test",
            "is_compliance_tip": True,
            "is_noncompliance_tip": True,
            "origin_content": "xxxx",
            "rule_type": "empty",
            "detail": {"field": {"name": "公司名称", "type": "文本"}},
        }

        rsp = await http_client.post("/plugins/cgs/rules", json_data={"rules": [data]})
        assert rsp.status_code == 200

        rule_id = rsp.json()["data"][0]["id"]

        data["name"] = "判空规则2"
        rsp = await http_client.post(f"/plugins/cgs/rules/{rule_id}", json_data=data)
        assert rsp.status_code == 200
        assert rsp.json()["data"]["name"] == data["name"]

        mapping = {"mapping": {"公司名称": {"value": "中国公司"}}}
        rsp = await http_client.post(f"/plugins/cgs/rules/{rule_id}/validate", json_data=mapping)
        result = rsp.json()["data"]["result"]
        assert result is True

        mapping = {"mapping": {"公司名称": {"value": None}}}
        rsp = await http_client.post(f"/plugins/cgs/rules/{rule_id}/validate", json_data=mapping)
        result = rsp.json()["data"]["result"]
        assert result is False

    @pytest.mark.gen_test
    async def test_validate_empty_answer(self, login, http_client):
        login(handlers.RulesHandler)
        login(handlers.RuleValidateHandler)

        data = {
            "name": "判空规则1",
            "schema_id": self.MID,
            "validate_company_info": True,
            "validate_bond_info": True,
            "tip_content": "test",
            "is_compliance_tip": True,
            "is_noncompliance_tip": True,
            "origin_content": "xxxx",
            "rule_type": "empty",
            "detail": {"field": {"name": "公司名称", "type": "文本"}},
        }

        rsp = await http_client.post("/plugins/cgs/rules", json_data={"rules": [data]})
        assert rsp.status_code == 200

        rule_id = rsp.json()["data"][0]["id"]

        mapping = {"mapping": {"公司名称": {}}}

        rsp = await http_client.post(f"/plugins/cgs/rules/{rule_id}/validate", json_data=mapping)
        result = rsp.json()["data"]["result"]
        assert result is False

        mapping = {"mapping": {"公司名称": {"value": None}}}
        rsp = await http_client.post(f"/plugins/cgs/rules/{rule_id}/validate", json_data=mapping)
        result = rsp.json()["data"]["result"]
        assert result is False

    @pytest.mark.gen_test
    async def test_validate_expr_rule(self, login, http_client):
        login(CGSHandler)

        data = {
            "name": "逻辑运算规则1",
            "schema_id": self.MID,
            "validate_company_info": True,
            "validate_bond_info": True,
            "tip_content": "test",
            "is_compliance_tip": True,
            "is_noncompliance_tip": True,
            "origin_content": "xxxx",
            "rule_type": "expr",
            "detail": {
                "expr": [{"name": "冷静期"}, ">", {"value": "24"}, "或", {"name": "考察期"}, "<", {"value": "3.3"}]
            },
        }

        rsp = await http_client.post("/plugins/cgs/rules", json_data={"rules": [data]})
        assert rsp.status_code == 200

        rule_id = rsp.json()["data"][0]["id"]
        data["name"] = "逻辑运算规则2"
        rsp = await http_client.post(f"/plugins/cgs/rules/{rule_id}", json_data=data)
        assert rsp.status_code == 200
        assert rsp.json()["data"]["name"] == data["name"]

        mapping = {"mapping": {"冷静期": {"value": "25"}, "考察期": {"value": "13"}}}
        rsp = await http_client.post(f"/plugins/cgs/rules/{rule_id}/validate", json_data=mapping)
        result = rsp.json()["data"]["result"]
        assert result is True

        mapping = {"mapping": {"冷静期": {"value": "23"}, "考察期": {"value": "1"}}}
        rsp = await http_client.post(f"/plugins/cgs/rules/{rule_id}/validate", json_data=mapping)
        result = rsp.json()["data"]["result"]
        assert result is True

        mapping = {"mapping": {"冷静期": {"value": "23"}, "考察期": {"value": "13"}}}
        rsp = await http_client.post(f"/plugins/cgs/rules/{rule_id}/validate", json_data=mapping)
        result = rsp.json()["data"]["result"]
        assert result is False

    @pytest.mark.gen_test
    async def test_validate_regex_rule(self, login, http_client):
        login(CGSHandler)

        data = {
            "name": "正则运算规则1",
            "schema_id": self.MID,
            "validate_company_info": True,
            "validate_bond_info": True,
            "tip_content": "test",
            "is_compliance_tip": True,
            "is_noncompliance_tip": True,
            "origin_content": "xxxx",
            "rule_type": "regex",
            "detail": {"regex": "^((?!中国|超级).)*$", "field": {"name": "公司名称"}, "message": "公司名称不合法名称"},
        }

        rsp = await http_client.post("/plugins/cgs/rules", json_data={"rules": [data]})
        assert rsp.status_code == 200

        rule_id = rsp.json()["data"][0]["id"]
        data["name"] = "正则运算规则2"
        rsp = await http_client.post(f"/plugins/cgs/rules/{rule_id}", json_data=data)
        assert rsp.status_code == 200
        assert rsp.json()["data"]["name"] == data["name"]

        mapping = {"mapping": {"公司名称": {"value": "一家公司"}}}
        rsp = await http_client.post(f"/plugins/cgs/rules/{rule_id}/validate", json_data=mapping)
        result = rsp.json()["data"]["result"]
        assert result is True

        mapping = {"mapping": {"公司名称": {"value": "中国公司"}}}
        rsp = await http_client.post(f"/plugins/cgs/rules/{rule_id}/validate", json_data=mapping)
        result = rsp.json()["data"]["result"]
        assert result is False

    @pytest.mark.gen_test
    async def test_validate_condition_rule(self, login, http_client):
        login(CGSHandler)

        data = {
            "name": "条件运算规则1",
            "schema_id": self.MID,
            "validate_company_info": True,
            "validate_bond_info": True,
            "tip_content": "test",
            "is_compliance_tip": True,
            "is_noncompliance_tip": True,
            "origin_content": "xxxx",
            "rule_type": "condition",
            "detail": {
                "conditions": [
                    {
                        "expr_if": {
                            "expr": [
                                {"name": "冷静期"},
                                ">",
                                {"value": "24"},
                            ],
                        },
                        "expr_then": {"expr": [{"name": "考察期"}, "<", {"value": "3.3"}]},
                    },
                    {
                        "expr_if": {
                            "expr": [
                                {"name": "冷静期"},
                                "==",
                                {"value": "24"},
                            ],
                        },
                        "expr_then": {"expr": [{"name": "考察期"}, "==", {"value": "3.3"}]},
                    },
                ]
            },
        }

        rsp = await http_client.post("/plugins/cgs/rules", json_data={"rules": [data]})
        assert rsp.status_code == 200

        rule_id = rsp.json()["data"][0]["id"]
        data["name"] = "逻辑运算规则2"
        rsp = await http_client.post(f"/plugins/cgs/rules/{rule_id}", json_data=data)
        assert rsp.status_code == 200
        assert rsp.json()["data"]["name"] == data["name"]

        mapping = {"mapping": {"冷静期": {"value": "25"}, "考察期": {"value": "1"}}}
        rsp = await http_client.post(f"/plugins/cgs/rules/{rule_id}/validate", json_data=mapping)
        result = rsp.json()["data"]["result"]
        assert result is True

        mapping = {"mapping": {"冷静期": {"value": "24"}, "考察期": {"value": "3.30"}}}
        rsp = await http_client.post(f"/plugins/cgs/rules/{rule_id}/validate", json_data=mapping)
        result = rsp.json()["data"]["result"]
        assert result is True

        mapping = {"mapping": {"冷静期": {"value": "23"}, "考察期": {"value": "2"}}}
        rsp = await http_client.post(f"/plugins/cgs/rules/{rule_id}/validate", json_data=mapping)
        data = rsp.json()["data"]
        print(rsp.json())
        assert data["result"] is None
        assert None == data["message"]
        assert "不符合任一条件" == data["reason"]

        mapping = {"mapping": {"冷静期": {"value": "25"}, "考察期": {"value": "4"}}}
        rsp = await http_client.post(f"/plugins/cgs/rules/{rule_id}/validate", json_data=mapping)
        data = rsp.json()["data"]
        print(rsp.json())
        assert data["result"] is False
        assert "考察期 < 3.3" == data["message"]
        assert "冷静期 > 24\n考察期 ≥ 3.3" == data["reason"]

    @pytest.mark.gen_test
    async def test_handler_exception(self, login, http_client):
        login(CGSHandler)

        data = {
            "name": "逻辑运算规则1",
            "schema_id": self.MID,
            "validate_company_info": True,
            "validate_bond_info": True,
            "tip_content": "test",
            "is_compliance_tip": True,
            "is_noncompliance_tip": True,
            "origin_content": "xxxx",
            "rule_type": "expr",
            "detail": {
                "expr": [
                    {"name": "冷静期"},
                    ">",
                    {"value": "24"},
                    {"value": "24"},
                    "或",
                    {"name": "考察期"},
                    "<",
                    {"value": "3.3"},
                ]
            },
        }

        rsp = await http_client.post("/plugins/cgs/rules", json_data=data)
        res = rsp.json()
        assert rsp.status_code == 422
        assert res["status"] == "error"


    @pytest.mark.gen_test
    async def test_delete_rule(self, http_client, login):
        login(CGSHandler)
        rsp = await http_client.get(f"/plugins/cgs/rules?mold_id={self.MID}")
        assert rsp.status_code == 200

        res = rsp.json()
        for item in res["data"]["items"]:
            rsp = await http_client.delete(f"/plugins/cgs/rules/{item["id"]}")
            assert rsp.status_code == 200