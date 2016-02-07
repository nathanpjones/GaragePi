import os, grp, stat
import time
import schedule
import threading
from threading import Thread
from sqlite3 import dbapi2 as sqlite3
import RPi.GPIO as GPIO
from flask import Flask, request, session, g, redirect, url_for, abort, \
     render_template, flash, jsonify, current_app, has_request_context
import requests
import json
from werkzeug.local import LocalProxy
import atexit
import logging
import collections
from common.group_write_handler import GroupWriteRotatingFileHandler
from common.iftt import IftttEvent


class Struct:
    def __init__(self, **entries): self.__dict__.update(entries)

#------------- Setup ------------

# create our little application :)
app = Flask(__name__, instance_relative_config=True)

file_handler = GroupWriteRotatingFileHandler(os.path.join(app.instance_path,'garage.log'), 'a', 1 * 1024 * 1024, 10)
file_handler.setLevel(logging.DEBUG)
file_handler.setFormatter(logging.Formatter('%(asctime)s [%(process)-5d:%(thread)d] %(levelname)-5s %(message)s [in %(module)s @ %(pathname)s:%(lineno)d]'))
app.logger.addHandler(file_handler)
app.debug_log_format = '%(relativeCreated)-6d [%(process)-5d:%(thread)#x] %(levelname)-5s %(message)s [in %(module)s @ %(pathname)s:%(lineno)d]'
app.logger.setLevel(logging.DEBUG)

app.logger.info('---------- Starting up!')
app.logger.info('__name__ is \'%s\'' % __name__)

# Load default config and override config from an environment variable
app.config.update(dict(
    DATABASE=os.path.join(app.instance_path, 'history.db'),
    RELAY_PIN=7,
    REED_PIN=18,
    DOOR_OPENED=None, # 1 for open, 0 for closed
    NEED_CLEANUP=False,
    SECRET_KEY='', # should be overwritten by your app config!
))
default_cfg_file = os.path.join(app.root_path, 'default_app.cfg')
app.logger.debug('Loading default config file from \'%s\'' % default_cfg_file)
app.config.from_pyfile(default_cfg_file)
app.logger.debug('Looking for custom app config in \'%s\'' % os.path.join(app.instance_path, 'app.cfg'))
app.config.from_pyfile('app.cfg')

relayLock = threading.Lock()

# Set up iftt events if a maker key is present
if app.config['IFTTT_MAKER_KEY'] is not None:
    changed_event = IftttEvent(app.config['IFTTT_MAKER_KEY'], 'garage_door_changed', app.logger)
    opened_event = IftttEvent(app.config['IFTTT_MAKER_KEY'], 'garage_door_opened', app.logger)
    closed_event = IftttEvent(app.config['IFTTT_MAKER_KEY'], 'garage_door_closed', app.logger)
else:
    changed_event = None
    opened_event = None
    closed_event = None

# Set up GPIO using BCM numbering
GPIO.setmode(GPIO.BCM)

def finalize():
    msg ='Calling cleanup on GPIO'
    app.logger.info(msg)
    GPIO.cleanup()
    return

# Register application finalizer
atexit.register(finalize)

#-------------- DB     ----------------
def connect_db():
    """Connects to the specific database."""
    rv = sqlite3.connect(app.config['DATABASE'])
    rv.row_factory = sqlite3.Row
    return rv


def init_db():
    """Initializes the database."""
    db = get_db()
    with app.open_resource('schema.sql', mode='r') as f:
        db.cursor().executescript(f.read())
    db.commit()


#@app.cli.command('initdb')
def initdb_command():
    """Creates the database tables."""
    with app.app_context():
        init_db()
    app.logger.info('Initialized the database.')


def get_db():
    """Opens a new database connection if there is none yet for the
    current application context.
    """
    if not hasattr(g, 'sqlite_db'):
        g.sqlite_db = connect_db()
    return g.sqlite_db


@app.teardown_appcontext
def close_db(error):
    """Closes the database again at the end of the request."""
    if hasattr(g, 'sqlite_db'):
        g.sqlite_db.close()

#-------------- Routes ----------------
@app.route('/')
def show_control():
    app.logger.debug('Received request for /')
    return render_template('garage_control.html')

def add_to_history(event, description):
    """Adds an entry to the history database"""
    db = get_db()
    db.execute('insert into entries (UserAgent, Login, Event, Description) values (?, ?, ?, ?)',
               [request.headers.get('User-Agent') if has_request_context() else 'SERVER', app.config['USERNAME'], event, description])
    db.commit()

@app.route('/trigger', methods=['POST'])
def trigger_openclose():
    if not session.get('logged_in'):
        abort(401)
    add_to_history('SwitchActivated', 'Door switch activated when in %s state.' % (get_status().status_text))
    trigger_relay();
    flash('Relay successfully triggered')
    return redirect(url_for('show_control'))

@app.route('/query_status')
def query_status():
    data = get_status()
    cpu_temp_f = data.cpu_temp * 9.0 / 5.0 + 32
    gpu_temp_f = data.gpu_temp * 9.0 / 5.0 + 32
    return jsonify(is_open=data.is_open,
                   status_text=data.status_text,
                   cpu_temp_c=data.cpu_temp,
                   cpu_temp_f=cpu_temp_f,
                   gpu_temp_c=data.gpu_temp,
                   gpu_temp_f=gpu_temp_f)

def get_status():
    """Gets the current system status"""
    data = Struct(is_open = app.config['DOOR_OPENED'])
    data.status_text = "OPEN" if data.is_open else "CLOSED"
    data.cpu_temp = get_cpu_temperature()
    data.gpu_temp = get_gpu_temperature()
    return data

def get_cpu_temperature():
    res = os.popen('cat /sys/class/thermal/thermal_zone0/temp').readline()
    app.logger.debug('Checked CPU temp and got: %r' % res)
    return float(res) / 1000.0

def get_gpu_temperature():
    res = os.popen('vcgencmd measure_temp').readline()
    app.logger.debug('Checked GPU temp and got: %r' % res)
    return float(res.replace("temp=","").replace("'C\n",""))

@app.route('/history')
def show_history():
    db = get_db()
    cur = db.execute('select datetime(timestamp, \'localtime\') as timestamp, event, description from entries order by timestamp desc')
    entries = cur.fetchall()
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

# ------- Functionality ----------

def trigger_relay():
    """Triggers the relay for a short period."""
    with relayLock:
        # Relay triggers on low so just setting as output will trigger
        # and closing will switch back.
        GPIO.setup(app.config['RELAY_PIN'], GPIO.OUT)
        time.sleep(0.5)
        GPIO.setup(app.config['RELAY_PIN'], GPIO.IN)

def door_opened_or_closed(pin_changed):
    new_state = GPIO.input(pin_changed)
    old_state = app.config['DOOR_OPENED']
    if (new_state == old_state): return
    app.config['DOOR_OPENED'] = new_state
    with app.app_context():
        if (old_state is not None):
            add_to_history('SensorTrip', 'Door state changed to %s.' % (get_status().status_text))
        else:
            add_to_history('StartupSensorRead', 'Door state initialized to %s.' % (get_status().status_text))

    if (old_state is not None):
        if get_status().is_open:
            change = 'opened'
            specific_event = opened_event
        else:
            change = 'closed'
            specific_event = closed_event

        if changed_event is not None: changed_event.trigger(change)
        if specific_event is not None: specific_event.trigger()

    app.logger.info("door %s (pin %d is %d)" % ("OPENED" if new_state == GPIO.HIGH else "CLOSED", pin_changed, new_state))

# ----- IFTTT --------

@app.route('/test_ifttt')
def test_ifttt():
    if not app.debug: return 'Only available when debug is set to True in application config.'

    maker_key = app.config['IFTTT_MAKER_KEY']
    if not maker_key: return 'No maker key provided!'

    event_name = request.args.get('event_name')
    #if not event_name: return redirect(url_for('show_control'), code=302)
    value1 = request.args.get('value1')
    value2 = request.args.get('value2')
    value3 = request.args.get('value3')
    app.logger.info("Testing IFTTT with: %r %r %r %r" % (event_name, value1, value2, value3))

    event = IftttEvent(maker_key, request.args.get('event_name'), app.logger)
    result = event.trigger(value1, value2, value3)

    return 'Result: %r' % (result,)

def check_door_open_for_warning():
    pass
    maker_key = app.config['IFTTT_MAKER_KEY']
    if get_status().is_open and maker_key:
        event = IftttEvent(maker_key, 'garage_door_warning', app.logger)
        event.trigger('open')

def run_schedule():
    while 1:
        schedule.run_pending()
        time.sleep(1)

# ----- Run -------

# Make sure database is created before anything else
initdb_command()

# Note that we need cleanup
app.config['NEED_CLEANUP'] = True

# Get initial reed state
GPIO.setup(app.config['REED_PIN'], GPIO.IN)
GPIO.add_event_detect(app.config['REED_PIN'], GPIO.BOTH, callback=door_opened_or_closed)
door_opened_or_closed(app.config['REED_PIN'])

# Set up warning timer if there's a setting
if app.config['DOOR_OPEN_WARNING_TIME']:
    app.logger.info('Starting schedule to check door at {0}...'.format(app.config['DOOR_OPEN_WARNING_TIME']))
    schedule.every().day.at(app.config['DOOR_OPEN_WARNING_TIME']).do(check_door_open_for_warning)
    t = Thread(target=run_schedule)
    t.start()
else:
    app.logger.info('No schedule to run.')
