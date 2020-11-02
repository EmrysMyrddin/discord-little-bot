import inspect
from typing import Callable, Any

import gevent

from ._key_value_store import KeyValueStore
from ._payloads.guild import Guild
from ._payloads.message import Message
from ._websocket import Websocket, Handler


class Bot(Handler):
    listen_for_events = {0: ['MESSAGE_CREATE', 'GUILD_CREATE', 'GUILD_UPDATE']}
    _discord_commands = []

    def __init__(self, ws, guild):
        Handler.__init__(self, ws)
        self.kv = KeyValueStore()
        self.guild_id = guild.id
        self.guild = guild
        self.disabled_commands = {}

    def __init_subclass__(cls):
        cls._discord_commands = cls._get_commands()

    def _receive(self, event):
        if event.type == 'GUILD_UPDATE' or event.type == 'GUILD_CREATE':
            self.guild = Guild(event.payload)

        elif event.type == 'MESSAGE_CREATE':
            self.print(f"handling message from {event.payload['author']['username']} in guild {self.guild_id}")
            command = self._find_matching_command(event.payload)
            if not command:
                self.print(f'no command found for message "{event.payload["content"]}"')
                return

            # FIXME: Keep track of spawned command handlers and kill them when the bot is shutdown ?
            gevent.spawn(command, self, Message(event.payload, self.ws))
            if command.cooldown > 0:
                self.disable_command(command)
                gevent.spawn_later(command.cooldown, self.enable_command, command)

    def enable_command(self, command):
        del self.disabled_commands[command]

    def disable_command(self, command):
        self.disabled_commands[command] = True

    def _find_matching_command(self, message):
        return next((
            command for command in self._discord_commands
            if message['content'].startswith(command.command_name)
            and command not in self.disabled_commands
        ), None)

    @classmethod
    def run(cls, bot_token: str):
        """Starts the bot and listens for Discord events. This will create Bot instances for each connected guild."""
        if len(cls._discord_commands) == 0:
            raise ValueError('No command found. Please register commands using @Bot.register_command(name) decorator')

        ws = Websocket(bot_token, cls)
        ws.listen()

    @staticmethod
    def register_command(command_name: str, cooldown=0):
        """Registers a new command"""
        def decorator(command_handler: Callable[[Bot, Message], Any]):
            command_handler.is_discord_command = True
            command_handler.command_name = command_name
            command_handler.cooldown = cooldown
            return command_handler

        return decorator

    @classmethod
    def _get_commands(cls):
        return [
            member for (_, member) in inspect.getmembers(cls)
            if getattr(member, 'is_discord_command', False)
        ]


