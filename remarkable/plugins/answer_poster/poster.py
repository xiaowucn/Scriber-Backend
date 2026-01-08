import logging

from remarkable.common.schema import Schema
from remarkable.plugins.predict.answer import AnswerReader

from .builder import TableBuilder, namespaces
from .models import Record, create_db_session


class AnswerPoster:
    def __init__(self, dsn_url, orm_classes):
        self.conn = create_db_session(dsn_url)
        self.orm_classes = orm_classes

    def post(self, record_key, file_name, file_meta, schema, answer_version, answer):
        record_id = self._post_record(record_key, file_name, file_meta, schema, answer_version)
        if record_id is None:
            logging.info("record(%s) no need to update", record_key)
            return
        self._post_answer_data(record_id, answer)
        return

    def _post_record(self, record_key, file_name, file_meta, schema, result_version):
        def set_record(_record):
            _record.filename = file_name
            _record.filemeta = file_meta
            _record.schema = schema
            _record.result_version = result_version

        def clear_record_data(_record):
            for orm in self.orm_classes.values():
                self.conn.query(orm).filter_by(record_id=_record.id).delete()

        records = self.conn.query(Record).filter(Record.key == record_key).all()
        if records:
            record = records[0]
            if record.result_version == str(result_version):
                return None
            clear_record_data(record)
            set_record(record)
        else:
            record = Record()
            record.key = record_key
            set_record(record)
            self.conn.add(record)
        self.conn.commit()
        return record.id

    def _post_answer_data(self, record_id, answer):
        reader = AnswerReader(answer)
        schema = Schema(answer["schema"])
        answer_root, _ = reader.build_answer_tree()
        meta = {"record_id": record_id, "schema": schema}
        root_name = reader.main_schema["name"]
        root_type = root_name
        if root_name in answer_root:
            self._post_answer_node_recursively(answer_root[root_name, 0], root_type, **meta)
            self.conn.commit()

    def _post_answer_node_recursively(self, node, _type, foreign_key_name=None, foreign_key_value=None, **meta):
        record_id = meta.get("record_id")
        mold_schema = meta.get("schema")
        _schema = mold_schema.schema_dict[_type]
        _model = self.orm_classes[_type]()
        _model.record_id = record_id
        if foreign_key_name:
            setattr(_model, foreign_key_name, foreign_key_value)
        table_name = TableBuilder.table_name(_type)
        for col, defination in _schema["schema"].items():
            col_name = TableBuilder.column_name(col, namespace=namespaces.get(_type, {}))
            if col not in node:
                continue
            col_type = defination["type"]
            if col_type in mold_schema.schema_dict:
                for sub_node in node[col].values():
                    foreign_key = TableBuilder.foreign_key(table_name, col_name, relationship_column=True)
                    self._post_answer_node_recursively(
                        sub_node, col_type, foreign_key_name=foreign_key, foreign_key_value=_model, **meta
                    )
            elif col_type in mold_schema.enum_dict:
                if node[col]:
                    value_node = node[col, 0]
                    setattr(_model, col_name, value_node.data["value"])
            else:
                texts = []
                for data_node in node[col].values():
                    for data in data_node.data["data"]:
                        for box in data["boxes"]:
                            texts.append(box["text"])
                setattr(_model, col_name, "\n".join(texts))

        self.conn.add(_model)
        return _model
