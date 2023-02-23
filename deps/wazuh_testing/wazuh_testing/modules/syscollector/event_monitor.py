'''
copyright: Copyright (C) 2015-2023, Wazuh Inc.
           Created by Wazuh, Inc. <info@wazuh.com>.
           This program is free software; you can redistribute it and/or modify it under the terms of GPLv2
'''
import sys

from wazuh_testing import T_5, T_10
from wazuh_testing.event_monitor import check_event
from wazuh_testing.modules import syscollector
from wazuh_testing.tools import LOG_FILE_PATH


def check_syscollector_event(file_monitor=None, callback='', error_message=None, update_position=True, timeout=T_10,
                             prefix=syscollector.SYSCOLLECTOR_PREFIX, accum_results=1, file_to_monitor=LOG_FILE_PATH):
    '''Wrapper function of the `check_event` function

    Args:
        file_monitor (FileMonitor): FileMonitor object to monitor the file content.
        callback (str): log regex to check in Wazuh log
        error_message (str): error message to show in case of expected event does not occur
        update_position (boolean): filter configuration parameter to search in Wazuh log
        timeout (str): timeout to check the event in Wazuh log
        prefix (str): log pattern regex
        accum_results (int): Accumulation of matches.

    Returns:
        result (list of any): It can return either a list of any type or simply any type.
                              If `accum_results > 1`, it will be a list.
    '''

    result = check_event(file_monitor=file_monitor, callback=callback, error_message=error_message,
                         update_position=update_position, timeout=timeout, prefix=prefix, accum_results=accum_results,
                         file_to_monitor=file_to_monitor)

    return result


def check_module_is_starting(file_monitor=None, timeout=T_5, update_position=True):
    '''Check if the syscollector module is starting'''
    check_syscollector_event(file_monitor=file_monitor, callback=syscollector.CB_SCAN_STARTED, timeout=timeout,
                             update_position=update_position)


def check_module_startup_finished(file_monitor=None, timeout=T_5, prefix=syscollector.SYSCOLLECTOR_PREFIX,
                                  update_position=True):
    '''Check if the syscollector startup was completed.

    Args:
        timeout (str): timeout to check the event in Wazuh log
        prefix (str): log pattern regex
    '''
    check_syscollector_event(file_monitor=file_monitor, callback=syscollector.CB_MODULE_STARTED,
                             timeout=timeout, prefix=prefix, update_position=update_position)


def check_scan_started(file_monitor=None, timeout=T_5, prefix=syscollector.SYSCOLLECTOR_PREFIX, update_position=True):
    '''Check if the syscollector scan has started

    Args:
        timeout (str): timeout to check the event in Wazuh log
        prefix (str): log pattern regex
    '''
    check_syscollector_event(file_monitor=file_monitor, callback=syscollector.CB_SCAN_STARTED, timeout=timeout,
                             prefix=prefix, update_position=update_position)


def check_scan_finished(file_monitor=None, timeout=T_5, update_position=True):
    '''Check if the syscollector scan has finished'''
    check_syscollector_event(file_monitor=file_monitor, callback=syscollector.CB_SCAN_FINISHED, timeout=timeout,
                             update_position=update_position)


def check_sync_started(file_monitor=None, timeout=T_5, update_position=True):
    '''Check if the syscollector synchronization has started'''
    check_syscollector_event(file_monitor=file_monitor, callback=syscollector.CB_SYNC_STARTED, timeout=timeout,
                             update_position=update_position)


def check_sync_finished(file_monitor=None, timeout=T_5, update_position=True):
    '''Check if the syscollector synchronization has finished'''
    check_syscollector_event(file_monitor=file_monitor, callback=syscollector.CB_SYNC_FINISHED, timeout=timeout,
                             update_position=update_position)


def check_syscollector_is_disabled(file_monitor=None, timeout=T_5, update_position=True):
    '''Check if the syscollector module is disabled'''
    check_syscollector_event(file_monitor=file_monitor, callback=syscollector.CB_SYSCOLLECTOR_DISABLED, timeout=timeout,
                             update_position=update_position)


def check_config(disabled='no', interval=3600, scan_on_start='yes', hardware='yes', os='yes', ports='yes',
                 network='yes', packages='yes', ports_all='no', processes='yes', hotfixes='yes', max_eps=10,
                 file_monitor=None, timeout=T_5, update_position=True):
    '''Check if the syscollector configuration was applied correctly.

    Args:
        disabled (str): Disable the Syscollector wodle.
        interval (int): Time between system scans.
        scan_on_start (str): Run a system scan immediately when service is started.
        hardware (str): Enables the hardware scan.
        os (str): Enables the OS scan.
        ports (str): Enables the ports scan.
        network (str): Enables the network scan.
        packages (str): Enables the packages scan.
        ports_all (str): Make Wazuh only scans listening ports.
        processes (str): Enables the processes scan.
        hotfixes (str): Enables the hotfixes scan.
        max_eps (int): Sets the maximum event reporting throughput.
    '''
    msg = 'DEBUG:.+"disabled":"{0}","scan-on-start":"{1}","interval":{2},'.format(disabled, scan_on_start, interval)
    msg += '"network":"{0}","os":"{1}","hardware":"{2}","packages":"{3}","ports":"{4}",'.format(network, os, hardware,
                                                                                                packages, ports)
    msg += '"ports_all":"{0}","processes":"{1}",'.format(ports_all, processes)
    if sys.platform == 'win32':
        msg += '"hotfixes":"{0}",'.format(hotfixes)
    msg += '"sync_max_eps":{0}.+'.format(max_eps)

    check_syscollector_event(file_monitor=file_monitor, callback=msg, timeout=timeout, update_position=update_position)


def check_hardware_scan_started(file_monitor=None, timeout=T_5, update_position=True):
    '''Check if the syscollector hardware scan has started'''
    check_syscollector_event(file_monitor=file_monitor, callback=syscollector.CB_HARDWARE_SCAN_STARTED, timeout=timeout,
                             update_position=update_position)


def check_hardware_scan_finished(file_monitor=None, timeout=T_5, update_position=True):
    '''Check if the syscollector OS scan has finished'''
    check_syscollector_event(file_monitor=file_monitor, callback=syscollector.CB_HARDWARE_SCAN_FINISHED,
                             timeout=timeout, update_position=update_position)


def check_os_scan_started(file_monitor=None, timeout=T_5, update_position=True):
    '''Check if the syscollector OS scan has started'''
    check_syscollector_event(file_monitor=file_monitor, callback=syscollector.CB_OS_SCAN_STARTED, timeout=timeout,
                             update_position=update_position)


def check_os_scan_finished(file_monitor=None, timeout=T_5, update_position=True):
    '''Check if the syscollector OS scan has finished'''
    check_syscollector_event(file_monitor=file_monitor, callback=syscollector.CB_OS_SCAN_FINISHED, timeout=timeout,
                             update_position=update_position)


def check_network_scan_started(file_monitor=None, timeout=T_5, update_position=True):
    '''Check if the syscollector network scan has started'''
    check_syscollector_event(file_monitor=file_monitor, callback=syscollector.CB_NETWORK_SCAN_STARTED, timeout=timeout,
                             update_position=update_position)


def check_network_scan_finished(file_monitor=None, timeout=T_5, update_position=True):
    '''Check if the syscollector network scan has finished'''
    check_syscollector_event(file_monitor=file_monitor, callback=syscollector.CB_NETWORK_SCAN_FINISHED, timeout=timeout,
                             update_position=update_position)


def check_packages_scan_started(file_monitor=None, timeout=T_5, update_position=True):
    '''Check if the syscollector packages scan has started'''
    check_syscollector_event(file_monitor=file_monitor, callback=syscollector.CB_PACKAGES_SCAN_STARTED, timeout=timeout,
                             update_position=update_position)


def check_packages_scan_finished(file_monitor=None, timeout=T_5, update_position=True):
    '''Check if the syscollector packages scan has finished'''
    check_syscollector_event(file_monitor=file_monitor, callback=syscollector.CB_PACKAGES_SCAN_FINISHED,
                             timeout=timeout, update_position=update_position)


def check_ports_scan_started(file_monitor=None, timeout=T_5, update_position=True):
    '''Check if the syscollector ports scan has started'''
    check_syscollector_event(file_monitor=file_monitor, callback=syscollector.CB_PORTS_SCAN_STARTED, timeout=timeout,
                             update_position=update_position)


def check_ports_scan_finished(file_monitor=None, timeout=T_5, update_position=True):
    '''Check if the syscollector ports scan has finished'''
    check_syscollector_event(file_monitor=file_monitor, callback=syscollector.CB_PORTS_SCAN_FINISHED, timeout=timeout,
                             update_position=update_position)


def check_processes_scan_started(file_monitor=None, timeout=T_5, update_position=True):
    '''Check if the syscollector processes scan has started'''
    check_syscollector_event(file_monitor=file_monitor, callback=syscollector.CB_PROCESES_SCAN_STARTED, timeout=timeout,
                             update_position=update_position)


def check_processes_scan_finished(file_monitor=None, timeout=T_5, update_position=True):
    '''Check if the syscollector processes scan has finished'''
    check_syscollector_event(file_monitor=file_monitor, callback=syscollector.CB_PROCESES_SCAN_FINISHED,
                             timeout=timeout, update_position=update_position)


def check_hotfixes_scan_started(file_monitor=None, timeout=T_5, update_position=True):
    '''Check if the syscollector hotfixes scan has started'''
    check_syscollector_event(file_monitor=file_monitor, callback=syscollector.CB_HOTFIXES_SCAN_STARTED, timeout=timeout,
                             update_position=update_position)


def check_hotfixes_scan_finished(file_monitor=None, timeout=T_5, update_position=True):
    '''Check if the syscollector hotfixes scan has finished'''
    check_syscollector_event(file_monitor=file_monitor, callback=syscollector.CB_HOTFIXES_SCAN_FINISHED,
                             timeout=timeout, update_position=update_position)


def check_tag_error(field='', file_monitor=None, timeout=T_5, prefix='.+wmodules_syscollector.+', update_position=True):
    '''Check if syscollector shows an error when using an invalid value in a tag.'''
    callbacks_options = {
        'max_eps': "WARNING:.+ Invalid value for element 'max_eps': .+",
        'interval': "ERROR: Invalid interval at module 'syscollector'",
        'all': f"ERROR: Invalid content for tag '{field}' at module 'syscollector'."
    }
    selected_callback = callbacks_options['all'] if field not in callbacks_options.keys() else callbacks_options[field]

    check_syscollector_event(file_monitor=file_monitor, callback=selected_callback, timeout=timeout, prefix=prefix,
                             update_position=update_position)


def check_attr_error(attr='', file_monitor=None, timeout=T_5, prefix='.+wmodules_syscollector.+', update_position=True):
    '''Check if syscollector shows an error when using an invalid value in an attribute.'''
    check_syscollector_event(file_monitor=file_monitor, timeout=timeout, prefix=prefix,
                             callback=f"ERROR: Invalid content for attribute '{attr}' at module 'syscollector'.",
                             update_position=update_position)
