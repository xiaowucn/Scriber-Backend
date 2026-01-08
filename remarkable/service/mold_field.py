import peewee

from remarkable.db import pw_db
from remarkable.pw_models.model import NewMoldField


class MoldFieldService:
    @staticmethod
    async def get_mold_field_uuid_path(mid: int) -> list[dict]:
        """
        获取指定模板(mid)下所有叶子节点的 uuid 路径
        """

        # 以叶子为基，向上回溯至根，构建根->叶路径
        base = NewMoldField.select(
            NewMoldField.id,
            NewMoldField.uuid,
            NewMoldField.parent,
            NewMoldField.is_leaf,
            peewee.SQL("1").alias("level"),
            peewee.fn.JSONB_BUILD_ARRAY(NewMoldField.uuid).alias("path"),
            NewMoldField.id.alias("leaf_id"),
            NewMoldField.uuid.alias("leaf_uuid"),
        ).where(NewMoldField.mid == mid, NewMoldField.is_leaf)

        cte = base.cte("path_cte", recursive=True)

        recursive = (
            NewMoldField.select(
                NewMoldField.id,
                NewMoldField.uuid,
                NewMoldField.parent,
                NewMoldField.is_leaf,
                (cte.c.level + 1).alias("level"),
                # peewee.SQL('to_jsonb("t2"."uuid") || "path_cte"."path"').alias("path"),
                peewee.fn.jsonb_insert(cte.c.path, "{0}", peewee.fn.to_jsonb(NewMoldField.uuid)).alias("path"),
                cte.c.leaf_id,
                cte.c.leaf_uuid,
            )
            .join(cte, on=(NewMoldField.uuid == cte.c.parent))
            .where(NewMoldField.mid == mid)
        )

        cte = cte.union_all(recursive)

        final_query = (
            cte.select_from(
                cte.c.leaf_id.alias("id"),
                cte.c.path,
            )
            .where(cte.c.parent.is_null())
            .order_by(cte.c.id)
        )

        rows = list(await pw_db.execute(final_query))
        return rows
