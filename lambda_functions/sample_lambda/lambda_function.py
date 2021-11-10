import logging
import os

# set up logger
logger = logging.getLogger()
console_handler = logging.StreamHandler()
formatter = logging.Formatter(
    '%(asctime)s - %(name)s - %(levelname)s - %(message)s',
)
console_handler.setFormatter(formatter)
logger.addHandler(console_handler)
logger.setLevel(logging.INFO)


def lambda_handler(event, context):
    """A lambda function for demo purpose.

    :param event: Not used.
    :type event: [type]
    :param context: Not used.
    :type context: [type]
    """
    logger.info('hello world')
    logger.info(f'env = {os.environ["env"]}')
