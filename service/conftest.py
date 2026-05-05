# service/conftest.py
import sys
import os

# Add the repo root to Python path so `service.app` imports resolve correctly
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
