import json
import gevent
from gevent import monkey
from gevent.pool import Group
from websocket import create_connection, WebSocketConnectionClosedException, STATUS_NORMAL

from ._payloads.guild import Guild
from ._actor import Actor

monkey.patch_all()


class Websocket:
    def __init__(self, bot_token, bot_class):
        self.bot_token = bot_token
        self.bot_class = bot_class

        self._handlers = [
            IdentityHandler(self),
            GuildsHandler(self),
            HeartbeatHandler(self),
        ]

    def listen(self):
        self._listening = True

        while self._listening:
            try:
                self._ws = create_connection('wss://gateway.discord.gg/?v=8&encoding=json')
                while True:
                    event = self.read()
                    if not event: continue
                    for handler in self.get_handlers_for_event(event):
                        handler.post(event)

            except (WebSocketConnectionClosedException, ConnectionResetError, TimeoutError):
                print('connection lost, reconnecting...')

            except BaseException as e:
                self.disconnect()
                raise e

    def get_handlers_for_event(self, event):
        return [handler for handler in self._handlers
                if event.op_code in handler.listen_for_events
                and event.type in handler.listen_for_events[event.op_code]
                and (handler.guild_id is None or event.payload.get('guild_id', None) == handler.guild_id)]

    def create_bot_instance(self, *args, **kwargs):
        bot_instance = self.bot_class(self, *args, **kwargs)
        self._handlers.append(bot_instance)
        return bot_instance

    def read(self):
        data = self._ws.recv()
        if not data: return

        event = json.loads(data)
        self.last_sequence = event['s']
        print(f"receive: {event['op']}/{event['t']}")
        return Event(event)

    def send(self, op_code, payload):
        message = {'op': op_code, 'd': payload}
        print(f'send: {op_code}')
        self._ws.send(json.dumps(message))

    def reconnect(self, status=STATUS_NORMAL):
        print('disconnecting')
        try:
            self._ws.close(status=status)
        except WebSocketConnectionClosedException:
            pass

    def disconnect(self):
        print('disconnecting')
        self._listening = False
        try: self._ws.close()
        except WebSocketConnectionClosedException: pass
        Group().imap_unordered(lambda handler: handler.close(), self._handlers)


class Event:
    def __init__(self, event):
        self.op_code = event['op']
        self.type = event['t']
        self.payload = event['d']


class Handler(Actor):
    """listen_for_events is a dict of op_codes and list of event types you want listen"""
    listen_for_events = {}

    """Is guild_id is not None, only event with the given guild_id will be dispatched to this handler"""
    guild_id = None

    def __init__(self, ws: Websocket):
        Actor.__init__(self)
        self.ws = ws

    @classmethod
    def print(cls, message: str, *args, **kwargs):
        """Print a debug log"""
        print(f"[{cls.__name__}]", message, *args, **kwargs)


class IdentityHandler(Handler):
    listen_for_events = {0: ['READY'], 7: [None], 9: [None], 10: [None]}

    def __init__(self, ws):
        Handler.__init__(self, ws)
        self.session_id = None

    def _receive(self, event):
        if event.op_code == 0 and event.type == 'READY':
            self.print('bot ready')
            self.session_id = event.payload['session_id']

        elif event.op_code == 10 and not self.session_id:
            if self.session_id:
                self.print('resuming')
                self.ws.send(6, {
                    'token': self.ws.bot_token, 'seq': self.ws.last_sequence, 'session_id': self.session_id
                })
            else:
                self.print('identifying')
                self.ws.send(2, {
                    'token': self.ws.bot_token, **_identity_properties
                })

        elif event.op_code == 9:
            if event.payload:
                self.print('invalid identity session, reconnecting')
                self.ws.reconnect()
            else:
                self.print('invalid identity, recreating session')
                self.session_id = None
                self.ws.reconnect(0)

        elif event.op_code == 7:
            self.print('graceful reconnection required')
            self.ws.reconnect()


class GuildsHandler(Handler):
    listen_for_events = {0: ['GUILD_CREATE']}

    def __init__(self, ws: Websocket):
        super().__init__(ws)
        self.guilds = {}

    def _receive(self, event):
        if event.type == 'GUILD_CREATE':
            guild = Guild(event.payload)
            if guild.id not in self.guilds:
                self.guilds[guild.id] = self.ws.create_bot_instance(guild=guild)


class HeartbeatHandler(Handler):
    listen_for_events = {10: [None], 11: [None], 1: [None]}

    def __init__(self, ws):
        Handler.__init__(self, ws)
        self._ack_timeout = None
        self._ping_greenlet = None

    def _receive(self, event):
        if event.op_code == 10:
            self.print('hello received')
            self.heartbeat_interval = event.payload['heartbeat_interval'] / 1000
            if self._ping_greenlet: gevent.killall([self._ping_greenlet])
            self._ping_greenlet = gevent.spawn(self.ping)
            self.print(f'ping began with {self.heartbeat_interval} interval')

        elif event.op_code == 1:
            self.print('ping required')
            self.ws.send(11, None)

        elif event.op_code == 11:
            self.print('ping ack received')
            gevent.kill(self._ack_timeout)

    def ping(self):
        while True:
            gevent.sleep(self.heartbeat_interval)
            self.print('ping sent')
            self._ack_timeout = gevent.spawn_later(5000, self.ws.reconnect)
            self.ws.send(1, self.ws.last_sequence)


_identity_properties = {
    'intents': 513,
    "properties": {
        "$os": "linux",
        "$browser": "Roulette Russe",
        "$device": "Roulette Russe"
    },
}
