# coding: utf-8
import sys
from pathlib import Path

import boto3

# CONSTANT
CLIENT = boto3.client('lambda')
ROOT_DIR: Path = Path(__file__).parent.parent.absolute()
PYTHON_VERSION: str = (
    f'python{sys.version_info[0]}.{sys.version_info[1]}'
)
FUNCTION_TEMP: Path = ROOT_DIR.joinpath('temp')
FUNCTION_ZIP: str = 'function.zip'
LAYER_TEMP: Path = ROOT_DIR.joinpath('python')
LAYER_ZIP: str = 'layer.zip'
