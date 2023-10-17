import argparse
import json
import logging
import os

import redis
from redis.exceptions import ConnectionError, TimeoutError
from dotenv import load_dotenv

from tools import read_quiz_questions, clean_answer

logger = logging.getLogger(__name__)


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
                        'question': questions[i],
                        'answer': clean_answer(questions[i + 1])
                    }
                    for i in range(0, len(questions), 2)
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
        logger.exception(conn_err)

    except FileNotFoundError:
        logger.error('Файл с вопросами не найден.')

    except Exception as e:
        logger.error(f'Не удалось записать вопросы в базу данных: {e}',
                     exc_info=True)


if __name__ == '__main__':
    main()
