from aiogram import types
from aiogram.dispatcher import FSMContext
from aiogram.dispatcher.filters.state import State, StatesGroup
import time
import json

import requests_to_server
import bot_logger
import message_objects
import config
import util


class BillStates(StatesGroup):
    callback_step = State()
    number_step = State()
    text_step = State()
    last_step = State()
    admin_step = State()


# When new chat is created with bot in it
async def chat_created_routine(message: types.Message) -> None:
    bot_logger.info(f"Bot has been added to chat through creation. "
                    f"Chat name is {message.chat.title}.")

    response = requests_to_server.send_to_server(
        code="newChat",
        data={
            'chat_id': message.chat.id,
            'user_id': (await message.chat.get_administrators())[0].user.id,
            'date': time.strftime("%d.%m.%Y %H:%M")
        },
        request_method=requests_to_server.RequestMethod.Post,
        url=config.WEB_URL_IS_ADMIN,
        from_user_id=message.from_user.id
    )
    data = response.text
    match json.loads(data)["data"]["isValidAdmin"]:
        case "True":
            await message.bot.send_message(message.chat.id, "Чат подтвержден, как действительный.")
        case _:
            await message.bot.send_message(message.chat.id, "У вас нет прав администратора.")
            await message.bot.leave_chat(message.chat.id)


# When bot gets added to chat after chat's creation
async def added_to_chat_routine(message: types.Message) -> None:
    bot_logger.info(f"Bot has been added to chat after it's creation and is going to leave. "
                    f"Chat name is {message.chat.title}.")

    await message.answer(
        **message_objects.added_to_chat
    )
    await message.bot.leave_chat(message.chat.id)


async def pre_bill_routine(message: types.Message, state: FSMContext) -> None:
    bot_logger.info(f"Bot has received /bill and is going to start billing process.")

    response = requests_to_server.has_access(
        previous_answers=[],
        current_question=1,
        data=json.dumps(
            {
                'user_id': message.from_user.id,
                'chat_id': message.chat.id
            }
        ),
        url=config.WEB_URL_IS_ACCESS,
        from_user_id=message.from_user.id
    )

    r = response.json()

    if r['result'] is not True:
        bot_logger.info(f"Problems connecting to server: {r['data']}")

        await message.bot.send_message(
            chat_id=message.chat.id,
            text=f"Проблемы с доступом к серверу: {r['data']}"
        )
        await requests_to_server.send_messages_to_delete(message, [message.message_id])
        return

    if r['data'] is not True:
        await message.bot.send_message(
            chat_id=message.chat.id,
            text=f"Вам отказано в доступе"
        )
        # await requests_to_server.send_messages_to_delete(message, [message.message_id])
        return

    state_data = util.StateData(
        previous_answers=[],
        current_question=1,
        user_id=message.from_user.id,
        message_id=None,
        chat_id=message.chat.id,
        answer_type=None,
        question_name=None,
        last_question=False,
        question_name_ru="",
        answers_dict={},
        answers_data=[]
    )

    await message.delete()

    await util.update_state_data(state, state_data)

    await new_question_routine(
        message=message,
        state=state
    )


async def new_question_routine(message: types.Message, state: FSMContext) -> None:
    state_data = await util.get_state_data(state)

    bot_logger.debug(f"Step {state_data.current_question} of bill dialogue, state_data is {state_data}.")

    response = requests_to_server.ask_for_question(
        data={
            'chat_id': message.chat.id,
            'user_id': message.from_user.id
        },
        previous_answers=json.dumps([
            {
                'name': previous_answer.name,
                'value': previous_answer.value
            }
            for previous_answer in state_data.previous_answers
        ]),
        current_question=state_data.current_question,
        from_user_id=message.from_user.id
    )

    try:
        response_data = requests_to_server.handle_json_error(message=message, response=response)[0]
    except requests_to_server.RequestStatusCodeException as e:
        await message.answer(
            text="Произошла проблема на сервере. Попробуйте еще раз."
        )
        await state.finish()
        return
    except requests_to_server.RequestDestroyException as e:
        await message.answer(
            text=f"{response.json()['data']}. Заканчиваю ввод данных."
        )
        await state.finish()
        return
    except Exception:
        await message.answer(
            text=response.json()['data']
        )
        await state.finish()
        return

    bot_logger.debug(f"Response data is {response_data}.")

    bot_msg = await util.construct_question_with_answers(
        message=message,
        question_name=response_data['name'],
        question=response_data['question'],
        answer_type=response_data['type'],
        required=response_data['required'],
        answers_data=response_data['data']
    )

    state_data.last_question = response_data['last_question']
    state_data.answer_type = response_data['type']
    state_data.question_name = response_data['name']
    state_data.question_name_ru = response_data['name_ru']
    state_data.answers_data = response_data['data']

    if state_data.current_question == 1:
        msg = await message.answer(**bot_msg)
        state_data.message_id = msg.message_id

        await util.update_state_data(state, state_data)

        await BillStates.callback_step.set()
    else:
        try:
            answer_type = util.AnswerType(response_data['type'])
        except ValueError as e:
            bot_logger.error(f"answer_type is not suitable for AnswerType: {response_data['type']=}.")
            await message.answer(
                text="Ошибочные данные с сервера, прекращаю /bill диалог."
            )
            await state.finish()
            return
        match answer_type:
            case util.AnswerType.list_:
                await message.bot.edit_message_text(
                    text=bot_msg.text,
                    chat_id=state_data.chat_id,
                    message_id=state_data.message_id,
                    reply_markup=bot_msg.reply_markup
                )

                await util.update_state_data(state, state_data)

                await BillStates.callback_step.set()
            case util.AnswerType.float_:
                await message.bot.edit_message_text(
                    text=bot_msg.text,
                    chat_id=state_data.chat_id,
                    message_id=state_data.message_id,
                    reply_markup=bot_msg.reply_markup
                )

                await util.update_state_data(state, state_data)

                await BillStates.number_step.set()
            case util.AnswerType.text_:
                await message.bot.edit_message_text(
                    text=bot_msg.text,
                    chat_id=state_data.chat_id,
                    message_id=state_data.message_id,
                    reply_markup=bot_msg.reply_markup
                )

                await util.update_state_data(state, state_data)

                await BillStates.text_step.set()
            case _:
                bot_logger.error(f"Some unexpected AnswerType object was passed: {answer_type=}")
                await message.answer(
                    text="Ошибка во время определения типа вопроса, прекращаю /bill диалог."
                )
                await state.finish()
                return


async def confirm_answers_routine(message: types.Message, state: FSMContext) -> None:
    state_data = await util.get_state_data(state)

    bot_logger.debug(f"It was the last question, sending a message to confirm the answers: "
                     f"{state_data=}")

    markup = types.InlineKeyboardMarkup(
        inline_keyboard=[
            [types.InlineKeyboardButton(
                text="Да",
                callback_data="yes"
            )],
            [types.InlineKeyboardButton(
                text="Нет",
                callback_data="no"
            )]
        ]
    )

    text = f"Эти данные верны?"
    for ans in state_data.answers_dict:
        text += f"\n{ans}: {state_data.answers_dict[ans]}"

    await message.bot.edit_message_text(
        text=text,
        chat_id=message.chat.id,
        message_id=state_data.message_id,
        reply_markup=markup
    )

    await util.update_state_data(state, state_data)

    await BillStates.last_step.set()


async def number_step_handler(message: types.Message, state: FSMContext) -> None:
    state_data = await util.get_state_data(state)

    bot_logger.debug(f"Received number answer: {message.text=}, {state_data=}")

    if message.from_user.id != state_data.user_id:
        bot_logger.debug(f"User's id doesn't match user_id saved in state_data: "
                         f"{message.from_user.id=} {state_data.user_id=}")

        await message.answer(
            text="Вы не можете отвечать на это сообщение, так как другой пользователь вызвал команду /bill."
        )
        return

    # if message.chat.id != state_data.chat_id:
    #     bot_logger.debug(f"Chat's id doesn't match chat_id saved in state_data: "
    #                      f"{message.chat.id=} {state_data.chat_id=}")
    #
    #     await message.answer(
    #         text="Вы не можете отвечать на это сообщение, так как вызвали команду /bill в другом чате."
    #     )
    #     return

    state_data.previous_answers.append(util.PreviousAnswer(
        name=state_data.question_name,
        value=float(message.text)
    ))
    state_data.current_question += 1
    state_data.answers_dict[state_data.question_name_ru] = float(message.text)

    bot_logger.debug(f"{state_data=}")

    await message.delete()

    await util.update_state_data(state, state_data)

    if not state_data.last_question:
        await new_question_routine(
            message=message,
            state=state
        )
    else:
        await confirm_answers_routine(
            message=message,
            state=state
        )


async def text_step_handler(message: types.Message, state: FSMContext) -> None:
    state_data = await util.get_state_data(state)

    bot_logger.debug(f"Received text answer: {message.text=}, {state_data=}")

    if message.from_user.id != state_data.user_id:
        bot_logger.debug(f"User's id doesn't match user_id saved in state_data: "
                         f"{message.from_user.id=} {state_data.user_id=}")

        await message.answer(
            text="Вы не можете отвечать на это сообщение, так как другой пользователь вызвал команду /bill."
        )
        return

    # if message.chat.id != state_data.chat_id:
    #     bot_logger.debug(f"Chat's id doesn't match chat_id saved in state_data: "
    #                      f"{message.chat.id=} {state_data.chat_id=}")
    #
    #     await message.answer(
    #         text="Вы не можете отвечать на это сообщение, так как вызвали команду /bill в другом чате."
    #     )
    #     return

    state_data.previous_answers.append(util.PreviousAnswer(
        name=state_data.question_name,
        value=message.text
    ))
    state_data.current_question += 1
    state_data.answers_dict[state_data.question_name_ru] = message.text

    bot_logger.debug(f"{state_data=}")

    await message.delete()

    await util.update_state_data(state, state_data)

    if not state_data.last_question:
        await new_question_routine(
            message=message,
            state=state
        )
    else:
        await confirm_answers_routine(
            message=message,
            state=state
        )


# When bot receives a hashtag starting message
async def hashtag_command_routine(message: types.Message) -> None:
    bot_logger.info(f"Bot has received a hashtag starting message. "
                    f"Hashtag command is {message.text}.")

    response = requests_to_server.send_to_server(
        code="addCommand",
        data={
            'chat_id': message.chat.id,
            'user_id': message.from_user.id,
            'date': time.strftime("%d.%m.%Y %H:%M"),
            'command': message.text
        },
        request_method=requests_to_server.RequestMethod.Post,
        url=config.WEB_URL_COMMAND,
        from_user_id=message.from_user.id
    )
    bot_logger.info(f"Hashtag command request was sent successfully. "
                    f"Hashtag command is {message.text}. "
                    f"Response is {response.text}")

    await message.answer(
        text=response.json()['data']
    )


# When bot receives any message aside from all above cases
async def any_message_routine(message: types.Message) -> None:
    bot_logger.info(f"Bot has received a message. "
                    f"Message text is {message.text}.")

    response = requests_to_server.send_to_server(
        code="addMessage",
        data={
            'text': util.get_text(message),
            'files': await util.get_files(message),
            'chat_id': message.chat.id,
            'user_id': message.from_user.id,
            'message_id': message.message_id,
            'reply_to_message_id': util.get_reply_to_message_id(message),
            'date': time.strftime("%d.%m.%Y %H:%M")
        },
        request_method=requests_to_server.RequestMethod.Post,
        url=config.WEB_URL_MESSAGE,
        from_user_id=message.from_user.id
    )
    bot_logger.info(f"Message request was sent successfully. "
                    f"Message text is {message.text}. "
                    f"Response is {response.text}")
