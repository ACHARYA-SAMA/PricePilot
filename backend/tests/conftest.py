"""pytest conftest for backend tests."""
import sys
import os
# Ensure the backend root is on the Python path
sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))
