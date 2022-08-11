'''
copyright: Copyright (C) 2015-2022, Wazuh Inc.

           Created by Wazuh, Inc. <info@wazuh.com>.

           This program is free software; you can redistribute it and/or modify it under the terms of GPLv2

type: end_to_end

brief: This test will verify that the AWS-S3 module is working correctly.The AWS S3 wodle allows you to gather and parse
       logs from multiple AWS services, such as Guard Duty, Macie, VPC Flow, etc.

components:
    - aws_s3

targets:
    - manager

daemons:
    - wazuh-modulesd
    - wazuh-analysisd

os_platform:
    - linux

os_version:
    - CentOS 8

references:
    - https://github.com/wazuh/wazuh-automation/wiki/Wazuh-demo:-Execution-guide#aws
    - https://documentation.wazuh.com/current/proof-of-concept-guide/aws-infrastructure-monitoring.html
    - https://documentation.wazuh.com/current/amazon/index.html

tags:
    - demo
    - aws
'''
import os
import json
import re
import pytest
from datetime import datetime
from tempfile import gettempdir

from wazuh_testing import end_to_end as e2e
from wazuh_testing import event_monitor as evm
from wazuh_testing.tools import configuration as config

# Test cases data
test_data_path = os.path.join(os.path.dirname(os.path.realpath(__file__)), 'data')
test_cases_path = os.path.join(test_data_path, 'test_cases')
test_cases_file_path = os.path.join(test_cases_path, 'cases_aws_infrastructure_monitoring.yaml')
alerts_json = os.path.join(gettempdir(), 'alerts.json')

# Playbooks
configuration_playbooks = ['configuration.yaml']
events_playbooks = ['generate_events.yaml']
teardown_playbooks = ['teardown.yaml']
configuration_extra_vars = {'date': datetime.strftime(datetime.now(), '%Y-%b-%d').upper()}

# Configuration
configuration, metadata, cases_ids = config.get_test_cases_data(test_cases_file_path)

# Custom paths
aws_api_script = os.path.join(test_data_path, 'configuration', 'aws_cloudtrail_event.py')

# Update configuration with custom paths
metadata = config.update_configuration_template(metadata, ['CUSTOM_AWS_SCRIPT_PATH'], [aws_api_script])
bucket_name = metadata[0]['extra_vars']['bucket']
configuration_extra_vars.update({'AWS_API_SCRIPT': aws_api_script, 'bucket': bucket_name})


@pytest.mark.parametrize('metadata', metadata, ids=cases_ids)
@pytest.mark.filterwarnings('ignore::urllib3.exceptions.InsecureRequestWarning')
def test_aws_infrastructure_monitoring(metadata, configure_environment, get_dashboard_credentials, generate_events,
                                       clean_alerts_index):
    '''
    description: Check that an alert is generated and indexed when an event obtained from AWS services matches a rule.

    test_phases:
        - Set a custom Wazuh configuration.
        - Create a bucket to generate event.
        - Check in the alerts.json log that the expected alert has been triggered and get its timestamp.
        - Check that the obtained alert from alerts.json has been indexed.

    wazuh_min_version: 4.4.0

    tier: 0

    parameters:
        - configurate_environment:
            type: fixture
            brief: Set the wazuh configuration according to the configuration playbook.
        - metadata:
            type: dict
            brief: Wazuh configuration metadata.
        - get_dashboard_credentials:
            type: fixture
            brief: Get the wazuh dashboard credentials.
        - generate_events:
            type: fixture
            brief: Generate events that will trigger the alert according to the generate_events playbook.
        - clean_alerts_index:
            type: fixture
            brief: Delete obtained alerts.json and alerts index.

    assertions:
        - Verify that the alert has been triggered.
        - Verify that the same alert has been indexed.

    input_description:
        - The `configuration.yaml` file provides the module configuration for this test.
        - The `generate_events.yaml`file provides the function configuration for this test.
    '''
    rule_description = metadata['rule.description']
    rule_id = metadata['rule.id']
    rule_level = metadata['rule.level']
    timestamp_regex = r'\d+-\d+-\d+T\d+:\d+:\d+\.\d+[\+|-]\d+'

    expected_alert_json = fr".+timestamp\":\"({timestamp_regex})\",.+level\":{rule_level}.+description\"" \
                          fr":\"{rule_description}.+id.+{rule_id}.+"

    expected_indexed_alert = fr".+level.+{rule_level}.+description.+{rule_description}.+id.+{rule_id}.+" \
                             fr"timestamp\": \"({timestamp_regex})\""

    # Check that alert has been raised and save timestamp
    raised_alert = evm.check_event(callback=expected_alert_json, file_to_monitor=alerts_json,
                                   error_message='The alert has not occurred').result()
    raised_alert_timestamp = raised_alert.group(1)

    query = e2e.make_query([
        {
          "term": {
            "rule.id": f"{rule_id}"
          }
        },
        {
          "term": {
            "rule.description": f"{rule_description}"
          }
        },
        {
            "term": {
                "timestamp": f"{raised_alert_timestamp}"
            }
        }
    ])

    # Check if the alert has been indexed and get its data
    response = e2e.get_alert_indexer_api(query=query, credentials=get_dashboard_credentials)
    indexed_alert = json.dumps(response.json())

    # Check that the alert data is the expected one
    alert_data = re.search(expected_indexed_alert, indexed_alert)
    assert alert_data is not None, 'Alert triggered, but not indexed'
