from .base_hub_connection_state import BaseHubConnectionState
from ...messages.base_message import BaseMessage
from .hub_connection_state import HubConnectionState
from ..errors import HubConnectionError


class DisconnectedHubState(BaseHubConnectionState):
    state = HubConnectionState.disconnected

    def __init__(self, context) -> None:
        super().__init__(context)

    def on_enter(self, previous_state: HubConnectionState) -> None:
        super().on_enter(previous_state)
        self.context.callbacks["on_close"]()

    def on_exit(self, next_state: HubConnectionState) -> None:
        super().on_exit(next_state)

    def start(self) -> bool:
        result = self.context.transport.start()
        self.context.change_state(HubConnectionState.connecting)
        return result

    def stop(self):
        raise HubConnectionError("Cant stop in Disconnected state")

    def send(self, message: BaseMessage) -> None:
        raise HubConnectionError("Cant send messages on disconnected state")
