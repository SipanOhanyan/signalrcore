import threading
from signalrcore.subject import Subject
from test.base_test_case import BaseTestCase, Urls


class TestClientStreamMethod(BaseTestCase):

    def test_stream(self):
        connection = self.get_connection()
        lock = threading.Lock()
        self.assertTrue(lock.acquire(blocking=True, timeout=30))

        connection.on_open(lock.release)
        connection.on_close(lock.release)

        connection.start()
        self.assertTrue(lock.acquire(blocking=True, timeout=30))

        self.items = list(range(0, 10))
        subject = Subject()
        connection.send("UploadStream", subject)

        while len(self.items) > 0:
            item = str(self.items.pop())
            self.assertIsNone(
                subject.next(item),
                f"Error receiving item {item}")
        subject.complete()

        self.assertTrue(len(self.items) == 0)

        connection.stop()
        self.assertTrue(lock.acquire(blocking=True, timeout=30))
        del lock


class TestClientStreamMethodMsgPack(TestClientStreamMethod):
    def get_connection(self):
        return super().get_connection(msgpack=True)


class TestClientNoSslStreamMethodMsgPack(TestClientStreamMethodMsgPack):
    server_url = Urls.server_url_no_ssl


class TestClientNoSslStreamMethod(TestClientStreamMethod):
    server_url = Urls.server_url_no_ssl
