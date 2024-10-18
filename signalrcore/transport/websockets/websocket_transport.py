import websocket
import threading
import requests
import traceback
import ssl
import logging
from ...hub.errors\
    import HubError, UnAuthorizedHubError, ConnectionClosedDError
from ..base_transport import BaseTransport
from ...helpers import Helpers


class WebsocketTransport(BaseTransport):
    def __init__(
            self,
            url="",
            headers=None,
            keep_alive_interval=15,
            reconnection_handler=None,
            verify_ssl=False,
            skip_negotiation=False,
            enable_trace=False,
            **kwargs):
        super(WebsocketTransport, self).__init__(**kwargs)
        self._ws = None
        self.enable_trace = enable_trace
        self._thread = None
        self.skip_negotiation = skip_negotiation
        self.keep_alive_interval = keep_alive_interval
        self.url = url
        if headers is None:
            self.headers = dict()
        else:
            self.headers = headers
        self.handshake_received = False
        self.token = None  # auth
        self.connection_alive = False
        self._thread = None
        self._ws = None
        self.verify_ssl = verify_ssl
        self.reconnection_handler = reconnection_handler

        if len(self.logger.handlers) > 0:
            websocket.enableTrace(self.enable_trace, self.logger.handlers[0])
        self.on_close_called = False

    def stop(self, wait=False):
        self.on_close_called = True
        self._ws.close()
        if wait:
            self._thread.join()

    def start(self) -> bool:
        if not self.skip_negotiation:
            self.negotiate()

        self.logger.debug("start url:" + self.url)

        self._ws = websocket.WebSocketApp(
            self.url,
            header=self.headers,
            on_message=self.on_message,
            on_error=self.on_socket_error,
            on_close=self.on_close,
            on_open=self.on_open)

        self._thread = threading.Thread(target=self.run_loop)
        self._thread.daemon = True
        self._thread.start()
        return True

    def run_loop(self):
        try:
            self._ws.run_forever(
                sslopt={"cert_reqs": ssl.CERT_NONE}
                if not self.verify_ssl else {}
            )
        except Exception as ex:
            logging.error(ex)

    def negotiate(self):
        negotiate_url = Helpers.get_negotiate_url(self.url)
        self.logger.debug("Negotiate url:{0}".format(negotiate_url))

        response = requests.post(
            negotiate_url, headers=self.headers, verify=self.verify_ssl)
        self.logger.debug(
            "Response status code{0}".format(response.status_code))

        if response.status_code != 200:
            raise HubError(response.status_code)\
                if response.status_code != 401 else UnAuthorizedHubError()

        data = response.json()

        if "connectionId" in data.keys():
            self.url = Helpers.encode_connection_id(
                self.url, data["connectionId"])

        # Azure
        if 'url' in data.keys() and 'accessToken' in data.keys():
            Helpers.get_logger().debug(
                "Azure url, reformat headers, token and url {0}".format(data))
            self.url = data["url"]\
                if data["url"].startswith("ws") else\
                Helpers.http_to_websocket(data["url"])
            self.token = data["accessToken"]
            self.headers = {"Authorization": "Bearer " + self.token}

    def on_open(self, _):
        self.logger.debug("-- web socket open --")
        self._on_open()

    def on_close(self, _, close_status_code, close_reason):
        self.logger.debug("-- web socket close --")
        self.logger.debug(close_status_code)
        self.logger.debug(close_reason)
        if self.on_close_called and\
                self._on_close is not None\
                and callable(self._on_close):
            self._on_close(close_status_code, close_reason)
        if not self.on_close_called:
            try:
                threading.Thread(
                    target=lambda: self._on_error(
                        HubError(
                            f"Close raised status code: {close_status_code}"))
                ).start()
            except Exception as ex:
                logging.error(ex)

    def on_socket_error(self, app, error):
        """
        Args:
            _: Required to support websocket-client version
                equal or greater than 0.58.0
            error ([type]): [description]

        Raises:
            HubError: [description]
        """
        self.logger.debug("-- web socket error --")
        self.logger.error(traceback.format_exc(10, True))
        self.logger.error("{0} {1}".format(self, error))
        self.logger.error("{0} {1}".format(error, type(error)))
        self._on_error(error)

    def on_message(self, app, raw_message):
        return self._on_message(raw_message)

    def send(self, encoded_message):
        logging.debug(f"{type(encoded_message)}: {encoded_message}")

        opcode = 0x2 if type(encoded_message) is not str else 0x1
        if type(encoded_message) is not str and\
                type(encoded_message) is not bytes:
            raise ValueError(
                f"Encoded message type not valid {type(encoded_message)}")
        try:
            self._ws.send(encoded_message, opcode=opcode)
        except (
                websocket._exceptions.WebSocketConnectionClosedException,
                OSError) as ex:
            raise ConnectionClosedDError(ex)
        except Exception as ex:
            raise ex
