# coding: utf-8

import json
import logging
import os
import sys
from argparse import ArgumentParser
from pathlib import Path
from shutil import copy, make_archive, rmtree
from typing import Dict, List, Union, cast

from config import (
    CLIENT,
    FUNCTION_TEMP,
    FUNCTION_ZIP,
    PYTHON_VERSION,
    ROOT_DIR,
)
from shared_utility import wait_for_update_successful

# set up logger
logger = logging.getLogger()
console_handler = logging.StreamHandler()
formatter = logging.Formatter(
    '%(asctime)s - %(name)s - %(levelname)s - %(message)s',
)
console_handler.setFormatter(formatter)
logger.addHandler(console_handler)
logger.setLevel(logging.INFO)


def clean_up() -> None:
    """Remove the temp folder and function zip file."""
    rmtree(FUNCTION_TEMP)
    Path.unlink(ROOT_DIR.joinpath(FUNCTION_ZIP))


def get_argument_parser() -> ArgumentParser:  # pragma no cover
    """Set up a parser to parse command line arguments.

    :return: A fresh, unused, ArgumentParser.
    """
    parser = ArgumentParser(
        description=(
            'Update lambda code and configuration for AWS Lambda '
            'Usage: env=dev python3 '
            'update_lambda --func_name [NAME] --func_folder_path [PATH] '
            '--description [DESC].'
        ),
    )
    parser.add_argument(
        '--func_folder_path',
        dest='func_folder_path',
        type=str,
        required=True,
        help=(
            'REQUIRED. The path to the folder containing one or more Python '
            'files that contribute to the lambda function'
        ),
    )
    parser.add_argument(
        '--func_name',
        dest='func_name',
        type=str,
        required=True,
        help=(
            'REQUIRED. The name of the lambda function as shown on AWS.'
        ),
    )
    parser.add_argument(
        '--description',
        dest='description',
        type=str,
        required=True,
        help=(
            'REQUIRED. The description of the lambda function.'
        ),
    )
    return parser


def exception_handler(error_msg: str, err: Exception) -> None:
    """Log exception and error message, and clean up the procedure.

    :param error_msg: The error message to log.
    :param err: The exception itself.
    """
    logger.exception(err)
    logger.error(f'\033[30;41m{error_msg}\033[0m')
    clean_up()
    sys.exit(1)


def prep_files(func_folder_path: str) -> None:
    """Prepare a temp folder to hold all the files to be uploaded to Lambda.

    :param func_folder_path: Path to the folder that holds all the Python files
        for the Lambda function.
    """
    # prepare temp folder
    if Path.exists(FUNCTION_TEMP):  # clean up any previous upload
        rmtree(FUNCTION_TEMP)
    Path.mkdir(FUNCTION_TEMP, parents=True)
    # copy files to temp
    for lambda_file in ROOT_DIR.joinpath(f'{func_folder_path}').glob('*.py'):
        copy(str(lambda_file), str(FUNCTION_TEMP))
    # create zip file
    make_archive(FUNCTION_ZIP.split('.')[0], 'zip', str(FUNCTION_TEMP))


def get_layer_arn(layers: List) -> List[str]:
    """Get the arns for each layer specified by the config JSON file.

    :param layers: Name of the layers specified in the config JSON file.
    :type layers: List
    :raises RuntimeError: when getting the list of layers fails
    :return: A list of layer arns.
    :rtype: List[str]
    """
    if not layers:
        return []
    try:
        resp = CLIENT.list_layers(CompatibleRuntime=PYTHON_VERSION)
    except Exception as err:
        raise RuntimeError('Unable to obtain ARNs for layers') from err
    res = []
    for ly in resp['Layers']:
        if ly['LayerName'] in layers:
            res.append(ly['LatestMatchingVersion']['LayerVersionArn'])
    return res


def update(
    func_name: str,
    desc: str,
    func_config: Dict[str, Union[Dict, List]],
) -> None:
    """Upload lambda code base (as a zip file) to its associated AWS Lambda.

    :param func_name: Name of the Lambda function as shown on AWS Lambda.
    :param desc: Description of the Lambda function.
    :param func_config: Configs associated with the Lambda function. It can
        have the following shape. {'vars': {key: value}, 'layers': [layers]}.
        The value for 'vars' is a Dict describing the key-value pair used by
        the Lambda function as environment variables. The value 'layers' is a
        list of layers used by the Lambda function. If no environment variable
        or no layer exists, func_config can be passed as an empty dict.
    :raises RuntimeError: Either update function code fails, or update function
        config fais.
    """
    with open(FUNCTION_ZIP, 'rb') as f_obj:  # upload
        zip_bytes = f_obj.read()
        try:
            CLIENT.update_function_code(
                FunctionName=func_name,
                ZipFile=zip_bytes,
            )
        except Exception as err1:
            raise RuntimeError('Update lambda function code FAILED.') from err1

    wait_for_update_successful(func_name, logger)
    logger.info(f'Lambda function {func_name} updated')

    try:  # config
        resp = CLIENT.update_function_configuration(
            FunctionName=func_name,
            Description=desc,
            Environment={
                'Variables': func_config.get('vars', {}),
            },
            Layers=get_layer_arn(cast(List, func_config.get('layers', []))),
        )
    except Exception as err3:
        raise RuntimeError(
            'Update lambda function configuration FAILED.',
        ) from err3
    cur_env_var = resp['Environment']['Variables']
    logger.info(f'Updated env variables: {cur_env_var}')
    cur_layers = [ly['Arn'] for ly in resp['Layers']]
    logger.info(f'Updated layers: {cur_layers}')


if __name__ == '__main__':
    # Parse command line arguments
    parser: ArgumentParser = get_argument_parser()
    args = parser.parse_args()

    logger.info(f'\033[30;43mUpdating code in {args.func_name}...\033[0m')

    if 'env' not in os.environ or os.environ['env'] != 'dev':
        logger.error('\033[30;41mMust use this script when "env=dev"!\033[0m')
        sys.exit(1)
    try:
        prep_files(args.func_folder_path)
    except Exception as err_prep:
        exception_handler('Failed to prepare zip file for function', err_prep)

    config_file = ROOT_DIR.joinpath(
        f'{args.func_folder_path}/config.dev.json',
    )
    try:
        with open(config_file, 'r') as f_obj:
            func_config = json.load(f_obj)
    except FileNotFoundError as err_config:
        exception_handler(f'Must provide {config_file} file', err_config)

    # make sure the function is ready to be updated before proceeding
    wait_for_update_successful(args.func_name, logger)

    try:
        update(args.func_name, args.description, func_config)
    except Exception as err_update:
        exception_handler('Failed to update function', err_update)
    clean_up()
    logger.info(f'\033[30;42mUpdate {args.func_name} SUCCESS!\033[0m')
