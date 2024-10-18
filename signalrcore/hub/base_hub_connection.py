import logging
import uuid
from typing import Callable, Optional, Union, Any, List
from signalrcore.messages.message_type import MessageType
from signalrcore.messages.stream_invocation_message\
    import StreamInvocationMessage
from .errors import HubConnectionError
from .handlers import StreamHandler, InvocationHandler
from ..transport.websockets.websocket_transport import WebsocketTransport
from ..helpers import Helpers
from ..subject import Subject
from ..messages.invocation_message import InvocationMessage
from ..transport.reconnection import ReconnectionHandler
from .states.connected_hub_state import ConnectedHubState
from .states.connecting_hub_state import ConnectingHubState
from .states.disconnected_hub_state import DisconnectedHubState
from .states.reconnecting_hub_state import ReconnectingHubState
from .states.base_hub_connection_state\
    import HubConnectionState, BaseHubConnectionState
from ..protocol.json_hub_protocol import JsonHubProtocol, BaseHubProtocol


class InvocationResult(object):
    def __init__(self, invocation_id: str) -> None:
        self.invocation_id: str = invocation_id
        self.message = None


class BaseHubConnection(object):
    def __init__(
            self,
            url: str,
            protocol: BaseHubProtocol = JsonHubProtocol(),
            reconnection_handler: Optional[ReconnectionHandler] = None,
            headers=None,
            **kwargs):
        self.protocol = protocol
        if headers is None:
            self.headers = dict()
        else:
            self.headers = headers
        self.logger = Helpers.get_logger()
        self.reconnection_handler = reconnection_handler
        self.handlers = []
        self.stream_handlers = []
        self._on_error = lambda error: self.logger.info(
            "on_error not defined {0}".format(error))

        self.states = {
            HubConnectionState.connected: ConnectedHubState,
            HubConnectionState.disconnected: DisconnectedHubState,
            HubConnectionState.connecting: ConnectingHubState,
            HubConnectionState.reconnecting: ReconnectingHubState
        }

        self.transport = WebsocketTransport(
            url=url,
            headers=self.headers,
            on_message=self._on_message,
            **kwargs)

        self.state: BaseHubConnectionState =\
            self.states[HubConnectionState.disconnected](self)

        self.callbacks = {
            "on_close": lambda: logging.warning(
                "on_close Not registered"),
            "on_open": lambda: logging.warning(
                "on_open Not registered"),
            "on_error": lambda _: logging.warning(
                "on_error Not registered"),
            "on_reconnect": lambda: logging.warning(
                "on_reconnect Not registered")
        }

    def _on_message(self, raw_message):
        self.logger.info(f"Message received {raw_message}")
        messages = self.state.on_message(raw_message)
        return self.on_message(messages)

    def change_state(self, state: HubConnectionState) -> None:
        previous_state = self.state.state
        self.state.on_exit(state)
        self.state = self.states[state](self)
        self.state.on_enter(previous_state)

    def start(self):
        self.logger.debug("Connection started")
        return self.state.start()

    def stop(self):
        self.logger.debug("Connection stop")
        return self.state.stop()

    def on_close(self, callback: Callable):
        """Configures on_close connection callback.
            It will be raised on connection closed event
        connection.on_close(lambda: print("connection closed"))
        Args:
            callback (function): function without params
        """
        self.callbacks["on_close"] = callback

    def on_open(self, callback: Callable):
        """Configures on_open connection callback.
            It will be raised on connection open event
        connection.on_open(lambda: print(
            "connection opened "))
        Args:
            callback (function): function without params
        """
        self.callbacks["on_open"] = callback

    def on_error(self, callback: Callable):
        """Configures on_error connection callback. It will be raised
            if any hub method throws an exception.
        connection.on_error(lambda data:
            print(f"An exception was thrown closed{data.error}"))
        Args:
            callback (function): function with one parameter.
                A CompletionMessage object.
        """
        self.callbacks["on_error"] = callback

    def on_reconnect(self, callback):
        """Configures on_reconnect reconnection callback.
            It will be raised on reconnection event
        connection.on_reconnect(lambda: print(
            "connection lost, reconnection in progress "))
        Args:
            callback (function): function without params
        """
        self.callbacks["on_reconnect"] = callback

    def on(self, event, callback_function: Callable):
        """Register a callback on the specified event
        Args:
            event (string):  Event name
            callback_function (Function): callback function,
                arguments will be bound
        """
        self.logger.debug("Handler registered started {0}".format(event))
        self.handlers.append((event, callback_function))

    def send(
            self,
            method: str,
            arguments: Union[List[Any], Subject],
            on_invocation:  Callable = None,
            invocation_id: str = None) -> InvocationResult:
        """Sends a message

        Args:
            method (string): Method name
            arguments (list|Subject): Method parameters
            on_invocation (function, optional): On invocation send callback
                will be raised on send server function ends. Defaults to None.
            invocation_id (string, optional): Override invocation ID.
                Exceptions thrown by the hub will use this ID,
                making it easier to handle with the on_error call.

        Raises:
            HubConnectionError: If hub is not ready to send
            TypeError: If arguments are invalid list or Subject
        """
        if invocation_id is None:
            invocation_id = str(uuid.uuid4())

        if self.state.state == HubConnectionState.disconnected:
            raise HubConnectionError(
                "Cannot connect to SignalR hub. Unable to transmit messages")

        if type(arguments) is not list and type(arguments) is not Subject:
            raise TypeError("Arguments of a message must be a list or subject")

        result = InvocationResult(invocation_id)

        if type(arguments) is list:
            message = InvocationMessage(
                invocation_id,
                method,
                arguments,
                headers=self.headers)

            if on_invocation:
                self.stream_handlers.append(
                    InvocationHandler(
                        message.invocation_id,
                        on_invocation))

            self.state.send(message)
            result.message = message

        if type(arguments) is Subject:
            arguments.connection = self
            arguments.target = method
            arguments.start()
            result.invocation_id = arguments.invocation_id
            result.message = arguments

        return result

    def on_message(self, messages):
        for message in messages:
            if message.type == MessageType.invocation_binding_failure:
                self.logger.error(message)
                self._on_error(message)
                continue

            if message.type == MessageType.ping:
                continue

            if message.type == MessageType.invocation:
                fired_handlers = list(
                    filter(
                        lambda h: h[0] == message.target,
                        self.handlers))
                if len(fired_handlers) == 0:
                    self.logger.debug(
                        f"event '{message.target}' hasn't fired any handler")
                for _, handler in fired_handlers:
                    handler(message.arguments)

#            if message.type == MessageType.close:
#                self.logger.info("Close message received from server")
#                self.stop()
                return

            if message.type == MessageType.completion:
                if message.error is not None and len(message.error) > 0:
                    self._on_error(message)

                # Send callbacks
                fired_handlers = list(
                    filter(
                        lambda h: h.invocation_id == message.invocation_id,
                        self.stream_handlers))

                # Stream callbacks
                for handler in fired_handlers:
                    handler.complete_callback(message)

                # unregister handler
                self.stream_handlers = list(
                    filter(
                        lambda h: h.invocation_id != message.invocation_id,
                        self.stream_handlers))

            if message.type == MessageType.stream_item:
                fired_handlers = list(
                    filter(
                        lambda h: h.invocation_id == message.invocation_id,
                        self.stream_handlers))
                if len(fired_handlers) == 0:
                    self.logger.warning(
                        "id '{0}' hasn't fire any stream handler".format(
                            message.invocation_id))
                for handler in fired_handlers:
                    handler.next_callback(message.item)

            if message.type == MessageType.stream_invocation:
                pass

            if message.type == MessageType.cancel_invocation:
                fired_handlers = list(
                    filter(
                        lambda h: h.invocation_id == message.invocation_id,
                        self.stream_handlers))
                if len(fired_handlers) == 0:
                    self.logger.warning(
                        "id '{0}' hasn't fire any stream handler".format(
                            message.invocation_id))

                for handler in fired_handlers:
                    handler.error_callback(message)

                # unregister handler
                self.stream_handlers = list(
                    filter(
                        lambda h: h.invocation_id != message.invocation_id,
                        self.stream_handlers))

    def stream(
            self,
            event: str,
            event_params: List[Any]) -> StreamHandler:
        """Starts server streaming
            connection.stream(
            "Counter",
            [len(self.items), 500])\
            .subscribe({
                "next": self.on_next,
                "complete": self.on_complete,
                "error": self.on_error
            })
        Args:
            event (string): Method Name
            event_params (list): Method parameters

        Returns:
            [StreamHandler]: stream handler
        """
        invocation_id = str(uuid.uuid4())
        stream_obj = StreamHandler(event, invocation_id)
        self.stream_handlers.append(stream_obj)
        self.state.send(
            StreamInvocationMessage(
                invocation_id,
                event,
                event_params,
                headers=self.headers))
        return stream_obj
