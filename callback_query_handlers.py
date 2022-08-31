from aiogram import types
from aiogram.dispatcher import FSMContext
import json

import bot_logger
import config
import message_handlers
import requests_to_server
import util


async def any_answer_callback_handler(callback_query: types.CallbackQuery, state: FSMContext) -> None:
    state_data = await util.get_state_data(state)

    bot_logger.debug(f"Received callback query: {callback_query.data=}, {state_data=}")

    if callback_query.from_user.id != state_data.user_id:
        bot_logger.debug(f"User's id doesn't match user_id saved in state_data: "
                         f"{callback_query.from_user.id=} {state_data.user_id=}")

        await callback_query.answer(
            text="Вы не можете отвечать на это сообщение, так как другой пользователь вызвал команду /bill.",
            show_alert=True
        )
        return

    if callback_query.message.chat.id != state_data.chat_id:
        bot_logger.debug(f"Chat's id doesn't match chat_id saved in state_data: "
                         f"{callback_query.message.chat.id=} {state_data.chat_id=}")

        await callback_query.answer(
            text="Вы не можете отвечать на это сообщение, так как вызвали команду /bill в другом чате.",
            show_alert=True
        )
        return

    if callback_query.message.message_id != state_data.message_id:
        bot_logger.debug(f"Message's id doesn't match message_id saved in state_data: "
                         f"{callback_query.message.message_id=} {state_data.message_id=}")

        await callback_query.answer(
            text="Вы не можете отвечать на это сообщение, так как это другое сообщение в ответ на /bill.",
            show_alert=True
        )
        return

    # callback_data = util.get_callback_data(callback_query.data)
    callback_data = callback_query.data

    state_data.previous_answers.append(util.PreviousAnswer(
        name=state_data.question_name,
        value=callback_data
    ))
    state_data.current_question += 1
    # print(state_data.answers_data)
    for answer_data in state_data.answers_data:
        # print(answer_data)
        if answer_data['id'] == int(callback_data):
            text = " ".join([str(answer_data[item]) for item in answer_data.keys() if item != 'id'])
            state_data.answers_dict[state_data.question_name_ru] = text

    bot_logger.debug(f"{state_data=}")

    await callback_query.message.edit_reply_markup()

    await util.update_state_data(state, state_data)

    await callback_query.answer(
        text=f"Ответ принят"
    )

    if not state_data.last_question:
        await message_handlers.new_question_routine(
            message=callback_query.message,
            state=state
        )
    else:
        await message_handlers.confirm_answers_routine(
            message=callback_query.message,
            state=state
        )


async def skip_callback_handler(callback_query: types.CallbackQuery, state: FSMContext) -> None:
    state_data = await util.get_state_data(state)

    bot_logger.debug(f"Received skip callback query: {callback_query.data=}, {state_data=}")

    if callback_query.from_user.id != state_data.user_id:
        bot_logger.debug(f"User's id doesn't match user_id saved in state_data: "
                         f"{callback_query.from_user.id=} {state_data.user_id=}")

        await callback_query.answer(
            text="Вы не можете отвечать на это сообщение, так как другой пользователь вызвал команду /bill.",
            show_alert=True
        )
        return

    if callback_query.message.chat.id != state_data.chat_id:
        bot_logger.debug(f"Chat's id doesn't match chat_id saved in state_data: "
                         f"{callback_query.message.chat.id=} {state_data.chat_id=}")

        await callback_query.answer(
            text="Вы не можете отвечать на это сообщение, так как вызвали команду /bill в другом чате.",
            show_alert=True
        )
        return

    if callback_query.message.message_id != state_data.message_id:
        bot_logger.debug(f"Message's id doesn't match message_id saved in state_data: "
                         f"{callback_query.message.message_id=} {state_data.message_id=}")

        await callback_query.answer(
            text="Вы не можете отвечать на это сообщение, так как это другое сообщение в ответ на /bill.",
            show_alert=True
        )
        return

    # callback_data = util.get_callback_data(callback_query.data)
    # callback_data = callback_query.data

    state_data.previous_answers.append(util.PreviousAnswer(
        name=state_data.question_name,
        value="---"
    ))
    state_data.current_question += 1
    # print(state_data.answers_data)
    state_data.answers_dict[state_data.question_name_ru] = "---"

    bot_logger.debug(f"{state_data=}")

    await callback_query.message.edit_reply_markup()

    await util.update_state_data(state, state_data)

    await callback_query.answer(
        text=f"Ответ принят"
    )

    if not state_data.last_question:
        await message_handlers.new_question_routine(
            message=callback_query.message,
            state=state
        )
    else:
        await message_handlers.confirm_answers_routine(
            message=callback_query.message,
            state=state
        )


async def last_step_callback_handler(callback_query: types.CallbackQuery, state: FSMContext) -> None:
    state_data = await util.get_state_data(state)

    bot_logger.debug(f"Received callback query: {callback_query.data=}, {state_data=}")

    if callback_query.from_user.id != state_data.user_id:
        bot_logger.debug(f"User's id doesn't match user_id saved in state_data: "
                         f"{callback_query.from_user.id=} {state_data.user_id=}")

        await callback_query.answer(
            text="Вы не можете отвечать на это сообщение, так как другой пользователь вызвал команду /bill.",
            show_alert=True
        )
        return

    # if callback_query.message.chat.id != state_data.chat_id:
    #     bot_logger.debug(f"Chat's id doesn't match chat_id saved in state_data: "
    #                      f"{callback_query.message.chat.id=} {state_data.chat_id=}")
    #
    #     await callback_query.answer(
    #         text="Вы не можете отвечать на это сообщение, так как вызвали команду /bill в другом чате.",
    #         show_alert=True
    #     )
    #     return

    if callback_query.message.message_id != state_data.message_id:
        bot_logger.debug(f"Message's id doesn't match message_id saved in state_data: "
                         f"{callback_query.message.message_id=} {state_data.message_id=}")

        await callback_query.answer(
            text="Вы не можете отвечать на это сообщение, так как это другое сообщение в ответ на /bill.",
            show_alert=True
        )
        return

    callback_data = callback_query.data

    match callback_data:
        case "no":
            await callback_query.message.delete()
            await callback_query.answer(
                text="Отмена"
            )
            await state.finish()
            return
        case "yes":
            response = requests_to_server.request_admin_question(
                data={
                    'chat_id': callback_query.message.chat.id,
                    'user_id': callback_query.from_user.id
                },
                previous_answers=json.dumps([
                    {
                        'name': previous_answer.name,
                        'value': previous_answer.value
                    }
                    for previous_answer in state_data.previous_answers
                ]),
                current_question=state_data.current_question,
                from_user_id=callback_query.from_user.id
            )
            balances_response = requests_to_server.request_balances(
                data={
                    'chat_id': callback_query.message.chat.id,
                    'user_id': callback_query.from_user.id
                },
                from_user_id=callback_query.from_user.id
            )
            bot_logger.debug(f"{balances_response.json()=}")

            admin_data = response.json()['data']['data']

            for balance_data in balances_response.json()['data']:
                bill = balance_data['bill']
                for idx in range(len(admin_data)):
                    if admin_data[idx]['bill'] == bill:
                        admin_data[idx]['current_sum'] = balance_data['current_sum']

            state_data.answers_data = admin_data

            bot_logger.debug(f"{state_data=}")

            await util.update_state_data(state, state_data)

            bot_logger.debug(f"{response.text=}")
            bot_msg = await util.construct_message_to_admin_chat(
                message=callback_query.message,
                answers_dict=state_data.answers_dict,
                answers_data=admin_data
            )

            await callback_query.bot.send_message(
                text=bot_msg.text,
                chat_id=config.ADMIN_CHAT_ID,
                reply_markup=bot_msg.reply_markup
            )
            await callback_query.answer(
                text="Запрос на подтверждение платежа был отправлен администратору.",
                show_alert=True
            )
            await callback_query.message.edit_text(
                text=callback_query.message.text + "\n\nОжидайте ответа от администрации."
            )


async def default_callback_handler(callback_query: types.CallbackQuery) -> None:
    await callback_query.message.delete()
    await callback_query.answer(
        text="Эта кнопка не работает, что-то пошло не так.",
        show_alert=True
    )
