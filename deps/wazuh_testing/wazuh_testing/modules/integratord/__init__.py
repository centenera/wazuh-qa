'''
copyright: Copyright (C) 2015-2022, Wazuh Inc.
           Created by Wazuh, Inc. <info@wazuh.com>.
           This program is free software; you can redistribute it and/or modify it under the terms of GPLv2
'''

# Variables

# Callbacks
CB_VIRUSTOTAL_ENABLED = ".*wazuh-integratord.*Enabling integration for: 'virustotal'.*"
CB_INTEGRATORD_SENDING_ALERT = '.*wazuh-integratord.*DEBUG: sending new alert'
CB_PROCESSING_ALERT = '.*wazuh-integratord.*Processing alert.*'
CB_INTEGRATORD_THREAD_READY ='.*wazuh-integratord.*DEBUG: Local requests thread ready'
CB_VIRUSTOTAL_ALERT = '.*wazuh-integratord.*alert_id.*\"integration\": \"virustotal\".*'
CB_VIRUSTOTAL_ALERT_JSON = '.*VirusTotal: Alert.*\"integration\":\"virustotal\".*'
CB_INVALID_JSON_ALERT_READ = '.*wazuh-integratord.*WARNING: Invalid JSON alert read.*'
CB_OVERLONG_JSON_ALERT_READ = '.*wazuh-integratord.*WARNING: Overlong JSON alert read.*'
CB_ALERTS_FILE_INODE_CHANGED = '.*wazuh-integratord.*DEBUG: jqueue_next.*Alert file inode changed.*'
CB_CANNOT_RETRIEVE_JSON_FILE = '.*wazuh-integratord.*ERROR.*Could not retrieve information of file.*'\
                               'alerts\.json.*No such file.*'

# Error messages
ERR_MSG_VIRUST_TOTAL_ENABLED_NOT_FOUND = 'Did not recieve the expected "Enabling integration for virustotal"'
ERR_MSG_VIRUSTOTAL_ALERT_NOT_DETECTED = 'Did not recieve the expected VirusTotal alert in alerts.json'
ERR_MSG_INVALID_ALERT_NOT_FOUND = 'Did not recieve the expected "...Invalid JSON alert read..." event'
ERR_MSG_OVERLONG_ALERT_NOT_FOUND = 'Did not recieve the expected "...Overlong JSON alert read..." event'
ERR_MSG_ALERT_INODE_CHANGED_NOT_FOUND = 'Did not recieve the expected "...Alert file inode changed..." event'
ERR_MSG_CANNOT_RETRIEVE_MSG_NOT_FOUND = 'Did not recieve the expected "...Could not retrieve information/open file"'
ERR_MSG_SENDING_ALERT_NOT_FOUND = 'Did not recieve the expected "...sending new alert" event'
ERR_MSG_PROCESSING_ALERT_NOT_FOUND = 'Did not recieve the expected "...Procesing alert" event'
