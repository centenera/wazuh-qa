import subprocess
from pathlib import Path
from typing import Callable

from wazuh_testing import logger
from .constants import AWS_WODLE_PATH

AWS_MODULE_PATH = Path(AWS_WODLE_PATH, "aws-s3")


class OutputAnalysisError(Exception):
    pass


def call_aws_module(*parameters) -> str:
    """Given some parameters call the AWS module and return the output"""
    command = [AWS_MODULE_PATH, *parameters]
    logger.debug("Calling AWS module with: '%s'", command)
    command_result = subprocess.run(command, capture_output=True)

    return command_result.stdout.decode()

def _default_callback(line: str) -> str:
    print(line)
    return line

def analyze_command_output(
    command_output: str, callback: Callable=_default_callback, expected_results: int=1, error_message: str=''
):
        """Analyze the given command output searching for a patter"""

        results = []

        for line in command_output.splitlines():
            item = callback(line)

            if item is not None:
                results.append(item)

            if len(results) == expected_results:
                break

        results_len = len(results)

        if results_len != expected_results:
            if error_message:
                logger.error(error_message)
                logger.error("Results found: %s", results_len)
                logger.error("Results expected: %s", expected_results)
                raise OutputAnalysisError(error_message)
            raise OutputAnalysisError()
