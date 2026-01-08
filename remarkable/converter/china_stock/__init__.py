from remarkable.answer.common import get_mold_name
from remarkable.converter import AnswerWorkShop, SimpleJSONConverter
from remarkable.db import pw_db
from remarkable.pw_models.model import NewChinaStockAnswer


class ChinaStockWorkShop(AnswerWorkShop):
    async def work(self):
        json_answer = SimpleJSONConverter(self.answer).convert()
        mold_name = get_mold_name(self.answer)
        if mold_name not in [
            "私募-基金合同",
            "公募-基金合同",
            "公募-托管协议",
            "公募-资产管理合同",
            "私募-运营操作备忘录",
        ]:
            return
        if mold_name == "公募-资产管理合同":
            product_name = json_answer.get("计划名称")
            managers = json_answer.get("计划管理人") or None
        elif mold_name == "私募-基金合同":
            product_name = json_answer.get("基金名称")
            managers = json_answer.get("基金管理人-名称") or None
        else:
            product_name = json_answer.get("基金名称")
            managers = json_answer.get("基金管理人") or None

        manager_name = None
        if isinstance(managers, str):
            manager_name = managers
        elif managers and isinstance(managers[0], dict):
            manager_name = managers[0].get("名称")

        answer = await NewChinaStockAnswer.find_by_kwargs(fid=self.file.id)
        params = {
            "qid": self.question.id,
            "fid": self.file.id,
            "tree_id": self.file.tree_id,
            "product_name": product_name,
            "manager_name": manager_name,
            "meta": json_answer,
        }
        if answer:
            await answer.update_(**params)
        else:
            await pw_db.create(NewChinaStockAnswer, **params)
