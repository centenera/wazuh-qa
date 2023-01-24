# Copyright (C) 2015-2023, Wazuh Inc.
# Created by Wazuh, Inc. <info@wazuh.com>.
# This program is free software; you can redistribute it and/or modify it under the terms of GPLv2
import os
import json
import socket
import rocksdb

from wazuh_testing.tools import ENGINE_QUEUE_SOCKET_PATH


# engine timeouts
T_1 = 0.5

# engine vars
ENGINE_ALERTS_PATH = '/var/ossec/logs/alerts/alerts-ECS.json'  # the engine uses this file during the dev phase
ENGINE_LOG_PATH = '/tmp/engine.log'
ENGINE_PREFIX = '.*'
MODULE_NAME = 'wazuh-engine'
QUEUE = '1'
LOCATION = 'location'
ENGINE_BIN_PATH = '/home/vagrant/engine/wazuh/src/engine/build/main'
ENGINE_KVDBS_PATH = '/var/ossec/etc/kvdb'


def send_events_to_engine_dgram(queue=QUEUE, location=LOCATION, events=[]):
    """Send events to the engine events' socket.

    The messages must follow the following format: queue:location_str:msg.

    The socket's protocol is unixgram, so we just need to send the events after formatting and encoding them.

    Args:
        queue(str): queue string that is used to create the message that will be sent to the socket.
        location(str): location string that is used to create the message that will be sent to the socket.
        events (list): Events that will be sent to the socket.
    """
    # Create a unixgram socket instance
    events_socket = socket.socket(socket.AF_UNIX, socket.SOCK_DGRAM)

    for event in events:
        # Build the message with the expected format: {queue:location_str:msg}
        msg_formatted = (queue + ':' + location + ':' + event).encode('utf8')

        # Send the encoded message to the engine's events socket
        events_socket.sendto(msg_formatted, ENGINE_QUEUE_SOCKET_PATH)


def create_api_call(command='kvdb', subcommand='list', options={}):
    """Create an engine's API call by joining the command, subcommand, and options.

    Args:
        options(dict): A dict that contains every desired option with its value.

    Returns:
        String with the proper API call that can be created with the parameters.
    """
    api_call_str = f"{ENGINE_BIN_PATH} {command} {subcommand}"

    for option_name in options:
        api_call_str += f" {option_name} {options[option_name]}"

    return api_call_str


def get_api_call_data(configuration_metadata):
    """Get the api call data collected from the provided configuration metadata.

    Args:
        configuration_metadata(dict): Test case's metadata that contains the api call data.

    Returns:
        An array with the API calls data for each provided test case.
    """
    api_call_data = []
    api_call_fields = ['command', 'subcommand', 'options']

    for test_case in configuration_metadata:
        # collect the api call info for each test case
        api_call_data_case = {}

        for field in api_call_fields:
            # which fields should be required? command? or none (in this case the engine will use its default pars)
            if field in test_case:
                if field == 'options' and '-p' in test_case[field] and 'create' == test_case['subcommand']:
                    extension = ("json" if 'extension' not in test_case else f"{test_case['extension']}")
                    test_case[field]['-p'] += f"/{test_case['kvdb_names'][0]}.{extension}"
                api_call_data_case[field] = test_case[field]

        api_call_data.append(api_call_data_case)

    return api_call_data


def get_kvdb_names(configuration_metadata):
    """Get the kvdb names collected from the provided configuration metadata.

    Args:
        configuration_metadata(dict): Test case's metadata that contains the api call data.

    Returns:
        A list with the kvdb names for each provided test case.
    """
    kvdb_names = []

    for cases in configuration_metadata:
        if 'kvdb_names' in cases:
            kvdb_names.append(cases['kvdb_names'])

    return kvdb_names


def create_rocksdb_instance(kvdb_path=ENGINE_KVDBS_PATH, db_name=None,
                            options=rocksdb.Options(create_if_missing=False), read_only=True):
    """Create a rocksdb instance that allow to communicate via its API.

    Args:
        kvdb_path(str): Path where the engine expects that KVDBs are stored.
        db_name(str): Name of the database to open.
        options(rocksdb.Options): Options object that rocksdb has.
                                  https://python-rocksdb.readthedocs.io/en/latest/api/options.html.
        read_only(boolean): If True the database is opened read-only. If modify data will raise an Exception.

    Returns:
        A database (rocksdb) instance that allow you to interact with databases.
    """
    db_instance = rocksdb.DB(db_name=os.path.join(kvdb_path, db_name), opts=options, read_only=read_only)

    return db_instance


def read_kvdb_file(kvdbs_path, db_name):
    """Read the kvdb's file content and store it within a dictionary.

    Args:
        kvdb_path(str): Path where the kvdb's json files are stored.
        db_name(str): Name of the database.

    Returns:
        KVDB content as a dictionary, loaded using the database JSON file.
    """
    return json.load(open(os.path.join(kvdbs_path, f"{db_name}.json")))


def get_kvdb_value(kvdb_path=ENGINE_KVDBS_PATH, db_name=None, key=None, rocksdb_instance=None):
    """Get database value for a certain key.

    Args:
        kvdb_path(str): Path where the engine expects that KVDBs are stored.
        db_name(str): Name of the database to be interacted with.
        key(str): Key used to perform the value request.
        rocksdb_instance(rocksdb.DB): Database instance used to interact with the db
                                      https://python-rocksdb.readthedocs.io/en/latest/api/database.html#rocksdb.DB.

    Returns:
        A string with the value for the provided key.

    Raises:
        AssertionError: If the provided key does not exist within the db.
        AssertionError: If the key exists but is not in memory.
    """
    if rocksdb_instance is None:
        db = create_rocksdb_instance(kvdb_path=kvdb_path, db_name=db_name)
    else:
        db = rocksdb_instance

    value_fetched = db.key_may_exist(key=key.encode() if type(key) != bytes else key, fetch=True)

    # (False, None) if key is not found
    assert value_fetched[0], f"The key {key} does not exist within the {kvdb_path} database."
    # (True, <data>) if key is found and value in memory and fetch=True
    assert not value_fetched[0] or not value_fetched[1] is None, f"The key {key} exists but is not in memory."

    # The request returns the value like "value", the quotes are discarded
    return value_fetched[1][1:-1]


def get_kvdb_content(kvdb_path=ENGINE_KVDBS_PATH, db_name=None, rocksdb_instance=None):
    """Get the database current content by requesting it via API.

    Args:
        kvdb_path(str): Path where the engine expects that KVDBs are stored.
        db_name(str): Name of the database to be interacted with.
        rocksdb_instance(rocksdb.DB): Database instance used to interact with the db
                                      https://python-rocksdb.readthedocs.io/en/latest/api/database.html#rocksdb.DB.

    Returns:
        A dictionary with the current database content.
    """
    kvdb_content = {}

    if rocksdb_instance is None:
        db = create_rocksdb_instance(kvdb_path=kvdb_path, db_name=db_name)
    else:
        db = rocksdb_instance

    # Create rocksdb.BaseIterator instance
    db_iterator = db.iterkeys()
    # Point to the beginning
    db_iterator.seek_to_first()

    for db_key in db_iterator:
        kvdb_content[db_key] = get_kvdb_value(kvdb_path, db_name, db_key, db)

    return kvdb_content


def get_available_kvdbs():
    """Get all the kvdbs available on memory within the kvdb's path that the engine has configured.

    Returns:
        A list with the available databases.
    """
    available_kvdbs = []

    # Iterate thru each file within the defined kvdbs' path
    for kvdb_folder in os.listdir(ENGINE_KVDBS_PATH):
        kvdb_folder_path = os.path.join(ENGINE_KVDBS_PATH, kvdb_folder)

        # Iterate thru each file within the specific kvdb folder
        if os.path.isdir(kvdb_folder_path):
            for kvdb_file in os.listdir(kvdb_folder_path):
                if 'MANIFEST-' in kvdb_file:
                    available_kvdbs += [kvdb_folder]

    return available_kvdbs
