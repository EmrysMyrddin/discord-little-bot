class JsonObject:
    _field_classes = {}

    def __init__(self, json):
        for key in json:
            unmarshall = self._unmarshall(self._field_classes.get(key, JsonObject))
            setattr(self, key, unmarshall(json[key]))

    @staticmethod
    def _unmarshall(field_class):
        def unmarshall_field(json):
            if isinstance(json, list): return map(unmarshall_field, json)
            if isinstance(json, dict): return field_class(json)
            else: return json

        return unmarshall_field
