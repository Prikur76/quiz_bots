import logging
import os
import random

import vk_api as vk
from dotenv import load_dotenv
from vk_api.longpoll import VkLongPoll, VkEventType
from telegram import Bot

from logshandler import TelegramLogsHandler


logger = logging.getLogger(__name__)


def get_quiz_answer(event, vk_api):
    """TODO"""
    user_id = event.user_id
    user_message = event.text
    vk_api.messages.send(
        user_id=user_id,
        message=flow_answer['answer'],
        random_id=random.randint(1, 1000000000)
    )


if __name__ == '__main__':
    load_dotenv()

    admin_chat_id = os.environ.get('SERVICE_CHAT_ID')
    admin_bot = Bot(token=os.environ.get('SERVICE_BOT_TOKEN'))
    admin_bot_handler = TelegramLogsHandler(
        admin_bot, admin_chat_id)
    admin_bot_handler.setLevel(logging.DEBUG)
    botformatter = logging.Formatter(
        fmt='{message}', style='{')
    admin_bot_handler.setFormatter(botformatter)
    logger.addHandler(admin_bot_handler)

    streamhandler = logging.StreamHandler()
    streamhandler.setLevel(logging.ERROR)
    streamformatter = logging.Formatter(
        fmt='{asctime} - {levelname} - {name} - {message}',
        style='{')
    streamhandler.setFormatter(streamformatter)
    logger.addHandler(streamhandler)
    logger.debug('VK бот запущен')

    try:
        vk_session = vk.VkApi(token=os.environ.get('VK_COMMUNITY_TOKEN'))
        vk_api = vk_session.get_api()
        longpoll = VkLongPoll(vk_session)

        for event in longpoll.listen():
            if event.type == VkEventType.MESSAGE_NEW and event.to_me:
                get_quiz_answer(event, vk_api)

    except Exception as e:
        logger.debug('Возникла ошибка в DialogFlow vk-боте')
        logger.exception(e)
