# This entry point is intended to be used to start the webserver at a terminal for debugging purposes.
# The entry point for hosting on lighttpd should be the .fcgi file.

from webserver.garage import app

# Run
if __name__ == '__main__':
    app.logger.info('Starting local server...')
    app.run(host = "0.0.0.0", port = 80, debug=True, use_reloader=False)
#regarding reloader: http://stackoverflow.com/questions/25504149/why-does-running-the-flask-dev-server-run-itself-twice
