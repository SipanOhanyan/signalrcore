from enum import Enum


class HubConnectionState(Enum):
    disconnected = 0
    connecting = 1
    connected = 2
    reconnecting = 3
