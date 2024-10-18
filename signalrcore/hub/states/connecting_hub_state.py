import logging
from .base_hub_connection_state\
    import BaseHubConnectionState, HubConnectionState
from ...protocol.base_hub_protocol import BaseHubProtocol


class ConnectingHubState(BaseHubConnectionState):
    state = HubConnectionState.connecting

    def __init__(self, context) -> None:
        super().__init__(context)

    def on_enter(self, previous_state: BaseHubConnectionState) -> None:
        super().on_enter(previous_state)

    def on_exit(self, next_state: BaseHubConnectionState) -> None:
        super().on_exit(next_state)

    def start(self) -> bool:
        logging.warning("Already started")
        return False

    def on_message(self, raw_message: str):
        protocol: BaseHubProtocol = self.context.protocol
        handshake_response, messages = protocol.decode_handshake(raw_message)
        if handshake_response.error is None or handshake_response.error == "":
            self.context.change_state(HubConnectionState.connected)
        else:
            self.logger.error(handshake_response.error)
            self.context.change_state(HubConnectionState.disconnected)
        return messages

    def on_close(self, callback):
        raise NotImplementedError()

    def on_open(self):
        protocol: BaseHubProtocol = self.context.protocol
        msg = protocol.handshake_message()
        self.context.transport.send(
            protocol.encode(msg).encode("utf-8"))

    def on_error(self, callback):
        raise NotImplementedError()

    def on_reconnect(self, callback):
        raise NotImplementedError()
