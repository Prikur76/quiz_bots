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
