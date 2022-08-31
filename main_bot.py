import json

from aiogram import Bot, Dispatcher, executor, types
from aiogram.contrib.fsm_storage.memory import MemoryStorage

import bot_logger
import callback_query_handlers
import requests_to_server
import util
from config import BOT_TOKEN
import message_handlers
import bot_filters


storage = MemoryStorage()

bot_logger.info("Creating Telegram Bot")
bot = Bot(token=BOT_TOKEN)
bot_logger.info("Creating Bot Dispatcher")
dp = Dispatcher(bot, storage=storage)


async def admin_callback_handler(callback_query: types.CallbackQuery) -> None:
    bot_logger.debug(f"Received callback query: {callback_query.data=}")

    _, chat_id, answer = callback_query.data.split("/")

    state = dp.get_current().current_state(
        chat=chat_id
    )
    try:
        state_data = await util.get_state_data(state)
    except KeyError as e:
        bot_logger.error(repr(e))
        await callback_query.message.delete()
        await callback_query.answer()
        return

    match answer:
        case "reject":
            await callback_query.answer()
            await callback_query.message.delete()
            await callback_query.bot.edit_message_text(
                text="Ваш запрос был отклонен.",
                chat_id=chat_id,
                message_id=state_data.message_id
            )
            await state.finish()
        case _:
            state_data.previous_answers.append(util.PreviousAnswer(
                name="bank_accountants",
                value=answer
            ))

            response = requests_to_server.request_order(
                answers=state_data.previous_answers,
                data=json.dumps({'chat_id': callback_query.message.chat.id, 'user_id': callback_query.from_user.id}),
                from_user_id=callback_query.from_user.id
            )

            bot_logger.debug(f"{response.text=}")

            if response.json()['error'] != 0:
                await callback_query.bot.send_message(
                    chat_id=callback_query.message.chat.id,
                    text=f"{response.json()['data']}"
                )
                await state.finish()
                return
            elif response.json()['data'] is not True:
                await callback_query.bot.send_message(
                    chat_id=callback_query.message.chat.id,
                    text=f"Произошла ошибка, pdf не был передан. Сообщите администратору"
                )
                await state.finish()
                return
            await callback_query.answer()
            await callback_query.message.delete()
            await callback_query.bot.send_document(
                chat_id=chat_id,
                document=response.json()['path'],
                caption=f"Вот ваш счёт и ссылка на него: {response.json()['path']}"
            )
            await callback_query.bot.delete_message(
                chat_id=chat_id,
                message_id=state_data.message_id,
            )
            await state.finish()
            return


bot_logger.info("Start registering message handlers")
dp.register_message_handler(
    message_handlers.chat_created_routine,
    bot_filters.ValidChatFilter(),
    content_types=['group_chat_created']
)
dp.register_message_handler(
    message_handlers.added_to_chat_routine,
    bot_filters.ValidChatFilter(),
    bot_filters.BotAddedToChatFilter(),
    content_types=['new_chat_members']
)
dp.register_message_handler(
    message_handlers.hashtag_command_routine,
    bot_filters.ValidChatFilter(),
    bot_filters.HashtagCommandFilter(),
    content_types=['text']
)
dp.register_message_handler(
    message_handlers.pre_bill_routine,
    bot_filters.ValidChatFilter(),
    commands=['bill']
)
dp.register_message_handler(
    message_handlers.number_step_handler,
    bot_filters.ValidChatFilter(),
    state=message_handlers.BillStates.number_step
)
dp.register_message_handler(
    message_handlers.text_step_handler,
    bot_filters.ValidChatFilter(),
    state=message_handlers.BillStates.text_step
)
dp.register_message_handler(
    message_handlers.any_message_routine,
    bot_filters.ValidChatFilter(),
    content_types=["text", "audio", "document", "photo", "sticker",
                   "video", "video_note", "voice", "location", "contact"]
)
bot_logger.info("Finish registering message handlers")


bot_logger.info("Start registering callback query handlers")
dp.register_callback_query_handler(
    callback_query_handlers.any_answer_callback_handler,
    state=message_handlers.BillStates.callback_step
)
dp.register_callback_query_handler(
    callback_query_handlers.skip_callback_handler,
    lambda cq: cq.data == "skip",
    state="*"
)
dp.register_callback_query_handler(
    callback_query_handlers.last_step_callback_handler,
    state=message_handlers.BillStates.last_step
)
dp.register_callback_query_handler(
    admin_callback_handler,
    lambda cq: cq.data.startswith("admin")
)
dp.register_callback_query_handler(
    callback_query_handlers.default_callback_handler,
    state="*"
)
bot_logger.info("Finish registering callback query handlers")


if __name__ == "__main__":
    executor.start_polling(dp, skip_updates=True)
