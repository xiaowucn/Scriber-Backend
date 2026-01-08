import json

from remarkable.fintable.schema import build_fintable_schema

if __name__ == "__main__":
    schema = build_fintable_schema()
    print(json.dumps(schema, ensure_ascii=False))
