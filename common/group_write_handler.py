import os, grp, stat
from logging.handlers import RotatingFileHandler

# http://stackoverflow.com/questions/1407474
class GroupWriteRotatingFileHandler(RotatingFileHandler):
    def __init__(self, filename, mode='a', maxBytes=0, backupCount=0, encoding=None):
        super(GroupWriteRotatingFileHandler, self).__init__(filename, mode, maxBytes, backupCount, encoding)
        print('calling ensure permissions')
        self.ensurePermissions()

    def doRollover(self):
        """
        Override base class method to make the new log file group writable.
        """
        print('executing base rollover')
        # Rotate the file first.
        RotatingFileHandler.doRollover(self)

        print('calling ensure permissions')
        self.ensurePermissions()

    def ensurePermissions(self):
        print('ensuring permissions')
        # Make sure the group is garage_site
        uid = os.stat(self.baseFilename).st_uid
        gid = grp.getgrnam("garage_site").gr_gid
        os.chown(self.baseFilename, uid, gid)

        # Add group write to the current permissions.
        currMode = os.stat(self.baseFilename).st_mode
        os.chmod(self.baseFilename, currMode | stat.S_IWGRP)
