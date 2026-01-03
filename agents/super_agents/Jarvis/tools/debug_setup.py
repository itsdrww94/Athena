import sys
import os
print(f"Python executable: {sys.executable}")
print(f"CWD: {os.getcwd()}")
try:
    sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "../../../../")))
    print("Path appended.")
    import services.notion_service
    print("Imported services.notion_service")
except Exception as e:
    print(f"Error: {e}")
