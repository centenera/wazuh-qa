"""AWS S3 related utils"""

import json
import logging
from typing import Tuple

import boto3
from botocore import exceptions
from botocore.exceptions import ClientError
from .data_generator import get_data_generator

session = boto3.Session(profile_name="qa")
s3 = session.resource('s3')


def upload_file(bucket_type: str, bucket_name: str) -> str:
    """Upload a file to an S3 bucket

    :param bucket_type: Bucket type to generate the data
    :param bucket_name: Bucket to upload
    :return: the name of the file if was uploaded, else ''
    """
    dg = get_data_generator(bucket_type)
    filename = dg.get_filename()
    obj = s3.Object(bucket_name, filename)

    data = dg.get_data_sample()

    # Upload the file
    try:
        obj.put(Body=json.dumps(data).encode())
    except ClientError as e:
        logging.error(e)
        filename = ''
    return filename

def delete_file(filename: str, bucket_name: str) -> None:
    """Delete the given a file from bucket a bucket

    Parameters
    ----------
    filename : str
        Full filename to delete
    bucket_name : str
        bucket that contains the file
    """
    s3.Object(bucket_name, filename).delete()


def file_exists(filename: str, bucket_name: str) -> bool:
    """Check if a file exists in a bucket

    Parameters
    ----------
    filename : str
        Full filename to check
    bucket_name : str
        bucket that contains the file

    Returns
    -------
    bool
        True if exists else False
    """
    exists = True
    try:
        s3.Object(bucket_name, filename).load()
    except exceptions.ClientError as error:
        if error.response['Error']['Code'] == '404':
            exists = False

    return exists
