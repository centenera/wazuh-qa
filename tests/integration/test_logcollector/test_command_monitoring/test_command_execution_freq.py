'''
copyright: Copyright (C) 2015-2022, Wazuh Inc.

           Created by Wazuh, Inc. <info@wazuh.com>.

           This program is free software; you can redistribute it and/or modify it under the terms of GPLv2

type: integration

brief: The 'wazuh-logcollector' daemon monitors configured files and commands for new log messages.
       Specifically, these tests will check if commands are executed at specific intervals set in
       the 'frequency' tag using the log formats 'command' and 'full_commnad'.
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
    - https://documentation.wazuh.com/current/user-manual/reference/ossec-conf/localfile.html#frequency

tags:
    - logcollector_cmd_exec
'''
import os
import sys
import subprocess
import pytest
from datetime import timedelta, datetime

from wazuh_testing import global_parameters, logger, T_30, T_60
from wazuh_testing.tools.time import TimeMachine
from wazuh_testing.modules.logcollector import LOG_COLLECTOR_PREFIX, WINDOWS_AGENT_PREFIX, \
                                               GENERIC_CALLBACK_ERROR_COMMAND_MONITORING
from wazuh_testing.tools.configuration import load_configuration_template, get_test_cases_data
from wazuh_testing.modules.logcollector import event_monitor as evm


# Marks
pytestmark = [pytest.mark.tier(level=0)]

prefix = LOG_COLLECTOR_PREFIX

# Reference paths
TEST_DATA_PATH = os.path.join(os.path.dirname(os.path.realpath(__file__)), 'data')
CONFIGURATIONS_PATH = os.path.join(TEST_DATA_PATH, 'configuration_template')
TEST_CASES_PATH = os.path.join(TEST_DATA_PATH, 'test_cases')

# ------------------------------------------------ TEST_ACCEPTED_VALUES ------------------------------------------------
# Configuration and cases data
t1_configurations_path = os.path.join(CONFIGURATIONS_PATH, 'configuration_execution_freq.yaml')
t1_cases_path = os.path.join(TEST_CASES_PATH, 'cases_execution_freq.yaml')

# Accepted values test configurations (t1)
t1_configuration_parameters, t1_configuration_metadata, t1_case_ids = get_test_cases_data(t1_cases_path)
t1_configurations = load_configuration_template(t1_configurations_path, t1_configuration_parameters,
                                                t1_configuration_metadata)

local_internal_options = {'logcollector.remote_commands': '1', 'logcollector.debug': '2', 'monitord.rotate_log': '0',
                          'windows.debug': '2'}

if sys.platform == 'win32':
    location = r'C:\testing\file.txt'
    prefix = WINDOWS_AGENT_PREFIX


@pytest.fixture(scope='module')
def change_date_format():
    """"Function to change format date to dd/mm/yy"""
    if sys.platform == 'win32':
        command = subprocess.run(["powershell.exe", "(Get-culture).DateTimeFormat.ShortDatePattern"],
                                 stdout=subprocess.PIPE)

        subprocess.call(['powershell.exe', 'Set-ItemProperty -Path "HKCU:\\Control Panel\\International" ' \
                         '-Name sShortDate -Value dd/MM/yy'])

        yield

        date_format = str(command.stdout).split('\'')[1].split('\\')[0]
        subprocess.call(['powershell.exe', 'Set-ItemProperty -Path \"HKCU:\\Control Panel\\International\" ' \
                         f"-Name sShortDate -Value {date_format}"])



@pytest.mark.parametrize('configuration, metadata', zip(t1_configurations, t1_configuration_metadata), ids=t1_case_ids)
def test_command_execution_freq(configuration, metadata, set_wazuh_configuration,
                                configure_local_internal_options_module, change_date_format, setup_log_monitor,
                                restart_wazuh_daemon_function):
    '''
    description: Check if the 'wazuh-logcollector' daemon runs commands at the specified interval, set in
                 the 'frequency' tag. For this purpose, the test will configure the logcollector to run
                 a command at specific intervals. Then it will travel in time up to the middle of the interval
                 set in the 'frequency' tag, and verify that the 'running' event is not been generated. That
                 confirms that the command is not executed. Finally, the test will travel in time again up to
                 the next interval and verify that the command is executed by detecting the 'running' event.

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
        - Verify that the logcollector runs commands at the interval set in the 'frequency' tag.
        - Verify that the logcollector does not run commands before the interval
          set in the 'frequency' tag expires.

    input_description: A configuration template (test_command_execution_freq) is contained in an external
                       YAML file (wazuh_command_conf.yaml), which includes configuration settings for
                       the 'wazuh-logcollector' daemon and, it is combined with the test cases
                       (log formats, frequencies, and commands to run) defined in the module.

    expected_output:
        - r'DEBUG: Running .*'

    tags:
        - logs
        - time_travel
    '''
    log_monitor = setup_log_monitor

    seconds_to_travel = metadata['frequency'] / 2  # Middle of the command execution cycle.

    evm.check_running_command(file_monitor=log_monitor, log_format=metadata['log_format'], command=metadata['command'],
                              error_message=GENERIC_CALLBACK_ERROR_COMMAND_MONITORING, prefix=prefix,
                              timeout=T_60)

    before = str(datetime.now())
    TimeMachine.travel_to_future(timedelta(seconds=seconds_to_travel))
    logger.debug(f"Changing the system clock from {before} to {datetime.now()}")

    # The command should not be executed in the middle of the command execution cycle.
    with pytest.raises(TimeoutError):
        evm.check_running_command(file_monitor=log_monitor,  log_format=metadata['log_format'],
                                  command=metadata['command'], error_message=GENERIC_CALLBACK_ERROR_COMMAND_MONITORING,
                                  prefix=prefix, timeout=global_parameters.default_timeout)

    before = str(datetime.now())
    TimeMachine.travel_to_future(timedelta(seconds=seconds_to_travel))
    logger.debug(f"Changing the system clock from {before} to {datetime.now()}")

    evm.check_running_command(file_monitor=log_monitor, log_format=metadata['log_format'], command=metadata['command'],
                              error_message=GENERIC_CALLBACK_ERROR_COMMAND_MONITORING, prefix=prefix,
                              timeout=T_30)

    # Restore the system clock.
    TimeMachine.time_rollback()
