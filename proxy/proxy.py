"""Proxy to facilitate messaging when running on different machines.

When the Raspberry Pi is behind a firewall, the frontend and this proxy, can run
on a publicly visible server.  This proxy facilitates the messaging between the
webserver frontend and the backend controller.
"""
__author__ = "Schlameel"
__copyright__ = "Copyright 2017, Schlameel"
__credits__ = ["Schlameel"]
__license__ = "GPL2"
__version__ = "0.1.0"
__maintainer__ = "Schlameel"
__email__ = "Schlameel@Schlameel"
__status__ = "Development"

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

    def start_monitor(self, host="localhost", port="5570"):
        """Monitor and log messages passed through the proxy

        Begin the process of monitoring messages passed through the proxy.
        Messages are logged to the proxy log.  This method runs until
        stop_monitor is called.

        Args:
            host: A hostname or IP address of the proxy.  While possible to run
                only the monitor on a seperate machine, it is likely to be
                "localhost" or "127.0.0.1".
            port: The port on which to monitor the proxy.  This should be the
                same as was supplied to the proxy.

        Returns:
            None

        Raises:
            None
        """
        context = zmq.Context()
        socket = context.socket(zmq.SUB)
        socket.setsockopt(zmq.RCVTIMEO, 2000)
        socket.setsockopt(zmq.SUBSCRIBE, b"")
        socket.connect('tcp://{0}:{1}'.format(host, port))

        NON_READ_THREASHOLD = 10
        nonReadCount = 0
        self.__monitoring = True
        while self.__monitoring:
            try:
                message = socket.recv_multipart()
                self.__logger.debug("Received message: [{0}]".format(message))
                nonReadCount = 0
            except zmq.error.Again:
                nonReadCount += 1
                if nonReadCount % NON_READ_THREASHOLD == 0:
                    self.__logger.warning("Monitor - no messages for {0} seconds".format(nonReadCount))
                time.sleep(1000)

        socket.close()
        self.__logger.info('Monitor shut down')

    def stop_monitor(self):
        """Stop the monitor

        This method tells the monitor to quit, but it may take the monitor a
        couple of seconds to finish.
        """
        self.__logger.info('Monitor shutting down...')
        self.__monitoring = False
