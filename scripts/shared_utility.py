# coding: utf-8

from time import sleep
from typing import Dict

from config import CLIENT


def wait_for_update_successful(
    func_name: str, logger, max_wait: int = 5,
) -> Dict:
    """Actively wait for lambda function update to succeed.

    This wait is important. If we don't wait and immediately perform other
    operation on the function resource, e.g. update its config, boto3 would
    throw botocore.errorfactory.ResourceConflictException.

    The criteria for waiting is the 'LastUpdateStatus' not reaching
    'Successful'.

    :param func_name: lambda function name
    :type func_name: str
    :param logger: for logging purpose. There is no need to create a new logger
        for this utility function
    :param max_wait: max wait time for function upload to complete, defaults
        to 5
    :type max_wait: int
    :raises RuntimeError: calling CLIENT.get_function_configuration failed
    :raises RuntimeError: cannot get successful status after max_wait seconds
    :return: Response from calling get_function_configuration
    :rtype: Dict
    """
    while max_wait:
        try:
            resp = CLIENT.get_function_configuration(FunctionName=func_name)
        except Exception as err2:
            raise RuntimeError('Get lambda function status FAILED.') from err2
        if resp['LastUpdateStatus'] == 'Successful':
            break
        logger.info('Waiting for lambda function update to complete...')
        max_wait -= 1
        sleep(1)
    if not max_wait:
        raise RuntimeError(
            f'Timeout: Lambda function took more than {max_wait} seconds to '
            'update',
        )
    return resp
