import pytest
import re

from pathlib import Path

from wazuh_testing.tools.configuration import set_section_wazuh_conf
from wazuh_testing.tools.file import read_file
from wazuh_testing.tools.utils import get_current_ip
from wazuh_testing.tools.virtualization import AgentsDockerizer


AGENT_CONFIG_PATH = Path(Path(Path(__file__).parent, 'data', 'conf_template'))


@pytest.fixture()
def dockerized_agents(agents_config: str, metadata: dict) -> AgentsDockerizer:
    """Build and cleanup dockerized agents.

    Args:
        agents_config (str): Agents ossec.conf.
        metadata (dict): Test metadata to get the agents_amount from.
    Yield:
        AgentsDockerizer: Instance to handle the dockerized agents.
    """
    agents = AgentsDockerizer(agents_config, metadata.get('agents_amount'))

    yield agents

    agents.stop()
    agents.destroy()


@pytest.fixture()
def agents_config(configuration: dict) -> str:
    """Retrieves an ossec.conf ready to be used by the agents to connect
    to the actual server.

    Args:
        configuration (dict): Configuration data to set in the ossec.conf.
    Yield:
        str: An ossec.conf for the dockerized agents.
    """

    def set_current_ip_to_agent_config(config: str) -> str:
        # Regex to match a substring inside the address tags.
        reg = '(?<=%s).*?(?=%s)' % ('<address>', '</address>')
        r = re.compile(reg, re.DOTALL)
        # Replace the matching substring with the actual IP.
        return r.sub(get_current_ip(), config)

    # Get template and configuration sections.
    template = read_file(AGENT_CONFIG_PATH)
    config_sections = configuration.get('sections')
    # Configure the agents ossec.conf with the correct values.
    agents_config = set_section_wazuh_conf(config_sections, template)
    agents_config = ''.join(agents_config)
    agents_config = set_current_ip_to_agent_config(agents_config)

    yield agents_config
