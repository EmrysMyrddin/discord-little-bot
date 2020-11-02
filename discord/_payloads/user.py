from .json_object import JsonObject


class User(JsonObject):
    def mention(self):
        return f'<@!{self.id}>'
