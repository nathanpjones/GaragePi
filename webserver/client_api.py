import zmq
import json
import logging
from common.struct import Struct

SEND_TIMEOUT = 2 * 1000  # in milliseconds
RECV_TIMEOUT = 3 * 1000  # in milliseconds

class GaragePiClient(object):
    """
    Client that connects with GaragePi backend to perform tasks
    """

    def __init__(self, logger: logging.Logger, connect_port='5550'):
        assert logger is not None
        self.__logger = logger

        self.__connect_addr = "tcp://localhost:%s" % connect_port
        self.__logger.debug("Connect address: " + self.__connect_addr)

        self.__context = zmq.Context()
        self.__context.setsockopt(zmq.RCVTIMEO, RECV_TIMEOUT)
        self.__poller = zmq.Poller()
        self.__socket = None    # type: zmq.sugar.Socket
        self.__create_socket()


    def __create_socket(self):
        if self.__socket is not None:
            self.close()

        self.__logger.debug("Creating new socket")
        self.__socket = self.__context.socket(zmq.DEALER)
        self.__socket.connect(self.__connect_addr)
        self.__poller.register(self.__socket, zmq.POLLIN)

    def close(self):
        self.__logger.debug("Closing out existing socket")
        self.__socket.setsockopt(zmq.LINGER, 0)
        self.__socket.close()
        self.__poller.unregister(self.__socket)
        self.__socket = None

    def __send_recv_msg(self, msg):
        # Make sure we're sending bytes instead of strings
        msg = list(map(lambda s: str.encode(s) if type(s) is str else s, msg))
        self.__socket.send_multipart(msg)

        events = dict(self.__poller.poll(SEND_TIMEOUT))
        if events.get(self.__socket) == zmq.POLLIN:
            try:
                # Receive response and make sure the return is converted to string if necessary
                ret_msg = self.__socket.recv_multipart()[0]
                return bytes.decode(ret_msg) if type(ret_msg) is bytes else ret_msg
            except zmq.error.Again:
                # If the receive timed out then return None
                self.__logger.warning("Receive operation timed out!")
                self.__create_socket()
                return None
        else:
            self.__logger.warning("Send operation timed out!")
            self.__create_socket()
            return None


    def echo(self, message):
        self.__logger.debug("Requesting 'echo' with message: {0}".format(message))
        msg_json = json.dumps({'message': message})
        msg = ['echo', msg_json]
        reply_json = self.__send_recv_msg(msg)
        if reply_json is None: return None
        return json.loads(reply_json)['message']

    def get_status(self):
        self.__logger.debug("Requesting 'get_status'")
        msg = ['get_status', '{}']
        reply_json = self.__send_recv_msg(msg)
        if reply_json is None: return None
        return json.loads(reply_json)

    def trigger_relay(self, user_agent: str, login: str):
        self.__logger.debug("Requesting 'trigger_relay'")
        data = Struct(user_agent=user_agent, login=login)
        msg_json = data.to_json_bytes()
        msg = ['trigger_relay', msg_json]
        reply_json = self.__send_recv_msg(msg)
        if reply_json is None: return None
        return json.loads(reply_json)
