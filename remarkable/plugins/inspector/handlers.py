"""
新审核模块的相关接口
"""

import http

from remarkable.base_handler import Auth, PermCheckHandler
from remarkable.common.exceptions import ItemNotFound
from remarkable.plugins.cgs.services.comment import export_result_comment
from remarkable.plugins.inspector import plugin


@plugin.route(r"/files/(\d+)/schemas/(\d+)/export-comment")
class ExportCommentHandler(PermCheckHandler):
    @Auth("browse")
    async def get(self, fid, schema_id):
        export_type = "pdf"  # docx 效果不好,通用环境暂只支持pdf
        try:
            path = await export_result_comment(
                export_type, fid, schema_id, self.current_user.is_admin, self.current_user.id
            )
        except ItemNotFound:
            return self.error(_("Item not found"), status_code=http.HTTPStatus.NOT_FOUND)

        if not path:
            return self.error(_("data not ready"), status_code=http.HTTPStatus.BAD_REQUEST)
        return await self.export(path)
