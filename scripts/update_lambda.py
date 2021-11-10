# coding: utf-8

import json
import logging
import os
import sys
from argparse import ArgumentParser
from pathlib import Path
from shutil import copy, make_archive, rmtree
from typing import Dict

from config import CLIENT

# set up logger
logger = logging.getLogger()
console_handler = logging.StreamHandler()
formatter = logging.Formatter(
    '%(asctime)s - %(name)s - %(levelname)s - %(message)s',
)
console_handler.setFormatter(formatter)
logger.addHandler(console_handler)
logger.setLevel(logging.INFO)

# CONSTANT
ROOT_DIR: Path = Path(__file__).parent.parent.absolute()
TEMP: Path = ROOT_DIR.joinpath('temp')
ZIP_NAME: str = 'function.zip'


def clean_up() -> None:
    """Remove the temp folder and function zip file."""
    rmtree(TEMP)
    Path.unlink(ROOT_DIR.joinpath(ZIP_NAME))


def get_argument_parser() -> ArgumentParser:  # pragma no cover
    """Set up a parser to parse command line arguments.

    :return: A fresh, unused, ArgumentParser.
    """
    parser = ArgumentParser(
        description=(
            'Update lambda code and configuration for AWS Lambda '
            'Usage: env=test python3 '
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
    if Path.exists(TEMP):  # clean up any previous upload
        rmtree(TEMP)
    Path.mkdir(TEMP, parents=True)
    # copy files to temp
    for lambda_file in ROOT_DIR.joinpath(f'{func_folder_path}').glob('*'):
        copy(str(lambda_file), str(TEMP))
    # create zip file
    make_archive(ZIP_NAME.split('.')[0], 'zip', str(TEMP))


def update(
    func_name: str, desc: str, func_config: Dict[str, Dict],
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
    with open(ZIP_NAME, 'rb') as f_obj:  # upload
        zip_bytes = f_obj.read()
        try:
            resp1 = CLIENT.update_function_code(
                FunctionName=func_name,
                ZipFile=zip_bytes,
            )
        except Exception as err1:
            raise RuntimeError('Update lambda function code FAILED.') from err1
        logger.info(resp1)

    try:  # config
        resp2 = CLIENT.update_function_configuration(
            FunctionName=func_name,
            Description=desc,
            Environment={
                'Variables': func_config.get('vars', {}),
            },
            Layers=func_config.get('layers', []),
        )
    except Exception as err2:
        raise RuntimeError(
            'Update lambda function configuration FAILED.',
        ) from err2
    logger.info(resp2)


if __name__ == '__main__':
    # Parse command line arguments
    parser: ArgumentParser = get_argument_parser()
    args = parser.parse_args()

    logger.info(f'\033[30;43mUpdating code in {args.func_name}...\033[0m')

    if os.environ['env'] != 'dev':
        logger.error('Must use this script when "env=dev"!')
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

    try:
        update(args.func_name, args.description, func_config)
    except Exception as err_update:
        exception_handler('Failed to update function', err_update)
    clean_up()
    logger.info(f'\033[30;42mUpdate {args.func_name} SUCCESS!\033[0m')
