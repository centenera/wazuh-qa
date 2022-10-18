'''
copyright: Copyright (C) 2015-2022, Wazuh Inc.
           Created by Wazuh, Inc. <info@wazuh.com>.
           This program is free software; you can redistribute it and/or modify it under the terms of GPLv2

type: integration

brief: The 'wazuh-logcollector' daemon monitors configured files and commands for new log messages.
       Specifically, these tests will check if commands with different characteristics are executed
       correctly by the logcollector. They will also check if the 'info' and 'debug' lines are
       written in the logs when running these commands.
       Log data collection is the real-time process of making sense out of the records generated by
       servers or devices. This component can receive logs through text files or Windows event logs.
       It can also directly receive logs via remote syslog which is useful for firewalls and
       other such devices.

components:
    - logcollector

suite: command_monitoring

targets:
    - agent
    - manager

daemons:
    - wazuh-logcollector

os_platform:
    - linux
    - macos
    - solaris

os_version:
    - Arch Linux
    - Amazon Linux 2
    - Amazon Linux 1
    - CentOS 8
    - CentOS 7
    - Debian Buster
    - Red Hat 8
    - Solaris 10
    - Solaris 11
    - macOS Catalina
    - macOS Server
    - Ubuntu Focal
    - Ubuntu Bionic

references:
    - https://documentation.wazuh.com/current/user-manual/capabilities/log-data-collection/index.html
    - https://documentation.wazuh.com/current/user-manual/reference/ossec-conf/localfile.html#command
    - https://documentation.wazuh.com/current/user-manual/reference/ossec-conf/localfile.html#alias
    - https://documentation.wazuh.com/current/user-manual/reference/ossec-conf/localfile.html#log-format

tags:
    - logcollector_cmd_exec
'''

import os
import pytest
import sys
from subprocess import check_output

from wazuh_testing import global_parameters
from wazuh_testing.modules.logcollector import LOG_COLLECTOR_PREFIX, GENERIC_CALLBACK_ERROR_COMMAND_MONITORING
from wazuh_testing.tools.configuration import load_configuration_template, get_test_cases_data
from wazuh_testing.modules.logcollector import event_monitor as evm


# Marks
pytestmark = [pytest.mark.linux, pytest.mark.darwin, pytest.mark.sunos5, pytest.mark.tier(level=0)]

prefix = LOG_COLLECTOR_PREFIX

# Reference paths
TEST_DATA_PATH = os.path.join(os.path.dirname(os.path.realpath(__file__)), 'data')
CONFIGURATIONS_PATH = os.path.join(TEST_DATA_PATH, 'configuration_template')
TEST_CASES_PATH = os.path.join(TEST_DATA_PATH, 'test_cases')

# ------------------------------------------------ TEST_ACCEPTED_VALUES ------------------------------------------------
# Configuration and cases data
t1_configurations_path = os.path.join(CONFIGURATIONS_PATH, 'configuration_execution_dbg.yaml')
t1_cases_path = os.path.join(TEST_CASES_PATH, 'cases_execution_dbg_linux_os.yaml')
t2_cases_path = os.path.join(TEST_CASES_PATH, 'cases_execution_dbg_non_linux_os.yaml')

local_internal_options = {
    'logcollector.remote_commands': '1',
    'logcollector.max_lines': '100',
    'logcollector.debug': '2',
    'monitord.rotate_log': '0'
}

# Accepted values test configurations (t1)
t1_configuration_parameters, t1_configuration_metadata, t1_case_ids = get_test_cases_data(t1_cases_path)
t1_configurations = load_configuration_template(t1_configurations_path, t1_configuration_parameters,
                                                t1_configuration_metadata)

# Accepted values test configurations (t2)
t2_configuration_parameters, t2_configuration_metadata, t2_case_ids = get_test_cases_data(t2_cases_path)
t2_configurations = load_configuration_template(t1_configurations_path, t2_configuration_parameters,
                                                t2_configuration_metadata)


def dbg_reading_command(command, alias, log_format):
    """Check if the (previously known) output of a command ("echo") is displayed correctly.

    It also checks if the "alias" option is working correctly.

    Args:
        command (str): Command to be monitored.
        alias (str): An alternate name for the command.
        log_format (str): Format of the log to be read ("command" or "full_command").

    Raises:
        TimeoutError: If the command monitoring callback is not generated.
    """
    internal_prefix = LOG_COLLECTOR_PREFIX
    output = check_output(command, universal_newlines=True, shell=True).strip()

    if log_format == 'full_command':
        msg = fr"^{output}'"
        internal_prefix = ''
    else:
        msg = fr"DEBUG: Reading command message: 'ossec: output: '{alias}': {output}'"

    evm.check_logcollector_event(timeout=global_parameters.default_timeout, callback=msg, prefix=internal_prefix,
                                 error_message=GENERIC_CALLBACK_ERROR_COMMAND_MONITORING)


def check_test_logs(log_monitor, metadata):
    """Check if the (previously known) output of a command ("echo") is displayed correctly.

    It also checks if the "alias" option is working correctly.

    Args:
        log_monitor (FileMonitor): File monitoring.
        metadata (dict): Get metadata from the module.

    Raises:
        TimeoutError: If the command monitoring callback is not generated.
    """
    # Check log line "DEBUG: Running command '<command>'"
    evm.check_running_command(file_monitor=log_monitor, log_format=metadata['log_format'], command=metadata['command'],
                              error_message=GENERIC_CALLBACK_ERROR_COMMAND_MONITORING, prefix=prefix,
                              timeout=global_parameters.default_timeout, escape=True)

    # Command with known output to test "Reading command message: ..."
    if metadata['command'].startswith('echo') and metadata['alias'] != '':
        dbg_reading_command(metadata['command'], metadata['alias'], metadata['log_format'])

    # "Read ... lines from command ..." only appears with log_format=command
    if metadata['log_format'] == 'command':
        evm.check_read_lines(file_monitor=log_monitor, command=metadata['command'],
                             error_message=GENERIC_CALLBACK_ERROR_COMMAND_MONITORING, prefix=prefix,
                             timeout=global_parameters.default_timeout, escape=True)


@pytest.mark.parametrize('configuration, metadata', zip(t1_configurations, t1_configuration_metadata), ids=t1_case_ids)
def test_command_execution_dbg_linux_os(configuration, metadata, set_wazuh_configuration,
                                        configure_local_internal_options_module, setup_log_monitor,
                                        restart_wazuh_daemon_function):
    '''
    description: Check if the 'wazuh-logcollector' daemon generates debug logs when running commands with
                 special characteristics. For this purpose, the test will configure the logcollector to run
                 a command, setting it in the 'command' tag and using the 'command' and 'full_command' log
                 formats. The properties of that command can be, for example, a non-existent command or one
                 that includes special characters. Once the logcollector has started, it will wait for the
                 'running' event that indicates that the command has been executed. Finally, the test
                 will verify that the debug 'read N lines' event is generated, this event indicates the number
                 of lines read from the command run. Depending on test case, the test also will verify that
                 the debug event 'reading command' is generated, this event includes the output of the command
                 run, and its alias if it is set in the 'alias' tag.

    wazuh_min_version: 4.2.0

    tier: 0

    parameters:
        - configuration:
            type: dict
            brief: Get configurations from the module.
        - metadata:
            type: dict
            brief: Get metadata from the module.
        - set_wazuh_configuration:
            type: fixture
            brief: Apply changes to the ossec.conf configuration.
        - configure_local_internal_options_module:
            type: fixture
            brief: Configure the Wazuh local internal options file.
        - setup_log_monitor:
            type: fixture
            brief: Create the log monitor.
        - restart_wazuh_daemon_function:
            type: fixture
            brief: Restart the wazuh service.

    assertions:
        - Verify that the debug 'running' event is generated when running the command set in the 'command' tag.
        - Verify that the debug 'reading command' event is generated when running the related command.
        - Verify that the debug 'lines' event is generated when running the related command.

    input_description: A configuration template (test_command_execution) is contained in an external
                       YAML file (configuration_execution_dbg.yaml), which includes configuration settings for
                       the 'wazuh-logcollector' daemon and, it is combined with the test cases
                       (log formats and commands to run) defined in the cases_execution_dbg_linux_os.yaml file.

    expected_output:
        - r'DEBUG: Running .*'
        - r'DEBUG: Reading command message.*'
        - r'lines from command .*'

    tags:
        - logs
    '''
    log_monitor = setup_log_monitor

    # Check logs in ossec.log
    check_test_logs(log_monitor, metadata)


@pytest.mark.parametrize('configuration, metadata', zip(t2_configurations, t2_configuration_metadata), ids=t2_case_ids)
def test_command_execution_dbg_non_linux_os(configuration, metadata, set_wazuh_configuration,
                                            configure_local_internal_options_module, setup_log_monitor,
                                            restart_wazuh_daemon_function):
    '''
    description: Check if the 'wazuh-logcollector' daemon generates debug logs when running commands with
                 special characteristics. For this purpose, the test will configure the logcollector to run
                 a command, setting it in the 'command' tag and using the 'command' and 'full_command' log
                 formats. The properties of that command can be, for example, a non-existent command or one
                 that includes special characters. Once the logcollector has started, it will wait for the
                 'running' event that indicates that the command has been executed. Finally, the test
                 will verify that the debug 'read N lines' event is generated, this event indicates the number
                 of lines read from the command run. Depending on test case, the test also will verify that
                 the debug event 'reading command' is generated, this event includes the output of the command
                 run, and its alias if it is set in the 'alias' tag.

    wazuh_min_version: 4.2.0

    tier: 0

    parameters:
        - configuration:
            type: dict
            brief: Get configurations from the module.
        - metadata:
            type: dict
            brief: Get metadata from the module.
        - set_wazuh_configuration:
            type: fixture
            brief: Apply changes to the ossec.conf configuration.
        - configure_local_internal_options_module:
            type: fixture
            brief: Configure the Wazuh local internal options file.
        - setup_log_monitor:
            type: fixture
            brief: Create the log monitor.
        - restart_wazuh_daemon_function:
            type: fixture
            brief: Restart the wazuh service.

    assertions:
        - Verify that the debug 'running' event is generated when running the command set in the 'command' tag.
        - Verify that the debug 'reading command' event is generated when running the related command.
        - Verify that the debug 'lines' event is generated when running the related command.

    input_description: A configuration template (test_command_execution) is contained in an external
                       YAML file (configuration_execution_dbg.yaml), which includes configuration settings for
                       the 'wazuh-logcollector' daemon and, it is combined with the test cases
                       (log formats and commands to run) defined in the cases_execution_dbg_non_linux_os.yaml file.

    expected_output:
        - r'DEBUG: Running .*'
        - r'DEBUG: Reading command message.*'
        - r'lines from command .*'

    tags:
        - logs
    '''
    log_monitor = setup_log_monitor

    # Check logs in ossec.log
    check_test_logs(log_monitor, metadata)
