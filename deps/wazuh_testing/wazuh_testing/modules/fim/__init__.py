# Copyright (C) 2015-2022, Wazuh Inc.
# Created by Wazuh, Inc. <info@wazuh.com>.
# This program is free software; you can redistribute it and/or modify it under the terms of GPLv2

'''
The purpose of this file is to contain all the variables necessary for FIM in order to be easier to
maintain if one of them changes in the future.
'''

import sys
import os
from wazuh_testing.tools import PREFIX

# Variables
SIZE_LIMIT_CONFIGURED_VALUE = 10240

# Key variables
MONITORED_KEY = 'SOFTWARE\\random_key'
MONITORED_KEY_2 = 'SOFTWARE\\Classes\\random_key_2'
MONITORED_KEY_3 = 'SOFTWARE\\Classes\\random_key_3'

WINDOWS_HKEY_LOCAL_MACHINE = 'HKEY_LOCAL_MACHINE'

WINDOWS_REGISTRY = 'WINDOWS_REGISTRY'


# Value key
SYNC_INTERVAL = 'SYNC_INTERVAL'
SYNC_INTERVAL_VALUE = MAX_EVENTS_VALUE = 20


# Folders variables
TEST_DIR_1 = 'testdir1'
TEST_DIRECTORIES = 'TEST_DIRECTORIES'
TEST_REGISTRIES = 'TEST_REGISTRIES'

MONITORED_DIR_1 = os.path.join(PREFIX, TEST_DIR_1)

# Syscheck attributes
REPORT_CHANGES = 'report_changes'

FILE_SIZE_ENABLED = 'FILE_SIZE_ENABLED'
FILE_SIZE_LIMIT = 'FILE_SIZE_LIMIT'

DISK_QUOTA_ENABLED = 'DISK_QUOTA_ENABLED'
DISK_QUOTA_LIMIT = 'DISK_QUOTA_LIMIT'
DIFF_SIZE_LIMIT = 'diff_size_limit'

# Syscheck values
DIFF_LIMIT_VALUE = 2
DIFF_DEFAULT_LIMIT_VALUE = 51200


# FIM modules
SCHEDULED_MODE = 'scheduled'
REALTIME_MODE = 'realtime'
WHODATA_MODE = 'whodata'


# Yaml Configuration
YAML_CONF_REGISTRY_RESPONSE = 'wazuh_conf_registry_responses_win32.yaml'
YAML_CONF_SYNC_WIN32 = 'wazuh_sync_conf_win32.yaml'
YAML_CONF_DIFF = 'wazuh_conf_diff.yaml'
YAML_CONF_MAX_EPS_SYNC = 'wazuh_sync_conf_max_eps.yaml'


# Synchronization options
SYNCHRONIZATION_ENABLED = 'SYNCHRONIZATION_ENABLED'
SYNCHRONIZATION_REGISTRY_ENABLED = 'SYNCHRONIZATION_REGISTRY_ENABLED'


# Callbacks message
CB_FIM_EVENT = r'.*Sending FIM event: (.+)$'
CB_REALTIME_MONITORED_FOLDERS = r'.*Folders monitored with real-time engine: (\d+)'
CB_REALTIME_WHODATA_ENGINE_STARTED = 'File integrity monitoring real-time Whodata engine started'
CB_INVALID_CONFIG_VALUE = r".*Invalid value for element '(.*)': (.*)."

CB_INTEGRITY_CONTROL_MESSAGE = r".*Sending integrity control message: (.+)$"
CB_MAXIMUM_FILE_SIZE = r".*Maximum file size limit to generate diff information configured to \'(\d+) KB\'.*"
CB_AGENT_CONNECT = r".* Connected to the server .*"
CB_INODE_ENTRIES_PATH_COUNT = r".*Fim inode entries: '(\d+)', path count: '(\d+)'"
CB_DETECT_FIM_EVENT = r".*Sending FIM event: (.+)$"
CB_DATABASE_FULL_COULD_NOT_INSERT_VALUE = r".*registry_value.*Couldn't insert ('.*') entry into DB. The DB is full.*"
CB_DATABASE_FULL_COULD_NOT_INSERT_KEY = r".*registry_key.*Couldn't insert ('.*') entry into DB. The DB is full.*"
CB_COUNT_REGISTRY_ENTRIES = r".*Fim registry entries count: '(\d+)'"
CB_COUNT_REGISTRY_VALUE_ENTRIES = r".*Fim registry values entries count: '(\d+)'"
CB_REGISTRY_DBSYNC_NO_DATA = r".*#!-fim_registry_(.*) dbsync no_data (.+)"
CB_REGISTRY_LIMIT_CAPACITY = r".*Registry database is (\d+)% full."
CB_REGISTRY_DB_BACK_TO_NORMAL = r".*(The registry database status returns to normal)."
CB_REGISTRY_LIMIT_VALUE = r".*Maximum number of registry values to be monitored: '(\d+)'"
CB_FILE_LIMIT_CAPACITY = r".*File database is (\d+)% full."
CB_FILE_LIMIT_BACK_TO_NORMAL = r".*(Sending DB back to normal alert)."
CB_FIM_ENTRIES_COUNT = r".*Fim file entries count: '(\d+)'"
CB_FILE_LIMIT_VALUE = r".*Maximum number of files to be monitored: '(\d+)'"
CB_FILE_LIMIT_DISABLED = r".*(No limit set) to maximum number of file entries to be monitored"
CB_PATH_MONITORED_REALTIME = r".*Directory added for real time monitoring: (.*)"
CB_PATH_MONITORED_WHODATA = r".*Added audit rule for monitoring directory: (.*)"
CB_PATH_MONITORED_WHODATA_WINDOWS = r".*Setting up SACL for (.*)"
CB_SYNC_SKIPPED = r".*Sync still in progress. Skipped next sync and increased interval.*'(\d+)s'"
CB_SYNC_INTERVAL_RESET = r".*Previous sync was successful. Sync interval is reset to: '(\d+)s'"
CB_IGNORING_DUE_TO_SREGEX = r".*?Ignoring path '(.*)' due to sregex '(.*)'.*"
CB_IGNORING_DUE_TO_PATTERN = r".*?Ignoring path '(.*)' due to pattern '(.*)'.*"


# Error message
ERR_MSG_REALTIME_FOLDERS_EVENT = 'Did not receive expected "Folders monitored with real-time engine" event'
ERR_MSG_WHODATA_ENGINE_EVENT = 'Did not receive expected "real-time Whodata engine started" event'
ERR_MSG_INVALID_CONFIG_VALUE = 'Did not receive expected "Invalid value for element" event'
ERR_MSG_AGENT_DISCONNECT = 'Agent couldn\'t connect to server.'
ERR_MSG_INTEGRITY_CONTROL_MSG = 'Didn\'t receive control message(integrity_check_global)'
ERR_MSG_DATABASE_PERCENTAGE_FULL_ALERT = 'Did not receive expected "DEBUG: ...: database is ...% full" alert'
ERR_MSG_WRONG_CAPACITY_LOG_DB_LIMIT = 'Wrong capacity log for DB file_limit'
ERR_MSG_DB_BACK_TO_NORMAL = 'Did not receive expected "DEBUG: ... database status returns to normal." event'
ERR_MSG_DATABASE_FULL_ALERT = 'Did not receive expected "DEBUG: ...: Registry database is 100% full" alert'
ERR_MSG_WRONG_VALUE_FOR_DATABASE_FULL = 'Wrong value for full database alert.'
ERR_MSG_DATABASE_FULL_COULD_NOT_INSERT = 'Did not receive expected "DEBUG: ...: Couldn\'t insert \'...\' entry \
                                          into DB. The DB is full, ..." event'
ERR_MSG_DATABASE_FULL_ALERT_EVENT = 'Did not receive expected "DEBUG: ...: Sending DB 100% full alert." event'
ERR_MSG_WRONG_NUMBER_OF_ENTRIES = 'Wrong number of entries counted.'
ERR_MSG_WRONG_INODE_PATH_COUNT = 'Wrong number of inodes and path count'
ERR_MSG_FIM_INODE_ENTRIES = 'Did not receive expected "Fim inode entries: ..., path count: ..." event'
ERR_MSG_FIM_REGISTRY_ENTRIES = 'Did not receive expected "Fim Registry entries count: ..." event'
ERR_MSG_FIM_REGISTRY_VALUE_ENTRIES = 'Did not receive expected "Fim Registry value entries count: ..." event'
ERR_MSG_REGISTRY_LIMIT_VALUES = 'Did not receive expected "DEBUG: ...: Maximum number of registry values to \
                                 be monitored: ..." event'
ERR_MSG_WRONG_REGISTRY_LIMIT_VALUE = 'Wrong value for db_value_limit registries tag.'
ERR_MSG_FILE_LIMIT_VALUES = 'Did not receive expected "DEBUG: ...: Maximum number of entries to be monitored: \
                             ..." event'
ERR_MSG_WRONG_FILE_LIMIT_VALUE = 'Wrong value for file_limit.'
ERR_MSG_FILE_LIMIT_DISABLED = 'Did not receive expected "DEBUG: ...: No limit set to maximum number of entries \
                               to be monitored" event'
ERR_MSG_MAXIMUM_FILE_SIZE = 'Did not receive expected "Maximum file size limit configured to \'... KB\'..." event'
ERR_MSG_NO_EVENTS_EXPECTED = 'No events should be detected.'
ERR_MSG_DELETED_EVENT_NOT_RECIEVED = 'Did not receive expected deleted event'
ERR_MSG_FIM_EVENT_NOT_RECIEVED = 'Did not receive expected "Sending FIM event: ..." event'
ERR_MSG_MONITORING_PATH = 'Did not get the expected monitoring path line'
ERR_MSG_MULTIPLE_FILES_CREATION = 'Multiple files could not be created.'
ERR_MSG_SCHEDULED_SCAN_ENDED = 'Did not recieve the expected  "DEBUG: ... Sending FIM event: {type:scan_end"...} event'
ERR_MSG_WRONG_VALUE_MAXIMUM_FILE_SIZE = 'Wrong value for diff_size_limit'
ERR_MSG_INTEGRITY_OR_WHODATA_NOT_STARTED = 'Did not receive expected "File integrity monitoring real-time Whodata \
                                            engine started" or "Initializing FIM Integrity Synchronization check"'
ERR_MSG_INTEGRITY_CHECK_EVENT = 'Did not receive expected "Initializing FIM Integrity Synchronization check" event'
ERR_MSG_SYNC_SKIPPED_EVENT = 'Did not recieve the expected "Sync still in progress. Skipped next sync" event'
ERR_MSG_FIM_SYNC_NOT_DETECTED = 'Did not receive expected "Initializing FIM Integrity Synchronization check" event'
ERR_MSG_SYNC_INTERVAL_RESET_EVENT = 'Did not recieve the expected "Sync interval is reset" event'
ERR_MSG_CONTENT_CHANGES_EMPTY = "content_changes is empty"
ERR_MSG_CONTENT_CHANGES_NOT_EMPTY = "content_changes isn't empty"


# Setting Local_internal_option file
if sys.platform == 'win32':
    FIM_DEFAULT_LOCAL_INTERNAL_OPTIONS = {
        'windows.debug': '2',
        'syscheck.debug': '2',
        'agent.debug': '2',
        'monitord.rotate_log': '0'
    }
else:
    FIM_DEFAULT_LOCAL_INTERNAL_OPTIONS = {
        'syscheck.debug': '2',
        'agent.debug': '2',
        'monitord.rotate_log': '0',
        'analysisd.debug': '2'
    }
