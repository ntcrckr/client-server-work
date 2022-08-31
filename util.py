from aiogram import types
from dataclasses import dataclass
from aiogram.dispatcher import FSMContext
from enum import Enum

import bot_logger
import bot_message
import config


class AnswerType(Enum):
    list_ = "list"
    float_ = "float"
    text_ = "text"


@dataclass
class PreviousAnswer:
    name: str
    value: str | float


@dataclass
class StateData:
    previous_answers: list[PreviousAnswer]
    current_question: int
    user_id: int
    message_id: int | None
    chat_id: int
    answer_type: AnswerType | None
    question_name: str | None
    last_question: bool
    question_name_ru: str
    answers_dict: dict
    answers_data: list[dict[str]]


@dataclass
class CallbackData:
    name: str
    answer_id: int


async def update_state_data(state: FSMContext, state_data: StateData) -> None:
    await state.update_data(data={
        'state_data': state_data
    })


async def get_state_data(state: FSMContext) -> StateData:
    return (await state.get_data())['state_data']


def get_text(message: types.Message):
    if message.text:
        return message.text
    elif message.caption:
        return message.caption
    else:
        return ""


async def get_files(message: types.Message):
    files = {
        "audio": "",
        "document": "",
        "photo": [],
        "sticker": "",
        "video": "",
        "video_note": "",
        "voice": "",
        "location": {},
        "contact": {}
    }
    if message.audio:
        new_file = await message.bot.get_file(message.audio.file_id)
        files["audio"] = "https://api.telegram.org/file/bot" + config.BOT_TOKEN + "/" + new_file["file_path"]
    if message.document:
        new_file = await message.bot.get_file(message.document.file_id)
        files["document"] = "https://api.telegram.org/file/bot" + config.BOT_TOKEN + "/" + new_file["file_path"]
    if message.photo:
        for photo in message.photo:
            new_file = await message.bot.get_file(photo.file_id)
            files["photo"].append("https://api.telegram.org/file/bot" + config.BOT_TOKEN + "/" + new_file["file_path"])
    if message.sticker:
        new_file = await message.bot.get_file(message.sticker.thumb.file_id)
        files["sticker"] = "https://api.telegram.org/file/bot" + config.BOT_TOKEN + "/" + new_file["file_path"]
    if message.video:
        new_file = await message.bot.get_file(message.video.file_id)
        files["video"] = "https://api.telegram.org/file/bot" + config.BOT_TOKEN + "/" + new_file["file_path"]
    if message.video_note:
        new_file = await message.bot.get_file(message.video_note.file_id)
        files["video_note"] = "https://api.telegram.org/file/bot" + config.BOT_TOKEN + "/" + new_file["file_path"]
    if message.voice:
        new_file = await message.bot.get_file(message.voice.file_id)
        files["voice"] = "https://api.telegram.org/file/bot" + config.BOT_TOKEN + "/" + new_file["file_path"]
    if message.location:
        files["location"]["longitude"] = message.location.longitude
        files["location"]["latitude"] = message.location.latitude
    if message.contact:
        files["contact"]["phone_number"] = message.contact.phone_number
        files["contact"]["first_name"] = message.contact.first_name
        if message.contact.last_name:
            files["contact"]["last_name"] = message.contact.last_name
        else:
            files["contact"]["last_name"] = ""
        if message.contact.user_id:
            files["contact"]["user_id"] = message.contact.user_id
        else:
            files["contact"]["user_id"] = 0
    return files


def get_reply_to_message_id(message: types.Message):
    if message.reply_to_message:
        print("reply good")
        return message.reply_to_message.message_id
    else:
        print("reply bad")
        return 0


def check_float(
        potential_float
) -> bool:
    try:
        float(potential_float)
        return True
    except ValueError:
        return False


async def construct_question_with_answers(
        message: types.Message,
        question_name: str,
        question: str,
        answer_type: str,
        required: bool,
        answers_data: list[dict[str]]
) -> bot_message.BotMessage:
    bot_logger.debug(f"Making a buttoned message for this data: "
                     f"{question_name=}, {question=}, {answer_type=}, {required=} {answers_data=}")

    _type = AnswerType(answer_type)

    match _type:
        case AnswerType.list_:
            markup = types.InlineKeyboardMarkup(
                row_width=1
            )
            for item in answers_data:
                text = f"{item['name']}, ИНН: {item['inn']}" if question_name == "legals" else item['name']
                callback_data = item['id']
                markup.add(
                    types.InlineKeyboardButton(
                        text=text,
                        callback_data=callback_data
                    )
                )
            if not required:
                markup.add(
                    types.InlineKeyboardButton(
                        text="Пропустить",
                        callback_data="skip"
                    )
                )

            return bot_message.BotMessage(
                text=question,
                reply_markup=markup
            )
        case AnswerType.float_:
            if required:
                return bot_message.BotMessage(
                    text=question
                )
            else:
                return bot_message.BotMessage(
                    text=question,
                    reply_markup=types.InlineKeyboardMarkup().add(
                        types.InlineKeyboardButton(
                            text="Пропустить",
                            callback_data="skip"
                        )
                    )
                )
        case AnswerType.text_:
            if required:
                return bot_message.BotMessage(
                    text=question
                )
            else:
                return bot_message.BotMessage(
                    text=question,
                    reply_markup=types.InlineKeyboardMarkup().add(
                        types.InlineKeyboardButton(
                            text="Пропустить",
                            callback_data="skip"
                        )
                    )
                )


async def construct_message_to_admin_chat(
        message: types.Message,
        answers_dict: dict[str],
        answers_data: list[dict[str]]
) -> bot_message.BotMessage:
    bot_logger.debug(f"Making a buttoned message for this data: "
                     f"{answers_dict=}, {answers_data=}")
    markup = types.InlineKeyboardMarkup(
        row_width=1
    )
    for item in answers_data:
        if item['name'].startswith("ОАО "):
            name = item['name'][4:]
        elif item['name'].startswith("КБ "):
            name = item['name'][3:]
        else:
            name = item['name']
        text = f"{name} : " \
               f"{item['date_add_current_sum'] if 'date_add_current_sum' in item else '---'} : " \
               f"{item['current_sum'] if 'current_sum' in item else '---'}"
        callback_data = f"admin/{message.chat.id}/{item['id']}"
        markup.add(
            types.InlineKeyboardButton(
                text=text,
                callback_data=str(callback_data)
            )
        )
    markup.add(
        types.InlineKeyboardButton(
            text="Отклонить",
            callback_data=f"admin/{message.chat.id}/reject"
        )
    )

    text = "Подтвердить данный запрос?"
    for ans in answers_dict:
        text += f"\n{ans}: {answers_dict[ans]}"
    return bot_message.BotMessage(
        text=text,
        reply_markup=markup
    )
