class SuggestionManager:
    MAPPING = {"开放日": "请补充开放日，或填写为“无”", "封闭期": "请补充封闭期，或填写为“无”"}

    @classmethod
    def get_suggestion_by_fields(cls, fields):
        if not fields:
            return None

        if not isinstance(fields, (list, tuple)):
            fields = [fields]

        mapping = {}
        for field in fields:
            if field not in mapping:
                mapping[field] = 1

        fields = list(mapping.keys())

        managed_fields = [field for field in fields if field in cls.MAPPING]
        other_fields = [field for field in fields if field not in cls.MAPPING]

        res = []

        if managed_fields:
            for field in managed_fields:
                res.append(cls.MAPPING[field])

        if other_fields:
            res.append(f'请补充{"、".join(other_fields)}')

        return "；".join(res)
