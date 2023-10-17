import json
import logging
import os
import random
from textwrap import dedent

import redis
from dotenv import load_dotenv
from telegram import ChatAction
from telegram import ReplyKeyboardMarkup, ReplyKeyboardRemove
from telegram import Update, Bot
from telegram.ext import CallbackContext
from telegram.ext import CommandHandler
from telegram.ext import ConversationHandler
from telegram.ext import Filters
from telegram.ext import MessageHandler
from telegram.ext import Updater

from logshandler import TelegramLogsHandler
from tools import send_action, fetch_answer_from_db

logger = logging.getLogger(__name__)

CHOOSING, ATTEMPTING = range(2)


def start(update: Update, context: CallbackContext) -> None:
    """Отправляет привественное сообщение при команде /start"""
    user = update.effective_user
    keyboard = [['Новый вопрос', 'Сдаться']]
    keyboard_markup = ReplyKeyboardMarkup(keyboard,
                                          resize_keyboard=True)
    start_message = dedent(
        '''\
        Привет, %s!
        Я бот для викторин. Нажмите "Новый вопрос" для начала викторины.
        /cancel - для отмены.
        ''' % user.first_name)
    update.message.reply_text(start_message,
                              reply_markup=keyboard_markup)
    return CHOOSING


@send_action(ChatAction.TYPING)
def handle_new_question_request(update: Update, context: CallbackContext):
    """Обработка нового вопроса"""
    user_id = update.message.from_user.id
    quiz_keys = db_connection.hkeys('quiz')
    question_number = random.choice(quiz_keys)
    question = json.loads(db_connection.hget('quiz', question_number))
    db_connection.hset('users', f'tg_user_{user_id}',
                       json.dumps({'last_question': question_number}))
    keyboard = [['Новый вопрос', 'Сдаться']]
    keyboard_markup = ReplyKeyboardMarkup(keyboard,
                                          resize_keyboard=True)
    update.message.reply_text(question['question'],
                              reply_markup=keyboard_markup)
    return ATTEMPTING


@send_action(ChatAction.TYPING)
def handle_solution_attempt(update: Update, context: CallbackContext):
    """Проверяет правильность ответа"""
    user_id = update.message.from_user.id
    user_message = update.message.text.strip().lower()
    quiz_answer = fetch_answer_from_db(f'tg_user_{user_id}', db_connection)
    if user_message == quiz_answer.lower():
        message_text = '''\
        Правильный ответ!
        Для продолжения нажмите "Новый вопрос"
        '''
        update.message.reply_text(dedent(message_text))
        return CHOOSING

    message_text = '''\
    Неверный ответ!
    Попробуешь ещё раз?
    '''
    update.message.reply_text(dedent(message_text))
    return ATTEMPTING


def handle_refuse_decision(update: Update, context: CallbackContext):
    """Отменяет вопрос"""
    user_id = update.message.from_user.id
    quiz_answer = fetch_answer_from_db(f'tg_user_{user_id}', db_connection)
    message_text = """\
    Правильный ответ:
    %s.
    'Новый вопрос' - продолжить викторину,
    '/cancel' - покинуть викторину
    """ % quiz_answer
    keyboard = [['Новый вопрос']]
    keyboard_markup = ReplyKeyboardMarkup(keyboard,
                                          resize_keyboard=True)
    update.message.reply_text(dedent(message_text),
                              reply_markup=keyboard_markup)
    return CHOOSING


def handle_cancel_decision(update: Update, context: CallbackContext):
    """Заканчивает диалог"""
    user = update.effective_user
    message_text = """\
    До свидания, %s! 
    Введите /start для начала новой викторины.
    """ % user.first_name
    update.message.reply_text(dedent(message_text),
                              reply_markup=ReplyKeyboardRemove())
    return ConversationHandler.END


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
    logger.debug('TG бот запущен')

    try:
        pool = redis.ConnectionPool(
            host=os.environ.get('REDIS_HOST'),
            port=os.environ.get('REDIS_PORT'),
            password=os.environ.get('REDIS_PASSWORD'),
            decode_responses=True,
            encoding='utf-8')
        db_connection = redis.Redis(connection_pool=pool)

        updater = Updater(os.environ.get('DF_BOT_TOKEN'))
        dp = updater.dispatcher

        conversation_handler = ConversationHandler(
            entry_points=[CommandHandler('start', start)],
            states={
                CHOOSING: [
                    MessageHandler(Filters.regex('^(Новый вопрос)$'),
                                   handle_new_question_request)
                ],
                ATTEMPTING: [
                    MessageHandler(Filters.regex('^(Сдаться)$'), handle_refuse_decision),
                    MessageHandler(Filters.text, handle_solution_attempt)
                ],
            },
            fallbacks=[CommandHandler('cancel', handle_cancel_decision)]
        )
        dp.add_handler(conversation_handler)

        updater.start_polling()
        updater.idle()
    except redis.exceptions.ConnectionError as conn_err:
        logger.debug('Ошибка подключения к БД')
        logger.exception(conn_err)
    except Exception as e:
        logger.debug('Возникла ошибка в tg-боте')
        logger.exception(e)
