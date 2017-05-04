import pyautogui
import time


width, height = pyautogui.size()

# bringing outlook to front
pyautogui.moveTo(500, 0)
pyautogui.click()

# selects new items on outlook
pyautogui.moveTo(160, 100)
pyautogui.click()


# more items
pyautogui.moveTo(213, 291)
time.sleep(0.5)
pyautogui.click()

# choose form
pyautogui.moveTo(400, 385)
time.sleep(0.5)
pyautogui.click()

# open drop-down
pyautogui.moveTo(1058, 368)
time.sleep(0.1)
pyautogui.click()

# look in user templates in file system
pyautogui.moveTo(947, 436)
time.sleep(0.1)
pyautogui.click()

# select template
pyautogui.moveTo(1168, 421)
time.sleep(0.1)
pyautogui.click()

# open
pyautogui.moveTo(1210, 604)
time.sleep(0.1)
pyautogui.click()
