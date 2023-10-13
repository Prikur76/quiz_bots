import os
import re
import redis
from functools import wraps


base_dir = os.path.dirname(__file__)


def read_quiz_questions(source_path, file_encoding='KOI8-R'):
    """Возвращает словарь из вопросов и ответов."""
    source_fullpath = os.path.abspath(source_path)
    questions = []
    for file in os.listdir(source_fullpath):
        filepath = os.path.join(source_fullpath, file)
        with open(filepath, 'r', encoding=file_encoding) as f:
            text = f.read().split('\n\n')
            content = [' '.join(i.strip().splitlines()[1:])
                       for i in text if i.strip().startswith(('Вопрос', 'Ответ'))]
            questions.extend(content)
    quiz_questions = dict(
        enumerate(
            [
                {
                    'question': questions[i],
                    'answer': re.sub(
                        r'[\(\[].*?[\)\]]','',
                        questions[i+1]).strip()
                }
                for i in range(0, len(questions), 2)
            ]
        )
    )
    return quiz_questions


def get_quiz_answer(quiz_questions, question):
    """Возвращает правильный ответ."""
    return next((i for i in quiz_questions.values() if i['question'] == question), None)['answer']


def send_action(action):
    """Sends `action` while processing func command."""

    def decorator(func):
        @wraps(func)
        def command_func(update, context, *args, **kwargs):
            context.bot.send_chat_action(chat_id=update.effective_message.chat_id, action=action)
            return func(update, context, *args, **kwargs)

        return command_func
    return decorator


#
# content = read_quiz_questions('quiz_questions')
# print(content)
# question = 'Это "недостающее звено" в прошлом веке обнаружил на острове Ява голландский врач, тем самым лишний раз доказывая правильность суждения одного англичанина. Позднее это "звено" было обнаружено в Африке, Азии, Европе. Как звали англичанина.'
# answer = get_quiz_answer(content, question)
# print(answer)

# pool = redis.ConnectionPool(host='localhost', port=6379, db=0, decode_responses=True)
# redis = redis.Redis(connection_pool=pool)
#
# redis.set('user_123', 'What the Fuck, Dude!')
# value = redis.get('user_123')
# print(value)