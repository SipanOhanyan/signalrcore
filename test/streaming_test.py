import time
import threading
from test.base_test_case import BaseTestCase, Urls


class TestSendMethod(BaseTestCase):
    server_url = Urls.server_url_ssl
    received = False
    items = list(range(0, 10))

    def on_complete(self, x):
        self.complete = True

    def on_next(self, x):
        item = self.items[0]
        self.items = self.items[1:]
        self.assertEqual(x, item)

    def test_stream(self):
        self.complete = False
        connection = self.get_connection()
        lock = threading.Lock()
        self.assertTrue(lock.acquire(blocking=True, timeout=30))

        connection.on_open(lock.release)
        connection.on_close(lock.release)

        connection.start()
        self.assertTrue(lock.acquire(blocking=True, timeout=30))

        self.items = list(range(0, 10))
        connection.stream(
            "Counter",
            [len(self.items), 500]).subscribe({
                "next": self.on_next,
                "complete": self.on_complete,
                "error": self.fail  # TestcaseFail
             })

        while not self.complete:
            time.sleep(0.1)

        connection.stop()
        self.assertTrue(lock.acquire(blocking=True, timeout=30))
        del lock
        del connection

    def test_stream_error(self):
        self.complete = False
        self.items = list(range(0, 10))

        connection = self.get_connection()
        lock = threading.Lock()
        self.assertTrue(lock.acquire(blocking=True, timeout=30))

        connection.on_open(lock.release)
        connection.on_close(lock.release)

        connection.start()
        self.assertTrue(lock.acquire(blocking=True, timeout=30))

        my_stream = connection.stream(
            "Counter",
            [len(self.items), 500])

        self.assertRaises(
            TypeError,
            lambda: my_stream.subscribe(None))

        self.assertRaises(
            TypeError, lambda: my_stream.subscribe([self.on_next]))

        self.assertRaises(KeyError, lambda: my_stream.subscribe({
                "key": self.on_next
            }))

        self.assertRaises(ValueError, lambda: my_stream.subscribe({
                "next": "",
                "complete": 1,
                "error": []  # TestcaseFail
             }))

        connection.stop()
        self.assertTrue(lock.acquire(blocking=True, timeout=30))
        del lock
        del connection


class TestSendNoSslMethod(TestSendMethod):
    server_url = Urls.server_url_no_ssl


class TestSendMethodMsgPack(TestSendMethod):
    def get_connection(self):
        return super().get_connection(msgpack=True)


class TestSendMethodNoSslMsgPack(TestSendNoSslMethod):
    def get_connection(self):
        return super().get_connection(msgpack=True)
