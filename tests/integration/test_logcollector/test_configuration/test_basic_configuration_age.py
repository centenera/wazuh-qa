'''
copyright: Copyright (C) 2015-2022, Wazuh Inc.

           Created by Wazuh, Inc. <info@wazuh.com>.

           This program is free software; you can redistribute it and/or modify it under the terms of GPLv2

type: integration

brief: The 'wazuh-logcollector' daemon monitors configured files and commands for new log messages.
       Specifically, these tests will check if the logcollector detects invalid values for the 'age'
       tag and the Wazuh API returns the same values for the configured 'localfile' section.
       Log data collection is the real-time process of making sense out of the records generated by
       servers or devices. This component can receive logs through text files or Windows event logs.
       It can also directly receive logs via remote syslog which is useful for firewalls and
       other such devices.

components:
    - logcollector

suite: configuration

targets:
    - agent
    - manager

daemons:
    - wazuh-logcollector
    - wazuh-apid

os_platform:
    - linux
    - windows

os_version:
    - Arch Linux
    - Amazon Linux 2
    - Amazon Linux 1
    - CentOS 8
    - CentOS 7
    - Debian Buster
    - Red Hat 8
    - Ubuntu Focal
    - Ubuntu Bionic
    - Windows 10
    - Windows Server 2019
    - Windows Server 2016
references:
    - https://documentation.wazuh.com/current/user-manual/capabilities/log-data-collection/index.html
    - https://documentation.wazuh.com/current/user-manual/reference/ossec-conf/localfile.html#age

tags:
    - logcollector_configuration
'''
import os
import sys
import pytest

import wazuh_testing.api as api
from wazuh_testing.tools.configuration import load_configuration_template, get_test_cases_data
from wazuh_testing.tools import get_service
from wazuh_testing.modules.logcollector import LOG_COLLECTOR_PREFIX, WINDOWS_AGENT_PREFIX, \
                                               GENERIC_CALLBACK_ERROR_ANALYZING_FILE
from wazuh_testing.modules.logcollector import event_monitor as evm
from wazuh_testing.tools import LOG_FILE_PATH
from wazuh_testing.tools.file import truncate_file
from wazuh_testing.tools.services import control_service
from wazuh_testing.processes import check_if_daemons_are_running


LOGCOLLECTOR_DAEMON = "wazuh-logcollector"

# Marks
pytestmark = pytest.mark.tier(level=0)

prefix = LOG_COLLECTOR_PREFIX
location = '/tmp/testing.txt'

# Reference paths
TEST_DATA_PATH = os.path.join(os.path.dirname(os.path.realpath(__file__)), 'data')
CONFIGURATIONS_PATH = os.path.join(TEST_DATA_PATH, 'configuration_template')
TEST_CASES_PATH = os.path.join(TEST_DATA_PATH, 'test_cases')

# ------------------------------------------------ TEST_ACCEPTED_VALUES ------------------------------------------------
# Configuration and cases data
t1_configurations_path = os.path.join(CONFIGURATIONS_PATH, 'configuration_age.yaml')
t1_cases_path = os.path.join(TEST_CASES_PATH, 'cases_age.yaml')
wazuh_component = get_service()

# Accepted values test configurations (t1)
t1_configuration_parameters, t1_configuration_metadata, t1_case_ids = get_test_cases_data(t1_cases_path)

if sys.platform == 'win32':
    location = r'C:\testing\file.txt'
    prefix = WINDOWS_AGENT_PREFIX

for index in range(len(t1_configuration_metadata)):
    t1_configuration_metadata[index]['location'] = location
    t1_configuration_parameters[index]['LOCATION'] = location

t1_configurations = load_configuration_template(t1_configurations_path, t1_configuration_parameters,
                                                t1_configuration_metadata)

problematic_values = ['44sTesting', '9hTesting', '400mTesting', '3992']


def check_configuration_age_valid(metadata):
    """Check if the Wazuh module runs correctly and analyze the desired file.

    Ensure logcollector is running with the specified configuration, analyzing the designated file and,
    in the case of the Wazuh server, check if the API answer for localfile configuration block coincides
    the selected configuration.

    Args:
        metadata (dict): Dictionary with the localfile configuration.

    Raises:
        TimeoutError: If the "Analyzing file" callback is not generated.
        AssertError: In the case of a server instance, the API response is different from real configuration.
    """
    error_message = GENERIC_CALLBACK_ERROR_ANALYZING_FILE

    evm.check_analyzing_file(file=metadata['location'], error_message=error_message, prefix=prefix)

    if wazuh_component == 'wazuh-manager':
        real_configuration = metadata.copy()
        real_configuration.pop('name')
        real_configuration.pop('description')
        real_configuration.pop('valid_value')
        api.wait_until_api_ready()
        api.compare_config_api_response([real_configuration], 'localfile')


@pytest.mark.filterwarnings('ignore::urllib3.exceptions.InsecureRequestWarning')
@pytest.mark.parametrize('configuration, metadata', zip(t1_configurations, t1_configuration_metadata), ids=t1_case_ids)
def test_configuration_age(configuration, metadata, restart_wazuh_daemon_after_finishing_function,
                           set_wazuh_configuration):
    '''
    description: Check if the 'wazuh-logcollector' daemon detects invalid configurations for the 'age' tag.
                 For this purpose, the test will set a 'localfile' section using valid/invalid values for that
                 tag. Then, it will check if the 'analyzing' event is triggered when using a valid value, or
                 if an error event is generated when using an invalid one. Finally, the test will verify that
                 the Wazuh API returns the same values for the 'localfile' section that the configured one.

    wazuh_min_version: 4.2.0

    tier: 0

    parameters:
        - configuration:
            type: dict
            brief: Get configurations from the module.
        - metadata:
            type: dict
            brief: Get metadata from the module.
        - restart_wazuh_daemon_after_finishing_function:
            type: fixture
            brief: Restart the wazuh service in tierdown stage.
        - set_wazuh_configuration:
            type: fixture
            brief: Apply changes to the ossec.conf configuration.

    assertions:
        - Verify that the logcollector generates error events when using invalid values for the 'age' tag.
        - Verify that the logcollector generates 'analyzing' events when using valid values for the 'age' tag.
        - Verify that the Wazuh API returns the same values for the 'localfile' section as the configured one.
        - Verify that the wazuh-logcollector daemon is not running when using invalid values for the 'age' tag.

    input_description: A configuration template (test_basic_configuration_age) is contained in an external YAML file
                       (configuration_age.yaml). That template is combined with different test cases defined
                       in the cases_age.yaml file.

    expected_output:
        - r'Analyzing file.*'
        - r'Invalid .* for localfile'
        - r'Configuration error at .*'

    tags:
        - invalid_settings
    '''
    control_service('stop')
    truncate_file(LOG_FILE_PATH)

    if metadata['valid_value']:
        control_service('start')
        check_configuration_age_valid(metadata)
    else:
        if metadata['age'] in problematic_values:
            pytest.xfail("Logcollector accepts invalid values: https://github.com/wazuh/wazuh/issues/8158")
        else:
            if sys.platform == 'win32':
                pytest.xfail("Windows agent allows invalid localfile configuration:\
                              https://github.com/wazuh/wazuh/issues/10890")
            else:
                try:
                    control_service('start')
                except ValueError:
                    evm.check_configuration_error()
                    # Check that wazuh-logcollector is not running
                    assert not check_if_daemons_are_running(['wazuh-logcollector'])[0], 'wazuh-logcollector is ' \
                                                                                         'running and was not ' \
                                                                                         'expected to'
