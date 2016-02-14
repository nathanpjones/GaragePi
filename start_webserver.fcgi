#!venv/bin/python

from flipflop import WSGIServer
from webserver.garage import app

if __name__ == '__main__':
    app.logger.info('Starting WSGIServer...')
    WSGIServer(app).run()
