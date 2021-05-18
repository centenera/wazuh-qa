import { When } from 'cypress-cucumber-preprocessor/steps';

import WazuhMenu from '../../../pageobjects/wzMenu/wazuh-menu';

When('The user navigates to rules', () => {
  const wzMenu = new WazuhMenu();
  wzMenu.goToRules();
  cy.wait(3000);
});
