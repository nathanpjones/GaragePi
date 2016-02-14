import configparser
import itertools
import os
import imp

class SimpleConfigParser(dict):
    """
    Provides a class to load a sectionless configuration

    This also provides a mechanism to load from a default config first
    and to simply get a particular value.
    """

    def __init__(self, cfgFile, defaultCfgFile=None):

        # Load default config file if it's given. Allow for exception if doesn't exist.
        if defaultCfgFile:
            self.__read_file(defaultCfgFile)

        # Load specific config but only if it exists.
        if os.path.isfile(cfgFile):
            self.__read_file(cfgFile)

    def __read_file(self, file_name):
        d = imp.new_module('config')
        d.__file__ = file_name
        with open(file_name) as config_file:
            exec(compile(config_file.read(), file_name, 'exec'), d.__dict__)

        for key in dir(d):
            if key.isupper():
                self[key] = getattr(d, key)
