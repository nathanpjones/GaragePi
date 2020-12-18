import apprise
import logging

class TelegramNotification:
    telegram_key = ''
    telegram_chat_id = ''

    def __init__(self,telegram_key: str, telegram_chat_id: str, event_name: str, logger: logging.Logger):
        """
        :param telegram_key: The telegram bot key
        :param telegram_chat_id: The telegram chat ID to send the message to
        :param event_name: The name of the event to trigger
        :param logger: Logger for logging purposes
        """
        if logger is None:
            raise Exception("Logger is missing!")
        if not telegram_key:
            logger.debug('IFTT: NO Telegram bot key provided')
            raise Exception("NO Telegram bot key provided!")
        if not telegram_chat_id:
            logger.debug('IFTT: NO Telegram_chat_id provided')
            raise Exception("NO Telegram chat id provided!")
        if not event_name:
            logger.debug('IFTT: NO event name provided')
            raise Exception("NO event name provided!")
        logger.info('Created TelegramNotification object %s' %(event_name))
        self.telegram_key = telegram_key
        self.telegram_chat_id = telegram_chat_id
        self.event_name = event_name
        self.logger = logger
    
    def trigger(self):
        self.logger.info('Triggering Telegram notification')
        apobj = apprise.Apprise()
        apobj.add("tgram://%s/%s" % (self.telegram_key,self.telegram_chat_id))
        apobj.notify(body=self.event_name)
