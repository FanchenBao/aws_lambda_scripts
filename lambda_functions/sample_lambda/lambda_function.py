import json
import logging
import os

import requests

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
    logger.info(f'env = {os.environ["env"]}')
    resp = requests.get(
        'https://v2.jokeapi.dev/joke/Programming?type=single',
    )
    logger.info(json.loads(resp.text)['joke'])
