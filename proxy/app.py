"""Launch and run the proxy.

Provides the daemon structure to run the proxy service.
"""
__author__ = "Schlameel"
__copyright__ = "Copyright 2017, Schlameel"
__credits__ = ["Schlameel"]
__license__ = "GPL2"
__version__ = "0.1.0"
__maintainer__ = "Schlameel"
__email__ = "Schlameel@Schlameel"
__status__ = "Development"

import sys
import os
import logging
from logging.handlers import RotatingFileHandler
from common import constants
import atexit
import signal
import time
from flask import Config

# Find paths
instance_path = os.path.dirname(os.path.realpath(os.path.abspath(sys.argv[0]))) + os.sep + 'instance'
resource_path = os.path.dirname(os.path.realpath(os.path.abspath(sys.argv[0]))) + os.sep + 'resource'

# Create logger
# Set up logging
environment = app.config['ENVIRONMENT']
logLevel = None
if environment == 'DEVELOPMENT':
    logLevel = logging.DEBUG
if environment == 'PRODUCTION':
    logLevel = logging.WARNING
file_handler = RotatingFileHandler(os.path.join(instance_path, 'garage_proxy.log'),
                                   constants.LOGFILE_MODE, constants.LOGFILE_MAXSIZE,
                                   constants.LOGFILE_BACKUP_COUNT)
file_handler.setLevel(logLevel)
file_handler.setFormatter(logging.Formatter(constants.LOGFILE_FORMAT))
console_handler = logging.StreamHandler()
console_handler.setLevel(logLevel)
console_handler.setFormatter(logging.Formatter("%(asctime)s - %(levelname)s - %(message)s [in %(module)s @ %(pathname)s:%(lineno)d]"))
logger = logging.Logger("PROXY", level=logLevel)
logger.addHandler(file_handler)
logger.addHandler(console_handler)


# Log startup
logger.info('---------- Proxy starting up!')

try:
    # Load configuration
    logger.info('Loading configuration')
    config_file = os.path.join(instance_path, 'app.cfg')
    default_config_file = os.path.join(resource_path, 'default_app.cfg')
    config = Config(instance_path)
    config.from_pyfile(default_config_file)
    config.from_pyfile(config_file)

except:
    logger.exception('Exception during startup actions')
    raise

finalized = False
proxy = None

# Set up application finalizer
def finalize():
    global finalized
    global proxy
    proxy.stop_monitor()
    logger.info('Entering finalizer.')
    if finalized:
        logger.info('Finalizer already called. Skipping...')
        return
    finalized = True
    return

logger.info('Registering finalizer')
atexit.register(finalize)

# Set up so SIGTERM will cause graceful shutdown
def sigterm_handler(_signo, _stack_frame):
    # Raises SystemExit(0):
    logger.info('SIGTERM received!')
    finalize()
    logger.info('Proxy terminated correctly')
    sys.exit(0)

logger.info('Registering SIGTERM handler')
signal.signal(signal.SIGTERM, sigterm_handler)

logger.info('Finished with startup actions')

# Provide startup routine
def main():
    global proxy
    logger.info('Starting proxy')
    try:
        from proxy.proxy import GaragePiProxy
        proxy = GaragePiProxy()
        proxy.start()
        # Once the proxy is started, simply monitor and log messages.
        while True:
            proxy.start_monitor()

    except Exception as e:
        logger.exception(e)
        logger.exception('Exception while running proxy')
    finally:
        logger.debug('Entered finally')
        finalize()
        logger.info('Exiting')
