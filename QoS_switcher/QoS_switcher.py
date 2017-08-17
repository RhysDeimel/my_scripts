from selenium import webdriver
import secrets
import argparse

parser = argparse.ArgumentParser(description='Enable or disable bandwidth control')
parser.add_argument('state', choices=['y', 'n'], help='Choose to enable or disable bandwidth control')
args = parser.parse_args()

driver = webdriver.Chrome()
driver.implicitly_wait(15)
driver.get('http://192.168.1.1/')

username_input = driver.find_element_by_id('userName')
password_input = driver.find_element_by_id('pcPassword')
login_button = driver.find_element_by_id('loginBtn')

username_input.send_keys(secrets.login[0]) # username
password_input.send_keys(secrets.login[1]) # password
login_button.click()

bandwidth_control = driver.find_element_by_id('menu_tc')
bandwidth_control.click()

bc_checkbox = driver.find_element_by_id('enableTc')
bc_submit = driver.find_element_by_id('saveBtn')

if args.state == 'y':
    print('Enabling QoS')
    if bc_checkbox.is_selected():
        print('QoS is already enabled!')
    else:
        bc_checkbox.click()
        bc_submit.click()
        print('QoS enabled')
else:
    print('Disabling QoS')
    if bc_checkbox.is_selected():
        bc_checkbox.click()
        bc_submit.click()
        print('QoS disabled')
    else:
        print('QoS is already disabled!')

driver.close()
exit()