import argparse
import json
import logging
import os
import re

import redis
from dotenv import load_dotenv
from redis.exceptions import ConnectionError, TimeoutError

logger = logging.getLogger(__name__)


def read_quiz_questions(source_path, file_encoding='KOI8-R'):
    """Возвращает словарь из вопросов и ответов."""
    source_fullpath = os.path.abspath(source_path)
    questions = []
    for file in os.listdir(source_fullpath):
        filepath = os.path.join(source_fullpath, file)
        with open(filepath, 'r', encoding=file_encoding) as f:
            text = f.read().split('\n\n')
        content = [' '.join(row.strip().splitlines()[1:])
                   for row in text
                   if row.strip().startswith(('Вопрос', 'Ответ'))]
        questions.extend(content)
    return questions


def clean_answer(answer):
    """Удаляет лишние символы и содержимое в ответе"""
    comments_pattern = r'[\(\[].*?[\)\]]'
    last_dot_pattern = r'\.$'
    quotation_marks_pattern = r'\"'
    return re.sub(comments_pattern, '',
                  re.sub(last_dot_pattern, '',
                         re.sub(quotation_marks_pattern, '',
                                answer)
                         )
                  ).strip()


def main():
    load_dotenv()
    logging.basicConfig(
        format='[%(levelname)s] - %(asctime)s - %(name)s - %(message)s',
        level=logging.INFO
    )

    parser = argparse.ArgumentParser(
        description='Записывает вопросы в базу данных Redis')
    parser.add_argument('-sp', type=str,
                        help='Путь до файлов с фразами',
                        required=True)
    parser.add_argument('-enc', type=str,
                        help='Кодировка фраз',
                        default='KOI8-R')
    args = parser.parse_args()
    source_path = args.sp
    file_encoding = args.enc

    try:
        questions = read_quiz_questions(source_path, file_encoding)
        quiz_questions = dict(
            enumerate(
                [
                    {
                        'question': questions[question_number],
                        'answer': clean_answer(
                            questions[question_number + 1])
                    }
                    for question_number in range(0, len(questions), 2)
                ],
                start=1
            )
        )
        pool = redis.ConnectionPool(
            host=os.environ.get('REDIS_HOST'),
            port=os.environ.get('REDIS_PORT'),
            password=os.environ.get('REDIS_PASSWORD'),
            db=0)
        r = redis.Redis(connection_pool=pool,
                        decode_responses=True)
        if r.ping():
            logger.info('Подключение к БД установлено')

        for question_number, question in quiz_questions.items():
            r.hset('quiz', key=str(question_number),
                   value=json.dumps(question))

        logger.info('Вопросы успешно записаны в базу данных.')

    except (TimeoutError, ConnectionError) as conn_err:
        logger.debug('Redis connection error')
        logger.exception(conn_err, exc_info=False)

    except FileNotFoundError:
        logger.error('Файл с вопросами не найден.')

    except Exception as e:
        logger.error(f'Не удалось записать вопросы в базу данных: {e}',
                     exc_info=True)


if __name__ == '__main__':
    main()
