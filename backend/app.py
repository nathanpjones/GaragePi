import sys
import os
import logging
from logging.handlers import RotatingFileHandler
from common import constants
from common.iftt import IftttEvent
import RPi.GPIO as GPIO
import atexit
import signal
from flask import Config

# Find paths
instance_path = os.path.dirname(os.path.realpath(os.path.abspath(sys.argv[0]))) + os.sep + 'instance'
resource_path = os.path.dirname(os.path.realpath(os.path.abspath(sys.argv[0]))) + os.sep + 'resource'

# Create logger
file_handler = RotatingFileHandler(os.path.join(instance_path, 'garage_backend.log'),
                                   constants.LOGFILE_MODE, constants.LOGFILE_MAXSIZE,
                                   constants.LOGFILE_BACKUP_COUNT)
file_handler.setLevel(logging.DEBUG)
file_handler.setFormatter(logging.Formatter(constants.LOGFILE_FORMAT))
console_handler = logging.StreamHandler()
console_handler.setLevel(logging.DEBUG)
console_handler.setFormatter(logging.Formatter("%(asctime)s - %(levelname)s - %(message)s [in %(module)s @ %(pathname)s:%(lineno)d]"))
logger = logging.Logger("CONTROL", level=logging.DEBUG)
logger.addHandler(file_handler)
logger.addHandler(console_handler)


# Log startup
logger.info('---------- Backend starting up!')

try:
    # Load configuration
    logger.info('Loading configuration')
    config_file = os.path.join(instance_path, 'app.cfg')
    default_config_file = os.path.join(resource_path, 'default_app.cfg')
    config = Config(instance_path)
    config.from_pyfile(default_config_file)
    config.from_pyfile(config_file)
    #config = SimpleConfigParser(config_file, default_config_file)

    # Set up iftt events if a maker key is present
    if config['IFTTT_MAKER_KEY']:
        logger.info('Creating IFTTT events')
        changed_event = IftttEvent(config['IFTTT_MAKER_KEY'], 'garage_door_changed', logger)
        opened_event = IftttEvent(config['IFTTT_MAKER_KEY'], 'garage_door_opened', logger)
        closed_event = IftttEvent(config['IFTTT_MAKER_KEY'], 'garage_door_closed', logger)
        warning_event = IftttEvent(config['IFTTT_MAKER_KEY'], 'garage_door_warning', logger)
    else:
        logger.info('No IFTTT maker key provided. No events will be raised.')
        changed_event = None    # type: IftttEvent
        opened_event = None     # type: IftttEvent
        closed_event = None     # type: IftttEvent
        warning_event = None    # type: IftttEvent

    # Set up GPIO using BCM numbering
    logger.info('Setting GPIO numbering')
    GPIO.setmode(GPIO.BCM)
except:
    logger.exception('Exception during startup actions')
    raise

finalized = False

# Set up application finalizer
def finalize():
    global finalized
    logger.info('Entering finalizer.')
    if finalized:
        logger.info('Finalizer already called. Skipping...')
        return
    logger.info('Calling cleanup on GPIO')
    GPIO.cleanup()
    finalized = True
    return

logger.info('Registering finalizer')
atexit.register(finalize)

# Set up so SIGTERM will cause graceful shutdown
def sigterm_handler(_signo, _stack_frame):
    # Raises SystemExit(0):
    logger.info('SIGTERM received!')
    finalize()
    sys.exit(0)

logger.info('Registering SIGTERM handler')
signal.signal(signal.SIGTERM, sigterm_handler)

logger.info('Finished with startup actions')

# Provide startup routine
def main():
    logger.info('Starting controller')
    try:
        from backend.controller import GaragePiController
        GaragePiController(config['IPC_PORT']).start()
    except:
        logger.exception('Exception while running controller')
    finally:
        logger.debug('Entered finally')
        finalize()
        logger.info('Exiting')
