import json
import os
import re
import shutil
import tempfile
from typing import Union

import pytest
from bandit.core import config as b_config, manager as b_manager
from git import Repo

TEST_PYTHON_CODE_PATH = os.path.dirname(__file__)
KNOWN_FLAWS_DIRECTORY = os.path.join(TEST_PYTHON_CODE_PATH, 'known_flaws')

DIRECTORIES_TO_EXCLUDE = ['tests', 'test']
DIRECTORIES_TO_CHECK = ['wodles', 'framework', 'api']
CONFIDENCE_LEVEL = 'MEDIUM'
SEVERITY_LEVEL = 'LOW'


def run_bandit_scan(directory_to_check: str, directories_to_exclude: Union[list, None] = None,
                    severity_level: str = SEVERITY_LEVEL, confidence_level: str = CONFIDENCE_LEVEL):
    """Run Bandit scan in a specified directory. The directories to exclude, minimum severity and confidence level can
    also be specified.

    Args:
        directory_to_check (str): Directory where Bandit will run the scan (recursively).
        directories_to_exclude (Union[list, None]): List containing the directories that will be excluded in the Bandit
            scan.
        severity_level (str): Minimum severity level taken into account in the Bandit scan.
        confidence_level (str): Minimum confidence level taken into account in the Bandit scan.
        confidence_level (str): Minimum confidence level taken into account in the Bandit scan.

    Returns:
        dict: Dictionary with the Bandit scan output.
    """
    if not directories_to_exclude:
        directories_to_exclude = DIRECTORIES_TO_EXCLUDE

    # Run Bandit to check possible security flaws
    b_mgr = b_manager.BanditManager(b_config.BanditConfig(),  # default config options object
                                    None)  # aggregation type
    b_mgr.discover_files([directory_to_check],  # list of targets
                         True,  # recursive
                         ",".join(directories_to_exclude))  # excluded paths
    b_mgr.run_tests()

    # Trigger output of results by Bandit Manager
    _, filename = tempfile.mkstemp(suffix='.json')
    b_mgr.output_results(None,  # context lines
                         severity_level,  # minimum severity level
                         confidence_level,  # minimum confidence level
                         open(filename, mode='w'),  # output file object
                         'json',  # output format
                         None)  # msg template

    # Read the temporary file with the Bandit result and remove it
    with open(filename, mode="r") as f:
        bandit_output = json.load(f)
    os.remove(filename)

    return bandit_output


def update_known_flaws(known_flaws: dict, results: list) -> dict:
    """Compare the Bandit results of the run with the already known flaws. Update the known flaws with the new line
    numbers and remove the known flaws that don't appear in the run results (were fixed).

    Args:
        known_flaws (dict): Dictionary containing already known vulnerabilities or false positives detected by Bandit.
        results (list): List containing all the possible flaws obtained in the Bandit run.

    Returns:
        dict: Updated known flaws.
    """
    updated_known_flaws = {k: None for k in known_flaws.keys()}
    for key in known_flaws.keys():
        for i in range(len(known_flaws[key])):
            next_flaw = next((flaw for flaw in results
                              if (flaw['code'] == known_flaws[key][i]['code']
                                  and flaw['filename'] == known_flaws[key][i]['filename']
                                  and flaw['test_id'] == known_flaws[key][i]['test_id'])), {})
            if next_flaw:
                known_flaws[key][i] = next_flaw
            else:
                known_flaws[key][i] = None
        updated_known_flaws[key] = [flaw for flaw in known_flaws[key] if flaw]

    return updated_known_flaws


@pytest.fixture(scope='session', autouse=True)
def clone_wazuh_repository(pytestconfig):
    """Fixture that clones a Wazuh repository in a temporary directory and checkout to the branch given by parameter.
    Remove the temporary directory once the test session using this fixture has finished.

    Args:
        pytestconfig (fixture): Session-scoped fixture that returns the :class:`_pytest.config.Config` object.

    Yields:
        Union[str, None]: The temporary directory name or None if the clone or checkout actions were not successful.
    """
    # Get Wazuh branch
    branch = pytestconfig.getoption('branch')

    # Create temporary dir
    t = tempfile.mkdtemp()

    try:
        # Clone into temporary dir
        repo = Repo.clone_from("https://github.com/wazuh/wazuh.git", t)
        # Checkout to given branch
        repo.git.checkout(branch)
        yield t
    except:
        yield None

    # Remove the temporary directory when the test ends
    shutil.rmtree(t)


@pytest.mark.parametrize("directory_to_check", DIRECTORIES_TO_CHECK)
def test_check_security_flaws(clone_wazuh_repository, directory_to_check: str):
    """Test whether the directory to check has python files with possible vulnerabilities or not.

    The test passes if there are no new vulnerabilities. The test fails in other case and generates a report.

    In case there is at least one vulnerability, a json file will be generated with the report. If we consider this
    result or results are false positives, we will move the json object containing each specific result to the
    `known_flaws/known_flaws_{framework|api|wodles}.json` file.

    Args:
        clone_wazuh_repository (fixture): Pytest fixture returning the path of the temporary directory path the
            repository cloned. This directory is removed at the end of the pytest session.
        directory_to_check (str): Directory containing the Python files where we want to look for vulnerabilities.
    """
    # Wazuh is cloned from GitHub using the clone_wazuh_repository fixture
    assert clone_wazuh_repository, "Error while cloning the Wazuh repository from GitHub, " \
                                   "please check the Wazuh branch set in the parameter."

    # Run Bandit scan
    bandit_output = run_bandit_scan(f"{clone_wazuh_repository}/{directory_to_check}")
    assert not bandit_output['errors'], \
        f"\nBandit returned errors when trying to get possible vulnerabilities:\n{bandit_output['errors']}"

    # We save the results obtained in the report as the rest of information is redundant or not used
    results = bandit_output['results']

    # Delete filenames to make it persistent with tmp directories
    for result in results:
        result['filename'] = "/".join(result['filename'].split('/')[3:])

    # Delete line numbers in code to make it persistent with updates
    for result in results:
        result['code'] = re.sub(r"^\d+", "", result['code'])  # Delete first line number
        result['code'] = re.sub(r"\n\d+", "\n", result['code'], re.M)  # Delete line numbers after newline

    # Compare the flaws obtained in results with the known flaws
    try:
        with open(f"{KNOWN_FLAWS_DIRECTORY}/known_flaws_{directory_to_check}.json", mode="r") as f:
            known_flaws = json.load(f)
    except json.decoder.JSONDecodeError:
        known_flaws = {'false_positives': [], 'to_fix': []}

    # There are security flaws if there are new possible vulnerabilities detected
    # To compare them, we cannot compare the whole dictionaries containing the flaws as the values of keys like
    # line_number and line_range will vary
    # Update known flaws with the ones detected in this Bandit run, remove them if they were fixed
    known_flaws = update_known_flaws(known_flaws, results)
    with open(f"{KNOWN_FLAWS_DIRECTORY}/known_flaws_{directory_to_check}.json", mode="w") as f:
        f.write(json.dumps(known_flaws, indent=4, sort_keys=True))

    new_flaws = [flaw for flaw in results if
                 flaw not in known_flaws['to_fix'] and flaw not in known_flaws['false_positives']]
    if new_flaws:
        # Write new flaws in a temporal file to analyze them
        new_flaws_path = os.path.join(TEST_PYTHON_CODE_PATH, f"new_flaws_{directory_to_check}.json")
        with open(new_flaws_path, mode="w") as f:
            f.write(json.dumps({'new_flaws': new_flaws}, indent=4, sort_keys=True))
        files_with_flaws = ', '.join(list(dict.fromkeys([res['filename'] for res in new_flaws])))
        assert False, f"\nVulnerabilities found in files:\n{files_with_flaws}" \
                      f"\nCheck them in {new_flaws_path}"
