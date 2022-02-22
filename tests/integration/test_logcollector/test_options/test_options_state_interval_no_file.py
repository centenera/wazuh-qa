"""
copyright: Copyright (C) 2015-2021, Wazuh Inc.

           Created by Wazuh, Inc. <info@wazuh.com>.

           This program is free software; you can redistribute it and/or modify it under the terms of GPLv2

type: integration

brief: The 'wazuh-logcollector' daemon monitors configured files and commands for new log messages.
       Specifically, these tests will check if the logcollector updates the 'wazuh-logcollector.state'
       file when a monitored log file is removed. Log data collection is the real-time process of
       making sense out of the records generated by servers or devices. This component can receive
       logs through text files or Windows event logs. It can also directly receive logs via
       remote syslog which is useful for firewalls and other such devices.

tier: 1

modules:
    - logcollector

components:
    - manager

daemons:
    - wazuh-logcollector

os_platform:
    - linux

os_version:
    - Arch Linux
    - Amazon Linux 2
    - Amazon Linux 1
    - CentOS 8
    - CentOS 7
    - CentOS 6
    - Ubuntu Focal
    - Ubuntu Bionic
    - Ubuntu Xenial
    - Ubuntu Trusty
    - Debian Buster
    - Debian Stretch
    - Debian Jessie
    - Debian Wheezy
    - Red Hat 8
    - Red Hat 7
    - Red Hat 6

references:
    - https://documentation.wazuh.com/current/user-manual/capabilities/log-data-collection/index.html
    - https://documentation.wazuh.com/current/user-manual/reference/ossec-conf/localfile.html
    - https://documentation.wazuh.com/current/user-manual/reference/statistics-files/wazuh-logcollector-state.html
    - https://documentation.wazuh.com/current/user-manual/reference/internal-options.html#logcollector

tags:
    - logcollector_options
"""

import os
from json import load
import tempfile

import pytest
import wazuh_testing.tools.configuration as conf
from wazuh_testing import logcollector
from wazuh_testing.tools.configuration import load_wazuh_configurations
from wazuh_testing.tools import LOGCOLLECTOR_STATISTICS_FILE
from wazuh_testing.tools import LOG_FILE_PATH
from wazuh_testing.tools.file import truncate_file
from wazuh_testing.tools.monitoring import FileMonitor
from wazuh_testing.tools.services import control_service

from time import sleep

# Marks
pytestmark = [pytest.mark.linux, pytest.mark.tier(level=1), pytest.mark.server]

# Configuration
test_data_path = os.path.join(os.path.dirname(os.path.realpath(__file__)), 'data', 'configuration')
configurations_path = os.path.join(test_data_path, 'wazuh_configuration.yaml')
daemons_handler_configuration = {'all_daemons': True}

temp_dir = tempfile.gettempdir()

file_structure = [
    {
        'folder_path': os.path.join(temp_dir, 'wazuh-testing'),
        'filename': ['test.txt'],
        'content': f'Content of testing_file\n'
    }
]

parameters = [
    {'LOCATION': os.path.join(temp_dir, 'wazuh-testing', 'test.txt'), 'LOG_FORMAT': 'syslog'},
    {'LOCATION': os.path.join(temp_dir, 'wazuh-testing', '*'), 'LOG_FORMAT': 'syslog'},

]

metadata = [
    {'location': os.path.join(temp_dir, 'wazuh-testing', 'test.txt'), 'log_format': 'syslog', 'regex': False},
    {'location': os.path.join(temp_dir, 'wazuh-testing', '*'), 'log_format': 'syslog', 'regex': True},
]

# Configuration data
configurations = load_wazuh_configurations(configurations_path, __name__, params=parameters, metadata=metadata)
configuration_ids = [f"{x['LOCATION']}_{x['LOG_FORMAT']}" for x in parameters]
local_options = [{'state_interval': '1', 'open_attempts': '1'},
                 {'state_interval': '4', 'open_attempts': '4'},
                 {'state_interval': '5', 'open_attempts': '10'}]

local_internal_options = {'logcollector.debug': '2'}


def check_wazuh_logcollector_status_file(file):
    with open(LOGCOLLECTOR_STATISTICS_FILE, 'r') as json_file:
        data = load(json_file)
    try:
        global_files = data['global']['files']
        interval_files = data['interval']['files']

        return (list(filter(lambda global_file: global_file['location'] == file, global_files)),
                list(filter(lambda interval_file: interval_file['location'] == file, interval_files)))
    except Exception:
        return (False, False)


# Fixtures
@pytest.fixture(scope="module", params=configurations, ids=configuration_ids)
def get_configuration(request):
    """Get configurations from the module."""
    return request.param


@pytest.fixture(scope="function")
def get_files_list():
    """Get file list to create from the module."""
    return file_structure


@pytest.fixture(scope="function", params=local_options)
def get_local_internal_options_function(request):
    """Get configurations from the module."""
    global local_internal_options
    local_internal_options = {'logcollector.open_attempts': request.param['open_attempts'],
                              'logcollector.state_interval': request.param['state_interval'],
                              'logcollector.vcheck_files': '3',
                              'logcollector.debug': '2'}


def test_options_state_interval_no_file(get_local_internal_options_function, configure_local_internal_options_function,
                                        get_files_list, create_file_structure_function, get_configuration,
                                        configure_environment, file_monitoring):
    """
    description: Check if the 'wazuh-logcollector' daemon updates the statistic file 'wazuh-logcollector.state'
                 when a monitored log file is removed. It also check the related internal options
                 'logcollector.open_attempts' and 'logcollector.state_interval'. For this purpose, the test
                  will create a testing log file and configure a 'localfile' section to monitor it. Once the
                 logcollector is started, it will check if the 'monitoring' event is triggered, indicating that
                 the logcollector starts to monitor the testing log file. Then, the test will verify that the
                 'wazuh-logcollector.state' file has been created and contains references to the monitored
                 log file. After this, it will remove the log file and check if the event that indicates that
                 action is generated. After removing the log file, the test will check if the number of attempts
                 to read it is correct (logcollector.open_attempts) and verify that the event indicating that
                 the log file is unavailable is generated. Finally, it will wait until the 'wazuh-logcollector.state'
                 file is updated and verify that it does not contain references to the removed log file.

    wazuh_min_version: 4.2.0

    parameters:
        - configure_local_internal_options_module:
            type: fixture
            brief: Set internal configuration for testing.
        - get_local_internal_options_function:
            type: fixture
            brief: Get local internal options from the module.
        - get_files_list:
            type: fixture
            brief: Get file list to create from the module.
        - create_file_structure_function:
            type: fixture
            brief: Create the specified file tree structure.
        - get_configuration:
            type: fixture
            brief: Get configurations from the module.
        - configure_environment:
            type: fixture
            brief: Configure a custom environment for testing.

    assertions:
        - Verify that the logcollector updates the 'wazuh-logcollector.state' file
          when a monitored log file is added or removed.
        - Verify that the 'logcollector.open_attempts' internal option works correctly.
        - Verify that the 'logcollector.state_interval' internal option works correctly.

    input_description: A configuration template (test_options) is contained in an external YAML file
                       (wazuh_configuration.yaml). That template is combined with different test cases
                       defined in the module. Those include configuration settings
                       for the 'wazuh-logcollector' daemon.

    expected_output:
        - r'Analyzing file.*'
        - r'File .* no longer exists.'
        - r'Unable to open file .*. Remaining attempts.*'
        - r'File not available, ignoring it.*'

    tags:
        - logs
    """
    control_service('restart')

    configuration = get_configuration['metadata']
    use_regex = configuration['regex']
    if not use_regex:
        pytest.xfail('Xfailing due to issue: https://github.com/wazuh/wazuh/issues/10783')

    location = configuration['location']

    interval = int(local_internal_options['logcollector.state_interval'])
    open_attempts = int(local_internal_options['logcollector.open_attempts'])
    logcollector_state_file_updated = False

    for file in get_files_list:
        for name in file['filename']:
            # Ensure file is analyzed
            log_path = os.path.join(file['folder_path'], name)
            with open(log_path, 'w') as log_file:
                log_file.write('Modifying the file\n')

            if use_regex:
                log_callback = logcollector.callback_match_pattern_file(location, log_path)
                log_monitor.start(timeout=logcollector.LOG_COLLECTOR_GLOBAL_TIMEOUT, callback=log_callback,
                                  error_message=logcollector.GENERIC_CALLBACK_ERROR_ANALYZING_FILE)
            else:
                log_callback = logcollector.callback_analyzing_file(log_path)
                log_monitor.start(timeout=logcollector.LOG_COLLECTOR_GLOBAL_TIMEOUT, callback=log_callback,
                                  error_message=logcollector.GENERIC_CALLBACK_ERROR_ANALYZING_FILE)

            # Ensure wazuh-logcollector.state is created
            elapsed_time_statistics_file = 10
            logcollector.wait_statistics_file(timeout=interval + elapsed_time_statistics_file)

            sleep(interval)

            assert all(check_wazuh_logcollector_status_file(log_path))

            os.remove(log_path)
            if use_regex:
                log_callback = logcollector.callback_removed_file(log_path)
                log_monitor.start(timeout=logcollector.LOG_COLLECTOR_GLOBAL_TIMEOUT, callback=log_callback,
                                  error_message="File no longer exists has not been generated")

            else:
                for n_attempts in range(open_attempts):
                    log_callback = logcollector.callback_unable_to_open(log_path, open_attempts - (n_attempts + 1))
                    log_monitor.start(timeout=logcollector.LOG_COLLECTOR_GLOBAL_TIMEOUT, callback=log_callback,
                                      error_message="Unable to open file callback has not been generated")

                log_callback = logcollector.callback_ignored_removed_file(log_path)
                log_monitor.start(timeout=logcollector.LOG_COLLECTOR_GLOBAL_TIMEOUT, callback=log_callback,
                                  error_message="File not available callback has not been generated")

            time_to_update_statistics_file = (interval if use_regex else interval*open_attempts) + 5

            sleep(time_to_update_statistics_file)

            if use_regex:
                assert not any(check_wazuh_logcollector_status_file(log_path)), f"Using regex as location, file \
                                                                                 {location} has not been deleted from \
                                                                                 {LOGCOLLECTOR_STATISTICS_FILE}"
            else:
                assert all(check_wazuh_logcollector_status_file(log_path)),  f"Using hardcoded location, file \
                                                                               {log_path} has been deleted \
                                                                               from {LOGCOLLECTOR_STATISTICS_FILE}"
