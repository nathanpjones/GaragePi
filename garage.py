import os
import time
#from threading import lock
import threading
from sqlite3 import dbapi2 as sqlite3
import RPi.GPIO as GPIO
from flask import Flask, request, session, g, redirect, url_for, abort, \
     render_template, flash, jsonify, current_app, has_request_context
from werkzeug.local import LocalProxy
import atexit
import logging
from logging.handlers import RotatingFileHandler
import collections

class Struct:
    def __init__(self, **entries): self.__dict__.update(entries)

#------------- Setup ------------

# create our little application :)
app = Flask(__name__)

file_handler = RotatingFileHandler(os.path.join(app.root_path,'data/garage.log'), 'a', 1 * 1024 * 1024, 10)
file_handler.setLevel(logging.DEBUG)
file_handler.setFormatter(logging.Formatter('%(asctime)s %(levelname)s: %(message)s [in %(pathname)s:%(lineno)d]'))
app.logger.addHandler(file_handler)
app.logger.setLevel(logging.INFO)
app.logger.info('---------- Starting up!')
app.logger.info('__name__ is \'%s\'' % __name__)

# Load default config and override config from an environment variable
app.config.update(dict(
    DATABASE=os.path.join(app.root_path, 'data/history.db'),
    RELAY_PIN=7,
    REED_PIN=18,
    DOOR_OPENED=None, # 1 for open, 0 for closed
    NEED_CLEANUP=False,
    DEBUG=True,
    SECRET_KEY='asdlkvhy37gh#&*5492',
    USERNAME='admin',
    PASSWORD='garageWonder!'
))
app.config.from_envvar('GARAGE_SETTINGS', silent=True)

relayLock = threading.Lock()

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
    app.logger.debug(res)
    return float(res) / 1000.0

def get_gpu_temperature():
    res = os.popen('vcgencmd measure_temp').readline()
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

    app.logger.info("door %s (pin %d is %d)" % ("OPENED" if new_state == GPIO.HIGH else "CLOSED", pin_changed, new_state))

# ----- Run -------

# Note that we need cleanup
app.config['NEED_CLEANUP'] = True

# Get initial reed state
GPIO.setup(app.config['REED_PIN'], GPIO.IN)
GPIO.add_event_detect(app.config['REED_PIN'], GPIO.BOTH, callback=door_opened_or_closed)
door_opened_or_closed(app.config['REED_PIN'])

# Make sure database is created
initdb_command()

# Run
if __name__ == '__main__':
    app.logger.info('Starting local server...')
    app.run(host = "0.0.0.0",port = 80,debug=True, use_reloader=False)
#regarding reloader: http://stackoverflow.com/questions/25504149/why-does-running-the-flask-dev-server-run-itself-twice
