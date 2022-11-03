# coding: utf-8

import json
import logging
import sys
from argparse import ArgumentParser
from pathlib import Path
from typing import Dict

from config import CLIENT, ROOT_DIR
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


def get_argument_parser() -> ArgumentParser:  # pragma no cover
    """Set up a parser to parse command line arguments.

    :return: A fresh, unused, ArgumentParser.
    """
    parser = ArgumentParser(
        description=(
            'Publish a new version of the well-tested lambda function, and '
            'assign an alias to it. When publishing '
            'a new version, the only thing that needs to be updated is the '
            'environmental variable. '
            'Usage: python3 '
            'publish_to_alias --func_folder_path [path] '
            '--func_name [lambda name] '
            '--alias [alias] '
            '--description [description of the alias].'
        ),
    )
    parser.add_argument(
        '--func_folder_path',
        dest='func_folder_path',
        type=str,
        required=True,
        help=(
            'REQUIRED. The path to the folder containing configs for lambda '
            'function of different alias'
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
        '--alias',
        dest='alias',
        type=str,
        required=True,
        help=(
            'REQUIRED. Name of the alias.'
        ),
    )
    parser.add_argument(
        '--description',
        dest='description',
        type=str,
        required=True,
        help=(
            'REQUIRED. The description of the lambda function version used for'
            'the alias.'
        ),
    )
    return parser


def exception_handler(
    error_msg: str, err: Exception, env_vars_dev: Dict, func_name: str,
) -> None:
    """Log exception and error message, and clean up the procedure.

    :param error_msg: The error message to log.
    :param err: The exception itself.
    :param env_vars_dev: Environment variables for the dev version of Lambda
        function
    :param func_name: Name of the target function.
    """
    logger.exception(err)
    logger.error(f'\033[30;41m{error_msg}\033[0m')
    if env_vars_dev:
        clean_up(env_vars_dev, func_name)
    sys.exit(1)


def update_env_variables(env_vars: Dict, func_name: str) -> Dict:
    """Update the environment variables of the Lambda.

    Only change the environment variables of the target lambda, such as the
    "ENV" field. Note that the entire environment variables must be passed, not
    just the field to be updated.

    :param env_vars: All the environment variables, including the field to be
        updated and the fields that remain the same.
    :param func_name: Name of the lambda function.
    :return: The response from calling update_function_configuration()
    :raises RuntimeError: when update_function_configuration() call fails.
    """
    try:  # config
        resp = CLIENT.update_function_configuration(
            FunctionName=func_name,
            Environment={
                'Variables': env_vars,
            },
        )
    except Exception as err:
        raise RuntimeError(
            'Update lambda function environment variable FAILED.',
        ) from err
    cur_env_var = resp['Environment']['Variables']
    logger.info(f'Updated env: {cur_env_var}')
    return resp


def publish_version(
    func_name: str,
    description: str,
    codesha256: str,
    revision_id: str,
) -> Dict:
    """Publish a new version of the Lambda function.

    :param func_name:   Name of the lambda function.
    :param description: A description for the new verion.
    :param codesha256:  Hashed value of the code file, obtained from the call
                        to update lambda function configuration.
    :param revision_id: Acquired from the call to update lambda function
                        configuration.
    :return: The response from calling publish_version().
    :raises RuntimeError: when publish version fails.
    """
    try:
        resp = CLIENT.publish_version(
            FunctionName=func_name,
            CodeSha256=codesha256,
            Description=description,
            RevisionId=revision_id,
        )
    except Exception as err:
        raise RuntimeError(
            'Publish new Lambda function version FAILED.',
        ) from err
    logger.info(f"Published version {resp['Version']}")
    return resp


def get_alias(func_name: str, alias: str):
    """Get the alias of the given lambda function.

    If the given alias does not exist in the lambda function, return an empty
    dict. Otherwise, return the response of get_alias().

    :param func_name:   Name of the lambda function.
    :param alias:       Name of the alias.
    :return: Empty dict if alias doesn't exist; otherwise resp of get_alias().
    :raises RuntimeError: when get_alias() call fails.
    """
    try:
        resp_get_alias: Dict = CLIENT.get_alias(
            FunctionName=func_name, Name=alias,
        )
    except CLIENT.exceptions.ResourceNotFoundException:
        return {}
    except Exception as err:
        raise RuntimeError(
            f'Error at acquiring current aliases for {func_name}',
        ) from err
    return resp_get_alias


def assign_alias(
    alias: str,
    func_name: str,
    version: str,
) -> Dict:
    """Assign an alias to the version provided.

    This function first checks whether the given alias exists. If it does not
    exist, we create a new alias. If it does, we update the current alias.

    :param alias:       Alias of the lambda function.
    :param func_name:   Name of the lambda function.
    :param version:     The lambda function version to be assigned to the
                        alias.
    :return: The response from calling create_alias() or update_alias().
    :raises RuntimeError: when update_alias() or create_alias() call fails.
    """
    resp_get_alias: Dict = get_alias(func_name, alias)
    if resp_get_alias:
        logger.info(f'Alias {alias} already exists. Update it.')
        try:
            resp_update = CLIENT.update_alias(
                FunctionName=func_name,
                Name=alias,
                FunctionVersion=version,
                Description=f'For use in the {alias} environment',
                RevisionId=resp_get_alias['RevisionId'],
            )
        except Exception as err1:
            raise RuntimeError(f'Unable to update alias: {alias}') from err1
        logger.info(
            f"Updated alias {resp_update['Name']} to version "
            f"{resp_update['FunctionVersion']}",
        )
        return resp_update
    logger.info(f'Alias {alias} does not exists. Create it.')
    try:
        resp_create = CLIENT.create_alias(
            FunctionName=func_name,
            Name=alias,
            FunctionVersion=version,
            Description=f'For use in the {alias} environment',
        )
    except Exception as err2:
        raise RuntimeError(f'Unable to create new alias: {alias}') from err2
    logger.info(
        f"Created alias {resp_create['Name']} to version "
        f"{resp_create['FunctionVersion']}",
    )
    return resp_create


def clean_up(env_vars_dev: Dict, func_name: str) -> None:
    """Clean up the whole process of publishing a lambda version to an alias.

    The procedure requires that the lambda environment variable to be first
    updated to the non-test condition and then proceed with the publish. This
    means after the publish completes, the $LATEST lambda function remains at
    the non-test condition. This is not what we want. We want to keep the
    default $LATEST lambda version at the test condition. Therefore, we use
    this clean_up function to reset the environment variables to the test
    condition.

    :param env_vars_dev: Environment variables for the dev version of Lambda
        function
    :param func_name: Name of the lambda function.
    """
    update_env_variables(env_vars_dev, func_name)


def read_config(config_file_path: Path) -> Dict[str, Dict]:
    """Read the config JSON file and return it as a Dict.

    :param config_file_path: The path to the config file
    :type config_file_path: Path
    :return: The config as a Dict
    :rtype: Dict[str, Dict]
    """
    try:
        with open(config_file_path, 'r') as f_obj:
            func_config = json.load(f_obj)
    except FileNotFoundError as err_config:
        exception_handler(
            f'Must provide {config_file_path} file',
            err_config,
            {},
            args.func_name,
        )
    return func_config


def publish_to_alias(
    func_config: Dict, func_name: str, description: str, alias: str,
) -> None:
    """The one-stop shop for all steps involved in publishing to an alias.

    :param func_config: configuration of the function under the current target
        alias
    :type func_config: Dict
    :param func_name: function name
    :type func_name: str
    :param description: description of the function specific to alias. It can
        be different from the function description.
    :type description: str
    :param alias: the alias to publish to
    :type alias: str
    """
    # make sure the function is ready to be updated before proceeding
    wait_for_update_successful(func_name, logger)
    # Publish new version and assign args.alias to it
    update_env_variables(
        func_config['vars'],
        func_name,
    )
    resp_func_state = wait_for_update_successful(func_name, logger)
    resp_publish_version = publish_version(
        func_name,
        description,
        resp_func_state['CodeSha256'],
        resp_func_state['RevisionId'],
    )
    resp_func_state = wait_for_update_successful(func_name, logger)
    assign_alias(
        alias,
        func_name,
        resp_publish_version['Version'],
    )


if __name__ == '__main__':
    # Parse command line arguments
    parser: ArgumentParser = get_argument_parser()
    args = parser.parse_args()

    if args.alias == 'dev':
        logger.error('\033[30;41mUsing "dev" as alias is forbidden.\033[0m')
        sys.exit(1)

    logger.info(
        f'\033[30;43mPublishing {args.func_name} to alias prod...\033[0m',
    )

    func_config_dev = read_config(
        ROOT_DIR.joinpath(f'{args.func_folder_path}/config.dev.json'),
    )
    func_config_alias = read_config(
        ROOT_DIR.joinpath(f'{args.func_folder_path}/config.{args.alias}.json'),
    )

    publish_to_alias(
        func_config_alias, args.func_name, args.description, args.alias,
    )
    wait_for_update_successful(args.func_name, logger)
    clean_up(func_config_dev['vars'], args.func_name)

    logger.info(f'\033[30;42mPublish {args.func_name} SUCCESS!\033[0m')
