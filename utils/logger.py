import sys
import configuration.config as config
import logging


def get_logger():
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
        stream=sys.stdout
    )
    return logging.getLogger(config.APP_NAME)

# exporting the logger
logger = get_logger()