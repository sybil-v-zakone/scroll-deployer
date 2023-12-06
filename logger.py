from loguru import logger

from constants import LOGS_FILE_PATH


def configure_logger():
    logger.add(sink=LOGS_FILE_PATH)


configure_logger()
