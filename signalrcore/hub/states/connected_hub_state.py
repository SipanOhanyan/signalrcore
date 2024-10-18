import logging
from .base_hub_connection_state\
    import BaseHubConnectionState, HubConnectionState
from ...protocol.base_hub_protocol import BaseHubProtocol


class ConnectedHubState(BaseHubConnectionState):
    state = HubConnectionState.connected

    def __init__(self, context) -> None:
        super().__init__(context)

    def on_enter(self, previous_state: BaseHubConnectionState) -> None:
        super().on_enter(previous_state)
        self.context.callbacks["on_open"]()

    def on_exit(self, next_state: BaseHubConnectionState) -> None:
        super().on_exit(next_state)

    def on_message(self, raw_message: str):
        protocol: BaseHubProtocol = self.context.protocol
        return protocol.parse_messages(raw_message)

    def start(self) -> bool:
        logging.warning("Already started")
        return False

    def stop(self):
        self.context.change_state(HubConnectionState.disconnected)

    def on_close(self, callback):
        raise NotImplementedError()

    def on_open(self, callback):
        raise NotImplementedError()

    def on_error(self, exception: Exception):
        if self.context.reconnection_handler is None:
            self.context.change_state(HubConnectionState.disconnected)
        else:
            self.context.change_state(HubConnectionState.reconnecting)

    def on_reconnect(self, callback):
        raise NotImplementedError()
