# Copyright (C) 2015-2021, Wazuh Inc.
# Created by Wazuh, Inc. <info@wazuh.com>.
# This program is free software; you can redistribute it and/or modify it under the terms of GPLv2
from setuptools import setup, find_packages
import glob

package_data_list = ['data/agent.conf',
                     'data/syscheck_event.json',
                     'data/syscheck_event_windows.json',
                     'data/mitre_event.json',
                     'data/analysis_alert.json',
                     'data/analysis_alert_windows.json',
                     'data/state_integrity_analysis_schema.json',
                     'data/gcp_event.json',
                     'data/keepalives.txt',
                     'data/rootcheck.txt',
                     'data/syscollector.py',
                     'data/winevt.py',
                     'data/sslmanager.key',
                     'data/sslmanager.cert',
                     'tools/macos_log/log_generator.m',
                     'qa_docs/config.yaml'
                      ]

directories = glob.glob('wazuh_testing/qa_docs/search_ui/')
for directory in directories:
    files = glob.glob(directory+'*')
    for file in files:
      package_data_list.append(file)

setup(name='wazuh_testing',
      version='4.3.0',
      description='Wazuh testing utilities to help programmers automate tests',
      url='https://github.com/wazuh',
      author='Wazuh',
      author_email='hello@wazuh.com',
      license='GPLv2',
      packages=find_packages(),
      package_data={'wazuh_testing': package_data_list},
      entry_points={
        'console_scripts': [
            'simulate-agents=wazuh_testing.scripts.simulate_agents:main',
            'wazuh-metrics=wazuh_testing.scripts.wazuh_metrics:main',
            'wazuh-statistics=wazuh_testing.scripts.wazuh_statistics:main',
            'data-visualizer=wazuh_testing.scripts.data_visualizations:main',
            'simulate-api-load=wazuh_testing.scripts.simulate_api_load:main',
            'wazuh-log-metrics=wazuh_testing.scripts.wazuh_log_metrics:main',
            'qa-docs=wazuh_testing.scripts.qa_docs:main'
        ],
      },
      include_package_data=True,
      zip_safe=False
      )
