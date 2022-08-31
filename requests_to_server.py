import hashlib
import time
import requests
import json
from enum import Enum
from aiogram import types

import bot_logger
import config


class RequestStatusCodeException(Exception):
    pass


class RequestDestroyException(Exception):
    pass


class RequestMethod(Enum):
    Post = 0
    Get = 1


def generate_token(from_user_id: types.User) -> str:
    return (
        hashlib.md5(
            (time.strftime("%H") + "SnabToken" + str(from_user_id)).encode()
        )
    ).hexdigest()


def send_to_server(
        code: str,
        data: dict[str],
        request_method: RequestMethod,
        url: str,
        from_user_id: types.User
) -> requests.Response:
    token = generate_token(from_user_id)
    params = {
        'code': code,
        'token': token,
        'data': json.dumps(data)
    }

    match request_method:
        case RequestMethod.Post:
            try:
                bot_logger.debug(f"Sending a post request to {url}. "
                                 f"Request params: {params}.")
                response = requests.post(url=url, data=params)
                response.raise_for_status()
                bot_logger.debug(f"Received a response for post request to {url}. "
                                 f"Request params: {params}. "
                                 f"Response text: {response.text}.")
                return response
            except requests.exceptions.HTTPError as e:
                bot_logger.error(f"Post request was unsuccessful due to HTTPError. Error: {e}.")
                raise e
            except requests.exceptions.RequestException as e:
                bot_logger.error(f"Post request was unsuccessful due to RequestException. Error: {e}.")
                raise e
        case RequestMethod.Get:
            try:
                bot_logger.debug(f"Sending a get request to {url}. "
                                 f"Request params: {params}.")
                response = requests.get(url=url, data=params)
                bot_logger.debug(f"Received a response for get request to {url}. "
                                 f"Request params: {params}. "
                                 f"Response text: {response.text}.")
                return response
            except requests.exceptions.HTTPError as e:
                bot_logger.error(f"Post request was unsuccessful due to HTTPError. Error: {e}.")
                raise e
            except requests.exceptions.RequestException as e:
                bot_logger.error(f"Post request was unsuccessful due to RequestException. Error: {e}.")
                raise e
        case _:
            bot_logger.error(f"Not a valid {request_method=} was passed to send_to_server().")
            raise Exception


def has_access(
        previous_answers: list,
        current_question: int,
        data: str,
        url: str,
        from_user_id: types.User
) -> requests.Response:
    bot_logger.info(f"Asking server if user has access to /bill.")

    params = {
        'previous_answers': previous_answers,
        'current_question': current_question,
        'data': data,
        'token': generate_token(from_user_id)
    }
    try:
        bot_logger.debug(f"Sending a bill post request to {url}. "
                         f"Request params: {params}.")
        response = requests.post(url=url, data=params)
        response.raise_for_status()
        bot_logger.debug(f"Received a bill response for post request to {url}. "
                         f"Request params: {params}. "
                         f"Response text: {response.text}.")
        return response
    except requests.exceptions.HTTPError as e:
        bot_logger.error(f"Post bill request was unsuccessful due to HTTPError. Error: {e}.")
        raise e
    except requests.exceptions.RequestException as e:
        bot_logger.error(f"Post bill request was unsuccessful due to RequestException. Error: {e}.")
        raise e


def ask_for_question(
        data: dict[str],
        previous_answers: str,
        current_question: int,
        from_user_id: types.User
) -> requests.Response:
    params = {
        'data': json.dumps(data),
        'previous_answers': previous_answers,
        'current_question': current_question,
        'token': generate_token(from_user_id)
    }
    url = config.WEB_URL_BILL_FORM
    try:
        bot_logger.debug(f"Sending a bill post request to {url}. "
                         f"Request params: {params}.")
        response = requests.post(
            url=url,
            data=params
        )
        response.raise_for_status()
        bot_logger.debug(f"Received a response for bill post request to {url}. "
                         f"Request params: {params}. "
                         f"Response text: {response.text}.")
        return response
    except requests.exceptions.HTTPError as e:
        bot_logger.error(f"Post request was unsuccessful due to HTTPError. Error: {e}.")
        raise e
    except requests.exceptions.RequestException as e:
        bot_logger.error(f"Post request was unsuccessful due to RequestException. Error: {e}.")
        raise e


def handle_json_error(
        message: types.Message,
        response: requests.Response
) -> dict:
    try:
        r = response.json()
    except requests.exceptions.JSONDecodeError as e:
        bot_logger.error(f"Failed to decode JSON response with text {response.text}: {repr(e)}.")
        raise e

    if response.status_code != 200:
        bot_logger.error(f"Response status code is not 200, but {response.status_code}. Response is {response.text}.")
        raise RequestStatusCodeException

    if r['error']:
        if r['destroy'] is True:
            raise RequestDestroyException
        else:
            raise Exception

    return r['data']


async def send_messages_to_delete(
        message: types.Message,
        message_ids: list[int]
) -> None:
    bot_logger.info(f"Sending messages to delete.")

    try:
        data = {
            'type': "bill",
            'data': json.dumps(
                {
                    'user_id': message.from_user.id,
                    'chat_id': message.chat.id
                }
            ),
            'messages': json.dumps(message_ids),
            'token': generate_token(message.from_user.id)
        }
        print(json.dumps(data, indent=4))
        response = requests.post(
            url=config.WEB_URL_DELETE,
            data=data
        )
        print(response.text)
        if response.status_code != 200:
            await message.bot.send_message(
                chat_id=message.chat.id,
                text=f"Неполадки с подключением к серверу. Код {response.status_code}"
            )
            return
        if response.json()['error']:
            await message.bot.send_message(
                chat_id=message.chat.id,
                text=f"Неполадки на сервере. {response.json()['error']}"
            )
            return
        return
    except Exception as e:
        return
    pass


def request_order(
        answers: list,
        data: str,
        from_user_id: types.User
) -> requests.Response:
    params = {
        f"{previous_answer.name}": previous_answer.value
        for previous_answer in answers
    }
    params['data'] = data
    params['token'] = generate_token(from_user_id)
    url = config.WEB_URL_ORDER
    try:
        bot_logger.debug(f"Sending a order post request to {url}. "
                         f"Request params: {params}.")
        response = requests.post(
            url=url,
            data=params
        )
        response.raise_for_status()
        bot_logger.debug(f"Received a response for order post request to {url}. "
                         f"Request params: {params}. "
                         f"Response text: {response.text}.")
        return response
    except requests.exceptions.HTTPError as e:
        bot_logger.error(f"Post request was unsuccessful due to HTTPError. Error: {e}.")
        raise e
    except requests.exceptions.RequestException as e:
        bot_logger.error(f"Post request was unsuccessful due to RequestException. Error: {e}.")
        raise e


def request_admin_question(
        data: dict[str],
        previous_answers: str,
        current_question: int,
        from_user_id: types.User
) -> requests.Response:
    params = {
        'data': json.dumps(data),
        'previous_answers': previous_answers,
        'current_question': current_question,
        'token': generate_token(from_user_id)
    }
    url = config.WEB_URL_ADMIN_QUESTION
    for answer in json.loads(previous_answers):
        if answer['name'] == "sellers":
            url += f"?seller_id={answer['value']}"
    try:
        bot_logger.debug(f"Sending a admin question post request to {url}. "
                         f"Request params: {params}.")
        response = requests.get(
            url=url,
            data=params
        )
        response.raise_for_status()
        bot_logger.debug(f"Received a response for admin question post request to {url}. "
                         f"Request params: {params}. "
                         f"Response text: {response.text}.")
        return response
    except requests.exceptions.HTTPError as e:
        bot_logger.error(f"Post request was unsuccessful due to HTTPError. Error: {e}.")
        raise e
    except requests.exceptions.RequestException as e:
        bot_logger.error(f"Post request was unsuccessful due to RequestException. Error: {e}.")
        raise e


def request_balances(
        data: dict[str],
        # previous_answers: str,
        # current_question: int,
        from_user_id: types.User
) -> requests.Response:
    params = {
        'data': json.dumps(data),
    #     'previous_answers': previous_answers,
    #     'current_question': current_question,
        'token': generate_token(from_user_id)
    }
    url = config.WEB_URL_BALANCES
    # for answer in json.loads(previous_answers):
    #     if answer['name'] == "sellers":
    #         url += f"?seller_id={answer['value']}"
    bot_logger.debug(f"Sending a admin question post request to {url}.")
    try:
        response = requests.post(
            url=url,
            params=params
        )
        response.raise_for_status()
        bot_logger.debug(f"Received a response for admin question post request to {url}."
                         f"Response text: {response.text}.")
        return response
    except requests.exceptions.HTTPError as e:
        bot_logger.error(f"Post request was unsuccessful due to HTTPError. Error: {e}.")
        raise e
    except requests.exceptions.RequestException as e:
        bot_logger.error(f"Post request was unsuccessful due to RequestException. Error: {e}.")
        raise e
