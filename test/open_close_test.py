
import logging
import threading
from signalrcore.hub_connection_builder import HubConnectionBuilder
from test.base_test_case import BaseTestCase


class TestClientStreamMethod(BaseTestCase):
    def setUp(self):
        pass

    def tearDown(self):
        pass

    def test_start(self):
        connection = HubConnectionBuilder()\
            .with_url(self.server_url, options={"verify_ssl": False})\
            .configure_logging(logging.ERROR)\
            .build()

        _lock = threading.Lock()
        self.assertTrue(_lock.acquire(timeout=30))

        connection.on_open(lambda: _lock.release())
        connection.on_close(lambda: _lock.release())

        result = connection.start()

        self.assertTrue(result)

        self.assertTrue(_lock.acquire(timeout=30))  # Released on open

        result = connection.start()

        self.assertFalse(result)

        connection.stop()

        del connection

    def test_open_close(self):
        self.connection = self.get_connection()

        _lock = threading.Lock()

        self.connection.on_open(_lock.release)
        self.connection.on_close(_lock.release)

        self.assertTrue(_lock.acquire(timeout=15))

        self.connection.start()

        self.assertTrue(_lock.acquire(timeout=15))

        self.connection.stop()

        self.assertTrue(_lock.acquire(timeout=15))

        _lock.release()
        del _lock
