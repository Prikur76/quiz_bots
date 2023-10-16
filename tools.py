import json
import os
import re
from functools import wraps


def send_action(action):
    """Отправляет действие в момент выполнения функции"""
    def decorator(func):
        @wraps(func)
        def command_func(update, context, *args, **kwargs):
            context.bot.send_chat_action(
                chat_id=update.effective_message.chat_id,
                action=action)
            return func(update, context, *args, **kwargs)
        return command_func
    return decorator


def read_quiz_questions(source_path, file_encoding='KOI8-R'):
    """Возвращает словарь из вопросов и ответов."""
    source_fullpath = os.path.abspath(source_path)
    questions = []
    for file in os.listdir(source_fullpath):
        filepath = os.path.join(source_fullpath, file)
        with open(filepath, 'r', encoding=file_encoding) as f:
            text = f.read().split('\n\n')
            content = [' '.join(i.strip().splitlines()[1:])
                       for i in text
                       if i.strip().startswith(('Вопрос', 'Ответ'))]
            questions.extend(content)
    return questions


def clean_answer(answer):
    """Удаляет лишние символы и содержимое в ответе"""
    pattern_1 = r'[\(\[].*?[\)\]]'
    pattern_2 = r'\.$'
    pattern_3 = r'\"'
    return re.sub(pattern_1, '',
                  re.sub(pattern_2, '',
                         re.sub(pattern_3, '',
                                answer)
                         )
                  ).strip()


def fetch_answer_from_db(user, db_connection):
    """Возвращает правильный ответ из базы данных по user_id"""
    question_number = json.loads(
        db_connection.hget('users', user)
    )['last_question']
    correct_answer = json.loads(
        db_connection.hget('quiz', question_number)
    )['answer']
    return correct_answer
