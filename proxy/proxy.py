"""Provides shortcut to ssh commands by maintaining a database nicknames that
reference host-username pairs.
"""
__author__ = "Schlameel"
__copyright__ = "Copyright 2017, Schlameel"
__credits__ = ["Schlameel"]
__license__ = "GPL2"
__version__ = "0.1.0"
__maintainer__ = "Schlameel"
__email__ = "john@Schlameel.com"
__status__ = "Prototype"

import zmq
from zmq.devices import ProcessDevice, ThreadProxy
import logging
from . import app
import json
import time

SEND_TIMEOUT = 2 * 1000  # in milliseconds
RECV_TIMEOUT = 3 * 1000  # in milliseconds

class GaragePiProxy(object):
    def __init__(self, hostIn="*", hostOut="*", hostMon="*", portIn="5550", portOut="5560", portMon="5570"):
        """Initialize object values and prepare any needed objects

        Args:
            hostIn: The address or hostname to bind to use for inbound messages
            hostOut: The address or hostname to bind to for outbound messages
            hostMon: The address or hostname to bind to for monitor messages
            portIn: The port to use for inbound messages
            portOut: The port to use for outbound messages
            portMon: The port to use for monitor messages

        Returns:
            None
            example:

            {'Serak': ('Rigel VII', 'Preparer'),
             'Zim': ('Irk', 'Invader'),
             'Lrrr': ('Omicron Persei 8', 'Emperor')}

            If a key from the keys argument is missing from the dictionary,
            then that row was not found in the table.

        Raises:
            None
        """

        # Get the logger
        self.__logger = app.logger

        # Capture arguments
        self.__hostIn = hostIn
        self.__hostOut = hostOut
        self.__hostMon = hostMon
        self.__portIn = portIn
        self.__portOut = portOut
        self.__portMon = portMon

        # Setup the monitor information
        self.__context = zmq.Context()
        self.__context.setsockopt(zmq.RCVTIMEO, RECV_TIMEOUT)
        self.__poller = zmq.Poller()
        self.__socket = None    # type: zmq.sugar.Socket
        self.__connect_addr_mon = None
        self.__proxy = ThreadProxy(zmq.DEALER, zmq.ROUTER, zmq.PUB)

    def start(self):
        """Start the proxy.

        Starts the 0MQ proxy for proxying messages. The proxy runs as a daemon thread, so it will die when
        the rest of the app dies.

        Args:
            None
        Returns:
            None

        Raises:
            None
        """
        self.__logger.debug('bind_in proxy: tcp://{0}:{1}'.format(self.__hostIn, self.__portIn))
        self.__logger.debug('bind_out proxy: tcp://{0}:{1}'.format(self.__hostOut, self.__portOut))
        self.__logger.debug('bind_mon proxy: tcp://{0}:{1}'.format(self.__hostMon, self.__portMon))
        self.__proxy.bind_in('tcp://{0}:{1}'.format(self.__hostIn, self.__portIn))
        self.__proxy.bind_out('tcp://{0}:{1}'.format(self.__hostOut, self.__portOut))
        self.__proxy.bind_mon('tcp://{0}:{1}'.format(self.__hostMon, self.__portMon))
        self.__proxy.setsockopt_out(zmq.IDENTITY, b'PROXY')
        self.__proxy.daemon = True
        self.__proxy.start()

    def __create_socket(self):
        if self.__socket is not None:
            self.close()

        self.__logger.debug("Connecting monitor socket to: {0}".format(self.__connect_addr_mon))
        self.__socket = self.__context.socket(zmq.DEALER)
        self.__socket.connect(self.__connect_addr_mon)
        self.__poller.register(self.__socket, zmq.POLLIN)

    def __log_msg(self):
        events = dict(self.__poller.poll(SEND_TIMEOUT))
        if events.get(self.__socket) == zmq.POLLIN:
            try:
                # Receive response and make sure the return is converted to string if necessary
                raw_msg = self.__socket.recv_multipart()[0]
                message = bytes.decode(raw_msg) if type(raw_msg) is bytes else raw_msg
                self.__logger.info("Received message: [{0}]".format(message))
                return True
            except zmq.error.Again:
                # If the receive timed out then return None
                self.__logger.warning("Receive operation timed out!")
                self.__create_socket()
                return False
        else:
            self.__logger.warning("Nothing to read")
            self.__create_socket()
            return False

    def close(self):
        self.__logger.debug("Closing out existing socket")
        self.__socket.setsockopt(zmq.LINGER, 0)
        self.__socket.close()
        self.__poller.unregister(self.__socket)
        self.__socket = None

    def monitor(self, host="localhost", port="5570"):
        if not self.__connect_addr_mon:
            self.__connect_addr_mon = "tcp://{0}:{1}".format(host, port)

        if not self.__socket:
            self.__create_socket()

        return self.__log_msg()

    def start_monitor(self, host="localhost", port="5570"):
        context = zmq.Context()
        socket = context.socket(zmq.SUB)
        socket.setsockopt(zmq.RCVTIMEO, 2000)
        socket.connect('tcp://{0}:{1}'.format(host, port))

        NON_READ_THREASHOLD = 10
        nonReadCount = 0
        self.__monitoring = True
        while self.__monitoring:
            try:
                message = socket.recv()
                self.__logger.info("Received message: [{0}]".format(message))
                nonReadCount = 0
            except zmq.error.Again:
                nonReadCount += 1
                if nonReadCount % NON_READ_THREASHOLD == 0:
                    self.__logger.warning("Monitor - no read {0} seconds".format(nonReadCount))
                time.sleep(1000)

        self.__logger.info('Monitor shut down')

    def stop_monitor(self):
        self.__logger.info('Monitor shutting down...')
        self.__monitoring = False
