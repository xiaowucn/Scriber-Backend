import collections
import re
from copy import deepcopy

from remarkable.common.constants import TagType
from remarkable.common.exceptions import CustomError
from remarkable.common.schema import Schema
from remarkable.common.util import md5json
from remarkable.config import get_config
from remarkable.db import pw_db
from remarkable.models.cmf_china import CmfMoldFieldRef
from remarkable.models.model_version import NewModelVersion
from remarkable.models.new_file import NewFile
from remarkable.predictor.mold_schema import MoldSchema
from remarkable.pw_models.model import (
    MoldWithFK,
    NewExtractMethod,
    NewMold,
    NewMoldField,
    NewRuleClass,
    NewRuleItem,
    NewRuleResult,
    NewTag,
    NewTagRelation,
)
from remarkable.pw_models.question import NewQuestion


class NewMoldService:
    @classmethod
    async def create(cls, data, name, mold_type, user_id, model_name):
        if cls.is_reserved_mold(name):
            raise CustomError("检测到系统保留Schema，请换个别的名称")
        Schema.validate(data)
        params = {"data": data, "name": name, "mold_type": mold_type, "model_name": model_name}
        params["checksum"] = md5json(params["data"])
        params.setdefault("predictor_option", {"framework_version": "2.0"})
        params["uid"] = user_id
        params["public"] = get_config("web.default_mold_public", True)
        mold = await MoldWithFK.get_by_cond((MoldWithFK.name == name) & (MoldWithFK.deleted_utc == 0))
        if not mold:
            mold = await MoldWithFK.create(**params)
        else:
            raise CustomError(_("Duplicate schema name detected"))
        return mold

    @classmethod
    async def update(cls, mold, **params):
        if "name" in params:
            params["name"] = params["name"].strip()

        if "data" in params:
            params["checksum"] = md5json(params.get("data"))

        if "name" in params and mold.name != params["name"]:
            question = await NewQuestion.find_by_kwargs(mold=mold.id)
            if question:
                raise CustomError(_("Schema is in use, unable to modify name"))
            exists_mold = await NewMold.find_by_kwargs(name=params["name"])
            if exists_mold:
                raise CustomError(_("Duplicate schema name detected"))

        if "data" in params:
            Schema.validate(params["data"], mold.data)
        mold_data = params["data"] if "data" in params else mold.data
        schema = Schema(mold_data)
        if "meta" in params:
            schema.validate_meta(params["meta"])
        await mold.update_(**params)

        return mold

    @staticmethod
    def is_reserved_mold(mold_name):
        return mold_name in (get_config("web.answer_convert") or {})

    @staticmethod
    async def set_same_name_tag_on_molds(tag, mold_ids):
        from remarkable.service.new_file import NewFileService

        if not await NewMold.all_ids_exists(mold_ids):
            raise CustomError(_("Not all ids valid."))

        mold_tag = await NewTag.find_by_kwargs(name=tag.name, tag_type=TagType.MOLD)
        if not mold_tag:
            mold_tag = await NewTag.create(name=tag.name, tag_type=TagType.MOLD)
        tag_relations = await pw_db.execute(
            NewTagRelation.select().where(
                NewTagRelation.tag_id == mold_tag.id,
            )
        )
        exists_mold_ids = []
        for tag_relation in tag_relations:
            mold_id = tag_relation.relational_id
            exists_mold_ids.append(mold_id)
            if mold_id not in mold_ids:
                fids = await NewFileService.find_fids_by_tag_and_mold(tag.id, mold_id)
                if fids:
                    mold = await NewMold.find_by_id(mold_id)
                    raise CustomError(
                        _("Mold bound to tag has assign to file, cannot be deleted.") + f" {mold.name}, "
                        f"file_ids:{fids[:10]}"
                    )
                await tag_relation.delete_()

        for mold_id in set(mold_ids) - set(exists_mold_ids):
            await NewTagRelation.create(tag_id=mold_tag.id, relational_id=mold_id)

    # todo inv中的导入导出也调用service里的方法
    @classmethod
    async def sync_mold_and_rule(cls, meta, rewrite=False, rename=None):
        def pre_process(mold, obj):
            obj["mold"] = mold.id
            obj.pop("id", None)
            obj.pop("created_utc", None)
            obj.pop("updated_utc", None)
            obj.pop("deleted_utc", None)
            return obj

        mold_dict = meta["mold"]
        mold = await NewMold.find_by_name(mold_dict["name"])
        mold_dict.pop("id")

        if mold:  # 已有同名mold
            if rewrite:  # 覆盖
                await mold.update_(**mold_dict)
                await NewExtractMethod.clear_by_mold(mold.id)
                await NewRuleClass.clear_by_mold(mold.id)
                await NewRuleItem.clear_by_mold(mold.id)
            elif rename:  # 重命名
                mold_dict["name"] = rename
                mold_dict["data"]["schemas"][0]["name"] = rename
                mold = await NewMold.create(**mold_dict)
            else:
                return False, "name is duplicated"
        else:
            mold = await NewMold.create(**mold_dict)

        for obj in meta["extract_method"]:
            obj = pre_process(mold, obj)
            await NewExtractMethod.create(**obj)

        rule_class_id_map = {}
        for obj in meta["rule_class"]:
            old_id = obj["id"]
            obj = pre_process(mold, obj)
            rule_class = await NewRuleClass.create(**obj)
            rule_class_id_map[old_id] = rule_class.id

        for obj in meta["rule_item"]:
            obj = pre_process(mold, obj)
            obj["class_name"] = rule_class_id_map[obj.get("class_name", obj.get("class", ""))]
            obj.pop("class", None)
            await NewRuleItem.create(**obj)

        return True, None

    @classmethod
    async def export_schema(cls, mold_obj):
        return {
            "mold": mold_obj.to_dict(exclude=["created_utc", "updated_utc"]),
            "extract_method": (await cls.get_extract_methods([mold_obj])),
            "rule_class": (await cls.get_rule_classes([mold_obj])),
            "rule_item": (await cls.get_rule_items([mold_obj])),
        }

    @classmethod
    async def get_extract_methods(cls, molds):
        models = []
        for mold in molds:
            models.extend(await NewExtractMethod.find_by_mold(mold.id))
        return [m.to_dict(exclude=["created_utc", "updated_utc"]) for m in models]

    @classmethod
    async def get_rule_classes(cls, molds):
        models = []
        for mold in molds:
            models.extend(await NewRuleClass.list_by_mold(mold.id))
        return [m.to_dict(exclude=["created_utc", "updated_utc"]) for m in models]

    @classmethod
    async def get_rule_items(cls, molds):
        models = []
        for mold in molds:
            models.extend(await NewRuleItem.list_by_mold(mold.id))
        return [m.to_dict(exclude=["created_utc", "updated_utc"]) for m in models]

    @classmethod
    async def get_rule_results(cls, fid):
        models = await NewRuleResult.get_by_fid(fid)
        return [m.to_dict(exclude=["created_utc", "updated_utc"]) for m in models]

    @classmethod
    async def get_model_versions(cls, molds):
        model_versions = []
        for mold in molds:
            enable_version_id = await NewModelVersion.get_enabled_version(mold.id)
            enable_version = await NewModelVersion.find_by_id(enable_version_id)
            model_versions.append(enable_version)
        return [m.to_dict(exclude=["created_utc", "updated_utc"]) for m in model_versions]

    @classmethod
    def revise_model_config(cls, configs):
        # fixme: only for auto model
        # group by path[0]
        groups = collections.defaultdict(list)
        for config in configs:
            first_node_name = config["path"][0]
            groups[first_node_name].append(config)
        # revise master node config
        for group_configs in groups.values():
            if len(group_configs) == 1:
                continue
            master_config = None
            for config in group_configs:
                if len(config["path"]) == 1:
                    master_config = config
                    break
            if not master_config:
                continue
            if "auto" not in [model["name"] for model in master_config["models"]]:
                continue
            custom_reg_mapping = {}
            for config in group_configs:
                if len(config["path"]) == 1:
                    continue
                if "auto" not in [model["name"] for model in config["models"]]:
                    continue
                for model in config["models"]:
                    if model["name"] != "auto":
                        continue
                    if custom_regs := model.get("custom_regs"):
                        custom_reg_mapping[config["path"][1]] = custom_regs
            for model in master_config["models"]:
                if model["name"] != "auto":
                    continue
                model["custom_regs"] = custom_reg_mapping
        return configs

    @staticmethod
    def master_mold_with_merged_schemas(molds):
        if len(molds) == 1:
            return molds[0], molds

        # 去重,有相同名字的字段,或者相同名字的组合类型的,保留较新的mold里的
        unify_fields = set()
        unify_types = set()
        for mold in molds[::-1]:
            schemas = mold.data["schemas"]
            root_node = schemas[0]
            if not root_node.get("orders"):
                continue
            other_nodes = schemas[1:]

            root_node["orders"] = [x for x in root_node["orders"] if x not in unify_fields]
            root_node["schema"] = {k: v for k, v in root_node["schema"].items() if k in root_node["orders"]}
            used_types = [x["type"] for x in root_node["schema"].values()]  # 被使用了的组合类型
            unify_fields = unify_fields.union(root_node["orders"])
            for x in other_nodes:
                for v in x["schema"].values():
                    if v["type"] not in ("文本", "数字", "日期"):
                        used_types.append(v["type"])
            other_nodes = [x for x in other_nodes if x["name"] in used_types and x["name"] not in unify_types]
            unify_types = unify_types.union([x["name"] for x in other_nodes])

            other_nodes.insert(0, root_node)
            mold.data["schemas"] = other_nodes

        master_mold = deepcopy(molds[0])
        master_mold.name = "、".join([mold.name for mold in molds])
        root_node = master_mold.data["schemas"][0]
        for mold in molds[1:]:
            if mold.data["schemas"][0].get("orders"):
                root_node["orders"].extend(mold.data["schemas"][0]["orders"])
            root_node["schema"].update(mold.data["schemas"][0]["schema"])
            master_mold.data["schemas"].extend(mold.data["schemas"][1:])
        return master_mold, molds

    @staticmethod
    def update_merged_answer_key_path(p_molds_name, master_mold, key_path):
        if p_molds_name:
            key_path_list = key_path.split(",")
            key_path_list[0] = p_molds_name.sub(master_mold.name, key_path_list[0])
            key_path = ",".join(key_path_list)
        return key_path

    @staticmethod
    def get_p_molds_name(molds: list[NewMold]):
        p_molds_name = None
        if len(molds) > 1:
            p_molds_name = re.compile(r"|".join((mold.name for mold in molds[1:])))
        return p_molds_name

    @staticmethod
    async def get_related_molds(fid, master_question_mid):
        if get_config("data_flow.file_answer.with_all_molds"):
            file = await NewFile.find_by_id(fid)
            molds = await pw_db.execute(NewMold.select().where(NewMold.id.in_(file.molds)).order_by(NewMold.id))
        else:
            molds = await NewMold.get_related_molds(master_question_mid)
        return molds

    @staticmethod
    async def update_field(mold: NewMold):
        schema = MoldSchema(mold.data)
        field_items = schema.get_field_items(mold.id)
        await pw_db.update(mold, only=["data"])
        ids = list(await NewMoldField.bulk_insert(field_items, iter_ids=True))
        await CmfMoldFieldRef.bulk_insert([{"mold_field": _id} for _id in ids])

    @staticmethod
    def check_duplicate_keys(pairs):
        keys = set()
        for key, _value in pairs:
            if key in keys:
                raise CustomError("字段名称重复，请修改后重新上传")
            keys.add(key)
        return dict(pairs)
