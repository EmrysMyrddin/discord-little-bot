import json
import gevent
from gevent import monkey
from gevent.pool import Group
from websocket import create_connection, WebSocketConnectionClosedException, STATUS_NORMAL
from discord._actor import Actor

monkey.patch_all()


class Websocket:
    def __init__(self, bot_token, bot_class):
        self.bot_token = bot_token
        self.bot_class = bot_class

        self.handlers = [
            IdentityHandler(self),
            EventHandler(self),
            HeartbeatHandler(self),
        ]

    def listen(self):
        self.listening = True

        while self.listening:
            try:
                self.ws = create_connection('wss://gateway.discord.gg/?v=8&encoding=json', )
                while True:
                    event = self.read()
                    if not event: continue
                    for handler in self.get_handlers_for_event(event):
                        handler.post(event)

            except (WebSocketConnectionClosedException, ConnectionResetError):
                print('connection lost, reconnecting...')

            except BaseException as e:
                self.disconnect()
                raise e

    def get_handlers_for_event(self, event):
        return [handler for handler in self.handlers
                if event.op_code in handler.listen_for_events
                and event.type in handler.listen_for_events[event.op_code]]

    def create_bot_instance(self, *args, **kwargs):
        self.handlers.append(self.bot_class(self, *args, **kwargs))

    def read(self):
        data = self.ws.recv()
        if not data: return

        event = json.loads(data)
        self.last_sequence = event['s']
        print('receive: {}/{}'.format(event['op'], event['t']))
        return Event(event)

    def send(self, op_code, payload):
        message = {'op': op_code, 'd': payload}
        print('send: {}'.format(op_code))
        self.ws.send(json.dumps(message))

    def reconnect(self, status=STATUS_NORMAL):
        print('disconnecting')
        try: self.ws.close(status=status)
        except WebSocketConnectionClosedException: pass

    def disconnect(self):
        print('disconnecting')
        self.listening = False
        try: self.ws.close()
        except WebSocketConnectionClosedException: pass
        Group().imap_unordered(lambda handler: handler.close(), self.handlers)


class Event:
    def __init__(self, event):
        self.op_code = event['op']
        self.type = event['t']
        self.payload = event['d']


class Handler(Actor):
    listen_for_events = {}

    def __init__(self, ws: Websocket):
        Actor.__init__(self)
        self.ws = ws

    @classmethod
    def print(cls, message: str, *args, **kwargs):
        print("[{}] {}".format(cls.__name__, message.format(*args, **kwargs)))


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


class EventHandler(Handler):
    listen_for_events = {0: ['GUILD_CREATE']}

    def _receive(self, event):
        if event.type == 'GUILD_CREATE':

            self.ws.create_bot_instance(event.payload['id'])


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
            self.print('ping began with {} interval', self.heartbeat_interval)

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
