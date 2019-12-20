# Copyright (C) 2015-2019, Wazuh Inc.
# Created by Wazuh, Inc. <info@wazuh.com>.
# This program is free software; you can redistribute it and/or modify it under the terms of GPLv2

import json
import os
import platform
import re
import shutil
import socket
import sys
import time
from datetime import datetime
import subprocess
from collections import Counter
from copy import deepcopy
from datetime import timedelta
from stat import ST_ATIME, ST_MTIME

from json import JSONDecodeError
from jsonschema import validate

from wazuh_testing.tools import TimeMachine

if sys.platform == 'win32':
    import win32con
    import win32api
elif sys.platform == 'linux2' or sys.platform == 'linux':
    from jq import jq

_data_path = os.path.join(os.path.dirname(os.path.realpath(__file__)), 'data')

if sys.platform == 'win32':
    WAZUH_PATH = os.path.join("C:", os.sep, "Program Files (x86)", "ossec-agent")
    LOG_FILE_PATH = os.path.join(WAZUH_PATH, 'ossec.log')
    DEFAULT_TIMEOUT = 10
    _REQUIRED_AUDIT = {"path", "process_id", "process_name", "user_id", "user_name"}

elif sys.platform == 'darwin':
    WAZUH_PATH = os.path.join('/', 'Library', 'Ossec')
    LOG_FILE_PATH = os.path.join(WAZUH_PATH, 'logs', 'ossec.log')
    DEFAULT_TIMEOUT = 5

else:
    WAZUH_PATH = os.path.join('/', 'var', 'ossec')
    LOG_FILE_PATH = os.path.join(WAZUH_PATH, 'logs', 'ossec.log')
    DEFAULT_TIMEOUT = 5 if sys.platform == "linux" else 10
    _REQUIRED_AUDIT = {'user_id', 'user_name', 'group_id', 'group_name', 'process_name', 'path', 'audit_uid',
                       'audit_name', 'effective_uid', 'effective_name', 'ppid', 'process_id'
                       }

FIFO = 'fifo'
SYMLINK = 'sym_link'
HARDLINK = 'hard_link'
SOCKET = 'socket'
REGULAR = 'regular'

CHECK_ALL = 'check_all'
CHECK_SUM = 'check_sum'
CHECK_SHA1SUM = 'check_sha1sum'
CHECK_MD5SUM = 'check_md5sum'
CHECK_SHA256SUM = 'check_sha256sum'
CHECK_SIZE = 'check_size'
CHECK_OWNER = 'check_owner'
CHECK_GROUP = 'check_group'
CHECK_PERM = 'check_perm'
CHECK_ATTRS = 'check_attrs'
CHECK_MTIME = 'check_mtime'
CHECK_INODE = 'check_inode'

REQUIRED_ATTRIBUTES = {
    CHECK_SHA1SUM: 'hash_sha1',
    CHECK_MD5SUM: 'hash_md5',
    CHECK_SHA256SUM: 'hash_sha256',
    CHECK_SIZE: 'size',
    CHECK_OWNER: ['uid', 'user_name'],
    CHECK_GROUP: ['gid', 'group_name'],
    CHECK_PERM: 'perm',
    CHECK_ATTRS: 'attributes',
    CHECK_MTIME: 'mtime',
    CHECK_INODE: 'inode',
    CHECK_ALL: {CHECK_SHA256SUM, CHECK_SHA1SUM, CHECK_MD5SUM, CHECK_SIZE, CHECK_OWNER,
                CHECK_GROUP, CHECK_PERM, CHECK_ATTRS, CHECK_MTIME, CHECK_INODE},
    CHECK_SUM: {CHECK_SHA1SUM, CHECK_SHA256SUM, CHECK_MD5SUM}
}

_last_log_line = 0


def validate_event(event, checks=None):
    """Checks if event is properly formatted according to some checks.

    :param event: dict representing an event generated by syscheckd
    :param checks: set of xml CHECK_* options. Default {CHECK_ALL}.

    :return: None
    """

    def get_required_attributes(check_attributes, result=None):
        result = set() if result is None else result
        for check in check_attributes:
            mapped = REQUIRED_ATTRIBUTES[check]
            if isinstance(mapped, str):
                result |= {mapped}
            elif isinstance(mapped, list):
                result |= set(mapped)
            elif isinstance(mapped, set):
                result |= get_required_attributes(mapped, result=result)
        return result

    checks = {CHECK_ALL} if checks is None else checks

    json_file = 'syscheck_event_windows.json' if sys.platform == "win32" else 'syscheck_event.json'
    with open(os.path.join(_data_path, json_file), 'r') as f:
        schema = json.load(f)
    validate(schema=schema, instance=event)

    # Check attributes
    attributes = event['data']['attributes'].keys() - {'type', 'checksum'}

    required_attributes = get_required_attributes(checks)
    required_attributes -= get_required_attributes({CHECK_GROUP}) if sys.platform == "win32" else {'attributes'}

    intersection = attributes ^ required_attributes
    intersection_debug = "Event attributes are: " + str(attributes)
    intersection_debug += "\nRequired Attributes are: " + str(required_attributes)
    intersection_debug += "\nIntersection is: " + str(intersection)
    assert (intersection == set()), f'Attributes and required_attributes are not the same. ' + intersection_debug

    # Check audit
    if event['data']['mode'] == 'whodata':
        assert ('audit' in event['data']), f'audit no detected in event'
        assert (event['data']['audit'].keys() ^ _REQUIRED_AUDIT == set()), \
            f'audit keys and required_audit are no the same'

    # Check add file event
    if event['data']['type'] == 'added':
        assert 'old_attributes' not in event['data'] and 'changed_attributes' not in event['data']
    # Check modify file event
    if event['data']['type'] == 'modified':
        assert 'old_attributes' in event['data'] and 'changed_attributes' in event['data']

        old_attributes = event['data']['old_attributes'].keys() - {'type', 'checksum'}
        old_intersection = old_attributes ^ required_attributes
        old_intersection_debug = "Event attributes are: " + str(old_attributes)
        old_intersection_debug += "\nRequired Attributes are: " + str(required_attributes)
        old_intersection_debug += "\nIntersection is: " + str(old_intersection)
        assert (old_intersection == set()), f'Old_attributes and required_attributes are not the same. ' + old_intersection_debug


def is_fim_scan_ended():
    message = 'File integrity monitoring scan ended.'
    line_number = 0
    with open(LOG_FILE_PATH, 'r') as f:
        for line in f:
            line_number += 1
            if line_number > _last_log_line:  # Ignore if has not reached from_line
                if message in line:
                    globals()['_last_log_line'] = line_number
                    return line_number
    return -1


def create_file(type_, path, name, **kwargs):
    """ Creates a file in a given path. The path will be created in case it does not exists.

    :param type_: Defined constant that specifies the type. It can be: FIFO, SYSLINK, SOCKET or REGULAR
    :type type_: Constant string
    :param path: Path where the file will be created
    :type path: String
    :param name: File name
    :type name: String
    :return: None
    """
    os.makedirs(path, exist_ok=True, mode=0o777)
    if type_ != REGULAR:
        try:
            kwargs.pop('content')
        except KeyError:
            pass
    if type_ in (SYMLINK, HARDLINK) and 'target' not in kwargs:
        raise ValueError(f"'target' param is mandatory for type {type_}")
    getattr(sys.modules[__name__], f'_create_{type_}')(path, name, **kwargs)


def _create_fifo(path, name):
    """Creates a FIFO file.

    :param path: Path where the file will be created
    :type path: String
    :param name: File name
    :type name: String
    :return: None
    """
    fifo_path = os.path.join(path, name)
    try:
        os.mkfifo(fifo_path)
    except OSError:
        raise


def _create_sym_link(path, name, target):
    """Creates a SymLink file.

    :param path: Path where the file will be created
    :type path: String
    :param name: File name
    :type name: String
    :return: None
    """
    symlink_path = os.path.join(path, name)
    try:
        os.symlink(target, symlink_path)
    except OSError:
        raise


def _create_hard_link(path, name, target):
    """Creates a SysLink file.

    :param path: Path where the file will be created
    :type path: String
    :param name: File name
    :type name: String
    :return: None
    """
    link_path = os.path.join(path, name)
    try:
        os.link(target, link_path)
    except OSError:
        raise


def _create_socket(path, name):
    """Creates a Socket file.

    :param path: Path where the file will be created
    :type path: String
    :param name: File name
    :type name: String
    :return: None
    """
    socket_path = os.path.join(path, name)
    try:
        os.unlink(socket_path)
    except OSError:
        if os.path.exists(socket_path):
            raise
    sock = socket.socket(socket.AF_UNIX, socket.SOCK_STREAM)
    sock.bind(socket_path)


def _create_regular(path, name, content=''):
    """Creates a Regular file.

    :param path: Path where the file will be created
    :type path: String
    :param name: File name
    :type name: String
    :param content: Content of the created file
    :type content: String or bytes
    :return: None
    """
    regular_path = os.path.join(path, name)
    mode = 'wb' if isinstance(content, bytes) else 'w'

    with open(regular_path, mode) as f:
        f.write(content)


def _create_regular_windows(path, name, content=''):
    regular_path = os.path.join(path, name)
    os.popen("echo " + content + " > " + regular_path + f" runas /user:{os.getlogin()}")


def delete_file(path, name):
    """Deletes regular file.

    :param path String Path to the file to be deleted
    :param name String Name of the file to be deleted
    """
    regular_path = os.path.join(path, name)
    if os.path.exists(regular_path):
        os.remove(regular_path)


def modify_file_content(path, name, new_content=None, is_binary=False):
    """Modifies the content of a file.

    :param path String Path to the file to be modified
    :param name String Name of the file to be modified
    :param new_content String New content to append to the file. Previous content will remain
    :param is_binary boolean True if the file's content is in binary format, False otherwise
    """
    path_to_file = os.path.join(path, name)
    content = "1234567890qwertyu" if new_content is None else new_content
    with open(path_to_file, 'ab' if is_binary else 'a') as f:
        f.write(content.encode() if is_binary else content)


def modify_file_mtime(path, name):
    """Change the modification time of a file

    :param path String Path to the file to be modified
    :param name String Name of the file to be modified
    """
    path_to_file = os.path.join(path, name)
    stat = os.stat(path_to_file)
    access_time = stat[ST_ATIME]
    modification_time = stat[ST_MTIME]
    modification_time = modification_time + 1000
    os.utime(path_to_file, (access_time, modification_time))


def modify_file_owner(path, name):
    """Change the owner of a file. The new owner will be '1'.

    On Windows, uid will always be 0.

    :param path String Path to the file to be modified
    :param name String Name of the file to be modified
    """
    def modify_file_owner_windows():
        cmd = f"takeown /S 127.0.0.1 /U {os.getlogin()} /F " + path_to_file
        subprocess.call(cmd)

    def modify_file_owner_unix():
        os.chown(path_to_file, 1, -1)

    path_to_file = os.path.join(path, name)

    if sys.platform == 'win32':
        modify_file_owner_windows()
    else:
        modify_file_owner_unix()


def modify_file_group(path, name):
    """Change the group of a file. The new group will be '1'.

    Available for UNIX. On Windows, gid will always be 0 and the group name will be blank.

    :param path String Path to the file to be modified
    :param name String Name of the file to be modified
    """
    if sys.platform == 'win32':
        return

    path_to_file = os.path.join(path, name)
    os.chown(path_to_file, -1, 1)


def modify_file_permission(path, name):
    """Change the permision of a file.

    On UNIX the new permissions will be '666'.
    On Windows, a list of denied and allowed permissions will be given for each user or group since version 3.8.0.
    Only works on NTFS partitions on Windows systems.

    :param path String Path to the file to be modified
    :param name String Name of the file to be modified
    """
    def modify_file_permission_windows():
        import win32security
        import ntsecuritycon

        user, domain, account_type = win32security.LookupAccountName(None, f"{platform.node()}\\{os.getlogin()}")
        sd = win32security.GetFileSecurity(path_to_file, win32security.DACL_SECURITY_INFORMATION)
        dacl = sd.GetSecurityDescriptorDacl()
        dacl.AddAccessAllowedAce(win32security.ACL_REVISION, ntsecuritycon.FILE_ALL_ACCESS, user)
        sd.SetSecurityDescriptorDacl(1, dacl, 0)
        win32security.SetFileSecurity(path_to_file, win32security.DACL_SECURITY_INFORMATION, sd)

    def modify_file_permission_unix():
        os.chmod(path_to_file, 0o666)

    path_to_file = os.path.join(path, name)

    if sys.platform == 'win32':
        modify_file_permission_windows()
    else:
        modify_file_permission_unix()


def modify_file_inode(path, name):
    """Change the inode of a file.

    :param path String Path to the file to be modified
    :param name String Name of the file to be modified
    """
    if sys.platform == 'win32':
        return

    path_to_file = os.path.join(path, name)
    shutil.copy2(path_to_file, os.path.join(path, "inodetmp"))
    os.replace(os.path.join(path, "inodetmp"), path_to_file)


def modify_file_win_attributes(path, name):
    if sys.platform != 'win32':
        return

    path_to_file = os.path.join(path, name)
    win32api.SetFileAttributes(path_to_file, win32con.FILE_ATTRIBUTE_HIDDEN)


def modify_file(path, name, new_content=None, is_binary=False):
    """Modify a Regular file.

    :param path: Path where the file will be created
    :type path: String
    :param name: File name
    :type name: String
    :param new_content: New content to add
    :type new_content: String
    :param is_binary: True if the file is binary. False otherwise.
    :type is_binary: boolean
    :return: None
    """
    modify_file_inode(path, name)
    modify_file_content(path, name, new_content, is_binary)
    modify_file_mtime(path, name)
    modify_file_owner(path, name)
    modify_file_group(path, name)
    modify_file_permission(path, name)
    modify_file_win_attributes(path, name)


def change_internal_options(param, value, opt_path=None):
    """Changes the value of a given parameter in local_internal_options.

    :param param: Parameter to change
    :type param: String
    :param value: New value
    :type value: String
    :param opt_path: local_internal_options path
    :type opt_path: String
    """
    if opt_path is None:
        local_conf_path = os.path.join(WAZUH_PATH, 'local_internal_options.conf') if sys.platform == 'win32' else \
            os.path.join(WAZUH_PATH, 'etc', 'local_internal_options.conf')
    else:
        local_conf_path = opt_path

    add_pattern = True
    with open(local_conf_path, "r") as sources:
        lines = sources.readlines()

    with open(local_conf_path, "w") as sources:
        for line in lines:
            sources.write(
                re.sub(f'{param}=[0-9]*', f'{param}={value}', line))
            if param in line:
                add_pattern = False

    if add_pattern:
        with open(local_conf_path, "a") as sources:
            sources.write(f'\n\n{param}={value}')


def change_conf_param(param, value):
    """Changes the value of a given parameter in ossec.conf.

    :param param: Parameter to change
    :type param: String
    :param value: New value
    :type value: String
    """
    conf_path = os.path.join(WAZUH_PATH, 'ossec.conf') if sys.platform == 'win32' else \
        os.path.join(WAZUH_PATH, 'etc', 'ossec.conf')

    with open(conf_path, "r") as sources:
        lines = sources.readlines()

    with open(conf_path, "w") as sources:
        for line in lines:
            sources.write(
                re.sub(f'<{param}>.*</{param}>', f'<{param}>{value}</{param}>', line))


def callback_detect_end_scan(line):
    if 'File integrity monitoring scan ended.' in line:
        return line
    return None


def callback_detect_event(line):
    msg = r'.*Sending FIM event: (.+)$'
    match = re.match(msg, line)

    try:
        if json.loads(match.group(1))['type'] == 'event':
            return json.loads(match.group(1))
    except (AttributeError, JSONDecodeError, KeyError):
        pass

    return None


def callback_detect_integrity_event(line):
    match = re.match(r'.*Sending integrity control message: (.+)$', line)
    if match:
        return json.loads(match.group(1))
    return None


def callback_detect_integrity_state(line):
    event = callback_detect_integrity_event(line)
    if event:
        if event['type'] == 'state':
            return event
    return None


def callback_detect_synchronization(line):
    if 'Performing synchronization check' in line:
        return line
    return None


def callback_ignore(line):
    match = re.match(r".*Ignoring '.*?' '(.*?)' due to( sregex)? '.*?'", line)
    if match:
        return match.group(1)
    return None


def callback_restricted(line):
    match = re.match(r".*Ignoring file '(.*?)' due to restriction '.*?'", line)
    if match:
        return match.group(1)
    return None


def callback_audit_health_check(line):
    if 'Whodata health-check: Success.' in line:
        return True
    return None


def callback_audit_cannot_start(line):
    match = re.match(r'.*Who-data engine could not start. Switching who-data to real-time.', line)
    if match:
        return True
    return None


def callback_audit_added_rule(line):
    match = re.match(r'.*Added audit rule for monitoring directory: \'(.+)\'', line)
    if match:
        return match.group(1)
    return None


def callback_audit_rules_manipulation(line):
    if 'Detected Audit rules manipulation' in line:
        return True
    return None


def callback_audit_removed_rule(line):
    match = re.match(r'.* Audit rule removed.', line)
    if match:
        return True
    return None


def callback_audit_deleting_rule(line):
    match = re.match(r'.*Deleting Audit rules...', line)
    if match:
        return True
    return None


def callback_audit_connection(line):
    if '(6030): Audit: connected' in line:
        return True
    return None


def callback_audit_connection_close(line):
    match = re.match(r'.*Audit: connection closed.', line)
    if match:
        return True
    return None


def callback_audit_loaded_rule(line):
    match = re.match(r'.*Audit rule loaded: -w (.+) -p', line)
    if match:
        return match.group(1)
    return None


def callback_audit_event_too_long(line):
    if 'Caching Audit message: event too long' in line:
        return True
    return None


def callback_audit_reloaded_rule(line):
    match = re.match(r'.*Reloaded audit rule for monitoring directory: \'(.+)\'', line)
    if match:
        return match.group(1)
    return None


def callback_audit_key(line):
    if 'Match audit_key' in line and 'key="wazuh_hc"' not in line and 'key="wazuh_fim"' not in line:
        return line
    return None


def callback_realtime_added_directory(line):
    match = re.match(r'.*Directory added for real time monitoring: \'(.+)\'', line)
    if match:
        return match.group(1)
    return None


def callback_configuration_error(line):
    match = re.match(r'.*CRITICAL: \(\d+\): Configuration error at', line)
    if match:
        return True
    return None


def callback_symlink_scan_ended(line):
    if 'Links check finalized.' in line:
        return True
    else:
        return None


def callback_syscheck_message(line):
    if callback_detect_integrity_event(line) or callback_detect_event(line):
        match = re.match(r"(\d{4}/\d{2}/\d{2} \d{2}:\d{2}:\d{2}).*({.*?})$", line)
        if match:
            return datetime.strptime(match.group(1), '%Y/%m/%d %H:%M:%S'), json.dumps(match.group(2))
        return None


def check_time_travel(time_travel):
    """Changes date and time of the system.

    :param time_travel boolean True if we need to update time, False otherwise
    """
    if time_travel:
        TimeMachine.travel_to_future(timedelta(hours=13))


def callback_configuration_warning(line):
    match = re.match(r'.*WARNING: \(\d+\): Invalid value for element', line)
    if match:
        return True
    return None


def callback_entries_path_count(line):
    match = re.match(r'.*Fim inode entries: (\d+), path count: (\d+)', line)

    if match:
        return match.group(1), match.group(2)


def callback_fim_event_message(line):
    match = re.match(r'^agent (\d{3,}) syscheck (\w+) (.+)$', line)
    if match:
        try:
            body = json.loads(match.group(3))
        except json.decoder.JSONDecodeError:
            body = match.group(3)
        return match.group(1), match.group(2), body
    return None


class EventChecker:
    """Utility to allow fetch events and validate them."""

    def __init__(self, log_monitor, folder, file_list=['testfile0'], options=None, custom_validator=None):
        self.log_monitor = log_monitor
        self.folder = folder
        self.file_list = file_list
        self.custom_validator = custom_validator
        self.options = options
        self.events = None

    def fetch_and_check(self, event_type, min_timeout=1, triggers_event=True):
        """Calls both 'fetch_events' and 'check_events'.

        :param event_type String Expected type of the raised event. It can be 'added', 'modified' or 'deleted'.
        :param min_timeout int Seconds to wait until an event is raised when trying to fetch.
        :param triggers_event boolean True if the event should be raised, False otherwise.
        """
        self.events = self.fetch_events(min_timeout, triggers_event)
        self.check_events(event_type)

    def fetch_events(self, min_timeout=1, triggers_event=True):
        """Try to fetch events on a given log monitor. Will return a list with the events detected.

        :param min_timeout int Seconds to wait until an event is raised when trying to fetch.
        :param triggers_event boolean True if the event should be raised, False otherwise.
        """
        try:
            result = self.log_monitor.start(timeout=max(len(self.file_list) * 0.01, min_timeout),
                                            callback=callback_detect_event,
                                            accum_results=len(self.file_list)
                                            ).result()
            assert triggers_event, f'No events should be detected.'
            return result if isinstance(result, list) else [result]
        except TimeoutError:
            if triggers_event:
                raise

    def check_events(self, event_type):
        """Check and validate all events in the 'events' list.

        :param event_type String Expected type of the raised event. It can be 'added', 'modified' or 'deleted'.
        """

        def validate_checkers_per_event(events, options):
            """Checks if each event is properly formatted according to some checks.

            :param events List The event list to be checked
            :param options Set A Set of xml CHECK_* options. Default {CHECK_ALL}.
            """
            if options is not None:
                for ev in events:
                    validate_event(ev, options)

        def check_events_type(events, ev_type, file_list=['testfile0']):
            event_types = Counter(filter_events(events, ".[].data.type"))
            assert (event_types[ev_type] == len(file_list)), f'Non expected number of events. {event_types[ev_type]} != {len(file_list)}'

        def check_files_in_event(events, folder, file_list=['testfile0']):
            file_paths = filter_events(events, ".[].data.path")
            for file_name in file_list:
                expected_file_path = os.path.join(folder, file_name)
                expected_file_path = expected_file_path[:1].lower() + expected_file_path[1:]
                assert (expected_file_path in file_paths), f'{expected_file_path} does not exist in {file_paths}'

        def filter_events(events, mask):
            """Returns a list of elements matching a specified mask in the events list using jq module."""
            if sys.platform in ("win32", 'sunos5'):
                stdout = subprocess.check_output(["jq", "-r", mask], input=json.dumps(events).encode())
                return stdout.decode("utf8").strip().split(os.linesep)
            else:
                return jq(mask).transform(events, multiple_output=True)

        if self.events is not None:
            validate_checkers_per_event(self.events, self.options)
            check_events_type(self.events, event_type, self.file_list)
            check_files_in_event(self.events, self.folder, self.file_list)

            if self.custom_validator is not None:
                self.custom_validator.validate_after_cud(self.events)
                if event_type == "added":
                    self.custom_validator.validate_after_create(self.events)
                elif event_type == "modified":
                    self.custom_validator.validate_after_update(self.events)
                elif event_type == "deleted":
                    self.custom_validator.validate_after_delete(self.events)


class CustomValidator:
    """Enables using user-defined validators over the events when validating them with EventChecker"""
    def __init__(self, validators_after_create=None, validators_after_update=None,
                 validators_after_delete=None, validators_after_cud=None):
        self.validators_create = validators_after_create
        self.validators_update = validators_after_update
        self.validators_delete = validators_after_delete
        self.validators_cud = validators_after_cud

    def validate_after_create(self, events):
        """Custom validators to be applied by default when the event_type is 'added'.
        :param events List List of event to be validated.
        """
        if self.validators_create is not None:
            for event in events:
                for validator in self.validators_create:
                    validator(event)

    def validate_after_update(self, events):
        """Custom validators to be applied by default when the event_type is 'modified'.
        :param events List List of event to be validated.
        """
        if self.validators_update is not None:
            for event in events:
                for validator in self.validators_update:
                    validator(event)

    def validate_after_delete(self, events):
        """Custom validators to be applied by default when the event_type is 'deleted'.
        :param events List List of event to be validated.
        """
        if self.validators_delete is not None:
            for event in events:
                for validator in self.validators_delete:
                    validator(event)

    def validate_after_cud(self, events):
        """Custom validators to be applied always by default.
        :param events List List of event to be validated.
        """
        if self.validators_cud is not None:
            for event in events:
                for validator in self.validators_cud:
                    validator(event)


def regular_file_cud(folder, log_monitor, file_list=['testfile0'], time_travel=False, min_timeout=1, options=None,
                     triggers_event=True, validators_after_create=None, validators_after_update=None,
                     validators_after_delete=None, validators_after_cud=None):
    """Checks if creation, update and delete events are detected by syscheck.

    :param folder: Path where the files will be created
    :type folder: String
    :param log_monitor: File event monitor
    :type log_monitor: FileMonitor
    :param file_list: List/Dict with the file names and content.
    List -> ['name0', 'name1'] -- Dict -> {'name0': 'content0', 'name1': 'content1'}
    If it is a list, it will be transformed to a dict with empty strings in each value.
    :type file_list: Either List or Dict
    :param time_travel: Boolean to determine if there will be time travels or not
    :type time_travel: Boolean
    :param min_timeout: Minimum timeout
    :type min_timeout: Float
    :param options: Dict with all the checkers
    :type options: Dict. Default value is None.
    :param triggers_event: Boolean to determine if the event should be raised or not.
    :type triggers_event: Boolean
    :param validators_after_create: list of functions that validate an event triggered when a new file is created. Each
    function must accept a param to receive the event to be validated.
    :type validators_after_create: list
    :param validators_after_update: list of functions that validate an event triggered when a new file is modified. Each
    function must accept a param to receive the event to be validated.
    :type validators_after_update: list
    :param validators_after_delete: list of functions that validate an event triggered when a new file is deleted. Each
    function must accept a param to receive the event to be validated.
    :type validators_after_delete: list
    :param validators_after_cud: list of functions that validate an event triggered when a new file is created, modified
    or deleted. Each function must accept a param to receive the event to be validated.
    :type validators_after_cud: list
    :return: None
    """
    # Transform file list
    if not isinstance(file_list, list) and not isinstance(file_list, dict):
        raise ValueError('Value error. It can only be list or dict')
    elif isinstance(file_list, list):
        file_list = {i: '' for i in file_list}

    custom_validator = CustomValidator(validators_after_create, validators_after_update,
                                       validators_after_delete, validators_after_cud)
    event_checker = EventChecker(log_monitor, folder, file_list, options, custom_validator)

    # Create text files
    for name, content in file_list.items():
        create_file(REGULAR, folder, name, content=content)

    check_time_travel(time_travel)
    event_checker.fetch_and_check('added', min_timeout, triggers_event)

    # Modify previous text files
    for name, content in file_list.items():
        modify_file(folder, name, is_binary=isinstance(content, bytes))

    check_time_travel(time_travel)
    event_checker.fetch_and_check('modified', min_timeout, triggers_event)

    # Delete previous text files
    for name in file_list:
        delete_file(folder, name)

    check_time_travel(time_travel)
    event_checker.fetch_and_check('deleted', min_timeout, triggers_event)


def detect_initial_scan(file_monitor):
    """Detect initial scan when restarting Wazuh

    :param file_monitor: Wazuh log monitor to detect syscheck events
    :type file_monitor: FileMonitor
    :return: None
    """
    file_monitor.start(timeout=60, callback=callback_detect_end_scan)
    # Add additional sleep to avoid changing system clock issues (TO BE REMOVED when syscheck has not sleeps anymore)
    time.sleep(11)


def generate_params(extra_params: dict = None, extra_metadata: dict = None, *, modes: list = None):
    """ Swings between FIM_MODE values to expand params and metadata with optional extra values.

        extra_params = {'WILDCARD': {'attribute': ['list', 'of', 'values']}} - Max. 3 elements in the list of values
                            or
                       {'WILDCARD': {'attribute': 'value'}} - It will have the same value for scheduled, realtime and whodata
                            or
                       {'WILDCARD': 'value'} - Valid when param is not an attribute. (ex: 'MODULE_NAME': __name__)

        extra_metadata = {'metadata': ['list', 'of', 'values']} - Same as params
                            or
                         {'metadata': 'value'} - Same as params

        The length of extra_params and extra_metadata must be the same

        Examples:
        p, m = set_configuration( extra_params={'REPORT_CHANGES': {'report_changes': 'value'},
                                               'MODULE_NAME': 'name''},
                                  extra_metadata={'report_changes': ['one', 'two'],
                                                 'module_name': 'name'},
                                  modes=['realtime', 'whodata'] )
        Returns:
        p = [{'FIM_MODE': {'realtime': 'yes'}, 'REPORT_CHANGES': {'report_changes': 'value'},
                'MODULE_NAME': 'name''},
             {'FIM_MODE': {'whodata': 'yes'}, 'REPORT_CHANGES': {'report_changes': 'value'},
                'MODULE_NAME': 'name''}
            ]

        m = [{'fim_mode': 'realtime', 'report_changes': 'one', 'module_name': 'name'},
             {'fim_mode': 'whodata', 'report_changes': 'two', 'module_name': 'name'}
            ]

    :param extra_params: params to add
    :param extra_metadata: metadata to add
    :param modes: monitoring modes to add. All by default
    :return: Tuple(params, metadata)
    """
    def transform_param(mutable_object: dict):
        for k, v in mutable_object.items():
            if isinstance(v, dict):
                for v_key, v_value in v.items():
                    mutable_object[k][v_key] = v_value if isinstance(v_value, list) else [v_value, v_value, v_value]

    def transform_metadata(mutable_object: dict):
        for k, v in mutable_object.items():
            mutable_object[k] = v if isinstance(v, list) else [v, v, v]

    add = False
    if extra_params is not None and extra_metadata is not None:
        assert len(extra_params) == len(extra_metadata), f'params and metadata length not equal'
        transform_param(extra_params)
        transform_metadata(extra_metadata)
        add = True

    fim_param = []
    fim_metadata = []

    modes = modes if modes is not None else ['scheduled', 'realtime', 'whodata']
    for mode in modes:
        if mode == 'scheduled':
            fim_param.append({'FIM_MODE': ''})
            fim_metadata.append({'fim_mode': 'scheduled'})
        elif mode == 'realtime' and sys.platform != 'darwin' and sys.platform != 'sunos5':
            fim_param.append({'FIM_MODE': {'realtime': 'yes'}})
            fim_metadata.append({'fim_mode': 'realtime'})
        elif mode == 'whodata' and sys.platform != 'darwin' and sys.platform != 'sunos5':
            fim_param.append({'FIM_MODE': {'whodata': 'yes'}})
            fim_metadata.append({'fim_mode': 'whodata'})

    params = []
    metadata = []

    for i, (fim_mode_param, fim_mode_meta) in enumerate(zip(fim_param, fim_metadata)):
        p_aux: dict = deepcopy(fim_mode_param)
        m_aux: dict = deepcopy(fim_mode_meta)
        if add:
            for key, value in extra_params.items():
                p_aux[key] = {k: v[i] for k, v in value.items()} if isinstance(value, dict) else value
            m_aux.update({key: value[i] for key, value in extra_metadata.items()})
        params.append(p_aux)
        metadata.append(m_aux)

    return params, metadata
