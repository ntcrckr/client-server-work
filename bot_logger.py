import logging

from config import LOG_FILE_PATH


logger = logging.getLogger("BotLog")
logger.setLevel(logging.DEBUG)

formatter = logging.Formatter(
    '%(asctime)s | %(name)s |  %(levelname)s: %(message)s')

stream_handler = logging.StreamHandler()
stream_handler.setLevel(logging.DEBUG)
stream_handler.setFormatter(formatter)

file_handler = logging.FileHandler(filename=LOG_FILE_PATH)
file_handler.setLevel(logging.DEBUG)
file_handler.setFormatter(formatter)

logger.addHandler(stream_handler)
logger.addHandler(file_handler)


def debug(message: str) -> None:
    logger.debug(message)


def info(message: str) -> None:
    logger.info(message)


def error(message: str) -> None:
    logger.error(message)
