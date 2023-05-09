import time
from pywinauto.application import Application

# Start the Notepad application
app = Application().start("notepad.exe")

# Find the Notepad window
notepad_window = app.window(title="Untitled - Notepad")

# Set focus to the Notepad window and type some text
notepad_window.set_focus()
notepad_window.Edit.type_keys("This is a test using pywinauto.", with_spaces=True)

# Open the "File" menu and click "Save As"
notepad_window.menu_select("File -> Save As")

# Wait for the "Save As" window to appear
save_as_window = app.window(title="Save As")
save_as_window.wait('visible', timeout=10)

# Set the file name and click the "Save" button
save_as_window.Edit.set_text("test_pywinauto.txt")
save_as_window.Save.click()

# Close Notepad
notepad_window.close()

print("Done!")
