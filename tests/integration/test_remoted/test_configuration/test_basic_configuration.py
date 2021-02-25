# Copyright (C) 2015-2021, Wazuh Inc.
# Created by Wazuh, Inc. <info@wazuh.com>.
# This program is free software; you can redistribute it and/or modify it under the terms of GPLv2

import os
import pytest
import wazuh_testing.api as api

from wazuh_testing.remote import callback_detect_remoted_started
from wazuh_testing.tools.configuration import load_wazuh_configurations

# Marks
pytestmark = pytest.mark.tier(level=0)

# Configuration
test_data_path = os.path.join(os.path.dirname(os.path.realpath(__file__)), '')
configurations_path = os.path.join(test_data_path, 'data', 'wazuh_basic_configuration.yaml')

parameters = [
    {'PROTOCOL': 'UDP', 'CONNECTION': 'secure', 'PORT': '1514'},
    {'PROTOCOL': 'UDP', 'CONNECTION': 'syslog', 'PORT': '514'},
    {'PROTOCOL': 'TCP', 'CONNECTION': 'syslog', 'PORT': '514'},
    {'PROTOCOL': 'TCP', 'CONNECTION': 'secure', 'PORT': '1514'},
    {'PROTOCOL': 'UDP', 'CONNECTION': 'secure', 'PORT': '56660'},
    {'PROTOCOL': 'UDP', 'CONNECTION': 'syslog', 'PORT': '18000'},
    {'PROTOCOL': 'TCP', 'CONNECTION': 'syslog', 'PORT': '18000'},
    {'PROTOCOL': 'TCP', 'CONNECTION': 'secure', 'PORT': '56660'}
]

metadata = [
    {'protocol': 'UDP', 'connection': 'secure', 'port': '1514'},
    {'protocol': 'UDP', 'connection': 'syslog', 'port': '514'},
    {'protocol': 'TCP', 'connection': 'syslog', 'port': '514'},
    {'protocol': 'TCP', 'connection': 'secure', 'port': '1514'},
    {'protocol': 'UDP', 'connection': 'secure', 'port': '56660'},
    {'protocol': 'UDP', 'connection': 'syslog', 'port': '18000'},
    {'protocol': 'TCP', 'connection': 'syslog', 'port': '18000'},
    {'protocol': 'TCP', 'connection': 'secure', 'port': '56660'}
]

configurations = load_wazuh_configurations(configurations_path, __name__, params=parameters, metadata=metadata)
configuration_ids = [f"{x['PROTOCOL']}_{x['CONNECTION']}_{x['PORT']}" for x in parameters]


# fixtures
@pytest.fixture(scope="module", params=configurations, ids=configuration_ids)
def get_configuration(request):
    """Get configurations from the module."""
    return request.param


def test_connection(get_configuration, configure_environment, restart_remoted):
    """
    Checks that "connection" option could be configured as "secure" or "syslog" without errors
        this option specifies a type of incoming connection to accept: secure or syslog.

    Checks that the API answer for manager connection coincides with the option selected on ossec.conf
    """
    cfg = get_configuration['metadata']

    log_callback = callback_detect_remoted_started(port=cfg['port'], protocol=cfg['protocol'],
                                                   connection_type=cfg['connection'])

    wazuh_log_monitor.start(timeout=5, callback=log_callback, error_message="Wazuh remoted didn't start as expected.")

    # Check that API query return the selected configuration
    for field in cfg.keys():
        api_answer = api.get_manager_configuration(section="remote", field=field)
        assert cfg[field] == api_answer, "Wazuh API answer different from introduced configuration"
