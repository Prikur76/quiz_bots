import json
import logging
import os
import random
from textwrap import dedent

import redis
import vk_api as vk
from dotenv import load_dotenv
from telegram import Bot
from vk_api.keyboard import VkKeyboard, VkKeyboardColor
from vk_api.longpoll import VkLongPoll, VkEventType
from vk_api.utils import get_random_id

from logshandler import TelegramLogsHandler
from tools import fetch_answer_from_db

logger = logging.getLogger(__name__)


def get_vk_keyboard():
    """Возвращает клавиатуру """
    keyboard = VkKeyboard(one_time=True)
    keyboard.add_button('Новый вопрос',
                        color=VkKeyboardColor.POSITIVE)
    keyboard.add_button('Сдаться',
                        color=VkKeyboardColor.NEGATIVE)
    return keyboard.get_keyboard()


def start(event, vk_api):
    """Отправляет привественное сообщение при команде Начать"""
    user_id = event.user_id
    start_message = """\
    Привет!
    Я бот для викторин.
    Нажмите 'Новый вопрос' для начала викторины.       
    """
    vk_api.messages.send(peer_id=user_id,
                         random_id=get_random_id(),
                         keyboard=get_vk_keyboard(),
                         message=dedent(start_message))


def handle_new_question_request(event, vk_api, db_connection):
    """Обработка нового вопроса"""
    user_id = event.user_id
    quiz_keys = db_connection.hkeys('quiz')
    question_number = random.choice(quiz_keys)
    question = json.loads(db_connection.hget('quiz', question_number))
    db_connection.hset('users', f'vk_user_{user_id}',
                       json.dumps({'last_question': question_number}))
    vk_api.messages.send(peer_id=user_id,
                         random_id=get_random_id(),
                         keyboard=get_vk_keyboard(),
                         message=question['question'])


def handle_solution_attempt(event, vk_api, db_connection):
    """Проверяет правильность ответа"""
    user_id = event.user_id
    quiz_answer = fetch_answer_from_db(f'vk_user_{user_id}', db_connection)
    user_message = event.text.strip().lower()

    if user_message == quiz_answer.lower():
        message_text = """\
        Правильный ответ!
        Для продолжения нажмите 'Новый вопрос'
        """
    else:
        message_text = """\
        Неверный ответ!
        Попробуешь ещё раз?
        """

    vk_api.messages.send(peer_id=user_id,
                         random_id=get_random_id(),
                         keyboard=get_vk_keyboard(),
                         message=dedent(message_text))


def handle_refuse_decision(event, vk_api, db_connection):
    """Отменяет вопрос"""
    user_id = event.user_id
    quiz_answer = fetch_answer_from_db(f'vk_user_{user_id}',
                                       db_connection)
    message_text = """\
    Правильный ответ:
    %s.
    'Новый вопрос' - продолжить викторину,
    'Выйти'  - отменить викторину
    """ % quiz_answer
    keyboard = VkKeyboard(one_time=True)
    keyboard.add_button('Новый вопрос',
                        color=VkKeyboardColor.POSITIVE)
    keyboard.add_button('Выйти',
                        color=VkKeyboardColor.NEGATIVE)
    vk_api.messages.send(peer_id=user_id,
                         random_id=get_random_id(),
                         keyboard=keyboard.get_keyboard(),
                         message=dedent(message_text))

def handle_cancel_decision(event, vk_api):
    """Заканчивает диалог"""
    user_id = event.user_id
    message_text = "До свидания!"
    keyboard = VkKeyboard(one_time=True)
    keyboard.add_button('Начать',
                        color=VkKeyboardColor.PRIMARY)
    keyboard.get_keyboard()
    vk_api.messages.send(peer_id=user_id,
                         random_id=get_random_id(),
                         message=message_text,
                         keyboard=keyboard.get_keyboard())


def main():
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



    while True:
        try:
            pool = redis.ConnectionPool(
                host=os.environ.get('REDIS_HOST'),
                port=os.environ.get('REDIS_PORT'),
                password=os.environ.get('REDIS_PASSWORD'),
                decode_responses=True)
            db_connection = redis.Redis(connection_pool=pool)
            vk_session = vk.VkApi(token=os.environ.get('VK_COMMUNITY_TOKEN'))
            vk_api = vk_session.get_api()
            longpoll = VkLongPoll(vk_session)

            for event in longpoll.listen():
                if not (event.type == VkEventType.MESSAGE_NEW and event.to_me):
                    continue

                if event.text.strip().lower() == 'начать':
                    start(event, vk_api)
                    continue

                if event.text.strip().lower() == 'новый вопрос':
                    handle_new_question_request(event, vk_api, db_connection)
                    continue

                if event.text.strip().lower() == 'сдаться':
                    handle_refuse_decision(event, vk_api, db_connection)
                    continue

                if event.text.strip().lower() == 'выйти':
                    handle_cancel_decision(event, vk_api)
                    continue

                handle_solution_attempt(event, vk_api, db_connection)
        except redis.exceptions.ConnectionError as conn_err:
            logger.debug('Ошибка подключения к БД')
            logger.exception(conn_err)
        except Exception as e:
            logger.debug('Возникла ошибка в vk-боте')
            logger.exception(e)


if __name__ == '__main__':
    main()
