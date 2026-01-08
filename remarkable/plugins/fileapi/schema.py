from marshmallow import fields

from remarkable.models.query_helper import PaginationSchema


class TreeSchema(PaginationSchema):
    search_fid = fields.Int(required=False, load_default=None)
