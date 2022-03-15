# Copyright (C) 2015-2022, Wazuh Inc.
# Created by Wazuh, Inc. <info@wazuh.com>.
# This program is free software; you can redistribute it and/or modify it under the terms of GPLv2

import os

from wazuh_testing.tools import WAZUH_PATH, WAZUH_LOGS_PATH


# Agent Variables
AGENT_STATUS_ACTIVE = 'active'
AGENT_STATUS_NEVER_CONNECTED = 'never_connected'
AGENT_STATUS_DISCONNECTED = 'disconnected'
AGENT_NO_GROUPS = 'Null'
AGENT_GROUPS_DEFAULT = 'default'


# Error Messages
ERR_MSG_CLIENT_KEYS_IN_MASTER_NOT_FOUND = f'Did not find the expected keys generated in the master node.'





def get_agent_id(host_manager):
    # Gets the first agent id in the master's client.keys file
    return host_manager.run_command('wazuh-master', f'cut -c 1-3 {WAZUH_PATH}/etc/client.keys')


def get_id_from_agent(agent, host_manager):
    # Get the agent id from the agent's client.keys file
    return host_manager.run_command(agent, f'cut -c 1-3 {WAZUH_PATH}/etc/client.keys')


def restart_cluster(hosts_list, host_manager):
    # Restart the cluster's hosts
    for host in hosts_list:
        if "agent" in host:
            host_manager.get_host(host).ansible('command', f'service wazuh-agent restart', check=False)
        host_manager.control_service(host=host, service='wazuh', state="restarted")


def clean_cluster_logs(hosts_list, host_manager):
    # Clean ossec.log and cluster.log
    for host in hosts_list:
        host_manager.clear_file(host=host, file_path=os.path.join(WAZUH_LOGS_PATH, 'ossec.log'))
        if "worker" in host or "master" in host:
            host_manager.clear_file(host=host, file_path=os.path.join(WAZUH_LOGS_PATH, 'cluster.log'))


def remove_cluster_agents(wazuh_master, agents_list, host_manager):
    # Removes a list of agents from the cluster using manage_agents
    agent_id = get_agent_id(host_manager)
    while (agent_id != ''):
        host_manager.get_host(wazuh_master).ansible("command", f'{WAZUH_PATH}/bin/manage_agents -r {agent_id}',
                                                    check=False)
        agent_id = get_agent_id(host_manager)
    for agent in agents_list:
        host_manager.control_service(host=agent, service='wazuh', state="stopped")
        host_manager.clear_file(agent, file_path=os.path.join(WAZUH_PATH, 'etc', 'client.keys'))


def get_agents_in_cluster(host, host_manager):
    # Get the list of agents in the cluster
    return host_manager.run_command(host, f'{WAZUH_PATH}/bin/cluster_control -a')


def check_keys_file(host, host_manager):
    # Checks that the key file is not empty in a host
    return host_manager.get_file_content(host, os.path.join(WAZUH_PATH, 'etc', 'client.keys'))


def create_new_agent_group(host, group_name, host_manager):
    # Creates an agent group
    host_manager.run_command(host, f"/var/ossec/bin/agent_groups -q -a -g {group_name}")


# Create new group and assing agent
def assign_agent_to_new_group(host, id_group, id_agent, host_manager):
    # Create group
    host_manager.run_command(host, f"/var/ossec/bin/agent_groups -q -a -g {id_group}")

    # Add agent to a group
    host_manager.run_command(host, f"/var/ossec/bin/agent_groups -q -a -i {id_agent} -g {id_group}")


def delete_group_of_agents(host, id_group, host_manager):
    # Delete group
    host_manager.run_command(host, f"/var/ossec/bin/agent_groups -q -r -g {id_group}")


def check_agent_groups(agent_id, group_to_check, hosts_list, host_manager):
    # Check the expected group is in the group data for the agent
    for host in hosts_list:
        group_data = host_manager.run_command(host, f'{WAZUH_PATH}/bin/agent_groups -s -i {agent_id}')
        assert group_to_check in group_data


def check_agent_status(agent_id, agent_name, agent_ip, status, host_manager, hosts_list):
    # Check the agent has the expected status (never_connected, pending, active, disconnected)
    for host in hosts_list:
        data = get_agents_in_cluster(host, host_manager)
        assert f"{agent_id}  {agent_name}  {agent_ip}  {status}" in data


def check_agents_status_in_node(agent_expected_status_list, host, host_manager):
    # Checks the expected status o of different agent in a host.
    # List format: [f"{agent_id}  {agent_name}  {agent_ip}  {status}",...]
    data = get_agents_in_cluster(host, host_manager)
    for status in agent_expected_status_list:
        assert status in data


def change_agent_group_with_wdb(agent_id, new_group, host, host_manager):
    # Uses wdb commands to change the group of an agent
    query = f'{"id":{agent_id}, "group":"{new_group}"}'
    group_data = host_manager.run_command(host, f"{WAZUH_PATH}/bin/query-wdb global 'update-agent-group {query}'")
    return group_data
