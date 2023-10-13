import json
import logging
import os
import random
import redis
from textwrap import dedent

from dotenv import load_dotenv
from telegram import Update, Bot, ReplyKeyboardMarkup, ChatAction
from telegram.ext import Updater
from telegram.ext import CallbackContext
from telegram.ext import Filters
from telegram.ext import CommandHandler
from telegram.ext import MessageHandler

from telegram.ext import ConversationHandler


from logshandler import TelegramLogsHandler
from tools import read_quiz_questions, send_action, get_quiz_answer


logger = logging.getLogger(__name__)


def start(update: Update, context: CallbackContext) -> None:
    """Отправляет привественное сообщение при команде /start"""
    user = update.effective_user
    keyboard = [['Новый вопрос', 'Сдаться']]
    keyboard_markup = ReplyKeyboardMarkup(keyboard, resize_keyboard=True)
    start_message = dedent(
        '''\
        Привет, %s!
        Я бот для викторин. Нажмите "Новый вопрос" для начала викторины.
        /cancel - для отмены.
        ''' % user.first_name)
    update.message.reply_text(start_message, reply_markup=keyboard_markup)


@send_action(ChatAction.TYPING)
def get_new_question(update: Update, context: CallbackContext):
    """Обработка нового вопроса"""
    message_text = update.message.text
    if message_text == 'Новый вопрос':
        user = update.effective_user
        question_number = random.choice(read_quiz_questions('quiz_questions/'))
        redis.set(
            f'user_{user.id}',
            json.dumps({'last_question': question_number})
        )

        question_number = json.loads(redis.get(f'user_{user.id}'))
        print(question_number['question'])
        print(question_number['answer'])
        update.message.reply_text(quiz_question)

    # quiz_question = question_number['question']
    # quiz_answer = question_number['answer'].strip().lower()
    # message_text = update.message.text


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

    pool = redis.ConnectionPool(
        host=os.environ.get('REDIS_HOST'),
        port=os.environ.get('REDIS_PORT'),
        db=0,
        decode_responses=True)
    redis = redis.Redis(connection_pool=pool)

    try:
        updater = Updater(os.environ.get('DF_BOT_TOKEN'))
        dispatcher = updater.dispatcher
        dispatcher.add_handler(CommandHandler('start', start))
        dispatcher.add_handler(
            MessageHandler(
                Filters.text & ~Filters.command, get_new_question
            )
        )

        updater.start_polling()
        updater.idle()

    except Exception as e:
        logger.debug('Возникла ошибка в DialogFlow tg-боте')
        logger.exception(e)
