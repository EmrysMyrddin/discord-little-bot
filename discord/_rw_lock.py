from gevent.event import Event
from gevent.lock import RLock


class RWLock:
    def __init__(self):
        self._w_lock = RLock()
        self._r_lock = RLock()
        self._readers = 0
        self._reader_released_event: Event
        self.read = LockContextManager(self.acquire_read, self.release_read)
        self.write = LockContextManager(self.acquire_write, self.release_write)

    def acquire_write(self):
        with self._r_lock:
            if self._readers == 0:
                self._w_lock.acquire()
                return
        self._reader_released_event.wait()
        self.acquire_write()

    def release_write(self):
        self._w_lock.release()

    def acquire_read(self):
        with self._w_lock:
            with self._r_lock:
                if self._readers == 0: self._reader_released_event = Event()
                self._readers += 1

    def release_read(self):
        with self._w_lock:
            with self._r_lock:
                self._readers -= 1
                if self._readers == 0: self._reader_released_event.set()


class LockContextManager:
    def __init__(self, acquire, release):
        self.acquire = acquire
        self.release = release

    def __enter__(self): self.acquire()
    def __exit__(self, exc_type, exc_val, exc_tb): self.release()