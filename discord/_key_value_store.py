from discord._rw_lock import RWLock


class KeyValueStore:
    def __init__(self, initial_values=None):
        self.values = initial_values if initial_values is not None else {}
        self.lock = RWLock()

    def get_int(self, key, default=None):
        with self.lock.read:
            if key in self.values: return self.values[key]
            if default is not None: return default
            raise KeyError(key)

    def increment_int(self, key, increment):
        with self.lock.write:
            if key not in self.values: self.values[key] = 0
            self.values[key] += increment
            return self.values[key]

    def decrement_int(self, key, decrement):
        with self.lock.write:
            if key not in self.values: self.values[key] = 0
            print(decrement)
            self.values[key] -= decrement
            return self.values[key]
