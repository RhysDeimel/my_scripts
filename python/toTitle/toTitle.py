#! python3
import pyperclip

word = pyperclip.paste()
word = word.title()
pyperclip.copy(word)
print("Done!")
