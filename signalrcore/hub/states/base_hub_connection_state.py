from .hub_connection_state import HubConnectionState
from signalrcore.helpers import Helpers
from ...messages.base_message import BaseMessage
from ...protocol.base_hub_protocol import BaseHubProtocol
from ..errors import ConnectionClosedDError


class BaseHubConnectionState(object):
    state: HubConnectionState

    def __init__(self, context) -> None:
        self.logger = Helpers.get_logger()
        self.context = context
        self.context.transport.on_close_callback(self.on_close)
        self.context.transport.on_open_callback(self.on_open)
        self.context.transport.on_reconnect_callback(self.on_reconnect)
        self.context.transport.on_error_callback(self.on_error)

    def on_message(self, raw_message: str):
        raise NotImplementedError()

    def on_enter(self, previous_state: HubConnectionState) -> None:
        self.logger.debug(f"Entering {self.state} from  {previous_state}")

    def on_exit(self, next_state: HubConnectionState) -> None:
        self.logger.debug(f"Exiting {self.state} to {next_state}")

    def start(self) -> bool:
        raise NotImplementedError()

    def stop(self) -> None:
        self.context.transport.stop()
        self.context.change_state(HubConnectionState.disconnected)

    def on_close(self, callback):
        raise NotImplementedError()

    def on_open(self, callback):
        raise NotImplementedError()

    def on_error(self, ex: Exception):
        raise NotImplementedError()

    def on_reconnect(self, callback):
        raise NotImplementedError()

    def send(
            self,
            message: BaseMessage) -> None:
        protocol: BaseHubProtocol = self.context.protocol
        self.logger.debug("Sending message {0}".format(message))
        encoded_message = protocol.encode(message)
        try:
            self.context.transport.send(encoded_message)
        except ConnectionClosedDError as ex:
            self.on_error(ex)
