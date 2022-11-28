import pytest
from wazuh_testing import logger
from wazuh_testing.modules.aws.s3_utils import delete_file, upload_file
from wazuh_testing.modules.aws.db_utils import delete_s3_db

# S3 fixtures

@pytest.fixture(scope='function')
def upload_file_to_s3(metadata: dict) -> None:
    """Upload a file to S3 bucket

    Parameters
    ----------
    metadata : dict
        Metadata to get the parameters
    """
    bucket_name = metadata['bucket_name']
    filename = upload_file(bucket_type=metadata['bucket_type'], bucket_name=bucket_name)
    if filename != '':
        logger.debug('Uploaded file: %s to bucket "%s"', filename, bucket_name)
        metadata["uploaded_file"] = filename


@pytest.fixture(scope='function')
def upload_and_delete_file_to_s3(metadata: dict):
    """Upload a file to S3 bucket and delete after the test ends.

    Parameters
    ----------
    metadata : dict
        Metadata to get the parameters
    """
    bucket_name = metadata['bucket_name']
    filename = upload_file(bucket_type=metadata['bucket_type'], bucket_name=metadata['bucket_name'])
    if filename != '':
        logger.debug('Uploaded file: %s to bucket "%s"', filename, bucket_name)

    yield

    delete_file(filename=filename, bucket_name=bucket_name)
    logger.debug('Deleted file: %s from bucket %s', filename, bucket_name)

# DB fixtures

@pytest.fixture(scope='function')
def clean_s3_cloudtrail_db():
    """Delete the DB file before and after the test execution"""
    delete_s3_db()

    yield

    delete_s3_db()
