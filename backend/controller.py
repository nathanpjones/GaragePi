import os
import time
import schedule
import threading
from threading import Thread
import zmq
import json
from RPi import GPIO
from . import app
from common.db import GarageDb
from common.struct import Struct

OPEN = "OPEN"
CLOSED = "CLOSED"

class GaragePiController:
    def __init__(self, port="5550"):
        self.__bind_addr = "tcp://*:%s" % port
        app.logger.info("Bind address: " + self.__bind_addr)

        self.__relay_lock = threading.Lock()

        self.__db = GarageDb(app.instance_path, app.resource_path)

        # Get initial reed state and subscribe to events
        GPIO.setup(app.config['REED_PIN'], GPIO.IN)
        GPIO.add_event_detect(app.config['REED_PIN'], GPIO.BOTH, callback=self.door_opened_or_closed)
        self.__door_state = None                            # 1 for open, 0 for closed, None for uninitialized
        self.door_opened_or_closed(app.config['REED_PIN'])  # force update

        # Set up warning timer if there's a setting
        if app.config['DOOR_OPEN_WARNING_TIME']:
            app.logger.info('Starting schedule to check door at {0}...'.format(app.config['DOOR_OPEN_WARNING_TIME']))
            schedule.every().day.at(app.config['DOOR_OPEN_WARNING_TIME']).do(self.check_door_open_for_warning)
            t = Thread(target=self.run_schedule)
            t.start()
        else:
            app.logger.info('No schedule to run.')

    def start(self):
        context = zmq.Context()
        socket = context.socket(zmq.ROUTER)
        socket.bind(self.__bind_addr)
        socket.setsockopt(zmq.SNDTIMEO, 1000)

        app.logger.info("Entering listen loop... ")

        try:
            while True:
                msg = socket.recv_multipart()
                app.logger.debug("Received msg: {0}".format(msg))

                if len(msg) != 3:
                    error_msg = 'invalid message received: %s' % msg
                    app.logger.error(error_msg)
                    reply = [msg[0], error_msg]
                    socket.send_multipart(reply)
                    continue

                # Break out incoming message
                id = msg[0]
                operation = bytes.decode(msg[1]) if type(msg[1]) is bytes else msg[1]
                contents = json.loads(bytes.decode(msg[2]) if type(msg[2]) is bytes else msg[2])

                # Initialize the reply. Must always send back the id with ROUTER
                reply = [id]

                if operation == 'echo':
                    # Just echo back the original contents serialized back to a string
                    reply.append(self.__get_json_bytes(contents))
                elif operation == 'get_status':
                    # Get status and return
                    reply.append(self.get_status().to_json_bytes())
                elif operation == 'trigger_relay':
                    # Trigger relay
                    self.trigger_relay(contents['user_agent'], contents['login'])
                    reply.append(b'{}')
                else:
                    app.logger.error('unknown request')

                socket.send_multipart(reply)

        finally:
            app.logger.info('Closing down socket')
            socket.setsockopt(zmq.LINGER, 500)
            socket.close()

    def __get_json_bytes(self, contents) -> bytes:
        json_str = json.dumps(contents)
        return str.encode(json_str)

    def __add_to_history(self, event: str, description: str, user_agent='SERVER', login='SERVER'):
        self.__db.record_event(user_agent, login, event, description)

    def door_opened_or_closed(self, pin_changed: int):
        """
        Callback for monitoring the reed switch's GPIO pin.

        :param pin_changed: pin number for the pin that changed
        :return:
        """

        new_state = GPIO.input(pin_changed)
        old_state = self.__door_state
        if (new_state == old_state): return

        self.__door_state = new_state
        new_state_text = "OPEN" if new_state else "CLOSED"

        if (old_state is not None):
            self.__add_to_history('SensorTrip', 'Door state changed to {0}.'.format(new_state_text))
        else:
            self.__add_to_history('StartupSensorRead', 'Door state initialized to {0}.'.format(new_state_text))

        # Check for IFTTT events that need to be fired
        if (old_state is not None):
            if self.__door_state:
                change = 'opened'
                specific_event = app.opened_event
            else:
                change = 'closed'
                specific_event = app.closed_event

            if app.changed_event is not None: app.changed_event.trigger(change)
            if specific_event is not None: specific_event.trigger()

        app.logger.info("door {0} (pin {1} is {2})".format("OPENED" if new_state else "CLOSED", pin_changed, new_state))

    def get_status(self) -> Struct:
        """
        Gets the current system status
        :return: A Struct populated with system state info
        """
        data = Struct(is_open=self.__door_state)
        data.status_text = "OPEN" if data.is_open else "CLOSED"
        data.cpu_temp_c = self.get_cpu_temperature()
        data.cpu_temp_f = data.cpu_temp_c * 9.0 / 5.0 + 32
        data.gpu_temp_c = self.get_gpu_temperature()
        data.gpu_temp_f = data.gpu_temp_c * 9.0 / 5.0 + 32
        return data

    def get_cpu_temperature(self) -> float:
        res = os.popen('cat /sys/class/thermal/thermal_zone0/temp').readline()
        app.logger.debug('Checked CPU temp and got: %r' % res)
        return float(res) / 1000.0

    def get_gpu_temperature(self) -> float:
        res = os.popen('vcgencmd measure_temp').readline()
        app.logger.debug('Checked GPU temp and got: %r' % res)
        return float(res.replace("temp=","").replace("'C\n",""))

    def trigger_relay(self, user_agent: str, login: str):
        """ Triggers the relay for a short period. """
        app.logger.debug('Triggering relay for {0} ({1})'.format(login, user_agent))
        self.__db.record_event(user_agent if user_agent else 'UNKNOWN',
                               login if login else 'UNKNOWN',
                               'SwitchActivated',
                               'Door switch activated when in {0} state.'.format(self.get_status().status_text))

        with self.__relay_lock:
            # Relay triggers on low so just setting as output will trigger
            # and closing will switch back.
            GPIO.setup(app.config['RELAY_PIN'], GPIO.OUT)
            time.sleep(0.5)
            GPIO.setup(app.config['RELAY_PIN'], GPIO.IN)

    def check_door_open_for_warning(self):
        if self.__door_state and app.warning_event is not None:
            app.warning_event.trigger('open')

    def run_schedule(self):
        while 1:
            schedule.run_pending()
            time.sleep(1)
