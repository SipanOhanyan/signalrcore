import time
import logging
from .base_hub_connection_state\
    import BaseHubConnectionState, HubConnectionState
from ..invocation_result import InvocationResult


class ReconnectingHubState(BaseHubConnectionState):
    state = HubConnectionState.reconnecting

    def __init__(self, context) -> None:
        super().__init__(context)

    def on_enter(self, previous_state: BaseHubConnectionState) -> None:
        super().on_enter(previous_state)
        try:
            offset = self.context.reconnection_handler.next()
            self.context.transport.stop()
            time.sleep(offset)
            self.context.transport.start()
        except StopIteration:
            self.context.change_state(HubConnectionState.disconnected)

    def start(self) -> bool:
        logging.warning("Already started")
        return False

    def on_exit(self, next_state: BaseHubConnectionState) -> None:
        raise NotImplementedError()

    def on_close(self, callback):
        raise NotImplementedError()

    def on_open(self, callback):
        self.context.on_reconnect()
        self.context.change_state(HubConnectionState.connected)

    def on_error(self, callback):
        raise NotImplementedError()

    def on_reconnect(self, callback):
        raise NotImplementedError()

    def send(self, message) -> InvocationResult:
        raise NotImplementedError()
