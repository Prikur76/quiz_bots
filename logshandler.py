import logging


class TelegramLogsHandler(logging.Handler):
    def __init__(self, tg_bot, chat_id):
        super().__init__()
        self.tg_bot = tg_bot
        self.chat_id = chat_id

    def emit(self, record):
        message = self.format(record)
        self.tg_bot.send_message(
            chat_id=self.chat_id,
            text=message)
