# Opens commonly used browser tabs at work.

import webbrowser
import time


webbrowser.open('https://outlook.live.com/owa/', new=1)
time.sleep(1)
webbrowser.open_new_tab('https://mail.google.com/mail')
webbrowser.open_new_tab('https://calendar.google.com/calendar/')
webbrowser.open_new_tab('https://www.linkedin.com/')
webbrowser.open_new_tab('https://login.salesforce.com/')
