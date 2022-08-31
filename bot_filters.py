from aiogram import types
from aiogram.dispatcher.filters import Filter

import config


class ValidChatFilter(Filter):
    key = "valid_chat"

    async def check(self, message: types.Message) -> bool:
        if message.chat.id != config.HOME_CHAT_ID and \
                message.chat.title is not None:
            return True
        else:
            return False


class BotAddedToChatFilter(Filter):
    key = "bot_added_to_chat"

    async def check(self, message: types.Message) -> bool:
        if message.new_chat_members:
            for new_chat_member in message.new_chat_members:
                if new_chat_member.id == config.BOT_ID:
                    return True
            return False
        else:
            return False


class HashtagCommandFilter(Filter):
    key = "hashtag_command_filter"

    async def check(self, message: types.Message) -> bool:
        if message.text:
            return message.text[:2] == "##"
        else:
            return False
