import json


def fetch_answer_from_db(user, db_connection):
    """Возвращает правильный ответ из базы данных по user_id"""
    question_number = json.loads(
        db_connection.hget('users', user)
    )['last_question']
    correct_answer = json.loads(
        db_connection.hget('quiz', question_number)
    )['answer']
    return correct_answer
