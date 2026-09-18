class ConversationNotFoundError(Exception):
    pass


class ConversationExpiredError(Exception):
    pass


class ConversationAccessDeniedError(Exception):
    pass