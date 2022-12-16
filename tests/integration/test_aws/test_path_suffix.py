import os

import pytest
from wazuh_testing import T_10, global_parameters
from wazuh_testing.modules.aws import event_monitor
from wazuh_testing.modules.aws.db_utils import get_s3_db_row, s3_db_exists, table_exists
from wazuh_testing.tools.configuration import (
    get_test_cases_data,
    load_configuration_template,
)

pytestmark = [pytest.mark.server]


# Generic vars
TEMPLATE_DIR = 'configuration_template'
TEST_CASES_DIR = 'test_cases'
MODULE = 'path_suffix_test_module'
TEST_DATA_PATH = os.path.join(os.path.dirname(os.path.realpath(__file__)), 'data')
CONFIGURATIONS_PATH = os.path.join(TEST_DATA_PATH, TEMPLATE_DIR, MODULE)
TEST_CASES_PATH = os.path.join(TEST_DATA_PATH, TEST_CASES_DIR, MODULE)
local_internal_options = {'wazuh_modules.debug': '2', 'monitord.rotate_log': '0'}

# ---------------------------------------------------- TEST_PATH -------------------------------------------------------
configurations_path = os.path.join(CONFIGURATIONS_PATH, 'configuration_path_suffix.yaml')
cases_path = os.path.join(TEST_CASES_PATH, 'cases_path_suffix.yaml')

configuration_parameters, configuration_metadata, case_ids = get_test_cases_data(cases_path)
configurations = load_configuration_template(
    configurations_path, configuration_parameters, configuration_metadata
)


@pytest.mark.tier(level=0)
@pytest.mark.parametrize('configuration, metadata', zip(configurations, configuration_metadata), ids=case_ids)
def test_path_suffix(
    configuration, metadata, load_wazuh_basic_configuration, set_wazuh_configuration, clean_s3_cloudtrail_db,
    configure_local_internal_options_function, truncate_monitored_files, restart_wazuh_function, wazuh_log_monitor
):
    """
    description: Only logs within a path_suffix are processed.
    test_phases:
        - setup:
            - Load Wazuh light configuration.
            - Apply ossec.conf configuration changes according to the configuration template and use case.
            - Apply custom settings in local_internal_options.conf.
            - Truncate wazuh logs.
            - Restart wazuh-manager service to apply configuration changes.
        - test:
            - Check in the ossec.log that a line has appeared calling the module with correct parameters.
            - If a path_suffix that does not exist was specified, make sure that a message is displayed in the ossec.log
              warning the user
            - Check the command was called with the correct parameters
            - Check the database was created and updated accordingly
        - tierdown:
            - Truncate wazuh logs.
            - Restore initial configuration, both ossec.conf and local_internal_options.conf.
            - Delete the uploaded file
    wazuh_min_version: 4.5.0
    parameters:
        - configuration:
            type: dict
            brief: Get configurations from the module.
        - metadata:
            type: dict
            brief: Get metadata from the module.
        - load_wazuh_basic_configuration:
            type: fixture
            brief: Load basic wazuh configuration.
        - set_wazuh_configuration:
            type: fixture
            brief: Apply changes to the ossec.conf configuration.
        - clean_s3_cloudtrail_db:
            type: fixture
            brief: Delete the DB file before and after the test execution
        - configure_local_internal_options_function:
            type: fixture
            brief: Apply changes to the local_internal_options.conf configuration.
        - truncate_monitored_files:
            type: fixture
            brief: Truncate wazuh logs.
        - restart_wazuh_daemon_function:
            type: fixture
            brief: Restart the wazuh service.
        - wazuh_log_monitor:
            type: fixture
            brief: Return a `ossec.log` monitor
    assertions:
        - Check in the log that the module was called with correct parameters.
        - Check the expected number of events were forwarded to analysisd
        - Check the database was created and updated accordingly, using the correct path for each entry
    input_description:
        - The `configuration_path_suffix` file provides the module configuration for this test.
        - The `cases_path_suffix` file provides the test cases.
    """
    bucket_name = metadata["bucket_name"]
    bucket_type = metadata["bucket_type"]
    only_logs_after = metadata["only_logs_after"]
    path_suffix = metadata["path_suffix"]
    expected_results = metadata["expected_results"]
    pattern = (
        fr".*No logs found in 'AWSLogs/{path_suffix}/'. "
        fr"Check the provided prefix and the location of the logs for the bucket type '{bucket_type}'*"
    )

    parameters = [
        "wodles/aws/aws-s3",
        "--bucket", bucket_name,
        "--aws_profile", "qa",
        "--trail_suffix", path_suffix,
        "--only_logs_after", only_logs_after,
        "--type", bucket_type,
        "--debug", "2"
    ]

    # Check AWS module started
    wazuh_log_monitor.start(
        timeout=global_parameters.default_timeout,
        callback=event_monitor.callback_detect_aws_module_start,
        error_message="The AWS module didn't start as expected",
    ).result()

    # Check command was called correctly
    wazuh_log_monitor.start(
        timeout=global_parameters.default_timeout,
        callback=event_monitor.callback_detect_aws_module_called(parameters),
        error_message="The AWS module wasn't called with the correct parameters",
    ).result()

    if expected_results:
        wazuh_log_monitor.start(
            timeout=global_parameters.default_timeout,
            callback=event_monitor.callback_detect_event_processed,
            error_message="The AWS module didn't process the expected number of events",
        ).result()
    else:
        with pytest.raises(TimeoutError):
            wazuh_log_monitor.start(
                timeout=global_parameters.default_timeout,
                callback=event_monitor.callback_detect_event_processed,
            ).result()

        wazuh_log_monitor.start(
            timeout=T_10,
            callback=event_monitor.make_aws_callback(pattern),
            error_message="The AWS module didn't show correct message about empty path_suffix"
        ).result()

    assert s3_db_exists()

    if expected_results:
        data = get_s3_db_row(table_name=bucket_type)
        assert f"{bucket_name}/{path_suffix}/" == data.bucket_path
        assert data.log_key.startswith(f"AWSLogs/{path_suffix}/")
    else:
        assert not table_exists(table_name=bucket_type)
