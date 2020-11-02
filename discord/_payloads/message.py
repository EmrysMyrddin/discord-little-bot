from .json_object import JsonObject
from .user import User
from .._websocket import Websocket
import requests

DISCORD_API = 'https://discord.com/api'


class Message(JsonObject):
    _field_classes = {'author': User}

    def __init__(self, json_message, ws: Websocket):
        JsonObject.__init__(self, json_message)
        self.ws = ws

    def respond(self, message):
        print(f'[Message] responding to message {self.id}: {message}')
        response = requests.post(
            f'{DISCORD_API}/channels/{self.channel_id}/messages',
            headers={'Content-Type': 'application/json', 'Authorization': f'Bot {self.ws.bot_token}'},
            json={'content': message},
        )
        response.raise_for_status()
        return response.json()
