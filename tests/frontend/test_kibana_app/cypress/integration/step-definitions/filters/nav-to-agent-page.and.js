import { And } from 'cypress-cucumber-preprocessor/steps';
import { clickElement, elementIsVisible} from '../../utils/driver';
import {
  wazuhMenuButton,
  agentsButton
} from '../../pageobjects/wazuh-menu/wazuh-menu.page';
  import {
  } from '../../pageobjects/agents/agents.page';

And('The user navigates to the agent page', () => {
  clickElement(wazuhMenuButton);
  elementIsVisible(agentsButton);
  clickElement(agentsButton);
});