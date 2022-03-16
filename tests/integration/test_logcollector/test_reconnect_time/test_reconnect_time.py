'''
copyright: Copyright (C) 2015-2022, Wazuh Inc.

           Created by Wazuh, Inc. <info@wazuh.com>.

           This program is free software; you can redistribute it and/or modify it under the terms of GPLv2

type: integration

brief: The 'wazuh-logcollector' daemon monitors configured files and commands for new log messages.
       Specifically, these tests will check if the logcollector uses the interval of reconnection
       attempts when the Windows Event Channel service is down, defined in the 'reconnect_time' tag.
       Log data collection is the real-time process of making sense out of the records generated by
       servers or devices. This component can receive logs through text files or Windows event logs.
       It can also directly receive logs via remote syslog which is useful for firewalls and
       other such devices.

components:
    - logcollector

suite: reconnect_time

targets:
    - agent

daemons:
    - wazuh-logcollector

os_platform:
    - windows

os_version:
    - Windows 10
    - Windows Server 2019
    - Windows Server 2016

references:
    - https://documentation.wazuh.com/current/user-manual/capabilities/log-data-collection/index.html
    - https://documentation.wazuh.com/current/user-manual/reference/ossec-conf/localfile.html#reconnect-time

tags:
    - logcollector_reconnect_time
'''
import os
import pytest
from datetime import timedelta, datetime
import time
import sys
from wazuh_testing.tools.configuration import load_wazuh_configurations
from wazuh_testing import global_parameters
from wazuh_testing.tools.logging import TestLogger
from wazuh_testing.tools.time import TimeMachine
import wazuh_testing.logcollector as logcollector
from wazuh_testing.tools.time import time_to_seconds
import wazuh_testing.tools.services as services

pytestmark = [pytest.mark.win32, pytest.mark.tier(level=0)]

local_internal_options = {
    'logcollector.remote_commands': 1,
    'logcollector.debug': 2,
    'monitord.rotate_log': 0,
    'windows.debug': '2'
}

# Configuration
test_data_path = os.path.join(os.path.dirname(os.path.realpath(__file__)), 'data')
configurations_path = os.path.join(test_data_path, 'wazuh_reconnect_time.yaml')

timeout_callback_reconnect_time = 30
timeout_eventlog_read = 5
elapsed_time_after_eventlog_stop = 1

parameters = [
    {'LOCATION': 'Application', 'LOG_FORMAT': 'eventchannel', 'RECONNECT_TIME': '5s'},
    {'LOCATION': 'Security', 'LOG_FORMAT': 'eventchannel', 'RECONNECT_TIME': '5s'},
    {'LOCATION': 'System', 'LOG_FORMAT': 'eventchannel', 'RECONNECT_TIME': '5s'},
    {'LOCATION': 'Application', 'LOG_FORMAT': 'eventchannel', 'RECONNECT_TIME': '40m'},
    {'LOCATION': 'Security', 'LOG_FORMAT': 'eventchannel', 'RECONNECT_TIME': '40m'},
    {'LOCATION': 'System', 'LOG_FORMAT': 'eventchannel', 'RECONNECT_TIME': '40m'},
    {'LOCATION': 'Application', 'LOG_FORMAT': 'eventchannel', 'RECONNECT_TIME': '20h'},
    {'LOCATION': 'Security', 'LOG_FORMAT': 'eventchannel', 'RECONNECT_TIME': '20h'},
    {'LOCATION': 'System', 'LOG_FORMAT': 'eventchannel', 'RECONNECT_TIME': '20h'},

]
metadata = [
    {'location': 'Application', 'log_format': 'eventchannel', 'reconnect_time': '5s'},
    {'location': 'Security', 'log_format': 'eventchannel', 'reconnect_time': '5s'},
    {'location': 'System', 'log_format': 'eventchannel', 'reconnect_time': '5s'},
    {'location': 'Application', 'log_format': 'eventchannel', 'reconnect_time': '40m'},
    {'location': 'Security', 'log_format': 'eventchannel', 'reconnect_time': '40m'},
    {'location': 'System', 'log_format': 'eventchannel', 'reconnect_time': '40m'},
    {'location': 'Application', 'log_format': 'eventchannel', 'reconnect_time': '20h'},
    {'location': 'Security', 'log_format': 'eventchannel', 'reconnect_time': '20h'},
    {'location': 'System', 'log_format': 'eventchannel', 'reconnect_time': '20h'},
]
configurations = load_wazuh_configurations(configurations_path, __name__,
                                           params=parameters,
                                           metadata=metadata)
configuration_ids = [f"{x['location']}_{x['log_format']}_{x['reconnect_time']}" for x in metadata]


@pytest.fixture(scope="module", params=configurations, ids=configuration_ids)
def get_configuration(request):
    """Get configurations from the module."""
    return request.param


@pytest.fixture(scope="module")
def get_local_internal_options():
    """Get configurations from the module."""
    return local_internal_options


@pytest.fixture(scope="module")
def start_eventlog_process(get_configuration):
    services.control_event_log_service('start')


def test_reconnect_time(start_eventlog_process, get_local_internal_options, configure_local_internal_options, get_configuration,
                        configure_environment, restart_monitord, file_monitoring, restart_logcollector):
    '''
    description: Check if the 'wazuh-logcollector' daemon uses the interval of reconnection attempts when
                 the Windows Event Channel service is down. That interval is set in the 'reconnect_time' tag.
                 For this purpose, the test will configure a 'localfile' section to monitor a windows 'event
                 log', and once the logcollector is started, it will verify that the 'event log' is being
                 monitored by detecting the event that indicates it. Then, the test will stop the event
                 channel service and wait for the event that indicates that the 'event log' is unavailable.
                 After this, it will verify that the 'trying to reconnect' event includes the time set in
                 the 'reconnect_time' tag and start the event channel service again. Finally, the test
                 will verify that the event indicating the successful reconnection to the 'event log'
                 is generated in the time set by the 'reconnect_time' tag.

    wazuh_min_version: 4.2.0

    tier: 0

    parameters:
        - get_local_internal_options:
            type: fixture
            brief: Get local internal options from the module.
        - configure_local_internal_options:
            type: fixture
            brief: Configure the Wazuh local internal options.
        - get_configuration:
            type: fixture
            brief: Get configurations from the module.
        - configure_environment:
            type: fixture
            brief: Configure a custom environment for testing.
        - restart_monitord:
            type: fixture
            brief: Reset the log file and start a new monitor.
        - file_monitoring:
            type: fixture
            brief: Handle the monitoring of a specified file.
        - restart_logcollector:
            type: fixture
            brief: Clear the 'ossec.log' file and start a new monitor.

    assertions:
        - Verify that the logcollector starts monitoring an 'event log'.
        - Verify that the logcollector detects when the 'event channel' service is down generating an event.
        - Verify that the logcollector tries to reconnect to an unavailable 'even log'
          using the time specified in the 'reconnect_time' tag.
        - Verify that the logcollector generates an event when successfully reconnects to an 'event log'.

    input_description: A configuration template (test_reconnect_time) is contained in an external YAML file
                       (wazuh_reconnect_time.yaml). That template is combined with different test cases
                       defined in the module. Those include configuration settings
                       for the 'wazuh-logcollector' daemon.

    expected_output:
        - r'Analyzing event log.*'
        - r'The eventlog service is down. Unable to collect logs from .* channel.'
        - r'Trying to reconnect .* channel in .* seconds.'
        - r'.* channel has been reconnected succesfully.'

    tags:
        - logs
        - time_travel
    '''
    config = get_configuration['metadata']

    if time_to_seconds(config['reconnect_time']) >= timeout_callback_reconnect_time:
        pytest.xfail("Expected fail: https://github.com/wazuh/wazuh/issues/8580")

    log_callback = logcollector.callback_eventchannel_analyzing(config['location'])
    wazuh_log_monitor.start(timeout=global_parameters.default_timeout, callback=log_callback,
                            error_message=logcollector.GENERIC_CALLBACK_ERROR_ANALYZING_EVENTCHANNEL)

    time.sleep(timeout_eventlog_read)
    
    services.control_event_log_service('stop')

    log_callback = logcollector.callback_event_log_service_down(config['location'])
    wazuh_log_monitor.start(timeout=logcollector.LOG_COLLECTOR_GLOBAL_TIMEOUT, callback=log_callback,
                            error_message=logcollector.GENERIC_CALLBACK_ERROR_ANALYZING_EVENTCHANNEL)

    log_callback = logcollector.callback_trying_to_reconnect(config['location'],
                                                             time_to_seconds(config['reconnect_time']))
    wazuh_log_monitor.start(timeout=logcollector.LOG_COLLECTOR_GLOBAL_TIMEOUT, callback=log_callback,
                            error_message=logcollector.GENERIC_CALLBACK_ERROR_ANALYZING_EVENTCHANNEL)

    services.control_event_log_service('start')
    time.sleep(elapsed_time_after_eventlog_stop)

    if time_to_seconds(config['reconnect_time']) >= timeout_callback_reconnect_time:
        before = str(datetime.now())
        seconds_to_travel = time_to_seconds(config['reconnect_time']) / 2
        TimeMachine.travel_to_future(timedelta(seconds=seconds_to_travel))
        TestLogger.VVV(f"Changing the system clock from {before} to {datetime.now()}")

    log_callback = logcollector.callback_reconnect_eventchannel(config['location'])

    before = str(datetime.now())

    if time_to_seconds(config['reconnect_time']) >= timeout_callback_reconnect_time:
        TimeMachine.travel_to_future(timedelta(seconds=(seconds_to_travel)))
        TestLogger.VVV(f"Changing the system clock from {before} to {datetime.now()}")

    wazuh_log_monitor.start(timeout=logcollector.LOG_COLLECTOR_GLOBAL_TIMEOUT, callback=log_callback,
                            error_message=logcollector.GENERIC_CALLBACK_ERROR_COMMAND_MONITORING)

    TimeMachine.time_rollback()
