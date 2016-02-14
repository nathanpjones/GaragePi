import requests
import logging

class IftttEvent:

    maker_key = ''
    event_name = ''
    logger = None

    def __init__(self, maker_key: str, event_name: str, logger: logging.Logger):
        """
        :param maker_key: The authenticating maker key
        :param event_name: The name of the event to trigger
        :param logger: Logger for logging purposes
        """
        if logger is None:
            raise Exception("Logger is missing!")
        if not maker_key:
            logger.debug('IFTT: NO maker key provided')
            raise Exception("NO maker key provided!")
        if not event_name:
            logger.debug('IFTT: NO event name provided')
            raise Exception("NO event name provided!")

        self.maker_key = maker_key
        self.event_name = event_name
        self.logger = logger

    def trigger(self, value1: str=None, value2: str=None, value3: str=None):
        url = 'https://maker.ifttt.com/trigger/{0}/with/key/{1}'.format(self.event_name, self.maker_key)

        self.logger.info("Sending IFTTT trigger for %s with values %r %r %r" % (self.event_name, value1, value2, value3))

        if value1 or value2 or value3:
            data = {}
            if value1: data['value1'] = value1
            if value2: data['value2'] = value2
            if value3: data['value3'] = value3

            r = requests.post(url, json=data)
        else:
            r = requests.post(url)

        self.logger.info("IFTTT response for {0}: {1}".format(self.event_name, r.text))

        return r.text
