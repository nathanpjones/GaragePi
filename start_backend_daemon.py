# This is intended to be run by the shell script in /etc/init.d

import grp
import daemon
import lockfile

context = daemon.DaemonContext(
    pidfile=lockfile.FileLock('/var/run/garagepi.pid'),
    )

# To make sure we have the appropriate access
garage_site_gid = grp.getgrnam('garage_site').gr_gid
context.gid = garage_site_gid

with context:
    # Explicitly open context
    context.open()

    # Import after context opened so files opened during init won't be closed out
    from backend import app
    app.main()

    # We're done after the main loop has ended
    context.close()
