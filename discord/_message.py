from discord._json_object import JsonObject
from discord._websocket import Websocket
import requests

DISCORD_API = 'https://discord.com/api'


class Author(JsonObject):
    def mention(self):
        print(self.__dict__)
        return f'<@!{self.id}>'


class Message(JsonObject):
    _field_classes = {'author': Author}

    def __init__(self, json_message, ws: Websocket):
        JsonObject.__init__(self, json_message)
        self.ws = ws

    def respond(self, message):
        print('should send message with token', message, self.ws.bot_token)
        response = requests.post(
            f'{DISCORD_API}/channels/{self.channel_id}/messages',
            headers={'Content-Type': 'application/json', 'Authorization': f'Bot {self.ws.bot_token}'},
            json={'content': message},
        )
        response.raise_for_status()
        return response.json()
