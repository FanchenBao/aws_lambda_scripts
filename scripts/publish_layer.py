# coding: utf-8

import logging
import shlex
import subprocess
import sys
from argparse import ArgumentParser
from pathlib import Path
from shutil import make_archive, rmtree

from config import CLIENT, LAYER_TEMP, LAYER_ZIP, PYTHON_VERSION, ROOT_DIR

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
    rmtree(LAYER_TEMP)
    Path.unlink(ROOT_DIR.joinpath(LAYER_ZIP))


def get_argument_parser() -> ArgumentParser:  # pragma no cover
    """Set up a parser to parse command line arguments.

    :return: A fresh, unused, ArgumentParser.
    """
    parser = ArgumentParser(
        description=(
            'Publish a layer to AWS Lambda. A layer is a package that is '
            'shared and can be imported by all Lambda under the same account '
            'If the layer name never exists before, create a new one. If it '
            'already exists, update it to a new version. Note that layer name '
            'must be the same as package name'
            'Usage: python3 publish_layer --package_name [PACKAGE NAME]'
            '--description [DESC].'
        ),
    )
    parser.add_argument(
        '--package_name',
        dest='package_name',
        type=str,
        required=True,
        help=(
            'REQUIRED. Name of the package to be uploaded as a layer.'
        ),
    )
    parser.add_argument(
        '--description',
        dest='description',
        type=str,
        required=True,
        help=(
            'REQUIRED. Description of the latest version of the layer.'
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


def prep_files(package_name: str) -> None:
    """Prepare a folder to hold all the files/folders for the package.

    Follow the instruction from here:
    https://aws.amazon.com/premiumsupport/knowledge-center/lambda-import-module-error-python/

    However, one major difference is that we are doing this on our local
    machine, which might or might not be incompatible with Amazon Linux
    machines.

    :param package_name: Name of the package to be zipped up for upload as
        layer.
    """
    # prepare temp folder
    if Path.exists(LAYER_TEMP):  # clean up any previous upload
        rmtree(LAYER_TEMP)
    Path.mkdir(LAYER_TEMP, parents=True)
    subprocess.run(
        shlex.split(f'pip install -t {LAYER_TEMP} {package_name}'),
    )
    # create zip file
    make_archive(
        LAYER_ZIP.split('.')[0],
        'zip',
        root_dir=ROOT_DIR,
        base_dir=LAYER_TEMP.parts[-1],
    )


def publish_layer(layer_name: str, desc: str) -> None:
    """Upload lambda code base (as a zip file) to its associated AWS Lambda.

    :param layer_name: Name of the layer.
    :param desc: Description of the layer.
    :raises RuntimeError: Either update layer fails
    """
    with open(LAYER_ZIP, 'rb') as f_obj:  # upload
        zip_bytes = f_obj.read()
    try:
        resp = CLIENT.publish_layer_version(
            LayerName=layer_name,
            Description=desc,
            Content={'ZipFile': zip_bytes},
            CompatibleRuntimes=[PYTHON_VERSION],
        )
    except Exception as err:
        raise RuntimeError('Publish layer FAILED.') from err
    logger.info(resp)


if __name__ == '__main__':
    # Parse command line arguments
    parser: ArgumentParser = get_argument_parser()
    args = parser.parse_args()

    logger.info(
        f'\033[30;43mPublishing {args.package_name} layer...\033[0m',
    )
    try:
        prep_files(args.package_name)
    except Exception as err2:
        exception_handler('Failed to prepare files', err2)

    try:
        publish_layer(args.package_name, args.description)
    except Exception as err3:
        exception_handler('Failed to publish layer', err3)

    clean_up()
    logger.info(
        f'\033[30;42mPublish {args.package_name} layer SUCCESS!\033[0m',
    )
