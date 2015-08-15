#!venv/bin/python

from flup.server.fcgi import WSGIServer
from garage import app

if __name__ == '__main__':
    app.logger.info('Starting WSGIServer...')
    WSGIServer(app).run()
