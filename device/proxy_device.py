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

SEND_TIMEOUT = 2 * 1000  # in milliseconds
RECV_TIMEOUT = 3 * 1000  # in milliseconds

class GaragePiDevice(object):
    def __init__(self, hostIn="*", hostOut="*", hostMon="*", portIn="5550", portOut="5560", portMon="5570", useProxy=True):
        """Initialize object values and prepare any needed objects

        Args:
            hostIn: The address or hostname to bind to use for inbound messages
            hostOut: The address or hostname to bind to for outbound messages
            hostMon: The address or hostname to bind to for monitor messages
            portIn: The port to use for inbound messages
            portOut: The port to use for outbound messages
            portMon: The port to use for monitor messages
            useProxy: A boolean that identifies if the device should use a Proxy
                or the old Device

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
        self.__useProxy = useProxy

        # Setup the monitor information
        self.__context = zmq.Context()
        self.__context.setsockopt(zmq.RCVTIMEO, RECV_TIMEOUT)
        self.__poller = zmq.Poller()
        self.__socket = None    # type: zmq.sugar.Socket
        self.__connect_addr_mon = None

        # Create the device of the appropriate type
        if self.__useProxy:
            self.__device = ThreadProxy(zmq.DEALER, zmq.ROUTER, zmq.ROUTER)
            #self.__device = ThreadProxy(zmq.ROUTER, zmq.DEALER, zmq.REP)
            self.__logger.info('Using Proxy')
        else:
            self.__device = ProcessDevice(zmq.QUEUE, zmq.ROUTER, zmq.DEALER)
            self.__logger.info('Using ProcessDevice')

    def start(self):
        """Start the device.

        Starts the 0MQ device for proxying messages. The device runs as a daemon thread, so it will die when
        the rest of the app dies.

        Args:
            big_table: An open Bigtable Table instance.
            keys: A sequence of strings representing the key of each table row
                to fetch.
            other_silly_variable: Another optional variable, that has a much
                longer name than the other args, and which does nothing.

        Returns:
            A dict mapping keys to the corresponding table row data
            fetched. Each row is represented as a tuple of strings. For
            example:

            {'Serak': ('Rigel VII', 'Preparer'),
             'Zim': ('Irk', 'Invader'),
             'Lrrr': ('Omicron Persei 8', 'Emperor')}

            If a key from the keys argument is missing from the dictionary,
            then that row was not found in the table.

        Raises:
            IOError: An error occurred accessing the bigtable.Table object.
        """
        self.__logger.info('bind_in device: tcp://{0}:{1}'.format(self.__hostIn, self.__portIn))
        self.__logger.info('bind_out device: tcp://{0}:{1}'.format(self.__hostOut, self.__portOut))
        self.__device.bind_in('tcp://{0}:{1}'.format(self.__hostIn, self.__portIn))
        self.__device.bind_out('tcp://{0}:{1}'.format(self.__hostOut, self.__portOut))

        if self.__useProxy:
            self.__device.setsockopt_mon(zmq.IDENTITY, b'monitor')
            self.__device.bind_mon('tcp://{0}:{1}'.format(self.__hostMon, self.__portMon))
        #else:
        #    self.__device.daemon = True
        self.__device.start()
        self.__running = True

    def join(self, timeout=2000):
        self.__running = False
        self.__device.join(timeout)

    def getContext(self):
        if hasattr(self.__device, '_context'):
            return self.__device._context
        else:
            return None

    def __create_socket(self):
        if self.__socket is not None:
            self.close()

        self.__logger.debug("Connecting socket to: {0}".format(self.__connect_addr_mon))
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

    def simpleMon(self, host="localhost", port="5570"):
        pass
