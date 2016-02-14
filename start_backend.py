# This entry point is intended to be used to start the webserver at a terminal for debugging purposes.
# The entry point for hosting on lighttpd should be the .fcgi file.

from backend import app

app.main()