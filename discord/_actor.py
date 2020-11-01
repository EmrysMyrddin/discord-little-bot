from gevent import spawn, sleep, killall
from gevent.queue import Queue


class Actor:
    def __init__(self):
        self.inbox = Queue()
        self.greenlet = spawn(self._listen)

    def _listen(self):
        try:
            while True:
                message = self.inbox.get()
                self._receive(message)
                sleep(0)
        except ActorStop:
            pass

    def _receive(self, message):
        raise NotImplemented()

    def stop(self):
        killall([self.greenlet], exception=ActorStop)

    def post(self, message, block=True, timeout=None):
        self.inbox.put(message, block, timeout)


class ActorStop(Exception):
    pass
