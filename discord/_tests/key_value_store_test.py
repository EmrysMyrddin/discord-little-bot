import unittest

from discord._key_value_store import KeyValueStore


class KeyValueStoreTest(unittest.TestCase):
    def test_kv_get_returns_correct_value(self):
        kv = KeyValueStore({'test': 'result'})
        self.assertEqual('result', kv.get_int('test'))

    def test_kv_get_throws_on_unknown_key(self):
        kv = KeyValueStore()
        with self.assertRaises(KeyError):
            kv.get_int("unknown")

    def test_kv_get_with_default(self):
        kv = KeyValueStore()
        self.assertEqual('default', kv.get_int('test', default='default'))

    def test_kv_increment_unknown_key(self):
        kv = KeyValueStore()
        self.assertEqual(10, kv.increment_int('unknown', 10))
        self.assertEqual(10, kv.get_int('unknown'))

    def test_kv_increment_known_key(self):
        kv = KeyValueStore({'test': 10})
        self.assertEqual(20, kv.increment_int('test', 10))
        self.assertEqual(20, kv.get_int('test'))

    def test_kv_decrement_unknown_key(self):
        kv = KeyValueStore()
        self.assertEqual(-10, kv.decrement_int('unknown', 10))
        self.assertEqual(-10, kv.get_int('unknown'))