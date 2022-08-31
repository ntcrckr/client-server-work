from aiogram import types
from collections.abc import Mapping


class BotMessage(Mapping):
    text: str = None
    reply_markup: types.InlineKeyboardMarkup | None = None
    _buttons: list[types.InlineKeyboardButton] = None

    def __init__(
            self,
            text: str = None,
            reply_markup: types.InlineKeyboardMarkup = None,
            buttons: list[types.InlineKeyboardButton] = None
    ):
        self.text = text
        if reply_markup is not None:
            self.reply_markup = reply_markup
        elif buttons is not None:
            self.reply_markup = types.InlineKeyboardMarkup(
                inline_keyboard=[
                    [button]
                    for button in buttons
                ]
            )
        else:
            self.reply_markup = None
        self._buttons = buttons

    def to_dict(self):
        return {
            'text': self.text,
            'reply_markup': self.reply_markup
        }

    def __getitem__(self, item):
        return self.to_dict()[item]

    def __iter__(self):
        return iter(self.to_dict())

    def __len__(self):
        return len(self.to_dict())
