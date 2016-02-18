import logging
from logging.handlers import RotatingFileHandler

import os
import sys
from flask import Flask, request, session, g, redirect, url_for, abort, \
     render_template, flash, jsonify, has_request_context

from common import constants
from common.db import GarageDb
from common.iftt import IftttEvent
from webserver.client_api import GaragePiClient

# ------------- Setup ------------

# Create our application
app = Flask(__name__, instance_relative_config=True)

# Set up logging
app.logger_name = "WEBSRVR"
file_handler = RotatingFileHandler(os.path.join(app.instance_path, 'garage_webserver.log'),
                                   constants.LOGFILE_MODE, constants.LOGFILE_MAXSIZE,
                                   constants.LOGFILE_BACKUP_COUNT)
file_handler.setLevel(logging.DEBUG)
file_handler.setFormatter(logging.Formatter(constants.LOGFILE_FORMAT))
app.logger.addHandler(file_handler)
app.debug_log_format = '%(relativeCreated)-6d [%(process)-5d:%(thread)#x] %(levelname)-5s %(message)s [in %(module)s @ %(pathname)s:%(lineno)d]'
app.logger.setLevel(logging.DEBUG)

# Log startup
app.logger.info('---------- Starting up!')
app.logger.info('__name__ is \'%s\'' % __name__)

# Load default config and override config from an environment variable
app.config.update(dict(
    RELAY_PIN=7,
    REED_PIN=18,
    DOOR_OPENED=None,  # 1 for open, 0 for closed
    NEED_CLEANUP=False,
    SECRET_KEY='',  # should be overwritten by your app config!
))

# Load configuration
resource_path = os.path.dirname(os.path.realpath(os.path.abspath(sys.argv[0]))) + os.sep + 'resource'
default_cfg_file = os.path.join(resource_path, 'default_app.cfg')
app.logger.debug('Loading default config file from \'%s\'' % default_cfg_file)
app.config.from_pyfile(default_cfg_file)
app.logger.debug('Looking for custom app config in \'%s\'' % os.path.join(app.instance_path, 'app.cfg'))
app.config.from_pyfile('app.cfg')


# -------------- App Context Resources ----------------
def get_api_client() -> GaragePiClient:
    """
    Creates a new client api connector if there isn't one created
    yet for the current application context.
    """
    if not hasattr(g, 'api_client'):
        g.api_client = GaragePiClient(app.logger, app.config['IPC_PORT'])
    return g.api_client

def get_db() -> GarageDb:
    """
    Creates a new database connection if there is none yet for the
    current application context.
    """
    if not hasattr(g, 'sqlite_db'):
        g.sqlite_db = GarageDb(app.instance_path, resource_path)
    return g.sqlite_db


@app.teardown_appcontext
def close_db(error):
    """Closes the database again at the end of the request."""
    app.logger.debug("Tearing down app context")
    if hasattr(g, 'api_client'):
        app.logger.debug("Tearing down app context: closing api client")
        g.api_client.close()

# -------------- Routes ----------------
@app.route('/')
def show_control():
    app.logger.debug('Received request for /')
    return render_template('garage_control.html')

@app.route('/trigger', methods=['POST'])
def trigger_openclose():
    app.logger.debug('Received POST to trigger')
    if not session.get('logged_in'):
        app.logger.warning('Refusing to trigger relay because not logged in!')
        abort(401)
    app.logger.debug('Triggering relay')
    get_api_client().trigger_relay(request.headers.get('User-Agent') if has_request_context() else 'SERVER',
                                   app.config['USERNAME']);
    app.logger.debug('Relay triggered')
    flash('Relay successfully triggered')
    return redirect(url_for('show_control'))


@app.route('/query_status')
def query_status() -> str:
    status = get_api_client().get_status()
    if status is None: return "{}"
    return jsonify(status)


def get_status():
    return get_api_client().get_status()


@app.route('/history')
def show_history():
    db = get_db()
    entries = db.read_history()
    return render_template('history.html', entries=entries)


@app.route('/login', methods=['GET', 'POST'])
def login():
    error = None
    if request.method == 'POST':
        if request.form['username'] != app.config['USERNAME']:
            error = 'Invalid username'
        elif request.form['password'] != app.config['PASSWORD']:
            error = 'Invalid password'
        else:
            session['logged_in'] = True
            session.permanent = True
            flash('You were logged in')
            return redirect(url_for('show_control'))
    return render_template('login.html', error=error)


@app.route('/logout')
def logout():
    session.pop('logged_in', None)
    flash('You were logged out')
    return redirect(url_for('show_control'))


# ----- Tests --------

@app.route('/test_zmq')
def test_zmq():
    if not app.debug: return 'Only available when debug is set to True in application config.'

    msg = request.args.get('msg')

    app.logger.debug("Calling echo with message: {0}".format(msg))
    message = get_api_client().echo(msg)
    app.logger.debug("Returned from echo: {0}".format(message))

    if message is None: return "Received no reply!"
    return "Received reply [{0}]".format(message)

@app.route('/test_ifttt')
def test_ifttt():
    if not app.debug: return 'Only available when debug is set to True in application config.'

    maker_key = app.config['IFTTT_MAKER_KEY']
    if not maker_key: return 'No maker key provided!'

    event_name = request.args.get('event_name')
    # if not event_name: return redirect(url_for('show_control'), code=302)
    value1 = request.args.get('value1')
    value2 = request.args.get('value2')
    value3 = request.args.get('value3')
    app.logger.debug("Testing IFTTT with: %r %r %r %r" % (event_name, value1, value2, value3))

    event = IftttEvent(maker_key, request.args.get('event_name'), app.logger)
    result = event.trigger(value1, value2, value3)

    return 'Result: %r' % (result,)
