'''
copyright: Copyright (C) 2015-2022, Wazuh Inc.
           Created by Wazuh, Inc. <info@wazuh.com>.
           This program is free software; you can redistribute it and/or modify it under the terms of GPLv2
'''


import pytest

from wazuh_testing.tools import LOG_FILE_PATH
from wazuh_testing.tools.monitoring import FileMonitor, callback_generator
from wazuh_testing.modules import analysisd
from wazuh_testing.modules.analysisd.event_monitor import check_analysisd_event
from wazuh_testing.modules import integratord as integrator
from wazuh_testing.modules.integratord.event_monitor import check_integratord_event


@pytest.fixture(scope='function')
def wait_for_start_module(request):
    # Wait for integratord thread to start
    file_monitor = FileMonitor(LOG_FILE_PATH)
    check_integratord_event(file_monitor=file_monitor, timeout=20,
                            callback=callback_generator(integrator.CB_INTEGRATORD_THREAD_READY),
                            error_message=integrator.ERR_MSG_VIRUST_TOTAL_ENABLED_NOT_FOUND)
    # Wait for analysisd to start successfully (to detect changes in the alerts.json file)
    check_analysisd_event(file_monitor=file_monitor, timeout=5,
                          callback=callback_generator(analysisd.CB_ANALYSISD_STARTUP_COMPLETED),
                          error_message=analysisd.ERR_MSG_STARTUP_COMPLETED_NOT_FOUND)
